"""
Circuit Breaker Pattern Implementation

Prevents cascading failures by temporarily blocking operations
when error rate exceeds threshold.

Author: Trading System Implementation Team
Date: 2025-10-28
"""

import logging
import time
from enum import Enum
from typing import Optional, Callable, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states"""
    CLOSED = "closed"        # Normal operation, requests pass through
    OPEN = "open"            # Circuit open, requests blocked
    HALF_OPEN = "half_open"  # Testing if system recovered


class CircuitBreaker:
    """
    Circuit Breaker for fault tolerance

    States:
    - CLOSED: Normal operation, all requests pass through
    - OPEN: Too many failures, block all requests
    - HALF_OPEN: Testing recovery, allow limited requests

    Transitions:
    - CLOSED -> OPEN: When failure threshold exceeded
    - OPEN -> HALF_OPEN: After timeout period
    - HALF_OPEN -> CLOSED: When test requests succeed
    - HALF_OPEN -> OPEN: When test requests fail
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout_seconds: int = 60,
        expected_exception: type = Exception,
        half_open_max_calls: int = 3,
    ):
        """
        Initialize circuit breaker

        Args:
            name: Circuit breaker name (for logging)
            failure_threshold: Number of failures before opening circuit
            recovery_timeout_seconds: Seconds to wait before testing recovery
            expected_exception: Exception type that triggers circuit
            half_open_max_calls: Max calls allowed in HALF_OPEN state
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.expected_exception = expected_exception
        self.half_open_max_calls = half_open_max_calls

        # State
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._opened_at: Optional[float] = None

        # Statistics
        self.stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "rejected_calls": 0,
            "state_changes": 0,
        }

        logger.info(
            f"Circuit Breaker '{name}' initialized: "
            f"threshold={failure_threshold}, timeout={recovery_timeout_seconds}s"
        )

    @property
    def state(self) -> CircuitState:
        """Get current circuit state"""
        return self._state

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)"""
        return self._state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (blocking requests)"""
        self._check_half_open_transition()
        return self._state == CircuitState.OPEN

    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open (testing recovery)"""
        return self._state == CircuitState.HALF_OPEN

    def _check_half_open_transition(self):
        """Check if circuit should transition from OPEN to HALF_OPEN"""
        if self._state == CircuitState.OPEN and self._opened_at:
            time_since_open = time.time() - self._opened_at
            if time_since_open >= self.recovery_timeout_seconds:
                self._transition_to_half_open()

    def _transition_to_half_open(self):
        """Transition to HALF_OPEN state"""
        self._state = CircuitState.HALF_OPEN
        self._failure_count = 0
        self._success_count = 0
        self.stats["state_changes"] += 1
        logger.info(f"Circuit Breaker '{self.name}': OPEN -> HALF_OPEN (testing recovery)")

    def _transition_to_open(self):
        """Transition to OPEN state"""
        self._state = CircuitState.OPEN
        self._opened_at = time.time()
        self.stats["state_changes"] += 1
        logger.warning(
            f"Circuit Breaker '{self.name}': -> OPEN "
            f"(threshold exceeded: {self._failure_count} failures)"
        )

    def _transition_to_closed(self):
        """Transition to CLOSED state"""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._opened_at = None
        self.stats["state_changes"] += 1
        logger.info(f"Circuit Breaker '{self.name}': -> CLOSED (recovered)")

    def _record_success(self):
        """Record successful call"""
        self.stats["total_calls"] += 1
        self.stats["successful_calls"] += 1

        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            logger.debug(
                f"Circuit Breaker '{self.name}': HALF_OPEN success "
                f"({self._success_count}/{self.half_open_max_calls})"
            )

            # Enough successes to close circuit
            if self._success_count >= self.half_open_max_calls:
                self._transition_to_closed()
        else:
            # Reset failure count on success in CLOSED state
            self._failure_count = 0

    def _record_failure(self):
        """Record failed call"""
        self.stats["total_calls"] += 1
        self.stats["failed_calls"] += 1
        self._failure_count += 1
        self._last_failure_time = time.time()

        logger.debug(
            f"Circuit Breaker '{self.name}': Failure recorded "
            f"({self._failure_count}/{self.failure_threshold})"
        )

        if self._state == CircuitState.HALF_OPEN:
            # Any failure in HALF_OPEN reopens circuit
            self._transition_to_open()
        elif self._state == CircuitState.CLOSED:
            # Check if threshold exceeded
            if self._failure_count >= self.failure_threshold:
                self._transition_to_open()

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection

        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenError: If circuit is open
            Original exception: If function fails
        """
        # Check if circuit is open
        if self.is_open:
            self.stats["rejected_calls"] += 1
            raise CircuitBreakerOpenError(
                f"Circuit breaker '{self.name}' is OPEN. "
                f"Retry after {self.recovery_timeout_seconds}s"
            )

        try:
            # Execute function
            if callable(func) and hasattr(func, '__code__'):
                # Sync function
                result = func(*args, **kwargs)
            else:
                # Async function
                result = await func(*args, **kwargs)

            # Record success
            self._record_success()

            return result

        except self.expected_exception as e:
            # Record failure
            self._record_failure()
            raise

    def reset(self):
        """Manually reset circuit breaker to CLOSED state"""
        logger.info(f"Circuit Breaker '{self.name}': Manual reset")
        self._transition_to_closed()

    def get_stats(self) -> dict[str, Any]:
        """Get circuit breaker statistics"""
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout_seconds": self.recovery_timeout_seconds,
            "last_failure_time": (
                datetime.fromtimestamp(self._last_failure_time).isoformat()
                if self._last_failure_time
                else None
            ),
            "opened_at": (
                datetime.fromtimestamp(self._opened_at).isoformat()
                if self._opened_at
                else None
            ),
            **self.stats,
        }


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open"""
    pass


# Export
__all__ = ["CircuitBreaker", "CircuitState", "CircuitBreakerOpenError"]
