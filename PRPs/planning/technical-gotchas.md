# Technical Gotchas & Mitigation Strategies

**Date**: October 27, 2025
**Phase**: Phase 1 - Business Discovery & Requirements
**Researcher**: Context Researcher Agent
**Status**: Complete
**Priority**: 🔴 CRITICAL - READ BEFORE IMPLEMENTATION

---

## Overview

This document catalogs all identified technical gotchas, edge cases, failure modes, and their mitigation strategies for the LLM-Powered Crypto Trading System. Each gotcha is rated by severity and includes specific implementation guidance.

**Severity Levels**:
- 🔴 **CRITICAL**: Will cause system failure, data loss, or financial loss
- 🟡 **HIGH**: Will degrade performance or cause reliability issues
- 🟢 **MEDIUM**: Will cause minor issues or annoyances
- 🔵 **LOW**: Edge cases with minimal impact

---

## 1. Exchange Integration Gotchas (ccxt)

### 🔴 CRITICAL: Rate Limit Violations Leading to Bans

**What Happens**:
- Exchange responds with `RateLimitExceeded` error
- Repeated violations can lead to temporary IP bans (1-24 hours)
- Trading operations completely blocked during ban period

**Why It Matters**:
- Cannot execute trades during ban = missed opportunities + unmanaged risk
- No way to close positions or adjust stop-losses
- Financial loss from inability to exit positions

**Where It Occurs**:
- REST API calls without proper throttling
- `fetchTickers()` on Binance (consumes high rate limit weight)
- `fetchPositions()` on Bybit (known issue even with `enableRateLimit: True`)
- Parallel requests to same exchange without coordination

**Mitigation Strategy**:
```python
# 1. ALWAYS enable rate limiting
exchange = ccxt.binance({
    'enableRateLimit': True,
    'rateLimit': 1200,  # Binance: 1200ms = 50 req/min
})

# 2. Use WebSocket for market data (doesn't count against limits)
from ccxt.pro import binance as binance_ws
exchange_ws = binance_ws({
    'enableRateLimit': True,
})

# 3. Implement exponential backoff for retries
async def safe_api_call(func, *args, max_retries=3, **kwargs):
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except ccxt.RateLimitExceeded as e:
            if attempt == max_retries - 1:
                # Log critical error and alert operator
                logger.critical(f"Rate limit exceeded after {max_retries} retries")
                await send_alert("CRITICAL: Exchange rate limit ban imminent")
                raise
            backoff = (2 ** attempt) * 60  # 60s, 120s, 240s
            logger.warning(f"Rate limit hit, backing off {backoff}s")
            await asyncio.sleep(backoff)

# 4. Coordinate requests with semaphore (for parallel operations)
exchange_semaphore = asyncio.Semaphore(3)  # Max 3 concurrent requests

async def fetch_with_semaphore(symbol):
    async with exchange_semaphore:
        return await exchange.fetch_ticker(symbol)

# 5. Track rate limit usage (for exchanges that provide headers)
def check_rate_limit_headers(response_headers):
    used = int(response_headers.get('X-MBX-USED-WEIGHT-1M', 0))
    limit = 1200
    if used > limit * 0.8:  # 80% threshold
        logger.warning(f"Rate limit at {used}/{limit} (80%)")
        await send_alert("WARNING: Approaching rate limit")
```

**Testing Strategy**:
- Deliberately trigger rate limits in testnet
- Verify backoff logic works correctly
- Confirm alerting system activates
- Test recovery after rate limit period expires

---

### 🔴 CRITICAL: Partial Order Fills Creating Position Mismatches

**What Happens**:
- Order placed for 1.0 BTC but only 0.7 BTC fills immediately
- System records 1.0 BTC position but exchange shows 0.7 BTC
- Stop-loss calculations incorrect (based on wrong position size)
- Risk management breaks down

**Why It Matters**:
- Incorrect position tracking = wrong risk exposure
- Stop-loss may not cover actual position
- Liquidation risk miscalculated
- P&L reporting incorrect

**Where It Occurs**:
- Limit orders in low liquidity markets
- Large positions (>1% of order book depth)
- Market orders during high volatility
- All exchanges, all order types

