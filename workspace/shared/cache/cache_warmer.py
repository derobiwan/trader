"""
Cache Warmer

Pre-loads frequently accessed data into cache on application startup
and implements intelligent cache warming strategies.

Features:
- Startup cache warming (market data, balances, positions)
- Parallel cache population
- Cache hit rate monitoring
- Selective refresh strategies

Author: Performance Optimization Team
Date: 2025-10-29
Sprint: 3, Stream C, Task 046
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CacheWarmingResult:
    """Result of cache warming operation"""

    category: str
    items_warmed: int
    time_taken_ms: float
    success: bool
    error_message: Optional[str] = None


class CacheWarmer:
    """
    Intelligent cache warming system.

    Warms frequently accessed data on startup and implements
    smart refresh strategies.
    """

    def __init__(
        self,
        market_data_service=None,
        account_service=None,
        position_service=None,
        llm_service=None,
    ):
        """
        Initialize cache warmer.

        Args:
            market_data_service: Market data service with caching
            account_service: Account service with balance caching
            position_service: Position service
            llm_service: LLM service with prompt caching
        """
        self.market_data_service = market_data_service
        self.account_service = account_service
        self.position_service = position_service
        self.llm_service = llm_service

        self.trading_symbols = [
            "BTC/USDT:USDT",
            "ETH/USDT:USDT",
            "SOL/USDT:USDT",
            "BNB/USDT:USDT",
            "ADA/USDT:USDT",
            "DOGE/USDT:USDT",
        ]

        logger.info("CacheWarmer initialized")

    # ========================================================================
    # Main Warming Functions
    # ========================================================================

    async def warm_all_caches(self) -> List[CacheWarmingResult]:
        """
        Warm all caches in parallel.

        Returns:
            List of warming results for each category
        """
        logger.info("🔥 Starting cache warming...")

        start_time = asyncio.get_event_loop().time()

        # Run all warming operations in parallel
        results = await asyncio.gather(
            self.warm_market_data(),
            self.warm_balance_data(),
            self.warm_position_data(),
            self.warm_llm_prompts(),
            return_exceptions=True,
        )

        # Handle exceptions
        final_results: List[CacheWarmingResult] = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Cache warming error: {result}")
                final_results.append(
                    CacheWarmingResult(
                        category="error",
                        items_warmed=0,
                        time_taken_ms=0,
                        success=False,
                        error_message=str(result),
                    )
                )
            elif isinstance(result, CacheWarmingResult):
                final_results.append(result)

        total_time = (asyncio.get_event_loop().time() - start_time) * 1000

        # Log summary
        successful = sum(1 for r in final_results if r.success)
        total_items = sum(r.items_warmed for r in final_results)

        logger.info(
            f"✓ Cache warming complete: {successful}/{len(final_results)} categories, "
            f"{total_items} items warmed in {total_time:.2f}ms"
        )

        return final_results

    # ========================================================================
    # Market Data Warming
    # ========================================================================

    async def warm_market_data(self) -> CacheWarmingResult:
        """
        Pre-load recent market data for all trading pairs.

        Returns:
            Warming result for market data
        """
        if not self.market_data_service:
            return CacheWarmingResult(
                category="market_data",
                items_warmed=0,
                time_taken_ms=0,
                success=False,
                error_message="Market data service not available",
            )

        start_time = asyncio.get_event_loop().time()
        items_warmed = 0

        try:
            # Warm OHLCV data for all symbols in parallel
            ohlcv_tasks = [
                self.market_data_service.get_ohlcv(
                    symbol=symbol,
                    timeframe="5m",
                    limit=100,
                )
                for symbol in self.trading_symbols
            ]

            ohlcv_results = await asyncio.gather(*ohlcv_tasks, return_exceptions=True)

            for symbol, result in zip(self.trading_symbols, ohlcv_results):
                if not isinstance(result, Exception):
                    items_warmed += 1
                    logger.debug(f"✓ Warmed OHLCV for {symbol}")
                else:
                    logger.warning(f"✗ Failed to warm OHLCV for {symbol}: {result}")

            # Warm ticker data for all symbols in parallel
            ticker_tasks = [
                self.market_data_service.get_ticker(symbol=symbol)
                for symbol in self.trading_symbols
            ]

            ticker_results = await asyncio.gather(*ticker_tasks, return_exceptions=True)

            for symbol, result in zip(self.trading_symbols, ticker_results):
                if not isinstance(result, Exception):
                    items_warmed += 1
                    logger.debug(f"✓ Warmed ticker for {symbol}")
                else:
                    logger.warning(f"✗ Failed to warm ticker for {symbol}: {result}")

            time_taken = (asyncio.get_event_loop().time() - start_time) * 1000

            logger.info(
                f"✓ Market data cache warmed: {items_warmed} items in {time_taken:.2f}ms"
            )

            return CacheWarmingResult(
                category="market_data",
                items_warmed=items_warmed,
                time_taken_ms=time_taken,
                success=True,
            )

        except Exception as e:
            time_taken = (asyncio.get_event_loop().time() - start_time) * 1000
            logger.error(f"✗ Market data cache warming failed: {e}")

            return CacheWarmingResult(
                category="market_data",
                items_warmed=items_warmed,
                time_taken_ms=time_taken,
                success=False,
                error_message=str(e),
            )

    # ========================================================================
    # Balance Data Warming
    # ========================================================================

    async def warm_balance_data(self) -> CacheWarmingResult:
        """
        Pre-load account balance.

        Returns:
            Warming result for balance data
        """
        if not self.account_service:
            return CacheWarmingResult(
                category="balance_data",
                items_warmed=0,
                time_taken_ms=0,
                success=False,
                error_message="Account service not available",
            )

        start_time = asyncio.get_event_loop().time()

        try:
            # Warm account balance
            balance = await self.account_service.get_balance()

            time_taken = (asyncio.get_event_loop().time() - start_time) * 1000

            logger.info(
                f"✓ Balance cache warmed: CHF {balance:.2f} in {time_taken:.2f}ms"
            )

            return CacheWarmingResult(
                category="balance_data",
                items_warmed=1,
                time_taken_ms=time_taken,
                success=True,
            )

        except Exception as e:
            time_taken = (asyncio.get_event_loop().time() - start_time) * 1000
            logger.error(f"✗ Balance cache warming failed: {e}")

            return CacheWarmingResult(
                category="balance_data",
                items_warmed=0,
                time_taken_ms=time_taken,
                success=False,
                error_message=str(e),
            )

    # ========================================================================
    # Position Data Warming
    # ========================================================================

    async def warm_position_data(self) -> CacheWarmingResult:
        """
        Pre-load all active positions.

        Returns:
            Warming result for position data
        """
        if not self.position_service:
            return CacheWarmingResult(
                category="position_data",
                items_warmed=0,
                time_taken_ms=0,
                success=False,
                error_message="Position service not available",
            )

        start_time = asyncio.get_event_loop().time()

        try:
            # Warm all positions
            positions = await self.position_service.get_all_positions()

            time_taken = (asyncio.get_event_loop().time() - start_time) * 1000

            logger.info(
                f"✓ Position cache warmed: {len(positions)} positions in {time_taken:.2f}ms"
            )

            return CacheWarmingResult(
                category="position_data",
                items_warmed=len(positions),
                time_taken_ms=time_taken,
                success=True,
            )

        except Exception as e:
            time_taken = (asyncio.get_event_loop().time() - start_time) * 1000
            logger.error(f"✗ Position cache warming failed: {e}")

            return CacheWarmingResult(
                category="position_data",
                items_warmed=0,
                time_taken_ms=time_taken,
                success=False,
                error_message=str(e),
            )

    # ========================================================================
    # LLM Prompt Warming
    # ========================================================================

    async def warm_llm_prompts(self) -> CacheWarmingResult:
        """
        Pre-load commonly used LLM prompts into cache.

        Returns:
            Warming result for LLM prompts
        """
        if not self.llm_service:
            return CacheWarmingResult(
                category="llm_prompts",
                items_warmed=0,
                time_taken_ms=0,
                success=False,
                error_message="LLM service not available",
            )

        start_time = asyncio.get_event_loop().time()

        try:
            # If LLM service has a cache warming method, call it
            if hasattr(self.llm_service, "warm_prompt_cache"):
                items_warmed = await self.llm_service.warm_prompt_cache()
            else:
                items_warmed = 0

            time_taken = (asyncio.get_event_loop().time() - start_time) * 1000

            if items_warmed > 0:
                logger.info(
                    f"✓ LLM prompt cache warmed: {items_warmed} prompts in {time_taken:.2f}ms"
                )
            else:
                logger.debug("LLM prompt cache warming skipped (not supported)")

            return CacheWarmingResult(
                category="llm_prompts",
                items_warmed=items_warmed,
                time_taken_ms=time_taken,
                success=True,
            )

        except Exception as e:
            time_taken = (asyncio.get_event_loop().time() - start_time) * 1000
            logger.error(f"✗ LLM prompt cache warming failed: {e}")

            return CacheWarmingResult(
                category="llm_prompts",
                items_warmed=0,
                time_taken_ms=time_taken,
                success=False,
                error_message=str(e),
            )

    # ========================================================================
    # Selective Refresh
    # ========================================================================

    async def refresh_critical_caches(self) -> int:
        """
        Refresh only the most critical caches.

        Used for periodic refresh during operation.

        Returns:
            Number of caches refreshed
        """
        logger.debug("Refreshing critical caches...")

        refreshed = 0

        try:
            # Refresh account balance
            if self.account_service:
                await self.account_service.get_balance()
                refreshed += 1

            # Refresh current prices for all symbols
            if self.market_data_service:
                ticker_tasks = [
                    self.market_data_service.get_ticker(symbol=symbol)
                    for symbol in self.trading_symbols
                ]
                await asyncio.gather(*ticker_tasks, return_exceptions=True)
                refreshed += len(self.trading_symbols)

            # Refresh active positions
            if self.position_service:
                await self.position_service.get_all_positions()
                refreshed += 1

            logger.debug(f"✓ Refreshed {refreshed} critical caches")

        except Exception as e:
            logger.error(f"✗ Critical cache refresh failed: {e}")

        return refreshed

    # ========================================================================
    # Cache Statistics
    # ========================================================================

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics from all services.

        Returns:
            Dictionary with cache statistics
        """
        stats: Dict[str, Any] = {
            "timestamp": datetime.utcnow(),
            "services": {},
        }

        # Market data cache stats
        if self.market_data_service and hasattr(
            self.market_data_service, "get_cache_stats"
        ):
            stats["services"]["market_data"] = (
                self.market_data_service.get_cache_stats()
            )

        # Account service cache stats
        if self.account_service and hasattr(self.account_service, "get_cache_stats"):
            stats["services"]["account"] = self.account_service.get_cache_stats()

        # LLM service cache stats
        if self.llm_service and hasattr(self.llm_service, "get_cache_stats"):
            stats["services"]["llm"] = self.llm_service.get_cache_stats()

        return stats

    def format_cache_stats_report(self, stats: Dict) -> str:
        """
        Format cache statistics as readable report.

        Args:
            stats: Cache statistics dictionary

        Returns:
            Formatted report string
        """
        report = "\n" + "=" * 60 + "\n"
        report += "CACHE STATISTICS\n"
        report += "=" * 60 + "\n\n"

        for service_name, service_stats in stats.get("services", {}).items():
            report += f"{service_name.upper()}:\n"
            report += f"  Hit Rate: {service_stats.get('hit_rate', 0):.1%}\n"
            report += f"  Total Hits: {service_stats.get('hits', 0)}\n"
            report += f"  Total Misses: {service_stats.get('misses', 0)}\n"
            report += f"  Cache Size: {service_stats.get('size', 0)} items\n"
            report += "\n"

        report += "=" * 60 + "\n"

        return report
