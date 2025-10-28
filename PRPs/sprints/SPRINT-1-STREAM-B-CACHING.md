# Sprint 1 - Stream B: Caching Integration

**Agent**: Performance Optimizer
**Duration**: 2-3 days
**Total Effort**: 8 hours
**Branch**: `sprint-1/stream-b-caching`

---

## 🎯 Stream Objectives

Integrate CacheService into two critical areas:
1. Market data fetching (reduce API calls by 80%)
2. LLM response caching (reduce API costs by 70%)

**Why These Tasks**: Reduce API costs and improve system performance

---

## 📋 Task Breakdown

### TASK-023: Market Data Caching Integration (4 hours)

**Current State**: No caching, every decision cycle fetches fresh market data

**Performance Impact**:
- Current: ~20 API calls per 3-minute cycle
- Target: ~4 API calls per 3-minute cycle (80% reduction)
- Cost savings: ~$50/month in exchange API fees

**Implementation Steps**:

1. **Add CacheService to MarketDataService** (1 hour)
   - File: `workspace/features/market_data/market_data_service.py`
   - Add cache initialization:
```python
from workspace.features.caching import CacheService

class MarketDataService:
    def __init__(
        self,
        exchange: ccxt.Exchange,
        cache_service: Optional[CacheService] = None,
    ):
        self.exchange = exchange

        # Initialize cache service
        if cache_service is not None:
            self.cache = cache_service
        else:
            self.cache = CacheService()

        logger.info("MarketDataService initialized with caching")
```

2. **Cache OHLCV data** (1 hour)
   - File: `workspace/features/market_data/market_data_service.py`
   - Update `fetch_ohlcv()` method:
```python
async def fetch_ohlcv(
    self,
    symbol: str,
    timeframe: str = "1m",
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    Fetch OHLCV data with caching

    Cache TTL: 60 seconds (data updates every minute)
    """
    # Generate cache key
    cache_key = f"market_data:ohlcv:{symbol}:{timeframe}:{limit}"

    # Try cache first
    cached_data = await self.cache.get(cache_key)
    if cached_data is not None:
        logger.debug(f"Cache hit for OHLCV {symbol} {timeframe}")
        return cached_data

    # Cache miss - fetch from exchange
    logger.debug(f"Cache miss for OHLCV {symbol} {timeframe}")

    try:
        ohlcv = await self.exchange.fetch_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            limit=limit,
        )

        # Convert to structured format
        formatted_data = [
            {
                "timestamp": candle[0],
                "open": Decimal(str(candle[1])),
                "high": Decimal(str(candle[2])),
                "low": Decimal(str(candle[3])),
                "close": Decimal(str(candle[4])),
                "volume": Decimal(str(candle[5])),
            }
            for candle in ohlcv
        ]

        # Cache for 60 seconds
        await self.cache.set(cache_key, formatted_data, ttl_seconds=60)

        return formatted_data

    except Exception as e:
        logger.error(f"Error fetching OHLCV for {symbol}: {e}", exc_info=True)
        raise
```

3. **Cache ticker data** (1 hour)
   - File: `workspace/features/market_data/market_data_service.py`
   - Update `fetch_ticker()` method:
```python
async def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
    """
    Fetch ticker data with caching

    Cache TTL: 30 seconds (ticker updates frequently)
    """
    cache_key = f"market_data:ticker:{symbol}"

    # Try cache first
    cached_ticker = await self.cache.get(cache_key)
    if cached_ticker is not None:
        logger.debug(f"Cache hit for ticker {symbol}")
        return cached_ticker

    # Cache miss - fetch from exchange
    logger.debug(f"Cache miss for ticker {symbol}")

    try:
        ticker = await self.exchange.fetch_ticker(symbol)

        # Extract relevant fields
        formatted_ticker = {
            "symbol": ticker["symbol"],
            "last": Decimal(str(ticker["last"])),
            "bid": Decimal(str(ticker.get("bid", 0))),
            "ask": Decimal(str(ticker.get("ask", 0))),
            "volume": Decimal(str(ticker.get("volume", 0))),
            "timestamp": ticker["timestamp"],
        }

        # Cache for 30 seconds
        await self.cache.set(cache_key, formatted_ticker, ttl_seconds=30)

        return formatted_ticker

    except Exception as e:
        logger.error(f"Error fetching ticker for {symbol}: {e}", exc_info=True)
        raise
```

4. **Write tests** (1 hour)
   - File: `workspace/tests/unit/test_market_data_caching.py` (NEW)
