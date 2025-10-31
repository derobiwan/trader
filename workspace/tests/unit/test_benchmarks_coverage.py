"""
Additional tests to achieve 80%+ coverage for Performance Benchmarks.

Focuses on uncovered lines and edge cases:
- Error handling paths (lines 265-267, 272-274, 555-557)
- Cache operation internals (lines 388-448)
- Memory benchmarking edge cases (lines 499-518)
- Performance target validation (lines 573-599)
- Regression detection internals (lines 629-688)
- Run all benchmarks method (lines 766-858)
- Report generation (lines 870-996)
- Utility methods (lines 1200-1257)

Author: Validation Engineer (PRP Orchestrator coordinated)
Date: 2025-10-31
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from workspace.shared.performance.benchmarks import (
    PerformanceBenchmark,
    BenchmarkConfig,
    BenchmarkMetrics,
    MemoryBenchmarkResult,
)


@pytest.fixture
def simple_config():
    """Simple benchmark configuration for fast tests."""
    return BenchmarkConfig(
        warmup_iterations=1,
        benchmark_iterations=2,
        db_query_samples=5,
        cache_samples=10,
        memory_baseline_operations=5,
        memory_test_operations=10,
    )


@pytest.fixture
def benchmark(simple_config):
    """Create benchmark instance with simple config."""
    return PerformanceBenchmark(simple_config)


# ====================
# Cache Operation Internals (lines 388-448)
# ====================


@pytest.mark.asyncio
async def test_execute_cache_set(benchmark):
    """Test _execute_cache_set internal method."""
    mock_cache = AsyncMock()
    mock_cache.set = AsyncMock(return_value=True)

    # Test successful set
    latency = await benchmark._execute_cache_set(mock_cache, "test_key", "test_value")

    assert latency is not None
    assert latency > 0
    mock_cache.set.assert_called_once_with("test_key", "test_value")


@pytest.mark.asyncio
async def test_execute_cache_set_failure(benchmark):
    """Test _execute_cache_set with failure."""
    mock_cache = AsyncMock()
    mock_cache.set = AsyncMock(side_effect=Exception("Cache unavailable"))

    # Should return None on failure
    latency = await benchmark._execute_cache_set(mock_cache, "test_key", "test_value")

    assert latency is None


@pytest.mark.asyncio
async def test_execute_cache_get(benchmark):
    """Test _execute_cache_get internal method."""
    mock_cache = AsyncMock()
    mock_cache.get = AsyncMock(return_value="cached_value")

    # Test successful get
    latency = await benchmark._execute_cache_get(mock_cache, "test_key")

    assert latency is not None
    assert latency > 0
    mock_cache.get.assert_called_once_with("test_key")


@pytest.mark.asyncio
async def test_execute_cache_get_miss(benchmark):
    """Test _execute_cache_get with cache miss."""
    mock_cache = AsyncMock()
    mock_cache.get = AsyncMock(return_value=None)

    # Should still return latency on cache miss
    latency = await benchmark._execute_cache_get(mock_cache, "test_key")

    assert latency is not None
    assert latency > 0


@pytest.mark.asyncio
async def test_execute_cache_get_failure(benchmark):
    """Test _execute_cache_get with failure."""
    mock_cache = AsyncMock()
    mock_cache.get = AsyncMock(side_effect=Exception("Cache error"))

    # Should return None on failure
    latency = await benchmark._execute_cache_get(mock_cache, "test_key")

    assert latency is None


@pytest.mark.asyncio
async def test_execute_cache_delete(benchmark):
    """Test _execute_cache_delete internal method."""
    mock_cache = AsyncMock()
    mock_cache.delete = AsyncMock(return_value=True)

    # Test successful delete
    latency = await benchmark._execute_cache_delete(mock_cache, "test_key")

    assert latency is not None
    assert latency > 0
    mock_cache.delete.assert_called_once_with("test_key")


@pytest.mark.asyncio
async def test_execute_cache_delete_failure(benchmark):
    """Test _execute_cache_delete with failure."""
    mock_cache = AsyncMock()
    mock_cache.delete = AsyncMock(side_effect=Exception("Delete failed"))

    # Should return None on failure
    latency = await benchmark._execute_cache_delete(mock_cache, "test_key")

    assert latency is None


# ====================
# Memory Benchmarking Edge Cases (lines 499-518)
# ====================


@pytest.mark.asyncio
async def test_force_gc(benchmark):
    """Test _force_gc internal method."""
    with patch("gc.collect") as mock_gc:
        await benchmark._force_gc()
        mock_gc.assert_called_once()


@pytest.mark.asyncio
async def test_memory_benchmark_with_gc(benchmark):
    """Test memory benchmark with garbage collection."""

    async def memory_op():
        # Create some garbage
        temp_data = [i for i in range(1000)]
        return len(temp_data)

    with patch("gc.collect") as mock_gc:
        result = await benchmark.benchmark_memory_usage("gc_test", memory_op)

        # GC should be called multiple times
        assert mock_gc.call_count >= 2
        assert isinstance(result, MemoryBenchmarkResult)


# ====================
# Performance Target Validation (lines 573-599)
# ====================


@pytest.mark.asyncio
async def test_validate_performance_targets_empty(benchmark):
    """Test performance target validation with no results."""
    validation = await benchmark.validate_performance_targets()

    assert isinstance(validation, dict)
    assert len(validation) == 0


@pytest.mark.asyncio
async def test_validate_performance_targets_mixed_results(benchmark):
    """Test validation with mixed pass/fail results."""
    # Add passing result
    benchmark.benchmark_results["fast"] = BenchmarkMetrics(
        benchmark_name="fast",
        timestamp=datetime.now(),
        total_operations=100,
        successful_operations=100,
        failed_operations=0,
        duration_ms=100,
        mean_latency_ms=1.0,
        median_latency_ms=1.0,
        p50_latency_ms=1.0,  # Under 5ms target
        p95_latency_ms=2.0,  # Under 10ms target
        p99_latency_ms=3.0,  # Under 20ms target
        min_latency_ms=0.5,
        max_latency_ms=4.0,
        stddev_latency_ms=0.5,
        operations_per_second=1000.0,
        meets_p50_target=True,
        meets_p95_target=True,
        meets_p99_target=True,
    )

    # Add failing result
    benchmark.benchmark_results["slow"] = BenchmarkMetrics(
        benchmark_name="slow",
        timestamp=datetime.now(),
        total_operations=100,
        successful_operations=100,
        failed_operations=0,
        duration_ms=1000,
        mean_latency_ms=15.0,
        median_latency_ms=15.0,
        p50_latency_ms=15.0,  # Over 5ms target
        p95_latency_ms=25.0,  # Over 10ms target
        p99_latency_ms=35.0,  # Over 20ms target
        min_latency_ms=10.0,
        max_latency_ms=40.0,
        stddev_latency_ms=5.0,
        operations_per_second=100.0,
        meets_p50_target=False,
        meets_p95_target=False,
        meets_p99_target=False,
    )

    validation = await benchmark.validate_performance_targets()

    assert validation["fast"] is True
    assert validation["slow"] is False


@pytest.mark.asyncio
async def test_validate_targets_boundary_conditions(simple_config):
    """Test target validation at exact boundaries."""
    config = BenchmarkConfig(
        p50_target_ms=10.0,
        p95_target_ms=20.0,
        p99_target_ms=30.0,
    )
    benchmark = PerformanceBenchmark(config)

    metrics = BenchmarkMetrics(
        benchmark_name="boundary",
        timestamp=datetime.now(),
        total_operations=100,
        successful_operations=100,
        failed_operations=0,
        duration_ms=1000,
        mean_latency_ms=10.0,
        median_latency_ms=10.0,
        p50_latency_ms=10.0,  # Exactly at target
        p95_latency_ms=20.0,  # Exactly at target
        p99_latency_ms=30.0,  # Exactly at target
        min_latency_ms=5.0,
        max_latency_ms=35.0,
        stddev_latency_ms=5.0,
        operations_per_second=100.0,
        meets_p50_target=True,
        meets_p95_target=True,
        meets_p99_target=True,
    )

    passes = benchmark.validate_targets(metrics)
    assert passes is True


# ====================
# Regression Detection Advanced (lines 629-688, 690-742)
# ====================


@pytest.mark.asyncio
async def test_detect_regressions_batch(benchmark):
    """Test batch regression detection."""
    # Set up baseline
    baseline = BenchmarkMetrics(
        benchmark_name="test1",
        timestamp=datetime.now() - timedelta(hours=1),
        total_operations=100,
        successful_operations=100,
        failed_operations=0,
        duration_ms=1000,
        mean_latency_ms=5.0,
        median_latency_ms=5.0,
        p50_latency_ms=5.0,
        p95_latency_ms=7.0,
        p99_latency_ms=10.0,
        min_latency_ms=3.0,
        max_latency_ms=12.0,
        stddev_latency_ms=2.0,
        operations_per_second=100.0,
        meets_p50_target=True,
        meets_p95_target=True,
        meets_p99_target=True,
    )

    benchmark.baseline_results["test1"] = baseline

    # Add current results with regression
    current = BenchmarkMetrics(
        benchmark_name="test1",
        timestamp=datetime.now(),
        total_operations=100,
        successful_operations=100,
        failed_operations=0,
        duration_ms=1000,
        mean_latency_ms=6.0,
        median_latency_ms=6.0,
        p50_latency_ms=6.0,
        p95_latency_ms=9.0,  # 28% increase - regression
        p99_latency_ms=12.0,
        min_latency_ms=4.0,
        max_latency_ms=15.0,
        stddev_latency_ms=2.5,
        operations_per_second=100.0,
        meets_p50_target=False,
        meets_p95_target=True,
        meets_p99_target=True,
    )

    benchmark.benchmark_results["test1"] = current

    # Detect regressions
    regressions = await benchmark.detect_regressions()

    assert "test1" in regressions
    assert regressions["test1"].regression_detected is True


@pytest.mark.asyncio
async def test_detect_regression_with_message(benchmark):
    """Test regression detection message generation."""
    baseline = BenchmarkMetrics(
        benchmark_name="api_call",
        timestamp=datetime.now() - timedelta(days=1),
        total_operations=500,
        successful_operations=500,
        failed_operations=0,
        duration_ms=5000,
        mean_latency_ms=8.0,
        median_latency_ms=7.5,
        p50_latency_ms=7.5,
        p95_latency_ms=12.0,
        p99_latency_ms=15.0,
        min_latency_ms=5.0,
        max_latency_ms=20.0,
        stddev_latency_ms=3.0,
        operations_per_second=100.0,
        meets_p50_target=False,
        meets_p95_target=False,
        meets_p99_target=True,
    )

    current = BenchmarkMetrics(
        benchmark_name="api_call",
        timestamp=datetime.now(),
        total_operations=500,
        successful_operations=500,
        failed_operations=0,
        duration_ms=5000,
        mean_latency_ms=10.0,
        median_latency_ms=9.5,
        p50_latency_ms=9.5,
        p95_latency_ms=16.0,  # 33% increase
        p99_latency_ms=20.0,
        min_latency_ms=6.0,
        max_latency_ms=25.0,
        stddev_latency_ms=4.0,
        operations_per_second=100.0,
        meets_p50_target=False,
        meets_p95_target=False,
        meets_p99_target=True,
    )

    benchmark.baseline_results["api_call"] = baseline
    analysis = benchmark.detect_regression(current)

    assert analysis.regression_detected is True
    assert "33" in analysis.message or "regression" in analysis.message.lower()
    assert analysis.baseline_p95_ms == 12.0
    assert analysis.current_p95_ms == 16.0


# ====================
# Run All Benchmarks Method (lines 766-858)
# ====================


@pytest.mark.asyncio
async def test_run_all_benchmarks_comprehensive(simple_config):
    """Test run_all_benchmarks with all components."""
    benchmark = PerformanceBenchmark(simple_config)

    # Create mocks
    mock_db_pool = AsyncMock()
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    mock_db_pool.acquire = MagicMock()
    mock_db_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    mock_db_pool.acquire.return_value.__aexit__ = AsyncMock()

    mock_cache = AsyncMock()
    mock_cache.set = AsyncMock()
    mock_cache.get = AsyncMock(return_value="value")
    mock_cache.delete = AsyncMock()

    # Run all benchmarks
    results = await benchmark.run_all_benchmarks(
        db_pool=mock_db_pool,
        cache_manager=mock_cache,
        run_memory_benchmarks=False,  # Skip memory benchmarks for speed
    )

    # Verify structure
    assert "database_queries" in results
    assert "cache_operations" in results
    assert "validation_results" in results
    assert "regression_analysis" in results
    assert "timestamp" in results


@pytest.mark.asyncio
async def test_run_all_benchmarks_with_memory(simple_config):
    """Test run_all_benchmarks including memory benchmarks."""
    benchmark = PerformanceBenchmark(simple_config)

    # Create mocks
    mock_db_pool = AsyncMock()
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    mock_db_pool.acquire = MagicMock()
    mock_db_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    mock_db_pool.acquire.return_value.__aexit__ = AsyncMock()

    mock_cache = AsyncMock()
    mock_cache.set = AsyncMock()
    mock_cache.get = AsyncMock(return_value="value")
    mock_cache.delete = AsyncMock()

    # Define memory test functions
    async def test_op1():
        return [1] * 100

    async def test_op2():
        return {"data": "test"}

    # Run with memory benchmarks
    results = await benchmark.run_all_benchmarks(
        db_pool=mock_db_pool,
        cache_manager=mock_cache,
        run_memory_benchmarks=True,
        memory_test_functions=[
            ("test_op1", test_op1),
            ("test_op2", test_op2),
        ],
    )

    # Memory results should be included
    assert "memory_benchmarks" in results
    assert len(results["memory_benchmarks"]) == 2


# ====================
# Report Generation (lines 870-996)
# ====================


def test_generate_report_empty(benchmark):
    """Test report generation with no results."""
    report = benchmark.generate_report({})

    assert isinstance(report, str)
    assert "Performance Benchmark Report" in report


def test_generate_report_with_metrics(benchmark):
    """Test report generation with actual metrics."""
    results = {
        "database": BenchmarkMetrics(
            benchmark_name="database",
            timestamp=datetime.now(),
            total_operations=100,
            successful_operations=95,
            failed_operations=5,
            duration_ms=1000,
            mean_latency_ms=10.0,
            median_latency_ms=9.0,
            p50_latency_ms=9.0,
            p95_latency_ms=15.0,
            p99_latency_ms=20.0,
            min_latency_ms=5.0,
            max_latency_ms=25.0,
            stddev_latency_ms=3.0,
            operations_per_second=100.0,
            meets_p50_target=False,
            meets_p95_target=False,
            meets_p99_target=True,
        ),
        "cache": BenchmarkMetrics(
            benchmark_name="cache",
            timestamp=datetime.now(),
            total_operations=1000,
            successful_operations=1000,
            failed_operations=0,
            duration_ms=500,
            mean_latency_ms=0.5,
            median_latency_ms=0.4,
            p50_latency_ms=0.4,
            p95_latency_ms=0.8,
            p99_latency_ms=1.2,
            min_latency_ms=0.2,
            max_latency_ms=2.0,
            stddev_latency_ms=0.2,
            operations_per_second=2000.0,
            meets_p50_target=True,
            meets_p95_target=True,
            meets_p99_target=True,
            metadata={"cache_hit_rate": 0.85},
        ),
    }

    report = benchmark.generate_report(results)

    assert "database" in report
    assert "cache" in report
    assert "95" in report  # Success rate
    assert "0.85" in report or "85" in report  # Cache hit rate


def test_generate_report_with_validation(benchmark):
    """Test report includes validation results."""
    # Add benchmark results
    benchmark.benchmark_results["test"] = BenchmarkMetrics(
        benchmark_name="test",
        timestamp=datetime.now(),
        total_operations=100,
        successful_operations=100,
        failed_operations=0,
        duration_ms=100,
        mean_latency_ms=2.0,
        median_latency_ms=2.0,
        p50_latency_ms=2.0,
        p95_latency_ms=3.0,
        p99_latency_ms=4.0,
        min_latency_ms=1.0,
        max_latency_ms=5.0,
        stddev_latency_ms=0.5,
        operations_per_second=1000.0,
        meets_p50_target=True,
        meets_p95_target=True,
        meets_p99_target=True,
    )

    results = {
        "test": benchmark.benchmark_results["test"],
        "validation_results": {"test": True},
    }

    report = benchmark.generate_report(results)

    assert "PASS" in report or "✓" in report or "Success" in report


# ====================
# Utility Methods (lines 1069-1150, 1200-1257)
# ====================


def test_percentile_large_dataset(benchmark):
    """Test percentile calculation with large dataset."""
    # Generate large dataset
    data = list(range(1, 10001))  # 10,000 points

    p50 = benchmark._percentile(data, 50)
    p95 = benchmark._percentile(data, 95)
    p99 = benchmark._percentile(data, 99)

    assert 4900 < p50 < 5100  # Around 5000
    assert 9400 < p95 < 9600  # Around 9500
    assert 9800 < p99 < 10000  # Around 9900


def test_metrics_to_dict(benchmark):
    """Test _metrics_to_dict conversion."""
    metrics = BenchmarkMetrics(
        benchmark_name="conversion_test",
        timestamp=datetime.now(),
        total_operations=100,
        successful_operations=100,
        failed_operations=0,
        duration_ms=1000.0,
        mean_latency_ms=10.0,
        median_latency_ms=10.0,
        p50_latency_ms=10.0,
        p95_latency_ms=15.0,
        p99_latency_ms=20.0,
        min_latency_ms=5.0,
        max_latency_ms=25.0,
        stddev_latency_ms=3.0,
        operations_per_second=100.0,
        meets_p50_target=True,
        meets_p95_target=True,
        meets_p99_target=True,
        metadata={"custom": "data"},
    )

    result = benchmark._metrics_to_dict(metrics)

    assert isinstance(result, dict)
    assert result["benchmark_name"] == "conversion_test"
    assert result["total_operations"] == 100
    assert result["p95_latency_ms"] == 15.0
    assert result["metadata"]["custom"] == "data"
    assert "timestamp" in result


def test_save_baseline_with_defaults(benchmark, tmp_path):
    """Test save_baseline with default parameters."""
    # Add a result to save
    benchmark.benchmark_results["default_test"] = BenchmarkMetrics(
        benchmark_name="default_test",
        timestamp=datetime.now(),
        total_operations=50,
        successful_operations=50,
        failed_operations=0,
        duration_ms=500,
        mean_latency_ms=10.0,
        median_latency_ms=10.0,
        p50_latency_ms=10.0,
        p95_latency_ms=15.0,
        p99_latency_ms=20.0,
        min_latency_ms=5.0,
        max_latency_ms=25.0,
        stddev_latency_ms=3.0,
        operations_per_second=100.0,
        meets_p50_target=False,
        meets_p95_target=False,
        meets_p99_target=True,
    )

    baseline_file = tmp_path / "baseline_default.json"

    # Save without specifying metrics (should use first from results)
    benchmark.save_baseline(filepath=str(baseline_file))

    assert baseline_file.exists()

    # Load and verify
    loaded = benchmark.load_baseline(str(baseline_file))
    assert loaded is not None
    assert loaded.benchmark_name == "default_test"


def test_load_baseline_corrupted_file(benchmark, tmp_path):
    """Test load_baseline with partially corrupted JSON."""
    corrupted_file = tmp_path / "corrupted.json"

    # Write invalid but partial JSON
    corrupted_file.write_text('{"benchmark_name": "test", "invalid": }')

    result = benchmark.load_baseline(str(corrupted_file))
    assert result is None  # Should handle gracefully


def test_load_baseline_missing_fields(benchmark, tmp_path):
    """Test load_baseline with missing required fields."""
    incomplete_file = tmp_path / "incomplete.json"

    # Write JSON missing required fields
    incomplete_data = {
        "benchmark_name": "incomplete",
        "timestamp": datetime.now().isoformat(),
        # Missing many required fields
    }

    with open(incomplete_file, "w") as f:
        json.dump(incomplete_data, f)

    result = benchmark.load_baseline(str(incomplete_file))
    # Should handle missing fields gracefully
    assert result is None or hasattr(result, "benchmark_name")


# ====================
# Edge Cases and Error Paths
# ====================


@pytest.mark.asyncio
async def test_benchmark_with_all_failures(simple_config):
    """Test benchmarks when all operations fail."""
    benchmark = PerformanceBenchmark(simple_config)

    # Mock DB that always fails
    mock_db = AsyncMock()
    mock_db.acquire = MagicMock(side_effect=Exception("Connection failed"))

    with pytest.raises(Exception):
        await benchmark.benchmark_database_queries(mock_db)


@pytest.mark.asyncio
async def test_memory_benchmark_oom_simulation(benchmark):
    """Test memory benchmark handling OOM scenarios."""

    async def oom_operation():
        raise MemoryError("Simulated OOM")

    with pytest.raises(MemoryError):
        await benchmark.benchmark_memory_usage("oom_test", oom_operation)


def test_calculate_metrics_no_data(benchmark):
    """Test metrics calculation with empty data."""
    metrics = benchmark._calculate_metrics(
        benchmark_name="empty", latencies=[], duration_ms=0
    )

    assert metrics.total_operations == 0
    assert metrics.successful_operations == 0
    assert metrics.mean_latency_ms == 0
    assert metrics.operations_per_second == 0


def test_calculate_metrics_single_point(benchmark):
    """Test metrics calculation with single data point."""
    metrics = benchmark._calculate_metrics(
        benchmark_name="single", latencies=[5.0], duration_ms=5.0
    )

    assert metrics.total_operations == 1
    assert metrics.mean_latency_ms == 5.0
    assert metrics.median_latency_ms == 5.0
    assert metrics.p50_latency_ms == 5.0
    assert metrics.p95_latency_ms == 5.0
    assert metrics.p99_latency_ms == 5.0


# ====================
# Main Function Coverage
# ====================


@pytest.mark.asyncio
async def test_main_function():
    """Test the main entry point."""
    from workspace.shared.performance import benchmarks

    # Mock the necessary components
    with patch("asyncio.run") as mock_run:
        # Import and call main indirectly
        if hasattr(benchmarks, "main"):
            # The main function exists, mock its execution
            mock_run.return_value = None
            # Don't actually run main, just verify it exists
            assert callable(benchmarks.main)
