# PRP: Database Setup Implementation

## Metadata
- **PRP Type**: Implementation
- **Feature**: Database Infrastructure
- **Priority**: Critical (Foundation)
- **Estimated Effort**: 13 story points
- **Dependencies**: None (First component)
- **Target Directory**: workspace/features/database/

## Context

### Business Requirements
Establish a robust, scalable database foundation for the trading system that can handle high-frequency data ingestion, maintain data integrity, and provide fast query performance for real-time trading decisions.

### Technical Context
- **Primary Database**: PostgreSQL 15+ with TimescaleDB extension
- **Time-Series Data**: TimescaleDB hypertables for OHLCV and metrics
- **Connection Pooling**: asyncpg with 10-50 connections
- **Migrations**: Alembic for schema versioning
- **Backup Strategy**: Daily automated backups with point-in-time recovery

### From Architecture Document
```sql
-- Core schema requirements from PRPs/architecture/database-schema.md
- positions table with state tracking
- orders table with status management
- market_data hypertable (3-minute candles)
- trading_signals with LLM responses
- performance_metrics time-series
- system_logs for audit trail
```

## Implementation Requirements

### 1. Database Installation and Configuration

**File**: `workspace/features/database/setup.sql`

```sql
-- PostgreSQL 15+ with TimescaleDB setup script

-- Create database
CREATE DATABASE llm_trading_system
    WITH
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TABLESPACE = pg_default
    CONNECTION LIMIT = 100;

-- Connect to database
\c llm_trading_system;

-- Install extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";      -- UUID generation
CREATE EXTENSION IF NOT EXISTS "timescaledb";    -- Time-series data
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements"; -- Query performance
CREATE EXTENSION IF NOT EXISTS "pgcrypto";       -- Encryption for sensitive data

-- Configure TimescaleDB
SELECT timescaledb_post_restore();

-- Create schemas for logical separation
CREATE SCHEMA IF NOT EXISTS trading;
CREATE SCHEMA IF NOT EXISTS market;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS audit;

-- Set search path
SET search_path TO trading, market, analytics, audit, public;

-- Performance tuning settings
ALTER SYSTEM SET shared_buffers = '2GB';
ALTER SYSTEM SET effective_cache_size = '6GB';
ALTER SYSTEM SET maintenance_work_mem = '512MB';
ALTER SYSTEM SET work_mem = '64MB';
ALTER SYSTEM SET max_connections = 100;
ALTER SYSTEM SET max_parallel_workers_per_gather = 4;
ALTER SYSTEM SET max_parallel_workers = 8;
ALTER SYSTEM SET random_page_cost = 1.1;  -- SSD optimized

-- Apply settings
SELECT pg_reload_conf();
```

### 2. Core Schema Implementation

**File**: `workspace/features/database/migrations/001_initial_schema.sql`

