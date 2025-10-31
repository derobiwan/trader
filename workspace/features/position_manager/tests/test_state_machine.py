"""
Unit Tests for Position State Machine

Tests all state transitions, validation, error handling, and helper methods.
Ensures state machine enforces lifecycle rules correctly.

Run with:
    pytest workspace/features/position_manager/tests/test_state_machine.py -v
"""

import pytest
from datetime import datetime
from uuid import uuid4

from workspace.features.position_manager.state_machine import (
    PositionStateMachine,
    PositionState,
    InvalidStateTransition,
    create_state_machine,
    validate_transition_path,
    get_state_flow_diagram,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def state_machine():
    """Create a fresh state machine for each test."""
    return PositionStateMachine(symbol="BTCUSDT", position_id=uuid4())


@pytest.fixture
def opened_state_machine():
    """Create a state machine in OPEN state."""
    sm = PositionStateMachine(symbol="BTCUSDT", position_id=uuid4())
    sm.transition(PositionState.OPENING, "Order submitted")
    sm.transition(PositionState.OPEN, "Order filled")
    return sm


# ============================================================================
# Basic State Machine Tests
# ============================================================================


def test_initial_state(state_machine):
    """Test state machine starts in NONE state."""
    assert state_machine.current_state == PositionState.NONE
    assert not state_machine.is_terminal_state()
    assert len(state_machine.history) == 0


def test_symbol_and_position_id(state_machine):
    """Test state machine stores symbol and position_id."""
    assert state_machine.symbol == "BTCUSDT"
    assert state_machine.position_id is not None


# ============================================================================
# Valid Transition Tests
# ============================================================================


def test_valid_transition_none_to_opening(state_machine):
    """Test valid transition: NONE → OPENING."""
    state_machine.transition(PositionState.OPENING, "Order submitted to exchange")

    assert state_machine.current_state == PositionState.OPENING
    assert len(state_machine.history) == 1
    assert state_machine.history[0].from_state == PositionState.NONE
    assert state_machine.history[0].to_state == PositionState.OPENING


def test_valid_transition_opening_to_open(state_machine):
    """Test valid transition: OPENING → OPEN."""
    state_machine.transition(PositionState.OPENING, "Order submitted")
    state_machine.transition(PositionState.OPEN, "Order filled successfully")

    assert state_machine.current_state == PositionState.OPEN
    assert len(state_machine.history) == 2
    assert state_machine.history[1].to_state == PositionState.OPEN


def test_valid_transition_opening_to_failed(state_machine):
    """Test valid transition: OPENING → FAILED."""
    state_machine.transition(PositionState.OPENING, "Order submitted")
    state_machine.transition(PositionState.FAILED, "Order rejected by exchange")

    assert state_machine.current_state == PositionState.FAILED
    assert state_machine.is_terminal_state()


def test_valid_transition_open_to_closing(opened_state_machine):
    """Test valid transition: OPEN → CLOSING."""
    opened_state_machine.transition(PositionState.CLOSING, "Close order submitted")

    assert opened_state_machine.current_state == PositionState.CLOSING
    assert len(opened_state_machine.history) == 3


def test_valid_transition_open_to_liquidated(opened_state_machine):
    """Test valid transition: OPEN → LIQUIDATED."""
    opened_state_machine.transition(
        PositionState.LIQUIDATED, "Position liquidated by exchange"
    )

    assert opened_state_machine.current_state == PositionState.LIQUIDATED
    assert opened_state_machine.is_terminal_state()


def test_valid_transition_closing_to_closed(opened_state_machine):
    """Test valid transition: CLOSING → CLOSED."""
    opened_state_machine.transition(PositionState.CLOSING, "Close order submitted")
    opened_state_machine.transition(PositionState.CLOSED, "Close order filled")

    assert opened_state_machine.current_state == PositionState.CLOSED
    assert opened_state_machine.is_terminal_state()


def test_valid_transition_closing_to_failed(opened_state_machine):
    """Test valid transition: CLOSING → FAILED."""
    opened_state_machine.transition(PositionState.CLOSING, "Close order submitted")
    opened_state_machine.transition(PositionState.FAILED, "Close order rejected")

    assert opened_state_machine.current_state == PositionState.FAILED
    assert opened_state_machine.is_terminal_state()


def test_complete_lifecycle_success(state_machine):
    """Test complete happy path: NONE → OPENING → OPEN → CLOSING → CLOSED."""
    state_machine.transition(PositionState.OPENING, "Order submitted")
    state_machine.transition(PositionState.OPEN, "Order filled")
    state_machine.transition(PositionState.CLOSING, "Close order submitted")
    state_machine.transition(PositionState.CLOSED, "Close order filled")

    assert state_machine.current_state == PositionState.CLOSED
    assert state_machine.is_terminal_state()
    assert len(state_machine.history) == 4


# ============================================================================
# Invalid Transition Tests
# ============================================================================


def test_invalid_transition_none_to_open(state_machine):
    """Test invalid transition: NONE → OPEN (must go through OPENING)."""
    with pytest.raises(InvalidStateTransition) as exc_info:
        state_machine.transition(PositionState.OPEN, "Direct open not allowed")

    assert "none" in str(exc_info.value).lower()
    assert "open" in str(exc_info.value).lower()
    assert state_machine.current_state == PositionState.NONE  # State unchanged


def test_invalid_transition_none_to_closing(state_machine):
    """Test invalid transition: NONE → CLOSING."""
    with pytest.raises(InvalidStateTransition):
        state_machine.transition(
            PositionState.CLOSING, "Cannot close non-existent position"
        )


def test_invalid_transition_opening_to_closing(state_machine):
    """Test invalid transition: OPENING → CLOSING."""
    state_machine.transition(PositionState.OPENING, "Order submitted")

    with pytest.raises(InvalidStateTransition):
        state_machine.transition(PositionState.CLOSING, "Cannot close before open")


def test_invalid_transition_from_closed(state_machine):
    """Test terminal state CLOSED cannot transition."""
    state_machine.transition(PositionState.OPENING, "Order submitted")
    state_machine.transition(PositionState.OPEN, "Order filled")
    state_machine.transition(PositionState.CLOSING, "Close order submitted")
    state_machine.transition(PositionState.CLOSED, "Close order filled")

    # Try to transition from CLOSED (terminal state)
    with pytest.raises(InvalidStateTransition):
        state_machine.transition(PositionState.OPENING, "Cannot reopen closed position")

    assert state_machine.current_state == PositionState.CLOSED


def test_invalid_transition_from_failed(state_machine):
    """Test terminal state FAILED cannot transition."""
    state_machine.transition(PositionState.OPENING, "Order submitted")
    state_machine.transition(PositionState.FAILED, "Order failed")

    with pytest.raises(InvalidStateTransition):
        state_machine.transition(PositionState.OPENING, "Cannot retry from FAILED")

    assert state_machine.current_state == PositionState.FAILED


def test_invalid_transition_from_liquidated(opened_state_machine):
    """Test terminal state LIQUIDATED cannot transition."""
    opened_state_machine.transition(PositionState.LIQUIDATED, "Position liquidated")

    with pytest.raises(InvalidStateTransition):
        opened_state_machine.transition(
            PositionState.CLOSING, "Cannot close liquidated position"
        )

    assert opened_state_machine.current_state == PositionState.LIQUIDATED


# ============================================================================
# Transition Validation Tests
# ============================================================================


def test_empty_reason_raises_error(state_machine):
    """Test that empty reason raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        state_machine.transition(PositionState.OPENING, "")

    assert "reason cannot be empty" in str(exc_info.value).lower()


def test_whitespace_only_reason_raises_error(state_machine):
    """Test that whitespace-only reason raises ValueError."""
    with pytest.raises(ValueError):
        state_machine.transition(PositionState.OPENING, "   ")


def test_reason_is_trimmed(state_machine):
    """Test that reason is trimmed of leading/trailing whitespace."""
    state_machine.transition(PositionState.OPENING, "  Order submitted  ")

    assert state_machine.history[0].reason == "Order submitted"


# ============================================================================
# State Transition History Tests
# ============================================================================


def test_transition_history_records_all_transitions(state_machine):
    """Test that history records all transitions in order."""
    state_machine.transition(PositionState.OPENING, "Reason 1")
    state_machine.transition(PositionState.OPEN, "Reason 2")
    state_machine.transition(PositionState.CLOSING, "Reason 3")
    state_machine.transition(PositionState.CLOSED, "Reason 4")

    history = state_machine.get_history()
    assert len(history) == 4
    assert history[0].from_state == PositionState.NONE
    assert history[0].to_state == PositionState.OPENING
    assert history[3].from_state == PositionState.CLOSING
    assert history[3].to_state == PositionState.CLOSED


def test_transition_history_has_timestamps(state_machine):
    """Test that each transition has a timestamp."""
    state_machine.transition(PositionState.OPENING, "Order submitted")
    state_machine.transition(PositionState.OPEN, "Order filled")

    for transition in state_machine.history:
        assert isinstance(transition.timestamp, datetime)
        assert transition.timestamp <= datetime.utcnow()


def test_transition_history_is_chronological(state_machine):
    """Test that transitions are in chronological order."""
    state_machine.transition(PositionState.OPENING, "Reason 1")
    state_machine.transition(PositionState.OPEN, "Reason 2")

    history = state_machine.get_history()
    assert history[0].timestamp <= history[1].timestamp


def test_transition_with_metadata(state_machine):
    """Test that transitions can include metadata."""
    metadata = {"order_id": "12345", "price": "45000.00"}
    state_machine.transition(
        PositionState.OPENING, "Order submitted", metadata=metadata
    )

    assert state_machine.history[0].metadata == metadata


# ============================================================================
# Terminal State Tests
# ============================================================================


def test_terminal_state_closed(state_machine):
    """Test CLOSED is a terminal state."""
    state_machine.transition(PositionState.OPENING, "Order submitted")
    state_machine.transition(PositionState.OPEN, "Order filled")
    state_machine.transition(PositionState.CLOSING, "Close order submitted")
    state_machine.transition(PositionState.CLOSED, "Close order filled")

    assert state_machine.is_terminal_state()


def test_terminal_state_failed(state_machine):
    """Test FAILED is a terminal state."""
    state_machine.transition(PositionState.OPENING, "Order submitted")
    state_machine.transition(PositionState.FAILED, "Order failed")

    assert state_machine.is_terminal_state()


def test_terminal_state_liquidated(opened_state_machine):
    """Test LIQUIDATED is a terminal state."""
    opened_state_machine.transition(PositionState.LIQUIDATED, "Position liquidated")

    assert opened_state_machine.is_terminal_state()


def test_non_terminal_states(state_machine):
    """Test non-terminal states return False."""
    assert not state_machine.is_terminal_state()  # NONE

    state_machine.transition(PositionState.OPENING, "Order submitted")
    assert not state_machine.is_terminal_state()  # OPENING

    state_machine.transition(PositionState.OPEN, "Order filled")
    assert not state_machine.is_terminal_state()  # OPEN

    state_machine.transition(PositionState.CLOSING, "Close order submitted")
    assert not state_machine.is_terminal_state()  # CLOSING


# ============================================================================
# Helper Method Tests
# ============================================================================


def test_can_transition_to(state_machine):
    """Test can_transition_to method."""
    assert state_machine.can_transition_to(PositionState.OPENING)
    assert not state_machine.can_transition_to(PositionState.OPEN)
    assert not state_machine.can_transition_to(PositionState.CLOSING)


def test_get_current_state(state_machine):
    """Test get_current_state method."""
    assert state_machine.get_current_state() == PositionState.NONE

    state_machine.transition(PositionState.OPENING, "Order submitted")
    assert state_machine.get_current_state() == PositionState.OPENING


def test_get_allowed_transitions(state_machine):
    """Test get_allowed_transitions method."""
    allowed = state_machine.get_allowed_transitions()
    assert PositionState.OPENING in allowed
    assert len(allowed) == 1

    state_machine.transition(PositionState.OPENING, "Order submitted")
    allowed = state_machine.get_allowed_transitions()
    assert PositionState.OPEN in allowed
    assert PositionState.FAILED in allowed
    assert len(allowed) == 2


def test_get_duration_in_state(state_machine):
    """Test get_duration_in_state method."""
    # Initially in NONE state
    duration = state_machine.get_duration_in_state(PositionState.NONE)
    assert duration is None  # No transitions yet

    # Transition to OPENING
    state_machine.transition(PositionState.OPENING, "Order submitted")

    # Transition to OPEN
    state_machine.transition(PositionState.OPEN, "Order filled")

    # Check duration in OPENING state
    duration = state_machine.get_duration_in_state(PositionState.OPENING)
    assert duration is not None
    assert duration >= 0


# ============================================================================
# Serialization Tests
# ============================================================================


def test_to_dict(state_machine):
    """Test to_dict serialization."""
    state_machine.transition(PositionState.OPENING, "Order submitted")
    state_machine.transition(PositionState.OPEN, "Order filled")

    data = state_machine.to_dict()

    assert data["symbol"] == "BTCUSDT"
    assert data["current_state"] == PositionState.OPEN.value
    assert data["is_terminal"] is False
    assert data["transition_count"] == 2
    assert len(data["history"]) == 2
    assert data["history"][0]["from_state"] == PositionState.NONE.value
    assert data["history"][0]["to_state"] == PositionState.OPENING.value


def test_repr(state_machine):
    """Test __repr__ method."""
    repr_str = repr(state_machine)

    assert "BTCUSDT" in repr_str
    assert "none" in repr_str
    assert "transitions=0" in repr_str


# ============================================================================
# Factory Function Tests
# ============================================================================


def test_create_state_machine_default():
    """Test factory function with default initial state."""
    sm = create_state_machine(symbol="ETHUSDT")

    assert sm.symbol == "ETHUSDT"
    assert sm.current_state == PositionState.NONE


def test_create_state_machine_with_initial_state():
    """Test factory function with custom initial state."""
    sm = create_state_machine(symbol="ETHUSDT", initial_state=PositionState.OPEN)

    assert sm.symbol == "ETHUSDT"
    assert sm.current_state == PositionState.OPEN


def test_create_state_machine_with_position_id():
    """Test factory function with position_id."""
    position_id = uuid4()
    sm = create_state_machine(symbol="ETHUSDT", position_id=position_id)

    assert sm.position_id == position_id


# ============================================================================
# Utility Function Tests
# ============================================================================


def test_validate_transition_path_valid():
    """Test validate_transition_path with valid path."""
    transitions = [
        (PositionState.NONE, PositionState.OPENING),
        (PositionState.OPENING, PositionState.OPEN),
        (PositionState.OPEN, PositionState.CLOSING),
        (PositionState.CLOSING, PositionState.CLOSED),
    ]

    assert validate_transition_path(transitions) is True


def test_validate_transition_path_invalid():
    """Test validate_transition_path with invalid path."""
    transitions = [
        (PositionState.NONE, PositionState.OPEN),  # Invalid: must go through OPENING
    ]

    assert validate_transition_path(transitions) is False


def test_get_state_flow_diagram():
    """Test get_state_flow_diagram returns diagram."""
    diagram = get_state_flow_diagram()

    assert "NONE" in diagram
    assert "OPENING" in diagram
    assert "OPEN" in diagram
    assert "CLOSING" in diagram
    assert "CLOSED" in diagram
    assert "FAILED" in diagram
    assert "LIQUIDATED" in diagram


# ============================================================================
# Edge Case Tests
# ============================================================================


def test_multiple_positions_same_symbol():
    """Test multiple state machines can exist for same symbol."""
    sm1 = PositionStateMachine(symbol="BTCUSDT", position_id=uuid4())
    sm2 = PositionStateMachine(symbol="BTCUSDT", position_id=uuid4())

    sm1.transition(PositionState.OPENING, "Order 1 submitted")
    sm2.transition(PositionState.OPENING, "Order 2 submitted")
    sm1.transition(PositionState.OPEN, "Order 1 filled")

    assert sm1.current_state == PositionState.OPEN
    assert sm2.current_state == PositionState.OPENING


def test_long_reason_string(state_machine):
    """Test state machine handles long reason strings."""
    long_reason = "A" * 500  # 500 characters
    state_machine.transition(PositionState.OPENING, long_reason)

    assert state_machine.history[0].reason == long_reason


def test_special_characters_in_reason(state_machine):
    """Test state machine handles special characters in reason."""
    reason = "Order failed: 'Insufficient margin' (error code: 123)"
    state_machine.transition(PositionState.OPENING, reason)
    state_machine.transition(
        PositionState.FAILED, "Database error: 'Connection refused'"
    )

    assert state_machine.history[0].reason == reason


# ============================================================================
# Performance Tests
# ============================================================================


def test_transition_performance(state_machine):
    """Test that transitions complete in <1ms (target requirement)."""
    import time

    # Measure single transition
    start = time.perf_counter()
    state_machine.transition(PositionState.OPENING, "Order submitted")
    duration_ms = (time.perf_counter() - start) * 1000

    # Should be well under 1ms (allow 0.5ms for safety)
    assert duration_ms < 0.5, f"Transition took {duration_ms:.3f}ms (target: <1ms)"


def test_multiple_transitions_performance(state_machine):
    """Test performance with multiple transitions."""
    import time

    start = time.perf_counter()

    # Execute complete lifecycle
    state_machine.transition(PositionState.OPENING, "Order submitted")
    state_machine.transition(PositionState.OPEN, "Order filled")
    state_machine.transition(PositionState.CLOSING, "Close order submitted")
    state_machine.transition(PositionState.CLOSED, "Close order filled")

    total_duration_ms = (time.perf_counter() - start) * 1000

    # 4 transitions should complete in under 2ms
    assert total_duration_ms < 2.0, f"4 transitions took {total_duration_ms:.3f}ms"


# ============================================================================
# Integration-Like Tests
# ============================================================================


def test_realistic_position_lifecycle():
    """Test realistic position lifecycle with metadata."""
    position_id = uuid4()
    sm = PositionStateMachine(symbol="BTCUSDT", position_id=position_id)

    # Order submission
    sm.transition(
        PositionState.OPENING,
        "Market order submitted to exchange",
        metadata={"order_id": "12345", "quantity": "0.01"},
    )

    # Order filled
    sm.transition(
        PositionState.OPEN,
        "Order filled successfully",
        metadata={"fill_price": "45000.00", "fill_time": datetime.utcnow().isoformat()},
    )

    # Close order submitted
    sm.transition(
        PositionState.CLOSING,
        "Take profit triggered at target price",
        metadata={"current_price": "46000.00"},
    )

    # Position closed
    sm.transition(
        PositionState.CLOSED,
        "Position closed with profit",
        metadata={"exit_price": "46000.00", "pnl": "85.00"},
    )

    assert sm.is_terminal_state()
    assert len(sm.history) == 4
    assert all(t.metadata is not None for t in sm.history)


def test_failed_order_lifecycle():
    """Test lifecycle when order fails."""
    sm = PositionStateMachine(symbol="ETHUSDT")

    sm.transition(
        PositionState.OPENING,
        "Order submitted to exchange",
        metadata={"order_id": "67890"},
    )

    sm.transition(
        PositionState.FAILED,
        "Order rejected: Insufficient margin",
        metadata={"error_code": "INSUFFICIENT_MARGIN", "required_margin": "500.00"},
    )

    assert sm.is_terminal_state()
    assert sm.current_state == PositionState.FAILED
    assert len(sm.history) == 2


def test_liquidation_lifecycle():
    """Test lifecycle when position is liquidated."""
    sm = PositionStateMachine(symbol="SOLUSDT")

    sm.transition(PositionState.OPENING, "Order submitted")
    sm.transition(PositionState.OPEN, "Order filled")

    sm.transition(
        PositionState.LIQUIDATED,
        "Position liquidated by exchange due to margin call",
        metadata={"liquidation_price": "100.00", "loss": "-450.00"},
    )

    assert sm.is_terminal_state()
    assert sm.current_state == PositionState.LIQUIDATED
    assert len(sm.history) == 3
