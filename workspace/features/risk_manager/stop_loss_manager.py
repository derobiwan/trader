"""
Stop-Loss Manager

Multi-layered stop-loss protection system with 3 independent layers.

Author: Risk Management Team
Date: 2025-10-28
"""

import logging
import asyncio
from decimal import Decimal
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from .models import Protection, ProtectionLayer

logger = logging.getLogger(__name__)


class StopLossManager:
    """
    Multi-Layered Stop-Loss Protection

    Implements 3 independent protection layers:
    1. Exchange Stop-Loss Order (primary)
    2. Application-Level Monitoring (backup)
    3. Emergency Liquidation (last resort at >15% loss)

    Each layer operates independently to ensure robust protection.

    Example:
        ```python
        stop_manager = StopLossManager(exchange=exchange, trade_executor=executor)

        # Start protection for a position
        protection = await stop_manager.start_protection(
            position_id="pos_123",
            symbol="BTC/USDT:USDT",
            entry_price=Decimal("50000"),
            stop_loss_pct=Decimal("0.03"),  # 3%
        )

        # Check if protection is active
        assert protection.layer_count() == 3
        ```
    """

    def __init__(
        self,
        exchange=None,  # Exchange API client (ccxt)
        trade_executor=None,  # Trade executor instance
        check_interval_seconds: int = 2,  # Layer 2 check interval
        emergency_check_interval_seconds: int = 1,  # Layer 3 check interval
    ):
        """
        Initialize Stop-Loss Manager

        Args:
            exchange: Exchange API client for placing stop orders
            trade_executor: Trade executor for emergency closes
            check_interval_seconds: Interval for layer 2 monitoring
            emergency_check_interval_seconds: Interval for layer 3 monitoring
        """
        self.exchange = exchange
        self.trade_executor = trade_executor
        self.check_interval = check_interval_seconds
        self.emergency_check_interval = emergency_check_interval_seconds

        # Active protections
        self.protections: Dict[str, Protection] = {}

        # Background tasks
        self.monitor_tasks: Dict[str, asyncio.Task] = {}

        logger.info(
            f"StopLossManager initialized (check interval: {check_interval_seconds}s, "
            f"emergency: {emergency_check_interval_seconds}s)"
        )

    async def start_protection(
        self,
        position_id: str,
        symbol: str,
        entry_price: Decimal,
        stop_loss_pct: Decimal,
        side: str = "long",  # long or short
    ) -> Protection:
        """
        Start multi-layer stop-loss protection for a position

        Args:
            position_id: Position identifier
            symbol: Trading symbol
            entry_price: Position entry price
            stop_loss_pct: Stop-loss percentage (e.g., 0.03 for 3%)
            side: Position side ("long" or "short")

        Returns:
            Protection object with all layer statuses
        """
        # Calculate stop-loss price
        if side == "long":
            stop_loss_price = entry_price * (Decimal("1") - stop_loss_pct)
        else:
            stop_loss_price = entry_price * (Decimal("1") + stop_loss_pct)

        logger.info(
            f"Starting protection for {symbol} position {position_id}: "
            f"Entry ${entry_price}, Stop ${stop_loss_price} ({stop_loss_pct:.1%})"
        )

        # Create protection object
        protection = Protection(
            position_id=position_id,
            symbol=symbol,
            entry_price=entry_price,
            stop_loss_price=stop_loss_price,
            stop_loss_pct=stop_loss_pct,
        )

        # Layer 1: Place exchange stop-loss order
        try:
            await self._place_exchange_stop(protection, side)
        except Exception as e:
            logger.error(f"Failed to place exchange stop: {e}")
            # Continue with other layers

        # Layer 2: Start application-level monitoring
        try:
            await self._start_app_monitor(protection, side)
        except Exception as e:
            logger.error(f"Failed to start app monitor: {e}")

        # Layer 3: Start emergency monitoring
        try:
            await self._start_emergency_monitor(protection, side)
        except Exception as e:
            logger.error(f"Failed to start emergency monitor: {e}")

        # Store protection
        self.protections[position_id] = protection

        logger.info(
            f"Protection started for {symbol}: {protection.layer_count()} layers active"
        )

        return protection

    async def _place_exchange_stop(self, protection: Protection, side: str):
        """
        Layer 1: Place stop-loss order on exchange

        This is the primary protection layer.
        """
        if not self.exchange:
            logger.warning("No exchange client available for stop-loss order")
            return

        try:
            # Determine order side
            order_side = "sell" if side == "long" else "buy"

            # Place stop-market order
            order = await self.exchange.create_order(
                symbol=protection.symbol,
                type="stop_market",
                side=order_side,
                amount=None,  # Will be filled by exchange
                params={
                    "stopPrice": float(protection.stop_loss_price),
                    "reduceOnly": True,  # Only reduce position, don't open new
                },
            )

            protection.exchange_stop_order_id = order["id"]
            protection.exchange_stop_active = True

            logger.info(
                f"Layer 1 (Exchange Stop) active for {protection.symbol}: "
                f"Order ID {order['id']}"
            )

        except Exception as e:
            logger.error(f"Failed to place exchange stop-loss: {e}")
            raise

    async def _start_app_monitor(self, protection: Protection, side: str):
        """
        Layer 2: Start application-level monitoring

        Monitors price every 2 seconds and triggers if exchange stop fails.
        """
        task = asyncio.create_task(
            self._app_monitor_loop(protection, side)
        )

        protection.app_monitor_active = True
        protection.app_monitor_task_id = str(id(task))
        self.monitor_tasks[protection.position_id] = task

        logger.info(
            f"Layer 2 (App Monitor) started for {protection.symbol}"
        )

    async def _app_monitor_loop(self, protection: Protection, side: str):
        """Application-level monitoring loop"""
        while protection.app_monitor_active:
            try:
                # Get current price
                current_price = await self._get_current_price(protection.symbol)

                # Check if stop should trigger
                if self._should_trigger_stop(
                    current_price,
                    protection.stop_loss_price,
                    side
                ):
                    logger.warning(
                        f"⚠️ Layer 2 (App Monitor) triggered for {protection.symbol}: "
                        f"Price ${current_price} hit stop ${protection.stop_loss_price}"
                    )

                    # Close position at market
                    await self._close_position_market(protection)

                    # Deactivate monitoring
                    protection.app_monitor_active = False
                    protection.triggered_layer = ProtectionLayer.APP_MONITOR
                    protection.triggered_at = datetime.now(timezone.utc)

                    break

                # Update last check time
                protection.last_check_at = datetime.now(timezone.utc)

                # Wait before next check
                await asyncio.sleep(self.check_interval)

            except asyncio.CancelledError:
                logger.info(f"App monitor cancelled for {protection.symbol}")
                break
            except Exception as e:
                logger.error(f"Error in app monitor: {e}")
                await asyncio.sleep(self.check_interval)

    async def _start_emergency_monitor(self, protection: Protection, side: str):
        """
        Layer 3: Start emergency liquidation monitoring

        Monitors for >15% loss and triggers emergency close.
        """
        task = asyncio.create_task(
            self._emergency_monitor_loop(protection, side)
        )

        protection.emergency_monitor_active = True
        protection.emergency_monitor_task_id = str(id(task))

        logger.info(
            f"Layer 3 (Emergency) started for {protection.symbol} "
            f"(threshold: {protection.emergency_threshold_pct:.1%})"
        )

    async def _emergency_monitor_loop(self, protection: Protection, side: str):
        """Emergency liquidation monitoring loop"""
        while protection.emergency_monitor_active:
            try:
                # Get current price
                current_price = await self._get_current_price(protection.symbol)

                # Calculate loss percentage
                loss_pct = await self._calculate_loss_pct(
                    protection.entry_price,
                    current_price,
                    side
                )

                # Check if emergency threshold exceeded
                if loss_pct > protection.emergency_threshold_pct:
                    logger.critical(
                        f"🚨 Layer 3 (EMERGENCY) triggered for {protection.symbol}: "
                        f"Loss {loss_pct:.1%} exceeds threshold {protection.emergency_threshold_pct:.1%}"
                    )

                    # Emergency close
                    await self._emergency_close(protection)

                    # Deactivate monitoring
                    protection.emergency_monitor_active = False
                    protection.triggered_layer = ProtectionLayer.EMERGENCY
                    protection.triggered_at = datetime.now(timezone.utc)

                    # Send alert
                    await self._send_emergency_alert(protection, loss_pct)

                    break

                # Update last check time
                protection.last_check_at = datetime.now(timezone.utc)

                # Wait before next check (faster for emergency)
                await asyncio.sleep(self.emergency_check_interval)

            except asyncio.CancelledError:
                logger.info(f"Emergency monitor cancelled for {protection.symbol}")
                break
            except Exception as e:
                logger.error(f"Error in emergency monitor: {e}")
                await asyncio.sleep(self.emergency_check_interval)

    async def stop_protection(self, position_id: str):
        """
        Stop all protection layers for a position

        Args:
            position_id: Position identifier
        """
        if position_id not in self.protections:
            logger.warning(f"No protection found for position {position_id}")
            return

        protection = self.protections[position_id]

        logger.info(f"Stopping protection for {protection.symbol}")

        # Cancel exchange stop order
        if protection.exchange_stop_active and protection.exchange_stop_order_id:
            try:
                await self.exchange.cancel_order(
                    protection.exchange_stop_order_id,
                    protection.symbol
                )
                protection.exchange_stop_active = False
            except Exception as e:
                logger.error(f"Failed to cancel exchange stop: {e}")

        # Stop app monitor
        if protection.app_monitor_active:
            protection.app_monitor_active = False
            if position_id in self.monitor_tasks:
                self.monitor_tasks[position_id].cancel()
                del self.monitor_tasks[position_id]

        # Stop emergency monitor
        if protection.emergency_monitor_active:
            protection.emergency_monitor_active = False

        # Remove protection
        del self.protections[position_id]

        logger.info(f"Protection stopped for {protection.symbol}")

    async def _get_current_price(self, symbol: str) -> Decimal:
        """Get current market price for symbol"""
        if not self.exchange:
            raise ValueError("No exchange client available")

        ticker = await self.exchange.fetch_ticker(symbol)
        return Decimal(str(ticker["last"]))

    def _should_trigger_stop(
        self,
        current_price: Decimal,
        stop_price: Decimal,
        side: str
    ) -> bool:
        """Check if stop-loss should trigger"""
        if side == "long":
            return current_price <= stop_price
        else:
            return current_price >= stop_price

    async def _calculate_loss_pct(
        self,
        entry_price: Decimal,
        current_price: Decimal,
        side: str
    ) -> Decimal:
        """Calculate loss percentage"""
        if side == "long":
            loss = entry_price - current_price
        else:
            loss = current_price - entry_price

        return (loss / entry_price).abs()

    async def _close_position_market(self, protection: Protection):
        """Close position at market (Layer 2)"""
        if not self.trade_executor:
            logger.error("No trade executor available for position closure")
            return

        try:
            logger.warning(f"Closing {protection.symbol} position at market (Layer 2)")

            await self.trade_executor.close_position(
                position_id=protection.position_id,
                reason="stop_loss_triggered_layer2",
            )

            logger.info(f"Position {protection.symbol} closed successfully (Layer 2)")

        except Exception as e:
            logger.error(f"Failed to close position: {e}")
            raise

    async def _emergency_close(self, protection: Protection):
        """Emergency position close (Layer 3)"""
        if not self.trade_executor:
            logger.critical("No trade executor available for emergency closure!")
            return

        try:
            logger.critical(
                f"🚨 EMERGENCY CLOSE: {protection.symbol} position {protection.position_id}"
            )

            await self.trade_executor.close_position(
                position_id=protection.position_id,
                reason="emergency_liquidation_layer3",
                force=True,  # Force immediate closure
            )

            logger.critical(
                f"Emergency close completed for {protection.symbol}"
            )

        except Exception as e:
            logger.critical(f"EMERGENCY CLOSE FAILED: {e}")
            raise

    async def _send_emergency_alert(self, protection: Protection, loss_pct: Decimal):
        """Send emergency alert"""
        # In production, this would send email/SMS/Telegram alerts
        logger.critical(
            f"📧 EMERGENCY ALERT: Position {protection.symbol} "
            f"closed at {loss_pct:.1%} loss (threshold: {protection.emergency_threshold_pct:.1%})"
        )

    def get_protection(self, position_id: str) -> Optional[Protection]:
        """Get protection status for a position"""
        return self.protections.get(position_id)

    def get_all_protections(self) -> Dict[str, Protection]:
        """Get all active protections"""
        return self.protections.copy()


# Export
__all__ = ["StopLossManager"]