```sql
-- Initial schema migration
-- Version: 001
-- Date: 2024-10-27

-- ============================================
-- Trading Schema
-- ============================================

-- Positions table (core state tracking)
CREATE TABLE trading.positions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(20) NOT NULL,
    exchange VARCHAR(50) NOT NULL DEFAULT 'bybit',

    -- Position details
    side VARCHAR(10) NOT NULL CHECK (side IN ('long', 'short')),
    status VARCHAR(20) NOT NULL DEFAULT 'open'
        CHECK (status IN ('pending', 'open', 'closing', 'closed', 'error')),

    -- Quantities and prices
    quantity DECIMAL(20, 8) NOT NULL CHECK (quantity > 0),
    entry_price DECIMAL(20, 8) NOT NULL CHECK (entry_price > 0),
    exit_price DECIMAL(20, 8),
    average_entry_price DECIMAL(20, 8),

    -- Risk management
    stop_loss_price DECIMAL(20, 8),
    take_profit_price DECIMAL(20, 8),
    trailing_stop_distance DECIMAL(20, 8),
    liquidation_price DECIMAL(20, 8),

    -- P&L tracking
    unrealized_pnl DECIMAL(20, 8) DEFAULT 0,
    realized_pnl DECIMAL(20, 8) DEFAULT 0,
    fees DECIMAL(20, 8) DEFAULT 0,
    funding_fees DECIMAL(20, 8) DEFAULT 0,

    -- Metadata
    leverage INTEGER DEFAULT 1 CHECK (leverage BETWEEN 1 AND 20),
    margin_used DECIMAL(20, 8),
    position_value DECIMAL(20, 8),

    -- Decision tracking
    signal_id UUID REFERENCES trading.trading_signals(id),
    strategy_name VARCHAR(100),

    -- Timestamps
    opened_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMP WITH TIME ZONE,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_exit_price CHECK (
        (status = 'closed' AND exit_price IS NOT NULL) OR
        (status != 'closed')
    ),
    CONSTRAINT valid_pnl CHECK (
        (status = 'closed' AND realized_pnl IS NOT NULL) OR
        (status != 'closed')
    )
);

-- Indexes for positions
CREATE INDEX idx_positions_status ON trading.positions(status) WHERE status = 'open';
CREATE INDEX idx_positions_symbol ON trading.positions(symbol);
CREATE INDEX idx_positions_opened_at ON trading.positions(opened_at DESC);
CREATE INDEX idx_positions_signal ON trading.positions(signal_id);

-- Orders table
CREATE TABLE trading.orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    position_id UUID REFERENCES trading.positions(id),
    exchange_order_id VARCHAR(100) UNIQUE,

    -- Order details
    symbol VARCHAR(20) NOT NULL,
    order_type VARCHAR(20) NOT NULL
        CHECK (order_type IN ('market', 'limit', 'stop_market', 'stop_limit', 'trailing_stop')),
    side VARCHAR(10) NOT NULL CHECK (side IN ('buy', 'sell')),
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'submitted', 'partial', 'filled', 'cancelled', 'rejected', 'expired')),

    -- Quantities and prices
    quantity DECIMAL(20, 8) NOT NULL CHECK (quantity > 0),
    filled_quantity DECIMAL(20, 8) DEFAULT 0,
    price DECIMAL(20, 8),  -- NULL for market orders
    average_fill_price DECIMAL(20, 8),
    stop_price DECIMAL(20, 8),  -- For stop orders

    -- Execution tracking
    time_in_force VARCHAR(10) DEFAULT 'IOC'
        CHECK (time_in_force IN ('IOC', 'FOK', 'GTC', 'GTD')),
    reduce_only BOOLEAN DEFAULT FALSE,
    close_position BOOLEAN DEFAULT FALSE,

    -- Fees and costs
    fees DECIMAL(20, 8) DEFAULT 0,
    fee_currency VARCHAR(10) DEFAULT 'USDT',

    -- Retry tracking
    retry_count INTEGER DEFAULT 0,
    last_error TEXT,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    submitted_at TIMESTAMP WITH TIME ZONE,
    filled_at TIMESTAMP WITH TIME ZONE,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,

    -- Constraints
    CONSTRAINT valid_fill CHECK (filled_quantity <= quantity),
    CONSTRAINT valid_limit_price CHECK (
        (order_type IN ('limit', 'stop_limit') AND price IS NOT NULL) OR
        (order_type NOT IN ('limit', 'stop_limit'))
    )
);

-- Indexes for orders
CREATE INDEX idx_orders_status ON trading.orders(status);
CREATE INDEX idx_orders_position ON trading.orders(position_id);
CREATE INDEX idx_orders_created ON trading.orders(created_at DESC);
CREATE INDEX idx_orders_exchange_id ON trading.orders(exchange_order_id);

-- Trading signals table
CREATE TABLE trading.trading_signals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Signal details
    symbol VARCHAR(20) NOT NULL,
    signal_type VARCHAR(20) NOT NULL
        CHECK (signal_type IN ('entry_long', 'entry_short', 'exit', 'hold', 'scale_in', 'scale_out')),
    confidence DECIMAL(5, 4) CHECK (confidence BETWEEN 0 AND 1),
    strength VARCHAR(10) CHECK (strength IN ('weak', 'moderate', 'strong')),

    -- LLM details
    llm_provider VARCHAR(50) NOT NULL,
    llm_model VARCHAR(100) NOT NULL,
    prompt_template VARCHAR(100),

    -- Market context (snapshot at signal time)
    price_at_signal DECIMAL(20, 8),
    volume_24h DECIMAL(20, 8),
    volatility DECIMAL(10, 6),
    market_sentiment VARCHAR(20),

    -- Technical indicators at signal
    indicators JSONB,  -- Store all indicator values

    -- LLM response
    llm_response JSONB NOT NULL,  -- Full response
    llm_reasoning TEXT,  -- Extracted reasoning
    token_usage INTEGER,
    response_time_ms INTEGER,

    -- Position sizing
    recommended_size DECIMAL(20, 8),
    recommended_leverage INTEGER,
    stop_loss_price DECIMAL(20, 8),
    take_profit_price DECIMAL(20, 8),

    -- Risk assessment
    risk_score DECIMAL(5, 4),
    max_drawdown_expected DECIMAL(10, 4),

    -- Execution status
    executed BOOLEAN DEFAULT FALSE,
    execution_price DECIMAL(20, 8),
    execution_time TIMESTAMP WITH TIME ZONE,
    skip_reason TEXT,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Metadata
    cycle_id VARCHAR(100),  -- Links to trading cycle
    session_id UUID  -- Trading session identifier
);

-- Indexes for signals
CREATE INDEX idx_signals_symbol ON trading.trading_signals(symbol);
CREATE INDEX idx_signals_created ON trading.trading_signals(created_at DESC);
CREATE INDEX idx_signals_executed ON trading.trading_signals(executed);
CREATE INDEX idx_signals_cycle ON trading.trading_signals(cycle_id);

-- ============================================
-- Market Schema
-- ============================================

-- Market data (3-minute candles)
CREATE TABLE market.ohlcv (
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL DEFAULT '3m',

    -- OHLCV data
    open_time TIMESTAMP WITH TIME ZONE NOT NULL,
    close_time TIMESTAMP WITH TIME ZONE NOT NULL,
    open DECIMAL(20, 8) NOT NULL,
    high DECIMAL(20, 8) NOT NULL,
    low DECIMAL(20, 8) NOT NULL,
    close DECIMAL(20, 8) NOT NULL,
    volume DECIMAL(20, 8) NOT NULL,

    -- Additional metrics
    trades_count INTEGER,
    taker_buy_volume DECIMAL(20, 8),
    quote_volume DECIMAL(20, 8),

    -- Technical indicators (calculated)
    sma_20 DECIMAL(20, 8),
    sma_50 DECIMAL(20, 8),
    ema_12 DECIMAL(20, 8),
    ema_26 DECIMAL(20, 8),
    rsi_14 DECIMAL(10, 4),
    macd DECIMAL(20, 8),
    macd_signal DECIMAL(20, 8),
    bollinger_upper DECIMAL(20, 8),
    bollinger_lower DECIMAL(20, 8),
    atr_14 DECIMAL(20, 8),

    -- Data source
    source VARCHAR(20) DEFAULT 'bybit',
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    PRIMARY KEY (symbol, timeframe, open_time)
);

-- Convert to TimescaleDB hypertable
SELECT create_hypertable('market.ohlcv', 'open_time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Create continuous aggregate for 15m candles
CREATE MATERIALIZED VIEW market.ohlcv_15m
WITH (timescaledb.continuous) AS
SELECT
    symbol,
    '15m' as timeframe,
    time_bucket('15 minutes', open_time) as open_time,
    first(open, open_time) as open,
    max(high) as high,
    min(low) as low,
    last(close, open_time) as close,
    sum(volume) as volume,
    sum(trades_count) as trades_count,
    avg(rsi_14) as rsi_14
FROM market.ohlcv
WHERE timeframe = '3m'
GROUP BY symbol, time_bucket('15 minutes', open_time);

-- ============================================
-- Analytics Schema
-- ============================================

-- Performance metrics
CREATE TABLE analytics.performance_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Time window
    metric_date DATE NOT NULL,
    metric_hour INTEGER CHECK (metric_hour BETWEEN 0 AND 23),

    -- P&L metrics
    gross_pnl DECIMAL(20, 8) DEFAULT 0,
    net_pnl DECIMAL(20, 8) DEFAULT 0,
    fees_paid DECIMAL(20, 8) DEFAULT 0,

    -- Trading metrics
    trades_count INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    win_rate DECIMAL(5, 4),

    -- Risk metrics
    max_drawdown DECIMAL(20, 8),
    sharpe_ratio DECIMAL(10, 4),
    sortino_ratio DECIMAL(10, 4),
    calmar_ratio DECIMAL(10, 4),

    -- Position metrics
    avg_position_duration INTERVAL,
    avg_position_size DECIMAL(20, 8),
    total_volume DECIMAL(20, 8),

    -- LLM metrics
    llm_requests_count INTEGER DEFAULT 0,
    llm_tokens_used INTEGER DEFAULT 0,
    llm_cost_usd DECIMAL(10, 4) DEFAULT 0,
    avg_response_time_ms INTEGER,

    -- System metrics
    cycles_executed INTEGER DEFAULT 0,
    cycles_skipped INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0,

    -- Account metrics
    account_balance DECIMAL(20, 8),
    account_equity DECIMAL(20, 8),
    margin_used DECIMAL(20, 8),
    free_margin DECIMAL(20, 8),

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(metric_date, metric_hour)
);

-- Convert to hypertable
SELECT create_hypertable('analytics.performance_metrics', 'metric_date',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

-- ============================================
-- Audit Schema
-- ============================================

-- System logs for audit trail
CREATE TABLE audit.system_logs (
    id BIGSERIAL PRIMARY KEY,
    log_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Log details
    log_level VARCHAR(10) NOT NULL
        CHECK (log_level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')),
    component VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,

    -- Context
    user_id UUID,
    session_id UUID,
    cycle_id VARCHAR(100),

    -- Additional data
    metadata JSONB,
    error_details JSONB,

    -- Request tracking
    request_id UUID,
    correlation_id UUID
);

-- Convert to hypertable
SELECT create_hypertable('audit.system_logs', 'log_time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Create index for fast queries
CREATE INDEX idx_logs_level ON audit.system_logs(log_level) WHERE log_level IN ('ERROR', 'CRITICAL');
CREATE INDEX idx_logs_component ON audit.system_logs(component, log_time DESC);

-- ============================================
-- Helper Functions
-- ============================================

-- Function to calculate position P&L
CREATE OR REPLACE FUNCTION trading.calculate_pnl(
    p_side VARCHAR,
    p_entry_price DECIMAL,
    p_exit_price DECIMAL,
    p_quantity DECIMAL
) RETURNS DECIMAL AS $$
BEGIN
    IF p_side = 'long' THEN
        RETURN (p_exit_price - p_entry_price) * p_quantity;
    ELSE
        RETURN (p_entry_price - p_exit_price) * p_quantity;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update position P&L
CREATE OR REPLACE FUNCTION trading.update_position_pnl()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'closed' AND NEW.exit_price IS NOT NULL THEN
        NEW.realized_pnl = trading.calculate_pnl(
            NEW.side,
            NEW.entry_price,
            NEW.exit_price,
            NEW.quantity
        ) - NEW.fees - NEW.funding_fees;
    END IF;

    NEW.last_updated = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_position_pnl
BEFORE UPDATE ON trading.positions
FOR EACH ROW
EXECUTE FUNCTION trading.update_position_pnl();

-- ============================================
-- Data Retention Policies
-- ============================================

-- Retention policy for market data (keep 30 days of 3m candles)
SELECT add_retention_policy('market.ohlcv', INTERVAL '30 days',
    if_not_exists => TRUE);

-- Retention policy for logs (keep 7 days)
SELECT add_retention_policy('audit.system_logs', INTERVAL '7 days',
    if_not_exists => TRUE);

-- Compression policy for older data
SELECT add_compression_policy('market.ohlcv', INTERVAL '1 day',
    if_not_exists => TRUE);

SELECT add_compression_policy('analytics.performance_metrics', INTERVAL '7 days',
    if_not_exists => TRUE);
```

