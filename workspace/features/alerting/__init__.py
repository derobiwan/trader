"""
Alerting System

Multi-channel alerting for trading operations.

Features:
- Email alerts via SMTP
- Slack alerts via webhooks
- PagerDuty alerts for critical events
- Alert routing based on severity
- Alert throttling to prevent spam

Author: DevOps Engineer (Agent C)
Date: 2025-10-29
Sprint: Sprint 2 Stream C
"""

from .alert_service import (AlertChannel, AlertRoutingRules, AlertService,
                            AlertThrottler)
from .channels import (EmailAlertChannel, PagerDutyAlertChannel,
                       SlackAlertChannel)
from .models import (Alert, AlertCategory, AlertDeliveryRecord,
                     AlertDeliveryStatus, AlertSeverity)

__all__ = [
    # Models
    "Alert",
    "AlertSeverity",
    "AlertCategory",
    "AlertDeliveryStatus",
    "AlertDeliveryRecord",
    # Service
    "AlertChannel",
    "AlertRoutingRules",
    "AlertThrottler",
    "AlertService",
    # Channels
    "EmailAlertChannel",
    "SlackAlertChannel",
    "PagerDutyAlertChannel",
]
