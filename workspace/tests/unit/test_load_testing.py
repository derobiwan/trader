"""
Unit tests for Load Testing Framework.

Tests core functionality:
- Trading cycle simulation
- Load test execution
- Metrics calculation
- Resource monitoring
- Worker management

Target: 80%+ code coverage
"""

import pytest
import asyncio
from unittest.mock import patch
from datetime import datetime
from workspace.shared.performance.load_testing import (
    LoadTester,
    LoadTestConfig,
    CycleResult,
    ResourceSnapshot,
    LoadTestResult,
)


@pytest.fixture
def load_config():
    """Create load test configuration."""
    return LoadTestConfig(
        target_cycles=10,
        concurrent_workers=2,
        ramp_up_seconds=1,
        test_duration_seconds=None,
        cooldown_seconds=1,
    )


@pytest.fixture
def load_tester(load_config):
    """Create LoadTester instance."""
    return LoadTester(load_config)


@pytest.mark.asyncio
async def test_simulate_trading_cycle_success(load_tester):
    """Test successful trading cycle simulation."""
    # Act
    result = await load_tester.simulate_trading_cycle(cycle_id=1, worker_id=0)

    # Assert
    assert isinstance(result, CycleResult)
    assert result.cycle_id == 1
    assert result.worker_id == 0
    assert result.success is True
    assert result.latency_ms > 0
    assert "market_data_fetch" in result.stages
    assert "llm_decision" in result.stages
    assert "trade_execution" in result.stages


@pytest.mark.asyncio
async def test_simulate_trading_cycle_failure(load_tester):
    """Test trading cycle simulation with failure."""
    # Arrange
    with patch.object(
        load_tester, "_simulate_market_data_fetch", side_effect=Exception("API error")
    ):
        # Act
        result = await load_tester.simulate_trading_cycle(cycle_id=1, worker_id=0)

        # Assert
        assert result.success is False
        assert result.error_message == "API error"
        assert result.latency_ms > 0


@pytest.mark.asyncio
async def test_run_load_test_success(load_tester):
    """Test successful load test execution."""
    # Act
    result = await load_tester.run_load_test(cycles=5)

    # Assert
    assert isinstance(result, LoadTestResult)
    assert result.total_cycles == 5
    assert result.duration_seconds > 0
    assert result.cycles_per_second > 0


@pytest.mark.asyncio
async def test_run_load_test_with_custom_cycle_fn(load_tester):
    """Test load test with custom cycle function."""

    # Arrange
    async def custom_cycle(cycle_id, worker_id):
        return CycleResult(
            cycle_id=cycle_id,
            worker_id=worker_id,
            timestamp=datetime.now(),
            success=True,
            latency_ms=100.0,
        )

    # Act
    result = await load_tester.run_load_test(cycles=5, custom_cycle_fn=custom_cycle)

    # Assert
    assert result.total_cycles == 5
    assert result.mean_latency_ms == pytest.approx(100.0, rel=0.1)


@pytest.mark.asyncio
async def test_calculate_ramp_up_schedule(load_tester):
    """Test ramp-up schedule calculation."""
    # Act
    delays = load_tester._calculate_ramp_up_schedule()

    # Assert
    assert len(delays) == load_tester.config.concurrent_workers
    assert delays[0] == 0.0
    assert delays[-1] < load_tester.config.ramp_up_seconds


@pytest.mark.asyncio
async def test_calculate_ramp_up_schedule_no_ramp(load_tester):
    """Test ramp-up schedule with no ramp-up."""
    # Arrange
    load_tester.config.ramp_up_seconds = 0

    # Act
    delays = load_tester._calculate_ramp_up_schedule()

    # Assert
    assert all(delay == 0.0 for delay in delays)


@pytest.mark.asyncio
async def test_monitor_resources(load_tester):
    """Test resource monitoring."""
    # Arrange
    load_tester._stop_monitoring = False

    # Start monitoring
    monitor_task = asyncio.create_task(load_tester._monitor_resources())

    # Let it run briefly
    await asyncio.sleep(0.2)

    # Stop monitoring
    load_tester._stop_monitoring = True
    await monitor_task

    # Assert
    assert len(load_tester.resource_snapshots) > 0
    snapshot = load_tester.resource_snapshots[0]
    assert isinstance(snapshot, ResourceSnapshot)
    assert snapshot.cpu_percent >= 0
    assert snapshot.memory_mb > 0


def test_calculate_metrics(load_tester):
    """Test metrics calculation."""
    # Arrange
    load_tester.results = [
        CycleResult(i, 0, datetime.now(), True, 100.0 + i * 10) for i in range(10)
    ]

    # Act
    metrics = load_tester.calculate_metrics(
        test_start=datetime.now(), test_end=datetime.now(), duration=10.0
    )

    # Assert
    assert isinstance(metrics, LoadTestResult)
    assert metrics.total_cycles == 10
    assert metrics.successful_cycles == 10
    assert metrics.mean_latency_ms > 0


def test_calculate_percentiles(load_tester):
    """Test percentile calculations."""
    # Arrange
    latencies = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]

    # Act
    p50 = load_tester._percentile(sorted(latencies), 50)
    p95 = load_tester._percentile(sorted(latencies), 95)
    p99 = load_tester._percentile(sorted(latencies), 99)

    # Assert
    assert p50 == pytest.approx(55.0, rel=0.1)
    assert p95 == pytest.approx(95.0, rel=0.1)
    assert p99 == pytest.approx(99.0, rel=0.1)


def test_load_test_config_defaults():
    """Test LoadTestConfig defaults."""
    config = LoadTestConfig()

    assert config.target_cycles == 1000
    assert config.concurrent_workers == 10
    assert config.target_success_rate == 0.995