### 3. Database Connection Manager

**File**: `workspace/features/database/connection.py`

```python
import asyncio
import asyncpg
from asyncpg.pool import Pool
from typing import Optional, Dict, Any
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class DatabaseConnection:
    """
    Manages PostgreSQL connection pool with automatic retry and health checks.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.pool: Optional[Pool] = None
        self._health_check_task: Optional[asyncio.Task] = None

    async def initialize(self) -> None:
        """
        Initialize the connection pool.
        """
        try:
            self.pool = await asyncpg.create_pool(
                host=self.config['host'],
                port=self.config['port'],
                database=self.config['database'],
                user=self.config['user'],
                password=self.config['password'],

                # Pool configuration
                min_size=10,  # Minimum connections
                max_size=50,  # Maximum connections

                # Connection parameters
                command_timeout=60,
                server_settings={
                    'application_name': 'llm_trading_system',
                    'jit': 'off'
                },

                # Retry configuration
                connection_attempts=3,
                connection_retry_delay=1.0,
            )

            # Verify connection
            async with self.pool.acquire() as conn:
                version = await conn.fetchval('SELECT version()')
                logger.info(f"Connected to PostgreSQL: {version}")

            # Start health check task
            self._health_check_task = asyncio.create_task(
                self._periodic_health_check()
            )

        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise

    async def _periodic_health_check(self) -> None:
        """
        Periodically check database health.
        """
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds

                async with self.pool.acquire() as conn:
                    await conn.fetchval('SELECT 1')

                    # Check pool stats
                    stats = self.pool.get_stats()
                    logger.debug(
                        f"Pool stats - Size: {stats['size']}, "
                        f"Free: {stats['free_size']}, "
                        f"Used: {stats['used_size']}"
                    )

            except Exception as e:
                logger.error(f"Health check failed: {e}")

    @asynccontextmanager
    async def acquire(self):
        """
        Acquire a connection from the pool.
        """
        async with self.pool.acquire() as connection:
            yield connection

    async def execute(self, query: str, *args) -> str:
        """
        Execute a query that doesn't return results.
        """
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args) -> list:
        """
        Execute a query and fetch all results.
        """
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args) -> Optional[asyncpg.Record]:
        """
        Execute a query and fetch a single row.
        """
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchval(self, query: str, *args) -> Any:
        """
        Execute a query and fetch a single value.
        """
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    async def close(self) -> None:
        """
        Close the connection pool.
        """
        if self._health_check_task:
            self._health_check_task.cancel()

        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")
```

