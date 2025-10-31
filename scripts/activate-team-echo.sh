#!/bin/bash
# Team Fix-Echo Activation Script
# Focus: Decision Engine Mock Fixes (11 tests)

echo "========================================="
echo "TEAM FIX-ECHO ACTIVATION"
echo "Mission: Fix Decision Engine Mock Issues"
echo "Target: 11 failing tests"
echo "========================================="

# Create team workspace
mkdir -p .agent-system/teams/fix-echo
cd /Users/tobiprivat/Documents/GitProjects/personal/trader

# Team briefing
cat << 'EOF' > .agent-system/teams/fix-echo/briefing.md
# Team Fix-Echo Mission Briefing

## Objective
Fix 11 failing tests in decision_engine by adding missing mock attributes.

## Root Cause Analysis
Mock Ticker objects are missing the 'quote_volume_24h' attribute that the implementation expects.

## Files to Modify
1. workspace/features/decision_engine/tests/conftest.py
2. workspace/features/decision_engine/tests/test_decision_engine_core.py
3. workspace/features/decision_engine/tests/test_prompt_builder.py

## Specific Tasks
1. Locate the mock_ticker fixture in conftest.py
2. Add 'quote_volume_24h': 1000000.0 to mock ticker data
3. Ensure all mock market snapshots include this field
4. Update any inline mocks in test files

## Validation Command
python -m pytest workspace/features/decision_engine/tests/ -v --tb=short

## Success Criteria
- All 11 previously failing tests now pass
- No new test failures introduced
- Mock data structure matches implementation expectations
EOF

# Run initial test to confirm failures
echo "Current test status:"
python -m pytest workspace/features/decision_engine/tests/ -v --tb=short 2>&1 | grep -E "FAILED|ERROR|passed" | tail -20

# Create fix tracker
cat << 'EOF' > .agent-system/teams/fix-echo/progress.md
# Team Fix-Echo Progress Tracker

## Tests to Fix (11 total)
- [ ] test_generate_signals_cache_miss_calls_llm
- [ ] test_generate_signals_caches_response
- [ ] test_generate_signals_usage_data_populated
- [ ] test_prompt_builder_empty_positions
- [ ] test_prompt_builder_no_positions_arg
- [ ] test_prompt_builder_large_capital
- [ ] test_prompt_builder_zero_capital
- [ ] test_prompt_builder_no_indicators
- [ ] test_prompt_format_snapshot_multiple_symbols
- [ ] test_generate_signals_partial_response
- [ ] test_generate_signals_with_all_parameters

## Fix Applied
[ ] Added quote_volume_24h to mock_ticker fixture
[ ] Updated inline mocks in test files
[ ] Verified all tests pass

## Start Time: $(date)
## End Time: [pending]
EOF

echo ""
echo "Team Fix-Echo activated and ready!"
echo "Briefing available at: .agent-system/teams/fix-echo/briefing.md"
echo ""
echo "RECOMMENDED FIRST ACTION:"
echo "1. Check workspace/features/decision_engine/tests/conftest.py for mock_ticker fixture"
echo "2. Add 'quote_volume_24h': 1000000.0 to the mock data"
echo "3. Run validation command to check progress"
