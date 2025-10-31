"""
Technical Indicators Calculator

Calculates RSI, MACD, EMA, and Bollinger Bands from OHLCV data.
All calculations use DECIMAL precision for accuracy.

Author: Market Data Service Implementation Team
Date: 2025-10-27
"""

import logging
from decimal import Decimal
from typing import List, Optional

from .models import EMA, MACD, OHLCV, RSI, BollingerBands

logger = logging.getLogger(__name__)


class IndicatorCalculator:
    """
    Technical Indicator Calculator

    Calculates various technical indicators from OHLCV data.
    All calculations use DECIMAL precision to avoid floating point errors.

    Methods:
        calculate_rsi: Calculate Relative Strength Index
        calculate_macd: Calculate MACD indicator
        calculate_ema: Calculate Exponential Moving Average
        calculate_bollinger_bands: Calculate Bollinger Bands
    """

    @staticmethod
    def calculate_rsi(
        ohlcv_data: List[OHLCV],
        period: int = 14,
        overbought: Decimal = Decimal("70"),
        oversold: Decimal = Decimal("30"),
    ) -> Optional[RSI]:
        """
        Calculate Relative Strength Index (RSI)

        RSI = 100 - (100 / (1 + RS))
        where RS = Average Gain / Average Loss

        Args:
            ohlcv_data: List of OHLCV candles (sorted by timestamp ascending)
            period: RSI period (default: 14)
            overbought: Overbought threshold (default: 70)
            oversold: Oversold threshold (default: 30)

        Returns:
            RSI object or None if insufficient data

        Example:
            ```python
            rsi = IndicatorCalculator.calculate_rsi(candles, period=14)
            if rsi.is_oversold:
                print("RSI indicates oversold condition")
            ```
        """
        if len(ohlcv_data) < period + 1:
            logger.warning(
                f"Insufficient data for RSI calculation: {len(ohlcv_data)} < {period + 1}"
            )
            return None

        try:
            # Calculate price changes
            changes = []
            for i in range(1, len(ohlcv_data)):
                change = ohlcv_data[i].close - ohlcv_data[i - 1].close
                changes.append(change)

            # Separate gains and losses
            gains = [max(change, Decimal("0")) for change in changes]
            losses = [abs(min(change, Decimal("0"))) for change in changes]

            # Calculate initial average gain and loss (SMA for first period)
            avg_gain = sum(gains[:period]) / Decimal(str(period))
            avg_loss = sum(losses[:period]) / Decimal(str(period))

            # Calculate RSI for subsequent periods (using smoothed averages)
            for i in range(period, len(gains)):
                avg_gain = ((avg_gain * Decimal(str(period - 1))) + gains[i]) / Decimal(
                    str(period)
                )
                avg_loss = (
                    (avg_loss * Decimal(str(period - 1))) + losses[i]
                ) / Decimal(str(period))

            # Calculate RS and RSI
            if avg_loss == 0:
                rsi_value = Decimal("100")
            else:
                rs = avg_gain / avg_loss
                rsi_value = Decimal("100") - (Decimal("100") / (Decimal("1") + rs))

            # Quantize to 2 decimal places for RSI model constraint
            rsi_value = rsi_value.quantize(Decimal("0.01"))

            # Get latest candle info
            latest = ohlcv_data[-1]

            return RSI(
                symbol=latest.symbol,
                timeframe=latest.timeframe,
                timestamp=latest.timestamp,
                value=rsi_value,
                period=period,
                overbought_level=overbought,
                oversold_level=oversold,
            )

        except Exception as e:
            logger.error(f"Error calculating RSI: {e}", exc_info=True)
            return None

    @staticmethod
    def _calculate_ema_unquantized(
        ohlcv_data: List[OHLCV],
        period: int,
    ) -> Optional[Decimal]:
        """
        Internal method to calculate EMA without quantizing (for use in MACD).
        Returns only the Decimal value, not an EMA object.
        """
        if len(ohlcv_data) < period:
            return None

        try:
            # Calculate SMA for initial EMA value
            sma = sum(candle.close for candle in ohlcv_data[:period]) / Decimal(
                str(period)
            )
            ema = sma

            # Calculate multiplier
            multiplier = Decimal("2") / Decimal(str(period + 1))

            # Calculate EMA for remaining periods
            for i in range(period, len(ohlcv_data)):
                close = ohlcv_data[i].close
                ema = (close - ema) * multiplier + ema

            return ema

        except Exception as e:
            logger.error(f"Error calculating EMA: {e}", exc_info=True)
            return None

    @staticmethod
    def calculate_ema(
        ohlcv_data: List[OHLCV],
        period: int,
    ) -> Optional[EMA]:
        """
        Calculate Exponential Moving Average (EMA)

        EMA = (Close - EMA_prev) * multiplier + EMA_prev
        where multiplier = 2 / (period + 1)

        Args:
            ohlcv_data: List of OHLCV candles (sorted by timestamp ascending)
            period: EMA period

        Returns:
            EMA object or None if insufficient data

        Example:
            ```python
            ema_12 = IndicatorCalculator.calculate_ema(candles, period=12)
            ema_26 = IndicatorCalculator.calculate_ema(candles, period=26)
            if ema_12.value > ema_26.value:
                print("Fast EMA above slow EMA - bullish")
            ```
        """
        if len(ohlcv_data) < period:
            logger.warning(
                f"Insufficient data for EMA calculation: {len(ohlcv_data)} < {period}"
            )
            return None

        try:
            # Calculate SMA for initial EMA value
            sma = sum(candle.close for candle in ohlcv_data[:period]) / Decimal(
                str(period)
            )
            ema = sma

            # Calculate multiplier
            multiplier = Decimal("2") / Decimal(str(period + 1))

            # Calculate EMA for remaining periods
            for i in range(period, len(ohlcv_data)):
                close = ohlcv_data[i].close
                ema = (close - ema) * multiplier + ema

            # Quantize to 8 decimal places for consistency with exchange precision
            ema = ema.quantize(Decimal("0.00000001"))

            # Get latest candle info
            latest = ohlcv_data[-1]

            return EMA(
                symbol=latest.symbol,
                timeframe=latest.timeframe,
                timestamp=latest.timestamp,
                value=ema,
                period=period,
            )

        except Exception as e:
            logger.error(f"Error calculating EMA: {e}", exc_info=True)
            return None

    @staticmethod
    def calculate_macd(
        ohlcv_data: List[OHLCV],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> Optional[MACD]:
        """
        Calculate MACD (Moving Average Convergence Divergence)

        MACD Line = EMA(12) - EMA(26)
        Signal Line = EMA(9) of MACD Line
        Histogram = MACD Line - Signal Line

        Args:
            ohlcv_data: List of OHLCV candles (sorted by timestamp ascending)
            fast_period: Fast EMA period (default: 12)
            slow_period: Slow EMA period (default: 26)
            signal_period: Signal line period (default: 9)

        Returns:
            MACD object or None if insufficient data

        Example:
            ```python
            macd = IndicatorCalculator.calculate_macd(candles)
            if macd.histogram > 0:
                print("MACD histogram positive - bullish momentum")
            ```
        """
        min_data_points = slow_period + signal_period
        if len(ohlcv_data) < min_data_points:
            logger.warning(
                f"Insufficient data for MACD calculation: {len(ohlcv_data)} < {min_data_points}"
            )
            return None

        try:
            # Calculate fast and slow EMAs (unquantized to preserve precision for histogram)
            fast_ema_value = IndicatorCalculator._calculate_ema_unquantized(
                ohlcv_data, fast_period
            )
            slow_ema_value = IndicatorCalculator._calculate_ema_unquantized(
                ohlcv_data, slow_period
            )

            if not fast_ema_value or not slow_ema_value:
                return None

            # Calculate MACD line (fast - slow) with full precision
            macd_line = fast_ema_value - slow_ema_value

            # Calculate MACD line history for signal line calculation
            macd_values = []
            for i in range(slow_period, len(ohlcv_data)):
                subset = ohlcv_data[: i + 1]
                fast = IndicatorCalculator._calculate_ema_unquantized(
                    subset, fast_period
                )
                slow = IndicatorCalculator._calculate_ema_unquantized(
                    subset, slow_period
                )
                if fast and slow:
                    macd_values.append(fast - slow)

            # Need enough MACD values for signal line
            if len(macd_values) < signal_period:
                return None

            # Calculate signal line (EMA of MACD line)
            sma = sum(macd_values[:signal_period]) / Decimal(str(signal_period))
            signal_line = sma
            multiplier = Decimal("2") / Decimal(str(signal_period + 1))

            for i in range(signal_period, len(macd_values)):
                signal_line = (macd_values[i] - signal_line) * multiplier + signal_line

            # Calculate histogram
            histogram = macd_line - signal_line

            # Quantize to 8 decimal places for consistency with exchange precision
            macd_line = macd_line.quantize(Decimal("0.00000001"))
            signal_line = signal_line.quantize(Decimal("0.00000001"))
            histogram = histogram.quantize(Decimal("0.00000001"))

            # Get latest candle info
            latest = ohlcv_data[-1]

            return MACD(
                symbol=latest.symbol,
                timeframe=latest.timeframe,
                timestamp=latest.timestamp,
                macd_line=macd_line,
                signal_line=signal_line,
                histogram=histogram,
                fast_period=fast_period,
                slow_period=slow_period,
                signal_period=signal_period,
            )

        except Exception as e:
            logger.error(f"Error calculating MACD: {e}", exc_info=True)
            return None

    @staticmethod
    def calculate_bollinger_bands(
        ohlcv_data: List[OHLCV],
        period: int = 20,
        std_dev: Decimal = Decimal("2"),
    ) -> Optional[BollingerBands]:
        """
        Calculate Bollinger Bands

        Middle Band = SMA(period)
        Upper Band = Middle Band + (std_dev * standard deviation)
        Lower Band = Middle Band - (std_dev * standard deviation)

        Args:
            ohlcv_data: List of OHLCV candles (sorted by timestamp ascending)
            period: SMA period (default: 20)
            std_dev: Standard deviation multiplier (default: 2)

        Returns:
            BollingerBands object or None if insufficient data

        Example:
            ```python
            bb = IndicatorCalculator.calculate_bollinger_bands(candles)
            position = bb.get_position_relative_to_bands(current_price)
            if position == "below":
                print("Price below lower band - potential buy signal")
            ```
        """
        if len(ohlcv_data) < period:
            logger.warning(
                f"Insufficient data for Bollinger Bands: {len(ohlcv_data)} < {period}"
            )
            return None

        try:
            # Get closing prices for calculation
            closes = [candle.close for candle in ohlcv_data[-period:]]

            # Calculate middle band (SMA)
            middle_band = sum(closes) / Decimal(str(period))

            # Calculate standard deviation
            variance = sum((close - middle_band) ** 2 for close in closes) / Decimal(
                str(period)
            )
            std = variance.sqrt()

            # Calculate upper and lower bands
            upper_band = middle_band + (std_dev * std)
            lower_band = middle_band - (std_dev * std)

            # Calculate bandwidth
            bandwidth = upper_band - lower_band

            # Quantize to 8 decimal places for consistency with exchange precision
            upper_band = upper_band.quantize(Decimal("0.00000001"))
            middle_band = middle_band.quantize(Decimal("0.00000001"))
            lower_band = lower_band.quantize(Decimal("0.00000001"))
            bandwidth = bandwidth.quantize(Decimal("0.00000001"))

            # Get latest candle info
            latest = ohlcv_data[-1]

            return BollingerBands(
                symbol=latest.symbol,
                timeframe=latest.timeframe,
                timestamp=latest.timestamp,
                upper_band=upper_band,
                middle_band=middle_band,
                lower_band=lower_band,
                bandwidth=bandwidth,
                period=period,
                std_dev=std_dev,
            )

        except Exception as e:
            logger.error(f"Error calculating Bollinger Bands: {e}", exc_info=True)
            return None

    @staticmethod
    def calculate_all_indicators(
        ohlcv_data: List[OHLCV],
        rsi_period: int = 14,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        ema_fast_period: int = 12,
        ema_slow_period: int = 26,
        bb_period: int = 20,
        bb_std_dev: Decimal = Decimal("2"),
    ) -> dict:
        """
        Calculate all technical indicators at once

        Args:
            ohlcv_data: List of OHLCV candles
            rsi_period: RSI period
            macd_fast: MACD fast period
            macd_slow: MACD slow period
            macd_signal: MACD signal period
            ema_fast_period: Fast EMA period
            ema_slow_period: Slow EMA period
            bb_period: Bollinger Bands period
            bb_std_dev: Bollinger Bands standard deviation

        Returns:
            Dictionary with all calculated indicators

        Example:
            ```python
            indicators = IndicatorCalculator.calculate_all_indicators(candles)
            rsi = indicators['rsi']
            macd = indicators['macd']
            ema_fast = indicators['ema_fast']
            ```
        """
        return {
            "rsi": IndicatorCalculator.calculate_rsi(ohlcv_data, rsi_period),
            "macd": IndicatorCalculator.calculate_macd(
                ohlcv_data, macd_fast, macd_slow, macd_signal
            ),
            "ema_fast": IndicatorCalculator.calculate_ema(ohlcv_data, ema_fast_period),
            "ema_slow": IndicatorCalculator.calculate_ema(ohlcv_data, ema_slow_period),
            "bollinger": IndicatorCalculator.calculate_bollinger_bands(
                ohlcv_data, bb_period, bb_std_dev
            ),
        }


# Export
__all__ = ["IndicatorCalculator"]
