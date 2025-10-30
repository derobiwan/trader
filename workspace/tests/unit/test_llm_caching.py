"""
Unit tests for LLM response caching

Tests cache hit/miss scenarios for LLM decision generation.

Author: Sprint 1 Stream B
Date: 2025-10-28
"""

import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import AsyncMock
from workspace.features.decision_engine import LLMDecisionEngine
from workspace.features.market_data import MarketDataSnapshot, Ticker, OHLCV, Timeframe
from workspace.features.trading_loop import TradingDecision
from workspace.features.caching import CacheService


def create_test_snapshot(
    symbol: str, price: float, rsi: float = 65.0, macd: float = 100.0
) -> MarketDataSnapshot:
    """Helper to create test market data snapshot"""
    ticker = Ticker(
        symbol=symbol,
        last=Decimal(str(price)),
        bid=Decimal(str(price - 1)),
        ask=Decimal(str(price + 1)),
        high_24h=Decimal(str(price + 500)),
        low_24h=Decimal(str(price - 500)),
        volume_24h=Decimal("1000"),
        change_24h=Decimal("100"),
        change_24h_pct=Decimal("2.0"),
        timestamp=datetime.utcnow(),
    )

    ohlcv = OHLCV(
        symbol=symbol,
        timeframe=Timeframe.M3,
        timestamp=datetime.utcnow(),
        open=Decimal(str(price - 5)),
        high=Decimal(str(price + 5)),
        low=Decimal(str(price - 10)),
        close=Decimal(str(price)),
        volume=Decimal("1000"),
        quote_volume=Decimal(str(price * 1000)),
        trades_count=100,
    )

    # Create RSI and MACD objects (simplified for testing)
    from workspace.features.market_data.models import RSI, MACD

    rsi_obj = RSI(
        symbol=symbol,
        timeframe=Timeframe.M3,
        timestamp=datetime.utcnow(),
        value=Decimal(str(rsi)),
        period=14,
        overbought_level=Decimal("70"),
        oversold_level=Decimal("30"),
    )

    macd_obj = MACD(
        symbol=symbol,
        timeframe=Timeframe.M3,
        timestamp=datetime.utcnow(),
        macd_line=Decimal(str(macd)),
        signal_line=Decimal(str(macd - 10)),
        histogram=Decimal("10"),
        fast_period=12,
        slow_period=26,
        signal_period=9,
    )

    return MarketDataSnapshot(
        symbol=symbol,
        timeframe=Timeframe.M3,
        timestamp=datetime.utcnow(),
        ohlcv=ohlcv,
        ticker=ticker,
        rsi=rsi_obj,
        macd=macd_obj,
    )


@pytest.mark.asyncio
async def test_llm_response_cached():
    """Test LLM responses are cached and returned on second call"""
    # Setup
    cache = CacheService()
    engine = LLMDecisionEngine(
        provider="openrouter",
        model="anthropic/claude-3.5-sonnet",
        api_key="test-key",
        cache_service=cache,
    )

    # Mock LLM API call
    mock_response_text = """
    ```json
    {"symbol": "BTC/USDT:USDT", "decision": "buy", "confidence": 0.8, "size_pct": 0.2, "reasoning": "Strong uptrend"}
    ```
    """
    mock_usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
    engine._call_llm = AsyncMock(return_value=(mock_response_text, mock_usage))

    # Create test snapshot
    snapshots = {
        "BTC/USDT:USDT": create_test_snapshot(
            "BTC/USDT:USDT", 45000.0, rsi=65.0, macd=100.0
        )
    }

    # First call - should hit LLM
    signals1 = await engine.generate_signals(snapshots, use_cache=True)
    assert engine._call_llm.call_count == 1
    assert "BTC/USDT:USDT" in signals1
    assert signals1["BTC/USDT:USDT"].decision == TradingDecision.BUY
    assert signals1["BTC/USDT:USDT"].from_cache is False

    # Second call with same data - should hit cache
    signals2 = await engine.generate_signals(snapshots, use_cache=True)
    assert engine._call_llm.call_count == 1  # Not called again
    assert "BTC/USDT:USDT" in signals2
    assert signals2["BTC/USDT:USDT"].decision == TradingDecision.BUY
    assert signals2["BTC/USDT:USDT"].from_cache is True

    # Check cache stats
    stats = cache.get_stats()
    assert stats["hits"] >= 1
    assert stats["misses"] >= 1


