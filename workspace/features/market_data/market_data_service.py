"""
Market Data Service

Main service coordinating WebSocket data ingestion, OHLCV storage,
indicator calculation, and caching for real-time trading decisions.

Author: Market Data Service Implementation Team
Date: 2025-10-27
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional

from .models import (
    OHLCV,
    Ticker,
    Timeframe,
    MarketDataSnapshot,
)
from .indicators import IndicatorCalculator
from .websocket_client import BybitWebSocketClient
from workspace.shared.database.connection import DatabasePool
from workspace.features.caching import CacheService


logger = logging.getLogger(__name__)


class MarketDataService:
    """
    Market Data Service

    Coordinates real-time market data ingestion, storage, and processing.

    Features:
    - Real-time WebSocket data streaming
    - OHLCV data storage in TimescaleDB
    - Technical indicator calculation
    - Market data snapshots for trading decisions
    - In-memory caching for fast access

    Attributes:
        symbols: List of trading pairs to track
        timeframe: Primary timeframe for trading
        testnet: Whether using testnet
        lookback_periods: Historical periods to maintain
    """

    def __init__(
        self,
        symbols: List[str],
        timeframe: Timeframe = Timeframe.M3,
        testnet: bool = True,
        lookback_periods: int = 100,  # Keep 100 candles in memory
        cache_service: Optional[CacheService] = None,
    ):
        """
        Initialize Market Data Service

        Args:
            symbols: List of trading pairs (e.g., ['BTCUSDT', 'ETHUSDT'])
            timeframe: Primary timeframe (default: 3m)
            testnet: Use testnet (default: True)
            lookback_periods: Number of historical periods to maintain
            cache_service: Optional CacheService instance (default: creates new one)

        Example:
            ```python
            service = MarketDataService(
                symbols=['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
                timeframe=Timeframe.M3,
            )
            await service.start()
            ```
        """
        self.symbols = symbols
        self.timeframe = timeframe
        self.testnet = testnet
        self.lookback_periods = lookback_periods

        # Initialize cache service
        if cache_service is not None:
            self.cache = cache_service
        else:
            self.cache = CacheService()

        # In-memory data stores
        self.latest_tickers: Dict[str, Ticker] = {}
        self.ohlcv_data: Dict[str, List[OHLCV]] = {
            self._format_symbol(symbol): [] for symbol in symbols
        }
        self.latest_snapshots: Dict[str, MarketDataSnapshot] = {}

        # WebSocket client
        self.ws_client: Optional[BybitWebSocketClient] = None

        # Background tasks
        self.running = False
        self.indicator_update_task: Optional[asyncio.Task] = None
        self.storage_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start market data service"""
        logger.info(f"Starting Market Data Service for {len(self.symbols)} symbols")
        self.running = True

        # Initialize WebSocket client
        self.ws_client = BybitWebSocketClient(
            symbols=self.symbols,
            timeframes=[self.timeframe],
            testnet=self.testnet,
            on_ticker=self._handle_ticker_update,
            on_kline=self._handle_kline_update,
            on_error=self._handle_websocket_error,
        )

        # Load historical data
        await self._load_historical_data()

        # Start WebSocket connection
        asyncio.create_task(self.ws_client.connect())

        # Start background tasks
        self.indicator_update_task = asyncio.create_task(self._indicator_update_loop())
        self.storage_task = asyncio.create_task(self._storage_loop())

        logger.info("Market Data Service started successfully")

    async def stop(self):
        """Stop market data service"""
        logger.info("Stopping Market Data Service")
        self.running = False

        # Stop WebSocket
        if self.ws_client:
            await self.ws_client.disconnect()

        # Cancel background tasks
        if self.indicator_update_task:
            self.indicator_update_task.cancel()
            try:
                await self.indicator_update_task
            except asyncio.CancelledError:
                pass

        if self.storage_task:
            self.storage_task.cancel()
            try:
                await self.storage_task
            except asyncio.CancelledError:
                pass

        logger.info("Market Data Service stopped")

    async def get_snapshot(self, symbol: str) -> Optional[MarketDataSnapshot]:
        """
        Get complete market data snapshot for symbol

        Includes latest OHLCV, ticker, and all technical indicators.

        Args:
            symbol: Trading pair

        Returns:
            MarketDataSnapshot or None if not available
        """
        formatted_symbol = self._format_symbol(symbol)

        # Check if we have recent data
        if formatted_symbol not in self.latest_snapshots:
            logger.warning(f"No snapshot available for {symbol}")
            return None

        snapshot = self.latest_snapshots[formatted_symbol]

        # Check if snapshot is recent (< 5 minutes old)
        age = datetime.utcnow() - snapshot.timestamp
        if age > timedelta(minutes=5):
            logger.warning(f"Snapshot for {symbol} is stale: {age}")

        return snapshot

    async def get_latest_ticker(
        self, symbol: str, use_cache: bool = True
    ) -> Optional[Ticker]:
        """
        Get latest ticker for symbol with caching

        Cache TTL: 30 seconds (ticker updates frequently)

        Args:
            symbol: Trading pair
            use_cache: Whether to use cache (default: True)

        Returns:
            Ticker object or None if not available
        """
        formatted_symbol = self._format_symbol(symbol)

        if use_cache:
            # Generate cache key
            cache_key = f"market_data:ticker:{formatted_symbol}"

            # Try cache first
            cached_ticker = await self.cache.get(cache_key)
            if cached_ticker is not None:
                logger.debug(f"Cache hit for ticker {formatted_symbol}")
                # Convert back to Ticker object
                return Ticker(
                    symbol=cached_ticker["symbol"],
                    last=Decimal(str(cached_ticker["last"])),
                    bid=Decimal(str(cached_ticker.get("bid", 0))),
                    ask=Decimal(str(cached_ticker.get("ask", 0))),
                    high_24h=Decimal(str(cached_ticker.get("high_24h", 0))),
                    low_24h=Decimal(str(cached_ticker.get("low_24h", 0))),
                    volume_24h=Decimal(str(cached_ticker.get("volume_24h", 0))),
                    change_24h=Decimal(str(cached_ticker.get("change_24h", 0))),
                    change_24h_pct=Decimal(str(cached_ticker.get("change_24h_pct", 0))),
                    timestamp=(
                        datetime.fromisoformat(cached_ticker["timestamp"])
                        if isinstance(cached_ticker["timestamp"], str)
                        else cached_ticker["timestamp"]
                    ),
                )

            # Cache miss
            logger.debug(f"Cache miss for ticker {formatted_symbol}")

        # Get from memory
        ticker = self.latest_tickers.get(formatted_symbol)

        if use_cache and ticker:
            # Serialize for caching
            serialized = {
                "symbol": ticker.symbol,
                "last": str(ticker.last),
                "bid": str(ticker.bid) if ticker.bid else "0",
                "ask": str(ticker.ask) if ticker.ask else "0",
                "high_24h": (
                    str(ticker.high_24h) if hasattr(ticker, "high_24h") else "0"
                ),
                "low_24h": str(ticker.low_24h) if hasattr(ticker, "low_24h") else "0",
                "volume_24h": (
                    str(ticker.volume_24h) if hasattr(ticker, "volume_24h") else "0"
                ),
                "change_24h": (
                    str(ticker.change_24h) if hasattr(ticker, "change_24h") else "0"
                ),
                "change_24h_pct": (
                    str(ticker.change_24h_pct)
                    if hasattr(ticker, "change_24h_pct")
                    else "0"
                ),
                "timestamp": (
                    ticker.timestamp.isoformat()
                    if hasattr(ticker.timestamp, "isoformat")
                    else str(ticker.timestamp)
                ),
            }
            # Cache for 30 seconds
            cache_key = f"market_data:ticker:{formatted_symbol}"
            await self.cache.set(cache_key, serialized, ttl_seconds=30)

        return ticker

    async def get_ohlcv_history(
        self,
        symbol: str,
        limit: int = 100,
        use_cache: bool = True,
    ) -> List[OHLCV]:
        """
        Get historical OHLCV data for symbol with caching

        Cache TTL: 60 seconds (data updates every minute)

        Args:
            symbol: Trading pair
            limit: Maximum number of candles
            use_cache: Whether to use cache (default: True)

        Returns:
            List of OHLCV candles (sorted by timestamp ascending)
        """
        formatted_symbol = self._format_symbol(symbol)

        if use_cache:
            # Generate cache key
            cache_key = (
                f"market_data:ohlcv:{formatted_symbol}:{self.timeframe.value}:{limit}"
            )

            # Try cache first
            cached_data = await self.cache.get(cache_key)
            if cached_data is not None:
                logger.debug(
                    f"Cache hit for OHLCV {formatted_symbol} {self.timeframe.value}"
                )
                # Convert back to OHLCV objects
                return [
                    OHLCV(
                        symbol=candle["symbol"],
                        timeframe=Timeframe(candle["timeframe"]),
                        timestamp=(
                            datetime.fromisoformat(candle["timestamp"])
                            if isinstance(candle["timestamp"], str)
                            else candle["timestamp"]
                        ),
                        open=Decimal(str(candle["open"])),
                        high=Decimal(str(candle["high"])),
                        low=Decimal(str(candle["low"])),
                        close=Decimal(str(candle["close"])),
                        volume=Decimal(str(candle["volume"])),
                        quote_volume=Decimal(str(candle.get("quote_volume", 0))),
                        trades_count=candle.get("trades_count", 0),
                    )
                    for candle in cached_data
                ]

            # Cache miss
            logger.debug(
                f"Cache miss for OHLCV {formatted_symbol} {self.timeframe.value}"
            )

        # Get from memory
        candles = self.ohlcv_data.get(formatted_symbol, [])
        result = candles[-limit:] if candles else []

        if use_cache and result:
            # Serialize for caching
            serialized = [
                {
                    "symbol": c.symbol,
                    "timeframe": (
                        c.timeframe.value
                        if hasattr(c.timeframe, "value")
                        else str(c.timeframe)
                    ),
                    "timestamp": (
                        c.timestamp.isoformat()
                        if hasattr(c.timestamp, "isoformat")
                        else str(c.timestamp)
                    ),
                    "open": str(c.open),
                    "high": str(c.high),
                    "low": str(c.low),
                    "close": str(c.close),
                    "volume": str(c.volume),
                    "quote_volume": str(c.quote_volume) if c.quote_volume else "0",
                    "trades_count": c.trades_count or 0,
                }
                for c in result
            ]
            # Cache for 60 seconds
            cache_key = (
                f"market_data:ohlcv:{formatted_symbol}:{self.timeframe.value}:{limit}"
            )
            await self.cache.set(cache_key, serialized, ttl_seconds=60)

        return result

    async def _handle_ticker_update(self, ticker: Ticker):
        """Handle incoming ticker update from WebSocket"""
        self.latest_tickers[ticker.symbol] = ticker
        logger.debug(f"Ticker updated: {ticker.symbol} @ {ticker.last}")

    async def _handle_kline_update(self, ohlcv: OHLCV):
        """Handle incoming kline update from WebSocket"""
        symbol = ohlcv.symbol

        # Add to in-memory store
        if symbol in self.ohlcv_data:
            candles = self.ohlcv_data[symbol]

            # Check if this is an update to latest candle or new candle
            if candles and candles[-1].timestamp == ohlcv.timestamp:
                # Update existing candle
                candles[-1] = ohlcv
            else:
                # New candle
                candles.append(ohlcv)

                # Maintain lookback window
                if len(candles) > self.lookback_periods:
                    candles.pop(0)

            logger.debug(
                f"Kline updated: {symbol} @ {ohlcv.timestamp} "
                f"(O:{ohlcv.open} H:{ohlcv.high} L:{ohlcv.low} C:{ohlcv.close})"
            )

            # Trigger indicator recalculation
            await self._update_indicators(symbol)

    async def _handle_websocket_error(self, error: Exception):
        """Handle WebSocket errors"""
        logger.error(f"WebSocket error: {error}")

    async def _load_historical_data(self):
        """Load historical OHLCV data from database"""
        logger.info("Loading historical OHLCV data")

        for symbol in self.symbols:
            formatted_symbol = self._format_symbol(symbol)

            try:
                async with DatabasePool.get_connection() as conn:
                    # Load last N candles
                    rows = await conn.fetch(
                        """
                        SELECT symbol, timeframe, timestamp, open, high, low, close,
                               volume, quote_volume, trades_count
                        FROM market_data
                        WHERE symbol = $1 AND timeframe = $2
                        ORDER BY timestamp DESC
                        LIMIT $3
                        """,
                        formatted_symbol,
                        self.timeframe.value,
                        self.lookback_periods,
                    )

                    # Convert to OHLCV objects (reverse to get ascending order)
                    candles = []
                    for row in reversed(rows):
                        candle = OHLCV(
                            symbol=row["symbol"],
                            timeframe=Timeframe(row["timeframe"]),
                            timestamp=row["timestamp"],
                            open=row["open"],
                            high=row["high"],
                            low=row["low"],
                            close=row["close"],
                            volume=row["volume"],
                            quote_volume=row["quote_volume"],
                            trades_count=row["trades_count"],
                        )
                        candles.append(candle)

                    self.ohlcv_data[formatted_symbol] = candles
                    logger.info(f"Loaded {len(candles)} candles for {formatted_symbol}")

            except Exception as e:
                logger.error(
                    f"Error loading historical data for {symbol}: {e}", exc_info=True
                )

    async def _update_indicators(self, symbol: str):
        """Calculate and update indicators for symbol"""
        try:
            candles = self.ohlcv_data.get(symbol, [])
            if len(candles) < 50:  # Need enough data for indicators
                logger.debug(
                    f"Insufficient data for indicators: {symbol} ({len(candles)} candles)"
                )
                return

            # Get latest ticker
            ticker = self.latest_tickers.get(symbol)
            if not ticker:
                logger.debug(f"No ticker available for {symbol}")
                return

            # Calculate all indicators
            indicators = IndicatorCalculator.calculate_all_indicators(candles)

            # Create snapshot
            snapshot = MarketDataSnapshot(
                symbol=symbol,
                timeframe=self.timeframe,
                timestamp=datetime.utcnow(),
                ohlcv=candles[-1],
                ticker=ticker,
                rsi=indicators.get("rsi"),
                macd=indicators.get("macd"),
                ema_fast=indicators.get("ema_fast"),
                ema_slow=indicators.get("ema_slow"),
                bollinger=indicators.get("bollinger"),
            )

            self.latest_snapshots[symbol] = snapshot
            logger.debug(f"Indicators updated for {symbol}")

        except Exception as e:
            logger.error(f"Error updating indicators for {symbol}: {e}", exc_info=True)

    async def _indicator_update_loop(self):
        """Background task to periodically update indicators"""
        logger.info("Indicator update loop started")

        while self.running:
            try:
                # Update indicators for all symbols every 10 seconds
                await asyncio.sleep(10)

                for symbol in self.symbols:
                    formatted_symbol = self._format_symbol(symbol)
                    await self._update_indicators(formatted_symbol)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in indicator update loop: {e}", exc_info=True)

        logger.info("Indicator update loop stopped")

    async def _storage_loop(self):
        """Background task to periodically store data to database"""
        logger.info("Storage loop started")

        while self.running:
            try:
                # Store data every 60 seconds
                await asyncio.sleep(60)

                for symbol in self.symbols:
                    formatted_symbol = self._format_symbol(symbol)
                    candles = self.ohlcv_data.get(formatted_symbol, [])

                    if candles:
                        # Store last candle (most recent complete candle)
                        await self._store_ohlcv(candles[-1])

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in storage loop: {e}", exc_info=True)

        logger.info("Storage loop stopped")

    async def _store_ohlcv(self, ohlcv: OHLCV):
        """Store OHLCV data to database"""
        try:
            async with DatabasePool.get_connection() as conn:
                await conn.execute(
                    """
                    INSERT INTO market_data (
                        symbol, timeframe, timestamp, open, high, low, close,
                        volume, quote_volume, trades_count
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (symbol, timeframe, timestamp)
                    DO UPDATE SET
                        open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        close = EXCLUDED.close,
                        volume = EXCLUDED.volume,
                        quote_volume = EXCLUDED.quote_volume,
                        trades_count = EXCLUDED.trades_count
                    """,
                    ohlcv.symbol,
                    ohlcv.timeframe.value,
                    ohlcv.timestamp,
                    ohlcv.open,
                    ohlcv.high,
                    ohlcv.low,
                    ohlcv.close,
                    ohlcv.volume,
                    ohlcv.quote_volume,
                    ohlcv.trades_count,
                )
            logger.debug(f"Stored OHLCV: {ohlcv.symbol} @ {ohlcv.timestamp}")

        except Exception as e:
            logger.error(f"Error storing OHLCV: {e}", exc_info=True)

    def _format_symbol(self, symbol: str) -> str:
        """Format symbol to standard format"""
        # If already formatted, return as-is
        if "/" in symbol and ":" in symbol:
            return symbol

        # Otherwise, format for perpetual futures
        if symbol.endswith("USDT"):
            base = symbol[:-4]
            return f"{base}/USDT:USDT"

        return symbol


# Export
__all__ = ["MarketDataService"]