**Mitigation Strategy**:
```python
# 1. Position reconciliation after every order
async def execute_order_with_reconciliation(symbol, side, amount):
    # Place order
    order = await exchange.create_order(
        symbol=symbol,
        type='market',  # or 'limit'
        side=side,
        amount=amount
    )

    # Wait for settlement (exchange-specific delay)
    await asyncio.sleep(2)

    # Fetch actual fills
    filled_order = await exchange.fetch_order(order['id'], symbol)

    # Reconcile position
    actual_filled = filled_order['filled']
    expected_filled = amount

    if actual_filled < expected_filled * 0.95:  # >5% discrepancy
        logger.warning(f"Partial fill: {actual_filled}/{expected_filled}")

        # Decision: wait for remaining or cancel
        if filled_order['status'] == 'open':
            remaining = expected_filled - actual_filled
            if remaining < minimum_order_size:
                # Cancel remaining (too small to fill)
                await exchange.cancel_order(order['id'], symbol)
                logger.info(f"Cancelled remaining {remaining} (below min size)")
            else:
                # Wait for remaining fill (with timeout)
                await wait_for_fill_or_timeout(order['id'], symbol, timeout=60)

    # Update position in database with ACTUAL filled amount
    await db.update_position(symbol, actual_filled, filled_order['average'])

    # Recalculate stop-loss based on actual position
    await update_stop_loss(symbol, actual_filled, filled_order['average'])

    return filled_order

# 2. Periodic position reconciliation (every 5 minutes)
async def reconcile_all_positions():
    # Fetch positions from exchange
    exchange_positions = await exchange.fetch_positions()

    # Fetch positions from database
    db_positions = await db.get_active_positions()

    # Compare and log discrepancies
    for db_pos in db_positions:
        exchange_pos = find_position(exchange_positions, db_pos['symbol'])

        if not exchange_pos:
            logger.error(f"Position {db_pos['symbol']} in DB but not on exchange!")
            await send_alert(f"CRITICAL: Ghost position {db_pos['symbol']}")
            continue

        db_qty = db_pos['quantity']
        exch_qty = exchange_pos['contracts']

        if abs(db_qty - exch_qty) > 0.0001:  # Floating point tolerance
            logger.error(f"Position mismatch {db_pos['symbol']}: DB={db_qty}, Exchange={exch_qty}")
            await send_alert(f"CRITICAL: Position mismatch {db_pos['symbol']}")

            # Auto-heal: trust exchange as source of truth
            await db.update_position_quantity(db_pos['symbol'], exch_qty)
            logger.info(f"Auto-healed position {db_pos['symbol']} to {exch_qty}")

# 3. Use ccxt's fetch_order_trades() for precise fill details
async def get_fill_details(order_id, symbol):
    trades = await exchange.fetch_order_trades(order_id, symbol)

    total_filled = sum(t['amount'] for t in trades)
    average_price = sum(t['price'] * t['amount'] for t in trades) / total_filled
    total_fees = sum(t['fee']['cost'] for t in trades)

    return {
        'filled': total_filled,
        'average_price': average_price,
        'fees': total_fees,
        'trades': trades
    }
```

**Testing Strategy**:
- Test with small limit orders in low liquidity pairs
- Simulate partial fills in testnet
- Verify reconciliation logic catches discrepancies
- Test auto-healing doesn't create new issues

---

### 🔴 CRITICAL: WebSocket Disconnections During Trading Cycle

**What Happens**:
- WebSocket connection drops mid-cycle
- Market data stream stops
- Stale data used for trading decisions
- Orders executed based on outdated prices

**Why It Matters**:
- Trading on stale data = guaranteed losses in volatile markets
- May enter positions at wrong prices
- Stop-losses may not trigger (no price updates)
- System appears to work but is actually broken

**Where It Occurs**:
- Network instability
- Exchange-side connection resets
- Long-running connections without heartbeat
- All exchanges with WebSocket support

**Mitigation Strategy**:
```python
import asyncio
from datetime import datetime, timedelta

class ResilientWebSocket:
    def __init__(self, exchange, symbol):
        self.exchange = exchange
        self.symbol = symbol
        self.last_message_time = None
        self.reconnect_delay = 5  # seconds
        self.max_staleness = 30  # seconds
        self.connection = None

    async def connect(self):
        """Establish WebSocket connection with retry"""
        retry_count = 0
        while retry_count < 5:
            try:
                self.connection = await self.exchange.watch_ticker(self.symbol)
                self.last_message_time = datetime.now()
                logger.info(f"WebSocket connected: {self.symbol}")
                return
            except Exception as e:
                retry_count += 1
                backoff = self.reconnect_delay * (2 ** retry_count)
                logger.error(f"WebSocket connect failed (attempt {retry_count}): {e}")
                await asyncio.sleep(backoff)

        raise Exception(f"Failed to connect WebSocket after 5 attempts")

    async def monitor_connection(self):
        """Background task to monitor connection health"""
        while True:
            await asyncio.sleep(10)  # Check every 10 seconds

            if self.last_message_time:
                staleness = (datetime.now() - self.last_message_time).total_seconds()

                if staleness > self.max_staleness:
                    logger.warning(f"WebSocket stale ({staleness}s), reconnecting")
                    await send_alert(f"WARNING: WebSocket stale for {self.symbol}")
                    await self.reconnect()

    async def reconnect(self):
        """Reconnect WebSocket"""
        try:
            await self.connection.close()
        except:
            pass

        await self.connect()

    async def get_ticker(self):
        """Get ticker with staleness check"""
        if not self.connection:
            await self.connect()

        # Check staleness before returning data
        if self.last_message_time:
            staleness = (datetime.now() - self.last_message_time).total_seconds()

            if staleness > self.max_staleness:
                logger.error(f"Data too stale ({staleness}s), falling back to REST")
                await send_alert(f"CRITICAL: Stale WebSocket data for {self.symbol}")

                # Fallback to REST API
                return await self.exchange.fetch_ticker(self.symbol)

        # Get latest message
        ticker = await self.exchange.watch_ticker(self.symbol)
        self.last_message_time = datetime.now()

        return ticker

# Usage in trading cycle
async def fetch_market_data_safe(symbols):
    websockets = {s: ResilientWebSocket(exchange, s) for s in symbols}

    # Start connection monitors
    monitors = [asyncio.create_task(ws.monitor_connection())
                for ws in websockets.values()]

    # Fetch data with automatic fallback
    data = {}
    for symbol, ws in websockets.items():
        try:
            data[symbol] = await ws.get_ticker()
        except Exception as e:
            logger.error(f"Failed to get data for {symbol}: {e}")
            # Critical: skip this asset in trading cycle
            await send_alert(f"CRITICAL: No data for {symbol}, skipping cycle")

    return data
```