### 4. Migration Manager

**File**: `workspace/features/database/migrations.py`

```python
import os
import asyncio
import asyncpg
from pathlib import Path
from typing import List, Optional
import hashlib
from datetime import datetime

class MigrationManager:
    """
    Manages database schema migrations.
    """

    def __init__(self, connection: DatabaseConnection):
        self.conn = connection
        self.migrations_dir = Path("workspace/features/database/migrations")

    async def initialize_migrations_table(self) -> None:
        """
        Create migrations tracking table.
        """
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id SERIAL PRIMARY KEY,
                version VARCHAR(255) UNIQUE NOT NULL,
                name VARCHAR(255) NOT NULL,
                checksum VARCHAR(64) NOT NULL,
                executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                execution_time_ms INTEGER
            );
        """)

    async def get_applied_migrations(self) -> List[str]:
        """
        Get list of applied migration versions.
        """
        rows = await self.conn.fetch(
            "SELECT version FROM schema_migrations ORDER BY id"
        )
        return [row['version'] for row in rows]

    async def apply_migration(self, migration_file: Path) -> None:
        """
        Apply a single migration.
        """
        version = migration_file.stem  # e.g., "001_initial_schema"

        # Check if already applied
        applied = await self.get_applied_migrations()
        if version in applied:
            logger.info(f"Migration {version} already applied")
            return

        # Read migration content
        content = migration_file.read_text()
        checksum = hashlib.sha256(content.encode()).hexdigest()

        # Apply migration
        start_time = datetime.now()

        try:
            async with self.conn.acquire() as conn:
                async with conn.transaction():
                    # Execute migration
                    await conn.execute(content)

                    # Record migration
                    execution_time = int(
                        (datetime.now() - start_time).total_seconds() * 1000
                    )

                    await conn.execute("""
                        INSERT INTO schema_migrations
                        (version, name, checksum, execution_time_ms)
                        VALUES ($1, $2, $3, $4)
                    """, version, migration_file.name, checksum, execution_time)

            logger.info(
                f"Applied migration {version} in {execution_time}ms"
            )

        except Exception as e:
            logger.error(f"Failed to apply migration {version}: {e}")
            raise

    async def run_migrations(self) -> None:
        """
        Run all pending migrations.
        """
        await self.initialize_migrations_table()

        # Get all migration files
        migration_files = sorted(
            self.migrations_dir.glob("*.sql")
        )

        for migration_file in migration_files:
            await self.apply_migration(migration_file)

        logger.info("All migrations completed successfully")
```