```python
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from workspace.features.market_data import MarketDataService
from workspace.features.caching import CacheService


@pytest.mark.asyncio
async def test_ohlcv_cache_hit():
    """Test OHLCV data is cached and returned on second call"""
    # Setup
    mock_exchange = MagicMock()
    mock_exchange.fetch_ohlcv = AsyncMock(return_value=[
        [1234567890000, 100, 105, 95, 102, 1000],
    ])

    cache = CacheService()
    service = MarketDataService(exchange=mock_exchange, cache_service=cache)

    # First call - should hit exchange
    data1 = await service.fetch_ohlcv("BTC/USDT", "1m", 1)
    assert mock_exchange.fetch_ohlcv.call_count == 1
    assert len(data1) == 1
    assert data1[0]["close"] == Decimal("102")

    # Second call - should hit cache
    data2 = await service.fetch_ohlcv("BTC/USDT", "1m", 1)
    assert mock_exchange.fetch_ohlcv.call_count == 1  # Not called again
    assert data1 == data2

    # Check cache stats
    stats = cache.get_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1


@pytest.mark.asyncio
async def test_ticker_cache_hit():
    """Test ticker data is cached and returned on second call"""
    # Setup
    mock_exchange = MagicMock()
    mock_exchange.fetch_ticker = AsyncMock(return_value={
        "symbol": "BTC/USDT",
        "last": 45000.0,
        "bid": 44999.0,
        "ask": 45001.0,
        "volume": 12345.67,
        "timestamp": 1234567890000,
    })

    cache = CacheService()
    service = MarketDataService(exchange=mock_exchange, cache_service=cache)

    # First call - should hit exchange
    ticker1 = await service.fetch_ticker("BTC/USDT")
    assert mock_exchange.fetch_ticker.call_count == 1
    assert ticker1["last"] == Decimal("45000.0")

    # Second call - should hit cache
    ticker2 = await service.fetch_ticker("BTC/USDT")
    assert mock_exchange.fetch_ticker.call_count == 1  # Not called again
    assert ticker1 == ticker2


@pytest.mark.asyncio
async def test_cache_ttl_expiration():
    """Test cache expires after TTL"""
    import asyncio

    # Setup with short TTL
    mock_exchange = MagicMock()
    mock_exchange.fetch_ticker = AsyncMock(return_value={
        "symbol": "BTC/USDT",
        "last": 45000.0,
        "bid": 44999.0,
        "ask": 45001.0,
        "volume": 12345.67,
        "timestamp": 1234567890000,
    })

    cache = CacheService()
    service = MarketDataService(exchange=mock_exchange, cache_service=cache)

    # Monkey patch set method to use 1 second TTL for testing
    original_fetch = service.fetch_ticker
    async def patched_fetch(symbol):
        cache_key = f"market_data:ticker:{symbol}"
        cached = await cache.get(cache_key)
        if cached:
            return cached
        ticker = await mock_exchange.fetch_ticker(symbol)
        formatted = {
            "symbol": ticker["symbol"],
            "last": Decimal(str(ticker["last"])),
        }
        await cache.set(cache_key, formatted, ttl_seconds=1)  # 1 second TTL
        return formatted

    service.fetch_ticker = patched_fetch

    # First call
    await service.fetch_ticker("BTC/USDT")
    assert mock_exchange.fetch_ticker.call_count == 1

    # Second call (within TTL)
    await service.fetch_ticker("BTC/USDT")
    assert mock_exchange.fetch_ticker.call_count == 1  # Cached

    # Wait for TTL to expire
    await asyncio.sleep(1.1)

    # Third call (after TTL)
    await service.fetch_ticker("BTC/USDT")
    assert mock_exchange.fetch_ticker.call_count == 2  # Cache expired
```

**Validation**:
```bash
# Run tests
pytest workspace/tests/unit/test_market_data_caching.py -v

# Test with real exchange (testnet)
python -c "
import asyncio
from workspace.features.market_data import MarketDataService
from workspace.features.caching import CacheService
import ccxt

async def test():
    exchange = ccxt.binance({
        'apiKey': 'YOUR_TESTNET_KEY',
        'secret': 'YOUR_TESTNET_SECRET',
        'options': {'defaultType': 'future'},
    })
    exchange.set_sandbox_mode(True)

    cache = CacheService()
    service = MarketDataService(exchange=exchange, cache_service=cache)

    # First call (cache miss)
    print('First call...')
    data1 = await service.fetch_ohlcv('BTC/USDT', '1m', 5)
    stats1 = cache.get_stats()
    print(f'Stats after first call: {stats1}')

    # Second call (cache hit)
    print('Second call...')
    data2 = await service.fetch_ohlcv('BTC/USDT', '1m', 5)
    stats2 = cache.get_stats()
    print(f'Stats after second call: {stats2}')

    print(f'Hit rate: {stats2[\"hit_rate_percent\"]}%')

asyncio.run(test())
"
```