@pytest.mark.asyncio
async def test_llm_cache_key_generation():
    """Test cache keys handle similar market conditions"""
    # Setup
    cache = CacheService()
    engine = LLMDecisionEngine(
        provider="openrouter",
        model="anthropic/claude-3.5-sonnet",
        api_key="test-key",
        cache_service=cache,
    )

    # Create snapshots with slightly different prices (should round to same)
    snapshot1 = create_test_snapshot("BTC/USDT:USDT", 45123.0, rsi=67.3, macd=123.456)
    snapshot2 = create_test_snapshot("BTC/USDT:USDT", 45127.0, rsi=68.9, macd=123.456)

    key1 = engine._generate_cache_key({"BTC/USDT:USDT": snapshot1})
    key2 = engine._generate_cache_key({"BTC/USDT:USDT": snapshot2})

    # Prices round to 45120, but RSI differs (65 vs 70)
    # So keys should be different
    assert key1 != key2
    assert key1.startswith("llm:signals:")
    assert key2.startswith("llm:signals:")


@pytest.mark.asyncio
async def test_llm_cache_with_similar_prices():
    """Test that similar prices use the same cache entry"""
    # Setup
    cache = CacheService()
    engine = LLMDecisionEngine(
        provider="openrouter",
        model="anthropic/claude-3.5-sonnet",
        api_key="test-key",
        cache_service=cache,
    )

    # Mock LLM
    mock_response_text = """
    ```json
    {"symbol": "BTC/USDT:USDT", "decision": "buy", "confidence": 0.8, "size_pct": 0.2, "reasoning": "Strong uptrend"}
    ```
    """
    mock_usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
    engine._call_llm = AsyncMock(return_value=(mock_response_text, mock_usage))

    # Prices within $10 should round to same value
    snapshot1 = create_test_snapshot("BTC/USDT:USDT", 45123.0, rsi=65.0, macd=100.0)
    snapshot2 = create_test_snapshot("BTC/USDT:USDT", 45127.0, rsi=65.0, macd=100.0)

    # First call
    signals1 = await engine.generate_signals(
        {"BTC/USDT:USDT": snapshot1}, use_cache=True
    )
    assert engine._call_llm.call_count == 1

    # Second call with similar price - should hit cache
    signals2 = await engine.generate_signals(
        {"BTC/USDT:USDT": snapshot2}, use_cache=True
    )
    assert engine._call_llm.call_count == 1  # Not called again

    # Both should have same decision
    assert signals1["BTC/USDT:USDT"].decision == signals2["BTC/USDT:USDT"].decision


@pytest.mark.asyncio
async def test_llm_cache_disabled():
    """Test that disabling cache works correctly"""
    # Setup
    cache = CacheService()
    engine = LLMDecisionEngine(
        provider="openrouter",
        model="anthropic/claude-3.5-sonnet",
        api_key="test-key",
        cache_service=cache,
    )

    # Mock LLM
    mock_response_text = """
    ```json
    {"symbol": "BTC/USDT:USDT", "decision": "buy", "confidence": 0.8, "size_pct": 0.2, "reasoning": "Strong uptrend"}
    ```
    """
    mock_usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
    engine._call_llm = AsyncMock(return_value=(mock_response_text, mock_usage))

    snapshots = {"BTC/USDT:USDT": create_test_snapshot("BTC/USDT:USDT", 45000.0)}

    # Call with cache disabled - should always hit LLM
    await engine.generate_signals(snapshots, use_cache=False)
    assert engine._call_llm.call_count == 1

    await engine.generate_signals(snapshots, use_cache=False)
    assert engine._call_llm.call_count == 2  # Called again

    # Cache should not be used
    stats = cache.get_stats()
    assert stats["sets"] == 0


