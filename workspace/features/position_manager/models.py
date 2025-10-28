"""
Position Manager Extended Models

Extended Pydantic models for position management operations including
creation requests, update requests, P&L calculations, and validation rules.

All models use Decimal for financial precision with 8 decimal places.
CHF amounts follow Swiss Franc precision requirements.

Usage:
    from workspace.features.position_manager.models import (
        PositionCreateRequest,
        PositionUpdateRequest,
        PositionCloseRequest,
        PositionWithPnL
    )

    # Create position request
    request = PositionCreateRequest(
        symbol="BTCUSDT",
        side="LONG",
        quantity=Decimal("0.01"),
        entry_price=Decimal("45000.00"),
        leverage=10,
        stop_loss=Decimal("44000.00")
    )

    # Validate against risk limits
    request.validate_risk_limits(
        max_position_size_chf=Decimal("525.39"),
        current_exposure_chf=Decimal("1000.00"),
        max_total_exposure_chf=Decimal("2101.57")
    )
"""

from datetime import datetime
from datetime import date as Date
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, ConfigDict

# Import base models from shared database models
from workspace.shared.database.models import (
    Position,
    PositionSide,
    PositionStatus,
    DatabaseModel,
    usd_to_chf,
    chf_to_usd
)


# ============================================================================
# Configuration Constants
# ============================================================================

# Trading System Configuration
CAPITAL_CHF = Decimal("2626.96")
CIRCUIT_BREAKER_LOSS_CHF = Decimal("-183.89")  # -7% daily loss limit
MAX_POSITION_SIZE_PCT = Decimal("0.20")  # 20% of capital
MAX_TOTAL_EXPOSURE_PCT = Decimal("0.80")  # 80% of capital
MIN_LEVERAGE = 5
MAX_LEVERAGE = 40
VALID_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT", "DOGEUSDT"]

# Calculated limits
MAX_POSITION_SIZE_CHF = CAPITAL_CHF * MAX_POSITION_SIZE_PCT  # CHF 525.39
MAX_TOTAL_EXPOSURE_CHF = CAPITAL_CHF * MAX_TOTAL_EXPOSURE_PCT  # CHF 2101.57

# USD/CHF exchange rate (approximate)
USD_CHF_RATE = Decimal("0.85")


# ============================================================================
# Custom Exceptions
# ============================================================================

class ValidationError(Exception):
    """Raised when position validation fails."""
    pass


class RiskLimitError(Exception):
    """Raised when position exceeds risk limits."""
    pass


class PositionNotFoundError(Exception):
    """Raised when position not found in database."""
    pass


class InsufficientCapitalError(Exception):
    """Raised when insufficient capital for operation."""
    pass


# ============================================================================
# Position Close Reason Enum
# ============================================================================

class CloseReason(str, Enum):
    """Reason for closing a position."""
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    MANUAL = "manual"
    CIRCUIT_BREAKER = "circuit_breaker"
    LIQUIDATION = "liquidation"
    SYSTEM_ERROR = "system_error"


# ============================================================================
# Position Creation Request
# ============================================================================

