#!/bin/bash
# Team Fix-Hotel Activation Script
# Focus: Position Service Database Integration (32 tests)

echo "========================================="
echo "TEAM FIX-HOTEL ACTIVATION"
echo "Mission: Fix Position Service Database"
echo "Target: 32 failing tests"
echo "========================================="

# Create team workspace
mkdir -p .agent-system/teams/fix-hotel
cd /Users/tobiprivat/Documents/GitProjects/personal/trader

# Team briefing
cat << 'EOF' > .agent-system/teams/fix-hotel/briefing.md
# Team Fix-Hotel Mission Briefing

## Objective
Fix 32 failing tests by properly configuring database mocks and async patterns.

## Root Cause Analysis
- Database session fixtures not properly configured for async operations
- AsyncSession context managers not mocked correctly
- Transaction commit/rollback handling issues
- Missing mock return values for database queries

## Files to Modify
1. workspace/features/position_manager/tests/conftest.py
2. workspace/features/position_manager/tests/test_position_service.py

## Specific Tasks

### Task 1: Fix Database Session Fixture
Create proper async database session fixture in conftest.py:
```python
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

@pytest_asyncio.fixture
async def db_session():
    """Mock database session for testing."""
    session = AsyncMock(spec=AsyncSession)

    # Mock transaction methods
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()

    # Mock query methods
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    # Mock context manager
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)

    return session
```

### Task 2: Fix Test Decorators
Ensure all async tests use proper decorators:
- Use @pytest.mark.asyncio for all async tests
- Or configure pytest-asyncio to auto mode in pytest.ini

### Task 3: Mock Database Queries
For each test, ensure proper mock return values:
- Position creation: Mock the returned position object
- Position updates: Mock the updated values
- Query results: Mock Result objects with proper data

### Task 4: Fix Import Issues
Ensure all necessary imports are present:
- from unittest.mock import AsyncMock, MagicMock, patch
- import pytest_asyncio
- from sqlalchemy.ext.asyncio import AsyncSession

## Validation Command
python -m pytest workspace/features/position_manager/tests/ -v --tb=short

## Success Criteria
- All 32 position service tests pass
- No async warnings
- Database operations properly mocked
- Transaction handling works correctly
EOF

# Run initial test to confirm failures
echo "Current test status:"
python -m pytest workspace/features/position_manager/tests/test_position_service.py -v 2>&1 | grep -E "FAILED|passed" | wc -l

# Create fix tracker
cat << 'EOF' > .agent-system/teams/fix-hotel/progress.md
# Team Fix-Hotel Progress Tracker

## Tests to Fix (32 total)

### Position Creation Tests
- [ ] test_create_position_success
- [ ] test_create_position_no_stop_loss
- [ ] test_create_position_invalid_leverage
- [ ] test_create_position_invalid_symbol
- [ ] test_create_position_wrong_side_stop_loss
- [ ] test_create_position_exceeds_size_limit
- [ ] test_create_position_exceeds_exposure_limit

### Position Update Tests
- [ ] test_update_position_price
- [ ] test_update_position_price_loss
- [ ] test_update_position_short_profit
- [ ] test_update_nonexistent_position
- [ ] test_bulk_update_prices

### Position Close Tests
- [ ] test_close_position_profit
- [ ] test_close_position_loss
- [ ] test_close_position_short_profit
- [ ] test_close_nonexistent_position

### Stop Loss/Take Profit Tests
- [ ] test_check_stop_loss_triggers_long
- [ ] test_check_stop_loss_triggers_short
- [ ] test_check_take_profit_triggers

### PnL Tests
- [ ] test_daily_pnl_with_open_positions
- [ ] test_daily_pnl_with_closed_positions
- [ ] test_zero_pnl

### Query Tests
- [ ] test_get_position_by_id
- [ ] test_get_position_by_id_not_found
- [ ] test_get_active_positions
- [ ] test_get_active_positions_by_symbol
- [ ] test_get_total_exposure
- [ ] test_get_statistics

### Edge Case Tests
- [ ] test_circuit_breaker_detection
- [ ] test_concurrent_price_updates
- [ ] test_very_high_leverage
- [ ] test_decimal_precision

## Fixes Applied
[ ] Created async database session fixture
[ ] Added pytest.mark.asyncio decorators
[ ] Fixed AsyncSession mocking
[ ] Added proper mock return values
[ ] All tests passing

## Start Time: $(date)
## End Time: [pending]
EOF

# Create pytest.ini if needed
cat << 'EOF' > .agent-system/teams/fix-hotel/pytest.ini.suggested
# Suggested pytest.ini configuration
[tool:pytest]
asyncio_mode = auto
testpaths = workspace/features/position_manager/tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
EOF

echo ""
echo "Team Fix-Hotel activated and ready!"
echo "Briefing available at: .agent-system/teams/fix-hotel/briefing.md"
echo ""
echo "RECOMMENDED FIRST ACTION:"
echo "1. Check current conftest.py: cat workspace/features/position_manager/tests/conftest.py"
echo "2. Add async database session fixture"
echo "3. Run single test to verify: python -m pytest workspace/features/position_manager/tests/test_position_service.py::test_create_position_success -vvs"
