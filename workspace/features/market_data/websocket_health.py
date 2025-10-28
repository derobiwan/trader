"""
WebSocket Health Monitor

Monitors WebSocket connection health through heartbeat tracking and message activity.
Detects connection issues before they cause failures.

Author: Sprint 2 Stream A - WebSocket Stability Team
Date: 2025-10-29
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass, field


logger = logging.getLogger(__name__)


@dataclass
class HealthMetrics:
    """Health metrics for WebSocket connection"""
    total_messages: int = 0
    messages_per_minute: float = 0.0
    total_errors: int = 0
    error_rate: float = 0.0
    last_health_check: Optional[datetime] = None
    health_check_count: int = 0
    consecutive_unhealthy_checks: int = 0


class WebSocketHealthMonitor:
    """
    Monitors WebSocket connection health

    Features:
    - Heartbeat-based health detection
    - Message activity tracking
    - Error rate monitoring
    - Health statistics and reporting

    A connection is considered unhealthy if:
    - No messages received for 2x heartbeat interval
    - Error rate exceeds threshold
    - Consecutive health check failures

    Example:
        ```python
        monitor = WebSocketHealthMonitor(heartbeat_interval=30)

        # Record message activity
        monitor.record_message()

        # Check health
        if not monitor.check_health():
            # Trigger reconnection
            await reconnect()

        # Get statistics
        stats = monitor.get_stats()
        ```
    """

    def __init__(
        self,
        heartbeat_interval: int = 30,
        unhealthy_threshold: float = 2.0,
        error_rate_threshold: float = 0.1,
    ):
        """
        Initialize WebSocket Health Monitor

        Args:
            heartbeat_interval: Expected interval between messages (seconds)
            unhealthy_threshold: Multiplier for heartbeat to consider unhealthy
            error_rate_threshold: Max error rate before considering unhealthy (0.1 = 10%)
        """
        self.heartbeat_interval = heartbeat_interval
        self.unhealthy_threshold = unhealthy_threshold
        self.error_rate_threshold = error_rate_threshold

        # Health state
        self.is_healthy = True
        self.last_message_time: Optional[datetime] = None
        self.first_message_time: Optional[datetime] = None

        # Metrics
        self.metrics = HealthMetrics()

        # Disconnect tracking
        self.disconnect_count = 0
        self.last_disconnect: Optional[datetime] = None

        # Message rate tracking
        self._message_timestamps = []
        self._message_rate_window = 60  # 1 minute window

    def record_message(self, message_type: str = "data"):
        """
        Record that a message was received

        Args:
            message_type: Type of message ('data', 'ping', 'pong', etc.)
        """
        now = datetime.utcnow()

        self.last_message_time = now
        if not self.first_message_time:
            self.first_message_time = now

        self.is_healthy = True
        self.metrics.total_messages += 1
        self.metrics.consecutive_unhealthy_checks = 0

        # Track message rate
        self._message_timestamps.append(now)
        self._cleanup_old_timestamps()
        self._update_message_rate()

        logger.debug(f"Message recorded: {message_type}")

    def record_error(self, error: Exception):
        """
        Record an error

        Args:
            error: Exception that occurred
        """
        self.metrics.total_errors += 1
        self._update_error_rate()

        logger.warning(f"Error recorded: {error}")

        # Check if error rate is too high
        if self.metrics.error_rate > self.error_rate_threshold:
            self.is_healthy = False
            logger.error(
                f"Error rate too high: {self.metrics.error_rate:.2%} "
                f"(threshold: {self.error_rate_threshold:.2%})"
            )

    def record_disconnect(self):
        """Record a disconnect event"""
        self.disconnect_count += 1
        self.last_disconnect = datetime.utcnow()
        self.is_healthy = False

        logger.info(f"Disconnect recorded (total: {self.disconnect_count})")

    def check_health(self) -> bool:
        """
        Check if WebSocket connection is healthy

        Returns:
            True if healthy, False if unhealthy
        """
        now = datetime.utcnow()
        self.metrics.last_health_check = now
        self.metrics.health_check_count += 1

        # No messages received yet
        if not self.last_message_time:
            logger.debug("Health check: No messages received yet")
            return False

        # Check time since last message
        time_since_last = (now - self.last_message_time).total_seconds()
        max_silence = self.heartbeat_interval * self.unhealthy_threshold

        if time_since_last > max_silence:
            self.is_healthy = False
            self.metrics.consecutive_unhealthy_checks += 1

            logger.warning(
                f"Health check FAILED: No messages for {time_since_last:.1f}s "
                f"(threshold: {max_silence:.1f}s)"
            )
            return False

        # Check error rate
        if self.metrics.error_rate > self.error_rate_threshold:
            self.is_healthy = False
            self.metrics.consecutive_unhealthy_checks += 1

            logger.warning(
                f"Health check FAILED: Error rate {self.metrics.error_rate:.2%} "
                f"exceeds threshold {self.error_rate_threshold:.2%}"
            )
            return False

        # Healthy
        self.is_healthy = True
        self.metrics.consecutive_unhealthy_checks = 0

        logger.debug(
            f"Health check OK: Last message {time_since_last:.1f}s ago, "
            f"message rate {self.metrics.messages_per_minute:.1f}/min"
        )
        return True

    def _cleanup_old_timestamps(self):
        """Remove timestamps older than tracking window"""
        cutoff = datetime.utcnow() - timedelta(seconds=self._message_rate_window)
        self._message_timestamps = [
            ts for ts in self._message_timestamps if ts > cutoff
        ]

    def _update_message_rate(self):
        """Update messages per minute rate"""
        if not self._message_timestamps:
            self.metrics.messages_per_minute = 0.0
            return

        # Calculate messages per minute
        window_duration = (
            datetime.utcnow() - self._message_timestamps[0]
        ).total_seconds()

        if window_duration > 0:
            messages_per_second = len(self._message_timestamps) / window_duration
            self.metrics.messages_per_minute = messages_per_second * 60
        else:
            self.metrics.messages_per_minute = 0.0

    def _update_error_rate(self):
        """Update error rate"""
        if self.metrics.total_messages == 0:
            self.metrics.error_rate = 0.0
        else:
            self.metrics.error_rate = (
                self.metrics.total_errors / self.metrics.total_messages
            )

    def get_seconds_since_last_message(self) -> Optional[float]:
        """
        Get seconds since last message

        Returns:
            Seconds since last message, or None if no messages received
        """
        if not self.last_message_time:
            return None

        return (datetime.utcnow() - self.last_message_time).total_seconds()

    def get_uptime_seconds(self) -> Optional[float]:
        """
        Get connection uptime in seconds

        Returns:
            Seconds since first message, or None if no messages received
        """
        if not self.first_message_time:
            return None

        return (datetime.utcnow() - self.first_message_time).total_seconds()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive health statistics

        Returns:
            Dictionary with health statistics
        """
        seconds_since_last = self.get_seconds_since_last_message()
        uptime_seconds = self.get_uptime_seconds()

        return {
            "is_healthy": self.is_healthy,
            "last_message_seconds_ago": seconds_since_last,
            "uptime_seconds": uptime_seconds,
            "total_messages": self.metrics.total_messages,
            "messages_per_minute": round(self.metrics.messages_per_minute, 2),
            "total_errors": self.metrics.total_errors,
            "error_rate": round(self.metrics.error_rate, 4),
            "disconnect_count": self.disconnect_count,
            "last_disconnect": (
                self.last_disconnect.isoformat() if self.last_disconnect else None
            ),
            "health_check_count": self.metrics.health_check_count,
            "consecutive_unhealthy_checks": self.metrics.consecutive_unhealthy_checks,
            "heartbeat_interval": self.heartbeat_interval,
            "unhealthy_threshold": self.unhealthy_threshold,
            "max_silence_seconds": self.heartbeat_interval * self.unhealthy_threshold,
        }

    def reset_metrics(self):
        """Reset all metrics (use after successful reconnection)"""
        self.metrics = HealthMetrics()
        self._message_timestamps = []
        logger.info("Health metrics reset")


# Export
__all__ = ["WebSocketHealthMonitor", "HealthMetrics"]
