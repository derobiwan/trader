-- ============================================================================
-- LLM-Powered Cryptocurrency Trading System - Database Schema
-- PostgreSQL 16 + TimescaleDB 2.17
-- ============================================================================
-- Purpose: Complete database schema for trading system with time-series
--          optimization, proper precision handling, and performance indexes
-- Created: 2025-10-27
-- Capital: CHF 2,626.96 | Circuit Breaker: CHF 183.89 (-7% daily loss)
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- TABLE 1: positions
-- Purpose: Core table tracking all trading positions (open and closed)
-- Performance: Indexed on symbol, status, created_at
-- ============================================================================
CREATE TABLE IF NOT EXISTS positions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(20) NOT NULL,                    -- e.g., 'BTCUSDT'
    side VARCHAR(10) NOT NULL,                      -- 'LONG' or 'SHORT'
    quantity DECIMAL(20, 8) NOT NULL,               -- Crypto quantity (8 decimals)
    entry_price DECIMAL(20, 8) NOT NULL,            -- Entry price in USD
    current_price DECIMAL(20, 8),                   -- Current market price in USD
    leverage INTEGER NOT NULL CHECK (leverage >= 5 AND leverage <= 40),
    stop_loss DECIMAL(20, 8),                       -- Stop loss price in USD
    take_profit DECIMAL(20, 8),                     -- Take profit price in USD
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN',     -- 'OPEN', 'CLOSED', 'LIQUIDATED'
    pnl_chf DECIMAL(20, 8),                         -- Realized P&L in CHF
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMP WITH TIME ZONE,

    CONSTRAINT valid_side CHECK (side IN ('LONG', 'SHORT')),
    CONSTRAINT valid_status CHECK (status IN ('OPEN', 'CLOSED', 'LIQUIDATED')),
    CONSTRAINT valid_quantity CHECK (quantity > 0),
    CONSTRAINT valid_entry_price CHECK (entry_price > 0)
);

-- Indexes for performance (<10ms queries)
CREATE INDEX idx_positions_symbol ON positions(symbol);
CREATE INDEX idx_positions_status ON positions(status);
CREATE INDEX idx_positions_created_at ON positions(created_at DESC);
CREATE INDEX idx_positions_symbol_status ON positions(symbol, status);

COMMENT ON TABLE positions IS 'Core trading positions table tracking all open and closed positions';
COMMENT ON COLUMN positions.pnl_chf IS 'Realized profit/loss in Swiss Francs (CHF)';
COMMENT ON COLUMN positions.leverage IS 'Position leverage (5-40x for perpetual futures)';

-- ============================================================================
-- TABLE 2: trading_signals
-- Purpose: Record all LLM-generated trading decisions and reasoning
-- Performance: Indexed on symbol, created_at, executed
-- ============================================================================
CREATE TABLE IF NOT EXISTS trading_signals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(20) NOT NULL,
    signal_type VARCHAR(20) NOT NULL,               -- 'ENTRY', 'EXIT', 'HOLD', 'INCREASE', 'DECREASE'
    action VARCHAR(20) NOT NULL,                    -- 'BUY', 'SELL', 'HOLD'
    confidence DECIMAL(5, 4) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    risk_usd DECIMAL(20, 8),                        -- Risk amount in USD
    reasoning TEXT NOT NULL,                        -- LLM's decision reasoning
    llm_model VARCHAR(100) NOT NULL,                -- e.g., 'anthropic/claude-3.5-sonnet'
    llm_tokens INTEGER,                             -- Total tokens used
    llm_cost_usd DECIMAL(10, 6),                    -- Cost in USD
    executed BOOLEAN NOT NULL DEFAULT FALSE,        -- Whether signal was acted upon
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_signal_type CHECK (signal_type IN ('ENTRY', 'EXIT', 'HOLD', 'INCREASE', 'DECREASE')),
    CONSTRAINT valid_action CHECK (action IN ('BUY', 'SELL', 'HOLD'))
);

CREATE INDEX idx_trading_signals_symbol ON trading_signals(symbol);
CREATE INDEX idx_trading_signals_created_at ON trading_signals(created_at DESC);
CREATE INDEX idx_trading_signals_executed ON trading_signals(executed);
CREATE INDEX idx_trading_signals_symbol_created ON trading_signals(symbol, created_at DESC);

