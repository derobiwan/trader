"""
Redis Connection Manager

Manages Redis connections with connection pooling and error handling.

Author: Infrastructure Specialist
Date: 2025-10-28

Usage:
    from workspace.infrastructure.cache import init_redis, get_redis

    # Initialize Redis
    await init_redis(host="localhost", port=6379)

    # Get Redis instance
    redis = await get_redis()
    await redis.set("key", {"data": "value"}, ttl_seconds=300)
    value = await redis.get("key")
"""

import json
import logging
from typing import Any, Dict, Optional

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class RedisManager:
    """
    Redis connection manager with connection pooling

    Provides async Redis operations with automatic serialization,
    connection pooling, and error handling.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        max_connections: int = 50,
        socket_timeout: int = 5,
        socket_connect_timeout: int = 5,
    ):
        """
        Initialize Redis manager

        Args:
            host: Redis host
            port: Redis port
            db: Redis database number (0-15)
            password: Redis password (if auth enabled)
            max_connections: Maximum connections in pool
            socket_timeout: Socket timeout in seconds
            socket_connect_timeout: Connection timeout in seconds
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.max_connections = max_connections
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout

        self.pool: Optional[redis.ConnectionPool] = None
        self.client: Optional[redis.Redis] = None
        self.is_initialized: bool = False

    async def initialize(self) -> None:
        """
        Initialize Redis connection pool

        Raises:
            ConnectionError: If unable to connect to Redis
        """
        if self.is_initialized:
            logger.warning("Redis manager already initialized")
            return

        try:
            logger.info(
                f"Initializing Redis connection: {self.host}:{self.port}/{self.db}"
            )

            # Create connection pool
            self.pool = redis.ConnectionPool(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                max_connections=self.max_connections,
                decode_responses=False,  # We handle encoding/decoding
                socket_timeout=self.socket_timeout,
                socket_connect_timeout=self.socket_connect_timeout,
            )

            # Create Redis client
            self.client = redis.Redis(connection_pool=self.pool)

            # Test connection
            await self.client.ping()

            self.is_initialized = True
            logger.info(f"✓ Redis connected: {self.host}:{self.port}/{self.db}")

        except Exception as e:
            logger.error(f"✗ Failed to connect to Redis: {e}", exc_info=True)
            raise ConnectionError(f"Redis connection failed: {e}") from e

    async def close(self) -> None:
        """Close Redis connection pool"""
        if not self.is_initialized:
            return

        logger.info("Closing Redis connection...")

        if self.client:
            await self.client.close()

        if self.pool:
            await self.pool.disconnect()

        self.is_initialized = False
        logger.info("✓ Redis connection closed")

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from Redis

        Args:
            key: Cache key

        Returns:
            Deserialized value or None if not found
        """
        if not self.is_initialized:
            raise RuntimeError("Redis not initialized. Call initialize() first.")

        try:
            value = await self.client.get(key)
            if value is None:
                return None

            # Deserialize JSON
            return json.loads(value)

        except json.JSONDecodeError:
            # Return raw value if not JSON
            logger.warning(f"Key '{key}' contains non-JSON data")
            return value.decode("utf-8") if isinstance(value, bytes) else value

        except Exception as e:
            logger.error(f"Redis GET error for key '{key}': {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
    ) -> bool:
        """
        Set value in Redis with optional TTL

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl_seconds: Time-to-live in seconds (None = no expiration)

        Returns:
            True if successful
        """
        if not self.is_initialized:
            raise RuntimeError("Redis not initialized. Call initialize() first.")

        try:
            # Serialize to JSON
            serialized = json.dumps(value, default=str)

            # Store in Redis
            if ttl_seconds:
                await self.client.setex(key, ttl_seconds, serialized)
            else:
                await self.client.set(key, serialized)

            logger.debug(f"Redis SET: {key} (TTL: {ttl_seconds}s)")
            return True

        except Exception as e:
            logger.error(f"Redis SET error for key '{key}': {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete key from Redis

        Args:
            key: Cache key to delete

        Returns:
            True if key existed and was deleted
        """
        if not self.is_initialized:
            raise RuntimeError("Redis not initialized. Call initialize() first.")

        try:
            result = await self.client.delete(key)
            return result > 0

        except Exception as e:
            logger.error(f"Redis DELETE error for key '{key}': {e}")
            return False

    async def exists(self, key: str) -> bool:
        """
        Check if key exists in Redis

        Args:
            key: Cache key

        Returns:
            True if key exists
        """
        if not self.is_initialized:
            raise RuntimeError("Redis not initialized. Call initialize() first.")

        try:
            return await self.client.exists(key) > 0

        except Exception as e:
            logger.error(f"Redis EXISTS error for key '{key}': {e}")
            return False

    async def clear(self, pattern: str = "*") -> int:
        """
        Clear keys matching pattern

        Args:
            pattern: Pattern to match (e.g., "market_data:*")

        Returns:
            Number of keys deleted
        """
        if not self.is_initialized:
            raise RuntimeError("Redis not initialized. Call initialize() first.")

        try:
            # Find matching keys
            keys = []
            async for key in self.client.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                deleted = await self.client.delete(*keys)
                logger.info(f"Cleared {deleted} keys matching '{pattern}'")
                return deleted

            return 0

        except Exception as e:
            logger.error(f"Redis CLEAR error for pattern '{pattern}': {e}")
            return 0

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get Redis statistics

        Returns:
            Dictionary with Redis stats
        """
        if not self.is_initialized:
            return {"error": "Not initialized"}

        try:
            info = await self.client.info("stats")

            keyspace_hits = info.get("keyspace_hits", 0)
            keyspace_misses = info.get("keyspace_misses", 0)
            total_requests = keyspace_hits + keyspace_misses

            hit_rate = 100 * keyspace_hits / total_requests if total_requests > 0 else 0

            return {
                "connected": True,
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": keyspace_hits,
                "keyspace_misses": keyspace_misses,
                "hit_rate_percent": round(hit_rate, 2),
                "total_requests": total_requests,
            }

        except Exception as e:
            logger.error(f"Redis stats error: {e}")
            return {"error": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on Redis connection

        Returns:
            Health status dictionary
        """
        if not self.is_initialized:
            return {
                "healthy": False,
                "error": "Not initialized",
            }

        try:
            import asyncio

            start_time = asyncio.get_event_loop().time()

            # Test ping
            await self.client.ping()

            latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            return {
                "healthy": True,
                "latency_ms": round(latency_ms, 2),
                "host": self.host,
                "port": self.port,
                "db": self.db,
            }

        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "healthy": False,
                "error": str(e),
            }

    async def __aenter__(self):
        """Context manager entry"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.close()


# Global Redis instance for convenience
_global_redis: Optional[RedisManager] = None


async def get_redis() -> RedisManager:
    """
    Get global Redis instance

    Returns:
        RedisManager instance

    Raises:
        RuntimeError: If Redis not initialized

    Example:
        redis = await get_redis()
        await redis.set("key", "value", ttl_seconds=300)
    """
    global _global_redis
    if _global_redis is None or not _global_redis.is_initialized:
        raise RuntimeError(
            "Global Redis manager not initialized. "
            "Call init_redis() first or use RedisManager() directly."
        )
    return _global_redis


async def init_redis(
    host: str = "localhost",
    port: int = 6379,
    db: int = 0,
    password: Optional[str] = None,
    **kwargs,
) -> RedisManager:
    """
    Initialize global Redis manager

    Args:
        host: Redis host
        port: Redis port
        db: Redis database number
        password: Redis password
        **kwargs: Additional configuration

    Returns:
        RedisManager instance

    Example:
        import os
        redis = await init_redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD")
        )
    """
    global _global_redis

    if _global_redis and _global_redis.is_initialized:
        logger.warning("Global Redis manager already initialized")
        return _global_redis

    _global_redis = RedisManager(
        host=host,
        port=port,
        db=db,
        password=password,
        **kwargs,
    )
    await _global_redis.initialize()

    return _global_redis


async def close_redis() -> None:
    """
    Close global Redis manager

    Should be called on application shutdown.

    Example:
        # On shutdown
        await close_redis()
    """
    global _global_redis
    if _global_redis:
        await _global_redis.close()
        _global_redis = None


# CLI for testing connection
async def test_connection():
    """Test Redis connection and display info"""
    import os

    print("Testing Redis connection...")

    redis_manager = RedisManager(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=int(os.getenv("REDIS_DB", "0")),
        password=os.getenv("REDIS_PASSWORD"),
    )

    try:
        await redis_manager.initialize()

        # Health check
        health = await redis_manager.health_check()
        print("\n✓ Redis connection successful!")
        print(f"  Latency: {health['latency_ms']}ms")
        print(f"  Host: {health['host']}:{health['port']}")
        print(f"  Database: {health['db']}")

        # Test set/get
        test_key = "test_connection_key"
        await redis_manager.set(test_key, {"test": "value"}, ttl_seconds=60)
        value = await redis_manager.get(test_key)
        print(f"\n  Test set/get: {value}")
        await redis_manager.delete(test_key)

        # Get stats
        stats = await redis_manager.get_stats()
        print(f"\n  Total commands: {stats.get('total_commands_processed', 0)}")
        print(f"  Hit rate: {stats.get('hit_rate_percent', 0):.2f}%")

        await redis_manager.close()
        print("\n✓ Connection test complete")

    except Exception as e:
        print(f"\n✗ Connection failed: {e}")
        raise


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_connection())
