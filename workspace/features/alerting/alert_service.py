"""
Alert Service

Multi-channel alerting system for trading operations.

Supports:
- Email alerts via SMTP
- Slack alerts via webhooks
- PagerDuty alerts for critical events
- Alert routing based on severity
- Alert throttling to prevent spam

Author: DevOps Engineer (Agent C)
Date: 2025-10-29
Sprint: Sprint 2 Stream C
"""

import logging
from typing import List, Dict
from datetime import datetime, timedelta

from .models import (
    Alert,
    AlertSeverity,
    AlertDeliveryStatus,
    AlertDeliveryRecord,
)

logger = logging.getLogger(__name__)


class AlertChannel:
    """Base class for alert channels"""

    def __init__(self, name: str):
        self.name = name
        self.enabled = True

    async def send(self, alert: Alert) -> bool:
        """
        Send alert through this channel

        Args:
            alert: Alert to send

        Returns:
            True if sent successfully, False otherwise
        """
        raise NotImplementedError("Subclasses must implement send()")

    def disable(self):
        """Disable this channel"""
        self.enabled = False

    def enable(self):
        """Enable this channel"""
        self.enabled = True


class AlertRoutingRules:
    """
    Alert routing configuration

    Maps severity levels to appropriate channels.
    """

    def __init__(self):
        self.rules: Dict[AlertSeverity, List[str]] = {
            AlertSeverity.INFO: ["email"],
            AlertSeverity.WARNING: ["email", "slack"],
            AlertSeverity.CRITICAL: ["email", "slack", "pagerduty"],
        }
        self.channel_map: Dict[str, AlertChannel] = {}

    def register_channel(self, name: str, channel: AlertChannel):
        """
        Register channel for routing

        Args:
            name: Channel name (e.g., 'email', 'slack')
            channel: AlertChannel instance
        """
        self.channel_map[name] = channel
        logger.info(f"Registered alert channel: {name}")

    def get_channels(self, severity: AlertSeverity) -> List[AlertChannel]:
        """
        Get channels for severity level

        Args:
            severity: Alert severity

        Returns:
            List of enabled AlertChannel instances
        """
        channel_names = self.rules.get(severity, [])
        channels = []

        for name in channel_names:
            if name in self.channel_map:
                channel = self.channel_map[name]
                if channel.enabled:
                    channels.append(channel)

        return channels

    def set_routing(self, severity: AlertSeverity, channels: List[str]):
        """
        Set routing for severity level

        Args:
            severity: Alert severity
            channels: List of channel names
        """
        self.rules[severity] = channels
        logger.info(f"Updated routing for {severity}: {channels}")


class AlertThrottler:
    """
    Alert throttling to prevent spam

    Prevents sending duplicate alerts within a time window.
    """

    def __init__(self, throttle_window: int = 300):
        """
        Initialize throttler

        Args:
            throttle_window: Throttle window in seconds (default: 300 = 5 minutes)
        """
        self.throttle_window = throttle_window
        self.recent_alerts: Dict[str, datetime] = {}

    def should_send(self, alert: Alert) -> bool:
        """
        Check if alert should be sent (throttling)

        Args:
            alert: Alert to check

        Returns:
            True if alert should be sent, False if throttled
        """
        # Create throttle key based on title and severity
        key = f"{alert.title}:{alert.severity}"

        # Check if we've sent this alert recently
        if key in self.recent_alerts:
            last_sent = self.recent_alerts[key]
            time_since_last = (datetime.utcnow() - last_sent).total_seconds()

            if time_since_last < self.throttle_window:
                logger.debug(
                    f"Alert throttled: {alert.title} (last sent {time_since_last:.1f}s ago)"
                )
                return False

        # Update last sent time
        self.recent_alerts[key] = datetime.utcnow()

        # Clean old entries (older than 2x throttle window)
        cutoff_time = datetime.utcnow() - timedelta(seconds=self.throttle_window * 2)
        self.recent_alerts = {
            k: v for k, v in self.recent_alerts.items() if v > cutoff_time
        }

        return True

    def reset(self):
        """Reset throttler state"""
        self.recent_alerts.clear()
        logger.info("Alert throttler reset")


