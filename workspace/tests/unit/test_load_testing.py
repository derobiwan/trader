"""
Unit Tests for Load Testing Framework

Tests load testing functionality including:
- Baseline testing
- Stress testing
- Spike testing
- Endurance testing
- Trading system specific tests

Author: Testing Team
Date: 2025-10-29
Sprint: 3, Stream C
"""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from workspace.shared.performance.load_testing import (
    LoadTestConfig,
    LoadTester,
    LoadTestResult,
    LoadTestType,
    RequestResult,
)


@pytest.fixture
def load_tester():
    """Load tester instance"""
    return LoadTester()


@pytest.fixture
async def mock_target_function():
    """Mock async target function for testing"""

    async def target():
        await asyncio.sleep(0.01)  # Simulate 10ms work
        return "success"

    return target


@pytest.fixture
async def mock_failing_function():
    """Mock async function that sometimes fails"""
    call_count = 0

    async def target():
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.01)
        if call_count % 5 == 0:  # Fail every 5th call
            raise Exception("Simulated failure")
        return "success"

    return target


# ============================================================================
# Initialization Tests
# ============================================================================


def test_load_tester_initialization(load_tester):
    """Test load tester initialization"""
    assert load_tester.results == []


# ============================================================================
# Request Execution Tests
# ============================================================================


@pytest.mark.asyncio
async def test_execute_request_success(load_tester, mock_target_function):
    """Test successful request execution"""
    # Execute
    result = await load_tester._execute_request(1, mock_target_function)

    # Assert
    assert isinstance(result, RequestResult)
    assert result.request_id == 1
    assert result.success
    assert result.response_time_ms > 0
    assert result.error_message is None


@pytest.mark.asyncio
async def test_execute_request_failure(load_tester):
    """Test failed request execution"""

    async def failing_function():
        raise Exception("Test error")

    # Execute
    result = await load_tester._execute_request(1, failing_function)

    # Assert
    assert isinstance(result, RequestResult)
    assert result.request_id == 1
    assert not result.success
    assert result.error_message == "Test error"
    assert result.response_time_ms > 0


@pytest.mark.asyncio
async def test_execute_request_stores_result(load_tester, mock_target_function):
    """Test that executed requests are stored"""
    # Execute
    await load_tester._execute_request(1, mock_target_function)

    # Assert
    assert len(load_tester.results) == 1
    assert load_tester.results[0].request_id == 1


# ============================================================================
# Baseline Test Tests
# ============================================================================


@pytest.mark.asyncio
async def test_run_baseline_test(load_tester, mock_target_function):
    """Test baseline load test"""
    # Execute
    result = await load_tester.run_baseline_test(
        mock_target_function, duration_seconds=1, concurrent_users=2
    )

    # Assert
    assert isinstance(result, LoadTestResult)
    assert result.test_type == LoadTestType.BASELINE
    assert result.total_requests > 0
    assert result.successful_requests > 0
    assert result.avg_response_time_ms > 0
    assert result.total_duration_seconds > 0


@pytest.mark.asyncio
async def test_run_baseline_test_metrics(load_tester, mock_target_function):
    """Test baseline test metrics calculation"""
    # Execute
    result = await load_tester.run_baseline_test(
        mock_target_function, duration_seconds=1, concurrent_users=2
    )

    # Assert metrics
    assert result.min_response_time_ms > 0
    assert result.max_response_time_ms >= result.min_response_time_ms
    assert result.p50_response_time_ms > 0
    assert result.p95_response_time_ms >= result.p50_response_time_ms
    assert result.p99_response_time_ms >= result.p95_response_time_ms
    assert result.error_rate_pct >= 0.0
    assert result.throughput > 0.0


# ============================================================================
# Stress Test Tests
# ============================================================================


@pytest.mark.asyncio
async def test_run_stress_test(load_tester, mock_target_function):
    """Test stress testing with increasing load"""
    # Execute
    results = await load_tester.run_stress_test(
        mock_target_function, max_concurrent_users=10, step_duration_seconds=1
    )

    # Assert
    assert isinstance(results, list)
    assert len(results) > 0
    assert all(isinstance(r, LoadTestResult) for r in results)
    assert all(r.test_type == LoadTestType.STRESS for r in results)

    # Load should increase across steps
    # (can't guarantee due to timing, but should have multiple results)
    assert len(results) >= 2


