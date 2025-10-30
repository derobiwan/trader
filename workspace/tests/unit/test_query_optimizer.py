"""
Unit Tests for Database Query Optimizer

Tests database optimization features including:
- Index creation
- Slow query analysis
- Database maintenance
- Performance monitoring

Author: Testing Team
Date: 2025-10-29
Sprint: 3, Stream C
"""

from unittest.mock import AsyncMock, Mock

import pytest

from workspace.shared.database.query_optimizer import (IndexRecommendation,
                                                       QueryOptimizer,
                                                       SlowQuery)


@pytest.fixture
def mock_connection():
    """Mock database connection"""
    conn = AsyncMock()
    conn.execute = AsyncMock()
    conn.fetch = AsyncMock()
    conn.fetchrow = AsyncMock()
    return conn


@pytest.fixture
def mock_db_pool(mock_connection):
    """Mock AsyncPG connection pool"""
    pool = Mock()
    # Create async context manager for acquire()
    acquire_context = AsyncMock()
    acquire_context.__aenter__ = AsyncMock(return_value=mock_connection)
    acquire_context.__aexit__ = AsyncMock(return_value=None)
    pool.acquire = Mock(return_value=acquire_context)
    return pool


@pytest.fixture
def optimizer(mock_db_pool):
    """Query optimizer with mocked database"""
    return QueryOptimizer(mock_db_pool)


# ============================================================================
# Index Creation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_all_indexes_success(optimizer, mock_connection):
    """Test successful index creation"""
    # Execute
    results = await optimizer.create_all_indexes()

    # Assert
    assert isinstance(results, dict)
    assert len(results) > 0
    assert mock_connection.execute.called


@pytest.mark.asyncio
async def test_create_all_indexes_partial_failure(optimizer, mock_connection):
    """Test index creation with some failures"""
    # Setup - Make some executions fail
    call_count = 0

    async def mock_execute(sql):
        nonlocal call_count
        call_count += 1
        if call_count % 3 == 0:  # Every 3rd call fails
            raise Exception("Index already exists")

    mock_connection.execute = mock_execute

    # Execute
    results = await optimizer.create_all_indexes()

    # Assert
    assert isinstance(results, dict)
    success_count = sum(1 for v in results.values() if v)
    failure_count = sum(1 for v in results.values() if not v)
    assert failure_count > 0  # Some failures occurred


def test_get_index_definitions(optimizer):
    """Test getting index definitions"""
    definitions = optimizer._get_index_definitions()

    assert isinstance(definitions, list)
    assert len(definitions) > 10  # Should have multiple indexes
    assert all("CREATE INDEX" in defn for defn in definitions)
    assert any("CONCURRENTLY" in defn for defn in definitions)
    assert any("WHERE" in defn for defn in definitions)  # Partial indexes


def test_extract_index_name(optimizer):
    """Test extracting index name from SQL"""
    sql = """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_positions_symbol_status
    ON positions(symbol, status)
    """

    name = optimizer._extract_index_name(sql)

    assert name == "idx_positions_symbol_status"


# ============================================================================
# Slow Query Analysis Tests
# ============================================================================


@pytest.mark.asyncio
async def test_analyze_slow_queries(optimizer, mock_connection):
    """Test slow query analysis"""
    # Setup
    mock_connection.fetch = AsyncMock(
        return_value=[
            {
                "query": "SELECT * FROM positions WHERE symbol = $1",
                "calls": 1000,
                "total_time": 15000.0,
                "mean_time": 15.0,
                "max_time": 100.0,
                "stddev_time": 5.0,
            },
            {
                "query": "SELECT * FROM trades WHERE timestamp > $1",
                "calls": 500,
                "total_time": 7500.0,
                "mean_time": 15.0,
                "max_time": 50.0,
                "stddev_time": 3.0,
            },
        ]
    )

    # Execute
    slow_queries = await optimizer.analyze_slow_queries(min_mean_time_ms=10.0)

    # Assert
    assert len(slow_queries) == 2
    assert all(isinstance(q, SlowQuery) for q in slow_queries)
    assert slow_queries[0].calls == 1000
    assert slow_queries[0].mean_time_ms == 15.0


@pytest.mark.asyncio
async def test_analyze_slow_queries_empty(optimizer, mock_connection):
    """Test slow query analysis with no slow queries"""
    # Setup
    mock_connection.fetch = AsyncMock(return_value=[])

    # Execute
    slow_queries = await optimizer.analyze_slow_queries()

    # Assert
    assert len(slow_queries) == 0


@pytest.mark.asyncio
async def test_analyze_slow_queries_error(optimizer, mock_connection):
    """Test slow query analysis error handling"""
    # Setup
    mock_connection.fetch = AsyncMock(side_effect=Exception("Database error"))

    # Execute
    slow_queries = await optimizer.analyze_slow_queries()

    # Assert - should return empty list on error
    assert slow_queries == []


# ============================================================================
# Database Maintenance Tests
# ============================================================================


@pytest.mark.asyncio
async def test_vacuum_analyze_default_tables(optimizer, mock_connection):
    """Test vacuum analyze with default tables"""
    # Execute
    await optimizer.vacuum_analyze()

    # Assert
    assert mock_connection.execute.call_count >= 5  # Default tables


