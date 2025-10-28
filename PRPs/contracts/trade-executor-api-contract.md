# API Contract: Trade Execution Service

**Version**: 1.0 | **Date**: 2025-10-27 | **Status**: Final

## Overview
Trade Execution Service handles order placement, position management, and reconciliation with Bybit exchange.

## Service Interface

```python
class TradeExecutor:
    async def execute_signal(self, signal: TradingSignal) -> ExecutionResult:
        """Execute trading signal with all checks"""

    async def place_market_order(
        self,
        symbol: str,
        side: str,
        amount: float
    ) -> Order:
        """Place market order"""

    async def place_stop_loss(
        self,
        position: Position
    ) -> Order:
        """Place stop-loss order"""

    async def close_position(
        self,
        position_id: str
    ) -> Order:
        """Close position with market order"""
```

## Bybit REST API Integration

### Base URL
`https://api.bybit.com`

### Create Order
```http
POST /v5/order/create
```

**Request**:
```json
{
  "category": "linear",
  "symbol": "BTCUSDT",
  "side": "Buy",
  "orderType": "Market",
  "qty": "0.002",
  "timeInForce": "GTC",
  "positionIdx": 0
}
```

**Response**:
```json
{
  "retCode": 0,
  "retMsg": "OK",
  "result": {
    "orderId": "1234567890",
    "orderLinkId": "client-order-123"
  }
}
```

### Place Stop-Loss
```http
POST /v5/order/create
```

**Request**:
```json
{
  "category": "linear",
  "symbol": "BTCUSDT",
  "side": "Sell",
  "orderType": "Market",
  "qty": "0.002",
  "stopLoss": "49000",
  "reduceOnly": true
}
```

### Get Positions
```http
GET /v5/position/list?category=linear&symbol=BTCUSDT
```

**Response**:
```json
{
  "retCode": 0,
  "result": {
    "list": [{
      "symbol": "BTCUSDT",
      "side": "Buy",
      "size": "0.002",
      "entryPrice": "50000",
      "leverage": "10",
      "unrealisedPnl": "10.50"
    }]
  }
}
```

## Position Sizing

```python
def calculate_position_size(
    signal: TradingSignal,
    account_balance_chf: float
) -> float:
    """
    Calculate position size in base currency

    Formula:
    position_value_chf = risk_usd * leverage * chf_to_usd_rate
    quantity = position_value_usd / entry_price

    Limits:
    - Max 20% of account per position
    - Validate against exchange lot size
    """
    chf_to_usd_rate = get_exchange_rate('CHF', 'USD')
    position_value_chf = signal.risk_usd * signal.leverage * chf_to_usd_rate

    if position_value_chf > account_balance_chf * 0.20:
        raise ValueError("Position exceeds 20% limit")

    position_value_usd = position_value_chf / chf_to_usd_rate
    quantity = position_value_usd / signal.entry_price

    return round_to_lot_size(quantity, signal.symbol)
```

## Position Reconciliation

### After Every Order
```python
async def reconcile_after_order(order_id: str):
    # Wait for settlement
    await asyncio.sleep(2)

    # Fetch order status
    order = await exchange.fetch_order(order_id)

    # Compare expected vs actual fill
    if order['filled'] < order['amount'] * 0.95:
        logger.warning(f"Partial fill: {order['filled']}/{order['amount']}")

    # Update database with actual values
    await db.update_position_actual(order['filled'], order['average'])
```

### Periodic (Every 5 Minutes)
```python
async def reconcile_all_positions():
    # Fetch from exchange (source of truth)
    exchange_positions = await exchange.fetch_positions()

    # Fetch from database
    db_positions = await db.get_active_positions()

    # Compare
    for db_pos in db_positions:
        exchange_pos = find_position(exchange_positions, db_pos['symbol'])

        if not exchange_pos:
            logger.error(f"Ghost position: {db_pos['symbol']}")
            await send_alert(f"Position {db_pos['symbol']} in DB but not on exchange")
            continue

        if abs(db_pos['quantity'] - exchange_pos['contracts']) > 0.0001:
            logger.error(f"Position mismatch: {db_pos['symbol']}")
            # Auto-heal: trust exchange
            await db.update_position_quantity(db_pos['symbol'], exchange_pos['contracts'])
```

## Error Handling

```python
class OrderExecutionError(Exception):
    """Raised when order placement fails"""

class InsufficientMarginError(Exception):
    """Raised when insufficient margin"""

class PartialFillError(Exception):
    """Raised when order partially filled"""
```

## Performance Targets
- **Order Placement**: <300ms
- **Position Reconciliation**: <100ms
- **Stop-Loss Placement**: <500ms (after entry)

---

**Document Location**: `/Users/tobiprivat/Documents/GitProjects/personal/trader/PRPs/contracts/trade-executor-api-contract.md`
