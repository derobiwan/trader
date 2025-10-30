"""
Decision Engine & LLM Integration Tests

Comprehensive test suite for:
- LLM Decision Engine (llm_engine.py)
- Prompt Builder (prompt_builder.py)
- Cache Service (cache_service.py)

Coverage targets:
- llm_engine.py: >85% (209 statements)
- prompt_builder.py: >85% (105 statements)
- cache_service.py: >80% (152 statements)

Author: Validation Engineer
Date: 2025-10-30
"""

import asyncio
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from workspace.features.decision_engine.llm_engine import (
    LLMDecisionEngine,
    LLMProvider,
    LLMConfig,
)
from workspace.features.decision_engine.prompt_builder import PromptBuilder
from workspace.features.caching.cache_service import CacheService
from workspace.features.market_data import (
    OHLCV,
    RSI,
    MACD,
    EMA,
    BollingerBands,
    MarketDataSnapshot,
    Ticker,
    Timeframe,
)
from workspace.features.trading_loop import TradingDecision, TradingSignal


# ============================================================================
# FIXTURES - Market Data
# ============================================================================


@pytest.fixture
def sample_ticker():
    """Sample ticker data with all required fields"""
    return Ticker(
        symbol="BTC/USDT:USDT",
        timestamp=datetime.utcnow(),
        bid=Decimal("50190"),
        ask=Decimal("50210"),
        last=Decimal("50200"),
        high_24h=Decimal("51000"),
        low_24h=Decimal("49000"),
        volume_24h=Decimal("500000000"),
        change_24h=Decimal("200"),
        change_24h_pct=Decimal("0.4"),
    )


@pytest.fixture
def sample_ohlcv():
    """Sample OHLCV candle"""
    return OHLCV(
        symbol="BTC/USDT:USDT",
        timeframe=Timeframe.M3,
        timestamp=datetime.utcnow(),
        open=Decimal("50000"),
        high=Decimal("50500"),
        low=Decimal("49500"),
        close=Decimal("50200"),
        volume=Decimal("100"),
        quote_volume=Decimal("5000000"),
        trades_count=1000,
    )


@pytest.fixture
def sample_snapshot(sample_ohlcv, sample_ticker):
    """Complete market data snapshot with all indicators"""
    return MarketDataSnapshot(
        symbol="BTC/USDT:USDT",
        timeframe=Timeframe.M3,
        timestamp=datetime.utcnow(),
        ohlcv=sample_ohlcv,
        ticker=sample_ticker,
        rsi=RSI(
            symbol="BTC/USDT:USDT",
            timeframe=Timeframe.M3,
            timestamp=datetime.utcnow(),
            value=Decimal("55.5"),
            period=14,
        ),
        macd=MACD(
            symbol="BTC/USDT:USDT",
            timeframe=Timeframe.M3,
            timestamp=datetime.utcnow(),
            macd_line=Decimal("100"),
            signal_line=Decimal("80"),
            histogram=Decimal("20"),
            fast_period=12,
            slow_period=26,
            signal_period=9,
        ),
        ema_fast=EMA(
            symbol="BTC/USDT:USDT",
            timeframe=Timeframe.M3,
            timestamp=datetime.utcnow(),
            value=Decimal("50100"),
            period=12,
        ),
        ema_slow=EMA(
            symbol="BTC/USDT:USDT",
            timeframe=Timeframe.M3,
            timestamp=datetime.utcnow(),
            value=Decimal("50000"),
            period=26,
        ),
        bollinger=BollingerBands(
            symbol="BTC/USDT:USDT",
            timeframe=Timeframe.M3,
            timestamp=datetime.utcnow(),
            middle_band=Decimal("50000"),
            upper_band=Decimal("51000"),
            lower_band=Decimal("49000"),
            bandwidth=Decimal("1000"),
            period=20,
            std_dev=Decimal("2"),
        ),
    )


# ============================================================================
# FIXTURES - Engine & Services
# ============================================================================


@pytest.fixture
def cache_service():
    """In-memory cache service for testing"""
    cache = CacheService(
        use_redis=False,
        enabled=True,
        default_ttl_seconds=300,
    )
    yield cache
    # Cleanup
    cache._cache.clear()
    cache._ttl.clear()


@pytest.fixture
def llm_engine(cache_service):
    """LLM Decision Engine with test configuration"""
    engine = LLMDecisionEngine(
        provider="openrouter",
        model="anthropic/claude-3.5-sonnet",
        api_key="test-api-key",
        temperature=0.7,
        max_tokens=2000,
        cache_service=cache_service,
    )
    yield engine
    # Cleanup


@pytest.fixture
def prompt_builder():
    """Prompt builder instance"""
    return PromptBuilder()


# ============================================================================
# TESTS - Cache Key Generation (LLM Engine)
# ============================================================================