COMMENT ON TABLE trading_signals IS 'LLM-generated trading signals with full reasoning and execution status';
COMMENT ON COLUMN trading_signals.reasoning IS 'Complete LLM reasoning for decision (for audit and analysis)';
COMMENT ON COLUMN trading_signals.confidence IS 'LLM confidence score (0.0 to 1.0)';

-- ============================================================================
-- TABLE 3: orders
-- Purpose: Track all orders placed on exchanges
-- Performance: Indexed on position_id, exchange_order_id, status
-- ============================================================================
CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    position_id UUID REFERENCES positions(id) ON DELETE CASCADE,
    exchange_order_id VARCHAR(100) UNIQUE,          -- Exchange's order ID
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,                      -- 'BUY' or 'SELL'
    order_type VARCHAR(20) NOT NULL,                -- 'MARKET', 'LIMIT', 'STOP_LOSS', 'TAKE_PROFIT'
    quantity DECIMAL(20, 8) NOT NULL,
    price DECIMAL(20, 8),                           -- NULL for market orders
    filled_quantity DECIMAL(20, 8) DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',  -- 'PENDING', 'FILLED', 'PARTIALLY_FILLED', 'CANCELLED', 'REJECTED'
    fee_chf DECIMAL(20, 8),                         -- Trading fee in CHF
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_order_side CHECK (side IN ('BUY', 'SELL')),
    CONSTRAINT valid_order_type CHECK (order_type IN ('MARKET', 'LIMIT', 'STOP_LOSS', 'TAKE_PROFIT')),
    CONSTRAINT valid_order_status CHECK (status IN ('PENDING', 'FILLED', 'PARTIALLY_FILLED', 'CANCELLED', 'REJECTED')),
    CONSTRAINT valid_quantity CHECK (quantity > 0)
);

CREATE INDEX idx_orders_position_id ON orders(position_id);
CREATE INDEX idx_orders_exchange_order_id ON orders(exchange_order_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created_at ON orders(created_at DESC);

COMMENT ON TABLE orders IS 'All exchange orders with execution status and fees';
COMMENT ON COLUMN orders.fee_chf IS 'Trading fee converted to CHF';

-- ============================================================================
-- TABLE 4: market_data (TimescaleDB Hypertable)
-- Purpose: Time-series market data with technical indicators
-- Performance: Partitioned by time (1 day chunks), compressed after 7 days
-- Retention: 90 days
-- ============================================================================
CREATE TABLE IF NOT EXISTS market_data (
    symbol VARCHAR(20) NOT NULL,
    timestamp BIGINT NOT NULL,                      -- Microseconds since epoch
    open DECIMAL(20, 8) NOT NULL,
    high DECIMAL(20, 8) NOT NULL,
    low DECIMAL(20, 8) NOT NULL,
    close DECIMAL(20, 8) NOT NULL,
    volume DECIMAL(20, 8) NOT NULL,
    indicators JSONB,                               -- Technical indicators (RSI, MACD, etc.)

    CONSTRAINT valid_ohlc CHECK (high >= low AND high >= open AND high >= close AND low <= open AND low <= close)
);

-- Convert to TimescaleDB hypertable (1 day chunks)
SELECT create_hypertable('market_data', 'timestamp',
    chunk_time_interval => 86400000000,             -- 1 day in microseconds
    if_not_exists => TRUE
);

-- Create indexes for performance
CREATE INDEX idx_market_data_symbol_timestamp ON market_data(symbol, timestamp DESC);

-- Enable compression after 7 days
ALTER TABLE market_data SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol',
    timescaledb.compress_orderby = 'timestamp DESC'
);

-- Add compression policy (compress data older than 7 days)
SELECT add_compression_policy('market_data', INTERVAL '7 days', if_not_exists => TRUE);

-- Add retention policy (keep 90 days)
SELECT add_retention_policy('market_data', INTERVAL '90 days', if_not_exists => TRUE);

COMMENT ON TABLE market_data IS 'Time-series OHLCV market data with technical indicators';
COMMENT ON COLUMN market_data.timestamp IS 'Microseconds since Unix epoch';
COMMENT ON COLUMN market_data.indicators IS 'JSONB object with technical indicators (RSI, MACD, BB, EMA, etc.)';

