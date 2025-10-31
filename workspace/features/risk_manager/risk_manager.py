"""
Risk Manager

Main risk management coordinator implementing signal validation,
position limits, and risk controls.

Author: Risk Management Team
Date: 2025-10-28
"""

import logging
from decimal import Decimal
from typing import Any, List, Optional

from .circuit_breaker import CircuitBreaker
from .models import (
    CircuitBreakerStatus,
    Protection,
    RiskCheckResult,
    RiskValidation,
    ValidationStatus,
)
from .stop_loss_manager import StopLossManager

logger = logging.getLogger(__name__)


class RiskManager:
    """
    Risk Manager

    Coordinates risk management across multiple layers:
    - Pre-trade signal validation
    - Position and exposure limits
    - Multi-layer stop-loss protection
    - Daily loss circuit breaker

    Example:
        ```python
        risk_manager = RiskManager(
            starting_balance_chf=Decimal("2626.96"),
            exchange=exchange,
            trade_executor=executor,
        )

        # Validate trading signal
        validation = await risk_manager.validate_signal(signal)

        if validation.approved:
            # Execute trade
            position = await execute_trade(signal)

            # Start stop-loss protection
            protection = await risk_manager.start_multi_layer_protection(position)
        ```
    """

    # Risk limits (from API contract)
    MAX_CONCURRENT_POSITIONS = 6
    MAX_POSITION_SIZE_PCT = Decimal("0.20")  # 20%
    MAX_TOTAL_EXPOSURE_PCT = Decimal("0.80")  # 80%
    MIN_LEVERAGE = 5
    MAX_LEVERAGE = 40
    MIN_STOP_LOSS_PCT = Decimal("0.01")  # 1%
    MAX_STOP_LOSS_PCT = Decimal("0.10")  # 10%
    MIN_CONFIDENCE = Decimal("0.60")  # 60%

    # Per-symbol leverage limits
    PER_SYMBOL_LEVERAGE = {
        "BTC/USDT:USDT": 40,
        "ETH/USDT:USDT": 40,
        "SOL/USDT:USDT": 25,
        "BNB/USDT:USDT": 25,
        "ADA/USDT:USDT": 20,
        "DOGE/USDT:USDT": 20,
    }

    def __init__(
        self,
        starting_balance_chf: Decimal = Decimal("2626.96"),
        max_daily_loss_chf: Decimal = Decimal("-183.89"),
        exchange=None,
        trade_executor=None,
        position_tracker=None,
    ):
        """
        Initialize Risk Manager

        Args:
            starting_balance_chf: Starting account balance
            max_daily_loss_chf: Maximum daily loss limit
            exchange: Exchange API client
            trade_executor: Trade executor instance
            position_tracker: Position tracking system
        """
        self.starting_balance_chf = starting_balance_chf
        self.current_balance_chf = starting_balance_chf
        self.exchange = exchange
        self.trade_executor = trade_executor
        self.position_tracker = position_tracker

        # Initialize sub-managers
        self.circuit_breaker = CircuitBreaker(
            starting_balance_chf=starting_balance_chf,
            max_daily_loss_chf=max_daily_loss_chf,
            trade_executor=trade_executor,
        )

        self.stop_loss_manager = StopLossManager(
            exchange=exchange,
            trade_executor=trade_executor,
        )

        logger.info(
            f"RiskManager initialized: Balance CHF {starting_balance_chf}, "
            f"Daily loss limit CHF {max_daily_loss_chf}"
        )

    async def validate_signal(
        self,
        signal: Any,  # TradingSignal from trading_loop or StrategySignal
        current_price: Optional[Decimal] = None,
    ) -> RiskValidation:
        """
        Validate trading signal against all risk limits

        Args:
            signal: Trading signal to validate
            current_price: Current market price (optional)

        Returns:
            RiskValidation with approval status and checks
        """
        checks: List[RiskCheckResult] = []

        # Get current positions
        open_positions = await self._get_open_positions()
        position_count = len(open_positions)

        # Calculate current exposure
        total_exposure_pct = await self._calculate_total_exposure()

        # Get daily P&L
        daily_pnl = await self._get_daily_pnl()

        # Check circuit breaker
        circuit_status = await self.circuit_breaker.check_daily_loss(daily_pnl)

        # Initialize validation
        validation = RiskValidation(
            status=ValidationStatus.APPROVED,
            approved=True,
            checks=checks,
            total_exposure_pct=total_exposure_pct,
            position_count=position_count,
            daily_pnl_chf=daily_pnl,
            circuit_breaker_active=circuit_status.is_tripped(),
        )

        # Pre-trade checks
        await self._check_circuit_breaker(validation, circuit_status)
        await self._check_position_count(validation, position_count)
        await self._check_confidence(validation, signal)
        await self._check_position_size(validation, signal)
        await self._check_total_exposure(validation, signal, total_exposure_pct)
        await self._check_leverage(validation, signal)
        await self._check_stop_loss(validation, signal)

        # Set final status
        if not validation.approved:
            validation.status = ValidationStatus.REJECTED
        elif validation.warnings:
            validation.status = ValidationStatus.WARNING

        logger.info(
            f"Signal validation: {validation.status.value} "
            f"(approved: {validation.approved}, checks: {len(checks)})"
        )

        return validation

    async def _check_circuit_breaker(
        self,
        validation: RiskValidation,
        circuit_status: CircuitBreakerStatus,
    ):
        """Check if circuit breaker is active"""
        if circuit_status.is_tripped():
            validation.add_rejection("Circuit breaker is TRIPPED - all trading halted")
            validation.checks.append(
                RiskCheckResult(
                    check_name="Circuit Breaker",
                    passed=False,
                    message=f"Daily loss limit exceeded: CHF {circuit_status.daily_pnl_chf:,.2f}",
                    severity="error",
                    current_value=circuit_status.daily_pnl_chf,
                    limit_value=circuit_status.daily_loss_limit_chf,
                )
            )
        else:
            validation.checks.append(
                RiskCheckResult(
                    check_name="Circuit Breaker",
                    passed=True,
                    message=f"Daily P&L: CHF {circuit_status.daily_pnl_chf:,.2f}",
                    severity="info",
                )
            )

    async def _check_position_count(self, validation: RiskValidation, count: int):
        """Check maximum concurrent positions limit"""
        passed = count < self.MAX_CONCURRENT_POSITIONS

        if not passed:
            validation.add_rejection(
                f"Maximum concurrent positions ({self.MAX_CONCURRENT_POSITIONS}) reached"
            )

        validation.checks.append(
            RiskCheckResult(
                check_name="Position Count",
                passed=passed,
                message=f"{count} / {self.MAX_CONCURRENT_POSITIONS} positions",
                severity="error" if not passed else "info",
                current_value=Decimal(count),
                limit_value=Decimal(self.MAX_CONCURRENT_POSITIONS),
            )
        )

    async def _check_confidence(self, validation: RiskValidation, signal: Any):
        """Check minimum confidence requirement"""
        confidence = getattr(signal, "confidence", Decimal("0"))
        passed = confidence >= self.MIN_CONFIDENCE

        if not passed:
            validation.add_rejection(
                f"Signal confidence {confidence:.1%} below minimum {self.MIN_CONFIDENCE:.1%}"
            )

        validation.checks.append(
            RiskCheckResult(
                check_name="Confidence",
                passed=passed,
                message=f"{confidence:.1%} (min: {self.MIN_CONFIDENCE:.1%})",
                severity="error" if not passed else "info",
                current_value=confidence,
                limit_value=self.MIN_CONFIDENCE,
            )
        )

    async def _check_position_size(self, validation: RiskValidation, signal: Any):
        """Check maximum position size limit"""
        size_pct = getattr(signal, "size_pct", Decimal("0"))
        passed = size_pct <= self.MAX_POSITION_SIZE_PCT

        if not passed:
            validation.add_rejection(
                f"Position size {size_pct:.1%} exceeds maximum {self.MAX_POSITION_SIZE_PCT:.1%}"
            )

        validation.checks.append(
            RiskCheckResult(
                check_name="Position Size",
                passed=passed,
                message=f"{size_pct:.1%} (max: {self.MAX_POSITION_SIZE_PCT:.1%})",
                severity="error" if not passed else "info",
                current_value=size_pct,
                limit_value=self.MAX_POSITION_SIZE_PCT,
            )
        )

    async def _check_total_exposure(
        self,
        validation: RiskValidation,
        signal: Any,
        current_exposure: Decimal,
    ):
        """Check maximum total exposure limit"""
        size_pct = getattr(signal, "size_pct", Decimal("0"))
        new_exposure = current_exposure + size_pct
        passed = new_exposure <= self.MAX_TOTAL_EXPOSURE_PCT

        if not passed:
            validation.add_rejection(
                f"Total exposure {new_exposure:.1%} would exceed maximum {self.MAX_TOTAL_EXPOSURE_PCT:.1%}"
            )

        validation.checks.append(
            RiskCheckResult(
                check_name="Total Exposure",
                passed=passed,
                message=f"{new_exposure:.1%} (max: {self.MAX_TOTAL_EXPOSURE_PCT:.1%})",
                severity="error" if not passed else "info",
                current_value=new_exposure,
                limit_value=self.MAX_TOTAL_EXPOSURE_PCT,
            )
        )

    async def _check_leverage(self, validation: RiskValidation, signal: Any):
        """Check leverage limits"""
        leverage = getattr(signal, "leverage", None)
        symbol = getattr(signal, "symbol", "")

        if leverage is None:
            # No leverage specified, skip check
            return

        # Get symbol-specific limit
        max_leverage = self.PER_SYMBOL_LEVERAGE.get(symbol, self.MAX_LEVERAGE)

        passed = self.MIN_LEVERAGE <= leverage <= max_leverage

        if not passed:
            validation.add_rejection(
                f"Leverage {leverage}x outside allowed range {self.MIN_LEVERAGE}-{max_leverage}x for {symbol}"
            )

        validation.checks.append(
            RiskCheckResult(
                check_name="Leverage",
                passed=passed,
                message=f"{leverage}x (range: {self.MIN_LEVERAGE}-{max_leverage}x)",
                severity="error" if not passed else "info",
                current_value=Decimal(leverage),
                limit_value=Decimal(max_leverage),
            )
        )

    async def _check_stop_loss(self, validation: RiskValidation, signal: Any):
        """Check stop-loss requirements"""
        stop_loss_pct = getattr(signal, "stop_loss_pct", None)

        if stop_loss_pct is None:
            validation.add_warning("No stop-loss specified")
            validation.checks.append(
                RiskCheckResult(
                    check_name="Stop-Loss",
                    passed=True,
                    message="No stop-loss specified (warning only)",
                    severity="warning",
                )
            )
            return

        passed = self.MIN_STOP_LOSS_PCT <= stop_loss_pct <= self.MAX_STOP_LOSS_PCT

        if not passed:
            validation.add_rejection(
                f"Stop-loss {stop_loss_pct:.1%} outside allowed range "
                f"{self.MIN_STOP_LOSS_PCT:.1%}-{self.MAX_STOP_LOSS_PCT:.1%}"
            )

        validation.checks.append(
            RiskCheckResult(
                check_name="Stop-Loss",
                passed=passed,
                message=f"{stop_loss_pct:.1%} (range: {self.MIN_STOP_LOSS_PCT:.1%}-{self.MAX_STOP_LOSS_PCT:.1%})",
                severity="error" if not passed else "info",
                current_value=stop_loss_pct,
                limit_value=self.MAX_STOP_LOSS_PCT,
            )
        )

    async def start_multi_layer_protection(
        self,
        position: Any,  # Position object
    ) -> Protection:
        """
        Start 3-layer stop-loss protection for a position

        Args:
            position: Position object with id, symbol, entry_price, stop_loss_pct

        Returns:
            Protection object with layer statuses
        """
        logger.info(f"Starting multi-layer protection for position {position.id}")

        protection = await self.stop_loss_manager.start_protection(
            position_id=position.id,
            symbol=position.symbol,
            entry_price=position.entry_price,
            stop_loss_pct=position.stop_loss_pct,
            side=getattr(position, "side", "long"),
        )

        logger.info(
            f"Multi-layer protection active: {protection.layer_count()} layers for {position.symbol}"
        )

        return protection

    async def check_daily_loss_limit(self) -> CircuitBreakerStatus:
        """
        Check if daily loss limit has been exceeded

        Returns:
            CircuitBreakerStatus with current state
        """
        daily_pnl = await self._get_daily_pnl()
        return await self.circuit_breaker.check_daily_loss(daily_pnl)

    async def emergency_close_position(
        self,
        position_id: str,
        reason: str,
    ) -> Any:  # Returns Order or ExecutionResult
        """
        Emergency position closure (bypasses normal validation)

        Args:
            position_id: Position identifier
            reason: Reason for emergency closure

        Returns:
            Order or ExecutionResult from trade executor
        """
        logger.critical(
            f"🚨 Emergency close requested for position {position_id}: {reason}"
        )

        if not self.trade_executor:
            raise ValueError("No trade executor available for emergency closure")

        # Close immediately
        result = await self.trade_executor.close_position(
            position_id=position_id,
            reason=f"emergency: {reason}",
            force=True,
        )

        logger.critical(f"Emergency close completed for position {position_id}")

        return result

    async def _get_open_positions(self) -> List[Any]:
        """Get list of currently open positions"""
        if self.position_tracker:
            positions = await self.position_tracker.get_open_positions()
            return list(positions) if positions else []
        return []

    async def _calculate_total_exposure(self) -> Decimal:
        """Calculate total exposure across all positions"""
        positions = await self._get_open_positions()

        if not positions:
            return Decimal("0")

        total_exposure = sum(
            getattr(pos, "size_pct", Decimal("0")) for pos in positions
        )

        return Decimal(str(total_exposure))

    async def _get_daily_pnl(self) -> Decimal:
        """Get today's P&L in CHF"""
        # In production, this would query the position tracker or database
        # For now, return from circuit breaker status
        return self.circuit_breaker.status.daily_pnl_chf

    def get_circuit_breaker_status(self) -> CircuitBreakerStatus:
        """Get current circuit breaker status"""
        return self.circuit_breaker.get_status()

    def get_protection_status(self, position_id: str) -> Optional[Protection]:
        """Get stop-loss protection status for a position"""
        return self.stop_loss_manager.get_protection(position_id)

    async def stop_protection(self, position_id: str):
        """Stop stop-loss protection for a position"""
        await self.stop_loss_manager.stop_protection(position_id)


# Export
__all__ = ["RiskManager"]