class TestCacheKeyGeneration:
    """Test LLM cache key generation and rounding logic"""

    def test_cache_key_single_symbol_btc(self, llm_engine, sample_snapshot):
        """Test cache key generation for BTC with price rounding"""
        snapshots = {"BTCUSDT": sample_snapshot}

        key1 = llm_engine._generate_cache_key(snapshots)

        # Key should be consistent string format
        assert isinstance(key1, str)
        assert key1.startswith("llm:signals:")
        assert len(key1) > 20

        # Same data should produce same key (deterministic)
        key2 = llm_engine._generate_cache_key(snapshots)
        assert key1 == key2

    def test_cache_key_price_rounding_btc(
        self, llm_engine, sample_ticker, sample_ohlcv
    ):
        """Test BTC price rounds to nearest $10"""
        # Create snapshots with slightly different prices
        snapshot1 = MarketDataSnapshot(
            symbol="BTC/USDT:USDT",
            timeframe=Timeframe.M3,
            timestamp=datetime.utcnow(),
            ohlcv=sample_ohlcv,
            ticker=Ticker(
                symbol="BTC/USDT:USDT",
                timestamp=datetime.utcnow(),
                bid=Decimal("50194"),
                ask=Decimal("50204"),
                last=Decimal("50199"),  # Should round to 50200
                high_24h=Decimal("51000"),
                low_24h=Decimal("49000"),
                volume_24h=Decimal("500000000"),
                change_24h=Decimal("200"),
                change_24h_pct=Decimal("0.4"),
            ),
            rsi=RSI(
                symbol="BTC/USDT:USDT",
                timeframe=Timeframe.M3,
                timestamp=datetime.utcnow(),
                value=Decimal("55.5"),
                period=14,
            ),
        )

        snapshot2 = MarketDataSnapshot(
            symbol="BTC/USDT:USDT",
            timeframe=Timeframe.M3,
            timestamp=datetime.utcnow(),
            ohlcv=sample_ohlcv,
            ticker=Ticker(
                symbol="BTC/USDT:USDT",
                timestamp=datetime.utcnow(),
                bid=Decimal("50194"),
                ask=Decimal("50204"),
                last=Decimal("50201"),  # Also rounds to 50200
                high_24h=Decimal("51000"),
                low_24h=Decimal("49000"),
                volume_24h=Decimal("500000000"),
                change_24h=Decimal("200"),
                change_24h_pct=Decimal("0.4"),
            ),
            rsi=RSI(
                symbol="BTC/USDT:USDT",
                timeframe=Timeframe.M3,
                timestamp=datetime.utcnow(),
                value=Decimal("55.5"),
                period=14,
            ),
        )

        key1 = llm_engine._generate_cache_key({"BTCUSDT": snapshot1})
        key2 = llm_engine._generate_cache_key({"BTCUSDT": snapshot2})

        # Should generate same key (prices within rounding range)
        assert key1 == key2

    def test_cache_key_rsi_rounding(self, llm_engine, sample_ticker, sample_ohlcv):
        """Test RSI rounds to nearest 5"""
        snapshot1 = MarketDataSnapshot(
            symbol="BTC/USDT:USDT",
            timeframe=Timeframe.M3,
            timestamp=datetime.utcnow(),
            ohlcv=sample_ohlcv,
            ticker=sample_ticker,
            rsi=RSI(
                symbol="BTC/USDT:USDT",
                timeframe=Timeframe.M3,
                timestamp=datetime.utcnow(),
                value=Decimal("52"),  # Rounds to 50
                period=14,
            ),
        )

        snapshot2 = MarketDataSnapshot(
            symbol="BTC/USDT:USDT",
            timeframe=Timeframe.M3,
            timestamp=datetime.utcnow(),
            ohlcv=sample_ohlcv,
            ticker=sample_ticker,
            rsi=RSI(
                symbol="BTC/USDT:USDT",
                timeframe=Timeframe.M3,
                timestamp=datetime.utcnow(),
                value=Decimal("58"),  # Rounds to 60
                period=14,
            ),
        )

        key1 = llm_engine._generate_cache_key({"BTCUSDT": snapshot1})
        key2 = llm_engine._generate_cache_key({"BTCUSDT": snapshot2})

        # Different RSI ranges = different keys
        assert key1 != key2

    def test_cache_key_multiple_symbols(self, llm_engine, sample_snapshot):
        """Test cache key includes all symbols"""
        snapshots = {
            "BTCUSDT": sample_snapshot,
            "ETHUSDT": sample_snapshot,
            "SOLUSDT": sample_snapshot,
        }

        key1 = llm_engine._generate_cache_key(snapshots)
        key2 = llm_engine._generate_cache_key({"BTCUSDT": sample_snapshot})

        # Different symbols = different keys
        assert key1 != key2

    def test_cache_key_model_included(self, llm_engine, sample_snapshot):
        """Test cache key includes model name"""
        original_model = llm_engine.config.model

        snapshots = {"BTCUSDT": sample_snapshot}
        key1 = llm_engine._generate_cache_key(snapshots)

        # Change model
        llm_engine.config.model = "openai/gpt-4"
        key2 = llm_engine._generate_cache_key(snapshots)

        assert key1 != key2

        # Restore
        llm_engine.config.model = original_model

    def test_cache_key_missing_indicators(
        self, llm_engine, sample_ticker, sample_ohlcv
    ):
        """Test cache key generation with missing indicators"""
        snapshot_no_indicators = MarketDataSnapshot(
            symbol="BTC/USDT:USDT",
            timeframe=Timeframe.M3,
            timestamp=datetime.utcnow(),
            ohlcv=sample_ohlcv,
            ticker=sample_ticker,
            rsi=None,
            macd=None,
        )

        snapshots = {"BTCUSDT": snapshot_no_indicators}
        key = llm_engine._generate_cache_key(snapshots)

        assert isinstance(key, str)
        assert key.startswith("llm:signals:")


# ============================================================================
# TESTS - Cost Calculation
# ============================================================================


