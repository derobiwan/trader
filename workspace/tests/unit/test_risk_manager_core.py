"""
Unit Tests for Risk Manager Core

Tests comprehensive risk validation including:
- Signal validation against all risk limits
- Position and exposure checking
- Leverage validation
- Stop-loss requirements
- Emergency position closure
- Multi-layer protection coordination

Author: Validation Engineer Team 2
Date: 2025-10-30
Sprint: 3, Stream A
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from workspace.features.risk_manager import RiskManager
from workspace.features.risk_manager.models import (
    CircuitBreakerState,
    CircuitBreakerStatus,
    Protection,
    ValidationStatus,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_exchange():
    """Mock exchange client"""
    return AsyncMock()


@pytest.fixture
def mock_trade_executor():
    """Mock trade executor"""
    executor = AsyncMock()
    executor.get_open_positions = AsyncMock(return_value=[])
    executor.close_position = AsyncMock()
    return executor


@pytest.fixture
def mock_position_tracker():
    """Mock position tracker"""
    tracker = MagicMock()
    tracker.get_open_positions = AsyncMock(return_value=[])
    return tracker


@pytest.fixture
def risk_manager(mock_exchange, mock_trade_executor, mock_position_tracker):
    """Risk manager with mocked dependencies"""
    return RiskManager(
        starting_balance_chf=Decimal("2626.96"),
        max_daily_loss_chf=Decimal("-183.89"),
        exchange=mock_exchange,
        trade_executor=mock_trade_executor,
        position_tracker=mock_position_tracker,
    )


@pytest.fixture
def valid_signal():
    """Valid trading signal"""
    signal = MagicMock()
    signal.symbol = "BTC/USDT:USDT"
    signal.confidence = Decimal("0.75")
    signal.size_pct = Decimal("0.15")  # 15%
    signal.leverage = 20
    signal.stop_loss_pct = Decimal("0.03")  # 3%
    return signal


@pytest.fixture
def mock_position():
    """Mock position"""
    position = MagicMock()
    position.id = "pos_123"
    position.symbol = "BTC/USDT:USDT"
    position.entry_price = Decimal("50000.00")
    position.stop_loss_pct = Decimal("0.03")
    position.side = "long"
    position.size_pct = Decimal("0.15")
    return position


# ============================================================================
# Initialization Tests
# ============================================================================


def test_risk_manager_initialization(risk_manager):
    """Test risk manager initializes correctly"""
    assert risk_manager.starting_balance_chf == Decimal("2626.96")
    assert risk_manager.current_balance_chf == Decimal("2626.96")
    assert risk_manager.circuit_breaker is not None
    assert risk_manager.stop_loss_manager is not None


def test_risk_manager_sub_managers_initialized(risk_manager):
    """Test sub-managers are initialized"""
    assert risk_manager.circuit_breaker.starting_balance_chf == Decimal("2626.96")
    assert risk_manager.circuit_breaker.max_daily_loss_chf == Decimal("-183.89")
    assert risk_manager.stop_loss_manager.exchange is not None


# ============================================================================
# Signal Validation - Success Cases
# ============================================================================


@pytest.mark.asyncio
async def test_validate_signal_success(risk_manager, valid_signal):
    """Test successful signal validation"""
    validation = await risk_manager.validate_signal(valid_signal)

    assert validation.status == ValidationStatus.APPROVED
    assert validation.approved is True
    assert len(validation.checks) > 0
    assert len(validation.rejection_reasons) == 0


@pytest.mark.asyncio
async def test_validate_signal_all_checks_present(risk_manager, valid_signal):
    """Test all required checks are performed"""
    validation = await risk_manager.validate_signal(valid_signal)

    check_names = [check.check_name for check in validation.checks]

    # Should have all major checks
    assert "Circuit Breaker" in check_names
    assert "Position Count" in check_names
    assert "Confidence" in check_names
    assert "Position Size" in check_names
    assert "Total Exposure" in check_names
    assert "Leverage" in check_names
    assert "Stop-Loss" in check_names


# ============================================================================
# Circuit Breaker Check Tests
# ============================================================================


@pytest.mark.asyncio
async def test_validate_signal_circuit_breaker_active(risk_manager, valid_signal):
    """Test validation when circuit breaker is active"""
    validation = await risk_manager.validate_signal(valid_signal)

    # Should pass circuit breaker check
    cb_check = next(
        (c for c in validation.checks if c.check_name == "Circuit Breaker"), None
    )
    assert cb_check is not None
    assert cb_check.passed is True


@pytest.mark.asyncio
async def test_validate_signal_circuit_breaker_tripped(risk_manager, valid_signal):
    """Test validation rejects when circuit breaker tripped"""
    # Trip circuit breaker
    await risk_manager.circuit_breaker.check_daily_loss(Decimal("-200.00"))

    validation = await risk_manager.validate_signal(valid_signal)

    assert validation.status == ValidationStatus.REJECTED
    assert validation.approved is False
    assert "Circuit breaker is TRIPPED" in validation.rejection_reasons[0]


# ============================================================================
# Position Count Check Tests
# ============================================================================


@pytest.mark.asyncio
async def test_validate_signal_position_count_ok(
    risk_manager, valid_signal, mock_position_tracker
):
    """Test validation with acceptable position count"""
    # 5 open positions (under limit of 6)
    mock_positions = [MagicMock(size_pct=Decimal("0.10")) for _ in range(5)]
    mock_position_tracker.get_open_positions.return_value = mock_positions

    validation = await risk_manager.validate_signal(valid_signal)

    position_check = next(
        (c for c in validation.checks if c.check_name == "Position Count"), None
    )
    assert position_check.passed is True


@pytest.mark.asyncio
async def test_validate_signal_position_count_exceeded(
    risk_manager, valid_signal, mock_position_tracker
):
    """Test validation rejects when max positions reached"""
    # 6 open positions (at limit)
    mock_positions = [MagicMock(size_pct=Decimal("0.10")) for _ in range(6)]
    mock_position_tracker.get_open_positions.return_value = mock_positions

    validation = await risk_manager.validate_signal(valid_signal)

    assert validation.approved is False
    assert any(
        "Maximum concurrent positions" in r for r in validation.rejection_reasons
    )


# ============================================================================
# Confidence Check Tests
# ============================================================================


@pytest.mark.asyncio
async def test_validate_signal_confidence_sufficient(risk_manager, valid_signal):
    """Test validation with sufficient confidence"""
    valid_signal.confidence = Decimal("0.75")  # 75% > 60% minimum

    validation = await risk_manager.validate_signal(valid_signal)

    conf_check = next(
        (c for c in validation.checks if c.check_name == "Confidence"), None
    )
    assert conf_check.passed is True


@pytest.mark.asyncio
async def test_validate_signal_confidence_insufficient(risk_manager, valid_signal):
    """Test validation rejects low confidence"""
    valid_signal.confidence = Decimal("0.50")  # 50% < 60% minimum

    validation = await risk_manager.validate_signal(valid_signal)

    assert validation.approved is False
    assert any("confidence" in r.lower() for r in validation.rejection_reasons)


@pytest.mark.asyncio
async def test_validate_signal_confidence_at_minimum(risk_manager, valid_signal):
    """Test validation at exact minimum confidence"""
    valid_signal.confidence = Decimal("0.60")  # Exactly at 60%

    validation = await risk_manager.validate_signal(valid_signal)

    conf_check = next(
        (c for c in validation.checks if c.check_name == "Confidence"), None
    )
    assert conf_check.passed is True


# ============================================================================
# Position Size Check Tests
# ============================================================================


@pytest.mark.asyncio
async def test_validate_signal_position_size_ok(risk_manager, valid_signal):
    """Test validation with acceptable position size"""
    valid_signal.size_pct = Decimal("0.15")  # 15% < 20% limit

    validation = await risk_manager.validate_signal(valid_signal)

    size_check = next(
        (c for c in validation.checks if c.check_name == "Position Size"), None
    )
    assert size_check.passed is True


@pytest.mark.asyncio
async def test_validate_signal_position_size_exceeds(risk_manager, valid_signal):
    """Test validation rejects oversized position"""
    valid_signal.size_pct = Decimal("0.25")  # 25% > 20% limit

    validation = await risk_manager.validate_signal(valid_signal)

    assert validation.approved is False
    assert any("Position size" in r for r in validation.rejection_reasons)


@pytest.mark.asyncio
async def test_validate_signal_position_size_at_limit(risk_manager, valid_signal):
    """Test validation at exact position size limit"""
    valid_signal.size_pct = Decimal("0.20")  # Exactly 20%

    validation = await risk_manager.validate_signal(valid_signal)

    size_check = next(
        (c for c in validation.checks if c.check_name == "Position Size"), None
    )
    assert size_check.passed is True


# ============================================================================
# Total Exposure Check Tests
# ============================================================================


@pytest.mark.asyncio
async def test_validate_signal_total_exposure_ok(
    risk_manager, valid_signal, mock_position_tracker
):
    """Test validation with acceptable total exposure"""
    # Existing positions with 50% exposure
    mock_positions = [MagicMock(size_pct=Decimal("0.25")) for _ in range(2)]
    mock_position_tracker.get_open_positions.return_value = mock_positions

    # New signal adds 15%, total = 65% < 80% limit
    valid_signal.size_pct = Decimal("0.15")

    validation = await risk_manager.validate_signal(valid_signal)

    exposure_check = next(
        (c for c in validation.checks if c.check_name == "Total Exposure"), None
    )
    assert exposure_check.passed is True


@pytest.mark.asyncio
async def test_validate_signal_total_exposure_exceeds(
    risk_manager, valid_signal, mock_position_tracker
):
    """Test validation rejects when total exposure would exceed limit"""
    # Existing positions with 70% exposure
    mock_positions = [MagicMock(size_pct=Decimal("0.35")) for _ in range(2)]
    mock_position_tracker.get_open_positions.return_value = mock_positions

    # New signal adds 15%, total = 85% > 80% limit
    valid_signal.size_pct = Decimal("0.15")

    validation = await risk_manager.validate_signal(valid_signal)

    assert validation.approved is False
    assert any("Total exposure" in r for r in validation.rejection_reasons)


# ============================================================================
# Leverage Check Tests
# ============================================================================


@pytest.mark.asyncio
async def test_validate_signal_leverage_within_range(risk_manager, valid_signal):
    """Test validation with leverage in acceptable range"""
    valid_signal.leverage = 20
    valid_signal.symbol = "BTC/USDT:USDT"

    validation = await risk_manager.validate_signal(valid_signal)

    leverage_check = next(
        (c for c in validation.checks if c.check_name == "Leverage"), None
    )
    assert leverage_check.passed is True


@pytest.mark.asyncio
async def test_validate_signal_leverage_too_low(risk_manager, valid_signal):
    """Test validation rejects leverage below minimum"""
    valid_signal.leverage = 3  # < 5 minimum

    validation = await risk_manager.validate_signal(valid_signal)

    assert validation.approved is False
    assert any("Leverage" in r for r in validation.rejection_reasons)


@pytest.mark.asyncio
async def test_validate_signal_leverage_too_high(risk_manager, valid_signal):
    """Test validation rejects excessive leverage"""
    valid_signal.leverage = 50  # > 40 maximum for BTC
    valid_signal.symbol = "BTC/USDT:USDT"

    validation = await risk_manager.validate_signal(valid_signal)

    assert validation.approved is False


@pytest.mark.asyncio
async def test_validate_signal_leverage_symbol_specific(risk_manager, valid_signal):
    """Test leverage limits are symbol-specific"""
    # SOL has max 25x leverage
    valid_signal.symbol = "SOL/USDT:USDT"
    valid_signal.leverage = 30  # > 25 limit for SOL

    validation = await risk_manager.validate_signal(valid_signal)

    assert validation.approved is False


@pytest.mark.asyncio
async def test_validate_signal_no_leverage(risk_manager, valid_signal):
    """Test validation when leverage not specified"""
    valid_signal.leverage = None

    validation = await risk_manager.validate_signal(valid_signal)

    # Should not have leverage check
    leverage_checks = [c for c in validation.checks if c.check_name == "Leverage"]
    assert len(leverage_checks) == 0


# ============================================================================
# Stop-Loss Check Tests
# ============================================================================


@pytest.mark.asyncio
async def test_validate_signal_stop_loss_valid(risk_manager, valid_signal):
    """Test validation with valid stop-loss"""
    valid_signal.stop_loss_pct = Decimal("0.03")  # 3% (within 1-10% range)

    validation = await risk_manager.validate_signal(valid_signal)

    sl_check = next((c for c in validation.checks if c.check_name == "Stop-Loss"), None)
    assert sl_check.passed is True


@pytest.mark.asyncio
async def test_validate_signal_stop_loss_too_tight(risk_manager, valid_signal):
    """Test validation rejects stop-loss below minimum"""
    valid_signal.stop_loss_pct = Decimal("0.005")  # 0.5% < 1% minimum

    validation = await risk_manager.validate_signal(valid_signal)

    assert validation.approved is False
    assert any("Stop-loss" in r for r in validation.rejection_reasons)


@pytest.mark.asyncio
async def test_validate_signal_stop_loss_too_wide(risk_manager, valid_signal):
    """Test validation rejects stop-loss above maximum"""
    valid_signal.stop_loss_pct = Decimal("0.15")  # 15% > 10% maximum

    validation = await risk_manager.validate_signal(valid_signal)

    assert validation.approved is False


@pytest.mark.asyncio
async def test_validate_signal_no_stop_loss(risk_manager, valid_signal):
    """Test validation with missing stop-loss (warning only)"""
    valid_signal.stop_loss_pct = None

    validation = await risk_manager.validate_signal(valid_signal)

    # Should still be approved with warning
    assert validation.approved is True
    assert "No stop-loss specified" in validation.warnings


# ============================================================================
# Multi-Layer Protection Tests
# ============================================================================


@pytest.mark.asyncio
async def test_start_multi_layer_protection(risk_manager, mock_position):
    """Test starting multi-layer protection"""
    with patch.object(
        risk_manager.stop_loss_manager, "start_protection"
    ) as mock_start_protection:
        mock_protection = Protection(
            position_id="pos_123",
            symbol="BTC/USDT:USDT",
            entry_price=Decimal("50000.00"),
            stop_loss_price=Decimal("48500.00"),
            stop_loss_pct=Decimal("0.03"),
        )
        mock_start_protection.return_value = mock_protection

        protection = await risk_manager.start_multi_layer_protection(mock_position)

        assert protection.position_id == "pos_123"
        mock_start_protection.assert_called_once()


# ============================================================================
# Daily Loss Limit Tests
# ============================================================================


@pytest.mark.asyncio
async def test_check_daily_loss_limit(risk_manager):
    """Test checking daily loss limit"""
    status = await risk_manager.check_daily_loss_limit()

    assert isinstance(status, CircuitBreakerStatus)
    assert status.state == CircuitBreakerState.ACTIVE


# ============================================================================
# Emergency Closure Tests
# ============================================================================


@pytest.mark.asyncio
async def test_emergency_close_position(risk_manager, mock_trade_executor):
    """Test emergency position closure"""
    mock_trade_executor.close_position.return_value = MagicMock()

    await risk_manager.emergency_close_position(
        position_id="pos_123",
        reason="extreme_loss",
    )

    mock_trade_executor.close_position.assert_called_once_with(
        position_id="pos_123",
        reason="emergency: extreme_loss",
        force=True,
    )


@pytest.mark.asyncio
async def test_emergency_close_no_executor(risk_manager):
    """Test emergency closure without executor raises error"""
    risk_manager.trade_executor = None

    with pytest.raises(ValueError, match="No trade executor available"):
        await risk_manager.emergency_close_position("pos_123", "test")


# ============================================================================
# Status Query Tests
# ============================================================================


def test_get_circuit_breaker_status(risk_manager):
    """Test getting circuit breaker status"""
    status = risk_manager.get_circuit_breaker_status()

    assert isinstance(status, CircuitBreakerStatus)
    assert status.state == CircuitBreakerState.ACTIVE


def test_get_protection_status(risk_manager):
    """Test getting protection status"""
    status = risk_manager.get_protection_status("pos_123")

    # Should return None if no protection exists
    assert status is None


@pytest.mark.asyncio
async def test_stop_protection(risk_manager):
    """Test stopping protection"""
    with patch.object(risk_manager.stop_loss_manager, "stop_protection") as mock_stop:
        await risk_manager.stop_protection("pos_123")
        mock_stop.assert_called_once_with("pos_123")


# ============================================================================
# Private Helper Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_open_positions_with_tracker(risk_manager, mock_position_tracker):
    """Test getting open positions when tracker available"""
    mock_positions = [MagicMock(), MagicMock()]
    mock_position_tracker.get_open_positions.return_value = mock_positions

    positions = await risk_manager._get_open_positions()

    assert len(positions) == 2


@pytest.mark.asyncio
async def test_get_open_positions_no_tracker(risk_manager):
    """Test getting open positions without tracker"""
    risk_manager.position_tracker = None

    positions = await risk_manager._get_open_positions()

    assert positions == []


@pytest.mark.asyncio
async def test_calculate_total_exposure(risk_manager, mock_position_tracker):
    """Test calculating total exposure"""
    mock_positions = [
        MagicMock(size_pct=Decimal("0.20")),
        MagicMock(size_pct=Decimal("0.30")),
    ]
    mock_position_tracker.get_open_positions.return_value = mock_positions

    total_exposure = await risk_manager._calculate_total_exposure()

    assert total_exposure == Decimal("0.50")


@pytest.mark.asyncio
async def test_calculate_total_exposure_no_positions(
    risk_manager, mock_position_tracker
):
    """Test total exposure with no positions"""
    mock_position_tracker.get_open_positions.return_value = []

    total_exposure = await risk_manager._calculate_total_exposure()

    assert total_exposure == Decimal("0")


@pytest.mark.asyncio
async def test_get_daily_pnl(risk_manager):
    """Test getting daily P&L"""
    # Set daily P&L
    risk_manager.circuit_breaker.status.daily_pnl_chf = Decimal("-50.00")

    daily_pnl = await risk_manager._get_daily_pnl()

    assert daily_pnl == Decimal("-50.00")


# ============================================================================
# Risk Constants Tests
# ============================================================================


def test_risk_limits_constants():
    """Test risk limit constants are set correctly"""
    assert RiskManager.MAX_CONCURRENT_POSITIONS == 6
    assert RiskManager.MAX_POSITION_SIZE_PCT == Decimal("0.20")
    assert RiskManager.MAX_TOTAL_EXPOSURE_PCT == Decimal("0.80")
    assert RiskManager.MIN_LEVERAGE == 5
    assert RiskManager.MAX_LEVERAGE == 40
    assert RiskManager.MIN_CONFIDENCE == Decimal("0.60")


def test_per_symbol_leverage_limits():
    """Test per-symbol leverage limits are defined"""
    assert RiskManager.PER_SYMBOL_LEVERAGE["BTC/USDT:USDT"] == 40
    assert RiskManager.PER_SYMBOL_LEVERAGE["ETH/USDT:USDT"] == 40
    assert RiskManager.PER_SYMBOL_LEVERAGE["SOL/USDT:USDT"] == 25
    assert RiskManager.PER_SYMBOL_LEVERAGE["ADA/USDT:USDT"] == 20


# ============================================================================
# Validation Status Tests
# ============================================================================


@pytest.mark.asyncio
async def test_validation_with_warnings(risk_manager, valid_signal):
    """Test validation can have warnings while still approved"""
    valid_signal.stop_loss_pct = None  # Triggers warning

    validation = await risk_manager.validate_signal(valid_signal)

    assert validation.status == ValidationStatus.WARNING
    assert validation.approved is True
    assert len(validation.warnings) > 0


@pytest.mark.asyncio
async def test_validation_rejection_overrides_warning(risk_manager, valid_signal):
    """Test rejection status overrides warning status"""
    valid_signal.confidence = Decimal("0.50")  # Rejection
    valid_signal.stop_loss_pct = None  # Warning

    validation = await risk_manager.validate_signal(valid_signal)

    assert validation.status == ValidationStatus.REJECTED
    assert validation.approved is False


# ============================================================================
# Integration Test
# ============================================================================


@pytest.mark.asyncio
async def test_full_validation_workflow(risk_manager, valid_signal, mock_position):
    """Test full validation and protection workflow"""
    # 1. Validate signal
    validation = await risk_manager.validate_signal(valid_signal)
    assert validation.approved is True

    # 2. Start protection (if signal approved)
    with patch.object(
        risk_manager.stop_loss_manager, "start_protection"
    ) as mock_start_protection:
        mock_protection = Protection(
            position_id="pos_123",
            symbol="BTC/USDT:USDT",
            entry_price=Decimal("50000.00"),
            stop_loss_price=Decimal("48500.00"),
            stop_loss_pct=Decimal("0.03"),
        )
        mock_start_protection.return_value = mock_protection

        protection = await risk_manager.start_multi_layer_protection(mock_position)
        assert protection.position_id == "pos_123"

    # 3. Check daily loss limit
    status = await risk_manager.check_daily_loss_limit()
    assert status.state == CircuitBreakerState.ACTIVE


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=workspace/features/risk_manager/risk_manager"])