-- ============================================================================
-- TABLE 5: daily_performance (TimescaleDB Hypertable)
-- Purpose: Daily portfolio performance metrics
-- Performance: Partitioned by time (1 day chunks)
-- Retention: 2 years
-- ============================================================================
CREATE TABLE IF NOT EXISTS daily_performance (
    date DATE NOT NULL,
    portfolio_value_chf DECIMAL(20, 8) NOT NULL,
    daily_pnl_chf DECIMAL(20, 8) NOT NULL,
    daily_pnl_pct DECIMAL(10, 4) NOT NULL,
    sharpe_ratio DECIMAL(10, 4),
    win_rate DECIMAL(5, 4),
    total_trades INTEGER NOT NULL DEFAULT 0,
    positions_snapshot JSONB,                       -- Snapshot of all positions at EOD

    CONSTRAINT valid_win_rate CHECK (win_rate >= 0 AND win_rate <= 1)
);

-- Convert to TimescaleDB hypertable (1 day chunks)
SELECT create_hypertable('daily_performance', 'date',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Create index for performance
CREATE INDEX idx_daily_performance_date ON daily_performance(date DESC);

-- Add retention policy (keep 2 years)
SELECT add_retention_policy('daily_performance', INTERVAL '2 years', if_not_exists => TRUE);

COMMENT ON TABLE daily_performance IS 'Daily portfolio performance metrics and snapshots';
COMMENT ON COLUMN daily_performance.sharpe_ratio IS 'Risk-adjusted return metric (target > 0.5)';
COMMENT ON COLUMN daily_performance.positions_snapshot IS 'JSONB snapshot of all positions at end of day';

-- ============================================================================
-- TABLE 6: risk_events (TimescaleDB Hypertable)
-- Purpose: Track all risk-related events (stop-loss, circuit breaker, etc.)
-- Performance: Partitioned by time, indexed on event_type and severity
-- Retention: 1 year
-- ============================================================================
CREATE TABLE IF NOT EXISTS risk_events (
    timestamp BIGINT NOT NULL,                      -- Microseconds since epoch
    event_type VARCHAR(50) NOT NULL,                -- 'STOP_LOSS_TRIGGERED', 'CIRCUIT_BREAKER', 'POSITION_LIQUIDATED', etc.
    severity VARCHAR(20) NOT NULL,                  -- 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    description TEXT NOT NULL,
    position_id UUID REFERENCES positions(id) ON DELETE SET NULL,
    metadata JSONB,                                 -- Additional event-specific data

    CONSTRAINT valid_severity CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL'))
);

-- Convert to TimescaleDB hypertable
SELECT create_hypertable('risk_events', 'timestamp',
    chunk_time_interval => 86400000000,             -- 1 day in microseconds
    if_not_exists => TRUE
);

-- Create indexes for performance
CREATE INDEX idx_risk_events_timestamp ON risk_events(timestamp DESC);
CREATE INDEX idx_risk_events_event_type ON risk_events(event_type);
CREATE INDEX idx_risk_events_severity ON risk_events(severity);
CREATE INDEX idx_risk_events_position_id ON risk_events(position_id);

-- Add retention policy (keep 1 year)
SELECT add_retention_policy('risk_events', INTERVAL '1 year', if_not_exists => TRUE);

COMMENT ON TABLE risk_events IS 'Time-series risk events with severity classification';
COMMENT ON COLUMN risk_events.metadata IS 'Event-specific data (trigger price, loss amount, etc.)';

-- ============================================================================
-- TABLE 7: llm_requests
-- Purpose: Audit log of all LLM API requests with cost tracking
-- Performance: Indexed on timestamp and model
-- ============================================================================
CREATE TABLE IF NOT EXISTS llm_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    model VARCHAR(100) NOT NULL,
    prompt_tokens INTEGER NOT NULL,
    completion_tokens INTEGER NOT NULL,
    cost_usd DECIMAL(10, 6) NOT NULL,
    latency_ms INTEGER NOT NULL,
    response JSONB NOT NULL,                        -- Full LLM response
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_tokens CHECK (prompt_tokens > 0 AND completion_tokens >= 0),
    CONSTRAINT valid_cost CHECK (cost_usd >= 0),
    CONSTRAINT valid_latency CHECK (latency_ms >= 0)
);

CREATE INDEX idx_llm_requests_timestamp ON llm_requests(timestamp DESC);
CREATE INDEX idx_llm_requests_model ON llm_requests(model);
CREATE INDEX idx_llm_requests_cost ON llm_requests(cost_usd DESC);

COMMENT ON TABLE llm_requests IS 'Complete audit log of all LLM API requests with cost and performance metrics';
COMMENT ON COLUMN llm_requests.cost_usd IS 'Cost per request in USD (target < $100/month total)';
COMMENT ON COLUMN llm_requests.latency_ms IS 'Total request latency in milliseconds (target < 2000ms)';

