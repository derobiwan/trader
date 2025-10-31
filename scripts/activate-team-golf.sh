#!/bin/bash
# Team Fix-Golf Activation Script
# Focus: Strategy & LLM Mock Fixes (11 tests)

echo "========================================="
echo "TEAM FIX-GOLF ACTIVATION"
echo "Mission: Fix Strategy & LLM Mock Issues"
echo "Target: 11 failing tests"
echo "========================================="

# Create team workspace
mkdir -p .agent-system/teams/fix-golf
cd /Users/tobiprivat/Documents/GitProjects/personal/trader

# Team briefing
cat << 'EOF' > .agent-system/teams/fix-golf/briefing.md
# Team Fix-Golf Mission Briefing

## Objective
Fix 11 failing tests across strategy, LLM engine, and prompt builder modules.

## Root Cause Analysis
- Strategy tests: Market snapshot mocks missing required fields
- LLM tests: OpenRouter API response mocks incomplete
- Prompt builder: Output format validation issue

## Files to Modify
1. workspace/features/strategy/tests/conftest.py (or inline mocks)
2. workspace/features/decision_engine/tests/test_llm_engine.py
3. workspace/features/decision_engine/tests/test_prompt_builder.py

## Specific Tasks

### Task 1: Fix Strategy Mocks (8 tests)
- Ensure market_snapshot includes all indicators:
  * rsi, macd, macd_signal, ema_12, ema_26
  * bollinger_upper, bollinger_lower, bollinger_sma
  * volume, close, high, low, open
  * Add any missing fields based on error messages

### Task 2: Fix LLM Engine Mocks (2 tests)
- test_call_openrouter_success:
  * Mock proper OpenRouter API response structure
  * Include: choices[0].message.content
  * Include: usage.total_tokens, usage.prompt_tokens, usage.completion_tokens
- test_call_openrouter_empty_response:
  * Mock empty but valid response structure

### Task 3: Fix Prompt Builder Format (1 test)
- test_build_output_format:
  * Ensure JSON schema matches expected structure
  * Check for required fields in output format

## Validation Commands
python -m pytest workspace/features/strategy/tests/ -v
python -m pytest workspace/features/decision_engine/tests/test_llm_engine.py::test_call_openrouter_success -v
python -m pytest workspace/features/decision_engine/tests/test_llm_engine.py::test_call_openrouter_empty_response -v
python -m pytest workspace/features/decision_engine/tests/test_prompt_builder.py::test_build_output_format -v

## Success Criteria
- 8/8 strategy tests passing
- 2/2 LLM engine tests passing
- 1/1 prompt builder test passing
EOF

# Run initial test to confirm failures
echo "Current test status:"
echo "Strategy tests:"
python -m pytest workspace/features/strategy/tests/ -v 2>&1 | grep -E "FAILED|ERROR" | wc -l
echo "LLM tests:"
python -m pytest workspace/features/decision_engine/tests/test_llm_engine.py -v 2>&1 | grep -E "FAILED" | wc -l

# Create fix tracker
cat << 'EOF' > .agent-system/teams/fix-golf/progress.md
# Team Fix-Golf Progress Tracker

## Tests to Fix (11 total)

### Strategy Tests (8)
- [ ] test_invalid_snapshot_returns_hold (MeanReversion)
- [ ] test_hold_on_no_squeeze (VolatilityBreakout)
- [ ] test_buy_signal_on_oversold (MeanReversion)
- [ ] test_sell_signal_on_overbought (MeanReversion)
- [ ] test_hold_on_neutral_rsi (MeanReversion)
- [ ] test_bollinger_confirmation (MeanReversion)
- [ ] test_macd_confirmation (MeanReversion)
- [ ] test_hold_during_squeeze_no_breakout (VolatilityBreakout)

### LLM Engine Tests (2)
- [ ] test_call_openrouter_success
- [ ] test_call_openrouter_empty_response

### Prompt Builder Tests (1)
- [ ] test_build_output_format

## Fixes Applied
[ ] Updated strategy mock snapshots with all required fields
[ ] Fixed OpenRouter API response mocks
[ ] Corrected prompt builder output format
[ ] All tests passing

## Start Time: $(date)
## End Time: [pending]
EOF

echo ""
echo "Team Fix-Golf activated and ready!"
echo "Briefing available at: .agent-system/teams/fix-golf/briefing.md"
echo ""
echo "RECOMMENDED FIRST ACTION:"
echo "1. Check strategy test failures for missing fields: python -m pytest workspace/features/strategy/tests/ -vvs --tb=short"
echo "2. Add missing fields to mock_market_snapshot"
echo "3. Fix OpenRouter response mocks in test_llm_engine.py"