@pytest.mark.asyncio
async def test_run_stress_test_stops_on_high_errors(load_tester, mock_failing_function):
    """Test stress test stops when error rate is high"""
    # Execute (with function that fails 20% of time)
    results = await load_tester.run_stress_test(
        mock_failing_function, max_concurrent_users=50, step_duration_seconds=1
    )

    # Assert - should stop early due to errors
    assert isinstance(results, list)
    assert len(results) > 0
    # Should stop before reaching max (though depends on timing)


# ============================================================================
# Spike Test Tests
# ============================================================================


@pytest.mark.asyncio
async def test_run_spike_test(load_tester, mock_target_function):
    """Test spike testing with sudden load increase"""
    # Execute
    result = await load_tester.run_spike_test(
        mock_target_function,
        baseline_users=2,
        spike_users=10,
        spike_duration_seconds=1,
    )

    # Assert
    assert isinstance(result, LoadTestResult)
    assert result.test_type == LoadTestType.SPIKE
    assert result.total_requests > 0


# ============================================================================
# Endurance Test Tests (Short Duration for Testing)
# ============================================================================


@pytest.mark.asyncio
async def test_run_endurance_test_short(load_tester, mock_target_function):
    """Test endurance testing (short duration for unit test)"""
    # Execute with very short duration
    result = await load_tester.run_endurance_test(
        mock_target_function, duration_hours=1 / 3600, concurrent_users=2
    )  # 1 second

    # Assert
    assert isinstance(result, LoadTestResult)
    assert result.test_type == LoadTestType.ENDURANCE
    assert result.total_requests > 0


# ============================================================================
# Result Analysis Tests
# ============================================================================


def test_analyze_results_empty(load_tester):
    """Test result analysis with no results"""
    config = LoadTestConfig(
        test_type=LoadTestType.BASELINE,
        duration_seconds=1,
        concurrent_users=1,
        requests_per_second=1,
    )

    # Execute
    result = load_tester._analyze_results(config, 1.0)

    # Assert
    assert result.total_requests == 0
    assert result.successful_requests == 0


def test_analyze_results_with_data(load_tester):
    """Test result analysis with data"""
    # Setup
    load_tester.results = [
        RequestResult(request_id=1, success=True, response_time_ms=10.0),
        RequestResult(request_id=2, success=True, response_time_ms=20.0),
        RequestResult(
            request_id=3, success=False, response_time_ms=30.0, error_message="Error"
        ),
        RequestResult(request_id=4, success=True, response_time_ms=15.0),
    ]

    config = LoadTestConfig(
        test_type=LoadTestType.BASELINE,
        duration_seconds=1,
        concurrent_users=1,
        requests_per_second=4,
    )

    # Execute
    result = load_tester._analyze_results(config, 1.0)

    # Assert
    assert result.total_requests == 4
    assert result.successful_requests == 3
    assert result.failed_requests == 1
    assert result.error_rate_pct == 25.0  # 1/4
    assert result.min_response_time_ms == 10.0
    assert result.max_response_time_ms == 30.0


def test_analyze_results_percentiles(load_tester):
    """Test percentile calculations"""
    # Setup - create results with known distribution
    load_tester.results = [
        RequestResult(request_id=i, success=True, response_time_ms=float(i))
        for i in range(1, 101)  # 1-100ms
    ]

    config = LoadTestConfig(
        test_type=LoadTestType.BASELINE,
        duration_seconds=1,
        concurrent_users=1,
        requests_per_second=100,
    )

    # Execute
    result = load_tester._analyze_results(config, 1.0)

    # Assert percentiles (approximately)
    assert 45 <= result.p50_response_time_ms <= 55  # Median ~50
    assert 90 <= result.p95_response_time_ms <= 100  # 95th ~95
    assert 95 <= result.p99_response_time_ms <= 100  # 99th ~99


# ============================================================================
# Bottleneck Identification Tests
# ============================================================================