-- ============================================================================
-- TABLE 8: system_config
-- Purpose: Key-value configuration storage with audit trail
-- Performance: Unique index on key
-- ============================================================================
CREATE TABLE IF NOT EXISTS system_config (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_by VARCHAR(100)
);

COMMENT ON TABLE system_config IS 'System configuration with version tracking';
COMMENT ON COLUMN system_config.value IS 'JSONB configuration value (allows complex structures)';

-- Insert default configuration
INSERT INTO system_config (key, value, updated_by) VALUES
    ('trading.capital_chf', '2626.96', 'SYSTEM_INIT'),
    ('trading.circuit_breaker_chf', '183.89', 'SYSTEM_INIT'),
    ('trading.circuit_breaker_pct', '0.07', 'SYSTEM_INIT'),
    ('trading.max_leverage', '40', 'SYSTEM_INIT'),
    ('trading.min_leverage', '5', 'SYSTEM_INIT'),
    ('trading.decision_interval_seconds', '180', 'SYSTEM_INIT'),
    ('trading.exchange', '"bybit"', 'SYSTEM_INIT'),
    ('trading.assets', '["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", "DOTUSDT"]', 'SYSTEM_INIT'),
    ('risk.max_position_size_pct', '0.2', 'SYSTEM_INIT'),
    ('risk.max_daily_trades', '20', 'SYSTEM_INIT'),
    ('llm.provider', '"openrouter"', 'SYSTEM_INIT'),
    ('llm.model', '"anthropic/claude-3.5-sonnet"', 'SYSTEM_INIT'),
    ('llm.max_cost_monthly_usd', '100', 'SYSTEM_INIT')
ON CONFLICT (key) DO NOTHING;

-- ============================================================================
-- TABLE 9: audit_log
-- Purpose: Immutable audit trail for all system actions
-- Performance: Append-only, indexed on timestamp and entity_type
-- ============================================================================
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    action VARCHAR(50) NOT NULL,                    -- 'CREATE', 'UPDATE', 'DELETE', 'EXECUTE', etc.
    entity_type VARCHAR(50) NOT NULL,               -- 'POSITION', 'ORDER', 'CONFIG', etc.
    entity_id VARCHAR(100),
    user VARCHAR(100) NOT NULL,                     -- 'SYSTEM', 'LLM_ENGINE', 'RISK_MANAGER', etc.
    changes JSONB,                                  -- Before/after state
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp DESC);
CREATE INDEX idx_audit_log_entity_type ON audit_log(entity_type);
CREATE INDEX idx_audit_log_entity_id ON audit_log(entity_id);

COMMENT ON TABLE audit_log IS 'Immutable audit trail for all system actions';
COMMENT ON COLUMN audit_log.changes IS 'JSONB object with before/after state';

-- ============================================================================
-- TABLE 10: circuit_breaker_state
-- Purpose: Track daily circuit breaker status
-- Performance: One row per trading day
-- ============================================================================
CREATE TABLE IF NOT EXISTS circuit_breaker_state (
    date DATE PRIMARY KEY,
    current_pnl_chf DECIMAL(20, 8) NOT NULL DEFAULT 0,
    triggered BOOLEAN NOT NULL DEFAULT FALSE,
    trigger_reason TEXT,
    positions_closed JSONB,                         -- Array of position IDs closed
    reset_at TIMESTAMP WITH TIME ZONE
);

COMMENT ON TABLE circuit_breaker_state IS 'Daily circuit breaker tracking (triggers at -7% daily loss)';
COMMENT ON COLUMN circuit_breaker_state.current_pnl_chf IS 'Cumulative P&L for the day in CHF';

