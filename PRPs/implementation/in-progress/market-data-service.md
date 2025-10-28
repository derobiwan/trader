# PRP: Market Data Service Implementation

## Metadata
- **PRP Type**: Implementation
- **Feature**: Market Data Collection & Processing
- **Priority**: High
- **Estimated Effort**: 21 story points
- **Dependencies**: Database Setup, Redis Cache
- **Target Directory**: workspace/features/market_data/

## Context

### Business Requirements
Reliable, low-latency market data collection for 6 cryptocurrency perpetual futures (BTC, ETH, SOL, BNB, ADA, DOGE) with 3-minute granularity, technical indicator calculation, and WebSocket-first architecture with REST fallback.

### Technical Context
- **Primary Source**: Bybit WebSocket streams
- **Fallback**: REST API polling
- **Indicators**: pandas-ta library (20+ indicators)
- **Caching**: Redis for recent data
- **Storage**: TimescaleDB for historical data
- **Latency Target**: <500ms for complete data fetch

### From API Contract
```yaml
# From PRPs/contracts/market-data-api-contract.md
- GET /market-data/ohlcv/{symbol}
- GET /market-data/indicators/{symbol}
- GET /market-data/realtime/{symbol}
- WebSocket: ws://localhost:8000/ws/market-data
```

## Implementation Requirements

### 1. WebSocket Client Implementation

**File**: `workspace/features/market_data/websocket_client.py`

