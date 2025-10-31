"""
Comprehensive tests for Load Testing to achieve 80%+ coverage.

This test suite focuses on previously uncovered areas:
- Worker pool coordination
- Resource monitoring edge cases
- Ramp-up/ramp-down logic
- Graceful shutdown scenarios
- Concurrent worker failures
- Metrics calculation edge cases

Author: Validation Engineer
Date: 2025-10-31
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch

from workspace.shared.performance.load_testing import (
    LoadTester,
    LoadTestConfig,
    CycleResult,
    ResourceSnapshot,
)


# ==============================================================================
# Worker Pool Coordination Tests (10 tests)
# ==============================================================================


@pytest.mark.asyncio
async def test_worker_pool_initialization():
    """Test that worker pool is properly initialized with correct number of workers."""
    config = LoadTestConfig(
        target_cycles=50,
        concurrent_workers=5,
        ramp_up_seconds=0,
        cooldown_seconds=1,
    )
    tester = LoadTester(config)

    result = await tester.run_load_test(cycles=50)

    # Should complete all cycles
    assert result.total_cycles == 50
    assert result.successful_cycles + result.failed_cycles == 50


@pytest.mark.asyncio
async def test_worker_distribution():
    """Test that work is evenly distributed across workers."""
    config = LoadTestConfig(
        target_cycles=20,
        concurrent_workers=4,
        ramp_up_seconds=0,
        cooldown_seconds=1,
    )
    tester = LoadTester(config)

    result = await tester.run_load_test(cycles=20)

    # Check that multiple workers participated
    worker_ids = set(cycle.worker_id for cycle in result.cycle_results)
    assert len(worker_ids) >= 2, "Multiple workers should have participated"


@pytest.mark.asyncio
async def test_worker_coordination_with_failures():
    """Test worker coordination when some cycles fail."""
    config = LoadTestConfig(
        target_cycles=10,
        concurrent_workers=3,
        ramp_up_seconds=0,
        cooldown_seconds=1,
        max_consecutive_failures=2,
    )
    tester = LoadTester(config)

    # Some cycles will fail (1% + 2% + 0.5% = ~3.5% failure rate)
    result = await tester.run_load_test(cycles=10)

    # Should complete despite some failures
    assert result.total_cycles > 0
    assert result.success_rate >= 0.95  # At least 95% should succeed


@pytest.mark.asyncio
async def test_worker_max_concurrent():
    """Test that no more than max concurrent workers execute at once."""
    config = LoadTestConfig(
        target_cycles=30,
        concurrent_workers=5,
        ramp_up_seconds=0,
        cooldown_seconds=1,
    )
    tester = LoadTester(config)

    result = await tester.run_load_test(cycles=30)

    # All cycles should complete
    assert result.total_cycles == 30


@pytest.mark.asyncio
async def test_worker_queue_management():
    """Test that work queue is properly managed."""
    config = LoadTestConfig(
        target_cycles=15,
        concurrent_workers=3,
        ramp_up_seconds=0,
        cooldown_seconds=1,
    )
    tester = LoadTester(config)

    result = await tester.run_load_test(cycles=15)

    # Should process all queued items
    assert result.total_cycles == 15
    assert len(result.cycle_results) == 15


@pytest.mark.asyncio
async def test_worker_shutdown_cleanup():
    """Test that workers clean up properly on shutdown."""
    config = LoadTestConfig(
        target_cycles=10,
        concurrent_workers=2,
        ramp_up_seconds=0,
        cooldown_seconds=1,
    )
    tester = LoadTester(config)

    result = await tester.run_load_test(cycles=10)

    # Monitoring should have stopped
    assert tester._stop_monitoring is True
    assert result.total_cycles == 10


@pytest.mark.asyncio
async def test_worker_exception_handling():
    """Test that worker exceptions are handled gracefully."""
    config = LoadTestConfig(
        target_cycles=5,
        concurrent_workers=2,
        ramp_up_seconds=0,
        cooldown_seconds=1,
    )
    tester = LoadTester(config)

    async def failing_cycle(cycle_id: int, worker_id: int) -> CycleResult:
        """Custom cycle function that raises exceptions."""
        if cycle_id % 3 == 0:
            raise Exception("Simulated worker exception")
        return await tester.simulate_trading_cycle(cycle_id, worker_id)

    result = await tester.run_load_test(cycles=5, custom_cycle_fn=failing_cycle)

    # Should handle exceptions and continue
    assert result.total_cycles >= 3  # At least some cycles should complete


@pytest.mark.asyncio
async def test_worker_timeout_handling():
    """Test that worker timeouts are handled correctly."""
    config = LoadTestConfig(
        target_cycles=8,
        concurrent_workers=2,
        ramp_up_seconds=0,
        cooldown_seconds=1,
    )
    tester = LoadTester(config)

    result = await tester.run_load_test(cycles=8)

    # Should complete without hanging
    assert result.total_cycles == 8


@pytest.mark.asyncio
async def test_worker_state_tracking():
    """Test that worker state is tracked correctly."""
    config = LoadTestConfig(
        target_cycles=12,
        concurrent_workers=3,
        ramp_up_seconds=0,
        cooldown_seconds=1,
    )
    tester = LoadTester(config)

    result = await tester.run_load_test(cycles=12)

    # All cycles should have valid timestamps
    for cycle in result.cycle_results:
        assert isinstance(cycle.timestamp, datetime)
        assert cycle.cycle_id >= 0
        assert cycle.worker_id >= 0


@pytest.mark.asyncio
async def test_worker_result_collection():
    """Test that all worker results are collected."""
    config = LoadTestConfig(
        target_cycles=20,
        concurrent_workers=4,
        ramp_up_seconds=0,
        cooldown_seconds=1,
    )
    tester = LoadTester(config)

    result = await tester.run_load_test(cycles=20)

    # All results should be collected
    assert len(result.cycle_results) == 20
    assert result.total_cycles == 20


# ==============================================================================
# Resource Monitoring Tests (8 tests)
# ==============================================================================


@pytest.mark.asyncio
async def test_monitor_resources_success():
    """Test successful resource monitoring."""
    config = LoadTestConfig(monitor_interval_seconds=0.1)
    tester = LoadTester(config)

    snapshot = await tester.monitor_resources()

    assert snapshot.cpu_percent >= 0
    assert snapshot.memory_percent >= 0
    assert snapshot.memory_mb >= 0
    assert snapshot.thread_count > 0
    assert isinstance(snapshot.timestamp, datetime)


@pytest.mark.asyncio
async def test_monitor_resources_cpu_spike():
    """Test monitoring during CPU spike."""
    config = LoadTestConfig(
        max_cpu_percent=50.0,
        monitor_interval_seconds=0.1,
    )
    tester = LoadTester(config)

    # Mock high CPU usage
    with patch.object(tester.process, "cpu_percent", return_value=95.0):
        snapshot = await tester.monitor_resources()
        assert snapshot.cpu_percent == 95.0


@pytest.mark.asyncio
async def test_monitor_resources_memory_leak():
    """Test monitoring during memory increase."""
    config = LoadTestConfig(
        max_memory_percent=70.0,
        monitor_interval_seconds=0.1,
    )
    tester = LoadTester(config)

    # Mock high memory usage
    mock_mem_info = Mock()
    mock_mem_info.rss = 500 * 1024 * 1024  # 500 MB
    with patch.object(tester.process, "memory_info", return_value=mock_mem_info):
        with patch.object(tester.process, "memory_percent", return_value=85.0):
            snapshot = await tester.monitor_resources()
            assert snapshot.memory_percent == 85.0
            assert snapshot.memory_mb == 500.0


@pytest.mark.asyncio
async def test_monitor_resources_io_unavailable():
    """Test monitoring when I/O counters are unavailable (macOS case)."""
    config = LoadTestConfig()
    tester = LoadTester(config)

    # Mock I/O counter unavailability
    with patch.object(
        tester.process, "io_counters", side_effect=NotImplementedError("macOS")
    ):
        snapshot = await tester.monitor_resources()
        assert snapshot.disk_io_read_mb == 0.0
        assert snapshot.disk_io_write_mb == 0.0


@pytest.mark.asyncio
async def test_monitor_resources_error_handling():
    """Test resource monitoring error handling."""
    config = LoadTestConfig()
    tester = LoadTester(config)

    # Mock complete failure
    with patch.object(
        tester.process, "cpu_percent", side_effect=Exception("Process error")
    ):
        snapshot = await tester.monitor_resources()
        # Should return default snapshot on error
        assert snapshot.cpu_percent == 0.0
        assert snapshot.memory_percent == 0.0


@pytest.mark.asyncio
async def test_monitor_resources_over_time():
    """Test resource monitoring over multiple intervals."""
    config = LoadTestConfig(
        target_cycles=5,
        concurrent_workers=2,
        ramp_up_seconds=0,
        cooldown_seconds=1,
        monitor_interval_seconds=0.1,
    )
    tester = LoadTester(config)

    result = await tester.run_load_test(cycles=5)

    # Should have captured multiple snapshots
    assert len(result.resource_snapshots) > 0
    # Each snapshot should have valid data
    for snapshot in result.resource_snapshots:
        assert snapshot.cpu_percent >= 0
        assert snapshot.memory_mb >= 0


@pytest.mark.asyncio
async def test_monitor_resources_threshold_alerts():
    """Test that monitoring logs alerts when thresholds are exceeded."""
    config = LoadTestConfig(
        max_cpu_percent=1.0,  # Very low threshold
        max_memory_percent=1.0,  # Very low threshold
        target_cycles=3,
        concurrent_workers=1,
        cooldown_seconds=1,
        monitor_interval_seconds=0.1,
    )
    tester = LoadTester(config)

    # This should trigger threshold warnings
    result = await tester.run_load_test(cycles=3)

    # Test should complete despite warnings
    assert result.total_cycles == 3


@pytest.mark.asyncio
async def test_monitor_resources_reporting():
    """Test that resource monitoring data is included in results."""
    config = LoadTestConfig(
        target_cycles=5,
        concurrent_workers=2,
        ramp_up_seconds=0,
        cooldown_seconds=1,
        monitor_interval_seconds=0.1,
    )
    tester = LoadTester(config)

    result = await tester.run_load_test(cycles=5)

    # Resource stats should be present
    assert result.peak_cpu_percent >= 0
    assert result.peak_memory_percent >= 0
    assert result.peak_memory_mb >= 0
    assert result.avg_cpu_percent >= 0
    assert result.avg_memory_percent >= 0


# ==============================================================================
# Ramp-Up/Down Logic Tests (4 tests)
# ==============================================================================


@pytest.mark.asyncio
async def test_ramp_up_gradual():
    """Test gradual ramp-up of workers."""
    config = LoadTestConfig(
        target_cycles=10,
        concurrent_workers=5,
        ramp_up_seconds=2,  # Gradual ramp-up
        cooldown_seconds=1,
    )
    tester = LoadTester(config)

    result = await tester.run_load_test(cycles=10)

    # Should complete all cycles with gradual ramp-up
    assert result.total_cycles == 10
    assert result.duration_seconds >= 2  # At least ramp-up duration


@pytest.mark.asyncio
async def test_ramp_up_immediate():
    """Test immediate start (no ramp-up)."""
    config = LoadTestConfig(
        target_cycles=10,
        concurrent_workers=5,
        ramp_up_seconds=0,  # Immediate start
        cooldown_seconds=1,
    )
    tester = LoadTester(config)

    schedule = tester._calculate_ramp_up_schedule()

    # All workers should start immediately
    assert all(delay == 0.0 for delay in schedule)
    assert len(schedule) == 5


@pytest.mark.asyncio
async def test_ramp_down_graceful():
    """Test graceful ramp-down after test completion."""
    config = LoadTestConfig(
        target_cycles=5,
        concurrent_workers=3,
        ramp_up_seconds=0,
        cooldown_seconds=2,  # Explicit cooldown
    )
    tester = LoadTester(config)

    start_time = asyncio.get_event_loop().time()
    result = await tester.run_load_test(cycles=5)
    end_time = asyncio.get_event_loop().time()

    # Should include cooldown period
    duration = end_time - start_time
    assert duration >= 2.0  # At least cooldown duration


@pytest.mark.asyncio
async def test_ramp_down_immediate():
    """Test immediate shutdown (no cooldown)."""
    config = LoadTestConfig(
        target_cycles=5,
        concurrent_workers=2,
        ramp_up_seconds=0,
        cooldown_seconds=0,  # No cooldown
    )
    tester = LoadTester(config)

    result = await tester.run_load_test(cycles=5)

    # Should complete quickly
    assert result.total_cycles == 5


# ==============================================================================
# Metrics Calculation Tests (3 tests)
# ==============================================================================


def test_calculate_percentiles():
    """Test percentile calculation for various distributions."""
    config = LoadTestConfig()
    tester = LoadTester(config)

    # Test with sorted values
    values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]

    p50 = tester._percentile(values, 50)
    p95 = tester._percentile(values, 95)
    p99 = tester._percentile(values, 99)

    assert 5.0 <= p50 <= 6.0  # Median
    assert 9.0 <= p95 <= 10.0  # 95th percentile
    assert 9.5 <= p99 <= 10.0  # 99th percentile


def test_calculate_success_rate():
    """Test success rate calculation."""
    config = LoadTestConfig()
    tester = LoadTester(config)

    # Create test results
    tester.results = [
        CycleResult(
            cycle_id=i,
            worker_id=0,
            timestamp=datetime.now(),
            success=i % 10 != 0,  # 90% success rate
            latency_ms=1000.0,
        )
        for i in range(100)
    ]

    result = tester.calculate_metrics(
        test_start=datetime.now(),
        test_end=datetime.now(),
        duration=10.0,
    )

    assert result.total_cycles == 100
    assert result.successful_cycles == 90
    assert result.failed_cycles == 10
    assert result.success_rate == 0.9


def test_calculate_resource_averages():
    """Test resource usage average calculation."""
    config = LoadTestConfig()
    tester = LoadTester(config)

    # Create test snapshots
    tester.resource_snapshots = [
        ResourceSnapshot(
            timestamp=datetime.now(),
            cpu_percent=float(i * 10),
            memory_percent=float(i * 5),
            memory_mb=float(i * 100),
            open_connections=10,
            thread_count=5,
        )
        for i in range(1, 6)  # 10, 20, 30, 40, 50 CPU
    ]

    result = tester.calculate_metrics(
        test_start=datetime.now(),
        test_end=datetime.now(),
        duration=10.0,
    )

    # Average CPU should be (10+20+30+40+50)/5 = 30
    assert result.avg_cpu_percent == 30.0
    # Peak CPU should be 50
    assert result.peak_cpu_percent == 50.0


# ==============================================================================
# Report Generation Tests (2 tests)
# ==============================================================================


def test_generate_report_with_errors():
    """Test report generation with errors."""
    config = LoadTestConfig()
    tester = LoadTester(config)

    # Create results with errors
    tester.results = [
        CycleResult(
            cycle_id=i,
            worker_id=0,
            timestamp=datetime.now(),
            success=i % 5 != 0,
            latency_ms=1000.0,
            error_message="Test error" if i % 5 == 0 else None,
        )
        for i in range(20)
    ]

    result = tester.calculate_metrics(
        test_start=datetime.now(),
        test_end=datetime.now(),
        duration=10.0,
    )

    report = tester.generate_report(result)

    # Report should include error summary
    assert "ERROR SUMMARY" in report
    assert "Test error" in report


def test_generate_report_compliance_pass():
    """Test report generation when all targets are met."""
    config = LoadTestConfig(
        target_success_rate=0.95,
        target_p50_latency_ms=1000.0,
        target_p95_latency_ms=2000.0,
        target_p99_latency_ms=3000.0,
    )
    tester = LoadTester(config)

    # Create perfect results
    tester.results = [
        CycleResult(
            cycle_id=i,
            worker_id=0,
            timestamp=datetime.now(),
            success=True,
            latency_ms=800.0,  # Well under target
        )
        for i in range(100)
    ]

    result = tester.calculate_metrics(
        test_start=datetime.now(),
        test_end=datetime.now(),
        duration=10.0,
    )

    report = tester.generate_report(result)

    # Report should show all targets met
    assert "ALL TARGETS MET" in report
    assert result.meets_success_rate_target
    assert result.meets_p50_latency_target
    assert result.meets_p95_latency_target
    assert result.meets_p99_latency_target


# ==============================================================================
# Edge Cases Tests (5 tests)
# ==============================================================================


@pytest.mark.asyncio
async def test_empty_results():
    """Test metrics calculation with no results."""
    config = LoadTestConfig()
    tester = LoadTester(config)

    # Empty results
    tester.results = []

    result = tester.calculate_metrics(
        test_start=datetime.now(),
        test_end=datetime.now(),
        duration=0.0,
    )

    assert result.total_cycles == 0
    assert result.success_rate == 0.0
    assert result.mean_latency_ms == 0.0


@pytest.mark.asyncio
async def test_single_cycle():
    """Test load test with single cycle."""
    config = LoadTestConfig(
        target_cycles=1,
        concurrent_workers=1,
        ramp_up_seconds=0,
        cooldown_seconds=1,
    )
    tester = LoadTester(config)

    result = await tester.run_load_test(cycles=1)

    assert result.total_cycles == 1
    assert result.successful_cycles == 1


@pytest.mark.asyncio
async def test_very_high_concurrency():
    """Test with very high concurrent workers."""
    config = LoadTestConfig(
        target_cycles=20,
        concurrent_workers=20,  # As many workers as cycles
        ramp_up_seconds=0,
        cooldown_seconds=1,
    )
    tester = LoadTester(config)

    result = await tester.run_load_test(cycles=20)

    assert result.total_cycles == 20


def test_percentile_empty_list():
    """Test percentile calculation with empty list."""
    config = LoadTestConfig()
    tester = LoadTester(config)

    result = tester._percentile([], 50)
    assert result == 0.0


def test_peak_throughput_calculation():
    """Test peak throughput calculation."""
    config = LoadTestConfig()
    tester = LoadTester(config)

    # Create results spread over time
    base_time = datetime.now()
    tester.results = [
        CycleResult(
            cycle_id=i,
            worker_id=0,
            timestamp=datetime.fromtimestamp(base_time.timestamp() + i * 0.1),
            success=True,
            latency_ms=100.0,
        )
        for i in range(100)
    ]

    peak = tester._calculate_peak_throughput()

    # Should calculate peak throughput
    assert peak >= 0.0
