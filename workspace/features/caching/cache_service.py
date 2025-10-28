"""
Redis Caching Service

Provides caching layer for market data and LLM responses.

Author: Trading System Implementation Team
Date: 2025-10-28
"""

import logging
import json
import hashlib
from typing import Any, Optional
from datetime import timedelta
from decimal import Decimal

logger = logging.getLogger(__name__)


class CacheService:
    """
    Redis-based caching service

    Provides caching for:
    - Market data (OHLCV, ticker, indicators)
    - LLM responses (signals, reasoning)
    - Exchange data (balances, positions)

    Note: Currently uses in-memory dict. In production, use Redis.
    """

    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        default_ttl_seconds: int = 300,
        enabled: bool = True,
    ):
        """
        Initialize cache service

        Args:
            redis_host: Redis server host
            redis_port: Redis server port
            redis_db: Redis database number
            default_ttl_seconds: Default TTL for cached entries
            enabled: Whether caching is enabled
        """
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_db = redis_db
        self.default_ttl_seconds = default_ttl_seconds
        self.enabled = enabled

        # In-memory cache (TODO: Replace with Redis)
        self._cache: dict[str, Any] = {}
        self._ttl: dict[str, float] = {}

        # Statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "evictions": 0,
        }

        if enabled:
            logger.info(f"Cache Service initialized (in-memory mode)")
        else:
            logger.info("Cache Service initialized (disabled)")

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        if not self.enabled:
            return None

        try:
            import time

            # Check if key exists
            if key not in self._cache:
                self.stats["misses"] += 1
                return None

            # Check if expired
            if key in self._ttl and time.time() > self._ttl[key]:
                del self._cache[key]
                del self._ttl[key]
                self.stats["evictions"] += 1
                self.stats["misses"] += 1
                return None

            # Cache hit
            self.stats["hits"] += 1
            value = self._cache[key]

            # Deserialize if JSON string
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value

            return value

        except Exception as e:
            logger.error(f"Cache get error for key '{key}': {e}", exc_info=True)
            self.stats["misses"] += 1
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
    ) -> bool:
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time-to-live in seconds (None = default)

        Returns:
            True if successful
        """
        if not self.enabled:
            return False

        try:
            import time

            # Serialize value
            if isinstance(value, (dict, list)):
                serialized = json.dumps(value, default=str)
            elif isinstance(value, Decimal):
                serialized = str(value)
            else:
                serialized = value

            # Store in cache
            self._cache[key] = serialized

            # Set TTL
            ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
            self._ttl[key] = time.time() + ttl

            self.stats["sets"] += 1
            logger.debug(f"Cached '{key}' with TTL {ttl}s")

            return True

        except Exception as e:
            logger.error(f"Cache set error for key '{key}': {e}", exc_info=True)
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete key from cache

        Args:
            key: Cache key to delete

        Returns:
            True if key existed and was deleted
        """
        if not self.enabled:
            return False

        try:
            if key in self._cache:
                del self._cache[key]
                if key in self._ttl:
                    del self._ttl[key]
                self.stats["deletes"] += 1
                return True
            return False

        except Exception as e:
            logger.error(f"Cache delete error for key '{key}': {e}", exc_info=True)
            return False

    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache

        Args:
            key: Cache key

        Returns:
            True if key exists and is not expired
        """
        value = await self.get(key)
        return value is not None

    async def clear(self, pattern: Optional[str] = None) -> int:
        """
        Clear cache entries

        Args:
            pattern: Optional pattern to match keys (e.g., "market_data:*")

        Returns:
            Number of keys deleted
        """
        if not self.enabled:
            return 0

        try:
            if pattern is None:
                # Clear all
                count = len(self._cache)
                self._cache.clear()
                self._ttl.clear()
                return count
            else:
                # Clear by pattern (simple prefix match)
                keys_to_delete = [k for k in self._cache.keys() if k.startswith(pattern.rstrip("*"))]
                for key in keys_to_delete:
                    await self.delete(key)
                return len(keys_to_delete)

        except Exception as e:
            logger.error(f"Cache clear error: {e}", exc_info=True)
            return 0

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Dictionary with cache stats
        """
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (
            (self.stats["hits"] / total_requests * 100)
            if total_requests > 0
            else 0
        )

        return {
            **self.stats,
            "total_requests": total_requests,
            "hit_rate": f"{hit_rate:.2f}%",
            "cache_size": len(self._cache),
            "enabled": self.enabled,
        }

    @staticmethod
    def generate_key(*args: Any, prefix: str = "") -> str:
        """
        Generate cache key from arguments

        Args:
            *args: Arguments to include in key
            prefix: Optional key prefix

        Returns:
            Cache key string
        """
        # Convert args to strings
        parts = [str(arg) for arg in args]

        # Create hash of parts
        content = ":".join(parts)
        hash_suffix = hashlib.md5(content.encode()).hexdigest()[:8]

        # Construct key
        if prefix:
            return f"{prefix}:{hash_suffix}"
        else:
            return hash_suffix

    async def get_or_set(
        self,
        key: str,
        fetch_func: callable,
        ttl_seconds: Optional[int] = None,
    ) -> Any:
        """
        Get from cache or fetch and set

        Args:
            key: Cache key
            fetch_func: Async function to fetch value if not cached
            ttl_seconds: TTL for cached value

        Returns:
            Cached or fetched value
        """
        # Try to get from cache
        value = await self.get(key)
        if value is not None:
            return value

        # Fetch value
        value = await fetch_func()

        # Cache it
        await self.set(key, value, ttl_seconds)

        return value


# Export
__all__ = ["CacheService"]
