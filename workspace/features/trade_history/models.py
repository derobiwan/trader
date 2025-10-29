"""
Trade History Models

Models for tracking and storing complete trade history.

Author: Trading System Implementation Team
Date: 2025-10-28
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class TradeType(str, Enum):
    """Type of trade action"""

    ENTRY_LONG = "entry_long"  # Opening long position
    ENTRY_SHORT = "entry_short"  # Opening short position
    EXIT_LONG = "exit_long"  # Closing long position
    EXIT_SHORT = "exit_short"  # Closing short position
    STOP_LOSS = "stop_loss"  # Stop-loss triggered
    TAKE_PROFIT = "take_profit"  # Take-profit triggered
    LIQUIDATION = "liquidation"  # Force liquidation


class TradeStatus(str, Enum):
    """Status of trade execution"""

    PENDING = "pending"  # Order submitted, not filled
    PARTIAL = "partial"  # Partially filled
    FILLED = "filled"  # Completely filled
    CANCELLED = "cancelled"  # Order cancelled
    FAILED = "failed"  # Execution failed
    REJECTED = "rejected"  # Order rejected by exchange


class TradeHistoryEntry(BaseModel):
    """
    Complete trade history entry

    Captures all details of a trade execution for audit trail,
    performance analysis, and regulatory compliance.

    Attributes:
        id: Unique trade ID (UUID)
        trade_type: Type of trade action
        status: Execution status
        symbol: Trading pair
        exchange: Exchange name
        order_id: Exchange order ID
        position_id: Associated position ID
        side: Buy or sell
        quantity: Trade quantity in base currency
        entry_price: Average entry price
        exit_price: Average exit price (for exits)
        fees: Total fees paid
        realized_pnl: Realized profit/loss (for exits)
        unrealized_pnl: Unrealized P&L at time of entry
        timestamp: Trade execution timestamp
        signal_confidence: Confidence of signal that triggered trade
        signal_reasoning: LLM reasoning for the trade
        execution_latency_ms: Time from signal to execution
        metadata: Additional metadata
    """

    # Identifiers
    id: str = Field(description="Unique trade ID (UUID)")
    trade_type: TradeType
    status: TradeStatus
    symbol: str = Field(description="Trading pair (e.g., 'BTC/USDT:USDT')")
    exchange: str = Field(default="bybit", description="Exchange name")

    # Order details
    order_id: str = Field(description="Exchange order ID")
    position_id: Optional[str] = Field(
        default=None, description="Associated position ID"
    )
    side: str = Field(description="Order side: 'buy' or 'sell'")

    # Quantity and pricing
    quantity: Decimal = Field(description="Trade quantity in base currency")
    entry_price: Decimal = Field(description="Average entry price")
    exit_price: Optional[Decimal] = Field(
        default=None, description="Average exit price"
    )

    # Financial metrics
    fees: Decimal = Field(default=Decimal("0"), description="Total fees paid")
    realized_pnl: Optional[Decimal] = Field(
        default=None, description="Realized P&L in quote currency (for exits)"
    )
    unrealized_pnl: Optional[Decimal] = Field(
        default=None, description="Unrealized P&L at time of entry"
    )

    # Timestamps
    timestamp: datetime = Field(description="Trade execution timestamp")
    signal_timestamp: Optional[datetime] = Field(
        default=None, description="When signal was generated"
    )

    # Signal metadata
    signal_confidence: Optional[Decimal] = Field(
        default=None, description="Confidence level of signal (0.0-1.0)"
    )
    signal_reasoning: Optional[str] = Field(
        default=None, description="LLM reasoning for the trade"
    )

    # Performance metrics
    execution_latency_ms: Optional[Decimal] = Field(
        default=None, description="Latency from signal to execution"
    )
    slippage_pct: Optional[Decimal] = Field(
        default=None, description="Price slippage percentage"
    )

    # Risk metrics
    position_size_pct: Optional[Decimal] = Field(
        default=None, description="Position size as % of capital"
    )
    leverage: Optional[Decimal] = Field(default=None, description="Leverage used")
    stop_loss_price: Optional[Decimal] = Field(
        default=None, description="Stop-loss price set"
    )
    take_profit_price: Optional[Decimal] = Field(
        default=None, description="Take-profit price set"
    )

    # Additional context
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat(),
        }


class TradeStatistics(BaseModel):
    """
    Aggregated trade statistics

    Used for performance reporting and analysis.
    """

    # Volume metrics
    total_trades: int = Field(description="Total number of trades")
    total_volume: Decimal = Field(description="Total trading volume")

    # Win/loss metrics
    winning_trades: int = Field(default=0)
    losing_trades: int = Field(default=0)
    win_rate: Decimal = Field(description="Win rate percentage")

    # P&L metrics
    total_pnl: Decimal = Field(description="Total realized P&L")
    average_win: Decimal = Field(default=Decimal("0"))
    average_loss: Decimal = Field(default=Decimal("0"))
    largest_win: Decimal = Field(default=Decimal("0"))
    largest_loss: Decimal = Field(default=Decimal("0"))

    # Risk metrics
    profit_factor: Decimal = Field(
        default=Decimal("0"), description="Gross profit / Gross loss"
    )
    sharpe_ratio: Optional[Decimal] = Field(default=None)
    max_drawdown: Optional[Decimal] = Field(default=None)

    # Fee metrics
    total_fees: Decimal = Field(default=Decimal("0"))

    # Time metrics
    average_trade_duration_minutes: Optional[Decimal] = Field(default=None)

    # Period
    period_start: datetime
    period_end: datetime

    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat(),
        }


class DailyTradeReport(BaseModel):
    """
    Daily trade report summary

    Generated at end of each trading day.
    """

    date: datetime = Field(description="Report date")
    statistics: TradeStatistics

    # Daily specifics
    trades_by_hour: Dict[int, int] = Field(
        default_factory=dict, description="Trade count by hour (0-23)"
    )
    trades_by_symbol: Dict[str, int] = Field(
        default_factory=dict, description="Trade count by symbol"
    )

    # Performance
    daily_pnl: Decimal = Field(description="Total daily P&L")
    daily_return_pct: Decimal = Field(description="Daily return percentage")

    # Risk
    max_position_size: Decimal = Field(description="Largest position size")
    circuit_breaker_triggered: bool = Field(
        default=False, description="Was circuit breaker triggered"
    )

    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat(),
        }


# Export all models
__all__ = [
    "TradeType",
    "TradeStatus",
    "TradeHistoryEntry",
    "TradeStatistics",
    "DailyTradeReport",
]
