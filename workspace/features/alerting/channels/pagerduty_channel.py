"""
PagerDuty Alert Channel

Sends critical alerts to PagerDuty for incident management.

Supports:
- Event creation via Events API v2
- Severity mapping
- Custom details
- Deduplication

Author: DevOps Engineer (Agent C)
Date: 2025-10-29
Sprint: Sprint 2 Stream C
"""

import logging

import httpx

from ..alert_service import AlertChannel
from ..models import Alert, AlertSeverity

logger = logging.getLogger(__name__)


class PagerDutyAlertChannel(AlertChannel):
    """
    PagerDuty alert channel

    Sends alerts to PagerDuty via Events API v2.
    """

    def __init__(
        self,
        integration_key: str,
        min_severity: AlertSeverity = AlertSeverity.CRITICAL,
    ):
        """
        Initialize PagerDuty channel

        Args:
            integration_key: PagerDuty integration key (routing key)
            min_severity: Minimum severity to send to PagerDuty
                         (default: CRITICAL only)
        """
        super().__init__(name="pagerduty")
        self.integration_key = integration_key
        self.min_severity = min_severity
        self.api_url = "https://events.pagerduty.com/v2/enqueue"

        logger.info(f"PagerDuty channel initialized (min_severity={min_severity})")

    async def send(self, alert: Alert) -> bool:
        """
        Send PagerDuty alert

        Args:
            alert: Alert to send

        Returns:
            True if sent successfully, False otherwise
        """
        # Check if severity meets minimum threshold
        severity_order = {
            AlertSeverity.INFO: 0,
            AlertSeverity.WARNING: 1,
            AlertSeverity.CRITICAL: 2,
        }

        if severity_order.get(alert.severity, 0) < severity_order.get(
            self.min_severity, 2
        ):
            logger.debug(
                f"Alert severity {alert.severity} below minimum {self.min_severity}, skipping PagerDuty"
            )
            return True  # Not an error, just filtered

        try:
            # Build PagerDuty event
            payload = self._build_payload(alert)

            # Send to PagerDuty
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.api_url, json=payload)
                response.raise_for_status()

            logger.info(f"PagerDuty alert sent: {alert.title}")
            return True

        except httpx.HTTPStatusError as e:
            logger.error(
                f"PagerDuty API error: {e.response.status_code} - {e.response.text}"
            )
            return False
        except Exception as e:
            logger.error(f"Failed to send PagerDuty alert: {e}", exc_info=True)
            return False

    def _build_payload(self, alert: Alert) -> dict:
        """Build PagerDuty event payload"""
        # Map severity to PagerDuty severity
        pd_severity_map = {
            AlertSeverity.INFO: "info",
            AlertSeverity.WARNING: "warning",
            AlertSeverity.CRITICAL: "critical",
        }
        pd_severity = pd_severity_map.get(alert.severity, "error")

        # Build custom details
        custom_details = {
            "category": alert.category,
            "alert_id": alert.id,
            "message": alert.message,
            "timestamp": alert.timestamp.isoformat(),
        }

        # Add metadata to custom details
        if alert.metadata:
            custom_details.update(alert.metadata)

        # Build payload
        payload = {
            "routing_key": self.integration_key,
            "event_action": "trigger",
            "dedup_key": f"trading-alert-{alert.id}",
            "payload": {
                "summary": alert.title,
                "severity": pd_severity,
                "source": "trading-system",
                "component": alert.category,
                "custom_details": custom_details,
            },
        }

        return payload

    async def resolve_alert(self, alert_id: str) -> bool:
        """
        Resolve an alert in PagerDuty

        Args:
            alert_id: Alert ID to resolve

        Returns:
            True if resolved successfully, False otherwise
        """
        try:
            payload = {
                "routing_key": self.integration_key,
                "event_action": "resolve",
                "dedup_key": f"trading-alert-{alert_id}",
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.api_url, json=payload)
                response.raise_for_status()

            logger.info(f"PagerDuty alert resolved: {alert_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to resolve PagerDuty alert: {e}", exc_info=True)
            return False


# Export
__all__ = ["PagerDutyAlertChannel"]
