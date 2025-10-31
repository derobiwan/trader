# Agent Coordination Summary - Test Coverage Improvement

**Date**: 2025-10-30
**Orchestrator**: PRP Orchestrator
**Workflow**: PARALLEL VALIDATION WORKFLOW

## Quick Reference

**Current Coverage**: 27% (3052/11389 statements)
**Target Coverage**: 80%+ (9111+ statements)
**Gap to Close**: ~6,000 statements
**Agents Needed**: 5 validation engineers (parallel execution)
**Estimated Time**: 4-6 hours (parallel), 20-25 hours (sequential)

## Agent Assignments

### Team 1: Trade Execution & Position Management
**Agent**: `validation-engineer-1`
**Priority**: CRITICAL (8-14% current coverage)
**Modules**:
- trade_executor/executor_service.py (8%)
- trade_executor/stop_loss_manager.py (12%)
- trade_executor/reconciliation.py (14%)
- position_manager/position_service.py (11%)
- position_reconciliation/reconciliation_service.py (13%)

**Output**: `workspace/tests/unit/test_executor_service.py` + 4 other test files
**Coverage Gain**: ~1,500 statements
**Task Brief**: `/Users/tobiprivat/Documents/GitProjects/personal/trader/docs/TASK_BRIEF_VALIDATION_ENGINEER_1.md`

---

### Team 2: Risk Management & Circuit Breakers
**Agent**: `validation-engineer-2`
**Priority**: HIGH (15-33% current coverage)
**Modules**:
- risk_manager/risk_manager.py (27%)
- risk_manager/circuit_breaker.py (22%)
- risk_manager/stop_loss_manager.py (15%)
- risk_manager/risk_metrics.py (25%)
- risk_manager/correlation_analysis.py (19%)
- risk_manager/position_sizing.py (33%)
- error_recovery/circuit_breaker.py (31%)

**Output**: `workspace/tests/unit/test_risk_management_suite.py`
**Coverage Gain**: ~1,200 statements

**Key Tests**:
- Circuit breaker state transitions (CLOSED → OPEN → HALF_OPEN)
- Risk limit validation (max position size, max leverage)
- Position sizing calculations (Kelly, fixed fractional, volatility-based)
- Stop-loss calculations (ATR-based, percentage, trailing)
- Correlation analysis (portfolio diversification)
- Risk metrics (VaR, Sharpe ratio, max drawdown)

---

### Team 3: Decision Engine & LLM Integration
**Agent**: `validation-engineer-3`
**Priority**: HIGH (13-19% current coverage)
**Modules**:
- decision_engine/llm_engine.py (19%)
- decision_engine/prompt_builder.py (13%)
- caching/cache_service.py (15%)
- infrastructure/cache/redis_manager.py (14%)

**Output**: `workspace/tests/unit/test_decision_engine_suite.py`
**Coverage Gain**: ~900 statements

**Key Tests**:
- LLM API integration (OpenRouter mock)
- Prompt construction with market data
- Response parsing and validation
- Cache hits/misses/TTL logic
- Redis operations (get, set, delete, expire)
- Rate limiting and retry logic
- Error handling for LLM failures

---

### Team 4: Market Data & WebSocket Infrastructure
**Agent**: `validation-engineer-4`
**Priority**: HIGH (15-28% current coverage)
**Modules**:
- market_data/market_data_service.py (15%)
- market_data/websocket_client.py (18%)
- market_data/websocket_health.py (26%)
- market_data/websocket_reconnection.py (28%)
- market_data/indicators.py (17%)

**Output**: `workspace/tests/unit/test_market_data_suite.py`
**Coverage Gain**: ~800 statements

**Key Tests**:
- WebSocket connection/disconnection
- Message handling and parsing
- Reconnection logic (exponential backoff)
- Health monitoring and heartbeat
- Technical indicators (RSI, MACD, Bollinger Bands, EMA)
- OHLCV data aggregation
- Error handling for connection failures

---

### Team 5: Trading Loop, Scheduler & Monitoring
**Agent**: `validation-engineer-5`
**Priority**: HIGH (14-35% current coverage)
**Modules**:
- trading_loop/trading_engine.py (35%)
- trading_loop/scheduler.py (17%)
- paper_trading/paper_executor.py (25%)
- paper_trading/virtual_portfolio.py (14%)
- paper_trading/performance_tracker.py (15%)
- monitoring/metrics/metrics_service.py (28%)
- trade_history/trade_history_service.py (15%)

**Output**: `workspace/tests/unit/test_trading_operations_suite.py`
**Coverage Gain**: ~1,100 statements

**Key Tests**:
- Trading loop execution flow
- Scheduler timing (3-minute intervals)
- Paper trading simulation
- Virtual portfolio P&L calculations
- Performance metrics (ROI, Sharpe, drawdown)
- Trade history persistence
- Metrics collection and aggregation

---

## Activation Commands

### For User to Execute:

