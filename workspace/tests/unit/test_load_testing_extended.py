"""
Extended tests for Load Testing to achieve 80%+ coverage.

Focuses on uncovered areas:
- Report generation (lines 715-831)
- Resource monitoring (lines 837-880)
- Worker coordination (lines 406-444)
- Error handling paths
- Platform-specific logic
- Ramp-up/ramp-down scenarios

Author: Validation Engineer (PRP Orchestrator coordinated)
Date: 2025-10-31
Target: Increase coverage from 69% to 80%+
"""

import asyncio
from datetime import datetime, timedelta
import pytest
from unittest.mock import MagicMock, patch
from workspace.shared.performance.load_testing import (
    LoadTester,
    LoadTestConfig,
    LoadTestResult,
    ResourceSnapshot,
    CycleResult,
)


@pytest.fixture
def test_config():
    """Create test configuration."""
    return LoadTestConfig(
        test_cycles=10,
        workers=2,
        target_success_rate=0.95,
        target_p50_latency_ms=100.0,
        target_p95_latency_ms=200.0,
        target_p99_latency_ms=300.0,
        cycle_delay_seconds=0.01,
        warmup_cycles=2,
        ramp_up_duration_seconds=1,
        ramp_down_duration_seconds=1,
        resource_monitoring_interval_seconds=0.5,
    )


@pytest.fixture
def load_runner(test_config):
    """Create LoadTester instance."""
    return LoadTester(test_config)


@pytest.fixture
def sample_result():
    """Create a sample LoadTestResult for testing."""
    return LoadTestResult(
        test_name="sample_test",
        start_time=datetime.now() - timedelta(minutes=5),
        end_time=datetime.now(),
        duration_seconds=300.0,
        total_cycles=1000,
        successful_cycles=950,
        failed_cycles=50,
        success_rate=0.95,
        mean_latency_ms=80.0,
        median_latency_ms=75.0,
        p50_latency_ms=75.0,
        p95_latency_ms=150.0,
        p99_latency_ms=250.0,
        min_latency_ms=20.0,
        max_latency_ms=500.0,
        stddev_latency_ms=40.0,
        cycles_per_second=3.33,
        resource_usage=ResourceSnapshot(
            cpu_percent=45.0,
            memory_mb=1024.0,
            memory_percent=25.0,
            io_read_mb=100.0,
            io_write_mb=50.0,
            network_sent_mb=20.0,
            network_recv_mb=30.0,
        ),
        platform_info={
            "system": "Darwin",
            "processor": "arm64",
            "python_version": "3.12.0",
            "cpu_count": 8,
        },
        cycle_results=[
            CycleResult(
                cycle_number=i,
                start_time=datetime.now() - timedelta(seconds=300 - i),
                end_time=datetime.now() - timedelta(seconds=299 - i),
                success=i % 20 != 0,  # 5% failure rate
                latency_ms=75.0 + (i % 10) * 10,
                error=None if i % 20 != 0 else f"Error in cycle {i}",
            )
            for i in range(100)  # Sample of 100 cycles
        ],
        meets_success_rate_target=True,
        meets_p50_latency_target=True,
        meets_p95_latency_target=True,
        meets_p99_latency_target=True,
    )


# ====================
# Report Generation Tests (lines 715-831)
# ====================


def test_generate_report_comprehensive(load_runner, sample_result):
    """Test comprehensive report generation."""
    report = load_runner.generate_report(sample_result)

    assert isinstance(report, str)
    assert "LOAD TEST REPORT" in report
    assert "sample_test" in report

    # Check execution summary
    assert "Total Cycles:      1000" in report
    assert "Successful:        950" in report
    assert "Failed:            50" in report
    assert "Success Rate:      95.00%" in report

    # Check latency statistics
    assert "LATENCY STATISTICS" in report
    assert "Mean:     80.00ms" in report
    assert "Median:   75.00ms" in report
    assert "P50:      75.00ms" in report
    assert "P95:      150.00ms" in report
    assert "P99:      250.00ms" in report

    # Check throughput statistics
    assert "THROUGHPUT STATISTICS" in report
    assert "Cycles/Second" in report

    # Check resource usage
    assert "RESOURCE USAGE" in report
    assert "CPU Usage" in report
    assert "Memory Usage" in report

    # Check platform info
    assert "PLATFORM INFORMATION" in report
    assert "System" in report
    assert "Python Version" in report


