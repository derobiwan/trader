"""
Unit tests for Market Data Service caching functionality

Tests cache integration for:
- OHLCV data fetching
- Ticker data fetching
- Cache hit rates
- TTL expiration

Author: Performance Optimizer
Date: 2025-10-28
"""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime

from workspace.features.market_data import MarketDataService
from workspace.features.market_data.models import OHLCV, Ticker, Timeframe
from workspace.features.caching import CacheService


@pytest.mark.asyncio
async def test_ohlcv_cache_hit():
    """Test OHLCV data is cached and returned on second call"""
    # Setup (use in-memory cache for testing)
    cache = CacheService(use_redis=False)
    service = MarketDataService(
        symbols=["BTC/USDT:USDT"],
        timeframe=Timeframe.M3,
        cache_service=cache,
    )

    # Pre-populate in-memory store
    test_candle = OHLCV(
        symbol="BTC/USDT:USDT",
        timeframe=Timeframe.M3,
        timestamp=datetime(2025, 10, 28, 12, 0, 0),
        open=Decimal("45000.0"),
        high=Decimal("45100.0"),
        low=Decimal("44900.0"),
        close=Decimal("45050.0"),
        volume=Decimal("100.5"),
        quote_volume=Decimal("4512225.0"),
        trades_count=150,
    )
    service.ohlcv_data["BTC/USDT:USDT"] = [test_candle]

    # First call - should populate cache
    data1 = await service.get_ohlcv_history("BTC/USDT:USDT", limit=1)
    assert len(data1) == 1
    assert data1[0].close == Decimal("45050.0")

    # Check cache stats
    stats = cache.get_stats()
    assert stats["misses"] == 1  # First call was cache miss
    assert stats["sets"] == 1  # Data was cached

    # Second call - should hit cache
    data2 = await service.get_ohlcv_history("BTC/USDT:USDT", limit=1)
    assert len(data2) == 1
    assert data2[0].close == Decimal("45050.0")

    # Check cache stats after second call
    stats = cache.get_stats()
    assert stats["hits"] == 1  # Second call was cache hit
    assert stats["misses"] == 1  # Still only one miss


@pytest.mark.asyncio
async def test_ticker_cache_hit():
    """Test ticker data is cached and returned on second call"""
    # Setup
    cache = CacheService()
    service = MarketDataService(
        symbols=["BTC/USDT:USDT"],
        timeframe=Timeframe.M3,
        cache_service=cache,
    )

    # Pre-populate ticker data
    test_ticker = Ticker(
        symbol="BTC/USDT:USDT",
        timestamp=datetime(2025, 10, 28, 12, 0, 0),
        bid=Decimal("44999.0"),
        ask=Decimal("45001.0"),
        last=Decimal("45000.0"),
        high_24h=Decimal("46000.0"),
        low_24h=Decimal("44000.0"),
        volume_24h=Decimal("12345.67"),
        change_24h=Decimal("500.0"),
        change_24h_pct=Decimal("0.05"),
    )
    service.latest_tickers["BTC/USDT:USDT"] = test_ticker

    # First call - should populate cache
    ticker1 = await service.get_latest_ticker("BTC/USDT:USDT")
    assert ticker1 is not None
    assert ticker1.last == Decimal("45000.0")

    # Check cache stats
    stats = cache.get_stats()
    assert stats["misses"] == 1
    assert stats["sets"] == 1

    # Second call - should hit cache
    ticker2 = await service.get_latest_ticker("BTC/USDT:USDT")
    assert ticker2 is not None
    assert ticker2.last == Decimal("45000.0")

    # Check cache stats
    stats = cache.get_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1


@pytest.mark.asyncio
async def test_cache_ttl_expiration():
    """Test cache expires after TTL"""
    # Setup with short TTL for testing
    cache = CacheService()
    service = MarketDataService(
        symbols=["BTC/USDT:USDT"],
        timeframe=Timeframe.M3,
        cache_service=cache,
    )

    # Pre-populate ticker data
    test_ticker = Ticker(
        symbol="BTC/USDT:USDT",
        timestamp=datetime(2025, 10, 28, 12, 0, 0),
        bid=Decimal("44999.0"),
        ask=Decimal("45001.0"),
        last=Decimal("45000.0"),
        high_24h=Decimal("46000.0"),
        low_24h=Decimal("44000.0"),
        volume_24h=Decimal("12345.67"),
        change_24h=Decimal("500.0"),
        change_24h_pct=Decimal("0.05"),
    )
    service.latest_tickers["BTC/USDT:USDT"] = test_ticker

    # Patch cache set to use 1 second TTL for testing
    original_set = cache.set

    async def patched_set(key, value, ttl_seconds=None):
        return await original_set(key, value, ttl_seconds=1)  # 1 second TTL

    cache.set = patched_set

    # First call
    await service.get_latest_ticker("BTC/USDT:USDT")
    assert cache.get_stats()["sets"] == 1

    # Second call (within TTL)
    await service.get_latest_ticker("BTC/USDT:USDT")
    assert cache.get_stats()["hits"] == 1

    # Wait for TTL to expire
    await asyncio.sleep(1.1)

    # Third call (after TTL) - should be cache miss and re-cache
    await service.get_latest_ticker("BTC/USDT:USDT")
    stats = cache.get_stats()
    assert stats["misses"] == 2  # Initial miss + expired miss
    assert stats["sets"] == 2  # Initial set + re-set after expiration