**Testing Strategy**:
- Deliberately disconnect network during trading cycle
- Verify fallback to REST API works
- Test reconnection logic under various failure scenarios
- Validate alerting triggers correctly

---

### 🟡 HIGH: Exchange-Specific Order Type Limitations

**What Happens**:
- Attempt to place stop-loss order type not supported by exchange
- Order rejected with cryptic error message
- Position left unprotected without stop-loss
- Must use different order types per exchange

**Why It Matters**:
- Risk management compromised without stop-losses
- Different code paths per exchange increases complexity
- Easy to forget edge cases during implementation

**Where It Occurs**:
- Binance: Supports `stop_market` and `stop_limit` orders
- Bybit: Supports `stop_market` with `stopPrice` parameter
- Some exchanges: Only support post-only `limit` orders
- DEXes: May not support stop orders at all

**Mitigation Strategy**:
```python
# 1. Exchange capability detection
EXCHANGE_CAPABILITIES = {
    'binance': {
        'stop_orders': True,
        'stop_order_types': ['stop_market', 'stop_limit'],
        'trailing_stop': True,
    },
    'bybit': {
        'stop_orders': True,
        'stop_order_types': ['stop_market'],
        'trailing_stop': True,
    },
    'coinbase': {
        'stop_orders': True,
        'stop_order_types': ['stop_limit'],
        'trailing_stop': False,
    },
}

# 2. Unified stop-loss abstraction
class StopLossManager:
    def __init__(self, exchange_id, exchange):
        self.exchange_id = exchange_id
        self.exchange = exchange
        self.capabilities = EXCHANGE_CAPABILITIES.get(exchange_id, {})

    async def place_stop_loss(self, symbol, side, amount, stop_price):
        """Place stop-loss using exchange-appropriate order type"""

        if not self.capabilities.get('stop_orders'):
            # Fallback: monitor in application layer
            logger.warning(f"{self.exchange_id} doesn't support stop orders, using app-level monitoring")
            return await self.monitor_stop_loss_in_app(symbol, side, amount, stop_price)

        # Determine best order type
        if 'stop_market' in self.capabilities['stop_order_types']:
            return await self.exchange.create_order(
                symbol=symbol,
                type='stop_market',
                side=side,
                amount=amount,
                params={'stopPrice': stop_price}
            )
        elif 'stop_limit' in self.capabilities['stop_order_types']:
            # Need limit price (e.g., stop_price - 0.1% for sell)
            limit_price = stop_price * 0.999 if side == 'sell' else stop_price * 1.001
            return await self.exchange.create_order(
                symbol=symbol,
                type='stop_limit',
                side=side,
                amount=amount,
                price=limit_price,
                params={'stopPrice': stop_price}
            )
        else:
            raise Exception(f"No supported stop order type for {self.exchange_id}")

    async def monitor_stop_loss_in_app(self, symbol, side, amount, stop_price):
        """Application-level stop-loss monitoring (fallback)"""
        # Store in database for monitoring task
        await db.add_stop_loss_monitor({
            'symbol': symbol,
            'side': side,
            'amount': amount,
            'stop_price': stop_price,
            'created_at': datetime.now()
        })

        logger.info(f"App-level stop-loss set: {symbol} @ {stop_price}")
        return {'type': 'app_monitored', 'stop_price': stop_price}

# 3. Background task for app-level stop-loss monitoring
async def monitor_app_level_stops():
    """Check prices and trigger stop-losses manually"""
    while True:
        try:
            stops = await db.get_active_stop_monitors()

            for stop in stops:
                ticker = await exchange.fetch_ticker(stop['symbol'])
                current_price = ticker['last']

                # Check if stop should trigger
                if stop['side'] == 'sell' and current_price <= stop['stop_price']:
                    logger.warning(f"App stop-loss triggered: {stop['symbol']}")
                    await execute_stop_order(stop)
                elif stop['side'] == 'buy' and current_price >= stop['stop_price']:
                    logger.warning(f"App stop-loss triggered: {stop['symbol']}")
                    await execute_stop_order(stop)

            await asyncio.sleep(5)  # Check every 5 seconds

        except Exception as e:
            logger.error(f"Error in stop-loss monitor: {e}")
            await asyncio.sleep(10)
```

**Testing Strategy**:
- Test with each supported exchange
- Verify stop-loss orders place correctly
- Test fallback for exchanges without stop support
- Validate app-level monitoring triggers correctly

