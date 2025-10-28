# Sprint 1 - Stream C: Database & Redis Infrastructure

**Agent**: Infrastructure Specialist
**Duration**: 4-5 days
**Total Effort**: 14 hours
**Branch**: `sprint-1/stream-c-infrastructure`

---

## 🎯 Stream Objectives

Build production-ready data persistence layer:
1. PostgreSQL with TimescaleDB for time-series data (8 hours)
2. Redis for distributed caching (6 hours)

**Why These Tasks**: Enable production deployment with persistent storage and distributed caching

---

## 📋 Task Breakdown

### TASK-001: PostgreSQL Database Migrations (8 hours)

**Current State**: All data stored in-memory (trade history, positions, etc.)

**Target State**: PostgreSQL with TimescaleDB for hypertables

**Implementation Steps**:

1. **Setup database schema** (2 hours)
   - File: `workspace/infrastructure/database/schema.sql` (NEW)
```sql
-- Create database and extensions
CREATE DATABASE trading_system;
\c trading_system;

-- Install TimescaleDB extension for time-series optimization
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Trades table (main historical data)
CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    trade_id VARCHAR(100) UNIQUE NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Trade details
    symbol VARCHAR(20) NOT NULL,
    trade_type VARCHAR(20) NOT NULL, -- ENTRY_LONG, EXIT_LONG, etc.
    side VARCHAR(10) NOT NULL, -- BUY, SELL

    -- Pricing
    entry_price NUMERIC(20, 8),
    exit_price NUMERIC(20, 8),
    quantity NUMERIC(20, 8) NOT NULL,
    fees_paid NUMERIC(20, 8) DEFAULT 0,

    -- P&L
    realized_pnl NUMERIC(20, 8),
    unrealized_pnl NUMERIC(20, 8),

    -- Signal information
    signal_confidence NUMERIC(5, 4),
    signal_reasoning TEXT,

    -- Position information
    position_size NUMERIC(20, 8),
    leverage NUMERIC(5, 2),

    -- Performance
    execution_latency_ms NUMERIC(10, 2),

    -- Metadata
    exchange VARCHAR(50) NOT NULL,
    order_id VARCHAR(100),

    -- Indexes for common queries
    INDEX idx_trades_timestamp (timestamp DESC),
    INDEX idx_trades_symbol (symbol),
    INDEX idx_trades_trade_type (trade_type),
    INDEX idx_trades_symbol_timestamp (symbol, timestamp DESC)
);

-- Convert to hypertable for time-series optimization
SELECT create_hypertable('trades', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Positions table (current state)
CREATE TABLE positions (
    id SERIAL PRIMARY KEY,
    position_id VARCHAR(100) UNIQUE NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL, -- LONG, SHORT

    -- Pricing
    entry_price NUMERIC(20, 8) NOT NULL,
    current_price NUMERIC(20, 8) NOT NULL,
    quantity NUMERIC(20, 8) NOT NULL,
    leverage NUMERIC(5, 2) DEFAULT 1,

    -- P&L
    unrealized_pnl NUMERIC(20, 8) NOT NULL,
    realized_pnl NUMERIC(20, 8) DEFAULT 0,

    -- Risk management
    stop_loss_price NUMERIC(20, 8),
    take_profit_price NUMERIC(20, 8),
    liquidation_price NUMERIC(20, 8),

    -- Timestamps
    opened_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMPTZ,

    -- Metadata
    exchange VARCHAR(50) NOT NULL,
    is_open BOOLEAN NOT NULL DEFAULT TRUE,

    INDEX idx_positions_symbol (symbol),
    INDEX idx_positions_is_open (is_open),
    INDEX idx_positions_opened_at (opened_at DESC)
);

-- Market data cache table (for Redis fallback)
CREATE TABLE market_data_cache (
    id SERIAL PRIMARY KEY,
    cache_key VARCHAR(255) UNIQUE NOT NULL,
    data JSONB NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    INDEX idx_market_cache_key (cache_key),
    INDEX idx_market_cache_expires (expires_at)
);

-- Metrics snapshots (for historical tracking)
CREATE TABLE metrics_snapshots (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Trading metrics
    trades_total INTEGER DEFAULT 0,
    trades_successful INTEGER DEFAULT 0,
    trades_failed INTEGER DEFAULT 0,

    -- Financial metrics
    realized_pnl_total NUMERIC(20, 8) DEFAULT 0,
    unrealized_pnl_current NUMERIC(20, 8) DEFAULT 0,
    fees_paid_total NUMERIC(20, 8) DEFAULT 0,

    -- Performance metrics
    execution_latency_avg_ms NUMERIC(10, 2) DEFAULT 0,
    execution_latency_p95_ms NUMERIC(10, 2) DEFAULT 0,
    execution_latency_p99_ms NUMERIC(10, 2) DEFAULT 0,

    -- LLM metrics
    llm_calls_total INTEGER DEFAULT 0,
    llm_cost_total_usd NUMERIC(10, 4) DEFAULT 0,

    -- Risk metrics
    circuit_breaker_triggers INTEGER DEFAULT 0,
    max_position_size_exceeded INTEGER DEFAULT 0,

    -- Cache metrics
    cache_hits_total INTEGER DEFAULT 0,
    cache_misses_total INTEGER DEFAULT 0,
    cache_hit_rate_percent NUMERIC(5, 2) DEFAULT 0,

    INDEX idx_metrics_timestamp (timestamp DESC)
);

-- Convert metrics to hypertable
SELECT create_hypertable('metrics_snapshots', 'timestamp',
    chunk_time_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- System logs table
CREATE TABLE system_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    level VARCHAR(20) NOT NULL, -- INFO, WARNING, ERROR, CRITICAL
    message TEXT NOT NULL,
    context JSONB,

    INDEX idx_logs_timestamp (timestamp DESC),
    INDEX idx_logs_level (level)
);

-- Convert logs to hypertable
SELECT create_hypertable('system_logs', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Retention policies (auto-delete old data)
SELECT add_retention_policy('trades', INTERVAL '90 days');
SELECT add_retention_policy('metrics_snapshots', INTERVAL '30 days');
SELECT add_retention_policy('system_logs', INTERVAL '14 days');

-- Continuous aggregates for faster queries
CREATE MATERIALIZED VIEW daily_trade_stats
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', timestamp) AS day,
    symbol,
    COUNT(*) AS trade_count,
    SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) AS winning_trades,
    SUM(CASE WHEN realized_pnl <= 0 THEN 1 ELSE 0 END) AS losing_trades,
    SUM(realized_pnl) AS total_pnl,
    AVG(realized_pnl) AS avg_pnl,
    SUM(fees_paid) AS total_fees
FROM trades
WHERE trade_type LIKE 'EXIT_%'
GROUP BY day, symbol;

-- Refresh policy for continuous aggregate
SELECT add_continuous_aggregate_policy('daily_trade_stats',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');
```