```python
import asyncio
import json
import logging
from datetime import datetime, UTC
from typing import Dict, Any, Optional, Callable, List
from decimal import Decimal
import aiohttp

logger = logging.getLogger(__name__)

class BybitWebSocketClient:
    """
    WebSocket client for Bybit perpetual futures market data.
    Implements auto-reconnection and message handling.
    """

    WEBSOCKET_URL = "wss://stream.bybit.com/v5/public/linear"
    HEARTBEAT_INTERVAL = 20  # seconds
    MAX_RECONNECT_ATTEMPTS = 5

    def __init__(self, symbols: List[str]):
        self.symbols = symbols
        self.websocket: Optional[aiohttp.ClientWebSocketResponse] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.is_connected = False
        self.reconnect_attempts = 0

        # Message handlers
        self.handlers: Dict[str, List[Callable]] = {
            'kline': [],
            'trade': [],
            'orderbook': [],
            'ticker': []
        }

        # Data buffers
        self.latest_klines: Dict[str, Dict] = {}
        self.latest_tickers: Dict[str, Dict] = {}
        self.orderbook_snapshot: Dict[str, Dict] = {}

        # Tasks
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._message_handler_task: Optional[asyncio.Task] = None

    async def connect(self) -> None:
        """
        Establish WebSocket connection with retry logic.
        """
        while self.reconnect_attempts < self.MAX_RECONNECT_ATTEMPTS:
            try:
                if not self.session:
                    self.session = aiohttp.ClientSession()

                self.websocket = await self.session.ws_connect(
                    self.WEBSOCKET_URL,
                    heartbeat=30,
                    receive_timeout=60,
                    ssl=True
                )

                self.is_connected = True
                self.reconnect_attempts = 0

                logger.info(f"WebSocket connected to {self.WEBSOCKET_URL}")

                # Subscribe to channels
                await self._subscribe_to_channels()

                # Start heartbeat
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

                # Start message handler
                self._message_handler_task = asyncio.create_task(self._handle_messages())

                break

            except Exception as e:
                self.reconnect_attempts += 1
                wait_time = min(2 ** self.reconnect_attempts, 30)
                logger.error(
                    f"WebSocket connection failed (attempt {self.reconnect_attempts}): {e}. "
                    f"Retrying in {wait_time}s..."
                )
                await asyncio.sleep(wait_time)

        if not self.is_connected:
            raise ConnectionError("Failed to establish WebSocket connection")

    async def _subscribe_to_channels(self) -> None:
        """
        Subscribe to required data channels for all symbols.
        """
        subscriptions = []

        for symbol in self.symbols:
            # Kline subscription (3-minute candles)
            subscriptions.append(f"kline.3.{symbol}USDT")

            # Ticker subscription (24hr stats)
            subscriptions.append(f"tickers.{symbol}USDT")

            # Trade subscription (real-time trades)
            subscriptions.append(f"publicTrade.{symbol}USDT")

            # Orderbook subscription (depth)
            subscriptions.append(f"orderbook.1.{symbol}USDT")

        # Send subscription message
        subscribe_msg = {
            "op": "subscribe",
            "args": subscriptions
        }

        await self.websocket.send_json(subscribe_msg)
        logger.info(f"Subscribed to {len(subscriptions)} channels")

    async def _heartbeat_loop(self) -> None:
        """
        Send periodic heartbeat to keep connection alive.
        """
        while self.is_connected:
            try:
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)

                ping_msg = {"op": "ping"}
                await self.websocket.send_json(ping_msg)

                logger.debug("Heartbeat sent")

            except Exception as e:
                logger.error(f"Heartbeat failed: {e}")
                await self._handle_disconnect()
                break

    async def _handle_messages(self) -> None:
        """
        Process incoming WebSocket messages.
        """
        async for msg in self.websocket:
            try:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    await self._process_message(data)

                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {msg.data}")
                    await self._handle_disconnect()
                    break

                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    logger.warning("WebSocket connection closed")
                    await self._handle_disconnect()
                    break

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse message: {e}")
            except Exception as e:
                logger.error(f"Message handling error: {e}")

    async def _process_message(self, data: Dict[str, Any]) -> None:
        """
        Process and route WebSocket messages.
        """
        # Handle pong response
        if data.get('op') == 'pong':
            logger.debug("Pong received")
            return

        # Handle subscription response
        if data.get('op') == 'subscribe':
            if data.get('success'):
                logger.info("Subscription successful")
            else:
                logger.error(f"Subscription failed: {data}")
            return

        # Handle data messages
        topic = data.get('topic', '')

        if 'kline' in topic:
            await self._process_kline(data)
        elif 'tickers' in topic:
            await self._process_ticker(data)
        elif 'publicTrade' in topic:
            await self._process_trade(data)
        elif 'orderbook' in topic:
            await self._process_orderbook(data)

    async def _process_kline(self, data: Dict[str, Any]) -> None:
        """
        Process kline (candlestick) data.
        """
        try:
            kline_data = data['data'][0] if isinstance(data.get('data'), list) else data['data']

            symbol = self._extract_symbol(data['topic'])

            kline = {
                'symbol': symbol,
                'interval': '3m',
                'open_time': datetime.fromtimestamp(int(kline_data['start']) / 1000, UTC),
                'close_time': datetime.fromtimestamp(int(kline_data['end']) / 1000, UTC),
                'open': Decimal(kline_data['open']),
                'high': Decimal(kline_data['high']),
                'low': Decimal(kline_data['low']),
                'close': Decimal(kline_data['close']),
                'volume': Decimal(kline_data['volume']),
                'turnover': Decimal(kline_data['turnover']),
                'confirm': kline_data.get('confirm', False)
            }

            # Update buffer
            self.latest_klines[symbol] = kline

            # Trigger handlers
            for handler in self.handlers['kline']:
                await handler(kline)

        except Exception as e:
            logger.error(f"Failed to process kline: {e}")

    async def _handle_disconnect(self) -> None:
        """
        Handle WebSocket disconnection and attempt reconnection.
        """
        self.is_connected = False

        # Cancel tasks
        if self._heartbeat_task:
            self._heartbeat_task.cancel()

        logger.warning("WebSocket disconnected, attempting reconnection...")
        await self.connect()

    def _extract_symbol(self, topic: str) -> str:
        """
        Extract symbol from topic string.
        """
        # Example: "kline.3.BTCUSDT" -> "BTC"
        parts = topic.split('.')
        if len(parts) >= 3:
            symbol_with_usdt = parts[-1]
            return symbol_with_usdt.replace('USDT', '')
        return ''

    async def close(self) -> None:
        """
        Clean shutdown of WebSocket connection.
        """
        self.is_connected = False

        if self._heartbeat_task:
            self._heartbeat_task.cancel()

        if self._message_handler_task:
            self._message_handler_task.cancel()

        if self.websocket:
            await self.websocket.close()

        if self.session:
            await self.session.close()

        logger.info("WebSocket client closed")
```

### 2. REST API Fallback