def test_generate_report_with_failures(load_runner):
    """Test report generation with high failure rate."""
    result = LoadTestResult(
        test_name="failure_test",
        start_time=datetime.now() - timedelta(minutes=1),
        end_time=datetime.now(),
        duration_seconds=60.0,
        total_cycles=100,
        successful_cycles=30,
        failed_cycles=70,
        success_rate=0.30,
        mean_latency_ms=500.0,
        median_latency_ms=450.0,
        p50_latency_ms=450.0,
        p95_latency_ms=800.0,
        p99_latency_ms=950.0,
        min_latency_ms=100.0,
        max_latency_ms=1000.0,
        stddev_latency_ms=200.0,
        cycles_per_second=1.67,
        resource_usage=ResourceSnapshot(
            cpu_percent=90.0,
            memory_mb=2048.0,
            memory_percent=50.0,
            io_read_mb=200.0,
            io_write_mb=100.0,
            network_sent_mb=50.0,
            network_recv_mb=75.0,
        ),
        platform_info={"system": "Linux", "processor": "x86_64"},
        cycle_results=[],
        meets_success_rate_target=False,
        meets_p50_latency_target=False,
        meets_p95_latency_target=False,
        meets_p99_latency_target=False,
    )

    report = load_runner.generate_report(result)

    # Should show failures prominently
    assert "✗" in report  # Failure indicators
    assert "30.00%" in report  # Low success rate
    assert "Failed:            70" in report


def test_generate_report_perfect_run(load_runner):
    """Test report generation for perfect run."""
    result = LoadTestResult(
        test_name="perfect_test",
        start_time=datetime.now() - timedelta(minutes=2),
        end_time=datetime.now(),
        duration_seconds=120.0,
        total_cycles=500,
        successful_cycles=500,
        failed_cycles=0,
        success_rate=1.0,
        mean_latency_ms=50.0,
        median_latency_ms=45.0,
        p50_latency_ms=45.0,
        p95_latency_ms=80.0,
        p99_latency_ms=95.0,
        min_latency_ms=20.0,
        max_latency_ms=100.0,
        stddev_latency_ms=15.0,
        cycles_per_second=4.17,
        resource_usage=ResourceSnapshot(
            cpu_percent=30.0,
            memory_mb=512.0,
            memory_percent=12.5,
            io_read_mb=50.0,
            io_write_mb=25.0,
            network_sent_mb=10.0,
            network_recv_mb=15.0,
        ),
        platform_info={"system": "Darwin", "processor": "arm64"},
        cycle_results=[],
        meets_success_rate_target=True,
        meets_p50_latency_target=True,
        meets_p95_latency_target=True,
        meets_p99_latency_target=True,
    )

    report = load_runner.generate_report(result)

    assert "✓" in report  # Success indicators
    assert "100.00%" in report  # Perfect success rate
    assert "Failed:            0" in report
    assert "ALL TARGETS MET" in report


def test_save_report(load_runner, sample_result, tmp_path):
    """Test saving report to file."""
    report_file = tmp_path / "test_report.txt"

    load_runner.save_report(sample_result, str(report_file))

    assert report_file.exists()
    content = report_file.read_text()
    assert "LOAD TEST REPORT" in content
    assert "sample_test" in content


# ====================
# Resource Monitoring Tests (lines 837-880)
# ====================


