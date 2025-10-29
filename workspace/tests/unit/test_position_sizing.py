"""
Unit Tests for Kelly Position Sizer

Tests Kelly Criterion position sizing including:
- Kelly percentage calculation
- Fractional Kelly application
- Confidence adjustments
- Trade history analysis
- Position size recommendations

Author: Testing Team
Date: 2025-10-29
Sprint: 3, Stream B
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta

from workspace.features.risk_manager import (
    KellyPositionSizer,
    TradeResult,
    PositionSizingResult,
)


@pytest.fixture
def kelly_sizer():
    """Kelly position sizer with default settings"""
    return KellyPositionSizer(
        max_kelly_fraction=0.25,
        min_sample_size=20,
    )


@pytest.fixture
def sample_trades():
    """Sample trade history for testing"""
    trades = []
    base_time = datetime.utcnow()

    # 6 winning trades
    for i in range(6):
        trades.append(
            TradeResult(
                symbol="BTCUSDT",
                entry_price=Decimal("50000.00"),
                exit_price=Decimal("51000.00"),
                quantity=Decimal("0.01"),
                pnl=Decimal("10.00"),
                is_win=True,
                timestamp=base_time - timedelta(days=30 - i),
            )
        )

    # 4 losing trades
    for i in range(4):
        trades.append(
            TradeResult(
                symbol="ETHUSDT",
                entry_price=Decimal("3000.00"),
                exit_price=Decimal("2950.00"),
                quantity=Decimal("0.1"),
                pnl=Decimal("-5.00"),
                is_win=False,
                timestamp=base_time - timedelta(days=20 - i),
            )
        )

    return trades


# ============================================================================
# Kelly Calculation Tests
# ============================================================================


def test_calculate_kelly_basic(kelly_sizer):
    """Test basic Kelly calculation"""
    # Win rate: 60%, Avg win: 100, Avg loss: 80
    # Kelly = 0.6 - (0.4 / 1.25) = 0.6 - 0.32 = 0.28
    kelly_pct = kelly_sizer.calculate_kelly_percentage(
        win_rate=0.6,
        avg_win=Decimal("100.00"),
        avg_loss=Decimal("80.00"),
    )

    assert abs(kelly_pct - 0.28) < 0.01


def test_calculate_kelly_high_win_rate(kelly_sizer):
    """Test Kelly with high win rate"""
    # Win rate: 80%, Avg win: 50, Avg loss: 50
    # Kelly = 0.8 - (0.2 / 1.0) = 0.6
    kelly_pct = kelly_sizer.calculate_kelly_percentage(
        win_rate=0.8,
        avg_win=Decimal("50.00"),
        avg_loss=Decimal("50.00"),
    )

    assert abs(kelly_pct - 0.6) < 0.01


def test_calculate_kelly_low_win_rate(kelly_sizer):
    """Test Kelly with low win rate but high win/loss ratio"""
    # Win rate: 40%, Avg win: 200, Avg loss: 50
    # Kelly = 0.4 - (0.6 / 4.0) = 0.4 - 0.15 = 0.25
    kelly_pct = kelly_sizer.calculate_kelly_percentage(
        win_rate=0.4,
        avg_win=Decimal("200.00"),
        avg_loss=Decimal("50.00"),
    )

    assert abs(kelly_pct - 0.25) < 0.01


def test_calculate_kelly_negative_expectancy(kelly_sizer):
    """Test Kelly with negative expectancy returns zero"""
    # Win rate: 30%, Avg win: 50, Avg loss: 100
    # Kelly would be negative, should return 0
    kelly_pct = kelly_sizer.calculate_kelly_percentage(
        win_rate=0.3,
        avg_win=Decimal("50.00"),
        avg_loss=Decimal("100.00"),
    )

    assert kelly_pct == 0.0


def test_calculate_kelly_zero_loss(kelly_sizer):
    """Test Kelly with zero average loss"""
    kelly_pct = kelly_sizer.calculate_kelly_percentage(
        win_rate=0.6,
        avg_win=Decimal("100.00"),
        avg_loss=Decimal("0"),
    )

    assert kelly_pct == 0.0


def test_calculate_kelly_invalid_win_rate(kelly_sizer):
    """Test Kelly with invalid win rate"""
    # Win rate > 1.0
    kelly_pct = kelly_sizer.calculate_kelly_percentage(
        win_rate=1.2,
        avg_win=Decimal("100.00"),
        avg_loss=Decimal("50.00"),
    )

    assert kelly_pct == 0.0


# ============================================================================
# Fractional Kelly Tests
# ============================================================================


def test_apply_fractional_kelly(kelly_sizer):
    """Test fractional Kelly application"""
    full_kelly = 0.4
    fractional = kelly_sizer.apply_fractional_kelly(full_kelly)

    # Should be 25% of full Kelly
    assert abs(fractional - 0.1) < 0.01


def test_apply_custom_fraction(kelly_sizer):
    """Test fractional Kelly with custom fraction"""
    full_kelly = 0.5
    fractional = kelly_sizer.apply_fractional_kelly(full_kelly, fraction=0.5)

    # Should be 50% of full Kelly
    assert abs(fractional - 0.25) < 0.01


# ============================================================================
# Confidence Adjustment Tests
# ============================================================================


def test_confidence_adjustment_large_sample(kelly_sizer):
    """Test confidence adjustment with large sample"""
    confidence = kelly_sizer.calculate_confidence_adjustment(30)

    assert confidence == 1.0  # Full confidence


def test_confidence_adjustment_small_sample(kelly_sizer):
    """Test confidence adjustment with small sample"""
    confidence = kelly_sizer.calculate_confidence_adjustment(5)

    # Sample < 10 returns 0.7
    assert confidence == 0.7  # 70% confidence


def test_confidence_adjustment_medium_sample(kelly_sizer):
    """Test confidence adjustment with medium sample"""
    confidence = kelly_sizer.calculate_confidence_adjustment(15)

    assert 0.7 < confidence < 1.0


# ============================================================================
# Position Size Calculation Tests
# ============================================================================


def test_calculate_position_size(kelly_sizer):
    """Test position size calculation"""
    position_size = kelly_sizer.calculate_position_size(
        win_rate=0.6,
        avg_win=Decimal("100.00"),
        avg_loss=Decimal("80.00"),
        portfolio_value=Decimal("2626.96"),
    )

    # Kelly = 0.28, Fractional (25%) = 0.07
    # Position = 2626.96 * 0.07 = ~183.89
    assert position_size > Decimal("150")
    assert position_size < Decimal("220")


def test_calculate_position_size_with_confidence(kelly_sizer):
    """Test position size with manual confidence adjustment"""
    position_size = kelly_sizer.calculate_position_size(
        win_rate=0.6,
        avg_win=Decimal("100.00"),
        avg_loss=Decimal("80.00"),
        portfolio_value=Decimal("2626.96"),
        confidence_adjustment=0.5,  # 50% confidence
    )

    # Should be half of normal position size
    normal_size = kelly_sizer.calculate_position_size(
        win_rate=0.6,
        avg_win=Decimal("100.00"),
        avg_loss=Decimal("80.00"),
        portfolio_value=Decimal("2626.96"),
    )

    assert abs(position_size - normal_size * Decimal("0.5")) < Decimal("1.0")


# ============================================================================
# Trade History Analysis Tests
# ============================================================================


def test_analyze_trade_history(kelly_sizer, sample_trades):
    """Test trade history analysis"""
    analysis = kelly_sizer.analyze_trade_history(sample_trades)

    # 6 wins, 4 losses = 60% win rate
    assert abs(analysis["win_rate"] - 0.6) < 0.01

    # Average win = 10.00
    assert analysis["avg_win"] == Decimal("10.00")

    # Average loss = 5.00
    assert analysis["avg_loss"] == Decimal("5.00")

    assert analysis["sample_size"] == 10


def test_analyze_empty_history(kelly_sizer):
    """Test analysis with no trades"""
    analysis = kelly_sizer.analyze_trade_history([])

    assert analysis["win_rate"] == 0.0
    assert analysis["avg_win"] == Decimal("0")
    assert analysis["avg_loss"] == Decimal("0")
    assert analysis["sample_size"] == 0


def test_calculate_from_trade_history(kelly_sizer, sample_trades):
    """Test full calculation from trade history"""
    result = kelly_sizer.calculate_from_trade_history(
        trade_history=sample_trades,
        portfolio_value=Decimal("2626.96"),
        lookback_days=None,  # Use all trades
    )

    assert isinstance(result, PositionSizingResult)
    assert result.win_rate == 0.6
    assert result.avg_win == Decimal("10.00")
    assert result.avg_loss == Decimal("5.00")
    assert result.win_loss_ratio == 2.0
    assert result.sample_size == 10
    assert result.recommended_size_chf > Decimal("0")


def test_calculate_from_history_with_lookback(kelly_sizer):
    """Test calculation with lookback period filter"""
    # Create trades spanning 60 days
    trades = []
    base_time = datetime.utcnow()

    for i in range(10):
        trades.append(
            TradeResult(
                symbol="BTCUSDT",
                entry_price=Decimal("50000.00"),
                exit_price=Decimal("51000.00"),
                quantity=Decimal("0.01"),
                pnl=Decimal("10.00"),
                is_win=True,
                timestamp=base_time - timedelta(days=60 - i * 6),
            )
        )

    # Use only last 30 days
    result = kelly_sizer.calculate_from_trade_history(
        trade_history=trades,
        portfolio_value=Decimal("2626.96"),
        lookback_days=30,
    )

    # Should only include ~5 most recent trades
    assert result.sample_size <= 5


# ============================================================================
# Variance Analysis Tests
# ============================================================================


def test_calculate_variance(kelly_sizer, sample_trades):
    """Test variance calculation"""
    variance = kelly_sizer.calculate_variance_of_returns(sample_trades)

    assert variance > Decimal("0")


def test_recommend_kelly_fraction_high_variance(kelly_sizer):
    """Test Kelly fraction recommendation with high variance"""
    # Create high variance trades
    trades = [
        TradeResult(
            symbol="BTCUSDT",
            entry_price=Decimal("50000.00"),
            exit_price=Decimal("55000.00"),
            quantity=Decimal("0.1"),
            pnl=Decimal("500.00"),  # Large win
            is_win=True,
            timestamp=datetime.utcnow(),
        ),
        TradeResult(
            symbol="BTCUSDT",
            entry_price=Decimal("50000.00"),
            exit_price=Decimal("45000.00"),
            quantity=Decimal("0.1"),
            pnl=Decimal("-500.00"),  # Large loss
            is_win=False,
            timestamp=datetime.utcnow(),
        ),
    ]

    fraction = kelly_sizer.recommend_kelly_fraction(trades)

    # High variance should recommend lower fraction
    assert fraction <= 0.2


def test_recommend_kelly_fraction_low_variance(kelly_sizer):
    """Test Kelly fraction recommendation with low variance"""
    # Create low variance trades
    trades = [
        TradeResult(
            symbol="BTCUSDT",
            entry_price=Decimal("50000.00"),
            exit_price=Decimal("50010.00"),
            quantity=Decimal("0.1"),
            pnl=Decimal("1.00"),
            is_win=True,
            timestamp=datetime.utcnow(),
        )
        for _ in range(10)
    ]

    fraction = kelly_sizer.recommend_kelly_fraction(trades)

    # Low variance should recommend higher fraction
    assert fraction >= 0.2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