2. **Create database connection pool** (2 hours)
   - File: `workspace/infrastructure/database/connection.py` (NEW)
```python
"""
Database Connection Pool

Manages PostgreSQL connections with connection pooling.
"""

import asyncpg
from typing import Optional
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class DatabasePool:
    """PostgreSQL connection pool manager"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "trading_system",
        user: str = "trading_user",
        password: str = "",
        min_size: int = 10,
        max_size: int = 50,
    ):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.min_size = min_size
        self.max_size = max_size

        self.pool: Optional[asyncpg.Pool] = None

    async def initialize(self):
        """Initialize connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                min_size=self.min_size,
                max_size=self.max_size,
                command_timeout=30,
                max_inactive_connection_lifetime=300,
            )
            logger.info(
                f"Database pool initialized: {self.min_size}-{self.max_size} connections"
            )
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}", exc_info=True)
            raise

    async def close(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database pool closed")

    @asynccontextmanager
    async def acquire(self):
        """Acquire connection from pool"""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")

        async with self.pool.acquire() as connection:
            yield connection

    async def execute(self, query: str, *args):
        """Execute query (INSERT, UPDATE, DELETE)"""
        async with self.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args):
        """Fetch multiple rows"""
        async with self.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args):
        """Fetch single row"""
        async with self.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchval(self, query: str, *args):
        """Fetch single value"""
        async with self.acquire() as conn:
            return await conn.fetchval(query, *args)


# Global database pool instance
_db_pool: Optional[DatabasePool] = None


async def get_db_pool() -> DatabasePool:
    """Get global database pool instance"""
    global _db_pool
    if _db_pool is None:
        raise RuntimeError("Database pool not initialized. Call init_db_pool() first.")
    return _db_pool


async def init_db_pool(
    host: str = "localhost",
    port: int = 5432,
    database: str = "trading_system",
    user: str = "trading_user",
    password: str = "",
) -> DatabasePool:
    """Initialize global database pool"""
    global _db_pool
    _db_pool = DatabasePool(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
    )
    await _db_pool.initialize()
    return _db_pool


async def close_db_pool():
    """Close global database pool"""
    global _db_pool
    if _db_pool:
        await _db_pool.close()
        _db_pool = None
```