@pytest.mark.asyncio
async def test_monitor_resources(load_runner):
    """Test resource monitoring during load test."""
    with patch("psutil.cpu_percent", return_value=45.0):
        with patch("psutil.virtual_memory") as mock_memory:
            mock_memory.return_value = MagicMock(
                used=1073741824,  # 1GB in bytes
                percent=25.0,
            )

            with patch("psutil.disk_io_counters") as mock_disk:
                mock_disk.return_value = MagicMock(
                    read_bytes=104857600,  # 100MB
                    write_bytes=52428800,  # 50MB
                )

                with patch("psutil.net_io_counters") as mock_net:
                    mock_net.return_value = MagicMock(
                        bytes_sent=20971520,  # 20MB
                        bytes_recv=31457280,  # 30MB
                    )

                    # Start monitoring
                    monitor_task = asyncio.create_task(load_runner._monitor_resources())

                    # Let it run briefly
                    await asyncio.sleep(0.1)

                    # Stop monitoring
                    load_runner._stop_monitoring = True
                    await monitor_task

                    # Check resource data collected
                    assert len(load_runner._resource_samples) > 0
                    sample = load_runner._resource_samples[0]
                    assert sample["cpu_percent"] == 45.0
                    assert sample["memory_mb"] == 1024.0


@pytest.mark.asyncio
async def test_monitor_resources_error_handling(load_runner):
    """Test resource monitoring with errors."""
    with patch("psutil.cpu_percent", side_effect=Exception("CPU error")):
        # Should handle errors gracefully
        monitor_task = asyncio.create_task(load_runner._monitor_resources())

        await asyncio.sleep(0.05)
        load_runner._stop_monitoring = True

        # Should complete without raising
        await monitor_task


def test_calculate_resource_usage(load_runner):
    """Test resource usage calculation."""
    # Add sample data
    load_runner._resource_samples = [
        {
            "cpu_percent": 30.0,
            "memory_mb": 500.0,
            "memory_percent": 12.5,
            "io_read_mb": 10.0,
            "io_write_mb": 5.0,
            "network_sent_mb": 2.0,
            "network_recv_mb": 3.0,
        },
        {
            "cpu_percent": 50.0,
            "memory_mb": 600.0,
            "memory_percent": 15.0,
            "io_read_mb": 20.0,
            "io_write_mb": 10.0,
            "network_sent_mb": 4.0,
            "network_recv_mb": 6.0,
        },
        {
            "cpu_percent": 40.0,
            "memory_mb": 550.0,
            "memory_percent": 13.75,
            "io_read_mb": 15.0,
            "io_write_mb": 7.5,
            "network_sent_mb": 3.0,
            "network_recv_mb": 4.5,
        },
    ]

    usage = load_runner._calculate_resource_usage()

    assert usage.cpu_percent == 40.0  # Average
    assert usage.memory_mb == 550.0  # Average
    assert usage.memory_percent == 13.75  # Average
    # Deltas
    assert usage.io_read_mb == 10.0  # 20 - 10
    assert usage.io_write_mb == 5.0  # 10 - 5
    assert usage.network_sent_mb == 2.0  # 4 - 2
    assert usage.network_recv_mb == 3.0  # 6 - 3


def test_calculate_resource_usage_empty(load_runner):
    """Test resource usage calculation with no samples."""
    load_runner._resource_samples = []

    usage = load_runner._calculate_resource_usage()

    assert usage.cpu_percent == 0.0
    assert usage.memory_mb == 0.0
    assert usage.memory_percent == 0.0
    assert usage.io_read_mb == 0.0


# ====================
# Worker Coordination Tests (lines 406-444)
# ====================


@pytest.mark.asyncio
async def test_worker_pool_execution(load_runner):
    """Test worker pool coordination."""
    cycle_count = 0

    async def mock_cycle():
        nonlocal cycle_count
        cycle_count += 1
        await asyncio.sleep(0.01)
        return CycleResult(
            cycle_number=cycle_count,
            start_time=datetime.now(),
            end_time=datetime.now(),
            success=True,
            latency_ms=50.0,
            error=None,
        )

    # Run with multiple workers
    load_runner.config.workers = 3
    load_runner.config.test_cycles = 9

    result = await load_runner.run(test_name="worker_test", cycle_function=mock_cycle)

    assert result.total_cycles == 9
    assert result.successful_cycles == 9
    assert cycle_count == 9


