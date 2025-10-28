# API Contract: Market Data Service

**Document Version**: 1.0
**Date**: 2025-10-27
**Phase**: P2 - Architecture Design
**Integration Architect**: Claude Integration Architect Agent
**Status**: Final for Review

---

## Overview

The Market Data Service provides real-time and historical cryptocurrency market data with calculated technical indicators. Primary data source is Bybit WebSocket with REST API fallback.

**Base URL**: Internal service (not exposed externally)
**Protocol**: Async Python API (function calls)
**Data Format**: Python dictionaries, pandas DataFrames

---

## Service Interface

### Class: MarketDataService

```python
from typing import List, Dict, Optional
import pandas as pd
from datetime import datetime

class MarketDataService:
    """Market Data Service for cryptocurrency data acquisition and processing"""

    async def fetch_real_time_data(
        self,
        symbols: List[str]
    ) -> Dict[str, MarketData]:
        """
        Fetch real-time market data for multiple symbols

        Args:
            symbols: List of trading symbols (e.g., ['BTC/USDT', 'ETH/USDT'])

        Returns:
            Dictionary mapping symbol to MarketData object

        Raises:
            DataFetchError: If unable to fetch data after retries
            ValidationError: If data fails quality checks
        """
        pass

    async def get_historical_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 100
    ) -> pd.DataFrame:
        """
        Get historical OHLCV data

        Args:
            symbol: Trading symbol (e.g., 'BTC/USDT')
            timeframe: Timeframe ('1m', '3m', '5m', '15m', '1h', '4h', '1d')
            limit: Number of candles to fetch (default: 100, max: 1000)

        Returns:
            DataFrame with columns: [timestamp, open, high, low, close, volume]

        Raises:
            ValueError: If invalid timeframe or limit
            DataFetchError: If fetch fails
        """
        pass

    async def calculate_indicators(
        self,
        ohlcv: pd.DataFrame
    ) -> Dict[str, float]:
        """
        Calculate technical indicators from OHLCV data

        Args:
            ohlcv: DataFrame with OHLCV data

        Returns:
            Dictionary of indicator values (current/latest values)

        Raises:
            InsufficientDataError: If not enough data for indicators
        """
        pass

    async def validate_data_quality(
        self,
        data: MarketData
    ) -> bool:
        """
        Validate data quality and freshness

        Args:
            data: MarketData object to validate

        Returns:
            True if data is valid, False otherwise
        """
        pass
```

---

## Data Models

### MarketData

**Purpose**: Real-time market data snapshot with indicators

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class MarketData(BaseModel):
    """Real-time market data with technical indicators"""

    # Symbol Identification
    symbol: str = Field(..., regex=r'^[A-Z]{3,10}/[A-Z]{3,10}$')
    exchange: str = Field(default='bybit')

    # Price Data
    timestamp: datetime
    price: float = Field(..., gt=0)
    bid: float = Field(..., gt=0)
    ask: float = Field(..., gt=0)
    spread: float = Field(..., ge=0)

    # Volume
    volume_24h: float = Field(..., ge=0)
    quote_volume_24h: float = Field(..., ge=0)

    # OHLCV (current candle)
    open: float = Field(..., gt=0)
    high: float = Field(..., gt=0)
    low: float = Field(..., gt=0)
    close: float = Field(..., gt=0)
    volume: float = Field(..., ge=0)

    # Technical Indicators
    ema_9: Optional[float] = None
    ema_20: Optional[float] = None
    ema_50: Optional[float] = None
    rsi_7: Optional[float] = Field(None, ge=0, le=100)
    rsi_14: Optional[float] = Field(None, ge=0, le=100)
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_hist: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None

    # Data Quality
    data_source: str = Field(default='websocket')  # 'websocket' or 'rest'
    staleness_seconds: float = Field(default=0, ge=0)
    quality_score: float = Field(default=1.0, ge=0, le=1.0)

    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "BTC/USDT",
                "exchange": "bybit",
                "timestamp": "2025-10-27T10:30:00Z",
                "price": 50000.00,
                "bid": 49999.50,
                "ask": 50000.50,
                "spread": 1.00,
                "volume_24h": 15000.5,
                "quote_volume_24h": 750000000.0,
                "open": 49900.00,
                "high": 50100.00,
                "low": 49850.00,
                "close": 50000.00,
                "volume": 250.5,
                "ema_9": 49950.00,
                "ema_20": 49800.00,
                "ema_50": 49500.00,
                "rsi_7": 65.5,
                "rsi_14": 58.2,
                "macd": 150.5,
                "macd_signal": 120.3,
                "macd_hist": 30.2,
                "bb_upper": 51000.00,
                "bb_middle": 50000.00,
                "bb_lower": 49000.00,
                "data_source": "websocket",
                "staleness_seconds": 0.5,
                "quality_score": 1.0
            }
        }
