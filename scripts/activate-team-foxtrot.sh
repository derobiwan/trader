#!/bin/bash
# Team Fix-Foxtrot Activation Script
# Focus: Paper Executor Precision (26 tests)

echo "========================================="
echo "TEAM FIX-FOXTROT ACTIVATION"
echo "Mission: Fix Paper Trading Precision"
echo "Target: 26 failing tests"
echo "========================================="

# Create team workspace
mkdir -p .agent-system/teams/fix-foxtrot
cd /Users/tobiprivat/Documents/GitProjects/personal/trader

# Team briefing
cat << 'EOF' > .agent-system/teams/fix-foxtrot/briefing.md
# Team Fix-Foxtrot Mission Briefing

## Objective
Fix 26 failing tests by standardizing decimal precision to 8 decimal places.

## Root Cause Analysis
Implementation returns excessive decimal precision (>8 places), while tests expect exactly 8 decimal places.

## Files to Modify
1. workspace/features/paper_trading/paper_executor.py
2. workspace/features/paper_trading/performance_tracker.py

## Specific Tasks
1. Add decimal rounding to paper_executor.py:
   - Import: from decimal import Decimal, ROUND_HALF_UP
   - Create helper: def round_decimal(value, places=8):
       return Decimal(str(value)).quantize(Decimal(10) ** -places, rounding=ROUND_HALF_UP)
   - Apply to all price/amount calculations in:
     * buy_order()
     * sell_order()
     * get_balance()
     * get_position()
     * calculate_pnl()

2. Fix performance_tracker.py precision:
   - Round all PnL calculations to 8 places
   - Fix win_rate calculation precision
   - Fix profit_factor calculation precision
   - Ensure all returned Decimals use consistent precision

## Validation Commands
python -m pytest workspace/features/paper_trading/tests/test_paper_executor.py -v
python -m pytest workspace/features/paper_trading/tests/test_performance_tracker.py -v

## Success Criteria
- All 26 tests pass
- Decimal precision consistent at 8 places
- No precision-related assertion errors
EOF

# Run initial test to confirm failures
echo "Current test status:"
python -m pytest workspace/features/paper_trading/tests/ -v --tb=short 2>&1 | grep -E "FAILED|passed" | wc -l

# Create fix tracker
cat << 'EOF' > .agent-system/teams/fix-foxtrot/progress.md
# Team Fix-Foxtrot Progress Tracker

## Tests to Fix (26 total)
### Paper Executor (14 tests)
- [ ] test_paper_trading_initialization
- [ ] test_paper_trading_buy_order
- [ ] test_paper_trading_sell_order
- [ ] test_paper_trading_insufficient_balance
- [ ] test_paper_trading_fees_calculation
- [ ] test_paper_trading_with_slippage
- [ ] test_paper_trading_with_partial_fills
- [ ] test_paper_trading_performance_report
- [ ] test_paper_trading_reset
- [ ] test_paper_trading_multiple_symbols
- [ ] test_paper_trading_stop_loss_order
- [ ] test_paper_trading_get_account_balance
- [ ] test_paper_trading_get_position
- [ ] test_decimal_precision (if exists)

### Performance Tracker (12 tests)
- [ ] test_record_winning_trade
- [ ] test_record_losing_trade
- [ ] test_calculate_win_rate
- [ ] test_calculate_average_winloss
- [ ] test_calculate_profit_factor
- [ ] test_daily_pnl_tracking
- [ ] test_generate_report
- [ ] test_get_trade_history
- [ ] test_get_symbol_performance
- [ ] test_reset
- [ ] test_export_trades_csv
- [ ] test_max_drawdown_calculation

## Fixes Applied
[ ] Added round_decimal helper function
[ ] Updated paper_executor.py calculations
[ ] Updated performance_tracker.py calculations
[ ] Verified all tests pass

## Start Time: $(date)
## End Time: [pending]
EOF

echo ""
echo "Team Fix-Foxtrot activated and ready!"
echo "Briefing available at: .agent-system/teams/fix-foxtrot/briefing.md"
echo ""
echo "RECOMMENDED FIRST ACTION:"
echo "1. Add decimal rounding helper to paper_executor.py"
echo "2. Apply rounding to all Decimal calculations"
echo "3. Test with: python -m pytest workspace/features/paper_trading/tests/test_paper_executor.py::test_paper_trading_initialization -v"
