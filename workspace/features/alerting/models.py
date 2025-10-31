"""
Alert Models

Data models for the alerting system.

Author: DevOps Engineer (Agent C)
Date: 2025-10-29
Sprint: Sprint 2 Stream C
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class AlertSeverity(str, Enum):
    """Alert severity levels"""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertCategory(str, Enum):
    """Alert categories for classification"""

    TRADING = "trading"
    SYSTEM = "system"
    RISK = "risk"
    PERFORMANCE = "performance"
    DATA = "data"


class Alert(BaseModel):
    """
    Alert object

    Represents an alert to be sent through configured channels.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = Field(..., description="Alert title")
    message: str = Field(..., description="Alert message")
    severity: AlertSeverity = Field(..., description="Alert severity level")
    category: AlertCategory = Field(
        default=AlertCategory.SYSTEM, description="Alert category"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional metadata"
    )

    class Config:
        use_enum_values = True


class AlertDeliveryStatus(str, Enum):
    """Alert delivery status"""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    THROTTLED = "throttled"


class AlertDeliveryRecord(BaseModel):
    """Record of alert delivery to a channel"""

    alert_id: str
    channel_name: str
    status: AlertDeliveryStatus
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    error_message: Optional[str] = None
    retry_count: int = 0


# Export
__all__ = [
    "AlertSeverity",
    "AlertCategory",
    "Alert",
    "AlertDeliveryStatus",
    "AlertDeliveryRecord",
]
