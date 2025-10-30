"""
Unit Tests for Portfolio Risk Manager

Tests portfolio-level risk management including:
- Position limits (single and total exposure)
- Daily loss limits and circuit breaker
- Position tracking and updates
- Concentration analysis
- Leverage limits

Author: Testing Team
Date: 2025-10-29
Sprint: 3, Stream B
"""

from datetime import datetime
from decimal import Decimal

import pytest

from workspace.features.risk_manager import (PortfolioLimits,
                                             PortfolioRiskManager,
                                             PositionInfo)


@pytest.fixture
def default_limits():
    """Default portfolio limits for testing"""
    return PortfolioLimits(
        max_portfolio_value=Decimal("2626.96"),
        max_single_position_pct=0.10,
        max_total_exposure_pct=0.80,
        daily_loss_limit_pct=0.07,
        max_leverage=10,
    )


@pytest.fixture
def risk_manager(default_limits):
    """Portfolio risk manager with default limits"""
    return PortfolioRiskManager(default_limits)


@pytest.fixture
def sample_position():
    """Sample position for testing"""
    return PositionInfo(
        symbol="BTCUSDT",
        side="LONG",
        quantity=Decimal("0.01"),
        entry_price=Decimal("50000.00"),
        current_price=Decimal("50500.00"),
        unrealized_pnl=Decimal("5.00"),
        leverage=5,
        position_value_chf=Decimal("227.27"),  # ~10% of portfolio
    )


# ============================================================================
# Initialization Tests
# ============================================================================


def test_initialization(default_limits):
    """Test portfolio risk manager initialization"""
    manager = PortfolioRiskManager(default_limits)

    assert manager.limits == default_limits
    assert len(manager.positions) == 0
    assert not manager.circuit_breaker_active


def test_custom_limits():
    """Test initialization with custom limits"""
    limits = PortfolioLimits(
        max_portfolio_value=Decimal("5000.00"),
        max_single_position_pct=0.05,
        max_total_exposure_pct=0.60,
        daily_loss_limit_pct=0.05,
        max_leverage=5,
    )

    manager = PortfolioRiskManager(limits)

    assert manager.limits.max_single_position_pct == 0.05
    assert manager.limits.max_total_exposure_pct == 0.60


# ============================================================================
# Position Limit Tests
# ============================================================================


def test_check_position_limits_within_limits(risk_manager):
    """Test position check when within limits"""
    # 5% of portfolio = 131.35 CHF
    can_open, reason = risk_manager.check_position_limits(Decimal("131.35"))

    assert can_open is True
    assert "OK" in reason


def test_check_position_limits_exceeds_single_limit(risk_manager):
    """Test position check when exceeding single position limit"""
    # 15% of portfolio (exceeds 10% limit)
    position_value = Decimal("400.00")

    can_open, reason = risk_manager.check_position_limits(position_value)

    assert can_open is False
    assert "single position limit" in reason.lower()


def test_check_position_limits_exceeds_total_exposure(risk_manager, sample_position):
    """Test position check when exceeding total exposure limit"""
    # Add positions totaling 75% of portfolio (each 9% to stay under 10% single limit)
    for i in range(9):
        pos = PositionInfo(
            symbol=f"SYMBOL{i}",
            side="LONG",
            quantity=Decimal("0.1"),
            entry_price=Decimal("1000.00"),
            current_price=Decimal("1000.00"),
            unrealized_pnl=Decimal("0"),
            leverage=1,
            position_value_chf=Decimal("218.91"),  # ~8.3% each = 75% total
        )
        risk_manager.add_position(pos)

    # Try to add another 8% (would exceed 80% total limit)
    can_open, reason = risk_manager.check_position_limits(Decimal("210.00"))

    assert can_open is False
    assert "total exposure" in reason.lower()


def test_check_position_limits_exact_limit(risk_manager):
    """Test position check at exact single position limit"""
    # Exactly 10% of portfolio
    position_value = Decimal("262.696")

    can_open, reason = risk_manager.check_position_limits(position_value)

    assert can_open is True


# ============================================================================
# Leverage Limit Tests
# ============================================================================


def test_check_leverage_within_limit(risk_manager):
    """Test leverage check within limit"""
    within_limit, reason = risk_manager.check_leverage_limit(5)

    assert within_limit is True
    assert "OK" in reason


def test_check_leverage_exceeds_limit(risk_manager):
    """Test leverage check exceeding limit"""
    within_limit, reason = risk_manager.check_leverage_limit(15)

    assert within_limit is False
    assert "exceeds maximum" in reason.lower()


