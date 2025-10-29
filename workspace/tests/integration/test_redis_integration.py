"""
Redis Integration Tests

Tests Redis connection, caching operations, and performance.

Author: Infrastructure Specialist
Date: 2025-10-28
"""

import pytest
import asyncio
from decimal import Decimal

from workspace.infrastructure.cache import RedisManager, init_redis, get_redis, close_redis
from workspace.features.caching.cache_service import CacheService


@pytest.fixture(scope="module")
async def redis_manager():
    """Initialize Redis manager for tests"""
    manager = await init_redis(
        host="localhost",
        port=6379,
        db=0,
    )
    yield manager
    await close_redis()


@pytest.mark.asyncio
async def test_redis_connection():
    """Test basic Redis connection"""
    manager = RedisManager(
        host="localhost",
        port=6379,
        db=0,
    )

    await manager.initialize()

    # Test ping
    health = await manager.health_check()
    assert health["healthy"] is True
    assert health["latency_ms"] < 10  # Should be very fast locally
    print(f"Redis health: {health}")

    await manager.close()


@pytest.mark.asyncio
async def test_redis_set_get(redis_manager):
    """Test basic set/get operations"""
    # Set simple value
    success = await redis_manager.set("test_key", "test_value", ttl_seconds=60)
    assert success is True

    # Get value
    value = await redis_manager.get("test_key")
    assert value == "test_value"

    # Cleanup
    await redis_manager.delete("test_key")


@pytest.mark.asyncio
async def test_redis_dict_serialization(redis_manager):
    """Test dictionary serialization"""
    test_data = {
        "symbol": "BTC/USDT",
        "price": 45000.50,
        "volume": 12345.67,
        "timestamp": "2025-10-28T12:00:00Z",
    }

    # Set dict
    success = await redis_manager.set("test_dict", test_data, ttl_seconds=60)
    assert success is True

    # Get dict
    value = await redis_manager.get("test_dict")
    assert value == test_data
    assert value["symbol"] == "BTC/USDT"
    assert value["price"] == 45000.50

    # Cleanup
    await redis_manager.delete("test_dict")


@pytest.mark.asyncio
async def test_redis_ttl_expiration(redis_manager):
    """Test TTL and expiration"""
    # Set value with short TTL
    await redis_manager.set("ttl_test", "value", ttl_seconds=1)

    # Should exist immediately
    value = await redis_manager.get("ttl_test")
    assert value == "value"

    # Wait for expiration
    await asyncio.sleep(1.1)

    # Should be expired
    value = await redis_manager.get("ttl_test")
    assert value is None


@pytest.mark.asyncio
async def test_redis_exists(redis_manager):
    """Test key existence check"""
    # Set key
    await redis_manager.set("exists_test", "value", ttl_seconds=60)

    # Should exist
    exists = await redis_manager.exists("exists_test")
    assert exists is True

    # Delete key
    await redis_manager.delete("exists_test")

    # Should not exist
    exists = await redis_manager.exists("exists_test")
    assert exists is False


@pytest.mark.asyncio
async def test_redis_clear_pattern(redis_manager):
    """Test clearing keys by pattern"""
    # Set multiple keys
    await redis_manager.set("market_data:BTC", {"price": 45000}, ttl_seconds=60)
    await redis_manager.set("market_data:ETH", {"price": 2500}, ttl_seconds=60)
    await redis_manager.set("market_data:SOL", {"price": 100}, ttl_seconds=60)
    await redis_manager.set("other_data:test", {"value": 123}, ttl_seconds=60)

    # Clear market_data keys
    count = await redis_manager.clear("market_data:*")
    assert count == 3

    # Other key should still exist
    exists = await redis_manager.exists("other_data:test")
    assert exists is True

    # Cleanup
    await redis_manager.delete("other_data:test")


@pytest.mark.asyncio
async def test_redis_stats(redis_manager):
    """Test Redis statistics"""
    # Perform some operations
    await redis_manager.set("stats_test_1", "value", ttl_seconds=60)
    await redis_manager.set("stats_test_2", "value", ttl_seconds=60)
    await redis_manager.get("stats_test_1")  # Hit
    await redis_manager.get("nonexistent")  # Miss

    # Get stats
    stats = await redis_manager.get_stats()
    print(f"Redis stats: {stats}")

    assert "keyspace_hits" in stats
    assert "keyspace_misses" in stats
    assert stats["connected"] is True

    # Cleanup
    await redis_manager.delete("stats_test_1")
    await redis_manager.delete("stats_test_2")


