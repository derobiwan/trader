# Bybit Testnet Integration Guide

**Version**: 1.0
**Last Updated**: 2025-10-27
**Target**: Trade Executor Implementation
**Exchange**: Bybit V5 API
**Library**: ccxt (Python)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Testnet Setup](#testnet-setup)
3. [CCXT Configuration](#ccxt-configuration)
4. [Order Execution](#order-execution)
5. [Position Management](#position-management)
6. [WebSocket Integration](#websocket-integration)
7. [Rate Limits](#rate-limits)
8. [Error Handling](#error-handling)
9. [Best Practices](#best-practices)
10. [Critical Gotchas](#critical-gotchas)
11. [Code Examples](#code-examples)

---

## Executive Summary

### Key Findings

- **Bybit API Version**: V5 (unified API for spot, derivatives, options)
- **CCXT Library**: Fully supports Bybit V5 with async operations
- **Symbol Format**: `'BTC/USDT:USDT'` for USDT perpetual futures
- **Testnet URL**: `api-testnet.bybit.com`
- **Rate Limit**: 600 requests per 5 seconds per IP (HTTP)
- **WebSocket**: Requires separate connections for public/private data

### Critical Success Factors

1. **Use `set_sandbox_mode(True)`** - Required for testnet
2. **Set `defaultType = 'swap'`** - Required for perpetual futures
3. **Enable Rate Limiting** - `enableRateLimit: True`
4. **Use Async Operations** - `ccxt.async_support` for production
5. **Implement Retry Logic** - Handle rate limits and network errors

---

## Testnet Setup

### 1. Account Registration

**URL**: https://testnet.bybit.com/

**Steps**:
1. Visit testnet.bybit.com
2. Click "Register" in top right corner
3. Register with email or phone number
4. Complete security verification
5. Verify email/phone with code

**Testnet Funding**:
- **Automatic**: 10,000 USDT + 1 BTC credited immediately to Spot Account
- **Additional Funding**: Request once every 24 hours via testnet interface
- **Important**: Testnet and mainnet are completely separate environments

### 2. API Key Generation

**URL**: https://testnet.bybit.com/app/user/api-management

**Steps**:
1. Navigate to API Management in testnet account
2. Click "Create New Key"
3. Set permissions:
   - ✓ Read-Write (for trading)
   - ✓ Contract Trading (for perpetual futures)
   - ✓ Spot Trading (if needed)
4. Set IP whitelist (optional, recommended for security)
5. Save API Key and Secret (Secret shown only once!)

**Permissions Required**:
```
Read-Write: Yes
Contract Trading: Yes (for perpetual futures)
Spot Trading: Optional
Withdraw: No (not needed for trading)
```

### 3. Testnet vs Mainnet Differences

| Feature | Testnet | Mainnet |
|---------|---------|---------|
| **Base URL** | `api-testnet.bybit.com` | `api.bybit.com` |
| **WebSocket** | `stream-testnet.bybit.com` | `stream.bybit.com` |
| **Funding** | Free test coins | Real money |
| **API Keys** | Separate from mainnet | Separate from testnet |
| **Data** | May not match real market | Real market data |
| **Performance** | May be slower | Production SLA |

**CRITICAL**: Never use mainnet API keys on testnet or vice versa!

---

## CCXT Configuration

### Basic Initialization

```python
import ccxt.async_support as ccxt

exchange = ccxt.bybit({
    'apiKey': 'YOUR_TESTNET_API_KEY',
    'secret': 'YOUR_TESTNET_SECRET',
    'enableRateLimit': True,  # CRITICAL: Enable built-in rate limiting
    'options': {
        'defaultType': 'swap',  # REQUIRED for perpetual futures
        'recvWindow': 10000,    # Adjust for clock sync (milliseconds)
    }
})

# CRITICAL: Enable testnet/sandbox mode
exchange.set_sandbox_mode(True)

# Load markets
await exchange.load_markets()
```

### Synchronous vs Asynchronous

**Asynchronous (Recommended for Production)**:
```python
import ccxt.async_support as ccxt
import asyncio

async def main():
    exchange = ccxt.bybit({
        'apiKey': 'YOUR_KEY',
        'secret': 'YOUR_SECRET',
        'enableRateLimit': True,
    })
    exchange.set_sandbox_mode(True)

    try:
        await exchange.load_markets()
        balance = await exchange.fetch_balance()
        print(balance)
    finally:
        await exchange.close()  # CRITICAL: Always close connection

asyncio.run(main())
```

**Synchronous (Simple Scripts Only)**:
```python
import ccxt

exchange = ccxt.bybit({
    'apiKey': 'YOUR_KEY',
    'secret': 'YOUR_SECRET',
    'enableRateLimit': True,
})
exchange.set_sandbox_mode(True)

exchange.load_markets()
balance = exchange.fetch_balance()
print(balance)
```

### Configuration Options

```python
exchange = ccxt.bybit({
    'apiKey': 'YOUR_KEY',
    'secret': 'YOUR_SECRET',
    'enableRateLimit': True,  # Enable automatic rate limiting
    'rateLimit': 100,  # Minimum milliseconds between requests (default: based on exchange)
    'timeout': 30000,  # Request timeout (milliseconds)
    'options': {
        'defaultType': 'swap',  # 'spot', 'swap', 'future'
        'defaultSettle': 'USDT',  # Settlement currency
        'recvWindow': 10000,  # Time window for request validity (ms)
        'adjustForTimeDifference': True,  # Auto-adjust for clock skew
    }
})
```

### Symbol Format

**USDT Perpetual Futures** (Linear):
```python
symbol = 'BTC/USDT:USDT'  # BTC perpetual, USDT-margined
symbol = 'ETH/USDT:USDT'  # ETH perpetual, USDT-margined
symbol = 'SOL/USDT:USDT'  # SOL perpetual, USDT-margined
```

**Format Breakdown**:
- `BTC/USDT` - Base/Quote pair
- `:USDT` - Settlement currency (indicates perpetual futures)

**Inverse Perpetual** (if needed):
```python
symbol = 'BTC/USD'  # BTC inverse perpetual (BTC-margined)
```

**Spot** (if needed):
```python
symbol = 'BTC/USDT'  # BTC spot trading
```

---

## Order Execution

### Market Orders

**Buy Market Order**:
```python
# Open long position
symbol = 'BTC/USDT:USDT'
amount = 0.001  # BTC quantity
side = 'buy'
order_type = 'market'

order = await exchange.create_order(
    symbol=symbol,
    type=order_type,
    side=side,
    amount=amount,
    params={}  # Additional parameters
)

print(f"Order ID: {order['id']}")
print(f"Status: {order['status']}")
```

**Sell Market Order**:
```python
# Open short position
order = await exchange.create_order(
    symbol='BTC/USDT:USDT',
    type='market',
    side='sell',
    amount=0.001
)
```

### Limit Orders

```python
# Buy limit order
symbol = 'BTC/USDT:USDT'
price = 89000  # Limit price
amount = 0.001

order = await exchange.create_order(
    symbol=symbol,
    type='limit',
    side='buy',
    amount=amount,
    price=price,
    params={
        'timeInForce': 'GTC',  # Good-Till-Cancel (default)
        # 'timeInForce': 'IOC',  # Immediate-Or-Cancel
        # 'timeInForce': 'FOK',  # Fill-Or-Kill
    }
)
```

### Market Orders with Leverage

**Set Leverage First**:
```python
# IMPORTANT: Set leverage before placing orders
symbol = 'BTC/USDT:USDT'
leverage = 10

# CCXT doesn't have direct set_leverage method for Bybit
# Use exchange-specific params or direct API call
params = {
    'leverage': leverage  # Some exchanges support this
}

# Alternative: Use pybit library for leverage setting
# Or use exchange.private_post_v5_position_set_leverage() directly
```

**Using pybit for Leverage** (Recommended):
```python
from pybit.unified_trading import HTTP

session = HTTP(
    testnet=True,
    api_key="YOUR_KEY",
    api_secret="YOUR_SECRET",
)

# Set leverage
result = session.set_leverage(
    category="linear",
    symbol="BTCUSDT",
    buyLeverage="10",
    sellLeverage="10",
)
print(result)
```

**Then place order**:
```python
# Order with leverage (leverage must be set first)
order = await exchange.create_order(
    symbol='BTC/USDT:USDT',
    type='market',
    side='buy',
    amount=0.01,  # 0.01 BTC with 10x leverage = ~$9,000 position
)
```

### Stop-Loss Orders

**Method 1: Set TP/SL When Opening Position**:
```python
order = await exchange.create_order(
    symbol='BTC/USDT:USDT',
    type='market',
    side='buy',
    amount=0.001,
    params={
        'stopLoss': 88000,  # Stop-loss trigger price
        'takeProfit': 92000,  # Take-profit trigger price
        'slTriggerBy': 'MarkPrice',  # 'LastPrice', 'MarkPrice', 'IndexPrice'
        'tpTriggerBy': 'MarkPrice',
    }
)
```

**Method 2: Set TP/SL on Existing Position**:
```python
# Use exchange-specific endpoint
symbol = 'BTC/USDT:USDT'

# This requires direct API call (not standard ccxt method)
# Use pybit or custom implementation
from pybit.unified_trading import HTTP

session = HTTP(testnet=True, api_key="KEY", api_secret="SECRET")

result = session.set_trading_stop(
    category="linear",
    symbol="BTCUSDT",
    stopLoss="88000",
    takeProfit="92000",
    tpTriggerBy="MarkPrice",
    slTriggerBy="MarkPrice",
    positionIdx=0,  # 0 = One-Way Mode, 1 = Long, 2 = Short (Hedge Mode)
)
```

**Method 3: Separate Stop Order**:
```python
# Place standalone stop-loss order
stop_order = await exchange.create_order(
    symbol='BTC/USDT:USDT',
    type='stop_market',  # Stop market order
    side='sell',  # Opposite of position
    amount=0.001,
    params={
        'stopPrice': 88000,  # Trigger price
        'triggerBy': 'MarkPrice',
        'reduceOnly': True,  # CRITICAL: Only reduces position
    }
)
```

### Order Types Summary

| Order Type | Use Case | Parameters |
|------------|----------|------------|
| `market` | Immediate execution | `symbol, side, amount` |
| `limit` | Price control | `symbol, side, amount, price` |
| `stop_market` | Stop-loss trigger | `symbol, side, amount, stopPrice` |
| `stop_limit` | Stop with limit price | `symbol, side, amount, stopPrice, price` |
| `take_profit_market` | Take-profit trigger | `symbol, side, amount, stopPrice` |
| `take_profit_limit` | Take-profit with limit | `symbol, side, amount, stopPrice, price` |

### Order Parameters

**Common Parameters**:
```python
params = {
    # Time in force
    'timeInForce': 'GTC',  # Good-Till-Cancel, IOC, FOK

    # Position control
    'reduceOnly': True,  # Only reduces position, doesn't flip
    'closeOnTrigger': False,  # Deprecated, use reduceOnly

    # Position mode (Hedge Mode only)
    'positionIdx': 0,  # 0=One-Way, 1=Long, 2=Short

    # Stop orders
    'stopPrice': 89000,  # Trigger price
    'triggerBy': 'MarkPrice',  # LastPrice, MarkPrice, IndexPrice

    # TP/SL
    'stopLoss': 88000,
    'takeProfit': 92000,
    'slTriggerBy': 'MarkPrice',
    'tpTriggerBy': 'MarkPrice',

    # Leverage (set separately, not in order)
    # 'leverage': 10,  # Not directly supported in ccxt create_order

    # Order linking
    'orderLinkId': 'my-custom-id-123',  # Custom ID (max 36 chars)
}
```

### Checking Order Status

```python
# Fetch specific order
order_id = 'order-id-from-create'
symbol = 'BTC/USDT:USDT'

order = await exchange.fetch_order(order_id, symbol)
print(f"Status: {order['status']}")  # open, closed, canceled

# Fetch open orders
open_orders = await exchange.fetch_open_orders(symbol)
for order in open_orders:
    print(f"Order {order['id']}: {order['side']} {order['amount']} @ {order['price']}")

# Fetch closed orders
closed_orders = await exchange.fetch_closed_orders(symbol, limit=10)
```

### Canceling Orders

```python
# Cancel single order
order_id = 'order-id'
symbol = 'BTC/USDT:USDT'

canceled = await exchange.cancel_order(order_id, symbol)
print(f"Canceled order: {canceled['id']}")

# Cancel all orders for symbol
result = await exchange.cancel_all_orders(symbol)
print(f"Canceled {len(result)} orders")
```

---

## Position Management

### Fetching Positions

**Fetch All Positions**:
```python
# Fetch all open positions
positions = await exchange.fetch_positions()

for position in positions:
    if float(position['contracts']) > 0:  # Only show open positions
        print(f"Symbol: {position['symbol']}")
        print(f"Side: {position['side']}")  # long or short
        print(f"Size: {position['contracts']}")
        print(f"Entry Price: {position['entryPrice']}")
        print(f"Current Price: {position['markPrice']}")
        print(f"Unrealized P&L: {position['unrealizedPnl']}")
        print(f"Leverage: {position['leverage']}")
        print("---")
```

**Fetch Specific Symbol Positions**:
```python
# Fetch position for specific symbol
symbols = ['BTC/USDT:USDT']
positions = await exchange.fetch_positions(symbols)

if positions:
    position = positions[0]
    print(f"Position size: {position['contracts']}")
    print(f"Entry price: {position['entryPrice']}")
```

**Position Data Structure**:
```python
{
    'id': 'position-id',
    'symbol': 'BTC/USDT:USDT',
    'timestamp': 1698450000000,
    'datetime': '2023-10-27T12:00:00.000Z',
    'isolated': False,  # Cross margin if False
    'hedged': False,  # One-way mode
    'side': 'long',  # 'long' or 'short'
    'contracts': 0.1,  # Position size in contracts
    'contractSize': 1,
    'entryPrice': 90000,
    'markPrice': 90500,
    'notional': 9050,  # Position value in USDT
    'leverage': 10,
    'collateral': 905,  # Margin used
    'initialMargin': 905,
    'maintenanceMargin': 45.25,
    'initialMarginPercentage': 0.1,
    'maintenanceMarginPercentage': 0.005,
    'unrealizedPnl': 50,  # Unrealized profit/loss
    'liquidationPrice': 81500,
    'marginMode': 'cross',  # 'cross' or 'isolated'
    'percentage': 5.52,  # ROI percentage
}
```

### Closing Positions

**Method 1: Market Order with reduce_only**:
```python
# Close long position (sell with reduce_only)
symbol = 'BTC/USDT:USDT'
position_size = 0.001  # BTC amount

close_order = await exchange.create_order(
    symbol=symbol,
    type='market',
    side='sell',  # Opposite of position direction
    amount=position_size,
    params={'reduceOnly': True}  # CRITICAL: Prevents opening opposite position
)

print(f"Position closed: {close_order['id']}")
```

**Method 2: Fetch Position Then Close**:
```python
async def close_all_positions(symbol):
    """Close all positions for a symbol"""
    positions = await exchange.fetch_positions([symbol])

    for position in positions:
        size = float(position['contracts'])
        if size == 0:
            continue

        side = position['side']  # 'long' or 'short'
        close_side = 'sell' if side == 'long' else 'buy'

        close_order = await exchange.create_order(
            symbol=symbol,
            type='market',
            side=close_side,
            amount=size,
            params={'reduceOnly': True}
        )

        print(f"Closed {side} position of {size} {symbol}")
        return close_order

# Usage
await close_all_positions('BTC/USDT:USDT')
```

**Method 3: Close via Position API** (pybit):
```python
from pybit.unified_trading import HTTP

session = HTTP(testnet=True, api_key="KEY", api_secret="SECRET")

# Get positions
positions = session.get_positions(category="linear", symbol="BTCUSDT")

# Close position
for position in positions['result']['list']:
    if float(position['size']) > 0:
        side = 'sell' if position['side'] == 'Buy' else 'buy'

        result = session.place_order(
            category="linear",
            symbol="BTCUSDT",
            side=side.capitalize(),
            orderType="Market",
            qty=position['size'],
            reduceOnly=True,
        )
        print(f"Closed position: {result}")
```

### Setting Leverage

**Using pybit** (Recommended):
```python
from pybit.unified_trading import HTTP

session = HTTP(testnet=True, api_key="KEY", api_secret="SECRET")

result = session.set_leverage(
    category="linear",
    symbol="BTCUSDT",
    buyLeverage="10",  # Leverage for long positions
    sellLeverage="10",  # Leverage for short positions
)

print(result)
# {'retCode': 0, 'retMsg': 'OK', ...}
```

**Using CCXT (Direct API)**:
```python
# CCXT doesn't have unified set_leverage for Bybit
# Use private endpoint directly
params = {
    'category': 'linear',
    'symbol': 'BTCUSDT',
    'buyLeverage': '10',
    'sellLeverage': '10',
}

# This is exchange-specific, not unified
# Better to use pybit for this
```

### Switching Margin Mode

**Cross Margin** (default):
- Uses all available balance as margin
- Positions share margin
- Lower liquidation risk but higher risk of total loss

**Isolated Margin**:
- Each position has dedicated margin
- Positions independent
- Limited loss per position

```python
# Using pybit to switch margin mode
session = HTTP(testnet=True, api_key="KEY", api_secret="SECRET")

# Switch to isolated margin
result = session.switch_margin_mode(
    category="linear",
    symbol="BTCUSDT",
    tradeMode=1,  # 0 = Cross, 1 = Isolated
    buyLeverage="10",
    sellLeverage="10",
)
```

### Fetching Balance

```python
# Fetch balance
balance = await exchange.fetch_balance()

# Total balance (all currencies)
print(f"Total: {balance['total']}")

# USDT balance
usdt = balance['USDT']
print(f"USDT Free: {usdt['free']}")
print(f"USDT Used: {usdt['used']}")
print(f"USDT Total: {usdt['total']}")

# Example output:
# {
#     'USDT': {
#         'free': 9500.00,
#         'used': 500.00,
#         'total': 10000.00
#     },
#     'BTC': {
#         'free': 0.95,
#         'used': 0.05,
#         'total': 1.0
#     },
#     ...
# }
```

### Position Monitoring

```python
async def monitor_position(symbol, entry_price, stop_loss, take_profit):
    """Monitor position and log status"""
    while True:
        positions = await exchange.fetch_positions([symbol])

        if not positions or float(positions[0]['contracts']) == 0:
            print("Position closed")
            break

        position = positions[0]
        current_price = float(position['markPrice'])
        unrealized_pnl = float(position['unrealizedPnl'])

        print(f"Current Price: {current_price}")
        print(f"Unrealized P&L: {unrealized_pnl} USDT")

        # Check stop-loss
        if position['side'] == 'long' and current_price <= stop_loss:
            print(f"Stop-loss triggered at {current_price}")
            await close_position(symbol)
            break

        # Check take-profit
        if position['side'] == 'long' and current_price >= take_profit:
            print(f"Take-profit triggered at {current_price}")
            await close_position(symbol)
            break

        await asyncio.sleep(5)  # Check every 5 seconds
```

---

## WebSocket Integration

### WebSocket Overview

Bybit V5 WebSocket supports:
- **Public streams**: Market data, orderbook, trades (no auth required)
- **Private streams**: Account updates, positions, orders (auth required)
- **Trade stream**: Order execution (auth required)

### WebSocket Endpoints

**Testnet**:
```python
# Public streams
public_linear = 'wss://stream-testnet.bybit.com/v5/public/linear'  # USDT perpetual
public_inverse = 'wss://stream-testnet.bybit.com/v5/public/inverse'  # Inverse perpetual
public_spot = 'wss://stream-testnet.bybit.com/v5/public/spot'

# Private streams
private = 'wss://stream-testnet.bybit.com/v5/private'

# Trade stream
trade = 'wss://stream-testnet.bybit.com/v5/trade'
```

**Mainnet**:
```python
public_linear = 'wss://stream.bybit.com/v5/public/linear'
private = 'wss://stream.bybit.com/v5/private'
trade = 'wss://stream.bybit.com/v5/trade'
```

### Using pybit WebSocket

**Public Stream Example** (No Authentication):
```python
from pybit.unified_trading import WebSocket
from time import sleep

# Initialize WebSocket
ws = WebSocket(
    testnet=True,
    channel_type="linear",  # 'linear', 'inverse', 'spot', 'option'
)

# Define callback
def handle_message(message):
    print(f"Received: {message}")

# Subscribe to trade stream
ws.trade_stream(
    symbol="BTCUSDT",
    callback=handle_message
)

# Subscribe to orderbook
ws.orderbook_stream(
    depth=1,  # 1, 50, 200, 500
    symbol="BTCUSDT",
    callback=handle_message
)

# Subscribe to kline/candlestick
ws.kline_stream(
    interval="1",  # 1, 3, 5, 15, 30, 60, 120, 240, 360, 720, D, W, M
    symbol="BTCUSDT",
    callback=handle_message
)

# Keep connection alive
while True:
    sleep(1)
```

**Private Stream Example** (Authentication Required):
```python
from pybit.unified_trading import WebSocket

# Initialize private WebSocket
ws = WebSocket(
    testnet=True,
    channel_type="private",
    api_key="YOUR_KEY",
    api_secret="YOUR_SECRET",
)

# Position updates
def handle_position(message):
    print(f"Position update: {message}")

ws.position_stream(callback=handle_position)

# Order updates
def handle_order(message):
    print(f"Order update: {message}")

ws.order_stream(callback=handle_order)

# Execution updates
def handle_execution(message):
    print(f"Execution: {message}")

ws.execution_stream(callback=handle_execution)

# Wallet updates
def handle_wallet(message):
    print(f"Wallet update: {message}")

ws.wallet_stream(callback=handle_wallet)

# Keep running
while True:
    sleep(1)
```

### WebSocket Message Format

**Trade Stream**:
```json
{
    "topic": "publicTrade.BTCUSDT",
    "type": "snapshot",
    "ts": 1698450000000,
    "data": [
        {
            "T": 1698450000123,
            "s": "BTCUSDT",
            "S": "Buy",
            "v": "0.001",
            "p": "90000.00",
            "L": "PlusTick",
            "i": "trade-id",
            "BT": false
        }
    ]
}
```

**Orderbook Stream**:
```json
{
    "topic": "orderbook.1.BTCUSDT",
    "type": "snapshot",
    "ts": 1698450000000,
    "data": {
        "s": "BTCUSDT",
        "b": [["89950.00", "1.5"]],  # bids [price, size]
        "a": [["90050.00", "2.3"]],  # asks [price, size]
        "u": 123456,
        "seq": 789012
    }
}
```

**Position Update**:
```json
{
    "topic": "position",
    "creationTime": 1698450000000,
    "data": [
        {
            "symbol": "BTCUSDT",
            "side": "Buy",
            "size": "0.01",
            "positionValue": "900",
            "entryPrice": "90000",
            "tradeMode": 0,
            "positionStatus": "Normal",
            "leverage": "10",
            "markPrice": "90100",
            "liqPrice": "81000",
            "bustPrice": "80500",
            "unrealisedPnl": "1",
            "cumRealisedPnl": "0"
        }
    ]
}
```

### WebSocket Heartbeat

pybit handles heartbeat automatically. For custom implementations:

```python
import websocket
import json
import time

def on_message(ws, message):
    data = json.loads(message)

    # Handle pong response
    if data.get('op') == 'pong':
        print("Pong received")
    else:
        print(f"Message: {data}")

def send_ping(ws):
    """Send ping every 20 seconds"""
    while True:
        time.sleep(20)
        ws.send(json.dumps({"op": "ping"}))

# WebSocket connection
ws = websocket.WebSocketApp(
    "wss://stream-testnet.bybit.com/v5/public/linear",
    on_message=on_message
)

# Start ping thread
import threading
ping_thread = threading.Thread(target=send_ping, args=(ws,))
ping_thread.daemon = True
ping_thread.start()

ws.run_forever()
```

### Reconnection Strategy

```python
import websocket
import time

def create_websocket(url):
    """Create WebSocket with auto-reconnect"""
    def on_error(ws, error):
        print(f"Error: {error}")

    def on_close(ws, close_status_code, close_msg):
        print(f"Connection closed. Reconnecting in 5 seconds...")
        time.sleep(5)
        create_websocket(url)  # Reconnect

    def on_open(ws):
        print("Connection opened")
        # Subscribe to topics
        subscribe_msg = {
            "op": "subscribe",
            "args": ["publicTrade.BTCUSDT"]
        }
        ws.send(json.dumps(subscribe_msg))

    def on_message(ws, message):
        print(f"Message: {message}")

    ws = websocket.WebSocketApp(
        url,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
        on_open=on_open
    )

    ws.run_forever()

# Start
create_websocket("wss://stream-testnet.bybit.com/v5/public/linear")
```

---

## Rate Limits

### HTTP Rate Limits

**IP-Based Limit**:
- **Limit**: 600 requests per 5 seconds per IP
- **Error**: 403 Forbidden when exceeded
- **Ban**: 10 minutes automatic ban
- **Recovery**: Automatic after ban period

**Per-Endpoint Limits**:
Rate limits vary by endpoint and account type (Classic, UTA Pro, etc.)

**Common Limits**:
- **Market Data**: 50-120 requests/second
- **Trading**: 10-50 requests/second (varies by account type)
- **Account**: 5-10 requests/second
- **Position**: 10-50 requests/second

**Rate Limit Headers**:
```
X-Bapi-Limit-Status: 45         # Remaining requests
X-Bapi-Limit: 50                # Total limit
X-Bapi-Limit-Reset-Timestamp: 1698450000  # Reset time
```

**Error Response**:
```json
{
    "retCode": 10006,
    "retMsg": "Too many visits!"
}
```

### WebSocket Rate Limits

**Connection Limits**:
- **Max Connections**: 500 per 5 minutes per IP
- **Total Connections**: 1,000 per IP (across all market types)
- **Subscriptions**: Up to 21,000 characters in args array

**Best Practices**:
- Maintain persistent connections
- Avoid frequent connect/disconnect
- Use ping/pong for keepalive
- Batch subscriptions in single connection

### Rate Limit Handling

**CCXT Built-in Rate Limiting**:
```python
exchange = ccxt.bybit({
    'enableRateLimit': True,  # Automatic rate limiting
    'rateLimit': 100,  # Minimum ms between requests (override default)
})
```

**Manual Rate Limiting**:
```python
import asyncio
import time

class RateLimiter:
    def __init__(self, max_requests, time_window):
        self.max_requests = max_requests
        self.time_window = time_window  # seconds
        self.requests = []

    async def wait_if_needed(self):
        now = time.time()

        # Remove old requests outside time window
        self.requests = [
            req_time for req_time in self.requests
            if now - req_time < self.time_window
        ]

        # Check if limit reached
        if len(self.requests) >= self.max_requests:
            sleep_time = self.time_window - (now - self.requests[0])
            if sleep_time > 0:
                print(f"Rate limit reached. Sleeping {sleep_time:.2f}s")
                await asyncio.sleep(sleep_time)
                self.requests = []

        self.requests.append(now)

# Usage
limiter = RateLimiter(max_requests=50, time_window=1)  # 50 req/sec

async def make_request():
    await limiter.wait_if_needed()
    # Make API request
    result = await exchange.fetch_ticker('BTC/USDT:USDT')
    return result
```

**Retry with Exponential Backoff**:
```python
import asyncio

async def fetch_with_retry(func, max_retries=3, base_delay=1):
    """Retry function with exponential backoff"""
    for attempt in range(max_retries):
        try:
            return await func()
        except ccxt.RateLimitExceeded as e:
            if attempt == max_retries - 1:
                raise

            delay = base_delay * (2 ** attempt)
            print(f"Rate limit exceeded. Retry {attempt + 1}/{max_retries} in {delay}s")
            await asyncio.sleep(delay)
        except Exception as e:
            print(f"Error: {e}")
            raise

# Usage
async def fetch_ticker():
    return await exchange.fetch_ticker('BTC/USDT:USDT')

ticker = await fetch_with_retry(fetch_ticker)
```

### Rate Limit Best Practices

1. **Enable Built-in Rate Limiting**:
   ```python
   exchange = ccxt.bybit({'enableRateLimit': True})
   ```

2. **Batch Operations**:
   ```python
   # Bad: Multiple separate requests
   for symbol in symbols:
       await exchange.fetch_ticker(symbol)

   # Good: Single batch request
   tickers = await exchange.fetch_tickers(symbols)
   ```

3. **Use WebSocket for Real-time Data**:
   - REST API for infrequent operations (orders, positions)
   - WebSocket for frequent updates (prices, orderbook)

4. **Cache Non-critical Data**:
   ```python
   import time

   class CachedExchange:
       def __init__(self, exchange, cache_duration=60):
           self.exchange = exchange
           self.cache = {}
           self.cache_duration = cache_duration

       async def fetch_ticker(self, symbol):
           now = time.time()
           if symbol in self.cache:
               cached_data, cached_time = self.cache[symbol]
               if now - cached_time < self.cache_duration:
                   return cached_data

           data = await self.exchange.fetch_ticker(symbol)
           self.cache[symbol] = (data, now)
           return data
   ```

5. **Monitor Rate Limit Headers**:
   ```python
   response = await exchange.fetch_ticker('BTC/USDT:USDT')

   # Check rate limit headers (if available)
   if hasattr(exchange, 'last_http_response'):
       headers = exchange.last_http_response.headers
       remaining = headers.get('X-Bapi-Limit-Status')
       print(f"Requests remaining: {remaining}")
   ```

---

## Error Handling

### Common Error Codes

#### Authentication Errors

| Code | Message | Cause | Solution |
|------|---------|-------|----------|
| 401 | Invalid request | Invalid API key | Check API key is correct and for testnet |
| 10003 | Invalid API key | Wrong environment (testnet vs mainnet) | Use correct API keys for environment |
| 10004 | Invalid signature | Signature generation error | Check secret key and signature algorithm |
| 10005 | Permission denied | Insufficient API permissions | Enable required permissions in API settings |
| 10009 | IP banned | Too many failed requests | Wait for ban to lift (10 min), check IP whitelist |
| 10010 | Unmatched IP | IP not whitelisted | Add IP to whitelist or remove IP restriction |

#### Rate Limiting Errors

| Code | Message | Cause | Solution |
|------|---------|-------|----------|
| 429 | System frequency protection | Too many requests | Implement exponential backoff |
| 10006 | Too many visits | Exceeded API rate limit | Enable rate limiting, reduce request frequency |
| 10429 | WebSocket frequency protection | Too many WS connections | Reduce connection frequency |
| 20003 | Too frequent requests | High request rate in session | Add delays between requests |

#### Trading Errors

| Code | Message | Cause | Solution |
|------|---------|-------|----------|
| 110003 | Order price exceeds range | Price too far from market | Check price limits for symbol |
| 110004 | Insufficient wallet balance | Not enough funds | Add funds or reduce order size |
| 110007 | Insufficient available balance | Balance locked in orders | Cancel orders or add funds |
| 110012 | Insufficient available balance | Margin insufficient | Reduce leverage or add margin |
| 110014 | Insufficient available balance for margin | Cannot add margin | Close positions or add funds |
| 110016 | Exceeds risk limit | Position too large for risk tier | Increase risk limit or reduce size |
| 110017 | Reduce-only rule not satisfied | Wrong direction or size | Check position side and size |
| 110019 | Invalid order ID | Order ID format wrong | Use correct ID format |
| 110020 | Too many active orders | >500 active orders | Cancel some orders |
| 110021 | Exceeds position limit | Open interest limit reached | Close positions or reduce size |
| 110024 | Cannot switch position mode | Open positions exist | Close positions first |
| 110028 | Cannot switch mode | Open orders exist | Cancel orders first |
| 110030 | Duplicate orderId | Order ID already used | Use unique order IDs |
| 110090 | Position may exceed max | Leverage too high | Reduce leverage |
| 170131 | Balance insufficient | Not enough balance | Add funds |
| 170141 | Duplicate clientOrderId | Client ID already used | Use unique client IDs |
| 176015 | Insufficient available balance | Margin insufficient | Add margin or reduce position |

### Error Handling Patterns

#### Basic Try-Catch

```python
import ccxt

try:
    order = await exchange.create_order(
        symbol='BTC/USDT:USDT',
        type='market',
        side='buy',
        amount=0.001
    )
    print(f"Order created: {order['id']}")

except ccxt.InsufficientFunds as e:
    print(f"Insufficient funds: {e}")
    # Handle: Wait for funds or reduce order size

except ccxt.InvalidOrder as e:
    print(f"Invalid order: {e}")
    # Handle: Check order parameters

except ccxt.RateLimitExceeded as e:
    print(f"Rate limit exceeded: {e}")
    # Handle: Wait and retry

except ccxt.NetworkError as e:
    print(f"Network error: {e}")
    # Handle: Retry with backoff

except ccxt.ExchangeError as e:
    print(f"Exchange error: {e}")
    # Handle: Log and investigate

except Exception as e:
    print(f"Unexpected error: {e}")
    # Handle: Log and alert
```

#### Comprehensive Error Handler

```python
import ccxt
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def execute_order_safe(
    exchange,
    symbol,
    order_type,
    side,
    amount,
    price=None,
    params=None,
    max_retries=3
):
    """Execute order with comprehensive error handling"""

    for attempt in range(max_retries):
        try:
            order = await exchange.create_order(
                symbol=symbol,
                type=order_type,
                side=side,
                amount=amount,
                price=price,
                params=params or {}
            )

            logger.info(f"Order executed: {order['id']}")
            return {'success': True, 'order': order}

        except ccxt.InsufficientFunds as e:
            logger.error(f"Insufficient funds: {e}")
            return {
                'success': False,
                'error': 'insufficient_funds',
                'message': str(e),
                'retry': False
            }

        except ccxt.InvalidOrder as e:
            logger.error(f"Invalid order: {e}")
            # Extract error code if available
            error_code = getattr(e, 'code', None)

            if error_code == 110017:  # Reduce-only not satisfied
                return {
                    'success': False,
                    'error': 'reduce_only_violation',
                    'message': 'No position to reduce',
                    'retry': False
                }

            return {
                'success': False,
                'error': 'invalid_order',
                'message': str(e),
                'retry': False
            }

        except ccxt.RateLimitExceeded as e:
            if attempt < max_retries - 1:
                delay = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                logger.warning(f"Rate limit exceeded. Retry {attempt + 1}/{max_retries} in {delay}s")
                await asyncio.sleep(delay)
                continue
            else:
                return {
                    'success': False,
                    'error': 'rate_limit',
                    'message': 'Max retries exceeded',
                    'retry': True
                }

        except ccxt.NetworkError as e:
            if attempt < max_retries - 1:
                delay = 1
                logger.warning(f"Network error. Retry {attempt + 1}/{max_retries} in {delay}s")
                await asyncio.sleep(delay)
                continue
            else:
                return {
                    'success': False,
                    'error': 'network_error',
                    'message': str(e),
                    'retry': True
                }

        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error: {e}")
            return {
                'success': False,
                'error': 'exchange_error',
                'message': str(e),
                'retry': False
            }

        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return {
                'success': False,
                'error': 'unexpected_error',
                'message': str(e),
                'retry': False
            }

    return {
        'success': False,
        'error': 'max_retries',
        'message': 'Maximum retries exceeded',
        'retry': True
    }

# Usage
result = await execute_order_safe(
    exchange=exchange,
    symbol='BTC/USDT:USDT',
    order_type='market',
    side='buy',
    amount=0.001
)

if result['success']:
    print(f"Order successful: {result['order']['id']}")
else:
    print(f"Order failed: {result['error']} - {result['message']}")
    if result['retry']:
        print("Consider retrying later")
```

#### Error Recovery Strategies

```python
class OrderExecutor:
    def __init__(self, exchange, max_retries=3):
        self.exchange = exchange
        self.max_retries = max_retries
        self.logger = logging.getLogger(__name__)

    async def execute_with_recovery(self, symbol, side, amount, **kwargs):
        """Execute order with automatic recovery"""

        # Check balance first
        balance_ok = await self._check_balance(symbol, amount)
        if not balance_ok:
            return {'success': False, 'error': 'insufficient_balance'}

        # Check position limits
        position_ok = await self._check_position_limits(symbol, amount)
        if not position_ok:
            return {'success': False, 'error': 'position_limit'}

        # Execute order
        result = await execute_order_safe(
            self.exchange,
            symbol,
            'market',
            side,
            amount,
            **kwargs
        )

        # Verify execution
        if result['success']:
            verified = await self._verify_order(result['order']['id'], symbol)
            if not verified:
                self.logger.error("Order verification failed")
                result['verified'] = False

        return result

    async def _check_balance(self, symbol, amount):
        """Check if sufficient balance for order"""
        try:
            balance = await self.exchange.fetch_balance()
            # Calculate required margin
            ticker = await self.exchange.fetch_ticker(symbol)
            price = ticker['last']
            required = amount * price / 10  # Assuming 10x leverage

            available = balance['USDT']['free']
            return available >= required

        except Exception as e:
            self.logger.error(f"Balance check failed: {e}")
            return False

    async def _check_position_limits(self, symbol, amount):
        """Check position limits"""
        try:
            positions = await self.exchange.fetch_positions([symbol])
            # Check if adding this amount would exceed limits
            # This is simplified - actual implementation needs position sizing logic
            return True

        except Exception as e:
            self.logger.error(f"Position limit check failed: {e}")
            return False

    async def _verify_order(self, order_id, symbol):
        """Verify order was executed"""
        try:
            await asyncio.sleep(1)  # Wait for exchange to process
            order = await self.exchange.fetch_order(order_id, symbol)
            return order['status'] in ['closed', 'filled']

        except Exception as e:
            self.logger.error(f"Order verification failed: {e}")
            return False

# Usage
executor = OrderExecutor(exchange)
result = await executor.execute_with_recovery(
    symbol='BTC/USDT:USDT',
    side='buy',
    amount=0.001
)
```

---

## Best Practices

### 1. Connection Management

```python
import ccxt.async_support as ccxt
import asyncio

class BybitClient:
    def __init__(self, api_key, secret, testnet=True):
        self.exchange = ccxt.bybit({
            'apiKey': api_key,
            'secret': secret,
            'enableRateLimit': True,
            'options': {'defaultType': 'swap'}
        })

        if testnet:
            self.exchange.set_sandbox_mode(True)

        self._initialized = False

    async def initialize(self):
        """Initialize exchange connection"""
        if not self._initialized:
            await self.exchange.load_markets()
            self._initialized = True

    async def close(self):
        """Close exchange connection"""
        if self._initialized:
            await self.exchange.close()
            self._initialized = False

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

# Usage with context manager
async def main():
    async with BybitClient(api_key="KEY", secret="SECRET") as client:
        balance = await client.exchange.fetch_balance()
        print(balance)

asyncio.run(main())
```

### 2. Position Sizing

```python
class PositionSizer:
    def __init__(self, exchange, max_position_pct=0.1):
        self.exchange = exchange
        self.max_position_pct = max_position_pct  # 10% of balance

    async def calculate_position_size(self, symbol, risk_pct=0.02):
        """
        Calculate safe position size

        Args:
            symbol: Trading pair
            risk_pct: Risk per trade (default 2% of balance)

        Returns:
            Position size in base currency
        """
        # Get balance
        balance = await self.exchange.fetch_balance()
        total_balance = balance['USDT']['total']

        # Get current price
        ticker = await self.exchange.fetch_ticker(symbol)
        current_price = ticker['last']

        # Calculate max position value
        max_position_value = total_balance * self.max_position_pct

        # Calculate position size
        position_size = max_position_value / current_price

        # Round to exchange precision
        market = self.exchange.market(symbol)
        position_size = self.exchange.amount_to_precision(symbol, position_size)

        return float(position_size)

# Usage
sizer = PositionSizer(exchange, max_position_pct=0.1)
size = await sizer.calculate_position_size('BTC/USDT:USDT')
print(f"Position size: {size} BTC")
```

### 3. Order Validation

```python
async def validate_order(exchange, symbol, side, amount, price=None):
    """Validate order before execution"""

    # Get market info
    market = exchange.market(symbol)

    # Check minimum amount
    if 'limits' in market and 'amount' in market['limits']:
        min_amount = market['limits']['amount']['min']
        if amount < min_amount:
            return False, f"Amount {amount} below minimum {min_amount}"

    # Check price (for limit orders)
    if price is not None:
        ticker = await exchange.fetch_ticker(symbol)
        current_price = ticker['last']

        # Check if price is within reasonable range (e.g., ±10%)
        if abs(price - current_price) / current_price > 0.1:
            return False, f"Price {price} too far from market {current_price}"

    # Check balance
    balance = await exchange.fetch_balance()
    ticker = await exchange.fetch_ticker(symbol)
    required_margin = (amount * ticker['last']) / 10  # Assuming 10x leverage

    if balance['USDT']['free'] < required_margin:
        return False, "Insufficient balance"

    return True, "Order valid"

# Usage
valid, message = await validate_order(
    exchange,
    'BTC/USDT:USDT',
    'buy',
    0.001,
    89000
)

if valid:
    order = await exchange.create_order(...)
else:
    print(f"Order validation failed: {message}")
```

### 4. Logging and Monitoring

```python
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bybit_trading.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('BybitTrader')

class LoggingExchange:
    def __init__(self, exchange):
        self.exchange = exchange

    async def create_order(self, *args, **kwargs):
        """Create order with logging"""
        logger.info(f"Creating order: {args}, {kwargs}")

        try:
            order = await self.exchange.create_order(*args, **kwargs)
            logger.info(f"Order created successfully: {order['id']}")

            # Log to database or monitoring system
            await self._log_to_db(order)

            return order

        except Exception as e:
            logger.error(f"Order creation failed: {e}", exc_info=True)
            raise

    async def _log_to_db(self, order):
        """Log order to database"""
        # Implement database logging
        pass

# Usage
exchange = LoggingExchange(exchange)
```

### 5. Testing with Testnet

```python
import os

class BybitConfig:
    @staticmethod
    def get_exchange(testnet=None):
        """Get exchange instance based on environment"""

        # Use environment variable if not specified
        if testnet is None:
            testnet = os.getenv('BYBIT_TESTNET', 'true').lower() == 'true'

        api_key = os.getenv('BYBIT_TESTNET_KEY' if testnet else 'BYBIT_KEY')
        secret = os.getenv('BYBIT_TESTNET_SECRET' if testnet else 'BYBIT_SECRET')

        exchange = ccxt.bybit({
            'apiKey': api_key,
            'secret': secret,
            'enableRateLimit': True,
            'options': {'defaultType': 'swap'}
        })

        if testnet:
            exchange.set_sandbox_mode(True)

        return exchange

# Usage
# For testing
exchange = BybitConfig.get_exchange(testnet=True)

# For production
exchange = BybitConfig.get_exchange(testnet=False)
```

---

## Critical Gotchas

### 1. Symbol Format Confusion

**GOTCHA**: Using wrong symbol format crashes orders

```python
# WRONG - Spot format for futures
symbol = 'BTC/USDT'  # This is spot trading

# RIGHT - Perpetual futures format
symbol = 'BTC/USDT:USDT'  # USDT perpetual

# Check market type
market = exchange.market(symbol)
print(f"Type: {market['type']}")  # 'swap' for perpetual
```

### 2. Testnet API Keys

**GOTCHA**: Using mainnet keys on testnet returns 10003 error

```python
# Generate separate API keys for testnet!
# Testnet: https://testnet.bybit.com/app/user/api-management
# Mainnet: https://www.bybit.com/app/user/api-management

# Always verify environment
exchange.set_sandbox_mode(True)  # CRITICAL for testnet
```

### 3. Position Mode (One-Way vs Hedge)

**GOTCHA**: `positionIdx` required in hedge mode

```python
# One-Way Mode (default, easier)
order = await exchange.create_order(
    symbol='BTC/USDT:USDT',
    type='market',
    side='buy',
    amount=0.001
)

# Hedge Mode (allows long and short simultaneously)
order = await exchange.create_order(
    symbol='BTC/USDT:USDT',
    type='market',
    side='buy',
    amount=0.001,
    params={'positionIdx': 1}  # 1=Long, 2=Short
)

# Check position mode first!
# Cannot switch mode with open positions/orders
```

### 4. Reduce-Only Flag

**GOTCHA**: Forgetting `reduceOnly` opens opposite position instead of closing

```python
# WRONG - Opens opposite position
close_order = await exchange.create_order(
    symbol='BTC/USDT:USDT',
    type='market',
    side='sell',  # If you have long position
    amount=0.001
)
# Result: Long position remains, short position opened!

# RIGHT - Closes position only
close_order = await exchange.create_order(
    symbol='BTC/USDT:USDT',
    type='market',
    side='sell',
    amount=0.001,
    params={'reduceOnly': True}  # CRITICAL
)
# Result: Long position reduced/closed
```

### 5. Leverage Must Be Set Before Trading

**GOTCHA**: Default leverage may be 1x, not what you expect

```python
# Set leverage BEFORE opening positions
# ccxt doesn't have unified set_leverage for Bybit
# Use pybit:

from pybit.unified_trading import HTTP
session = HTTP(testnet=True, api_key="KEY", api_secret="SECRET")

# Set leverage first
session.set_leverage(
    category="linear",
    symbol="BTCUSDT",
    buyLeverage="10",
    sellLeverage="10"
)

# Then trade
order = await exchange.create_order(...)
```

### 6. Market Orders Convert to Limit

**GOTCHA**: Bybit converts market orders to IOC limit orders for slippage protection

```python
# Market order != guaranteed execution
order = await exchange.create_order(
    symbol='BTC/USDT:USDT',
    type='market',
    side='buy',
    amount=0.001
)

# May get partially filled or rejected in extreme volatility
# Check order status after execution!
filled_order = await exchange.fetch_order(order['id'], symbol)
if filled_order['status'] != 'closed':
    print(f"Order not fully filled: {filled_order['filled']}/{filled_order['amount']}")
```

### 7. Stop-Loss Trigger Price Types

**GOTCHA**: Different trigger types can cause unexpected SL triggers

```python
# LastPrice - Uses last traded price (can be manipulated by wicks)
# MarkPrice - Uses mark price (recommended, more stable)
# IndexPrice - Uses index price (most stable)

# RECOMMENDED
params = {
    'stopLoss': 88000,
    'slTriggerBy': 'MarkPrice'  # Use MarkPrice to avoid wick triggers
}

# AVOID
params = {
    'stopLoss': 88000,
    'slTriggerBy': 'LastPrice'  # Can trigger on brief wicks
}
```

### 8. WebSocket Connection Limits

**GOTCHA**: Too many connections gets IP banned

```python
# WRONG - Creates new connection for each symbol
for symbol in symbols:
    ws = WebSocket(testnet=True, channel_type="linear")
    ws.trade_stream(symbol=symbol, callback=handle)
    # Result: 6 symbols = 6 connections = banned

# RIGHT - Single connection, multiple subscriptions
ws = WebSocket(testnet=True, channel_type="linear")
for symbol in symbols:
    ws.trade_stream(symbol=symbol, callback=handle)
# Result: 1 connection, 6 subscriptions = efficient
```

### 9. Time Synchronization

**GOTCHA**: Clock skew causes signature errors (10004)

```python
# Error: "Invalid signature"
# Cause: System time off by >5 seconds

# Solution 1: Sync system time
# Solution 2: Adjust recvWindow
exchange = ccxt.bybit({
    'options': {
        'recvWindow': 10000,  # 10 seconds (default: 5000)
        'adjustForTimeDifference': True  # Auto-adjust
    }
})
```

### 10. Order ID vs Client Order ID

**GOTCHA**: Bybit returns different IDs

```python
order = await exchange.create_order(
    symbol='BTC/USDT:USDT',
    type='market',
    side='buy',
    amount=0.001,
    params={'orderLinkId': 'my-custom-id-123'}  # Client order ID
)

# order['id'] = Bybit's order ID (use for fetch_order)
# order['clientOrderId'] = Your custom ID (if provided)

# Fetch by Bybit order ID
order = await exchange.fetch_order(order['id'], symbol)

# Cannot fetch by clientOrderId in ccxt
# Use fetch_open_orders and filter
```

### 11. Position Size Precision

**GOTCHA**: Invalid precision causes order rejection

```python
# WRONG - Too many decimals
amount = 0.123456789  # BTC

# RIGHT - Use exchange precision
symbol = 'BTC/USDT:USDT'
amount = exchange.amount_to_precision(symbol, 0.123456789)
print(amount)  # '0.123' (rounded to valid precision)

# For prices too
price = exchange.price_to_precision(symbol, 90123.456789)
```

### 12. Funding Rates Deducted from Position

**GOTCHA**: Funding fees reduce position margin

```python
# Perpetual futures have funding rates (every 8 hours)
# Positive rate: Longs pay shorts
# Negative rate: Shorts pay longs

# Check funding rate
ticker = await exchange.fetch_ticker('BTC/USDT:USDT')
funding_rate = ticker.get('fundingRate', 0)
print(f"Funding rate: {funding_rate * 100}%")

# Ensure margin buffer for funding fees
# Or close positions before funding time
```

---

## Code Examples

### Complete Trading Bot Example

```python
import ccxt.async_support as ccxt
import asyncio
import logging
from typing import Optional, Dict
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BybitTradingBot:
    def __init__(
        self,
        api_key: str,
        secret: str,
        testnet: bool = True,
        leverage: int = 10
    ):
        self.exchange = ccxt.bybit({
            'apiKey': api_key,
            'secret': secret,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'swap',
                'recvWindow': 10000,
                'adjustForTimeDifference': True,
            }
        })

        if testnet:
            self.exchange.set_sandbox_mode(True)

        self.leverage = leverage
        self.positions = {}

    async def initialize(self):
        """Initialize bot"""
        logger.info("Initializing bot...")
        await self.exchange.load_markets()

        # Set leverage for all symbols
        # Note: Use pybit for this in production
        logger.info(f"Leverage: {self.leverage}x")

        logger.info("Bot initialized successfully")

    async def close(self):
        """Cleanup"""
        await self.exchange.close()

    async def get_balance(self) -> Dict:
        """Get account balance"""
        balance = await self.exchange.fetch_balance()
        return {
            'total': balance['USDT']['total'],
            'free': balance['USDT']['free'],
            'used': balance['USDT']['used'],
        }

    async def get_current_price(self, symbol: str) -> float:
        """Get current market price"""
        ticker = await self.exchange.fetch_ticker(symbol)
        return ticker['last']

    async def calculate_position_size(
        self,
        symbol: str,
        risk_pct: float = 0.02
    ) -> float:
        """Calculate position size based on risk"""
        balance = await self.get_balance()
        price = await self.get_current_price(symbol)

        # Calculate position value (2% of balance with leverage)
        position_value = balance['total'] * risk_pct * self.leverage

        # Calculate position size in base currency
        position_size = position_value / price

        # Round to exchange precision
        position_size = float(
            self.exchange.amount_to_precision(symbol, position_size)
        )

        return position_size

    async def open_position(
        self,
        symbol: str,
        side: str,
        stop_loss_pct: float = 0.02,
        take_profit_pct: float = 0.04
    ) -> Optional[Dict]:
        """
        Open a position with stop-loss and take-profit

        Args:
            symbol: Trading pair (e.g., 'BTC/USDT:USDT')
            side: 'buy' for long, 'sell' for short
            stop_loss_pct: Stop-loss percentage (default 2%)
            take_profit_pct: Take-profit percentage (default 4%)
        """
        try:
            # Calculate position size
            amount = await self.calculate_position_size(symbol)

            # Get current price
            price = await self.get_current_price(symbol)

            # Calculate stop-loss and take-profit prices
            if side == 'buy':
                stop_loss = price * (1 - stop_loss_pct)
                take_profit = price * (1 + take_profit_pct)
            else:
                stop_loss = price * (1 + stop_loss_pct)
                take_profit = price * (1 - take_profit_pct)

            # Round prices
            stop_loss = float(self.exchange.price_to_precision(symbol, stop_loss))
            take_profit = float(self.exchange.price_to_precision(symbol, take_profit))

            logger.info(f"Opening {side} position on {symbol}")
            logger.info(f"Amount: {amount}, Entry: {price}")
            logger.info(f"SL: {stop_loss}, TP: {take_profit}")

            # Place order with TP/SL
            order = await self.exchange.create_order(
                symbol=symbol,
                type='market',
                side=side,
                amount=amount,
                params={
                    'stopLoss': str(stop_loss),
                    'takeProfit': str(take_profit),
                    'slTriggerBy': 'MarkPrice',
                    'tpTriggerBy': 'MarkPrice',
                }
            )

            logger.info(f"Position opened: {order['id']}")

            # Store position info
            self.positions[symbol] = {
                'order_id': order['id'],
                'side': side,
                'amount': amount,
                'entry_price': price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'timestamp': datetime.now(),
            }

            return order

        except Exception as e:
            logger.error(f"Failed to open position: {e}", exc_info=True)
            return None

    async def close_position(self, symbol: str) -> Optional[Dict]:
        """Close position for symbol"""
        try:
            # Get current position
            positions = await self.exchange.fetch_positions([symbol])

            if not positions or float(positions[0]['contracts']) == 0:
                logger.warning(f"No open position for {symbol}")
                return None

            position = positions[0]
            side = position['side']  # 'long' or 'short'
            amount = float(position['contracts'])

            # Determine close side
            close_side = 'sell' if side == 'long' else 'buy'

            logger.info(f"Closing {side} position on {symbol}")
            logger.info(f"Amount: {amount}")

            # Place close order
            order = await self.exchange.create_order(
                symbol=symbol,
                type='market',
                side=close_side,
                amount=amount,
                params={'reduceOnly': True}
            )

            logger.info(f"Position closed: {order['id']}")

            # Remove from tracked positions
            if symbol in self.positions:
                del self.positions[symbol]

            return order

        except Exception as e:
            logger.error(f"Failed to close position: {e}", exc_info=True)
            return None

    async def get_positions(self) -> list:
        """Get all open positions"""
        try:
            positions = await self.exchange.fetch_positions()

            # Filter only open positions
            open_positions = [
                p for p in positions
                if float(p['contracts']) > 0
            ]

            return open_positions

        except Exception as e:
            logger.error(f"Failed to fetch positions: {e}", exc_info=True)
            return []

    async def monitor_positions(self):
        """Monitor positions and log status"""
        positions = await self.get_positions()

        if not positions:
            logger.info("No open positions")
            return

        for position in positions:
            symbol = position['symbol']
            side = position['side']
            size = position['contracts']
            entry = position['entryPrice']
            mark = position['markPrice']
            pnl = position['unrealizedPnl']

            logger.info(f"{symbol} | {side.upper()} | Size: {size} | "
                       f"Entry: {entry} | Mark: {mark} | PnL: {pnl} USDT")


async def main():
    """Main trading loop"""

    # Initialize bot
    bot = BybitTradingBot(
        api_key="YOUR_TESTNET_KEY",
        secret="YOUR_TESTNET_SECRET",
        testnet=True,
        leverage=10
    )

    try:
        await bot.initialize()

        # Check balance
        balance = await bot.get_balance()
        logger.info(f"Balance: {balance}")

        # Open long position on BTC
        symbol = 'BTC/USDT:USDT'
        order = await bot.open_position(
            symbol=symbol,
            side='buy',
            stop_loss_pct=0.02,  # 2% SL
            take_profit_pct=0.04  # 4% TP
        )

        if order:
            # Monitor position for 60 seconds
            for i in range(12):
                await asyncio.sleep(5)
                await bot.monitor_positions()

            # Close position
            await bot.close_position(symbol)

        # Final balance
        balance = await bot.get_balance()
        logger.info(f"Final balance: {balance}")

    finally:
        await bot.close()


if __name__ == '__main__':
    asyncio.run(main())
```

### Simple Order Example

```python
import ccxt.async_support as ccxt
import asyncio

async def simple_order_example():
    # Initialize exchange
    exchange = ccxt.bybit({
        'apiKey': 'YOUR_KEY',
        'secret': 'YOUR_SECRET',
        'enableRateLimit': True,
        'options': {'defaultType': 'swap'}
    })
    exchange.set_sandbox_mode(True)

    try:
        # Load markets
        await exchange.load_markets()

        # Place market order
        symbol = 'BTC/USDT:USDT'
        order = await exchange.create_order(
            symbol=symbol,
            type='market',
            side='buy',
            amount=0.001,
            params={
                'stopLoss': '88000',
                'takeProfit': '92000',
            }
        )

        print(f"Order placed: {order['id']}")

        # Wait a bit
        await asyncio.sleep(2)

        # Check order status
        order_status = await exchange.fetch_order(order['id'], symbol)
        print(f"Order status: {order_status['status']}")

        # Fetch position
        positions = await exchange.fetch_positions([symbol])
        if positions:
            print(f"Position: {positions[0]}")

        # Close position
        close_order = await exchange.create_order(
            symbol=symbol,
            type='market',
            side='sell',
            amount=0.001,
            params={'reduceOnly': True}
        )

        print(f"Position closed: {close_order['id']}")

    finally:
        await exchange.close()

asyncio.run(simple_order_example())
```

---

## Summary

### Key Takeaways

1. **Always use testnet first**: Register at testnet.bybit.com
2. **Use correct symbol format**: `'BTC/USDT:USDT'` for perpetual futures
3. **Enable sandbox mode**: `exchange.set_sandbox_mode(True)`
4. **Set default type**: `options={'defaultType': 'swap'}`
5. **Enable rate limiting**: `enableRateLimit=True`
6. **Use reduce_only flag**: Prevents opening opposite positions
7. **Set leverage before trading**: Use pybit or direct API
8. **Use MarkPrice for triggers**: Avoid LastPrice for SL/TP
9. **Handle errors properly**: Implement retry logic
10. **Monitor rate limits**: Stay within 600 req/5sec

### Integration Checklist

- [ ] Testnet account created
- [ ] API keys generated (testnet)
- [ ] ccxt library installed (`pip install ccxt`)
- [ ] pybit library installed (`pip install pybit`) - Optional but recommended
- [ ] Test connection successful
- [ ] Markets loaded successfully
- [ ] Balance fetch working
- [ ] Market order execution tested
- [ ] Limit order execution tested
- [ ] Position fetching tested
- [ ] Position closing tested
- [ ] Stop-loss orders tested
- [ ] WebSocket connection tested (if needed)
- [ ] Error handling implemented
- [ ] Rate limiting implemented
- [ ] Logging configured
- [ ] Ready for Trade Executor integration

### Next Steps for Trade Executor

1. **Environment Setup**:
   - Create `.env` file with testnet credentials
   - Configure logging paths
   - Set up database for trade history

2. **Core Components**:
   - Exchange client wrapper (use BybitClient example)
   - Position manager
   - Order executor with retry logic
   - Risk manager (position sizing, max positions)
   - Error handler

3. **Testing Strategy**:
   - Unit tests for each component
   - Integration tests with testnet
   - Paper trading simulation
   - Performance benchmarks

4. **Production Preparation**:
   - Switch to mainnet credentials (when ready)
   - Set up monitoring and alerts
   - Implement circuit breakers
   - Configure backup systems

---

**End of Bybit Integration Guide**
