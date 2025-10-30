"""
Unit Tests for Risk Metrics Calculator

Tests comprehensive risk and performance metrics including:
- Sharpe and Sortino ratios
- Maximum drawdown
- Value at Risk (VaR) and CVaR
- Calmar ratio
- Win rate and profit factor

Author: Testing Team
Date: 2025-10-29
Sprint: 3, Stream B
"""

import pytest
from decimal import Decimal
from datetime import datetime

from workspace.features.risk_manager import (
    RiskMetricsCalculator,
    RiskMetrics,
)


@pytest.fixture
def calculator():
    """Risk metrics calculator with default settings"""
    return RiskMetricsCalculator(
        risk_free_rate=0.02,
        trading_days_per_year=365,
    )


@pytest.fixture
def sample_returns():
    """Sample return series for testing"""
    # Mix of positive and negative returns
    return [0.01, -0.005, 0.02, -0.01, 0.015, 0.03, -0.008, 0.012, -0.015, 0.025]


@pytest.fixture
def sample_equity_curve():
    """Sample equity curve for testing"""
    return [
        Decimal("1000"),
        Decimal("1010"),  # +10
        Decimal("1005"),  # -5
        Decimal("1025"),  # +20
        Decimal("1015"),  # -10
        Decimal("1030"),  # +15
        Decimal("1060"),  # +30
        Decimal("1052"),  # -8
        Decimal("1064"),  # +12
        Decimal("1049"),  # -15
        Decimal("1074"),  # +25
    ]


# ============================================================================
# Sharpe Ratio Tests
# ============================================================================


def test_calculate_sharpe_ratio(calculator, sample_returns):
    """Test Sharpe ratio calculation"""
    sharpe = calculator.calculate_sharpe_ratio(sample_returns)

    # Should be positive for profitable strategy
    assert sharpe > 0.0


def test_calculate_sharpe_negative_returns(calculator):
    """Test Sharpe ratio with losing strategy"""
    returns = [-0.01, -0.02, -0.015, -0.008]

    sharpe = calculator.calculate_sharpe_ratio(returns)

    # Should be negative for losing strategy
    assert sharpe < 0.0


def test_calculate_sharpe_insufficient_data(calculator):
    """Test Sharpe ratio with insufficient data"""
    sharpe = calculator.calculate_sharpe_ratio([0.01])

    assert sharpe == 0.0


def test_calculate_sharpe_zero_volatility(calculator):
    """Test Sharpe ratio with zero volatility"""
    returns = [0.0, 0.0, 0.0]

    sharpe = calculator.calculate_sharpe_ratio(returns)

    assert sharpe == 0.0


# ============================================================================
# Sortino Ratio Tests
# ============================================================================


def test_calculate_sortino_ratio(calculator, sample_returns):
    """Test Sortino ratio calculation"""
    sortino = calculator.calculate_sortino_ratio(sample_returns)

    # Should be positive and typically higher than Sharpe
    # (only penalizes downside volatility)
    assert sortino > 0.0


def test_calculate_sortino_no_losses(calculator):
    """Test Sortino ratio with no losing trades"""
    returns = [0.01, 0.02, 0.015, 0.03]

    sortino = calculator.calculate_sortino_ratio(returns)

    # Should be capped at 10.0 for no downside
    assert sortino == 10.0


# ============================================================================
# Maximum Drawdown Tests
# ============================================================================


def test_calculate_max_drawdown(calculator, sample_equity_curve):
    """Test maximum drawdown calculation"""
    max_dd, max_dd_pct = calculator.calculate_max_drawdown(sample_equity_curve)

    # Should have some drawdown
    assert max_dd > Decimal("0")
    assert max_dd_pct > 0.0


def test_calculate_max_drawdown_always_increasing(calculator):
    """Test max drawdown with no decline"""
    equity_curve = [
        Decimal("1000"),
        Decimal("1100"),
        Decimal("1200"),
        Decimal("1300"),
    ]

    max_dd, max_dd_pct = calculator.calculate_max_drawdown(equity_curve)

    assert max_dd == Decimal("0")
    assert max_dd_pct == 0.0


def test_calculate_max_drawdown_large_decline(calculator):
    """Test max drawdown with significant decline"""
    equity_curve = [
        Decimal("1000"),
        Decimal("1200"),  # Peak
        Decimal("900"),  # 25% drawdown
        Decimal("1100"),
    ]

    max_dd, max_dd_pct = calculator.calculate_max_drawdown(equity_curve)

    assert max_dd == Decimal("300")  # 1200 - 900
    assert abs(max_dd_pct - 0.25) < 0.01  # 25%


# ============================================================================
# Calmar Ratio Tests
# ============================================================================


def test_calculate_calmar_ratio(calculator):
    """Test Calmar ratio calculation"""
    calmar = calculator.calculate_calmar_ratio(
        annualized_return=0.25,  # 25% return
        max_drawdown_pct=0.10,  # 10% max drawdown
    )

    # Calmar = 0.25 / 0.10 = 2.5
    assert abs(calmar - 2.5) < 0.01


def test_calculate_calmar_ratio_zero_drawdown(calculator):
    """Test Calmar ratio with zero drawdown"""
    calmar = calculator.calculate_calmar_ratio(
        annualized_return=0.20,
        max_drawdown_pct=0.0,
    )

    # Should be capped at 10.0
    assert calmar == 10.0


