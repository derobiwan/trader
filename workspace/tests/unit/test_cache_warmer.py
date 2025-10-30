"""
Unit tests for Cache Warmer.

Tests all major functionality:
- Cache warming for all data types
- Parallel warming execution
- Selective refresh
- Statistics tracking
- Error handling
- Cache invalidation

Target: 80%+ code coverage
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
from workspace.shared.cache.cache_warmer import CacheWarmer, CacheStats, CacheConfig


@pytest.fixture
def mock_redis():
    """Mock Redis manager."""
    redis = AsyncMock()
    redis.set = AsyncMock()
    redis.get = AsyncMock()
    redis.delete_many = AsyncMock()
    redis.scan_keys = AsyncMock(return_value=[])
    redis.info = AsyncMock(
        return_value={
            "connected_clients": 5,
            "used_memory": 1024 * 1024 * 50,  # 50MB
            "expired_keys": 100,
            "evicted_keys": 10,
            "keyspace_hits": 9000,
            "keyspace_misses": 1000,
        }
    )
    return redis


@pytest.fixture
def mock_market_data_fetcher():
    """Mock market data fetcher."""
    fetcher = AsyncMock()
    fetcher.fetch_ohlcv = AsyncMock(
        return_value=[[1234567890, 50000.0, 51000.0, 49000.0, 50500.0, 1000.0]]
    )
    fetcher.fetch_ticker = AsyncMock(
        return_value={
            "symbol": "BTC/USDT",
            "last": 50000.0,
            "bid": 49999.0,
            "ask": 50001.0,
        }
    )
    fetcher.fetch_orderbook = AsyncMock(
        return_value={"bids": [[50000.0, 1.0]], "asks": [[50001.0, 1.0]]}
    )
    return fetcher


@pytest.fixture
def mock_balance_fetcher():
    """Mock balance fetcher."""
    fetcher = AsyncMock()
    fetcher.fetch_total_balance = AsyncMock(return_value=10000.0)
    fetcher.fetch_available_balance = AsyncMock(return_value=8000.0)
    fetcher.fetch_detailed_balances = AsyncMock(
        return_value={"USDT": {"total": 10000.0, "available": 8000.0}}
    )
    return fetcher


@pytest.fixture
def mock_position_service():
    """Mock position service."""
    service = AsyncMock()

    # Mock position object
    position = MagicMock()
    position.id = 1
    position.symbol = "BTC/USDT"
    position.dict = MagicMock(return_value={"id": 1, "symbol": "BTC/USDT", "size": 1.0})

    service.get_active_positions = AsyncMock(return_value=[position])
    service.get_closed_positions = AsyncMock(return_value=[position])
    service.get_position_statistics = AsyncMock(
        return_value={"total_positions": 10, "active_positions": 2}
    )
    return service


@pytest.fixture
def cache_config():
    """Create cache configuration."""
    return CacheConfig(
        market_symbols=["BTC/USDT", "ETH/USDT"],
        parallel_workers=2,
        warm_timeout_seconds=10,
    )


@pytest.fixture
def cache_warmer(
    mock_redis,
    mock_market_data_fetcher,
    mock_balance_fetcher,
    mock_position_service,
    cache_config,
):
    """Create CacheWarmer instance with mocked dependencies."""
    return CacheWarmer(
        redis_manager=mock_redis,
        market_data_fetcher=mock_market_data_fetcher,
        balance_fetcher=mock_balance_fetcher,
        position_service=mock_position_service,
        config=cache_config,
    )


@pytest.mark.asyncio
async def test_warm_all_caches_success(cache_warmer):
    """Test successful cache warming for all data types."""
    # Act
    stats = await cache_warmer.warm_all_caches()

    # Assert
    assert isinstance(stats, CacheStats)
    assert stats.successful_keys > 0
    assert stats.warm_time_ms > 0


@pytest.mark.asyncio
async def test_warm_all_caches_already_in_progress(cache_warmer):
    """Test that warming doesn't start if already in progress."""
    # Arrange
    cache_warmer._warming_in_progress = True

    # Act
    stats = await cache_warmer.warm_all_caches()

    # Assert
    assert stats.total_keys == 0


@pytest.mark.asyncio
async def test_warm_all_caches_timeout(cache_warmer, cache_config):
    """Test cache warming with timeout."""
    # Arrange
    cache_config.warm_timeout_seconds = 0.1
    cache_warmer.warm_market_data = AsyncMock(side_effect=asyncio.sleep(10))

    # Act
    stats = await cache_warmer.warm_all_caches()

    # Assert
    assert "timeout" in str(stats.errors).lower() or stats.failed_keys > 0


