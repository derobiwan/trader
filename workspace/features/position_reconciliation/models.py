"""
Position Reconciliation Models

Data structures for reconciliation process.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class DiscrepancyType(str, Enum):
    """Type of discrepancy detected"""

    POSITION_MISSING_IN_SYSTEM = "position_missing_in_system"
    POSITION_MISSING_ON_EXCHANGE = "position_missing_on_exchange"
    QUANTITY_MISMATCH = "quantity_mismatch"
    PRICE_MISMATCH = "price_mismatch"
    SIDE_MISMATCH = "side_mismatch"
    NO_DISCREPANCY = "no_discrepancy"


class DiscrepancySeverity(str, Enum):
    """Severity level of discrepancy"""

    INFO = "info"  # Minor difference, within tolerance
    WARNING = "warning"  # Moderate difference, auto-corrected
    CRITICAL = "critical"  # Major difference, requires manual intervention


class ExchangePosition(BaseModel):
    """Position as reported by exchange"""

    symbol: str
    side: str  # "LONG" or "SHORT"
    quantity: Decimal
    entry_price: Decimal
    current_price: Decimal
    unrealized_pnl: Decimal
    leverage: Decimal
    liquidation_price: Optional[Decimal] = None
    margin: Decimal
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SystemPosition(BaseModel):
    """Position as tracked by system"""

    symbol: str
    side: str
    quantity: Decimal
    entry_price: Decimal
    current_price: Decimal
    unrealized_pnl: Decimal
    leverage: Decimal
    stop_loss_price: Optional[Decimal] = None
    take_profit_price: Optional[Decimal] = None
    last_updated: datetime


class PositionDiscrepancy(BaseModel):
    """Discrepancy between exchange and system position"""

    symbol: str
    discrepancy_type: DiscrepancyType
    severity: DiscrepancySeverity

    # Position states
    exchange_position: Optional[ExchangePosition] = None
    system_position: Optional[SystemPosition] = None

    # Differences
    quantity_difference: Optional[Decimal] = None
    price_difference: Optional[Decimal] = None
    pnl_difference: Optional[Decimal] = None

    # Action taken
    auto_corrected: bool = False
    correction_action: Optional[str] = None
    requires_manual_intervention: bool = False

    # Metadata
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    notes: Optional[str] = None


class ReconciliationResult(BaseModel):
    """Result of reconciliation check"""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    symbols_checked: int = 0
    discrepancies_found: int = 0
    auto_corrections: int = 0
    critical_alerts: int = 0

    discrepancies: list[PositionDiscrepancy] = Field(default_factory=list)

    # Performance
    duration_ms: Decimal = Decimal("0")
