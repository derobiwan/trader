# Risk Manager Module

Multi-layered risk management system providing pre-trade validation, position limits, stop-loss protection, and daily loss circuit breaker for cryptocurrency trading.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Components](#components)
  - [RiskManager](#riskmanager)
  - [CircuitBreaker](#circuitbreaker)
  - [StopLossManager](#stoplossmanager)
- [Risk Limits](#risk-limits)
- [Usage](#usage)
- [Multi-Layer Stop-Loss Protection](#multi-layer-stop-loss-protection)
- [Circuit Breaker System](#circuit-breaker-system)
- [Testing](#testing)
- [Integration](#integration)

## Overview

The Risk Manager Module provides comprehensive risk management for algorithmic trading systems. It implements multiple layers of protection to ensure trading operations stay within defined risk parameters.

**Key Features:**
- Pre-trade signal validation with 7+ risk checks
- Maximum position and exposure limits
- Multi-layered stop-loss protection (3 independent layers)
- Daily loss circuit breaker with automatic shutdown
- Symbol-specific leverage limits
- Manual reset requirement after circuit breaker trips
- Comprehensive testing coverage

**Risk Protection Layers:**
1. **Pre-Trade Validation**: Signal checks before execution
2. **Position Limits**: Maximum concurrent positions and exposure
3. **Stop-Loss Protection**: 3-layer independent protection system
4. **Circuit Breaker**: Daily loss limit with emergency shutdown

## Architecture

```
risk_manager/
├── __init__.py              # Module exports
├── models.py                # Data models and enums
├── risk_manager.py          # Main risk coordinator
├── circuit_breaker.py       # Daily loss monitoring
├── stop_loss_manager.py     # Multi-layer stop-loss
└── tests/
    ├── __init__.py
    └── test_risk_manager.py  # Comprehensive test suite
```

### Core Components

**RiskManager** (`risk_manager.py`)
- Main coordinator for all risk management
- Pre-trade signal validation
- Multi-layer protection orchestration
- Emergency position closure

**CircuitBreaker** (`circuit_breaker.py`)
- Daily loss monitoring and system shutdown
- Manual reset requirement after trip
- Position closure on limit breach
- Daily automatic reset at 00:00 UTC

**StopLossManager** (`stop_loss_manager.py`)
- 3-layer independent stop-loss protection
- Exchange stop orders (Layer 1)
- Application-level monitoring (Layer 2)
- Emergency liquidation (Layer 3)

**Data Models** (`models.py`)
- RiskValidation: Validation result with checks
- Protection: Multi-layer protection status
- CircuitBreakerStatus: Circuit breaker state and metrics
- Enums: ValidationStatus, CircuitBreakerState, ProtectionLayer

## Components

### RiskManager

Main risk management coordinator that validates signals and orchestrates protection layers.

**Initialization:**
```python
from workspace.features.risk_manager import RiskManager
from decimal import Decimal

risk_manager = RiskManager(
    starting_balance_chf=Decimal("2626.96"),
    max_daily_loss_chf=Decimal("-183.89"),  # -7%
    exchange=exchange_client,
    trade_executor=executor,
    position_tracker=tracker,
)
```

**Signal Validation:**
```python
# Validate trading signal before execution
validation = await risk_manager.validate_signal(signal)

if validation.approved:
    print(f"✅ Signal approved: {validation.status.value}")
    print(f"Checks passed: {len([c for c in validation.checks if c.passed])}")

    # Execute trade
    position = await executor.execute_signal(signal)

    # Start multi-layer protection
    protection = await risk_manager.start_multi_layer_protection(position)
else:
    print(f"❌ Signal rejected:")
    for reason in validation.rejection_reasons:
        print(f"   - {reason}")
```

**Validation Checks:**
```python
# View detailed validation results
for check in validation.checks:
    symbol = "✅" if check.passed else "❌"
    print(f"{symbol} {check.check_name}: {check.message}")
```

### CircuitBreaker

Daily loss monitoring with automatic system shutdown on limit breach.

**Initialization:**
```python
from workspace.features.risk_manager import CircuitBreaker
from decimal import Decimal

circuit_breaker = CircuitBreaker(
    starting_balance_chf=Decimal("2626.96"),
    max_daily_loss_chf=Decimal("-183.89"),  # -7%
    trade_executor=executor,
)
```

**Daily Loss Monitoring:**
```python
# Check daily loss (called periodically)
current_daily_pnl = Decimal("-150.00")
status = await circuit_breaker.check_daily_loss(current_daily_pnl)

if status.is_tripped():
    print(f"🚨 Circuit breaker TRIPPED!")
    print(f"Daily P&L: CHF {status.daily_pnl_chf:,.2f}")
    print(f"Loss: {status.loss_percentage():.2f}%")
    print(f"Reset token: {status.manual_reset_token}")
else:
    print(f"✅ Circuit breaker ACTIVE")
    print(f"Daily P&L: CHF {status.daily_pnl_chf:,.2f}")
    print(f"Remaining allowance: CHF {status.remaining_loss_allowance_chf():,.2f}")
```

**Manual Reset:**
```python
# Reset after circuit breaker trips (requires token)
reset_successful = await circuit_breaker.manual_reset(reset_token)

if reset_successful:
    print("✅ Circuit breaker reset successful")
else:
    print("❌ Invalid reset token")
```

**Daily Automatic Reset:**
```python
# Automatic reset at 00:00 UTC (runs in background)
await circuit_breaker.start_daily_reset_scheduler()
```

### StopLossManager

Multi-layered stop-loss protection with 3 independent layers.

**Initialization:**
```python
from workspace.features.risk_manager import StopLossManager

stop_loss_manager = StopLossManager(
    exchange=exchange_client,
    trade_executor=executor,
    check_interval_seconds=2,          # Layer 2 interval
    emergency_check_interval_seconds=1, # Layer 3 interval
)
```

**Start Protection:**
```python
# Start 3-layer protection for a position
protection = await stop_loss_manager.start_protection(
    position_id="pos_123",
    symbol="BTC/USDT:USDT",
    entry_price=Decimal("50000"),
    stop_loss_pct=Decimal("0.03"),  # 3%
    side="long",
)

print(f"Protection started: {protection.layer_count()} layers active")
print(f"Entry: ${protection.entry_price}")
print(f"Stop: ${protection.stop_loss_price}")

# Check layer statuses
if protection.exchange_stop_active:
    print(f"✅ Layer 1 (Exchange): Order {protection.exchange_stop_order_id}")
if protection.app_monitor_active:
    print(f"✅ Layer 2 (App Monitor): Checking every 2s")
if protection.emergency_monitor_active:
    print(f"✅ Layer 3 (Emergency): Monitoring >15% loss")
```

**Stop Protection:**
```python
# Stop protection when position closes
await stop_loss_manager.stop_protection("pos_123")
```

**Get Protection Status:**
```python
# Check protection status
protection = stop_loss_manager.get_protection("pos_123")

if protection:
    print(f"Protection active for {protection.symbol}")
    print(f"Layers: {protection.layer_count()}")
else:
    print("No protection found")
```

## Risk Limits

### Position Limits
- **Max Concurrent Positions**: 6
- **Max Position Size**: 20% of account balance
- **Max Total Exposure**: 80% of account balance

### Leverage Limits
- **Global Range**: 5x - 40x
- **Per-Symbol Limits:**
  - BTC/USDT:USDT: 40x
  - ETH/USDT:USDT: 40x
  - SOL/USDT:USDT: 25x
  - BNB/USDT:USDT: 25x
  - ADA/USDT:USDT: 20x
  - DOGE/USDT:USDT: 20x

### Stop-Loss Requirements
- **Min Stop-Loss**: 1%
- **Max Stop-Loss**: 10%

### Signal Requirements
- **Min Confidence**: 60%

### Daily Loss Limits
- **Max Daily Loss**: -7% of starting balance
- **Max Daily Loss (CHF)**: CHF -183.89 (from CHF 2,626.96)

## Usage

### Basic Setup

```python
from workspace.features.risk_manager import RiskManager
from decimal import Decimal

# Initialize risk manager
risk_manager = RiskManager(
    starting_balance_chf=Decimal("2626.96"),
    max_daily_loss_chf=Decimal("-183.89"),
    exchange=exchange,
    trade_executor=executor,
    position_tracker=tracker,
)
```

### Pre-Trade Workflow

```python
async def execute_trading_decision(signal):
    """Complete pre-trade validation and execution workflow"""

    # 1. Validate signal
    validation = await risk_manager.validate_signal(signal)

    # 2. Check validation result
    if not validation.approved:
        logger.warning(f"Signal rejected: {validation.rejection_reasons}")
        return None

    # 3. Log validation summary
    logger.info(f"Signal approved with {len(validation.checks)} checks:")
    for check in validation.checks:
        logger.info(f"  {check.check_name}: {check.message}")

    # 4. Execute trade
    position = await executor.execute_signal(signal)

    # 5. Start multi-layer protection
    protection = await risk_manager.start_multi_layer_protection(position)

    logger.info(
        f"Position opened with {protection.layer_count()} protection layers"
    )

    return position
```

### Position Closure Workflow

```python
async def close_position(position_id: str):
    """Close position and stop protection"""

    # 1. Close position
    result = await executor.close_position(position_id)

    # 2. Stop protection layers
    await risk_manager.stop_protection(position_id)

    logger.info(f"Position {position_id} closed, protection stopped")

    return result
```

### Emergency Closure

```python
async def emergency_close(position_id: str, reason: str):
    """Emergency position closure (bypasses validation)"""

    result = await risk_manager.emergency_close_position(
        position_id=position_id,
        reason=reason,
    )

    logger.critical(f"Emergency close executed: {reason}")

    return result
```

### Circuit Breaker Monitoring

```python
async def monitor_daily_loss():
    """Monitor daily P&L and circuit breaker status"""

    # Check circuit breaker status
    status = await risk_manager.check_daily_loss_limit()

    if status.is_tripped():
        logger.critical(
            f"🚨 Circuit breaker TRIPPED!\n"
            f"Daily P&L: CHF {status.daily_pnl_chf:,.2f}\n"
            f"Loss: {status.loss_percentage():.2f}%\n"
            f"Manual reset required with token: {status.manual_reset_token}"
        )

        # Send alerts
        await send_emergency_alert(status)

        return False  # Trading halted

    # Log current status
    logger.info(
        f"Circuit breaker active - "
        f"Daily P&L: CHF {status.daily_pnl_chf:,.2f} "
        f"({status.loss_percentage():.2f}%)"
    )

    return True  # Trading allowed
```

## Multi-Layer Stop-Loss Protection

The Risk Manager implements 3 independent protection layers that operate simultaneously:

### Layer 1: Exchange Stop-Loss Order (Primary)

**Purpose**: Primary protection using exchange native stop orders
**Implementation**: Stop-market order placed on exchange
**Trigger**: Executes when price hits stop level
**Reliability**: High (exchange-level execution)

```python
# Automatically placed when protection starts
protection = await stop_loss_manager.start_protection(...)

# Check status
if protection.exchange_stop_active:
    print(f"Exchange stop order: {protection.exchange_stop_order_id}")
```

### Layer 2: Application-Level Monitoring (Backup)

**Purpose**: Backup protection if exchange stop fails
**Implementation**: Background asyncio task checking price every 2 seconds
**Trigger**: Closes position at market if stop level breached
**Reliability**: High (independent of exchange)

```python
# Runs automatically in background
# Monitors price every 2 seconds
# Triggers market close if stop breached

# Example log output when triggered:
# ⚠️ Layer 2 (App Monitor) triggered for BTC/USDT:USDT:
# Price $48,400 hit stop $48,500
```

### Layer 3: Emergency Liquidation (Last Resort)

**Purpose**: Emergency protection for catastrophic losses
**Implementation**: Background asyncio task checking loss every 1 second
**Trigger**: Emergency close if loss exceeds 15%
**Reliability**: Maximum (fastest response)

```python
# Runs automatically in background
# Monitors loss percentage every 1 second
# Emergency threshold: 15% loss

# Example log output when triggered:
# 🚨 Layer 3 (EMERGENCY) triggered for BTC/USDT:USDT:
# Loss 16.2% exceeds threshold 15.0%
# 🚨 EMERGENCY CLOSE: BTC/USDT:USDT position pos_123
```

### Layer Coordination

All layers operate independently and simultaneously:

```python
protection = await stop_loss_manager.start_protection(
    position_id="pos_123",
    symbol="BTC/USDT:USDT",
    entry_price=Decimal("50000"),
    stop_loss_pct=Decimal("0.03"),  # 3% stop
)

# Check which layers are active
print(f"Active layers: {protection.layer_count()}")
print(f"Layer 1 (Exchange): {protection.exchange_stop_active}")
print(f"Layer 2 (App): {protection.app_monitor_active}")
print(f"Layer 3 (Emergency): {protection.emergency_monitor_active}")

# If any layer triggers, others are automatically deactivated
if protection.triggered_layer:
    print(f"Triggered by: {protection.triggered_layer.value}")
    print(f"Triggered at: {protection.triggered_at}")
```

## Circuit Breaker System

The circuit breaker monitors daily P&L and triggers emergency shutdown when loss limit is exceeded.

### States

**ACTIVE**: Normal operation, trading allowed
```python
status.state == CircuitBreakerState.ACTIVE
# Trading can proceed
```

**TRIPPED**: Loss limit exceeded, initiating shutdown
```python
status.state == CircuitBreakerState.TRIPPED
# Closing all positions
# Transitioning to MANUAL_RESET_REQUIRED
```

**MANUAL_RESET_REQUIRED**: Requires manual intervention
```python
status.state == CircuitBreakerState.MANUAL_RESET_REQUIRED
# All trading halted
# Manual reset required with token
# Token: status.manual_reset_token
```

**RECOVERING**: Transitioning back to active (future use)
```python
status.state == CircuitBreakerState.RECOVERING
# Gradual return to normal operation
```

### Trip Sequence

1. **Daily loss exceeds -7%** (CHF -183.89)
2. **State changes to TRIPPED**
3. **All positions closed** via trade executor
4. **State changes to MANUAL_RESET_REQUIRED**
5. **Reset token generated** (secure random hex)
6. **Critical alerts sent**
7. **Trading halted** until manual reset

### Manual Reset

```python
# After investigating cause of loss
reset_token = "abc123def456"  # From circuit breaker logs

success = await circuit_breaker.manual_reset(reset_token)

if success:
    print("✅ Circuit breaker reset - trading can resume")
else:
    print("❌ Invalid token - check logs for correct token")
```

### Daily Automatic Reset

Circuit breaker automatically resets at 00:00 UTC each day (if not tripped):

```python
# Start background scheduler (runs indefinitely)
asyncio.create_task(circuit_breaker.start_daily_reset_scheduler())

# Resets:
# - daily_pnl_chf to 0
# - daily_trade_count to 0
# - state to ACTIVE
# - Clears manual reset token
```

## Testing

The Risk Manager module includes comprehensive tests covering all components.

### Run All Tests

```bash
# Run complete test suite
python -m pytest workspace/features/risk_manager/tests/test_risk_manager.py -v

# Run with coverage
python -m pytest workspace/features/risk_manager/tests/ --cov=workspace.features.risk_manager --cov-report=html
```

### Test Coverage

**RiskManager Tests (6 tests)**
- Signal validation with valid signals
- Signal rejection (low confidence, large position, invalid stop-loss)
- Initialization and status checks

**CircuitBreaker Tests (6 tests)**
- Active state operation
- Trip on loss limit breach
- No trip within limit
- Loss percentage calculation
- Remaining allowance calculation
- Daily reset

**StopLossManager Tests (4 tests)**
- Protection creation
- Layer count verification
- Protection removal
- Get all protections

### Test Examples

**Test Signal Validation:**
```python
@pytest.mark.asyncio
async def test_validate_signal_approved(risk_manager):
    """Test signal validation with valid signal"""
    signal = MockSignal(
        confidence=Decimal("0.75"),
        size_pct=Decimal("0.15"),
        stop_loss_pct=Decimal("0.03"),
    )

    validation = await risk_manager.validate_signal(signal)

    assert validation.approved is True
    assert validation.status in [ValidationStatus.APPROVED, ValidationStatus.WARNING]
```

**Test Circuit Breaker:**
```python
@pytest.mark.asyncio
async def test_circuit_breaker_trips_on_loss(circuit_breaker):
    """Test circuit breaker trips when loss limit exceeded"""
    daily_pnl = Decimal("-200.00")  # Below -183.89 limit

    status = await circuit_breaker.check_daily_loss(daily_pnl)

    assert status.state in [CircuitBreakerState.TRIPPED,
                           CircuitBreakerState.MANUAL_RESET_REQUIRED]
```

**Test Stop-Loss Protection:**
```python
@pytest.mark.asyncio
async def test_start_protection_creates_protection(stop_loss_manager):
    """Test starting protection creates Protection object"""
    protection = await stop_loss_manager.start_protection(
        position_id="pos_123",
        symbol="BTC/USDT:USDT",
        entry_price=Decimal("50000"),
        stop_loss_pct=Decimal("0.03"),
    )

    assert protection.stop_loss_price == Decimal("48500")  # 3% below entry
    assert protection.layer_count() >= 2
```

## Integration

### With Trading Loop

```python
from workspace.features.risk_manager import RiskManager
from workspace.features.strategy import MeanReversionStrategy

async def trading_loop():
    """Complete trading loop with risk management"""

    # Initialize components
    risk_manager = RiskManager(...)
    strategy = MeanReversionStrategy()

    while True:
        # 1. Get market data
        market_data = await exchange.fetch_ohlcv(symbol, timeframe="3m")

        # 2. Generate signal
        signal = await strategy.generate_signal(market_data)

        # 3. Validate with risk manager
        validation = await risk_manager.validate_signal(signal)

        if not validation.approved:
            logger.info(f"Signal rejected: {validation.rejection_reasons}")
            await asyncio.sleep(180)  # Wait 3 minutes
            continue

        # 4. Execute trade
        position = await executor.execute_signal(signal)

        # 5. Start protection
        protection = await risk_manager.start_multi_layer_protection(position)

        logger.info(
            f"Trade executed with {protection.layer_count()} protection layers"
        )

        await asyncio.sleep(180)  # 3-minute intervals
```

### With Decision Engine

```python
async def make_trading_decision(llm_recommendation):
    """Process LLM recommendation through risk management"""

    # 1. Convert LLM recommendation to signal
    signal = convert_to_signal(llm_recommendation)

    # 2. Check circuit breaker first
    status = await risk_manager.check_daily_loss_limit()

    if status.is_tripped():
        logger.critical("Circuit breaker tripped - no trading allowed")
        return None

    # 3. Validate signal
    validation = await risk_manager.validate_signal(signal)

    # 4. Log validation details
    logger.info(f"Risk validation: {validation.status.value}")
    for check in validation.checks:
        logger.info(f"  {check.check_name}: {check.message}")

    # 5. Return decision
    if validation.approved:
        return signal
    else:
        logger.warning(f"Signal rejected: {validation.rejection_reasons}")
        return None
```

### Position Monitoring

```python
async def monitor_positions():
    """Monitor all active positions and protections"""

    while True:
        # Get all active protections
        protections = risk_manager.stop_loss_manager.get_all_protections()

        logger.info(f"Monitoring {len(protections)} positions")

        for pos_id, protection in protections.items():
            # Check layer statuses
            layers_active = protection.layer_count()

            # Log status
            logger.info(
                f"{protection.symbol}: {layers_active} layers, "
                f"Stop: ${protection.stop_loss_price}"
            )

            # Check if triggered
            if protection.triggered_layer:
                logger.warning(
                    f"Protection triggered for {protection.symbol}: "
                    f"{protection.triggered_layer.value}"
                )

        # Check circuit breaker
        cb_status = risk_manager.get_circuit_breaker_status()
        logger.info(
            f"Circuit breaker: {cb_status.state.value}, "
            f"Daily P&L: CHF {cb_status.daily_pnl_chf:,.2f}"
        )

        await asyncio.sleep(10)  # Check every 10 seconds
```

---

**Risk Manager Module** - Production-ready risk management system
**Version**: 1.0.0
**Author**: Risk Management Team
**Date**: 2025-10-28
