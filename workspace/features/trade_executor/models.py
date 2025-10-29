"""
Trade Executor Models

Defines data models for order execution, tracking, and reconciliation.
All monetary values use DECIMAL precision for CHF and USD amounts.

Author: Trade Executor Implementation Team
Date: 2025-10-27
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
import uuid


class OrderType(str, Enum):
    """Order type enumeration"""

    MARKET = "market"
    LIMIT = "limit"
    STOP_MARKET = "stop_market"
    STOP_LIMIT = "stop_limit"


class OrderSide(str, Enum):
    """Order side enumeration"""

    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    """Order status enumeration"""

    PENDING = "pending"  # Created but not yet submitted
    OPEN = "open"  # Submitted to exchange, awaiting fill
    FILLED = "filled"  # Completely filled
    PARTIALLY_FILLED = "partially_filled"  # Partially filled
    CANCELED = "canceled"  # Canceled by user or system
    FAILED = "failed"  # Failed to submit or execute
    EXPIRED = "expired"  # Expired without fill


class TimeInForce(str, Enum):
    """Time in force options"""

    GTC = "GTC"  # Good Till Cancel
    IOC = "IOC"  # Immediate or Cancel
    FOK = "FOK"  # Fill or Kill
    POST_ONLY = "POST_ONLY"  # Post only (maker only)


class StopLossLayer(str, Enum):
    """Stop-loss protection layers"""

    EXCHANGE = "exchange"  # Layer 1: Exchange stop-loss order
    APPLICATION = "application"  # Layer 2: App-level monitoring
    EMERGENCY = "emergency"  # Layer 3: Emergency liquidation


class Order(BaseModel):
    """
    Order model representing a trading order

    Attributes:
        id: Unique order identifier (UUID)
        exchange_order_id: Exchange-assigned order ID
        symbol: Trading pair (e.g., 'BTC/USDT:USDT')
        type: Order type (market, limit, stop_market, etc.)
        side: Buy or sell
        quantity: Order quantity in base currency (DECIMAL)
        price: Limit price if applicable (DECIMAL)
        stop_price: Stop trigger price if applicable (DECIMAL)
        filled_quantity: Amount filled so far (DECIMAL)
        remaining_quantity: Amount remaining to fill (DECIMAL)
        average_fill_price: Average price of fills (DECIMAL)
        status: Current order status
        time_in_force: Time in force option
        reduce_only: Whether order reduces position only
        position_id: Associated position ID
        created_at: Order creation timestamp
        submitted_at: Exchange submission timestamp
        updated_at: Last update timestamp
        filled_at: Full fill timestamp
        fees_paid: Trading fees paid (DECIMAL, in USDT)
        metadata: Additional order metadata
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    exchange_order_id: Optional[str] = None
    symbol: str = Field(..., min_length=1)
    type: OrderType
    side: OrderSide
    quantity: Decimal = Field(..., decimal_places=8, gt=0)
    price: Optional[Decimal] = Field(default=None, decimal_places=8)
    stop_price: Optional[Decimal] = Field(default=None, decimal_places=8)
    filled_quantity: Decimal = Field(default=Decimal("0"), decimal_places=8, ge=0)
    remaining_quantity: Decimal = Field(default=Decimal("0"), decimal_places=8, ge=0)
    average_fill_price: Optional[Decimal] = Field(default=None, decimal_places=8)
    status: OrderStatus = OrderStatus.PENDING
    time_in_force: TimeInForce = TimeInForce.GTC
    reduce_only: bool = False
    position_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    submitted_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    filled_at: Optional[datetime] = None
    fees_paid: Decimal = Field(default=Decimal("0"), decimal_places=8, ge=0)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True
        json_encoders = {Decimal: lambda v: str(v), datetime: lambda v: v.isoformat()}

    @validator("remaining_quantity", always=True)
    def calculate_remaining(cls, v, values):
        """Calculate remaining quantity"""
        if "quantity" in values and "filled_quantity" in values:
            return values["quantity"] - values["filled_quantity"]
        return v

    @property
    def is_fully_filled(self) -> bool:
        """Check if order is fully filled"""
        return self.filled_quantity >= self.quantity

    @property
    def fill_percentage(self) -> Decimal:
        """Calculate fill percentage"""
        if self.quantity == 0:
            return Decimal("0")
        return (self.filled_quantity / self.quantity) * Decimal("100")