---

## 2. LLM Integration Gotchas (OpenRouter)

### 🔴 CRITICAL: Invalid JSON Responses Breaking Trading Cycle

**What Happens**:
- LLM returns malformed JSON (extra text, missing braces, incorrect format)
- JSON parser raises exception
- Trading cycle aborts
- No decisions made for that cycle (3 minutes lost)

**Why It Matters**:
- Missed trading opportunities every time JSON parsing fails
- System appears unreliable
- Manual intervention required frequently
- Cannot achieve 99.5% uptime target

**Where It Occurs**:
- All LLM providers (even with `response_format: 'json_object'`)
- Worse with smaller/cheaper models
- Exacerbated by complex prompts
- More frequent under high load

**Mitigation Strategy**:
```python
import json
import re
from typing import Optional, Dict

class LLMResponseParser:
    def __init__(self):
        self.retry_count = 0
        self.max_retries = 2

    def extract_json_from_text(self, text: str) -> Optional[Dict]:
        """Extract JSON even if LLM adds extra text"""

        # Method 1: Try direct JSON parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Method 2: Find JSON block in markdown code fence
        json_block_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_block_match:
            try:
                return json.loads(json_block_match.group(1))
            except json.JSONDecodeError:
                pass

        # Method 3: Find JSON object anywhere in text
        json_match = re.search(r'(\{.*\})', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Method 4: Try to fix common JSON errors
        try:
            # Remove trailing commas
            fixed_text = re.sub(r',\s*}', '}', text)
            fixed_text = re.sub(r',\s*]', ']', fixed_text)
            # Fix unquoted keys
            fixed_text = re.sub(r'(\w+):', r'"\1":', fixed_text)
            return json.loads(fixed_text)
        except:
            pass

        return None

    def validate_trading_signals(self, data: Dict) -> bool:
        """Validate trading signals structure"""
        required_fields = ['signals']

        if not all(field in data for field in required_fields):
            logger.error(f"Missing required fields: {required_fields}")
            return False

        # Validate each signal
        for signal in data['signals']:
            required_signal_fields = ['symbol', 'action', 'confidence']
            if not all(field in signal for field in required_signal_fields):
                logger.error(f"Signal missing required fields: {required_signal_fields}")
                return False

            # Validate action values
            valid_actions = ['buy_to_enter', 'sell_to_enter', 'hold', 'close_position']
            if signal['action'] not in valid_actions:
                logger.error(f"Invalid action: {signal['action']}")
                return False

            # Validate confidence range
            if not (0.0 <= signal['confidence'] <= 1.0):
                logger.error(f"Invalid confidence: {signal['confidence']}")
                return False

        return True

    async def parse_llm_response(self, response_text: str) -> Optional[Dict]:
        """Parse and validate LLM response with retry"""

        # Extract JSON
        data = self.extract_json_from_text(response_text)

        if not data:
            logger.error(f"Failed to extract JSON from response: {response_text[:200]}")

            if self.retry_count < self.max_retries:
                self.retry_count += 1
                logger.info(f"Retrying LLM request (attempt {self.retry_count})")

                # Retry with more explicit prompt
                retry_prompt = "IMPORTANT: Return ONLY valid JSON. No extra text."
                # ... make new LLM request with retry_prompt ...
                return None  # Trigger retry in calling code

            await send_alert("CRITICAL: LLM returning invalid JSON repeatedly")
            return None

        # Validate structure
        if not self.validate_trading_signals(data):
            logger.error(f"Invalid trading signals structure: {data}")

            if self.retry_count < self.max_retries:
                self.retry_count += 1
                return None  # Trigger retry

            return None

        self.retry_count = 0  # Reset on success
        return data

# Usage in trading cycle
async def get_trading_decisions(market_data):
    parser = LLMResponseParser()

    for attempt in range(3):
        try:
            # Call LLM
            response = await openrouter.chat_completion(
                model='anthropic/claude-3-haiku',
                messages=[
                    {'role': 'system', 'content': SYSTEM_PROMPT},
                    {'role': 'user', 'content': format_market_data(market_data)}
                ],
                response_format={'type': 'json_object'},
                temperature=0.2  # Lower for consistency
            )

            response_text = response['choices'][0]['message']['content']

            # Parse and validate
            signals = await parser.parse_llm_response(response_text)

            if signals:
                return signals

            # Retry with different model if JSON parsing fails
            if attempt == 1:
                logger.warning("Switching to backup model due to JSON issues")
                # Try more reliable (but expensive) model
                # ... retry logic ...

        except Exception as e:
            logger.error(f"LLM request failed (attempt {attempt + 1}): {e}")
            await asyncio.sleep(2 ** attempt)

    # All retries failed - use safe default
    logger.critical("All LLM attempts failed, using safe default (hold all)")
    await send_alert("CRITICAL: LLM failures, defaulting to HOLD")

    return create_hold_all_signals(market_data)

def create_hold_all_signals(market_data):
    """Safe default: hold all positions"""
    return {
        'signals': [
            {'symbol': symbol, 'action': 'hold', 'confidence': 0.0, 'reasoning': 'LLM failure - safe default'}
            for symbol in market_data.keys()
        ]
    }
```

