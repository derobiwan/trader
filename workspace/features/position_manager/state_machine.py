"""
Position State Machine

Robust state machine implementation for tracking position lifecycle.
Ensures only valid state transitions occur and maintains full audit history.

The state machine enforces the following lifecycle:
    NONE → OPENING → OPEN → CLOSING → CLOSED
    NONE → OPENING → FAILED
    OPEN → CLOSING → FAILED
    OPEN → LIQUIDATED

Terminal states (cannot transition from): CLOSED, FAILED, LIQUIDATED

Usage:
    from workspace.features.position_manager.state_machine import (
        PositionStateMachine,
        PositionState,
    )

    # Create state machine for a position
    sm = PositionStateMachine(symbol="BTCUSDT", position_id=uuid4())

    # Transition: NONE → OPENING
    sm.transition(PositionState.OPENING, "Order submitted to exchange")

    # Transition: OPENING → OPEN
    sm.transition(PositionState.OPEN, "Order filled successfully")

    # Transition: OPEN → CLOSING
    sm.transition(PositionState.CLOSING, "Close order submitted")

    # Transition: CLOSING → CLOSED
    sm.transition(PositionState.CLOSED, "Close order filled")

    # Check history
    history = sm.get_history()
    print(f"Position went through {len(history)} transitions")
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============================================================================
# Position State Enum
# ============================================================================


class PositionState(str, Enum):
    """
    Position lifecycle states.

    State Flow:
        NONE: Initial state, no position exists
        OPENING: Order submitted, waiting for fill
        OPEN: Position is active
        CLOSING: Close order submitted, waiting for fill
        CLOSED: Position closed successfully
        FAILED: Order or close failed
        LIQUIDATED: Position liquidated by exchange
    """

    NONE = "none"
    OPENING = "opening"
    OPEN = "open"
    CLOSING = "closing"
    CLOSED = "closed"
    FAILED = "failed"
    LIQUIDATED = "liquidated"


# ============================================================================
# State Transition Model
# ============================================================================


class StateTransition(BaseModel):
    """
    Record of a single state transition.

    Captures:
    - Previous state
    - New state
    - Reason for transition
    - Timestamp of transition
    """

    from_state: PositionState = Field(..., description="Previous state")
    to_state: PositionState = Field(..., description="New state")
    reason: str = Field(
        ..., min_length=1, max_length=500, description="Reason for transition"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When transition occurred"
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    def __repr__(self) -> str:
        return (
            f"StateTransition({self.from_state.value} → {self.to_state.value}, "
            f"reason='{self.reason}', timestamp={self.timestamp.isoformat()})"
        )


# ============================================================================
# Custom Exceptions
# ============================================================================


class InvalidStateTransition(Exception):
    """Raised when an invalid state transition is attempted."""

    pass


# ============================================================================
# Position State Machine
# ============================================================================


class PositionStateMachine:
    """
    State machine for position lifecycle management.

    Enforces valid state transitions and maintains complete audit history.
    Provides sub-millisecond transition performance for real-time trading.

    Attributes:
        symbol: Trading pair (e.g., BTCUSDT)
        position_id: Optional position ID for database correlation
        current_state: Current position state
        history: List of all state transitions
    """

    # Valid state transitions mapping
    # Key = current state, Value = list of allowed next states
    VALID_TRANSITIONS: Dict[PositionState, List[PositionState]] = {
        PositionState.NONE: [PositionState.OPENING],
        PositionState.OPENING: [PositionState.OPEN, PositionState.FAILED],
        PositionState.OPEN: [PositionState.CLOSING, PositionState.LIQUIDATED],
        PositionState.CLOSING: [PositionState.CLOSED, PositionState.FAILED],
        PositionState.CLOSED: [],  # Terminal state
        PositionState.FAILED: [],  # Terminal state
        PositionState.LIQUIDATED: [],  # Terminal state
    }

    # Terminal states (cannot transition from these)
    TERMINAL_STATES = {
        PositionState.CLOSED,
        PositionState.FAILED,
        PositionState.LIQUIDATED,
    }

    def __init__(self, symbol: str, position_id: Optional[UUID] = None):
        """
        Initialize position state machine.

        Args:
            symbol: Trading pair (e.g., BTCUSDT)
            position_id: Optional position ID for database correlation
        """
        self.symbol = symbol
        self.position_id = position_id
        self.current_state = PositionState.NONE
        self.history: List[StateTransition] = []

        logger.debug(
            f"State machine initialized: symbol={symbol} "
            f"position_id={position_id} state={self.current_state.value}"
        )

    def transition(
        self,
        to_state: PositionState,
        reason: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Transition to a new state.

        Validates the transition is allowed, records it in history,
        and updates the current state.

        Args:
            to_state: Target state to transition to
            reason: Human-readable reason for transition
            metadata: Optional additional data about the transition

        Raises:
            InvalidStateTransition: If transition is not allowed
            ValueError: If parameters are invalid

        Performance:
            Target: <1ms per transition
        """
        if not reason or not reason.strip():
            raise ValueError("Transition reason cannot be empty")

        # Validate transition is allowed
        if not self._is_valid_transition(to_state):
            allowed = self.VALID_TRANSITIONS[self.current_state]
            raise InvalidStateTransition(
                f"Invalid transition for position {self.symbol}: "
                f"{self.current_state.value} → {to_state.value}. "
                f"Allowed transitions from {self.current_state.value}: "
                f"{[s.value for s in allowed]}"
            )

        # Record transition
        transition = StateTransition(
            from_state=self.current_state,
            to_state=to_state,
            reason=reason.strip(),
            metadata=metadata,
        )
        self.history.append(transition)

        # Update state
        old_state = self.current_state
        self.current_state = to_state

        # Log transition
        logger.info(
            f"Position {self.symbol} transitioned: "
            f"{old_state.value} → {to_state.value} "
            f"(reason: {reason[:50]}{'...' if len(reason) > 50 else ''})"
        )

        # Additional logging for terminal states
        if self.is_terminal_state():
            logger.info(
                f"Position {self.symbol} reached terminal state: {to_state.value} "
                f"(total transitions: {len(self.history)})"
            )

    def _is_valid_transition(self, to_state: PositionState) -> bool:
        """
        Check if transition to target state is valid.

        Args:
            to_state: Target state

        Returns:
            bool: True if transition is allowed
        """
        allowed_states = self.VALID_TRANSITIONS[self.current_state]
        return to_state in allowed_states

    def can_transition_to(self, to_state: PositionState) -> bool:
        """
        Check if transition to target state is valid (public API).

        Args:
            to_state: Target state

        Returns:
            bool: True if transition is allowed
        """
        return self._is_valid_transition(to_state)

    def get_history(self) -> List[StateTransition]:
        """
        Get complete transition history.

        Returns:
            List of StateTransition objects in chronological order
        """
        return self.history.copy()

    def get_current_state(self) -> PositionState:
        """
        Get current state.

        Returns:
            Current PositionState
        """
        return self.current_state

    def is_terminal_state(self) -> bool:
        """
        Check if position is in a terminal state.

        Terminal states cannot transition to any other state.

        Returns:
            bool: True if in terminal state (CLOSED, FAILED, or LIQUIDATED)
        """
        return self.current_state in self.TERMINAL_STATES

    def get_allowed_transitions(self) -> List[PositionState]:
        """
        Get list of allowed transitions from current state.

        Returns:
            List of allowed PositionState values
        """
        return self.VALID_TRANSITIONS[self.current_state].copy()

    def get_duration_in_state(self, state: PositionState) -> Optional[float]:
        """
        Calculate total duration spent in a specific state (in seconds).

        Args:
            state: State to calculate duration for

        Returns:
            float: Total seconds in state, or None if never in that state
        """
        total_duration = 0.0
        found_state = False

        for i, transition in enumerate(self.history):
            if transition.from_state == state:
                found_state = True

                # Calculate duration until next transition
                if i + 1 < len(self.history):
                    next_transition = self.history[i + 1]
                    duration = (
                        next_transition.timestamp - transition.timestamp
                    ).total_seconds()
                    total_duration += duration
                elif self.current_state == state:
                    # Still in this state
                    duration = (
                        datetime.utcnow() - transition.timestamp
                    ).total_seconds()
                    total_duration += duration

        return total_duration if found_state else None

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize state machine to dictionary.

        Returns:
            Dict containing state machine data
        """
        return {
            "symbol": self.symbol,
            "position_id": str(self.position_id) if self.position_id else None,
            "current_state": self.current_state.value,
            "is_terminal": self.is_terminal_state(),
            "transition_count": len(self.history),
            "history": [
                {
                    "from_state": t.from_state.value,
                    "to_state": t.to_state.value,
                    "reason": t.reason,
                    "timestamp": t.timestamp.isoformat(),
                    "metadata": t.metadata,
                }
                for t in self.history
            ],
        }

    def __repr__(self) -> str:
        return (
            f"PositionStateMachine(symbol={self.symbol}, "
            f"state={self.current_state.value}, "
            f"transitions={len(self.history)}, "
            f"terminal={self.is_terminal_state()})"
        )


# ============================================================================
# State Machine Factory
# ============================================================================


def create_state_machine(
    symbol: str,
    position_id: Optional[UUID] = None,
    initial_state: PositionState = PositionState.NONE,
) -> PositionStateMachine:
    """
    Factory function to create a position state machine.

    Args:
        symbol: Trading pair
        position_id: Optional position ID
        initial_state: Starting state (default: NONE)

    Returns:
        PositionStateMachine instance
    """
    sm = PositionStateMachine(symbol=symbol, position_id=position_id)

    # If initial state is not NONE, we need to set it
    # (This is for reconstructing state machines from database)
    if initial_state != PositionState.NONE:
        sm.current_state = initial_state
        logger.debug(f"State machine created with initial state: {initial_state.value}")

    return sm


# ============================================================================
# State Validation Utilities
# ============================================================================


def validate_transition_path(
    transitions: List[tuple[PositionState, PositionState]],
) -> bool:
    """
    Validate a sequence of state transitions.

    Args:
        transitions: List of (from_state, to_state) tuples

    Returns:
        bool: True if all transitions are valid

    Example:
        transitions = [
            (PositionState.NONE, PositionState.OPENING),
            (PositionState.OPENING, PositionState.OPEN),
            (PositionState.OPEN, PositionState.CLOSING),
            (PositionState.CLOSING, PositionState.CLOSED),
        ]
        is_valid = validate_transition_path(transitions)
    """
    for from_state, to_state in transitions:
        allowed = PositionStateMachine.VALID_TRANSITIONS[from_state]
        if to_state not in allowed:
            return False
    return True


def get_state_flow_diagram() -> str:
    """
    Get ASCII diagram of state flow.

    Returns:
        String representation of state flow
    """
    return """
Position State Machine Flow:

    NONE
      ↓
    OPENING ──→ FAILED (terminal)
      ↓
    OPEN ──────→ LIQUIDATED (terminal)
      ↓
    CLOSING ───→ FAILED (terminal)
      ↓
    CLOSED (terminal)

Valid Transitions:
    NONE → OPENING
    OPENING → OPEN, FAILED
    OPEN → CLOSING, LIQUIDATED
    CLOSING → CLOSED, FAILED

Terminal States:
    CLOSED, FAILED, LIQUIDATED
    """
