"""
Integration Tests: Strategy + Market Data

Tests verifying strategies work correctly with market data snapshots.
"""

from decimal import Decimal

import pytest

from workspace.features.strategy import (MeanReversionStrategy,
                                         TrendFollowingStrategy,
                                         VolatilityBreakoutStrategy)
from workspace.features.trading_loop import TradingDecision
from workspace.tests.integration.conftest import create_snapshot


class TestStrategyMarketDataIntegration:
    """Tests for strategy + market data integration"""

    def test_mean_reversion_with_oversold_conditions(self, market_snapshot_oversold):
        """Test mean reversion strategy detects oversold conditions"""
        strategy = MeanReversionStrategy()

        # Analyze market snapshot
        signal = strategy.analyze(market_snapshot_oversold)

        # Should generate BUY signal for oversold conditions
        assert signal is not None
        assert signal.decision == TradingDecision.BUY
        assert signal.confidence > Decimal("0.5")
        assert isinstance(signal.size_pct, Decimal)
        assert signal.size_pct > 0

    def test_mean_reversion_with_overbought_conditions(
        self, market_snapshot_overbought
    ):
        """Test mean reversion strategy detects overbought conditions"""
        strategy = MeanReversionStrategy()

        # Analyze market snapshot
        signal = strategy.analyze(market_snapshot_overbought)

        # Should generate SELL signal for overbought conditions
        assert signal is not None
        assert signal.decision == TradingDecision.SELL
        assert signal.confidence > Decimal("0.5")

    def test_mean_reversion_with_neutral_conditions(self, market_snapshot_neutral):
        """Test mean reversion strategy with neutral market"""
        strategy = MeanReversionStrategy()

        # Analyze market snapshot
        signal = strategy.analyze(market_snapshot_neutral)

        # Should likely be HOLD or low confidence
        assert signal is not None
        assert signal.decision in [
            TradingDecision.HOLD,
            TradingDecision.BUY,
            TradingDecision.SELL,
        ]

    def test_trend_following_with_bullish_trend(self):
        """Test trend following strategy detects bullish trend"""
        strategy = TrendFollowingStrategy()

        # Create snapshot with fast EMA above slow EMA (bullish)
        snapshot = create_snapshot(
            price=Decimal("50000.00"),
            rsi_value=Decimal("60.0"),
            is_bullish=True,
        )

        signal = strategy.analyze(snapshot)

        # Should generate BUY or HOLD signal
        assert signal is not None
        assert signal.decision in [TradingDecision.BUY, TradingDecision.HOLD]

    def test_volatility_breakout_strategy(self, market_snapshot_neutral):
        """Test volatility breakout strategy analyzes market"""
        strategy = VolatilityBreakoutStrategy()

        signal = strategy.analyze(market_snapshot_neutral)

        # Should produce valid signal
        assert signal is not None
        assert signal.decision in [
            TradingDecision.BUY,
            TradingDecision.SELL,
            TradingDecision.HOLD,
        ]
        assert isinstance(signal.confidence, Decimal)

    def test_multiple_strategies_same_snapshot(self, market_snapshot_oversold):
        """Test multiple strategies analyzing the same market snapshot"""
        strategies = [
            MeanReversionStrategy(),
            TrendFollowingStrategy(),
            VolatilityBreakoutStrategy(),
        ]

        signals = []
        for strategy in strategies:
            signal = strategy.analyze(market_snapshot_oversold)
            signals.append(signal)

        # All strategies should produce signals
        assert len(signals) == 3
        for signal in signals:
            assert signal is not None
            assert signal.decision in [
                TradingDecision.BUY,
                TradingDecision.SELL,
                TradingDecision.HOLD,
            ]
            assert isinstance(signal.confidence, Decimal)
            assert 0 <= signal.confidence <= 1

    def test_strategy_signal_has_risk_parameters(self, market_snapshot_oversold):
        """Test strategy signals include proper risk parameters"""
        strategy = MeanReversionStrategy()
        signal = strategy.analyze(market_snapshot_oversold)

        # Signal should have risk management fields
        if signal.decision != TradingDecision.HOLD:
            assert signal.stop_loss_pct is not None
            assert isinstance(signal.stop_loss_pct, Decimal)
            assert signal.stop_loss_pct > 0

            assert signal.take_profit_pct is not None
            assert isinstance(signal.take_profit_pct, Decimal)
            assert signal.take_profit_pct > 0

            # Take profit should be >= stop loss
            assert signal.take_profit_pct >= signal.stop_loss_pct

    def test_strategy_position_sizing_reasonable(self, market_snapshot_oversold):
        """Test strategy position sizing is within reasonable bounds"""
        strategies = [
            MeanReversionStrategy(),
            TrendFollowingStrategy(),
            VolatilityBreakoutStrategy(),
        ]

        for strategy in strategies:
            signal = strategy.analyze(market_snapshot_oversold)

            if signal.decision != TradingDecision.HOLD:
                # Position size should be reasonable
                assert Decimal("0") < signal.size_pct <= Decimal("0.25")

                # Higher confidence should generally mean larger position
                # (within reason - max 25%)
                expected_max = min(signal.confidence * Decimal("0.30"), Decimal("0.25"))
                assert signal.size_pct <= expected_max

    def test_strategy_provides_reasoning(self, market_snapshot_oversold):
        """Test strategies provide reasoning for their decisions"""
        strategy = MeanReversionStrategy()
        signal = strategy.analyze(market_snapshot_oversold)

        # Signal should include reasoning or strategy name
        assert signal.strategy_name is not None or signal.reasoning is not None

    def test_extreme_oversold_high_confidence(self):
        """Test extreme oversold conditions generate high confidence BUY"""
        strategy = MeanReversionStrategy()

        # Create extremely oversold snapshot (RSI = 15)
        snapshot = create_snapshot(
            price=Decimal("50000.00"),
            rsi_value=Decimal("15.0"),  # Extremely oversold
            is_bullish=True,
        )

        signal = strategy.analyze(snapshot)

        # Should be strong BUY signal
        assert signal.decision == TradingDecision.BUY
        assert signal.confidence >= Decimal("0.6")

    def test_extreme_overbought_high_confidence(self):
        """Test extreme overbought conditions generate high confidence SELL"""
        strategy = MeanReversionStrategy()

        # Create extremely overbought snapshot (RSI = 85)
        snapshot = create_snapshot(
            price=Decimal("50000.00"),
            rsi_value=Decimal("85.0"),  # Extremely overbought
            is_bullish=False,
        )

        signal = strategy.analyze(snapshot)

        # Should be strong SELL signal
        assert signal.decision == TradingDecision.SELL
        assert signal.confidence >= Decimal("0.6")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