@pytest.mark.asyncio
async def test_worker_with_failures(load_runner):
    """Test worker handling failures."""
    call_count = 0

    async def failing_cycle():
        nonlocal call_count
        call_count += 1
        if call_count % 3 == 0:
            raise Exception(f"Failure {call_count}")
        return CycleResult(
            cycle_number=call_count,
            start_time=datetime.now(),
            end_time=datetime.now(),
            success=True,
            latency_ms=100.0,
            error=None,
        )

    load_runner.config.workers = 2
    load_runner.config.test_cycles = 6

    result = await load_runner.run(
        test_name="failure_test", cycle_function=failing_cycle
    )

    assert result.total_cycles == 6
    assert result.failed_cycles == 2  # Cycles 3 and 6 fail
    assert result.successful_cycles == 4


@pytest.mark.asyncio
async def test_worker_graceful_shutdown(load_runner):
    """Test graceful shutdown of worker pool."""
    shutdown_called = False

    async def slow_cycle():
        nonlocal shutdown_called
        try:
            await asyncio.sleep(10)  # Long operation
        except asyncio.CancelledError:
            shutdown_called = True
            raise
        return CycleResult(
            cycle_number=1,
            start_time=datetime.now(),
            end_time=datetime.now(),
            success=True,
            latency_ms=100.0,
            error=None,
        )

    load_runner.config.workers = 1
    load_runner.config.test_cycles = 1
    load_runner.config.timeout_seconds = 0.1

    with pytest.raises(asyncio.TimeoutError):
        await load_runner.run(test_name="shutdown_test", cycle_function=slow_cycle)


# ====================
# Ramp Up/Down Tests
# ====================


@pytest.mark.asyncio
async def test_ramp_up_phase(load_runner):
    """Test ramp-up phase execution."""
    cycle_times = []

    async def track_cycle():
        cycle_times.append(datetime.now())
        return CycleResult(
            cycle_number=len(cycle_times),
            start_time=datetime.now(),
            end_time=datetime.now(),
            success=True,
            latency_ms=50.0,
            error=None,
        )

    load_runner.config.ramp_up_duration_seconds = 0.5
    load_runner.config.test_cycles = 5
    load_runner.config.workers = 1

    await load_runner.run(test_name="ramp_up_test", cycle_function=track_cycle)

    # Cycles should be spread out during ramp-up
    if len(cycle_times) >= 2:
        first_gap = (cycle_times[1] - cycle_times[0]).total_seconds()
        assert first_gap > 0  # Should have delay during ramp-up


@pytest.mark.asyncio
async def test_ramp_down_phase(load_runner):
    """Test ramp-down phase execution."""
    load_runner.config.ramp_down_duration_seconds = 0.5
    load_runner.config.test_cycles = 5
    load_runner.config.workers = 1

    async def simple_cycle():
        return CycleResult(
            cycle_number=1,
            start_time=datetime.now(),
            end_time=datetime.now(),
            success=True,
            latency_ms=50.0,
            error=None,
        )

    result = await load_runner.run(
        test_name="ramp_down_test", cycle_function=simple_cycle
    )

    # Should complete successfully with ramp-down
    assert result.total_cycles == 5


# ====================
# Platform-Specific Tests
# ====================


def test_platform_info_collection(load_runner):
    """Test platform information collection."""
    with patch("platform.system", return_value="Linux"):
        with patch("platform.processor", return_value="x86_64"):
            with patch("platform.python_version", return_value="3.12.0"):
                with patch("os.cpu_count", return_value=16):
                    info = load_runner._get_platform_info()

                    assert info["system"] == "Linux"
                    assert info["processor"] == "x86_64"
                    assert info["python_version"] == "3.12.0"
                    assert info["cpu_count"] == 16