---

### TASK-021: LLM Response Caching Integration (4 hours)

**Current State**: Every decision cycle calls LLM, even with identical inputs

**Performance Impact**:
- Current: ~$0.10 per cycle (100 cycles/day = $10/day = $300/month)
- Target: ~$0.03 per cycle (70% cache hit rate = $90/month)
- Cost savings: $210/month (70% reduction)

**Implementation Steps**:

1. **Add CacheService to DecisionEngine** (1 hour)
   - File: `workspace/features/decision_engine/decision_engine.py`
   - Add cache initialization:
```python
from workspace.features.caching import CacheService
import hashlib
import json

class DecisionEngine:
    def __init__(
        self,
        llm_provider: str = "openai",
        model: str = "gpt-4",
        cache_service: Optional[CacheService] = None,
    ):
        self.llm_provider = llm_provider
        self.model = model

        # Initialize cache service
        if cache_service is not None:
            self.cache = cache_service
        else:
            self.cache = CacheService()

        logger.info("DecisionEngine initialized with LLM caching")
```

2. **Implement cache key generation** (1 hour)
   - File: `workspace/features/decision_engine/decision_engine.py`
   - Add helper method:
```python
def _generate_cache_key(
    self,
    prompt: str,
    market_data: Dict[str, Any],
) -> str:
    """
    Generate cache key from prompt and market data

    Key includes:
    - Prompt hash
    - Symbol
    - Rounded price (to nearest $10 for BTC, $1 for others)
    - Rounded indicators (RSI to nearest 5, etc.)

    This allows caching similar market conditions.
    """
    # Round market data to make cache more effective
    symbol = market_data.get("symbol", "UNKNOWN")
    price = market_data.get("price", 0)

    # Round price to reduce cache misses
    if "BTC" in symbol:
        rounded_price = round(price / 10) * 10  # Nearest $10
    else:
        rounded_price = round(price)  # Nearest $1

    # Round indicators
    rsi = market_data.get("rsi", 0)
    rounded_rsi = round(rsi / 5) * 5  # Nearest 5

    macd = market_data.get("macd", 0)
    rounded_macd = round(macd, 2)  # 2 decimals

    # Create hashable representation
    cache_input = {
        "prompt_hash": hashlib.md5(prompt.encode()).hexdigest(),
        "symbol": symbol,
        "price": rounded_price,
        "rsi": rounded_rsi,
        "macd": rounded_macd,
        "model": self.model,
    }

    # Generate cache key
    cache_key = f"llm:decision:{hashlib.md5(json.dumps(cache_input, sort_keys=True).encode()).hexdigest()}"

    return cache_key
```

3. **Cache LLM responses** (1.5 hours)
   - File: `workspace/features/decision_engine/decision_engine.py`
   - Update `generate_trading_signal()` method:
```python
async def generate_trading_signal(
    self,
    symbol: str,
    market_data: Dict[str, Any],
    position: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate trading signal with LLM response caching

    Cache TTL: 180 seconds (3 minutes - one decision cycle)
    """
    # Build prompt
    prompt = self._build_trading_prompt(symbol, market_data, position)

    # Generate cache key
    cache_key = self._generate_cache_key(prompt, market_data)

    # Try cache first
    cached_response = await self.cache.get(cache_key)
    if cached_response is not None:
        logger.info(f"LLM cache hit for {symbol}")

        # Add cache metadata
        cached_response["from_cache"] = True
        cached_response["cache_key"] = cache_key

        return cached_response

    # Cache miss - call LLM
    logger.info(f"LLM cache miss for {symbol}, calling LLM")

    try:
        # Call LLM API
        response = await self._call_llm_api(prompt)

        # Parse response
        trading_signal = self._parse_llm_response(response)

        # Add metadata
        trading_signal["from_cache"] = False
        trading_signal["cache_key"] = cache_key
        trading_signal["llm_model"] = self.model
        trading_signal["prompt_tokens"] = response.get("usage", {}).get("prompt_tokens", 0)
        trading_signal["completion_tokens"] = response.get("usage", {}).get("completion_tokens", 0)

        # Cache for 3 minutes (one decision cycle)
        await self.cache.set(cache_key, trading_signal, ttl_seconds=180)

        return trading_signal

    except Exception as e:
        logger.error(f"Error generating trading signal: {e}", exc_info=True)

        # Return safe default (HOLD)
        return {
            "action": "HOLD",
            "confidence": 0.0,
            "reasoning": f"Error calling LLM: {e}",
            "from_cache": False,
            "error": True,
        }
```

