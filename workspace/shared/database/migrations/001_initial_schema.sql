-- Initial Database Schema with TimescaleDB
-- Trading System - Sprint 1 Stream C
--
-- This migration creates the complete database schema with TimescaleDB
-- hypertables for time-series optimization.
--
-- Author: Infrastructure Specialist
-- Date: 2025-10-28

-- ============================================================================
-- Create Extensions
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- Trades Table (Hypertable)
-- ============================================================================

CREATE TABLE IF NOT EXISTS trades (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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

    -- Constraints
    CONSTRAINT positive_quantity CHECK (quantity > 0),
    CONSTRAINT valid_leverage CHECK (leverage >= 5 AND leverage <= 40)
);

-- Create indexes before converting to hypertable
CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades (symbol);
CREATE INDEX IF NOT EXISTS idx_trades_trade_type ON trades (trade_type);
CREATE INDEX IF NOT EXISTS idx_trades_symbol_timestamp ON trades (symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_trades_order_id ON trades (order_id) WHERE order_id IS NOT NULL;

-- Convert to hypertable for time-series optimization
SELECT create_hypertable(
    'trades',
    'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- ============================================================================
-- Positions Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS positions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    position_id VARCHAR(100) UNIQUE NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL, -- LONG, SHORT

    -- Pricing
    entry_price NUMERIC(20, 8) NOT NULL,
    current_price NUMERIC(20, 8) NOT NULL,
    quantity NUMERIC(20, 8) NOT NULL,
    leverage NUMERIC(5, 2) DEFAULT 1,

    -- P&L
    unrealized_pnl NUMERIC(20, 8) NOT NULL DEFAULT 0,
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

    -- Constraints
    CONSTRAINT positive_quantity CHECK (quantity > 0),
    CONSTRAINT positive_prices CHECK (entry_price > 0 AND current_price > 0),
    CONSTRAINT valid_leverage CHECK (leverage >= 5 AND leverage <= 40),
    CONSTRAINT valid_side CHECK (side IN ('LONG', 'SHORT'))
);

-- Indexes for positions
CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions (symbol);
CREATE INDEX IF NOT EXISTS idx_positions_is_open ON positions (is_open);
CREATE INDEX IF NOT EXISTS idx_positions_opened_at ON positions (opened_at DESC);
CREATE INDEX IF NOT EXISTS idx_positions_symbol_open ON positions (symbol, is_open);

-- ============================================================================
-- Market Data Cache Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS market_data_cache (
    id SERIAL PRIMARY KEY,
    cache_key VARCHAR(255) UNIQUE NOT NULL,
    data JSONB NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT future_expiration CHECK (expires_at > created_at)
);

CREATE INDEX IF NOT EXISTS idx_market_cache_key ON market_data_cache (cache_key);
CREATE INDEX IF NOT EXISTS idx_market_cache_expires ON market_data_cache (expires_at);

-- Cleanup expired cache entries automatically
CREATE INDEX IF NOT EXISTS idx_market_cache_expired ON market_data_cache (expires_at) WHERE expires_at < NOW();

-- ============================================================================
-- Metrics Snapshots (Hypertable)
-- ============================================================================

CREATE TABLE IF NOT EXISTS metrics_snapshots (
    id SERIAL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Trading metrics
    trades_total INTEGER DEFAULT 0,
    trades_successful INTEGER DEFAULT 0,
    trades_failed INTEGER DEFAULT 0,

    -- Financial metrics
    realized_pnl_total NUMERIC(20, 8) DEFAULT 0,
    unrealized_pnl_current NUMERIC(20, 8) DEFAULT 0,
    fees_paid_total NUMERIC(20, 8) DEFAULT 0,
    portfolio_value_chf NUMERIC(20, 8) DEFAULT 0,

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

    PRIMARY KEY (timestamp, id)
);

CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics_snapshots (timestamp DESC);

-- Convert to hypertable
SELECT create_hypertable(
    'metrics_snapshots',
    'timestamp',
    chunk_time_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- ============================================================================
-- System Logs (Hypertable)
-- ============================================================================

CREATE TABLE IF NOT EXISTS system_logs (
    id SERIAL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    level VARCHAR(20) NOT NULL, -- INFO, WARNING, ERROR, CRITICAL
    message TEXT NOT NULL,
    context JSONB,

    PRIMARY KEY (timestamp, id),

    CONSTRAINT valid_log_level CHECK (level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'))
);

CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON system_logs (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_logs_level ON system_logs (level);
CREATE INDEX IF NOT EXISTS idx_logs_level_timestamp ON system_logs (level, timestamp DESC);

-- Convert to hypertable
SELECT create_hypertable(
    'system_logs',
    'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- ============================================================================
-- LLM Requests Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS llm_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    model VARCHAR(100) NOT NULL,
    prompt_tokens INTEGER NOT NULL,
    completion_tokens INTEGER NOT NULL,
    cost_usd NUMERIC(10, 6) NOT NULL,
    latency_ms INTEGER NOT NULL,
    response JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT positive_tokens CHECK (prompt_tokens > 0 AND completion_tokens >= 0),
    CONSTRAINT positive_cost CHECK (cost_usd >= 0),
    CONSTRAINT positive_latency CHECK (latency_ms >= 0)
);

CREATE INDEX IF NOT EXISTS idx_llm_timestamp ON llm_requests (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_llm_model ON llm_requests (model);
CREATE INDEX IF NOT EXISTS idx_llm_cost ON llm_requests (cost_usd DESC);

-- ============================================================================
-- Orders Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    position_id UUID REFERENCES positions(id),
    exchange_order_id VARCHAR(100),
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    order_type VARCHAR(20) NOT NULL,
    quantity NUMERIC(20, 8) NOT NULL,
    price NUMERIC(20, 8),
    filled_quantity NUMERIC(20, 8) DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    fee_chf NUMERIC(20, 8),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT positive_quantity CHECK (quantity > 0),
    CONSTRAINT valid_filled CHECK (filled_quantity >= 0 AND filled_quantity <= quantity),
    CONSTRAINT valid_order_side CHECK (side IN ('BUY', 'SELL')),
    CONSTRAINT valid_order_type CHECK (order_type IN ('MARKET', 'LIMIT', 'STOP_LOSS', 'TAKE_PROFIT')),
    CONSTRAINT valid_order_status CHECK (status IN ('PENDING', 'FILLED', 'PARTIALLY_FILLED', 'CANCELLED', 'REJECTED'))
);

CREATE INDEX IF NOT EXISTS idx_orders_position ON orders (position_id);
CREATE INDEX IF NOT EXISTS idx_orders_exchange ON orders (exchange_order_id) WHERE exchange_order_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders (status);
CREATE INDEX IF NOT EXISTS idx_orders_created ON orders (created_at DESC);

-- ============================================================================
-- Trading Signals Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS trading_signals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(20) NOT NULL,
    signal_type VARCHAR(20) NOT NULL,
    action VARCHAR(10) NOT NULL,
    confidence NUMERIC(5, 4) NOT NULL,
    risk_usd NUMERIC(20, 8),
    reasoning TEXT NOT NULL,
    llm_model VARCHAR(100) NOT NULL,
    llm_tokens INTEGER,
    llm_cost_usd NUMERIC(10, 6),
    executed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_confidence CHECK (confidence >= 0 AND confidence <= 1),
    CONSTRAINT valid_signal_type CHECK (signal_type IN ('ENTRY', 'EXIT', 'HOLD', 'INCREASE', 'DECREASE')),
    CONSTRAINT valid_action CHECK (action IN ('BUY', 'SELL', 'HOLD'))
);

CREATE INDEX IF NOT EXISTS idx_signals_symbol ON trading_signals (symbol);
CREATE INDEX IF NOT EXISTS idx_signals_created ON trading_signals (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_signals_executed ON trading_signals (executed);

-- ============================================================================
-- Retention Policies (Auto-cleanup)
-- ============================================================================

-- Keep trades for 90 days
SELECT add_retention_policy('trades', INTERVAL '90 days', if_not_exists => TRUE);

-- Keep metrics for 30 days
SELECT add_retention_policy('metrics_snapshots', INTERVAL '30 days', if_not_exists => TRUE);

-- Keep logs for 14 days
SELECT add_retention_policy('system_logs', INTERVAL '14 days', if_not_exists => TRUE);

-- ============================================================================
-- Continuous Aggregates (Pre-computed views)
-- ============================================================================

-- Daily trade statistics
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_trade_stats
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', timestamp) AS day,
    symbol,
    COUNT(*) AS trade_count,
    SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) AS winning_trades,
    SUM(CASE WHEN realized_pnl <= 0 THEN 1 ELSE 0 END) AS losing_trades,
    SUM(realized_pnl) AS total_pnl,
    AVG(realized_pnl) AS avg_pnl,
    SUM(fees_paid) AS total_fees,
    AVG(execution_latency_ms) AS avg_latency_ms
FROM trades
WHERE trade_type LIKE 'EXIT_%' AND realized_pnl IS NOT NULL
GROUP BY day, symbol;

-- Refresh policy for continuous aggregate (every hour)
SELECT add_continuous_aggregate_policy(
    'daily_trade_stats',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- Hourly metrics rollup
CREATE MATERIALIZED VIEW IF NOT EXISTS hourly_metrics_rollup
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', timestamp) AS hour,
    AVG(execution_latency_avg_ms) AS avg_latency,
    MAX(execution_latency_p99_ms) AS max_p99_latency,
    SUM(trades_total) AS total_trades,
    SUM(llm_calls_total) AS total_llm_calls,
    AVG(cache_hit_rate_percent) AS avg_cache_hit_rate
FROM metrics_snapshots
GROUP BY hour;

-- Refresh policy for metrics rollup
SELECT add_continuous_aggregate_policy(
    'hourly_metrics_rollup',
    start_offset => INTERVAL '2 hours',
    end_offset => INTERVAL '10 minutes',
    schedule_interval => INTERVAL '10 minutes',
    if_not_exists => TRUE
);

-- ============================================================================
-- Utility Functions
-- ============================================================================

-- Function to update position updated_at timestamp
CREATE OR REPLACE FUNCTION update_position_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for position updates
DROP TRIGGER IF EXISTS update_position_timestamp_trigger ON positions;
CREATE TRIGGER update_position_timestamp_trigger
    BEFORE UPDATE ON positions
    FOR EACH ROW
    EXECUTE FUNCTION update_position_timestamp();

-- Function to clean expired cache entries
CREATE OR REPLACE FUNCTION cleanup_expired_cache()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM market_data_cache WHERE expires_at < NOW();
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Database Metadata
-- ============================================================================

-- Table to track schema version
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    description TEXT
);

-- Record this migration
INSERT INTO schema_migrations (version, description)
VALUES (1, 'Initial schema with TimescaleDB hypertables')
ON CONFLICT (version) DO NOTHING;

-- ============================================================================
-- Comments for Documentation
-- ============================================================================

COMMENT ON TABLE trades IS 'Historical trade records with TimescaleDB optimization';
COMMENT ON TABLE positions IS 'Current and historical position state';
COMMENT ON TABLE metrics_snapshots IS 'System performance metrics snapshots';
COMMENT ON TABLE system_logs IS 'Application logs with structured data';
COMMENT ON TABLE market_data_cache IS 'Fallback cache for Redis failures';
COMMENT ON TABLE llm_requests IS 'LLM API request audit trail';
COMMENT ON TABLE orders IS 'Exchange order tracking';
COMMENT ON TABLE trading_signals IS 'LLM-generated trading signals';

COMMENT ON COLUMN trades.execution_latency_ms IS 'Time from signal to execution in milliseconds';
COMMENT ON COLUMN positions.leverage IS 'Position leverage (5-40x for this system)';
COMMENT ON COLUMN metrics_snapshots.cache_hit_rate_percent IS 'Cache hit rate as percentage (0-100)';
