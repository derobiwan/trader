"""
Comprehensive database schema tests

Tests all 11 tables, indexes, constraints, TimescaleDB hypertables,
connection pooling, and performance benchmarks.

Run with: pytest workspace/shared/database/tests/test_schema.py -v
"""

import asyncio
import os

# Import models
import sys
import time
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

import asyncpg
import pytest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
)

# Imports after path setup to ensure correct module resolution
from workspace.shared.database.connection import DatabasePool  # noqa: E402
from workspace.shared.database.models import (  # noqa: E402
    CircuitBreakerState,
    MarketData,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    PositionSide,
    SignalAction,
    SignalType,
    TradingSignal,
    datetime_to_microseconds,
)

# ============================================================================
# Test Configuration
# ============================================================================


@pytest.fixture(scope="session")
def db_config():
    """Database configuration for tests."""
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "database": os.getenv("DB_NAME", "trading_system_test"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", ""),
    }


@pytest.fixture(scope="session")
async def pool(db_config):
    """Create database pool for all tests."""
    pool = DatabasePool(**db_config)
    await pool.initialize()
    yield pool
    await pool.close()


@pytest.fixture(autouse=True)
async def clean_tables(pool):
    """Clean all tables before each test."""
    # Order matters due to foreign keys
    tables = [
        "position_reconciliation",
        "orders",
        "risk_events",
        "trading_signals",
        "positions",
        "market_data",
        "daily_performance",
        "llm_requests",
        "audit_log",
        "circuit_breaker_state",
    ]

    for table in tables:
        try:
            await pool.execute(f"DELETE FROM {table}")
        except Exception:
            pass  # Table might not exist yet

    yield


# ============================================================================
# Connection Pool Tests
# ============================================================================


@pytest.mark.asyncio
async def test_pool_initialization(db_config):
    """Test database pool initialization."""
    pool = DatabasePool(**db_config)
    await pool.initialize()

    assert pool.is_initialized
    assert pool.pool is not None

    # Test health check
    health = await pool.health_check()
    assert health["healthy"]
    assert health["latency_ms"] < 100  # Should be fast for local

    await pool.close()
    assert not pool.is_initialized


@pytest.mark.asyncio
async def test_pool_concurrent_connections(pool):
    """Test connection pool with 50 concurrent queries."""

    async def query_task(i: int):
        result = await pool.fetchval("SELECT $1", i)
        return result

    # Run 50 concurrent queries
    tasks = [query_task(i) for i in range(50)]
    results = await asyncio.gather(*tasks)

    assert len(results) == 50
    assert results == list(range(50))


@pytest.mark.asyncio
async def test_pool_health_check(pool):
    """Test health check functionality."""
    health = await pool.health_check()

    assert health["healthy"]
    assert "latency_ms" in health
    assert "pool_size" in health
    assert "pool_free" in health
    assert health["latency_ms"] < 100


# ============================================================================
# Table Creation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_all_tables_exist(pool):
    """Test that all 11 tables exist."""
    expected_tables = [
        "positions",
        "trading_signals",
        "orders",
        "market_data",
        "daily_performance",
        "risk_events",
        "llm_requests",
        "system_config",
        "audit_log",
        "circuit_breaker_state",
        "position_reconciliation",
    ]

    for table in expected_tables:
        exists = await pool.fetchval(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = $1)",
            table,
        )
        assert exists, f"Table {table} does not exist"


@pytest.mark.asyncio
async def test_timescaledb_hypertables(pool):
    """Test that TimescaleDB hypertables are created."""
    hypertables = ["market_data", "daily_performance", "risk_events"]

    for table in hypertables:
        is_hypertable = await pool.fetchval(
            "SELECT COUNT(*) FROM timescaledb_information.hypertables WHERE hypertable_name = $1",
            table,
        )
        assert is_hypertable > 0, f"Table {table} is not a hypertable"


@pytest.mark.asyncio
async def test_indexes_exist(pool):
    """Test that critical indexes exist."""
    # Check a few critical indexes
    critical_indexes = [
        ("positions", "idx_positions_symbol"),
        ("positions", "idx_positions_status"),
        ("trading_signals", "idx_trading_signals_symbol"),
        ("orders", "idx_orders_position_id"),
        ("market_data", "idx_market_data_symbol_timestamp"),
    ]

    for table, index in critical_indexes:
        exists = await pool.fetchval(
            """
            SELECT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE tablename = $1 AND indexname = $2
            )
            """,
            table,
            index,
        )
        assert exists, f"Index {index} on {table} does not exist"


