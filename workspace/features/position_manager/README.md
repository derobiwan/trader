# Position Manager Service

Critical path service for managing trading position lifecycle including creation, updates, P&L tracking, stop-loss monitoring, and closure.

## Overview

The Position Manager is the **core service** that all trading logic depends on. It ensures:
- Accurate position tracking throughout lifecycle
- Real-time P&L calculations in CHF
- Risk limit enforcement (position size, total exposure)
- Stop-loss and take-profit monitoring
- Daily P&L tracking for circuit breaker
- Comprehensive audit logging

**Status**: Phase 4 Implementation Complete ✅

## Architecture

```
Position Manager
├── models.py                  # Extended Pydantic models with validation
├── position_service.py        # Core position lifecycle service
├── tests/
│   └── test_position_service.py  # Comprehensive test suite (>80% coverage)
└── README.md                  # This file
```

### Dependencies

```
workspace/shared/database/
├── connection.py              # Database connection pool (from TASK-001)
└── models.py                  # Base Pydantic models (from TASK-001)
```

## Key Features

### 1. Position Creation with Validation

Creates new positions with comprehensive validation:
- ✅ Stop-loss required (100% enforcement)
- ✅ Leverage in range 5-40x
- ✅ Position size < 20% of capital (CHF 525.39)
- ✅ Total exposure < 80% of capital (CHF 2,101.57)
- ✅ Valid symbols only (BTC, ETH, SOL, BNB, ADA, DOGE)
- ✅ Stop-loss on correct side of entry price

### 2. Real-Time Price Updates

Updates position prices and recalculates P&L:
- Current price tracking
- Unrealized P&L in USD and CHF
- P&L percentage calculation
- Stop-loss/take-profit trigger detection

### 3. Position Closure

Closes positions with final P&L calculation:
- Multiple close reasons (stop_loss, take_profit, manual, circuit_breaker)
- Final P&L in CHF
- Daily P&L aggregation
- Comprehensive audit logging

### 4. Stop-Loss Monitoring

Monitors all positions for stop-loss triggers:
- Automatic detection when price hits stop-loss
- Flags positions for Trade Executor to close
- Does NOT close positions (separation of concerns)

### 5. Daily P&L Tracking

Tracks daily performance for circuit breaker:
- Realized P&L from closed positions
- Unrealized P&L from open positions
- Total daily P&L in CHF
- Circuit breaker threshold monitoring (-CHF 183.89)

## Usage Examples

### Initialize Service

```python
from workspace.shared.database.connection import init_pool
from workspace.features.position_manager.position_service import PositionService

# Initialize database pool
pool = await init_pool(
    host="localhost",
    database="trading_system",
    user="postgres",
    password="secure_password"
)

# Create service
service = PositionService(pool)
```

### Create Position

```python
# Create LONG position
position = await service.create_position(
    symbol="BTCUSDT",
    side="LONG",
    quantity=Decimal("0.01"),
    entry_price=Decimal("45000.00"),
    leverage=10,
    stop_loss=Decimal("44000.00"),
    take_profit=Decimal("46000.00")  # Optional
)

print(f"Position created: {position.id}")
print(f"Value: CHF {position.position_value_chf:.2f}")
print(f"P&L: CHF {position.unrealized_pnl_chf:.2f}")
```

### Update Position Price

```python
# Update with current market price
updated = await service.update_position_price(
    position_id=position.id,
    current_price=Decimal("45500.00")
)

print(f"Current price: {updated.current_price}")
print(f"Unrealized P&L: CHF {updated.unrealized_pnl_chf:.2f} ({updated.unrealized_pnl_pct:.2f}%)")
print(f"Stop-loss triggered: {updated.is_stop_loss_triggered}")
```

### Close Position

```python
# Close position with profit
closed = await service.close_position(
    position_id=position.id,
    close_price=Decimal("46000.00"),
    reason="take_profit"
)

print(f"Position closed")
print(f"Final P&L: CHF {closed.pnl_chf:.2f}")
print(f"Status: {closed.status.value}")
```

### Monitor Stop-Loss Triggers

```python
# Check all positions for stop-loss
triggered_positions = await service.check_stop_loss_triggers()

for position in triggered_positions:
    print(f"⚠️ Stop-loss hit: {position.symbol} {position.side.value}")
    print(f"  Current: {position.current_price}, Stop: {position.stop_loss}")

    # Trade Executor should close these positions
```

### Get Daily P&L