@pytest.mark.asyncio
async def test_cache_service_redis_backend():
    """Test CacheService with Redis backend"""
    # Initialize Redis
    await init_redis()

    # Create cache service with Redis
    cache = CacheService(use_redis=True)

    # Test set and get
    await cache.set("cache_test_key", {"value": 123}, ttl_seconds=60)
    result = await cache.get("cache_test_key")
    assert result == {"value": 123}

    # Test cache hit
    result2 = await cache.get("cache_test_key")
    assert result2 == {"value": 123}

    # Check stats
    stats = cache.get_stats()
    print(f"Cache stats: {stats}")
    assert stats["hits"] >= 1
    assert stats["backend"] == "redis"

    # Cleanup
    await cache.delete("cache_test_key")
    await close_redis()


@pytest.mark.asyncio
async def test_cache_service_fallback():
    """Test CacheService fallback to in-memory when Redis unavailable"""
    # Create cache service pointing to non-existent Redis
    cache = CacheService(
        use_redis=True,
        redis_host="nonexistent-host",
        redis_port=9999,
    )

    # This should fall back to in-memory
    await cache.set("fallback_test", {"value": 456}, ttl_seconds=60)
    result = await cache.get("fallback_test")

    # Should work with in-memory fallback
    assert result == {"value": 456}


@pytest.mark.asyncio
async def test_cache_service_get_or_set():
    """Test get_or_set functionality"""
    await init_redis()
    cache = CacheService(use_redis=True)

    fetch_count = 0

    async def fetch_data():
        """Simulates expensive data fetch"""
        nonlocal fetch_count
        fetch_count += 1
        await asyncio.sleep(0.01)  # Simulate delay
        return {"expensive": "data"}

    # First call should fetch
    result1 = await cache.get_or_set("get_or_set_test", fetch_data, ttl_seconds=60)
    assert result1 == {"expensive": "data"}
    assert fetch_count == 1

    # Second call should use cache
    result2 = await cache.get_or_set("get_or_set_test", fetch_data, ttl_seconds=60)
    assert result2 == {"expensive": "data"}
    assert fetch_count == 1  # Still 1, not fetched again

    # Cleanup
    await cache.delete("get_or_set_test")
    await close_redis()


@pytest.mark.asyncio
async def test_redis_performance(redis_manager):
    """Test Redis performance"""
    import time

    # Measure SET performance
    set_times = []
    for i in range(100):
        start = time.time()
        await redis_manager.set(f"perf_test_{i}", {"index": i}, ttl_seconds=60)
        set_times.append((time.time() - start) * 1000)

    avg_set_ms = sum(set_times) / len(set_times)
    p95_set_ms = sorted(set_times)[int(len(set_times) * 0.95)]

    print(f"SET performance: avg={avg_set_ms:.2f}ms, p95={p95_set_ms:.2f}ms")
    assert p95_set_ms < 2  # Should be <2ms p95 for SET

    # Measure GET performance
    get_times = []
    for i in range(100):
        start = time.time()
        await redis_manager.get(f"perf_test_{i}")
        get_times.append((time.time() - start) * 1000)

    avg_get_ms = sum(get_times) / len(get_times)
    p95_get_ms = sorted(get_times)[int(len(get_times) * 0.95)]

    print(f"GET performance: avg={avg_get_ms:.2f}ms, p95={p95_get_ms:.2f}ms")
    assert p95_get_ms < 1  # Should be <1ms p95 for GET

    # Cleanup
    await redis_manager.clear("perf_test_*")


@pytest.mark.asyncio
async def test_cache_ttl_expiration():
    """Test cache TTL with Redis"""
    await init_redis()
    cache = CacheService(use_redis=True)

    # Set with 1 second TTL
    await cache.set("ttl_cache_test", "value", ttl_seconds=1)

    # Should exist immediately
    value = await cache.get("ttl_cache_test")
    assert value == "value"

    # Wait for expiration
    await asyncio.sleep(1.1)

    # Should be expired
    value2 = await cache.get("ttl_cache_test")
    assert value2 is None

    await close_redis()


@pytest.mark.asyncio
async def test_cache_clear_pattern():
    """Test clearing cache by pattern"""
    await init_redis()
    cache = CacheService(use_redis=True)

    # Set multiple keys
    await cache.set("market:BTC", {"price": 45000}, ttl_seconds=60)
    await cache.set("market:ETH", {"price": 2500}, ttl_seconds=60)
    await cache.set("llm:request_1", {"response": "data"}, ttl_seconds=60)

    # Clear market keys
    count = await cache.clear("market:*")
    assert count == 2

    # LLM key should still exist
    exists = await cache.exists("llm:request_1")
    assert exists is True

    # Cleanup
    await cache.delete("llm:request_1")
    await close_redis()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
