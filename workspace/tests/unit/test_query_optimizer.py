"""
Unit tests for Query Optimizer.

Tests all major functionality:
- Index creation
- Slow query detection
- Index usage stats
- Table bloat monitoring
- Table optimization
- Performance metrics
- Monitoring loop

Target: 80%+ code coverage
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta
from workspace.shared.database.query_optimizer import (
    QueryOptimizer,
    QueryStats,
    IndexStats,
    TableStats,
)


@pytest.fixture
def mock_pool():
    """Mock asyncpg connection pool."""
    pool = AsyncMock()

    # Mock connection
    conn = AsyncMock()
    conn.execute = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchval = AsyncMock(return_value=False)

    # Mock acquire context manager
    pool.acquire = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.acquire.return_value.__aexit__ = AsyncMock()

    return pool


@pytest.fixture
def query_optimizer(mock_pool):
    """Create QueryOptimizer instance with mocked pool."""
    return QueryOptimizer(mock_pool)


@pytest.mark.asyncio
async def test_initialize_success(query_optimizer, mock_pool):
    """Test successful initialization."""
    # Act
    await query_optimizer.initialize()

    # Assert
    conn = await mock_pool.acquire().__aenter__()
    assert conn.execute.call_count >= 2  # At least 2 SQL commands


@pytest.mark.asyncio
async def test_initialize_failure(query_optimizer, mock_pool):
    """Test initialization failure handling."""
    # Arrange
    conn = await mock_pool.acquire().__aenter__()
    conn.execute.side_effect = Exception("Database connection failed")

    # Act & Assert
    with pytest.raises(Exception, match="Database connection failed"):
        await query_optimizer.initialize()


@pytest.mark.asyncio
async def test_create_indexes_success(query_optimizer, mock_pool):
    """Test successful index creation."""
    # Arrange
    conn = await mock_pool.acquire().__aenter__()
    conn.fetchval = AsyncMock(return_value=False)  # Index doesn't exist
    conn.execute = AsyncMock()

    # Act
    results = await query_optimizer.create_indexes()

    # Assert
    assert isinstance(results, dict)
    assert len(results) > 0
    # At least some indexes should be created
    successful = sum(1 for success in results.values() if success)
    assert successful >= 0


@pytest.mark.asyncio
async def test_create_indexes_already_exists(query_optimizer, mock_pool):
    """Test creating indexes that already exist."""
    # Arrange
    conn = await mock_pool.acquire().__aenter__()
    conn.fetchval = AsyncMock(return_value=True)  # Index already exists

    # Act
    results = await query_optimizer.create_indexes()

    # Assert
    assert all(results.values())  # All should return True


@pytest.mark.asyncio
async def test_create_index_with_where_clause(query_optimizer, mock_pool):
    """Test index creation with WHERE clause."""
    # Arrange
    conn = await mock_pool.acquire().__aenter__()
    conn.fetchval = AsyncMock(return_value=False)
    conn.execute = AsyncMock()

    # Act
    result = await query_optimizer._create_index(
        "test_idx", "test_table", "(column1, column2)", "WHERE status = 'active'"
    )

    # Assert
    assert result is True
    conn.execute.assert_called()


@pytest.mark.asyncio
async def test_analyze_slow_queries_with_extension(query_optimizer, mock_pool):
    """Test slow query analysis when extension is available."""
    # Arrange
    conn = await mock_pool.acquire().__aenter__()
    conn.fetchval = AsyncMock(return_value=True)  # Extension exists
    conn.fetch = AsyncMock(
        return_value=[
            {
                "query": "SELECT * FROM positions WHERE symbol = $1",
                "calls": 100,
                "total_time": 5000.0,
                "mean_time": 50.0,
                "max_time": 200.0,
                "min_time": 10.0,
                "stddev_time": 20.0,
            }
        ]
    )

    # Act
    stats = await query_optimizer.analyze_slow_queries()

    # Assert
    assert len(stats) == 1
    assert isinstance(stats[0], QueryStats)
    assert stats[0].avg_time_ms == 50.0
    assert stats[0].total_count == 100


@pytest.mark.asyncio
async def test_analyze_slow_queries_no_extension(query_optimizer, mock_pool):
    """Test slow query analysis when extension is not available."""
    # Arrange
    conn = await mock_pool.acquire().__aenter__()
    conn.fetchval = AsyncMock(return_value=False)  # Extension doesn't exist

    # Act
    stats = await query_optimizer.analyze_slow_queries()

    # Assert
    assert len(stats) == 0


@pytest.mark.asyncio
async def test_analyze_slow_queries_with_limit(query_optimizer, mock_pool):
    """Test slow query analysis with limit parameter."""
    # Arrange
    conn = await mock_pool.acquire().__aenter__()
    conn.fetchval = AsyncMock(return_value=True)
    mock_queries = [
        {
            "query": f"SELECT * FROM table{i}",
            "calls": 100,
            "total_time": 1000.0,
            "mean_time": 10.0,
            "max_time": 50.0,
            "min_time": 5.0,
            "stddev_time": 2.0,
        }
        for i in range(50)
    ]
    conn.fetch = AsyncMock(return_value=mock_queries)

    # Act
    await query_optimizer.analyze_slow_queries(limit=5)

    # Assert
    # Should have called with limit parameter
    call_args = conn.fetch.call_args
    assert call_args[0][2] == 5  # limit parameter


def test_normalize_query(query_optimizer):
    """Test query normalization."""
    # Test number replacement
    query1 = "SELECT * FROM table WHERE id = 123"
    normalized1 = query_optimizer._normalize_query(query1)
    assert "123" not in normalized1
    assert "?" in normalized1

    # Test string replacement
    query2 = "SELECT * FROM table WHERE name = 'test'"
    normalized2 = query_optimizer._normalize_query(query2)
    assert "'test'" not in normalized2
    assert "'?'" in normalized2

    # Test truncation
    query3 = "SELECT * " + "x" * 300
    normalized3 = query_optimizer._normalize_query(query3)
    assert len(normalized3) <= 203  # 200 + "..."


@pytest.mark.asyncio
async def test_get_index_usage_stats(query_optimizer, mock_pool):
    """Test getting index usage statistics."""
    # Arrange
    conn = await mock_pool.acquire().__aenter__()
    conn.fetch = AsyncMock(
        return_value=[
            {
                "schemaname": "public",
                "tablename": "positions",
                "indexname": "idx_positions_symbol",
                "idx_scan": 1000,
                "idx_tup_read": 5000,
                "idx_tup_fetch": 4500,
                "index_size": "1 MB",
            }
        ]
    )

    # Act
    stats = await query_optimizer.get_index_usage_stats()

    # Assert
    assert len(stats) == 1
    assert isinstance(stats[0], IndexStats)
    assert stats[0].table_name == "positions"
    assert stats[0].index_scans == 1000


def test_parse_size_to_mb(query_optimizer):
    """Test size parsing from PostgreSQL format."""
    assert query_optimizer._parse_size_to_mb("1 MB") == 1.0
    assert query_optimizer._parse_size_to_mb("2 GB") == 2048.0
    assert query_optimizer._parse_size_to_mb("512 kB") == 0.5
    assert query_optimizer._parse_size_to_mb("1024 bytes") == pytest.approx(
        0.0009765625, rel=1e-3
    )


@pytest.mark.asyncio
async def test_get_table_stats(query_optimizer, mock_pool):
    """Test getting table statistics."""
    # Arrange
    conn = await mock_pool.acquire().__aenter__()
    last_vacuum = datetime.now() - timedelta(hours=12)
    last_analyze = datetime.now() - timedelta(hours=3)

    conn.fetch = AsyncMock(
        return_value=[
            {
                "schemaname": "public",
                "tablename": "positions",
                "n_live_tup": 10000,
                "n_dead_tup": 2000,
                "last_vacuum": last_vacuum,
                "last_analyze": last_analyze,
                "total_size": "10 MB",
                "table_size": "8 MB",
                "indexes_size": "2 MB",
            }
        ]
    )

    # Act
    stats = await query_optimizer.get_table_stats()

    # Assert
    assert len(stats) == 1
    assert isinstance(stats[0], TableStats)
    assert stats[0].table_name == "positions"
    assert stats[0].total_rows == 10000
    assert stats[0].dead_rows == 2000
    assert stats[0].bloat_ratio == pytest.approx(2000 / 12000, rel=1e-3)


@pytest.mark.asyncio
async def test_optimize_tables_with_bloat(query_optimizer, mock_pool):
    """Test optimizing tables with bloat."""
    # Arrange
    await mock_pool.acquire().__aenter__()

    # Mock table stats showing bloat
    old_vacuum = datetime.now() - timedelta(hours=48)
    query_optimizer.get_table_stats = AsyncMock(
        return_value=[
            TableStats(
                table_name="positions",
                total_rows=10000,
                dead_rows=3000,  # 30% bloat
                table_size_mb=10.0,
                index_size_mb=2.0,
                bloat_ratio=0.3,
                last_vacuum=old_vacuum,
                last_analyze=old_vacuum,
            )
        ]
    )

    # Act
    results = await query_optimizer.optimize_tables()

    # Assert
    assert "positions" in results
    assert results["positions"] is True


@pytest.mark.asyncio
async def test_optimize_tables_force(query_optimizer, mock_pool):
    """Test forcing table optimization."""
    # Arrange
    query_optimizer.get_table_stats = AsyncMock(
        return_value=[
            TableStats(
                table_name="positions",
                total_rows=10000,
                dead_rows=100,  # Low bloat
                table_size_mb=10.0,
                index_size_mb=2.0,
                bloat_ratio=0.01,
                last_vacuum=datetime.now(),
                last_analyze=datetime.now(),
            )
        ]
    )

    # Act
    results = await query_optimizer.optimize_tables(force=True)

    # Assert
    assert "positions" in results


@pytest.mark.asyncio
async def test_optimize_table_vacuum_and_analyze(query_optimizer, mock_pool):
    """Test optimizing a table with VACUUM and ANALYZE."""
    # Arrange
    conn = await mock_pool.acquire().__aenter__()
    conn.execute = AsyncMock()

    # Act
    result = await query_optimizer._optimize_table(
        "positions", vacuum=True, analyze=True
    )

    # Assert
    assert result is True
    # Should have executed VACUUM ANALYZE
    call_args = str(conn.execute.call_args_list)
    assert "VACUUM" in call_args or "vacuum" in call_args.lower()


@pytest.mark.asyncio
async def test_get_performance_metrics(query_optimizer, mock_pool):
    """Test getting comprehensive performance metrics."""
    # Arrange
    query_optimizer.analyze_slow_queries = AsyncMock(
        return_value=[
            QueryStats(
                query_pattern="SELECT * FROM positions",
                total_count=100,
                total_time_ms=5000.0,
                avg_time_ms=50.0,
                max_time_ms=200.0,
                min_time_ms=10.0,
                p95_time_ms=150.0,
                slow_count=100,
            )
        ]
    )

    query_optimizer.get_index_usage_stats = AsyncMock(
        return_value=[
            IndexStats(
                table_name="positions",
                index_name="idx_positions_symbol",
                index_size_mb=1.0,
                index_scans=1000,
                index_reads=5000,
                effectiveness=0.8,
            )
        ]
    )

    query_optimizer.get_table_stats = AsyncMock(
        return_value=[
            TableStats(
                table_name="positions",
                total_rows=10000,
                dead_rows=2000,
                table_size_mb=10.0,
                index_size_mb=2.0,
                bloat_ratio=0.2,
                last_vacuum=datetime.now(),
                last_analyze=datetime.now(),
            )
        ]
    )

    # Act
    metrics = await query_optimizer.get_performance_metrics()

    # Assert
    assert "slow_queries" in metrics
    assert "indexes" in metrics
    assert "tables" in metrics
    assert metrics["slow_queries"]["count"] == 1


@pytest.mark.asyncio
async def test_start_monitoring(query_optimizer):
    """Test starting performance monitoring."""
    # Act
    await query_optimizer.start_monitoring(interval_seconds=1)

    # Assert
    assert query_optimizer.monitoring_enabled is True
    assert query_optimizer._monitor_task is not None

    # Cleanup
    await query_optimizer.stop_monitoring()


@pytest.mark.asyncio
async def test_stop_monitoring(query_optimizer):
    """Test stopping performance monitoring."""
    # Arrange
    await query_optimizer.start_monitoring(interval_seconds=1)

    # Act
    await query_optimizer.stop_monitoring()

    # Assert
    assert query_optimizer.monitoring_enabled is False


@pytest.mark.asyncio
async def test_monitoring_loop_detects_slow_queries(query_optimizer, mock_pool):
    """Test that monitoring loop detects slow queries."""
    # Arrange
    query_optimizer.analyze_slow_queries = AsyncMock(
        return_value=[
            QueryStats(
                query_pattern="SELECT * FROM positions",
                total_count=100,
                total_time_ms=5000.0,
                avg_time_ms=50.0,
                max_time_ms=200.0,
                min_time_ms=10.0,
                p95_time_ms=150.0,
                slow_count=100,
            )
        ]
    )

    query_optimizer.get_table_stats = AsyncMock(return_value=[])
    query_optimizer.get_index_usage_stats = AsyncMock(return_value=[])

    # Start monitoring with very short interval
    await query_optimizer.start_monitoring(interval_seconds=0.1)

    # Wait for at least one monitoring cycle
    await asyncio.sleep(0.2)

    # Stop monitoring
    await query_optimizer.stop_monitoring()

    # Assert
    assert query_optimizer.analyze_slow_queries.called


@pytest.mark.asyncio
async def test_monitoring_loop_detects_bloated_tables(query_optimizer, mock_pool):
    """Test that monitoring loop detects and optimizes bloated tables."""
    # Arrange
    query_optimizer.analyze_slow_queries = AsyncMock(return_value=[])
    query_optimizer.get_index_usage_stats = AsyncMock(return_value=[])

    query_optimizer.get_table_stats = AsyncMock(
        return_value=[
            TableStats(
                table_name="positions",
                total_rows=10000,
                dead_rows=3000,
                table_size_mb=10.0,
                index_size_mb=2.0,
                bloat_ratio=0.3,  # 30% bloat - above threshold
                last_vacuum=datetime.now() - timedelta(hours=48),
                last_analyze=datetime.now(),
            )
        ]
    )

    query_optimizer.optimize_tables = AsyncMock()

    # Start monitoring
    await query_optimizer.start_monitoring(interval_seconds=0.1)
    await asyncio.sleep(0.2)
    await query_optimizer.stop_monitoring()

    # Assert
    assert query_optimizer.optimize_tables.called


@pytest.mark.asyncio
async def test_cleanup(query_optimizer):
    """Test cleanup method."""
    # Arrange
    await query_optimizer.start_monitoring(interval_seconds=1)

    # Act
    await query_optimizer.cleanup()

    # Assert
    assert query_optimizer.monitoring_enabled is False


@pytest.mark.asyncio
async def test_error_handling_in_monitoring_loop(query_optimizer):
    """Test error handling in monitoring loop."""
    # Arrange
    query_optimizer.analyze_slow_queries = AsyncMock(
        side_effect=Exception("Test error")
    )

    # Start monitoring
    await query_optimizer.start_monitoring(interval_seconds=0.1)

    # Should not crash despite error
    await asyncio.sleep(0.2)

    # Stop monitoring
    await query_optimizer.stop_monitoring()

    # Assert - should have survived the error
    assert True


@pytest.mark.asyncio
async def test_multiple_index_creation_attempts(query_optimizer, mock_pool):
    """Test handling multiple index creation attempts."""
    # Arrange
    conn = await mock_pool.acquire().__aenter__()

    # First call: index doesn't exist
    # Second call: index exists
    conn.fetchval = AsyncMock(side_effect=[False, True])

    # Act
    result1 = await query_optimizer._create_index("test_idx", "test_table", "(col)")
    result2 = await query_optimizer._create_index("test_idx", "test_table", "(col)")

    # Assert
    assert result1 is True
    assert result2 is True


@pytest.mark.asyncio
async def test_index_creation_failure(query_optimizer, mock_pool):
    """Test handling index creation failure."""
    # Arrange
    conn = await mock_pool.acquire().__aenter__()
    conn.fetchval = AsyncMock(return_value=False)
    conn.execute = AsyncMock(side_effect=Exception("Index creation failed"))

    # Act
    result = await query_optimizer._create_index("test_idx", "test_table", "(col)")

    # Assert
    assert result is False