## Validation Requirements

### Level 1: Unit Tests
```python
# Tests for workspace/features/database/tests/test_connection.py

async def test_connection_pool_creation():
    """Test database connection pool initialization."""
    config = load_test_config()
    db = DatabaseConnection(config)
    await db.initialize()
    assert db.pool is not None
    assert db.pool.get_stats()['size'] >= 10

async def test_query_execution():
    """Test basic query execution."""
    db = await get_test_db()
    result = await db.fetchval("SELECT 1 + 1")
    assert result == 2

async def test_transaction_rollback():
    """Test transaction rollback on error."""
    db = await get_test_db()
    async with db.acquire() as conn:
        async with conn.transaction():
            await conn.execute("INSERT INTO test_table VALUES (1)")
            # This should cause rollback
            raise Exception("Test error")
    # Verify no data was inserted
    count = await db.fetchval("SELECT COUNT(*) FROM test_table")
    assert count == 0
```

### Level 2: Integration Tests
```python
# Tests for workspace/features/database/tests/test_schema.py

async def test_schema_creation():
    """Test complete schema creation."""
    manager = MigrationManager(test_db)
    await manager.run_migrations()

    # Verify all tables exist
    tables = await test_db.fetch("""
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_schema IN ('trading', 'market', 'analytics', 'audit')
    """)

    assert len(tables) >= 7  # Minimum expected tables

async def test_hypertable_creation():
    """Test TimescaleDB hypertable creation."""
    result = await test_db.fetchrow("""
        SELECT * FROM timescaledb_information.hypertables
        WHERE hypertable_name = 'ohlcv'
    """)
    assert result is not None
```