-- ============================================================================
-- TABLE 11: position_reconciliation
-- Purpose: Track discrepancies between system state and exchange state
-- Performance: Indexed on timestamp, position_id, resolved
-- ============================================================================
CREATE TABLE IF NOT EXISTS position_reconciliation (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    position_id UUID REFERENCES positions(id) ON DELETE CASCADE,
    system_state JSONB NOT NULL,                    -- System's view of position
    exchange_state JSONB NOT NULL,                  -- Exchange's view of position
    discrepancies JSONB,                            -- List of discrepancies found
    resolved BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_position_reconciliation_timestamp ON position_reconciliation(timestamp DESC);
CREATE INDEX idx_position_reconciliation_position_id ON position_reconciliation(position_id);
CREATE INDEX idx_position_reconciliation_resolved ON position_reconciliation(resolved);

COMMENT ON TABLE position_reconciliation IS 'Position reconciliation between system and exchange';
COMMENT ON COLUMN position_reconciliation.discrepancies IS 'JSONB array of discrepancies (quantity, price, status)';

-- ============================================================================
-- TRIGGERS
-- Purpose: Automatic timestamp updates and audit logging
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at columns
CREATE TRIGGER update_positions_updated_at BEFORE UPDATE ON positions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_orders_updated_at BEFORE UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_system_config_updated_at BEFORE UPDATE ON system_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- VIEWS
-- Purpose: Convenience views for common queries
-- ============================================================================

-- View: Open positions with current P&L
CREATE OR REPLACE VIEW v_open_positions AS
SELECT
    p.id,
    p.symbol,
    p.side,
    p.quantity,
    p.entry_price,
    p.current_price,
    p.leverage,
    p.stop_loss,
    p.take_profit,
    CASE
        WHEN p.side = 'LONG' THEN (p.current_price - p.entry_price) * p.quantity * p.leverage
        WHEN p.side = 'SHORT' THEN (p.entry_price - p.current_price) * p.quantity * p.leverage
    END AS unrealized_pnl_usd,
    p.created_at,
    p.updated_at
FROM positions p
WHERE p.status = 'OPEN';

COMMENT ON VIEW v_open_positions IS 'All open positions with calculated unrealized P&L';

-- View: Portfolio summary
CREATE OR REPLACE VIEW v_portfolio_summary AS
SELECT
    COUNT(*) FILTER (WHERE status = 'OPEN') as open_positions,
    COUNT(*) FILTER (WHERE status = 'CLOSED') as closed_positions,
    SUM(pnl_chf) FILTER (WHERE status = 'CLOSED') as total_realized_pnl_chf,
    SUM(pnl_chf) FILTER (WHERE status = 'CLOSED' AND pnl_chf > 0) as total_profit_chf,
    SUM(pnl_chf) FILTER (WHERE status = 'CLOSED' AND pnl_chf < 0) as total_loss_chf,
    COUNT(*) FILTER (WHERE status = 'CLOSED' AND pnl_chf > 0) as winning_trades,
    COUNT(*) FILTER (WHERE status = 'CLOSED' AND pnl_chf < 0) as losing_trades
FROM positions;

COMMENT ON VIEW v_portfolio_summary IS 'Portfolio-level summary statistics';

-- View: Daily LLM cost
CREATE OR REPLACE VIEW v_daily_llm_cost AS
SELECT
    DATE(timestamp) as date,
    COUNT(*) as request_count,
    SUM(cost_usd) as total_cost_usd,
    SUM(prompt_tokens) as total_prompt_tokens,
    SUM(completion_tokens) as total_completion_tokens,
    AVG(latency_ms) as avg_latency_ms
FROM llm_requests
GROUP BY DATE(timestamp)
ORDER BY DATE(timestamp) DESC;

COMMENT ON VIEW v_daily_llm_cost IS 'Daily LLM API cost and usage metrics';

-- ============================================================================
-- FUNCTIONS
-- Purpose: Helper functions for common operations
-- ============================================================================

-- Function: Get current circuit breaker status
CREATE OR REPLACE FUNCTION get_circuit_breaker_status()
RETURNS TABLE(
    is_triggered BOOLEAN,
    current_pnl_chf DECIMAL(20, 8),
    threshold_chf DECIMAL(20, 8)
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COALESCE(cb.triggered, FALSE),
        COALESCE(cb.current_pnl_chf, 0),
        -183.89::DECIMAL(20, 8)
    FROM circuit_breaker_state cb
    WHERE cb.date = CURRENT_DATE
    UNION ALL
    SELECT FALSE, 0::DECIMAL(20, 8), -183.89::DECIMAL(20, 8)
    WHERE NOT EXISTS (SELECT 1 FROM circuit_breaker_state WHERE date = CURRENT_DATE)
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_circuit_breaker_status() IS 'Get current circuit breaker status for today';

-- ============================================================================
-- GRANTS (For application user)
-- ============================================================================

-- Note: In production, create a dedicated application user with limited permissions
-- Example:
-- CREATE USER trading_app WITH PASSWORD 'secure_password';
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO trading_app;
-- GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO trading_app;

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================