3. **Migrate TradeHistoryService to PostgreSQL** (2 hours)
   - File: `workspace/features/trade_history/trade_history_service.py`
   - Replace in-memory storage with database:
```python
from workspace.infrastructure.database import get_db_pool

class TradeHistoryService:
    def __init__(self, use_database: bool = True):
        self.use_database = use_database

        # Keep in-memory as fallback
        self._trades: Dict[str, TradeRecord] = {}
        self._index_by_symbol: Dict[str, List[str]] = {}

    async def record_trade(self, trade: TradeRecord) -> bool:
        """Record trade to database"""
        if self.use_database:
            try:
                db = await get_db_pool()

                query = """
                INSERT INTO trades (
                    trade_id, timestamp, symbol, trade_type, side,
                    entry_price, exit_price, quantity, fees_paid,
                    realized_pnl, unrealized_pnl, signal_confidence,
                    signal_reasoning, position_size, leverage,
                    execution_latency_ms, exchange, order_id
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                         $11, $12, $13, $14, $15, $16, $17, $18)
                ON CONFLICT (trade_id) DO UPDATE SET
                    exit_price = EXCLUDED.exit_price,
                    realized_pnl = EXCLUDED.realized_pnl,
                    unrealized_pnl = EXCLUDED.unrealized_pnl
                """

                await db.execute(
                    query,
                    trade.trade_id,
                    trade.timestamp,
                    trade.symbol,
                    trade.trade_type.value,
                    trade.side.value,
                    float(trade.entry_price) if trade.entry_price else None,
                    float(trade.exit_price) if trade.exit_price else None,
                    float(trade.quantity),
                    float(trade.fees_paid),
                    float(trade.realized_pnl) if trade.realized_pnl else None,
                    float(trade.unrealized_pnl) if trade.unrealized_pnl else None,
                    float(trade.signal_confidence) if trade.signal_confidence else None,
                    trade.signal_reasoning,
                    float(trade.position_size),
                    float(trade.leverage),
                    float(trade.execution_latency_ms) if trade.execution_latency_ms else None,
                    trade.exchange,
                    trade.order_id,
                )

                logger.debug(f"Trade {trade.trade_id} recorded to database")
                return True

            except Exception as e:
                logger.error(f"Database error, falling back to in-memory: {e}")
                # Fall back to in-memory
                self._trades[trade.trade_id] = trade
                return True
        else:
            # In-memory storage
            self._trades[trade.trade_id] = trade
            return True

    async def get_trades_by_symbol(
        self,
        symbol: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[TradeRecord]:
        """Get trades by symbol from database"""
        if self.use_database:
            try:
                db = await get_db_pool()

                query = """
                SELECT * FROM trades
                WHERE symbol = $1
                """
                params = [symbol]

                if start_date:
                    query += " AND timestamp >= $2"
                    params.append(start_date)

                if end_date:
                    query += f" AND timestamp <= ${len(params) + 1}"
                    params.append(end_date)

                query += " ORDER BY timestamp DESC"

                rows = await db.fetch(query, *params)

                return [self._row_to_trade_record(row) for row in rows]

            except Exception as e:
                logger.error(f"Database error: {e}")
                return []
        else:
            # In-memory fallback
            return [
                trade for trade in self._trades.values()
                if trade.symbol == symbol
            ]

    def _row_to_trade_record(self, row) -> TradeRecord:
        """Convert database row to TradeRecord"""
        return TradeRecord(
            trade_id=row["trade_id"],
            timestamp=row["timestamp"],
            symbol=row["symbol"],
            trade_type=TradeType(row["trade_type"]),
            side=TradeSide(row["side"]),
            entry_price=Decimal(str(row["entry_price"])) if row["entry_price"] else None,
            exit_price=Decimal(str(row["exit_price"])) if row["exit_price"] else None,
            quantity=Decimal(str(row["quantity"])),
            fees_paid=Decimal(str(row["fees_paid"])),
            realized_pnl=Decimal(str(row["realized_pnl"])) if row["realized_pnl"] else None,
            unrealized_pnl=Decimal(str(row["unrealized_pnl"])) if row["unrealized_pnl"] else None,
            signal_confidence=Decimal(str(row["signal_confidence"])) if row["signal_confidence"] else None,
            signal_reasoning=row["signal_reasoning"],
            position_size=Decimal(str(row["position_size"])),
            leverage=Decimal(str(row["leverage"])),
            execution_latency_ms=Decimal(str(row["execution_latency_ms"])) if row["execution_latency_ms"] else None,
            exchange=row["exchange"],
            order_id=row["order_id"],
        )
```

