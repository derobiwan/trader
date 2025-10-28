"""
Database Models using Pydantic

Type-safe models for all database tables with proper validation,
CHF precision handling, and conversion utilities.

All CHF amounts use Decimal with 8 decimal places for precision.
All cryptocurrency quantities use Decimal with 8 decimal places.

Usage:
    from workspace.shared.database.models import Position, TradingSignal

    # Create position
    position = Position(
        symbol="BTCUSDT",
        side="LONG",
        quantity=Decimal("0.01"),
        entry_price=Decimal("45000.00"),
        leverage=10
    )

    # Validate data
    try:
        position.validate()
    except ValidationError as e:
        print(f"Invalid data: {e}")
"""

from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, ConfigDict


# ============================================================================
# Enums for type safety
# ============================================================================

class PositionSide(str, Enum):
    """Position side (long or short)."""
    LONG = "LONG"
    SHORT = "SHORT"


class PositionStatus(str, Enum):
    """Position status."""
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    LIQUIDATED = "LIQUIDATED"


class SignalType(str, Enum):
    """Trading signal type."""
    ENTRY = "ENTRY"
    EXIT = "EXIT"
    HOLD = "HOLD"
    INCREASE = "INCREASE"
    DECREASE = "DECREASE"


class SignalAction(str, Enum):
    """Trading signal action."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class OrderSide(str, Enum):
    """Order side."""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """Order type."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"


class OrderStatus(str, Enum):
    """Order status."""
    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class RiskEventSeverity(str, Enum):
    """Risk event severity."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ============================================================================
# Base Model Configuration
# ============================================================================

class DatabaseModel(BaseModel):
    """Base model with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=False,
        arbitrary_types_allowed=True,
        json_encoders={
            Decimal: lambda v: str(v),
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }
    )


# ============================================================================
# Position Model
# ============================================================================

class Position(DatabaseModel):
    """
    Trading position model.

    Represents an open or closed position with full P&L tracking.
    """

    id: UUID = Field(default_factory=uuid4)
    symbol: str = Field(..., min_length=1, max_length=20, description="Trading pair (e.g., BTCUSDT)")
    side: PositionSide = Field(..., description="Position side (LONG or SHORT)")
    quantity: Decimal = Field(..., gt=0, description="Position quantity (crypto amount)")
    entry_price: Decimal = Field(..., gt=0, description="Entry price in USD")
    current_price: Optional[Decimal] = Field(None, gt=0, description="Current market price in USD")
    leverage: int = Field(..., ge=5, le=40, description="Position leverage (5-40x)")
    stop_loss: Optional[Decimal] = Field(None, gt=0, description="Stop loss price in USD")
    take_profit: Optional[Decimal] = Field(None, gt=0, description="Take profit price in USD")
    status: PositionStatus = Field(default=PositionStatus.OPEN, description="Position status")
    pnl_chf: Optional[Decimal] = Field(None, description="Realized P&L in CHF")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    closed_at: Optional[datetime] = Field(None, description="Position close timestamp")

    @field_validator("quantity", "entry_price", "current_price", "stop_loss", "take_profit", "pnl_chf")
    @classmethod
    def validate_decimal_precision(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        """Ensure proper decimal precision (8 places)."""
        if v is None:
            return v
        # Quantize to 8 decimal places
        return v.quantize(Decimal("0.00000001"))

    def calculate_unrealized_pnl_usd(self) -> Optional[Decimal]:
        """
        Calculate unrealized P&L in USD.

        Returns:
            Decimal: Unrealized P&L or None if current_price not set
        """
        if self.current_price is None:
            return None

        if self.side == PositionSide.LONG:
            pnl = (self.current_price - self.entry_price) * self.quantity * self.leverage
        else:  # SHORT
            pnl = (self.entry_price - self.current_price) * self.quantity * self.leverage

        return pnl.quantize(Decimal("0.00000001"))

    def to_db_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": self.quantity,
            "entry_price": self.entry_price,
            "current_price": self.current_price,
            "leverage": self.leverage,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "status": self.status.value,
            "pnl_chf": self.pnl_chf,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "closed_at": self.closed_at,
        }


# ============================================================================
# Trading Signal Model
# ============================================================================

class TradingSignal(DatabaseModel):
    """
    LLM-generated trading signal model.

    Captures the LLM's decision, reasoning, and execution status.
    """

    id: UUID = Field(default_factory=uuid4)
    symbol: str = Field(..., min_length=1, max_length=20)
    signal_type: SignalType
    action: SignalAction
    confidence: Decimal = Field(..., ge=0, le=1, description="Confidence score (0.0-1.0)")
    risk_usd: Optional[Decimal] = Field(None, description="Risk amount in USD")
    reasoning: str = Field(..., min_length=1, description="LLM decision reasoning")
    llm_model: str = Field(..., min_length=1, max_length=100)
    llm_tokens: Optional[int] = Field(None, ge=0)
    llm_cost_usd: Optional[Decimal] = Field(None, ge=0)
    executed: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("confidence")
    @classmethod
    def validate_confidence_precision(cls, v: Decimal) -> Decimal:
        """Ensure confidence has 4 decimal places."""
        return v.quantize(Decimal("0.0001"))

    def to_db_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "signal_type": self.signal_type.value,
            "action": self.action.value,
            "confidence": self.confidence,
            "risk_usd": self.risk_usd,
            "reasoning": self.reasoning,
            "llm_model": self.llm_model,
            "llm_tokens": self.llm_tokens,
            "llm_cost_usd": self.llm_cost_usd,
            "executed": self.executed,
            "created_at": self.created_at,
        }


