"""
Unit Tests for Kelly Position Sizer

Tests for dynamic position sizing using Kelly Criterion.

Author: Risk Management Team
Date: 2025-10-29
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta

from workspace.features.risk_manager.position_sizing import (
    KellyPositionSizer,
    TradeResult,
    PositionSizingResult,
)


class TestKellyPositionSizer:
    """Test suite for KellyPositionSizer"""

    def setup_method(self):
        """Set up test fixtures"""
        self.sizer = KellyPositionSizer(max_kelly_fraction=0.25)
        self.portfolio_value = Decimal("2626.96")

    def test_initialization(self):
        """Test position sizer initialization"""
        assert self.sizer.max_kelly_fraction == 0.25
        assert self.sizer.min_sample_size == 10

    def test_calculate_position_size_basic(self):
        """Test basic Kelly calculation"""
        # Win rate 55%, avg win $100, avg loss $80
        position_size = self.sizer.calculate_position_size(
            win_rate=0.55,
            avg_win=Decimal("100.00"),
            avg_loss=Decimal("80.00"),
            portfolio_value=self.portfolio_value,
        )

        # Should be positive and reasonable
        assert position_size > Decimal("0")
        assert position_size < self.portfolio_value  # Never exceed portfolio

    def test_calculate_position_size_high_win_rate(self):
        """Test with high win rate"""
        position_size = self.sizer.calculate_position_size(
            win_rate=0.70,
            avg_win=Decimal("100.00"),
            avg_loss=Decimal("50.00"),
            portfolio_value=self.portfolio_value,
        )

        # High win rate should yield larger position
        assert position_size > Decimal("100")

    def test_calculate_position_size_low_win_rate(self):
        """Test with low win rate"""
        position_size = self.sizer.calculate_position_size(
            win_rate=0.40,
            avg_win=Decimal("150.00"),
            avg_loss=Decimal("100.00"),
            portfolio_value=self.portfolio_value,
        )

        # Low win rate may yield smaller or zero position
        assert position_size >= Decimal("0")

    def test_calculate_position_size_zero_avg_loss(self):
        """Test with zero average loss (edge case)"""
        position_size = self.sizer.calculate_position_size(
            win_rate=0.60,
            avg_win=Decimal("100.00"),
            avg_loss=Decimal("0"),
            portfolio_value=self.portfolio_value,
        )

        # Should return zero (invalid parameters)
        assert position_size == Decimal("0")

    def test_calculate_position_size_with_confidence(self):
        """Test with confidence adjustment"""
        # Full confidence
        size_full = self.sizer.calculate_position_size(
            win_rate=0.60,
            avg_win=Decimal("100.00"),
            avg_loss=Decimal("80.00"),
            portfolio_value=self.portfolio_value,
            confidence_level=1.0,
        )

        # Half confidence
        size_half = self.sizer.calculate_position_size(
            win_rate=0.60,
            avg_win=Decimal("100.00"),
            avg_loss=Decimal("80.00"),
            portfolio_value=self.portfolio_value,
            confidence_level=0.5,
        )

        # Half confidence should yield smaller position
        assert size_half < size_full
        assert abs(size_half - size_full / 2) < Decimal("1.00")  # Approximately half

    def test_calculate_from_trade_history(self):
        """Test calculation from trade history"""
        # Create mock trade history
        now = datetime.utcnow()
        trades = [
            TradeResult(
                symbol="BTC",
                realized_pnl=Decimal("100.00"),
                entry_time=now - timedelta(days=10),
                exit_time=now - timedelta(days=9),
                duration_seconds=86400,
            ),
            TradeResult(
                symbol="ETH",
                realized_pnl=Decimal("-50.00"),
                entry_time=now - timedelta(days=8),
                exit_time=now - timedelta(days=7),
                duration_seconds=86400,
            ),
            TradeResult(
                symbol="SOL",
                realized_pnl=Decimal("80.00"),
                entry_time=now - timedelta(days=6),
                exit_time=now - timedelta(days=5),
                duration_seconds=86400,
            ),
        ]

        result = self.sizer.calculate_from_trade_history(
            trade_history=trades,
            portfolio_value=self.portfolio_value,
            lookback_days=30,
        )

        assert isinstance(result, PositionSizingResult)
        assert result.trade_count == 3
        assert result.win_rate > 0.5  # 2 wins out of 3
        assert result.recommended_size_chf >= Decimal("0")

    def test_calculate_from_empty_history(self):
        """Test with empty trade history"""
        result = self.sizer.calculate_from_trade_history(
            trade_history=[],
            portfolio_value=self.portfolio_value,
            lookback_days=30,
        )

        assert result.recommended_size_chf == Decimal("0")
        assert result.trade_count == 0
        assert result.calculation_method == "insufficient_data"

    def test_calculate_confidence(self):
        """Test confidence calculation"""
        # Full confidence with enough samples
        confidence = self.sizer._calculate_confidence(20)
        assert confidence == 1.0

        # Reduced confidence with small sample
        confidence_small = self.sizer._calculate_confidence(5)
        assert 0 < confidence_small < 1.0

    def test_calculate_optimal_kelly_fraction(self):
        """Test optimal Kelly fraction calculation"""
        optimal_fraction = self.sizer.calculate_optimal_kelly_fraction(
            win_rate=0.55,
            win_loss_ratio=Decimal("1.25"),
            max_drawdown_tolerance=Decimal("0.20"),
        )

        assert 0 <= optimal_fraction <= 0.25  # Capped at max_kelly_fraction


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