**File**: `workspace/features/market_data/rest_client.py`

```python
import asyncio
import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, UTC
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class BybitRESTClient:
    """
    REST API client for Bybit with fallback capability.
    """

    BASE_URL = "https://api.bybit.com"
    TIMEOUT = 5.0  # seconds

    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=httpx.Timeout(self.TIMEOUT),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
        )

    async def get_klines(
        self,
        symbol: str,
        interval: str = "3",
        limit: int = 200
    ) -> List[Dict[str, Any]]:
        """
        Fetch historical kline data.
        """
        try:
            response = await self.client.get(
                "/v5/market/kline",
                params={
                    "category": "linear",
                    "symbol": f"{symbol}USDT",
                    "interval": interval,
                    "limit": limit
                }
            )

            response.raise_for_status()
            data = response.json()

            if data['retCode'] != 0:
                raise Exception(f"API error: {data.get('retMsg', 'Unknown error')}")

            klines = []
            for item in data['result']['list']:
                klines.append({
                    'open_time': datetime.fromtimestamp(int(item[0]) / 1000, UTC),
                    'open': Decimal(item[1]),
                    'high': Decimal(item[2]),
                    'low': Decimal(item[3]),
                    'close': Decimal(item[4]),
                    'volume': Decimal(item[5]),
                    'turnover': Decimal(item[6])
                })

            return klines

        except httpx.TimeoutException:
            logger.error(f"Timeout fetching klines for {symbol}")
            return []
        except Exception as e:
            logger.error(f"Error fetching klines: {e}")
            return []

    async def get_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetch 24hr ticker statistics.
        """
        try:
            response = await self.client.get(
                "/v5/market/tickers",
                params={
                    "category": "linear",
                    "symbol": f"{symbol}USDT"
                }
            )

            response.raise_for_status()
            data = response.json()

            if data['retCode'] == 0 and data['result']['list']:
                ticker_data = data['result']['list'][0]
                return {
                    'symbol': symbol,
                    'last_price': Decimal(ticker_data['lastPrice']),
                    'bid_price': Decimal(ticker_data['bid1Price']),
                    'ask_price': Decimal(ticker_data['ask1Price']),
                    'volume_24h': Decimal(ticker_data['volume24h']),
                    'turnover_24h': Decimal(ticker_data['turnover24h']),
                    'high_24h': Decimal(ticker_data['highPrice24h']),
                    'low_24h': Decimal(ticker_data['lowPrice24h']),
                    'price_change_percent': Decimal(ticker_data['price24hPcnt'])
                }

            return None

        except Exception as e:
            logger.error(f"Error fetching ticker: {e}")
            return None

    async def close(self) -> None:
        """
        Close HTTP client.
        """
        await self.client.aclose()
```

### 3. Technical Indicators Calculation

**File**: `workspace/features/market_data/indicators.py`