```python
# Get today's P&L summary
summary = await service.get_daily_pnl()

print(f"Date: {summary.date}")
print(f"Total P&L: CHF {summary.total_pnl_chf:.2f}")
print(f"  Realized: CHF {summary.realized_pnl_chf:.2f}")
print(f"  Unrealized: CHF {summary.unrealized_pnl_chf:.2f}")
print(f"Open positions: {summary.open_positions_count}")
print(f"Circuit breaker triggered: {summary.is_circuit_breaker_triggered}")
```

### Get Active Positions

```python
# Get all open positions
active_positions = await service.get_active_positions()

for position in active_positions:
    print(f"{position.symbol} {position.side.value}")
    print(f"  Quantity: {position.quantity} @ {position.entry_price}")
    print(f"  Current: {position.current_price}")
    print(f"  P&L: CHF {position.unrealized_pnl_chf:.2f}")

# Get positions for specific symbol
btc_positions = await service.get_active_positions(symbol="BTCUSDT")
```

### Get Statistics

```python
# Get aggregated statistics
stats = await service.get_statistics()

print(f"Total positions: {stats.total_positions}")
print(f"Open: {stats.open_positions}, Closed: {stats.closed_positions}")
print(f"Total exposure: CHF {stats.total_exposure_chf:.2f}")
print(f"Unrealized P&L: CHF {stats.total_unrealized_pnl_chf:.2f}")
print(f"Realized P&L: CHF {stats.total_realized_pnl_chf:.2f}")
print(f"At stop-loss: {stats.positions_at_stop_loss}")
print(f"At take-profit: {stats.positions_at_take_profit}")
```

### Bulk Price Updates

```python
from workspace.features.position_manager.position_service import bulk_update_prices

# Update prices for multiple symbols efficiently
price_updates = {
    "BTCUSDT": Decimal("45500.00"),
    "ETHUSDT": Decimal("2550.00"),
    "SOLUSDT": Decimal("105.50")
}

updated_positions = await bulk_update_prices(service, price_updates)

print(f"Updated {len(updated_positions)} positions")
```

## Position Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│                      POSITION LIFECYCLE                      │
└─────────────────────────────────────────────────────────────┘

1. CREATE
   ├─ Validate parameters (stop-loss, leverage, symbol)
   ├─ Check risk limits (position size, total exposure)
   ├─ Insert into database
   ├─ Log to audit_log
   └─ Return PositionWithPnL