# ============================================================================
# Position Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_position(pool):
    """Test position creation with CHF amounts."""
    position = Position(
        symbol="BTCUSDT",
        side=PositionSide.LONG,
        quantity=Decimal("0.01"),
        entry_price=Decimal("45000.00"),
        current_price=Decimal("46000.00"),
        leverage=10,
        stop_loss=Decimal("44000.00"),
        take_profit=Decimal("47000.00"),
    )

    await pool.execute(
        """
        INSERT INTO positions (id, symbol, side, quantity, entry_price, current_price,
                              leverage, stop_loss, take_profit, status)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """,
        position.id,
        position.symbol,
        position.side.value,
        position.quantity,
        position.entry_price,
        position.current_price,
        position.leverage,
        position.stop_loss,
        position.take_profit,
        position.status.value,
    )

    # Verify insertion
    row = await pool.fetchrow("SELECT * FROM positions WHERE id = $1", position.id)
    assert row is not None
    assert row["symbol"] == "BTCUSDT"
    assert row["side"] == "LONG"
    assert row["leverage"] == 10


@pytest.mark.asyncio
async def test_position_unrealized_pnl(pool):
    """Test position unrealized P&L calculation."""
    # LONG position with profit
    long_position = Position(
        symbol="BTCUSDT",
        side=PositionSide.LONG,
        quantity=Decimal("0.1"),
        entry_price=Decimal("40000.00"),
        current_price=Decimal("41000.00"),
        leverage=10,
    )

    pnl = long_position.calculate_unrealized_pnl_usd()
    expected_pnl = (Decimal("41000") - Decimal("40000")) * Decimal("0.1") * 10
    assert pnl == expected_pnl

    # SHORT position with profit
    short_position = Position(
        symbol="ETHUSDT",
        side=PositionSide.SHORT,
        quantity=Decimal("1.0"),
        entry_price=Decimal("3000.00"),
        current_price=Decimal("2900.00"),
        leverage=5,
    )

    pnl = short_position.calculate_unrealized_pnl_usd()
    expected_pnl = (Decimal("3000") - Decimal("2900")) * Decimal("1.0") * 5
    assert pnl == expected_pnl


@pytest.mark.asyncio
async def test_position_constraints(pool):
    """Test position constraints (leverage range, valid side, etc.)."""

    # Test invalid leverage (too high)
    with pytest.raises(asyncpg.CheckViolationError):
        await pool.execute(
            """
            INSERT INTO positions (symbol, side, quantity, entry_price, leverage)
            VALUES ($1, $2, $3, $4, $5)
            """,
            "BTCUSDT",
            "LONG",
            Decimal("0.1"),
            Decimal("45000"),
            50,  # Invalid: > 40
        )

    # Test invalid side
    with pytest.raises(asyncpg.CheckViolationError):
        await pool.execute(
            """
            INSERT INTO positions (symbol, side, quantity, entry_price, leverage)
            VALUES ($1, $2, $3, $4, $5)
            """,
            "BTCUSDT",
            "MIDDLE",
            Decimal("0.1"),
            Decimal("45000"),
            10,
        )


# ============================================================================
# Trading Signal Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_trading_signal(pool):
    """Test trading signal creation with LLM data."""
    signal = TradingSignal(
        symbol="BTCUSDT",
        signal_type=SignalType.ENTRY,
        action=SignalAction.BUY,
        confidence=Decimal("0.8500"),
        risk_usd=Decimal("100.00"),
        reasoning="Strong bullish momentum with RSI oversold",
        llm_model="anthropic/claude-3.5-sonnet",
        llm_tokens=1500,
        llm_cost_usd=Decimal("0.015"),
    )

    await pool.execute(
        """
        INSERT INTO trading_signals (id, symbol, signal_type, action, confidence,
                                     risk_usd, reasoning, llm_model, llm_tokens, llm_cost_usd)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """,
        signal.id,
        signal.symbol,
        signal.signal_type.value,
        signal.action.value,
        signal.confidence,
        signal.risk_usd,
        signal.reasoning,
        signal.llm_model,
        signal.llm_tokens,
        signal.llm_cost_usd,
    )

    # Verify
    row = await pool.fetchrow("SELECT * FROM trading_signals WHERE id = $1", signal.id)
    assert row is not None
    assert row["confidence"] == Decimal("0.8500")
    assert row["executed"] is False


