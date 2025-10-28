# Database Schema Design: LLM-Powered Cryptocurrency Trading System

**Document Version**: 1.0
**Date**: 2025-10-27
**Phase**: P2 - Architecture Design
**Integration Architect**: Claude Integration Architect Agent
**Status**: Final for Review

---

## Executive Summary

This document defines the complete database schema for the trading system using **PostgreSQL 16** with **TimescaleDB 2.17** extension for time-series optimization.

**Key Design Decisions**:
1. **Currency**: All amounts stored in **CHF** (Swiss Franc) with DECIMAL precision
2. **Precision**: DECIMAL(20,8) for prices/amounts (supports crypto precision)
3. **Time-Series**: TimescaleDB hypertables for market_data and performance_metrics
4. **Indexing**: Strategic indexes for trading cycle queries (<10ms)
5. **Audit Trail**: Immutable logs for 7-year compliance

**Performance Targets**:
- Market data inserts: >10,000/second (TimescaleDB optimized)
- Position queries: <5ms (indexed)
- Trading signal lookups: <10ms
- Historical analytics: <100ms (continuous aggregates)

---

## Table of Contents

1. [Database Configuration](#1-database-configuration)
2. [Core Tables](#2-core-tables)
3. [Time-Series Tables](#3-time-series-tables)
4. [Indexing Strategy](#4-indexing-strategy)
5. [Constraints and Validation](#5-constraints-and-validation)
6. [Migration Strategy](#6-migration-strategy)
7. [Backup and Recovery](#7-backup-and-recovery)
8. [Performance Optimization](#8-performance-optimization)

---

## 1. Database Configuration

### 1.1 Database Setup

```sql
-- Create database
CREATE DATABASE trading_db
  WITH
  OWNER = trading_user
  ENCODING = 'UTF8'
  LC_COLLATE = 'en_US.UTF-8'
  LC_CTYPE = 'en_US.UTF-8'
  TABLESPACE = pg_default
  CONNECTION LIMIT = -1;

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pg_trgm for text search (optional)
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

### 1.2 Connection Pooling Configuration

```python
# asyncpg pool configuration
DATABASE_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'trading_db',
    'user': 'trading_user',
    'password': os.getenv('DB_PASSWORD'),
    'min_size': 10,
    'max_size': 50,
    'command_timeout': 30,
    'max_queries': 50000,
    'max_inactive_connection_lifetime': 300
}
```

---

## 2. Core Tables

### 2.1 positions (Position Tracking)

**Purpose**: Track all trading positions (open and closed)

**Schema**:
```sql
CREATE TABLE positions (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Position Identification
    symbol VARCHAR(20) NOT NULL,  -- e.g., 'BTC/USDT'
    side VARCHAR(10) NOT NULL,     -- 'long' or 'short'
    status VARCHAR(20) NOT NULL,   -- 'open', 'closed', 'liquidated'

    -- Position Details
    entry_price DECIMAL(20,8) NOT NULL,      -- Entry price in USDT
    entry_price_chf DECIMAL(20,8) NOT NULL,  -- Entry price converted to CHF
    quantity DECIMAL(20,8) NOT NULL,          -- Position size in base currency
    leverage INTEGER NOT NULL CHECK (leverage BETWEEN 5 AND 40),

    -- Risk Management
    stop_loss_price DECIMAL(20,8),           -- Stop-loss price in USDT
    stop_loss_pct DECIMAL(5,4) NOT NULL,     -- Stop-loss percentage (e.g., 0.0200 for 2%)
    take_profit_price DECIMAL(20,8),         -- Take-profit price in USDT
    take_profit_pct DECIMAL(5,4),            -- Take-profit percentage

    -- Exchange Details
    exchange_order_id VARCHAR(100),          -- Exchange order ID for entry
    exchange_stop_order_id VARCHAR(100),     -- Exchange stop-loss order ID
    exchange VARCHAR(20) NOT NULL DEFAULT 'bybit',

    -- Financial Tracking
    realized_pnl_usdt DECIMAL(20,8),         -- Realized P&L in USDT (when closed)
    realized_pnl_chf DECIMAL(20,8),          -- Realized P&L in CHF (when closed)
    unrealized_pnl_usdt DECIMAL(20,8),       -- Unrealized P&L in USDT (updated periodically)
    unrealized_pnl_chf DECIMAL(20,8),        -- Unrealized P&L in CHF
    fees_usdt DECIMAL(20,8) DEFAULT 0,       -- Trading fees in USDT
    fees_chf DECIMAL(20,8) DEFAULT 0,        -- Trading fees in CHF
    funding_fees_usdt DECIMAL(20,8) DEFAULT 0,  -- Funding fees in USDT
    funding_fees_chf DECIMAL(20,8) DEFAULT 0,   -- Funding fees in CHF

    -- Timestamps
    entry_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    exit_time TIMESTAMPTZ,
    last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Related Records
    trading_signal_id UUID,  -- FK to trading_signals (which signal created this)

    -- Metadata
    notes TEXT,  -- Any additional notes or context
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_positions_status ON positions(status);
CREATE INDEX idx_positions_symbol ON positions(symbol);
CREATE INDEX idx_positions_entry_time ON positions(entry_time DESC);
CREATE INDEX idx_positions_open ON positions(status) WHERE status = 'open';  -- Partial index for fast active position queries
CREATE INDEX idx_positions_signal_id ON positions(trading_signal_id);

-- Comments
COMMENT ON TABLE positions IS 'All trading positions (open, closed, liquidated)';
COMMENT ON COLUMN positions.entry_price_chf IS 'Entry price converted to CHF at time of entry';
COMMENT ON COLUMN positions.realized_pnl_chf IS 'Final P&L in CHF when position closed';
```

**Example Row**:
```sql
INSERT INTO positions (
    symbol, side, status, entry_price, entry_price_chf, quantity, leverage,
    stop_loss_price, stop_loss_pct, exchange_order_id
) VALUES (
    'BTC/USDT', 'long', 'open', 50000.00, 44500.00, 0.002, 10,
    49000.00, 0.0200, 'bybit_order_12345'
);
```

---

### 2.2 orders (Order Tracking)

**Purpose**: Track all orders placed on exchange (entries, exits, stop-losses)

**Schema**:
```sql
CREATE TABLE orders (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Order Identification
    exchange_order_id VARCHAR(100) NOT NULL,  -- Exchange's order ID
    client_order_id VARCHAR(100),              -- Our internal order ID
    position_id UUID REFERENCES positions(id), -- Related position (if applicable)

    -- Order Details
    symbol VARCHAR(20) NOT NULL,
    order_type VARCHAR(20) NOT NULL,  -- 'market', 'limit', 'stop_market', 'stop_limit'
    side VARCHAR(10) NOT NULL,        -- 'buy' or 'sell'
    amount DECIMAL(20,8) NOT NULL,    -- Requested amount
    price DECIMAL(20,8),              -- Limit price (if applicable)
    stop_price DECIMAL(20,8),         -- Stop price (if applicable)

    -- Execution Details
    filled DECIMAL(20,8) DEFAULT 0,   -- Amount filled
    remaining DECIMAL(20,8),          -- Amount remaining
    average_price DECIMAL(20,8),      -- Average fill price
    status VARCHAR(20) NOT NULL,      -- 'open', 'closed', 'canceled', 'expired', 'rejected'

    -- Fees
    fee_amount DECIMAL(20,8) DEFAULT 0,
    fee_currency VARCHAR(10),

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    filled_at TIMESTAMPTZ,
    canceled_at TIMESTAMPTZ,

    -- Exchange Details
    exchange VARCHAR(20) NOT NULL DEFAULT 'bybit',
    exchange_response JSONB,  -- Full exchange response for debugging

    -- Metadata
    notes TEXT
);

-- Indexes
CREATE INDEX idx_orders_exchange_order_id ON orders(exchange_order_id);
CREATE INDEX idx_orders_position_id ON orders(position_id);
CREATE INDEX idx_orders_symbol ON orders(symbol);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created_at ON orders(created_at DESC);

-- Comments
COMMENT ON TABLE orders IS 'All orders placed on exchange';
COMMENT ON COLUMN orders.exchange_response IS 'Full JSON response from exchange for debugging';
```

---

### 2.3 trading_signals (LLM Decision Tracking)

**Purpose**: Record all trading signals generated by LLM

**Schema**:
```sql
CREATE TABLE trading_signals (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Signal Details
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    symbol VARCHAR(20) NOT NULL,
    action VARCHAR(20) NOT NULL,  -- 'buy_to_enter', 'sell_to_enter', 'hold', 'close_position'
    confidence DECIMAL(5,4) NOT NULL CHECK (confidence BETWEEN 0 AND 1),

    -- Risk Parameters
    risk_usd DECIMAL(20,8),       -- Risk amount in USD (if action is entry)
    risk_chf DECIMAL(20,8),       -- Risk amount in CHF
    leverage INTEGER CHECK (leverage BETWEEN 5 AND 40),
    stop_loss_pct DECIMAL(5,4),   -- Stop-loss percentage
    take_profit_pct DECIMAL(5,4), -- Take-profit percentage (optional)

    -- LLM Details
    reasoning TEXT NOT NULL,      -- LLM's reasoning for the decision
    model_used VARCHAR(100) NOT NULL,  -- e.g., 'deepseek-chat', 'qwen3-max'
    provider VARCHAR(50) NOT NULL,     -- e.g., 'deepseek', 'openrouter'
    tokens_input INTEGER,              -- Input tokens used
    tokens_output INTEGER,             -- Output tokens used
    cost_usd DECIMAL(10,6),            -- Cost of LLM call in USD
    latency_ms INTEGER,                -- LLM response latency in milliseconds

    -- Execution Tracking
    executed BOOLEAN NOT NULL DEFAULT FALSE,  -- Was this signal executed?
    execution_result VARCHAR(20),             -- 'success', 'rejected_risk', 'rejected_error', 'skipped'
    execution_notes TEXT,                     -- Details about execution or rejection
    executed_at TIMESTAMPTZ,

    -- Market Context (at time of signal)
    market_price DECIMAL(20,8),
    indicators JSONB,  -- Technical indicators used (EMA, RSI, MACD, etc.)

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_trading_signals_timestamp ON trading_signals(timestamp DESC);
CREATE INDEX idx_trading_signals_symbol ON trading_signals(symbol);
CREATE INDEX idx_trading_signals_action ON trading_signals(action);
CREATE INDEX idx_trading_signals_executed ON trading_signals(executed);

-- Comments
COMMENT ON TABLE trading_signals IS 'All trading signals generated by LLM';
COMMENT ON COLUMN trading_signals.indicators IS 'JSON object with technical indicators at time of signal';
```

**Example Row**:
```sql
INSERT INTO trading_signals (
    symbol, action, confidence, risk_usd, leverage, stop_loss_pct,
    reasoning, model_used, provider, market_price
) VALUES (
    'BTC/USDT', 'buy_to_enter', 0.75, 100.00, 10, 0.0200,
    'Bullish MACD crossover with RSI oversold at 32. EMA20 > EMA50 confirming uptrend.',
    'deepseek-chat', 'deepseek', 50000.00
);
```

---

### 2.4 stop_loss_monitors (Multi-Layer Protection)

**Purpose**: Track application-level stop-loss monitoring (Layer 2 protection)

**Schema**:
```sql
CREATE TABLE stop_loss_monitors (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Related Position
    position_id UUID NOT NULL REFERENCES positions(id),
    symbol VARCHAR(20) NOT NULL,

    -- Stop-Loss Details
    stop_price DECIMAL(20,8) NOT NULL,
    side VARCHAR(10) NOT NULL,  -- 'sell' (for long) or 'buy' (for short)
    amount DECIMAL(20,8) NOT NULL,

    -- Monitoring Status
    status VARCHAR(20) NOT NULL,  -- 'active', 'triggered', 'canceled'
    triggered_at TIMESTAMPTZ,
    trigger_price DECIMAL(20,8),  -- Actual price when triggered

    -- Execution Details (if triggered)
    execution_order_id VARCHAR(100),
    execution_result VARCHAR(20),

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_stop_monitors_position ON stop_loss_monitors(position_id);
CREATE INDEX idx_stop_monitors_status ON stop_loss_monitors(status) WHERE status = 'active';
CREATE INDEX idx_stop_monitors_symbol ON stop_loss_monitors(symbol);

-- Comments
COMMENT ON TABLE stop_loss_monitors IS 'Application-level stop-loss monitoring (Layer 2 protection)';
```

---

### 2.5 account_balances (Account Balance Tracking)

**Purpose**: Track account balance over time for circuit breaker and reporting

**Schema**:
```sql
CREATE TABLE account_balances (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Balance Details
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    total_balance_usdt DECIMAL(20,8) NOT NULL,
    total_balance_chf DECIMAL(20,8) NOT NULL,
    available_balance_usdt DECIMAL(20,8) NOT NULL,
    available_balance_chf DECIMAL(20,8) NOT NULL,
    margin_used_usdt DECIMAL(20,8) NOT NULL,
    margin_used_chf DECIMAL(20,8) NOT NULL,

    -- P&L Tracking
    unrealized_pnl_usdt DECIMAL(20,8) DEFAULT 0,
    unrealized_pnl_chf DECIMAL(20,8) DEFAULT 0,
    realized_pnl_daily_chf DECIMAL(20,8) DEFAULT 0,  -- Daily realized P&L

    -- Exchange Details
    exchange VARCHAR(20) NOT NULL DEFAULT 'bybit',

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_account_balances_timestamp ON account_balances(timestamp DESC);
CREATE INDEX idx_account_balances_daily ON account_balances(DATE(timestamp));

-- Comments
COMMENT ON TABLE account_balances IS 'Account balance snapshots for circuit breaker and reporting';
COMMENT ON COLUMN account_balances.realized_pnl_daily_chf IS 'Cumulative realized P&L for the day in CHF (for circuit breaker)';
```

---

## 3. Time-Series Tables

### 3.1 market_data (OHLCV + Indicators)

**Purpose**: Store market data with technical indicators (TimescaleDB optimized)

**Schema**:
```sql
CREATE TABLE market_data (
    -- Time-Series Key
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,

    -- OHLCV Data
    open DECIMAL(20,8) NOT NULL,
    high DECIMAL(20,8) NOT NULL,
    low DECIMAL(20,8) NOT NULL,
    close DECIMAL(20,8) NOT NULL,
    volume DECIMAL(20,8) NOT NULL,

    -- Technical Indicators (calculated)
    ema_9 DECIMAL(20,8),
    ema_20 DECIMAL(20,8),
    ema_50 DECIMAL(20,8),
    rsi_7 DECIMAL(10,4),
    rsi_14 DECIMAL(10,4),
    macd DECIMAL(20,8),
    macd_signal DECIMAL(20,8),
    macd_hist DECIMAL(20,8),
    bb_upper DECIMAL(20,8),
    bb_middle DECIMAL(20,8),
    bb_lower DECIMAL(20,8),

    -- Metadata
    data_source VARCHAR(20) DEFAULT 'websocket',  -- 'websocket' or 'rest'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Convert to hypertable (TimescaleDB)
SELECT create_hypertable('market_data', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Create index for symbol-based queries
CREATE INDEX idx_market_data_symbol_time ON market_data (symbol, time DESC);

-- Enable compression (after 7 days)
ALTER TABLE market_data SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol',
    timescaledb.compress_orderby = 'time DESC'
);

SELECT add_compression_policy('market_data', INTERVAL '7 days');

-- Data retention (keep 90 days)
SELECT add_retention_policy('market_data', INTERVAL '90 days');

-- Comments
COMMENT ON TABLE market_data IS 'Time-series market data with indicators (TimescaleDB hypertable)';
```

**Continuous Aggregate - 1 Hour OHLCV**:
```sql
CREATE MATERIALIZED VIEW market_data_1h
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS bucket,
    symbol,
    first(open, time) AS open,
    max(high) AS high,
    min(low) AS low,
    last(close, time) AS close,
    sum(volume) AS volume
FROM market_data
GROUP BY bucket, symbol;

-- Refresh policy (keep up to date)
SELECT add_continuous_aggregate_policy('market_data_1h',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour'
);
```

---

### 3.2 performance_metrics (System Performance)

**Purpose**: Track system performance metrics (TimescaleDB optimized)

**Schema**:
```sql
CREATE TABLE performance_metrics (
    -- Time-Series Key
    time TIMESTAMPTZ NOT NULL,
    metric_name VARCHAR(100) NOT NULL,

    -- Metric Value
    value DECIMAL(20,8) NOT NULL,
    unit VARCHAR(20),  -- 'ms', 'count', 'chf', 'usd', 'percentage'

    -- Context
    component VARCHAR(50),  -- 'market_data', 'decision_engine', 'trade_executor', etc.
    details JSONB,          -- Additional metric details

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Convert to hypertable
SELECT create_hypertable('performance_metrics', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Indexes
CREATE INDEX idx_perf_metrics_name_time ON performance_metrics (metric_name, time DESC);
CREATE INDEX idx_perf_metrics_component ON performance_metrics (component);

-- Compression (after 7 days)
ALTER TABLE performance_metrics SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'metric_name, component'
);

SELECT add_compression_policy('performance_metrics', INTERVAL '7 days');

-- Retention (keep 1 year)
SELECT add_retention_policy('performance_metrics', INTERVAL '1 year');

-- Comments
COMMENT ON TABLE performance_metrics IS 'System performance metrics (latency, throughput, costs, etc.)';
```

**Example Metrics**:
```sql
-- Trading cycle latency
INSERT INTO performance_metrics (time, metric_name, value, unit, component)
VALUES (NOW(), 'trading_cycle_latency', 1234, 'ms', 'coordinator');

-- LLM cost
INSERT INTO performance_metrics (time, metric_name, value, unit, component)
VALUES (NOW(), 'llm_cost', 0.002, 'usd', 'decision_engine');

-- Position reconciliation
INSERT INTO performance_metrics (time, metric_name, value, unit, component)
VALUES (NOW(), 'position_reconciliation_discrepancies', 0, 'count', 'position_manager');
```

---

### 3.3 audit_logs (Immutable Audit Trail)

**Purpose**: Immutable audit trail for compliance (7-year retention)

**Schema**:
```sql
CREATE TABLE audit_logs (
    -- Primary Key
    id BIGSERIAL PRIMARY KEY,

    -- Timestamp
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Event Details
    event_type VARCHAR(50) NOT NULL,  -- 'position_opened', 'position_closed', 'order_placed', etc.
    actor VARCHAR(100) NOT NULL,      -- 'system', 'operator', 'llm'
    action VARCHAR(100) NOT NULL,     -- Descriptive action

    -- Context
    entity_type VARCHAR(50),  -- 'position', 'order', 'signal', etc.
    entity_id UUID,           -- ID of affected entity
    symbol VARCHAR(20),

    -- Details
    details JSONB NOT NULL,   -- Full event details
    result VARCHAR(20),       -- 'success', 'failure', 'rejected'

    -- Metadata
    ip_address INET,
    user_agent TEXT
);

-- Convert to hypertable
SELECT create_hypertable('audit_logs', 'timestamp',
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE
);

-- Indexes
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX idx_audit_logs_event_type ON audit_logs(event_type);
CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_logs_symbol ON audit_logs(symbol);

-- Retention (7 years for compliance)
SELECT add_retention_policy('audit_logs', INTERVAL '7 years');

-- Prevent updates and deletes (immutable)
CREATE RULE audit_logs_no_update AS ON UPDATE TO audit_logs DO INSTEAD NOTHING;
CREATE RULE audit_logs_no_delete AS ON DELETE TO audit_logs DO INSTEAD NOTHING;

-- Comments
COMMENT ON TABLE audit_logs IS 'Immutable audit trail for compliance (7-year retention)';
```

**Example Audit Log**:
```sql
INSERT INTO audit_logs (event_type, actor, action, entity_type, entity_id, symbol, details, result)
VALUES (
    'position_opened',
    'system',
    'Opened long position based on LLM signal',
    'position',
    '123e4567-e89b-12d3-a456-426614174000',
    'BTC/USDT',
    '{"signal_confidence": 0.75, "entry_price": 50000, "leverage": 10, "stop_loss": 49000}'::jsonb,
    'success'
);
```

---

## 4. Indexing Strategy

### 4.1 Index Performance Guidelines

**Index Priorities**:
1. **Critical (< 5ms queries)**: Active positions, current balances, open orders
2. **High (< 10ms queries)**: Recent signals, position history, market data
3. **Medium (< 100ms queries)**: Historical analytics, aggregated metrics

### 4.2 Index Summary

| Table | Index | Purpose | Expected Usage |
|-------|-------|---------|----------------|
| **positions** | `idx_positions_open` | Fast lookup of active positions | Every trading cycle (480x/day) |
| **positions** | `idx_positions_symbol` | Symbol-based queries | Frequent |
| **orders** | `idx_orders_exchange_order_id` | Order reconciliation | After every order |
| **orders** | `idx_orders_position_id` | Position → Orders lookup | Frequent |
| **trading_signals** | `idx_trading_signals_timestamp` | Recent signals | Dashboard, analytics |
| **market_data** | `idx_market_data_symbol_time` | Time-series queries | LLM prompt building |
| **audit_logs** | `idx_audit_logs_timestamp` | Audit queries | Compliance reporting |

---

## 5. Constraints and Validation

### 5.1 Check Constraints

```sql
-- Leverage limits
ALTER TABLE positions
ADD CONSTRAINT chk_positions_leverage
CHECK (leverage BETWEEN 5 AND 40);

-- Stop-loss percentage limits
ALTER TABLE positions
ADD CONSTRAINT chk_positions_stop_loss
CHECK (stop_loss_pct BETWEEN 0.01 AND 0.10);

-- Confidence range
ALTER TABLE trading_signals
ADD CONSTRAINT chk_signals_confidence
CHECK (confidence BETWEEN 0 AND 1);

-- Valid sides
ALTER TABLE positions
ADD CONSTRAINT chk_positions_side
CHECK (side IN ('long', 'short'));

-- Valid actions
ALTER TABLE trading_signals
ADD CONSTRAINT chk_signals_action
CHECK (action IN ('buy_to_enter', 'sell_to_enter', 'hold', 'close_position'));
```

### 5.2 Foreign Key Constraints

```sql
-- Orders → Positions
ALTER TABLE orders
ADD CONSTRAINT fk_orders_position
FOREIGN KEY (position_id) REFERENCES positions(id) ON DELETE SET NULL;

-- Stop-Loss Monitors → Positions
ALTER TABLE stop_loss_monitors
ADD CONSTRAINT fk_monitors_position
FOREIGN KEY (position_id) REFERENCES positions(id) ON DELETE CASCADE;

-- Positions → Trading Signals
ALTER TABLE positions
ADD CONSTRAINT fk_positions_signal
FOREIGN KEY (trading_signal_id) REFERENCES trading_signals(id) ON DELETE SET NULL;
```

---

## 6. Migration Strategy

### 6.1 Initial Schema Creation

```bash
# migration_001_initial_schema.sql
-- Run all CREATE TABLE statements
-- Run all CREATE INDEX statements
-- Run TimescaleDB hypertable conversions
-- Run compression and retention policies
```

### 6.2 Migration Versioning

```sql
CREATE TABLE schema_migrations (
    id SERIAL PRIMARY KEY,
    version VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO schema_migrations (version, description)
VALUES ('001', 'Initial schema creation');
```

### 6.3 Rollback Strategy

```sql
-- Each migration has corresponding rollback script
-- migration_001_initial_schema_rollback.sql

DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS performance_metrics CASCADE;
DROP TABLE IF EXISTS market_data CASCADE;
DROP TABLE IF EXISTS account_balances CASCADE;
DROP TABLE IF EXISTS stop_loss_monitors CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS trading_signals CASCADE;
DROP TABLE IF EXISTS positions CASCADE;

DELETE FROM schema_migrations WHERE version = '001';
```

---

## 7. Backup and Recovery

### 7.1 Backup Strategy

```yaml
backup_schedule:
  full_backup:
    frequency: Daily at 02:00 UTC
    retention: 30 days
    method: pg_dump with TimescaleDB support

  continuous_archiving:
    method: WAL archiving
    retention: 7 days
    location: S3 or local storage

  critical_tables:
    positions:
      frequency: After every closed position
      method: Incremental backup
    audit_logs:
      frequency: Continuous (WAL)
      retention: 7 years
```

**Backup Command**:
```bash
# Full backup with TimescaleDB
pg_dump -h localhost -U trading_user -d trading_db \
  --format=custom \
  --file=backup_$(date +%Y%m%d_%H%M%S).dump \
  --verbose

# Restore
pg_restore -h localhost -U trading_user -d trading_db \
  --clean --if-exists \
  backup_20251027_020000.dump
```

---

### 7.2 Point-in-Time Recovery

```bash
# Enable WAL archiving in postgresql.conf
wal_level = replica
archive_mode = on
archive_command = 'test ! -f /backup/wal/%f && cp %p /backup/wal/%f'

# Restore to specific time
pg_restore --create --dbname=postgres backup.dump
# Then apply WAL files up to recovery target
```

---

## 8. Performance Optimization

### 8.1 Query Performance Targets

| Query Type | Target | Optimization Strategy |
|------------|--------|----------------------|
| **Get active positions** | <5ms | Partial index on status='open' |
| **Get market data (latest)** | <10ms | TimescaleDB time-based index + cache |
| **Insert market data** | <1ms | TimescaleDB batch inserts (COPY) |
| **Get recent signals** | <10ms | Index on timestamp DESC |
| **Aggregate performance** | <100ms | Continuous aggregates (pre-computed) |

---

### 8.2 Database Tuning

**PostgreSQL Configuration** (postgresql.conf):
```conf
# Memory Settings
shared_buffers = 2GB                # 25% of system RAM
effective_cache_size = 6GB          # 75% of system RAM
work_mem = 64MB                     # For sorting/aggregation
maintenance_work_mem = 512MB        # For VACUUM, CREATE INDEX

# Checkpoint Settings
checkpoint_timeout = 15min
checkpoint_completion_target = 0.9
max_wal_size = 4GB

# Query Planner
random_page_cost = 1.1              # For SSD
effective_io_concurrency = 200      # For SSD

# Connections
max_connections = 100

# TimescaleDB Settings
timescaledb.max_background_workers = 8
```

---

### 8.3 Connection Pooling

```python
# asyncpg pool configuration (recommended)
pool = await asyncpg.create_pool(
    dsn='postgresql://trading_user:password@localhost/trading_db',
    min_size=10,
    max_size=50,
    command_timeout=30,
    max_queries=50000,
    max_inactive_connection_lifetime=300
)
```

---

## 9. Monitoring and Maintenance

### 9.1 Health Checks

```sql
-- Check table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Check index usage
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan AS index_scans,
    idx_tup_read AS tuples_read,
    idx_tup_fetch AS tuples_fetched
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;

-- Check TimescaleDB hypertable stats
SELECT * FROM timescaledb_information.hypertables;

-- Check compression
SELECT * FROM timescaledb_information.compression_settings;
```

---

### 9.2 Maintenance Tasks

```sql
-- Vacuum and analyze (daily)
VACUUM ANALYZE positions;
VACUUM ANALYZE orders;
VACUUM ANALYZE trading_signals;

-- Reindex (weekly)
REINDEX TABLE positions;

-- Update statistics (after significant data changes)
ANALYZE positions;
```

---

## 10. Data Integrity Validation

### 10.1 Validation Queries

```sql
-- Check for orphaned orders (no corresponding position)
SELECT COUNT(*)
FROM orders
WHERE position_id IS NOT NULL
  AND position_id NOT IN (SELECT id FROM positions);

-- Check for positions without entry orders
SELECT COUNT(*)
FROM positions
WHERE status IN ('open', 'closed')
  AND exchange_order_id NOT IN (SELECT exchange_order_id FROM orders);

-- Validate stop-loss percentages
SELECT COUNT(*)
FROM positions
WHERE stop_loss_pct NOT BETWEEN 0.01 AND 0.10;

-- Check for daily loss limit violations
SELECT
    DATE(entry_time) AS trade_date,
    SUM(realized_pnl_chf) AS daily_pnl
FROM positions
WHERE status = 'closed'
GROUP BY DATE(entry_time)
HAVING SUM(realized_pnl_chf) < -131.35;  -- -5% of CHF 2,626.96
```

---

## 11. Sample Queries

### 11.1 Trading Cycle Queries

```sql
-- Get all active positions
SELECT *
FROM positions
WHERE status = 'open'
ORDER BY entry_time DESC;

-- Get latest market data for symbol
SELECT *
FROM market_data
WHERE symbol = 'BTC/USDT'
ORDER BY time DESC
LIMIT 1;

-- Get recent trading signals (last hour)
SELECT *
FROM trading_signals
WHERE timestamp > NOW() - INTERVAL '1 hour'
ORDER BY timestamp DESC;

-- Calculate current daily P&L
SELECT
    COALESCE(SUM(realized_pnl_chf), 0) AS realized_pnl,
    COALESCE(SUM(unrealized_pnl_chf), 0) AS unrealized_pnl,
    COALESCE(SUM(realized_pnl_chf), 0) + COALESCE(SUM(unrealized_pnl_chf), 0) AS total_pnl
FROM positions
WHERE DATE(entry_time) = CURRENT_DATE;
```

---

### 11.2 Analytics Queries

```sql
-- Performance by symbol (last 30 days)
SELECT
    symbol,
    COUNT(*) AS total_trades,
    SUM(CASE WHEN realized_pnl_chf > 0 THEN 1 ELSE 0 END) AS winning_trades,
    SUM(realized_pnl_chf) AS total_pnl,
    AVG(realized_pnl_chf) AS avg_pnl,
    MAX(realized_pnl_chf) AS max_win,
    MIN(realized_pnl_chf) AS max_loss
FROM positions
WHERE status = 'closed'
  AND entry_time > NOW() - INTERVAL '30 days'
GROUP BY symbol
ORDER BY total_pnl DESC;

-- LLM cost analysis
SELECT
    model_used,
    COUNT(*) AS total_calls,
    SUM(tokens_input) AS total_input_tokens,
    SUM(tokens_output) AS total_output_tokens,
    SUM(cost_usd) AS total_cost
FROM trading_signals
WHERE timestamp > NOW() - INTERVAL '30 days'
GROUP BY model_used;

-- System performance (average latencies)
SELECT
    metric_name,
    component,
    AVG(value) AS avg_value,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY value) AS p95_value,
    MAX(value) AS max_value
FROM performance_metrics
WHERE time > NOW() - INTERVAL '24 hours'
  AND unit = 'ms'
GROUP BY metric_name, component
ORDER BY avg_value DESC;
```

---

## Document Control

**Version History**:
| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-27 | Integration Architect | Initial database schema design |

**Approval**:
- [ ] Integration Architect: ___________________ Date: ___________
- [ ] Database Administrator: ___________________ Date: ___________
- [ ] Security Auditor: ___________________ Date: ___________

**Document Location**: `/Users/tobiprivat/Documents/GitProjects/personal/trader/PRPs/architecture/database-schema.md`

---

**END OF DATABASE SCHEMA DOCUMENT**

This schema supports CHF 2,626.96 capital tracking, -7% daily loss circuit breaker (CHF 183.89), and 7-year audit compliance. TimescaleDB provides 20x insert and 450x query performance for time-series data. Ready for migration implementation.