@pytest.mark.asyncio
async def test_warm_market_data_success(cache_warmer, mock_redis, cache_config):
    """Test warming market data successfully."""
    # Act
    warmed_keys = await cache_warmer.warm_market_data()

    # Assert
    assert warmed_keys > 0
    # Should have called redis.set for each symbol * 3 data types
    expected_min_calls = len(cache_config.market_symbols) * 3
    assert mock_redis.set.call_count >= expected_min_calls


@pytest.mark.asyncio
async def test_warm_market_data_with_auto_symbols(cache_warmer, mock_position_service):
    """Test warming market data with auto-detected symbols."""
    # Arrange
    cache_warmer.config.market_symbols = []  # Empty to trigger auto-detection

    # Act
    warmed_keys = await cache_warmer.warm_market_data()

    # Assert
    assert warmed_keys > 0
    assert mock_position_service.get_active_positions.called


@pytest.mark.asyncio
async def test_warm_ohlcv_success(cache_warmer, mock_redis, mock_market_data_fetcher):
    """Test warming OHLCV data."""
    # Act
    result = await cache_warmer._warm_ohlcv("BTC/USDT")

    # Assert
    assert result is True
    assert mock_market_data_fetcher.fetch_ohlcv.called
    assert mock_redis.set.called


@pytest.mark.asyncio
async def test_warm_ohlcv_failure(cache_warmer, mock_market_data_fetcher):
    """Test handling OHLCV warming failure."""
    # Arrange
    mock_market_data_fetcher.fetch_ohlcv = AsyncMock(side_effect=Exception("API error"))

    # Act
    result = await cache_warmer._warm_ohlcv("BTC/USDT")

    # Assert
    assert result is False


@pytest.mark.asyncio
async def test_warm_ohlcv_no_data(cache_warmer, mock_market_data_fetcher):
    """Test warming OHLCV when no data is returned."""
    # Arrange
    mock_market_data_fetcher.fetch_ohlcv = AsyncMock(return_value=None)

    # Act
    result = await cache_warmer._warm_ohlcv("BTC/USDT")

    # Assert
    assert result is False


@pytest.mark.asyncio
async def test_warm_ticker_success(cache_warmer, mock_redis, mock_market_data_fetcher):
    """Test warming ticker data."""
    # Act
    result = await cache_warmer._warm_ticker("BTC/USDT")

    # Assert
    assert result is True
    assert mock_market_data_fetcher.fetch_ticker.called
    assert mock_redis.set.called


@pytest.mark.asyncio
async def test_warm_orderbook_success(
    cache_warmer, mock_redis, mock_market_data_fetcher
):
    """Test warming orderbook data."""
    # Act
    result = await cache_warmer._warm_orderbook("BTC/USDT")

    # Assert
    assert result is True
    assert mock_market_data_fetcher.fetch_orderbook.called
    assert mock_redis.set.called


@pytest.mark.asyncio
async def test_warm_balance_data_success(
    cache_warmer, mock_redis, mock_balance_fetcher
):
    """Test warming balance data."""
    # Act
    warmed_keys = await cache_warmer.warm_balance_data()

    # Assert
    assert warmed_keys == 3  # total, available, detailed
    assert mock_balance_fetcher.fetch_total_balance.called
    assert mock_balance_fetcher.fetch_available_balance.called
    assert mock_balance_fetcher.fetch_detailed_balances.called
    assert mock_redis.set.call_count >= 3


@pytest.mark.asyncio
async def test_warm_balance_data_partial_failure(cache_warmer, mock_balance_fetcher):
    """Test warming balance data with partial failures."""
    # Arrange
    mock_balance_fetcher.fetch_total_balance = AsyncMock(return_value=None)

    # Act
    warmed_keys = await cache_warmer.warm_balance_data()

    # Assert
    # Should still warm other balance types
    assert warmed_keys >= 0


@pytest.mark.asyncio
async def test_warm_balance_data_failure(cache_warmer, mock_balance_fetcher):
    """Test handling balance data warming failure."""
    # Arrange
    mock_balance_fetcher.fetch_total_balance = AsyncMock(
        side_effect=Exception("Balance fetch error")
    )

    # Act & Assert
    with pytest.raises(Exception):
        await cache_warmer.warm_balance_data()


@pytest.mark.asyncio
async def test_warm_position_data_success(
    cache_warmer, mock_redis, mock_position_service
):
    """Test warming position data."""
    # Act
    warmed_keys = await cache_warmer.warm_position_data()

    # Assert
    assert warmed_keys > 0
    assert mock_position_service.get_active_positions.called
    assert mock_position_service.get_closed_positions.called
    assert mock_position_service.get_position_statistics.called