def test_check_leverage_at_limit(risk_manager):
    """Test leverage check at exact limit"""
    within_limit, reason = risk_manager.check_leverage_limit(10)

    assert within_limit is True


# ============================================================================
# Daily Loss Limit Tests
# ============================================================================


def test_check_daily_loss_within_limit(risk_manager):
    """Test daily loss check within limit"""
    # Loss of 50 CHF (< 7% of 2626.96 = 183.89 CHF)
    within_limit, message = risk_manager.check_daily_loss_limit(Decimal("-50.00"))

    assert within_limit is True
    assert "Daily loss" in message


def test_check_daily_loss_exceeds_limit(risk_manager):
    """Test daily loss exceeding limit triggers circuit breaker"""
    # Loss of 200 CHF (> 7% limit of 183.89 CHF)
    within_limit, message = risk_manager.check_daily_loss_limit(Decimal("-200.00"))

    assert within_limit is False
    assert "CIRCUIT BREAKER" in message
    assert risk_manager.circuit_breaker_active is True


def test_check_daily_loss_positive_pnl(risk_manager):
    """Test daily loss check with positive P&L"""
    within_limit, message = risk_manager.check_daily_loss_limit(Decimal("50.00"))

    assert within_limit is True
    assert "+50.00" in message


def test_circuit_breaker_reset(risk_manager):
    """Test circuit breaker can be reset"""
    # Trigger circuit breaker
    risk_manager.check_daily_loss_limit(Decimal("-200.00"))
    assert risk_manager.circuit_breaker_active is True

    # Reset
    risk_manager.reset_circuit_breaker()
    assert risk_manager.circuit_breaker_active is False


# ============================================================================
# Position Tracking Tests
# ============================================================================


def test_add_position(risk_manager, sample_position):
    """Test adding a position"""
    risk_manager.add_position(sample_position)

    assert len(risk_manager.positions) == 1
    assert "BTCUSDT" in risk_manager.positions
    assert risk_manager.positions["BTCUSDT"] == sample_position


def test_remove_position(risk_manager, sample_position):
    """Test removing a position"""
    risk_manager.add_position(sample_position)
    risk_manager.remove_position("BTCUSDT")

    assert len(risk_manager.positions) == 0
    assert "BTCUSDT" not in risk_manager.positions


def test_update_position(risk_manager, sample_position):
    """Test updating a position"""
    risk_manager.add_position(sample_position)

    # Update price and P&L
    risk_manager.update_position(
        "BTCUSDT",
        current_price=Decimal("51000.00"),
        unrealized_pnl=Decimal("10.00"),
    )

    updated_pos = risk_manager.get_position("BTCUSDT")
    assert updated_pos.current_price == Decimal("51000.00")
    assert updated_pos.unrealized_pnl == Decimal("10.00")


def test_get_nonexistent_position(risk_manager):
    """Test getting a position that doesn't exist"""
    position = risk_manager.get_position("NONEXISTENT")

    assert position is None


def test_get_all_positions(risk_manager):
    """Test getting all positions"""
    # Add multiple positions
    for i in range(3):
        pos = PositionInfo(
            symbol=f"SYMBOL{i}",
            side="LONG",
            quantity=Decimal("0.1"),
            entry_price=Decimal("1000.00"),
            current_price=Decimal("1000.00"),
            unrealized_pnl=Decimal("0"),
            leverage=1,
            position_value_chf=Decimal("100.00"),
        )
        risk_manager.add_position(pos)

    all_positions = risk_manager.get_all_positions()

    assert len(all_positions) == 3


# ============================================================================
# Portfolio Metrics Tests
# ============================================================================


def test_calculate_total_exposure(risk_manager):
    """Test total exposure calculation"""
    # Add 3 positions
    for i in range(3):
        pos = PositionInfo(
            symbol=f"SYMBOL{i}",
            side="LONG",
            quantity=Decimal("0.1"),
            entry_price=Decimal("1000.00"),
            current_price=Decimal("1000.00"),
            unrealized_pnl=Decimal("0"),
            leverage=1,
            position_value_chf=Decimal("100.00"),
        )
        risk_manager.add_position(pos)

    total_exposure = risk_manager.calculate_total_exposure()

    assert total_exposure == Decimal("300.00")