def test_calculate_calmar_ratio_negative_return(calculator):
    """Test Calmar ratio with negative return"""
    calmar = calculator.calculate_calmar_ratio(
        annualized_return=-0.10,
        max_drawdown_pct=0.15,
    )

    # Should be negative
    assert calmar < 0.0


# ============================================================================
# VaR and CVaR Tests
# ============================================================================


def test_calculate_var(calculator, sample_returns):
    """Test VaR calculation"""
    var_95 = calculator.calculate_var(sample_returns, confidence=0.95)

    # VaR should be negative (loss)
    assert var_95 < 0.0


def test_calculate_var_99(calculator, sample_returns):
    """Test VaR at 99% confidence"""
    var_95 = calculator.calculate_var(sample_returns, confidence=0.95)
    var_99 = calculator.calculate_var(sample_returns, confidence=0.99)

    # VaR(99%) should be more extreme than VaR(95%)
    assert abs(var_99) >= abs(var_95)


def test_calculate_cvar(calculator, sample_returns):
    """Test CVaR calculation"""
    var_95 = calculator.calculate_var(sample_returns, confidence=0.95)
    cvar_95 = calculator.calculate_cvar(sample_returns, confidence=0.95)

    # CVaR should be more extreme than VaR (tail risk)
    assert abs(cvar_95) >= abs(var_95)


# ============================================================================
# Performance Metrics Tests
# ============================================================================


def test_calculate_win_rate(calculator):
    """Test win rate calculation"""
    win_rate = calculator.calculate_win_rate(
        winning_trades=7,
        total_trades=10,
    )

    assert win_rate == 0.7


def test_calculate_win_rate_zero_trades(calculator):
    """Test win rate with no trades"""
    win_rate = calculator.calculate_win_rate(0, 0)

    assert win_rate == 0.0


def test_calculate_profit_factor(calculator):
    """Test profit factor calculation"""
    profit_factor = calculator.calculate_profit_factor(
        total_wins=Decimal("500.00"),
        total_losses=Decimal("300.00"),
    )

    # 500 / 300 = 1.67
    assert abs(profit_factor - 1.67) < 0.01


def test_calculate_profit_factor_zero_losses(calculator):
    """Test profit factor with no losses"""
    profit_factor = calculator.calculate_profit_factor(
        total_wins=Decimal("500.00"),
        total_losses=Decimal("0"),
    )

    # Should be capped at 10.0
    assert profit_factor == 10.0


def test_calculate_win_loss_ratio(calculator):
    """Test win/loss ratio calculation"""
    ratio = calculator.calculate_win_loss_ratio(
        avg_win=Decimal("100.00"),
        avg_loss=Decimal("50.00"),
    )

    # 100 / 50 = 2.0
    assert ratio == 2.0


# ============================================================================
# Volatility Tests
# ============================================================================


def test_calculate_volatility(calculator, sample_returns):
    """Test volatility calculation"""
    vol = calculator.calculate_volatility(sample_returns)

    # Should be positive
    assert vol > 0.0


def test_calculate_downside_deviation(calculator, sample_returns):
    """Test downside deviation calculation"""
    downside_dev = calculator.calculate_downside_deviation(sample_returns)

    # Should be positive and typically less than overall volatility
    assert downside_dev > 0.0

    vol = calculator.calculate_volatility(sample_returns)
    assert downside_dev <= vol


# ============================================================================
# All Metrics Calculation Tests
# ============================================================================


def test_calculate_all_metrics(calculator, sample_returns, sample_equity_curve):
    """Test comprehensive metrics calculation"""
    metrics = calculator.calculate_all_metrics(
        returns=sample_returns,
        equity_curve=sample_equity_curve,
        initial_balance=Decimal("1000"),
    )

    assert isinstance(metrics, RiskMetrics)

    # Check all metrics are calculated
    assert metrics.total_return > Decimal("0")
    assert metrics.sharpe_ratio != 0.0
    assert metrics.sortino_ratio != 0.0
    assert metrics.max_drawdown >= Decimal("0")
    assert metrics.win_rate > 0.0
    assert metrics.profit_factor > 0.0
    assert isinstance(metrics.calculation_timestamp, datetime)


def test_calculate_all_metrics_with_trade_stats(
    calculator, sample_returns, sample_equity_curve
):
    """Test metrics calculation with provided trade stats"""
    metrics = calculator.calculate_all_metrics(
        returns=sample_returns,
        equity_curve=sample_equity_curve,
        initial_balance=Decimal("1000"),
        winning_trades=7,
        losing_trades=3,
        total_wins=Decimal("350.00"),
        total_losses=Decimal("150.00"),
        largest_win=Decimal("100.00"),
        largest_loss=Decimal("-80.00"),
    )

    assert metrics.winning_trades == 7
    assert metrics.losing_trades == 3
    assert metrics.total_trades == 10
    assert metrics.win_rate == 0.7
    assert metrics.largest_win == Decimal("100.00")
    assert metrics.largest_loss == Decimal("-80.00")


def test_calculate_all_metrics_empty_data(calculator):
    """Test metrics calculation with minimal data"""
    metrics = calculator.calculate_all_metrics(
        returns=[],
        equity_curve=[Decimal("1000")],
        initial_balance=Decimal("1000"),
    )

    # Should handle gracefully
    assert metrics.sharpe_ratio == 0.0
    assert metrics.total_trades == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
