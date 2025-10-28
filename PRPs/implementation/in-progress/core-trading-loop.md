# PRP: Core Trading Loop Implementation

## Metadata
- **PRP Type**: Implementation
- **Feature**: Core Trading Loop
- **Priority**: Critical
- **Estimated Effort**: 34 story points
- **Dependencies**: Database Schema, Position Management, All Service Components
- **Target Directory**: workspace/features/core/

## Context

### Business Requirements
The core trading loop is the heart of the LLM Crypto Trading System. It orchestrates all components to execute trading decisions every 3 minutes, managing the complete lifecycle from market analysis to trade execution.

### Technical Context
- **Architecture**: Event-driven async with Celery Beat scheduler
- **Interval**: 3 minutes (480 cycles/day)
- **Latency Target**: <2 seconds total decision time
- **Error Handling**: Graceful degradation with circuit breakers
- **State Management**: PostgreSQL for persistence, Redis for caching

### Dependencies
```python
# External Dependencies
- celery==5.3.4
- redis==5.0.1
- asyncio (built-in)
- ccxt==4.1.0
- httpx==0.25.2

# Internal Components (must be implemented first)
- market_data_service
- decision_engine
- trade_executor
- risk_manager
- position_manager
```

## Implementation Requirements

### 1. Main Trading Loop Entry Point

**File**: `workspace/features/core/trading_loop.py`

```python
import asyncio
from datetime import datetime, UTC
from typing import Optional, Dict, Any
import logging
from decimal import Decimal

from celery import Celery
from celery.schedules import crontab

from ..market_data.service import MarketDataService
from ..decision_engine.service import DecisionEngine
from ..trade_executor.service import TradeExecutor
from ..risk_manager.service import RiskManager
from ..position_manager.service import PositionManager
from ..monitoring.metrics import MetricsCollector
from ..database.session import get_db_session

logger = logging.getLogger(__name__)

class TradingLoop:
    """
    Main trading loop orchestrator.
    Coordinates all components for the 3-minute trading cycle.
    """

    def __init__(self):
        self.market_data = MarketDataService()
        self.decision_engine = DecisionEngine()
        self.trade_executor = TradeExecutor()
        self.risk_manager = RiskManager()
        self.position_manager = PositionManager()
        self.metrics = MetricsCollector()
        self.is_running = False
        self.circuit_breaker_triggered = False

    async def execute_trading_cycle(self) -> Dict[str, Any]:
        """
        Execute one complete trading cycle.

        Returns:
            Dict containing cycle results and metrics
        """
        cycle_start = datetime.now(UTC)
        cycle_id = f"cycle_{cycle_start.timestamp()}"

        try:
            # Step 1: Pre-cycle checks
            if not await self._pre_cycle_checks():
                return {"status": "skipped", "reason": "pre-checks failed"}

            # Step 2: Fetch market data (target: <500ms)
            market_data = await self._fetch_market_data()

            # Step 3: Get current positions (target: <100ms)
            positions = await self._get_current_positions()

            # Step 4: Calculate risk metrics (target: <100ms)
            risk_metrics = await self._calculate_risk_metrics(positions)

            # Step 5: Generate trading signals (target: <1000ms)
            signals = await self._generate_signals(
                market_data,
                positions,
                risk_metrics
            )

            # Step 6: Validate signals (target: <100ms)
            validated_signals = await self._validate_signals(
                signals,
                risk_metrics
            )

            # Step 7: Execute trades (target: <200ms per trade)
            execution_results = await self._execute_trades(validated_signals)

            # Step 8: Post-trade reconciliation (target: <100ms)
            await self._reconcile_positions()

            # Step 9: Update metrics
            cycle_duration = (datetime.now(UTC) - cycle_start).total_seconds()
            await self._update_metrics(cycle_id, cycle_duration, execution_results)

            return {
                "status": "completed",
                "cycle_id": cycle_id,
                "duration": cycle_duration,
                "trades_executed": len(execution_results),
                "signals_generated": len(signals),
                "timestamp": cycle_start.isoformat()
            }

        except Exception as e:
            logger.error(f"Trading cycle failed: {e}", exc_info=True)
            await self._handle_cycle_error(cycle_id, e)
            return {
                "status": "error",
                "cycle_id": cycle_id,
                "error": str(e),
                "timestamp": cycle_start.isoformat()
            }
```