**Testing Strategy**:
- Test with intentionally malformed JSON responses
- Verify extraction logic handles all edge cases
- Test retry logic with multiple failures
- Validate safe default (hold) activates correctly

---

### 🟡 HIGH: LLM Cost Runaway from Oversized Prompts

**What Happens**:
- Prompt includes too much historical data or indicators
- Token count exceeds 2,000+ tokens per request
- Cost multiplies: 86,400 decisions/month × 2,000 tokens × $0.001 = $172/month
- Blows past $100/month budget

**Why It Matters**:
- Budget constraint violated
- Unsustainable operational costs
- Forces downgrade to worse models or reduced frequency

**Where It Occurs**:
- Including full price history (last 100 candles = 1,000+ tokens)
- Verbose indicator explanations
- Including all 6 assets in single prompt
- Using expensive models (GPT-4, Claude Opus)

**Mitigation Strategy**:
```python
import tiktoken

class TokenOptimizedPromptBuilder:
    def __init__(self, model='gpt-4o-mini'):
        self.encoder = tiktoken.encoding_for_model(model)
        self.max_input_tokens = 1000  # Budget constraint
        self.max_output_tokens = 300   # For trading signals

    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        return len(self.encoder.encode(text))

    def build_optimized_prompt(self, market_data, current_positions):
        """Build token-optimized prompt"""

        # Static components (cached/reused)
        system_prompt = """You are a crypto trading agent. Analyze data and return JSON signals.
Output format: {"signals": [{"symbol": "BTC", "action": "hold|buy_to_enter|sell_to_enter|close_position", "confidence": 0.0-1.0, "risk_usd": 100}]}"""

        # Dynamic components (minimized)
        market_summary = []
        for symbol, data in market_data.items():
            # Minimize data to essentials
            summary = (
                f"{symbol}: ${data['price']:.2f} "
                f"EMA20:{data['ema20']:.1f} RSI:{data['rsi']:.0f} "
                f"MACD:{data['macd']:.3f} Vol:{data['volume_ratio']:.1f}x"
            )
            market_summary.append(summary)

        # Current positions (if any)
        position_summary = []
        for pos in current_positions:
            summary = f"{pos['symbol']} {pos['side']} {pos['size']:.4f} @{pos['entry']:.2f} PnL:{pos['pnl']:.1f}%"
            position_summary.append(summary)

        # Assemble prompt
        user_prompt = "\n".join([
            "Market Data:",
            *market_summary,
            "\nPositions:" if position_summary else "",
            *position_summary
        ])

        # Count tokens
        system_tokens = self.count_tokens(system_prompt)
        user_tokens = self.count_tokens(user_prompt)
        total_input = system_tokens + user_tokens

        # Log token usage
        logger.info(f"Prompt tokens: {total_input} (system: {system_tokens}, user: {user_tokens})")

        if total_input > self.max_input_tokens:
            logger.warning(f"Prompt exceeds budget: {total_input} > {self.max_input_tokens}")
            # Trim to fit budget
            user_prompt = self.trim_prompt(user_prompt, self.max_input_tokens - system_tokens)

        return system_prompt, user_prompt

    def trim_prompt(self, prompt: str, max_tokens: int) -> str:
        """Trim prompt to fit token budget"""
        current_tokens = self.count_tokens(prompt)

        if current_tokens <= max_tokens:
            return prompt

        # Remove least important information first
        lines = prompt.split('\n')
        while current_tokens > max_tokens and len(lines) > 1:
            # Remove oldest market data
            lines.pop(-1)
            prompt = '\n'.join(lines)
            current_tokens = self.count_tokens(prompt)

        return prompt

# Cost tracking
class CostTracker:
    def __init__(self):
        self.daily_cost = 0.0
        self.monthly_cost = 0.0
        self.daily_limit = 5.0  # $5/day = $150/month (buffer)
        self.last_reset = datetime.now()

    async def track_request(self, input_tokens: int, output_tokens: int, model: str):
        """Track cost of LLM request"""

        # Model pricing (per 1M tokens)
        pricing = {
            'gpt-4o-mini': {'input': 0.150, 'output': 0.600},
            'claude-3-haiku': {'input': 0.250, 'output': 1.250},
            'gpt-4o': {'input': 2.500, 'output': 10.000},
        }

        rates = pricing.get(model, pricing['gpt-4o-mini'])

        cost = (input_tokens / 1_000_000 * rates['input'] +
                output_tokens / 1_000_000 * rates['output'])

        self.daily_cost += cost
        self.monthly_cost += cost

        # Check limits
        if self.daily_cost > self.daily_limit:
            logger.error(f"Daily cost limit exceeded: ${self.daily_cost:.2f}")
            await send_alert(f"CRITICAL: Daily LLM cost at ${self.daily_cost:.2f}")
            # Switch to cheaper model
            return 'claude-3-haiku'  # Cheaper fallback

        return model

    async def reset_daily_cost(self):
        """Reset daily cost (run at midnight)"""
        self.daily_cost = 0.0
        logger.info(f"Daily cost reset. Monthly total: ${self.monthly_cost:.2f}")

# Usage
prompt_builder = TokenOptimizedPromptBuilder()
cost_tracker = CostTracker()

async def make_llm_request(market_data, positions):
    system_prompt, user_prompt = prompt_builder.build_optimized_prompt(market_data, positions)

    model = 'gpt-4o-mini'

    response = await openrouter_client.chat(
        model=model,
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt}
        ]
    )

    # Track cost
    input_tokens = response['usage']['prompt_tokens']
    output_tokens = response['usage']['completion_tokens']

    next_model = await cost_tracker.track_request(input_tokens, output_tokens, model)

    return response, next_model
```

