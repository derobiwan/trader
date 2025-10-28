# API Contract: Risk Management Service

**Version**: 1.0 | **Date**: 2025-10-27 | **Status**: Final

## Overview
Risk Management Service implements multi-layered protection, position limits, and daily loss circuit breaker.

## Service Interface

```python
class RiskManager:
    async def validate_signal(self, signal: TradingSignal) -> RiskValidation:
        """Validate trading signal against risk limits"""

    async def start_multi_layer_protection(self, position: Position) -> Protection:
        """Start 3-layer stop-loss protection"""

    async def check_daily_loss_limit(self) -> CircuitBreakerStatus:
        """Check if daily loss limit exceeded"""

    async def emergency_close_position(
        self,
        position_id: str,
        reason: str
    ) -> Order:
        """Emergency position closure"""
```

## Risk Validation Rules

### Pre-Trade Checks

```python
PRE_TRADE_LIMITS = {
    'max_concurrent_positions': 6,
    'max_position_size_pct': 0.20,  # 20% of account
    'max_total_exposure_pct': 0.80,  # 80% of account
    'min_leverage': 5,
    'max_leverage': 40,
    'per_symbol_leverage': {
        'BTC/USDT': 40,
        'ETH/USDT': 40,
        'SOL/USDT': 25,
        'BNB/USDT': 25,
        'ADA/USDT': 20,
        'DOGE/USDT': 20
    },
    'min_stop_loss_pct': 0.01,  # 1%
    'max_stop_loss_pct': 0.10,  # 10%
    'min_confidence': 0.60  # 60% for entries
}
```

### Daily Loss Circuit Breaker

```python
DAILY_LOSS_LIMITS = {
    'max_daily_loss_pct': -0.07,  # -7%
    'max_daily_loss_chf': -183.89,  # -7% of CHF 2,626.96
    'reset_time_utc': '00:00'
}
```

## Multi-Layered Stop-Loss Protection

### Layer 1: Exchange Stop-Loss Order

```python
async def place_exchange_stop(position: Position) -> Order:
    """Place stop-loss order on exchange (primary)"""
    stop_price = calculate_stop_price(position)

    order = await exchange.create_order(
        symbol=position.symbol,
        type='stop_market',
        side='sell' if position.side == 'long' else 'buy',
        amount=position.quantity,
        params={'stopPrice': stop_price, 'reduceOnly': True}
    )

    return order
```

### Layer 2: Application-Level Monitoring

```python
async def app_level_monitor(position: Position):
    """Monitor price and trigger if exchange stop fails"""
    while await position_exists(position):
        current_price = await get_current_price(position.symbol)

        if should_trigger_stop(position, current_price):
            logger.warning(f"App-level stop triggered: {position.symbol}")
            await close_position_market(position)
            break

        await asyncio.sleep(2)  # Check every 2 seconds
```

### Layer 3: Emergency Liquidation

```python
async def emergency_monitor(position: Position):
    """Emergency close if loss exceeds 15%"""
    EMERGENCY_THRESHOLD = 0.15  # 15% loss

    while await position_exists(position):
        current_loss_pct = await calculate_loss_pct(position)

        if current_loss_pct > EMERGENCY_THRESHOLD:
            logger.critical(f"EMERGENCY LIQUIDATION: {position.symbol}")
            await send_alert(f"Emergency close {position.symbol} at {current_loss_pct:.1%} loss")
            await emergency_close(position)
            break

        await asyncio.sleep(1)  # Check every second
```

## Circuit Breaker

```python
class CircuitBreaker:
    async def check_daily_loss(self):
        """Check if daily loss limit exceeded"""
        daily_pnl_chf = await calculate_daily_pnl()
        daily_loss_limit_chf = -183.89  # -7% of CHF 2,626.96

        if daily_pnl_chf < daily_loss_limit_chf:
            logger.critical(f"CIRCUIT BREAKER TRIGGERED: {daily_pnl_chf:.2f} CHF")
            await send_alert(f"Daily loss {daily_pnl_chf:.2f} CHF exceeds limit")

            # Close all positions
            await self.close_all_positions()

            # Enter circuit breaker state
            await self.enter_circuit_breaker_state()

            # Require manual reset
            await self.await_manual_reset()
```

## Performance Targets
- **Risk Validation**: <30ms
- **Stop-Loss Monitoring**: 2-second interval
- **Emergency Detection**: 1-second interval
- **Circuit Breaker Check**: Real-time (after every position change)

---

**Document Location**: `/Users/tobiprivat/Documents/GitProjects/personal/trader/PRPs/contracts/risk-manager-api-contract.md`