class TestCostCalculation:
    """Test LLM API cost calculation for different models"""

    def test_cost_claude_sonnet(self, llm_engine):
        """Test Claude 3.5 Sonnet pricing"""
        # Input: 1000 tokens, Output: 500 tokens
        # Price: $3/1M input, $15/1M output
        cost = llm_engine._calculate_cost(1000, 500, "anthropic/claude-3.5-sonnet")

        expected = (1000 / 1_000_000) * 3 + (500 / 1_000_000) * 15
        assert cost == Decimal(str(expected))
        assert cost > Decimal("0")
        assert cost < Decimal("0.02")  # Less than 2 cents

    def test_cost_gpt4(self, llm_engine):
        """Test GPT-4 pricing (expensive)"""
        # Input: 1000 tokens, Output: 500 tokens
        # Price: $30/1M input, $60/1M output
        cost = llm_engine._calculate_cost(1000, 500, "openai/gpt-4")

        expected = (1000 / 1_000_000) * 30 + (500 / 1_000_000) * 60
        assert cost == Decimal(str(expected))
        assert cost > Decimal("0.00002")  # GPT-4 is expensive

    def test_cost_gpt35_turbo(self, llm_engine):
        """Test GPT-3.5 Turbo pricing (cheap)"""
        # Input: 1000 tokens, Output: 500 tokens
        # Price: $0.50/1M input, $1.50/1M output
        cost = llm_engine._calculate_cost(1000, 500, "openai/gpt-3.5-turbo")

        expected = (1000 / 1_000_000) * 0.50 + (500 / 1_000_000) * 1.50
        assert cost == Decimal(str(expected))
        assert cost < Decimal("0.002")  # Less than 0.2 cents

    def test_cost_default_model(self, llm_engine):
        """Test cost calculation for unknown model (uses default pricing)"""
        cost = llm_engine._calculate_cost(1000, 500, "unknown/model")

        # Default pricing: $1/1M input, $3/1M output
        expected = (1000 / 1_000_000) * 1 + (500 / 1_000_000) * 3
        assert cost == Decimal(str(expected))

    def test_cost_scales_with_tokens(self, llm_engine):
        """Test cost scales linearly with token count"""
        cost_1k = llm_engine._calculate_cost(1000, 1000, "anthropic/claude-3.5-sonnet")
        cost_2k = llm_engine._calculate_cost(2000, 2000, "anthropic/claude-3.5-sonnet")

        # Cost should double
        assert cost_2k == cost_1k * 2

    def test_cost_zero_tokens(self, llm_engine):
        """Test cost calculation with zero tokens (edge case)"""
        cost = llm_engine._calculate_cost(0, 0, "anthropic/claude-3.5-sonnet")
        assert cost == Decimal("0")

    def test_cost_large_tokens(self, llm_engine):
        """Test cost calculation with large token counts"""
        # 100k input, 50k output
        cost = llm_engine._calculate_cost(100000, 50000, "anthropic/claude-3.5-sonnet")

        expected = (100000 / 1_000_000) * 3 + (50000 / 1_000_000) * 15
        assert cost == Decimal(str(expected))
        assert cost > Decimal("0.001")


# ============================================================================
# TESTS - Signal Generation & Caching
# ============================================================================


class TestSignalGenerationAndCaching:
    """Test signal generation with cache integration"""

    @pytest.mark.asyncio
    async def test_generate_signals_cache_hit(self, llm_engine, sample_snapshot):
        """Test cache hit returns cached signals"""
        snapshots = {"BTCUSDT": sample_snapshot}

        # Pre-populate cache
        cache_key = llm_engine._generate_cache_key(snapshots)
        cached_signals = {
            "BTCUSDT": {
                "symbol": "BTCUSDT",
                "decision": "buy",  # Lowercase for enum
                "confidence": "0.8",
                "size_pct": "0.15",
                "stop_loss_pct": "0.02",
                "take_profit_pct": "0.05",
                "reasoning": "Cached signal",
                "model_used": "anthropic/claude-3.5-sonnet",
                "tokens_input": 500,
                "tokens_output": 250,
                "cost_usd": "0.0001",
                "generation_time_ms": 1000,
            }
        }
        await llm_engine.cache.set(cache_key, cached_signals, ttl_seconds=180)

        signals = await llm_engine.generate_signals(
            snapshots=snapshots,
            use_cache=True,
        )

        assert "BTCUSDT" in signals
        assert signals["BTCUSDT"].decision == TradingDecision.BUY
        assert signals["BTCUSDT"].from_cache is True

    @pytest.mark.asyncio
    async def test_generate_signals_cache_miss_calls_llm(
        self, llm_engine, sample_snapshot
    ):
        """Test cache miss triggers LLM call"""
        snapshots = {"BTCUSDT": sample_snapshot}

        mock_response = """
```json
{
  "symbol": "BTCUSDT",
  "decision": "SELL",
  "confidence": 0.7,
  "size_pct": 0.12,
  "stop_loss_pct": 0.03,
  "reasoning": "LLM generated"
}
```
"""

        with patch.object(
            llm_engine, "_call_llm", new=AsyncMock(return_value=(mock_response, {}))
        ):
            signals = await llm_engine.generate_signals(
                snapshots=snapshots,
                use_cache=True,
            )

            assert signals["BTCUSDT"].from_cache is False
            assert signals["BTCUSDT"].decision == TradingDecision.SELL

    @pytest.mark.asyncio
    async def test_generate_signals_caches_response(self, llm_engine, sample_snapshot):
        """Test LLM response is cached after generation"""
        snapshots = {"BTCUSDT": sample_snapshot}

        mock_response = """
```json
{
  "symbol": "BTCUSDT",
  "decision": "HOLD",
  "confidence": 0.5,
  "size_pct": 0.0,
  "reasoning": "Wait for signal"
}
```
"""

        with patch.object(
            llm_engine, "_call_llm", new=AsyncMock(return_value=(mock_response, {}))
        ):
            # First call - cache miss
            await llm_engine.generate_signals(
                snapshots=snapshots,
                use_cache=True,
            )

            # Second call - cache hit
            with patch.object(llm_engine, "_call_llm", new=AsyncMock()) as mock_llm:
                signals2 = await llm_engine.generate_signals(
                    snapshots=snapshots,
                    use_cache=True,
                )

                # LLM should not be called again
                mock_llm.assert_not_called()
                assert signals2["BTCUSDT"].from_cache is True

    @pytest.mark.asyncio
    async def test_generate_signals_usage_data_populated(
        self, llm_engine, sample_snapshot
    ):
        """Test signal includes usage data from LLM"""
        snapshots = {"BTCUSDT": sample_snapshot}

        mock_response = """
```json
{
  "symbol": "BTCUSDT",
  "decision": "BUY",
  "confidence": 0.75,
  "size_pct": 0.15,
  "reasoning": "Signal"
}
```
"""

        usage_data = {
            "prompt_tokens": 1234,
            "completion_tokens": 567,
            "total_tokens": 1801,
        }

        with patch.object(
            llm_engine,
            "_call_llm",
            new=AsyncMock(return_value=(mock_response, usage_data)),
        ):
            signals = await llm_engine.generate_signals(
                snapshots=snapshots,
                use_cache=False,
            )

            signal = signals["BTCUSDT"]
            assert signal.tokens_input == 1234
            assert signal.tokens_output == 567
            assert signal.cost_usd > Decimal("0")
            # generation_time_ms may be 0 for very fast operations (mock)
            assert signal.generation_time_ms >= 0

    @pytest.mark.asyncio
    async def test_generate_signals_cache_disabled(self, llm_engine, sample_snapshot):
        """Test signals can be generated without caching"""
        snapshots = {"BTCUSDT": sample_snapshot}

        mock_response = """
```json
{
  "symbol": "BTCUSDT",
  "decision": "BUY",
  "confidence": 0.8,
  "size_pct": 0.2,
  "reasoning": "Strong signal"
}
```
"""

        with patch.object(
            llm_engine, "_call_llm", new=AsyncMock(return_value=(mock_response, {}))
        ):
            signals = await llm_engine.generate_signals(
                snapshots=snapshots,
                use_cache=False,  # Disable cache
            )

            assert "BTCUSDT" in signals
            assert signals["BTCUSDT"].from_cache is False