```python
import pandas as pd
import pandas_ta as ta
from typing import Dict, Any, Optional, List
from decimal import Decimal
import numpy as np
import logging

logger = logging.getLogger(__name__)

class TechnicalIndicators:
    """
    Calculate technical indicators using pandas-ta.
    """

    def __init__(self):
        # Configure pandas-ta
        pd.set_option('mode.chained_assignment', None)

    def calculate_indicators(
        self,
        df: pd.DataFrame,
        config: Optional[Dict] = None
    ) -> pd.DataFrame:
        """
        Calculate all required technical indicators.

        Args:
            df: DataFrame with OHLCV data
            config: Optional configuration for indicators

        Returns:
            DataFrame with indicators added
        """
        if df.empty or len(df) < 50:
            logger.warning("Insufficient data for indicator calculation")
            return df

        try:
            # Ensure numeric types
            numeric_cols = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            # Moving Averages
            df['sma_20'] = ta.sma(df['close'], length=20)
            df['sma_50'] = ta.sma(df['close'], length=50)
            df['ema_12'] = ta.ema(df['close'], length=12)
            df['ema_26'] = ta.ema(df['close'], length=26)

            # RSI
            df['rsi_14'] = ta.rsi(df['close'], length=14)

            # MACD
            macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
            if macd is not None and not macd.empty:
                df['macd'] = macd['MACD_12_26_9']
                df['macd_signal'] = macd['MACDs_12_26_9']
                df['macd_histogram'] = macd['MACDh_12_26_9']

            # Bollinger Bands
            bbands = ta.bbands(df['close'], length=20, std=2)
            if bbands is not None and not bbands.empty:
                df['bb_upper'] = bbands['BBU_20_2.0']
                df['bb_middle'] = bbands['BBM_20_2.0']
                df['bb_lower'] = bbands['BBL_20_2.0']

            # ATR (Average True Range)
            df['atr_14'] = ta.atr(df['high'], df['low'], df['close'], length=14)

            # Stochastic
            stoch = ta.stoch(df['high'], df['low'], df['close'])
            if stoch is not None and not stoch.empty:
                df['stoch_k'] = stoch['STOCHk_14_3_3']
                df['stoch_d'] = stoch['STOCHd_14_3_3']

            # Volume indicators
            df['obv'] = ta.obv(df['close'], df['volume'])
            df['vwap'] = ta.vwap(df['high'], df['low'], df['close'], df['volume'])

            # Support/Resistance levels
            df['pivot'] = (df['high'] + df['low'] + df['close']) / 3
            df['resistance_1'] = 2 * df['pivot'] - df['low']
            df['support_1'] = 2 * df['pivot'] - df['high']

            # Additional custom indicators
            df = self._calculate_custom_indicators(df)

            # Clean up NaN values for recent rows
            df = df.fillna(method='ffill', limit=5)

            return df

        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return df

    def _calculate_custom_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate custom trading indicators.
        """
        try:
            # Momentum
            df['momentum'] = df['close'].pct_change(periods=10) * 100

            # Volatility (using ATR ratio)
            if 'atr_14' in df.columns:
                df['volatility'] = df['atr_14'] / df['close'] * 100

            # Volume ratio (current vs average)
            df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()

            # Price position in range
            df['price_position'] = (df['close'] - df['low'].rolling(20).min()) / \
                                  (df['high'].rolling(20).max() - df['low'].rolling(20).min())

            # Trend strength (using ADX if we add it)
            adx = ta.adx(df['high'], df['low'], df['close'], length=14)
            if adx is not None and not adx.empty:
                df['adx'] = adx['ADX_14']
                df['trend_strength'] = pd.cut(
                    df['adx'],
                    bins=[0, 25, 50, 75, 100],
                    labels=['weak', 'moderate', 'strong', 'very_strong']
                )

            return df

        except Exception as e:
            logger.error(f"Error in custom indicators: {e}")
            return df

    def get_latest_indicators(
        self,
        df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Extract latest indicator values for decision making.
        """
        if df.empty:
            return {}

        latest = df.iloc[-1]
        indicators = {}

        # Extract all indicator values
        indicator_columns = [
            'sma_20', 'sma_50', 'ema_12', 'ema_26',
            'rsi_14', 'macd', 'macd_signal', 'macd_histogram',
            'bb_upper', 'bb_middle', 'bb_lower',
            'atr_14', 'stoch_k', 'stoch_d',
            'obv', 'vwap', 'momentum', 'volatility',
            'volume_ratio', 'price_position'
        ]

        for col in indicator_columns:
            if col in df.columns:
                value = latest[col]
                if pd.notna(value):
                    indicators[col] = float(value)

        # Add interpreted signals
        indicators['signals'] = self._interpret_signals(latest)

        return indicators

    def _interpret_signals(self, row: pd.Series) -> Dict[str, str]:
        """
        Interpret technical indicators into trading signals.
        """
        signals = {}

        # RSI signals
        if pd.notna(row.get('rsi_14')):
            rsi = row['rsi_14']
            if rsi < 30:
                signals['rsi'] = 'oversold'
            elif rsi > 70:
                signals['rsi'] = 'overbought'
            else:
                signals['rsi'] = 'neutral'

        # MACD signals
        if pd.notna(row.get('macd')) and pd.notna(row.get('macd_signal')):
            if row['macd'] > row['macd_signal']:
                signals['macd'] = 'bullish'
            else:
                signals['macd'] = 'bearish'

        # Moving average signals
        if pd.notna(row.get('close')) and pd.notna(row.get('sma_20')):
            if row['close'] > row['sma_20']:
                signals['ma_trend'] = 'above_ma'
            else:
                signals['ma_trend'] = 'below_ma'

        # Bollinger Band signals
        if all(pd.notna(row.get(x)) for x in ['close', 'bb_upper', 'bb_lower']):
            if row['close'] > row['bb_upper']:
                signals['bb'] = 'overbought'
            elif row['close'] < row['bb_lower']:
                signals['bb'] = 'oversold'
            else:
                signals['bb'] = 'neutral'

        return signals
```

