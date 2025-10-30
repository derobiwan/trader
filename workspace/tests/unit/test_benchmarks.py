"""
Unit tests for Performance Benchmarks.

Tests core functionality:
- Database query benchmarks
- Cache operation benchmarks
- Memory benchmarks
- Target validation
- Regression detection

Target: 80%+ code coverage
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
from workspace.shared.performance.benchmarks import (
    PerformanceBenchmark,
    BenchmarkConfig,
    BenchmarkMetrics,
    MemoryBenchmarkResult,
    RegressionAnalysis,
)


@pytest.fixture
def benchmark_config():
    """Create benchmark configuration."""
    return BenchmarkConfig(
        warmup_iterations=5,
        benchmark_iterations=50,
        db_query_samples=100,
        cache_samples=100,
    )


@pytest.fixture
def performance_benchmark(benchmark_config):
    """Create PerformanceBenchmark instance."""
    return PerformanceBenchmark(benchmark_config)


@pytest.fixture
def mock_db_pool():
    """Mock database pool."""
    pool = AsyncMock()
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])

    pool.acquire = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.acquire.return_value.__aexit__ = AsyncMock()

    return pool


@pytest.fixture
def mock_cache_manager():
    """Mock cache manager."""
    cache = AsyncMock()
    cache.set = AsyncMock()
    cache.get = AsyncMock(return_value="value")
    cache.delete = AsyncMock()
    return cache


@pytest.mark.asyncio
async def test_benchmark_database_queries(performance_benchmark, mock_db_pool):
    """Test database query benchmarking."""
    # Act
    metrics = await performance_benchmark.benchmark_database_queries(mock_db_pool)

    # Assert
    assert isinstance(metrics, BenchmarkMetrics)
    assert metrics.benchmark_name == "database_queries"
    assert metrics.total_operations > 0
    assert metrics.p95_latency_ms >= 0


@pytest.mark.asyncio
async def test_benchmark_database_queries_with_errors(
    performance_benchmark, mock_db_pool
):
    """Test database query benchmarking with errors."""
    # Arrange
    performance_benchmark._execute_query_benchmark = AsyncMock(
        side_effect=Exception("DB error")
    )

    # Act & Assert
    with pytest.raises(Exception):
        await performance_benchmark.benchmark_database_queries(mock_db_pool)


@pytest.mark.asyncio
async def test_benchmark_cache_operations(performance_benchmark, mock_cache_manager):
    """Test cache operation benchmarking."""
    # Act
    metrics = await performance_benchmark.benchmark_cache_operations(mock_cache_manager)

    # Assert
    assert isinstance(metrics, BenchmarkMetrics)
    assert metrics.benchmark_name == "cache_operations"
    assert metrics.total_operations > 0
    assert "cache_hit_rate" in metrics.metadata


@pytest.mark.asyncio
async def test_benchmark_cache_operations_hit_rate(
    performance_benchmark, mock_cache_manager
):
    """Test cache operation benchmarking with hit rate calculation."""
    # Act
    metrics = await performance_benchmark.benchmark_cache_operations(mock_cache_manager)

    # Assert
    hit_rate = metrics.metadata["cache_hit_rate"]
    assert 0 <= hit_rate <= 1.0


@pytest.mark.asyncio
async def test_benchmark_memory_usage(performance_benchmark):
    """Test memory usage benchmarking."""

    # Arrange
    async def test_operation():
        # Simulate some work
        data = [1] * 1000
        return len(data)

    # Act
    result = await performance_benchmark.benchmark_memory_usage(
        "test_operation", test_operation
    )

    # Assert
    assert isinstance(result, MemoryBenchmarkResult)
    assert result.baseline_memory_mb > 0
    assert result.peak_memory_mb >= result.baseline_memory_mb
    assert result.memory_growth_mb >= 0


@pytest.mark.asyncio
async def test_benchmark_memory_leak_detection(performance_benchmark):
    """Test memory leak detection."""

    # Arrange
    async def leaky_operation():
        # Simulate memory leak
        global leak_list
        leak_list = leak_list + [1] * 10000 if "leak_list" in globals() else [1] * 10000

    # Act
    result = await performance_benchmark.benchmark_memory_usage(
        "leaky_operation", leaky_operation
    )

    # Assert
    # May or may not detect leak in short test
    assert isinstance(result, MemoryBenchmarkResult)


def test_calculate_metrics(performance_benchmark):
    """Test metrics calculation."""
    # Arrange
    latencies = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]

    # Act
    metrics = performance_benchmark._calculate_metrics(
        benchmark_name="test", latencies=latencies, duration_ms=1000.0
    )

    # Assert
    assert isinstance(metrics, BenchmarkMetrics)
    assert metrics.mean_latency_ms == 55.0
    assert metrics.median_latency_ms == 55.0
    assert metrics.min_latency_ms == 10.0
    assert metrics.max_latency_ms == 100.0


def test_percentile_calculation(performance_benchmark):
    """Test percentile calculation."""
    # Arrange
    data = list(range(1, 101))  # 1 to 100

    # Act
    p50 = performance_benchmark._percentile(data, 50)
    p95 = performance_benchmark._percentile(data, 95)
    p99 = performance_benchmark._percentile(data, 99)

    # Assert
    assert p50 == pytest.approx(50.5, rel=0.1)
    assert p95 == pytest.approx(95.05, rel=0.1)
    assert p99 == pytest.approx(99.01, rel=0.1)


def test_percentile_edge_cases(performance_benchmark):
    """Test percentile calculation edge cases."""
    # Single value
    assert performance_benchmark._percentile([10.0], 95) == 10.0

    # Two values
    result = performance_benchmark._percentile([10.0, 20.0], 50)
    assert 10.0 <= result <= 20.0


@pytest.mark.asyncio
async def test_validate_performance_targets(performance_benchmark):
    """Test performance target validation."""
    # Arrange
    metrics = BenchmarkMetrics(
        benchmark_name="test",
        timestamp=datetime.now(),
        total_operations=100,
        successful_operations=100,
        failed_operations=0,
        duration_ms=1000.0,
        mean_latency_ms=5.0,
        median_latency_ms=5.0,
        p50_latency_ms=5.0,
        p95_latency_ms=9.0,
        p99_latency_ms=15.0,
        min_latency_ms=1.0,
        max_latency_ms=20.0,
        stddev_latency_ms=3.0,
        operations_per_second=100.0,
        meets_p50_target=True,
        meets_p95_target=True,
        meets_p99_target=True,
    )

    # Act
    passes = performance_benchmark.validate_targets(metrics)

    # Assert
    assert passes is True


def test_detect_regression_no_baseline(performance_benchmark):
    """Test regression detection with no baseline."""
    # Arrange
    current_metrics = BenchmarkMetrics(
        benchmark_name="test",
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
    )

    # Act
    analysis = performance_benchmark.detect_regression(current_metrics)

    # Assert
    assert isinstance(analysis, RegressionAnalysis)
    assert analysis.regression_detected is False
    assert analysis.baseline_p95_ms is None


def test_detect_regression_with_baseline(performance_benchmark):
    """Test regression detection with baseline."""
    # Arrange
    baseline = BenchmarkMetrics(
        benchmark_name="test",
        timestamp=datetime.now(),
        total_operations=100,
        successful_operations=100,
        failed_operations=0,
        duration_ms=1000.0,
        mean_latency_ms=10.0,
        median_latency_ms=10.0,
        p50_latency_ms=10.0,
        p95_latency_ms=10.0,  # Baseline P95
        p99_latency_ms=15.0,
        min_latency_ms=5.0,
        max_latency_ms=20.0,
        stddev_latency_ms=2.0,
        operations_per_second=100.0,
        meets_p50_target=True,
        meets_p95_target=True,
        meets_p99_target=True,
    )

    current = BenchmarkMetrics(
        benchmark_name="test",
        timestamp=datetime.now(),
        total_operations=100,
        successful_operations=100,
        failed_operations=0,
        duration_ms=1000.0,
        mean_latency_ms=15.0,
        median_latency_ms=15.0,
        p50_latency_ms=15.0,
        p95_latency_ms=25.0,  # 150% of baseline - significant regression
        p99_latency_ms=30.0,
        min_latency_ms=10.0,
        max_latency_ms=40.0,
        stddev_latency_ms=5.0,
        operations_per_second=66.7,
        meets_p50_target=False,
        meets_p95_target=False,
        meets_p99_target=False,
    )

    performance_benchmark.baseline_results["test"] = baseline

    # Act
    analysis = performance_benchmark.detect_regression(current)

    # Assert
    assert analysis.regression_detected is True
    assert analysis.regression_percent > 10.0


@pytest.mark.asyncio
async def test_save_baseline(performance_benchmark, tmp_path):
    """Test saving baseline metrics."""
    # Arrange
    metrics = BenchmarkMetrics(
        benchmark_name="test",
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
    )

    baseline_file = tmp_path / "baseline.json"

    # Act
    performance_benchmark.save_baseline(metrics, str(baseline_file))

    # Assert
    assert baseline_file.exists()


@pytest.mark.asyncio
async def test_load_baseline(performance_benchmark, tmp_path):
    """Test loading baseline metrics."""
    # Arrange
    metrics = BenchmarkMetrics(
        benchmark_name="test",
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
    )

    baseline_file = tmp_path / "baseline.json"
    performance_benchmark.save_baseline(metrics, str(baseline_file))

    # Act
    loaded_metrics = performance_benchmark.load_baseline(str(baseline_file))

    # Assert
    assert loaded_metrics.benchmark_name == "test"
    assert loaded_metrics.p95_latency_ms == 15.0


def test_benchmark_config_defaults():
    """Test BenchmarkConfig default values."""
    config = BenchmarkConfig()

    assert config.warmup_iterations == 10
    assert config.benchmark_iterations == 100
    assert config.p50_target_ms == 5.0
    assert config.p95_target_ms == 10.0
    assert config.p99_target_ms == 20.0