4. **Create migration tool** (1 hour)
   - File: `workspace/infrastructure/database/migrations.py` (NEW)
```python
"""
Database Migration Tool

Simple migration runner for schema changes.
"""

import asyncio
import asyncpg
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class MigrationRunner:
    """Run database migrations"""

    def __init__(self, host: str, port: int, database: str, user: str, password: str):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password

    async def run_migration(self, sql_file: Path):
        """Run a single migration file"""
        try:
            # Connect to database
            conn = await asyncpg.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
            )

            # Read SQL file
            sql = sql_file.read_text()

            # Execute SQL
            await conn.execute(sql)

            logger.info(f"Migration {sql_file.name} completed successfully")

            await conn.close()

        except Exception as e:
            logger.error(f"Migration {sql_file.name} failed: {e}", exc_info=True)
            raise

    async def run_all_migrations(self, migrations_dir: Path):
        """Run all migration files in order"""
        migration_files = sorted(migrations_dir.glob("*.sql"))

        for migration_file in migration_files:
            logger.info(f"Running migration: {migration_file.name}")
            await self.run_migration(migration_file)

        logger.info(f"All {len(migration_files)} migrations completed")


async def main():
    """Run migrations from command line"""
    import os

    runner = MigrationRunner(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        database=os.getenv("DB_NAME", "trading_system"),
        user=os.getenv("DB_USER", "trading_user"),
        password=os.getenv("DB_PASSWORD", ""),
    )

    migrations_dir = Path(__file__).parent / "migrations"
    await runner.run_all_migrations(migrations_dir)


if __name__ == "__main__":
    asyncio.run(main())
```

5. **Write tests** (1 hour)
   - File: `workspace/tests/integration/test_database_integration.py` (NEW)
