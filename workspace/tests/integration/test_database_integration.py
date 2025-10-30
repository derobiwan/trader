"""
Database Integration Tests

Tests PostgreSQL connection, TimescaleDB features, and database operations.

Author: Infrastructure Specialist
Date: 2025-10-28
"""

from datetime import datetime
from decimal import Decimal

import pytest

from workspace.shared.database.connection import DatabasePool, close_pool, init_pool


@pytest.fixture(scope="module")
async def db_pool():
    """Initialize database pool for tests"""
    pool = await init_pool(
        host="localhost",
        port=5432,
        database="trading_system",
        user="trading_user",
        password="",
    )
    yield pool
    await close_pool()


@pytest.mark.asyncio
async def test_database_connection():
    """Test basic database connection"""
    pool = DatabasePool(
        host="localhost",
        port=5432,
        database="trading_system",
        user="trading_user",
        password="",
    )

    await pool.initialize()

    # Test simple query
    result = await pool.fetchval("SELECT 1")
    assert result == 1

    # Check TimescaleDB extension
    timescaledb_version = await pool.fetchval(
        "SELECT extversion FROM pg_extension WHERE extname = 'timescaledb'"
    )
    assert timescaledb_version is not None
    print(f"TimescaleDB version: {timescaledb_version}")

    await pool.close()


@pytest.mark.asyncio
async def test_connection_pool():
    """Test connection pooling"""
    pool = await init_pool()

    # Get pool health
    health = await pool.health_check()
    assert health["healthy"] is True
    assert health["latency_ms"] < 100  # Should be fast locally
    assert health["pool_size"] >= 10  # Min pool size
    print(f"Pool health: {health}")

    await close_pool()


@pytest.mark.asyncio
async def test_trades_hypertable(db_pool):
    """Test trades hypertable operations"""
    # Insert test trade
    trade_id = f"test_trade_{datetime.utcnow().timestamp()}"

    insert_query = """
    INSERT INTO trades (
        trade_id, timestamp, symbol, trade_type, side,
        entry_price, quantity, fees_paid, leverage, exchange
    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
    RETURNING id
    """

    result = await db_pool.fetchval(
        insert_query,
        trade_id,
        datetime.utcnow(),
        "BTC/USDT",
        "ENTRY_LONG",
        "BUY",
        Decimal("45000.00"),
        Decimal("0.1"),
        Decimal("4.50"),
        Decimal("10"),
        "bybit",
    )

    assert result is not None
    print(f"Inserted trade with ID: {result}")

    # Query trade
    select_query = "SELECT * FROM trades WHERE trade_id = $1"
    trade = await db_pool.fetchrow(select_query, trade_id)

    assert trade is not None
    assert trade["symbol"] == "BTC/USDT"
    assert trade["trade_type"] == "ENTRY_LONG"
    assert float(trade["entry_price"]) == 45000.00

    # Cleanup
    await db_pool.execute("DELETE FROM trades WHERE trade_id = $1", trade_id)


@pytest.mark.asyncio
async def test_positions_table(db_pool):
    """Test positions table operations"""
    # Create test position
    position_id = f"test_position_{datetime.utcnow().timestamp()}"

    insert_query = """
    INSERT INTO positions (
        position_id, symbol, side, entry_price, current_price,
        quantity, leverage, unrealized_pnl, exchange, is_open
    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
    RETURNING id
    """

    result = await db_pool.fetchval(
        insert_query,
        position_id,
        "ETH/USDT",
        "LONG",
        Decimal("2500.00"),
        Decimal("2550.00"),
        Decimal("0.5"),
        Decimal("10"),
        Decimal("250.00"),
        "bybit",
        True,
    )

    assert result is not None
    print(f"Inserted position with ID: {result}")

    # Query position
    select_query = "SELECT * FROM positions WHERE position_id = $1"
    position = await db_pool.fetchrow(select_query, position_id)

    assert position is not None
    assert position["symbol"] == "ETH/USDT"
    assert position["side"] == "LONG"
    assert position["is_open"] is True
    assert float(position["unrealized_pnl"]) == 250.00

    # Update position
    update_query = """
    UPDATE positions
    SET current_price = $1, unrealized_pnl = $2
    WHERE position_id = $3
    """
    await db_pool.execute(
        update_query,
        Decimal("2600.00"),
        Decimal("500.00"),
        position_id,
    )

    # Verify update
    updated = await db_pool.fetchrow(select_query, position_id)
    assert float(updated["current_price"]) == 2600.00
    assert float(updated["unrealized_pnl"]) == 500.00

    # Cleanup
    await db_pool.execute("DELETE FROM positions WHERE position_id = $1", position_id)