### 4. Market Data Service Orchestrator

**File**: `workspace/features/market_data/service.py`

```python
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, UTC
from decimal import Decimal
import pandas as pd
import logging

from .websocket_client import BybitWebSocketClient
from .rest_client import BybitRESTClient
from .indicators import TechnicalIndicators
from ..database.connection import DatabaseConnection
from ..cache.redis_client import RedisClient

logger = logging.getLogger(__name__)

class MarketDataService:
    """
    Main service orchestrating market data collection, processing, and storage.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.symbols = ['BTC', 'ETH', 'SOL', 'BNB', 'ADA', 'DOGE']

        # Initialize components
        self.ws_client = BybitWebSocketClient(self.symbols)
        self.rest_client = BybitRESTClient()
        self.indicators = TechnicalIndicators()
        self.db = DatabaseConnection(config['database'])
        self.redis = RedisClient(config['redis'])

        # Data buffers
        self.market_data_cache: Dict[str, pd.DataFrame] = {}

        # State tracking
        self.is_running = False
        self.last_update_time: Dict[str, datetime] = {}

    async def initialize(self) -> None:
        """
        Initialize all components and start data collection.
        """
        try:
            # Initialize database
            await self.db.initialize()

            # Initialize Redis
            await self.redis.connect()

            # Connect WebSocket
            await self.ws_client.connect()

            # Register WebSocket handlers
            self.ws_client.handlers['kline'].append(self._handle_kline)
            self.ws_client.handlers['ticker'].append(self._handle_ticker)

            # Load historical data for indicators
            await self._load_historical_data()

            # Start periodic tasks
            asyncio.create_task(self._periodic_sync())
            asyncio.create_task(self._health_monitor())

            self.is_running = True
            logger.info("Market data service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize market data service: {e}")
            raise

    async def _load_historical_data(self) -> None:
        """
        Load historical data for indicator calculation.
        """
        for symbol in self.symbols:
            try:
                # Fetch last 200 candles via REST
                klines = await self.rest_client.get_klines(symbol, interval="3", limit=200)

                if klines:
                    # Convert to DataFrame
                    df = pd.DataFrame(klines)
                    df['symbol'] = symbol
                    df.set_index('open_time', inplace=True)

                    # Calculate indicators
                    df = self.indicators.calculate_indicators(df)

                    # Store in cache
                    self.market_data_cache[symbol] = df

                    # Store in database
                    await self._store_historical_data(symbol, df)

                    logger.info(f"Loaded {len(df)} historical candles for {symbol}")

            except Exception as e:
                logger.error(f"Failed to load historical data for {symbol}: {e}")

    async def _handle_kline(self, kline: Dict[str, Any]) -> None:
        """
        Handle incoming kline data from WebSocket.
        """
        try:
            symbol = kline['symbol']

            # Update DataFrame
            if symbol not in self.market_data_cache:
                self.market_data_cache[symbol] = pd.DataFrame()

            df = self.market_data_cache[symbol]

            # Add new kline
            new_row = pd.DataFrame([{
                'open': float(kline['open']),
                'high': float(kline['high']),
                'low': float(kline['low']),
                'close': float(kline['close']),
                'volume': float(kline['volume'])
            }], index=[kline['open_time']])

            # Append or update
            if kline['confirm']:
                df = pd.concat([df, new_row])
                df = df[-500:]  # Keep last 500 candles

                # Recalculate indicators
                df = self.indicators.calculate_indicators(df)
                self.market_data_cache[symbol] = df

                # Store in database
                await self._store_kline(symbol, kline, df.iloc[-1])

            # Update Redis cache
            await self._update_redis_cache(symbol, kline)

            self.last_update_time[symbol] = datetime.now(UTC)

        except Exception as e:
            logger.error(f"Error handling kline: {e}")

    async def get_market_data(
        self,
        symbol: str,
        include_indicators: bool = True
    ) -> Dict[str, Any]:
        """
        Get latest market data for a symbol.
        """
        try:
            # Check cache first
            cached = await self.redis.get(f"market:{symbol}")
            if cached and not include_indicators:
                return cached

            # Get from DataFrame
            if symbol in self.market_data_cache:
                df = self.market_data_cache[symbol]
                if not df.empty:
                    latest = df.iloc[-1].to_dict()

                    if include_indicators:
                        indicators = self.indicators.get_latest_indicators(df)
                        latest['indicators'] = indicators

                    return {
                        'symbol': symbol,
                        'data': latest,
                        'timestamp': self.last_update_time.get(symbol, datetime.now(UTC)).isoformat()
                    }

            # Fallback to REST
            ticker = await self.rest_client.get_ticker(symbol)
            if ticker:
                return {
                    'symbol': symbol,
                    'data': ticker,
                    'timestamp': datetime.now(UTC).isoformat(),
                    'source': 'rest_fallback'
                }

            return {}

        except Exception as e:
            logger.error(f"Error getting market data for {symbol}: {e}")
            return {}

    async def get_all_market_data(self) -> Dict[str, Any]:
        """
        Get market data for all symbols.
        """
        tasks = [
            self.get_market_data(symbol, include_indicators=True)
            for symbol in self.symbols
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        market_data = {}
        for symbol, result in zip(self.symbols, results):
            if isinstance(result, Exception):
                logger.error(f"Failed to get data for {symbol}: {result}")
                market_data[symbol] = {}
            else:
                market_data[symbol] = result

        return market_data

    async def _periodic_sync(self) -> None:
        """
        Periodically sync data and handle fallback.
        """
        while self.is_running:
            try:
                await asyncio.sleep(30)  # Every 30 seconds

                # Check for stale data
                now = datetime.now(UTC)
                for symbol in self.symbols:
                    last_update = self.last_update_time.get(symbol)

                    if not last_update or (now - last_update) > timedelta(minutes=5):
                        logger.warning(f"Data stale for {symbol}, using REST fallback")

                        # Fetch via REST
                        klines = await self.rest_client.get_klines(symbol, limit=10)
                        if klines:
                            # Update cache
                            await self._process_rest_klines(symbol, klines)

            except Exception as e:
                logger.error(f"Error in periodic sync: {e}")

    async def close(self) -> None:
        """
        Cleanup resources.
        """
        self.is_running = False

        await self.ws_client.close()
        await self.rest_client.close()
        await self.db.close()
        await self.redis.close()

        logger.info("Market data service closed")
```

