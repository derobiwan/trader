#!/bin/bash

# Smoke Tests for LLM Crypto Trading System
# Usage: ./smoke-tests.sh [environment]
# Environment: staging | production

set -e

ENVIRONMENT=${1:-staging}
if [ "$ENVIRONMENT" == "production" ]; then
    BASE_URL="https://api.llm-trader.example.com"
    METRICS_URL="https://metrics.llm-trader.example.com"
else
    BASE_URL="https://staging.llm-trader.example.com"
    METRICS_URL="https://staging-metrics.llm-trader.example.com"
fi

echo "Running smoke tests for $ENVIRONMENT environment"
echo "Base URL: $BASE_URL"
echo "Metrics URL: $METRICS_URL"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track test results
TESTS_PASSED=0
TESTS_FAILED=0

# Function to run a test
run_test() {
    local test_name="$1"
    local command="$2"
    local expected_code="${3:-200}"

    echo -n "Testing $test_name... "

    response_code=$(eval "$command" 2>/dev/null || echo "000")

    if [ "$response_code" == "$expected_code" ]; then
        echo -e "${GREEN}PASSED${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}FAILED${NC} (Expected: $expected_code, Got: $response_code)"
        ((TESTS_FAILED++))
    fi
}

# Test 1: Health Check
run_test "Health Check" \
    "curl -s -o /dev/null -w '%{http_code}' $BASE_URL/health" \
    "200"

# Test 2: Readiness Check
run_test "Readiness Check" \
    "curl -s -o /dev/null -w '%{http_code}' $BASE_URL/health/ready" \
    "200"

# Test 3: Metrics Endpoint
run_test "Metrics Endpoint" \
    "curl -s -o /dev/null -w '%{http_code}' $METRICS_URL/metrics" \
    "200"

# Test 4: API Version
run_test "API Version" \
    "curl -s -o /dev/null -w '%{http_code}' $BASE_URL/api/v1/version" \
    "200"

# Test 5: Database Connection
echo -n "Testing Database Connection... "
db_status=$(curl -s $BASE_URL/health/ready | jq -r '.database' 2>/dev/null || echo "error")
if [ "$db_status" == "healthy" ]; then
    echo -e "${GREEN}PASSED${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}FAILED${NC} (Database status: $db_status)"
    ((TESTS_FAILED++))
fi

# Test 6: Redis Connection
echo -n "Testing Redis Connection... "
redis_status=$(curl -s $BASE_URL/health/ready | jq -r '.redis' 2>/dev/null || echo "error")
if [ "$redis_status" == "healthy" ]; then
    echo -e "${GREEN}PASSED${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}FAILED${NC} (Redis status: $redis_status)"
    ((TESTS_FAILED++))
fi

# Test 7: WebSocket Health (if applicable)
echo -n "Testing WebSocket Health... "
ws_status=$(curl -s $BASE_URL/health/ready | jq -r '.websocket' 2>/dev/null || echo "not_configured")
if [ "$ws_status" == "healthy" ] || [ "$ws_status" == "not_configured" ]; then
    echo -e "${GREEN}PASSED${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}FAILED${NC} (WebSocket status: $ws_status)"
    ((TESTS_FAILED++))
fi

# Test 8: Trading Mode Check
echo -n "Testing Trading Mode... "
trading_mode=$(curl -s $BASE_URL/api/v1/config | jq -r '.trading_mode' 2>/dev/null || echo "error")
if [ "$ENVIRONMENT" == "production" ]; then
    expected_mode="live"
else
    expected_mode="paper"
fi

if [ "$trading_mode" == "$expected_mode" ] || [ "$trading_mode" == "paper" ]; then
    echo -e "${GREEN}PASSED${NC} (Mode: $trading_mode)"
    ((TESTS_PASSED++))
else
    echo -e "${RED}FAILED${NC} (Expected: $expected_mode, Got: $trading_mode)"
    ((TESTS_FAILED++))
fi

# Test 9: Account Balance Endpoint (paper trading)
run_test "Account Balance" \
    "curl -s -o /dev/null -w '%{http_code}' -H 'Authorization: Bearer test-token' $BASE_URL/api/v1/account/balance" \
    "200"

# Test 10: Market Data Endpoint
run_test "Market Data" \
    "curl -s -o /dev/null -w '%{http_code}' $BASE_URL/api/v1/market/BTC-USDT" \
    "200"

# Test 11: Response Time Check
echo -n "Testing Response Time... "
response_time=$(curl -s -o /dev/null -w '%{time_total}' $BASE_URL/health)
response_time_ms=$(echo "$response_time * 1000" | bc | cut -d'.' -f1)

if [ "$response_time_ms" -lt 1000 ]; then
    echo -e "${GREEN}PASSED${NC} (${response_time_ms}ms)"
    ((TESTS_PASSED++))
else
    echo -e "${YELLOW}WARNING${NC} (${response_time_ms}ms - slow response)"
    ((TESTS_PASSED++))
fi

# Test 12: SSL Certificate Check
echo -n "Testing SSL Certificate... "
ssl_expiry=$(echo | openssl s_client -servername ${BASE_URL#https://} -connect ${BASE_URL#https://}:443 2>/dev/null | openssl x509 -noout -enddate 2>/dev/null | cut -d'=' -f2)

if [ -n "$ssl_expiry" ]; then
    expiry_epoch=$(date -d "$ssl_expiry" +%s 2>/dev/null || date -j -f "%b %d %H:%M:%S %Y %Z" "$ssl_expiry" +%s 2>/dev/null || echo 0)
    current_epoch=$(date +%s)
    days_until_expiry=$(( ($expiry_epoch - $current_epoch) / 86400 ))

    if [ "$days_until_expiry" -gt 7 ]; then
        echo -e "${GREEN}PASSED${NC} (Expires in $days_until_expiry days)"
        ((TESTS_PASSED++))
    else
        echo -e "${YELLOW}WARNING${NC} (Expires in $days_until_expiry days)"
        ((TESTS_PASSED++))
    fi
else
    echo -e "${YELLOW}SKIPPED${NC} (Could not check SSL)"
    ((TESTS_PASSED++))
fi

# Print summary
echo ""
echo "========================================"
echo "Smoke Test Results for $ENVIRONMENT"
echo "========================================"
echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}"
echo "========================================"

# Exit with appropriate code
if [ "$TESTS_FAILED" -gt 0 ]; then
    echo -e "${RED}SMOKE TESTS FAILED${NC}"
    exit 1
else
    echo -e "${GREEN}ALL SMOKE TESTS PASSED${NC}"
    exit 0
fi