2. UPDATE (Real-time)
   ├─ Update current_price
   ├─ Recalculate unrealized P&L
   ├─ Check stop-loss trigger (flag only, don't close)
   ├─ Check take-profit trigger (flag only, don't close)
   └─ Return updated PositionWithPnL

3. MONITOR
   ├─ check_stop_loss_triggers() → List of positions to close
   ├─ check_take_profit_triggers() → List of positions to close
   ├─ Trade Executor decides whether to close
   └─ Risk Manager enforces circuit breaker

4. CLOSE
   ├─ Calculate final P&L in CHF
   ├─ Update status to CLOSED/LIQUIDATED
   ├─ Update daily P&L tracking
   ├─ Log to audit_log
   └─ Return closed PositionWithPnL

5. DAILY AGGREGATION
   ├─ Sum realized P&L (closed positions)
   ├─ Sum unrealized P&L (open positions)
   ├─ Check circuit breaker threshold (-CHF 183.89)
   └─ Update circuit_breaker_state table
```

## P&L Calculation Formulas

### Long Position

```python
# Unrealized P&L in USD
pnl_usd = (current_price - entry_price) * quantity * leverage

# Convert to CHF (USD/CHF rate = 0.85)
pnl_chf = pnl_usd * 0.85

# Percentage
pnl_pct = ((current_price - entry_price) / entry_price) * leverage * 100
```

**Example**: LONG BTC
- Entry: $45,000
- Current: $45,500
- Quantity: 0.01 BTC
- Leverage: 10x

```
pnl_usd = (45500 - 45000) * 0.01 * 10 = $50
pnl_chf = 50 * 0.85 = CHF 42.50
pnl_pct = (500 / 45000) * 10 * 100 = 11.11%
```

### Short Position

```python
# Unrealized P&L in USD
pnl_usd = (entry_price - current_price) * quantity * leverage

# Convert to CHF
pnl_chf = pnl_usd * 0.85

# Percentage
pnl_pct = ((entry_price - current_price) / entry_price) * leverage * 100
```

**Example**: SHORT BTC
- Entry: $45,000
- Current: $44,500
- Quantity: 0.01 BTC
- Leverage: 10x

```
pnl_usd = (45000 - 44500) * 0.01 * 10 = $50
pnl_chf = 50 * 0.85 = CHF 42.50
pnl_pct = (500 / 45000) * 10 * 100 = 11.11%
```

## Risk Limits

### Position Size Limit

Maximum single position size: **20% of capital**
```
Max position value = CHF 2,626.96 * 0.20 = CHF 525.39
```

**Calculation**:
```python
position_value_usd = quantity * entry_price * leverage
position_value_chf = position_value_usd * 0.85

if position_value_chf > CHF 525.39:
    raise RiskLimitError("Position exceeds 20% of capital")
```

### Total Exposure Limit

Maximum total exposure: **80% of capital**
```
Max total exposure = CHF 2,626.96 * 0.80 = CHF 2,101.57
```

**Calculation**:
```python
total_exposure = sum(position.position_value_chf for position in open_positions)

if total_exposure + new_position_value > CHF 2,101.57:
    raise RiskLimitError("Total exposure exceeds 80% of capital")
```

### Circuit Breaker Threshold

Daily loss limit: **-7% of capital**
```
Circuit breaker = CHF 2,626.96 * -0.07 = CHF -183.89
```

**Calculation**:
```python
daily_pnl = realized_pnl + unrealized_pnl

if daily_pnl <= CHF -183.89:
    trigger_circuit_breaker()
    close_all_positions()
```

## Error Handling

### Custom Exceptions

```python
from workspace.features.position_manager.models import (
    ValidationError,       # Invalid parameters
    RiskLimitError,        # Risk limits exceeded
    PositionNotFoundError, # Position doesn't exist
    InsufficientCapitalError  # Not enough capital
)

try:
    position = await service.create_position(...)
except ValidationError as e:
    print(f"Validation failed: {e}")
except RiskLimitError as e:
    print(f"Risk limit exceeded: {e}")
except ConnectionError as e:
    print(f"Database error: {e}")
```

### Retry Logic

All database operations include automatic retry with exponential backoff:
- **Retries**: 3 attempts
- **Backoff**: 0.5s, 1.0s, 1.5s
- **Timeout**: 10 seconds per query

```python
# Automatic retry for transient errors
for attempt in range(max_retries):
    try:
        await conn.execute(query)
        break
    except asyncpg.PostgresError as e:
        if attempt == max_retries - 1:
            raise ConnectionError(f"Failed after {max_retries} attempts")
        await asyncio.sleep(0.5 * (attempt + 1))
```

## Testing

### Run Tests

```bash
# Run all tests
pytest workspace/features/position_manager/tests/test_position_service.py -v

# Run specific test
pytest workspace/features/position_manager/tests/test_position_service.py::test_create_position_success -v

# Run with coverage
pytest workspace/features/position_manager/tests/ --cov=workspace/features/position_manager --cov-report=html
```

### Test Coverage

Comprehensive test suite with **>80% coverage**:

**Position Creation Tests** (8 tests):
- ✅ Successful creation
- ✅ Missing stop-loss
- ✅ Invalid leverage
- ✅ Invalid symbol
- ✅ Wrong side stop-loss
- ✅ Exceeds size limit
- ✅ Exceeds exposure limit

**Price Update Tests** (4 tests):
- ✅ Update with profit
- ✅ Update with loss
- ✅ SHORT position profit
- ✅ Nonexistent position

**Position Closure Tests** (4 tests):
- ✅ Close with profit
- ✅ Close with loss
- ✅ SHORT position profit
- ✅ Nonexistent position

**Stop-Loss Detection Tests** (3 tests):
- ✅ LONG position trigger
- ✅ SHORT position trigger
- ✅ Take-profit trigger

**Daily P&L Tests** (3 tests):
- ✅ With open positions
- ✅ With closed positions
- ✅ Circuit breaker detection

**Query Tests** (5 tests):
- ✅ Get by ID
- ✅ Get active positions
- ✅ Filter by symbol
- ✅ Total exposure
- ✅ Statistics

**Concurrent Operations** (2 tests):
- ✅ Concurrent price updates
- ✅ Bulk price updates

**Edge Cases** (3 tests):
- ✅ Zero P&L
- ✅ Maximum leverage (40x)
- ✅ Decimal precision

## Database Schema Integration

Uses tables from TASK-001:

### positions
```sql
CREATE TABLE positions (
    id UUID PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    quantity NUMERIC(20, 8) NOT NULL,
    entry_price NUMERIC(20, 8) NOT NULL,
    current_price NUMERIC(20, 8),
    leverage INTEGER NOT NULL,
    stop_loss NUMERIC(20, 8),
    take_profit NUMERIC(20, 8),
    status VARCHAR(20) NOT NULL,
    pnl_chf NUMERIC(20, 8),
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    closed_at TIMESTAMP
);
```

### circuit_breaker_state
```sql
CREATE TABLE circuit_breaker_state (
    date DATE PRIMARY KEY,
    current_pnl_chf NUMERIC(20, 8) NOT NULL DEFAULT 0,
    triggered BOOLEAN NOT NULL DEFAULT FALSE,
    trigger_reason TEXT,
    positions_closed TEXT[],
    reset_at TIMESTAMP
);
```

### audit_log
```sql
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50),
    entity_id UUID,
    details JSONB
);
```

## Integration Points

### Used By

1. **Trade Executor** (Next: TASK-003)
   - Creates positions when executing trades
   - Closes positions at stop-loss/take-profit
   - Validates position parameters

2. **Risk Manager** (Next: TASK-004)
   - Checks risk limits before trade execution
   - Monitors stop-loss triggers
   - Enforces circuit breaker

3. **Decision Engine**
   - Gets current positions before decisions
   - Calculates available capital
   - Checks position concentration

4. **Monitoring Service**
   - Tracks daily P&L
   - Generates performance reports
   - Sends alerts

### API Contract Example

```python
# Trade Executor uses this API:
class TradeExecutor:
    def __init__(self, position_service: PositionService):
        self.positions = position_service

    async def execute_entry(self, signal: TradingSignal):
        # Create position from signal
        position = await self.positions.create_position(
            symbol=signal.symbol,
            side=signal.action.value,
            quantity=calculated_quantity,
            entry_price=current_price,
            leverage=calculated_leverage,
            stop_loss=calculated_stop_loss,
            signal_id=signal.id
        )
        return position

    async def execute_exit(self, position_id: UUID, reason: str):
        # Close position
        closed = await self.positions.close_position(
            position_id=position_id,
            close_price=current_price,
            reason=reason
        )
        return closed
