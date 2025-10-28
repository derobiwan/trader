"""
Error Recovery Module

Circuit breaker and retry logic for fault tolerance.

Components:
- CircuitBreaker: Circuit breaker pattern implementation
- RetryManager: Intelligent retry with exponential backoff

Author: Trading System Implementation Team
Date: 2025-10-28
"""

from .circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitBreakerOpenError,
)
from .retry_manager import (
    RetryManager,
    RetryStrategy,
    retry,
)

__all__ = [
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitState",
    "CircuitBreakerOpenError",
    # Retry Manager
    "RetryManager",
    "RetryStrategy",
    "retry",
]
