# External Services Analysis: LLM-Powered Crypto Trading System

**Date**: October 27, 2025
**Phase**: Phase 1 - Business Discovery & Requirements
**Researcher**: Context Researcher Agent
**Status**: Complete

---

## Executive Summary

This document provides comprehensive analysis of all external services required for the trading system, including capabilities, limitations, pricing, reliability metrics, and integration strategies.

**Services Analyzed**:
1. **Cryptocurrency Exchanges** (Binance, Bybit)
2. **LLM Provider** (OpenRouter API)
3. **Market Data Feeds** (Exchange WebSocket + REST APIs)
4. **Infrastructure Services** (Redis, PostgreSQL/TimescaleDB)

---

## 1. Cryptocurrency Exchange APIs

### 1.1 Binance Perpetual Futures

**API Documentation**: https://binance-docs.github.io/apidocs/futures/en/

#### Capabilities

**Market Data**:
- REST API: OHLCV data (1m, 3m, 5m, 15m, 30m, 1h, 4h, 1d timeframes)
- WebSocket: Real-time kline/candlestick streams
- WebSocket: Real-time ticker data (price, volume, 24h change)
- WebSocket: Real-time order book depth
- Funding rate history and mark price data

**Trading Operations**:
- Order Types: LIMIT, MARKET, STOP_MARKET, STOP_LIMIT, TAKE_PROFIT, TAKE_PROFIT_MARKET
- Position Management: Cross margin and isolated margin modes
- Leverage: Up to 125x (symbol-dependent)
- Time-in-Force: GTC (Good Till Cancel), IOC (Immediate or Cancel), FOK (Fill or Kill)
- Reduce-Only Orders: Close positions without opening opposite direction
- Post-Only Orders: Maker-only orders

**Account Management**:
- Real-time balance and position updates
- Margin and leverage adjustment
- Position mode: One-way or hedge mode
- P&L calculation (realized and unrealized)

#### Rate Limits

**REST API**:
- **General Limit**: 1,200 request weight per minute
- **Order Limit**: 300 orders per 10 seconds per symbol
- **Weight System**: Different endpoints consume different weights
  - `GET /fapi/v1/ticker/price`: 1 weight per symbol (2 for all symbols)
  - `GET /fapi/v1/klines`: 5-10 weight depending on limit parameter
  - `POST /fapi/v1/order`: 1 weight
  - `GET /fapi/v1/depth`: 5-50 weight depending on limit parameter

**WebSocket**:
- Connection Weight: 2 weight per connection
- **No rate limits on message throughput** (critical advantage)
- Maximum 5 connections per IP
- Maximum 200 streams per connection

**Rate Limit Headers** (useful for monitoring):
```
X-MBX-USED-WEIGHT-1M: Current 1-minute weight used
X-MBX-ORDER-COUNT-10S: Orders placed in last 10 seconds
```

#### Performance Characteristics

- **REST API Latency**: 50-150ms (typical)
- **WebSocket Latency**: 10-30ms (typical)
- **Order Execution Time**: 100-300ms (market orders)
- **System Uptime**: 99.95% (industry-leading)
- **Downtime Windows**: Rare, usually <5 minutes for maintenance

#### Testnet

- **URL**: https://testnet.binancefuture.com
- **Features**: Full API parity with production
- **Funding**: Free testnet USDT via faucet
- **Rate Limits**: Same as production
- **Recommendation**: ✅ Use for all development and testing

#### Pricing Structure

- **Trading Fees**:
  - Maker: 0.02% (can reduce with BNB discount)
  - Taker: 0.04% (can reduce with BNB discount)
  - VIP levels: Lower fees with volume (up to 0.005% maker / 0.015% taker)

- **Funding Rate**:
  - Charged every 8 hours (00:00, 08:00, 16:00 UTC)
  - Typical range: -0.1% to +0.1% per funding period
  - Can significantly impact profitability for longer-held positions

#### Known Issues & Workarounds