class AlertService:
    """
    Alert Service

    Central service for sending alerts through multiple channels.
    """

    def __init__(self, throttle_window: int = 300):
        """
        Initialize alert service

        Args:
            throttle_window: Throttle window in seconds (default: 300)
        """
        self.routing_rules = AlertRoutingRules()
        self.throttler = AlertThrottler(throttle_window=throttle_window)
        self.delivery_history: List[AlertDeliveryRecord] = []
        self._max_history = 1000  # Keep last 1000 delivery records

        logger.info(f"Alert Service initialized (throttle={throttle_window}s)")

    def register_channel(self, name: str, channel: AlertChannel):
        """
        Register alert channel

        Args:
            name: Channel name
            channel: AlertChannel instance
        """
        self.routing_rules.register_channel(name, channel)

    async def send_alert(
        self, alert: Alert, force: bool = False
    ) -> Dict[str, AlertDeliveryStatus]:
        """
        Send alert to appropriate channels

        Args:
            alert: Alert to send
            force: If True, bypass throttling

        Returns:
            Dictionary mapping channel names to delivery status
        """
        # Check throttling
        if not force and not self.throttler.should_send(alert):
            logger.info(f"Alert throttled: {alert.title}")
            return {"throttled": AlertDeliveryStatus.THROTTLED}

        # Get channels for this severity
        channels = self.routing_rules.get_channels(alert.severity)

        if not channels:
            logger.warning(f"No channels configured for severity {alert.severity}")
            return {}

        # Send to each channel
        results = {}
        for channel in channels:
            try:
                logger.info(
                    f"Sending {alert.severity} alert to {channel.name}: {alert.title}"
                )

                success = await channel.send(alert)

                status = (
                    AlertDeliveryStatus.SENT if success else AlertDeliveryStatus.FAILED
                )

                results[channel.name] = status

                # Record delivery
                record = AlertDeliveryRecord(
                    alert_id=alert.id,
                    channel_name=channel.name,
                    status=status,
                )
                self._track_delivery(record)

            except Exception as e:
                logger.error(
                    f"Failed to send alert via {channel.name}: {e}", exc_info=True
                )
                results[channel.name] = AlertDeliveryStatus.FAILED

                # Record failure
                record = AlertDeliveryRecord(
                    alert_id=alert.id,
                    channel_name=channel.name,
                    status=AlertDeliveryStatus.FAILED,
                    error_message=str(e),
                )
                self._track_delivery(record)

        return results

    def _track_delivery(self, record: AlertDeliveryRecord):
        """Track alert delivery"""
        self.delivery_history.append(record)

        # Trim history
        if len(self.delivery_history) > self._max_history:
            self.delivery_history = self.delivery_history[-self._max_history :]

    def get_delivery_stats(self) -> Dict:
        """Get alert delivery statistics"""
        total = len(self.delivery_history)
        if total == 0:
            return {
                "total": 0,
                "sent": 0,
                "failed": 0,
                "success_rate": 0.0,
            }

        sent = sum(
            1 for r in self.delivery_history if r.status == AlertDeliveryStatus.SENT
        )
        failed = sum(
            1 for r in self.delivery_history if r.status == AlertDeliveryStatus.FAILED
        )

        return {
            "total": total,
            "sent": sent,
            "failed": failed,
            "success_rate": sent / total if total > 0 else 0.0,
        }

    def get_recent_alerts(self, limit: int = 10) -> List[AlertDeliveryRecord]:
        """
        Get recent alert deliveries

        Args:
            limit: Maximum number of records to return

        Returns:
            List of recent AlertDeliveryRecord objects
        """
        return self.delivery_history[-limit:]


# Export
__all__ = [
    "AlertChannel",
    "AlertRoutingRules",
    "AlertThrottler",
    "AlertService",
]