```python
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from workspace.infrastructure.database import init_db_pool, close_db_pool, get_db_pool
from workspace.features.trade_history import TradeHistoryService, TradeRecord, TradeType, TradeSide


@pytest.mark.asyncio
async def test_database_connection():
    """Test database connection pool"""
    # Initialize pool
    pool = await init_db_pool(
        host="localhost",
        database="trading_system_test",
        user="postgres",
        password="",
    )

    # Test query
    db = await get_db_pool()
    result = await db.fetchval("SELECT 1")
    assert result == 1

    # Close pool
    await close_db_pool()


@pytest.mark.asyncio
async def test_trade_history_database_storage():
    """Test storing trades in database"""
    # Initialize database
    await init_db_pool(database="trading_system_test")

    # Create service
    service = TradeHistoryService(use_database=True)

    # Create test trade
    trade = TradeRecord(
        trade_id="test_trade_001",
        timestamp=datetime.utcnow(),
        symbol="BTC/USDT",
        trade_type=TradeType.ENTRY_LONG,
        side=TradeSide.BUY,
        entry_price=Decimal("45000.00"),
        quantity=Decimal("0.1"),
        fees_paid=Decimal("4.50"),
        position_size=Decimal("4500.00"),
        leverage=Decimal("1"),
        exchange="binance",
    )

    # Record trade
    success = await service.record_trade(trade)
    assert success is True

    # Retrieve trade
    trades = await service.get_trades_by_symbol("BTC/USDT")
    assert len(trades) == 1
    assert trades[0].trade_id == "test_trade_001"
    assert trades[0].entry_price == Decimal("45000.00")

    # Cleanup
    await close_db_pool()
```

---

### TASK-004: Redis Integration (6 hours)

**Current State**: In-memory caching (CacheService uses dict)

**Target State**: Redis with persistence and distributed support

**Implementation Steps**:

1. **Setup Redis connection** (1.5 hours)
   - File: `workspace/infrastructure/cache/redis_connection.py` (NEW)
```python
"""
Redis Connection Manager

Manages Redis connections with connection pooling.
"""

import redis.asyncio as redis
from typing import Optional, Any
import logging
import json
from datetime import timedelta

logger = logging.getLogger(__name__)


class RedisManager:
    """Redis connection manager"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        max_connections: int = 50,
    ):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.max_connections = max_connections

        self.pool: Optional[redis.ConnectionPool] = None
        self.client: Optional[redis.Redis] = None

    async def initialize(self):
        """Initialize Redis connection pool"""
        try:
            self.pool = redis.ConnectionPool(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                max_connections=self.max_connections,
                decode_responses=False,  # We handle encoding
            )

            self.client = redis.Redis(connection_pool=self.pool)

            # Test connection
            await self.client.ping()

            logger.info(f"Redis connected: {self.host}:{self.port}/{self.db}")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}", exc_info=True)
            raise

    async def close(self):
        """Close Redis connection"""
        if self.client:
            await self.client.close()
        if self.pool:
            await self.pool.disconnect()
        logger.info("Redis connection closed")

    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis"""
        try:
            value = await self.client.get(key)
            if value is None:
                return None

            # Deserialize JSON
            return json.loads(value)

        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
    ) -> bool:
        """Set value in Redis with optional TTL"""
        try:
            # Serialize to JSON
            serialized = json.dumps(value, default=str)

            if ttl_seconds:
                await self.client.setex(key, ttl_seconds, serialized)
            else:
                await self.client.set(key, serialized)

            return True

        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        try:
            await self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            return await self.client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False

    async def clear(self, pattern: str = "*") -> int:
        """Clear keys matching pattern"""
        try:
            keys = await self.client.keys(pattern)
            if keys:
                return await self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis CLEAR error for pattern {pattern}: {e}")
            return 0

    async def get_stats(self) -> dict:
        """Get Redis stats"""
        try:
            info = await self.client.info("stats")
            return {
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate_percent": (
                    100 * info.get("keyspace_hits", 0) /
                    (info.get("keyspace_hits", 0) + info.get("keyspace_misses", 1))
                ),
            }
        except Exception as e:
            logger.error(f"Redis stats error: {e}")
            return {}


# Global Redis instance
_redis_manager: Optional[RedisManager] = None


async def get_redis() -> RedisManager:
    """Get global Redis instance"""
    global _redis_manager
    if _redis_manager is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return _redis_manager


async def init_redis(
    host: str = "localhost",
    port: int = 6379,
    db: int = 0,
    password: Optional[str] = None,
) -> RedisManager:
    """Initialize global Redis instance"""
    global _redis_manager
    _redis_manager = RedisManager(host=host, port=port, db=db, password=password)
    await _redis_manager.initialize()
    return _redis_manager


async def close_redis():
    """Close global Redis instance"""
    global _redis_manager
    if _redis_manager:
        await _redis_manager.close()
        _redis_manager = None
```