```

### Indicators

**Purpose**: Technical indicator values

```python
class Indicators(BaseModel):
    """Technical indicators calculated from OHLCV data"""

    # Moving Averages
    ema_9: float
    ema_20: float
    ema_50: float

    # Momentum Indicators
    rsi_7: float = Field(..., ge=0, le=100)
    rsi_14: float = Field(..., ge=0, le=100)

    # Trend Indicators
    macd: float
    macd_signal: float
    macd_hist: float

    # Volatility Indicators
    bb_upper: float
    bb_middle: float
    bb_lower: float

    # Volume Indicators
    volume_ratio: float = Field(..., ge=0)  # Current volume / average volume

    # Metadata
    calculated_at: datetime
    candles_used: int = Field(..., ge=0)
```

---

## WebSocket Integration

### WebSocket Subscriptions

**Bybit WebSocket URL**: `wss://stream.bybit.com/v5/public/linear`

**Subscription Message**:
```json
{
  "op": "subscribe",
  "args": [
    "kline.3.BTCUSDT",
    "kline.3.ETHUSDT",
    "kline.3.SOLUSDT",
    "kline.3.BNBUSDT",
    "kline.3.ADAUSDT",
    "kline.3.DOGEUSDT",
    "tickers.BTCUSDT",
    "tickers.ETHUSDT",
    "tickers.SOLUSDT",
    "tickers.BNBUSDT",
    "tickers.ADAUSDT",
    "tickers.DOGEUSDT"
  ]
}
```

**Kline Event** (3-minute candles):
```json
{
  "topic": "kline.3.BTCUSDT",
  "type": "snapshot",
  "ts": 1698765432000,
  "data": [{
    "start": 1698765000000,
    "end": 1698765180000,
    "interval": "3",
    "open": "49900.50",
    "close": "50000.00",
    "high": "50100.00",
    "low": "49850.00",
    "volume": "250.5",
    "turnover": "12500000.00",
    "confirm": false
  }]
}
```

**Ticker Event**:
```json
{
  "topic": "tickers.BTCUSDT",
  "type": "snapshot",
  "ts": 1698765432000,
  "data": {
    "symbol": "BTCUSDT",
    "lastPrice": "50000.00",
    "bidPrice": "49999.50",
    "askPrice": "50000.50",
    "volume24h": "15000.5",
    "turnover24h": "750000000.00"
  }
}
```

---

### WebSocket Connection Management

**Connection Class**:
```python
class ResilientWebSocket:
    """Resilient WebSocket with automatic reconnection"""

    def __init__(
        self,
        url: str,
        symbols: List[str],
        max_staleness: int = 30
    ):
        """
        Initialize WebSocket connection

        Args:
            url: WebSocket URL
            symbols: List of symbols to subscribe
            max_staleness: Maximum seconds without message before reconnect
        """
        self.url = url
        self.symbols = symbols
        self.max_staleness = max_staleness
        self.last_message_time: Optional[datetime] = None
        self.connection = None

    async def connect(self) -> None:
        """Establish WebSocket connection with retry"""
        pass

    async def subscribe(self, symbols: List[str]) -> None:
        """Subscribe to market data streams"""
        pass

    async def monitor_connection(self) -> None:
        """Background task to monitor connection health"""
        pass

    async def reconnect(self) -> None:
        """Reconnect WebSocket with exponential backoff"""
        pass

    async def on_message(self, message: str) -> None:
        """Handle incoming WebSocket message"""
        pass

    async def close(self) -> None:
        """Close WebSocket connection gracefully"""
        pass
```

---

## REST API Fallback

### Bybit REST API Endpoints

**Base URL**: `https://api.bybit.com`

**Get Kline Data**:
```http
GET /v5/market/kline
```

**Query Parameters**:
```
symbol: BTCUSDT (required)
interval: 3 (required - 3-minute candles)
limit: 200 (optional, default 200, max 1000)
start: 1698765000000 (optional, unix timestamp in ms)
end: 1698765180000 (optional, unix timestamp in ms)
```

