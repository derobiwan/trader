"""
Database Query Optimizer for Trading System.

This module provides comprehensive database query optimization including:
- Index creation and management for all common query patterns
- Slow query detection and analysis
- Table bloat monitoring
- Automatic VACUUM ANALYZE operations
- Performance metrics collection

Author: Performance Optimizer Agent
Date: 2025-10-30
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import asyncpg
from dataclasses import dataclass
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class QueryStats:
    """Statistics for a specific query pattern."""

    query_pattern: str
    total_count: int
    total_time_ms: float
    avg_time_ms: float
    max_time_ms: float
    min_time_ms: float
    p95_time_ms: float
    slow_count: int  # Count of queries > 10ms


@dataclass
class IndexStats:
    """Statistics for database indexes."""

    table_name: str
    index_name: str
    index_size_mb: float
    index_scans: int
    index_reads: int
    effectiveness: float  # Percentage of scans vs table scans


@dataclass
class TableStats:
    """Statistics for database tables."""

    table_name: str
    total_rows: int
    dead_rows: int
    table_size_mb: float
    index_size_mb: float
    bloat_ratio: float
    last_vacuum: Optional[datetime]
    last_analyze: Optional[datetime]


class QueryOptimizer:
    """
    Database query optimizer for the trading system.

    Provides comprehensive query optimization, index management,
    and performance monitoring capabilities.
    """

    # Performance thresholds
    SLOW_QUERY_THRESHOLD_MS = 10.0
    TABLE_BLOAT_THRESHOLD = 0.2  # 20%
    MIN_INDEX_EFFECTIVENESS = 0.5  # 50%
    VACUUM_INTERVAL_HOURS = 24
    ANALYZE_INTERVAL_HOURS = 6

    def __init__(self, connection_pool: asyncpg.Pool):
        """
        Initialize the query optimizer.

        Args:
            connection_pool: AsyncPG connection pool
        """
        self.pool = connection_pool
        self.query_stats: Dict[str, List[float]] = defaultdict(list)
        self.monitoring_enabled = False
        self._monitor_task: Optional[asyncio.Task] = None

    async def initialize(self) -> None:
        """Initialize the query optimizer and enable monitoring extensions."""
        try:
            async with self.pool.acquire() as conn:
                # Enable pg_stat_statements if available
                await conn.execute(
                    """
                    CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
                """
                )

                # Create optimization metadata table
                await conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS optimization_metadata (
                        id SERIAL PRIMARY KEY,
                        optimization_type VARCHAR(50) NOT NULL,
                        table_name VARCHAR(100),
                        index_name VARCHAR(100),
                        executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        duration_ms FLOAT,
                        status VARCHAR(20),
                        details JSONB
                    );
                """
                )

                logger.info("Query optimizer initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize query optimizer: {e}")
            raise

    async def create_indexes(self) -> Dict[str, bool]:
        """
        Create all optimized indexes for common query patterns.

        Returns:
            Dictionary mapping index names to creation success status
        """
        indexes = [
            # Position queries
            (
                "idx_positions_symbol_status",
                "positions",
                "(symbol, status)",
                "WHERE status = 'active'",
            ),
            ("idx_positions_opened_at", "positions", "(opened_at DESC)", None),
            (
                "idx_positions_closed_at",
                "positions",
                "(closed_at DESC)",
                "WHERE closed_at IS NOT NULL",
            ),
            (
                "idx_positions_symbol_opened",
                "positions",
                "(symbol, opened_at DESC)",
                None,
            ),
            # Trade history queries
            ("idx_trades_executed_at", "trades", "(executed_at DESC)", None),
            (
                "idx_trades_symbol_executed",
                "trades",
                "(symbol, executed_at DESC)",
                None,
            ),
            (
                "idx_trades_pnl",
                "trades",
                "(realized_pnl DESC)",
                "WHERE realized_pnl IS NOT NULL",
            ),
            ("idx_trades_symbol_pnl", "trades", "(symbol, realized_pnl)", None),
            # State transition queries
            (
                "idx_state_transitions_symbol",
                "state_transitions",
                "(symbol, transitioned_at DESC)",
                None,
            ),
            (
                "idx_state_transitions_position",
                "state_transitions",
                "(position_id, transitioned_at DESC)",
                None,
            ),
            (
                "idx_state_transitions_from_to",
                "state_transitions",
                "(from_state, to_state)",
                None,
            ),
            # Market data queries (time-series optimization)
            (
                "idx_market_data_symbol_time",
                "market_data",
                "(symbol, timestamp DESC)",
                None,
            ),
            (
                "idx_market_data_partition",
                "market_data",
                "(symbol, DATE(timestamp))",
                None,
            ),
            # Signal queries
            ("idx_signals_symbol_time", "signals", "(symbol, generated_at DESC)", None),
            ("idx_signals_action", "signals", "(action, generated_at DESC)", None),
            # Order queries
            ("idx_orders_symbol_status", "orders", "(symbol, status)", None),
            ("idx_orders_created", "orders", "(created_at DESC)", None),
            # Performance metrics
            (
                "idx_metrics_type_time",
                "performance_metrics",
                "(metric_type, recorded_at DESC)",
                None,
            ),
            # Risk events
            (
                "idx_risk_events_severity",
                "risk_events",
                "(severity, created_at DESC)",
                None,
            ),
        ]

        results = {}

        for index_name, table, columns, where_clause in indexes:
            success = await self._create_index(index_name, table, columns, where_clause)
            results[index_name] = success

        # Log summary
        successful = sum(1 for s in results.values() if s)
        logger.info(f"Created {successful}/{len(indexes)} indexes successfully")

        return results

    async def _create_index(
        self,
        index_name: str,
        table: str,
        columns: str,
        where_clause: Optional[str] = None,
    ) -> bool:
        """
        Create a single index with error handling.

        Args:
            index_name: Name of the index
            table: Table name
            columns: Column specification
            where_clause: Optional WHERE clause for partial index

        Returns:
            True if index was created successfully
        """
        try:
            async with self.pool.acquire() as conn:
                # Check if index already exists
                exists = await conn.fetchval(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM pg_indexes
                        WHERE indexname = $1
                    );
                """,
                    index_name,
                )

                if exists:
                    logger.debug(f"Index {index_name} already exists")
                    return True

                # Build index creation query
                query = f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {index_name} ON {table} {columns}"
                if where_clause:
                    query += f" {where_clause}"

                start_time = time.time()
                await conn.execute(query)
                duration = (time.time() - start_time) * 1000

                # Log optimization metadata
                await conn.execute(
                    """
                    INSERT INTO optimization_metadata
                    (optimization_type, table_name, index_name, duration_ms, status)
                    VALUES ('create_index', $1, $2, $3, 'success');
                """,
                    table,
                    index_name,
                    duration,
                )

                logger.info(f"Created index {index_name} in {duration:.2f}ms")
                return True

        except Exception as e:
            logger.error(f"Failed to create index {index_name}: {e}")
            return False

    async def analyze_slow_queries(self, limit: int = 20) -> List[QueryStats]:
        """
        Analyze slow queries from pg_stat_statements.

        Args:
            limit: Maximum number of slow queries to return

        Returns:
            List of QueryStats for slow queries
        """
        try:
            async with self.pool.acquire() as conn:
                # Check if pg_stat_statements is available
                has_extension = await conn.fetchval(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM pg_extension
                        WHERE extname = 'pg_stat_statements'
                    );
                """
                )

                if not has_extension:
                    logger.warning("pg_stat_statements extension not available")
                    return []

                # Fetch slow queries
                rows = await conn.fetch(
                    """
                    SELECT
                        query,
                        calls,
                        total_time,
                        mean_time,
                        max_time,
                        min_time,
                        stddev_time
                    FROM pg_stat_statements
                    WHERE mean_time > $1
                        AND query NOT LIKE '%pg_stat_statements%'
                        AND query NOT LIKE '%optimization_metadata%'
                    ORDER BY mean_time DESC
                    LIMIT $2;
                """,
                    self.SLOW_QUERY_THRESHOLD_MS,
                    limit,
                )

                stats = []
                for row in rows:
                    # Calculate P95 (approximation using mean + 2*stddev)
                    p95 = row["mean_time"] + (2 * row["stddev_time"])

                    stats.append(
                        QueryStats(
                            query_pattern=self._normalize_query(row["query"]),
                            total_count=row["calls"],
                            total_time_ms=row["total_time"],
                            avg_time_ms=row["mean_time"],
                            max_time_ms=row["max_time"],
                            min_time_ms=row["min_time"],
                            p95_time_ms=p95,
                            slow_count=row["calls"],  # All are slow if in this result
                        )
                    )

                logger.info(f"Found {len(stats)} slow queries")
                return stats

        except Exception as e:
            logger.error(f"Failed to analyze slow queries: {e}")
            return []

    def _normalize_query(self, query: str) -> str:
        """Normalize query by removing specific values for pattern matching."""
        import re

        # Replace numbers with placeholders
        query = re.sub(r"\b\d+\b", "?", query)
        # Replace quoted strings with placeholders
        query = re.sub(r"'[^']*'", "'?'", query)
        # Truncate long queries
        if len(query) > 200:
            query = query[:200] + "..."
        return query.strip()

    async def get_index_usage_stats(self) -> List[IndexStats]:
        """
        Get usage statistics for all indexes.

        Returns:
            List of IndexStats for all indexes
        """
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT
                        schemaname,
                        tablename,
                        indexname,
                        idx_scan,
                        idx_tup_read,
                        idx_tup_fetch,
                        pg_size_pretty(pg_relation_size(indexrelid)) as index_size
                    FROM pg_stat_user_indexes
                    WHERE schemaname = 'public'
                    ORDER BY idx_scan DESC;
                """
                )

                stats = []
                for row in rows:
                    # Calculate effectiveness (simplified)
                    total_scans = row["idx_scan"] or 0
                    effectiveness = (
                        min(1.0, total_scans / 1000.0) if total_scans > 0 else 0.0
                    )

                    # Parse size
                    size_str = row["index_size"]
                    size_mb = self._parse_size_to_mb(size_str)

                    stats.append(
                        IndexStats(
                            table_name=row["tablename"],
                            index_name=row["indexname"],
                            index_size_mb=size_mb,
                            index_scans=row["idx_scan"] or 0,
                            index_reads=row["idx_tup_read"] or 0,
                            effectiveness=effectiveness,
                        )
                    )

                return stats

        except Exception as e:
            logger.error(f"Failed to get index usage stats: {e}")
            return []

    def _parse_size_to_mb(self, size_str: str) -> float:
        """Parse PostgreSQL size string to MB."""
        if "MB" in size_str:
            return float(size_str.replace(" MB", ""))
        elif "GB" in size_str:
            return float(size_str.replace(" GB", "")) * 1024
        elif "kB" in size_str:
            return float(size_str.replace(" kB", "")) / 1024
        elif "bytes" in size_str:
            return float(size_str.replace(" bytes", "")) / (1024 * 1024)
        return 0.0

    async def get_table_stats(self) -> List[TableStats]:
        """
        Get statistics for all tables including bloat analysis.

        Returns:
            List of TableStats for all tables
        """
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT
                        schemaname,
                        tablename,
                        n_live_tup,
                        n_dead_tup,
                        last_vacuum,
                        last_analyze,
                        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
                        pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
                        pg_size_pretty(pg_indexes_size(schemaname||'.'||tablename)) as indexes_size
                    FROM pg_stat_user_tables
                    WHERE schemaname = 'public'
                    ORDER BY n_live_tup DESC;
                """
                )

                stats = []
                for row in rows:
                    # Calculate bloat ratio
                    live_rows = row["n_live_tup"] or 0
                    dead_rows = row["n_dead_tup"] or 0
                    total_rows = live_rows + dead_rows
                    bloat_ratio = dead_rows / total_rows if total_rows > 0 else 0.0

                    # Parse sizes
                    table_size_mb = self._parse_size_to_mb(row["table_size"])
                    index_size_mb = self._parse_size_to_mb(row["indexes_size"])

                    stats.append(
                        TableStats(
                            table_name=row["tablename"],
                            total_rows=live_rows,
                            dead_rows=dead_rows,
                            table_size_mb=table_size_mb,
                            index_size_mb=index_size_mb,
                            bloat_ratio=bloat_ratio,
                            last_vacuum=row["last_vacuum"],
                            last_analyze=row["last_analyze"],
                        )
                    )

                return stats

        except Exception as e:
            logger.error(f"Failed to get table stats: {e}")
            return []

    async def optimize_tables(self, force: bool = False) -> Dict[str, bool]:
        """
        Run VACUUM ANALYZE on tables that need optimization.

        Args:
            force: Force optimization even if not needed

        Returns:
            Dictionary mapping table names to optimization success status
        """
        results = {}

        try:
            table_stats = await self.get_table_stats()

            for stats in table_stats:
                needs_vacuum = (
                    force
                    or stats.bloat_ratio > self.TABLE_BLOAT_THRESHOLD
                    or (
                        stats.last_vacuum
                        and datetime.now() - stats.last_vacuum
                        > timedelta(hours=self.VACUUM_INTERVAL_HOURS)
                    )
                )

                needs_analyze = (
                    force
                    or stats.last_analyze is None
                    or datetime.now() - stats.last_analyze
                    > timedelta(hours=self.ANALYZE_INTERVAL_HOURS)
                )

                if needs_vacuum or needs_analyze:
                    success = await self._optimize_table(
                        stats.table_name, vacuum=needs_vacuum, analyze=needs_analyze
                    )
                    results[stats.table_name] = success

            logger.info(f"Optimized {len(results)} tables")
            return results

        except Exception as e:
            logger.error(f"Failed to optimize tables: {e}")
            return results

    async def _optimize_table(
        self, table: str, vacuum: bool = True, analyze: bool = True
    ) -> bool:
        """
        Run VACUUM and/or ANALYZE on a specific table.

        Args:
            table: Table name
            vacuum: Whether to run VACUUM
            analyze: Whether to run ANALYZE

        Returns:
            True if optimization was successful
        """
        try:
            async with self.pool.acquire() as conn:
                operations = []
                if vacuum:
                    operations.append("VACUUM")
                if analyze:
                    operations.append("ANALYZE")

                operation = " ".join(operations)

                start_time = time.time()
                await conn.execute(f"{operation} {table};")
                duration = (time.time() - start_time) * 1000

                # Log optimization metadata
                await conn.execute(
                    """
                    INSERT INTO optimization_metadata
                    (optimization_type, table_name, duration_ms, status, details)
                    VALUES ($1, $2, $3, 'success', $4);
                """,
                    operation.lower(),
                    table,
                    duration,
                    {"vacuum": vacuum, "analyze": analyze},
                )

                logger.info(
                    f"Optimized table {table} ({operation}) in {duration:.2f}ms"
                )
                return True

        except Exception as e:
            logger.error(f"Failed to optimize table {table}: {e}")
            return False

    async def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive performance metrics.

        Returns:
            Dictionary containing various performance metrics
        """
        try:
            # Gather all metrics
            slow_queries = await self.analyze_slow_queries(10)
            index_stats = await self.get_index_usage_stats()
            table_stats = await self.get_table_stats()

            # Calculate aggregates
            total_slow_queries = len(slow_queries)
            avg_slow_query_time = (
                sum(q.avg_time_ms for q in slow_queries) / len(slow_queries)
                if slow_queries
                else 0
            )

            unused_indexes = [
                idx
                for idx in index_stats
                if idx.effectiveness < self.MIN_INDEX_EFFECTIVENESS
            ]

            bloated_tables = [
                tbl
                for tbl in table_stats
                if tbl.bloat_ratio > self.TABLE_BLOAT_THRESHOLD
            ]

            # Calculate database size
            total_size_mb = sum(t.table_size_mb + t.index_size_mb for t in table_stats)

            metrics = {
                "timestamp": datetime.now().isoformat(),
                "slow_queries": {
                    "count": total_slow_queries,
                    "avg_time_ms": avg_slow_query_time,
                    "threshold_ms": self.SLOW_QUERY_THRESHOLD_MS,
                    "top_slow_queries": [
                        {
                            "pattern": q.query_pattern[:100],
                            "avg_time_ms": q.avg_time_ms,
                            "count": q.total_count,
                        }
                        for q in slow_queries[:5]
                    ],
                },
                "indexes": {
                    "total_count": len(index_stats),
                    "unused_count": len(unused_indexes),
                    "total_size_mb": sum(idx.index_size_mb for idx in index_stats),
                    "unused_indexes": [idx.index_name for idx in unused_indexes[:5]],
                },
                "tables": {
                    "total_count": len(table_stats),
                    "bloated_count": len(bloated_tables),
                    "total_size_mb": total_size_mb,
                    "bloated_tables": [
                        {
                            "name": t.table_name,
                            "bloat_ratio": round(t.bloat_ratio, 2),
                            "dead_rows": t.dead_rows,
                        }
                        for t in bloated_tables[:5]
                    ],
                },
                "optimization_status": {
                    "monitoring_enabled": self.monitoring_enabled,
                    "last_optimization": datetime.now().isoformat(),
                },
            }

            return metrics

        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return {}

    async def start_monitoring(self, interval_seconds: int = 300) -> None:
        """
        Start continuous performance monitoring.

        Args:
            interval_seconds: Monitoring interval in seconds (default: 5 minutes)
        """
        if self.monitoring_enabled:
            logger.warning("Monitoring already enabled")
            return

        self.monitoring_enabled = True
        self._monitor_task = asyncio.create_task(
            self._monitoring_loop(interval_seconds)
        )
        logger.info(f"Started performance monitoring (interval: {interval_seconds}s)")

    async def stop_monitoring(self) -> None:
        """Stop continuous performance monitoring."""
        if not self.monitoring_enabled:
            return

        self.monitoring_enabled = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        logger.info("Stopped performance monitoring")

    async def _monitoring_loop(self, interval: int) -> None:
        """
        Continuous monitoring loop.

        Args:
            interval: Monitoring interval in seconds
        """
        while self.monitoring_enabled:
            try:
                # Analyze slow queries
                slow_queries = await self.analyze_slow_queries()
                if slow_queries:
                    logger.warning(f"Found {len(slow_queries)} slow queries")

                # Check for bloated tables
                table_stats = await self.get_table_stats()
                bloated = [
                    t for t in table_stats if t.bloat_ratio > self.TABLE_BLOAT_THRESHOLD
                ]

                if bloated:
                    logger.warning(f"Found {len(bloated)} bloated tables")
                    # Auto-optimize if needed
                    await self.optimize_tables()

                # Check index effectiveness
                index_stats = await self.get_index_usage_stats()
                ineffective = [
                    i
                    for i in index_stats
                    if i.effectiveness < self.MIN_INDEX_EFFECTIVENESS
                ]

                if ineffective:
                    logger.warning(
                        f"Found {len(ineffective)} ineffective indexes: "
                        f"{[i.index_name for i in ineffective[:3]]}"
                    )

                # Sleep until next interval
                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(interval)

    async def cleanup(self) -> None:
        """Cleanup resources and stop monitoring."""
        await self.stop_monitoring()
        logger.info("Query optimizer cleanup complete")