# ============================================================================
# TESTS - Cache Service (In-Memory Backend)
# ============================================================================


class TestCacheServiceInMemory:
    """Test in-memory cache service functionality"""

    @pytest.mark.asyncio
    async def test_cache_set_and_get(self, cache_service):
        """Test basic cache set and get"""
        await cache_service.set("test_key", {"data": "value"}, ttl_seconds=60)

        result = await cache_service.get("test_key")

        assert result is not None
        assert result["data"] == "value"

    @pytest.mark.asyncio
    async def test_cache_miss_returns_none(self, cache_service):
        """Test cache miss returns None"""
        result = await cache_service.get("nonexistent_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_ttl_expiration(self, cache_service):
        """Test cache entries expire after TTL"""
        await cache_service.set("expiring_key", {"data": "value"}, ttl_seconds=1)

        # Immediate get - should hit
        result1 = await cache_service.get("expiring_key")
        assert result1 is not None

        # Wait for expiration
        await asyncio.sleep(1.1)

        # After expiration - should miss
        result2 = await cache_service.get("expiring_key")
        assert result2 is None

    @pytest.mark.asyncio
    async def test_cache_delete(self, cache_service):
        """Test cache deletion"""
        await cache_service.set("delete_key", {"data": "value"}, ttl_seconds=60)

        # Verify exists
        assert await cache_service.exists("delete_key")

        # Delete
        deleted = await cache_service.delete("delete_key")
        assert deleted is True

        # Verify deleted
        assert not await cache_service.exists("delete_key")

    @pytest.mark.asyncio
    async def test_cache_delete_nonexistent(self, cache_service):
        """Test deleting nonexistent key returns False"""
        result = await cache_service.delete("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_cache_clear_all(self, cache_service):
        """Test clearing all cache entries"""
        await cache_service.set("key1", {"data": "1"}, ttl_seconds=60)
        await cache_service.set("key2", {"data": "2"}, ttl_seconds=60)
        await cache_service.set("key3", {"data": "3"}, ttl_seconds=60)

        count = await cache_service.clear()

        assert count == 3
        assert await cache_service.get("key1") is None
        assert await cache_service.get("key2") is None
        assert await cache_service.get("key3") is None

    @pytest.mark.asyncio
    async def test_cache_clear_pattern(self, cache_service):
        """Test clearing cache by pattern"""
        await cache_service.set("market:btc", {"data": "1"}, ttl_seconds=60)
        await cache_service.set("market:eth", {"data": "2"}, ttl_seconds=60)
        await cache_service.set("llm:signals", {"data": "3"}, ttl_seconds=60)

        count = await cache_service.clear("market:*")

        assert count == 2
        assert await cache_service.get("market:btc") is None
        assert await cache_service.get("market:eth") is None
        assert await cache_service.get("llm:signals") is not None

    @pytest.mark.asyncio
    async def test_cache_statistics(self, cache_service):
        """Test cache statistics tracking"""
        await cache_service.set("key1", {"data": "1"}, ttl_seconds=60)
        await cache_service.set("key2", {"data": "2"}, ttl_seconds=60)

        # Hits
        await cache_service.get("key1")
        await cache_service.get("key1")

        # Misses
        await cache_service.get("nonexistent")
        await cache_service.get("nonexistent")

        stats = cache_service.get_stats()

        assert stats["hits"] == 2
        assert stats["misses"] == 2
        assert stats["sets"] == 2
        assert stats["total_requests"] == 4
        assert "70" in stats["hit_rate"] or stats["hit_rate_percent"] == 50.0

    @pytest.mark.asyncio
    async def test_cache_disabled(self):
        """Test caching disabled returns None"""
        cache = CacheService(enabled=False)

        await cache.set("key", "value", ttl_seconds=60)
        result = await cache.get("key")

        assert result is None

    @pytest.mark.asyncio
    async def test_cache_get_or_set_hit(self, cache_service):
        """Test get_or_set returns cached value"""
        await cache_service.set("cached_key", "cached_value", ttl_seconds=60)

        async def fetch_func():
            return "new_value"

        result = await cache_service.get_or_set("cached_key", fetch_func)

        assert result == "cached_value"

    @pytest.mark.asyncio
    async def test_cache_get_or_set_miss(self, cache_service):
        """Test get_or_set fetches and caches on miss"""
        fetch_called = False

        async def fetch_func():
            nonlocal fetch_called
            fetch_called = True
            return "fetched_value"

        result = await cache_service.get_or_set("new_key", fetch_func)

        assert result == "fetched_value"
        assert fetch_called is True

        # Verify cached
        cached = await cache_service.get("new_key")
        assert cached == "fetched_value"

    def test_cache_key_generation(self):
        """Test cache key generation utility"""
        key1 = CacheService.generate_key("symbol", "BTCUSDT", prefix="market")
        key2 = CacheService.generate_key("symbol", "BTCUSDT", prefix="market")

        # Should be consistent
        assert key1 == key2
        assert key1.startswith("market:")


# ============================================================================
# TESTS - Prompt Builder Edge Cases
# ============================================================================


class TestPromptBuilderEdgeCases:
    """Test prompt builder with edge cases and special conditions"""

    def test_prompt_builder_empty_positions(self, prompt_builder, sample_snapshot):
        """Test prompt with empty positions dict (not included)"""
        snapshots = {"BTCUSDT": sample_snapshot}

        prompt = prompt_builder.build_trading_prompt(
            snapshots=snapshots,
            capital_chf=Decimal("1000"),
            max_position_size_chf=Decimal("200"),
            current_positions={},  # Empty dict is falsy, so section not included
        )

        # Empty dict is falsy, so positions section is not included
        assert "# Current Open Positions" not in prompt
        assert "# Trading Decision System" in prompt  # System context still included
        assert (
            "# Trading Capital & Risk Parameters" in prompt
        )  # Capital context still included

    def test_prompt_builder_no_positions_arg(self, prompt_builder, sample_snapshot):
        """Test prompt without positions argument"""
        snapshots = {"BTCUSDT": sample_snapshot}

        prompt = prompt_builder.build_trading_prompt(
            snapshots=snapshots,
            capital_chf=Decimal("1000"),
            max_position_size_chf=Decimal("200"),
            current_positions=None,
        )

        assert "# Current Open Positions" not in prompt

    def test_prompt_builder_large_capital(self, prompt_builder, sample_snapshot):
        """Test prompt with large capital amounts"""
        snapshots = {"BTCUSDT": sample_snapshot}

        prompt = prompt_builder.build_trading_prompt(
            snapshots=snapshots,
            capital_chf=Decimal("1000000"),  # 1 million CHF
            max_position_size_chf=Decimal("200000"),
        )

        assert "1,000,000.00" in prompt
        assert "200,000.00" in prompt

    def test_prompt_builder_zero_capital(self, prompt_builder, sample_snapshot):
        """Test prompt with zero capital (edge case)"""
        snapshots = {"BTCUSDT": sample_snapshot}

        prompt = prompt_builder.build_trading_prompt(
            snapshots=snapshots,
            capital_chf=Decimal("0"),
            max_position_size_chf=Decimal("0"),
        )

        assert "CHF 0.00" in prompt

    def test_prompt_builder_no_indicators(
        self, prompt_builder, sample_ticker, sample_ohlcv
    ):
        """Test prompt when snapshot has no technical indicators"""
        snapshot_minimal = MarketDataSnapshot(
            symbol="BTC/USDT:USDT",
            timeframe=Timeframe.M3,
            timestamp=datetime.utcnow(),
            ohlcv=sample_ohlcv,
            ticker=sample_ticker,
            rsi=None,
            macd=None,
            ema_fast=None,
            ema_slow=None,
            bollinger=None,
        )

        snapshots = {"BTCUSDT": snapshot_minimal}

        prompt = prompt_builder.build_trading_prompt(
            snapshots=snapshots,
            capital_chf=Decimal("1000"),
            max_position_size_chf=Decimal("200"),
        )

        # Should still have market data section
        assert "### Price Action" in prompt
        assert "### Latest Candle" in prompt
        assert "### Technical Indicators" in prompt

    def test_prompt_format_snapshot_multiple_symbols(
        self, prompt_builder, sample_snapshot
    ):
        """Test formatting multiple different snapshots"""
        snapshots = {
            "BTCUSDT": sample_snapshot,
            "ETHUSDT": sample_snapshot,
            "SOLUSDT": sample_snapshot,
        }

        formatted = prompt_builder._build_market_data_section(snapshots)

        assert "Number of Assets: 3" in formatted
        assert "BTCUSDT" in formatted
        assert "ETHUSDT" in formatted
        assert "SOLUSDT" in formatted


# ============================================================================
# TESTS - LLM Response Parsing Edge Cases
# ============================================================================


class TestLLMResponseParsing:
    """Test robust parsing of LLM responses with various formats"""

    def test_parse_response_mixed_json_formats(self, llm_engine, sample_snapshot):
        """Test parsing mixed JSON block formats"""
        response = """
Here's my analysis:

```json
{
  "symbol": "BTCUSDT",
  "decision": "BUY",
  "confidence": 0.8,
  "size_pct": 0.15
}
```

For ETH, I think:

{"symbol": "ETHUSDT", "decision": "HOLD", "confidence": 0.5, "size_pct": 0}
"""

        snapshots = {
            "BTCUSDT": sample_snapshot,
            "ETHUSDT": sample_snapshot,
        }

        signals = llm_engine._parse_response(response, snapshots)

        assert len(signals) >= 1
        assert "BTCUSDT" in signals

    def test_parse_response_decimal_precision(self, llm_engine, sample_snapshot):
        """Test parsing maintains decimal precision"""
        response = """
```json
{
  "symbol": "BTCUSDT",
  "decision": "BUY",
  "confidence": 0.7534567,
  "size_pct": 0.123456789
}
```
"""

        snapshots = {"BTCUSDT": sample_snapshot}
        signals = llm_engine._parse_response(response, snapshots)

        signal = signals["BTCUSDT"]
        assert signal.confidence == Decimal("0.7534567")
        assert signal.size_pct == Decimal("0.123456789")

    def test_parse_response_missing_optional_fields(self, llm_engine, sample_snapshot):
        """Test parsing with missing optional fields"""
        response = """
```json
{
  "symbol": "BTCUSDT",
  "decision": "SELL",
  "confidence": 0.6,
  "size_pct": 0.1
}
```
"""

        snapshots = {"BTCUSDT": sample_snapshot}
        signals = llm_engine._parse_response(response, snapshots)

        signal = signals["BTCUSDT"]
        assert signal.stop_loss_pct is None
        assert signal.take_profit_pct is None
        assert signal.reasoning == ""

    def test_parse_response_nested_json_structures(self, llm_engine, sample_snapshot):
        """Test parsing handles nested JSON safely"""
        response = """
```json
{
  "symbol": "BTCUSDT",
  "decision": "BUY",
  "confidence": 0.8,
  "size_pct": 0.15,
  "metadata": {"source": "analysis", "confidence_score": 0.95}
}
```
"""

        snapshots = {"BTCUSDT": sample_snapshot}
        signals = llm_engine._parse_response(response, snapshots)

        # Should still extract required fields
        assert "BTCUSDT" in signals
        assert signals["BTCUSDT"].decision == TradingDecision.BUY

    def test_extract_json_blocks_multiple_types(self, llm_engine):
        """Test extracting various JSON block formats"""
        text = """
Analysis:

```json
{"symbol": "BTC", "decision": "BUY"}
```

Also:
{"symbol": "ETH", "decision": "SELL", "confidence": 0.9}

```json
{
  "symbol": "SOL",
  "decision": "HOLD"
}
```
"""

        blocks = llm_engine._extract_json_blocks(text)

        assert len(blocks) >= 2
        assert any("BTC" in b for b in blocks)


# ============================================================================
# TESTS - Error Handling & Resilience
# ============================================================================


class TestErrorHandlingAndResilience:
    """Test error handling and fail-safe mechanisms"""

    @pytest.mark.asyncio
    async def test_generate_signals_invalid_response_fallback(
        self, llm_engine, sample_snapshot
    ):
        """Test fallback to HOLD signals on invalid response"""
        snapshots = {"BTCUSDT": sample_snapshot, "ETHUSDT": sample_snapshot}

        # Mock invalid response
        with patch.object(
            llm_engine, "_call_llm", new=AsyncMock(return_value=("not json", {}))
        ):
            signals = await llm_engine.generate_signals(snapshots=snapshots)

            # Should return HOLD for all symbols
            assert signals["BTCUSDT"].decision == TradingDecision.HOLD
            assert signals["ETHUSDT"].decision == TradingDecision.HOLD

    @pytest.mark.asyncio
    async def test_generate_signals_partial_response(self, llm_engine, sample_snapshot):
        """Test handling response with only partial symbols"""
        snapshots = {
            "BTCUSDT": sample_snapshot,
            "ETHUSDT": sample_snapshot,
            "SOLUSDT": sample_snapshot,
        }

        mock_response = """
```json
{
  "symbol": "BTCUSDT",
  "decision": "BUY",
  "confidence": 0.8,
  "size_pct": 0.15
}
```

```json
{
  "symbol": "ETHUSDT",
  "decision": "SELL",
  "confidence": 0.7,
  "size_pct": 0.12
}
```
"""

        with patch.object(
            llm_engine, "_call_llm", new=AsyncMock(return_value=(mock_response, {}))
        ):
            signals = await llm_engine.generate_signals(snapshots=snapshots)

            # Should have signals for all
            assert len(signals) == 3
            assert signals["BTCUSDT"].decision == TradingDecision.BUY
            assert signals["ETHUSDT"].decision == TradingDecision.SELL
            # SOL should default to HOLD
            assert signals["SOLUSDT"].decision == TradingDecision.HOLD

    @pytest.mark.asyncio
    async def test_generate_signals_malformed_json(self, llm_engine, sample_snapshot):
        """Test handling malformed JSON in response"""
        snapshots = {"BTCUSDT": sample_snapshot}

        mock_response = """
```json
{
  "symbol": "BTCUSDT",
  "decision": "BUY",
  "confidence": 0.8,
  "size_pct": 0.15,
  "extra": "unclosed
```
"""

        with patch.object(
            llm_engine, "_call_llm", new=AsyncMock(return_value=(mock_response, {}))
        ):
            signals = await llm_engine.generate_signals(snapshots=snapshots)

            # Should still return valid signal (HOLD fallback)
            assert "BTCUSDT" in signals
            assert isinstance(signals["BTCUSDT"], TradingSignal)


# ============================================================================
# TESTS - LLM Provider Configuration
# ============================================================================


class TestLLMProviderConfiguration:
    """Test LLM provider configuration and initialization"""

    def test_llm_provider_enum(self):
        """Test LLM provider enum values"""
        assert LLMProvider.OPENROUTER.value == "openrouter"
        assert LLMProvider.ANTHROPIC.value == "anthropic"
        assert LLMProvider.OPENAI.value == "openai"

    def test_llm_config_dataclass(self):
        """Test LLM configuration dataclass"""
        config = LLMConfig(
            provider=LLMProvider.OPENROUTER,
            model="anthropic/claude-3.5-sonnet",
            api_key="test-key",
            temperature=0.5,
            max_tokens=1500,
            timeout=45.0,
        )

        assert config.provider == LLMProvider.OPENROUTER
        assert config.temperature == 0.5
        assert config.max_tokens == 1500
        assert config.timeout == 45.0

    def test_engine_with_different_providers(self):
        """Test initializing engine with different providers"""
        # OpenRouter
        engine1 = LLMDecisionEngine(
            provider="openrouter",
            model="anthropic/claude-3.5-sonnet",
            api_key="key1",
        )
        assert engine1.config.provider == LLMProvider.OPENROUTER

        # Anthropic (future support)
        engine2 = LLMDecisionEngine(
            provider="anthropic",
            model="claude-3-sonnet",
            api_key="key2",
        )
        assert engine2.config.provider == LLMProvider.ANTHROPIC

        # OpenAI (future support)
        engine3 = LLMDecisionEngine(
            provider="openai",
            model="gpt-4",
            api_key="key3",
        )
        assert engine3.config.provider == LLMProvider.OPENAI


# ============================================================================
# TESTS - Concurrency & Thread Safety
# ============================================================================


class TestConcurrencyAndThreadSafety:
    """Test thread-safe operations on cache and signal generation"""

    @pytest.mark.asyncio
    async def test_concurrent_cache_writes(self, cache_service):
        """Test concurrent cache writes are safe"""

        async def write_task(key: str, value: dict):
            await cache_service.set(key, value, ttl_seconds=60)

        # Concurrent writes
        tasks = [write_task(f"key_{i}", {"data": f"value_{i}"}) for i in range(10)]
        await asyncio.gather(*tasks)

        # Verify all written
        for i in range(10):
            result = await cache_service.get(f"key_{i}")
            assert result is not None

    @pytest.mark.asyncio
    async def test_concurrent_cache_reads(self, cache_service):
        """Test concurrent cache reads are safe"""
        # Pre-populate
        await cache_service.set("shared_key", {"data": "shared"}, ttl_seconds=60)

        async def read_task():
            return await cache_service.get("shared_key")

        # Concurrent reads
        results = await asyncio.gather(*[read_task() for _ in range(10)])

        # All should get same value
        assert all(r["data"] == "shared" for r in results)

    @pytest.mark.asyncio
    async def test_mixed_cache_operations(self, cache_service):
        """Test mixed cache operations (read/write) are safe"""

        async def mixed_tasks():
            tasks = []
            for i in range(5):
                tasks.append(cache_service.set(f"k{i}", {"v": i}, ttl_seconds=60))
            for i in range(5):
                tasks.append(cache_service.get(f"k{i}"))
            for i in range(5):
                tasks.append(cache_service.delete(f"k{i}"))
            return await asyncio.gather(*tasks, return_exceptions=True)

        results = await mixed_tasks()

        # Should complete without errors
        assert len(results) == 15
        assert all(not isinstance(r, Exception) for r in results)


# ============================================================================
# TESTS - Additional Cache Service Coverage
# ============================================================================


class TestCacheServiceAdvanced:
    """Advanced cache service tests for better coverage"""

    @pytest.mark.asyncio
    async def test_cache_json_serialization(self, cache_service):
        """Test cache properly serializes JSON data"""
        complex_data = {
            "nested": {
                "list": [1, 2, 3],
                "decimal": Decimal("123.45"),
            }
        }

        await cache_service.set("complex", complex_data, ttl_seconds=60)
        result = await cache_service.get("complex")

        assert result is not None
        assert result["nested"]["list"] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_cache_decimal_handling(self, cache_service):
        """Test cache handles Decimal values correctly"""
        data_with_decimal = {"price": Decimal("99.99"), "qty": Decimal("1.5")}

        await cache_service.set("decimal_data", data_with_decimal, ttl_seconds=60)
        result = await cache_service.get("decimal_data")

        assert result is not None

    @pytest.mark.asyncio
    async def test_cache_large_value(self, cache_service):
        """Test cache with large data"""
        large_data = {f"key_{i}": f"value_{i}" for i in range(100)}

        await cache_service.set("large", large_data, ttl_seconds=60)
        result = await cache_service.get("large")

        assert result is not None
        assert len(result) == 100

    @pytest.mark.asyncio
    async def test_cache_special_characters(self, cache_service):
        """Test cache with special characters in keys and values"""
        special_key = "key:with:colons:and:symbols!"
        special_value = {"text": "contains\nnewlines\tand\rspecial"}

        await cache_service.set(special_key, special_value, ttl_seconds=60)
        result = await cache_service.get(special_key)

        assert result is not None

    @pytest.mark.asyncio
    async def test_cache_very_short_ttl(self, cache_service):
        """Test cache with very short TTL"""
        await cache_service.set("short_ttl", "value", ttl_seconds=1)

        # Should exist immediately
        assert await cache_service.exists("short_ttl")

        # Should expire quickly
        await asyncio.sleep(1.1)
        assert not await cache_service.exists("short_ttl")

    @pytest.mark.asyncio
    async def test_cache_pattern_matching_edge_cases(self, cache_service):
        """Test pattern matching with edge cases"""
        await cache_service.set("prefix:key1", "v1", ttl_seconds=60)
        await cache_service.set("prefix:key2", "v2", ttl_seconds=60)
        await cache_service.set("other:key", "v3", ttl_seconds=60)

        # Clear with prefix
        count = await cache_service.clear("prefix")

        assert count == 2
        assert await cache_service.get("other:key") is not None
        assert await cache_service.get("prefix:key1") is None

    @pytest.mark.asyncio
    async def test_cache_get_nonexistent_key_after_delete(self, cache_service):
        """Test getting a key after deletion"""
        await cache_service.set("temp", "value", ttl_seconds=60)
        assert await cache_service.exists("temp")

        await cache_service.delete("temp")
        assert not await cache_service.exists("temp")

        result = await cache_service.get("temp")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_overwrite_existing_key(self, cache_service):
        """Test overwriting existing cache key"""
        await cache_service.set("key", "value1", ttl_seconds=60)
        result1 = await cache_service.get("key")
        assert result1 == "value1"

        await cache_service.set("key", "value2", ttl_seconds=60)
        result2 = await cache_service.get("key")
        assert result2 == "value2"

    @pytest.mark.asyncio
    async def test_cache_different_ttl_values(self, cache_service):
        """Test cache with different TTL values"""
        await cache_service.set("short", "value", ttl_seconds=1)
        await cache_service.set("long", "value", ttl_seconds=300)

        # Both should exist immediately
        assert await cache_service.exists("short")
        assert await cache_service.exists("long")

        # Wait for short to expire
        await asyncio.sleep(1.1)

        assert not await cache_service.exists("short")
        assert await cache_service.exists("long")

    @pytest.mark.asyncio
    async def test_cache_stats_reset_after_clear(self, cache_service):
        """Test cache stats after clear"""
        # Build stats
        await cache_service.set("k1", "v1", ttl_seconds=60)
        await cache_service.get("k1")  # Hit
        await cache_service.get("k2")  # Miss

        stats_before = cache_service.get_stats()
        assert stats_before["hits"] > 0

        # Clear and check stats
        await cache_service.clear()
        stats_after = cache_service.get_stats()

        # Stats should still be present (not cleared)
        assert stats_after["cache_size"] == 0

    def test_cache_key_generation_uniqueness(self):
        """Test cache key generation produces unique keys"""
        keys = set()
        for i in range(100):
            key = CacheService.generate_key(f"symbol_{i}", prefix="market")
            keys.add(key)

        # All keys should be unique
        assert len(keys) == 100

    def test_cache_key_generation_consistency(self):
        """Test cache key generation is consistent"""
        key1 = CacheService.generate_key("BTCUSDT", "price", prefix="market")
        key2 = CacheService.generate_key("BTCUSDT", "price", prefix="market")
        key3 = CacheService.generate_key("ETHUSDT", "price", prefix="market")

        assert key1 == key2
        assert key1 != key3


# ============================================================================
# TESTS - LLM Engine Additional Coverage
# ============================================================================


class TestLLMEngineAdditional:
    """Additional LLM engine tests for complete coverage"""

    def test_llm_invalid_provider(self):
        """Test engine with invalid provider raises error"""
        with pytest.raises(ValueError):
            LLMDecisionEngine(
                provider="invalid_provider",
                model="test",
                api_key="key",
            )

    def test_cache_key_with_no_indicators(
        self, llm_engine, sample_ticker, sample_ohlcv
    ):
        """Test cache key generation with all indicators missing"""
        snapshot = MarketDataSnapshot(
            symbol="BTC/USDT:USDT",
            timeframe=Timeframe.M3,
            timestamp=datetime.utcnow(),
            ohlcv=sample_ohlcv,
            ticker=sample_ticker,
        )

        key = llm_engine._generate_cache_key({"BTCUSDT": snapshot})
        assert isinstance(key, str)
        assert len(key) > 0

    def test_llm_config_defaults(self):
        """Test default LLM configuration values"""
        engine = LLMDecisionEngine(
            provider="openrouter",
            model="anthropic/claude-3.5-sonnet",
            api_key="test",
        )

        assert engine.config.temperature == 0.7
        assert engine.config.max_tokens == 2000
        assert engine.config.timeout == 30.0
        assert engine.prompt_builder is not None

    @pytest.mark.asyncio
    async def test_generate_signals_with_all_parameters(
        self, llm_engine, sample_snapshot
    ):
        """Test signal generation with all optional parameters"""
        snapshots = {"BTCUSDT": sample_snapshot}
        positions = {"BTCUSDT": {"side": "long", "size": 0.01}}
        risk_context = {"daily_loss": "-150", "open_positions": "2/6"}

        mock_response = """
```json
{
  "symbol": "BTCUSDT",
  "decision": "CLOSE",
  "confidence": 0.9,
  "size_pct": 0.0,
  "stop_loss_pct": 0.02,
  "take_profit_pct": 0.05,
  "reasoning": "Take profit"
}
```
"""

        with patch.object(
            llm_engine, "_call_llm", new=AsyncMock(return_value=(mock_response, {}))
        ):
            signals = await llm_engine.generate_signals(
                snapshots=snapshots,
                capital_chf=Decimal("10000"),
                max_position_size_chf=Decimal("2000"),
                current_positions=positions,
                risk_context=risk_context,
                use_cache=False,
            )

            assert signals["BTCUSDT"].decision == TradingDecision.CLOSE


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
