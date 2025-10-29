"""
Migration 002: Position State Transitions Table

Adds state_transitions table to track position lifecycle state changes.
Enables comprehensive audit trail of all position state transitions.

Created: 2025-10-29
Sprint: Sprint 2 Stream D - Position State Machine
"""

import asyncpg


async def upgrade(conn: asyncpg.Connection) -> None:
    """
    Apply migration: Create position_state_transitions table.

    Args:
        conn: Database connection
    """
    await conn.execute("""
        -- Position State Transitions Table
        -- Tracks all state changes throughout position lifecycle
        CREATE TABLE IF NOT EXISTS position_state_transitions (
            id SERIAL PRIMARY KEY,
            position_id UUID NOT NULL,
            symbol VARCHAR(20) NOT NULL,
            from_state VARCHAR(20) NOT NULL,
            to_state VARCHAR(20) NOT NULL,
            reason TEXT NOT NULL,
            metadata JSONB,
            timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            -- Indexes for efficient queries
            CONSTRAINT fk_position
                FOREIGN KEY (position_id)
                REFERENCES positions(id)
                ON DELETE CASCADE
        );

        -- Index for querying transitions by position
        CREATE INDEX IF NOT EXISTS idx_transitions_position_id
            ON position_state_transitions(position_id);

        -- Index for querying transitions by symbol
        CREATE INDEX IF NOT EXISTS idx_transitions_symbol
            ON position_state_transitions(symbol);

        -- Index for querying transitions by timestamp (most recent first)
        CREATE INDEX IF NOT EXISTS idx_transitions_timestamp
            ON position_state_transitions(timestamp DESC);

        -- Index for querying transitions by state
        CREATE INDEX IF NOT EXISTS idx_transitions_states
            ON position_state_transitions(from_state, to_state);

        -- Composite index for common query pattern (position + time)
        CREATE INDEX IF NOT EXISTS idx_transitions_position_timestamp
            ON position_state_transitions(position_id, timestamp DESC);

        -- Comment on table
        COMMENT ON TABLE position_state_transitions IS
            'Audit log of all position state transitions for lifecycle tracking';

        -- Comment on columns
        COMMENT ON COLUMN position_state_transitions.position_id IS
            'ID of the position this transition belongs to';
        COMMENT ON COLUMN position_state_transitions.symbol IS
            'Trading pair symbol (e.g., BTCUSDT) for quick filtering';
        COMMENT ON COLUMN position_state_transitions.from_state IS
            'Previous state (none, opening, open, closing, closed, failed, liquidated)';
        COMMENT ON COLUMN position_state_transitions.to_state IS
            'New state after transition';
        COMMENT ON COLUMN position_state_transitions.reason IS
            'Human-readable reason for the transition';
        COMMENT ON COLUMN position_state_transitions.metadata IS
            'Additional structured data about the transition (optional)';
        COMMENT ON COLUMN position_state_transitions.timestamp IS
            'When the transition occurred (UTC)';
    """)

    print("✅ Migration 002 applied: position_state_transitions table created")


async def downgrade(conn: asyncpg.Connection) -> None:
    """
    Rollback migration: Drop position_state_transitions table.

    Args:
        conn: Database connection
    """
    await conn.execute("""
        -- Drop indexes first
        DROP INDEX IF EXISTS idx_transitions_position_timestamp;
        DROP INDEX IF EXISTS idx_transitions_states;
        DROP INDEX IF EXISTS idx_transitions_timestamp;
        DROP INDEX IF EXISTS idx_transitions_symbol;
        DROP INDEX IF EXISTS idx_transitions_position_id;

        -- Drop table
        DROP TABLE IF EXISTS position_state_transitions;
    """)

    print("✅ Migration 002 rolled back: position_state_transitions table dropped")


# Migration metadata
MIGRATION_ID = "002"
MIGRATION_NAME = "position_state_transitions"
MIGRATION_DESCRIPTION = "Add position state transitions tracking table"
REQUIRES = ["001"]  # Depends on initial schema migration