### 2. Scheduler Configuration

**File**: `workspace/features/core/scheduler.py`

```python
from celery import Celery
from celery.schedules import crontab
import os

# Celery configuration
app = Celery('trading_bot')
app.config_from_object('config.celery_config')

# Schedule trading cycle every 3 minutes
app.conf.beat_schedule = {
    'trading-cycle': {
        'task': 'core.tasks.execute_trading_cycle',
        'schedule': 180.0,  # 3 minutes in seconds
        'options': {
            'expires': 170.0,  # Expire if not executed within time
            'priority': 10,  # Highest priority
        }
    },
    'position-reconciliation': {
        'task': 'core.tasks.reconcile_positions',
        'schedule': 300.0,  # Every 5 minutes
        'options': {
            'priority': 8,
        }
    },
    'performance-report': {
        'task': 'core.tasks.generate_performance_report',
        'schedule': crontab(hour=0, minute=0),  # Daily at midnight
        'options': {
            'priority': 5,
        }
    },
    'health-check': {
        'task': 'core.tasks.system_health_check',
        'schedule': 60.0,  # Every minute
        'options': {
            'priority': 3,
        }
    }
}

@app.task(bind=True, max_retries=3)
async def execute_trading_cycle(self):
    """Celery task for trading cycle execution."""
    from .trading_loop import TradingLoop

    loop = TradingLoop()
    result = await loop.execute_trading_cycle()

    if result['status'] == 'error':
        # Retry with exponential backoff
        raise self.retry(countdown=2 ** self.request.retries)

    return result
```

### 3. Error Handling and Recovery

**File**: `workspace/features/core/error_handler.py`

```python
import asyncio
from enum import Enum
from typing import Optional, Callable, Any
import logging

logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    LOW = "low"        # Log and continue
    MEDIUM = "medium"  # Alert and continue with degradation
    HIGH = "high"      # Close positions and pause
    CRITICAL = "critical"  # Emergency shutdown

class ErrorHandler:
    """
    Centralized error handling with recovery strategies.
    """

    def __init__(self):
        self.error_counts = {}
        self.recovery_strategies = {
            "connection_error": self._recover_connection,
            "api_error": self._recover_api,
            "data_error": self._recover_data,
            "execution_error": self._recover_execution,
        }

    async def handle_error(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle errors with appropriate recovery strategy.
        """
        error_type = self._classify_error(error)
        severity = self._determine_severity(error_type, context)

        # Log error with context
        logger.error(
            f"Error in {context.get('component', 'unknown')}: {error}",
            extra={
                "error_type": error_type,
                "severity": severity.value,
                "context": context
            }
        )

        # Track error frequency
        self._track_error(error_type)

        # Execute recovery strategy
        recovery_result = await self._execute_recovery(
            error_type,
            severity,
            context
        )

        return {
            "error_type": error_type,
            "severity": severity.value,
            "recovery_attempted": recovery_result['attempted'],
            "recovery_successful": recovery_result['successful'],
            "action_taken": recovery_result['action']
        }

    async def _execute_recovery(
        self,
        error_type: str,
        severity: ErrorSeverity,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute appropriate recovery strategy."""

        if severity == ErrorSeverity.CRITICAL:
            return await self._emergency_shutdown(context)

        if severity == ErrorSeverity.HIGH:
            return await self._safe_mode_activation(context)

        # Try specific recovery strategy
        if error_type in self.recovery_strategies:
            strategy = self.recovery_strategies[error_type]
            return await strategy(context)

        return {
            "attempted": False,
            "successful": False,
            "action": "no_recovery_available"
        }
```

### 4. State Management

**File**: `workspace/features/core/state_manager.py`

