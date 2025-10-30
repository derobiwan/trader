"""
Portfolio Risk Management

Implements portfolio-level risk controls including:
- Single position size limits (10% of portfolio max)
- Total exposure limits (80% of portfolio max)
- Daily loss circuit breaker (-7% threshold)
- Position concentration monitoring

Author: Trading System Implementation Team
Date: 2025-10-29
Sprint: 3, Stream B, Task 043
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class PortfolioLimits:
    """Portfolio risk limit configuration"""

    max_portfolio_value: Decimal
    max_single_position_pct: float = 0.10  # 10% max per position
    max_total_exposure_pct: float = 0.80  # 80% max total exposure
    daily_loss_limit_pct: float = 0.07  # -7% circuit breaker
    max_leverage: int = 10  # Maximum leverage allowed


@dataclass
class PositionInfo:
    """Information about a single position"""

    symbol: str
    side: str  # "LONG" or "SHORT"
    quantity: Decimal
    entry_price: Decimal
    current_price: Decimal
    unrealized_pnl: Decimal
    leverage: int
    position_value_chf: Decimal  # Position size in CHF
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class PortfolioStatus:
    """Current portfolio status snapshot"""

    total_portfolio_value: Decimal
    open_positions: int
    total_exposure_chf: Decimal
    exposure_pct: float
    largest_position_chf: Decimal
    largest_position_pct: float
    total_unrealized_pnl: Decimal
    daily_pnl: Decimal
    timestamp: datetime


class PortfolioRiskManager:
    """
    Portfolio-level risk management and controls.

    Enforces:
    - Maximum single position size (10% of portfolio)
    - Maximum total exposure (80% of portfolio)
    - Daily loss limit (-7% circuit breaker)
    - Position concentration limits
    - Leverage limits
    """

    def __init__(self, limits: PortfolioLimits):
        """
        Initialize portfolio risk manager.

        Args:
            limits: Portfolio risk limit configuration
        """
        self.limits = limits
        self.positions: Dict[str, PositionInfo] = {}
        self.daily_pnl_history: Dict[date, Decimal] = {}
        self.circuit_breaker_active = False

        logger.info(
            f"PortfolioRiskManager initialized with limits: "
            f"max_single={limits.max_single_position_pct:.1%}, "
            f"max_exposure={limits.max_total_exposure_pct:.1%}, "
            f"daily_loss_limit={limits.daily_loss_limit_pct:.1%}"
        )

    # ========================================================================
    # Position Limit Checks
    # ========================================================================

    def check_position_limits(self, new_position_value: Decimal) -> Tuple[bool, str]:
        """
        Check if a new position would exceed portfolio limits.

        Args:
            new_position_value: Size of new position in CHF

        Returns:
            Tuple of (can_open: bool, reason: str)
        """
        # Check single position limit (10% of portfolio)
        max_single_position = self.limits.max_portfolio_value * Decimal(
            str(self.limits.max_single_position_pct)
        )

        if new_position_value > max_single_position:
            reason = (
                f"Position size ({new_position_value:.2f} CHF) exceeds "
                f"single position limit ({max_single_position:.2f} CHF, "
                f"{self.limits.max_single_position_pct:.1%} of portfolio)"
            )
            logger.warning(reason)
            return False, reason

        # Check total exposure limit (80% of portfolio)
        current_exposure = self.calculate_total_exposure()
        new_total_exposure = current_exposure + new_position_value

        max_total_exposure = self.limits.max_portfolio_value * Decimal(
            str(self.limits.max_total_exposure_pct)
        )

        if new_total_exposure > max_total_exposure:
            reason = (
                f"New total exposure ({new_total_exposure:.2f} CHF) would exceed "
                f"limit ({max_total_exposure:.2f} CHF, "
                f"{self.limits.max_total_exposure_pct:.1%} of portfolio)"
            )
            logger.warning(reason)
            return False, reason

        return True, "Position limits OK"

    def check_leverage_limit(self, leverage: int) -> Tuple[bool, str]:
        """
        Check if leverage exceeds maximum allowed.

        Args:
            leverage: Requested leverage

        Returns:
            Tuple of (within_limit: bool, reason: str)
        """
        if leverage > self.limits.max_leverage:
            reason = (
                f"Leverage {leverage}x exceeds maximum allowed "
                f"({self.limits.max_leverage}x)"
            )
            logger.warning(reason)
            return False, reason

        return True, "Leverage OK"

    # ========================================================================
    # Daily Loss Limit and Circuit Breaker
    # ========================================================================

    def check_daily_loss_limit(self, current_pnl: Decimal) -> Tuple[bool, str]:
        """
        Check if daily P&L exceeds loss limit.
        Triggers circuit breaker if limit exceeded.

        Args:
            current_pnl: Current day's P&L in CHF (negative for loss)

        Returns:
            Tuple of (within_limit: bool, message: str)
        """
        daily_loss_limit = self.limits.max_portfolio_value * Decimal(
            str(self.limits.daily_loss_limit_pct)
        )

        if current_pnl < -daily_loss_limit:
            self.trigger_circuit_breaker(
                f"Daily loss limit exceeded: {current_pnl:.2f} CHF < "
                f"-{daily_loss_limit:.2f} CHF ({self.limits.daily_loss_limit_pct:.1%})"
            )
            return False, "CIRCUIT BREAKER TRIGGERED"

        # Calculate percentage used
        if current_pnl < 0:
            pct_used = (abs(current_pnl) / daily_loss_limit) * 100
            return True, f"Daily loss: {current_pnl:.2f} CHF ({pct_used:.1f}% of limit)"

        return True, f"Daily P&L: +{current_pnl:.2f} CHF"

    def trigger_circuit_breaker(self, reason: str):
        """
        Trigger circuit breaker - stops all new trading.

        Args:
            reason: Reason for triggering circuit breaker
        """
        self.circuit_breaker_active = True
        logger.critical(f"🚨 CIRCUIT BREAKER TRIGGERED: {reason}")

        # TODO: Integration points:
        # - Send critical alert to alerting system
        # - Close all open positions
        # - Prevent new positions from opening
        # - Notify administrators

    def reset_circuit_breaker(self):
        """Reset circuit breaker - must be done manually."""
        self.circuit_breaker_active = False
        logger.info("Circuit breaker reset")

    def is_circuit_breaker_active(self) -> bool:
        """Check if circuit breaker is currently active."""
        return self.circuit_breaker_active

    # ========================================================================
    # Position Tracking
    # ========================================================================

    def add_position(self, position: PositionInfo):
        """
        Add a position to portfolio tracking.

        Args:
            position: Position information
        """
        self.positions[position.symbol] = position
        logger.info(
            f"Position added: {position.symbol} {position.side} "
            f"{position.quantity} @ {position.entry_price:.2f} "
            f"(Value: {position.position_value_chf:.2f} CHF)"
        )

    def remove_position(self, symbol: str):
        """
        Remove a position from portfolio tracking.

        Args:
            symbol: Symbol to remove
        """
        if symbol in self.positions:
            self.positions.pop(symbol)
            logger.info(f"Position removed: {symbol}")
        else:
            logger.warning(f"Attempted to remove non-existent position: {symbol}")

    def update_position(
        self,
        symbol: str,
        current_price: Decimal,
        unrealized_pnl: Decimal,
    ):
        """
        Update position with current price and P&L.

        Args:
            symbol: Symbol to update
            current_price: Current market price
            unrealized_pnl: Current unrealized P&L
        """
        if symbol in self.positions:
            self.positions[symbol].current_price = current_price
            self.positions[symbol].unrealized_pnl = unrealized_pnl
            self.positions[symbol].timestamp = datetime.utcnow()
        else:
            logger.warning(f"Attempted to update non-existent position: {symbol}")

    def get_position(self, symbol: str) -> Optional[PositionInfo]:
        """
        Get position information.

        Args:
            symbol: Symbol to get

        Returns:
            Position info or None if not found
        """
        return self.positions.get(symbol)

    def get_all_positions(self) -> List[PositionInfo]:
        """Get all tracked positions."""
        return list(self.positions.values())

    # ========================================================================
    # Portfolio Status and Metrics
    # ========================================================================

    def calculate_total_exposure(self) -> Decimal:
        """
        Calculate total portfolio exposure in CHF.

        Returns:
            Total exposure across all positions
        """
        return sum(pos.position_value_chf for pos in self.positions.values())

    def calculate_total_unrealized_pnl(self) -> Decimal:
        """
        Calculate total unrealized P&L across all positions.

        Returns:
            Total unrealized P&L in CHF
        """
        return sum(pos.unrealized_pnl for pos in self.positions.values())

    def get_largest_position(self) -> Tuple[Optional[PositionInfo], Decimal, float]:
        """
        Get largest position by value.

        Returns:
            Tuple of (position, value_chf, percentage_of_portfolio)
        """
        if not self.positions:
            return None, Decimal("0"), 0.0

        largest = max(self.positions.values(), key=lambda p: p.position_value_chf)

        pct_of_portfolio = float(
            largest.position_value_chf / self.limits.max_portfolio_value * 100
        )

        return largest, largest.position_value_chf, pct_of_portfolio

    def get_portfolio_status(self) -> PortfolioStatus:
        """
        Get current portfolio status snapshot.

        Returns:
            Complete portfolio status
        """
        total_exposure = self.calculate_total_exposure()
        exposure_pct = float(total_exposure / self.limits.max_portfolio_value * 100)

        largest_pos, largest_value, largest_pct = self.get_largest_position()

        total_unrealized_pnl = self.calculate_total_unrealized_pnl()

        # Get daily P&L
        today = date.today()
        daily_pnl = self.daily_pnl_history.get(today, Decimal("0"))

        return PortfolioStatus(
            total_portfolio_value=self.limits.max_portfolio_value,
            open_positions=len(self.positions),
            total_exposure_chf=total_exposure,
            exposure_pct=exposure_pct,
            largest_position_chf=largest_value,
            largest_position_pct=largest_pct,
            total_unrealized_pnl=total_unrealized_pnl,
            daily_pnl=daily_pnl,
            timestamp=datetime.utcnow(),
        )

    def update_daily_pnl(self, pnl: Decimal):
        """
        Update daily P&L tracking.

        Args:
            pnl: Current day's realized P&L
        """
        today = date.today()
        self.daily_pnl_history[today] = pnl

    # ========================================================================
    # Concentration Analysis
    # ========================================================================

    def check_position_concentration(
        self, max_concentration_pct: float = 0.4
    ) -> Tuple[bool, List[str]]:
        """
        Check if portfolio is too concentrated in few positions.

        Args:
            max_concentration_pct: Maximum concentration allowed (default 40%)

        Returns:
            Tuple of (is_diversified: bool, warnings: List[str])
        """
        warnings = []

        if len(self.positions) == 0:
            return True, []

        # Check single position concentration
        largest_pos, largest_value, largest_pct = self.get_largest_position()

        if largest_pct > max_concentration_pct * 100:
            warnings.append(
                f"Largest position ({largest_pos.symbol}) is {largest_pct:.1f}% "
                f"of portfolio (limit: {max_concentration_pct:.1%})"
            )

        # Check top 3 positions concentration
        if len(self.positions) >= 3:
            sorted_positions = sorted(
                self.positions.values(),
                key=lambda p: p.position_value_chf,
                reverse=True,
            )
            top_3_value = sum(p.position_value_chf for p in sorted_positions[:3])
            top_3_pct = float(top_3_value / self.limits.max_portfolio_value * 100)

            if top_3_pct > 60:  # Top 3 > 60% is concentrated
                warnings.append(
                    f"Top 3 positions represent {top_3_pct:.1f}% of portfolio"
                )

        is_diversified = len(warnings) == 0

        if not is_diversified:
            logger.warning(f"Portfolio concentration issues: {'; '.join(warnings)}")

        return is_diversified, warnings

    # ========================================================================
    # Reporting and Logging
    # ========================================================================

    def get_risk_summary(self) -> Dict:
        """
        Get comprehensive risk summary.

        Returns:
            Dictionary with risk metrics
        """
        status = self.get_portfolio_status()

        return {
            "portfolio_value": float(status.total_portfolio_value),
            "open_positions": status.open_positions,
            "total_exposure_chf": float(status.total_exposure_chf),
            "exposure_pct": status.exposure_pct,
            "largest_position_chf": float(status.largest_position_chf),
            "largest_position_pct": status.largest_position_pct,
            "total_unrealized_pnl": float(status.total_unrealized_pnl),
            "daily_pnl": float(status.daily_pnl),
            "circuit_breaker_active": self.circuit_breaker_active,
            "limits": {
                "max_single_position_pct": self.limits.max_single_position_pct,
                "max_total_exposure_pct": self.limits.max_total_exposure_pct,
                "daily_loss_limit_pct": self.limits.daily_loss_limit_pct,
                "max_leverage": self.limits.max_leverage,
            },
        }
