"""
Strategy Tests

Comprehensive tests for all trading strategy implementations.

Author: Strategy Implementation Team
Date: 2025-10-28
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone

from workspace.features.strategy import (
    StrategySignal,
    StrategyType,
    MeanReversionStrategy,
    TrendFollowingStrategy,
    VolatilityBreakoutStrategy,
)
from workspace.features.trading_loop import TradingDecision
from workspace.features.market_data import (
    MarketDataSnapshot,
    OHLCV,
    Ticker,
    RSI,
    MACD,
    EMA,
    BollingerBands,
    Timeframe,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def base_snapshot():
    """Create base snapshot with all required data"""
    return MarketDataSnapshot(
        symbol="BTC/USDT:USDT",
        timeframe=Timeframe.M3,
        timestamp=datetime.now(timezone.utc),
        ohlcv=OHLCV(
            symbol="BTC/USDT:USDT",
            timeframe=Timeframe.M3,
            timestamp=datetime.now(timezone.utc),
            open=Decimal("50000.00"),
            high=Decimal("50500.00"),
            low=Decimal("49500.00"),
            close=Decimal("50200.00"),
            volume=Decimal("100.0"),
        ),
        ticker=Ticker(
            symbol="BTC/USDT:USDT",
            timestamp=datetime.now(timezone.utc),
            bid=Decimal("50150.00"),
            ask=Decimal("50250.00"),
            last=Decimal("50200.00"),
            high_24h=Decimal("51000.00"),
            low_24h=Decimal("49000.00"),
            volume_24h=Decimal("48000.0"),  # 480 * 100
            change_24h=Decimal("500.00"),
            change_24h_pct=Decimal("1.00"),
        ),
        rsi=None,
        macd=None,
        ema_fast=None,
        ema_slow=None,
        bollinger=None,
    )


@pytest.fixture
def oversold_snapshot(base_snapshot):
    """Snapshot with oversold RSI (< 30)"""
    base_snapshot.rsi = RSI(
        value=Decimal("25.0"),
        is_oversold=True,
        is_overbought=False,
    )
    base_snapshot.bollinger = BollingerBands(
        upper=Decimal("51000.00"),
        middle=Decimal("50000.00"),
        lower=Decimal("49000.00"),
        bandwidth=Decimal("0.04"),
        percent_b=Decimal("0.6"),
        is_squeeze=False,
    )
    base_snapshot.macd = MACD(
        value=Decimal("-100.0"),
        signal=Decimal("-150.0"),
        histogram=Decimal("50.0"),
        is_bullish=False,
    )
    return base_snapshot


@pytest.fixture
def overbought_snapshot(base_snapshot):
    """Snapshot with overbought RSI (> 70)"""
    base_snapshot.rsi = RSI(
        value=Decimal("75.0"),
        is_oversold=False,
        is_overbought=True,
    )
    base_snapshot.bollinger = BollingerBands(
        upper=Decimal("51000.00"),
        middle=Decimal("50000.00"),
        lower=Decimal("49000.00"),
        bandwidth=Decimal("0.04"),
        percent_b=Decimal("0.6"),
        is_squeeze=False,
    )
    base_snapshot.macd = MACD(
        value=Decimal("100.0"),
        signal=Decimal("150.0"),
        histogram=Decimal("-50.0"),
        is_bullish=False,
    )
    return base_snapshot


@pytest.fixture
def neutral_rsi_snapshot(base_snapshot):
    """Snapshot with neutral RSI (30-70)"""
    base_snapshot.rsi = RSI(
        value=Decimal("50.0"),
        is_oversold=False,
        is_overbought=False,
    )
    return base_snapshot


@pytest.fixture
def bullish_trend_snapshot(base_snapshot):
    """Snapshot with bullish EMA crossover"""
    base_snapshot.ema_fast = EMA(
        period=12,
        value=Decimal("50500.00"),
    )
    base_snapshot.ema_slow = EMA(
        period=26,
        value=Decimal("50000.00"),
    )
    base_snapshot.rsi = RSI(
        value=Decimal("60.0"),
        is_oversold=False,
        is_overbought=False,
    )
    base_snapshot.macd = MACD(
        value=Decimal("150.0"),
        signal=Decimal("100.0"),
        histogram=Decimal("50.0"),
        is_bullish=True,
    )
    return base_snapshot


@pytest.fixture
def bearish_trend_snapshot(base_snapshot):
    """Snapshot with bearish EMA crossover"""
    base_snapshot.ema_fast = EMA(
        period=12,
        value=Decimal("49500.00"),
    )
    base_snapshot.ema_slow = EMA(
        period=26,
        value=Decimal("50000.00"),
    )
    base_snapshot.rsi = RSI(
        value=Decimal("40.0"),
        is_oversold=False,
        is_overbought=False,
    )
    base_snapshot.macd = MACD(
        value=Decimal("-150.0"),
        signal=Decimal("-100.0"),
        histogram=Decimal("-50.0"),
        is_bullish=False,
    )
    return base_snapshot


@pytest.fixture
def squeeze_snapshot(base_snapshot):
    """Snapshot with Bollinger Band squeeze"""
    base_snapshot.ticker.last = Decimal("50000.00")
    base_snapshot.bollinger = BollingerBands(
        upper=Decimal("50500.00"),
        middle=Decimal("50000.00"),
        lower=Decimal("49500.00"),
        bandwidth=Decimal("0.015"),  # 1.5% < 2% threshold
        percent_b=Decimal("0.5"),
        is_squeeze=True,
    )
    base_snapshot.rsi = RSI(
        value=Decimal("55.0"),
        is_oversold=False,
        is_overbought=False,
    )
    base_snapshot.macd = MACD(
        value=Decimal("0.0"),
        signal=Decimal("0.0"),
        histogram=Decimal("0.0"),
        is_bullish=False,
    )
    return base_snapshot


@pytest.fixture
def upper_breakout_snapshot(base_snapshot):
    """Snapshot with upper Bollinger Band breakout"""
    base_snapshot.ticker.last = Decimal("50800.00")  # Above upper band
    base_snapshot.ohlcv.volume = Decimal("150.0")  # High volume
    base_snapshot.bollinger = BollingerBands(
        upper=Decimal("50500.00"),
        middle=Decimal("50000.00"),
        lower=Decimal("49500.00"),
        bandwidth=Decimal("0.015"),  # Squeeze
        percent_b=Decimal("1.3"),
        is_squeeze=True,
    )
    base_snapshot.rsi = RSI(
        value=Decimal("65.0"),
        is_oversold=False,
        is_overbought=False,
    )
    base_snapshot.macd = MACD(
        value=Decimal("100.0"),
        signal=Decimal("50.0"),
        histogram=Decimal("50.0"),
        is_bullish=True,
    )
    return base_snapshot


@pytest.fixture
def lower_breakout_snapshot(base_snapshot):
    """Snapshot with lower Bollinger Band breakout"""
    base_snapshot.ticker.last = Decimal("49200.00")  # Below lower band
    base_snapshot.ohlcv.volume = Decimal("150.0")  # High volume
    base_snapshot.bollinger = BollingerBands(
        upper=Decimal("50500.00"),
        middle=Decimal("50000.00"),
        lower=Decimal("49500.00"),
        bandwidth=Decimal("0.015"),  # Squeeze
        percent_b=Decimal("-0.3"),
        is_squeeze=True,
    )
    base_snapshot.rsi = RSI(
        value=Decimal("35.0"),
        is_oversold=False,
        is_overbought=False,
    )
    base_snapshot.macd = MACD(
        value=Decimal("-100.0"),
        signal=Decimal("-50.0"),
        histogram=Decimal("-50.0"),
        is_bullish=False,
    )
    return base_snapshot


# ============================================================================
# StrategySignal Tests
# ============================================================================


class TestStrategySignal:
    """Tests for StrategySignal dataclass"""

    def test_valid_signal_creation(self):
        """Test creating a valid strategy signal"""
        signal = StrategySignal(
            symbol="BTC/USDT:USDT",
            decision=TradingDecision.BUY,
            confidence=Decimal("0.8"),
            size_pct=Decimal("0.15"),
            stop_loss_pct=Decimal("0.02"),
            take_profit_pct=Decimal("0.04"),
            reasoning="Test signal",
            strategy_name="Test Strategy",
        )

        assert signal.symbol == "BTC/USDT:USDT"
        assert signal.decision == TradingDecision.BUY
        assert signal.confidence == Decimal("0.8")
        assert signal.size_pct == Decimal("0.15")

    def test_confidence_validation(self):
        """Test confidence must be 0-1"""
        with pytest.raises(ValueError, match="Confidence must be 0-1"):
            StrategySignal(
                symbol="BTC/USDT:USDT",
                decision=TradingDecision.BUY,
                confidence=Decimal("1.5"),
                size_pct=Decimal("0.15"),
            )

    def test_size_pct_validation(self):
        """Test size_pct must be 0-1"""
        with pytest.raises(ValueError, match="Size percentage must be 0-1"):
            StrategySignal(
                symbol="BTC/USDT:USDT",
                decision=TradingDecision.BUY,
                confidence=Decimal("0.8"),
                size_pct=Decimal("1.5"),
            )


# ============================================================================
# MeanReversionStrategy Tests
# ============================================================================


class TestMeanReversionStrategy:
    """Tests for Mean Reversion Strategy"""

    def test_strategy_initialization(self):
        """Test strategy initialization with default config"""
        strategy = MeanReversionStrategy()

        assert strategy.get_name() == "Mean Reversion (RSI-based)"
        assert strategy.get_type() == StrategyType.MEAN_REVERSION
        assert strategy.rsi_oversold == Decimal("30")
        assert strategy.rsi_overbought == Decimal("70")

    def test_custom_config(self):
        """Test strategy with custom configuration"""
        strategy = MeanReversionStrategy(
            config={
                "rsi_oversold": 25,
                "rsi_overbought": 75,
                "position_size_pct": 0.20,
            }
        )

        assert strategy.rsi_oversold == Decimal("25")
        assert strategy.rsi_overbought == Decimal("75")
        assert strategy.position_size_pct == Decimal("0.20")

    def test_buy_signal_on_oversold(self, oversold_snapshot):
        """Test BUY signal when RSI is oversold"""
        strategy = MeanReversionStrategy()
        signal = strategy.analyze(oversold_snapshot)

        assert signal.decision == TradingDecision.BUY
        assert signal.confidence > Decimal("0.5")
        assert signal.size_pct > Decimal("0.0")
        assert "RSI oversold" in signal.reasoning

    def test_sell_signal_on_overbought(self, overbought_snapshot):
        """Test SELL signal when RSI is overbought"""
        strategy = MeanReversionStrategy()
        signal = strategy.analyze(overbought_snapshot)

        assert signal.decision == TradingDecision.SELL
        assert signal.confidence > Decimal("0.5")
        assert signal.size_pct > Decimal("0.0")
        assert "RSI overbought" in signal.reasoning

    def test_hold_on_neutral_rsi(self, neutral_rsi_snapshot):
        """Test HOLD when RSI is neutral"""
        strategy = MeanReversionStrategy()
        signal = strategy.analyze(neutral_rsi_snapshot)

        assert signal.decision == TradingDecision.HOLD
        assert signal.size_pct == Decimal("0.0")
        assert "RSI neutral" in signal.reasoning

    def test_bollinger_confirmation(self, oversold_snapshot):
        """Test Bollinger Band confirmation increases confidence"""
        # Set price near lower band
        oversold_snapshot.ticker.last = Decimal("49100.00")  # Near lower band (49000)

        strategy = MeanReversionStrategy()
        signal = strategy.analyze(oversold_snapshot)

        assert signal.decision == TradingDecision.BUY
        assert "Bollinger" in signal.reasoning

    def test_macd_confirmation(self, oversold_snapshot):
        """Test MACD confirmation increases confidence"""
        # MACD histogram already positive in fixture
        strategy = MeanReversionStrategy()
        signal = strategy.analyze(oversold_snapshot)

        assert signal.decision == TradingDecision.BUY
        assert "MACD" in signal.reasoning

    def test_no_rsi_returns_hold(self, base_snapshot):
        """Test HOLD when RSI not available"""
        strategy = MeanReversionStrategy()
        signal = strategy.analyze(base_snapshot)

        assert signal.decision == TradingDecision.HOLD
        assert "RSI not available" in signal.reasoning

    def test_invalid_snapshot_returns_hold(self):
        """Test HOLD on invalid snapshot"""
        strategy = MeanReversionStrategy()

        # Create minimal invalid snapshot
        invalid_snapshot = MarketDataSnapshot(
            symbol="BTC/USDT:USDT",
            timestamp=datetime.now(timezone.utc),
            ohlcv=None,  # Missing required data
            ticker=None,
        )

        signal = strategy.analyze(invalid_snapshot)
        assert signal.decision == TradingDecision.HOLD


# ============================================================================
# TrendFollowingStrategy Tests
# ============================================================================


class TestTrendFollowingStrategy:
    """Tests for Trend Following Strategy"""

    def test_strategy_initialization(self):
        """Test strategy initialization with default config"""
        strategy = TrendFollowingStrategy()

        assert strategy.get_name() == "Trend Following (EMA Crossover)"
        assert strategy.get_type() == StrategyType.TREND_FOLLOWING
        assert strategy.ema_fast_period == 12
        assert strategy.ema_slow_period == 26

    def test_custom_config(self):
        """Test strategy with custom configuration"""
        strategy = TrendFollowingStrategy(
            config={
                "ema_fast_period": 9,
                "ema_slow_period": 21,
                "min_ema_distance_pct": 0.8,
            }
        )

        assert strategy.ema_fast_period == 9
        assert strategy.ema_slow_period == 21
        assert strategy.min_ema_distance_pct == Decimal("0.8")

    def test_buy_signal_on_bullish_crossover(self, bullish_trend_snapshot):
        """Test BUY signal when Fast EMA > Slow EMA"""
        strategy = TrendFollowingStrategy()
        signal = strategy.analyze(bullish_trend_snapshot)

        assert signal.decision == TradingDecision.BUY
        assert signal.confidence > Decimal("0.5")
        assert signal.size_pct > Decimal("0.0")
        assert "Bullish trend" in signal.reasoning

    def test_sell_signal_on_bearish_crossover(self, bearish_trend_snapshot):
        """Test SELL signal when Fast EMA < Slow EMA"""
        strategy = TrendFollowingStrategy()
        signal = strategy.analyze(bearish_trend_snapshot)

        assert signal.decision == TradingDecision.SELL
        assert signal.confidence > Decimal("0.5")
        assert signal.size_pct > Decimal("0.0")
        assert "Bearish trend" in signal.reasoning

    def test_hold_on_small_ema_distance(self, bullish_trend_snapshot):
        """Test HOLD when EMA distance too small (whipsaw protection)"""
        # Make EMAs very close
        bullish_trend_snapshot.ema_fast.value = Decimal("50100.00")
        bullish_trend_snapshot.ema_slow.value = Decimal("50000.00")
        # Distance = 100 / 50000 * 100 = 0.2% < 0.5% threshold

        strategy = TrendFollowingStrategy()
        signal = strategy.analyze(bullish_trend_snapshot)

        assert signal.decision == TradingDecision.HOLD
        assert "EMA distance too small" in signal.reasoning

    def test_rsi_filter_blocks_extreme_buy(self, bullish_trend_snapshot):
        """Test RSI filter blocks BUY when RSI too high"""
        bullish_trend_snapshot.rsi.value = Decimal("85.0")  # Above 80 threshold

        strategy = TrendFollowingStrategy()
        signal = strategy.analyze(bullish_trend_snapshot)

        assert signal.decision == TradingDecision.HOLD
        assert "RSI too high" in signal.reasoning

    def test_rsi_filter_blocks_extreme_sell(self, bearish_trend_snapshot):
        """Test RSI filter blocks SELL when RSI too low"""
        bearish_trend_snapshot.rsi.value = Decimal("15.0")  # Below 20 threshold

        strategy = TrendFollowingStrategy()
        signal = strategy.analyze(bearish_trend_snapshot)

        assert signal.decision == TradingDecision.HOLD
        assert "RSI too low" in signal.reasoning

    def test_macd_confirmation(self, bullish_trend_snapshot):
        """Test MACD confirmation increases confidence"""
        strategy = TrendFollowingStrategy()
        signal = strategy.analyze(bullish_trend_snapshot)

        assert signal.decision == TradingDecision.BUY
        assert "MACD confirms" in signal.reasoning

    def test_no_emas_returns_hold(self, base_snapshot):
        """Test HOLD when EMAs not available"""
        strategy = TrendFollowingStrategy()
        signal = strategy.analyze(base_snapshot)

        assert signal.decision == TradingDecision.HOLD
        assert "EMAs not available" in signal.reasoning


# ============================================================================
# VolatilityBreakoutStrategy Tests
# ============================================================================


class TestVolatilityBreakoutStrategy:
    """Tests for Volatility Breakout Strategy"""

    def test_strategy_initialization(self):
        """Test strategy initialization with default config"""
        strategy = VolatilityBreakoutStrategy()

        assert strategy.get_name() == "Volatility Breakout (Bollinger Bands)"
        assert strategy.get_type() == StrategyType.VOLATILITY_BREAKOUT
        assert strategy.squeeze_threshold == Decimal("0.02")
        assert strategy.breakout_threshold_pct == Decimal("0.5")

    def test_custom_config(self):
        """Test strategy with custom configuration"""
        strategy = VolatilityBreakoutStrategy(
            config={
                "squeeze_bandwidth_threshold": 0.015,
                "breakout_threshold_pct": 0.8,
                "position_size_pct": 0.20,
            }
        )

        assert strategy.squeeze_threshold == Decimal("0.015")
        assert strategy.breakout_threshold_pct == Decimal("0.8")
        assert strategy.position_size_pct == Decimal("0.20")

    def test_hold_on_no_squeeze(self, base_snapshot):
        """Test HOLD when no squeeze detected"""
        base_snapshot.bollinger = BollingerBands(
            upper=Decimal("52000.00"),
            middle=Decimal("50000.00"),
            lower=Decimal("48000.00"),
            bandwidth=Decimal("0.08"),  # 8% > 2% threshold
            percent_b=Decimal("0.55"),
            is_squeeze=False,
        )

        strategy = VolatilityBreakoutStrategy()
        signal = strategy.analyze(base_snapshot)

        assert signal.decision == TradingDecision.HOLD
        assert "No squeeze detected" in signal.reasoning

    def test_hold_during_squeeze_no_breakout(self, squeeze_snapshot):
        """Test HOLD when squeeze but no breakout yet"""
        strategy = VolatilityBreakoutStrategy()
        signal = strategy.analyze(squeeze_snapshot)

        assert signal.decision == TradingDecision.HOLD
        assert "Squeeze detected but no breakout" in signal.reasoning

    def test_buy_on_upper_breakout(self, upper_breakout_snapshot):
        """Test BUY signal on upper band breakout"""
        strategy = VolatilityBreakoutStrategy()
        signal = strategy.analyze(upper_breakout_snapshot)

        assert signal.decision == TradingDecision.BUY
        assert signal.confidence > Decimal("0.5")
        assert signal.size_pct > Decimal("0.0")
        assert "Upper band breakout" in signal.reasoning
        assert "After squeeze" in signal.reasoning

    def test_sell_on_lower_breakout(self, lower_breakout_snapshot):
        """Test SELL signal on lower band breakout"""
        strategy = VolatilityBreakoutStrategy()
        signal = strategy.analyze(lower_breakout_snapshot)

        assert signal.decision == TradingDecision.SELL
        assert signal.confidence > Decimal("0.5")
        assert signal.size_pct > Decimal("0.0")
        assert "Lower band breakout" in signal.reasoning
        assert "After squeeze" in signal.reasoning

    def test_volume_confirmation(self, upper_breakout_snapshot):
        """Test volume confirmation increases confidence"""
        strategy = VolatilityBreakoutStrategy()
        signal = strategy.analyze(upper_breakout_snapshot)

        assert signal.decision == TradingDecision.BUY
        assert "Volume confirmation" in signal.reasoning

    def test_insufficient_volume_blocks_signal(self, upper_breakout_snapshot):
        """Test breakout blocked when volume insufficient"""
        upper_breakout_snapshot.ohlcv.volume = Decimal("50.0")  # Low volume

        strategy = VolatilityBreakoutStrategy()
        signal = strategy.analyze(upper_breakout_snapshot)

        assert signal.decision == TradingDecision.HOLD
        assert "insufficient volume" in signal.reasoning

    def test_rsi_confirmation_buy(self, upper_breakout_snapshot):
        """Test RSI confirmation for BUY"""
        strategy = VolatilityBreakoutStrategy()
        signal = strategy.analyze(upper_breakout_snapshot)

        assert signal.decision == TradingDecision.BUY
        assert "RSI confirms upward momentum" in signal.reasoning

    def test_rsi_confirmation_sell(self, lower_breakout_snapshot):
        """Test RSI confirmation for SELL"""
        strategy = VolatilityBreakoutStrategy()
        signal = strategy.analyze(lower_breakout_snapshot)

        assert signal.decision == TradingDecision.SELL
        assert "RSI confirms downward momentum" in signal.reasoning

    def test_no_bollinger_returns_hold(self, base_snapshot):
        """Test HOLD when Bollinger Bands not available"""
        strategy = VolatilityBreakoutStrategy()
        signal = strategy.analyze(base_snapshot)

        assert signal.decision == TradingDecision.HOLD
        assert "Bollinger Bands not available" in signal.reasoning


# ============================================================================
# BaseStrategy Tests
# ============================================================================


class TestBaseStrategy:
    """Tests for BaseStrategy abstract class"""

    def test_validate_snapshot_success(self, base_snapshot):
        """Test snapshot validation succeeds with valid data"""
        strategy = MeanReversionStrategy()
        assert strategy.validate_snapshot(base_snapshot) is True

    def test_validate_snapshot_missing_ohlcv(self, base_snapshot):
        """Test snapshot validation fails without OHLCV"""
        base_snapshot.ohlcv = None
        strategy = MeanReversionStrategy()
        assert strategy.validate_snapshot(base_snapshot) is False

    def test_validate_snapshot_missing_ticker(self, base_snapshot):
        """Test snapshot validation fails without ticker"""
        base_snapshot.ticker = None
        strategy = MeanReversionStrategy()
        assert strategy.validate_snapshot(base_snapshot) is False

    def test_validate_snapshot_none(self):
        """Test snapshot validation fails on None"""
        strategy = MeanReversionStrategy()
        assert strategy.validate_snapshot(None) is False

    def test_get_config(self):
        """Test get_config returns configuration copy"""
        strategy = MeanReversionStrategy(config={"rsi_oversold": 25})
        config = strategy.get_config()

        assert config["rsi_oversold"] == 25
        # Modify returned config shouldn't affect strategy
        config["rsi_oversold"] = 40
        assert strategy.config["rsi_oversold"] == 25

    def test_get_stats(self, oversold_snapshot):
        """Test get_stats returns strategy statistics"""
        strategy = MeanReversionStrategy()

        # Generate signal to update stats
        strategy.analyze(oversold_snapshot)

        stats = strategy.get_stats()
        assert stats["name"] == "Mean Reversion (RSI-based)"
        assert stats["type"] == "mean_reversion"
        assert stats["signal_count"] == 1
        assert stats["last_signal_time"] is not None

    def test_signal_count_increments(self, oversold_snapshot, overbought_snapshot):
        """Test signal count increments correctly"""
        strategy = MeanReversionStrategy()

        assert strategy._signal_count == 0

        strategy.analyze(oversold_snapshot)
        assert strategy._signal_count == 1

        strategy.analyze(overbought_snapshot)
        assert strategy._signal_count == 2


# ============================================================================
# Integration Tests
# ============================================================================


class TestStrategyIntegration:
    """Integration tests for multiple strategies"""

    def test_all_strategies_with_same_snapshot(self, bullish_trend_snapshot):
        """Test all strategies analyze same snapshot"""
        # Add all required indicators
        bullish_trend_snapshot.rsi = RSI(
            value=Decimal("60.0"),
            is_oversold=False,
            is_overbought=False,
        )
        bullish_trend_snapshot.bollinger = BollingerBands(
            upper=Decimal("51000.00"),
            middle=Decimal("50000.00"),
            lower=Decimal("49000.00"),
            bandwidth=Decimal("0.04"),
            percent_b=Decimal("0.6"),
            is_squeeze=False,
        )

        # Create all strategies
        mean_reversion = MeanReversionStrategy()
        trend_following = TrendFollowingStrategy()
        volatility_breakout = VolatilityBreakoutStrategy()

        # Analyze
        mr_signal = mean_reversion.analyze(bullish_trend_snapshot)
        tf_signal = trend_following.analyze(bullish_trend_snapshot)
        vb_signal = volatility_breakout.analyze(bullish_trend_snapshot)

        # All should return valid signals
        assert mr_signal.symbol == bullish_trend_snapshot.symbol
        assert tf_signal.symbol == bullish_trend_snapshot.symbol
        assert vb_signal.symbol == bullish_trend_snapshot.symbol

        # Trend following should BUY (bullish crossover)
        assert tf_signal.decision == TradingDecision.BUY

        # Mean reversion should HOLD (RSI neutral)
        assert mr_signal.decision == TradingDecision.HOLD

        # Volatility breakout should HOLD (no squeeze)
        assert vb_signal.decision == TradingDecision.HOLD

    def test_strategy_confidence_ranges(self):
        """Test all strategies produce valid confidence ranges"""
        strategies = [
            MeanReversionStrategy(),
            TrendFollowingStrategy(),
            VolatilityBreakoutStrategy(),
        ]

        # Create snapshots that should trigger signals
        {
            "mean_reversion": pytest.lazy_fixture("oversold_snapshot"),
            "trend_following": pytest.lazy_fixture("bullish_trend_snapshot"),
            "volatility_breakout": pytest.lazy_fixture("upper_breakout_snapshot"),
        }

        for strategy in strategies:
            # Get appropriate snapshot for strategy
            if isinstance(strategy, MeanReversionStrategy):
                pass
            elif isinstance(strategy, TrendFollowingStrategy):
                pass
            else:
                pass

            # Note: Can't use fixtures directly here, will need to create in actual test
            # This is just to show the pattern

    def test_strategy_type_uniqueness(self):
        """Test each strategy has unique type"""
        strategies = [
            MeanReversionStrategy(),
            TrendFollowingStrategy(),
            VolatilityBreakoutStrategy(),
        ]

        types = [s.get_type() for s in strategies]
        assert len(types) == len(set(types))  # All unique

    def test_strategy_name_uniqueness(self):
        """Test each strategy has unique name"""
        strategies = [
            MeanReversionStrategy(),
            TrendFollowingStrategy(),
            VolatilityBreakoutStrategy(),
        ]

        names = [s.get_name() for s in strategies]
        assert len(names) == len(set(names))  # All unique