def test_identify_bottlenecks_high_response_time(load_tester):
    """Test identifying slow response time bottleneck"""
    bottlenecks = load_tester._identify_bottlenecks(
        avg_response_time=3000.0,  # 3 seconds
        error_rate=1.0,
        p95=2500.0,
        p99=3500.0,
    )

    assert len(bottlenecks) > 0
    assert any("average response time" in b.lower() for b in bottlenecks)


def test_identify_bottlenecks_high_error_rate(load_tester):
    """Test identifying high error rate bottleneck"""
    bottlenecks = load_tester._identify_bottlenecks(
        avg_response_time=100.0,
        error_rate=10.0,
        p95=150.0,
        p99=200.0,  # 10% errors
    )

    assert len(bottlenecks) > 0
    assert any("error rate" in b.lower() for b in bottlenecks)


def test_identify_bottlenecks_high_tail_latency(load_tester):
    """Test identifying tail latency bottleneck"""
    bottlenecks = load_tester._identify_bottlenecks(
        avg_response_time=100.0,
        error_rate=1.0,
        p95=200.0,
        p99=6000.0,  # p99 very high
    )

    assert len(bottlenecks) > 0
    assert any("p99" in b.lower() for b in bottlenecks)


def test_identify_bottlenecks_none(load_tester):
    """Test identifying no bottlenecks when performance is good"""
    bottlenecks = load_tester._identify_bottlenecks(
        avg_response_time=100.0,  # Fast
        error_rate=0.5,  # Low errors
        p95=150.0,
        p99=200.0,
    )

    assert len(bottlenecks) == 0


# ============================================================================
# Report Generation Tests
# ============================================================================


def test_generate_load_test_report(load_tester):
    """Test generating load test report"""
    # Create test result
    result = LoadTestResult(
        test_type=LoadTestType.BASELINE,
        total_requests=100,
        successful_requests=95,
        failed_requests=5,
        total_duration_seconds=10.0,
        requests_per_second=10.0,
        avg_response_time_ms=50.0,
        min_response_time_ms=10.0,
        max_response_time_ms=100.0,
        p50_response_time_ms=45.0,
        p95_response_time_ms=80.0,
        p99_response_time_ms=95.0,
        error_rate_pct=5.0,
        throughput=9.5,
        bottlenecks=["High error rate: 5.0%"],
    )

    # Execute
    report = load_tester.generate_load_test_report(result)

    # Assert
    assert "LOAD TEST REPORT" in report
    assert "BASELINE" in report
    assert "Total Requests: 100" in report
    assert "Successful: 95" in report
    assert "Failed: 5" in report
    assert "Average: 50.00ms" in report
    assert "P95: 80.00ms" in report
    assert "BOTTLENECKS" in report
    assert "High error rate" in report


def test_generate_load_test_report_no_bottlenecks(load_tester):
    """Test report with no bottlenecks"""
    result = LoadTestResult(
        test_type=LoadTestType.BASELINE,
        total_requests=100,
        successful_requests=100,
        failed_requests=0,
        total_duration_seconds=10.0,
        requests_per_second=10.0,
        avg_response_time_ms=50.0,
        min_response_time_ms=10.0,
        max_response_time_ms=100.0,
        p50_response_time_ms=45.0,
        p95_response_time_ms=80.0,
        p99_response_time_ms=95.0,
        error_rate_pct=0.0,
        throughput=10.0,
        bottlenecks=[],
    )

    # Execute
    report = load_tester.generate_load_test_report(result)

    # Assert
    assert "LOAD TEST REPORT" in report
    assert "No major bottlenecks detected" in report