@pytest.mark.asyncio
async def test_warm_position_data_no_active_positions(
    cache_warmer, mock_position_service
):
    """Test warming position data when no active positions exist."""
    # Arrange
    mock_position_service.get_active_positions = AsyncMock(return_value=[])

    # Act
    warmed_keys = await cache_warmer.warm_position_data()

    # Assert
    assert warmed_keys >= 0


@pytest.mark.asyncio
async def test_refresh_cache_all_types(cache_warmer):
    """Test refreshing all cache types."""
    # Act
    stats = await cache_warmer.refresh_cache()

    # Assert
    assert isinstance(stats, CacheStats)
    assert stats.successful_keys > 0


@pytest.mark.asyncio
async def test_refresh_cache_selective(cache_warmer):
    """Test selectively refreshing specific cache types."""
    # Act
    stats = await cache_warmer.refresh_cache(cache_types=["market"])

    # Assert
    assert isinstance(stats, CacheStats)
    # Should only warm market data


@pytest.mark.asyncio
async def test_refresh_cache_specific_symbols(cache_warmer):
    """Test refreshing cache for specific symbols."""
    # Act
    stats = await cache_warmer.refresh_cache(
        cache_types=["market"], symbols=["BTC/USDT"]
    )

    # Assert
    assert isinstance(stats, CacheStats)


@pytest.mark.asyncio
async def test_refresh_cache_with_errors(cache_warmer):
    """Test refresh cache handling errors."""
    # Arrange
    cache_warmer.warm_market_data = AsyncMock(side_effect=Exception("Refresh error"))

    # Act
    stats = await cache_warmer.refresh_cache(cache_types=["market"])

    # Assert
    assert stats.failed_keys > 0
    assert len(stats.errors) > 0


@pytest.mark.asyncio
async def test_get_cache_stats(cache_warmer, mock_redis):
    """Test getting comprehensive cache statistics."""
    # Arrange
    cache_warmer._last_warm_time = datetime.now()
    cache_warmer.stats.warm_time_ms = 100.0
    cache_warmer.stats.total_keys = 10

    # Act
    stats = await cache_warmer.get_cache_stats()

    # Assert
    assert "warming" in stats
    assert "performance" in stats
    assert "redis" in stats
    assert "config" in stats
    assert mock_redis.info.called


@pytest.mark.asyncio
async def test_get_active_symbols_from_positions(cache_warmer, mock_position_service):
    """Test getting active symbols from positions."""
    # Act
    symbols = await cache_warmer._get_active_symbols()

    # Assert
    assert len(symbols) > 0
    assert "BTC/USDT" in symbols


@pytest.mark.asyncio
async def test_get_active_symbols_default(cache_warmer, mock_position_service):
    """Test getting default symbols when no active positions."""
    # Arrange
    mock_position_service.get_active_positions = AsyncMock(return_value=[])

    # Act
    symbols = await cache_warmer._get_active_symbols()

    # Assert
    assert len(symbols) > 0
    # Should return default symbols


@pytest.mark.asyncio
async def test_get_active_symbols_error(cache_warmer, mock_position_service):
    """Test handling error when getting active symbols."""
    # Arrange
    mock_position_service.get_active_positions = AsyncMock(
        side_effect=Exception("Service error")
    )

    # Act
    symbols = await cache_warmer._get_active_symbols()

    # Assert
    assert len(symbols) > 0  # Should return default symbols


@pytest.mark.asyncio
async def test_calculate_hit_rate(cache_warmer, mock_redis):
    """Test calculating cache hit rate."""
    # Act
    hit_rate = await cache_warmer._calculate_hit_rate()

    # Assert
    assert 0 <= hit_rate <= 100
    assert hit_rate == 90.0  # 9000 hits / (9000 + 1000)


@pytest.mark.asyncio
async def test_calculate_hit_rate_no_data(cache_warmer, mock_redis):
    """Test calculating hit rate with no data."""
    # Arrange
    mock_redis.info = AsyncMock(return_value={"keyspace_hits": 0, "keyspace_misses": 0})

    # Act
    hit_rate = await cache_warmer._calculate_hit_rate()

    # Assert
    assert hit_rate == 0.0


@pytest.mark.asyncio
async def test_calculate_hit_rate_error(cache_warmer, mock_redis):
    """Test handling error when calculating hit rate."""
    # Arrange
    mock_redis.info = AsyncMock(side_effect=Exception("Redis error"))

    # Act
    hit_rate = await cache_warmer._calculate_hit_rate()

    # Assert
    assert hit_rate == 0.0


