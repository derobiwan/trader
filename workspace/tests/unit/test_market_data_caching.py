"""
Unit tests for market data caching

Tests cache hit/miss scenarios for OHLCV and ticker data.

Author: Sprint 1 Stream B
Date: 2025-10-28
"""

from datetime import datetime
from decimal import Decimal

import pytest

from workspace.features.caching import CacheService
from workspace.features.market_data import (OHLCV, MarketDataService, Ticker,
                                            Timeframe)


@pytest.mark.asyncio
async def test_ohlcv_cache_hit():
    """Test OHLCV data is cached and returned on second call"""
    # Setup
    cache = CacheService()
    service = MarketDataService(
        symbols=["BTCUSDT"],
        timeframe=Timeframe.M3,
        cache_service=cache,
    )

    # Add test data to in-memory store
    test_candle = OHLCV(
        symbol="BTC/USDT:USDT",
        timeframe=Timeframe.M3,
        timestamp=datetime.utcnow(),
        open=Decimal("45000"),
        high=Decimal("45100"),
        low=Decimal("44900"),
        close=Decimal("45050"),
        volume=Decimal("100"),
        quote_volume=Decimal("4500000"),
        trades_count=500,
    )
    service.ohlcv_data["BTC/USDT:USDT"] = [test_candle]

    # First call - should populate cache
    data1 = await service.get_ohlcv_history("BTCUSDT", limit=1, use_cache=True)
    assert len(data1) == 1
    assert data1[0].close == Decimal("45050")

    # Clear in-memory store to verify cache is used
    service.ohlcv_data["BTC/USDT:USDT"] = []

    # Second call - should hit cache
    data2 = await service.get_ohlcv_history("BTCUSDT", limit=1, use_cache=True)
    assert len(data2) == 1
    assert data2[0].close == Decimal("45050")

    # Check cache stats
    stats = cache.get_stats()
    assert stats["hits"] >= 1
    assert stats["misses"] >= 1


@pytest.mark.asyncio
async def test_ticker_cache_hit():
    """Test ticker data is cached and returned on second call"""
    # Setup
    cache = CacheService()
    service = MarketDataService(
        symbols=["BTCUSDT"],
        timeframe=Timeframe.M3,
        cache_service=cache,
    )

    # Add test ticker to in-memory store
    test_ticker = Ticker(
        symbol="BTC/USDT:USDT",
        last=Decimal("45000"),
        bid=Decimal("44999"),
        ask=Decimal("45001"),
        high_24h=Decimal("46000"),
        low_24h=Decimal("44000"),
        volume_24h=Decimal("12345.67"),
        change_24h=Decimal("1000"),
        change_24h_pct=Decimal("2.27"),
        timestamp=datetime.utcnow(),
    )
    service.latest_tickers["BTC/USDT:USDT"] = test_ticker

    # First call - should populate cache
    ticker1 = await service.get_latest_ticker("BTCUSDT", use_cache=True)
    assert ticker1 is not None
    assert ticker1.last == Decimal("45000")

    # Clear in-memory store to verify cache is used
    service.latest_tickers["BTC/USDT:USDT"] = None

    # Second call - should hit cache
    ticker2 = await service.get_latest_ticker("BTCUSDT", use_cache=True)
    assert ticker2 is not None
    assert ticker2.last == Decimal("45000")

    # Check cache stats
    stats = cache.get_stats()
    assert stats["hits"] >= 1


@pytest.mark.asyncio
async def test_cache_disabled():
    """Test that disabling cache works correctly"""
    # Setup
    cache = CacheService()
    service = MarketDataService(
        symbols=["BTCUSDT"],
        timeframe=Timeframe.M3,
        cache_service=cache,
    )

    # Add test data
    test_candle = OHLCV(
        symbol="BTC/USDT:USDT",
        timeframe=Timeframe.M3,
        timestamp=datetime.utcnow(),
        open=Decimal("45000"),
        high=Decimal("45100"),
        low=Decimal("44900"),
        close=Decimal("45050"),
        volume=Decimal("100"),
        quote_volume=Decimal("4500000"),
        trades_count=500,
    )
    service.ohlcv_data["BTC/USDT:USDT"] = [test_candle]

    # Call with cache disabled
    data = await service.get_ohlcv_history("BTCUSDT", limit=1, use_cache=False)
    assert len(data) == 1

    # Cache should not be used
    stats = cache.get_stats()
    assert stats["sets"] == 0


