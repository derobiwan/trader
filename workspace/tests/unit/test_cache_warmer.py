"""
Unit Tests for Cache Warmer

Tests cache warming functionality including:
- Market data warming
- Balance data warming
- Position data warming
- LLM prompt warming
- Parallel cache warming

Author: Testing Team
Date: 2025-10-29
Sprint: 3, Stream C
"""

import pytest
from unittest.mock import Mock, AsyncMock
from decimal import Decimal

from workspace.shared.cache.cache_warmer import (
    CacheWarmer,
    CacheWarmingResult,
)


@pytest.fixture
def mock_market_data_service():
    """Mock market data service"""
    service = Mock()
    service.get_ohlcv = AsyncMock(return_value=[])
    service.get_ticker = AsyncMock(return_value={"last": 50000.0})
    service.get_cache_stats = Mock(
        return_value={
            "hit_rate": 0.85,
            "hits": 100,
            "misses": 15,
            "size": 50,
        }
    )
    return service


@pytest.fixture
def mock_account_service():
    """Mock account service"""
    service = Mock()
    service.get_balance = AsyncMock(return_value=Decimal("10000.00"))
    service.get_cache_stats = Mock(
        return_value={
            "hit_rate": 0.90,
            "hits": 50,
            "misses": 5,
            "size": 10,
        }
    )
    return service


@pytest.fixture
def mock_position_service():
    """Mock position service"""
    service = Mock()
    service.get_all_positions = AsyncMock(return_value=[])
    return service


@pytest.fixture
def mock_llm_service():
    """Mock LLM service"""
    service = Mock()
    service.warm_prompt_cache = AsyncMock(return_value=5)
    service.get_cache_stats = Mock(
        return_value={
            "hit_rate": 0.75,
            "hits": 30,
            "misses": 10,
            "size": 20,
        }
    )
    return service


@pytest.fixture
def cache_warmer(
    mock_market_data_service,
    mock_account_service,
    mock_position_service,
    mock_llm_service,
):
    """Cache warmer with all mocked services"""
    return CacheWarmer(
        market_data_service=mock_market_data_service,
        account_service=mock_account_service,
        position_service=mock_position_service,
        llm_service=mock_llm_service,
    )


# ============================================================================
# Market Data Warming Tests
# ============================================================================


@pytest.mark.asyncio
async def test_warm_market_data_success(cache_warmer, mock_market_data_service):
    """Test successful market data warming"""
    # Execute
    result = await cache_warmer.warm_market_data()

    # Assert
    assert isinstance(result, CacheWarmingResult)
    assert result.category == "market_data"
    assert result.success
    assert result.items_warmed > 0
    assert result.time_taken_ms > 0

    # Verify service calls
    assert mock_market_data_service.get_ohlcv.call_count == len(
        cache_warmer.trading_symbols
    )
    assert mock_market_data_service.get_ticker.call_count == len(
        cache_warmer.trading_symbols
    )


@pytest.mark.asyncio
async def test_warm_market_data_no_service(cache_warmer):
    """Test market data warming without service"""
    cache_warmer.market_data_service = None

    # Execute
    result = await cache_warmer.warm_market_data()

    # Assert
    assert not result.success
    assert result.items_warmed == 0
    assert "not available" in result.error_message


