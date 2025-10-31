"""
Final tests to achieve 80%+ coverage for Performance Benchmarks.

Targets remaining uncovered lines to reach 80% threshold.

Author: Validation Engineer (PRP Orchestrator coordinated)
Date: 2025-10-31
"""

import asyncio
import pytest
from unittest.mock import AsyncMock
from datetime import datetime
from workspace.shared.performance.benchmarks import (
    PerformanceBenchmark,
    BenchmarkConfig,
    BenchmarkMetrics,
    MemoryBenchmarkResult,
)


@pytest.fixture
def fast_config():
    """Fast configuration for quick tests."""
    return BenchmarkConfig(
        warmup_iterations=1,
        benchmark_iterations=3,
        db_query_samples=5,
        cache_samples=5,
        memory_baseline_operations=2,
        memory_test_operations=3,
        p50_target_ms=5.0,
        p95_target_ms=10.0,
        p99_target_ms=20.0,
    )


# Test async context manager for database queries
@pytest.mark.asyncio
async def test_database_query_async_context(fast_config):
    """Test database query execution with async context manager."""
    benchmark = PerformanceBenchmark(fast_config)

    mock_pool = AsyncMock()
    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[{"id": 1, "value": "test"}])

    # Setup async context manager
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock()

    metrics = await benchmark.benchmark_database_queries(mock_pool)

    assert metrics is not None
    assert metrics.benchmark_name == "database_queries"
    assert metrics.total_operations > 0


# Test cache operations with different patterns
@pytest.mark.asyncio
async def test_cache_operations_patterns(fast_config):
    """Test cache operations with various access patterns."""
    benchmark = PerformanceBenchmark(fast_config)

    mock_cache = AsyncMock()
    mock_cache.set = AsyncMock(return_value=True)
    mock_cache.get = AsyncMock(
        side_effect=lambda k: f"value_{k}" if hash(k) % 3 != 0 else None
    )
    mock_cache.delete = AsyncMock(return_value=True)

    metrics = await benchmark.benchmark_cache_operations(mock_cache)

    assert metrics is not None
    assert "cache_hit_rate" in metrics.metadata
    assert 0 <= metrics.metadata["cache_hit_rate"] <= 1


# Test memory benchmark with realistic operation
@pytest.mark.asyncio
async def test_memory_benchmark_realistic(fast_config):
    """Test memory benchmark with realistic memory allocation."""
    benchmark = PerformanceBenchmark(fast_config)

    data_store = []

    async def realistic_operation():
        # Simulate realistic memory usage
        temp_data = {"key": "value" * 100, "numbers": list(range(100))}
        data_store.append(temp_data)
        await asyncio.sleep(0.001)
        return len(data_store)

    result = await benchmark.benchmark_memory_usage("realistic", realistic_operation)

    assert isinstance(result, MemoryBenchmarkResult)
    assert result.baseline_memory_mb > 0
    assert result.memory_growth_mb >= 0


# Test percentile with unsorted data
def test_percentile_unsorted(fast_config):
    """Test percentile calculation handles unsorted data."""
    benchmark = PerformanceBenchmark(fast_config)

    # Unsorted data
    data = [10, 5, 15, 3, 20, 8, 12, 1, 18, 7]

    p50 = benchmark._percentile(data, 50)
    p90 = benchmark._percentile(data, 90)

    # Should sort internally
    assert 7 <= p50 <= 10  # Median should be around 8-9
    assert p90 >= 15  # 90th percentile should be high