@pytest.mark.asyncio
async def test_different_symbols_different_cache():
    """Test different symbols use different cache keys"""
    # Setup
    cache = CacheService()
    service = MarketDataService(
        symbols=["BTC/USDT:USDT", "ETH/USDT:USDT"],
        timeframe=Timeframe.M3,
        cache_service=cache,
    )

    # Pre-populate tickers for both symbols
    btc_ticker = Ticker(
        symbol="BTC/USDT:USDT",
        timestamp=datetime(2025, 10, 28, 12, 0, 0),
        bid=Decimal("44999.0"),
        ask=Decimal("45001.0"),
        last=Decimal("45000.0"),
        high_24h=Decimal("46000.0"),
        low_24h=Decimal("44000.0"),
        volume_24h=Decimal("12345.67"),
        change_24h=Decimal("500.0"),
        change_24h_pct=Decimal("0.05"),
    )
    eth_ticker = Ticker(
        symbol="ETH/USDT:USDT",
        timestamp=datetime(2025, 10, 28, 12, 0, 0),
        bid=Decimal("2499.0"),
        ask=Decimal("2501.0"),
        last=Decimal("2500.0"),
        high_24h=Decimal("2600.0"),
        low_24h=Decimal("2400.0"),
        volume_24h=Decimal("54321.0"),
        change_24h=Decimal("100.0"),
        change_24h_pct=Decimal("0.04"),
    )

    service.latest_tickers["BTC/USDT:USDT"] = btc_ticker
    service.latest_tickers["ETH/USDT:USDT"] = eth_ticker

    # Fetch both symbols
    btc1 = await service.get_latest_ticker("BTC/USDT:USDT")
    eth1 = await service.get_latest_ticker("ETH/USDT:USDT")

    assert btc1.last == Decimal("45000.0")
    assert eth1.last == Decimal("2500.0")

    # Both should be cache misses (first fetch)
    stats = cache.get_stats()
    assert stats["misses"] == 2
    assert stats["sets"] == 2

    # Fetch again - both should be cache hits
    btc2 = await service.get_latest_ticker("BTC/USDT:USDT")
    eth2 = await service.get_latest_ticker("ETH/USDT:USDT")

    assert btc2.last == Decimal("45000.0")
    assert eth2.last == Decimal("2500.0")

    stats = cache.get_stats()
    assert stats["hits"] == 2
    assert stats["misses"] == 2


@pytest.mark.asyncio
async def test_cache_hit_rate_calculation():
    """Test cache hit rate is calculated correctly"""
    # Setup
    cache = CacheService()
    service = MarketDataService(
        symbols=["BTC/USDT:USDT"],
        timeframe=Timeframe.M3,
        cache_service=cache,
    )

    # Pre-populate ticker
    test_ticker = Ticker(
        symbol="BTC/USDT:USDT",
        timestamp=datetime(2025, 10, 28, 12, 0, 0),
        bid=Decimal("44999.0"),
        ask=Decimal("45001.0"),
        last=Decimal("45000.0"),
        high_24h=Decimal("46000.0"),
        low_24h=Decimal("44000.0"),
        volume_24h=Decimal("12345.67"),
        change_24h=Decimal("500.0"),
        change_24h_pct=Decimal("0.05"),
    )
    service.latest_tickers["BTC/USDT:USDT"] = test_ticker

    # Make multiple calls: 1 miss + 4 hits
    await service.get_latest_ticker("BTC/USDT:USDT")  # Miss
    await service.get_latest_ticker("BTC/USDT:USDT")  # Hit
    await service.get_latest_ticker("BTC/USDT:USDT")  # Hit
    await service.get_latest_ticker("BTC/USDT:USDT")  # Hit
    await service.get_latest_ticker("BTC/USDT:USDT")  # Hit

    # Check stats
    stats = cache.get_stats()
    assert stats["hits"] == 4
    assert stats["misses"] == 1
    assert stats["total_requests"] == 5
    assert stats["hit_rate"] == "80.00%"