class PositionCreateRequest(DatabaseModel):
    """
    Request to create a new trading position.

    Includes validation for all risk limits and trading parameters.
    """

    symbol: str = Field(..., min_length=1, max_length=20, description="Trading pair (e.g., BTCUSDT)")
    side: PositionSide = Field(..., description="Position side (LONG or SHORT)")
    quantity: Decimal = Field(..., gt=0, description="Position quantity (crypto amount)")
    entry_price: Decimal = Field(..., gt=0, description="Entry price in USD")
    leverage: int = Field(..., ge=MIN_LEVERAGE, le=MAX_LEVERAGE, description="Position leverage (5-40x)")
    stop_loss: Decimal = Field(..., gt=0, description="Stop loss price in USD (REQUIRED)")
    take_profit: Optional[Decimal] = Field(None, gt=0, description="Take profit price in USD")
    signal_id: Optional[UUID] = Field(None, description="Associated trading signal ID")
    notes: Optional[str] = Field(None, max_length=500, description="Position notes")

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """Validate symbol is in allowed list."""
        if v not in VALID_SYMBOLS:
            raise ValueError(f"Invalid symbol: {v}. Must be one of {VALID_SYMBOLS}")
        return v

    @field_validator("quantity", "entry_price", "stop_loss", "take_profit")
    @classmethod
    def validate_decimal_precision(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        """Ensure proper decimal precision (8 places)."""
        if v is None:
            return v
        return v.quantize(Decimal("0.00000001"))

    @field_validator("stop_loss")
    @classmethod
    def validate_stop_loss_required(cls, v: Optional[Decimal]) -> Decimal:
        """Ensure stop loss is always set."""
        if v is None:
            raise ValueError("Stop loss is REQUIRED for all positions")
        return v

    def validate_stop_loss_price(self) -> None:
        """
        Validate stop loss is on correct side of entry price.

        Raises:
            ValidationError: If stop loss is invalid
        """
        if self.side == PositionSide.LONG:
            if self.stop_loss >= self.entry_price:
                raise ValidationError(
                    f"LONG position stop loss ({self.stop_loss}) must be below entry price ({self.entry_price})"
                )
        else:  # SHORT
            if self.stop_loss <= self.entry_price:
                raise ValidationError(
                    f"SHORT position stop loss ({self.stop_loss}) must be above entry price ({self.entry_price})"
                )

    def validate_take_profit_price(self) -> None:
        """
        Validate take profit is on correct side of entry price.

        Raises:
            ValidationError: If take profit is invalid
        """
        if self.take_profit is None:
            return

        if self.side == PositionSide.LONG:
            if self.take_profit <= self.entry_price:
                raise ValidationError(
                    f"LONG position take profit ({self.take_profit}) must be above entry price ({self.entry_price})"
                )
        else:  # SHORT
            if self.take_profit >= self.entry_price:
                raise ValidationError(
                    f"SHORT position take profit ({self.take_profit}) must be below entry price ({self.entry_price})"
                )

    def calculate_position_value_chf(self) -> Decimal:
        """
        Calculate position value in CHF.

        Returns:
            Decimal: Position value in CHF
        """
        position_value_usd = self.quantity * self.entry_price * self.leverage
        position_value_chf = usd_to_chf(position_value_usd, USD_CHF_RATE)
        return position_value_chf.quantize(Decimal("0.00000001"))

    def validate_risk_limits(
        self,
        current_exposure_chf: Decimal = Decimal("0"),
        max_position_size_chf: Decimal = MAX_POSITION_SIZE_CHF,
        max_total_exposure_chf: Decimal = MAX_TOTAL_EXPOSURE_CHF
    ) -> None:
        """
        Validate position against risk limits.

        Args:
            current_exposure_chf: Current total exposure in CHF
            max_position_size_chf: Maximum single position size
            max_total_exposure_chf: Maximum total exposure

        Raises:
            RiskLimitError: If position exceeds limits
        """
        position_value_chf = self.calculate_position_value_chf()

        # Check single position size limit (20% of capital)
        if position_value_chf > max_position_size_chf:
            raise RiskLimitError(
                f"Position size CHF {position_value_chf:.2f} exceeds maximum CHF {max_position_size_chf:.2f} "
                f"(20% of capital)"
            )

        # Check total exposure limit (80% of capital)
        new_total_exposure = current_exposure_chf + position_value_chf
        if new_total_exposure > max_total_exposure_chf:
            raise RiskLimitError(
                f"Total exposure CHF {new_total_exposure:.2f} would exceed maximum CHF {max_total_exposure_chf:.2f} "
                f"(80% of capital). Current exposure: CHF {current_exposure_chf:.2f}"
            )

    def validate_all(self, current_exposure_chf: Decimal = Decimal("0")) -> None:
        """
        Run all validation checks.

        Args:
            current_exposure_chf: Current total exposure in CHF

        Raises:
            ValidationError: If validation fails
            RiskLimitError: If risk limits exceeded
        """
        self.validate_stop_loss_price()
        self.validate_take_profit_price()
        self.validate_risk_limits(current_exposure_chf)


# ============================================================================
# Position Update Request
# ============================================================================

class PositionUpdateRequest(DatabaseModel):
    """
    Request to update an existing position's price.

    Used for real-time price updates and P&L tracking.
    """

    position_id: UUID = Field(..., description="Position ID to update")
    current_price: Decimal = Field(..., gt=0, description="Current market price in USD")
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow, description="Update timestamp")

    @field_validator("current_price")
    @classmethod
    def validate_decimal_precision(cls, v: Decimal) -> Decimal:
        """Ensure proper decimal precision (8 places)."""
        return v.quantize(Decimal("0.00000001"))