```bash
# Option 1: Launch agents one-by-one in Claude Code
# In Claude Code, start 5 separate conversations:

# Conversation 1:
"You are Validation Engineer 1. Read /Users/tobiprivat/Documents/GitProjects/personal/trader/docs/TASK_BRIEF_VALIDATION_ENGINEER_1.md and implement all required tests."

# Conversation 2:
"You are Validation Engineer 2. Implement comprehensive tests for Risk Management modules:
- risk_manager/risk_manager.py (27% → 85%)
- risk_manager/circuit_breaker.py (22% → 85%)
- risk_manager/stop_loss_manager.py (15% → 85%)
- risk_manager/risk_metrics.py (25% → 85%)
- risk_manager/correlation_analysis.py (19% → 85%)
- error_recovery/circuit_breaker.py (31% → 85%)
Output: workspace/tests/unit/test_risk_management_suite.py"

# Conversation 3:
"You are Validation Engineer 3. Implement comprehensive tests for Decision Engine modules:
- decision_engine/llm_engine.py (19% → 85%)
- decision_engine/prompt_builder.py (13% → 85%)
- caching/cache_service.py (15% → 85%)
- infrastructure/cache/redis_manager.py (14% → 85%)
Output: workspace/tests/unit/test_decision_engine_suite.py"

# Conversation 4:
"You are Validation Engineer 4. Implement comprehensive tests for Market Data modules:
- market_data/market_data_service.py (15% → 85%)
- market_data/websocket_client.py (18% → 85%)
- market_data/websocket_health.py (26% → 85%)
- market_data/websocket_reconnection.py (28% → 85%)
- market_data/indicators.py (17% → 85%)
Output: workspace/tests/unit/test_market_data_suite.py"

# Conversation 5:
"You are Validation Engineer 5. Implement comprehensive tests for Trading Operations modules:
- trading_loop/trading_engine.py (35% → 85%)
- trading_loop/scheduler.py (17% → 85%)
- paper_trading/paper_executor.py (25% → 85%)
- paper_trading/virtual_portfolio.py (14% → 85%)
- paper_trading/performance_tracker.py (15% → 85%)
- monitoring/metrics/metrics_service.py (28% → 85%)
- trade_history/trade_history_service.py (15% → 85%)
Output: workspace/tests/unit/test_trading_operations_suite.py"

# Option 2: Sequential in single conversation (slower)
# Work through each team's tests one at a time
```

---

## Testing Standards Reference

### All Tests Must:
1. Use pytest with async support (`@pytest.mark.asyncio`)
2. Mock external services (LLM, exchange, Redis, PostgreSQL)
3. Test edge cases and error paths
4. Be isolated and deterministic
5. Follow existing patterns in `workspace/tests/unit/`

### Mock Strategy:
```python
# External APIs
- OpenRouter: pytest-httpx or respx
- Exchange: Mock ccxt Exchange class
- Redis: fakeredis or pytest fixtures
- PostgreSQL: SQLAlchemy test fixtures
- WebSocket: Mock websockets.connect()
```

### Verification:
```bash
# Run specific test suite
pytest workspace/tests/unit/test_<suite_name>.py -v

# Check coverage for specific modules
pytest --cov=workspace.features.<module> workspace/tests/unit/test_<suite_name>.py --cov-report=term-missing

# Run all tests
pytest workspace/tests/unit/ -v

# Full coverage report
pytest --cov=workspace workspace/tests/ --cov-report=html
```

---

## Coordination Protocol

### Phase 1: Implementation (Parallel)
- Each agent works independently on their assigned modules
- No coordination needed (separate files, separate modules)
- Each agent verifies their tests pass locally

### Phase 2: Integration (Orchestrator)
- Collect all test suites
- Run full test suite: `pytest workspace/tests/unit/ -v`
- Generate coverage report
- Verify >80% total coverage
- Resolve any conflicts

### Phase 3: Deployment
- Create comprehensive commit
- Push to branch
- Verify CI/CD passes

---

## Expected Outcomes

### Quantitative:
- Total coverage: 27% → 80%+
- Critical modules: <20% → 85%+
- All tests passing: 100%
- CI/CD green

### Qualitative:
- Production-ready test suites
- Maintainable and extendable tests
- Consistent mock patterns
- Comprehensive edge case coverage

---

## Notes for Orchestrator

Since we cannot directly spawn multiple agent instances in this session, we have two approaches:

**Approach 1 (Recommended - True Parallel)**:
- User opens 5 separate Claude Code conversations
- Each conversation becomes a dedicated Validation Engineer
- True parallel execution (4-6 hours total)
- Orchestrator integrates results afterward

**Approach 2 (Sequential - Single Session)**:
- Work through each team's tests one at a time in this session
- Sequential execution (20-25 hours total)
- Immediate integration as we go

**Recommendation**: Use Approach 1 for time efficiency, or Approach 2 if user prefers single-session coordination.

---

**Orchestrator is ready to coordinate. Awaiting user decision on approach.**
