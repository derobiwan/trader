"""Unit Tests for Correlation Analyzer"""

import pytest
from decimal import Decimal

from workspace.features.risk_manager.correlation_analysis import (
    CorrelationAnalyzer,
    CorrelationMatrix,
)


class TestCorrelationAnalyzer:
    """Test suite for CorrelationAnalyzer"""

    def setup_method(self):
        """Set up test fixtures"""
        self.analyzer = CorrelationAnalyzer()

    @pytest.mark.asyncio
    async def test_calculate_portfolio_correlation(self):
        """Test correlation matrix calculation"""
        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

        correlation_matrix = await self.analyzer.calculate_portfolio_correlation(
            symbols=symbols,
            days=30,
        )

        assert isinstance(correlation_matrix, CorrelationMatrix)
        assert len(correlation_matrix.symbols) == 3
        assert 0 <= correlation_matrix.diversification_score <= 1.0

    def test_check_correlation_limits(self):
        """Test correlation limits check"""
        # Mock correlation matrix with high correlation
        matrix = {
            "BTC": {"BTC": 1.0, "ETH": 0.85},
            "ETH": {"BTC": 0.85, "ETH": 1.0},
        }

        highly_correlated = self.analyzer.check_correlation_limits(
            correlation_matrix=matrix,
            max_correlation=0.7,
        )

        assert len(highly_correlated) > 0
        assert highly_correlated[0].correlation > 0.7

    def test_calculate_returns(self):
        """Test returns calculation"""
        prices = [
            Decimal("100.00"),
            Decimal("105.00"),
            Decimal("103.00"),
            Decimal("107.00"),
        ]

        returns = self.analyzer._calculate_returns(prices)

        assert len(returns) == 3
        assert returns[0] > 0  # 5% gain
        assert returns[1] < 0  # ~1.9% loss
        assert returns[2] > 0  # ~3.9% gain

    def test_calculate_correlation(self):
        """Test correlation calculation"""
        returns1 = [0.01, -0.02, 0.03, -0.01, 0.02]
        returns2 = [0.015, -0.018, 0.028, -0.012, 0.022]

        correlation = self.analyzer._calculate_correlation(returns1, returns2)

        # Should be highly correlated (similar movements)
        assert 0.8 < correlation <= 1.0

    def test_calculate_diversification_score(self):
        """Test diversification score calculation"""
        # Low correlation = high diversification
        matrix_low_corr = {
            "A": {"A": 1.0, "B": 0.1, "C": 0.2},
            "B": {"A": 0.1, "B": 1.0, "C": 0.15},
            "C": {"A": 0.2, "B": 0.15, "C": 1.0},
        }

        score_high_div = self.analyzer._calculate_diversification_score(matrix_low_corr)
        assert score_high_div > 0.7

        # High correlation = low diversification
        matrix_high_corr = {
            "A": {"A": 1.0, "B": 0.9, "C": 0.85},
            "B": {"A": 0.9, "B": 1.0, "C": 0.88},
            "C": {"A": 0.85, "B": 0.88, "C": 1.0},
        }

        score_low_div = self.analyzer._calculate_diversification_score(matrix_high_corr)
        assert score_low_div < 0.3

    def test_get_correlation_strength(self):
        """Test correlation strength classification"""
        assert self.analyzer._get_correlation_strength(0.95) == "very_strong"
        assert self.analyzer._get_correlation_strength(0.75) == "strong"
        assert self.analyzer._get_correlation_strength(0.55) == "moderate"
        assert self.analyzer._get_correlation_strength(0.35) == "weak"
        assert self.analyzer._get_correlation_strength(0.15) == "negligible"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