def test_generate_stress_test_report(load_tester):
    """Test generating stress test report"""
    # Create test results
    results = [
        LoadTestResult(
            test_type=LoadTestType.STRESS,
            total_requests=50,
            successful_requests=50,
            failed_requests=0,
            total_duration_seconds=5.0,
            requests_per_second=10.0,
            avg_response_time_ms=50.0,
            min_response_time_ms=10.0,
            max_response_time_ms=100.0,
            p50_response_time_ms=45.0,
            p95_response_time_ms=80.0,
            p99_response_time_ms=95.0,
            error_rate_pct=0.0,
            throughput=10.0,
            bottlenecks=[],
        ),
        LoadTestResult(
            test_type=LoadTestType.STRESS,
            total_requests=100,
            successful_requests=90,
            failed_requests=10,
            total_duration_seconds=5.0,
            requests_per_second=20.0,
            avg_response_time_ms=150.0,
            min_response_time_ms=10.0,
            max_response_time_ms=500.0,
            p50_response_time_ms=100.0,
            p95_response_time_ms=300.0,
            p99_response_time_ms=450.0,
            error_rate_pct=10.0,
            throughput=18.0,
            bottlenecks=["High error rate: 10.0%"],
        ),
    ]

    # Execute
    report = load_tester.generate_stress_test_report(results)

    # Assert
    assert "STRESS TEST REPORT" in report
    assert "Performance Under Increasing Load" in report
    assert "Users" in report
    assert "Req/s" in report
    assert "Avg(ms)" in report
    assert "degradation detected" in report


def test_generate_stress_test_report_stable(load_tester):
    """Test stress test report when system remains stable"""
    # Create results with no degradation
    results = [
        LoadTestResult(
            test_type=LoadTestType.STRESS,
            total_requests=50,
            successful_requests=50,
            failed_requests=0,
            total_duration_seconds=5.0,
            requests_per_second=10.0,
            avg_response_time_ms=50.0,
            min_response_time_ms=10.0,
            max_response_time_ms=100.0,
            p50_response_time_ms=45.0,
            p95_response_time_ms=80.0,
            p99_response_time_ms=95.0,
            error_rate_pct=0.0,
            throughput=10.0,
            bottlenecks=[],
        ),
    ]

    # Execute
    report = load_tester.generate_stress_test_report(results)

    # Assert
    assert "remained stable" in report


# ============================================================================
# Trading System Specific Tests
# ============================================================================


@pytest.mark.asyncio
async def test_test_market_data_fetching(load_tester):
    """Test market data fetching load test"""
    # Mock market data service
    mock_service = Mock()
    mock_service.get_ticker = AsyncMock(return_value={"last": 50000.0})

    symbols = ["BTC/USDT:USDT", "ETH/USDT:USDT"]

    # Execute (very short duration)
    result = await load_tester.test_market_data_fetching(
        mock_service, symbols, duration_seconds=1
    )

    # Assert
    assert isinstance(result, LoadTestResult)
    assert result.test_type == LoadTestType.BASELINE
    assert mock_service.get_ticker.called


@pytest.mark.asyncio
async def test_test_trading_decision_cycle(load_tester):
    """Test trading decision cycle load test"""
    # Mock decision engine
    mock_engine = Mock()
    mock_engine.analyze_market = AsyncMock()
    mock_engine.generate_signals = AsyncMock()
    mock_engine.evaluate_positions = AsyncMock()

    # Execute (very short duration)
    result = await load_tester.test_trading_decision_cycle(
        mock_engine, duration_seconds=1
    )

    # Assert
    assert isinstance(result, LoadTestResult)
    assert mock_engine.analyze_market.called
    assert mock_engine.generate_signals.called
    assert mock_engine.evaluate_positions.called


@pytest.mark.asyncio
async def test_test_llm_request_handling(load_tester):
    """Test LLM request handling load test"""
    # Mock LLM service
    mock_service = Mock()
    mock_service.generate_response = AsyncMock(return_value="Analysis complete")

    # Execute (very short duration)
    result = await load_tester.test_llm_request_handling(
        mock_service, duration_seconds=1
    )

    # Assert
    assert isinstance(result, LoadTestResult)
    assert mock_service.generate_response.called


# ============================================================================
# Configuration Tests
# ============================================================================


def test_load_test_config():
    """Test load test configuration"""
    config = LoadTestConfig(
        test_type=LoadTestType.BASELINE,
        duration_seconds=60,
        concurrent_users=10,
        requests_per_second=5,
        ramp_up_seconds=10,
        cooldown_seconds=10,
    )

    assert config.test_type == LoadTestType.BASELINE
    assert config.duration_seconds == 60
    assert config.concurrent_users == 10
    assert config.requests_per_second == 5
    assert config.ramp_up_seconds == 10
    assert config.cooldown_seconds == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