# ============================================================================
# Position Close Request
# ============================================================================

class PositionCloseRequest(DatabaseModel):
    """
    Request to close an existing position.

    Captures close price, reason, and calculates final P&L.
    """

    position_id: UUID = Field(..., description="Position ID to close")
    close_price: Decimal = Field(..., gt=0, description="Close price in USD")
    reason: CloseReason = Field(..., description="Reason for closing")
    notes: Optional[str] = Field(None, max_length=500, description="Additional notes")
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow, description="Close timestamp")

    @field_validator("close_price")
    @classmethod
    def validate_decimal_precision(cls, v: Decimal) -> Decimal:
        """Ensure proper decimal precision (8 places)."""
        return v.quantize(Decimal("0.00000001"))


# ============================================================================
# Position with P&L Calculations
# ============================================================================

class PositionWithPnL(DatabaseModel):
    """
    Position model with calculated P&L metrics.

    Extends base Position with real-time P&L calculations.
    """

    # Core position data
    id: UUID
    symbol: str
    side: PositionSide
    quantity: Decimal
    entry_price: Decimal
    current_price: Optional[Decimal]
    leverage: int
    stop_loss: Optional[Decimal]
    take_profit: Optional[Decimal]
    status: PositionStatus
    pnl_chf: Optional[Decimal]
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime]

    # Calculated P&L metrics
    unrealized_pnl_usd: Optional[Decimal] = Field(None, description="Unrealized P&L in USD")
    unrealized_pnl_chf: Optional[Decimal] = Field(None, description="Unrealized P&L in CHF")
    unrealized_pnl_pct: Optional[Decimal] = Field(None, description="Unrealized P&L percentage")
    position_value_chf: Optional[Decimal] = Field(None, description="Current position value in CHF")
    is_stop_loss_triggered: bool = Field(False, description="Whether stop loss is triggered")
    is_take_profit_triggered: bool = Field(False, description="Whether take profit is triggered")

    @classmethod
    def from_position(cls, position: Position) -> "PositionWithPnL":
        """
        Create PositionWithPnL from base Position model.

        Args:
            position: Base Position model

        Returns:
            PositionWithPnL with calculated metrics
        """
        # Calculate P&L if current price is set
        unrealized_pnl_usd = None
        unrealized_pnl_chf = None
        unrealized_pnl_pct = None
        position_value_chf = None

        if position.current_price:
            # Calculate unrealized P&L in USD
            if position.side == PositionSide.LONG:
                unrealized_pnl_usd = (position.current_price - position.entry_price) * position.quantity * position.leverage
            else:  # SHORT
                unrealized_pnl_usd = (position.entry_price - position.current_price) * position.quantity * position.leverage

            # Convert to CHF
            unrealized_pnl_chf = usd_to_chf(unrealized_pnl_usd, USD_CHF_RATE)

            # Calculate percentage
            price_change = position.current_price - position.entry_price
            if position.side == PositionSide.SHORT:
                price_change = -price_change
            unrealized_pnl_pct = (price_change / position.entry_price) * position.leverage * Decimal("100")

            # Calculate position value in CHF
            position_value_usd = position.quantity * position.current_price * position.leverage
            position_value_chf = usd_to_chf(position_value_usd, USD_CHF_RATE)

        # Check stop loss and take profit triggers
        is_stop_loss_triggered = False
        is_take_profit_triggered = False

        if position.current_price and position.stop_loss:
            if position.side == PositionSide.LONG:
                is_stop_loss_triggered = position.current_price <= position.stop_loss
            else:  # SHORT
                is_stop_loss_triggered = position.current_price >= position.stop_loss

        if position.current_price and position.take_profit:
            if position.side == PositionSide.LONG:
                is_take_profit_triggered = position.current_price >= position.take_profit
            else:  # SHORT
                is_take_profit_triggered = position.current_price <= position.take_profit

        return cls(
            id=position.id,
            symbol=position.symbol,
            side=position.side,
            quantity=position.quantity,
            entry_price=position.entry_price,
            current_price=position.current_price,
            leverage=position.leverage,
            stop_loss=position.stop_loss,
            take_profit=position.take_profit,
            status=position.status,
            pnl_chf=position.pnl_chf,
            created_at=position.created_at,
            updated_at=position.updated_at,
            closed_at=position.closed_at,
            unrealized_pnl_usd=unrealized_pnl_usd,
            unrealized_pnl_chf=unrealized_pnl_chf,
            unrealized_pnl_pct=unrealized_pnl_pct,
            position_value_chf=position_value_chf,
            is_stop_loss_triggered=is_stop_loss_triggered,
            is_take_profit_triggered=is_take_profit_triggered
        )


