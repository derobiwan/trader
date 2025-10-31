# Task Brief: Validation Engineer 1 - Trade Execution & Position Management

**Agent**: Validation Engineer 1
**Priority**: CRITICAL
**Duration**: 3-4 hours
**Status**: READY TO START

## Mission
Create comprehensive test suites for trade execution, position management, and reconciliation modules to achieve 80-85% coverage from current 8-14%.

## Assigned Modules

### Critical Priority:
1. **trade_executor/executor_service.py** - 8% → 85% (393 statements, 361 missing)
2. **trade_executor/stop_loss_manager.py** - 12% → 85% (183 statements, 161 missing)
3. **trade_executor/reconciliation.py** - 14% → 85% (175 statements, 150 missing)
4. **position_manager/position_service.py** - 11% → 85% (230 statements, 205 missing)
5. **position_reconciliation/reconciliation_service.py** - 13% → 85% (177 statements, 154 missing)

**Total Impact**: ~1,500 statements coverage gain

## Context Files

### Code to Test:
- `/Users/tobiprivat/Documents/GitProjects/personal/trader/workspace/features/trade_executor/executor_service.py`
- `/Users/tobiprivat/Documents/GitProjects/personal/trader/workspace/features/trade_executor/stop_loss_manager.py`
- `/Users/tobiprivat/Documents/GitProjects/personal/trader/workspace/features/trade_executor/reconciliation.py`
- `/Users/tobiprivat/Documents/GitProjects/personal/trader/workspace/features/position_manager/position_service.py`
- `/Users/tobiprivat/Documents/GitProjects/personal/trader/workspace/features/position_reconciliation/reconciliation_service.py`

### Related Models:
- `/Users/tobiprivat/Documents/GitProjects/personal/trader/workspace/features/trade_executor/models.py`
- `/Users/tobiprivat/Documents/GitProjects/personal/trader/workspace/features/position_manager/models.py`
- `/Users/tobiprivat/Documents/GitProjects/personal/trader/workspace/features/position_reconciliation/models.py`

### Existing Tests (for patterns):
- `/Users/tobiprivat/Documents/GitProjects/personal/trader/workspace/tests/integration/test_trade_executor_signal_py.html`
- `/Users/tobiprivat/Documents/GitProjects/personal/trader/workspace/tests/integration/conftest.py`

### Fixtures:
- `/Users/tobiprivat/Documents/GitProjects/personal/trader/workspace/tests/integration/conftest.py`

## Test Requirements

### 1. ExecutorService Tests

**File**: `workspace/tests/unit/test_executor_service.py`

**Test Coverage Required**:
```python
class TestExecutorService:
    # Order Placement
    - test_place_market_order_success()
    - test_place_limit_order_success()
    - test_place_stop_order_success()
    - test_place_order_with_insufficient_balance()
    - test_place_order_with_invalid_symbol()
    - test_place_order_exchange_api_failure()
    - test_place_order_retry_logic()

    # Order Modification
    - test_modify_order_price()
    - test_modify_order_quantity()
    - test_modify_order_not_found()
    - test_modify_order_already_filled()

    # Order Cancellation
    - test_cancel_order_success()
    - test_cancel_order_not_found()
    - test_cancel_order_already_filled()
    - test_cancel_all_orders_for_symbol()

    # Order Status
    - test_get_order_status_pending()
    - test_get_order_status_filled()
    - test_get_order_status_cancelled()
    - test_sync_order_status_with_exchange()

    # Position Management
    - test_get_current_positions()
    - test_update_position_on_fill()
    - test_close_position_fully()
    - test_close_position_partially()

    # Error Handling
    - test_handle_exchange_rate_limit()
    - test_handle_network_timeout()
    - test_handle_insufficient_margin()
    - test_handle_invalid_order_params()
```