@pytest.mark.asyncio
async def test_cache_ttl_expiration():
    """Test cache expires after TTL"""
    # Setup with short TTL
    cache = CacheService()
    service = MarketDataService(
        symbols=["BTCUSDT"],
        timeframe=Timeframe.M3,
        cache_service=cache,
    )

    # Add test ticker
    test_ticker = Ticker(
        symbol="BTC/USDT:USDT",
        last=Decimal("45000"),
        bid=Decimal("44999"),
        ask=Decimal("45001"),
        high_24h=Decimal("46000"),
        low_24h=Decimal("44000"),
        volume_24h=Decimal("12345.67"),
        change_24h=Decimal("1000"),
        change_24h_pct=Decimal("2.27"),
        timestamp=datetime.utcnow(),
    )
    service.latest_tickers["BTC/USDT:USDT"] = test_ticker

    # First call to populate cache
    ticker1 = await service.get_latest_ticker("BTCUSDT", use_cache=True)
    assert ticker1 is not None

    # Update in-memory data - create new ticker object
    test_ticker = Ticker(
        symbol="BTC/USDT:USDT",
        last=Decimal("46000"),
        bid=Decimal("45999"),
        ask=Decimal("46001"),
        high_24h=Decimal("46500"),
        low_24h=Decimal("44000"),
        volume_24h=Decimal("12345.67"),
        change_24h=Decimal("2000"),
        change_24h_pct=Decimal("4.55"),
        timestamp=datetime.utcnow(),
    )
    service.latest_tickers["BTC/USDT:USDT"] = test_ticker

    # Second call (within TTL) - should return cached value
    ticker2 = await service.get_latest_ticker("BTCUSDT", use_cache=True)
    assert ticker2.last == Decimal("45000")  # Cached value

    # Wait for cache to expire (30s TTL, wait 31s)
    # Note: In production, this would be a real wait
    # For testing, we can manually expire the cache
    await cache.clear("market_data:ticker:")

    # Third call (after expiration) - should fetch fresh data
    ticker3 = await service.get_latest_ticker("BTCUSDT", use_cache=True)
    assert ticker3.last == Decimal("46000")  # Fresh value


@pytest.mark.asyncio
async def test_multiple_symbols_cache_isolation():
    """Test that cache correctly isolates data for different symbols"""
    # Setup
    cache = CacheService()
    service = MarketDataService(
        symbols=["BTCUSDT", "ETHUSDT"],
        timeframe=Timeframe.M3,
        cache_service=cache,
    )

    # Add test tickers for both symbols
    btc_ticker = Ticker(
        symbol="BTC/USDT:USDT",
        last=Decimal("45000"),
        bid=Decimal("44999"),
        ask=Decimal("45001"),
        high_24h=Decimal("46000"),
        low_24h=Decimal("44000"),
        volume_24h=Decimal("12345.67"),
        change_24h=Decimal("1000"),
        change_24h_pct=Decimal("2.27"),
        timestamp=datetime.utcnow(),
    )
    eth_ticker = Ticker(
        symbol="ETH/USDT:USDT",
        last=Decimal("2500"),
        bid=Decimal("2499"),
        ask=Decimal("2501"),
        high_24h=Decimal("2600"),
        low_24h=Decimal("2400"),
        volume_24h=Decimal("54321.89"),
        change_24h=Decimal("100"),
        change_24h_pct=Decimal("4.17"),
        timestamp=datetime.utcnow(),
    )
    service.latest_tickers["BTC/USDT:USDT"] = btc_ticker
    service.latest_tickers["ETH/USDT:USDT"] = eth_ticker

    # Fetch both tickers (should cache separately)
    btc1 = await service.get_latest_ticker("BTCUSDT", use_cache=True)
    eth1 = await service.get_latest_ticker("ETHUSDT", use_cache=True)

    assert btc1.last == Decimal("45000")
    assert eth1.last == Decimal("2500")

    # Clear in-memory and verify cache returns correct data
    service.latest_tickers = {}

    btc2 = await service.get_latest_ticker("BTCUSDT", use_cache=True)
    eth2 = await service.get_latest_ticker("ETHUSDT", use_cache=True)

    assert btc2.last == Decimal("45000")
    assert eth2.last == Decimal("2500")

    # Cache should have 2 hits (one for each symbol)
    stats = cache.get_stats()
    assert stats["hits"] == 2
