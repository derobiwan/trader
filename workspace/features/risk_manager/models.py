"""
Risk Management Models

Data models for risk validation, protection layers, and circuit breaker.

Author: Risk Management Team
Date: 2025-10-28
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional


class ValidationStatus(str, Enum):
    """Risk validation status"""

    APPROVED = "approved"
    REJECTED = "rejected"
    WARNING = "warning"


class CircuitBreakerState(str, Enum):
    """Circuit breaker operational states"""

    ACTIVE = "active"
    TRIPPED = "tripped"
    MANUAL_RESET_REQUIRED = "manual_reset_required"
    RECOVERING = "recovering"


class ProtectionLayer(str, Enum):
    """Stop-loss protection layers"""

    EXCHANGE_STOP = "exchange_stop"
    APP_MONITOR = "app_monitor"
    EMERGENCY = "emergency"


@dataclass
class RiskCheckResult:
    """Individual risk check result"""

    check_name: str
    passed: bool
    message: str
    severity: str = "info"  # info, warning, error
    current_value: Optional[Decimal] = None
    limit_value: Optional[Decimal] = None

    def __str__(self) -> str:
        status = "✓" if self.passed else "✗"
        msg = f"{status} {self.check_name}: {self.message}"
        if self.current_value is not None and self.limit_value is not None:
            msg += f" (current: {self.current_value}, limit: {self.limit_value})"
        return msg


@dataclass
class RiskValidation:
    """
    Risk validation result for a trading signal

    Contains all pre-trade checks and validation results.
    """

    status: ValidationStatus
    approved: bool
    checks: List[RiskCheckResult]
    total_exposure_pct: Decimal
    position_count: int
    daily_pnl_chf: Decimal
    circuit_breaker_active: bool
    rejection_reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_rejection(self, reason: str):
        """Add rejection reason"""
        self.rejection_reasons.append(reason)
        self.approved = False
        self.status = ValidationStatus.REJECTED

    def add_warning(self, warning: str):
        """Add warning"""
        self.warnings.append(warning)
        if self.status != ValidationStatus.REJECTED:
            self.status = ValidationStatus.WARNING

    def summary(self) -> str:
        """Generate validation summary"""
        lines = [
            f"Risk Validation: {self.status.value.upper()}",
            f"Approved: {self.approved}",
            f"Position Count: {self.position_count}",
            f"Total Exposure: {self.total_exposure_pct:.1%}",
            f"Daily P&L: CHF {self.daily_pnl_chf:,.2f}",
            f"Circuit Breaker: {'ACTIVE' if self.circuit_breaker_active else 'OK'}",
        ]

        if self.rejection_reasons:
            lines.append("\nRejection Reasons:")
            for reason in self.rejection_reasons:
                lines.append(f"  - {reason}")

        if self.warnings:
            lines.append("\nWarnings:")
            for warning in self.warnings:
                lines.append(f"  - {warning}")

        if self.checks:
            lines.append("\nDetailed Checks:")
            for check in self.checks:
                lines.append(f"  {check}")

        return "\n".join(lines)


@dataclass
class Protection:
    """
    Multi-layer stop-loss protection status

    Tracks all three protection layers for a position.
    """

    position_id: str
    symbol: str
    entry_price: Decimal
    stop_loss_price: Decimal
    stop_loss_pct: Decimal

    # Layer 1: Exchange stop-loss order
    exchange_stop_order_id: Optional[str] = None
    exchange_stop_active: bool = False

    # Layer 2: Application-level monitoring
    app_monitor_active: bool = False
    app_monitor_task_id: Optional[str] = None

    # Layer 3: Emergency liquidation
    emergency_monitor_active: bool = False
    emergency_monitor_task_id: Optional[str] = None
    emergency_threshold_pct: Decimal = Decimal("0.15")  # 15%

    # Status
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_check_at: Optional[datetime] = None
    triggered_layer: Optional[ProtectionLayer] = None
    triggered_at: Optional[datetime] = None

    def is_active(self) -> bool:
        """Check if any protection layer is active"""
        return (
            self.exchange_stop_active
            or self.app_monitor_active
            or self.emergency_monitor_active
        )

    def layer_count(self) -> int:
        """Count active protection layers"""
        return sum(
            [
                self.exchange_stop_active,
                self.app_monitor_active,
                self.emergency_monitor_active,
            ]
        )

    def status_summary(self) -> str:
        """Generate protection status summary"""
        layers = []
        if self.exchange_stop_active:
            layers.append(f"Exchange Stop (order: {self.exchange_stop_order_id})")
        if self.app_monitor_active:
            layers.append("App Monitor")
        if self.emergency_monitor_active:
            layers.append(f"Emergency (threshold: {self.emergency_threshold_pct:.1%})")

        if not layers:
            return "No active protection layers"

        return f"Active layers ({len(layers)}): {', '.join(layers)}"


@dataclass
class CircuitBreakerStatus:
    """
    Circuit breaker status and metrics

    Tracks daily P&L and circuit breaker state.
    """

    state: CircuitBreakerState
    daily_pnl_chf: Decimal
    daily_loss_limit_chf: Decimal = Decimal("-183.89")  # -7% of CHF 2,626.96
    daily_loss_limit_pct: Decimal = Decimal("-0.07")  # -7%

    # Metrics
    starting_balance_chf: Decimal = Decimal("2626.96")
    current_balance_chf: Decimal = Decimal("0")
    daily_trade_count: int = 0
    daily_winning_trades: int = 0
    daily_losing_trades: int = 0

    # Timestamps
    last_reset_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tripped_at: Optional[datetime] = None
    recovery_started_at: Optional[datetime] = None

    # Manual reset requirement
    manual_reset_required: bool = False
    manual_reset_token: Optional[str] = None

    def is_tripped(self) -> bool:
        """Check if circuit breaker is tripped"""
        return self.state == CircuitBreakerState.TRIPPED

    def is_manual_reset_required(self) -> bool:
        """Check if manual reset is required"""
        return self.state == CircuitBreakerState.MANUAL_RESET_REQUIRED

    def should_trip(self) -> bool:
        """Check if circuit breaker should trip"""
        return (
            self.daily_pnl_chf < self.daily_loss_limit_chf
            and self.state == CircuitBreakerState.ACTIVE
        )

    def loss_percentage(self) -> Decimal:
        """Calculate current daily loss percentage"""
        if self.starting_balance_chf == 0:
            return Decimal("0")
        return (self.daily_pnl_chf / self.starting_balance_chf) * Decimal("100")

    def remaining_loss_allowance_chf(self) -> Decimal:
        """Calculate remaining loss allowance before circuit breaker trips"""
        return self.daily_loss_limit_chf - self.daily_pnl_chf

    def remaining_loss_allowance_pct(self) -> Decimal:
        """Calculate remaining loss allowance as percentage"""
        remaining_chf = self.remaining_loss_allowance_chf()
        if self.starting_balance_chf == 0:
            return Decimal("0")
        return (remaining_chf / self.starting_balance_chf) * Decimal("100")

    def status_summary(self) -> str:
        """Generate circuit breaker status summary"""
        lines = [
            f"Circuit Breaker: {self.state.value.upper()}",
            f"Daily P&L: CHF {self.daily_pnl_chf:,.2f} ({self.loss_percentage():.2f}%)",
            f"Daily Limit: CHF {self.daily_loss_limit_chf:,.2f} ({self.daily_loss_limit_pct:.1%})",
            f"Remaining Allowance: CHF {self.remaining_loss_allowance_chf():,.2f} ({self.remaining_loss_allowance_pct():.2f}%)",
            f"Trades Today: {self.daily_trade_count} (W: {self.daily_winning_trades}, L: {self.daily_losing_trades})",
        ]

        if self.is_tripped():
            lines.append(f"⚠️ TRIPPED at {self.tripped_at.strftime('%H:%M:%S UTC')}")

        if self.is_manual_reset_required():
            lines.append(f"🔒 MANUAL RESET REQUIRED (token: {self.manual_reset_token})")

        return "\n".join(lines)


# Export all models
__all__ = [
    "ValidationStatus",
    "CircuitBreakerState",
    "ProtectionLayer",
    "RiskCheckResult",
    "RiskValidation",
    "Protection",
    "CircuitBreakerStatus",
]