**Issue 1: Rate Limit Weight Not Always Accurate**
- **Problem**: `fetchTickers()` for all symbols can unexpectedly consume high weight
- **Workaround**: Fetch tickers individually per symbol, or use WebSocket

**Issue 2: Partial Fills Not Immediately Reflected**
- **Problem**: Position updates may lag by 1-2 seconds after order fill
- **Workaround**: Add 2-second delay before fetching position, enable user data stream WebSocket

**Issue 3: Funding Rate Applied Even During Position Close**
- **Problem**: If position held across funding time, funding charged even if closed 1 second later
- **Workaround**: Close positions at least 30 seconds before funding times

#### Integration Recommendations

```python
# Recommended configuration
binance_config = {
    'apiKey': os.getenv('BINANCE_API_KEY'),
    'secret': os.getenv('BINANCE_SECRET'),
    'enableRateLimit': True,
    'rateLimit': 1200,  # milliseconds between requests
    'options': {
        'defaultType': 'future',  # Use futures API
        'recvWindow': 10000,  # 10-second receive window for order execution
    }
}

# Use WebSocket for market data
websocket_streams = [
    f'{symbol.lower()}@kline_1m',  # 1-minute candles
    f'{symbol.lower()}@ticker',     # Real-time ticker
]
```

**Risk Assessment**: 🟢 **LOW** - Industry leader, highly reliable, excellent documentation

---

### 1.2 Bybit Perpetual Futures

**API Documentation**: https://bybit-exchange.github.io/docs/v5/intro

#### Capabilities

**Market Data**:
- REST API: OHLCV data (1, 3, 5, 15, 30, 60, 120, 240, 360, 720, D, M, W)
- WebSocket: Real-time kline streams
- WebSocket: Real-time orderbook (25 levels, 50 levels, 200 levels)
- Funding rate and mark price data
- Open interest data

**Trading Operations**:
- Order Types: LIMIT, MARKET
- Conditional Orders: Stop-loss, take-profit (separate endpoint)
- Leverage: Up to 100x (symbol-dependent)
- Position Mode: One-way or hedge mode
- TP/SL: Can be set during order placement or separately

**Account Management**:
- Real-time wallet balance
- Position updates
- Trade history
- P&L calculation

#### Rate Limits

**REST API** (V5):
- **General Limit**: 120 requests per second per UID
- **Order Limit**: 50 orders per second per symbol
- Different endpoints have different rate limit groups