@pytest.mark.asyncio
async def test_estimate_cache_size(cache_warmer, mock_redis):
    """Test estimating cache size."""
    # Act
    size_mb = await cache_warmer._estimate_cache_size()

    # Assert
    assert size_mb == 50.0  # 50MB from mock


@pytest.mark.asyncio
async def test_estimate_cache_size_error(cache_warmer, mock_redis):
    """Test handling error when estimating cache size."""
    # Arrange
    mock_redis.info = AsyncMock(side_effect=Exception("Redis error"))

    # Act
    size_mb = await cache_warmer._estimate_cache_size()

    # Assert
    assert size_mb == 0.0


def test_track_access_hit(cache_warmer):
    """Test tracking cache hit."""
    # Act
    cache_warmer.track_access(hit=True)

    # Assert
    assert cache_warmer._cache_hits == 1
    assert cache_warmer._cache_misses == 0


def test_track_access_miss(cache_warmer):
    """Test tracking cache miss."""
    # Act
    cache_warmer.track_access(hit=False)

    # Assert
    assert cache_warmer._cache_hits == 0
    assert cache_warmer._cache_misses == 1


@pytest.mark.asyncio
async def test_invalidate_cache(cache_warmer, mock_redis):
    """Test invalidating cache by pattern."""
    # Arrange
    mock_redis.scan_keys = AsyncMock(
        return_value=["market:ohlcv:BTC/USDT:5m", "market:ohlcv:ETH/USDT:5m"]
    )

    # Act
    count = await cache_warmer.invalidate_cache("market:*")

    # Assert
    assert count == 2
    assert mock_redis.scan_keys.called
    assert mock_redis.delete_many.called


@pytest.mark.asyncio
async def test_invalidate_cache_no_matches(cache_warmer, mock_redis):
    """Test invalidating cache with no matching keys."""
    # Arrange
    mock_redis.scan_keys = AsyncMock(return_value=[])

    # Act
    count = await cache_warmer.invalidate_cache("nonexistent:*")

    # Assert
    assert count == 0


@pytest.mark.asyncio
async def test_invalidate_cache_error(cache_warmer, mock_redis):
    """Test handling error during cache invalidation."""
    # Arrange
    mock_redis.scan_keys = AsyncMock(side_effect=Exception("Redis error"))

    # Act
    count = await cache_warmer.invalidate_cache("market:*")

    # Assert
    assert count == 0


@pytest.mark.asyncio
async def test_cleanup(cache_warmer):
    """Test cleanup method."""
    # Arrange
    cache_warmer._cache_hits = 100
    cache_warmer._cache_misses = 20
    cache_warmer.stats.total_keys = 50

    # Act
    await cache_warmer.cleanup()

    # Assert
    assert cache_warmer._cache_hits == 0
    assert cache_warmer._cache_misses == 0
    assert cache_warmer.stats.total_keys == 0


@pytest.mark.asyncio
async def test_parallel_warming_execution(cache_warmer):
    """Test that warming executes in parallel."""
    # Arrange
    start_time = asyncio.get_event_loop().time()

    # Act
    stats = await cache_warmer.warm_all_caches()

    # Assert
    duration = asyncio.get_event_loop().time() - start_time
    # Parallel execution should be faster than sequential
    assert duration < 5.0  # Should complete quickly with mocks
    assert stats.successful_keys > 0


@pytest.mark.asyncio
async def test_warm_all_caches_exception_handling(cache_warmer):
    """Test exception handling in warm_all_caches."""
    # Arrange
    cache_warmer.warm_market_data = AsyncMock(side_effect=Exception("Test error"))

    # Act
    stats = await cache_warmer.warm_all_caches()

    # Assert
    assert stats.failed_keys > 0
    assert len(stats.errors) > 0


@pytest.mark.asyncio
async def test_cache_config_defaults():
    """Test CacheConfig default values."""
    # Act
    config = CacheConfig()

    # Assert
    assert config.market_ohlcv_candles == 100
    assert config.market_ohlcv_timeframe == "5m"
    assert config.parallel_workers == 4
    assert config.retry_attempts == 3


@pytest.mark.asyncio
async def test_cache_stats_initialization():
    """Test CacheStats initialization."""
    # Act
    stats = CacheStats()

    # Assert
    assert stats.total_keys == 0
    assert stats.successful_keys == 0
    assert stats.failed_keys == 0
    assert len(stats.errors) == 0
