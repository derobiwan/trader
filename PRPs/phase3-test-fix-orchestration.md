# Phase 3 Test Fix Orchestration Plan

## Executive Summary

**Objective**: Fix 80 failing tests to achieve 100% pass rate (1,062/1,062)
**Current State**: 982/1,062 passing (92.5% pass rate)
**Timeline**: 9 hours total (3 waves, parallelized to 4 hours wall clock time)
**Teams Required**: 6 parallel implementation specialist teams

---

## Failure Analysis by Category

### Category A: Decision Engine Mock Issues (11 failures)
**Root Cause**: Mock Ticker objects missing `quote_volume_24h` attribute
**Complexity**: LOW
**Files Affected**:
- `test_decision_engine_core.py`
- `test_prompt_builder.py`

**Specific Failures**:
```
- test_generate_signals_cache_miss_calls_llm
- test_generate_signals_caches_response
- test_generate_signals_usage_data_populated
- test_prompt_builder_empty_positions
- test_prompt_builder_no_positions_arg
- test_prompt_builder_large_capital
- test_prompt_builder_zero_capital
- test_prompt_builder_no_indicators
- test_prompt_format_snapshot_multiple_symbols
- test_generate_signals_partial_response
- test_generate_signals_with_all_parameters
```

### Category B: Paper Executor Precision (26 failures)
**Root Cause**: Decimal precision mismatches (>8 decimal places in implementation)
**Complexity**: LOW
**Files Affected**:
- `test_paper_executor.py` (14 tests)
- `test_performance_tracker.py` (12 tests)

**Key Issue**: Implementation returns Decimal with excessive precision, tests expect 8 decimal places

### Category C: Position Service Database Integration (32 failures)
**Root Cause**: Database session mocking and async context issues
**Complexity**: MEDIUM
**Files Affected**:
- `test_position_service.py` (32 tests)

**Key Issues**:
- Database session fixture not properly configured
- Async context manager issues
- Transaction rollback handling

### Category D: Strategy Test Mock Issues (8 failures)
**Root Cause**: Market snapshot mock structure mismatch
**Complexity**: LOW
**Files Affected**:
- `test_strategies.py` (8 tests)

### Category E: LLM Engine Integration (2 failures)
**Root Cause**: OpenRouter API mock configuration
**Complexity**: LOW
**Files Affected**:
- `test_llm_engine.py` (2 tests)

### Category F: Prompt Builder Output Format (1 failure)
**Root Cause**: JSON schema validation issue
**Complexity**: LOW
**Files Affected**:
- `test_prompt_builder.py` (1 test)

---

## Team Structure and Assignment

### Wave 1 Teams (Quick Wins - 2 hours)

#### Team Fix-Echo
**Focus**: Decision Engine Mock Fixes
**Tests to Fix**: 11
**Complexity**: LOW
**Estimated Time**: 1 hour

#### Team Fix-Foxtrot
**Focus**: Paper Executor Precision
**Tests to Fix**: 26
**Complexity**: LOW
**Estimated Time**: 2 hours

#### Team Fix-Golf
**Focus**: Strategy & LLM Mocks
**Tests to Fix**: 11 (8 strategy + 2 LLM + 1 prompt)
**Complexity**: LOW
**Estimated Time**: 1 hour

### Wave 2 Team (Medium Complexity - 2 hours)

#### Team Fix-Hotel
**Focus**: Position Service Database Integration
**Tests to Fix**: 32
**Complexity**: MEDIUM
**Estimated Time**: 2 hours

---

## Execution Plan

### Wave 1: Quick Wins (Parallel Execution)
**Teams**: Echo, Foxtrot, Golf
**Total Tests**: 48
**Wall Clock Time**: 2 hours
**Expected Result**: 1,030/1,062 passing (97% pass rate)

### Wave 2: Database Integration
**Teams**: Hotel
**Total Tests**: 32
**Wall Clock Time**: 2 hours
**Expected Result**: 1,062/1,062 passing (100% pass rate)

---

## Team Activation Commands

### Wave 1 Activation (Execute Simultaneously)