@pytest.mark.asyncio
async def test_empty_cache_returns_none():
    """Test cache correctly handles missing data"""
    # Setup
    cache = CacheService()
    service = MarketDataService(
        symbols=["BTC/USDT:USDT"],
        timeframe=Timeframe.M3,
        cache_service=cache,
    )

    # Don't pre-populate any data

    # Try to get ticker that doesn't exist
    ticker = await service.get_latest_ticker("BTC/USDT:USDT")
    assert ticker is None

    # Try to get OHLCV that doesn't exist
    ohlcv = await service.get_ohlcv_history("BTC/USDT:USDT", limit=100)
    assert len(ohlcv) == 0


@pytest.mark.asyncio
async def test_cache_disabled():
    """Test service works when cache is disabled"""
    # Setup with disabled cache
    cache = CacheService(enabled=False)
    service = MarketDataService(
        symbols=["BTC/USDT:USDT"],
        timeframe=Timeframe.M3,
        cache_service=cache,
    )

    # Pre-populate ticker
    test_ticker = Ticker(
        symbol="BTC/USDT:USDT",
        timestamp=datetime(2025, 10, 28, 12, 0, 0),
        bid=Decimal("44999.0"),
        ask=Decimal("45001.0"),
        last=Decimal("45000.0"),
        high_24h=Decimal("46000.0"),
        low_24h=Decimal("44000.0"),
        volume_24h=Decimal("12345.67"),
        change_24h=Decimal("500.0"),
        change_24h_pct=Decimal("0.05"),
    )
    service.latest_tickers["BTC/USDT:USDT"] = test_ticker

    # Make multiple calls
    ticker1 = await service.get_latest_ticker("BTC/USDT:USDT")
    ticker2 = await service.get_latest_ticker("BTC/USDT:USDT")

    # Both should return data
    assert ticker1.last == Decimal("45000.0")
    assert ticker2.last == Decimal("45000.0")

    # But no cache stats (cache disabled)
    stats = cache.get_stats()
    assert stats["hits"] == 0
    assert stats["misses"] == 0


@pytest.mark.asyncio
async def test_ohlcv_serialization_deserialization():
    """Test OHLCV objects are correctly serialized and deserialized"""
    # Setup
    cache = CacheService()
    service = MarketDataService(
        symbols=["BTC/USDT:USDT"],
        timeframe=Timeframe.M3,
        cache_service=cache,
    )

    # Pre-populate with multiple candles
    candles = [
        OHLCV(
            symbol="BTC/USDT:USDT",
            timeframe=Timeframe.M3,
            timestamp=datetime(2025, 10, 28, 12, 0, 0),
            open=Decimal("45000.0"),
            high=Decimal("45100.0"),
            low=Decimal("44900.0"),
            close=Decimal("45050.0"),
            volume=Decimal("100.5"),
            quote_volume=Decimal("4512225.0"),
            trades_count=150,
        ),
        OHLCV(
            symbol="BTC/USDT:USDT",
            timeframe=Timeframe.M3,
            timestamp=datetime(2025, 10, 28, 12, 3, 0),
            open=Decimal("45050.0"),
            high=Decimal("45200.0"),
            low=Decimal("45000.0"),
            close=Decimal("45150.0"),
            volume=Decimal("120.3"),
            quote_volume=Decimal("5436045.0"),
            trades_count=180,
        ),
    ]
    service.ohlcv_data["BTC/USDT:USDT"] = candles

    # Fetch and cache
    data1 = await service.get_ohlcv_history("BTC/USDT:USDT", limit=2)

    # Verify data integrity
    assert len(data1) == 2
    assert data1[0].open == Decimal("45000.0")
    assert data1[0].close == Decimal("45050.0")
    assert data1[1].open == Decimal("45050.0")
    assert data1[1].close == Decimal("45150.0")
    assert data1[0].trades_count == 150
    assert data1[1].trades_count == 180

    # Fetch from cache (second call)
    data2 = await service.get_ohlcv_history("BTC/USDT:USDT", limit=2)

    # Verify cached data matches
    assert len(data2) == 2
    assert data2[0].open == data1[0].open
    assert data2[0].close == data1[0].close
    assert data2[1].open == data1[1].open
    assert data2[1].close == data1[1].close

    # Verify cache was hit
    stats = cache.get_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