class ExecutionResult(BaseModel):
    """
    Result of order execution

    Attributes:
        success: Whether execution was successful
        order: The order object (if successful)
        error_code: Error code if failed
        error_message: Error message if failed
        exchange_response: Raw exchange response
        latency_ms: Execution latency in milliseconds
        timestamp: Result timestamp
    """

    success: bool
    order: Optional[Order] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    exchange_response: Optional[Dict[str, Any]] = None
    latency_ms: Optional[Decimal] = Field(default=None, decimal_places=2)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {Decimal: lambda v: str(v), datetime: lambda v: v.isoformat()}


class StopLossProtection(BaseModel):
    """
    3-layer stop-loss protection tracking

    Attributes:
        position_id: Associated position ID
        layer1_order_id: Exchange stop-loss order ID (Layer 1)
        layer1_status: Layer 1 status
        layer2_active: Whether Layer 2 monitoring is active
        layer3_active: Whether Layer 3 emergency monitoring is active
        stop_price: Stop trigger price
        created_at: Protection setup timestamp
        triggered_at: Protection trigger timestamp
        triggered_layer: Which layer was triggered
        metadata: Additional protection metadata
    """

    position_id: str
    layer1_order_id: Optional[str] = None
    layer1_status: OrderStatus = OrderStatus.PENDING
    layer2_active: bool = False
    layer3_active: bool = False
    stop_price: Decimal = Field(..., decimal_places=8)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    triggered_at: Optional[datetime] = None
    triggered_layer: Optional[StopLossLayer] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True
        json_encoders = {Decimal: lambda v: str(v), datetime: lambda v: v.isoformat()}


class ReconciliationResult(BaseModel):
    """
    Position reconciliation result

    Attributes:
        position_id: Position being reconciled
        system_quantity: Quantity in our system
        exchange_quantity: Quantity on exchange
        discrepancy: Difference (system - exchange)
        needs_correction: Whether correction is needed
        corrections_applied: List of corrections made
        timestamp: Reconciliation timestamp
    """

    position_id: str
    system_quantity: Decimal = Field(..., decimal_places=8)
    exchange_quantity: Decimal = Field(..., decimal_places=8)
    discrepancy: Decimal = Field(..., decimal_places=8)
    needs_correction: bool = False
    corrections_applied: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {Decimal: lambda v: str(v), datetime: lambda v: v.isoformat()}

    @validator("discrepancy", always=True)
    def calculate_discrepancy(cls, v, values):
        """Calculate discrepancy"""
        if "system_quantity" in values and "exchange_quantity" in values:
            return values["system_quantity"] - values["exchange_quantity"]
        return v

    @validator("needs_correction", always=True)
    def check_correction_needed(cls, v, values):
        """Check if correction is needed"""
        if "discrepancy" in values:
            # Need correction if discrepancy > 0.001% of position
            threshold = Decimal("0.00001")
            return abs(values["discrepancy"]) > threshold
        return v


class PositionSnapshot(BaseModel):
    """
    Position snapshot for reconciliation

    Attributes:
        position_id: Position ID
        symbol: Trading pair
        side: Long or short
        quantity: Current quantity
        entry_price: Entry price
        current_price: Current market price
        unrealized_pnl: Unrealized P&L
        timestamp: Snapshot timestamp
    """

    position_id: str
    symbol: str
    side: str
    quantity: Decimal = Field(..., decimal_places=8)
    entry_price: Decimal = Field(..., decimal_places=8)
    current_price: Decimal = Field(..., decimal_places=8)
    unrealized_pnl: Decimal = Field(..., decimal_places=8)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {Decimal: lambda v: str(v), datetime: lambda v: v.isoformat()}


# Export all models
__all__ = [
    "OrderType",
    "OrderSide",
    "OrderStatus",
    "TimeInForce",
    "StopLossLayer",
    "Order",
    "ExecutionResult",
    "StopLossProtection",
    "ReconciliationResult",
    "PositionSnapshot",
]