2. **Migrate CacheService to use Redis** (2 hours)
   - File: `workspace/features/caching/cache_service.py`
   - Replace in-memory storage with Redis:
```python
from workspace.infrastructure.cache import get_redis

class CacheService:
    """Cache service with Redis backend"""

    def __init__(self, use_redis: bool = True):
        self.use_redis = use_redis

        # Statistics
        self._hits = 0
        self._misses = 0
        self._sets = 0
        self._deletes = 0
        self._evictions = 0

        # In-memory fallback
        self._memory_cache: Dict[str, Tuple[Any, float]] = {}

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if self.use_redis:
            try:
                redis = await get_redis()
                value = await redis.get(key)

                if value is not None:
                    self._hits += 1
                    logger.debug(f"Cache hit: {key}")
                    return value
                else:
                    self._misses += 1
                    logger.debug(f"Cache miss: {key}")
                    return None

            except Exception as e:
                logger.error(f"Redis error, falling back to memory: {e}")
                # Fall back to memory cache
                return self._memory_get(key)
        else:
            return self._memory_get(key)

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
    ) -> bool:
        """Set value in cache"""
        if self.use_redis:
            try:
                redis = await get_redis()
                success = await redis.set(key, value, ttl_seconds=ttl_seconds)

                if success:
                    self._sets += 1
                    logger.debug(f"Cache set: {key} (TTL: {ttl_seconds}s)")

                return success

            except Exception as e:
                logger.error(f"Redis error, falling back to memory: {e}")
                return self._memory_set(key, value, ttl_seconds)
        else:
            return self._memory_set(key, value, ttl_seconds)

    async def clear(self, pattern: str = "*") -> int:
        """Clear cache entries matching pattern"""
        if self.use_redis:
            try:
                redis = await get_redis()
                count = await redis.clear(pattern)
                self._evictions += count
                logger.info(f"Cleared {count} cache entries matching '{pattern}'")
                return count

            except Exception as e:
                logger.error(f"Redis error: {e}")
                return 0
        else:
            return self._memory_clear(pattern)

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics"""
        total_requests = self._hits + self._misses

        return {
            "hits": self._hits,
            "misses": self._misses,
            "sets": self._sets,
            "deletes": self._deletes,
            "evictions": self._evictions,
            "hit_rate_percent": (
                100 * self._hits / total_requests if total_requests > 0 else 0
            ),
            "backend": "redis" if self.use_redis else "memory",
        }

    # In-memory fallback methods
    def _memory_get(self, key: str) -> Optional[Any]:
        """Get from in-memory cache"""
        import time
        if key in self._memory_cache:
            value, expires_at = self._memory_cache[key]
            if expires_at == 0 or time.time() < expires_at:
                self._hits += 1
                return value
            else:
                # Expired
                del self._memory_cache[key]
                self._misses += 1
                return None
        else:
            self._misses += 1
            return None

    def _memory_set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
    ) -> bool:
        """Set in in-memory cache"""
        import time
        expires_at = time.time() + ttl_seconds if ttl_seconds else 0
        self._memory_cache[key] = (value, expires_at)
        self._sets += 1
        return True

    def _memory_clear(self, pattern: str) -> int:
        """Clear from in-memory cache"""
        import fnmatch
        keys_to_delete = [
            key for key in self._memory_cache.keys()
            if fnmatch.fnmatch(key, pattern)
        ]
        for key in keys_to_delete:
            del self._memory_cache[key]
        self._evictions += len(keys_to_delete)
        return len(keys_to_delete)
```