@pytest.mark.asyncio
async def test_llm_cache_different_symbols():
    """Test that different symbols don't share cache"""
    # Setup
    cache = CacheService()
    engine = LLMDecisionEngine(
        provider="openrouter",
        model="anthropic/claude-3.5-sonnet",
        api_key="test-key",
        cache_service=cache,
    )

    # Mock LLM to return different signals for each symbol
    def mock_call_llm_side_effect(prompt):
        if "BTC" in prompt:
            response = """
            ```json
            {"symbol": "BTC/USDT:USDT", "decision": "buy", "confidence": 0.8, "size_pct": 0.2, "reasoning": "BTC strong"}
            ```
            """
        else:
            response = """
            ```json
            {"symbol": "ETH/USDT:USDT", "decision": "sell", "confidence": 0.7, "size_pct": 0.15, "reasoning": "ETH weak"}
            ```
            """
        mock_usage = {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
        }
        return response, mock_usage

    engine._call_llm = AsyncMock(side_effect=mock_call_llm_side_effect)

    # Create snapshots for two symbols
    btc_snapshot = create_test_snapshot("BTC/USDT:USDT", 45000.0)
    eth_snapshot = create_test_snapshot("ETH/USDT:USDT", 2500.0)

    # Call with BTC
    signals_btc = await engine.generate_signals(
        {"BTC/USDT:USDT": btc_snapshot}, use_cache=True
    )
    assert signals_btc["BTC/USDT:USDT"].decision == TradingDecision.BUY

    # Call with ETH - should not use BTC cache
    signals_eth = await engine.generate_signals(
        {"ETH/USDT:USDT": eth_snapshot}, use_cache=True
    )
    assert signals_eth["ETH/USDT:USDT"].decision == TradingDecision.SELL

    # Both should be cache misses
    assert engine._call_llm.call_count == 2


@pytest.mark.asyncio
async def test_llm_cache_observability_fields():
    """Test that cached signals preserve observability fields"""
    # Setup
    cache = CacheService()
    engine = LLMDecisionEngine(
        provider="openrouter",
        model="anthropic/claude-3.5-sonnet",
        api_key="test-key",
        cache_service=cache,
    )

    # Mock LLM
    mock_response_text = """
    ```json
    {"symbol": "BTC/USDT:USDT", "decision": "buy", "confidence": 0.8, "size_pct": 0.2, "reasoning": "Strong uptrend"}
    ```
    """
    mock_usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
    engine._call_llm = AsyncMock(return_value=(mock_response_text, mock_usage))

    snapshots = {"BTC/USDT:USDT": create_test_snapshot("BTC/USDT:USDT", 45000.0)}

    # First call
    signals1 = await engine.generate_signals(snapshots, use_cache=True)
    signal1 = signals1["BTC/USDT:USDT"]

    # Check observability fields are set
    assert signal1.model_used == "anthropic/claude-3.5-sonnet"
    assert signal1.tokens_input == 100
    assert signal1.tokens_output == 50
    assert signal1.cost_usd is not None
    assert signal1.cost_usd > 0
    assert signal1.generation_time_ms is not None

    # Second call (cached)
    signals2 = await engine.generate_signals(snapshots, use_cache=True)
    signal2 = signals2["BTC/USDT:USDT"]

    # Cached signal should preserve observability fields
    assert signal2.model_used == signal1.model_used
    assert signal2.tokens_input == signal1.tokens_input
    assert signal2.tokens_output == signal1.tokens_output
    assert signal2.cost_usd == signal1.cost_usd
    assert signal2.from_cache is True
