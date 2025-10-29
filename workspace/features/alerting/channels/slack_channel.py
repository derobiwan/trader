"""
Slack Alert Channel

Sends alerts to Slack via webhook.

Supports:
- Rich message formatting
- Color-coded severity levels
- Metadata fields
- Link buttons

Author: DevOps Engineer (Agent C)
Date: 2025-10-29
Sprint: Sprint 2 Stream C
"""

import httpx
import logging
from typing import Optional

from ..alert_service import AlertChannel
from ..models import Alert, AlertSeverity

logger = logging.getLogger(__name__)


class SlackAlertChannel(AlertChannel):
    """
    Slack alert channel

    Sends alerts to Slack via incoming webhooks.
    """

    def __init__(
        self,
        webhook_url: str,
        username: Optional[str] = "Trading System",
        icon_emoji: Optional[str] = ":chart_with_upwards_trend:",
    ):
        """
        Initialize Slack channel

        Args:
            webhook_url: Slack incoming webhook URL
            username: Bot username (default: "Trading System")
            icon_emoji: Bot icon emoji (default: chart icon)
        """
        super().__init__(name="slack")
        self.webhook_url = webhook_url
        self.username = username
        self.icon_emoji = icon_emoji

        logger.info("Slack channel initialized")

    async def send(self, alert: Alert) -> bool:
        """
        Send Slack alert

        Args:
            alert: Alert to send

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Build Slack message
            payload = self._build_payload(alert)

            # Send to Slack
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.webhook_url, json=payload)
                response.raise_for_status()

            logger.info(f"Slack alert sent: {alert.title}")
            return True

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Slack API error: {e.response.status_code} - {e.response.text}"
            )
            return False
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}", exc_info=True)
            return False

    def _build_payload(self, alert: Alert) -> dict:
        """Build Slack message payload"""
        # Color based on severity
        severity_colors = {
            AlertSeverity.INFO: "#36a64f",  # Green
            AlertSeverity.WARNING: "#ff9900",  # Orange
            AlertSeverity.CRITICAL: "#ff0000",  # Red
        }
        color = severity_colors.get(alert.severity, "#808080")

        # Emoji based on severity
        severity_emojis = {
            AlertSeverity.INFO: ":information_source:",
            AlertSeverity.WARNING: ":warning:",
            AlertSeverity.CRITICAL: ":rotating_light:",
        }
        emoji = severity_emojis.get(alert.severity, ":bell:")

        # Build attachment fields
        fields = [
            {
                "title": "Severity",
                "value": f"{emoji} *{alert.severity.upper()}*",
                "short": True,
            },
            {
                "title": "Category",
                "value": alert.category.upper(),
                "short": True,
            },
            {
                "title": "Time",
                "value": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "short": True,
            },
        ]

        # Add metadata fields
        if alert.metadata:
            for key, value in alert.metadata.items():
                # Convert key to title case
                title = key.replace("_", " ").title()
                fields.append(
                    {
                        "title": title,
                        "value": str(value),
                        "short": True,
                    }
                )

        # Build payload
        payload = {
            "username": self.username,
            "icon_emoji": self.icon_emoji,
            "attachments": [
                {
                    "color": color,
                    "title": alert.title,
                    "text": alert.message,
                    "fields": fields,
                    "footer": "Trading System",
                    "footer_icon": "https://platform.slack-edge.com/img/default_application_icon.png",
                    "ts": int(alert.timestamp.timestamp()),
                }
            ],
        }

        return payload


# Export
__all__ = ["SlackAlertChannel"]
