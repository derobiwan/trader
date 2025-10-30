"""
Strategy Tests (Simplified)

Concise tests for trading strategy implementations.

Author: Strategy Implementation Team
Date: 2025-10-28
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from workspace.features.market_data import (EMA, MACD, OHLCV, RSI,
                                            BollingerBands, MarketDataSnapshot,
                                            Ticker, Timeframe)
from workspace.features.strategy import (MeanReversionStrategy, StrategyType,
                                         TrendFollowingStrategy,
                                         VolatilityBreakoutStrategy)
from workspace.features.trading_loop import TradingDecision

# ============================================================================
# Helper Functions
# ============================================================================


def create_ticker(last_price: Decimal = Decimal("50000.00")) -> Ticker:
    """Create a ticker with required fields"""
    return Ticker(
        symbol="BTC/USDT:USDT",
        timestamp=datetime.now(timezone.utc),
        bid=last_price - Decimal("50"),
        ask=last_price + Decimal("50"),
        last=last_price,
        high_24h=last_price * Decimal("1.02"),
        low_24h=last_price * Decimal("0.98"),
        volume_24h=Decimal("48000.0"),
        change_24h=Decimal("500.00"),
        change_24h_pct=Decimal("1.00"),
    )


def create_ohlcv(close_price: Decimal = Decimal("50000.00")) -> OHLCV:
    """Create OHLCV with required fields"""
    return OHLCV(
        symbol="BTC/USDT:USDT",
        timeframe=Timeframe.M3,
        timestamp=datetime.now(timezone.utc),
        open=close_price - Decimal("100"),
        high=close_price + Decimal("200"),
        low=close_price - Decimal("200"),
        close=close_price,
        volume=Decimal("100.0"),
    )


def create_rsi(value: Decimal = Decimal("50.0")) -> RSI:
    """Create RSI indicator with required fields"""
    return RSI(
        symbol="BTC/USDT:USDT",
        timeframe=Timeframe.M3,
        timestamp=datetime.now(timezone.utc),
        value=value,
    )


def create_macd(is_bullish: bool = True) -> MACD:
    """Create MACD indicator with required fields"""
    macd_val = Decimal("100.0") if is_bullish else Decimal("-100.0")
    signal_val = Decimal("50.0") if is_bullish else Decimal("-50.0")
    return MACD(
        symbol="BTC/USDT:USDT",
        timeframe=Timeframe.M3,
        timestamp=datetime.now(timezone.utc),
        macd_line=macd_val,
        signal_line=signal_val,
        histogram=macd_val - signal_val,
    )


def create_ema(value: Decimal, period: int) -> EMA:
    """Create EMA indicator with required fields"""
    return EMA(
        symbol="BTC/USDT:USDT",
        timeframe=Timeframe.M3,
        timestamp=datetime.now(timezone.utc),
        value=value,
        period=period,
    )


def create_bollinger_bands(
    upper: Decimal, middle: Decimal, lower: Decimal
) -> BollingerBands:
    """Create Bollinger Bands with required fields"""
    return BollingerBands(
        symbol="BTC/USDT:USDT",
        timeframe=Timeframe.M3,
        timestamp=datetime.now(timezone.utc),
        upper_band=upper,
        middle_band=middle,
        lower_band=lower,
        bandwidth=upper - lower,
    )


def create_snapshot(
    price: Decimal = Decimal("50000.00"),
    rsi: RSI = None,
    macd: MACD = None,
    ema_fast: EMA = None,
    ema_slow: EMA = None,
    bollinger: BollingerBands = None,
) -> MarketDataSnapshot:
    """Create a market data snapshot with optional indicators"""
    return MarketDataSnapshot(
        symbol="BTC/USDT:USDT",
        timeframe=Timeframe.M3,
        timestamp=datetime.now(timezone.utc),
        ohlcv=create_ohlcv(price),
        ticker=create_ticker(price),
        rsi=rsi,
        macd=macd,
        ema_fast=ema_fast,
        ema_slow=ema_slow,
        bollinger=bollinger,
    )


# ============================================================================
# Tests
# ============================================================================


class TestMeanReversionStrategy:
    """Tests for Mean Reversion Strategy"""

    def test_strategy_initialization(self):
        """Test strategy initialization"""
        strategy = MeanReversionStrategy()
        assert strategy.get_name() == "Mean Reversion (RSI-based)"
        assert strategy.get_type() == StrategyType.MEAN_REVERSION

    def test_buy_signal_on_oversold(self):
        """Test BUY signal when RSI is oversold"""
        snapshot = create_snapshot(
            rsi=create_rsi(Decimal("25.0")),
            bollinger=create_bollinger_bands(
                Decimal("51000"), Decimal("50000"), Decimal("49000")
            ),
        )
        strategy = MeanReversionStrategy()
        signal = strategy.analyze(snapshot)

        assert signal.decision == TradingDecision.BUY
        assert signal.confidence > Decimal("0.5")

    def test_sell_signal_on_overbought(self):
        """Test SELL signal when RSI is overbought"""
        snapshot = create_snapshot(
            rsi=create_rsi(Decimal("75.0")),
            bollinger=create_bollinger_bands(
                Decimal("51000"), Decimal("50000"), Decimal("49000")
            ),
        )
        strategy = MeanReversionStrategy()
        signal = strategy.analyze(snapshot)

        assert signal.decision == TradingDecision.SELL
        assert signal.confidence > Decimal("0.5")

    def test_hold_on_neutral_rsi(self):
        """Test HOLD when RSI is neutral"""
        snapshot = create_snapshot(rsi=create_rsi(Decimal("50.0")))
        strategy = MeanReversionStrategy()
        signal = strategy.analyze(snapshot)

        assert signal.decision == TradingDecision.HOLD


class TestTrendFollowingStrategy:
    """Tests for Trend Following Strategy"""

    def test_strategy_initialization(self):
        """Test strategy initialization"""
        strategy = TrendFollowingStrategy()
        assert strategy.get_name() == "Trend Following (EMA Crossover)"
        assert strategy.get_type() == StrategyType.TREND_FOLLOWING

    def test_buy_signal_on_bullish_crossover(self):
        """Test BUY signal when Fast EMA > Slow EMA"""
        snapshot = create_snapshot(
            ema_fast=create_ema(Decimal("50500"), 12),
            ema_slow=create_ema(Decimal("50000"), 26),
            rsi=create_rsi(Decimal("60.0")),
        )
        strategy = TrendFollowingStrategy()
        signal = strategy.analyze(snapshot)

        assert signal.decision == TradingDecision.BUY
        assert signal.confidence > Decimal("0.5")

    def test_sell_signal_on_bearish_crossover(self):
        """Test SELL signal when Fast EMA < Slow EMA"""
        snapshot = create_snapshot(
            ema_fast=create_ema(Decimal("49500"), 12),
            ema_slow=create_ema(Decimal("50000"), 26),
            rsi=create_rsi(Decimal("40.0")),
        )
        strategy = TrendFollowingStrategy()
        signal = strategy.analyze(snapshot)

        assert signal.decision == TradingDecision.SELL
        assert signal.confidence > Decimal("0.5")


class TestVolatilityBreakoutStrategy:
    """Tests for Volatility Breakout Strategy"""

    def test_strategy_initialization(self):
        """Test strategy initialization"""
        strategy = VolatilityBreakoutStrategy()
        assert strategy.get_name() == "Volatility Breakout (Bollinger Bands)"
        assert strategy.get_type() == StrategyType.VOLATILITY_BREAKOUT

    def test_buy_on_upper_breakout(self):
        """Test BUY signal on upper band breakout"""
        snapshot = create_snapshot(
            price=Decimal("50800.00"),  # Above upper band
            bollinger=create_bollinger_bands(
                Decimal("50500"), Decimal("50000"), Decimal("49500")
            ),
            rsi=create_rsi(Decimal("65.0")),
        )
        # Set high volume
        snapshot.ohlcv.volume = Decimal("150.0")

        strategy = VolatilityBreakoutStrategy()
        signal = strategy.analyze(snapshot)

        assert signal.decision == TradingDecision.BUY
        assert signal.confidence > Decimal("0.5")

    def test_sell_on_lower_breakout(self):
        """Test SELL signal on lower band breakout"""
        snapshot = create_snapshot(
            price=Decimal("49200.00"),  # Below lower band
            bollinger=create_bollinger_bands(
                Decimal("50500"), Decimal("50000"), Decimal("49500")
            ),
            rsi=create_rsi(Decimal("35.0")),
        )
        # Set high volume
        snapshot.ohlcv.volume = Decimal("150.0")

        strategy = VolatilityBreakoutStrategy()
        signal = strategy.analyze(snapshot)

        assert signal.decision == TradingDecision.SELL
        assert signal.confidence > Decimal("0.5")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
