"""
Tests for Database Query Optimizer

Author: Performance Optimizer Agent
Date: 2025-10-29
Sprint: 3 Stream C Task-046
"""

from unittest.mock import AsyncMock, Mock

import pytest

from workspace.shared.database.query_optimizer import QueryOptimizer


@pytest.fixture
async def mock_db_pool():
    """Create mock database pool."""
    pool = Mock()
    pool.execute = AsyncMock()
    pool.fetch = AsyncMock()
    pool.fetchrow = AsyncMock()
    pool.fetchval = AsyncMock()
    return pool


@pytest.fixture
async def optimizer(mock_db_pool):
    """Create query optimizer with mock database."""
    return QueryOptimizer(mock_db_pool)


class TestQueryOptimizer:
    """Test query optimizer functionality."""

    @pytest.mark.asyncio
    async def test_initialize(self, optimizer, mock_db_pool):
        """Test optimizer initialization."""
        await optimizer.initialize()

        assert optimizer.is_initialized
        mock_db_pool.execute.assert_called()

    @pytest.mark.asyncio
    async def test_create_indexes(self, optimizer):
        """Test index creation."""
        optimizer.is_initialized = True

        results = await optimizer.create_indexes()

        assert "total" in results
        assert "created" in results
        assert "failed" in results
        assert results["total"] > 0

    @pytest.mark.asyncio
    async def test_analyze_slow_queries(self, optimizer, mock_db_pool):
        """Test slow query analysis."""
        optimizer.is_initialized = True

        # Mock slow query results
        mock_db_pool.fetch.return_value = [
            {
                "query": "SELECT * FROM positions",
                "calls": 100,
                "total_exec_time": 1500.0,
                "mean_exec_time": 15.0,
                "max_exec_time": 50.0,
                "min_exec_time": 5.0,
                "stddev_exec_time": 10.0,
                "rows": 1000,
            }
        ]

        slow_queries = await optimizer.analyze_slow_queries(threshold_ms=10.0)

        assert len(slow_queries) == 1
        assert slow_queries[0]["mean_time_ms"] == 15.0
        assert slow_queries[0]["calls"] == 100

    @pytest.mark.asyncio
    async def test_get_index_usage_stats(self, optimizer, mock_db_pool):
        """Test index usage statistics."""
        optimizer.is_initialized = True

        mock_db_pool.fetch.return_value = [
            {
                "tablename": "positions",
                "indexname": "idx_positions_symbol",
                "idx_scan": 1000,
                "idx_tup_read": 5000,
                "idx_tup_fetch": 5000,
                "index_size": "64 kB",
            }
        ]

        stats = await optimizer.get_index_usage_stats()

        assert len(stats) == 1
        assert stats[0]["table"] == "positions"
        assert stats[0]["scans"] == 1000

    @pytest.mark.asyncio
    async def test_get_table_stats(self, optimizer, mock_db_pool):
        """Test table statistics."""
        optimizer.is_initialized = True

        mock_db_pool.fetch.return_value = [
            {
                "tablename": "positions",
                "seq_scan": 10,
                "seq_tup_read": 100,
                "idx_scan": 1000,
                "idx_tup_fetch": 5000,
                "n_tup_ins": 500,
                "n_tup_upd": 200,
                "n_tup_del": 50,
                "n_live_tup": 450,
                "n_dead_tup": 50,
                "total_size": "128 kB",
            }
        ]

        stats = await optimizer.get_table_stats()

        assert len(stats) == 1
        assert stats[0]["table"] == "positions"
        assert stats[0]["live_tuples"] == 450
        assert stats[0]["bloat_percent"] == 10.0  # 50/(450+50) * 100

    @pytest.mark.asyncio
    async def test_optimize_tables(self, optimizer, mock_db_pool):
        """Test table optimization."""
        optimizer.is_initialized = True

        mock_db_pool.fetch.return_value = [
            {"tablename": "positions"},
            {"tablename": "trades"},
        ]

        results = await optimizer.optimize_tables()

        assert "tables_optimized" in results
        assert results["tables_optimized"] == 2

    @pytest.mark.asyncio
    async def test_get_performance_metrics(self, optimizer, mock_db_pool):
        """Test performance metrics collection."""
        optimizer.is_initialized = True

        mock_db_pool.fetch.return_value = []

        metrics = await optimizer.get_performance_metrics()

        assert "slow_queries" in metrics
        assert "index_usage" in metrics
        assert "table_stats" in metrics
        assert "summary" in metrics