```

## Performance Considerations

### Database Optimization

- **Connection Pooling**: 10-50 connections, auto-recycling
- **Query Timeout**: 10 seconds per query
- **Indexes**: id (PK), status, symbol, created_at
- **Transactions**: All updates use ACID transactions

### Memory Efficiency

- **Lazy Loading**: Only load positions when needed
- **Decimal Precision**: 8 decimal places (sufficient for crypto)
- **Batch Operations**: Use `bulk_update_prices()` for multiple updates

### Latency Targets

- **Create Position**: < 50ms
- **Update Price**: < 20ms
- **Get Active Positions**: < 30ms
- **Daily P&L Calculation**: < 100ms

## Important Notes

### DO

✅ Use database transactions for all updates
✅ Log all position changes to audit_log
✅ Calculate P&L in CHF (not USD)
✅ Validate all inputs rigorously
✅ Handle edge cases (zero quantity, negative prices)
✅ Test with real-world scenarios

### DO NOT

❌ Close positions in this service (Trade Executor does that)
❌ Place orders (Trade Executor does that)
❌ Make trading decisions (Decision Engine does that)
❌ Skip stop-loss validation
❌ Use FLOAT for calculations (use Decimal)
❌ Bypass risk limit checks

## Next Steps

### TASK-003: Trade Executor
- Use `PositionService.create_position()` for entries
- Use `PositionService.close_position()` for exits
- Monitor `check_stop_loss_triggers()` continuously

### TASK-004: Risk Manager
- Use `get_total_exposure()` before trades
- Use `get_daily_pnl()` for circuit breaker
- Validate limits with `validate_risk_limits()`

## Troubleshooting

### Position Not Found

```python
# Check if position exists
position = await service.get_position_by_id(position_id)
if position is None:
    print("Position not found or already closed")
```

### Risk Limit Exceeded

```python
# Check current exposure before creating position
current_exposure = await service.get_total_exposure()
print(f"Current exposure: CHF {current_exposure:.2f}")
print(f"Available: CHF {MAX_TOTAL_EXPOSURE_CHF - current_exposure:.2f}")
```

### Database Connection Issues

```python
# Check database health
health = await pool.health_check()
if not health["healthy"]:
    print(f"Database unhealthy: {health['error']}")
    print(f"Latency: {health['latency_ms']}ms")
```

## Contact

For issues or questions about Position Manager:
- Check test suite for usage examples
- Review error messages for validation details
- Consult audit_log for transaction history

---

**Version**: 1.0.0
**Status**: Production Ready ✅
**Last Updated**: 2025-01-27
**Phase**: 4 (Implementation)