**Response**:
```json
{
  "retCode": 0,
  "retMsg": "OK",
  "result": {
    "category": "linear",
    "symbol": "BTCUSDT",
    "list": [
      [
        "1698765000000",  // start time
        "49900.50",       // open
        "50100.00",       // high
        "49850.00",       // low
        "50000.00",       // close
        "250.5",          // volume
        "12500000.00"     // turnover
      ]
    ]
  },
  "time": 1698765432000
}
```

**Get Ticker Data**:
```http
GET /v5/market/tickers
```

**Query Parameters**:
```
category: linear (required)
symbol: BTCUSDT (optional, if omitted returns all)
```

**Response**:
```json
{
  "retCode": 0,
  "retMsg": "OK",
  "result": {
    "category": "linear",
    "list": [{
      "symbol": "BTCUSDT",
      "lastPrice": "50000.00",
      "bidPrice": "49999.50",
      "askPrice": "50000.50",
      "volume24h": "15000.5",
      "turnover24h": "750000000.00",
      "price24hPcnt": "0.0050"
    }]
  },
  "time": 1698765432000
}
```

---

## Indicator Calculation Specifications

### Moving Averages

**EMA (Exponential Moving Average)**:
```python
# EMA calculation using pandas-ta
import pandas_ta as ta

# EMA with 9, 20, 50 periods
df['ema_9'] = ta.ema(df['close'], length=9)
df['ema_20'] = ta.ema(df['close'], length=20)
df['ema_50'] = ta.ema(df['close'], length=50)
```

**Requirements**:
- Minimum data points: `max(periods) + 10` (e.g., 60 candles for EMA50)
- NaN handling: Drop or forward-fill initial NaN values

---

### Momentum Indicators

**RSI (Relative Strength Index)**:
```python
# RSI with 7 and 14 periods
df['rsi_7'] = ta.rsi(df['close'], length=7)
df['rsi_14'] = ta.rsi(df['close'], length=14)
```

**Interpretation**:
- `0-30`: Oversold
- `30-70`: Neutral
- `70-100`: Overbought

---

### Trend Indicators

**MACD (Moving Average Convergence Divergence)**:
```python
# MACD with standard parameters (12, 26, 9)
macd_result = ta.macd(df['close'], fast=12, slow=26, signal=9)
df['macd'] = macd_result['MACD_12_26_9']
df['macd_signal'] = macd_result['MACDs_12_26_9']
df['macd_hist'] = macd_result['MACDh_12_26_9']
```

**Interpretation**:
- `macd > macd_signal`: Bullish crossover
- `macd < macd_signal`: Bearish crossover
- `macd_hist > 0`: Increasing momentum

---

### Volatility Indicators

**Bollinger Bands**:
```python
# Bollinger Bands with 20 period, 2 standard deviations
bb_result = ta.bbands(df['close'], length=20, std=2)
df['bb_upper'] = bb_result['BBU_20_2.0']
df['bb_middle'] = bb_result['BBM_20_2.0']
df['bb_lower'] = bb_result['BBL_20_2.0']
```

**Interpretation**:
- Price near upper band: Overbought
- Price near lower band: Oversold
- Band width: Volatility indicator

---

## Error Handling

### Error Types

```python
class DataFetchError(Exception):
    """Raised when unable to fetch market data"""
    pass

class ValidationError(Exception):
    """Raised when data fails quality checks"""
    pass

class InsufficientDataError(Exception):
    """Raised when not enough data for indicators"""
    pass

class StaleDataError(Exception):
    """Raised when data is too old"""
    pass
```

### Error Responses

**DataFetchError**:
```python
{
    "error": "DataFetchError",
    "message": "Failed to fetch market data after 3 retries",
    "details": {
        "symbols": ["BTC/USDT", "ETH/USDT"],
        "last_error": "WebSocket connection timeout",
        "timestamp": "2025-10-27T10:30:00Z"
    }
}
```

**ValidationError**:
```python
{
    "error": "ValidationError",
    "message": "Market data failed quality checks",
    "details": {
        "symbol": "BTC/USDT",
        "failed_checks": ["price_sanity", "timestamp_freshness"],
        "staleness_seconds": 45.5
    }
}
```

**InsufficientDataError**:
```python
{
    "error": "InsufficientDataError",
    "message": "Not enough historical data for indicators",
    "details": {
        "symbol": "BTC/USDT",
        "required_candles": 60,
        "available_candles": 30
    }
}
```

---

## Caching Strategy

### Redis Cache

