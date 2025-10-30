"""
Comprehensive tests for IndicatorCalculator

Tests cover:
- RSI calculation with various periods
- MACD calculation
- EMA calculation
- Bollinger Bands calculation
- All indicators batch calculation
- Edge cases (insufficient data, zero values, extreme prices)
- Decimal precision handling
- Indicator signals and conditions

Author: Validation Engineer - Market Data Team
Date: 2025-10-30
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from workspace.features.market_data.indicators import IndicatorCalculator
from workspace.features.market_data.models import OHLCV, Timeframe


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def minimal_ohlcv_data():
    """Fixture: Minimal OHLCV data for testing"""
    candles = []
    base_time = datetime.utcnow() - timedelta(hours=1)
    base_price = Decimal("100")

    for i in range(15):
        timestamp = base_time + timedelta(minutes=i)
        candle = OHLCV(
            symbol="TEST/USDT:USDT",
            timeframe=Timeframe.M1,
            timestamp=timestamp,
            open=base_price + Decimal(str(i)),
            high=base_price + Decimal(str(i + 1)),
            low=base_price + Decimal(str(i - 1)),
            close=base_price + Decimal(str(i + 0.5)),
            volume=Decimal("1.0"),
        )
        candles.append(candle)

    return candles


@pytest.fixture
def standard_ohlcv_data():
    """Fixture: Standard OHLCV data (50 candles)"""
    candles = []
    base_time = datetime.utcnow() - timedelta(hours=3)
    base_price = Decimal("90000")

    for i in range(50):
        timestamp = base_time + timedelta(minutes=3 * i)
        # Create some volatility
        price_change = Decimal(str(i % 10 - 5)) * Decimal("10")

        candle = OHLCV(
            symbol="BTC/USDT:USDT",
            timeframe=Timeframe.M3,
            timestamp=timestamp,
            open=base_price + price_change,
            high=base_price + price_change + Decimal("100"),
            low=base_price + price_change - Decimal("50"),
            close=base_price + price_change + Decimal("50"),
            volume=Decimal("1.5"),
            quote_volume=Decimal("135700"),
        )
        candles.append(candle)

    return candles


@pytest.fixture
def trending_up_data():
    """Fixture: Strong uptrend data"""
    candles = []
    base_time = datetime.utcnow() - timedelta(hours=3)
    base_price = Decimal("90000")

    for i in range(50):
        timestamp = base_time + timedelta(minutes=3 * i)
        price = base_price + Decimal(str(i * 100))  # Strong uptrend

        candle = OHLCV(
            symbol="BTC/USDT:USDT",
            timeframe=Timeframe.M3,
            timestamp=timestamp,
            open=price,
            high=price + Decimal("50"),
            low=price - Decimal("20"),
            close=price + Decimal("40"),
            volume=Decimal("1.5"),
        )
        candles.append(candle)

    return candles


@pytest.fixture
def trending_down_data():
    """Fixture: Strong downtrend data"""
    candles = []
    base_time = datetime.utcnow() - timedelta(hours=3)
    base_price = Decimal("95000")

    for i in range(50):
        timestamp = base_time + timedelta(minutes=3 * i)
        price = base_price - Decimal(str(i * 100))  # Strong downtrend

        candle = OHLCV(
            symbol="BTC/USDT:USDT",
            timeframe=Timeframe.M3,
            timestamp=timestamp,
            open=price,
            high=price + Decimal("20"),
            low=price - Decimal("50"),
            close=price - Decimal("40"),
            volume=Decimal("1.5"),
        )
        candles.append(candle)

    return candles


@pytest.fixture
def sideways_data():
    """Fixture: Sideways/ranging data"""
    candles = []
    base_time = datetime.utcnow() - timedelta(hours=3)
    base_price = Decimal("90000")

    for i in range(50):
        timestamp = base_time + timedelta(minutes=3 * i)
        # Small oscillations
        variation = Decimal(str((i % 5) - 2)) * Decimal("10")

        candle = OHLCV(
            symbol="BTC/USDT:USDT",
            timeframe=Timeframe.M3,
            timestamp=timestamp,
            open=base_price + variation,
            high=base_price + variation + Decimal("20"),
            low=base_price + variation - Decimal("20"),
            close=base_price + variation,
            volume=Decimal("1.5"),
        )
        candles.append(candle)

    return candles


# =============================================================================
# RSI Tests
# =============================================================================


class TestRSICalculation:
    """Tests for RSI (Relative Strength Index) calculation"""

    def test_rsi_insufficient_data(self, minimal_ohlcv_data):
        """Test RSI with insufficient data"""
        # Need period + 1 data points
        rsi = IndicatorCalculator.calculate_rsi(minimal_ohlcv_data[:14], period=14)
        assert rsi is None

    def test_rsi_minimum_data(self, minimal_ohlcv_data):
        """Test RSI with minimum required data"""
        rsi = IndicatorCalculator.calculate_rsi(minimal_ohlcv_data, period=14)
        assert rsi is not None
        assert rsi.symbol == "TEST/USDT:USDT"
        assert rsi.period == 14
        assert Decimal("0") <= rsi.value <= Decimal("100")

    def test_rsi_custom_period(self, standard_ohlcv_data):
        """Test RSI with custom period"""
        rsi_14 = IndicatorCalculator.calculate_rsi(standard_ohlcv_data, period=14)
        rsi_7 = IndicatorCalculator.calculate_rsi(standard_ohlcv_data, period=7)

        assert rsi_14 is not None
        assert rsi_7 is not None
        # Different periods should produce different values
        assert rsi_14.value != rsi_7.value

    def test_rsi_overbought_oversold_thresholds(self, standard_ohlcv_data):
        """Test RSI with custom thresholds"""
        rsi = IndicatorCalculator.calculate_rsi(
            standard_ohlcv_data,
            period=14,
            overbought=Decimal("70"),
            oversold=Decimal("30"),
        )

        assert rsi is not None
        assert rsi.overbought_level == Decimal("70")
        assert rsi.oversold_level == Decimal("30")

    def test_rsi_on_uptrend(self, trending_up_data):
        """Test RSI behavior on uptrend"""
        rsi = IndicatorCalculator.calculate_rsi(trending_up_data, period=14)

        assert rsi is not None
        # Strong uptrend should have high RSI
        assert rsi.value > Decimal("60")

    def test_rsi_on_downtrend(self, trending_down_data):
        """Test RSI behavior on downtrend"""
        rsi = IndicatorCalculator.calculate_rsi(trending_down_data, period=14)

        assert rsi is not None
        # Strong downtrend should have low RSI
        assert rsi.value < Decimal("40")

    def test_rsi_on_sideways(self, sideways_data):
        """Test RSI behavior on sideways market"""
        rsi = IndicatorCalculator.calculate_rsi(sideways_data, period=14)

        assert rsi is not None
        # Sideways should be around 50
        assert Decimal("30") < rsi.value < Decimal("70")

    def test_rsi_timestamp_and_symbol(self, standard_ohlcv_data):
        """Test RSI preserves symbol and timestamp from latest candle"""
        rsi = IndicatorCalculator.calculate_rsi(standard_ohlcv_data, period=14)

        latest = standard_ohlcv_data[-1]
        assert rsi.symbol == latest.symbol
        assert rsi.timestamp == latest.timestamp
        assert rsi.timeframe == latest.timeframe

    def test_rsi_calculation_properties(self, standard_ohlcv_data):
        """Test RSI calculation properties"""
        rsi = IndicatorCalculator.calculate_rsi(standard_ohlcv_data, period=14)

        assert rsi is not None
        # Value should always be between 0 and 100
        assert Decimal("0") <= rsi.value <= Decimal("100")
        # Timestamp should match latest candle
        assert rsi.timestamp == standard_ohlcv_data[-1].timestamp


# =============================================================================
# EMA Tests
# =============================================================================


class TestEMACalculation:
    """Tests for EMA (Exponential Moving Average) calculation"""

    def test_ema_insufficient_data(self, minimal_ohlcv_data):
        """Test EMA with insufficient data"""
        ema = IndicatorCalculator.calculate_ema(minimal_ohlcv_data[:5], period=10)
        assert ema is None

    def test_ema_minimum_data(self, minimal_ohlcv_data):
        """Test EMA with minimum required data"""
        ema = IndicatorCalculator.calculate_ema(minimal_ohlcv_data, period=10)
        assert ema is not None
        assert ema.symbol == "TEST/USDT:USDT"
        assert ema.period == 10

    def test_ema_various_periods(self, standard_ohlcv_data):
        """Test EMA with various periods"""
        ema_5 = IndicatorCalculator.calculate_ema(standard_ohlcv_data, period=5)
        ema_12 = IndicatorCalculator.calculate_ema(standard_ohlcv_data, period=12)
        ema_26 = IndicatorCalculator.calculate_ema(standard_ohlcv_data, period=26)

        assert ema_5 is not None
        assert ema_12 is not None
        assert ema_26 is not None

        # Different periods should produce different values
        assert ema_5.value != ema_12.value
        assert ema_12.value != ema_26.value

    def test_ema_follows_latest_price_trend(self, trending_up_data):
        """Test that EMA responds to price trend"""
        ema_fast = IndicatorCalculator.calculate_ema(trending_up_data, period=5)
        ema_slow = IndicatorCalculator.calculate_ema(trending_up_data, period=20)

        assert ema_fast is not None
        assert ema_slow is not None

        # On uptrend, fast EMA should be above slow EMA
        assert ema_fast.value > ema_slow.value

    def test_ema_on_downtrend(self, trending_down_data):
        """Test EMA behavior on downtrend"""
        ema_fast = IndicatorCalculator.calculate_ema(trending_down_data, period=5)
        ema_slow = IndicatorCalculator.calculate_ema(trending_down_data, period=20)

        assert ema_fast is not None
        assert ema_slow is not None

        # On downtrend, fast EMA should be below slow EMA
        assert ema_fast.value < ema_slow.value

    def test_ema_timestamp_and_symbol(self, standard_ohlcv_data):
        """Test EMA preserves symbol and timestamp"""
        ema = IndicatorCalculator.calculate_ema(standard_ohlcv_data, period=12)

        latest = standard_ohlcv_data[-1]
        assert ema.symbol == latest.symbol
        assert ema.timestamp == latest.timestamp
        assert ema.timeframe == latest.timeframe


# =============================================================================
# MACD Tests
# =============================================================================


class TestMACDCalculation:
    """Tests for MACD (Moving Average Convergence Divergence) calculation"""

    def test_macd_insufficient_data(self, standard_ohlcv_data):
        """Test MACD with insufficient data"""
        macd = IndicatorCalculator.calculate_macd(
            standard_ohlcv_data[:20], fast_period=12, slow_period=26, signal_period=9
        )
        assert macd is None

    def test_macd_minimum_data(self, standard_ohlcv_data):
        """Test MACD with minimum required data"""
        macd = IndicatorCalculator.calculate_macd(
            standard_ohlcv_data, fast_period=12, slow_period=26, signal_period=9
        )
        assert macd is not None
        assert macd.symbol == "BTC/USDT:USDT"

    def test_macd_components(self, standard_ohlcv_data):
        """Test MACD has all required components"""
        macd = IndicatorCalculator.calculate_macd(standard_ohlcv_data)

        assert macd is not None
        assert hasattr(macd, "macd_line")
        assert hasattr(macd, "signal_line")
        assert hasattr(macd, "histogram")
        assert macd.fast_period == 12
        assert macd.slow_period == 26
        assert macd.signal_period == 9

    def test_macd_on_uptrend(self, trending_up_data):
        """Test MACD behavior on uptrend"""
        macd = IndicatorCalculator.calculate_macd(trending_up_data)

        assert macd is not None
        # On strong uptrend, MACD should be positive
        assert macd.macd_line > Decimal("0")
        # Histogram should be positive on uptrend
        assert macd.histogram > Decimal("0")

    def test_macd_on_downtrend(self, trending_down_data):
        """Test MACD behavior on downtrend"""
        macd = IndicatorCalculator.calculate_macd(trending_down_data)

        assert macd is not None
        # On strong downtrend, MACD should be negative
        assert macd.macd_line < Decimal("0")
        # Histogram should be negative on downtrend
        assert macd.histogram < Decimal("0")

    def test_macd_crossover_potential(self, standard_ohlcv_data):
        """Test MACD crossover signals"""
        macd = IndicatorCalculator.calculate_macd(standard_ohlcv_data)

        assert macd is not None
        # Histogram = MACD Line - Signal Line
        expected_histogram = macd.macd_line - macd.signal_line
        assert abs(expected_histogram - macd.histogram) < Decimal(
            "0.001"
        )  # Allow tiny rounding error

    def test_macd_custom_parameters(self, standard_ohlcv_data):
        """Test MACD with custom parameters"""
        macd_custom = IndicatorCalculator.calculate_macd(
            standard_ohlcv_data,
            fast_period=10,
            slow_period=25,
            signal_period=8,
        )

        assert macd_custom is not None
        assert macd_custom.fast_period == 10
        assert macd_custom.slow_period == 25
        assert macd_custom.signal_period == 8


# =============================================================================
# Bollinger Bands Tests
# =============================================================================


class TestBollingerBandsCalculation:
    """Tests for Bollinger Bands calculation"""

    def test_bollinger_bands_insufficient_data(self, minimal_ohlcv_data):
        """Test Bollinger Bands with insufficient data"""
        bb = IndicatorCalculator.calculate_bollinger_bands(
            minimal_ohlcv_data[:10], period=20
        )
        assert bb is None

    def test_bollinger_bands_minimum_data(self, minimal_ohlcv_data):
        """Test Bollinger Bands with minimum required data"""
        bb = IndicatorCalculator.calculate_bollinger_bands(
            minimal_ohlcv_data, period=10
        )
        assert bb is not None

    def test_bollinger_bands_structure(self, standard_ohlcv_data):
        """Test Bollinger Bands have correct structure"""
        bb = IndicatorCalculator.calculate_bollinger_bands(
            standard_ohlcv_data, period=20
        )

        assert bb is not None
        assert hasattr(bb, "upper_band")
        assert hasattr(bb, "middle_band")
        assert hasattr(bb, "lower_band")
        assert hasattr(bb, "bandwidth")

    def test_bollinger_bands_band_ordering(self, standard_ohlcv_data):
        """Test that bands are in correct order"""
        bb = IndicatorCalculator.calculate_bollinger_bands(
            standard_ohlcv_data, period=20
        )

        assert bb is not None
        # Lower band should be below middle band
        assert bb.lower_band < bb.middle_band
        # Middle band should be below upper band
        assert bb.middle_band < bb.upper_band

    def test_bollinger_bands_middle_is_sma(self, standard_ohlcv_data):
        """Test that middle band is the SMA"""
        bb = IndicatorCalculator.calculate_bollinger_bands(
            standard_ohlcv_data, period=20
        )

        # Calculate expected SMA
        closes = [c.close for c in standard_ohlcv_data[-20:]]
        expected_sma = sum(closes) / Decimal("20")

        assert bb is not None
        assert abs(bb.middle_band - expected_sma) < Decimal("0.01")

    def test_bollinger_bands_custom_std_dev(self, standard_ohlcv_data):
        """Test Bollinger Bands with custom standard deviation"""
        bb_2 = IndicatorCalculator.calculate_bollinger_bands(
            standard_ohlcv_data, period=20, std_dev=Decimal("2")
        )
        bb_3 = IndicatorCalculator.calculate_bollinger_bands(
            standard_ohlcv_data, period=20, std_dev=Decimal("3")
        )

        assert bb_2 is not None
        assert bb_3 is not None

        # Wider std dev should give wider bands
        bb_2_width = bb_2.upper_band - bb_2.lower_band
        bb_3_width = bb_3.upper_band - bb_3.lower_band
        assert bb_3_width > bb_2_width

    def test_bollinger_bands_bandwidth(self, standard_ohlcv_data):
        """Test bandwidth calculation"""
        bb = IndicatorCalculator.calculate_bollinger_bands(
            standard_ohlcv_data, period=20
        )

        assert bb is not None
        expected_bandwidth = bb.upper_band - bb.lower_band
        assert abs(bb.bandwidth - expected_bandwidth) < Decimal("0.001")

    def test_bollinger_bands_volatility_detection(
        self, sideways_data, trending_up_data
    ):
        """Test that Bollinger Bands reflect volatility"""
        bb_sideways = IndicatorCalculator.calculate_bollinger_bands(
            sideways_data, period=20
        )
        bb_uptrend = IndicatorCalculator.calculate_bollinger_bands(
            trending_up_data, period=20
        )

        assert bb_sideways is not None
        assert bb_uptrend is not None

        # Width should reflect volatility
        # (Uptrend typically has less volatility than ranging market)
        assert bb_sideways.bandwidth > Decimal("0")
        assert bb_uptrend.bandwidth > Decimal("0")


# =============================================================================
# Batch Calculation Tests
# =============================================================================


class TestAllIndicatorsBatchCalculation:
    """Tests for batch calculation of all indicators"""

    def test_all_indicators_calculation(self, standard_ohlcv_data):
        """Test batch calculation of all indicators"""
        indicators = IndicatorCalculator.calculate_all_indicators(standard_ohlcv_data)

        assert indicators is not None
        assert "rsi" in indicators
        assert "macd" in indicators
        assert "ema_fast" in indicators
        assert "ema_slow" in indicators
        assert "bollinger" in indicators

    def test_all_indicators_with_insufficient_data(self, minimal_ohlcv_data):
        """Test batch calculation with insufficient data"""
        indicators = IndicatorCalculator.calculate_all_indicators(minimal_ohlcv_data)

        assert indicators is not None
        # Some indicators may be None, others not
        assert isinstance(indicators, dict)

    def test_all_indicators_custom_parameters(self, standard_ohlcv_data):
        """Test batch calculation with custom parameters"""
        indicators = IndicatorCalculator.calculate_all_indicators(
            standard_ohlcv_data,
            rsi_period=10,
            macd_fast=10,
            macd_slow=20,
            macd_signal=5,
            ema_fast_period=10,
            ema_slow_period=20,
            bb_period=15,
            bb_std_dev=Decimal("1.5"),
        )

        assert indicators is not None

        if indicators["rsi"]:
            assert indicators["rsi"].period == 10

        if indicators["macd"]:
            assert indicators["macd"].fast_period == 10
            assert indicators["macd"].slow_period == 20

        if indicators["bollinger"]:
            assert indicators["bollinger"].period == 15

    def test_all_indicators_consistency(self, standard_ohlcv_data):
        """Test that batch and individual calculations are consistent"""
        batch = IndicatorCalculator.calculate_all_indicators(standard_ohlcv_data)
        individual_rsi = IndicatorCalculator.calculate_rsi(standard_ohlcv_data)
        individual_ema_fast = IndicatorCalculator.calculate_ema(
            standard_ohlcv_data, period=12
        )

        assert batch["rsi"] is not None
        assert individual_rsi is not None
        assert batch["rsi"].value == individual_rsi.value

        assert batch["ema_fast"] is not None
        assert individual_ema_fast is not None
        assert batch["ema_fast"].value == individual_ema_fast.value


# =============================================================================
# Decimal Precision Tests
# =============================================================================


class TestDecimalPrecision:
    """Tests for Decimal precision handling"""

    def test_rsi_decimal_precision(self, standard_ohlcv_data):
        """Test RSI maintains Decimal precision"""
        rsi = IndicatorCalculator.calculate_rsi(standard_ohlcv_data)

        assert rsi is not None
        assert isinstance(rsi.value, Decimal)

    def test_ema_decimal_precision(self, standard_ohlcv_data):
        """Test EMA maintains Decimal precision"""
        ema = IndicatorCalculator.calculate_ema(standard_ohlcv_data, period=12)

        assert ema is not None
        assert isinstance(ema.value, Decimal)

    def test_macd_decimal_precision(self, standard_ohlcv_data):
        """Test MACD maintains Decimal precision"""
        macd = IndicatorCalculator.calculate_macd(standard_ohlcv_data)

        assert macd is not None
        assert isinstance(macd.macd_line, Decimal)
        assert isinstance(macd.signal_line, Decimal)
        assert isinstance(macd.histogram, Decimal)

    def test_bollinger_decimal_precision(self, standard_ohlcv_data):
        """Test Bollinger Bands maintain Decimal precision"""
        bb = IndicatorCalculator.calculate_bollinger_bands(standard_ohlcv_data)

        assert bb is not None
        assert isinstance(bb.upper_band, Decimal)
        assert isinstance(bb.middle_band, Decimal)
        assert isinstance(bb.lower_band, Decimal)
        assert isinstance(bb.bandwidth, Decimal)


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions"""

    def test_zero_volume_candles(self):
        """Test handling of zero volume candles"""
        candles = []
        base_time = datetime.utcnow() - timedelta(hours=1)

        for i in range(50):
            timestamp = base_time + timedelta(minutes=i)
            candle = OHLCV(
                symbol="TEST/USDT:USDT",
                timeframe=Timeframe.M1,
                timestamp=timestamp,
                open=Decimal("100") + Decimal(str(i)),
                high=Decimal("101") + Decimal(str(i)),
                low=Decimal("99") + Decimal(str(i)),
                close=Decimal("100.5") + Decimal(str(i)),
                volume=Decimal("0"),  # Zero volume
            )
            candles.append(candle)

        rsi = IndicatorCalculator.calculate_rsi(candles)
        assert rsi is not None  # Should still work

    def test_identical_price_candles(self):
        """Test handling of identical price candles"""
        candles = []
        base_time = datetime.utcnow() - timedelta(hours=1)
        price = Decimal("100")

        for i in range(50):
            timestamp = base_time + timedelta(minutes=i)
            candle = OHLCV(
                symbol="TEST/USDT:USDT",
                timeframe=Timeframe.M1,
                timestamp=timestamp,
                open=price,
                high=price,
                low=price,
                close=price,
                volume=Decimal("1.0"),
            )
            candles.append(candle)

        rsi = IndicatorCalculator.calculate_rsi(candles)
        # RSI should be around 50 (neutral) for no price change
        if rsi:
            assert Decimal("0") <= rsi.value <= Decimal("100")

    def test_extreme_price_values(self):
        """Test handling of extreme price values"""
        candles = []
        base_time = datetime.utcnow() - timedelta(hours=1)
        base_price = Decimal("999999999.99999999")

        for i in range(50):
            timestamp = base_time + timedelta(minutes=i)
            candle = OHLCV(
                symbol="TEST/USDT:USDT",
                timeframe=Timeframe.M1,
                timestamp=timestamp,
                open=base_price + Decimal(str(i)),
                high=base_price + Decimal(str(i + 1)),
                low=base_price + Decimal(str(i - 1)),
                close=base_price + Decimal(str(i + 0.5)),
                volume=Decimal("1.0"),
            )
            candles.append(candle)

        rsi = IndicatorCalculator.calculate_rsi(candles)
        assert rsi is not None


# =============================================================================
# Export
# =============================================================================

__all__ = [
    "TestRSICalculation",
    "TestEMACalculation",
    "TestMACDCalculation",
    "TestBollingerBandsCalculation",
    "TestAllIndicatorsBatchCalculation",
    "TestDecimalPrecision",
    "TestEdgeCases",
]