# ============================================================================
# Order Model
# ============================================================================

class Order(DatabaseModel):
    """
    Exchange order model.

    Tracks orders placed on the exchange with execution status.
    """

    id: UUID = Field(default_factory=uuid4)
    position_id: Optional[UUID] = Field(None, description="Associated position ID")
    exchange_order_id: Optional[str] = Field(None, max_length=100, description="Exchange's order ID")
    symbol: str = Field(..., min_length=1, max_length=20)
    side: OrderSide
    order_type: OrderType
    quantity: Decimal = Field(..., gt=0)
    price: Optional[Decimal] = Field(None, gt=0, description="NULL for market orders")
    filled_quantity: Decimal = Field(default=Decimal("0"), ge=0)
    status: OrderStatus = Field(default=OrderStatus.PENDING)
    fee_chf: Optional[Decimal] = Field(None, description="Trading fee in CHF")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("quantity", "price", "filled_quantity", "fee_chf")
    @classmethod
    def validate_decimal_precision(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        """Ensure proper decimal precision (8 places)."""
        if v is None:
            return v
        return v.quantize(Decimal("0.00000001"))

    def to_db_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return {
            "id": self.id,
            "position_id": self.position_id,
            "exchange_order_id": self.exchange_order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "quantity": self.quantity,
            "price": self.price,
            "filled_quantity": self.filled_quantity,
            "status": self.status.value,
            "fee_chf": self.fee_chf,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# ============================================================================
# Market Data Model
# ============================================================================

class MarketData(DatabaseModel):
    """
    Time-series market data model.

    OHLCV data with technical indicators stored in JSONB.
    """

    symbol: str = Field(..., min_length=1, max_length=20)
    timestamp: int = Field(..., description="Microseconds since Unix epoch")
    open: Decimal = Field(..., gt=0)
    high: Decimal = Field(..., gt=0)
    low: Decimal = Field(..., gt=0)
    close: Decimal = Field(..., gt=0)
    volume: Decimal = Field(..., ge=0)
    indicators: Optional[Dict[str, Any]] = Field(None, description="Technical indicators (RSI, MACD, etc.)")

    @field_validator("open", "high", "low", "close", "volume")
    @classmethod
    def validate_decimal_precision(cls, v: Decimal) -> Decimal:
        """Ensure proper decimal precision (8 places)."""
        return v.quantize(Decimal("0.00000001"))

    def to_db_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "indicators": self.indicators,
        }


# ============================================================================
# Daily Performance Model
# ============================================================================

class DailyPerformance(DatabaseModel):
    """
    Daily portfolio performance model.

    Aggregated metrics for performance tracking.
    """

    date: date
    portfolio_value_chf: Decimal = Field(..., description="Total portfolio value in CHF")
    daily_pnl_chf: Decimal = Field(..., description="Daily P&L in CHF")
    daily_pnl_pct: Decimal = Field(..., description="Daily P&L percentage")
    sharpe_ratio: Optional[Decimal] = Field(None, description="Sharpe ratio (target > 0.5)")
    win_rate: Optional[Decimal] = Field(None, ge=0, le=1, description="Win rate (0.0-1.0)")
    total_trades: int = Field(default=0, ge=0)
    positions_snapshot: Optional[Dict[str, Any]] = Field(None, description="EOD positions snapshot")

    @field_validator("portfolio_value_chf", "daily_pnl_chf")
    @classmethod
    def validate_chf_precision(cls, v: Decimal) -> Decimal:
        """Ensure CHF amounts have 8 decimal places."""
        return v.quantize(Decimal("0.00000001"))

    @field_validator("daily_pnl_pct", "sharpe_ratio", "win_rate")
    @classmethod
    def validate_percentage_precision(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        """Ensure percentages have 4 decimal places."""
        if v is None:
            return v
        return v.quantize(Decimal("0.0001"))

    def to_db_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return {
            "date": self.date,
            "portfolio_value_chf": self.portfolio_value_chf,
            "daily_pnl_chf": self.daily_pnl_chf,
            "daily_pnl_pct": self.daily_pnl_pct,
            "sharpe_ratio": self.sharpe_ratio,
            "win_rate": self.win_rate,
            "total_trades": self.total_trades,
            "positions_snapshot": self.positions_snapshot,
        }


# ============================================================================
# Risk Event Model
# ============================================================================

class RiskEvent(DatabaseModel):
    """
    Risk event model.

    Tracks risk-related events with severity classification.
    """

    timestamp: int = Field(..., description="Microseconds since Unix epoch")
    event_type: str = Field(..., min_length=1, max_length=50)
    severity: RiskEventSeverity
    description: str = Field(..., min_length=1)
    position_id: Optional[UUID] = None
    metadata: Optional[Dict[str, Any]] = Field(None, description="Event-specific data")

    def to_db_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return {
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "severity": self.severity.value,
            "description": self.description,
            "position_id": self.position_id,
            "metadata": self.metadata,
        }


# ============================================================================
# LLM Request Model
# ============================================================================

class LLMRequest(DatabaseModel):
    """
    LLM API request audit model.

    Tracks all LLM requests with cost and performance metrics.
    """

    id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    model: str = Field(..., min_length=1, max_length=100)
    prompt_tokens: int = Field(..., gt=0)
    completion_tokens: int = Field(..., ge=0)
    cost_usd: Decimal = Field(..., ge=0)
    latency_ms: int = Field(..., ge=0)
    response: Dict[str, Any] = Field(..., description="Full LLM response")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("cost_usd")
    @classmethod
    def validate_cost_precision(cls, v: Decimal) -> Decimal:
        """Ensure cost has 6 decimal places."""
        return v.quantize(Decimal("0.000001"))

    def to_db_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "cost_usd": self.cost_usd,
            "latency_ms": self.latency_ms,
            "response": self.response,
            "created_at": self.created_at,
        }


# ============================================================================
# Circuit Breaker State Model
# ============================================================================

class CircuitBreakerState(DatabaseModel):
    """
    Circuit breaker daily state model.

    Tracks daily P&L for circuit breaker trigger (-7% daily loss = CHF 183.89).
    """

    date: date
    current_pnl_chf: Decimal = Field(default=Decimal("0"))
    triggered: bool = Field(default=False)
    trigger_reason: Optional[str] = None
    positions_closed: Optional[List[str]] = Field(None, description="Array of position IDs closed")
    reset_at: Optional[datetime] = None

    @field_validator("current_pnl_chf")
    @classmethod
    def validate_chf_precision(cls, v: Decimal) -> Decimal:
        """Ensure CHF amount has 8 decimal places."""
        return v.quantize(Decimal("0.00000001"))

    def should_trigger(self, threshold_chf: Decimal = Decimal("-183.89")) -> bool:
        """
        Check if circuit breaker should trigger.

        Args:
            threshold_chf: Circuit breaker threshold (default: -CHF 183.89)

        Returns:
            bool: True if should trigger
        """
        return self.current_pnl_chf <= threshold_chf and not self.triggered

    def to_db_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return {
            "date": self.date,
            "current_pnl_chf": self.current_pnl_chf,
            "triggered": self.triggered,
            "trigger_reason": self.trigger_reason,
            "positions_closed": self.positions_closed,
            "reset_at": self.reset_at,
        }


# ============================================================================
# Position Reconciliation Model
# ============================================================================

class PositionReconciliation(DatabaseModel):
    """
    Position reconciliation model.

    Tracks discrepancies between system and exchange state.
    """

    id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    position_id: UUID
    system_state: Dict[str, Any] = Field(..., description="System's view of position")
    exchange_state: Dict[str, Any] = Field(..., description="Exchange's view of position")
    discrepancies: Optional[List[Dict[str, Any]]] = Field(None, description="List of discrepancies")
    resolved: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def to_db_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "position_id": self.position_id,
            "system_state": self.system_state,
            "exchange_state": self.exchange_state,
            "discrepancies": self.discrepancies,
            "resolved": self.resolved,
            "created_at": self.created_at,
        }