3. **Docker Compose setup** (1.5 hours)
   - File: `docker-compose.yml` (NEW)
```yaml
version: '3.8'

services:
  # PostgreSQL with TimescaleDB
  postgres:
    image: timescale/timescaledb:latest-pg15
    container_name: trading_postgres
    environment:
      POSTGRES_DB: trading_system
      POSTGRES_USER: trading_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_INITDB_ARGS: "-E UTF8"
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./workspace/infrastructure/database/schema.sql:/docker-entrypoint-initdb.d/01_schema.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U trading_user -d trading_system"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis cache
  redis:
    image: redis:7-alpine
    container_name: trading_redis
    command: redis-server --appendonly yes --maxmemory 2gb --maxmemory-policy allkeys-lru
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  # Grafana (monitoring dashboard)
  grafana:
    image: grafana/grafana:latest
    container_name: trading_grafana
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}
      GF_INSTALL_PLUGINS: grafana-piechart-panel
    volumes:
      - grafana_data:/var/lib/grafana
      - ./infrastructure/grafana/dashboards:/etc/grafana/provisioning/dashboards
    depends_on:
      - postgres

  # Prometheus (metrics collection)
  prometheus:
    image: prom/prometheus:latest
    container_name: trading_prometheus
    ports:
      - "9090:9090"
    volumes:
      - prometheus_data:/prometheus
      - ./infrastructure/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'

volumes:
  postgres_data:
  redis_data:
  grafana_data:
  prometheus_data:
```

4. **Write tests** (1 hour)
   - File: `workspace/tests/integration/test_redis_integration.py` (NEW)
```python
import pytest
import asyncio
from workspace.infrastructure.cache import init_redis, close_redis, get_redis
from workspace.features.caching import CacheService


@pytest.mark.asyncio
async def test_redis_connection():
    """Test Redis connection"""
    # Initialize Redis
    redis = await init_redis(host="localhost", port=6379)

    # Test ping
    client = await get_redis()
    assert await client.client.ping()

    # Close
    await close_redis()


@pytest.mark.asyncio
async def test_cache_service_redis_backend():
    """Test CacheService with Redis backend"""
    # Initialize Redis
    await init_redis()

    # Create cache service
    cache = CacheService(use_redis=True)

    # Test set and get
    await cache.set("test_key", {"value": 123}, ttl_seconds=60)
    result = await cache.get("test_key")
    assert result == {"value": 123}

    # Test cache hit
    result2 = await cache.get("test_key")
    assert result2 == {"value": 123}

    # Check stats
    stats = cache.get_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 0
    assert stats["backend"] == "redis"

    # Cleanup
    await cache.delete("test_key")
    await close_redis()


@pytest.mark.asyncio
async def test_cache_ttl_expiration_redis():
    """Test cache TTL with Redis"""
    await init_redis()

    cache = CacheService(use_redis=True)

    # Set with 1 second TTL
    await cache.set("ttl_test", "value", ttl_seconds=1)

    # Should exist immediately
    value = await cache.get("ttl_test")
    assert value == "value"

    # Wait for expiration
    await asyncio.sleep(1.1)

    # Should be expired
    value2 = await cache.get("ttl_test")
    assert value2 is None

    await close_redis()
```

---

## ✅ Definition of Done

- [ ] PostgreSQL schema created with TimescaleDB
- [ ] Database connection pool configured and tested
- [ ] TradeHistoryService migrated to PostgreSQL
- [ ] Database queries < 10ms p95 latency
- [ ] Redis connection manager implemented
- [ ] CacheService migrated to Redis
- [ ] Docker Compose setup for all services
- [ ] Integration tests passing
- [ ] Database migrations automated
- [ ] Connection pooling optimized