#### Team Fix-Echo Activation
```bash
# Team Fix-Echo: Decision Engine Mock Fixes (11 tests)
"Implementation Specialist Echo, you are assigned to fix decision engine mock issues.

OBJECTIVE: Fix 11 failing tests in decision_engine by adding missing mock attributes.

ROOT CAUSE: Mock Ticker objects missing 'quote_volume_24h' attribute.

FILES TO MODIFY:
- workspace/features/decision_engine/tests/conftest.py
- workspace/features/decision_engine/tests/test_decision_engine_core.py
- workspace/features/decision_engine/tests/test_prompt_builder.py

SPECIFIC TASK:
1. Locate the mock_ticker fixture in conftest.py
2. Add 'quote_volume_24h': 1000000.0 to the mock ticker data
3. Ensure all mock market snapshots include this field
4. Run: python -m pytest workspace/features/decision_engine/tests/ -v
5. Verify all 11 tests pass

SUCCESS CRITERIA: 11/11 decision engine tests passing"
```

#### Team Fix-Foxtrot Activation
```bash
# Team Fix-Foxtrot: Paper Executor Precision (26 tests)
"Implementation Specialist Foxtrot, you are assigned to fix paper executor precision issues.

OBJECTIVE: Fix 26 failing tests by standardizing decimal precision to 8 places.

ROOT CAUSE: Implementation returns excessive decimal precision, tests expect 8 places.

FILES TO MODIFY:
- workspace/features/paper_trading/paper_executor.py
- workspace/features/paper_trading/performance_tracker.py

SPECIFIC TASK:
1. Add rounding to all decimal operations in paper_executor.py:
   - Use quantize(Decimal('0.00000001')) for all price/amount calculations
   - Apply to: buy_order(), sell_order(), get_balance(), calculate_pnl()
2. Fix performance_tracker.py decimal precision:
   - Round all PnL calculations to 8 decimal places
   - Fix win_rate, profit_factor calculations
3. Run: python -m pytest workspace/features/paper_trading/tests/ -v
4. Verify all 26 tests pass

SUCCESS CRITERIA: 26/26 paper trading tests passing"
```

#### Team Fix-Golf Activation
```bash
# Team Fix-Golf: Strategy & LLM Mock Fixes (11 tests)
"Implementation Specialist Golf, you are assigned to fix strategy and LLM mock issues.

OBJECTIVE: Fix 11 failing tests across strategy, LLM, and prompt builder modules.

ROOT CAUSE: Mock data structure mismatches and missing API response fields.

FILES TO MODIFY:
- workspace/features/strategy/tests/conftest.py
- workspace/features/decision_engine/tests/test_llm_engine.py
- workspace/features/decision_engine/tests/test_prompt_builder.py

SPECIFIC TASK:
1. Fix strategy mock snapshots (8 tests):
   - Ensure market_snapshot mock has all required indicator fields
   - Add missing volume, candle, and indicator data
2. Fix LLM engine mocks (2 tests):
   - Properly mock OpenRouter API responses
   - Add usage data fields to mock responses
3. Fix prompt builder output format (1 test):
   - Ensure JSON schema matches expected format
4. Run: python -m pytest workspace/features/strategy/tests/ workspace/features/decision_engine/tests/test_llm_engine.py workspace/features/decision_engine/tests/test_prompt_builder.py::test_build_output_format -v
5. Verify all 11 tests pass

SUCCESS CRITERIA: 11/11 targeted tests passing"
```

### Wave 2 Activation (After Wave 1 Complete)

#### Team Fix-Hotel Activation
```bash
# Team Fix-Hotel: Position Service Database Integration (32 tests)
"Implementation Specialist Hotel, you are assigned to fix position service database integration.

OBJECTIVE: Fix 32 failing tests by properly configuring database mocks and async patterns.

ROOT CAUSE: Database session fixtures and async context managers not properly configured.

FILES TO MODIFY:
- workspace/features/position_manager/tests/conftest.py
- workspace/features/position_manager/tests/test_position_service.py

SPECIFIC TASK:
1. Create proper database session fixture in conftest.py:
   - Use pytest-asyncio fixtures
   - Properly mock AsyncSession
   - Handle transaction commits/rollbacks
2. Fix async context managers in test_position_service.py:
   - Ensure all async tests use proper decorators
   - Mock database queries with appropriate return values
3. Add missing mock data for:
   - Position creation responses
   - Update operations
   - Query results
4. Run: python -m pytest workspace/features/position_manager/tests/ -v
5. Verify all 32 tests pass

SUCCESS CRITERIA: 32/32 position service tests passing"
```