# ============================================================================
# Utility Functions
# ============================================================================

def usd_to_chf(usd_amount: Decimal, exchange_rate: Decimal = Decimal("0.85")) -> Decimal:
    """
    Convert USD to CHF.

    Args:
        usd_amount: Amount in USD
        exchange_rate: USD/CHF exchange rate (default: 0.85)

    Returns:
        Decimal: Amount in CHF
    """
    chf_amount = usd_amount * exchange_rate
    return chf_amount.quantize(Decimal("0.00000001"))


def chf_to_usd(chf_amount: Decimal, exchange_rate: Decimal = Decimal("0.85")) -> Decimal:
    """
    Convert CHF to USD.

    Args:
        chf_amount: Amount in CHF
        exchange_rate: USD/CHF exchange rate (default: 0.85)

    Returns:
        Decimal: Amount in USD
    """
    usd_amount = chf_amount / exchange_rate
    return usd_amount.quantize(Decimal("0.00000001"))


def microseconds_to_datetime(microseconds: int) -> datetime:
    """
    Convert microseconds since epoch to datetime.

    Args:
        microseconds: Microseconds since Unix epoch

    Returns:
        datetime: Datetime object
    """
    return datetime.utcfromtimestamp(microseconds / 1_000_000)


def datetime_to_microseconds(dt: datetime) -> int:
    """
    Convert datetime to microseconds since epoch.

    Args:
        dt: Datetime object

    Returns:
        int: Microseconds since Unix epoch
    """
    return int(dt.timestamp() * 1_000_000)