@pytest.mark.asyncio
async def test_warm_market_data_partial_failure(cache_warmer, mock_market_data_service):
    """Test market data warming with some failures"""
    # Setup - make some calls fail
    call_count = 0

    async def mock_get_ohlcv(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count % 2 == 0:
            raise Exception("API rate limit")
        return []

    mock_market_data_service.get_ohlcv = mock_get_ohlcv

    # Execute
    result = await cache_warmer.warm_market_data()

    # Assert
    assert result.success  # Overall success even with partial failures
    assert result.items_warmed < len(cache_warmer.trading_symbols) * 2


# ============================================================================
# Balance Data Warming Tests
# ============================================================================


@pytest.mark.asyncio
async def test_warm_balance_data_success(cache_warmer, mock_account_service):
    """Test successful balance warming"""
    # Execute
    result = await cache_warmer.warm_balance_data()

    # Assert
    assert isinstance(result, CacheWarmingResult)
    assert result.category == "balance_data"
    assert result.success
    assert result.items_warmed == 1
    assert result.time_taken_ms > 0

    # Verify service call
    mock_account_service.get_balance.assert_called_once()


@pytest.mark.asyncio
async def test_warm_balance_data_no_service(cache_warmer):
    """Test balance warming without service"""
    cache_warmer.account_service = None

    # Execute
    result = await cache_warmer.warm_balance_data()

    # Assert
    assert not result.success
    assert result.items_warmed == 0
    assert "not available" in result.error_message


@pytest.mark.asyncio
async def test_warm_balance_data_error(cache_warmer, mock_account_service):
    """Test balance warming error handling"""
    # Setup
    mock_account_service.get_balance = AsyncMock(
        side_effect=Exception("API connection error")
    )

    # Execute
    result = await cache_warmer.warm_balance_data()

    # Assert
    assert not result.success
    assert result.items_warmed == 0
    assert "API connection error" in result.error_message


# ============================================================================
# Position Data Warming Tests
# ============================================================================


@pytest.mark.asyncio
async def test_warm_position_data_success(cache_warmer, mock_position_service):
    """Test successful position warming"""
    # Setup - return some positions
    mock_position_service.get_all_positions = AsyncMock(
        return_value=[
            {"symbol": "BTC/USDT:USDT"},
            {"symbol": "ETH/USDT:USDT"},
        ]
    )

    # Execute
    result = await cache_warmer.warm_position_data()

    # Assert
    assert isinstance(result, CacheWarmingResult)
    assert result.category == "position_data"
    assert result.success
    assert result.items_warmed == 2
    assert result.time_taken_ms > 0

    # Verify service call
    mock_position_service.get_all_positions.assert_called_once()


@pytest.mark.asyncio
async def test_warm_position_data_empty(cache_warmer, mock_position_service):
    """Test position warming with no positions"""
    # Setup
    mock_position_service.get_all_positions = AsyncMock(return_value=[])

    # Execute
    result = await cache_warmer.warm_position_data()

    # Assert
    assert result.success
    assert result.items_warmed == 0


@pytest.mark.asyncio
async def test_warm_position_data_no_service(cache_warmer):
    """Test position warming without service"""
    cache_warmer.position_service = None

    # Execute
    result = await cache_warmer.warm_position_data()

    # Assert
    assert not result.success
    assert "not available" in result.error_message


# ============================================================================
# LLM Prompt Warming Tests
# ============================================================================


@pytest.mark.asyncio
async def test_warm_llm_prompts_success(cache_warmer, mock_llm_service):
    """Test successful LLM prompt warming"""
    # Execute
    result = await cache_warmer.warm_llm_prompts()

    # Assert
    assert isinstance(result, CacheWarmingResult)
    assert result.category == "llm_prompts"
    assert result.success
    assert result.items_warmed == 5
    assert result.time_taken_ms > 0

    # Verify service call
    mock_llm_service.warm_prompt_cache.assert_called_once()


@pytest.mark.asyncio
async def test_warm_llm_prompts_not_supported(cache_warmer, mock_llm_service):
    """Test LLM prompt warming when not supported"""
    # Setup - remove warm_prompt_cache method
    delattr(mock_llm_service, "warm_prompt_cache")

    # Execute
    result = await cache_warmer.warm_llm_prompts()

    # Assert
    assert result.success
    assert result.items_warmed == 0  # Skipped


@pytest.mark.asyncio
async def test_warm_llm_prompts_no_service(cache_warmer):
    """Test LLM prompt warming without service"""
    cache_warmer.llm_service = None

    # Execute
    result = await cache_warmer.warm_llm_prompts()

    # Assert
    assert not result.success
    assert "not available" in result.error_message


# ============================================================================
# Warm All Caches Tests
# ============================================================================


@pytest.mark.asyncio
async def test_warm_all_caches_success(cache_warmer):
    """Test warming all caches in parallel"""
    # Execute
    results = await cache_warmer.warm_all_caches()

    # Assert
    assert len(results) == 4  # market_data, balance, position, llm
    assert all(isinstance(r, CacheWarmingResult) for r in results)

    # At least some should succeed
    successful = [r for r in results if r.success]
    assert len(successful) > 0


@pytest.mark.asyncio
async def test_warm_all_caches_with_failures(cache_warmer, mock_market_data_service):
    """Test warming all caches with some failures"""
    # Setup - make market data fail
    mock_market_data_service.get_ohlcv = AsyncMock(
        side_effect=Exception("Network error")
    )

    # Execute
    results = await cache_warmer.warm_all_caches()

    # Assert
    assert len(results) == 4
    # Cache warmer continues on failures, so check for reduced items_warmed
    market_result = [r for r in results if r.category == "market_data"][0]
    assert market_result.items_warmed < len(cache_warmer.trading_symbols) * 2


@pytest.mark.asyncio
async def test_warm_all_caches_no_services(cache_warmer):
    """Test warming with no services available"""
    # Setup
    cache_warmer.market_data_service = None
    cache_warmer.account_service = None
    cache_warmer.position_service = None
    cache_warmer.llm_service = None

    # Execute
    results = await cache_warmer.warm_all_caches()

    # Assert
    assert len(results) == 4
    assert all(not r.success for r in results)


# ============================================================================
# Selective Refresh Tests
# ============================================================================


@pytest.mark.asyncio
async def test_refresh_critical_caches(cache_warmer):
    """Test refreshing only critical caches"""
    # Execute
    refreshed = await cache_warmer.refresh_critical_caches()

    # Assert
    assert refreshed > 0
    # Should refresh: balance (1) + tickers (6) + positions (1) = 8
    assert refreshed == 8


@pytest.mark.asyncio
async def test_refresh_critical_caches_no_services(cache_warmer):
    """Test refresh with no services"""
    # Setup
    cache_warmer.market_data_service = None
    cache_warmer.account_service = None
    cache_warmer.position_service = None

    # Execute
    refreshed = await cache_warmer.refresh_critical_caches()

    # Assert
    assert refreshed == 0


# ============================================================================
# Cache Statistics Tests
# ============================================================================


def test_get_cache_stats(cache_warmer):
    """Test getting cache statistics"""
    # Execute
    stats = cache_warmer.get_cache_stats()

    # Assert
    assert "timestamp" in stats
    assert "services" in stats
    assert "market_data" in stats["services"]
    assert "account" in stats["services"]
    assert "llm" in stats["services"]

    # Check market data stats
    market_stats = stats["services"]["market_data"]
    assert "hit_rate" in market_stats
    assert "hits" in market_stats
    assert "misses" in market_stats


def test_get_cache_stats_no_services(cache_warmer):
    """Test getting stats with services that don't support it"""
    # Setup - remove get_cache_stats methods
    delattr(cache_warmer.market_data_service, "get_cache_stats")
    delattr(cache_warmer.account_service, "get_cache_stats")
    delattr(cache_warmer.llm_service, "get_cache_stats")

    # Execute
    stats = cache_warmer.get_cache_stats()

    # Assert
    assert "timestamp" in stats
    assert "services" in stats
    assert len(stats["services"]) == 0  # No services with stats


def test_format_cache_stats_report(cache_warmer):
    """Test formatting cache statistics report"""
    # Setup
    stats = {
        "timestamp": "2025-10-29T12:00:00",
        "services": {
            "market_data": {
                "hit_rate": 0.85,
                "hits": 100,
                "misses": 15,
                "size": 50,
            },
            "account": {
                "hit_rate": 0.90,
                "hits": 50,
                "misses": 5,
                "size": 10,
            },
        },
    }

    # Execute
    report = cache_warmer.format_cache_stats_report(stats)

    # Assert
    assert "CACHE STATISTICS" in report
    assert "MARKET_DATA" in report
    assert "ACCOUNT" in report
    assert "85.0%" in report  # Market data hit rate
    assert "90.0%" in report  # Account hit rate


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_full_warming_cycle(cache_warmer):
    """Test complete warming cycle"""
    # Warm all caches
    initial_results = await cache_warmer.warm_all_caches()

    # Verify all completed
    assert len(initial_results) == 4

    # Refresh critical caches
    refreshed = await cache_warmer.refresh_critical_caches()
    assert refreshed > 0

    # Get statistics
    stats = cache_warmer.get_cache_stats()
    assert "services" in stats


@pytest.mark.asyncio
async def test_trading_symbols_configuration(cache_warmer):
    """Test that trading symbols are correctly configured"""
    # Assert
    assert len(cache_warmer.trading_symbols) == 6
    assert "BTC/USDT:USDT" in cache_warmer.trading_symbols
    assert "ETH/USDT:USDT" in cache_warmer.trading_symbols
    assert all("/USDT:USDT" in symbol for symbol in cache_warmer.trading_symbols)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