# ============================================================================
# Order Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_order_with_position(pool):
    """Test order creation with foreign key to position."""
    # Create position first
    position_id = uuid4()
    await pool.execute(
        """
        INSERT INTO positions (id, symbol, side, quantity, entry_price, leverage)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        position_id,
        "BTCUSDT",
        "LONG",
        Decimal("0.1"),
        Decimal("45000"),
        10,
    )

    # Create order
    order = Order(
        position_id=position_id,
        exchange_order_id="BYBIT-12345",
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=Decimal("0.1"),
        filled_quantity=Decimal("0.1"),
        status=OrderStatus.FILLED,
        fee_chf=Decimal("5.00"),
    )

    await pool.execute(
        """
        INSERT INTO orders (id, position_id, exchange_order_id, symbol, side, order_type,
                           quantity, filled_quantity, status, fee_chf)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """,
        order.id,
        order.position_id,
        order.exchange_order_id,
        order.symbol,
        order.side.value,
        order.order_type.value,
        order.quantity,
        order.filled_quantity,
        order.status.value,
        order.fee_chf,
    )

    # Verify foreign key relationship
    row = await pool.fetchrow("SELECT * FROM orders WHERE id = $1", order.id)
    assert row["position_id"] == position_id


@pytest.mark.asyncio
async def test_order_cascade_delete(pool):
    """Test that orders are deleted when position is deleted (CASCADE)."""
    # Create position and order
    position_id = uuid4()
    await pool.execute(
        """
        INSERT INTO positions (id, symbol, side, quantity, entry_price, leverage)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        position_id,
        "BTCUSDT",
        "LONG",
        Decimal("0.1"),
        Decimal("45000"),
        10,
    )

    order_id = uuid4()
    await pool.execute(
        """
        INSERT INTO orders (id, position_id, symbol, side, order_type, quantity)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        order_id,
        position_id,
        "BTCUSDT",
        "BUY",
        "MARKET",
        Decimal("0.1"),
    )

    # Delete position
    await pool.execute("DELETE FROM positions WHERE id = $1", position_id)

    # Verify order was also deleted
    order_exists = await pool.fetchval(
        "SELECT EXISTS(SELECT 1 FROM orders WHERE id = $1)", order_id
    )
    assert not order_exists


# ============================================================================
# Market Data (TimescaleDB) Tests
# ============================================================================


@pytest.mark.asyncio
async def test_market_data_hypertable_insert(pool):
    """Test TimescaleDB hypertable insert and query."""
    # Insert market data
    now = datetime_to_microseconds(datetime.utcnow())

    data = MarketData(
        symbol="BTCUSDT",
        timestamp=now,
        open=Decimal("45000.00"),
        high=Decimal("45500.00"),
        low=Decimal("44800.00"),
        close=Decimal("45200.00"),
        volume=Decimal("1000.5"),
        indicators={"rsi": 55.5, "macd": 120.3},
    )

    await pool.execute(
        """
        INSERT INTO market_data (symbol, timestamp, open, high, low, close, volume, indicators)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """,
        data.symbol,
        data.timestamp,
        data.open,
        data.high,
        data.low,
        data.close,
        data.volume,
        data.indicators,
    )

    # Query back
    row = await pool.fetchrow(
        "SELECT * FROM market_data WHERE symbol = $1 AND timestamp = $2",
        data.symbol,
        data.timestamp,
    )
    assert row is not None
    assert row["close"] == Decimal("45200.00")
    assert row["indicators"]["rsi"] == 55.5


@pytest.mark.asyncio
async def test_market_data_ohlc_constraint(pool):
    """Test OHLC validation constraint."""
    now = datetime_to_microseconds(datetime.utcnow())

    # Invalid: high < low
    with pytest.raises(asyncpg.CheckViolationError):
        await pool.execute(
            """
            INSERT INTO market_data (symbol, timestamp, open, high, low, close, volume)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            "BTCUSDT",
            now,
            Decimal("45000"),
            Decimal("44000"),
            Decimal("45000"),
            Decimal("44500"),
            Decimal("100"),
        )


# ============================================================================
# Circuit Breaker Tests
# ============================================================================


@pytest.mark.asyncio
async def test_circuit_breaker_tracking(pool):
    """Test daily P&L tracking for circuit breaker."""
    today = date.today()

    # Insert circuit breaker state
    cb = CircuitBreakerState(
        date=today, current_pnl_chf=Decimal("-150.00"), triggered=False
    )

    await pool.execute(
        """
        INSERT INTO circuit_breaker_state (date, current_pnl_chf, triggered)
        VALUES ($1, $2, $3)
        """,
        cb.date,
        cb.current_pnl_chf,
        cb.triggered,
    )

    # Test should_trigger
    assert not cb.should_trigger()

    # Update to trigger threshold
    cb.current_pnl_chf = Decimal("-185.00")
    assert cb.should_trigger()  # Should trigger at -183.89


