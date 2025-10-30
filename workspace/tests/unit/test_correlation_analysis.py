"""
Unit Tests for Correlation Analyzer

Tests portfolio correlation analysis including:
- Correlation matrix calculation
- Highly correlated pair detection
- Diversification score calculation
- Risk assessment

Author: Testing Team
Date: 2025-10-29
Sprint: 3, Stream B
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from workspace.features.risk_manager import (CorrelationAnalyzer,
                                             CorrelationMatrix,
                                             CorrelationPair)


@pytest.fixture
def mock_market_data_service():
    """Mock market data service"""
    service = AsyncMock()

    # Mock OHLCV data for different symbols
    def create_ohlcv(base_price, days=30):
        ohlcv = []
        for i in range(days):
            timestamp = (datetime.utcnow().timestamp() - (days - i) * 86400) * 1000
            # [timestamp, open, high, low, close, volume]
            price = base_price + (i % 10)  # Simple price movement
            ohlcv.append([timestamp, price, price + 10, price - 10, price, 1000])
        return ohlcv

    service.get_ohlcv = AsyncMock(
        side_effect=lambda symbol, **kwargs: (
            create_ohlcv(50000)
            if "BTC" in symbol
            else create_ohlcv(3000) if "ETH" in symbol else create_ohlcv(100)
        )
    )

    return service


@pytest.fixture
def analyzer(mock_market_data_service):
    """Correlation analyzer with mock service"""
    return CorrelationAnalyzer(
        market_data_service=mock_market_data_service,
        max_correlation_threshold=0.7,
        lookback_days=30,
    )


# ============================================================================
# Returns Calculation Tests
# ============================================================================


def test_calculate_returns(analyzer):
    """Test returns calculation from prices"""
    prices = [
        Decimal("100"),
        Decimal("105"),  # +5%
        Decimal("110"),  # +4.76%
        Decimal("105"),  # -4.55%
    ]

    returns = analyzer.calculate_returns(prices)

    assert len(returns) == 3
    assert abs(returns[0] - 0.05) < 0.001  # ~5%
    assert returns[2] < 0  # Negative return


def test_calculate_returns_empty(analyzer):
    """Test returns with insufficient data"""
    returns = analyzer.calculate_returns([Decimal("100")])

    assert len(returns) == 0


def test_calculate_returns_with_zero(analyzer):
    """Test returns handling zero prices"""
    prices = [Decimal("100"), Decimal("0"), Decimal("105")]

    returns = analyzer.calculate_returns(prices)

    # Should skip zero price
    assert len(returns) == 1


# ============================================================================
# Correlation Calculation Tests
# ============================================================================


def test_calculate_correlation_perfect_positive(analyzer):
    """Test perfect positive correlation"""
    returns1 = [0.01, 0.02, -0.01, 0.03]
    returns2 = [0.01, 0.02, -0.01, 0.03]  # Identical

    corr = analyzer.calculate_correlation(returns1, returns2)

    assert abs(corr - 1.0) < 0.01


def test_calculate_correlation_perfect_negative(analyzer):
    """Test perfect negative correlation"""
    returns1 = [0.01, 0.02, -0.01, 0.03]
    returns2 = [-0.01, -0.02, 0.01, -0.03]  # Opposite

    corr = analyzer.calculate_correlation(returns1, returns2)

    assert abs(corr - (-1.0)) < 0.01


def test_calculate_correlation_no_correlation(analyzer):
    """Test near-zero correlation"""
    returns1 = [0.01, -0.01, 0.01, -0.01]
    returns2 = [-0.01, -0.01, 0.01, 0.01]

    corr = analyzer.calculate_correlation(returns1, returns2)

    # Should be close to zero (not exactly zero due to small sample)
    assert abs(corr) < 0.5


def test_calculate_correlation_insufficient_data(analyzer):
    """Test correlation with insufficient data"""
    corr = analyzer.calculate_correlation([0.01], [0.02])

    assert corr == 0.0


# ============================================================================
# Portfolio Correlation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_calculate_portfolio_correlation(analyzer):
    """Test full portfolio correlation matrix calculation"""
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

    matrix = await analyzer.calculate_portfolio_correlation(symbols, days=30)

    assert isinstance(matrix, CorrelationMatrix)
    assert set(matrix.symbols) == set(symbols)
    assert len(matrix.matrix) == 3

    # Check diagonal is 1.0 (self-correlation)
    for symbol in symbols:
        assert matrix.matrix[symbol][symbol] == 1.0


@pytest.mark.asyncio
async def test_calculate_correlation_single_symbol(analyzer):
    """Test correlation with single symbol"""
    matrix = await analyzer.calculate_portfolio_correlation(["BTCUSDT"])

    assert matrix.diversification_score == 1.0
    assert len(matrix.highly_correlated_pairs) == 0


# ============================================================================
# Correlation Limits Tests
# ============================================================================


def test_check_correlation_limits_none_exceeded(analyzer):
    """Test correlation limits with no violations"""
    matrix = {
        "BTC": {"BTC": 1.0, "ETH": 0.5, "SOL": 0.3},
        "ETH": {"BTC": 0.5, "ETH": 1.0, "SOL": 0.4},
        "SOL": {"BTC": 0.3, "ETH": 0.4, "SOL": 1.0},
    }

    pairs = analyzer.check_correlation_limits(matrix, max_correlation=0.7)

    assert len(pairs) == 0


def test_check_correlation_limits_exceeded(analyzer):
    """Test correlation limits with violations"""
    matrix = {
        "BTC": {"BTC": 1.0, "ETH": 0.85},  # High correlation
        "ETH": {"BTC": 0.85, "ETH": 1.0},
    }

    pairs = analyzer.check_correlation_limits(matrix, max_correlation=0.7)

    assert len(pairs) == 1
    assert pairs[0].correlation == 0.85
    assert pairs[0].strength == "VERY_STRONG"


def test_classify_correlation_strength(analyzer):
    """Test correlation strength classification"""
    assert analyzer.classify_correlation_strength(0.2) == "WEAK"
    assert analyzer.classify_correlation_strength(0.4) == "MODERATE"
    assert analyzer.classify_correlation_strength(0.6) == "STRONG"
    assert analyzer.classify_correlation_strength(0.8) == "VERY_STRONG"


# ============================================================================
# Diversification Score Tests
# ============================================================================


def test_calculate_diversification_perfect(analyzer):
    """Test diversification with zero correlation"""
    matrix = {
        "SYM1": {"SYM1": 1.0, "SYM2": 0.0, "SYM3": 0.0},
        "SYM2": {"SYM1": 0.0, "SYM2": 1.0, "SYM3": 0.0},
        "SYM3": {"SYM1": 0.0, "SYM2": 0.0, "SYM3": 1.0},
    }

    score = analyzer.calculate_diversification_score(matrix)

    assert score == 1.0  # Perfect diversification


def test_calculate_diversification_poor(analyzer):
    """Test diversification with high correlation"""
    matrix = {
        "SYM1": {"SYM1": 1.0, "SYM2": 0.9, "SYM3": 0.85},
        "SYM2": {"SYM1": 0.9, "SYM2": 1.0, "SYM3": 0.88},
        "SYM3": {"SYM1": 0.85, "SYM2": 0.88, "SYM3": 1.0},
    }

    score = analyzer.calculate_diversification_score(matrix)

    # High correlation = low diversification
    assert score < 0.2


def test_calculate_diversification_empty(analyzer):
    """Test diversification with empty matrix"""
    score = analyzer.calculate_diversification_score({})

    assert score == 1.0


# ============================================================================
# Risk Assessment Tests
# ============================================================================


def test_assess_correlation_risk_low(analyzer):
    """Test risk assessment with good diversification"""
    matrix = CorrelationMatrix(
        symbols=["BTC", "ETH", "SOL"],
        matrix={
            "BTC": {"BTC": 1.0, "ETH": 0.3, "SOL": 0.2},
            "ETH": {"BTC": 0.3, "ETH": 1.0, "SOL": 0.25},
            "SOL": {"BTC": 0.2, "ETH": 0.25, "SOL": 1.0},
        },
        highly_correlated_pairs=[],
        diversification_score=0.75,
        timestamp=datetime.utcnow(),
    )

    risk_level, warnings = analyzer.assess_correlation_risk(matrix)

    assert risk_level == "LOW"
    assert len(warnings) == 0


def test_assess_correlation_risk_high(analyzer):
    """Test risk assessment with poor diversification"""
    # Create highly correlated pair
    pair = CorrelationPair(
        symbol1="BTC",
        symbol2="ETH",
        correlation=0.9,
        strength="VERY_STRONG",
    )

    matrix = CorrelationMatrix(
        symbols=["BTC", "ETH"],
        matrix={
            "BTC": {"BTC": 1.0, "ETH": 0.9},
            "ETH": {"BTC": 0.9, "ETH": 1.0},
        },
        highly_correlated_pairs=[pair],
        diversification_score=0.1,
        timestamp=datetime.utcnow(),
    )

    risk_level, warnings = analyzer.assess_correlation_risk(matrix)

    assert risk_level in ["HIGH", "MEDIUM"]
    assert len(warnings) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