**Mocking Strategy**:
```python
# Mock ccxt Exchange
@pytest.fixture
def mock_exchange():
    with patch('ccxt.binance') as mock:
        mock.return_value.create_order = AsyncMock(return_value={
            'id': 'order_123',
            'status': 'open',
            'filled': 0,
            'remaining': 1.0
        })
        mock.return_value.fetch_order = AsyncMock()
        mock.return_value.cancel_order = AsyncMock()
        mock.return_value.fetch_positions = AsyncMock()
        yield mock
```

### 2. StopLossManager Tests

**File**: `workspace/tests/unit/test_stop_loss_manager.py`

**Test Coverage Required**:
```python
class TestStopLossManager:
    # Stop Loss Calculation
    - test_calculate_stop_loss_percentage()
    - test_calculate_stop_loss_atr_based()
    - test_calculate_stop_loss_with_volatility()

    # Trailing Stop
    - test_update_trailing_stop_price_up()
    - test_update_trailing_stop_keeps_best()
    - test_trailing_stop_activation()

    # Trigger Detection
    - test_check_stop_loss_triggered()
    - test_check_stop_loss_not_triggered()
    - test_multiple_position_stop_checks()

    # Stop Loss Execution
    - test_execute_stop_loss_market_order()
    - test_execute_stop_loss_with_slippage()
    - test_execute_stop_loss_partial_fill()

    # Edge Cases
    - test_stop_loss_with_zero_position()
    - test_stop_loss_with_extreme_volatility()
    - test_stop_loss_during_exchange_outage()
```

### 3. Reconciliation Tests

**File**: `workspace/tests/unit/test_trade_reconciliation.py`

**Test Coverage Required**:
```python
class TestTradeReconciliation:
    # Reconciliation Logic
    - test_reconcile_orders_all_match()
    - test_reconcile_orders_missing_local()
    - test_reconcile_orders_missing_exchange()
    - test_reconcile_positions_match()
    - test_reconcile_positions_drift()

    # Discrepancy Handling
    - test_handle_quantity_mismatch()
    - test_handle_price_mismatch()
    - test_handle_status_mismatch()
    - test_resolve_discrepancy_auto()
    - test_resolve_discrepancy_manual()

    # Position Reconciliation
    - test_reconcile_position_quantity()
    - test_reconcile_position_average_price()
    - test_reconcile_unrealized_pnl()
```

### 4. PositionService Tests

**File**: `workspace/tests/unit/test_position_service.py`

**Test Coverage Required**:
```python
class TestPositionService:
    # Position Creation
    - test_create_position_long()
    - test_create_position_short()
    - test_create_position_duplicate_symbol()

    # Position Updates
    - test_update_position_add_quantity()
    - test_update_position_reduce_quantity()
    - test_update_position_average_price()
    - test_update_position_realized_pnl()

    # Position Queries
    - test_get_position_by_symbol()
    - test_get_all_positions()
    - test_get_open_positions_only()
    - test_get_positions_with_pnl()

    # Position Closure
    - test_close_position_full()
    - test_close_position_partial()
    - test_close_multiple_positions()

    # State Management
    - test_position_state_transitions()
    - test_position_locks_concurrent_access()
```

### 5. PositionReconciliationService Tests

**File**: `workspace/tests/unit/test_position_reconciliation_service.py`

**Test Coverage Required**:
```python
class TestPositionReconciliationService:
    # Full Reconciliation
    - test_full_reconciliation_no_drift()
    - test_full_reconciliation_with_drift()
    - test_reconciliation_frequency_control()

    # Drift Detection
    - test_detect_quantity_drift()
    - test_detect_price_drift()
    - test_detect_unrealized_pnl_drift()
    - test_drift_threshold_configuration()

    # Correction Actions
    - test_correct_position_from_exchange()
    - test_correct_position_with_adjustment()
    - test_log_reconciliation_events()
```

## Mock Setup