---

## Success Metrics and Validation

### Wave 1 Completion Criteria
- [ ] Team Fix-Echo: 11/11 decision engine tests passing
- [ ] Team Fix-Foxtrot: 26/26 paper trading tests passing
- [ ] Team Fix-Golf: 11/11 strategy/LLM tests passing
- [ ] Combined: 1,030/1,062 tests passing (97% pass rate)

### Wave 2 Completion Criteria
- [ ] Team Fix-Hotel: 32/32 position service tests passing
- [ ] Final: 1,062/1,062 tests passing (100% pass rate)

### Final Validation Steps
```bash
# 1. Run full test suite
python -m pytest workspace/features/ -v --tb=short

# 2. Verify test count
python -m pytest workspace/features/ --co -q | wc -l
# Expected: 1,062

# 3. Check coverage maintained
python -m pytest workspace/features/ --cov=workspace/features --cov-report=term-missing
# Expected: ≥79% coverage

# 4. Run specific category validations
python -m pytest workspace/features/decision_engine/tests/ -v  # 200+ passing
python -m pytest workspace/features/paper_trading/tests/ -v    # 26 passing
python -m pytest workspace/features/position_manager/tests/ -v  # 32 passing
python -m pytest workspace/features/strategy/tests/ -v          # 100+ passing

# 5. Generate final report
python -m pytest workspace/features/ --html=reports/phase3-final.html --self-contained-html
```

---

## Risk Mitigation

### Potential Blockers and Solutions

1. **Mock Complexity**: If mocks are more complex than expected
   - Solution: Create shared mock factory functions in conftest.py

2. **Async Issues**: If async patterns cause unexpected failures
   - Solution: Use pytest-asyncio fixtures consistently

3. **Import Errors**: If test imports fail due to module changes
   - Solution: Update PYTHONPATH and __init__.py files

4. **Precision Issues**: If decimal precision fixes break other tests
   - Solution: Use context-specific precision (8 for prices, 2 for percentages)

---

## Timeline

| Phase | Teams | Tests | Start | End | Wall Clock |
|-------|-------|-------|-------|-----|------------|
| Wave 1 | Echo, Foxtrot, Golf | 48 | T+0 | T+2h | 2 hours |
| Validation 1 | - | - | T+2h | T+2.5h | 30 min |
| Wave 2 | Hotel | 32 | T+2.5h | T+4.5h | 2 hours |
| Final Validation | - | - | T+4.5h | T+5h | 30 min |
| **Total** | **4** | **80** | **-** | **-** | **5 hours** |

---

## Post-Fix Actions

1. **Documentation Update**: Update test documentation with patterns learned
2. **Mock Library**: Create reusable mock fixtures for future tests
3. **CI/CD Update**: Ensure all tests run in CI pipeline
4. **Performance Baseline**: Record test execution time for regression detection
5. **Coverage Report**: Generate and archive final coverage report

---

## Command Summary

### Initialize All Teams (Orchestrator)
```bash
# Wave 1 - Execute in parallel terminals or background
./activate-team-echo.sh &
./activate-team-foxtrot.sh &
./activate-team-golf.sh &

# Wait for Wave 1 completion
wait

# Validate Wave 1
python -m pytest workspace/features/ --co -q | wc -l

# Wave 2
./activate-team-hotel.sh

# Final validation
python -m pytest workspace/features/ -v --tb=short
```

---

## Success Declaration

Phase 3 will be considered complete when:
1. ✅ All 1,062 tests passing (100% pass rate)
2. ✅ Coverage maintained at ≥79%
3. ✅ No new test failures introduced
4. ✅ All fixes documented with comments
5. ✅ CI/CD pipeline green

---

*Orchestration Plan Created: 2025-01-31*
*Target Completion: 5 hours from activation*
*Expected Outcome: 100% test pass rate with 79% coverage*
