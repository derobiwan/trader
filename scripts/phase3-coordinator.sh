#!/bin/bash
# Phase 3 Test Fix Master Coordinator
# Orchestrates parallel test fixing across 4 teams

set -e

TRADER_ROOT="/Users/tobiprivat/Documents/GitProjects/personal/trader"
cd "$TRADER_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}=========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}=========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

check_test_status() {
    local total=$(python -m pytest "$1" --co -q 2>/dev/null | wc -l | xargs)
    local passing=$(python -m pytest "$1" -q 2>&1 | grep -E "passed" | wc -l | xargs)
    local failing=$(python -m pytest "$1" -q 2>&1 | grep -E "FAILED|ERROR" | wc -l | xargs)
    echo "Total: $total | Passing: $passing | Failing: $failing"
}

# Main orchestration
print_header "PHASE 3: TEST FIX ORCHESTRATION"
echo "Target: Fix 80 failing tests to achieve 100% pass rate"
echo ""

# Initial status
print_header "INITIAL STATUS CHECK"
echo "Checking current test status..."
INITIAL_TOTAL=$(python -m pytest workspace/features/ --co -q 2>/dev/null | wc -l | xargs)
INITIAL_PASSING=$(python -m pytest workspace/features/ -q 2>&1 | grep -E "passed" | wc -l | xargs || echo "0")
INITIAL_FAILING=$(python -m pytest workspace/features/ -q 2>&1 | grep -E "FAILED|ERROR" | wc -l | xargs || echo "0")

echo "Initial Status:"
echo "  Total Tests: $INITIAL_TOTAL"
echo "  Passing: $INITIAL_PASSING"
echo "  Failing: $INITIAL_FAILING"
echo ""

# Wave 1: Quick Wins
print_header "WAVE 1: QUICK WINS (3 Teams in Parallel)"
echo "Activating teams Echo, Foxtrot, and Golf..."
echo ""

# Create team status directory
mkdir -p .agent-system/teams/status

# Launch Wave 1 teams in parallel
(
    echo "Team Echo starting..." > .agent-system/teams/status/echo.log
    ./scripts/activate-team-echo.sh > .agent-system/teams/status/echo.output 2>&1
    echo "COMPLETE" > .agent-system/teams/status/echo.done
) &
PID_ECHO=$!

(
    echo "Team Foxtrot starting..." > .agent-system/teams/status/foxtrot.log
    ./scripts/activate-team-foxtrot.sh > .agent-system/teams/status/foxtrot.output 2>&1
    echo "COMPLETE" > .agent-system/teams/status/foxtrot.done
) &
PID_FOXTROT=$!

(
    echo "Team Golf starting..." > .agent-system/teams/status/golf.log
    ./scripts/activate-team-golf.sh > .agent-system/teams/status/golf.output 2>&1
    echo "COMPLETE" > .agent-system/teams/status/golf.done
) &
PID_GOLF=$!

print_success "Wave 1 teams activated"
echo "  - Team Echo (PID: $PID_ECHO): Decision Engine Mocks (11 tests)"
echo "  - Team Foxtrot (PID: $PID_FOXTROT): Paper Trading Precision (26 tests)"
echo "  - Team Golf (PID: $PID_GOLF): Strategy & LLM Mocks (11 tests)"
echo ""

# Monitor Wave 1 progress
print_warning "Teams are now working in parallel. Monitor progress with:"
echo "  tail -f .agent-system/teams/status/*.output"
echo ""

# Create status monitor
cat << 'EOF' > .agent-system/teams/monitor-wave1.sh
#!/bin/bash
while true; do
    clear
    echo "WAVE 1 STATUS MONITOR"
    echo "===================="
    echo ""
    for team in echo foxtrot golf; do
        if [ -f ".agent-system/teams/status/$team.done" ]; then
            echo "Team ${team^}: ✓ COMPLETE"
        else
            echo "Team ${team^}: ⏳ IN PROGRESS"
        fi
    done
    echo ""
    echo "Press Ctrl+C to exit monitor"
    sleep 5
done
EOF
chmod +x .agent-system/teams/monitor-wave1.sh

print_header "WAVE 1 MONITORING"
echo "To monitor Wave 1 progress, run:"
echo "  .agent-system/teams/monitor-wave1.sh"
echo ""
echo "To check specific team output:"
echo "  cat .agent-system/teams/status/echo.output"
echo "  cat .agent-system/teams/status/foxtrot.output"
echo "  cat .agent-system/teams/status/golf.output"
echo ""

# Wave 2 preparation
print_header "WAVE 2: DATABASE INTEGRATION"
echo "Wave 2 will start after Wave 1 completes."
echo "Team Hotel will fix Position Service Database Integration (32 tests)"
echo ""

# Create Wave 2 launcher
cat << 'EOF' > .agent-system/teams/launch-wave2.sh
#!/bin/bash
echo "Checking Wave 1 completion..."
if [ -f ".agent-system/teams/status/echo.done" ] && \
   [ -f ".agent-system/teams/status/foxtrot.done" ] && \
   [ -f ".agent-system/teams/status/golf.done" ]; then
    echo "Wave 1 complete! Launching Wave 2..."
    ./scripts/activate-team-hotel.sh
else
    echo "Wave 1 not yet complete. Please wait for all teams to finish."
fi
EOF
chmod +x .agent-system/teams/launch-wave2.sh

# Final validation script
cat << 'EOF' > .agent-system/teams/final-validation.sh
#!/bin/bash
echo "FINAL VALIDATION"
echo "================"
echo ""

# Run full test suite
echo "Running complete test suite..."
python -m pytest workspace/features/ -v --tb=short > .agent-system/teams/final-results.txt 2>&1

# Extract results
TOTAL=$(python -m pytest workspace/features/ --co -q 2>/dev/null | wc -l | xargs)
PASSING=$(grep -E "passed" .agent-system/teams/final-results.txt | wc -l | xargs)
FAILING=$(grep -E "FAILED|ERROR" .agent-system/teams/final-results.txt | wc -l | xargs)

echo "Final Results:"
echo "  Total Tests: $TOTAL"
echo "  Passing: $PASSING"
echo "  Failing: $FAILING"
echo ""

if [ "$FAILING" -eq 0 ]; then
    echo "✅ SUCCESS! All tests passing (100% pass rate)"
else
    echo "❌ Still $FAILING tests failing. Review required."
fi

# Generate HTML report
python -m pytest workspace/features/ --html=reports/phase3-final.html --self-contained-html
echo ""
echo "HTML report generated: reports/phase3-final.html"
EOF
chmod +x .agent-system/teams/final-validation.sh

print_header "COORDINATION COMMANDS"
echo "Wave 1 Monitor:"
echo "  .agent-system/teams/monitor-wave1.sh"
echo ""
echo "Launch Wave 2 (after Wave 1):"
echo "  .agent-system/teams/launch-wave2.sh"
echo ""
echo "Final Validation (after all waves):"
echo "  .agent-system/teams/final-validation.sh"
echo ""

print_success "Phase 3 Orchestration initialized!"
echo ""
echo "Next Steps:"
echo "1. Monitor Wave 1 progress"
echo "2. When Wave 1 completes, launch Wave 2"
echo "3. After Wave 2, run final validation"
echo "4. Target: 1,062/1,062 tests passing (100%)"