```python
from enum import Enum
from datetime import datetime, UTC
import asyncio
from typing import Optional, Dict, Any

class SystemState(Enum):
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    SAFE_MODE = "safe_mode"  # Limited functionality
    EMERGENCY_STOP = "emergency_stop"  # All positions closed
    MAINTENANCE = "maintenance"
    SHUTTING_DOWN = "shutting_down"

class StateManager:
    """
    Manages system state and state transitions.
    """

    def __init__(self, db_session):
        self.db_session = db_session
        self.current_state = SystemState.INITIALIZING
        self.state_history = []
        self.state_lock = asyncio.Lock()

    async def transition_to(
        self,
        new_state: SystemState,
        reason: str
    ) -> bool:
        """
        Transition to new state with validation.
        """
        async with self.state_lock:
            # Validate state transition
            if not self._is_valid_transition(self.current_state, new_state):
                logger.warning(
                    f"Invalid state transition: {self.current_state} -> {new_state}"
                )
                return False

            # Record state change
            old_state = self.current_state
            self.current_state = new_state

            # Log to history
            self.state_history.append({
                "from_state": old_state.value,
                "to_state": new_state.value,
                "reason": reason,
                "timestamp": datetime.now(UTC).isoformat()
            })

            # Persist to database
            await self._persist_state_change(old_state, new_state, reason)

            # Execute state-specific actions
            await self._execute_state_actions(new_state)

            logger.info(
                f"State transition: {old_state.value} -> {new_state.value} "
                f"(reason: {reason})"
            )

            return True

    def _is_valid_transition(
        self,
        from_state: SystemState,
        to_state: SystemState
    ) -> bool:
        """
        Validate if state transition is allowed.
        """
        valid_transitions = {
            SystemState.INITIALIZING: [
                SystemState.RUNNING,
                SystemState.MAINTENANCE
            ],
            SystemState.RUNNING: [
                SystemState.PAUSED,
                SystemState.SAFE_MODE,
                SystemState.EMERGENCY_STOP,
                SystemState.MAINTENANCE,
                SystemState.SHUTTING_DOWN
            ],
            SystemState.PAUSED: [
                SystemState.RUNNING,
                SystemState.MAINTENANCE,
                SystemState.SHUTTING_DOWN
            ],
            SystemState.SAFE_MODE: [
                SystemState.RUNNING,
                SystemState.EMERGENCY_STOP,
                SystemState.SHUTTING_DOWN
            ],
            SystemState.EMERGENCY_STOP: [
                SystemState.MAINTENANCE,
                SystemState.SHUTTING_DOWN
            ],
            SystemState.MAINTENANCE: [
                SystemState.RUNNING,
                SystemState.SHUTTING_DOWN
            ],
            SystemState.SHUTTING_DOWN: []  # Terminal state
        }

        return to_state in valid_transitions.get(from_state, [])
```

### 5. Integration Points

**File**: `workspace/features/core/integration.py`

```python
class ComponentIntegration:
    """
    Manages integration between all trading components.
    """

    def __init__(self):
        self.components = {}
        self.health_status = {}

    async def initialize_components(self) -> bool:
        """
        Initialize and verify all components.
        """
        try:
            # Initialize in dependency order
            self.components['database'] = await self._init_database()
            self.components['redis'] = await self._init_redis()
            self.components['market_data'] = await self._init_market_data()
            self.components['position_manager'] = await self._init_position_manager()
            self.components['risk_manager'] = await self._init_risk_manager()
            self.components['decision_engine'] = await self._init_decision_engine()
            self.components['trade_executor'] = await self._init_trade_executor()
            self.components['monitoring'] = await self._init_monitoring()

            # Verify all components healthy
            for name, component in self.components.items():
                health = await self._check_component_health(component)
                self.health_status[name] = health
                if not health['healthy']:
                    logger.error(f"Component {name} failed health check")
                    return False

            logger.info("All components initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Component initialization failed: {e}")
            return False
```

## Validation Requirements

