# Phase 3 Team Activation Commands

## Quick Reference for Implementation Specialists

### Wave 1: Parallel Execution (Execute Simultaneously)

#### Team Fix-Echo Command
```bash
# Team Fix-Echo: Decision Engine Mock Fixes (11 tests)
"Implementation Specialist, you are Team Fix-Echo.

OBJECTIVE: Fix 11 failing tests in decision_engine by adding missing mock attributes.

ROOT CAUSE: Mock Ticker objects missing 'quote_volume_24h' attribute.

IMMEDIATE ACTIONS:
1. Open workspace/features/decision_engine/tests/conftest.py
2. Find the mock_ticker or create_mock_ticker fixture
3. Add 'quote_volume_24h': 1000000.0 to the ticker data
4. Check test files for any inline mocks and update them too
5. Run: python -m pytest workspace/features/decision_engine/tests/ -v

SUCCESS: All 11 decision engine tests pass."
```

#### Team Fix-Foxtrot Command
```bash
# Team Fix-Foxtrot: Paper Executor Precision (26 tests)
"Implementation Specialist, you are Team Fix-Foxtrot.

OBJECTIVE: Fix 26 failing tests by standardizing decimal precision to 8 places.

ROOT CAUSE: Implementation returns excessive decimal precision.

IMMEDIATE ACTIONS:
1. Open workspace/features/paper_trading/paper_executor.py
2. Add decimal rounding helper:
   from decimal import Decimal, ROUND_HALF_UP
   def round_decimal(value, places=8):
       return Decimal(str(value)).quantize(Decimal(10) ** -places, rounding=ROUND_HALF_UP)
3. Apply rounding to all calculations in buy_order, sell_order, get_balance
4. Fix performance_tracker.py similarly
5. Run: python -m pytest workspace/features/paper_trading/tests/ -v

SUCCESS: All 26 paper trading tests pass."
```

#### Team Fix-Golf Command
```bash
# Team Fix-Golf: Strategy & LLM Mock Fixes (11 tests)
"Implementation Specialist, you are Team Fix-Golf.

OBJECTIVE: Fix 11 failing tests in strategy and LLM modules.

ROOT CAUSE: Missing fields in mock data structures.

IMMEDIATE ACTIONS:
1. Fix strategy mocks (8 tests):
   - Add all indicator fields to market_snapshot mocks
   - Include: rsi, macd, macd_signal, ema_12, ema_26, bollinger_*
2. Fix LLM engine mocks (2 tests):
   - Mock OpenRouter API response with choices[0].message.content
   - Add usage data: total_tokens, prompt_tokens, completion_tokens
3. Fix prompt builder format (1 test):
   - Ensure JSON output schema is correct
4. Run: python -m pytest workspace/features/strategy/tests/ workspace/features/decision_engine/tests/test_llm_engine.py -v

SUCCESS: All 11 tests pass."
```

### Wave 2: Database Integration (After Wave 1)

#### Team Fix-Hotel Command
```bash
# Team Fix-Hotel: Position Service Database Integration (32 tests)
"Implementation Specialist, you are Team Fix-Hotel.

OBJECTIVE: Fix 32 failing tests by configuring database mocks.

ROOT CAUSE: AsyncSession not properly mocked for async operations.

IMMEDIATE ACTIONS:
1. Open workspace/features/position_manager/tests/conftest.py
2. Create async database session fixture:
   import pytest_asyncio
   from unittest.mock import AsyncMock, MagicMock

   @pytest_asyncio.fixture
   async def db_session():
       session = AsyncMock(spec=AsyncSession)
       session.commit = AsyncMock()
       session.rollback = AsyncMock()
       session.execute = AsyncMock()
       session.__aenter__ = AsyncMock(return_value=session)
       session.__aexit__ = AsyncMock()
       return session
3. Add @pytest.mark.asyncio to all async tests
4. Mock query return values for each test
5. Run: python -m pytest workspace/features/position_manager/tests/ -v

SUCCESS: All 32 position service tests pass."
```

---

## Execution Timeline

| Time | Action | Teams | Tests Fixed |
|------|--------|-------|-------------|
| T+0 | Wave 1 Start | Echo, Foxtrot, Golf | 0 |
| T+1h | Wave 1 Mid-point | Echo, Foxtrot, Golf | ~24 |
| T+2h | Wave 1 Complete | - | 48 |
| T+2.5h | Wave 2 Start | Hotel | 48 |
| T+4.5h | Wave 2 Complete | - | 80 |
| T+5h | Final Validation | - | 80 (100%) |

---

## Validation Commands

### Check Wave 1 Progress
```bash
# Decision Engine (Echo)
python -m pytest workspace/features/decision_engine/tests/ --tb=no -q

# Paper Trading (Foxtrot)
python -m pytest workspace/features/paper_trading/tests/ --tb=no -q

# Strategy & LLM (Golf)
python -m pytest workspace/features/strategy/tests/ --tb=no -q
```

### Check Wave 2 Progress
```bash
# Position Service (Hotel)
python -m pytest workspace/features/position_manager/tests/ --tb=no -q
```

### Final Validation
```bash
# Full suite
python -m pytest workspace/features/ -v --tb=short

# Count totals
python -m pytest workspace/features/ --co -q | wc -l

# Generate report
python -m pytest workspace/features/ --html=reports/phase3-final.html --self-contained-html
```

---

## Emergency Fixes

If a team encounters unexpected issues:

### Mock Structure Issues
```python
# Universal mock factory
def create_complete_mock(data_type):
    if data_type == "ticker":
        return {
            'symbol': 'BTC/USDT',
            'close': 50000.0,
            'volume': 1000000.0,
            'quote_volume_24h': 1000000.0,  # Often missing
            'bid': 49999.0,
            'ask': 50001.0,
        }
    elif data_type == "snapshot":
        return {
            'symbol': 'BTC/USDT',
            'close': 50000.0,
            'rsi': 50.0,
            'macd': 100.0,
            'macd_signal': 95.0,
            'ema_12': 49900.0,
            'ema_26': 49800.0,
            'bollinger_upper': 51000.0,
            'bollinger_lower': 49000.0,
            'bollinger_sma': 50000.0,
            'volume': 1000000.0,
        }
```

### Async Test Issues
```python
# Ensure pytest-asyncio is configured
# Add to pytest.ini:
[tool:pytest]
asyncio_mode = auto

# Or use explicit decorators:
@pytest.mark.asyncio
async def test_something():
    pass
```

### Decimal Precision Issues
```python
from decimal import Decimal, ROUND_HALF_UP

def standardize_decimal(value, places=8):
    """Standardize decimal to specific precision."""
    if isinstance(value, (int, float)):
        value = Decimal(str(value))
    return value.quantize(Decimal(10) ** -places, rounding=ROUND_HALF_UP)
```

---

## Success Criteria

Phase 3 is complete when:
- ✅ 1,062 tests passing (100% pass rate)
- ✅ Coverage maintained at ≥79%
- ✅ No new test failures
- ✅ All fixes documented
- ✅ CI/CD pipeline green

---

*Commands ready for immediate execution*
*Target: 100% test pass rate in 5 hours*