4. **Write tests** (30 minutes)
   - File: `workspace/tests/unit/test_llm_caching.py` (NEW)
```python
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from workspace.features.decision_engine import DecisionEngine
from workspace.features.caching import CacheService


@pytest.mark.asyncio
async def test_llm_response_cached():
    """Test LLM responses are cached"""
    # Setup
    mock_llm_api = AsyncMock(return_value={
        "choices": [{"message": {"content": "BUY"}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 50},
    })

    cache = CacheService()
    engine = DecisionEngine(cache_service=cache)
    engine._call_llm_api = mock_llm_api
    engine._parse_llm_response = MagicMock(return_value={
        "action": "BUY",
        "confidence": 0.8,
        "reasoning": "Strong uptrend",
    })

    market_data = {
        "symbol": "BTC/USDT",
        "price": 45000.0,
        "rsi": 65.0,
        "macd": 100.0,
    }

    # First call - should hit LLM
    signal1 = await engine.generate_trading_signal("BTC/USDT", market_data)
    assert mock_llm_api.call_count == 1
    assert signal1["action"] == "BUY"
    assert signal1["from_cache"] is False

    # Second call with same data - should hit cache
    signal2 = await engine.generate_trading_signal("BTC/USDT", market_data)
    assert mock_llm_api.call_count == 1  # Not called again
    assert signal2["action"] == "BUY"
    assert signal2["from_cache"] is True

    # Check cache stats
    stats = cache.get_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["hit_rate_percent"] == 50.0


@pytest.mark.asyncio
async def test_llm_cache_key_generation():
    """Test cache keys are generated correctly"""
    engine = DecisionEngine()

    market_data1 = {
        "symbol": "BTC/USDT",
        "price": 45123.45,  # Will round to 45120
        "rsi": 67.3,  # Will round to 65
        "macd": 123.456,  # Will round to 123.46
    }

    market_data2 = {
        "symbol": "BTC/USDT",
        "price": 45127.89,  # Will round to 45120 (same)
        "rsi": 68.9,  # Will round to 70 (different)
        "macd": 123.456,
    }

    prompt = "Analyze market and decide"

    key1 = engine._generate_cache_key(prompt, market_data1)
    key2 = engine._generate_cache_key(prompt, market_data2)

    # Different RSI should produce different keys
    assert key1 != key2
    assert key1.startswith("llm:decision:")
    assert key2.startswith("llm:decision:")


@pytest.mark.asyncio
async def test_llm_cache_different_prompts():
    """Test different prompts produce different cache keys"""
    cache = CacheService()
    engine = DecisionEngine(cache_service=cache)
    engine._call_llm_api = AsyncMock(return_value={
        "choices": [{"message": {"content": "BUY"}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 50},
    })
    engine._parse_llm_response = MagicMock(return_value={
        "action": "BUY",
        "confidence": 0.8,
    })

    market_data = {
        "symbol": "BTC/USDT",
        "price": 45000.0,
        "rsi": 65.0,
        "macd": 100.0,
    }

    # Different symbols should not share cache
    await engine.generate_trading_signal("BTC/USDT", market_data)
    await engine.generate_trading_signal("ETH/USDT", {**market_data, "symbol": "ETH/USDT"})

    # Both should be cache misses (different symbols)
    stats = cache.get_stats()
    assert stats["misses"] == 2
    assert stats["hits"] == 0
```

**Validation**:
```bash
# Run tests
pytest workspace/tests/unit/test_llm_caching.py -v

# Monitor cache hit rate in production
python -c "
import asyncio
from workspace.features.decision_engine import DecisionEngine
from workspace.features.caching import CacheService

async def test():
    cache = CacheService()
    engine = DecisionEngine(cache_service=cache)

    # Simulate 10 decision cycles
    for i in range(10):
        market_data = {
            'symbol': 'BTC/USDT',
            'price': 45000.0 + (i * 5),  # Slight price variation
            'rsi': 65.0 + (i * 0.5),
            'macd': 100.0,
        }

        signal = await engine.generate_trading_signal('BTC/USDT', market_data)
        print(f'Cycle {i+1}: {signal[\"action\"]} (from_cache={signal[\"from_cache\"]})')

    # Check cache statistics
    stats = cache.get_stats()
    print(f'\\nCache Statistics:')
    print(f'  Hits: {stats[\"hits\"]}')
    print(f'  Misses: {stats[\"misses\"]}')
    print(f'  Hit Rate: {stats[\"hit_rate_percent\"]}%')

asyncio.run(test())
"
```