### Level 1: Unit Tests
```python
# Tests for workspace/features/core/tests/test_trading_loop.py

async def test_trading_cycle_execution():
    """Test complete trading cycle execution."""
    loop = TradingLoop()
    result = await loop.execute_trading_cycle()
    assert result['status'] in ['completed', 'skipped']
    assert result['duration'] < 2.0  # Under 2 seconds

async def test_circuit_breaker_activation():
    """Test circuit breaker triggers at -7% loss."""
    loop = TradingLoop()
    # Simulate -7% loss
    loop.risk_manager.daily_pnl = Decimal('-183.89')
    result = await loop.execute_trading_cycle()
    assert result['status'] == 'skipped'
    assert result['reason'] == 'circuit_breaker_triggered'

async def test_error_recovery():
    """Test error handling and recovery."""
    handler = ErrorHandler()
    error = ConnectionError("WebSocket disconnected")
    result = await handler.handle_error(error, {'component': 'market_data'})
    assert result['recovery_attempted'] == True
```

### Level 2: Integration Tests
```python
# Tests for workspace/features/core/tests/test_integration.py

async def test_component_initialization():
    """Test all components initialize properly."""
    integration = ComponentIntegration()
    success = await integration.initialize_components()
    assert success == True
    assert len(integration.components) == 8

async def test_end_to_end_trading_flow():
    """Test complete trading flow from market data to execution."""
    # Setup test environment
    # Execute full cycle
    # Verify results
```

### Level 3: Edge Cases
- WebSocket disconnection during cycle
- LLM timeout during signal generation
- Partial order fills
- Database connection loss
- Redis cache miss
- Multiple simultaneous errors

### Level 4: Performance Tests
- Cycle completion under 2 seconds
- 1000 cycles without memory leak
- Concurrent cycle handling
- Recovery time after crash

## Acceptance Criteria

### Must Have
- [x] Trading cycle executes every 3 minutes
- [x] Complete cycle under 2 seconds
- [x] Error handling with recovery
- [x] State management with persistence
- [x] Component health monitoring
- [x] Circuit breaker at -7% daily loss
- [x] Position reconciliation after trades

### Should Have
- [x] Graceful degradation on component failure
- [x] Detailed cycle metrics
- [x] Retry logic with backoff
- [x] State transition validation
- [x] Component dependency management

### Nice to Have
- [ ] Hot reload configuration
- [ ] Dynamic cycle interval adjustment
- [ ] Multi-strategy support
- [ ] A/B testing framework

## Implementation Notes

### Critical Considerations
1. **Async Everything**: Use asyncio throughout for non-blocking execution
2. **Error Boundaries**: Each component call wrapped in try/except
3. **Timeouts**: Every external call has timeout (httpx: 5s, database: 1s)
4. **Idempotency**: Cycles can be safely retried
5. **Observability**: Comprehensive logging and metrics

### Performance Optimizations
1. **Parallel Execution**: Fetch market data for all assets concurrently
2. **Connection Pooling**: Reuse database/Redis connections
3. **Caching**: Cache static data (asset info, trading rules)
4. **Batch Operations**: Group database writes

### Security Considerations
1. **No Credentials in Code**: All from environment variables
2. **Audit Logging**: Every trade decision logged
3. **Rate Limiting**: Respect exchange limits
4. **Input Validation**: Sanitize all external data

## Testing Checklist

- [ ] Unit tests pass (>80% coverage)
- [ ] Integration tests pass
- [ ] Performance tests meet targets
- [ ] Error scenarios handled
- [ ] State transitions work correctly
- [ ] Scheduler triggers on time
- [ ] Metrics collected accurately
- [ ] Logs structured properly
- [ ] Documentation complete

## Handoff Notes

### For Implementation Specialist
1. Start with state management (foundation)
2. Implement component initialization next
3. Build trading cycle step by step
4. Add error handling throughout
5. Integrate scheduler last

### For Validation Engineer
1. Focus on cycle timing tests
2. Verify error recovery works
3. Test circuit breaker thoroughly
4. Validate state transitions
5. Check metric accuracy

### For DevOps Engineer
1. Celery Beat configuration
2. Redis setup for scheduler
3. Monitoring dashboard setup
4. Alert rules configuration
5. Log aggregation setup

---

**PRP Status**: Ready for Implementation
**Estimated Hours**: 68 hours (34 story points)
**Priority**: Critical - Core System Component
**Dependencies**: All service components must be built first