**Testing Strategy**:
- Monitor token usage in production
- Set up alerts at 80% of daily budget
- Test automatic model downgrade
- Verify prompt trimming doesn't break logic

---

## 3. Data & Database Gotchas

### 🔴 CRITICAL: TimescaleDB Connection Pool Exhaustion

**What Happens**:
- All database connections in pool are in use
- New requests wait indefinitely or timeout
- Trading cycle cannot complete
- System appears frozen

**Why It Matters**:
- Cannot record trades or update positions
- Data loss if trades execute but aren't recorded
- System recovery requires manual intervention

**Where It Occurs**:
- High concurrent load (multiple workers)
- Long-running queries block connections
- Connections not released after use
- Pool size too small for workload

**Mitigation Strategy**:
```python
import asyncpg
from contextlib import asynccontextmanager

class DatabasePool:
    def __init__(self):
        self.pool = None
        self.pool_size_min = 10
        self.pool_size_max = 50
        self.connection_timeout = 10  # seconds
        self.command_timeout = 30  # seconds

    async def initialize(self):
        """Initialize connection pool"""
        self.pool = await asyncpg.create_pool(
            database='trading_db',
            user='trading_user',
            password=os.getenv('DB_PASSWORD'),
            host='localhost',
            port=5432,
            min_size=self.pool_size_min,
            max_size=self.pool_size_max,
            command_timeout=self.command_timeout,
            max_queries=50000,  # Recycle after 50k queries
            max_inactive_connection_lifetime=300,  # Close idle after 5 min
        )

        logger.info(f"Database pool initialized: {self.pool_size_min}-{self.pool_size_max} connections")

    @asynccontextmanager
    async def acquire(self, timeout=None):
        """Acquire connection with timeout"""
        timeout = timeout or self.connection_timeout

        try:
            async with asyncio.timeout(timeout):
                async with self.pool.acquire() as conn:
                    yield conn
        except asyncio.TimeoutError:
            logger.error(f"Database connection timeout after {timeout}s")
            await send_alert("CRITICAL: Database connection pool exhausted")

            # Log pool stats
            await self.log_pool_stats()

            raise Exception("Database connection timeout - pool exhausted")

    async def log_pool_stats(self):
        """Log connection pool statistics"""
        stats = {
            'size': self.pool.get_size(),
            'free': self.pool.get_idle_size(),
            'in_use': self.pool.get_size() - self.pool.get_idle_size(),
            'max': self.pool_size_max
        }

        logger.warning(f"Pool stats: {stats}")

        if stats['free'] == 0:
            logger.error("Pool exhausted: no free connections")
            await send_alert(f"CRITICAL: DB pool exhausted ({stats})")

    async def execute_with_retry(self, query, *args, max_retries=3):
        """Execute query with connection retry"""
        for attempt in range(max_retries):
            try:
                async with self.acquire() as conn:
                    return await conn.fetch(query, *args)
            except asyncio.TimeoutError:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"DB query timeout, retry {attempt + 1}/{max_retries}")
                await asyncio.sleep(2 ** attempt)
            except Exception as e:
                logger.error(f"DB query error: {e}")
                raise

    async def close(self):
        """Close pool gracefully"""
        if self.pool:
            await self.pool.close()
            logger.info("Database pool closed")

# Global pool instance
db_pool = DatabasePool()

# Usage in trading cycle
async def record_trading_signal(signal):
    query = """
        INSERT INTO trading_signals (symbol, action, confidence, reasoning, created_at)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id
    """

    async with db_pool.acquire(timeout=5) as conn:
        signal_id = await conn.fetchval(
            query,
            signal['symbol'],
            signal['action'],
            signal['confidence'],
            signal['reasoning'],
            datetime.now()
        )

    return signal_id

# Monitoring task
async def monitor_db_pool():
    """Monitor pool health periodically"""
    while True:
        await asyncio.sleep(60)  # Every minute
        await db_pool.log_pool_stats()
```

**Testing Strategy**:
- Load test with concurrent requests exceeding pool size
- Verify timeout handling works correctly
- Test connection recycling after max_queries
- Validate monitoring alerts trigger

---

## 4. Risk Management Gotchas

### 🔴 CRITICAL: Stop-Loss Not Triggering During Flash Crash

**What Happens**:
- Market price gaps through stop-loss level
- Stop-loss order doesn't execute (price never touched stop level on order book)
- Position liquidated at much worse price
- Catastrophic loss exceeding risk parameters