---

## 🧪 Testing Checklist

```bash
# PostgreSQL tests
pytest workspace/tests/integration/test_database_integration.py -v

# Redis tests
pytest workspace/tests/integration/test_redis_integration.py -v

# Start infrastructure
docker-compose up -d

# Check services
docker-compose ps
docker-compose logs postgres
docker-compose logs redis

# Run migrations
python workspace/infrastructure/database/migrations.py

# Test connection
python -c "
import asyncio
from workspace.infrastructure.database import init_db_pool, get_db_pool

async def test():
    await init_db_pool()
    db = await get_db_pool()
    result = await db.fetchval('SELECT 1')
    print(f'Database connected: {result}')

asyncio.run(test())
"
```

---

## 📝 Commit Strategy

**Commit 1**: PostgreSQL schema and connection pool
```
feat(infrastructure): add PostgreSQL with TimescaleDB

- Create database schema with hypertables
- Implement connection pool manager
- Add migration runner
- Configure retention policies and continuous aggregates
```

**Commit 2**: Migrate TradeHistory to database
```
feat(trade-history): migrate to PostgreSQL

- Update TradeHistoryService to use database
- Maintain in-memory fallback for errors
- Add database integration tests
```

**Commit 3**: Redis integration
```
feat(infrastructure): add Redis caching layer

- Implement Redis connection manager
- Migrate CacheService to use Redis backend
- Maintain in-memory fallback
- Add integration tests
```

**Commit 4**: Docker Compose setup
```
feat(infrastructure): add Docker Compose configuration

- Setup PostgreSQL with TimescaleDB
- Setup Redis with persistence
- Add Grafana and Prometheus
- Configure health checks
```

---

## 🚀 Getting Started

1. **Setup**:
```bash
git checkout -b sprint-1/stream-c-infrastructure
cd /Users/tobiprivat/Documents/GitProjects/personal/trader
```

2. **Install dependencies**:
```bash
pip install asyncpg redis
```

3. **Start services**:
```bash
docker-compose up -d
```

4. **Wait for services to be ready**:
```bash
docker-compose ps
# Wait until all services show "healthy"
```

5. **Run migrations**:
```bash
python workspace/infrastructure/database/migrations.py
```

6. **Test connections**:
```bash
pytest workspace/tests/integration/test_database_integration.py -v
pytest workspace/tests/integration/test_redis_integration.py -v
```

7. **Create PR when done**

---

## 📊 Performance Targets

**Database Performance**:
- Connection pool: 10-50 connections
- Query latency: <10ms p95, <50ms p99
- Bulk inserts: >1000 trades/second
- Query throughput: >100 queries/second

**Redis Performance**:
- Get operation: <1ms p95
- Set operation: <2ms p95
- Hit rate: >70% after 1 hour
- Memory usage: <2GB

**TimescaleDB Optimization**:
- Hypertable chunks: 1 day intervals
- Continuous aggregates: 1 hour refresh
- Retention policy: 90 days for trades, 30 days for metrics

---

## ⚠️ Important Notes

1. **Database Credentials**:
   - Use environment variables for passwords
   - Never commit credentials to git
   - Example: `export DB_PASSWORD=your_password`

2. **Docker Volumes**:
   - Data persists across restarts
   - To reset: `docker-compose down -v`
   - Backup volumes regularly

3. **Migration Safety**:
   - Always backup database before migrations
   - Test migrations on staging first
   - Migrations are idempotent (can run multiple times)

4. **Redis Persistence**:
   - AOF (Append Only File) enabled
   - Rewrite interval: 1 hour
   - Maxmemory policy: allkeys-lru (evict least recently used)

5. **Connection Pooling**:
   - Min connections: 10 (always ready)
   - Max connections: 50 (prevents overload)
   - Connection timeout: 30 seconds
   - Idle timeout: 5 minutes