def test_calculate_total_unrealized_pnl(risk_manager):
    """Test total unrealized P&L calculation"""
    # Add positions with different P&L
    positions = [
        ("SYM1", Decimal("10.00")),
        ("SYM2", Decimal("-5.00")),
        ("SYM3", Decimal("15.00")),
    ]

    for symbol, pnl in positions:
        pos = PositionInfo(
            symbol=symbol,
            side="LONG",
            quantity=Decimal("0.1"),
            entry_price=Decimal("1000.00"),
            current_price=Decimal("1000.00"),
            unrealized_pnl=pnl,
            leverage=1,
            position_value_chf=Decimal("100.00"),
        )
        risk_manager.add_position(pos)

    total_pnl = risk_manager.calculate_total_unrealized_pnl()

    assert total_pnl == Decimal("20.00")  # 10 - 5 + 15


def test_get_largest_position(risk_manager):
    """Test getting largest position"""
    # Add positions of different sizes
    positions = [
        ("SMALL", Decimal("50.00")),
        ("LARGE", Decimal("200.00")),
        ("MEDIUM", Decimal("100.00")),
    ]

    for symbol, value in positions:
        pos = PositionInfo(
            symbol=symbol,
            side="LONG",
            quantity=Decimal("0.1"),
            entry_price=Decimal("1000.00"),
            current_price=Decimal("1000.00"),
            unrealized_pnl=Decimal("0"),
            leverage=1,
            position_value_chf=value,
        )
        risk_manager.add_position(pos)

    largest, value, pct = risk_manager.get_largest_position()

    assert largest.symbol == "LARGE"
    assert value == Decimal("200.00")
    assert pct > 7.0  # ~7.6% of portfolio


def test_get_portfolio_status(risk_manager, sample_position):
    """Test portfolio status snapshot"""
    risk_manager.add_position(sample_position)
    risk_manager.update_daily_pnl(Decimal("25.00"))

    status = risk_manager.get_portfolio_status()

    assert status.open_positions == 1
    assert status.total_exposure_chf == Decimal("227.27")
    assert status.daily_pnl == Decimal("25.00")
    assert isinstance(status.timestamp, datetime)


# ============================================================================
# Concentration Analysis Tests
# ============================================================================


def test_check_concentration_diversified(risk_manager):
    """Test concentration check with well-diversified portfolio"""
    # Add 5 small positions (5% each)
    for i in range(5):
        pos = PositionInfo(
            symbol=f"SYMBOL{i}",
            side="LONG",
            quantity=Decimal("0.1"),
            entry_price=Decimal("1000.00"),
            current_price=Decimal("1000.00"),
            unrealized_pnl=Decimal("0"),
            leverage=1,
            position_value_chf=Decimal("131.35"),  # ~5% each
        )
        risk_manager.add_position(pos)

    is_diversified, warnings = risk_manager.check_position_concentration()

    assert is_diversified is True
    assert len(warnings) == 0


def test_check_concentration_single_large_position(risk_manager):
    """Test concentration check with one large position"""
    # One position taking 50% of portfolio
    large_pos = PositionInfo(
        symbol="LARGE",
        side="LONG",
        quantity=Decimal("1.0"),
        entry_price=Decimal("1000.00"),
        current_price=Decimal("1000.00"),
        unrealized_pnl=Decimal("0"),
        leverage=1,
        position_value_chf=Decimal("1313.48"),  # 50% of portfolio
    )
    risk_manager.add_position(large_pos)

    is_diversified, warnings = risk_manager.check_position_concentration(
        max_concentration_pct=0.4
    )

    assert is_diversified is False
    assert len(warnings) > 0
    assert "Largest position" in warnings[0]


# ============================================================================
# Integration Test
# ============================================================================


def test_full_risk_workflow(risk_manager):
    """Test complete risk management workflow"""
    # 1. Check if we can open a position
    position_value = Decimal("200.00")
    can_open, _ = risk_manager.check_position_limits(position_value)
    assert can_open is True

    # 2. Open the position
    position = PositionInfo(
        symbol="BTCUSDT",
        side="LONG",
        quantity=Decimal("0.01"),
        entry_price=Decimal("50000.00"),
        current_price=Decimal("50000.00"),
        unrealized_pnl=Decimal("0"),
        leverage=5,
        position_value_chf=position_value,
    )
    risk_manager.add_position(position)

    # 3. Update with profit
    risk_manager.update_position(
        "BTCUSDT",
        current_price=Decimal("51000.00"),
        unrealized_pnl=Decimal("10.00"),
    )

    # 4. Check daily P&L
    risk_manager.update_daily_pnl(Decimal("10.00"))
    within_limit, _ = risk_manager.check_daily_loss_limit(Decimal("10.00"))
    assert within_limit is True

    # 5. Get status
    status = risk_manager.get_portfolio_status()
    assert status.open_positions == 1
    assert status.daily_pnl == Decimal("10.00")

    # 6. Close position
    risk_manager.remove_position("BTCUSDT")
    assert len(risk_manager.positions) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