@pytest.mark.asyncio
async def test_circuit_breaker_function(pool):
    """Test get_circuit_breaker_status() function."""
    # Test with no data (should return defaults)
    row = await pool.fetchrow("SELECT * FROM get_circuit_breaker_status()")
    assert row["is_triggered"] is False
    assert row["current_pnl_chf"] == Decimal("0")
    assert row["threshold_chf"] == Decimal("-183.89")

    # Insert triggered state
    today = date.today()
    await pool.execute(
        """
        INSERT INTO circuit_breaker_state (date, current_pnl_chf, triggered, trigger_reason)
        VALUES ($1, $2, $3, $4)
        """,
        today,
        Decimal("-200.00"),
        True,
        "Daily loss exceeded -7%",
    )

    # Test function returns triggered state
    row = await pool.fetchrow("SELECT * FROM get_circuit_breaker_status()")
    assert row["is_triggered"] is True
    assert row["current_pnl_chf"] == Decimal("-200.00")


# ============================================================================
# Performance Tests
# ============================================================================


@pytest.mark.asyncio
async def test_query_performance(pool):
    """Test that all queries execute in <10ms."""
    # Insert test data
    position_id = uuid4()
    await pool.execute(
        """
        INSERT INTO positions (id, symbol, side, quantity, entry_price, leverage, status)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        """,
        position_id,
        "BTCUSDT",
        "LONG",
        Decimal("0.1"),
        Decimal("45000"),
        10,
        "OPEN",
    )

    # Test queries
    queries = [
        ("SELECT * FROM positions WHERE status = 'OPEN'", []),
        ("SELECT * FROM positions WHERE symbol = $1", ["BTCUSDT"]),
        ("SELECT * FROM positions WHERE id = $1", [position_id]),
        ("SELECT COUNT(*) FROM positions", []),
    ]

    for query, args in queries:
        start = time.perf_counter()
        await pool.fetch(query, *args)
        duration_ms = (time.perf_counter() - start) * 1000
        assert duration_ms < 10, f"Query took {duration_ms:.2f}ms (expected < 10ms)"


@pytest.mark.asyncio
async def test_bulk_insert_performance(pool):
    """Test bulk insert performance."""
    # Insert 1000 market data points
    now = datetime_to_microseconds(datetime.utcnow())

    start = time.perf_counter()

    for i in range(1000):
        await pool.execute(
            """
            INSERT INTO market_data (symbol, timestamp, open, high, low, close, volume)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            "BTCUSDT",
            now + i,
            Decimal("45000"),
            Decimal("45100"),
            Decimal("44900"),
            Decimal("45000"),
            Decimal("100"),
        )

    duration = time.perf_counter() - start
    print(f"\nInserted 1000 rows in {duration:.2f}s ({1000 / duration:.0f} rows/sec)")

    # Should be reasonably fast
    assert duration < 5.0, f"Bulk insert too slow: {duration:.2f}s"


# ============================================================================
# View Tests
# ============================================================================


@pytest.mark.asyncio
async def test_open_positions_view(pool):
    """Test v_open_positions view."""
    # Insert open position
    await pool.execute(
        """
        INSERT INTO positions (symbol, side, quantity, entry_price, current_price, leverage, status)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        """,
        "BTCUSDT",
        "LONG",
        Decimal("0.1"),
        Decimal("45000"),
        Decimal("46000"),
        10,
        "OPEN",
    )

    # Query view
    rows = await pool.fetch("SELECT * FROM v_open_positions")
    assert len(rows) == 1
    assert rows[0]["symbol"] == "BTCUSDT"
    assert rows[0]["unrealized_pnl_usd"] > 0  # Should have profit


@pytest.mark.asyncio
async def test_portfolio_summary_view(pool):
    """Test v_portfolio_summary view."""
    # Insert some positions
    await pool.execute(
        """
        INSERT INTO positions (symbol, side, quantity, entry_price, leverage, status, pnl_chf)
        VALUES
            ('BTCUSDT', 'LONG', 0.1, 45000, 10, 'CLOSED', 100.50),
            ('ETHUSDT', 'SHORT', 1.0, 3000, 5, 'CLOSED', -50.25),
            ('BNBUSDT', 'LONG', 2.0, 400, 10, 'OPEN', NULL)
        """
    )

    # Query view
    row = await pool.fetchrow("SELECT * FROM v_portfolio_summary")
    assert row["open_positions"] == 1
    assert row["closed_positions"] == 2
    assert row["winning_trades"] == 1
    assert row["losing_trades"] == 1


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