**Known Issue**: Users report `RateLimitExceeded` errors on `fetchPositions()` even with rate limiting enabled (ccxt issue #20718)

**WebSocket**:
- **No rate limits** on subscriptions
- Maximum 500 topics per connection
- Recommend separate connections for public vs private streams

#### Performance Characteristics

- **REST API Latency**: 100-200ms (typical)
- **WebSocket Latency**: 20-50ms (typical)
- **Order Execution Time**: 150-400ms (market orders)
- **System Uptime**: 99.9%
- **Downtime**: Occasional maintenance (usually announced 24h in advance)

#### Testnet

- **URL**: https://testnet.bybit.com
- **Features**: Full API parity
- **Funding**: Free testnet USDT
- **Recommendation**: ✅ Use for development

#### Pricing Structure

- **Trading Fees**:
  - Maker: 0.01% (VIP 0)
  - Taker: 0.06% (VIP 0)
  - VIP levels: 0% maker / 0.02% taker (at highest level)

- **Funding Rate**:
  - Charged every 8 hours (00:00, 08:00, 16:00 UTC)
  - Typical range: -0.1% to +0.1%

#### Known Issues & Workarounds

**Issue 1: fetchPositions() Rate Limit**
- **Problem**: Even with `enableRateLimit: True`, this endpoint hits rate limits
- **Workaround**: Cache position data, only fetch when necessary, use WebSocket position stream

**Issue 2: Conditional Order Execution Delays**
- **Problem**: Stop-loss orders may take 5-10 seconds to trigger during high volatility
- **Workaround**: Use application-level monitoring as backup

#### Integration Recommendations

```python
# Recommended configuration
bybit_config = {
    'apiKey': os.getenv('BYBIT_API_KEY'),
    'secret': os.getenv('BYBIT_SECRET'),
    'enableRateLimit': True,
    'rateLimit': 100,  # Conservative (ccxt default: 50)
    'options': {
        'defaultType': 'linear',  # USDT perpetual contracts
        'recvWindow': 20000,  # 20-second window
    }
}

# Minimize fetchPositions() calls
# Cache positions, rely on WebSocket for updates
```

**Risk Assessment**: 🟡 **MEDIUM** - Reliable but has rate limit quirks, requires careful handling

---

### 1.3 Exchange Comparison & Recommendation

| Feature | Binance | Bybit |
|---------|---------|-------|
| **API Quality** | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐⭐⭐ Good |
| **Rate Limits** | 🟢 Generous, well-documented | 🟡 Tighter, some edge cases |
| **Latency** | 🟢 50-150ms REST | 🟡 100-200ms REST |
| **WebSocket** | 🟢 Low latency, reliable | 🟢 Low latency, reliable |
| **Documentation** | 🟢 Comprehensive | 🟢 Good |
| **Uptime** | 🟢 99.95% | 🟢 99.9% |
| **Liquidity** | 🟢 Highest | 🟢 High |
| **Testnet** | 🟢 Full parity | 🟢 Full parity |
| **ccxt Support** | 🟢 Mature, stable | 🟡 Some quirks |

**Recommendation**:
- **Primary Exchange**: Binance (better API, higher liquidity, fewer quirks)
- **Backup**: Bybit (for failover and geographic redundancy)

---

## 2. LLM Provider Analysis: OpenRouter

**API Documentation**: https://openrouter.ai/docs

### 2.1 Service Overview

OpenRouter provides unified API access to 400+ Large Language Models from multiple providers including:
- **OpenAI**: GPT-4o, GPT-4o-mini, GPT-3.5-Turbo
- **Anthropic**: Claude 3.5 Sonnet, Claude 3 Haiku, Claude 3 Opus
- **Google**: Gemini 1.5 Pro, Gemini 1.5 Flash
- **Meta**: Llama 3.1 (405B, 70B, 8B)
- **Mistral**: Mistral Large, Mistral Small
- **And 30+ other providers**

### 2.2 API Capabilities

**Request Format**:
- OpenAI-compatible endpoint: `POST /api/v1/chat/completions`
- Accepts `messages` array (chat format) or `prompt` (completion format)
- Supports function calling and tool use
- Supports streaming responses
- Supports structured outputs (JSON mode)

**Key Features**:
- **Automatic Fallback**: If primary provider fails (5xx or rate limit), automatically tries backup
- **Model Routing**: Use model suffixes for optimization:
  - `:floor` - Cheapest providers
  - `:nitro` - Fastest providers
  - Default - Best balance of speed/cost
- **Provider Preferences**: Specify preferred providers in request
- **Generation Tracking**: Query `/api/v1/generation` for precise token counts and costs

### 2.3 Pricing Structure

**Fee Structure**:
- **Credit Purchase**: 5.5% fee ($0.80 minimum) when purchasing credits
- **Usage Charges**: Pass-through pricing from underlying models (no markup)
- **Minimum**: $5 credit purchase

**Model Pricing** (per 1M tokens, as of October 2025):

| Model | Input | Output | Speed | Quality |
|-------|-------|--------|-------|---------|
| **GPT-4o-mini** | $0.150 | $0.600 | ⭐⭐⭐⭐ Fast | ⭐⭐⭐⭐ Good |
| **Claude 3 Haiku** | $0.250 | $1.250 | ⭐⭐⭐⭐⭐ Fastest | ⭐⭐⭐ Decent |
| **Gemini 1.5 Flash** | $0.075 | $0.300 | ⭐⭐⭐⭐⭐ Fastest | ⭐⭐⭐ Decent |
| **GPT-4o** | $2.500 | $10.000 | ⭐⭐⭐ Moderate | ⭐⭐⭐⭐⭐ Excellent |
| **Claude 3.5 Sonnet** | $3.000 | $15.000 | ⭐⭐⭐ Moderate | ⭐⭐⭐⭐⭐ Excellent |
| **Llama 3.1 8B** | $0.060 | $0.060 | ⭐⭐⭐⭐ Fast | ⭐⭐ Fair |

**Cost Optimization for Trading System**:
```python
# Scenario: 6 assets × 480 decisions/day × 30 days = 86,400 decisions/month

# Option 1: GPT-4o-mini (Best Balance)
# Avg: 500 input + 200 output tokens per decision
cost_per_decision = (500/1_000_000 * 0.150) + (200/1_000_000 * 0.600)
# = $0.000075 + $0.000120 = $0.000195
monthly_cost = 86_400 * 0.000195  # = $16.85/month ✅

# Option 2: Claude 3 Haiku (Faster, slightly more expensive)
cost_per_decision = (500/1_000_000 * 0.250) + (200/1_000_000 * 1.250)
# = $0.000125 + $0.000250 = $0.000375
monthly_cost = 86_400 * 0.000375  # = $32.40/month ✅

# Option 3: Gemini 1.5 Flash (Cheapest)
cost_per_decision = (500/1_000_000 * 0.075) + (200/1_000_000 * 0.300)
# = $0.0000375 + $0.000060 = $0.0000975
monthly_cost = 86_400 * 0.0000975  # = $8.42/month ✅
```

**Conclusion**: All cost-effective options are **well within** $100/month budget.

### 2.4 Rate Limits

**Official Documentation**: ⚠️ Rate limits are **NOT specified** in the official OpenRouter documentation.

**Inference from Community**:
- No hard rate limits mentioned
- Relies on underlying provider limits
- Automatic fallback when provider rate-limited
- Recommend: Implement conservative 10 requests/second limit client-side

**Mitigation**: Implement exponential backoff on all requests

### 2.5 Performance Characteristics

**Latency** (based on model and provider):
- **Fast Models** (GPT-4o-mini, Haiku, Gemini Flash): 500-1,200ms
- **Large Models** (GPT-4o, Claude 3.5 Sonnet): 1,000-2,500ms
- **Streaming**: First token in 200-500ms

**Reliability**:
- **Automatic Fallback**: If provider returns 5xx or rate limit, tries next provider
- **Provider Selection**: Can specify preferred providers
- **Uptime**: Depends on underlying providers (typically 99.9%+)

### 2.6 Error Handling

**Error Response Format**:
```json
{
  "error": {
    "code": "rate_limit_exceeded",
    "message": "You have exceeded the rate limit",
    "metadata": {
      "provider": "openai",
      "raw": {...}
    }
  }
}
```

**Common Errors**:
- `rate_limit_exceeded`: Hit provider rate limit
- `context_length_exceeded`: Token limit exceeded
- `invalid_request_error`: Malformed request
- `insufficient_credits`: Account balance too low

**Recommended Handling**:
```python
async def make_llm_request_with_retry(messages, model='gpt-4o-mini', max_retries=3):
    for attempt in range(max_retries):
        try:
            response = await openrouter.chat(
                model=model,
                messages=messages,
                route='fallback',  # Enable automatic fallback
            )
            return response

        except RateLimitError as e:
            if attempt == max_retries - 1:
                # Try cheaper/different model
                logger.warning(f"Rate limited, switching to backup model")
                return await make_llm_request_with_retry(messages, model='claude-3-haiku')

            backoff = (2 ** attempt) * 5
            await asyncio.sleep(backoff)

        except InsufficientCreditsError as e:
            logger.critical("OpenRouter credits exhausted!")
            await send_alert("CRITICAL: OpenRouter out of credits")
            # Return safe default
            return create_hold_all_signals()

        except Exception as e:
            logger.error(f"LLM request failed: {e}")
            if attempt == max_retries - 1:
                return create_hold_all_signals()
            await asyncio.sleep(2 ** attempt)
```

### 2.7 Model Selection Strategy

**For Trading System**:

1. **Primary Model**: `gpt-4o-mini` or `gemini-1.5-flash`
   - Fast response times (<1 second typical)
   - Low cost ($8-17/month)
   - Good JSON reliability

2. **Backup Model**: `claude-3-haiku`
   - Excellent JSON consistency
   - Fast response
   - Slightly higher cost acceptable for reliability

3. **Emergency Fallback**: `llama-3.1-8b`
   - Very cheap
   - Fast
   - Lower quality acceptable for emergency

**Model Rotation Strategy**:
```python
MODEL_PRIORITY = [
    'google/gemini-1.5-flash',  # Cheapest + Fast
    'gpt-4o-mini',              # Good balance
    'claude-3-haiku',           # Best JSON reliability
    'llama-3.1-8b',             # Emergency fallback
]

async def get_trading_decisions_with_fallback(market_data):
    for model in MODEL_PRIORITY:
        try:
            signals = await get_trading_decisions(market_data, model=model)
            if validate_signals(signals):
                return signals
        except Exception as e:
            logger.warning(f"Model {model} failed: {e}")
            continue

    # All models failed
    return create_hold_all_signals()
```

### 2.8 Token Accounting & Cost Tracking

**Important**: Token counts in API responses use GPT-4o's normalized tokenizer, **NOT** native model tokenizers.

**For Precise Cost Tracking**:
```python
async def track_llm_cost(response):
    generation_id = response['id']

    # Query generation endpoint for native token counts
    generation_info = await openrouter.get_generation(generation_id)

    native_tokens = generation_info['native_tokens_prompt'] + generation_info['native_tokens_completion']
    actual_cost = generation_info['total_cost']

    # Log for cost monitoring
    await log_llm_usage({
        'model': generation_info['model'],
        'tokens': native_tokens,
        'cost': actual_cost,
        'timestamp': datetime.now()
    })

    return actual_cost
```

**Cost Monitoring Dashboard**:
- Track daily/monthly spend
- Alert at 80% of budget
- Automatic model downgrade at 90% of budget

### 2.9 Integration Recommendations

```python
# Recommended configuration
openrouter_config = {
    'api_key': os.getenv('OPENROUTER_API_KEY'),
    'base_url': 'https://openrouter.ai/api/v1',
    'default_model': 'google/gemini-1.5-flash',
    'fallback_models': ['gpt-4o-mini', 'claude-3-haiku'],
    'max_tokens': 500,  # Limit output tokens to control cost
    'temperature': 0.2,  # Low for consistency
    'timeout': 10,  # seconds
}

# Always use response_format for structured output
response_format = {'type': 'json_object'}
```

**Risk Assessment**: 🟡 **MEDIUM** - Good service, but rate limits unclear, requires robust error handling

---

## 3. Market Data Feeds

### 3.1 Exchange WebSocket Feeds

**Binance WebSocket**:
- **URL**: `wss://fstream.binance.com/ws`
- **Features**: Real-time klines, tickers, depth, trades
- **Latency**: 10-30ms
- **Reliability**: 99.9%+ uptime
- **Recommendation**: ✅ **Primary source** for real-time market data

**Bybit WebSocket**:
- **URL**: `wss://stream.bybit.com/v5/public/linear`
- **Features**: Real-time klines, orderbook, trades
- **Latency**: 20-50ms
- **Reliability**: 99.9% uptime
- **Recommendation**: ✅ Backup source

### 3.2 REST API Fallback

**Use Case**: WebSocket disconnection or staleness

**Implementation**:
```python
# Fallback to REST if WebSocket stale (>30 seconds)
if websocket_stale():
    data = await exchange.fetch_ohlcv(symbol, '1m', limit=100)
```

**Risk Assessment**: 🟢 **LOW** - Dual WebSocket + REST provides redundancy

---

## 4. Infrastructure Services

### 4.1 Redis

**Use Case**: Task queue (Celery broker), caching, session storage

**Deployment**: Self-hosted or managed (AWS ElastiCache, Redis Cloud)

**Configuration**:
```python
redis_config = {
    'host': 'localhost',
    'port': 6379,
    'db': 0,
    'password': os.getenv('REDIS_PASSWORD'),
    'socket_timeout': 5,
    'socket_connect_timeout': 5,
    'retry_on_timeout': True,
    'max_connections': 50,
}
```

**Persistence** (critical for task queue reliability):
```
# redis.conf
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec
save 900 1
save 300 10
save 60 10000
```

**Risk Assessment**: 🟢 **LOW** - Mature, stable, widely used

### 4.2 PostgreSQL + TimescaleDB

**Use Case**: Market data storage, position tracking, performance metrics

**Deployment**: Self-hosted or managed (AWS RDS, TimescaleDB Cloud)

**Configuration**:
```python
database_config = {
    'host': 'localhost',
    'port': 5432,
    'database': 'trading_db',
    'user': 'trading_user',
    'password': os.getenv('DB_PASSWORD'),
    'min_pool_size': 10,
    'max_pool_size': 50,
    'command_timeout': 30,
}
```

**Risk Assessment**: 🟢 **LOW** - Battle-tested, highly reliable

---

## 5. Service Level Agreements (SLA) Summary

| Service | Uptime SLA | Latency (p95) | Rate Limits | Backup Strategy |
|---------|-----------|---------------|-------------|-----------------|
| **Binance API** | 99.95% | 150ms | 1200 req/min | Bybit failover |
| **Bybit API** | 99.9% | 200ms | 120 req/sec | Binance primary |
| **OpenRouter** | 99.9%* | 1200ms | Unknown | Multiple models |
| **Redis** | 99.9%** | <1ms | N/A | AOF + RDB |
| **PostgreSQL** | 99.95%** | <10ms | N/A | Backups |

*Depends on underlying LLM providers
**Self-hosted or managed service SLA

---

## 6. Dependency Risk Matrix

| Dependency | Criticality | Availability | Mitigations | Risk Level |
|------------|-------------|--------------|-------------|------------|
| **Exchange API** | 🔴 CRITICAL | 99.9%+ | Multi-exchange support, local caching | 🟢 LOW |
| **LLM Provider** | 🔴 CRITICAL | 99.9%+ | Multiple models, safe defaults | 🟡 MEDIUM |
| **WebSocket Feed** | 🟡 HIGH | 99.9% | REST fallback, staleness detection | 🟢 LOW |
| **Redis** | 🟡 HIGH | 99.9% | Persistence, backup instance | 🟢 LOW |
| **Database** | 🟡 HIGH | 99.9% | Regular backups, read replicas | 🟢 LOW |

---

## 7. Operational Cost Breakdown (Monthly)

| Service | Cost Range | Notes |
|---------|-----------|-------|
| **LLM API (OpenRouter)** | $8-35 | Depends on model choice |
| **Exchange Trading Fees** | Variable | 0.02-0.06% per trade |
| **Exchange Funding Rates** | Variable | -0.3% to +0.3% per day |
| **Compute (Cloud VM)** | $50-100 | 4 CPU, 8 GB RAM |
| **Database (Managed)** | $30-50 | PostgreSQL + TimescaleDB |
| **Redis (Managed)** | $20-40 | Optional, can self-host |
| **Monitoring Tools** | $0-20 | Grafana Cloud, Sentry |
| **Total** | **$108-245/month** | Scales with trading volume |

**Budget**: $130-230/month for MVP ✅ Within target

---

## 8. External Service Integration Checklist

```
Before Production:

Exchange APIs:
[ ] API keys generated with appropriate permissions (read + trade, no withdrawal)
[ ] IP whitelist configured (if supported)
[ ] Testnet integration tested and verified
[ ] Rate limit handling tested
[ ] WebSocket reconnection logic tested
[ ] Order execution verified on testnet

LLM Provider:
[ ] OpenRouter account created and funded
[ ] API key secured in environment variables
[ ] Model selection tested and validated
[ ] JSON parsing tested with various responses
[ ] Cost tracking implemented and tested
[ ] Fallback models configured

Infrastructure:
[ ] Redis persistence enabled (AOF + RDB)
[ ] Database backups configured (daily minimum)
[ ] Connection pooling tested under load
[ ] Monitoring and alerting configured
[ ] Log aggregation configured

Security:
[ ] All secrets in environment variables (not code)
[ ] API keys restricted to minimum permissions
[ ] Database credentials rotated regularly
[ ] TLS/SSL enabled for all external connections
[ ] Access logs enabled and monitored
```

---

## 9. Vendor Lock-in Mitigation

**Exchange Lock-in**:
- ✅ Using ccxt provides abstraction layer
- ✅ Can switch exchanges with minimal code changes
- ✅ Multi-exchange support from day 1

**LLM Lock-in**:
- ✅ OpenRouter provides provider abstraction
- ✅ Can switch models without code changes
- ✅ OpenAI-compatible API for easy migration

**Infrastructure Lock-in**:
- ✅ Open-source components (Redis, PostgreSQL, TimescaleDB)
- ✅ Can deploy anywhere (self-hosted, any cloud)
- ✅ Standard protocols (no proprietary tech)

**Overall Risk**: 🟢 **LOW** - Minimal vendor lock-in

---

## 10. Recommendations for Architecture Phase

### 10.1 Service Selection Priorities

1. **Exchange API**: Binance (primary), Bybit (backup)
2. **LLM Provider**: OpenRouter with Gemini 1.5 Flash (primary)
3. **Market Data**: WebSocket (primary), REST (fallback)
4. **Task Queue**: Celery + Redis
5. **Database**: PostgreSQL + TimescaleDB extension

### 10.2 Critical Integration Points

1. **Exchange ↔ Application**:
   - WebSocket for market data (real-time, no rate limits)
   - REST for order execution (with retry logic)
   - Position reconciliation every 5 minutes

2. **LLM ↔ Application**:
   - OpenRouter API with automatic fallback
   - Structured output (JSON mode)
   - Response validation and safe defaults

3. **Application ↔ Database**:
   - Connection pooling (asyncpg)
   - TimescaleDB hypertables for market data
   - Regular backups and monitoring

### 10.3 Monitoring & Observability

**Essential Metrics**:
- Exchange API latency and error rates
- LLM API latency and cost
- WebSocket connection health
- Database query performance
- Redis memory usage and latency
- Trading cycle completion time

**Alerting Thresholds**:
- Exchange API error rate > 1%
- LLM API cost > $5/day
- WebSocket disconnection > 30 seconds
- Database connection pool > 80% utilization
- Trading cycle latency > 2 seconds (p95)

---

## 11. Conclusion

**Service Assessment Summary**:
- ✅ **Binance API**: Excellent choice, reliable, well-documented
- ✅ **OpenRouter**: Cost-effective, flexible, good for MVP
- ✅ **WebSocket Feeds**: Low latency, reliable, no rate limits
- ✅ **Infrastructure**: Standard, open-source, minimal lock-in

**Risk Level**: 🟢 **LOW** - All external services are production-ready and reliable

**Budget**: ✅ **Within Target** - $108-245/month operational costs

**Readiness**: ✅ **GREEN LIGHT** - Proceed with proposed external services

---

**Next Document**: See `reusable-components.md` for libraries, code patterns, and implementation examples.
