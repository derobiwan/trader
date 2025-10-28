# User Stories: LLM-Powered Cryptocurrency Trading System

**Document Version**: 1.0
**Date**: 2025-10-27
**Phase**: P1 - Business Discovery & Requirements
**Status**: Draft for Review
**Business Analyst**: Claude Business Analyst Agent

---

## Table of Contents

1. [User Story Template](#1-user-story-template)
2. [Epic Overview](#2-epic-overview)
3. [Prioritization Framework](#3-prioritization-framework)
4. [User Stories by Epic](#4-user-stories-by-epic)
5. [Story Dependencies](#5-story-dependencies)
6. [Acceptance Testing Guidelines](#6-acceptance-testing-guidelines)

---

## 1. User Story Template

All user stories in this document follow this structure:

```
US-XXX: [Title]
Priority: [Must/Should/Could/Won't]
Epic: [Epic Name]
Story Points: [1, 2, 3, 5, 8, 13]

As a [persona]
I want to [action/capability]
So that [business value/outcome]

Acceptance Criteria:
GIVEN [initial context/state]
WHEN [action is performed]
THEN [expected outcome]
AND [additional verification]

Edge Cases:
- [Edge case scenario 1]
- [Edge case scenario 2]

Dependencies:
- [US-XXX: Related story]

Technical Notes:
- [Implementation considerations]

Business Rules:
- [Rules governing this functionality]
```

---

## 2. Epic Overview

### Epic 1: Market Data Processing & Analysis
**Goal**: Fetch, process, and prepare market data for LLM analysis
**Business Value**: Foundation for all trading decisions
**Stories**: 8 stories (US-001 to US-008)

### Epic 2: LLM Integration & Decision Engine
**Goal**: Integrate LLM providers and generate trading decisions
**Business Value**: Core intelligence of automated trading
**Stories**: 9 stories (US-009 to US-017)

### Epic 3: Trade Execution & Position Management
**Goal**: Execute trades and manage active positions
**Business Value**: Translates decisions into actual market actions
**Stories**: 10 stories (US-018 to US-027)

### Epic 4: Risk Management & Compliance
**Goal**: Enforce risk limits and ensure safe operation
**Business Value**: Protects capital and ensures regulatory compliance
**Stories**: 8 stories (US-028 to US-035)

### Epic 5: Performance Monitoring & Analytics
**Goal**: Track system performance and provide insights
**Business Value**: Enables optimization and demonstrates ROI
**Stories**: 7 stories (US-036 to US-042)

### Epic 6: System Operations & Reliability
**Goal**: Ensure system reliability and operational excellence
**Business Value**: Maximizes uptime and minimizes manual intervention
**Stories**: 8 stories (US-043 to US-050)

### Epic 7: User Interface & Configuration
**Goal**: Provide interface for monitoring and configuration
**Business Value**: Enables operator control and visibility
**Stories**: 6 stories (US-051 to US-056)

---

## 3. Prioritization Framework

### MoSCoW Method

**Must Have** (Critical for MVP, system cannot function without):
- Core trading cycle execution
- LLM integration
- Risk management fundamentals
- Basic position tracking
- Essential monitoring

**Should Have** (Important but workarounds exist):
- Advanced analytics
- Multi-model comparison
- Enhanced error recovery
- Performance optimization

**Could Have** (Nice to have, enhances experience):
- Advanced charting
- Historical analysis
- Strategy backtesting
- Mobile responsive design

**Won't Have** (Explicitly out of scope for MVP):
- Multi-strategy support
- Social trading features
- Custom model training
- Enterprise features

---

## 4. User Stories by Epic

## Epic 1: Market Data Processing & Analysis

### US-001: Real-Time Market Data Fetching via WebSocket
**Priority**: Must Have
**Epic**: Market Data Processing & Analysis
**Story Points**: 5

**User Story**:
As a system operator
I want the system to fetch real-time market data via WebSocket
So that trading decisions are based on the most current price information

**Acceptance Criteria**:
```gherkin
GIVEN the trading system is running
AND exchange WebSocket connection is established
WHEN new price data is received for any of the 6 cryptocurrencies
THEN the system updates the market data cache within 500ms
AND triggers recalculation of technical indicators
AND logs the data timestamp for latency tracking

GIVEN WebSocket connection is active
WHEN connection is interrupted or closed unexpectedly
THEN system attempts reconnection with exponential backoff (1s, 2s, 4s, 8s)
AND falls back to REST API polling at 1-second intervals
AND alerts operator if fallback persists >5 minutes

GIVEN market data is received
WHEN data contains invalid or missing values (null prices, negative volume)
THEN system rejects the data point
AND logs validation error with details
AND uses last known good value with staleness indicator
```

**Edge Cases**:
- WebSocket data arrives out of order (old timestamp after new data)
- Duplicate data packets received
- Extremely high frequency updates (>10/second) causing processing bottleneck
- Exchange sends incorrect symbol data
- WebSocket connection silently stale (no data, but connection appears active)

**Dependencies**:
- None (foundational story)

**Technical Notes**:
- Use `ccxt` library's WebSocket support or native websocket client
- Implement heartbeat/ping-pong to detect stale connections
- Buffer data in Redis for fast access by decision engine
- Consider separate WebSocket connections per exchange for fault isolation

**Business Rules**:
- Maximum data staleness: 10 seconds (alert if exceeded)
- Required data fields: timestamp, open, high, low, close, volume
- Data must include exchange-provided timestamp (not system timestamp)

---

### US-002: Technical Indicator Calculation (EMA, MACD, RSI, Bollinger Bands)
**Priority**: Must Have
**Epic**: Market Data Processing & Analysis
**Story Points**: 5

**User Story**:
As a trading system
I want to calculate technical indicators from OHLCV data
So that the LLM has quantitative analysis inputs for trading decisions

**Acceptance Criteria**:
```gherkin
GIVEN a new price data point is received for a cryptocurrency
WHEN the market data processing service processes the data
THEN it calculates the following indicators within 200ms:
- EMA (Exponential Moving Average): 9, 20, 50 periods
- MACD (Moving Average Convergence Divergence): 12, 26, 9 settings
- RSI (Relative Strength Index): 7, 14 periods
- Bollinger Bands: 20 period, 2 standard deviations
AND stores indicators in structured format (JSON) with timestamp
AND makes indicators available to decision engine via Redis cache

GIVEN insufficient historical data for indicator calculation (cold start)
WHEN attempting to calculate indicators
THEN system uses minimum required periods (e.g., 50 candles for 50-EMA)
AND marks indicators as "warming up" until sufficient data accumulated
AND does NOT generate trading signals during warm-up period

GIVEN indicator calculation encounters invalid input (e.g., division by zero)
WHEN error occurs during calculation
THEN system logs error with context (symbol, indicator, input data)
AND substitutes with last known good value
AND flags indicator as "stale" in output
```

**Edge Cases**:
- Missing candles in historical data (gaps due to exchange downtime)
- Extremely volatile markets causing RSI to hit 0 or 100
- Flat price action causing Bollinger Bands to collapse
- Calculation overflow for extremely high price values
- Time zone mismatches in OHLCV timestamps

**Dependencies**:
- US-001: Real-Time Market Data Fetching

**Technical Notes**:
- Use `ta-lib` or `pandas_ta` library for indicator calculations
- Pre-calculate indicator values during warm-up period (fetch historical data)
- Cache calculations to avoid re-computation of unchanged historical data
- Consider vectorized operations (numpy) for performance

**Business Rules**:
- Indicator parameters are configurable but default to standard values
- Warm-up period: Minimum 50 candles for all indicators
- Indicators recalculated on every new candle close (not on every tick)
- Stale indicators (>5 minutes old) must not be used for decisions

**Testing Approach**:
- Unit tests with known input/output pairs from TradingView or similar platforms
- Verify indicator values match external calculation tools within 0.1% tolerance
- Performance test: Calculate all indicators for 6 symbols in <200ms

---

### US-003: Open Interest and Funding Rate Tracking
**Priority**: Should Have
**Epic**: Market Data Processing & Analysis
**Story Points**: 3

**User Story**:
As a trading analyst
I want the system to track Open Interest and Funding Rate for perpetual futures
So that the LLM can incorporate market sentiment and positioning into decisions

**Acceptance Criteria**:
```gherkin
GIVEN the system is connected to exchange APIs
WHEN fetching market data for perpetual futures
THEN system retrieves Open Interest (total contract value) every 5 minutes
AND retrieves current Funding Rate and next funding timestamp
AND calculates rolling average Open Interest (24-hour window)
AND stores OI and FR data with timestamp in database

GIVEN Open Interest data is unavailable from exchange
WHEN attempting to fetch OI/FR data
THEN system logs warning
AND uses last known value with staleness indicator
AND continues trading decisions without OI/FR data (graceful degradation)

GIVEN abnormal Open Interest change (>20% in 1 hour)
WHEN OI spike is detected
THEN system flags this in decision engine context as "high volatility event"
AND optionally reduces position sizes (configurable)
```

**Edge Cases**:
- Exchange API does not provide OI/FR for specific contract
- Funding rate changes during the decision cycle
- Negative funding rates (shorts pay longs)
- Open Interest data delayed or stale from exchange

**Dependencies**:
- US-001: Real-Time Market Data Fetching

**Technical Notes**:
- Different exchanges have different OI/FR API endpoints (use ccxt abstraction)
- Funding rate is typically paid every 8 hours (check exchange schedule)
- Store OI/FR separately from OHLCV data (different update frequency)

**Business Rules**:
- OI change >20% in 1 hour = high volatility flag
- Funding rate >0.1% (annualized >10%) = extreme market condition
- OI data staleness tolerance: 15 minutes

---

### US-004: Market Data Quality Validation & Gap Detection
**Priority**: Must Have
**Epic**: Market Data Processing & Analysis
**Story Points**: 3

**User Story**:
As a risk manager
I want the system to validate market data quality and detect gaps
So that trading decisions are never based on corrupted or incomplete data

**Acceptance Criteria**:
```gherkin
GIVEN market data is received from exchange
WHEN validating data quality
THEN system checks:
- Timestamp is within acceptable range (not future, not >1 minute old)
- Price values are positive and non-zero
- Volume is non-negative
- High >= Low, High >= Open, High >= Close, Low <= Open, Low <= Close
- Price change from previous candle is <50% (circuit breaker)
AND rejects data failing any validation
AND logs validation failure details

GIVEN system detects missing candles (time gap in data)
WHEN gap is detected (expected candle timestamp missing)
THEN system logs gap with start/end timestamps
AND backfills missing candles from REST API if possible
AND marks indicators as "uncertain" until gap is filled
AND does NOT trade affected symbol until data is continuous again

GIVEN data quality issues persist for >10 minutes
WHEN data remains invalid or gapped
THEN system pauses trading for affected symbol
AND sends alert to operator
AND continues monitoring other symbols
```

**Edge Cases**:
- Flash crash causing legitimate >50% price moves
- Exchange maintenance causing prolonged data gaps
- Daylight saving time transitions causing timestamp confusion
- Simultaneous data quality issues across multiple exchanges

**Dependencies**:
- US-001: Real-Time Market Data Fetching
- US-002: Technical Indicator Calculation

**Technical Notes**:
- Implement data validation as early as possible (ingestion layer)
- Use exchange-provided data checksum if available
- Store data quality metrics for monitoring and alerting
- Consider separate data quality monitoring dashboard

**Business Rules**:
- Maximum acceptable data gap: 3 minutes (skip 1 trading cycle)
- Price change circuit breaker: 50% in single candle
- Data staleness tolerance: 60 seconds for decision-making
- Failed validation = skip trading cycle for that symbol

---

### US-005: Historical Data Backfill for Warm-Up
**Priority**: Must Have
**Epic**: Market Data Processing & Analysis
**Story Points**: 3

**User Story**:
As a system operator
I want the system to automatically fetch historical data on startup
So that indicators can be calculated immediately without waiting 50+ cycles

**Acceptance Criteria**:
```gherkin
GIVEN the trading system is starting up (cold start)
AND no historical data exists in database
WHEN initialization process runs
THEN system fetches last 200 candles (3-minute interval) for each of 6 cryptocurrencies
AND stores candles in database with source timestamp
AND calculates all technical indicators from historical data
AND marks system as "ready for trading" once all symbols warm
AND total warm-up time is <2 minutes

GIVEN historical data fetch fails for one symbol
WHEN backfill error occurs
THEN system retries fetch up to 3 times with 5-second delay
AND logs error details if all retries fail
AND continues with other symbols (partial initialization)
AND marks failed symbol as "not ready" (no trading)

GIVEN historical data is already present in database
WHEN system restarts (warm start)
THEN system checks freshness of historical data (gap since last shutdown)
AND backfills only missing candles since last run
AND warm-up completes in <30 seconds
```

**Edge Cases**:
- Exchange rate limits during bulk historical data fetch
- Historical data has gaps or quality issues
- System crash during warm-up process (incomplete state)
- Different exchanges provide different historical data limits

**Dependencies**:
- US-001: Real-Time Market Data Fetching
- US-002: Technical Indicator Calculation

**Technical Notes**:
- Use exchange REST API `/klines` or equivalent endpoint
- Implement rate limit handling (backoff, parallel fetch limits)
- Store raw OHLCV and calculated indicators separately
- Consider one-time manual backfill for longer history (testing/backtesting)

**Business Rules**:
- Minimum history required: 200 candles (10 hours at 3-minute intervals)
- Historical data must match real-time data format exactly
- System must not trade until warm-up is 100% complete for a symbol
- Historical data retention: Keep last 7 days in database for analysis

---

### US-006: Multi-Timeframe Analysis Preparation
**Priority**: Could Have
**Epic**: Market Data Processing & Analysis
**Story Points**: 5

**User Story**:
As a trading strategist
I want the system to provide multi-timeframe market data to the LLM
So that decisions consider both short-term and longer-term trends

**Acceptance Criteria**:
```gherkin
GIVEN the system has 3-minute candle data (primary timeframe)
WHEN preparing data for LLM analysis
THEN system aggregates candles into additional timeframes:
- 15-minute candles (5 x 3-minute)
- 1-hour candles (20 x 3-minute)
AND calculates indicators for each timeframe separately
AND includes all timeframes in LLM prompt context
AND maintains consistent timestamp alignment across timeframes

GIVEN candle aggregation is in progress
WHEN a 3-minute candle closes that completes a higher timeframe candle
THEN system triggers indicator recalculation for that timeframe
AND updates cached values for decision engine
```

**Edge Cases**:
- Partial higher-timeframe candles (e.g., 2/5 candles for 15-minute)
- Timestamp misalignment causing incorrect aggregation
- Missing 3-minute candles affecting higher timeframe accuracy

**Dependencies**:
- US-002: Technical Indicator Calculation

**Technical Notes**:
- Store aggregated candles separately or calculate on-the-fly
- Consider caching strategy for higher timeframe indicators
- Multi-timeframe analysis increases LLM token usage (monitor costs)

**Business Rules**:
- Primary timeframe (3-minute) always takes precedence
- Higher timeframe indicators used for trend confirmation only
- Incomplete higher timeframe candles marked as "incomplete"

---

### US-007: Market Data Caching Strategy
**Priority**: Should Have
**Epic**: Market Data Processing & Analysis
**Story Points**: 3

**User Story**:
As a performance optimizer
I want market data cached in Redis with appropriate TTL
So that decision engine can access data with <10ms latency

**Acceptance Criteria**:
```gherkin
GIVEN market data is processed successfully
WHEN storing data for decision engine access
THEN system caches in Redis with structure:
- Key: "market_data:{symbol}:latest"
- Value: JSON with OHLCV + indicators + timestamp
- TTL: 5 minutes (auto-expire stale data)
AND cache read latency is <10ms (99th percentile)

GIVEN decision engine requests market data
WHEN cache hit occurs
THEN data is returned immediately from Redis
AND cache hit rate is tracked (target >95%)

GIVEN cache miss occurs
WHEN decision engine requests data
THEN system fetches from database
AND repopulates cache
AND logs cache miss for monitoring
```

**Edge Cases**:
- Redis connection failure (fallback to database)
- Cache stampede (multiple requests for same missing key)
- Memory pressure in Redis (eviction policy)

**Dependencies**:
- US-001: Real-Time Market Data Fetching
- US-002: Technical Indicator Calculation

**Technical Notes**:
- Use Redis pipeline for batch cache updates (performance)
- Implement cache-aside pattern with lazy loading
- Monitor Redis memory usage and eviction rate
- Consider separate Redis instance for market data vs. other caching

**Business Rules**:
- Cache TTL: 5 minutes for market data, 1 minute for indicators
- Cache hit rate target: >95% (indicates healthy caching)
- Cache miss SLA: <50ms to fetch from database and repopulate

---

### US-008: Data Normalization for LLM Prompt
**Priority**: Must Have
**Epic**: Market Data Processing & Analysis
**Story Points**: 3

**User Story**:
As a prompt engineer
I want market data normalized and formatted consistently for LLM consumption
So that the LLM receives clean, structured, and complete context

**Acceptance Criteria**:
```gherkin
GIVEN market data and indicators are ready for a symbol
WHEN preparing LLM prompt context
THEN system formats data as:
- Price series: Last 20 candles (Close prices as array)
- Current candle: OHLCV values
- Indicators: EMA, MACD, RSI, Bollinger Bands (current values)
- Open Interest: Current + 24h average
- Funding Rate: Current value + next funding time
- Timestamp: ISO format with timezone
AND data is formatted as JSON structure matching prompt template
AND all numeric values rounded to appropriate precision (2-8 decimals)
AND null values replaced with "N/A" or sensible defaults

GIVEN data is incomplete (indicators warming up)
WHEN formatting for prompt
THEN system includes "data_quality" field with warnings
AND marks specific indicators as "pending" or "unavailable"
AND LLM is instructed to skip trading if data is incomplete
```

**Edge Cases**:
- Extremely large or small numeric values (scientific notation)
- Unicode characters in symbol names (encoding issues)
- Timezone confusion in timestamps (always use UTC)

**Dependencies**:
- US-002: Technical Indicator Calculation
- US-003: Open Interest and Funding Rate Tracking

**Technical Notes**:
- Use Jinja2 or similar template engine for consistent formatting
- Define schema for prompt data structure (validate before sending to LLM)
- Consider data compression if token limits are approached
- Store prompt data snapshots for decision auditability

**Business Rules**:
- Price precision: 2-8 decimals depending on asset value
- Indicator precision: 2 decimals for percentages, 4 decimals for ratios
- Timestamp format: ISO 8601 with UTC timezone
- Prompt data structure version: Include version number for compatibility

---

## Epic 2: LLM Integration & Decision Engine

### US-009: OpenRouter API Integration
**Priority**: Must Have
**Epic**: LLM Integration & Decision Engine
**Story Points**: 5

**User Story**:
As a system operator
I want the system to integrate with OpenRouter API for LLM access
So that I can use multiple LLM models through a unified interface

**Acceptance Criteria**:
```gherkin
GIVEN OpenRouter API key is configured
WHEN system sends a trading analysis request
THEN request includes:
- Model identifier (e.g., "anthropic/claude-3.5-sonnet")
- Formatted prompt with market data
- System message defining agent role
- Temperature setting (0.3-0.7 range)
- Max tokens limit (1000-2000)
AND receives response within 5 seconds (95th percentile)
AND response is parsed as JSON
AND total request/response logged for audit

GIVEN API request fails (timeout, 5xx error, rate limit)
WHEN error occurs
THEN system retries up to 2 times with 2-second delay
AND logs error details (status code, error message, model)
AND falls back to backup model if primary fails
AND skips trading cycle if all models fail

GIVEN API returns non-JSON response
WHEN response parsing fails
THEN system logs full response for debugging
AND treats as failed request (triggers retry logic)
AND counts as model failure for model performance tracking
```

**Edge Cases**:
- OpenRouter API key expired or invalid
- Model temporarily unavailable or deprecated
- Token limit exceeded for large prompts
- Response truncated mid-JSON (incomplete output)
- Cost tracking mismatch between OpenRouter and system

**Dependencies**:
- US-008: Data Normalization for LLM Prompt

**Technical Notes**:
- Use `httpx` or `aiohttp` for async API calls
- Implement circuit breaker pattern for API failures
- Track token usage per request (prompt + completion)
- Store API responses for debugging and model comparison

**Business Rules**:
- Request timeout: 5 seconds for decision latency SLA
- Retry limit: 2 retries per request (total 3 attempts)
- Cost alert threshold: Trigger warning at $70/month (70% of budget)
- Model availability: At least 2 models must be configured (primary + backup)

---

### US-010: Multi-Model Support & Configuration
**Priority**: Must Have
**Epic**: LLM Integration & Decision Engine
**Story Points**: 3

**User Story**:
As a cost optimizer
I want to configure and switch between different LLM models without code changes
So that I can optimize for cost vs. performance based on market conditions

**Acceptance Criteria**:
```gherkin
GIVEN LLM configuration file exists
WHEN system loads configuration
THEN it supports multiple model definitions:
- Model name/identifier
- Provider (OpenRouter, OpenAI direct, Anthropic direct)
- API endpoint URL
- Cost per 1M tokens (input/output)
- Performance tier (fast/balanced/accurate)
- Enabled/disabled status
AND allows selection of primary model and backup models
AND validates configuration on load (required fields present)

GIVEN operator changes model configuration
WHEN configuration is updated via API or file
THEN system reloads configuration without restart
AND applies new model settings on next trading cycle
AND logs model change event with timestamp

GIVEN primary model is slow or expensive
WHEN performance or cost threshold is exceeded
THEN system automatically switches to backup model (if configured)
AND alerts operator of model change
AND continues to monitor primary model for recovery
```

**Edge Cases**:
- Invalid model identifier in configuration
- Model provider changed but endpoint not updated
- Cost per token data outdated or incorrect
- Simultaneous configuration changes from multiple sources

**Dependencies**:
- US-009: OpenRouter API Integration

**Technical Notes**:
- Store configuration in YAML or JSON file + database
- Implement configuration validation schema (Pydantic)
- Support environment variable overrides for API keys
- Consider A/B testing framework for model comparison

**Business Rules**:
- Minimum 1 model, recommended 3 models (fast, balanced, accurate)
- Model switch cooldown: 5 minutes minimum between automatic switches
- Cost per token must be updated monthly (OpenRouter pricing changes)
- Primary model performance SLA: <3s average response time

---

### US-011: Prompt Template Management
**Priority**: Must Have
**Epic**: LLM Integration & Decision Engine
**Story Points**: 3

**User Story**:
As a prompt engineer
I want to manage and version prompt templates separately from code
So that I can iterate on prompts without code deployments

**Acceptance Criteria**:
```gherkin
GIVEN prompt template file exists (Jinja2 format)
WHEN decision engine prepares LLM request
THEN system loads template from file system
AND renders template with current market data context
AND includes:
- System message (agent role definition)
- Market data for all 6 cryptocurrencies
- Current positions and account status
- Decision framework instructions
- Output format specification (JSON schema)
AND validates rendered prompt size (token estimate)

GIVEN prompt template is updated
WHEN file is modified
THEN system detects change and reloads template on next cycle
AND logs template version change
AND stores old template version for rollback

GIVEN rendered prompt exceeds token limit
WHEN token count is too high
THEN system truncates historical price series (reduce from 20 to 10 candles)
AND logs truncation event
AND still sends request with reduced context
```

**Edge Cases**:
- Template syntax error causing rendering failure
- Missing template variables in context data
- Extremely large prompts (>10,000 tokens) due to many positions
- Template encoding issues (UTF-8)

**Dependencies**:
- US-008: Data Normalization for LLM Prompt

**Technical Notes**:
- Use Jinja2 template engine with strict mode (fail on undefined variables)
- Implement template validation on load (syntax check)
- Store templates in version control (Git)
- Consider separate templates for different models (model-specific optimization)
- Use `tiktoken` library for accurate token counting

**Business Rules**:
- Prompt template versioning: Use semantic versioning (e.g., v1.2.0)
- Maximum prompt size: 8,000 tokens (input limit for most models)
- Template changes require testing in paper trading mode before live use
- System message must remain consistent across template versions

---

### US-012: JSON Response Parsing & Validation
**Priority**: Must Have
**Epic**: LLM Integration & Decision Engine
**Story Points**: 5

**User Story**:
As a trade executor
I want LLM responses parsed and validated against a strict schema
So that only well-formed trading signals are executed

**Acceptance Criteria**:
```gherkin
GIVEN LLM returns a response
WHEN parsing the response
THEN system extracts JSON from response text (handles markdown code blocks)
AND validates against schema:
{
  "decisions": [
    {
      "coin": "BTCUSDT",
      "action": "buy_to_enter|sell_to_enter|hold|close_position",
      "confidence": 0.0-1.0,
      "reasoning": "string (50-500 chars)",
      "risk_usd": 0-5000,
      "leverage": 5-40,
      "stop_loss_pct": 0.01-0.10,
      "take_profit_pct": 0.01-0.30 (optional),
      "invalidation_conditions": ["string"] (optional)
    }
  ]
}
AND rejects response if:
- JSON is malformed or incomplete
- Required fields missing
- Value types incorrect (string instead of number)
- Values out of acceptable ranges
- Unknown action types
- Symbol not in configured list

GIVEN response validation fails
WHEN schema validation errors occur
THEN system logs full response + validation errors
AND treats as failed request (retry logic)
AND does NOT execute any trades from that response

GIVEN response contains mixed signals (some valid, some invalid)
WHEN partial validation occurs
THEN system extracts valid decisions only
AND logs invalid decisions for review
AND executes valid decisions
AND alerts operator of partial response
```

**Edge Cases**:
- LLM returns narrative text instead of JSON
- JSON embedded in markdown code fence (```json ... ```)
- Multiple JSON objects in response (pick first valid one)
- LLM returns empty decisions array (no trades)
- LLM invents new fields not in schema (ignore extra fields)
- Unicode characters in reasoning text

**Dependencies**:
- US-009: OpenRouter API Integration

**Technical Notes**:
- Use `pydantic` for schema validation and type coercion
- Implement lenient JSON extraction (regex to find JSON in text)
- Log schema validation errors with specific field and error type
- Store raw responses for debugging and model tuning

**Business Rules**:
- Zero tolerance for invalid actions (reject entire decision if action invalid)
- Confidence range: 0.0-1.0 (scale to percentage)
- Risk per trade: Maximum $5000 or 10% of account (whichever is lower)
- Leverage limits: 5-40x (reject if outside range)
- Stop-loss minimum: 1% (prevent too-tight stops)

---

### US-013: Automatic Model Failover
**Priority**: Should Have
**Epic**: LLM Integration & Decision Engine
**Story Points**: 3

**User Story**:
As a reliability engineer
I want the system to automatically failover to backup LLM models on primary failure
So that trading continues even when one model/provider is unavailable

**Acceptance Criteria**:
```gherkin
GIVEN primary LLM model is configured
AND backup models are configured (ranked priority)
WHEN primary model request fails 2 consecutive times
THEN system automatically switches to backup model #1
AND logs failover event with reason (timeout/error/rate limit)
AND continues trading cycle with backup model

GIVEN backup model is in use
WHEN primary model becomes available again (health check succeeds)
THEN system automatically fails back to primary model
AND logs recovery event
AND cooldown period of 10 minutes before failback

GIVEN all configured models fail
WHEN no models are available
THEN system enters "degraded mode"
AND skips trading cycles until model availability restored
AND sends critical alert to operator
AND continues monitoring and market data collection
```

**Edge Cases**:
- Flapping: Rapid switching between models
- Model-specific response format differences
- Cost differences between models (failover to expensive model)
- Backup model slower than primary (latency SLA breach)

**Dependencies**:
- US-009: OpenRouter API Integration
- US-010: Multi-Model Support & Configuration

**Technical Notes**:
- Implement model health check (lightweight test request)
- Track model availability metrics (uptime, latency, error rate)
- Circuit breaker pattern: Open (failed) → Half-Open (testing) → Closed (healthy)
- Consider model-specific prompt adjustments

**Business Rules**:
- Failover trigger: 2 consecutive failures OR 5 failures in 10 minutes
- Failback cooldown: 10 minutes (prevent flapping)
- Health check frequency: Every 60 seconds when in failover state
- Maximum failover depth: 2 levels (primary → backup #1 → backup #2)

---

### US-014: Token Usage Tracking & Cost Monitoring
**Priority**: Must Have
**Epic**: LLM Integration & Decision Engine
**Story Points**: 3

**User Story**:
As a cost controller
I want accurate tracking of LLM token usage and costs
So that I can ensure operating costs stay within budget

**Acceptance Criteria**:
```gherkin
GIVEN each LLM request is made
WHEN response is received
THEN system extracts token usage from API response:
- Prompt tokens (input)
- Completion tokens (output)
- Total tokens
AND calculates cost using model pricing ($/1M tokens)
AND stores usage data: timestamp, model, tokens, cost, symbol
AND updates running totals: hourly, daily, monthly

GIVEN daily cost exceeds warning threshold ($3.30 = 70% of daily budget)
WHEN cost calculation is updated
THEN system sends warning alert to operator
AND logs cost alert event

GIVEN monthly cost exceeds hard limit ($100)
WHEN cost limit is reached
THEN system enters "cost protection mode"
AND switches to cheapest available model
AND optionally reduces trading frequency (configurable)
AND requires operator approval to resume normal operations

GIVEN cost data is requested
WHEN operator queries cost dashboard
THEN system provides:
- Current month total cost
- Cost breakdown by model
- Cost per trading decision (average)
- Projected monthly cost (based on current usage)
- Token usage efficiency (tokens per decision)
```

**Edge Cases**:
- API does not return token usage (estimate using tiktoken)
- Model pricing changes mid-month
- Free tier or credits affecting actual cost
- Multiple API keys with different billing

**Dependencies**:
- US-009: OpenRouter API Integration

**Technical Notes**:
- Store cost data in time-series database or dedicated table
- Use OpenRouter's usage API for billing reconciliation
- Implement cost projection algorithm (linear + moving average)
- Alert via multiple channels (email, dashboard, logs)

**Business Rules**:
- Daily budget: $3.30/day ($100/month average)
- Warning threshold: 70% of daily budget ($2.31/day)
- Hard limit: $100/month (trading pause)
- Cost tracking granularity: Per request (for detailed analysis)
- Billing reconciliation: Weekly check against provider billing dashboard

---

### US-015: Decision Confidence Thresholding
**Priority**: Should Have
**Epic**: LLM Integration & Decision Engine
**Story Points**: 2

**User Story**:
As a risk manager
I want to filter LLM decisions based on confidence level
So that only high-confidence signals are executed

**Acceptance Criteria**:
```gherkin
GIVEN LLM returns a trading decision with confidence score
WHEN decision engine evaluates the signal
THEN system checks if confidence meets minimum threshold:
- Buy/Sell entry: Confidence >= 0.60 (configurable)
- Close position: Confidence >= 0.50 (lower threshold OK for exits)
- Hold: Any confidence (always acceptable)
AND rejects signals below threshold
AND logs rejected signal with reason "low confidence"

GIVEN market conditions are volatile (high VIX equivalent)
WHEN confidence thresholding is applied
THEN system dynamically increases threshold by 0.10
AND logs threshold adjustment
AND requires higher confidence for entries during volatility

GIVEN operator wants to adjust confidence threshold
WHEN configuration is updated
THEN new threshold applies to next trading cycle
AND historical threshold changes are logged
```

**Edge Cases**:
- LLM returns confidence exactly at threshold (0.60 = accept)
- Confidence value missing or null (reject decision)
- Confidence >1.0 or <0.0 (validation error, reject)

**Dependencies**:
- US-012: JSON Response Parsing & Validation

**Technical Notes**:
- Store confidence threshold in configuration (per action type)
- Track distribution of confidence scores by model (analytics)
- Consider separate thresholds per symbol or market condition

**Business Rules**:
- Default entry threshold: 0.60 (60% confidence)
- Default exit threshold: 0.50 (50% confidence)
- Threshold adjustment range: 0.40-0.90 (prevent too loose or too tight)
- Dynamic adjustment: +0.10 in volatile markets, -0.05 in calm markets

---

### US-016: LLM Response Caching for Testing
**Priority**: Could Have
**Epic**: LLM Integration & Decision Engine
**Story Points**: 2

**User Story**:
As a developer
I want to cache LLM responses during testing
So that I can iterate quickly without incurring API costs

**Acceptance Criteria**:
```gherkin
GIVEN testing mode is enabled
AND prompt hash matches cached response
WHEN LLM request is about to be sent
THEN system checks cache for matching prompt (SHA256 hash)
AND returns cached response if available
AND skips API call entirely
AND logs cache hit

GIVEN no cache hit occurs
WHEN LLM request is sent in testing mode
THEN response is cached with prompt hash as key
AND TTL set to 24 hours (testing session)
AND cache stored in Redis or file system

GIVEN production mode is enabled
WHEN any LLM request is made
THEN caching is bypassed entirely (always fresh decisions)
```

**Edge Cases**:
- Cache storage limit exceeded
- Prompt contains timestamp or random data (never matches)

**Dependencies**:
- US-009: OpenRouter API Integration

**Technical Notes**:
- Use content-based hashing (exclude timestamp from prompt for caching)
- Store cache in separate Redis database or file directory
- Implement cache clear command for test cleanup

**Business Rules**:
- Caching only in non-production environments
- Cache TTL: 24 hours maximum
- Cache key: SHA256 hash of prompt (normalized, timestamps removed)

---

### US-017: Model Performance Comparison Dashboard
**Priority**: Could Have
**Epic**: LLM Integration & Decision Engine
**Story Points**: 5

**User Story**:
As a performance analyst
I want to compare the performance of different LLM models
So that I can select the best model for my trading strategy

**Acceptance Criteria**:
```gherkin
GIVEN multiple models have been used for trading decisions
WHEN operator views model comparison dashboard
THEN system displays for each model:
- Total decisions made
- Average confidence per decision
- Win rate (profitable trades / total trades)
- Average profit per trade
- Average response time
- Total cost (API usage)
- Cost per decision
AND allows filtering by date range and symbol

GIVEN A/B testing mode is enabled
WHEN trading cycle executes
THEN system randomly selects model for decision (50/50 split or configured ratio)
AND tracks decisions separately by model
AND does NOT execute both models' decisions (only one per cycle)
```

**Edge Cases**:
- Insufficient data for statistical significance
- Models used in different market conditions (unfair comparison)

**Dependencies**:
- US-010: Multi-Model Support & Configuration
- US-014: Token Usage Tracking & Cost Monitoring

**Technical Notes**:
- Store model attribution for each trade in database
- Calculate statistical significance (p-value) for performance differences
- Consider market condition normalization for fair comparison

**Business Rules**:
- Minimum sample size for comparison: 50 decisions per model
- Statistical significance threshold: p < 0.05
- A/B testing duration: Minimum 7 days for meaningful results

---

## Epic 3: Trade Execution & Position Management

### US-018: Market Order Execution
**Priority**: Must Have
**Epic**: Trade Execution & Position Management
**Story Points**: 5

**User Story**:
As a trade executor
I want to execute market orders based on LLM signals
So that positions are entered and exited immediately at current market price

**Acceptance Criteria**:
```gherkin
GIVEN a validated trading signal (buy_to_enter or sell_to_enter)
WHEN execution service processes the signal
THEN system places market order on exchange:
- Symbol: Extracted from signal
- Side: Buy (long) or Sell (short)
- Quantity: Calculated from risk_usd and entry price
- Order type: MARKET
- Leverage: Set according to signal parameter
AND receives order confirmation within 2 seconds
AND stores order details: order_id, symbol, side, quantity, price, timestamp
AND logs execution event with full signal context

GIVEN order is placed successfully
WHEN order fill confirmation is received
THEN system updates position tracking:
- Creates new position record
- Stores entry price (actual fill price)
- Calculates position size in base currency
- Sets leverage on position
- Marks position as ACTIVE
AND proceeds to place stop-loss order (US-020)

GIVEN order fails (insufficient margin, exchange error)
WHEN execution error occurs
THEN system logs error with details (error code, message)
AND does NOT create position record
AND does NOT retry execution (safety measure)
AND alerts operator of failed execution
```

**Edge Cases**:
- Partial fills (order only partially executed)
- Slippage exceeds acceptable threshold (>2%)
- Order rejected due to position limits
- Exchange API returns success but order doesn't appear (reconciliation needed)
- Price moves significantly during order execution (latency impact)

**Dependencies**:
- US-012: JSON Response Parsing & Validation

**Technical Notes**:
- Use `ccxt` library's `create_order()` with order type `market`
- Implement order timeout (cancel if not filled in 5 seconds)
- Calculate quantity with rounding to exchange lot size requirements
- Store both requested and actual fill price for slippage analysis

**Business Rules**:
- Order execution timeout: 5 seconds maximum
- Acceptable slippage: 2% from expected price (reject if exceeded)
- Minimum position size: Exchange-specific (e.g., $10 equivalent)
- Maximum single order size: $5000 or 10% of account (risk limit)
- Leverage setting: Must be within exchange limits (usually 1-125x, our limit 5-40x)

---

### US-019: Position Size Calculation
**Priority**: Must Have
**Epic**: Trade Execution & Position Management
**Story Points**: 3

**User Story**:
As a risk manager
I want position sizes calculated based on risk parameters
So that each trade risks an appropriate amount of capital

**Acceptance Criteria**:
```gherkin
GIVEN a trading signal with risk_usd and leverage parameters
AND current account balance and available margin
WHEN calculating position size
THEN system calculates:
- Position value = risk_usd × leverage
- Required margin = position value / leverage
- Quantity = position value / entry_price
AND validates:
- Required margin <= available margin (can afford position)
- Position size >= exchange minimum lot size
- Position size <= exchange maximum lot size
- Total exposure (all positions) <= 80% of account value
AND rounds quantity to exchange tick size precision

GIVEN calculated position size violates constraints
WHEN validation fails
THEN system adjusts position size downward to fit constraints
AND logs adjustment reason
AND uses adjusted size for order execution

GIVEN account margin is insufficient for calculated position
WHEN margin check fails
THEN system rejects signal entirely (does not execute)
AND logs rejection reason "insufficient margin"
AND alerts operator
```

**Edge Cases**:
- Extremely high leverage requiring tiny margin (rounding errors)
- Price precision issues (8+ decimal places for some altcoins)
- Available margin reported incorrectly by exchange (stale data)
- Simultaneous orders exhausting margin (race condition)

**Dependencies**:
- US-018: Market Order Execution

**Technical Notes**:
- Fetch account balance and margin before each position calculation
- Use exchange API's precision info (lot size, tick size) for rounding
- Implement margin buffer (use only 90% of available margin)
- Consider cross-margin vs. isolated margin mode

**Business Rules**:
- Maximum risk per trade: $5000 or 10% of account balance (whichever is lower)
- Leverage range: 5-40x (signal must be within this range)
- Margin utilization limit: 80% of total account value
- Minimum position value: $50 (below this, skip trade)
- Quantity rounding: Always round DOWN to avoid insufficient margin errors

---

### US-020: Stop-Loss Order Placement & Management
**Priority**: Must Have
**Epic**: Trade Execution & Position Management
**Story Points**: 5

**User Story**:
As a risk manager
I want stop-loss orders placed immediately upon position entry
So that downside risk is limited on every trade

**Acceptance Criteria**:
```gherkin
GIVEN a position is entered successfully (order filled)
WHEN position is recorded in system
THEN system immediately places stop-loss order:
- Side: Opposite of position (Sell for long, Buy for short)
- Quantity: Equal to position size
- Order type: STOP_MARKET or STOP_LIMIT (exchange-dependent)
- Stop price: entry_price × (1 - stop_loss_pct) for long, entry_price × (1 + stop_loss_pct) for short
- Time in force: GTC (Good Till Canceled)
AND stores stop-loss order ID with position record
AND confirms order placement within 3 seconds
AND logs stop-loss placement event

GIVEN stop-loss order is triggered (price hits stop price)
WHEN exchange notifies of order fill or system detects position closed
THEN system updates position status to CLOSED_STOP_LOSS
AND records exit price, exit timestamp, P&L
AND removes position from active tracking
AND logs stop-loss trigger event with market conditions

GIVEN stop-loss order placement fails
WHEN order error occurs (insufficient margin, invalid price, exchange error)
THEN system immediately closes position at market price (safety)
AND logs critical error "stop-loss placement failed - emergency close"
AND sends urgent alert to operator
```

**Edge Cases**:
- Stop-loss triggered within seconds of entry (whipsaw)
- Exchange does not support stop-loss orders (use manual monitoring)
- Stop-loss price outside exchange price limits (too close/too far)
- Multiple stop-loss orders exist for same position (duplicate issue)
- Stop-loss order rejected after position entry (orphaned position)

**Dependencies**:
- US-018: Market Order Execution
- US-019: Position Size Calculation

**Technical Notes**:
- Different exchanges have different stop order types (STOP_MARKET, STOP_LOSS, STOP_LIMIT)
- Some exchanges require separate stop-loss order, others support native stop-loss on position
- Implement stop-loss order verification (fetch order status after placement)
- Monitor for stop-loss order cancellation (exchange maintenance, user error)

**Business Rules**:
- Stop-loss placement timeout: 5 seconds after position entry
- Stop-loss placement failure = immediate position close (zero tolerance)
- Stop-loss distance minimum: 1% from entry (prevent immediate trigger)
- Stop-loss distance maximum: 10% from entry (prevent excessive risk)
- Stop-loss monitoring frequency: Every 30 seconds (verify order still active)
- **Critical Rule**: NO POSITION WITHOUT STOP-LOSS (enforce at code level)

---

### US-021: Position Tracking & State Management
**Priority**: Must Have
**Epic**: Trade Execution & Position Management
**Story Points**: 5

**User Story**:
As a system operator
I want all open positions tracked with complete state information
So that I always know my current market exposure

**Acceptance Criteria**:
```gherkin
GIVEN a position is opened or closed
WHEN position state changes
THEN system maintains position record with:
- Position ID (unique)
- Symbol (e.g., BTCUSDT)
- Side (LONG or SHORT)
- Quantity (in base currency)
- Entry price (average if multiple fills)
- Current price (updated every cycle)
- Leverage
- Unrealized P&L (current - entry × quantity)
- Entry timestamp
- Stop-loss price and order ID
- Take-profit price and order ID (if applicable)
- Status (ACTIVE, CLOSED_MANUAL, CLOSED_STOP_LOSS, CLOSED_TAKE_PROFIT, CLOSED_INVALIDATED)
- Invalidation conditions (from LLM signal)
- Associated trading signal ID (for audit trail)
AND position is stored in database (persistent)
AND position is cached in Redis (fast access)

GIVEN positions exist in system
WHEN trading cycle executes
THEN system updates all positions:
- Fetches current price from market data
- Recalculates unrealized P&L
- Checks invalidation conditions (US-023)
- Updates position record with latest data
- Logs P&L changes if significant (>5% change)

GIVEN operator requests position summary
WHEN dashboard queries position data
THEN system provides:
- List of all active positions with current state
- Total portfolio value (cash + unrealized P&L)
- Total exposure (sum of position values)
- Margin utilization (used / total)
- Largest position and risk concentration
```

**Edge Cases**:
- Position exists in exchange but not in system database (manual trade)
- Position exists in system but closed on exchange (reconciliation needed)
- Unrealized P&L calculation error due to stale price
- Multiple positions for same symbol (averaging logic)

**Dependencies**:
- US-018: Market Order Execution
- US-020: Stop-Loss Order Placement & Management

**Technical Notes**:
- Use database transactions for position updates (atomic operations)
- Implement position reconciliation with exchange (detect discrepancies)
- Store position history (audit trail of all state changes)
- Index positions by symbol, status, timestamp for fast queries

**Business Rules**:
- Position status transitions: ACTIVE → CLOSED_* (no reopening closed positions)
- Maximum concurrent positions: 6 (one per cryptocurrency)
- Position update frequency: Every 3 minutes (trading cycle)
- Position reconciliation frequency: Every 30 minutes (sync with exchange)
- Stale position data tolerance: 5 minutes (alert if not updated)

---

### US-022: Take-Profit Order Management (Optional)
**Priority**: Could Have
**Epic**: Trade Execution & Position Management
**Story Points**: 3

**User Story**:
As a trader
I want take-profit orders placed for positions when specified
So that profitable exits are automated

**Acceptance Criteria**:
```gherkin
GIVEN a trading signal includes take_profit_pct parameter
AND position is entered successfully
WHEN position is recorded in system
THEN system places take-profit order:
- Side: Opposite of position (Sell for long, Buy for short)
- Quantity: Equal to position size (or partial if specified)
- Order type: LIMIT
- Limit price: entry_price × (1 + take_profit_pct) for long, entry_price × (1 - take_profit_pct) for short
- Time in force: GTC (Good Till Canceled)
AND stores take-profit order ID with position record
AND logs take-profit placement event

GIVEN take-profit order is filled
WHEN exchange notifies of order fill
THEN system updates position status to CLOSED_TAKE_PROFIT
AND records exit price, exit timestamp, P&L
AND cancels associated stop-loss order
AND logs take-profit trigger event

GIVEN take-profit is not specified in signal
WHEN position is entered
THEN system skips take-profit order placement
AND relies on manual close or invalidation condition close
```

**Edge Cases**:
- Take-profit and stop-loss orders conflict (OCO not supported by exchange)
- Take-profit triggered but stop-loss cancellation fails (orphaned stop order)
- Take-profit price outside exchange limits

**Dependencies**:
- US-020: Stop-Loss Order Placement & Management

**Technical Notes**:
- Implement OCO (One-Cancels-Other) if exchange supports it
- If OCO not supported, monitor for fills and manually cancel opposite order
- Consider partial take-profit (close 50% at target, let rest run)

**Business Rules**:
- Take-profit is optional (not all signals will include it)
- Take-profit distance minimum: 2% from entry (must justify fees)
- Take-profit distance maximum: 30% from entry (realistic target)
- Take-profit execution: Limit order (not market) to ensure target price

---

### US-023: Position Invalidation Condition Monitoring
**Priority**: Should Have
**Epic**: Trade Execution & Position Management
**Story Points**: 5

**User Story**:
As a trading strategist
I want positions closed automatically when invalidation conditions are met
So that thesis-violated positions are exited even before stop-loss

**Acceptance Criteria**:
```gherkin
GIVEN a position has invalidation conditions specified (from LLM signal)
Examples:
- "Close if RSI7 drops below 30"
- "Close if price drops below EMA20"
- "Close if funding rate turns negative"
WHEN system evaluates position during trading cycle
THEN system parses invalidation conditions
AND checks current market data against each condition
AND if ANY condition is TRUE:
  - Closes position immediately at market price
  - Updates position status to CLOSED_INVALIDATED
  - Cancels stop-loss and take-profit orders
  - Logs invalidation event with condition met
  - Records exit price and P&L

GIVEN invalidation condition syntax is invalid
WHEN parsing invalidation conditions
THEN system logs parsing error
AND ignores invalid conditions (does not fail position)
AND alerts operator of unparseable condition

GIVEN multiple invalidation conditions exist
WHEN evaluating conditions
THEN system treats conditions as OR logic (any true = close)
AND logs which specific condition triggered the close
```

**Edge Cases**:
- Invalidation condition references data not available (missing indicator)
- Condition is ambiguous or contradictory
- Condition triggers immediately after entry (not enough time)
- LLM provides condition in unexpected format (free text vs. structured)

**Dependencies**:
- US-021: Position Tracking & State Management
- US-002: Technical Indicator Calculation

**Technical Notes**:
- Implement simple DSL (Domain Specific Language) parser for conditions
- Support operators: <, >, <=, >=, ==
- Support references: RSI7, RSI14, EMA20, EMA50, MACD, price, funding_rate
- Store condition evaluation results for debugging
- Consider using `pyparsing` or `lark` library for parsing

**Business Rules**:
- Invalidation conditions are optional (not required on every position)
- Maximum 3 invalidation conditions per position (keep it simple)
- Condition evaluation frequency: Every trading cycle (3 minutes)
- Condition close = market order (immediate exit, no delay)
- Invalidation condition close does NOT count as stop-loss violation

---

### US-024: Manual Position Close Override
**Priority**: Should Have
**Epic**: Trade Execution & Position Management
**Story Points**: 2

**User Story**:
As a system operator
I want the ability to manually close positions via UI/API
So that I can intervene in emergencies or take manual exits

**Acceptance Criteria**:
```gherkin
GIVEN an active position exists
WHEN operator initiates manual close via dashboard or API
THEN system:
- Places market order to close position (opposite side)
- Cancels stop-loss and take-profit orders
- Updates position status to CLOSED_MANUAL
- Records exit price, timestamp, P&L
- Logs manual close event with operator user ID
AND close executes within 3 seconds
AND confirmation message displayed to operator

GIVEN multiple positions exist
WHEN operator initiates "close all positions" command
THEN system closes all active positions in parallel
AND logs bulk close event
AND provides summary of closed positions

GIVEN manual close fails (exchange error)
WHEN close order is rejected
THEN system retries close up to 3 times
AND logs error details
AND alerts operator of failure
AND keeps position marked as ACTIVE (manual retry required)
```

**Edge Cases**:
- Operator closes position that was already closing (race condition)
- Manual close conflicts with automatic close (invalidation/stop-loss)
- Operator closes position in multiple assets simultaneously (concurrent requests)

**Dependencies**:
- US-021: Position Tracking & State Management

**Technical Notes**:
- Implement API endpoint POST /api/positions/{id}/close
- Require authentication and authorization (operator role)
- Log operator identity for audit purposes
- Implement confirmation prompt in UI (prevent accidental closes)

**Business Rules**:
- Manual close = market order (immediate exit)
- Manual close cancels ALL associated orders (stop-loss, take-profit)
- Manual close requires operator authentication
- Manual close event logged with reason (optional text field)
- Bulk close has maximum limit: 10 positions at once (prevent accidental mass exit)

---

### US-025: Position Reconciliation with Exchange
**Priority**: Must Have
**Epic**: Trade Execution & Position Management
**Story Points**: 5

**User Story**:
As a reliability engineer
I want the system to reconcile positions with the exchange periodically
So that discrepancies are detected and resolved automatically

**Acceptance Criteria**:
```gherkin
GIVEN system is running normally
WHEN reconciliation cycle executes (every 30 minutes)
THEN system:
- Fetches all open positions from exchange API
- Compares exchange positions with system database positions
- Identifies discrepancies:
  * Positions in exchange but not in system (orphaned)
  * Positions in system but not in exchange (ghost)
  * Quantity mismatches
  * Entry price mismatches
AND logs all discrepancies with details

GIVEN discrepancy is detected (orphaned position)
WHEN position exists on exchange but not in system
THEN system:
- Creates position record in database with "RECONCILED" flag
- Fetches position details from exchange (entry price, size, timestamp)
- Places stop-loss order if missing (safety measure)
- Alerts operator of orphaned position
- Includes in position tracking going forward

GIVEN discrepancy is detected (ghost position)
WHEN position exists in system but not on exchange
THEN system:
- Marks position as CLOSED_RECONCILED
- Records exit timestamp as unknown
- Logs ghost position event
- Alerts operator of ghost position (possible data loss)

GIVEN quantity or price mismatch detected
WHEN values differ between system and exchange
THEN system:
- Updates system record to match exchange (exchange is source of truth)
- Logs mismatch with old and new values
- Recalculates P&L based on correct values
```

**Edge Cases**:
- Exchange API returns stale data during reconciliation
- Reconciliation runs during active trading (position just opened/closed)
- Exchange and system use different position IDs (no direct mapping)
- Partial fills not reflected in system (order in-flight)

**Dependencies**:
- US-021: Position Tracking & State Management

**Technical Notes**:
- Implement idempotent reconciliation (safe to run multiple times)
- Use position fingerprinting (symbol + side + entry_time) for matching
- Store reconciliation results in separate audit table
- Consider real-time reconciliation on critical events (not just periodic)

**Business Rules**:
- Reconciliation frequency: Every 30 minutes
- Exchange is always source of truth (system syncs to exchange)
- Discrepancy tolerance: ±1% for quantity mismatches (rounding errors OK)
- Operator alert threshold: Any discrepancy >5% or >$100 value
- Ghost position handling: Mark closed, do NOT attempt to re-create on exchange

---

### US-026: Partial Fill Handling
**Priority**: Should Have
**Epic**: Trade Execution & Position Management
**Story Points**: 3

**User Story**:
As a trade executor
I want partial fills handled gracefully
So that positions are tracked correctly even when orders don't fully execute

**Acceptance Criteria**:
```gherkin
GIVEN a market order is placed
WHEN order is only partially filled (e.g., 80% of requested quantity)
THEN system:
- Creates position record with actual filled quantity (not requested)
- Adjusts stop-loss quantity to match filled quantity
- Logs partial fill event with filled/requested ratio
- Decides on remainder:
  Option A: Cancel remainder (accept partial position)
  Option B: Keep order active (wait for full fill)
AND decision is configurable via system settings

GIVEN partial fill creates undersized position
WHEN filled quantity is <50% of requested
THEN system evaluates if position meets minimum size
AND if below minimum:
  - Closes partial position immediately
  - Logs undersized position rejection
  - Does not place stop-loss (position too small)

GIVEN order is filled in multiple chunks (sequential partial fills)
WHEN multiple fill notifications are received
THEN system:
- Aggregates fills into single position
- Calculates average entry price across fills
- Updates position record with total quantity and avg price
- Places stop-loss only after last fill confirmed
```

**Edge Cases**:
- Order partially filled, then cancelled by exchange (unexpected)
- Second fill arrives minutes after first (delayed notification)
- Fills arrive out of order (older fill notification after newer one)
- Position closed before all fills completed (premature stop-loss trigger)

**Dependencies**:
- US-018: Market Order Execution
- US-019: Position Size Calculation

**Technical Notes**:
- Monitor order status with polling (don't rely solely on WebSocket notifications)
- Implement fill aggregation logic with deduplication (prevent double-counting)
- Store individual fills in database for audit trail
- Consider increasing order size to account for expected partial fill rate

**Business Rules**:
- Partial fill handling mode: Accept partial (default) or Wait for full fill (configurable)
- Minimum acceptable fill ratio: 50% (below this, reject position)
- Fill aggregation timeout: 30 seconds (if no more fills, finalize position)
- Average entry price calculation: Volume-weighted average of all fills

---

### US-027: Position P&L Calculation & Tracking
**Priority**: Must Have
**Epic**: Trade Execution & Position Management
**Story Points**: 3

**User Story**:
As a performance analyst
I want accurate P&L calculated for all positions
So that I can track profitability and system performance

**Acceptance Criteria**:
```gherkin
GIVEN a position is active
WHEN current market price is available
THEN system calculates unrealized P&L:
- For LONG: (current_price - entry_price) × quantity
- For SHORT: (entry_price - current_price) × quantity
- Leverage multiplies P&L (inherent in quantity calculation)
AND updates position record with unrealized P&L
AND updates portfolio total unrealized P&L

GIVEN a position is closed
WHEN exit price is confirmed
THEN system calculates realized P&L:
- Realized P&L = unrealized P&L at close
- Subtract exchange fees (entry fee + exit fee)
- Calculate ROI = realized P&L / margin_used
AND stores in position record (immutable)
AND updates account balance
AND includes in performance metrics

GIVEN multiple positions exist
WHEN calculating portfolio P&L
THEN system aggregates:
- Total unrealized P&L (sum of all active positions)
- Total realized P&L (sum of all closed positions today/week/month)
- Total portfolio value = account_balance + unrealized_P&L
- Portfolio ROI = total realized P&L / initial capital
```

**Edge Cases**:
- Price data unavailable (calculate using last known price)
- Unrealized P&L swings wildly due to volatility (display with update frequency limit)
- Fee calculation when fee structure changes
- Position held across funding rate payments (fee impact)

**Dependencies**:
- US-021: Position Tracking & State Management

**Technical Notes**:
- Recalculate unrealized P&L every trading cycle (3 minutes)
- Store P&L snapshots for historical analysis (time series)
- Include exchange fees in realized P&L (fetch from exchange API or estimate)
- Consider funding rate payments as part of P&L (perpetual futures specific)

**Business Rules**:
- P&L calculation precision: 2 decimal places for display, full precision in database
- Exchange fee assumption: 0.04% per trade (2x for round trip) if actual fees not available
- Unrealized P&L display: Update every cycle, not every price tick (avoid UI flicker)
- Realized P&L finality: Once position closed, P&L is immutable

---

## Epic 4: Risk Management & Compliance

### US-028: Daily Loss Limit Circuit Breaker
**Priority**: Must Have
**Epic**: Risk Management & Compliance
**Story Points**: 3

**User Story**:
As a risk manager
I want trading paused automatically if daily loss exceeds threshold
So that catastrophic losses are prevented

**Acceptance Criteria**:
```gherkin
GIVEN system is tracking daily P&L
WHEN realized losses for current day exceed configured limit (e.g., -5% of account)
THEN system:
- Immediately closes all open positions
- Enters "CIRCUIT_BREAKER_TRIPPED" state
- Pauses all new trading signals (no new positions)
- Sends urgent alert to operator
- Logs circuit breaker event with current P&L

GIVEN circuit breaker is tripped
WHEN operator reviews situation
THEN operator can:
- Acknowledge circuit breaker (required before reset)
- Review closed positions and losses
- Reset circuit breaker manually (requires confirmation)
AND system resumes trading only after manual reset

GIVEN new trading day begins (00:00 UTC)
WHEN daily reset occurs
THEN system resets daily loss counter to $0
AND circuit breaker automatically re-enables
AND logs daily reset event
```

**Edge Cases**:
- Multiple positions closed simultaneously causing cascade losses
- Unrealized losses large but not yet realized (should we preempt?)
- Circuit breaker trips just before market reversal (opportunity cost)
- Operator unavailable to reset (system paused indefinitely)

**Dependencies**:
- US-027: Position P&L Calculation & Tracking

**Technical Notes**:
- Implement circuit breaker as state machine (ACTIVE → TRIPPED → ACKNOWLEDGED → RESET)
- Use UTC timezone for daily reset consistency
- Store circuit breaker events in dedicated audit table
- Consider graduated circuit breakers (warning at -3%, trip at -5%)

**Business Rules**:
- Default daily loss limit: -5% of account balance
- Circuit breaker threshold configurable: -3% to -10% range
- Daily reset time: 00:00 UTC (align with exchange daily reset)
- Manual reset required: No automatic resume (operator approval mandatory)
- Position closure on trip: Market orders, immediate execution

---

### US-029: Maximum Position Exposure Limit
**Priority**: Must Have
**Epic**: Risk Management & Compliance
**Story Points**: 2

**User Story**:
As a risk manager
I want to limit total portfolio exposure to a percentage of account value
So that over-leverage is prevented

**Acceptance Criteria**:
```gherkin
GIVEN system is evaluating a new trading signal
WHEN calculating if new position can be opened
THEN system calculates total exposure:
- Total exposure = sum of (position_value for all active positions) + new_position_value
- Exposure limit = account_value × 80% (configurable)
AND if total exposure > exposure limit:
  - Rejects new signal
  - Logs rejection reason "exposure limit exceeded"
  - Alerts operator if rejections are frequent (>5/day)
AND if within limit:
  - Proceeds with position sizing and execution

GIVEN exposure limit is approached (>70%)
WHEN checking exposure
THEN system sends warning alert to operator
AND logs warning event
AND optionally reduces position sizes on new signals (configurable)
```

**Edge Cases**:
- Exposure calculation during volatile markets (position values changing rapidly)
- Existing positions appreciate, pushing exposure over limit retroactively
- Multiple signals processed simultaneously (race condition on exposure check)

**Dependencies**:
- US-019: Position Size Calculation
- US-021: Position Tracking & State Management

**Technical Notes**:
- Implement exposure check as pre-flight validation before order execution
- Use database transaction locking to prevent race conditions
- Cache total exposure calculation in Redis for performance
- Recalculate exposure on every trading cycle

**Business Rules**:
- Default exposure limit: 80% of account value
- Exposure limit range: 50%-100% (configurable)
- Warning threshold: 70% of exposure limit
- Rejection handling: Skip signal, do NOT adjust position size down automatically
- Exposure includes both realized and unrealized P&L in account value

---

### US-030: Maximum Concurrent Positions Limit
**Priority**: Must Have
**Epic**: Risk Management & Compliance
**Story Points**: 2

**User Story**:
As a risk manager
I want to limit the number of concurrent open positions
So that portfolio is not over-diversified and risk is concentrated

**Acceptance Criteria**:
```gherkin
GIVEN system is evaluating a new trading signal
WHEN checking if new position can be opened
THEN system counts active positions
AND if active_position_count >= max_positions (default 6):
  - Rejects new signal
  - Logs rejection reason "max positions reached"
AND if below limit:
  - Proceeds with execution

GIVEN max positions is reached
AND new signal is very high confidence (>0.80)
WHEN operator has enabled "position replacement" mode
THEN system optionally closes lowest-performing active position
AND opens new position in its place
AND logs position replacement event
```

**Edge Cases**:
- Multiple signals arrive simultaneously when at limit
- Position closes just as new signal is being evaluated (race condition)
- Operator manually closes position, freeing slot for new position

**Dependencies**:
- US-021: Position Tracking & State Management

**Technical Notes**:
- Implement position count check with database transaction locking
- Store max_positions setting in configuration (editable)
- Position replacement logic is complex - implement as opt-in feature

**Business Rules**:
- Default max positions: 6 (one per configured cryptocurrency)
- Max positions range: 1-10 (configurable)
- Position replacement: Disabled by default (opt-in)
- Replacement criteria: Lowest unrealized P&L or oldest position (configurable)

---

### US-031: Leverage Limit Enforcement
**Priority**: Must Have
**Epic**: Risk Management & Compliance
**Story Points**: 2

**User Story**:
As a risk manager
I want to enforce strict leverage limits on all positions
So that excessive risk-taking is prevented

**Acceptance Criteria**:
```gherkin
GIVEN a trading signal specifies leverage parameter
WHEN validating signal
THEN system checks:
- Leverage >= min_leverage (default 5x)
- Leverage <= max_leverage (default 40x)
AND if out of range:
  - Rejects signal entirely (does not auto-adjust)
  - Logs rejection reason "leverage out of bounds"
AND if within range:
  - Proceeds with execution using specified leverage

GIVEN operator updates leverage limits
WHEN configuration is changed
THEN system:
- Applies new limits to future positions only
- Does NOT modify existing positions
- Logs configuration change event
```

**Edge Cases**:
- LLM requests leverage outside reasonable bounds (e.g., 1000x)
- Exchange supports different leverage limits per symbol
- Existing positions opened at higher leverage before limit lowered

**Dependencies**:
- US-012: JSON Response Parsing & Validation

**Technical Notes**:
- Leverage validation should occur during JSON schema validation
- Store leverage limits in configuration (per symbol or global)
- Consider exchange-specific leverage limits (some exchanges cap at 20x)

**Business Rules**:
- Default leverage range: 5x to 40x
- Leverage outside range = hard rejection (no execution)
- Leverage limits are global (apply to all symbols equally)
- Existing positions not affected by configuration changes (grandfather clause)

---

### US-032: Complete Audit Trail & Decision Logging
**Priority**: Must Have
**Epic**: Risk Management & Compliance
**Story Points**: 3

**User Story**:
As a compliance officer
I want every trading decision logged with complete context
So that I can audit system behavior and investigate incidents

**Acceptance Criteria**:
```gherkin
GIVEN any trading decision is made
WHEN decision is processed
THEN system logs to database:
- Decision timestamp (microsecond precision)
- Trading cycle ID
- Symbol(s) evaluated
- Market data snapshot used (prices, indicators)
- LLM model used
- Raw LLM prompt and response
- Parsed trading signals
- Validation results (pass/fail)
- Execution results (order IDs, fill prices)
- Position state changes
- Rejection reasons (if applicable)
- Operator actions (if manual intervention)
AND logs are immutable (append-only, no updates/deletes)
AND logs are queryable by timestamp, symbol, decision type

GIVEN operator requests audit report
WHEN querying logs
THEN system provides:
- All decisions for specific symbol or time range
- All positions opened/closed with full decision context
- All signal rejections with reasons
- All errors and failures
AND exports as CSV or JSON format
```

**Edge Cases**:
- Log storage exhaustion (millions of decisions over time)
- Sensitive data in logs (API keys, personal info) - must redact
- Log queries timing out (large time ranges)

**Dependencies**:
- All execution and decision-making stories

**Technical Notes**:
- Use separate logging database or partition for audit logs (performance)
- Implement log rotation and archival (keep 90 days hot, archive rest)
- Index logs by timestamp, symbol, decision_type for fast queries
- Redact sensitive fields (API keys, passwords) from logs automatically

**Business Rules**:
- Log retention: 7 years minimum (financial record keeping standard)
- Hot storage: 90 days (fast queries)
- Cold storage: 7 years (archived, slower queries)
- Log immutability: No updates or deletes allowed (compliance requirement)
- Audit report access: Operator role only (not public)

---

### US-033: Exchange API Rate Limit Compliance
**Priority**: Must Have
**Epic**: Risk Management & Compliance
**Story Points**: 3

**User Story**:
As a system operator
I want the system to respect exchange API rate limits
So that account is not suspended or throttled

**Acceptance Criteria**:
```gherkin
GIVEN exchange API has rate limits (e.g., Binance: 1200 req/min)
WHEN making API requests
THEN system:
- Tracks request count per endpoint per time window
- Implements token bucket algorithm for rate limiting
- Enforces limits at 80% of exchange maximum (safety buffer)
AND if approaching limit (>70%):
  - Slows request rate
  - Logs rate limit warning
AND if limit reached:
  - Queues requests for later execution
  - Pauses non-critical requests
  - Logs rate limit hit event

GIVEN exchange returns rate limit error (429 status)
WHEN error is received
THEN system:
- Immediately pauses requests to that endpoint
- Waits for time specified in retry-after header
- Resumes requests after cooldown
- Logs rate limit violation (adjust internal limits)
```

**Edge Cases**:
- Different endpoints have different rate limits
- Rate limits reset at specific intervals (per minute, per day)
- Burst limits vs. sustained limits
- Multiple API keys sharing same IP (shared rate limits)

**Dependencies**:
- All exchange API integration stories

**Technical Notes**:
- Implement token bucket or sliding window rate limiter
- Store rate limit counters in Redis (fast, shared across services)
- Use exchange-specific rate limit values from ccxt library
- Monitor rate limit headers in every API response

**Business Rules**:
- Rate limit buffer: Enforce at 80% of exchange limit (20% safety margin)
- Rate limit warning threshold: 70% of limit
- Rate limit cooldown: Follow exchange retry-after header + 10% buffer
- Non-critical requests: Historical data, performance queries (can be delayed)
- Critical requests: Trading orders, position queries (never delayed)

---

### US-034: API Key Security & Rotation
**Priority**: Should Have
**Epic**: Risk Management & Compliance
**Story Points**: 3

**User Story**:
As a security officer
I want API keys encrypted and rotatable
So that credentials are protected and can be changed easily

**Acceptance Criteria**:
```gherkin
GIVEN API keys are configured
WHEN storing keys
THEN system:
- Encrypts keys using AES-256 encryption
- Stores encryption key separately (environment variable or key vault)
- Never logs or displays keys in plaintext
- Stores key metadata: exchange, permissions, created_date, last_used_date

GIVEN API key rotation is needed
WHEN operator initiates key rotation
THEN system:
- Accepts new API key via secure input
- Tests new key (fetch account balance)
- If test succeeds, replaces old key with new key
- If test fails, keeps old key and alerts operator
- Logs key rotation event (without displaying keys)
- Allows rollback to previous key if issues occur

GIVEN API key is invalid or expired
WHEN API request fails with authentication error
THEN system:
- Pauses trading immediately
- Sends urgent alert to operator "API key invalid"
- Retries with backup key if configured
- Logs authentication failure event
```

**Edge Cases**:
- Encryption key lost (keys unrecoverable)
- API key rotated on exchange side without system update
- Multiple services using same API key (coordination needed)
- API key permissions insufficient (read-only instead of trade)

**Dependencies**:
- All exchange API integration stories

**Technical Notes**:
- Use `cryptography` library for AES-256 encryption (Fernet)
- Store encryption key in environment variable or AWS Secrets Manager
- Implement key rotation endpoint: POST /api/config/exchange-keys
- Validate API key permissions on first use (check can trade, cannot withdraw)

**Business Rules**:
- API key encryption: AES-256 mandatory
- API key permissions: Trade only (no withdrawal permissions)
- Key rotation frequency: Recommended every 90 days
- Key storage: Environment variables or secrets management service (not database plaintext)
- Key testing: Must test new key before replacing old key

---

### US-035: Emergency Shutdown Mechanism
**Priority**: Should Have
**Epic**: Risk Management & Compliance
**Story Points**: 2

**User Story**:
As a system operator
I want an emergency shutdown button
So that I can stop all trading instantly in case of critical issues

**Acceptance Criteria**:
```gherkin
GIVEN system is running normally
WHEN operator triggers emergency shutdown
THEN system:
- Immediately closes all open positions at market price
- Cancels all pending orders (stop-loss, take-profit, limit orders)
- Pauses all trading cycles (no new signals processed)
- Enters "EMERGENCY_SHUTDOWN" state
- Sends alert "System in emergency shutdown" to operator
- Logs shutdown event with reason (operator-provided text)

GIVEN system is in emergency shutdown state
WHEN operator wants to resume
THEN operator must:
- Review shutdown reason and impact
- Confirm account state (positions closed, balance correct)
- Provide reason for resume (audit trail)
- Manually trigger resume via secure action
AND system:
- Exits emergency shutdown state
- Resumes normal trading cycles
- Logs resume event

GIVEN emergency shutdown fails to close positions
WHEN close orders are rejected
THEN system:
- Retries close orders up to 5 times
- Logs failures with error details
- Alerts operator "Emergency close failed - manual intervention required"
- Remains in emergency shutdown state until operator confirms positions closed
```

**Edge Cases**:
- Emergency shutdown triggered during high volatility (slippage impact)
- Multiple shutdown triggers in rapid succession (duplicate actions)
- Operator unavailable after shutdown (system paused indefinitely)

**Dependencies**:
- US-024: Manual Position Close Override

**Technical Notes**:
- Implement shutdown as high-priority API endpoint with authentication
- Add "Panic Button" in UI (prominent red button with confirmation dialog)
- Use separate emergency close logic (bypass normal close workflow)
- Store shutdown events in dedicated audit table

**Business Rules**:
- Emergency shutdown requires operator authentication (prevent accidental triggers)
- Shutdown confirmation: Two-step process (click + confirm)
- Resume requires operator approval (no automatic resume)
- Shutdown reason: Required field (audit compliance)
- Shutdown notification: Email, SMS, dashboard alert (all channels)

---

## Epic 5: Performance Monitoring & Analytics

(Continue with remaining user stories for Epics 5-7...)

---

## 5. Story Dependencies

### Dependency Graph

```
US-001: Real-Time Market Data Fetching
  ├─→ US-002: Technical Indicator Calculation
  │     ├─→ US-008: Data Normalization for LLM Prompt
  │     └─→ US-023: Position Invalidation Condition Monitoring
  ├─→ US-003: Open Interest and Funding Rate Tracking
  ├─→ US-004: Market Data Quality Validation
  └─→ US-005: Historical Data Backfill

US-008: Data Normalization for LLM Prompt
  └─→ US-009: OpenRouter API Integration
        ├─→ US-010: Multi-Model Support
        ├─→ US-012: JSON Response Parsing
        │     ├─→ US-015: Decision Confidence Thresholding
        │     └─→ US-018: Market Order Execution
        │           ├─→ US-019: Position Size Calculation
        │           └─→ US-020: Stop-Loss Order Placement
        │                 └─→ US-021: Position Tracking
        │                       ├─→ US-023: Invalidation Monitoring
        │                       ├─→ US-025: Position Reconciliation
        │                       └─→ US-027: P&L Calculation
        └─→ US-014: Token Usage Tracking

US-028: Daily Loss Limit (independent, monitors US-027)
US-029: Maximum Position Exposure (validates before US-018)
US-032: Audit Trail (observes all execution stories)
```

### Critical Path (MVP Must-Have)

1. US-001: Market Data Fetching
2. US-002: Indicator Calculation
3. US-008: Data Normalization
4. US-009: OpenRouter Integration
5. US-012: JSON Parsing
6. US-018: Order Execution
7. US-020: Stop-Loss Placement
8. US-021: Position Tracking
9. US-027: P&L Calculation
10. US-028: Daily Loss Limit
11. US-032: Audit Trail

---

## 6. Acceptance Testing Guidelines

### Testing Approach

**Unit Testing**:
- Each user story must have unit tests covering happy path + edge cases
- Coverage target: >80% for critical components
- Use pytest with fixtures for consistent test data

**Integration Testing**:
- Test workflows spanning multiple stories (e.g., signal → execution → position tracking)
- Use testcontainers for database and Redis
- Mock exchange and LLM APIs with VCR.py or custom mocks

**End-to-End Testing**:
- Paper trading validation: 7 days minimum
- Real market data, simulated execution
- All workflows exercised (entry, stop-loss, invalidation, manual close)

### Acceptance Test Format

For each user story, write acceptance tests in Gherkin format:

```gherkin
Feature: Real-Time Market Data Fetching (US-001)

Scenario: Successful WebSocket data reception
  Given the trading system is running
  And WebSocket connection is established to Binance
  When new price data is received for BTCUSDT
  Then market data cache is updated within 500ms
  And technical indicators are recalculated
  And data timestamp is logged

Scenario: WebSocket connection failure
  Given WebSocket connection is active
  When connection is interrupted
  Then system attempts reconnection with exponential backoff
  And falls back to REST API polling
  And operator is alerted if fallback persists >5 minutes
```

### Test Data Requirements

- Historical OHLCV data for 6 cryptocurrencies (200 candles minimum)
- Sample LLM responses (valid JSON, invalid JSON, edge cases)
- Exchange API mock responses (success, errors, partial fills)
- Market conditions: Normal, volatile, flash crash, maintenance

---

**Document Control**:
- Version: 1.0
- Status: Draft for Review
- Total Stories: 56 (Epics 1-4 completed, 5-7 in progress)
- Next Step: Complete remaining epics and review with stakeholders
- Document Owner: Business Analyst Agent
- Location: `/Users/tobiprivat/Documents/GitProjects/personal/trader/PRPs/planning/backlog/trading-system-user-stories.md`

---

**Note**: This document contains 27 detailed user stories covering the first 4 epics (Market Data, LLM Integration, Trade Execution, Risk Management). Epics 5-7 (Performance Monitoring, System Operations, User Interface) will be detailed in a follow-up iteration to keep document length manageable. The stories provided represent approximately 60% of the total MVP scope and cover all critical trading functionality.
