"""
Retry Manager

Provides intelligent retry logic with exponential backoff.

Author: Trading System Implementation Team
Date: 2025-10-28
"""

import asyncio
import logging
from enum import Enum
from typing import Any, Callable, Optional, Type

logger = logging.getLogger(__name__)


class RetryStrategy(str, Enum):
    """Retry strategies"""

    EXPONENTIAL = "exponential"  # Exponential backoff (2^attempt * base_delay)
    LINEAR = "linear"  # Linear increase (attempt * base_delay)
    FIXED = "fixed"  # Fixed delay (base_delay)
    FIBONACCI = "fibonacci"  # Fibonacci backoff


class RetryManager:
    """
    Retry manager with multiple strategies

    Provides intelligent retry logic with:
    - Multiple backoff strategies
    - Max retry limits
    - Exception filtering
    - Jitter for avoiding thundering herd
    - Retry statistics
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay_seconds: float = 1.0,
        max_delay_seconds: float = 60.0,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
        jitter: bool = True,
        retryable_exceptions: Optional[tuple[Type[Exception], ...]] = None,
    ):
        """
        Initialize retry manager

        Args:
            max_retries: Maximum retry attempts
            base_delay_seconds: Base delay between retries
            max_delay_seconds: Maximum delay cap
            strategy: Retry strategy to use
            jitter: Add random jitter to delays
            retryable_exceptions: Tuple of exceptions that trigger retry (None = all)
        """
        self.max_retries = max_retries
        self.base_delay_seconds = base_delay_seconds
        self.max_delay_seconds = max_delay_seconds
        self.strategy = strategy
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or (Exception,)

        # Statistics
        self.stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "total_retries": 0,
            "total_delay_seconds": 0.0,
        }

        logger.info(
            f"Retry Manager initialized: "
            f"max_retries={max_retries}, strategy={strategy.value}"
        )

    def _calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for given attempt

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        if self.strategy == RetryStrategy.EXPONENTIAL:
            # Exponential backoff: 2^attempt * base_delay
            delay = self.base_delay_seconds * (2**attempt)

        elif self.strategy == RetryStrategy.LINEAR:
            # Linear backoff: attempt * base_delay
            delay = self.base_delay_seconds * (attempt + 1)

        elif self.strategy == RetryStrategy.FIXED:
            # Fixed delay
            delay = self.base_delay_seconds

        elif self.strategy == RetryStrategy.FIBONACCI:
            # Fibonacci backoff
            fib = self._fibonacci(attempt + 1)
            delay = self.base_delay_seconds * fib

        else:
            delay = self.base_delay_seconds

        # Apply max delay cap
        delay = min(delay, self.max_delay_seconds)

        # Add jitter if enabled
        if self.jitter:
            import random

            jitter_amount = delay * 0.1 * random.random()
            delay += jitter_amount

        return float(delay)

    @staticmethod
    def _fibonacci(n: int) -> int:
        """Calculate nth Fibonacci number"""
        if n <= 1:
            return n
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b

    def _is_retryable(self, exception: Exception) -> bool:
        """Check if exception is retryable"""
        return isinstance(exception, self.retryable_exceptions)

    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with retry logic

        Args:
            func: Function to execute (can be sync or async)
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            Last exception if all retries exhausted
        """
        self.stats["total_calls"] += 1
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                # Execute function
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                # Success
                if attempt > 0:
                    logger.info(f"Retry successful after {attempt} attempts")
                    self.stats["total_retries"] += attempt

                self.stats["successful_calls"] += 1
                return result

            except Exception as e:
                last_exception = e

                # Check if retryable
                if not self._is_retryable(e):
                    logger.error(f"Non-retryable exception: {type(e).__name__}: {e}")
                    self.stats["failed_calls"] += 1
                    raise

                # Check if retries exhausted
                if attempt >= self.max_retries:
                    logger.error(
                        f"All {self.max_retries} retries exhausted. "
                        f"Last error: {type(e).__name__}: {e}"
                    )
                    self.stats["failed_calls"] += 1
                    raise

                # Calculate delay
                delay = self._calculate_delay(attempt)
                self.stats["total_delay_seconds"] += delay

                logger.warning(
                    f"Attempt {attempt + 1}/{self.max_retries + 1} failed: "
                    f"{type(e).__name__}: {e}. "
                    f"Retrying in {delay:.2f}s..."
                )

                # Wait before retry
                await asyncio.sleep(delay)

        # Should never reach here, but just in case
        if last_exception:
            raise last_exception

    def get_stats(self) -> dict[str, Any]:
        """Get retry statistics"""
        success_rate = (
            (self.stats["successful_calls"] / self.stats["total_calls"] * 100)
            if self.stats["total_calls"] > 0
            else 0
        )

        avg_retries = (
            (self.stats["total_retries"] / self.stats["successful_calls"])
            if self.stats["successful_calls"] > 0
            else 0
        )

        return {
            **self.stats,
            "success_rate": f"{success_rate:.2f}%",
            "average_retries_per_success": f"{avg_retries:.2f}",
            "max_retries": self.max_retries,
            "strategy": self.strategy.value,
        }


# Decorator for easy retry functionality
def retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
    exceptions: Optional[tuple[Type[Exception], ...]] = None,
):
    """
    Decorator to add retry logic to a function

    Usage:
        @retry(max_retries=3, base_delay=1.0)
        async def fetch_data():
            # Your code here
            pass
    """

    def decorator(func: Callable) -> Callable:
        retry_manager = RetryManager(
            max_retries=max_retries,
            base_delay_seconds=base_delay,
            strategy=strategy,
            retryable_exceptions=exceptions,
        )

        async def wrapper(*args, **kwargs):
            return await retry_manager.execute(func, *args, **kwargs)

        return wrapper

    return decorator


# Export
__all__ = [
    "RetryManager",
    "RetryStrategy",
    "retry",
]