**Why It Matters**:
- Risk management completely fails
- Losses far exceed intended stop-loss amount
- Can wipe out account in extreme cases
- Violates "100% adherence to stop-loss rules" requirement

**Where It Occurs**:
- Flash crashes (price drops 20%+ in seconds)
- Low liquidity assets during off-hours
- Exchange outages during volatile periods
- Network delays during execution

**Mitigation Strategy**:
```python
class RobustStopLossManager:
    def __init__(self):
        self.max_loss_per_position = 0.02  # 2% of position
        self.emergency_liquidation_threshold = 0.15  # 15% loss

    async def multi_layered_stop_loss(self, position):
        """Implement defense-in-depth for stop-losses"""

        # Layer 1: Exchange stop-loss order (primary)
        exchange_stop = await self.place_exchange_stop(position)

        # Layer 2: Application-level monitoring (backup)
        await self.start_app_level_monitor(position, exchange_stop)

        # Layer 3: Emergency liquidation (last resort)
        await self.start_emergency_monitor(position)

        return {
            'exchange_stop': exchange_stop,
            'app_monitor': True,
            'emergency_monitor': True
        }

    async def place_exchange_stop(self, position):
        """Place stop-loss on exchange"""
        stop_price = self.calculate_stop_price(position)

        try:
            order = await exchange.create_order(
                symbol=position['symbol'],
                type='stop_market',
                side='sell' if position['side'] == 'long' else 'buy',
                amount=position['size'],
                params={'stopPrice': stop_price}
            )

            logger.info(f"Exchange stop-loss placed: {position['symbol']} @ {stop_price}")
            return order

        except Exception as e:
            logger.error(f"Failed to place exchange stop: {e}")
            # Critical: cannot protect position
            await send_alert(f"CRITICAL: Failed to place stop-loss for {position['symbol']}")
            # Fallback: close position immediately
            await self.emergency_close_position(position, reason="stop_loss_failure")
            raise

    async def start_app_level_monitor(self, position, exchange_stop):
        """Monitor price and trigger stop if exchange fails"""

        async def monitor():
            stop_price = self.calculate_stop_price(position)
            check_interval = 2  # seconds (faster during volatile periods)

            while True:
                try:
                    # Check if position still exists
                    if not await self.position_exists(position):
                        logger.info(f"Position closed: {position['symbol']}")
                        break

                    # Get current price
                    ticker = await exchange.fetch_ticker(position['symbol'])
                    current_price = ticker['last']

                    # Check if stop should trigger
                    if self.should_trigger_stop(position, current_price, stop_price):
                        logger.warning(f"App-level stop triggered: {position['symbol']}")
                        await self.trigger_app_stop(position, current_price)
                        break

                    await asyncio.sleep(check_interval)

                except Exception as e:
                    logger.error(f"Error in app-level stop monitor: {e}")
                    await asyncio.sleep(5)

        # Start monitoring task
        asyncio.create_task(monitor())

    async def start_emergency_monitor(self, position):
        """Emergency liquidation if loss exceeds threshold"""

        async def monitor():
            while True:
                try:
                    # Check if position still exists
                    if not await self.position_exists(position):
                        break

                    # Calculate current loss
                    ticker = await exchange.fetch_ticker(position['symbol'])
                    current_price = ticker['last']

                    loss_pct = self.calculate_loss_pct(position, current_price)

                    # Emergency liquidation if loss exceeds threshold
                    if loss_pct > self.emergency_liquidation_threshold:
                        logger.critical(f"EMERGENCY LIQUIDATION: {position['symbol']} loss {loss_pct:.1%}")
                        await send_alert(f"CRITICAL: Emergency liquidation {position['symbol']} at {loss_pct:.1%} loss")
                        await self.emergency_close_position(position, reason="emergency_threshold")
                        break

                    await asyncio.sleep(1)  # Check every second for emergency

                except Exception as e:
                    logger.error(f"Error in emergency monitor: {e}")
                    await asyncio.sleep(5)

        asyncio.create_task(monitor())

    def calculate_stop_price(self, position):
        """Calculate stop-loss price"""
        entry_price = position['entry_price']
        max_loss_pct = self.max_loss_per_position

        if position['side'] == 'long':
            return entry_price * (1 - max_loss_pct)
        else:  # short
            return entry_price * (1 + max_loss_pct)

    def should_trigger_stop(self, position, current_price, stop_price):
        """Check if stop should trigger"""
        if position['side'] == 'long':
            return current_price <= stop_price
        else:  # short
            return current_price >= stop_price

    def calculate_loss_pct(self, position, current_price):
        """Calculate current loss percentage"""
        entry_price = position['entry_price']

        if position['side'] == 'long':
            return (entry_price - current_price) / entry_price
        else:  # short
            return (current_price - entry_price) / entry_price

    async def trigger_app_stop(self, position, current_price):
        """Trigger stop-loss at application level"""
        try:
            # Cancel exchange stop (if it didn't trigger)
            if position.get('exchange_stop_id'):
                try:
                    await exchange.cancel_order(position['exchange_stop_id'], position['symbol'])
                except:
                    pass  # May have already been cancelled/filled

            # Close position with market order
            await self.emergency_close_position(position, reason="app_stop_triggered")

        except Exception as e:
            logger.critical(f"Failed to trigger app-level stop: {e}")
            await send_alert(f"CRITICAL: Stop-loss execution failed for {position['symbol']}")

    async def emergency_close_position(self, position, reason):
        """Emergency position closure"""
        try:
            order = await exchange.create_order(
                symbol=position['symbol'],
                type='market',
                side='sell' if position['side'] == 'long' else 'buy',
                amount=position['size'],
                params={'reduceOnly': True}  # Prevent opening opposite position
            )

            logger.critical(f"Emergency close executed: {position['symbol']} reason={reason}")
            await send_alert(f"EMERGENCY CLOSE: {position['symbol']} - {reason}")

            return order

        except Exception as e:
            logger.critical(f"FAILED to emergency close {position['symbol']}: {e}")
            await send_alert(f"CRITICAL: Emergency close FAILED for {position['symbol']}")
            raise

# Usage
stop_manager = RobustStopLossManager()

async def open_position_with_protection(signal):
    # Enter position
    position = await execute_entry_order(signal)

    # Immediately set up multi-layered stop-loss
    protection = await stop_manager.multi_layered_stop_loss(position)

    # Record protection in database
    await db.update_position_protection(position['id'], protection)

    return position
```