### conftest.py Additions
```python
import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime
from decimal import Decimal

@pytest.fixture
def mock_ccxt_exchange():
    """Mock ccxt exchange for trade execution tests"""
    with patch('ccxt.binance') as mock_exchange:
        exchange = AsyncMock()
        exchange.create_order = AsyncMock()
        exchange.fetch_order = AsyncMock()
        exchange.cancel_order = AsyncMock()
        exchange.fetch_positions = AsyncMock()
        exchange.fetch_balance = AsyncMock()
        mock_exchange.return_value = exchange
        yield exchange

@pytest.fixture
def sample_order():
    """Sample order for testing"""
    return {
        'id': 'order_123',
        'symbol': 'BTC/USDT',
        'type': 'limit',
        'side': 'buy',
        'price': Decimal('50000.00'),
        'amount': Decimal('1.0'),
        'filled': Decimal('0.0'),
        'remaining': Decimal('1.0'),
        'status': 'open',
        'timestamp': datetime.utcnow().timestamp()
    }

@pytest.fixture
def sample_position():
    """Sample position for testing"""
    return {
        'symbol': 'BTC/USDT',
        'side': 'long',
        'contracts': Decimal('1.0'),
        'entry_price': Decimal('50000.00'),
        'mark_price': Decimal('51000.00'),
        'unrealized_pnl': Decimal('1000.00'),
        'leverage': 10
    }

@pytest.fixture
async def executor_service(mock_ccxt_exchange):
    """ExecutorService instance with mocked exchange"""
    from workspace.features.trade_executor.executor_service import ExecutorService
    service = ExecutorService(exchange=mock_ccxt_exchange)
    yield service
    await service.cleanup()
```

## Quality Standards

### Coverage Requirements:
- **executor_service.py**: 8% → 85% (331 new statements covered)
- **stop_loss_manager.py**: 12% → 85% (139 new statements)
- **reconciliation.py**: 14% → 85% (125 new statements)
- **position_service.py**: 11% → 85% (173 new statements)
- **reconciliation_service.py**: 13% → 85% (132 new statements)

### Test Quality:
- All async functions tested with `@pytest.mark.asyncio`
- All external APIs mocked (no real exchange calls)
- All edge cases covered (errors, None values, empty lists)
- All state transitions tested
- All error paths tested

### Verification Commands:
```bash
# Run your test suite
pytest workspace/tests/unit/test_executor_service.py -v
pytest workspace/tests/unit/test_stop_loss_manager.py -v
pytest workspace/tests/unit/test_trade_reconciliation.py -v
pytest workspace/tests/unit/test_position_service.py -v
pytest workspace/tests/unit/test_position_reconciliation_service.py -v

# Check coverage
pytest --cov=workspace.features.trade_executor \
       --cov=workspace.features.position_manager \
       --cov=workspace.features.position_reconciliation \
       workspace/tests/unit/test_executor_service.py \
       workspace/tests/unit/test_stop_loss_manager.py \
       workspace/tests/unit/test_trade_reconciliation.py \
       workspace/tests/unit/test_position_service.py \
       workspace/tests/unit/test_position_reconciliation_service.py \
       --cov-report=term-missing
```

## Deliverables

1. **5 new test files** with comprehensive coverage
2. **Updated conftest.py** with fixtures for your modules
3. **Coverage report** showing 85%+ for all assigned modules
4. **All tests passing** (100% pass rate)
5. **Documentation** in test docstrings

## Coordination

- **No conflicts with**: Other validation engineers (separate modules)
- **Share fixtures in**: `workspace/tests/unit/conftest.py` or `workspace/tests/integration/conftest.py`
- **Update progress in**: Your agent changelog
- **Report blockers to**: PRP Orchestrator

## Success Criteria

- [ ] All 5 test files created
- [ ] executor_service.py coverage: 85%+
- [ ] stop_loss_manager.py coverage: 85%+
- [ ] reconciliation.py coverage: 85%+
- [ ] position_service.py coverage: 85%+
- [ ] reconciliation_service.py coverage: 85%+
- [ ] All tests pass
- [ ] No regressions in existing tests
- [ ] Code follows project standards

---

**BEGIN IMMEDIATELY - This is the highest priority module group!**