@pytest.mark.asyncio
async def test_vacuum_analyze_specific_tables(optimizer, mock_connection):
    """Test vacuum analyze with specific tables"""
    # Execute
    await optimizer.vacuum_analyze(table_names=["positions", "trades"])

    # Assert
    assert mock_connection.execute.call_count == 2


@pytest.mark.asyncio
async def test_get_table_stats(optimizer, mock_connection):
    """Test getting table statistics"""
    # Setup
    mock_connection.fetchrow = AsyncMock(
        return_value={
            "schemaname": "public",
            "relname": "positions",
            "live_tuples": 1000,
            "dead_tuples": 50,
            "inserts": 1500,
            "updates": 200,
            "deletes": 100,
            "last_vacuum": None,
            "last_autovacuum": None,
            "last_analyze": None,
            "last_autoanalyze": None,
        }
    )

    # Execute
    stats = await optimizer.get_table_stats("positions")

    # Assert
    assert stats["live_tuples"] == 1000
    assert stats["dead_tuples"] == 50
    assert stats["inserts"] == 1500


@pytest.mark.asyncio
async def test_get_table_stats_not_found(optimizer, mock_connection):
    """Test getting stats for non-existent table"""
    # Setup
    mock_connection.fetchrow = AsyncMock(return_value=None)

    # Execute
    stats = await optimizer.get_table_stats("nonexistent")

    # Assert
    assert stats == {}


# ============================================================================
# Index Usage Analysis Tests
# ============================================================================


@pytest.mark.asyncio
async def test_analyze_index_usage(optimizer, mock_connection):
    """Test index usage analysis"""
    # Setup
    mock_connection.fetch = AsyncMock(
        return_value=[
            {
                "schemaname": "public",
                "tablename": "positions",
                "indexname": "idx_positions_symbol",
                "scans": 1000,
                "tuples_read": 10000,
                "tuples_fetched": 9500,
            },
            {
                "schemaname": "public",
                "tablename": "trades",
                "indexname": "idx_trades_timestamp",
                "scans": 0,  # Unused index
                "tuples_read": 0,
                "tuples_fetched": 0,
            },
        ]
    )

    # Execute
    index_stats = await optimizer.analyze_index_usage()

    # Assert
    assert len(index_stats) == 2
    assert index_stats[0]["scans"] == 1000
    assert index_stats[1]["scans"] == 0  # Unused


# ============================================================================
# Query Plan Analysis Tests
# ============================================================================


@pytest.mark.asyncio
async def test_explain_query(optimizer, mock_connection):
    """Test EXPLAIN query functionality"""
    # Setup
    mock_connection.fetch = AsyncMock(
        return_value=[
            ["Seq Scan on positions  (cost=0.00..35.50 rows=10 width=100)"],
            ["  Filter: (symbol = 'BTC/USDT:USDT'::text)"],
        ]
    )

    # Execute
    plan = await optimizer.explain_query("SELECT * FROM positions WHERE symbol = $1")

    # Assert
    assert "Seq Scan" in plan
    assert "Filter" in plan


@pytest.mark.asyncio
async def test_explain_query_analyze(optimizer, mock_connection):
    """Test EXPLAIN ANALYZE query functionality"""
    # Setup
    mock_connection.fetch = AsyncMock(
        return_value=[
            [
                "Seq Scan on positions  (cost=0.00..35.50 rows=10 width=100) (actual time=0.010..0.020 rows=5 loops=1)"
            ],
            ["Planning Time: 0.050 ms"],
            ["Execution Time: 0.100 ms"],
        ]
    )

    # Execute
    plan = await optimizer.explain_query(
        "SELECT * FROM positions WHERE symbol = $1", analyze=True
    )

    # Assert
    assert "actual time" in plan
    assert "Execution Time" in plan


# ============================================================================
# Recommendations Tests
# ============================================================================


def test_get_index_recommendations(optimizer):
    """Test getting index recommendations"""
    recommendations = optimizer.get_index_recommendations()

    assert len(recommendations) > 0
    assert all(isinstance(r, IndexRecommendation) for r in recommendations)

    # Check for partial index recommendation
    partial_indexes = [r for r in recommendations if r.is_partial]
    assert len(partial_indexes) > 0

    # Check structure
    rec = recommendations[0]
    assert hasattr(rec, "table")
    assert hasattr(rec, "columns")
    assert hasattr(rec, "index_type")
    assert hasattr(rec, "estimated_benefit")


# ============================================================================
# Performance Summary Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_performance_summary(optimizer, mock_connection):
    """Test getting performance summary"""
    # Setup - Mock slow queries
    mock_connection.fetch = AsyncMock(return_value=[])

    # Mock table stats
    mock_connection.fetchrow = AsyncMock(
        return_value={
            "live_tuples": 1000,
            "dead_tuples": 50,
        }
    )

    # Execute
    summary = await optimizer.get_performance_summary()

    # Assert
    assert "timestamp" in summary
    assert "slow_queries" in summary
    assert "index_usage" in summary
    assert "table_stats" in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