@pytest.mark.asyncio
async def test_metrics_snapshots_hypertable(db_pool):
    """Test metrics snapshots hypertable"""
    # Insert test metrics
    insert_query = """
    INSERT INTO metrics_snapshots (
        timestamp, trades_total, trades_successful, realized_pnl_total,
        execution_latency_avg_ms, cache_hit_rate_percent
    ) VALUES ($1, $2, $3, $4, $5, $6)
    RETURNING id
    """

    result = await db_pool.fetchval(
        insert_query,
        datetime.utcnow(),
        10,
        8,
        Decimal("150.50"),
        Decimal("8.5"),
        Decimal("75.5"),
    )

    assert result is not None
    print(f"Inserted metrics snapshot with ID: {result}")

    # Query recent metrics
    select_query = """
    SELECT * FROM metrics_snapshots
    WHERE timestamp >= NOW() - INTERVAL '1 hour'
    ORDER BY timestamp DESC
    LIMIT 10
    """

    metrics = await db_pool.fetch(select_query)
    assert len(metrics) > 0


@pytest.mark.asyncio
async def test_continuous_aggregate(db_pool):
    """Test continuous aggregate (daily_trade_stats)"""
    # Check if view exists
    view_exists = await db_pool.fetchval(
        """
        SELECT EXISTS (
            SELECT 1 FROM pg_views
            WHERE viewname = 'daily_trade_stats'
        )
        """
    )

    assert view_exists is True
    print("Continuous aggregate 'daily_trade_stats' exists")

    # Query the view (may be empty in tests)
    query = "SELECT * FROM daily_trade_stats LIMIT 5"
    results = await db_pool.fetch(query)
    print(f"Daily trade stats rows: {len(results)}")


@pytest.mark.asyncio
async def test_retention_policy(db_pool):
    """Test retention policies are configured"""
    # Check retention policies exist
    query = """
    SELECT * FROM timescaledb_information.jobs
    WHERE proc_name = 'policy_retention'
    """

    policies = await db_pool.fetch(query)
    print(f"Retention policies configured: {len(policies)}")

    # We expect retention policies for trades, metrics, and logs
    assert len(policies) >= 3


@pytest.mark.asyncio
async def test_database_performance(db_pool):
    """Test database query performance"""
    import time

    # Measure simple query latency
    start = time.time()
    await db_pool.fetchval("SELECT 1")
    latency_ms = (time.time() - start) * 1000

    print(f"Query latency: {latency_ms:.2f}ms")
    assert latency_ms < 10  # Should be <10ms for local database

    # Measure bulk insert performance
    trades_to_insert = 100
    start = time.time()

    for i in range(trades_to_insert):
        trade_id = f"perf_test_{i}_{time.time()}"
        await db_pool.execute(
            """
            INSERT INTO trades (
                trade_id, timestamp, symbol, trade_type, side,
                entry_price, quantity, leverage, exchange
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
            trade_id,
            datetime.utcnow(),
            "BTC/USDT",
            "ENTRY_LONG",
            "BUY",
            Decimal("45000.00"),
            Decimal("0.01"),
            Decimal("10"),
            "bybit",
        )

    insert_time = time.time() - start
    trades_per_second = trades_to_insert / insert_time

    print(f"Bulk insert: {trades_per_second:.0f} trades/second")
    assert trades_per_second > 50  # Should handle >50 trades/sec

    # Cleanup
    await db_pool.execute("DELETE FROM trades WHERE trade_id LIKE 'perf_test_%'")


@pytest.mark.asyncio
async def test_llm_requests_table(db_pool):
    """Test LLM requests audit table"""
    # Insert test LLM request
    insert_query = """
    INSERT INTO llm_requests (
        timestamp, model, prompt_tokens, completion_tokens,
        cost_usd, latency_ms, response
    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
    RETURNING id
    """

    result = await db_pool.fetchval(
        insert_query,
        datetime.utcnow(),
        "anthropic/claude-3-5-sonnet",
        1500,
        350,
        Decimal("0.015000"),
        450,
        {"signal": "BUY", "confidence": 0.85},
    )

    assert result is not None
    print(f"Inserted LLM request with ID: {result}")

    # Query recent requests
    select_query = """
    SELECT * FROM llm_requests
    WHERE timestamp >= NOW() - INTERVAL '1 hour'
    ORDER BY timestamp DESC
    LIMIT 10
    """

    requests = await db_pool.fetch(select_query)
    assert len(requests) > 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