---

## ✅ Definition of Done

- [ ] Market data caching integrated into MarketDataService
- [ ] OHLCV and ticker data cached with appropriate TTLs
- [ ] LLM response caching integrated into DecisionEngine
- [ ] Cache key generation handles similar market conditions
- [ ] Cache hit rate > 50% after 1 hour of runtime
- [ ] Unit tests passing (>90% coverage)
- [ ] Integration tests verify cache effectiveness
- [ ] Documentation updated with caching strategy

---

## 🧪 Testing Checklist

```bash
# Unit tests
pytest workspace/tests/unit/test_market_data_caching.py -v
pytest workspace/tests/unit/test_llm_caching.py -v

# Integration test - run system for 1 hour and check cache hit rate
python scripts/test_caching_effectiveness.py

# Verify cost savings
python scripts/calculate_api_cost_savings.py
```

---

## 📝 Commit Strategy

**Commit 1**: Market data caching
```
feat(market-data): add caching to OHLCV and ticker fetching

- Integrate CacheService into MarketDataService
- Cache OHLCV data for 60 seconds
- Cache ticker data for 30 seconds
- Add unit tests for cache hit/miss scenarios
- Target 80% reduction in exchange API calls
```

**Commit 2**: LLM response caching
```
feat(decision-engine): add caching to LLM responses

- Integrate CacheService into DecisionEngine
- Implement smart cache key generation
- Round market data for better cache hit rates
- Cache responses for 180 seconds (one cycle)
- Add unit tests for cache effectiveness
- Target 70% reduction in LLM API costs
```

---

## 🚀 Getting Started

1. **Setup**:
```bash
git checkout -b sprint-1/stream-b-caching
cd /Users/tobiprivat/Documents/GitProjects/personal/trader
```

2. **Verify CacheService exists**:
```bash
ls workspace/features/caching/cache_service.py
# Should exist from previous implementation
```

3. **Run existing tests** (baseline):
```bash
pytest workspace/tests/ -v
```

4. **Start with TASK-023** (Market Data Caching):
   - Add cache to MarketDataService
   - Write tests
   - Validate cache hit rates

5. **Then TASK-021** (LLM Caching):
   - Add cache to DecisionEngine
   - Implement cache key generation
   - Write tests

6. **Monitor cache effectiveness**:
```bash
# After integration, check cache statistics
python -c "
from workspace.features.caching import CacheService
cache = CacheService()
stats = cache.get_stats()
print(f'Hit Rate: {stats[\"hit_rate_percent\"]}%')
"
```

7. **Create PR when done**

---

## 📊 Expected Performance Improvements

**Before Caching**:
- Exchange API calls: ~20 per cycle
- LLM API calls: ~6 per cycle (one per symbol)
- Cost per day: ~$10
- Latency: ~2 seconds per cycle

**After Caching**:
- Exchange API calls: ~4 per cycle (80% cached)
- LLM API calls: ~2 per cycle (70% cached)
- Cost per day: ~$3
- Latency: ~0.5 seconds per cycle

**Monthly Savings**: ~$210/month

---

## 🔍 Cache Strategy Reference

### Market Data Cache TTLs
- OHLCV (1m): 60 seconds
- OHLCV (5m): 300 seconds
- Ticker: 30 seconds
- Order book: 10 seconds

### LLM Cache TTLs
- Trading signals: 180 seconds (one cycle)
- Market analysis: 300 seconds
- Risk assessment: 60 seconds

### Cache Key Patterns
- Market data: `market_data:{type}:{symbol}:{timeframe}:{limit}`
- LLM responses: `llm:decision:{hash(prompt+rounded_data)}`
- Tickers: `market_data:ticker:{symbol}`

---

## ⚠️ Important Notes

1. **Cache Invalidation**:
   - Market data cache auto-expires via TTL
   - LLM cache uses rounded values for better hit rates
   - No manual invalidation needed

2. **Memory Usage**:
   - Cached market data: ~50KB per symbol per timeframe
   - Cached LLM responses: ~2KB per response
   - Expected total: ~5MB after 1 hour

3. **Cache Hit Rate Targets**:
   - Market data: >80% after 15 minutes
   - LLM responses: >70% after 30 minutes
   - Overall: >75% combined

4. **Migration to Redis**:
   - Current implementation uses in-memory dict
   - TODO markers for Redis integration (Stream C)
   - Cache logic remains identical