# Test regression detection edge cases
def test_regression_detection_edge_cases(fast_config):
    """Test regression detection with edge cases."""
    benchmark = PerformanceBenchmark(fast_config)

    # No baseline - should not detect regression
    metrics = BenchmarkMetrics(
        benchmark_name="no_baseline",
        timestamp=datetime.now(),
        total_operations=100,
        successful_operations=100,
        failed_operations=0,
        duration_ms=1000,
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

    analysis = benchmark.detect_regression(metrics)
    assert not analysis.regression_detected
    assert analysis.baseline_p95_ms is None


# Test validate targets with all passing
def test_validate_targets_all_pass(fast_config):
    """Test validate_targets when all targets pass."""
    benchmark = PerformanceBenchmark(fast_config)

    metrics = BenchmarkMetrics(
        benchmark_name="all_pass",
        timestamp=datetime.now(),
        total_operations=100,
        successful_operations=100,
        failed_operations=0,
        duration_ms=1000,
        mean_latency_ms=2.0,
        median_latency_ms=2.0,
        p50_latency_ms=2.0,  # Under 5ms
        p95_latency_ms=4.0,  # Under 10ms
        p99_latency_ms=8.0,  # Under 20ms
        min_latency_ms=1.0,
        max_latency_ms=10.0,
        stddev_latency_ms=1.0,
        operations_per_second=100.0,
        meets_p50_target=True,
        meets_p95_target=True,
        meets_p99_target=True,
    )

    result = benchmark.validate_targets(metrics)
    assert result is True


# Test validate targets with mixed results
def test_validate_targets_mixed(fast_config):
    """Test validate_targets with some failures."""
    benchmark = PerformanceBenchmark(fast_config)

    metrics = BenchmarkMetrics(
        benchmark_name="mixed",
        timestamp=datetime.now(),
        total_operations=100,
        successful_operations=100,
        failed_operations=0,
        duration_ms=1000,
        mean_latency_ms=7.0,
        median_latency_ms=7.0,
        p50_latency_ms=7.0,  # Over 5ms (fail)
        p95_latency_ms=9.0,  # Under 10ms (pass)
        p99_latency_ms=15.0,  # Under 20ms (pass)
        min_latency_ms=3.0,
        max_latency_ms=20.0,
        stddev_latency_ms=2.0,
        operations_per_second=100.0,
        meets_p50_target=False,
        meets_p95_target=True,
        meets_p99_target=True,
    )

    result = benchmark.validate_targets(metrics)
    assert result is False  # Should fail if any target fails


# Test metrics calculation with various distributions
def test_calculate_metrics_distributions(fast_config):
    """Test metrics calculation with different latency distributions."""
    benchmark = PerformanceBenchmark(fast_config)

    # Uniform distribution
    uniform_latencies = [5.0] * 100
    metrics_uniform = benchmark._calculate_metrics("uniform", uniform_latencies, 500.0)
    assert metrics_uniform.stddev_latency_ms == 0.0
    assert metrics_uniform.mean_latency_ms == 5.0

    # Bimodal distribution (fast and slow responses)
    bimodal_latencies = [2.0] * 50 + [20.0] * 50
    metrics_bimodal = benchmark._calculate_metrics("bimodal", bimodal_latencies, 1100.0)
    assert metrics_bimodal.mean_latency_ms == 11.0
    assert metrics_bimodal.stddev_latency_ms > 5.0

    # Skewed distribution
    skewed_latencies = [1.0] * 80 + [10.0] * 15 + [100.0] * 5
    metrics_skewed = benchmark._calculate_metrics("skewed", skewed_latencies, 1000.0)
    assert metrics_skewed.p99_latency_ms > metrics_skewed.p95_latency_ms
    assert metrics_skewed.p95_latency_ms > metrics_skewed.median_latency_ms


# Test baseline save/load with different file paths
def test_baseline_file_operations(fast_config, tmp_path):
    """Test baseline save/load with various file scenarios."""
    benchmark = PerformanceBenchmark(fast_config)

    metrics = BenchmarkMetrics(
        benchmark_name="file_test",
        timestamp=datetime.now(),
        total_operations=100,
        successful_operations=100,
        failed_operations=0,
        duration_ms=1000,
        mean_latency_ms=5.0,
        median_latency_ms=5.0,
        p50_latency_ms=5.0,
        p95_latency_ms=8.0,
        p99_latency_ms=12.0,
        min_latency_ms=2.0,
        max_latency_ms=15.0,
        stddev_latency_ms=2.0,
        operations_per_second=100.0,
        meets_p50_target=True,
        meets_p95_target=True,
        meets_p99_target=True,
    )

    # Test saving to subdirectory
    subdir = tmp_path / "baselines"
    subdir.mkdir()
    filepath = subdir / "test_baseline.json"

    benchmark.save_baseline(metrics, str(filepath))
    assert filepath.exists()

    # Test loading
    loaded = benchmark.load_baseline(str(filepath))
    assert loaded is not None
    assert loaded.benchmark_name == "file_test"

    # Test loading non-existent file
    missing = benchmark.load_baseline(str(tmp_path / "missing.json"))
    assert missing is None


# Test regression analysis with improvements
def test_regression_analysis_improvement(fast_config):
    """Test regression analysis when performance improves."""
    benchmark = PerformanceBenchmark(fast_config)

    # Baseline (slower)
    baseline = BenchmarkMetrics(
        benchmark_name="improved",
        timestamp=datetime.now(),
        total_operations=100,
        successful_operations=100,
        failed_operations=0,
        duration_ms=1000,
        mean_latency_ms=20.0,
        median_latency_ms=20.0,
        p50_latency_ms=20.0,
        p95_latency_ms=30.0,
        p99_latency_ms=40.0,
        min_latency_ms=10.0,
        max_latency_ms=50.0,
        stddev_latency_ms=5.0,
        operations_per_second=50.0,
        meets_p50_target=False,
        meets_p95_target=False,
        meets_p99_target=False,
    )

    # Current (faster - improvement)
    current = BenchmarkMetrics(
        benchmark_name="improved",
        timestamp=datetime.now(),
        total_operations=100,
        successful_operations=100,
        failed_operations=0,
        duration_ms=500,
        mean_latency_ms=5.0,
        median_latency_ms=5.0,
        p50_latency_ms=5.0,
        p95_latency_ms=8.0,  # Much better than baseline
        p99_latency_ms=12.0,
        min_latency_ms=2.0,
        max_latency_ms=15.0,
        stddev_latency_ms=2.0,
        operations_per_second=200.0,
        meets_p50_target=True,
        meets_p95_target=True,
        meets_p99_target=True,
    )

    benchmark.baseline_results["improved"] = baseline
    analysis = benchmark.detect_regression(current)

    assert not analysis.regression_detected
    assert analysis.regression_percent < 0  # Negative means improvement


# Test concurrent benchmark operations
@pytest.mark.asyncio
async def test_concurrent_cache_operations(fast_config):
    """Test cache operations under concurrent load."""
    benchmark = PerformanceBenchmark(fast_config)

    mock_cache = AsyncMock()

    # Simulate concurrent access with delays
    async def delayed_set(key, value):
        await asyncio.sleep(0.001)
        return True

    async def delayed_get(key):
        await asyncio.sleep(0.001)
        return f"cached_{key}"

    mock_cache.set = delayed_set
    mock_cache.get = delayed_get
    mock_cache.delete = AsyncMock(return_value=True)

    metrics = await benchmark.benchmark_cache_operations(mock_cache)

    assert metrics is not None
    assert metrics.mean_latency_ms >= 1.0  # Should include delay


# Test error handling in batch operations
@pytest.mark.asyncio
async def test_batch_regression_detection(fast_config):
    """Test batch regression detection with multiple benchmarks."""
    benchmark = PerformanceBenchmark(fast_config)

    # Set up multiple baselines
    for i in range(3):
        baseline = BenchmarkMetrics(
            benchmark_name=f"test_{i}",
            timestamp=datetime.now(),
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
            stddev_latency_ms=1.5,
            operations_per_second=100.0,
            meets_p50_target=True,
            meets_p95_target=True,
            meets_p99_target=True,
        )
        benchmark.baseline_results[f"test_{i}"] = baseline

        # Add current results (some with regression)
        current = BenchmarkMetrics(
            benchmark_name=f"test_{i}",
            timestamp=datetime.now(),
            total_operations=100,
            successful_operations=100,
            failed_operations=0,
            duration_ms=1000,
            mean_latency_ms=5.0 + i * 2,  # Increasing latency
            median_latency_ms=5.0 + i * 2,
            p50_latency_ms=5.0 + i * 2,
            p95_latency_ms=7.0 + i * 3,  # Some will regress
            p99_latency_ms=10.0 + i * 4,
            min_latency_ms=3.0,
            max_latency_ms=15.0 + i * 5,
            stddev_latency_ms=2.0,
            operations_per_second=100.0 - i * 10,
            meets_p50_target=i < 1,
            meets_p95_target=i < 1,
            meets_p99_target=i < 2,
        )
        benchmark.benchmark_results[f"test_{i}"] = current

    regressions = await benchmark.detect_regressions()

    assert len(regressions) >= 2  # At least 2 should have regressions
    assert "test_0" in regressions
    assert not regressions["test_0"].regression_detected  # First should be fine
    assert regressions["test_2"].regression_detected  # Last should have regression