**Testing Strategy**:
- Simulate flash crashes in testnet
- Test with deliberately delayed stop-loss orders
- Verify emergency liquidation triggers at threshold
- Test with exchange API failures during stop execution

---

## 5. Additional Critical Gotchas Summary

### 🔴 CRITICAL: Redis Failure Causing Task Queue Loss

**Mitigation**: Enable RDB + AOF persistence, implement task state recovery on startup

### 🔴 CRITICAL: Network Partition During Order Execution

**Mitigation**: Idempotency keys for orders, position reconciliation after recovery

### 🟡 HIGH: Celery Beat Clock Drift Causing Mistimed Cycles

**Mitigation**: Use external scheduler (cron) instead of Celery Beat for critical timing

### 🟡 HIGH: Funding Rate Costs Exceeding Profit

**Mitigation**: Monitor funding rates, close positions before funding time if unprofitable

### 🟡 HIGH: Liquidation Price Too Close to Entry

**Mitigation**: Validate liquidation price > 2× stop-loss distance before entry

### 🟢 MEDIUM: Indicator Calculation Errors on Insufficient Data

**Mitigation**: Require minimum 100 candles before trading, handle NaN gracefully

---

## 6. Testing Checklist for Gotchas

```
Before Production Deployment:

Exchange Integration:
[ ] Rate limit handling tested with deliberate violations
[ ] Partial fill reconciliation tested with small orders
[ ] WebSocket disconnection recovery tested
[ ] Exchange-specific order types verified for each exchange

LLM Integration:
[ ] Invalid JSON responses handled gracefully
[ ] Token usage monitored and within budget
[ ] Model fallback tested with API failures
[ ] Safe default (hold) activates when all LLMs fail

Database:
[ ] Connection pool exhaustion tested with high load
[ ] Query timeouts handled correctly
[ ] Connection recovery after database restart
[ ] TimescaleDB compression policies active

Risk Management:
[ ] Stop-loss triggers tested in flash crash simulation
[ ] Multi-layered protection tested with exchange failures
[ ] Emergency liquidation triggers at threshold
[ ] Position reconciliation after network partition

End-to-End:
[ ] Full trading cycle completes in <2 seconds (p95)
[ ] System recovers from all component failures within 3 minutes
[ ] Alerting system notifies on all critical issues
[ ] Monitoring dashboards show all key metrics
```

---

## 7. Incident Response Playbook

```
CRITICAL ALERT: Rate Limit Ban
1. Check exchange ban duration (usually 1-24 hours)
2. Close all positions via alternative exchange or API key
3. Review rate limit logs to identify root cause
4. Increase rateLimit parameter by 50%
5. Test in testnet before resuming live trading

CRITICAL ALERT: Invalid JSON from LLM
1. Check if affecting all models or specific model
2. Switch to backup model immediately
3. Review prompt for issues causing JSON failure
4. Monitor token usage (may indicate prompt corruption)
5. If persistent, enable safe default (hold all)

CRITICAL ALERT: Position Mismatch
1. Immediately stop all new orders
2. Fetch positions from exchange (source of truth)
3. Update database with exchange positions
4. Review order execution logs for root cause
5. Verify stop-losses are correctly placed
6. Resume trading only after reconciliation complete

CRITICAL ALERT: Stop-Loss Failure
1. IMMEDIATELY close position with market order
2. Review exchange logs for stop order status
3. Switch to app-level monitoring for all positions
4. Alert human operator for position oversight
5. Investigate why exchange stop failed
6. Consider reducing position sizes until resolved
```

---

**Next Document**: See `external-services-analysis.md` for detailed evaluation of exchange APIs, OpenRouter capabilities, and service-level agreements.