# ============================================================================
# Daily P&L Summary
# ============================================================================

class DailyPnLSummary(DatabaseModel):
    """
    Daily P&L summary for circuit breaker tracking.

    Aggregates all position P&L for a specific date.
    """

    date: Date = Field(..., description="Trading date")
    total_pnl_chf: Decimal = Field(..., description="Total P&L in CHF")
    realized_pnl_chf: Decimal = Field(default=Decimal("0"), description="Realized P&L from closed positions")
    unrealized_pnl_chf: Decimal = Field(default=Decimal("0"), description="Unrealized P&L from open positions")
    open_positions_count: int = Field(default=0, ge=0, description="Number of open positions")
    closed_positions_count: int = Field(default=0, ge=0, description="Number of closed positions")
    total_exposure_chf: Decimal = Field(default=Decimal("0"), description="Total exposure in CHF")
    is_circuit_breaker_triggered: bool = Field(False, description="Whether circuit breaker triggered")
    circuit_breaker_threshold_chf: Decimal = Field(
        default=CIRCUIT_BREAKER_LOSS_CHF,
        description="Circuit breaker threshold"
    )

    @field_validator("total_pnl_chf", "realized_pnl_chf", "unrealized_pnl_chf", "total_exposure_chf")
    @classmethod
    def validate_chf_precision(cls, v: Decimal) -> Decimal:
        """Ensure CHF amounts have 8 decimal places."""
        return v.quantize(Decimal("0.00000001"))

    def check_circuit_breaker(self) -> bool:
        """
        Check if circuit breaker should trigger.

        Returns:
            bool: True if circuit breaker should trigger
        """
        return self.total_pnl_chf <= self.circuit_breaker_threshold_chf


# ============================================================================
# Position Statistics
# ============================================================================

class PositionStatistics(DatabaseModel):
    """
    Aggregated position statistics.

    Used for reporting and monitoring.
    """

    total_positions: int = Field(default=0, ge=0)
    open_positions: int = Field(default=0, ge=0)
    closed_positions: int = Field(default=0, ge=0)
    total_exposure_chf: Decimal = Field(default=Decimal("0"))
    total_unrealized_pnl_chf: Decimal = Field(default=Decimal("0"))
    total_realized_pnl_chf: Decimal = Field(default=Decimal("0"))
    positions_at_stop_loss: int = Field(default=0, ge=0, description="Positions that hit stop loss")
    positions_at_take_profit: int = Field(default=0, ge=0, description="Positions that hit take profit")

    @field_validator("total_exposure_chf", "total_unrealized_pnl_chf", "total_realized_pnl_chf")
    @classmethod
    def validate_chf_precision(cls, v: Decimal) -> Decimal:
        """Ensure CHF amounts have 8 decimal places."""
        return v.quantize(Decimal("0.00000001"))
