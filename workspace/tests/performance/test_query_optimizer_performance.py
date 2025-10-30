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
    async def test_create_all_indexes(self, optimizer, mock_db_pool):
        """Test index creation."""
        results = await optimizer.create_all_indexes()

        assert "total" in results
        assert "created" in results
        assert "failed" in results
        assert results["total"] > 0

    @pytest.mark.asyncio
    async def test_analyze_slow_queries(self, optimizer, mock_db_pool):
        """Test slow query analysis."""
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

        slow_queries = await optimizer.analyze_slow_queries(limit=10)

        assert len(slow_queries) > 0
        assert slow_queries[0].query == "SELECT * FROM positions"
        assert slow_queries[0].calls == 100
        assert slow_queries[0]["mean_time_ms"] == 15.0
        assert slow_queries[0]["calls"] == 100

    @pytest.mark.asyncio
    async def test_analyze_index_usage(self, optimizer, mock_db_pool):
        """Test index usage analysis."""
        mock_db_pool.fetch.return_value = [
            {
                "tablename": "positions",
                "indexname": "idx_positions_symbol",
                "idx_scan": 1000,
                "idx_tup_read": 5000,
                "idx_tup_fetch": 5000,
            }
        ]

        stats = await optimizer.analyze_index_usage()

        assert len(stats) > 0
        assert stats[0]["table"] == "positions"
        assert stats[0]["scans"] == 1000

    @pytest.mark.asyncio
    async def test_get_table_stats(self, optimizer, mock_db_pool):
        """Test table statistics."""
        mock_db_pool.fetch.return_value = {
            "seq_scan": 10,
            "seq_tup_read": 100,
            "idx_scan": 1000,
            "idx_tup_fetch": 5000,
            "n_tup_ins": 500,
            "n_tup_upd": 200,
            "n_tup_del": 50,
            "n_live_tup": 450,
            "n_dead_tup": 50,
        }

        stats = await optimizer.get_table_stats("positions")

        assert "live_tuples" in stats
        assert stats["live_tuples"] == 450

    @pytest.mark.asyncio
    async def test_vacuum_analyze(self, optimizer, mock_db_pool):
        """Test vacuum analyze operation."""
        await optimizer.vacuum_analyze(["positions", "trades"])

        # Verify vacuum analyze was called
        assert mock_db_pool.execute.call_count >= 2

    @pytest.mark.asyncio
    async def test_get_performance_summary(self, optimizer, mock_db_pool):
        """Test performance summary collection."""
        mock_db_pool.fetch.return_value = []

        summary = await optimizer.get_performance_summary()

        assert "total_indexes" in summary
        assert "slow_queries_count" in summary
        assert "recommendations" in summary
