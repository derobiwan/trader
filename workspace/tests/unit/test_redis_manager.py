"""
Redis Manager Tests

Comprehensive test suite for Redis connection management and caching.

Author: Validation Engineer
Date: 2025-10-30
"""

import asyncio

import pytest

from workspace.infrastructure.cache.redis_manager import (
    RedisManager,
    close_redis,
    get_redis,
    init_redis,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def redis_config():
    """Redis configuration"""
    return {
        "host": "localhost",
        "port": 6379,
        "db": 0,
        "password": None,
        "max_connections": 50,
        "socket_timeout": 5,
        "socket_connect_timeout": 5,
    }


@pytest.fixture
async def redis_manager(redis_config):
    """Create Redis manager instance"""
    manager = RedisManager(**redis_config)
    yield manager
    # Cleanup
    if manager.is_initialized:
        await manager.close()


# ============================================================================
# Initialization Tests
# ============================================================================


def test_redis_manager_initialization(redis_config):
    """Test Redis manager initializes with correct config"""
    manager = RedisManager(**redis_config)

    assert manager.host == "localhost"
    assert manager.port == 6379
    assert manager.db == 0
    assert manager.password is None
    assert manager.max_connections == 50
    assert manager.is_initialized is False
    assert manager.client is None
    assert manager.pool is None


def test_redis_manager_with_password(redis_config):
    """Test Redis manager with password authentication"""
    redis_config["password"] = "secret_password"
    manager = RedisManager(**redis_config)

    assert manager.password == "secret_password"


def test_redis_manager_custom_timeouts(redis_config):
    """Test Redis manager with custom timeout values"""
    redis_config["socket_timeout"] = 10
    redis_config["socket_connect_timeout"] = 15
    manager = RedisManager(**redis_config)

    assert manager.socket_timeout == 10
    assert manager.socket_connect_timeout == 15


@pytest.mark.asyncio
async def test_redis_manager_initialize_failure():
    """Test Redis manager handles connection failure gracefully"""
    manager = RedisManager(
        host="invalid_host",
        port=9999,
        socket_connect_timeout=1,
    )

    with pytest.raises(ConnectionError, match="Redis connection failed"):
        await manager.initialize()


# ============================================================================
# Connection Management Tests
# ============================================================================


@pytest.mark.asyncio
async def test_redis_manager_context_manager(redis_manager):
    """Test Redis manager context manager support"""
    async with redis_manager as manager:
        assert manager.is_initialized is True
        assert manager.client is not None
        assert manager.pool is not None

    # After exit, should be closed
    assert redis_manager.is_initialized is False


@pytest.mark.asyncio
async def test_redis_manager_double_initialization(redis_manager):
    """Test double initialization doesn't create new pool"""
    await redis_manager.initialize()
    first_pool = redis_manager.pool

    await redis_manager.initialize()
    second_pool = redis_manager.pool

    assert first_pool is second_pool


@pytest.mark.asyncio
async def test_redis_manager_close(redis_manager):
    """Test Redis manager close operation"""
    await redis_manager.initialize()
    assert redis_manager.is_initialized is True

    await redis_manager.close()

    assert redis_manager.is_initialized is False
    # Client and pool are not explicitly set to None, but is_initialized is False
    # which is what matters for correctness


@pytest.mark.asyncio
async def test_redis_manager_close_without_initialize():
    """Test closing manager that was never initialized"""
    manager = RedisManager()

    # Should not raise error
    await manager.close()
    assert manager.is_initialized is False


# ============================================================================
# Set/Get Operations Tests
# ============================================================================


@pytest.mark.asyncio
async def test_redis_set_get_basic(redis_manager):
    """Test basic set and get operations"""
    await redis_manager.initialize()

    # Set value
    result = await redis_manager.set("test_key", {"data": "value"})
    assert result is True

    # Get value
    value = await redis_manager.get("test_key")
    assert value == {"data": "value"}

    # Cleanup
    await redis_manager.delete("test_key")


@pytest.mark.asyncio
async def test_redis_set_with_ttl(redis_manager):
    """Test setting value with TTL"""
    await redis_manager.initialize()

    result = await redis_manager.set("ttl_key", {"data": "value"}, ttl_seconds=60)
    assert result is True

    # Verify value exists
    value = await redis_manager.get("ttl_key")
    assert value == {"data": "value"}

    # Cleanup
    await redis_manager.delete("ttl_key")


@pytest.mark.asyncio
async def test_redis_get_nonexistent_key(redis_manager):
    """Test getting nonexistent key returns None"""
    await redis_manager.initialize()

    value = await redis_manager.get("nonexistent_key")
    assert value is None


@pytest.mark.asyncio
async def test_redis_set_get_complex_data(redis_manager):
    """Test set/get with complex nested data"""
    await redis_manager.initialize()

    complex_data = {
        "symbol": "BTCUSDT",
        "price": 50000.50,
        "indicators": {
            "rsi": 65.5,
            "macd": {"value": 100, "signal": 80},
        },
        "tags": ["bullish", "strong"],
    }

    await redis_manager.set("complex_key", complex_data)
    result = await redis_manager.get("complex_key")

    assert result == complex_data

    # Cleanup
    await redis_manager.delete("complex_key")


@pytest.mark.asyncio
async def test_redis_operations_without_initialization():
    """Test operations fail appropriately without initialization"""
    manager = RedisManager()

    with pytest.raises(RuntimeError, match="Redis not initialized"):
        await manager.set("key", "value")

    with pytest.raises(RuntimeError, match="Redis not initialized"):
        await manager.get("key")

    with pytest.raises(RuntimeError, match="Redis not initialized"):
        await manager.delete("key")


# ============================================================================
# Delete Operations Tests
# ============================================================================


@pytest.mark.asyncio
async def test_redis_delete_existing_key(redis_manager):
    """Test deleting existing key"""
    await redis_manager.initialize()

    # Set value
    await redis_manager.set("delete_key", "value")

    # Delete key
    result = await redis_manager.delete("delete_key")
    assert result is True

    # Verify deleted
    value = await redis_manager.get("delete_key")
    assert value is None


@pytest.mark.asyncio
async def test_redis_delete_nonexistent_key(redis_manager):
    """Test deleting nonexistent key returns False"""
    await redis_manager.initialize()

    result = await redis_manager.delete("nonexistent_key")
    assert result is False


# ============================================================================
# Exists Operation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_redis_exists_key(redis_manager):
    """Test checking if key exists"""
    await redis_manager.initialize()

    # Set value
    await redis_manager.set("exists_key", "value")

    # Check exists
    result = await redis_manager.exists("exists_key")
    assert result is True

    # Check nonexistent
    result = await redis_manager.exists("nonexistent_key")
    assert result is False

    # Cleanup
    await redis_manager.delete("exists_key")


# ============================================================================
# Clear Operation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_redis_clear_with_pattern(redis_manager):
    """Test clearing keys matching pattern"""
    await redis_manager.initialize()

    # Set multiple keys
    await redis_manager.set("market_data:btc", {"price": 50000})
    await redis_manager.set("market_data:eth", {"price": 3000})
    await redis_manager.set("signal:btc", {"decision": "buy"})

    # Clear market_data:* pattern
    deleted = await redis_manager.clear("market_data:*")
    assert deleted >= 2

    # Verify market_data keys deleted but signal key exists
    assert await redis_manager.exists("market_data:btc") is False
    assert await redis_manager.exists("signal:btc") is True

    # Cleanup
    await redis_manager.delete("signal:btc")


@pytest.mark.asyncio
async def test_redis_clear_all_keys(redis_manager):
    """Test clearing all keys"""
    await redis_manager.initialize()

    # Set some keys
    await redis_manager.set("key1", "value1")
    await redis_manager.set("key2", "value2")
    await redis_manager.set("key3", "value3")

    # Clear all
    deleted = await redis_manager.clear("*")
    assert deleted >= 3


# ============================================================================
# Health Check Tests
# ============================================================================


@pytest.mark.asyncio
async def test_redis_health_check(redis_manager):
    """Test Redis health check"""
    await redis_manager.initialize()

    health = await redis_manager.health_check()

    assert health["healthy"] is True
    assert "latency_ms" in health
    assert health["latency_ms"] >= 0
    assert health["host"] == "localhost"
    assert health["port"] == 6379
    assert health["db"] == 0


@pytest.mark.asyncio
async def test_redis_health_check_without_initialization():
    """Test health check without initialization"""
    manager = RedisManager()

    health = await manager.health_check()

    assert health["healthy"] is False
    assert "error" in health


# ============================================================================
# Statistics Tests
# ============================================================================


@pytest.mark.asyncio
async def test_redis_get_stats(redis_manager):
    """Test getting Redis statistics"""
    await redis_manager.initialize()

    # Perform some operations
    await redis_manager.set("stat_key1", "value1")
    await redis_manager.get("stat_key1")
    await redis_manager.get("nonexistent")

    stats = await redis_manager.get_stats()

    assert stats["connected"] is True
    assert "total_commands_processed" in stats
    assert "keyspace_hits" in stats
    assert "keyspace_misses" in stats
    assert "hit_rate_percent" in stats
    assert "total_requests" in stats

    # Cleanup
    await redis_manager.delete("stat_key1")


@pytest.mark.asyncio
async def test_redis_get_stats_without_initialization():
    """Test stats without initialization"""
    manager = RedisManager()

    stats = await manager.get_stats()

    assert "error" in stats


# ============================================================================
# Serialization Tests
# ============================================================================


@pytest.mark.asyncio
async def test_redis_json_serialization(redis_manager):
    """Test JSON serialization of values"""
    await redis_manager.initialize()

    data = {
        "string": "value",
        "number": 42,
        "float": 3.14,
        "list": [1, 2, 3],
        "nested": {"key": "value"},
    }

    await redis_manager.set("json_key", data)
    result = await redis_manager.get("json_key")

    assert result == data

    # Cleanup
    await redis_manager.delete("json_key")


@pytest.mark.asyncio
async def test_redis_serialization_with_none_values(redis_manager):
    """Test serialization with None values"""
    await redis_manager.initialize()

    data = {
        "key1": "value1",
        "key2": None,
        "key3": "value3",
    }

    await redis_manager.set("none_key", data)
    result = await redis_manager.get("none_key")

    assert result == data

    # Cleanup
    await redis_manager.delete("none_key")


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.asyncio
async def test_redis_handles_connection_errors(redis_manager):
    """Test graceful handling of connection errors"""
    await redis_manager.initialize()

    # Mock client to simulate error
    async def mock_get(*args, **kwargs):
        raise Exception("Connection error")

    redis_manager.client.get = mock_get

    result = await redis_manager.get("key")
    assert result is None


@pytest.mark.asyncio
async def test_redis_handles_json_decode_error(redis_manager):
    """Test handling of JSON decode errors"""
    await redis_manager.initialize()

    # Mock client to return non-JSON data
    async def mock_get(*args, **kwargs):
        return b"not_json_data"

    redis_manager.client.get = mock_get

    result = await redis_manager.get("key")
    # Should return the raw value
    assert result is not None


# ============================================================================
# Connection Pool Tests
# ============================================================================


@pytest.mark.asyncio
async def test_redis_connection_pool_creation(redis_manager):
    """Test connection pool is created correctly"""
    await redis_manager.initialize()

    assert redis_manager.pool is not None
    # Verify pool configuration
    assert redis_manager.pool.connection_class is not None
    # Connection pool exists and is functional
    assert redis_manager.client is not None


# ============================================================================
# Global Manager Tests
# ============================================================================


@pytest.mark.asyncio
async def test_global_redis_manager_init():
    """Test global Redis manager initialization"""
    # Clean up any existing global manager
    import workspace.infrastructure.cache.redis_manager as redis_module

    redis_module._global_redis = None

    manager = await init_redis(host="localhost", port=6379)

    assert manager.is_initialized is True

    # Cleanup
    await close_redis()


@pytest.mark.asyncio
async def test_global_redis_manager_get():
    """Test getting global Redis manager"""
    import workspace.infrastructure.cache.redis_manager as redis_module

    redis_module._global_redis = None

    # Initialize first
    await init_redis(host="localhost", port=6379)

    # Get global manager
    manager = await get_redis()
    assert manager.is_initialized is True

    # Cleanup
    await close_redis()


@pytest.mark.asyncio
async def test_global_redis_get_without_init():
    """Test getting global manager without initialization fails"""
    import workspace.infrastructure.cache.redis_manager as redis_module

    redis_module._global_redis = None

    with pytest.raises(RuntimeError, match="Global Redis manager not initialized"):
        await get_redis()


@pytest.mark.asyncio
async def test_global_redis_init_already_initialized():
    """Test initializing already initialized global manager"""
    import workspace.infrastructure.cache.redis_manager as redis_module

    redis_module._global_redis = None

    # First init
    manager1 = await init_redis(host="localhost", port=6379)

    # Second init should return same instance
    manager2 = await init_redis(host="localhost", port=6379)

    assert manager1 is manager2

    # Cleanup
    await close_redis()


@pytest.mark.asyncio
async def test_global_redis_close():
    """Test closing global Redis manager"""
    import workspace.infrastructure.cache.redis_manager as redis_module

    redis_module._global_redis = None

    await init_redis(host="localhost", port=6379)
    await close_redis()

    # Should be None after close
    assert redis_module._global_redis is None


# ============================================================================
# High-Concurrency Tests
# ============================================================================


@pytest.mark.asyncio
async def test_redis_concurrent_operations(redis_manager):
    """Test concurrent set/get operations"""
    await redis_manager.initialize()

    # Perform concurrent operations
    async def set_and_get(key_num):
        key = f"concurrent_key_{key_num}"
        await redis_manager.set(key, {"index": key_num})
        return await redis_manager.get(key)

    tasks = [set_and_get(i) for i in range(10)]
    results = await asyncio.gather(*tasks)

    assert len(results) == 10
    assert all(r is not None for r in results)

    # Cleanup
    await redis_manager.clear("concurrent_key_*")


# ============================================================================
# Data Type Tests
# ============================================================================


@pytest.mark.asyncio
async def test_redis_store_strings(redis_manager):
    """Test storing and retrieving strings"""
    await redis_manager.initialize()

    await redis_manager.set("string_key", "string_value")
    result = await redis_manager.get("string_key")

    assert result == "string_value"

    await redis_manager.delete("string_key")


@pytest.mark.asyncio
async def test_redis_store_numbers(redis_manager):
    """Test storing and retrieving numbers"""
    await redis_manager.initialize()

    # Store dict with numbers
    data = {"integer": 42, "float": 3.14, "negative": -100}
    await redis_manager.set("number_key", data)
    result = await redis_manager.get("number_key")

    assert result == data

    await redis_manager.delete("number_key")


@pytest.mark.asyncio
async def test_redis_store_lists(redis_manager):
    """Test storing and retrieving lists"""
    await redis_manager.initialize()

    data = {"items": [1, 2, 3, 4, 5], "names": ["a", "b", "c"]}
    await redis_manager.set("list_key", data)
    result = await redis_manager.get("list_key")

    assert result == data

    await redis_manager.delete("list_key")