### Level 3: Performance Tests
- Connection pool under load (100 concurrent queries)
- Query performance benchmarks
- Index effectiveness tests
- Hypertable compression validation

## Acceptance Criteria

### Must Have
- [x] PostgreSQL 15+ with TimescaleDB installed
- [x] All schema tables created
- [x] Connection pooling working (10-50 connections)
- [x] Migrations system functional
- [x] Hypertables configured for time-series data
- [x] Indexes optimized for query patterns
- [x] Triggers for automatic updates

### Should Have
- [x] Continuous aggregates for candle data
- [x] Retention policies configured
- [x] Compression policies active
- [x] Health check monitoring
- [x] Query performance monitoring

## Implementation Notes

### Critical Considerations
1. **Connection Pooling**: Never exceed 50 connections (leave room for maintenance)
2. **Transactions**: Use explicit transactions for multi-statement operations
3. **Prepared Statements**: Use parameterized queries to prevent SQL injection
4. **Timezone Handling**: Always use TIMESTAMP WITH TIME ZONE
5. **Decimal Precision**: Use DECIMAL(20, 8) for prices and quantities

### Performance Optimizations
1. **Partitioning**: TimescaleDB auto-partitions by time
2. **Indexes**: Created on frequently queried columns
3. **Continuous Aggregates**: Pre-calculate 15m candles
4. **Compression**: Older data automatically compressed
5. **Connection Reuse**: Pool maintains persistent connections

## Testing Checklist

- [ ] Schema creates successfully
- [ ] All constraints enforced
- [ ] Triggers fire correctly
- [ ] Hypertables chunk data properly
- [ ] Retention policies work
- [ ] Connection pool handles load
- [ ] Transactions rollback on error
- [ ] Migrations are idempotent

---

**PRP Status**: Ready for Implementation
**Estimated Hours**: 26 hours (13 story points)
**Priority**: Critical - Must be first component
**Next Steps**: After completion, proceed to Position Management implementation