**Cache Keys**:
```
market_data:{symbol}:latest
market_data:{symbol}:ohlcv:{timeframe}
market_data:{symbol}:indicators
```

**Cache TTL**:
- `latest`: 5 seconds (real-time data)
- `ohlcv`: 300 seconds (5 minutes)
- `indicators`: 180 seconds (3 minutes)

**Cache Structure**:
```json
{
  "symbol": "BTC/USDT",
  "timestamp": "2025-10-27T10:30:00Z",
  "price": 50000.00,
  "indicators": {
    "ema_20": 49800.00,
    "rsi_14": 58.2,
    "macd": 150.5
  },
  "cached_at": "2025-10-27T10:30:05Z"
}
```

---

## Performance Specifications

### Latency Targets

| Operation | Target | Typical |
|-----------|--------|---------|
| **WebSocket Data** | <50ms | 10-30ms |
| **REST Fallback** | <200ms | 100-150ms |
| **Indicator Calculation** | <100ms | 50-80ms |
| **Full Data Fetch (6 assets)** | <500ms | 200-400ms |
| **Cache Hit** | <5ms | 1-3ms |

### Throughput Targets

| Metric | Target |
|--------|--------|
| **WebSocket Messages/sec** | >100 |
| **REST Requests/min** | 60 (1/second fallback) |
| **Indicator Calculations/sec** | >10 |
| **Concurrent Symbol Streams** | 6 |

---

## Quality Assurance

### Data Validation Rules

```python
def validate_market_data(data: MarketData) -> bool:
    """Validate market data quality"""

    # 1. Timestamp freshness
    if data.staleness_seconds > 30:
        raise StaleDataError(f"Data is {data.staleness_seconds}s old")

    # 2. Price sanity checks
    if data.price <= 0:
        raise ValidationError("Invalid price: must be positive")

    if data.bid >= data.ask:
        raise ValidationError("Invalid spread: bid >= ask")

    # 3. OHLC relationships
    if not (data.low <= data.open <= data.high):
        raise ValidationError("Invalid OHLC: open outside range")

    if not (data.low <= data.close <= data.high):
        raise ValidationError("Invalid OHLC: close outside range")

    # 4. Volume sanity
    if data.volume < 0:
        raise ValidationError("Invalid volume: must be non-negative")

    # 5. Indicator ranges (if present)
    if data.rsi_14 is not None and not (0 <= data.rsi_14 <= 100):
        raise ValidationError(f"Invalid RSI: {data.rsi_14} (must be 0-100)")

    return True
```

---

## Testing Specifications

### Unit Tests

```python
import pytest
from market_data_service import MarketDataService

@pytest.mark.asyncio
async def test_fetch_real_time_data():
    """Test fetching real-time data for multiple symbols"""
    service = MarketDataService()
    symbols = ['BTC/USDT', 'ETH/USDT']

    data = await service.fetch_real_time_data(symbols)

    assert 'BTC/USDT' in data
    assert 'ETH/USDT' in data
    assert data['BTC/USDT'].price > 0
    assert data['BTC/USDT'].staleness_seconds < 30

@pytest.mark.asyncio
async def test_indicator_calculation():
    """Test technical indicator calculation"""
    service = MarketDataService()

    # Create sample OHLCV data
    ohlcv = create_sample_ohlcv(100)  # 100 candles

    indicators = await service.calculate_indicators(ohlcv)

    assert 'ema_20' in indicators
    assert 'rsi_14' in indicators
    assert 'macd' in indicators
    assert 0 <= indicators['rsi_14'] <= 100

@pytest.mark.asyncio
async def test_websocket_reconnection():
    """Test WebSocket reconnection on disconnect"""
    ws = ResilientWebSocket(url="wss://stream.bybit.com/v5/public/linear", symbols=['BTC/USDT'])

    await ws.connect()
    # Simulate disconnect
    await ws.connection.close()

    # Should auto-reconnect
    await asyncio.sleep(10)
    assert ws.connection is not None
    assert ws.connection.open
```

---

## Document Control

**Version History**:
| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-27 | Integration Architect | Initial API contract |

**Document Location**: `/Users/tobiprivat/Documents/GitProjects/personal/trader/PRPs/contracts/market-data-api-contract.md`

---

**END OF MARKET DATA API CONTRACT**

This contract defines the complete interface for market data acquisition from Bybit (WebSocket primary, REST fallback) with technical indicator calculation. Supports 6 concurrent assets with <500ms latency. Ready for implementation.
