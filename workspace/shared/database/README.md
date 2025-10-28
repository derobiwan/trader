# Database Layer - LLM Cryptocurrency Trading System

Complete PostgreSQL 16 + TimescaleDB 2.17 database setup for the trading system with 11 tables, time-series optimization, and comprehensive connection pooling.

## Table of Contents

- [Overview](#overview)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Database Schema](#database-schema)
- [Usage Examples](#usage-examples)
- [Performance](#performance)
- [Testing](#testing)
- [Maintenance](#maintenance)
- [Troubleshooting](#troubleshooting)

## Overview

The database layer provides:
- **11 tables** tracking positions, orders, signals, market data, and performance
- **TimescaleDB hypertables** for time-series data (market data, performance, risk events)
- **Async connection pooling** with 10-50 connections using asyncpg
- **CHF precision handling** with DECIMAL(20, 8) for all monetary amounts
- **Comprehensive indexing** for <10ms query performance
- **Data compression** after 7 days and retention policies

### Key Tables

| Table | Type | Purpose |
|-------|------|---------|
| **positions** | Standard | Core trading positions (open/closed) |
| **trading_signals** | Standard | LLM-generated trading decisions |
| **orders** | Standard | Exchange orders with execution status |
| **market_data** | Hypertable | Time-series OHLCV with indicators |
| **daily_performance** | Hypertable | Daily portfolio metrics |
| **risk_events** | Hypertable | Risk events with severity |
| **llm_requests** | Standard | LLM API audit log |
| **system_config** | Standard | System configuration |
| **audit_log** | Standard | Immutable audit trail |
| **circuit_breaker_state** | Standard | Daily circuit breaker tracking |
| **position_reconciliation** | Standard | System-exchange sync tracking |

## Requirements

- **PostgreSQL 16+** (not 15 or earlier)
- **TimescaleDB 2.17+**
- **Python 3.12+**
- **asyncpg** for async database access
- **alembic** for migrations
- **pydantic** for type-safe models

## Installation

### 1. Install PostgreSQL 16

**macOS (Homebrew)**:
```bash
brew install postgresql@16
brew services start postgresql@16

# Add to PATH (add to ~/.zshrc or ~/.bash_profile)
export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"
```

**Linux (Ubuntu/Debian)**:
```bash
sudo apt-get install postgresql-16 postgresql-contrib-16
sudo systemctl start postgresql
```

**Windows**:
Download from https://www.postgresql.org/download/windows/

### 2. Install TimescaleDB

**macOS**:
```bash
brew install timescaledb
timescaledb-tune --quiet --yes
brew services restart postgresql@16
```

**Linux**:
```bash
sudo add-apt-repository ppa:timescale/timescaledb-ppa
sudo apt update
sudo apt install timescaledb-2-postgresql-16
sudo timescaledb-tune --quiet --yes
sudo systemctl restart postgresql
```

**Verify Installation**:
```bash
psql -U postgres -c "SELECT version()"
psql -U postgres -c "CREATE EXTENSION IF NOT EXISTS timescaledb; SELECT extversion FROM pg_extension WHERE extname = 'timescaledb'"
```

### 3. Create Database

```bash
# Create database
createdb -U postgres trading_system

# Or using psql
psql -U postgres
CREATE DATABASE trading_system;
\q
```

### 4. Enable Extensions

```bash
psql -U postgres trading_system
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
\dx  -- List extensions
\q
```

### 5. Run Migrations

```bash
# Install Python dependencies
cd /Users/tobiprivat/Documents/GitProjects/personal/trader
pip install asyncpg alembic pydantic

# Initialize Alembic (if not done)
alembic init alembic

# Edit alembic.ini to set database URL
# sqlalchemy.url = postgresql://postgres:@localhost/trading_system

# Run migrations
alembic upgrade head
```

Or run SQL directly:
```bash
psql -U postgres trading_system < workspace/shared/database/schema.sql
```

## Configuration

### Environment Variables

Create a `.env` file:
```bash
# Database connection
DB_HOST=localhost
DB_PORT=5432
DB_NAME=trading_system
DB_USER=postgres
DB_PASSWORD=

# Connection pool
DB_MIN_POOL_SIZE=10
DB_MAX_POOL_SIZE=50
DB_COMMAND_TIMEOUT=10.0
```

### Python Configuration

```python
from workspace.shared.database.connection import init_pool

# Initialize global pool
pool = await init_pool(
    host=os.getenv("DB_HOST", "localhost"),
    database=os.getenv("DB_NAME", "trading_system"),
    user=os.getenv("DB_USER", "postgres"),
    password=os.getenv("DB_PASSWORD", ""),
    min_size=10,
    max_size=50
)

# Use pool
positions = await pool.fetch("SELECT * FROM positions WHERE status = 'OPEN'")
```

## Database Schema

### Positions Table

Core trading positions with P&L tracking.

```sql
CREATE TABLE positions (
    id UUID PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,  -- 'LONG' or 'SHORT'
    quantity DECIMAL(20, 8) NOT NULL,
    entry_price DECIMAL(20, 8) NOT NULL,
    current_price DECIMAL(20, 8),
    leverage INTEGER NOT NULL CHECK (leverage >= 5 AND leverage <= 40),
    stop_loss DECIMAL(20, 8),
    take_profit DECIMAL(20, 8),
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
    pnl_chf DECIMAL(20, 8),  -- Realized P&L in CHF
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for <10ms queries
CREATE INDEX idx_positions_symbol ON positions(symbol);
CREATE INDEX idx_positions_status ON positions(status);
CREATE INDEX idx_positions_created_at ON positions(created_at DESC);
```

### Market Data (TimescaleDB Hypertable)

Time-series OHLCV data with technical indicators.

```sql
CREATE TABLE market_data (
    symbol VARCHAR(20) NOT NULL,
    timestamp BIGINT NOT NULL,  -- Microseconds since epoch
    open DECIMAL(20, 8) NOT NULL,
    high DECIMAL(20, 8) NOT NULL,
    low DECIMAL(20, 8) NOT NULL,
    close DECIMAL(20, 8) NOT NULL,
    volume DECIMAL(20, 8) NOT NULL,
    indicators JSONB  -- {rsi: 55.5, macd: 120.3, ...}
);

-- Convert to hypertable (1 day chunks)
SELECT create_hypertable('market_data', 'timestamp',
    chunk_time_interval => 86400000000
);

-- Compression after 7 days
ALTER TABLE market_data SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol'
);
SELECT add_compression_policy('market_data', INTERVAL '7 days');

-- Retention policy (90 days)
SELECT add_retention_policy('market_data', INTERVAL '90 days');
```

### System Configuration

Key-value configuration storage.

```sql
-- Default configuration (CHF 2,626.96 capital)
SELECT * FROM system_config WHERE key LIKE 'trading.%';

key                              | value
---------------------------------|--------
trading.capital_chf              | 2626.96
trading.circuit_breaker_chf      | 183.89
trading.circuit_breaker_pct      | 0.07
trading.max_leverage             | 40
trading.exchange                 | "bybit"
trading.assets                   | ["BTCUSDT", "ETHUSDT", ...]
```

## Usage Examples

### 1. Connection Pool

```python
from workspace.shared.database.connection import DatabasePool

# Create pool
pool = DatabasePool(
    host="localhost",
    database="trading_system",
    user="postgres"
)
await pool.initialize()

# Execute query
positions = await pool.fetch(
    "SELECT * FROM positions WHERE status = $1",
    "OPEN"
)

# Single value
count = await pool.fetchval(
    "SELECT COUNT(*) FROM positions WHERE symbol = $1",
    "BTCUSDT"
)

# Health check
health = await pool.health_check()
print(f"DB healthy: {health['healthy']}, latency: {health['latency_ms']}ms")

# Cleanup
await pool.close()
```

### 2. Create Position

```python
from workspace.shared.database.models import Position, PositionSide
from decimal import Decimal

position = Position(
    symbol="BTCUSDT",
    side=PositionSide.LONG,
    quantity=Decimal("0.01"),
    entry_price=Decimal("45000.00"),
    leverage=10,
    stop_loss=Decimal("44000.00")
)

await pool.execute(
    """
    INSERT INTO positions (id, symbol, side, quantity, entry_price, leverage, stop_loss)
    VALUES ($1, $2, $3, $4, $5, $6, $7)
    """,
    position.id, position.symbol, position.side.value, position.quantity,
    position.entry_price, position.leverage, position.stop_loss
)
```

### 3. Query Open Positions

```python
# Get all open positions with unrealized P&L
positions = await pool.fetch("""
    SELECT * FROM v_open_positions
    ORDER BY unrealized_pnl_usd DESC
""")

for pos in positions:
    print(f"{pos['symbol']}: {pos['side']} {pos['quantity']} @ {pos['entry_price']}")
    print(f"  Unrealized P&L: ${pos['unrealized_pnl_usd']:.2f}")
```

### 4. Insert Market Data

```python
from workspace.shared.database.models import MarketData, datetime_to_microseconds
from datetime import datetime

data = MarketData(
    symbol="BTCUSDT",
    timestamp=datetime_to_microseconds(datetime.utcnow()),
    open=Decimal("45000.00"),
    high=Decimal("45500.00"),
    low=Decimal("44800.00"),
    close=Decimal("45200.00"),
    volume=Decimal("1000.5"),
    indicators={"rsi": 55.5, "macd": 120.3, "bb_upper": 46000}
)

await pool.execute(
    """
    INSERT INTO market_data (symbol, timestamp, open, high, low, close, volume, indicators)
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
    """,
    data.symbol, data.timestamp, data.open, data.high, data.low,
    data.close, data.volume, data.indicators
)
```

### 5. Check Circuit Breaker

```python
# Get current circuit breaker status
status = await pool.fetchrow("SELECT * FROM get_circuit_breaker_status()")

if status['is_triggered']:
    print(f"⚠️  CIRCUIT BREAKER TRIGGERED!")
    print(f"   Current P&L: CHF {status['current_pnl_chf']}")
    print(f"   Threshold: CHF {status['threshold_chf']}")
else:
    print(f"✓ Circuit breaker OK (P&L: CHF {status['current_pnl_chf']})")
```

### 6. Query Performance Metrics

```python
# Daily performance summary
performance = await pool.fetch("""
    SELECT
        date,
        portfolio_value_chf,
        daily_pnl_chf,
        daily_pnl_pct,
        sharpe_ratio,
        win_rate,
        total_trades
    FROM daily_performance
    ORDER BY date DESC
    LIMIT 30
""")

# Portfolio summary
summary = await pool.fetchrow("SELECT * FROM v_portfolio_summary")
print(f"Open positions: {summary['open_positions']}")
print(f"Win rate: {summary['winning_trades'] / summary['closed_positions'] * 100:.1f}%")
print(f"Total P&L: CHF {summary['total_realized_pnl_chf']:.2f}")
```

## Performance

### Query Performance Targets

All queries must execute in **< 10ms**:
- Position lookups by ID: ~1ms
- Symbol-based queries: ~2-5ms
- Market data time-series: ~3-7ms
- Aggregate queries: ~5-10ms

### Optimization Features

1. **Proper Indexing**
   - Symbol indexes on all tables
   - Composite indexes for common query patterns
   - Time-based indexes for time-series queries

2. **TimescaleDB Compression**
   - Automatic compression after 7 days
   - 10-20x storage reduction
   - Fast decompression on query

3. **Connection Pooling**
   - 10-50 concurrent connections
   - Connection reuse
   - Health monitoring

4. **Retention Policies**
   - Market data: 90 days
   - Daily performance: 2 years
   - Risk events: 1 year

### Monitoring Queries

```sql
-- Check compression status
SELECT * FROM timescaledb_information.compression_settings;

-- Check chunk sizes
SELECT * FROM timescaledb_information.chunks;

-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;

-- Check table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

## Testing

### Run All Tests

```bash
# Set test database
export DB_NAME=trading_system_test

# Create test database
createdb -U postgres trading_system_test
psql -U postgres trading_system_test < workspace/shared/database/schema.sql

# Run tests
pytest workspace/shared/database/tests/test_schema.py -v

# Run with coverage
pytest workspace/shared/database/tests/test_schema.py --cov=workspace.shared.database -v
```

### Test Connection

```bash
# Quick connection test
python -m workspace.shared.database.connection

# Should output:
# Testing database connection...
# ✓ Database connection successful!
#   Latency: 2.5ms
#   Pool size: 10
#   PostgreSQL version: PostgreSQL 16.x...
#   TimescaleDB version: 2.17.x
```

### Test Coverage

Tests cover:
- ✅ All 11 tables created
- ✅ All indexes exist
- ✅ TimescaleDB hypertables working
- ✅ Connection pool (50 concurrent connections)
- ✅ CRUD operations on all tables
- ✅ Foreign key constraints
- ✅ Check constraints
- ✅ Views and functions
- ✅ Performance benchmarks (<10ms)
- ✅ Circuit breaker logic
- ✅ Compression and retention policies

## Maintenance

### Vacuum and Analyze

```bash
# Vacuum all tables (reclaim storage)
psql -U postgres trading_system -c "VACUUM ANALYZE"

# Auto-vacuum is enabled by default
# Check auto-vacuum settings:
psql -U postgres -c "SHOW autovacuum"
```

### Backup and Restore

```bash
# Backup database
pg_dump -U postgres -Fc trading_system > backup_$(date +%Y%m%d).dump

# Restore database
pg_restore -U postgres -d trading_system_restore backup_20251027.dump
```

### Monitor Database Size

```bash
# Database size
psql -U postgres -c "SELECT pg_size_pretty(pg_database_size('trading_system'))"

# Table sizes
psql -U postgres trading_system -c "
SELECT
    tablename,
    pg_size_pretty(pg_total_relation_size('public.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size('public.'||tablename) DESC
"
```

### Compression Status

```sql
-- Check compression status
SELECT
    hypertable_name,
    compression_status,
    uncompressed_total_bytes,
    compressed_total_bytes
FROM timescaledb_information.hypertable_compression_stats;

-- Manually trigger compression
SELECT compress_chunk(i) FROM show_chunks('market_data', older_than => INTERVAL '7 days') i;
```

## Troubleshooting

### TimescaleDB Extension Not Found

```bash
# Check if TimescaleDB is installed
psql -U postgres -c "SELECT * FROM pg_available_extensions WHERE name = 'timescaledb'"

# Install TimescaleDB
brew install timescaledb  # macOS
sudo apt install timescaledb-2-postgresql-16  # Linux

# Enable extension
psql -U postgres trading_system -c "CREATE EXTENSION IF NOT EXISTS timescaledb"
```

### Connection Pool Exhausted

```python
# Increase pool size
pool = DatabasePool(
    max_size=100,  # Increase from 50
    max_inactive_connection_lifetime=600.0  # 10 minutes
)
```

### Slow Queries

```sql
-- Enable query logging
ALTER DATABASE trading_system SET log_min_duration_statement = 100;  -- Log queries > 100ms

-- Check slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

### Disk Space Issues

```bash
# Check disk usage
df -h

# Clean old data (respects retention policies)
SELECT drop_chunks('market_data', older_than => INTERVAL '90 days');

# Vacuum full (reclaim space, requires lock)
VACUUM FULL market_data;
```

### Connection Errors

```python
# Test connection manually
import asyncpg
conn = await asyncpg.connect(
    host="localhost",
    database="trading_system",
    user="postgres"
)
print(await conn.fetchval("SELECT version()"))
await conn.close()
```

## Files

```
workspace/shared/database/
├── schema.sql                    # Complete SQL schema
├── connection.py                 # Async connection pool
├── models.py                     # Pydantic models
├── migrations/
│   └── 001_initial_schema.py    # Alembic migration
├── tests/
│   └── test_schema.py           # Comprehensive tests
└── README.md                    # This file
```

## Next Steps

1. **Position Management** (TASK-002): Implement position tracking logic
2. **Market Data Fetcher**: Connect to exchange APIs for real-time data
3. **LLM Engine Integration**: Connect trading signals to LLM
4. **Risk Manager**: Implement circuit breaker and risk checks
5. **Monitoring**: Add Prometheus metrics and Grafana dashboards

## Support

For issues or questions:
1. Check logs: `tail -f /var/log/postgresql/postgresql-16-main.log`
2. Run health check: `python -m workspace.shared.database.connection`
3. Review test output: `pytest workspace/shared/database/tests/ -v`

---

**Database Version**: 1.0.0
**PostgreSQL**: 16+
**TimescaleDB**: 2.17+
**Created**: 2025-10-27
**Capital**: CHF 2,626.96
**Circuit Breaker**: CHF -183.89 (-7%)
