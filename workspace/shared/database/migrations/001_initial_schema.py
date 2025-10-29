"""
Initial database schema migration

Revision ID: 001_initial_schema
Create Date: 2025-10-27

Creates all 11 tables with TimescaleDB hypertables, indexes, and constraints.
This migration is idempotent and can be run multiple times safely.
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Apply migration: Create all tables, indexes, and TimescaleDB optimizations.
    """

    # Enable extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")

    # ========================================================================
    # TABLE 1: positions
    # ========================================================================
    op.create_table(
        "positions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("side", sa.String(10), nullable=False),
        sa.Column("quantity", sa.Numeric(20, 8), nullable=False),
        sa.Column("entry_price", sa.Numeric(20, 8), nullable=False),
        sa.Column("current_price", sa.Numeric(20, 8), nullable=True),
        sa.Column("leverage", sa.Integer, nullable=False),
        sa.Column("stop_loss", sa.Numeric(20, 8), nullable=True),
        sa.Column("take_profit", sa.Numeric(20, 8), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="OPEN"),
        sa.Column("pnl_chf", sa.Numeric(20, 8), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("closed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint("side IN ('LONG', 'SHORT')", name="valid_side"),
        sa.CheckConstraint(
            "status IN ('OPEN', 'CLOSED', 'LIQUIDATED')", name="valid_status"
        ),
        sa.CheckConstraint("quantity > 0", name="valid_quantity"),
        sa.CheckConstraint("entry_price > 0", name="valid_entry_price"),
        sa.CheckConstraint("leverage >= 5 AND leverage <= 40", name="valid_leverage"),
    )

    op.create_index("idx_positions_symbol", "positions", ["symbol"])
    op.create_index("idx_positions_status", "positions", ["status"])
    op.create_index(
        "idx_positions_created_at", "positions", [sa.text("created_at DESC")]
    )
    op.create_index("idx_positions_symbol_status", "positions", ["symbol", "status"])

    # ========================================================================
    # TABLE 2: trading_signals
    # ========================================================================
    op.create_table(
        "trading_signals",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("signal_type", sa.String(20), nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("risk_usd", sa.Numeric(20, 8), nullable=True),
        sa.Column("reasoning", sa.Text, nullable=False),
        sa.Column("llm_model", sa.String(100), nullable=False),
        sa.Column("llm_tokens", sa.Integer, nullable=True),
        sa.Column("llm_cost_usd", sa.Numeric(10, 6), nullable=True),
        sa.Column("executed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "signal_type IN ('ENTRY', 'EXIT', 'HOLD', 'INCREASE', 'DECREASE')",
            name="valid_signal_type",
        ),
        sa.CheckConstraint("action IN ('BUY', 'SELL', 'HOLD')", name="valid_action"),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1", name="valid_confidence"
        ),
    )

    op.create_index("idx_trading_signals_symbol", "trading_signals", ["symbol"])
    op.create_index(
        "idx_trading_signals_created_at",
        "trading_signals",
        [sa.text("created_at DESC")],
    )
    op.create_index("idx_trading_signals_executed", "trading_signals", ["executed"])
    op.create_index(
        "idx_trading_signals_symbol_created",
        "trading_signals",
        ["symbol", sa.text("created_at DESC")],
    )

    # ========================================================================
    # TABLE 3: orders
    # ========================================================================
    op.create_table(
        "orders",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("position_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("exchange_order_id", sa.String(100), nullable=True, unique=True),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("side", sa.String(10), nullable=False),
        sa.Column("order_type", sa.String(20), nullable=False),
        sa.Column("quantity", sa.Numeric(20, 8), nullable=False),
        sa.Column("price", sa.Numeric(20, 8), nullable=True),
        sa.Column(
            "filled_quantity", sa.Numeric(20, 8), nullable=False, server_default="0"
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("fee_chf", sa.Numeric(20, 8), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(["position_id"], ["positions.id"], ondelete="CASCADE"),
        sa.CheckConstraint("side IN ('BUY', 'SELL')", name="valid_order_side"),
        sa.CheckConstraint(
            "order_type IN ('MARKET', 'LIMIT', 'STOP_LOSS', 'TAKE_PROFIT')",
            name="valid_order_type",
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'FILLED', 'PARTIALLY_FILLED', 'CANCELLED', 'REJECTED')",
            name="valid_order_status",
        ),
        sa.CheckConstraint("quantity > 0", name="valid_order_quantity"),
    )

    op.create_index("idx_orders_position_id", "orders", ["position_id"])
    op.create_index("idx_orders_exchange_order_id", "orders", ["exchange_order_id"])
    op.create_index("idx_orders_status", "orders", ["status"])
    op.create_index("idx_orders_created_at", "orders", [sa.text("created_at DESC")])

    # ========================================================================
    # TABLE 4: market_data (TimescaleDB Hypertable)
    # ========================================================================
    op.create_table(
        "market_data",
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("timestamp", sa.BigInteger, nullable=False),
        sa.Column("open", sa.Numeric(20, 8), nullable=False),
        sa.Column("high", sa.Numeric(20, 8), nullable=False),
        sa.Column("low", sa.Numeric(20, 8), nullable=False),
        sa.Column("close", sa.Numeric(20, 8), nullable=False),
        sa.Column("volume", sa.Numeric(20, 8), nullable=False),
        sa.Column("indicators", postgresql.JSONB, nullable=True),
        sa.CheckConstraint(
            "high >= low AND high >= open AND high >= close AND low <= open AND low <= close",
            name="valid_ohlc",
        ),
    )

    # Convert to TimescaleDB hypertable
    op.execute(
        """
        SELECT create_hypertable('market_data', 'timestamp',
            chunk_time_interval => 86400000000,
            if_not_exists => TRUE
        )
    """
    )

    op.create_index(
        "idx_market_data_symbol_timestamp",
        "market_data",
        ["symbol", sa.text("timestamp DESC")],
    )

    # Enable compression
    op.execute(
        """
        ALTER TABLE market_data SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'symbol',
            timescaledb.compress_orderby = 'timestamp DESC'
        )
    """
    )

    # Add compression policy (compress after 7 days)
    op.execute(
        """
        SELECT add_compression_policy('market_data', INTERVAL '7 days', if_not_exists => TRUE)
    """
    )

    # Add retention policy (keep 90 days)
    op.execute(
        """
        SELECT add_retention_policy('market_data', INTERVAL '90 days', if_not_exists => TRUE)
    """
    )

    # ========================================================================
    # TABLE 5: daily_performance (TimescaleDB Hypertable)
    # ========================================================================
    op.create_table(
        "daily_performance",
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("portfolio_value_chf", sa.Numeric(20, 8), nullable=False),
        sa.Column("daily_pnl_chf", sa.Numeric(20, 8), nullable=False),
        sa.Column("daily_pnl_pct", sa.Numeric(10, 4), nullable=False),
        sa.Column("sharpe_ratio", sa.Numeric(10, 4), nullable=True),
        sa.Column("win_rate", sa.Numeric(5, 4), nullable=True),
        sa.Column("total_trades", sa.Integer, nullable=False, server_default="0"),
        sa.Column("positions_snapshot", postgresql.JSONB, nullable=True),
        sa.CheckConstraint("win_rate >= 0 AND win_rate <= 1", name="valid_win_rate"),
    )

    # Convert to TimescaleDB hypertable
    op.execute(
        """
        SELECT create_hypertable('daily_performance', 'date',
            chunk_time_interval => INTERVAL '1 day',
            if_not_exists => TRUE
        )
    """
    )

    op.create_index(
        "idx_daily_performance_date", "daily_performance", [sa.text("date DESC")]
    )

    # Add retention policy (keep 2 years)
    op.execute(
        """
        SELECT add_retention_policy('daily_performance', INTERVAL '2 years', if_not_exists => TRUE)
    """
    )

    # ========================================================================
    # TABLE 6: risk_events (TimescaleDB Hypertable)
    # ========================================================================
    op.create_table(
        "risk_events",
        sa.Column("timestamp", sa.BigInteger, nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("position_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.ForeignKeyConstraint(["position_id"], ["positions.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            "severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')", name="valid_severity"
        ),
    )

    # Convert to TimescaleDB hypertable
    op.execute(
        """
        SELECT create_hypertable('risk_events', 'timestamp',
            chunk_time_interval => 86400000000,
            if_not_exists => TRUE
        )
    """
    )

    op.create_index(
        "idx_risk_events_timestamp", "risk_events", [sa.text("timestamp DESC")]
    )
    op.create_index("idx_risk_events_event_type", "risk_events", ["event_type"])
    op.create_index("idx_risk_events_severity", "risk_events", ["severity"])
    op.create_index("idx_risk_events_position_id", "risk_events", ["position_id"])

    # Add retention policy (keep 1 year)
    op.execute(
        """
        SELECT add_retention_policy('risk_events', INTERVAL '1 year', if_not_exists => TRUE)
    """
    )

    # ========================================================================
    # TABLE 7: llm_requests
    # ========================================================================
    op.create_table(
        "llm_requests",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "timestamp",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("prompt_tokens", sa.Integer, nullable=False),
        sa.Column("completion_tokens", sa.Integer, nullable=False),
        sa.Column("cost_usd", sa.Numeric(10, 6), nullable=False),
        sa.Column("latency_ms", sa.Integer, nullable=False),
        sa.Column("response", postgresql.JSONB, nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "prompt_tokens > 0 AND completion_tokens >= 0", name="valid_tokens"
        ),
        sa.CheckConstraint("cost_usd >= 0", name="valid_cost"),
        sa.CheckConstraint("latency_ms >= 0", name="valid_latency"),
    )

    op.create_index(
        "idx_llm_requests_timestamp", "llm_requests", [sa.text("timestamp DESC")]
    )
    op.create_index("idx_llm_requests_model", "llm_requests", ["model"])
    op.create_index("idx_llm_requests_cost", "llm_requests", [sa.text("cost_usd DESC")])

    # ========================================================================
    # TABLE 8: system_config
    # ========================================================================
    op.create_table(
        "system_config",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("value", postgresql.JSONB, nullable=False),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("updated_by", sa.String(100), nullable=True),
    )

    # Insert default configuration
    op.execute(
        """
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
        ON CONFLICT (key) DO NOTHING
    """
    )

    # ========================================================================
    # TABLE 9: audit_log
    # ========================================================================
    op.create_table(
        "audit_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "timestamp",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.String(100), nullable=True),
        sa.Column("user", sa.String(100), nullable=False),
        sa.Column("changes", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    op.create_index("idx_audit_log_timestamp", "audit_log", [sa.text("timestamp DESC")])
    op.create_index("idx_audit_log_entity_type", "audit_log", ["entity_type"])
    op.create_index("idx_audit_log_entity_id", "audit_log", ["entity_id"])

    # ========================================================================
    # TABLE 10: circuit_breaker_state
    # ========================================================================
    op.create_table(
        "circuit_breaker_state",
        sa.Column("date", sa.Date, primary_key=True),
        sa.Column(
            "current_pnl_chf", sa.Numeric(20, 8), nullable=False, server_default="0"
        ),
        sa.Column("triggered", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("trigger_reason", sa.Text, nullable=True),
        sa.Column("positions_closed", postgresql.JSONB, nullable=True),
        sa.Column("reset_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )

    # ========================================================================
    # TABLE 11: position_reconciliation
    # ========================================================================
    op.create_table(
        "position_reconciliation",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "timestamp",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("position_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("system_state", postgresql.JSONB, nullable=False),
        sa.Column("exchange_state", postgresql.JSONB, nullable=False),
        sa.Column("discrepancies", postgresql.JSONB, nullable=True),
        sa.Column("resolved", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(["position_id"], ["positions.id"], ondelete="CASCADE"),
    )

    op.create_index(
        "idx_position_reconciliation_timestamp",
        "position_reconciliation",
        [sa.text("timestamp DESC")],
    )
    op.create_index(
        "idx_position_reconciliation_position_id",
        "position_reconciliation",
        ["position_id"],
    )
    op.create_index(
        "idx_position_reconciliation_resolved", "position_reconciliation", ["resolved"]
    )

    # ========================================================================
    # TRIGGERS
    # ========================================================================

    # Function to update updated_at timestamp
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """
    )

    # Triggers for updated_at columns
    op.execute(
        """
        CREATE TRIGGER update_positions_updated_at
        BEFORE UPDATE ON positions
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
    """
    )

    op.execute(
        """
        CREATE TRIGGER update_orders_updated_at
        BEFORE UPDATE ON orders
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
    """
    )

    op.execute(
        """
        CREATE TRIGGER update_system_config_updated_at
        BEFORE UPDATE ON system_config
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
    """
    )

    # ========================================================================
    # VIEWS
    # ========================================================================

    # View: Open positions with current P&L
    op.execute(
        """
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
        WHERE p.status = 'OPEN'
    """
    )

    # View: Portfolio summary
    op.execute(
        """
        CREATE OR REPLACE VIEW v_portfolio_summary AS
        SELECT
            COUNT(*) FILTER (WHERE status = 'OPEN') as open_positions,
            COUNT(*) FILTER (WHERE status = 'CLOSED') as closed_positions,
            SUM(pnl_chf) FILTER (WHERE status = 'CLOSED') as total_realized_pnl_chf,
            SUM(pnl_chf) FILTER (WHERE status = 'CLOSED' AND pnl_chf > 0) as total_profit_chf,
            SUM(pnl_chf) FILTER (WHERE status = 'CLOSED' AND pnl_chf < 0) as total_loss_chf,
            COUNT(*) FILTER (WHERE status = 'CLOSED' AND pnl_chf > 0) as winning_trades,
            COUNT(*) FILTER (WHERE status = 'CLOSED' AND pnl_chf < 0) as losing_trades
        FROM positions
    """
    )

    # View: Daily LLM cost
    op.execute(
        """
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
        ORDER BY DATE(timestamp) DESC
    """
    )

    # ========================================================================
    # FUNCTIONS
    # ========================================================================

    # Function: Get current circuit breaker status
    op.execute(
        """
        CREATE OR REPLACE FUNCTION get_circuit_breaker_status()
        RETURNS TABLE(
            is_triggered BOOLEAN,
            current_pnl_chf NUMERIC(20, 8),
            threshold_chf NUMERIC(20, 8)
        ) AS $$
        BEGIN
            RETURN QUERY
            SELECT
                COALESCE(cb.triggered, FALSE),
                COALESCE(cb.current_pnl_chf, 0::NUMERIC(20, 8)),
                -183.89::NUMERIC(20, 8)
            FROM circuit_breaker_state cb
            WHERE cb.date = CURRENT_DATE
            UNION ALL
            SELECT FALSE, 0::NUMERIC(20, 8), -183.89::NUMERIC(20, 8)
            WHERE NOT EXISTS (SELECT 1 FROM circuit_breaker_state WHERE date = CURRENT_DATE)
            LIMIT 1;
        END;
        $$ LANGUAGE plpgsql
    """
    )


def downgrade() -> None:
    """
    Revert migration: Drop all tables, views, functions, and triggers.
    """

    # Drop views
    op.execute("DROP VIEW IF EXISTS v_open_positions")
    op.execute("DROP VIEW IF EXISTS v_portfolio_summary")
    op.execute("DROP VIEW IF EXISTS v_daily_llm_cost")

    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS get_circuit_breaker_status()")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE")

    # Drop tables (in reverse order of dependencies)
    op.drop_table("position_reconciliation")
    op.drop_table("circuit_breaker_state")
    op.drop_table("audit_log")
    op.drop_table("system_config")
    op.drop_table("llm_requests")
    op.drop_table("risk_events")
    op.drop_table("daily_performance")
    op.drop_table("market_data")
    op.drop_table("orders")
    op.drop_table("trading_signals")
    op.drop_table("positions")