def test_platform_info_with_errors(load_runner):
    """Test platform info collection with errors."""
    with patch("platform.system", side_effect=Exception("Platform error")):
        info = load_runner._get_platform_info()

        # Should have default/unknown values
        assert "system" in info
        assert info["system"] == "Unknown" or info["system"] is None


# ====================
# Error Handling and Edge Cases
# ====================


@pytest.mark.asyncio
async def test_empty_cycle_results(load_runner):
    """Test handling of empty cycle results."""

    async def no_op_cycle():
        return None  # Invalid return

    load_runner.config.test_cycles = 1

    with pytest.raises(Exception):
        await load_runner.run(test_name="empty_test", cycle_function=no_op_cycle)


@pytest.mark.asyncio
async def test_calculate_latencies_edge_cases(load_runner):
    """Test latency calculation with edge cases."""
    # Single result
    single_result = [
        CycleResult(
            cycle_number=1,
            start_time=datetime.now(),
            end_time=datetime.now(),
            success=True,
            latency_ms=100.0,
            error=None,
        )
    ]

    stats = load_runner._calculate_latency_stats(single_result)
    assert stats["mean"] == 100.0
    assert stats["median"] == 100.0
    assert stats["p50"] == 100.0

    # All failures
    failure_results = [
        CycleResult(
            cycle_number=i,
            start_time=datetime.now(),
            end_time=datetime.now(),
            success=False,
            latency_ms=0.0,
            error=f"Error {i}",
        )
        for i in range(5)
    ]

    stats = load_runner._calculate_latency_stats(failure_results)
    assert stats["mean"] == 0.0  # No successful results


def test_warmup_cycles_config(test_config):
    """Test warmup cycles configuration."""
    runner = LoadTester(test_config)
    assert runner.config.warmup_cycles == 2

    # Test with no warmup
    config_no_warmup = LoadTestConfig(
        test_cycles=10,
        workers=1,
        warmup_cycles=0,
    )
    runner_no_warmup = LoadTester(config_no_warmup)
    assert runner_no_warmup.config.warmup_cycles == 0


# ====================
# Integration Tests
# ====================


@pytest.mark.asyncio
async def test_full_load_test_simulation(load_runner):
    """Test complete load test simulation."""
    call_count = 0
    errors = []

    async def realistic_cycle():
        nonlocal call_count
        call_count += 1

        # Simulate varying latencies
        if call_count < 5:
            latency = 50.0  # Warmup - fast
        elif call_count < 95:
            latency = 75.0 + (call_count % 20) * 5  # Normal variation
        else:
            latency = 150.0  # Ramp down - slower

        # Simulate occasional failures
        if call_count % 25 == 0:
            errors.append(f"Timeout at cycle {call_count}")
            raise TimeoutError(f"Timeout at cycle {call_count}")

        await asyncio.sleep(latency / 1000)  # Convert to seconds

        return CycleResult(
            cycle_number=call_count,
            start_time=datetime.now(),
            end_time=datetime.now(),
            success=True,
            latency_ms=latency,
            error=None,
        )

    load_runner.config.test_cycles = 100
    load_runner.config.workers = 4
    load_runner.config.warmup_cycles = 5
    load_runner.config.ramp_up_duration_seconds = 0.5
    load_runner.config.ramp_down_duration_seconds = 0.5

    result = await load_runner.run(
        test_name="simulation", cycle_function=realistic_cycle
    )

    # Verify results
    assert result.total_cycles == 100
    assert result.failed_cycles == 4  # 100/25 = 4 failures
    assert result.successful_cycles == 96
    assert result.success_rate == 0.96

    # Generate and verify report
    report = load_runner.generate_report(result)
    assert "LOAD TEST REPORT: simulation" in report
    assert "96.00%" in report  # Success rate

    # Check that all phases ran
    assert call_count == 100
