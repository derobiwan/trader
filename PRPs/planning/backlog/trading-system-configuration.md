# Trading System Configuration - Stakeholder Decisions

**Document Version**: 1.0
**Date**: 2025-10-27
**Phase**: P1 - Business Discovery & Requirements
**Status**: Approved by Stakeholder
**Source**: Stakeholder Design Decision Session

---

## Configuration Summary

This document captures the key configuration decisions made by the stakeholder that will guide architecture and implementation.

### 1. Capital Allocation

**Initial Trading Capital**: CHF 2,626.96 (~$2,950 USD at current exchange rates)

**Impact on System Design**:
- **Position Sizing**: Calculate risk per trade as percentage of CHF 2,626.96
- **Minimum Position Size**: Set minimum order thresholds based on exchange requirements
- **Leverage Limits**: Maximum exposure = CHF 2,626.96 * leverage (5-40x range)
- **Database Precision**: Use DECIMAL(20,8) for Swiss Franc amounts
- **Risk Per Trade**: Typical 1-2% risk = CHF 26-52 per trade

**Risk Calculations**:
```
Maximum Daily Loss: CHF 183.89 (-7% circuit breaker)
Maximum Single Trade Risk: CHF 52.54 (2% of capital)
Typical Position Size (10x leverage): CHF 263-526 notional
Maximum Concurrent Positions: 6 cryptocurrencies
```

**Currency Handling**:
- Primary currency: Swiss Franc (CHF)
- Exchange quotation: USD/USDT (most exchanges)
- Conversion: Real-time CHF/USD rate for display
- Position sizing: Based on CHF value

---

### 2. Risk Management Parameters

**Daily Loss Limit**: -7% (More Aggressive Approach)

**Circuit Breaker Trigger**: CHF 183.89 loss in single day
- When triggered: Close ALL positions immediately
- Reset: Next trading day (00:00 UTC)
- Override: Manual approval required to resume trading

**Risk Tolerance**: More Aggressive
- Gives strategy more room to work
- Higher drawdown tolerance
- Potentially higher returns with controlled risk

**Position Limits**:
- Maximum leverage: 40x (exchange-dependent)
- Minimum leverage: 5x
- Maximum position exposure: 80% of account (CHF 2,101.57)
- Maximum single position: 20% of account (CHF 525.39)

**Stop-Loss Policy**:
- **100% Adherence Required**: Every position MUST have stop-loss
- No exceptions, system rejects positions without stop-loss
- Multi-layered protection:
  1. Exchange-level stop-loss order (primary)
  2. Application-level monitoring (secondary)
  3. Emergency shutdown mechanism (failsafe)

---

### 3. Exchange Configuration

**Primary Exchange**: Bybit

**Rationale**:
- Lower fees compared to Binance (0.055% maker, 0.075% taker vs Binance 0.10%)
- Strong derivatives platform (perpetual futures)
- Good API documentation and reliability
- Popular in Asian markets
- Competitive leverage options

**Bybit Specific Considerations**:
- **API Rate Limits**:
  - REST API: 120 requests/minute (authenticated)
  - WebSocket: 200 connections max, unlimited messages
  - Order placement: 100 orders/second
- **Supported Assets** (Perpetual Futures):
  - BTCUSDT (Bitcoin)
  - ETHUSDT (Ethereum)
  - SOLUSDT (Solana)
  - BNBUSDT (Binance Coin)
  - ADAUSDT (Cardano)
  - DOGEUSDT (Dogecoin)
  - Additional pairs available as needed
- **Minimum Order Sizes**:
  - BTC: 0.001 BTC (~$90 at $90K/BTC)
  - ETH: 0.01 ETH (~$30 at $3K/ETH)
  - Others: Vary by asset (typically $5-20 minimum)
