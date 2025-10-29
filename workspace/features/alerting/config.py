"""
Alerting Configuration

Configuration loader for alerting system.

Author: DevOps Engineer (Agent C)
Date: 2025-10-29
Sprint: Sprint 2 Stream C
"""

import os
import logging
from typing import Optional, List
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class EmailConfig(BaseModel):
    """Email channel configuration"""

    enabled: bool = Field(default=True)
    smtp_host: str = Field(...)
    smtp_port: int = Field(default=587)
    username: str = Field(...)
    password: str = Field(...)
    from_email: str = Field(...)
    to_emails: List[str] = Field(...)
    use_tls: bool = Field(default=True)


class SlackConfig(BaseModel):
    """Slack channel configuration"""

    enabled: bool = Field(default=True)
    webhook_url: str = Field(...)
    username: Optional[str] = Field(default="Trading System")
    icon_emoji: Optional[str] = Field(default=":chart_with_upwards_trend:")


class PagerDutyConfig(BaseModel):
    """PagerDuty channel configuration"""

    enabled: bool = Field(default=True)
    integration_key: str = Field(...)
    min_severity: str = Field(default="critical")


class AlertingConfig(BaseModel):
    """Alerting system configuration"""

    throttle_window: int = Field(default=300, description="Throttle window in seconds")
    email: Optional[EmailConfig] = None
    slack: Optional[SlackConfig] = None
    pagerduty: Optional[PagerDutyConfig] = None


def load_alerting_config() -> AlertingConfig:
    """
    Load alerting configuration from environment variables

    Returns:
        AlertingConfig object

    Environment Variables:
        # Email
        ALERT_EMAIL_ENABLED=true
        SMTP_HOST=smtp.gmail.com
        SMTP_PORT=587
        SMTP_USERNAME=your_email@gmail.com
        SMTP_PASSWORD=your_app_password
        ALERT_EMAIL_FROM=trading-system@yourcompany.com
        ALERT_EMAIL_TO=alerts@yourcompany.com,admin@yourcompany.com

        # Slack
        ALERT_SLACK_ENABLED=true
        SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

        # PagerDuty
        ALERT_PAGERDUTY_ENABLED=true
        PAGERDUTY_INTEGRATION_KEY=your_key_here

        # General
        ALERT_THROTTLE_WINDOW=300
    """
    config = AlertingConfig(
        throttle_window=int(os.getenv("ALERT_THROTTLE_WINDOW", "300"))
    )

    # Email configuration
    email_enabled = os.getenv("ALERT_EMAIL_ENABLED", "false").lower() == "true"
    smtp_host = os.getenv("SMTP_HOST")
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    email_from = os.getenv("ALERT_EMAIL_FROM")
    email_to = os.getenv("ALERT_EMAIL_TO")

    if email_enabled and all(
        [smtp_host, smtp_username, smtp_password, email_from, email_to]
    ):
        config.email = EmailConfig(
            enabled=True,
            smtp_host=smtp_host,
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            username=smtp_username,
            password=smtp_password,
            from_email=email_from,
            to_emails=[e.strip() for e in email_to.split(",")],
            use_tls=os.getenv("SMTP_USE_TLS", "true").lower() == "true",
        )
        logger.info("Email alerting configured")
    elif email_enabled:
        logger.warning("Email alerting enabled but configuration incomplete")

    # Slack configuration
    slack_enabled = os.getenv("ALERT_SLACK_ENABLED", "false").lower() == "true"
    slack_webhook = os.getenv("SLACK_WEBHOOK_URL")

    if slack_enabled and slack_webhook:
        config.slack = SlackConfig(
            enabled=True,
            webhook_url=slack_webhook,
            username=os.getenv("SLACK_USERNAME", "Trading System"),
            icon_emoji=os.getenv("SLACK_ICON_EMOJI", ":chart_with_upwards_trend:"),
        )
        logger.info("Slack alerting configured")
    elif slack_enabled:
        logger.warning("Slack alerting enabled but webhook URL missing")

    # PagerDuty configuration
    pagerduty_enabled = os.getenv("ALERT_PAGERDUTY_ENABLED", "false").lower() == "true"
    pagerduty_key = os.getenv("PAGERDUTY_INTEGRATION_KEY")

    if pagerduty_enabled and pagerduty_key:
        config.pagerduty = PagerDutyConfig(
            enabled=True,
            integration_key=pagerduty_key,
            min_severity=os.getenv("PAGERDUTY_MIN_SEVERITY", "critical"),
        )
        logger.info("PagerDuty alerting configured")
    elif pagerduty_enabled:
        logger.warning("PagerDuty alerting enabled but integration key missing")

    return config


# Export
__all__ = [
    "EmailConfig",
    "SlackConfig",
    "PagerDutyConfig",
    "AlertingConfig",
    "load_alerting_config",
]
