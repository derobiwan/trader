"""
WebSocket Reconnection Manager

Handles automatic reconnection with exponential backoff and jitter.
Implements connection retry logic with configurable delays and max attempts.

Author: Sprint 2 Stream A - WebSocket Stability Team
Date: 2025-10-29
"""

import asyncio
import random
import logging
from typing import Optional, Callable, Any
from datetime import datetime
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class ReconnectionStats:
    """Statistics about reconnection attempts"""

    total_attempts: int = 0
    successful_reconnections: int = 0
    failed_attempts: int = 0
    last_disconnect: Optional[datetime] = None
    last_reconnect: Optional[datetime] = None
    current_uptime_start: Optional[datetime] = None
    total_downtime_seconds: float = 0.0

    def calculate_uptime_percentage(self) -> float:
        """Calculate uptime percentage since first connection"""
        if not self.current_uptime_start:
            return 0.0

        total_time = (datetime.utcnow() - self.current_uptime_start).total_seconds()
        if total_time == 0:
            return 100.0

        uptime_time = total_time - self.total_downtime_seconds
        return (uptime_time / total_time) * 100.0


class WebSocketReconnectionManager:
    """
    Manages WebSocket reconnection with exponential backoff and jitter.

    Features:
    - Exponential backoff with configurable base delay and max delay
    - Jitter to prevent thundering herd
    - Connection state tracking
    - Reconnection statistics
    - Automatic retry on failure

    Example:
        ```python
        manager = WebSocketReconnectionManager(base_delay=1.0, max_delay=60.0)

        async def connect():
            # Your connection logic here
            await websocket.connect()

        await manager.connect_with_retry(connect)
        ```
    """

    def __init__(
        self,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        max_attempts: Optional[int] = None,
        jitter_range: float = 0.1,
    ):
        """
        Initialize WebSocket Reconnection Manager

        Args:
            base_delay: Initial delay between reconnection attempts (seconds)
            max_delay: Maximum delay between reconnection attempts (seconds)
            max_attempts: Maximum number of reconnection attempts (None = unlimited)
            jitter_range: Random jitter range as fraction of delay (0.1 = +/- 10%)
        """
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.max_attempts = max_attempts
        self.jitter_range = jitter_range

        # Connection state
        self.attempt = 0
        self.is_connected = False
        self.is_connecting = False

        # Statistics
        self.stats = ReconnectionStats()

    def calculate_backoff(self) -> float:
        """
        Calculate exponential backoff with jitter

        Formula: min(base_delay * (2 ** attempt), max_delay) + jitter
        Jitter: random value in range [-jitter_range * delay, +jitter_range * delay]

        Returns:
            Delay in seconds before next reconnection attempt
        """
        # Exponential backoff: 1, 2, 4, 8, 16, 32, 60 (capped at max_delay)
        delay = min(self.base_delay * (2**self.attempt), self.max_delay)

        # Add jitter to prevent thundering herd problem
        # Jitter range: +/- (jitter_range * delay)
        jitter = random.uniform(-delay * self.jitter_range, delay * self.jitter_range)

        return max(0, delay + jitter)  # Ensure non-negative

    async def connect_with_retry(
        self,
        connect_func: Callable[[], Any],
        on_attempt: Optional[Callable[[int, float], None]] = None,
    ) -> bool:
        """
        Connect with exponential backoff retry

        Args:
            connect_func: Async function to establish connection
            on_attempt: Optional callback called before each attempt (attempt_num, delay)

        Returns:
            True if connection successful, False if max_attempts reached

        Raises:
            Exception: If connect_func raises an unhandled exception
        """
        self.is_connecting = True
        self.stats.total_attempts = 0

        while not self.is_connected:
            # Check max attempts
            if self.max_attempts and self.attempt >= self.max_attempts:
                logger.error(
                    f"Max reconnection attempts ({self.max_attempts}) reached. Giving up."
                )
                self.stats.failed_attempts += 1
                self.is_connecting = False
                return False

            try:
                self.stats.total_attempts += 1
                self.attempt += 1

                logger.info(
                    f"Connection attempt {self.attempt}"
                    + (f"/{self.max_attempts}" if self.max_attempts else "")
                )

                # Attempt connection
                await connect_func()

                # Connection successful
                self.is_connected = True
                self.is_connecting = False
                self.stats.successful_reconnections += 1
                self.stats.last_reconnect = datetime.utcnow()

                # Track uptime
                if not self.stats.current_uptime_start:
                    self.stats.current_uptime_start = datetime.utcnow()

                # Calculate downtime
                if self.stats.last_disconnect:
                    downtime = (
                        datetime.utcnow() - self.stats.last_disconnect
                    ).total_seconds()
                    self.stats.total_downtime_seconds += downtime

                logger.info(
                    f"Connection successful after {self.attempt} attempt(s). "
                    f"Uptime: {self.stats.calculate_uptime_percentage():.2f}%"
                )

                self.reset()
                return True

            except Exception as e:
                self.stats.failed_attempts += 1
                logger.warning(
                    f"Connection attempt {self.attempt} failed: {e}",
                    exc_info=False,  # Don't log full traceback for expected reconnection errors
                )

                # Calculate backoff delay
                delay = self.calculate_backoff()

                # Notify about retry
                if on_attempt:
                    try:
                        if asyncio.iscoroutinefunction(on_attempt):
                            await on_attempt(self.attempt, delay)
                        else:
                            on_attempt(self.attempt, delay)
                    except Exception as callback_error:
                        logger.error(f"on_attempt callback failed: {callback_error}")

                logger.info(f"Retrying in {delay:.2f}s...")
                await asyncio.sleep(delay)

    def mark_disconnected(self):
        """Mark connection as disconnected and record disconnect time"""
        if self.is_connected:
            self.is_connected = False
            self.stats.last_disconnect = datetime.utcnow()
            logger.info("Connection marked as disconnected")

    def reset(self):
        """Reset backoff after successful connection"""
        self.attempt = 0
        logger.debug("Reconnection backoff reset")

    def get_stats(self) -> dict:
        """
        Get reconnection statistics

        Returns:
            Dictionary with reconnection statistics
        """
        return {
            "is_connected": self.is_connected,
            "is_connecting": self.is_connecting,
            "current_attempt": self.attempt,
            "total_attempts": self.stats.total_attempts,
            "successful_reconnections": self.stats.successful_reconnections,
            "failed_attempts": self.stats.failed_attempts,
            "last_disconnect": (
                self.stats.last_disconnect.isoformat()
                if self.stats.last_disconnect
                else None
            ),
            "last_reconnect": (
                self.stats.last_reconnect.isoformat()
                if self.stats.last_reconnect
                else None
            ),
            "uptime_percentage": self.stats.calculate_uptime_percentage(),
            "total_downtime_seconds": self.stats.total_downtime_seconds,
        }


# Export
__all__ = ["WebSocketReconnectionManager", "ReconnectionStats"]
