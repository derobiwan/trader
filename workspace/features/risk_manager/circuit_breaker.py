"""
Circuit Breaker

Daily loss limit monitoring and emergency system shutdown.

Author: Risk Management Team
Date: 2025-10-28
"""

import asyncio
import logging
import secrets
from datetime import datetime, time, timezone
from decimal import Decimal
from typing import List, Optional

from .models import CircuitBreakerState, CircuitBreakerStatus

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """
    Circuit Breaker Implementation

    Monitors daily P&L and triggers system shutdown when daily loss limit is exceeded.

    Configuration:
    - max_daily_loss_pct: -7% maximum daily loss
    - max_daily_loss_chf: CHF -183.89 (7% of CHF 2,626.96)
    - reset_time_utc: 00:00 UTC daily reset
    - manual_reset_required: Requires manual confirmation to resume

    Example:
        ```python
        circuit_breaker = CircuitBreaker(
            starting_balance_chf=Decimal("2626.96"),
            max_daily_loss_chf=Decimal("-183.89")
        )

        # Check daily loss
        status = await circuit_breaker.check_daily_loss()

        if status.is_tripped():
            logger.critical("Circuit breaker tripped!")
            await close_all_positions()
        ```
    """

    def __init__(
        self,
        starting_balance_chf: Decimal = Decimal("2626.96"),
        max_daily_loss_chf: Decimal = Decimal("-183.89"),
        max_daily_loss_pct: Decimal = Decimal("-0.07"),
        reset_time_utc: time = time(0, 0),  # 00:00 UTC
        trade_executor=None,  # Optional dependency injection
    ):
        """
        Initialize Circuit Breaker

        Args:
            starting_balance_chf: Starting balance for the day
            max_daily_loss_chf: Maximum allowed daily loss in CHF
            max_daily_loss_pct: Maximum allowed daily loss percentage
            reset_time_utc: Daily reset time (UTC)
            trade_executor: Trade executor instance for closing positions
        """
        self.starting_balance_chf = starting_balance_chf
        self.max_daily_loss_chf = max_daily_loss_chf
        self.max_daily_loss_pct = max_daily_loss_pct
        self.reset_time_utc = reset_time_utc
        self.trade_executor = trade_executor

        # Initialize status
        self.status = CircuitBreakerStatus(
            state=CircuitBreakerState.ACTIVE,
            daily_pnl_chf=Decimal("0"),
            daily_loss_limit_chf=max_daily_loss_chf,
            daily_loss_limit_pct=max_daily_loss_pct,
            starting_balance_chf=starting_balance_chf,
            current_balance_chf=starting_balance_chf,
        )

        # Alert callbacks
        self._alert_callbacks: List[callable] = []

        logger.info(
            f"Circuit Breaker initialized: "
            f"Starting balance CHF {starting_balance_chf}, "
            f"Daily loss limit CHF {max_daily_loss_chf} ({max_daily_loss_pct:.1%})"
        )

    async def check_daily_loss(
        self,
        current_daily_pnl_chf: Optional[Decimal] = None,
    ) -> CircuitBreakerStatus:
        """
        Check if daily loss limit has been exceeded

        Args:
            current_daily_pnl_chf: Current daily P&L (if None, will be calculated)

        Returns:
            CircuitBreakerStatus with current state
        """
        # Update daily P&L
        if current_daily_pnl_chf is not None:
            self.status.daily_pnl_chf = current_daily_pnl_chf
            self.status.current_balance_chf = (
                self.starting_balance_chf + current_daily_pnl_chf
            )

        # Check if already tripped
        if self.status.is_tripped() or self.status.is_manual_reset_required():
            logger.warning(
                f"Circuit breaker already in state: {self.status.state.value}"
            )
            return self.status

        # Check if should trip
        if self.status.should_trip():
            logger.critical(
                f"🚨 CIRCUIT BREAKER TRIGGERED 🚨\n"
                f"Daily P&L: CHF {self.status.daily_pnl_chf:,.2f} "
                f"({self.status.loss_percentage():.2f}%)\n"
                f"Daily Limit: CHF {self.status.daily_loss_limit_chf:,.2f} "
                f"({self.status.daily_loss_limit_pct:.1%})"
            )

            # Trip the circuit breaker
            await self._trip()

        return self.status

    async def _trip(self):
        """
        Trip the circuit breaker

        Actions:
        1. Change state to TRIPPED
        2. Close all open positions
        3. Send critical alerts
        4. Require manual reset
        """
        self.status.state = CircuitBreakerState.TRIPPED
        self.status.tripped_at = datetime.now(timezone.utc)

        # Send alerts
        await self._send_alert(
            level="critical",
            message=f"Circuit Breaker TRIPPED: Daily loss CHF {self.status.daily_pnl_chf:,.2f}",
        )

        # Close all positions
        if self.trade_executor:
            try:
                logger.critical("Closing all positions due to circuit breaker...")
                await self._close_all_positions()
            except Exception as e:
                logger.error(f"Error closing positions: {e}")
                # Continue with circuit breaker activation even if close fails

        # Enter manual reset required state
        self.status.state = CircuitBreakerState.MANUAL_RESET_REQUIRED
        self.status.manual_reset_required = True
        self.status.manual_reset_token = self._generate_reset_token()

        logger.critical(
            f"🔒 Manual reset required. Reset token: {self.status.manual_reset_token}"
        )

        await self._send_alert(
            level="critical",
            message=(
                f"Circuit breaker entered MANUAL RESET REQUIRED state. "
                f"All trading halted. Reset token: {self.status.manual_reset_token}"
            ),
        )

    async def _close_all_positions(self):
        """Close all open positions (emergency)"""
        if not self.trade_executor:
            logger.warning("No trade executor available for closing positions")
            return

        try:
            # Get all open positions
            positions = await self.trade_executor.get_open_positions()

            logger.info(f"Closing {len(positions)} open positions...")

            # Close each position
            for position in positions:
                try:
                    logger.info(
                        f"Closing position {position.symbol} (ID: {position.id})"
                    )
                    await self.trade_executor.close_position(
                        position_id=position.id,
                        reason="circuit_breaker_triggered",
                    )
                except Exception as e:
                    logger.error(f"Failed to close position {position.symbol}: {e}")

            logger.info("All positions closed")

        except Exception as e:
            logger.error(f"Error getting/closing positions: {e}")
            raise

    def _generate_reset_token(self) -> str:
        """Generate secure reset token"""
        return secrets.token_hex(8)

    async def manual_reset(self, reset_token: str) -> bool:
        """
        Manually reset circuit breaker

        Args:
            reset_token: Reset token provided when circuit breaker tripped

        Returns:
            True if reset successful, False otherwise
        """
        if not self.status.is_manual_reset_required():
            logger.warning("Circuit breaker not in manual reset required state")
            return False

        if reset_token != self.status.manual_reset_token:
            logger.error("Invalid reset token provided")
            return False

        logger.warning("Circuit breaker manually reset")

        # Reset status
        await self._reset()

        await self._send_alert(
            level="warning",
            message="Circuit breaker manually reset. Trading can resume.",
        )

        return True

    async def daily_reset(self):
        """
        Daily automatic reset (at 00:00 UTC)

        Resets daily P&L and trade counters.
        """
        logger.info("Performing daily circuit breaker reset")

        await self._reset()

        await self._send_alert(
            level="info",
            message="Circuit breaker daily reset complete",
        )

    async def _reset(self):
        """Internal reset logic"""
        self.status = CircuitBreakerStatus(
            state=CircuitBreakerState.ACTIVE,
            daily_pnl_chf=Decimal("0"),
            daily_loss_limit_chf=self.max_daily_loss_chf,
            daily_loss_limit_pct=self.max_daily_loss_pct,
            starting_balance_chf=self.starting_balance_chf,
            current_balance_chf=self.starting_balance_chf,
            last_reset_at=datetime.now(timezone.utc),
        )

    async def update_daily_pnl(self, daily_pnl_chf: Decimal):
        """
        Update daily P&L and check circuit breaker

        Args:
            daily_pnl_chf: Current daily P&L in CHF
        """
        self.status.daily_pnl_chf = daily_pnl_chf
        self.status.current_balance_chf = self.starting_balance_chf + daily_pnl_chf

        # Check if should trip
        await self.check_daily_loss(daily_pnl_chf)

    async def update_trade_stats(self, is_winning_trade: bool):
        """
        Update daily trade statistics

        Args:
            is_winning_trade: True if trade was profitable
        """
        self.status.daily_trade_count += 1

        if is_winning_trade:
            self.status.daily_winning_trades += 1
        else:
            self.status.daily_losing_trades += 1

    def register_alert_callback(self, callback: callable):
        """
        Register alert callback function

        Args:
            callback: Async function(level: str, message: str)
        """
        self._alert_callbacks.append(callback)

    async def _send_alert(self, level: str, message: str):
        """
        Send alert to all registered callbacks

        Args:
            level: Alert level (info, warning, critical)
            message: Alert message
        """
        for callback in self._alert_callbacks:
            try:
                await callback(level, message)
            except Exception as e:
                logger.error(f"Error sending alert: {e}")

    def get_status(self) -> CircuitBreakerStatus:
        """Get current circuit breaker status"""
        return self.status

    def is_trading_allowed(self) -> bool:
        """Check if trading is currently allowed"""
        return self.status.state == CircuitBreakerState.ACTIVE

    async def start_daily_reset_scheduler(self):
        """
        Start background task for daily resets

        Runs indefinitely, checking every minute for reset time.
        """
        logger.info("Starting daily reset scheduler")

        while True:
            try:
                now = datetime.now(timezone.utc).time()

                # Check if it's reset time (within 1 minute)
                if self._is_reset_time(now):
                    logger.info("Daily reset time reached")
                    await self.daily_reset()

                    # Sleep for 2 minutes to avoid double reset
                    await asyncio.sleep(120)
                else:
                    # Check every minute
                    await asyncio.sleep(60)

            except Exception as e:
                logger.error(f"Error in daily reset scheduler: {e}")
                await asyncio.sleep(60)

    def _is_reset_time(self, current_time: time) -> bool:
        """Check if current time is reset time (within 1 minute)"""
        # Convert to minutes for comparison
        current_minutes = current_time.hour * 60 + current_time.minute
        reset_minutes = self.reset_time_utc.hour * 60 + self.reset_time_utc.minute

        # Within 1 minute of reset time
        return abs(current_minutes - reset_minutes) <= 1


# Export
__all__ = ["CircuitBreaker"]
