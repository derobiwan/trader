"""
Database Query Optimizer

Creates optimized indexes for common queries and identifies slow queries.

Features:
- Create strategic indexes (including partial indexes)
- Analyze slow queries via pg_stat_statements
- Vacuum and analyze recommendations
- Query performance monitoring

Author: Performance Optimization Team
Date: 2025-10-29
Sprint: 3, Stream C, Task 046
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import asyncpg

logger = logging.getLogger(__name__)


@dataclass
class SlowQuery:
    """Information about a slow query"""

    query: str
    calls: int
    total_time_ms: float
    mean_time_ms: float
    max_time_ms: float
    stddev_time_ms: float


@dataclass
class IndexRecommendation:
    """Recommendation for creating an index"""

    table: str
    columns: List[str]
    index_type: str  # "btree", "hash", "gin", etc.
    is_partial: bool
    condition: Optional[str]
    estimated_benefit: str


class QueryOptimizer:
    """
    Database query optimization and performance analysis.

    Features:
    - Strategic index creation for common queries
    - Partial indexes for active data
    - Slow query identification
    - Vacuum and analyze scheduling
    """

    def __init__(self, db_pool: asyncpg.Pool):
        """
        Initialize query optimizer.

        Args:
            db_pool: AsyncPG connection pool
        """
        self.db_pool = db_pool
        logger.info("QueryOptimizer initialized")

    # ========================================================================
    # Index Creation
    # ========================================================================

    async def create_all_indexes(self) -> Dict[str, bool]:
        """
        Create all recommended indexes.

        Returns:
            Dictionary mapping index name to success status
        """
        indexes = self._get_index_definitions()
        results = {}

        for index_def in indexes:
            try:
                async with self.db_pool.acquire() as conn:
                    await conn.execute(index_def)
                    index_name = self._extract_index_name(index_def)
                    results[index_name] = True
                    logger.info(f"✓ Created index: {index_name}")
            except Exception as e:
                index_name = self._extract_index_name(index_def)
                results[index_name] = False
                logger.error(f"✗ Failed to create index {index_name}: {e}")

        success_count = sum(1 for v in results.values() if v)
        logger.info(
            f"Index creation complete: {success_count}/{len(results)} successful"
        )

        return results

    def _get_index_definitions(self) -> List[str]:
        """
        Get list of index definitions to create.

        Returns:
            List of CREATE INDEX SQL statements
        """
        return [
            # ================================================================
            # Position Indexes
            # ================================================================
            # Composite index for position queries by symbol and status
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_positions_symbol_status
            ON positions(symbol, status)
            """,
            # Time-based queries
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_positions_created_at
            ON positions(created_at DESC)
            """,
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_positions_updated_at
            ON positions(updated_at DESC)
            """,
            # Partial index for ONLY active positions (most common query)
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_active_positions
            ON positions(symbol, side, quantity)
            WHERE status IN ('OPEN', 'OPENING', 'CLOSING')
            """,
            # ================================================================
            # Trade History Indexes
            # ================================================================
            # Time-based queries (most common)
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trades_timestamp
            ON trades(timestamp DESC)
            """,
            # Symbol-based P&L queries
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trades_symbol_pnl
            ON trades(symbol, realized_pnl)
            """,
            # Trade type filtering
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trades_type_timestamp
            ON trades(trade_type, timestamp DESC)
            """,
            # Partial index for profitable trades
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trades_profitable
            ON trades(symbol, realized_pnl, timestamp DESC)
            WHERE realized_pnl > 0
            """,
            # ================================================================
            # State Transition Indexes
            # ================================================================
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_state_transitions_symbol
            ON position_state_transitions(symbol, timestamp DESC)
            """,
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_state_transitions_position
            ON position_state_transitions(position_id, timestamp DESC)
            """,
            # ================================================================
            # Market Data Cache Indexes
            # ================================================================
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_market_data_symbol_time
            ON market_data_cache(symbol, timeframe, timestamp DESC)
            """,
            # Partial index for recent data only (last 7 days)
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_market_data_recent
            ON market_data_cache(symbol, timestamp DESC)
            WHERE timestamp > NOW() - INTERVAL '7 days'
            """,
            # ================================================================
            # Risk Events Indexes
            # ================================================================
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_risk_events_timestamp
            ON risk_events(timestamp DESC)
            """,
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_risk_events_severity
            ON risk_events(severity, timestamp DESC)
            WHERE severity IN ('CRITICAL', 'HIGH')
            """,
        ]

    def _extract_index_name(self, index_sql: str) -> str:
        """
        Extract index name from CREATE INDEX statement.

        Args:
            index_sql: SQL CREATE INDEX statement

        Returns:
            Index name
        """
        # Simple extraction: find text after "IF NOT EXISTS"
        if "IF NOT EXISTS" in index_sql:
            parts = index_sql.split("IF NOT EXISTS")[1].strip().split()
            return parts[0]
        return "unknown_index"

    # ========================================================================
    # Slow Query Analysis
    # ========================================================================

    async def analyze_slow_queries(
        self,
        min_mean_time_ms: float = 10.0,
        limit: int = 20,
    ) -> List[SlowQuery]:
        """
        Identify slow queries using pg_stat_statements.

        Args:
            min_mean_time_ms: Minimum mean execution time in milliseconds
            limit: Maximum number of queries to return

        Returns:
            List of slow queries ordered by mean time
        """
        query = """
        SELECT
            query,
            calls,
            total_exec_time as total_time,
            mean_exec_time as mean_time,
            max_exec_time as max_time,
            stddev_exec_time as stddev_time
        FROM pg_stat_statements
        WHERE mean_exec_time > $1
        ORDER BY mean_exec_time DESC
        LIMIT $2
        """

        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(query, min_mean_time_ms, limit)

                slow_queries = [
                    SlowQuery(
                        query=row["query"],
                        calls=row["calls"],
                        total_time_ms=row["total_time"],
                        mean_time_ms=row["mean_time"],
                        max_time_ms=row["max_time"],
                        stddev_time_ms=row["stddev_time"],
                    )
                    for row in rows
                ]

                logger.info(f"Found {len(slow_queries)} slow queries")

                for sq in slow_queries:
                    logger.warning(
                        f"Slow query: {sq.mean_time_ms:.2f}ms avg, "
                        f"{sq.calls} calls - {sq.query[:100]}..."
                    )

                return slow_queries

        except Exception as e:
            logger.error(f"Failed to analyze slow queries: {e}")
            return []

    # ========================================================================
    # Database Maintenance
    # ========================================================================

    async def vacuum_analyze(self, table_names: Optional[List[str]] = None):
        """
        Run VACUUM ANALYZE on specified tables.

        Args:
            table_names: List of table names (None = all tables)
        """
        if table_names is None:
            table_names = [
                "positions",
                "trades",
                "position_state_transitions",
                "market_data_cache",
                "risk_events",
            ]

        for table in table_names:
            try:
                async with self.db_pool.acquire() as conn:
                    await conn.execute(f"VACUUM ANALYZE {table}")
                    logger.info(f"✓ Vacuumed and analyzed table: {table}")
            except Exception as e:
                logger.error(f"✗ Failed to vacuum {table}: {e}")

    async def get_table_stats(self, table_name: str) -> Dict:
        """
        Get statistics for a table.

        Args:
            table_name: Name of table

        Returns:
            Dictionary with table statistics
        """
        query = """
        SELECT
            schemaname,
            relname,
            n_live_tup as live_tuples,
            n_dead_tup as dead_tuples,
            n_tup_ins as inserts,
            n_tup_upd as updates,
            n_tup_del as deletes,
            last_vacuum,
            last_autovacuum,
            last_analyze,
            last_autoanalyze
        FROM pg_stat_user_tables
        WHERE relname = $1
        """

        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(query, table_name)

                if row:
                    stats = dict(row)
                    logger.info(
                        f"Table {table_name}: "
                        f"{stats['live_tuples']} live, "
                        f"{stats['dead_tuples']} dead tuples"
                    )
                    return stats

                return {}

        except Exception as e:
            logger.error(f"Failed to get stats for {table_name}: {e}")
            return {}

    # ========================================================================
    # Index Usage Analysis
    # ========================================================================

    async def analyze_index_usage(self) -> List[Dict]:
        """
        Analyze which indexes are being used.

        Returns:
            List of index usage statistics
        """
        query = """
        SELECT
            schemaname,
            tablename,
            indexname,
            idx_scan as scans,
            idx_tup_read as tuples_read,
            idx_tup_fetch as tuples_fetched
        FROM pg_stat_user_indexes
        ORDER BY idx_scan DESC
        """

        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(query)

                index_stats = [dict(row) for row in rows]

                # Log unused indexes
                unused = [idx for idx in index_stats if idx["scans"] == 0]
                if unused:
                    logger.warning(
                        f"Found {len(unused)} unused indexes that could be dropped"
                    )

                return index_stats

        except Exception as e:
            logger.error(f"Failed to analyze index usage: {e}")
            return []

    # ========================================================================
    # Query Plan Analysis
    # ========================================================================

    async def explain_query(self, query: str, analyze: bool = False) -> str:
        """
        Get EXPLAIN output for a query.

        Args:
            query: SQL query to explain
            analyze: If True, run EXPLAIN ANALYZE (actually executes query)

        Returns:
            EXPLAIN output as string
        """
        explain_cmd = "EXPLAIN ANALYZE" if analyze else "EXPLAIN"
        explain_query = f"{explain_cmd} {query}"

        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(explain_query)
                plan = "\n".join([row[0] for row in rows])
                return plan

        except Exception as e:
            logger.error(f"Failed to explain query: {e}")
            return f"Error: {e}"

    # ========================================================================
    # Recommendations
    # ========================================================================

    def get_index_recommendations(self) -> List[IndexRecommendation]:
        """
        Get list of recommended indexes.

        Returns:
            List of index recommendations with explanations
        """
        return [
            IndexRecommendation(
                table="positions",
                columns=["symbol", "status"],
                index_type="btree",
                is_partial=False,
                condition=None,
                estimated_benefit="High - Most common position query pattern",
            ),
            IndexRecommendation(
                table="positions",
                columns=["symbol", "side", "quantity"],
                index_type="btree",
                is_partial=True,
                condition="status IN ('OPEN', 'OPENING', 'CLOSING')",
                estimated_benefit=(
                    "Very High - Dramatically reduces index size for active position queries"
                ),
            ),
            IndexRecommendation(
                table="trades",
                columns=["timestamp"],
                index_type="btree",
                is_partial=False,
                condition=None,
                estimated_benefit="High - Time-based queries are extremely common",
            ),
            IndexRecommendation(
                table="trades",
                columns=["symbol", "realized_pnl", "timestamp"],
                index_type="btree",
                is_partial=True,
                condition="realized_pnl > 0",
                estimated_benefit="Medium - Profitable trade analysis queries",
            ),
            IndexRecommendation(
                table="market_data_cache",
                columns=["symbol", "timestamp"],
                index_type="btree",
                is_partial=True,
                condition="timestamp > NOW() - INTERVAL '7 days'",
                estimated_benefit=(
                    "High - Most queries target recent data, dramatically reduces index size"
                ),
            ),
        ]

    # ========================================================================
    # Performance Monitoring
    # ========================================================================

    async def get_performance_summary(self) -> Dict:
        """
        Get overall database performance summary.

        Returns:
            Dictionary with performance metrics
        """
        summary = {
            "timestamp": datetime.utcnow(),
            "slow_queries": len(await self.analyze_slow_queries()),
            "index_usage": await self.analyze_index_usage(),
        }

        # Get table stats for key tables
        table_stats = {}
        for table in ["positions", "trades", "market_data_cache"]:
            stats = await self.get_table_stats(table)
            if stats:
                table_stats[table] = {
                    "live_tuples": stats.get("live_tuples", 0),
                    "dead_tuples": stats.get("dead_tuples", 0),
                }

        summary["table_stats"] = table_stats

        return summary
