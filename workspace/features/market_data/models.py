"""
Market Data Models

Defines data models for OHLCV data, tickers, and technical indicators.
All price values use DECIMAL precision for accuracy.

Author: Market Data Service Implementation Team
Date: 2025-10-27
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, validator


class Timeframe(str, Enum):
    """Supported timeframes for OHLCV data"""

    M1 = "1m"  # 1 minute
    M3 = "3m"  # 3 minutes (our trading interval)
    M5 = "5m"  # 5 minutes
    M15 = "15m"  # 15 minutes
    M30 = "30m"  # 30 minutes
    H1 = "1h"  # 1 hour
    H4 = "4h"  # 4 hours
    D1 = "1d"  # 1 day


class OHLCV(BaseModel):
    """
    OHLCV (Open, High, Low, Close, Volume) candlestick data

    Attributes:
        symbol: Trading pair (e.g., 'BTC/USDT:USDT')
        timeframe: Candle timeframe
        timestamp: Candle open timestamp
        open: Open price
        high: High price
        low: Low price
        close: Close price
        volume: Trading volume in base currency
        quote_volume: Trading volume in quote currency (USDT)
        trades_count: Number of trades in this candle
    """

    symbol: str = Field(..., min_length=1)
    timeframe: Timeframe
    timestamp: datetime
    open: Decimal = Field(..., decimal_places=8)
    high: Decimal = Field(..., decimal_places=8)
    low: Decimal = Field(..., decimal_places=8)
    close: Decimal = Field(..., decimal_places=8)
    volume: Decimal = Field(..., decimal_places=8, ge=0)
    quote_volume: Optional[Decimal] = Field(default=None, decimal_places=8, ge=0)
    trades_count: Optional[int] = Field(default=None, ge=0)

    class Config:
        use_enum_values = True
        json_encoders = {Decimal: lambda v: str(v), datetime: lambda v: v.isoformat()}

    @property
    def price_change(self) -> Decimal:
        """Calculate price change (close - open)"""
        return self.close - self.open

    @property
    def price_change_pct(self) -> Decimal:
        """Calculate price change percentage"""
        if self.open == 0:
            return Decimal("0")
        return (self.price_change / self.open) * Decimal("100")

    @property
    def body_size(self) -> Decimal:
        """Calculate candle body size (absolute close - open)"""
        return abs(self.close - self.open)

    @property
    def range_size(self) -> Decimal:
        """Calculate candle range (high - low)"""
        return self.high - self.low

    @property
    def upper_wick(self) -> Decimal:
        """Calculate upper wick size"""
        return self.high - max(self.open, self.close)

    @property
    def lower_wick(self) -> Decimal:
        """Calculate lower wick size"""
        return min(self.open, self.close) - self.low

    @property
    def is_bullish(self) -> bool:
        """Check if candle is bullish (close > open)"""
        return self.close > self.open

    @property
    def is_bearish(self) -> bool:
        """Check if candle is bearish (close < open)"""
        return self.close < self.open


class Ticker(BaseModel):
    """
    Real-time ticker data

    Attributes:
        symbol: Trading pair
        timestamp: Ticker timestamp
        bid: Best bid price
        ask: Best ask price
        last: Last traded price
        high_24h: 24-hour high
        low_24h: 24-hour low
        volume_24h: 24-hour volume in base currency
        quote_volume_24h: 24-hour volume in quote currency (USDT)
        change_24h: 24-hour price change
        change_24h_pct: 24-hour price change percentage
    """

    symbol: str = Field(..., min_length=1)
    timestamp: datetime
    bid: Decimal = Field(..., decimal_places=8)
    ask: Decimal = Field(..., decimal_places=8)
    last: Decimal = Field(..., decimal_places=8)
    high_24h: Decimal = Field(..., decimal_places=8)
    low_24h: Decimal = Field(..., decimal_places=8)
    volume_24h: Decimal = Field(..., decimal_places=8, ge=0)
    quote_volume_24h: Decimal = Field(..., decimal_places=8, ge=0)
    change_24h: Decimal = Field(..., decimal_places=8)
    change_24h_pct: Decimal = Field(..., decimal_places=4)

    class Config:
        json_encoders = {Decimal: lambda v: str(v), datetime: lambda v: v.isoformat()}

    @property
    def spread(self) -> Decimal:
        """Calculate bid-ask spread"""
        return self.ask - self.bid

    @property
    def spread_pct(self) -> Decimal:
        """Calculate bid-ask spread percentage"""
        if self.bid == 0:
            return Decimal("0")
        return (self.spread / self.bid) * Decimal("100")

    @property
    def mid_price(self) -> Decimal:
        """Calculate mid price (average of bid and ask)"""
        return (self.bid + self.ask) / Decimal("2")


class RSI(BaseModel):
    """
    Relative Strength Index indicator

    Attributes:
        symbol: Trading pair
        timeframe: Indicator timeframe
        timestamp: Calculation timestamp
        value: RSI value (0-100)
        period: RSI period (typically 14)
        overbought_level: Overbought threshold (typically 70)
        oversold_level: Oversold threshold (typically 30)
    """

    symbol: str
    timeframe: Timeframe
    timestamp: datetime
    value: Decimal = Field(..., decimal_places=2, ge=0, le=100)
    period: int = Field(default=14, ge=1)
    overbought_level: Decimal = Field(default=Decimal("70"), ge=0, le=100)
    oversold_level: Decimal = Field(default=Decimal("30"), ge=0, le=100)

    class Config:
        use_enum_values = True
        json_encoders = {Decimal: lambda v: str(v), datetime: lambda v: v.isoformat()}

    @property
    def is_overbought(self) -> bool:
        """Check if RSI indicates overbought condition"""
        return self.value >= self.overbought_level

    @property
    def is_oversold(self) -> bool:
        """Check if RSI indicates oversold condition"""
        return self.value <= self.oversold_level

    @property
    def signal(self) -> str:
        """Generate trading signal based on RSI"""
        if self.is_oversold:
            return "buy"
        elif self.is_overbought:
            return "sell"
        else:
            return "neutral"


class MACD(BaseModel):
    """
    Moving Average Convergence Divergence indicator

    Attributes:
        symbol: Trading pair
        timeframe: Indicator timeframe
        timestamp: Calculation timestamp
        macd_line: MACD line value (fast EMA - slow EMA)
        signal_line: Signal line value (EMA of MACD line)
        histogram: MACD histogram (MACD line - signal line)
        fast_period: Fast EMA period (typically 12)
        slow_period: Slow EMA period (typically 26)
        signal_period: Signal line period (typically 9)
    """

    symbol: str
    timeframe: Timeframe
    timestamp: datetime
    macd_line: Decimal = Field(..., decimal_places=8)
    signal_line: Decimal = Field(..., decimal_places=8)
    histogram: Decimal = Field(..., decimal_places=8)
    fast_period: int = Field(default=12, ge=1)
    slow_period: int = Field(default=26, ge=1)
    signal_period: int = Field(default=9, ge=1)

    class Config:
        use_enum_values = True
        json_encoders = {Decimal: lambda v: str(v), datetime: lambda v: v.isoformat()}

    @property
    def value(self) -> Decimal:
        """Return the MACD line value (main value)"""
        return self.macd_line

    @property
    def is_bullish(self) -> bool:
        """Check if MACD is in bullish state"""
        return self.macd_line > self.signal_line and self.histogram > 0

    @property
    def is_bullish_crossover(self) -> bool:
        """Check if MACD line crossed above signal line (bullish)"""
        # Would need previous values to detect crossover
        return self.macd_line > self.signal_line and self.histogram > 0

    @property
    def is_bearish_crossover(self) -> bool:
        """Check if MACD line crossed below signal line (bearish)"""
        return self.macd_line < self.signal_line and self.histogram < 0

    @property
    def signal(self) -> str:
        """Generate trading signal based on MACD"""
        if self.histogram > 0 and self.macd_line > self.signal_line:
            return "buy"
        elif self.histogram < 0 and self.macd_line < self.signal_line:
            return "sell"
        else:
            return "neutral"


class EMA(BaseModel):
    """
    Exponential Moving Average

    Attributes:
        symbol: Trading pair
        timeframe: Indicator timeframe
        timestamp: Calculation timestamp
        value: EMA value
        period: EMA period
    """

    symbol: str
    timeframe: Timeframe
    timestamp: datetime
    value: Decimal = Field(..., decimal_places=8)
    period: int = Field(..., ge=1)

    class Config:
        use_enum_values = True
        json_encoders = {Decimal: lambda v: str(v), datetime: lambda v: v.isoformat()}


class BollingerBands(BaseModel):
    """
    Bollinger Bands indicator

    Attributes:
        symbol: Trading pair
        timeframe: Indicator timeframe
        timestamp: Calculation timestamp
        upper_band: Upper Bollinger Band
        middle_band: Middle band (SMA)
        lower_band: Lower Bollinger Band
        bandwidth: Band width (upper - lower)
        period: SMA period (typically 20)
        std_dev: Standard deviation multiplier (typically 2)
    """

    symbol: str
    timeframe: Timeframe
    timestamp: datetime
    upper_band: Decimal = Field(..., decimal_places=8)
    middle_band: Decimal = Field(..., decimal_places=8)
    lower_band: Decimal = Field(..., decimal_places=8)
    bandwidth: Decimal = Field(..., decimal_places=8, ge=0)
    period: int = Field(default=20, ge=1)
    std_dev: Decimal = Field(default=Decimal("2"), ge=0)

    class Config:
        use_enum_values = True
        json_encoders = {Decimal: lambda v: str(v), datetime: lambda v: v.isoformat()}

    @property
    def upper(self) -> Decimal:
        """Alias for upper_band"""
        return self.upper_band

    @property
    def middle(self) -> Decimal:
        """Alias for middle_band"""
        return self.middle_band

    @property
    def lower(self) -> Decimal:
        """Alias for lower_band"""
        return self.lower_band

    @validator("bandwidth", always=True)
    def calculate_bandwidth(cls, v, values):
        """Calculate bandwidth if not provided"""
        if "upper_band" in values and "lower_band" in values:
            return values["upper_band"] - values["lower_band"]
        return v

    def get_position_relative_to_bands(self, current_price: Decimal) -> str:
        """
        Determine price position relative to bands

        Returns: 'above', 'upper', 'middle', 'lower', 'below'
        """
        if current_price > self.upper_band:
            return "above"
        elif current_price >= self.middle_band:
            return "upper"
        elif current_price >= self.lower_band:
            return "lower"
        else:
            return "below"

    @property
    def is_squeeze(self) -> bool:
        """Check if bands are in squeeze (narrow bandwidth)"""
        # Bandwidth less than 10% of middle band indicates squeeze
        threshold = self.middle_band * Decimal("0.10")
        return self.bandwidth < threshold


class MarketDataSnapshot(BaseModel):
    """
    Complete market data snapshot for a symbol

    Combines OHLCV, ticker, and all technical indicators
    for a single point in time.

    Attributes:
        symbol: Trading pair
        timeframe: Data timeframe
        timestamp: Snapshot timestamp
        ohlcv: OHLCV data
        ticker: Real-time ticker
        rsi: RSI indicator (optional)
        macd: MACD indicator (optional)
        ema_fast: Fast EMA (optional)
        ema_slow: Slow EMA (optional)
        bollinger: Bollinger Bands (optional)
        additional_data: Any additional indicator data
    """

    symbol: str
    timeframe: Timeframe
    timestamp: datetime
    ohlcv: OHLCV
    ticker: Ticker
    rsi: Optional[RSI] = None
    macd: Optional[MACD] = None
    ema_fast: Optional[EMA] = None
    ema_slow: Optional[EMA] = None
    bollinger: Optional[BollingerBands] = None
    additional_data: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True
        json_encoders = {Decimal: lambda v: str(v), datetime: lambda v: v.isoformat()}

    @property
    def has_all_indicators(self) -> bool:
        """Check if all core indicators are present"""
        return all(
            [
                self.rsi is not None,
                self.macd is not None,
                self.ema_fast is not None,
                self.ema_slow is not None,
                self.bollinger is not None,
            ]
        )

    def to_llm_prompt_data(self) -> Dict[str, Any]:
        """
        Format data for LLM prompt

        Returns minimal, relevant data for decision-making
        """
        data = {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "price": str(self.ticker.last),
            "change_24h_pct": str(self.ticker.change_24h_pct),
            "volume_24h": str(self.ticker.volume_24h),
            "candle": {
                "open": str(self.ohlcv.open),
                "high": str(self.ohlcv.high),
                "low": str(self.ohlcv.low),
                "close": str(self.ohlcv.close),
                "is_bullish": self.ohlcv.is_bullish,
            },
        }

        if self.rsi:
            data["rsi"] = {
                "value": str(self.rsi.value),
                "signal": self.rsi.signal,
            }

        if self.macd:
            data["macd"] = {
                "histogram": str(self.macd.histogram),
                "signal": self.macd.signal,
            }

        if self.ema_fast and self.ema_slow:
            data["ema_cross"] = (
                "bullish" if self.ema_fast.value > self.ema_slow.value else "bearish"
            )

        if self.bollinger:
            data["bollinger"] = {
                "position": self.bollinger.get_position_relative_to_bands(
                    self.ticker.last
                ),
                "is_squeeze": self.bollinger.is_squeeze,
            }

        return data


class WebSocketMessage(BaseModel):
    """
    WebSocket message wrapper

    Attributes:
        channel: WebSocket channel (ticker, candle, trade)
        symbol: Trading pair
        data: Message payload
        timestamp: Message timestamp
    """

    channel: str
    symbol: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# Export all models
__all__ = [
    "Timeframe",
    "OHLCV",
    "Ticker",
    "RSI",
    "MACD",
    "EMA",
    "BollingerBands",
    "MarketDataSnapshot",
    "WebSocketMessage",
]
