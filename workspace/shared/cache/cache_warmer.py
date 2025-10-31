"""
Cache Warming Strategy for Trading System.

This module provides intelligent cache pre-loading on application startup to:
- Reduce first-cycle latency
- Improve cache hit rates
- Pre-load critical trading data
- Enable parallel warming for efficiency

Author: Performance Optimizer Agent
Date: 2025-10-30
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from dataclasses import dataclass, field
import json

# Import from workspace features
if TYPE_CHECKING:
    # Type-checking only imports (avoid circular dependencies and missing modules)
    pass

from workspace.features.market_data.market_data_service import MarketDataService
from workspace.infrastructure.cache.redis_manager import RedisManager

logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """Statistics for cache warming operations."""

    total_keys: int = 0
    successful_keys: int = 0
    failed_keys: int = 0
    warm_time_ms: float = 0.0
    cache_hit_rate: float = 0.0
    total_size_mb: float = 0.0
    errors: List[str] = field(default_factory=list)


@dataclass
class CacheConfig:
    """Configuration for cache warming."""

    # Market data config
    market_symbols: List[str] = field(default_factory=list)
    market_ohlcv_candles: int = 100
    market_ohlcv_timeframe: str = "5m"
    market_ohlcv_ttl: int = 60  # seconds
    market_ticker_ttl: int = 10
    market_orderbook_levels: int = 20
    market_orderbook_ttl: int = 5

    # Account data config
    balance_ttl: int = 30

    # Position data config
    position_ttl: int = 60
    position_history_days: int = 7

    # Warming config
    parallel_workers: int = 4
    retry_attempts: int = 3
    retry_delay_seconds: int = 1
    warm_timeout_seconds: int = 30


class CacheWarmer:
    """
    Intelligent cache warming system for the trading application.

    Pre-loads critical data into cache on startup to improve performance
    and reduce latency during trading operations.
    """

    def __init__(
        self,
        redis_manager: RedisManager,
        market_data_service: MarketDataService,
        balance_fetcher: Any,  # BalanceFetcher
        position_service: Any,  # PositionService
        config: Optional[CacheConfig] = None,
    ):
        """
        Initialize the cache warmer.

        Args:
            redis_manager: Redis cache manager
            market_data_service: Market data service
            balance_fetcher: Balance fetching service
            position_service: Position management service
            config: Cache warming configuration
        """
        self.redis = redis_manager
        self.market_data = market_data_service
        self.balance_fetcher = balance_fetcher
        self.position_service = position_service
        self.config = config or CacheConfig()

        # Statistics tracking
        self.stats = CacheStats()
        self._warming_in_progress = False
        self._last_warm_time: Optional[datetime] = None
        self._cache_hits: int = 0
        self._cache_misses: int = 0

    async def warm_all_caches(self) -> CacheStats:
        """
        Warm all caches with parallel execution.

        Returns:
            CacheStats containing warming results
        """
        if self._warming_in_progress:
            logger.warning("Cache warming already in progress")
            return self.stats

        self._warming_in_progress = True
        start_time = time.time()
        self.stats = CacheStats()

        try:
            logger.info("Starting cache warming...")

            # Create warming tasks
            tasks = [
                asyncio.create_task(self.warm_market_data()),
                asyncio.create_task(self.warm_balance_data()),
                asyncio.create_task(self.warm_position_data()),
            ]

            # Wait with timeout
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.config.warm_timeout_seconds,
            )

            # Process results
            for idx, result in enumerate(results):
                if isinstance(result, Exception):
                    task_name = ["market_data", "balance", "position"][idx]
                    error_msg = f"Failed to warm {task_name}: {str(result)}"
                    logger.error(error_msg)
                    self.stats.errors.append(error_msg)
                    self.stats.failed_keys += 1
                else:
                    # Result is the number of keys warmed
                    self.stats.successful_keys += result

            # Calculate final statistics
            self.stats.warm_time_ms = (time.time() - start_time) * 1000
            self.stats.total_keys = self.stats.successful_keys + self.stats.failed_keys
            self.stats.cache_hit_rate = await self._calculate_hit_rate()
            self.stats.total_size_mb = await self._estimate_cache_size()

            self._last_warm_time = datetime.now()

            logger.info(
                f"Cache warming completed: {self.stats.successful_keys}/{self.stats.total_keys} keys "
                f"in {self.stats.warm_time_ms:.2f}ms"
            )

            return self.stats

        except asyncio.TimeoutError:
            logger.error(
                f"Cache warming timeout after {self.config.warm_timeout_seconds}s"
            )
            self.stats.errors.append("Warming timeout exceeded")
            return self.stats

        except Exception as e:
            logger.error(f"Cache warming failed: {e}")
            self.stats.errors.append(str(e))
            return self.stats

        finally:
            self._warming_in_progress = False

    async def warm_market_data(self) -> int:
        """
        Warm market data caches.

        Returns:
            Number of keys successfully warmed
        """
        warmed_keys = 0

        try:
            symbols = self.config.market_symbols or await self._get_active_symbols()

            # Parallel warming for each symbol
            tasks = []
            for symbol in symbols:
                tasks.extend(
                    [
                        self._warm_ohlcv(symbol),
                        self._warm_ticker(symbol),
                        self._warm_orderbook(symbol),
                    ]
                )

            # Execute in batches to avoid overwhelming the API
            batch_size = self.config.parallel_workers
            for i in range(0, len(tasks), batch_size):
                batch = tasks[i : i + batch_size]
                results = await asyncio.gather(*batch, return_exceptions=True)

                for result in results:
                    if not isinstance(result, Exception) and result:
                        warmed_keys += 1

            logger.info(
                f"Warmed {warmed_keys} market data keys for {len(symbols)} symbols"
            )
            return warmed_keys

        except Exception as e:
            logger.error(f"Failed to warm market data: {e}")
            raise

    async def _warm_ohlcv(self, symbol: str) -> bool:
        """Warm OHLCV data for a symbol."""
        try:
            cache_key = f"market:ohlcv:{symbol}:{self.config.market_ohlcv_timeframe}"

            # Fetch OHLCV data from market data service
            ohlcv_data = await self.market_data.get_ohlcv_history(
                symbol=symbol,
                timeframe=self.config.market_ohlcv_timeframe,
                limit=self.config.market_ohlcv_candles,
            )

            if ohlcv_data:
                # Convert to JSON-serializable format
                ohlcv_json = [
                    [
                        ohlcv.timestamp.isoformat(),
                        float(ohlcv.open),
                        float(ohlcv.high),
                        float(ohlcv.low),
                        float(ohlcv.close),
                        float(ohlcv.volume),
                    ]
                    for ohlcv in ohlcv_data
                ]
                # Store in cache
                await self.redis.set(
                    cache_key, json.dumps(ohlcv_json), ttl=self.config.market_ohlcv_ttl
                )
                return True

            return False

        except Exception as e:
            logger.debug(f"Failed to warm OHLCV for {symbol}: {e}")
            return False

    async def _warm_ticker(self, symbol: str) -> bool:
        """Warm ticker data for a symbol."""
        try:
            cache_key = f"market:ticker:{symbol}"

            # Fetch ticker data from market snapshot
            snapshot = await self.market_data.get_snapshot(symbol)

            if snapshot and snapshot.ticker:
                # Convert ticker to dict for caching
                ticker_data = {
                    "symbol": snapshot.ticker.symbol,
                    "last": float(snapshot.ticker.last_price),
                    "bid": float(snapshot.ticker.bid_price)
                    if snapshot.ticker.bid_price
                    else None,
                    "ask": float(snapshot.ticker.ask_price)
                    if snapshot.ticker.ask_price
                    else None,
                    "volume": float(snapshot.ticker.volume_24h),
                    "timestamp": snapshot.ticker.timestamp.isoformat(),
                }
                # Store in cache
                await self.redis.set(
                    cache_key,
                    json.dumps(ticker_data),
                    ttl=self.config.market_ticker_ttl,
                )
                return True

            return False

        except Exception as e:
            logger.debug(f"Failed to warm ticker for {symbol}: {e}")
            return False

    async def _warm_orderbook(self, symbol: str) -> bool:
        """Warm orderbook data for a symbol."""
        try:
            cache_key = f"market:orderbook:{symbol}"

            # Fetch orderbook data from market snapshot
            snapshot = await self.market_data.get_snapshot(symbol)

            if snapshot and snapshot.orderbook:
                # Convert orderbook to dict for caching
                orderbook_data = {
                    "bids": [
                        [float(price), float(size)]
                        for price, size in snapshot.orderbook.bids[
                            : self.config.market_orderbook_levels
                        ]
                    ],
                    "asks": [
                        [float(price), float(size)]
                        for price, size in snapshot.orderbook.asks[
                            : self.config.market_orderbook_levels
                        ]
                    ],
                    "timestamp": snapshot.orderbook.timestamp.isoformat(),
                }
                # Store in cache
                await self.redis.set(
                    cache_key,
                    json.dumps(orderbook_data),
                    ttl=self.config.market_orderbook_ttl,
                )
                return True

            return False

        except Exception as e:
            logger.debug(f"Failed to warm orderbook for {symbol}: {e}")
            return False

    async def warm_balance_data(self) -> int:
        """
        Warm balance data caches.

        Returns:
            Number of keys successfully warmed
        """
        warmed_keys = 0

        try:
            # Fetch total balance
            total_balance = await self.balance_fetcher.fetch_total_balance()
            if total_balance is not None:
                await self.redis.set(
                    "account:balance:total",
                    str(total_balance),
                    ttl=self.config.balance_ttl,
                )
                warmed_keys += 1

            # Fetch available balance
            available_balance = await self.balance_fetcher.fetch_available_balance()
            if available_balance is not None:
                await self.redis.set(
                    "account:balance:available",
                    str(available_balance),
                    ttl=self.config.balance_ttl,
                )
                warmed_keys += 1

            # Fetch detailed balances by asset
            detailed_balances = await self.balance_fetcher.fetch_detailed_balances()
            if detailed_balances:
                await self.redis.set(
                    "account:balance:detailed",
                    json.dumps(detailed_balances),
                    ttl=self.config.balance_ttl,
                )
                warmed_keys += 1

            logger.info(f"Warmed {warmed_keys} balance data keys")
            return warmed_keys

        except Exception as e:
            logger.error(f"Failed to warm balance data: {e}")
            raise

    async def warm_position_data(self) -> int:
        """
        Warm position data caches.

        Returns:
            Number of keys successfully warmed
        """
        warmed_keys = 0

        try:
            # Fetch active positions
            active_positions = await self.position_service.get_active_positions()
            if active_positions:
                await self.redis.set(
                    "positions:active",
                    json.dumps([p.dict() for p in active_positions]),
                    ttl=self.config.position_ttl,
                )
                warmed_keys += 1

                # Cache individual positions
                for position in active_positions:
                    await self.redis.set(
                        f"position:{position.id}",
                        json.dumps(position.dict()),
                        ttl=self.config.position_ttl,
                    )
                    warmed_keys += 1

            # Fetch recent closed positions
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.config.position_history_days)

            closed_positions = await self.position_service.get_closed_positions(
                start_date=start_date, end_date=end_date
            )

            if closed_positions:
                await self.redis.set(
                    "positions:recent_closed",
                    json.dumps([p.dict() for p in closed_positions]),
                    ttl=self.config.position_ttl,
                )
                warmed_keys += 1

            # Cache position statistics
            stats = await self.position_service.get_position_statistics()
            if stats:
                await self.redis.set(
                    "positions:statistics",
                    json.dumps(stats),
                    ttl=self.config.position_ttl,
                )
                warmed_keys += 1

            logger.info(f"Warmed {warmed_keys} position data keys")
            return warmed_keys

        except Exception as e:
            logger.error(f"Failed to warm position data: {e}")
            raise

    async def refresh_cache(
        self,
        cache_types: Optional[List[str]] = None,
        symbols: Optional[List[str]] = None,
    ) -> CacheStats:
        """
        Selectively refresh specific cache types.

        Args:
            cache_types: List of cache types to refresh ("market", "balance", "position")
            symbols: Specific symbols to refresh (for market data)

        Returns:
            CacheStats containing refresh results
        """
        if not cache_types:
            cache_types = ["market", "balance", "position"]

        start_time = time.time()
        self.stats = CacheStats()

        try:
            tasks = []

            if "market" in cache_types:
                if symbols:
                    # Store original symbols and replace temporarily
                    original_symbols = self.config.market_symbols
                    self.config.market_symbols = symbols
                    tasks.append(asyncio.create_task(self.warm_market_data()))
                    # Restore after task creation
                    self.config.market_symbols = original_symbols
                else:
                    tasks.append(asyncio.create_task(self.warm_market_data()))

            if "balance" in cache_types:
                tasks.append(asyncio.create_task(self.warm_balance_data()))

            if "position" in cache_types:
                tasks.append(asyncio.create_task(self.warm_position_data()))

            # Execute refresh tasks
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for idx, result in enumerate(results):
                if isinstance(result, Exception):
                    self.stats.errors.append(str(result))
                    self.stats.failed_keys += 1
                else:
                    self.stats.successful_keys += result

            self.stats.warm_time_ms = (time.time() - start_time) * 1000
            self.stats.total_keys = self.stats.successful_keys + self.stats.failed_keys

            logger.info(
                f"Cache refresh completed: {self.stats.successful_keys}/{self.stats.total_keys} keys "
                f"in {self.stats.warm_time_ms:.2f}ms"
            )

            return self.stats

        except Exception as e:
            logger.error(f"Cache refresh failed: {e}")
            self.stats.errors.append(str(e))
            return self.stats

    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive cache statistics.

        Returns:
            Dictionary containing cache statistics
        """
        try:
            hit_rate = await self._calculate_hit_rate()
            cache_size = await self._estimate_cache_size()

            # Get Redis info
            redis_info = await self.redis.info()

            stats = {
                "warming": {
                    "last_warm_time": self._last_warm_time.isoformat()
                    if self._last_warm_time
                    else None,
                    "last_warm_duration_ms": self.stats.warm_time_ms,
                    "total_keys_warmed": self.stats.total_keys,
                    "successful_keys": self.stats.successful_keys,
                    "failed_keys": self.stats.failed_keys,
                    "errors": self.stats.errors[-5:],  # Last 5 errors
                },
                "performance": {
                    "hit_rate": hit_rate,
                    "total_hits": self._cache_hits,
                    "total_misses": self._cache_misses,
                    "estimated_size_mb": cache_size,
                },
                "redis": {
                    "connected_clients": redis_info.get("connected_clients", 0),
                    "used_memory_mb": redis_info.get("used_memory", 0) / (1024 * 1024),
                    "expired_keys": redis_info.get("expired_keys", 0),
                    "evicted_keys": redis_info.get("evicted_keys", 0),
                    "keyspace_hits": redis_info.get("keyspace_hits", 0),
                    "keyspace_misses": redis_info.get("keyspace_misses", 0),
                },
                "config": {
                    "market_symbols": len(self.config.market_symbols),
                    "market_ohlcv_ttl": self.config.market_ohlcv_ttl,
                    "balance_ttl": self.config.balance_ttl,
                    "position_ttl": self.config.position_ttl,
                    "parallel_workers": self.config.parallel_workers,
                },
            }

            return stats

        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {}

    async def _get_active_symbols(self) -> List[str]:
        """Get list of active trading symbols."""
        try:
            # Get symbols from active positions
            positions = await self.position_service.get_active_positions()
            active_symbols = list(set(p.symbol for p in positions))

            # Add default symbols if no active positions
            if not active_symbols:
                active_symbols = [
                    "BTC/USDT",
                    "ETH/USDT",
                    "BNB/USDT",
                    "SOL/USDT",
                    "MATIC/USDT",
                    "AVAX/USDT",
                ]

            return active_symbols

        except Exception as e:
            logger.error(f"Failed to get active symbols: {e}")
            # Return default symbols
            return ["BTC/USDT", "ETH/USDT"]

    async def _calculate_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        try:
            redis_info = await self.redis.info()
            hits = redis_info.get("keyspace_hits", 0)
            misses = redis_info.get("keyspace_misses", 0)

            total = hits + misses
            if total > 0:
                return (hits / total) * 100
            return 0.0

        except Exception:
            return 0.0

    async def _estimate_cache_size(self) -> float:
        """Estimate total cache size in MB."""
        try:
            redis_info = await self.redis.info()
            # Get used memory in bytes
            used_memory = redis_info.get("used_memory", 0)
            # Convert to MB
            return used_memory / (1024 * 1024)

        except Exception:
            return 0.0

    def track_access(self, hit: bool) -> None:
        """
        Track cache access for hit rate calculation.

        Args:
            hit: Whether the access was a cache hit
        """
        if hit:
            self._cache_hits += 1
        else:
            self._cache_misses += 1

    async def invalidate_cache(self, pattern: str) -> int:
        """
        Invalidate cache keys matching a pattern.

        Args:
            pattern: Redis key pattern (e.g., "market:*")

        Returns:
            Number of keys invalidated
        """
        try:
            keys = await self.redis.scan_keys(pattern)

            if keys:
                await self.redis.delete_many(keys)
                logger.info(f"Invalidated {len(keys)} cache keys matching '{pattern}'")
                return len(keys)

            return 0

        except Exception as e:
            logger.error(f"Failed to invalidate cache: {e}")
            return 0

    async def cleanup(self) -> None:
        """Cleanup cache warmer resources."""
        # Clear statistics
        self.stats = CacheStats()
        self._cache_hits = 0
        self._cache_misses = 0
        logger.info("Cache warmer cleanup complete")