- **Leverage Limits**:
  - BTC/ETH: Up to 100x (we'll use max 40x for safety)
  - Altcoins: Typically 25-50x
- **Fees**:
  - Maker: 0.055% (rebate with high volume)
  - Taker: 0.075%
  - Funding rate: Every 8 hours (can be positive or negative)

**API Integration Requirements**:
- API Key: Required (trade permissions only, no withdrawal)
- Secret Key: AES-256 encrypted storage
- WebSocket: Primary for market data (doesn't count against rate limits)
- REST API: For order placement and account queries
- Testnet: Available for paper trading (testnet.bybit.com)

**Failover Strategy**:
- Primary: Bybit WebSocket + REST
- Fallback: Bybit REST only (if WebSocket down)
- Emergency: Manual intervention if both fail

---

### 4. LLM Model Configuration

**Primary Model**: DeepSeek Chat V3.1

**Pricing** (Post-promotional, Feb 2025):
- Input tokens: $0.27 per 1M tokens
- Output tokens: $1.10 per 1M tokens
- Cache hit: $0.068 per 1M tokens

**Expected Monthly Cost** (Primary Model):
```
Assumptions:
- 480 trading cycles per day (3-minute intervals)
- ~1,000 input tokens per cycle (market data + prompt)
- ~500 output tokens per cycle (trading decisions)

Daily Token Usage:
- Input: 480,000 tokens
- Output: 240,000 tokens

Monthly Token Usage (30 days):
- Input: 14.4M tokens
- Output: 7.2M tokens

Monthly Cost:
- Input: 14.4M * $0.27 = $3.89
- Output: 7.2M * $1.10 = $7.92
- Total: ~$12/month
```

**Backup Model**: Qwen3 Max (via OpenRouter)

**Pricing**:
- Input tokens: $1.20 per 1M tokens
- Output tokens: $6.00 per 1M tokens

**Expected Monthly Cost** (Backup Model):
```
Same usage assumptions as primary:

Monthly Cost:
- Input: 14.4M * $1.20 = $17.28
- Output: 7.2M * $6.00 = $43.20
- Total: ~$60/month
```

**Cost Analysis**:
- **Primary (DeepSeek)**: ~$12/month ✅ **EXCELLENT** - 88% under budget
- **Backup (Qwen3 Max)**: ~$60/month ✅ **Good** - 40% under budget
- **Total Budget**: $100/month (stakeholder requirement)
- **Safety Margin**: $88/month (733% headroom with primary model)

**Model Selection Rationale**:

**DeepSeek Chat V3.1** (Primary):
- ✅ Extremely cost-effective ($12/month vs $100 budget)
- ✅ Good reasoning capabilities
- ✅ Fast response times (typically <800ms)
- ✅ Supports JSON mode for structured outputs
- ✅ Large context window (64K tokens)
- ⚠️ Less established than OpenAI/Anthropic
- ⚠️ Chinese model (subject to potential geopolitical risks)

**Qwen3 Max** (Backup):
- ✅ Still cost-effective ($60/month vs $100 budget)
- ✅ Excellent reasoning and instruction following
- ✅ Strong multilingual support (100+ languages)
- ✅ Optimized for RAG and tool calling
- ✅ Available via OpenRouter (easy switching)
- ⚠️ 5x more expensive than DeepSeek
- ⚠️ Also Chinese model (Alibaba)

**Failover Strategy**:
1. **Primary**: DeepSeek Chat V3.1 (direct API)
2. **Backup**: Qwen3 Max (OpenRouter)
3. **Emergency**: Hold all positions, no new trades
4. **Fallback**: GPT-4o-mini ($15-20/month) via OpenRouter if both Chinese models fail

**Token Optimization Strategy**:
- Keep prompts concise (<1,000 tokens target)
- Use structured output format (JSON mode)
- Cache market data formatting templates
- Compress historical data (remove redundant info)
- Use abbreviated indicator names

**Cost Monitoring**:
- Real-time token usage tracking
- Daily cost alerts if >$5/day
- Weekly cost reports
- Automatic model downgrade if approaching budget limit
- Budget enforcement: Pause trading if monthly cost >$100

---

### 5. System Parameters

**Trading Schedule**:
- Operating Hours: 24/7/365
- Decision Interval: Every 3 minutes (480 cycles/day)
- Pause Periods: None (unless circuit breaker triggered)

**Asset Universe**:
- Number of Assets: 6 cryptocurrencies
- Asset Selection (Bybit Perpetual Futures):
  1. BTCUSDT (Bitcoin)
  2. ETHUSDT (Ethereum)
  3. SOLUSDT (Solana)
  4. BNBUSDT (Binance Coin)
  5. ADAUSDT (Cardano)
  6. DOGEUSDT (Dogecoin)
- Rebalancing: Can be adjusted based on liquidity and volatility

**Position Limits**:
- Maximum Concurrent Positions: 6 (one per asset)
- Maximum Position Size: CHF 525.39 (20% of capital)
- Maximum Total Exposure: CHF 2,101.57 (80% of capital)
- Minimum Position Size: Exchange minimums (~$5-20 per asset)

**Performance Targets**:
- Sharpe Ratio: >0.5 (target from PRD)
- Win Rate: >45%
- Maximum Drawdown: <15%
- Daily Loss Limit: -7% (CHF 183.89)
- Monthly Target: 5-10% return (aspirational)

---

### 6. Operational Costs Summary

| Cost Category | Monthly Cost (CHF) | Monthly Cost (USD) | Annual Cost |
|---------------|--------------------|--------------------|-------------|
| **LLM API (Primary)** | CHF 11 | $12 | $144 |
| **LLM API (Backup)** | CHF 0-55 | $0-60 | $0-720 |
| **Infrastructure** | CHF 46-92 | $50-100 | $600-1,200 |
| **Database (PostgreSQL)** | CHF 18-46 | $20-50 | $240-600 |
| **Redis/Cache** | CHF 9-23 | $10-25 | $120-300 |
| **Compute (VPS/Cloud)** | CHF 18-46 | $20-50 | $240-600 |
| **Monitoring** | CHF 0-9 | $0-10 | $0-120 |
| **Trading Fees** | Variable | Variable | Est. $100-300 |
| **TOTAL** | CHF 100-220 | $110-240 | $1,320-2,880 |

**Notes**:
- LLM costs are well under budget ($12 vs $100)
- Infrastructure costs depend on self-hosted vs cloud
- Trading fees depend on volume and strategy performance
- Total operational cost: ~$110-240/month
- Break-even: Need to generate >$240/month profit to cover costs

---

### 7. Configuration Files

These settings should be stored in environment variables or encrypted configuration:

```yaml
# config/trading.yaml (TEMPLATE - actual values in environment)
trading:
  capital:
    initial_capital_chf: 2626.96
    currency: CHF
    display_currency: CHF

  risk:
    daily_loss_limit_pct: -7.0
    max_position_size_pct: 20.0
    max_total_exposure_pct: 80.0
    stop_loss_required: true

  exchange:
    primary: bybit
    testnet: false  # Set to true for paper trading
    api_key: ${BYBIT_API_KEY}
    api_secret: ${BYBIT_API_SECRET}
    fee_maker: 0.055
    fee_taker: 0.075

  assets:
    - BTCUSDT
    - ETHUSDT
    - SOLUSDT
    - BNBUSDT
    - ADAUSDT
    - DOGEUSDT

  schedule:
    decision_interval_seconds: 180  # 3 minutes
    operating_24_7: true

llm:
  primary:
    provider: deepseek
    model: deepseek-chat
    api_key: ${DEEPSEEK_API_KEY}
    max_tokens: 1000
    temperature: 0.7
    timeout_seconds: 10

  backup:
    provider: openrouter
    model: qwen/qwen3-max
    api_key: ${OPENROUTER_API_KEY}
    max_tokens: 1000
    temperature: 0.7
    timeout_seconds: 10

  cost_control:
    monthly_budget_usd: 100
    daily_alert_threshold_usd: 5
    auto_downgrade_at_pct: 90  # Switch to backup if 90% of budget used

monitoring:
  alerts:
    circuit_breaker_triggered: true
    position_closed: true
    llm_failure: true
    api_rate_limit: true
    daily_loss_warning_pct: -5.0  # Warning before circuit breaker at -7%
```

---

### 8. Architecture Impact

These decisions impact the following architectural components:

**Database Schema**:
- All monetary amounts in CHF (DECIMAL(20,8))
- Exchange-specific fields for Bybit
- LLM cost tracking per model
- Token usage logging

**API Integrations**:
- Bybit-specific ccxt configuration
- DeepSeek direct API client
- OpenRouter fallback client
- CHF/USD conversion service (real-time rates)

**Risk Management**:
- Daily loss tracking in CHF (circuit breaker at -CHF 183.89)
- Position sizing calculator (CHF-based)
- Circuit breaker logic (triggers at -7%)
- Stop-loss enforcement
- Warning alerts at -5% (before circuit breaker)

**Cost Monitoring**:
- LLM token usage tracker
- Cost aggregation service
- Budget enforcement system
- Alert system for cost overruns

**Configuration Management**:
- Environment variables for secrets
- Encrypted storage for API keys
- Configuration validation on startup
- Hot-reload for non-critical parameters

---

### 9. Next Steps for Architecture Phase

With these configurations defined, the **Integration Architect** should now design:

1. **Database Schema** reflecting CHF currency and Bybit specifics
2. **API Contracts** for DeepSeek and Qwen3 Max integration
3. **Risk Management Module** with -5% circuit breaker logic
4. **Cost Monitoring Service** for LLM budget tracking
5. **Bybit Integration Layer** with WebSocket and REST APIs
6. **Currency Conversion Service** for CHF/USD handling

---

**Configuration Approved**: ✅ Ready for Phase 2 (Architecture Design)
**Capital Allocation**: CHF 2,626.96
**Risk Profile**: More Aggressive (-7% daily loss limit)
**Exchange**: Bybit (perpetual futures)
**LLM Models**: DeepSeek Chat V3.1 (primary), Qwen3 Max (backup)
**Expected Monthly LLM Cost**: ~$12-15 (primary) or ~$60 (backup)
**Budget Compliance**: ✅ Well under $100/month LLM budget