## Validation Requirements

### Level 1: Unit Tests
```python
async def test_websocket_connection():
    """Test WebSocket connection establishment."""
    client = BybitWebSocketClient(['BTC'])
    await client.connect()
    assert client.is_connected == True
    await client.close()

async def test_indicator_calculation():
    """Test technical indicator calculations."""
    calc = TechnicalIndicators()
    df = create_test_ohlcv_data()
    result = calc.calculate_indicators(df)
    assert 'rsi_14' in result.columns
    assert 'macd' in result.columns

async def test_data_caching():
    """Test Redis caching functionality."""
    service = MarketDataService(test_config)
    await service.initialize()
    data = await service.get_market_data('BTC')
    assert data['symbol'] == 'BTC'
```

### Level 2: Integration Tests
- WebSocket reconnection after disconnect
- REST fallback when WebSocket fails
- Data persistence to TimescaleDB
- Indicator accuracy verification

### Level 3: Performance Tests
- Data fetch under 500ms
- Handle 100 updates/second
- Memory usage under 500MB
- CPU usage under 20%

## Acceptance Criteria

### Must Have
- [x] WebSocket connection with auto-reconnect
- [x] REST API fallback
- [x] 20+ technical indicators
- [x] Redis caching
- [x] TimescaleDB storage
- [x] <500ms latency

### Should Have
- [x] Data validation
- [x] Error recovery
- [x] Performance metrics
- [x] Health monitoring

---

**PRP Status**: Ready for Implementation
**Estimated Hours**: 42 hours (21 story points)
**Priority**: High - Required for decision engine
**Dependencies**: Database setup must be complete