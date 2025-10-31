"""
Stop-Loss Protection Manager

Implements 3-layer stop-loss protection system for risk management:
- Layer 1: Exchange stop-loss order (primary protection)
- Layer 2: Application-level monitoring (secondary, polls every 2 seconds)
- Layer 3: Emergency liquidation (tertiary, polls every 1 second, triggers at 15% loss)

Author: Trade Executor Implementation Team
Date: 2025-10-27
"""

import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional
from uuid import UUID

from workspace.features.position_manager import PositionService
from workspace.shared.database.connection import get_pool

from .executor_service import TradeExecutor
from .models import OrderSide, StopLossLayer, StopLossProtection

logger = logging.getLogger(__name__)


class StopLossManager:
    """
    3-Layer Stop-Loss Protection System

    Provides comprehensive stop-loss protection through multiple layers:

    Layer 1 (Exchange): Stop-loss order placed on exchange
        - Primary protection mechanism
        - Executed by exchange automatically
        - Lowest latency response

    Layer 2 (Application): Price monitoring and market order execution
        - Backup if Layer 1 fails
        - Monitors price every 2 seconds
        - Executes market order if stop triggered

    Layer 3 (Emergency): Emergency liquidation for severe losses
        - Last resort protection
        - Monitors every 1 second
        - Triggers at 15% loss (emergency threshold)
        - Alerts sent immediately

    Attributes:
        executor: Trade Executor service
        position_service: Position Manager service
        layer2_interval: Layer 2 monitoring interval (seconds)
        layer3_interval: Layer 3 monitoring interval (seconds)
        emergency_threshold: Emergency loss threshold (default: 15%)
    """

    def __init__(
        self,
        executor: TradeExecutor,
        position_service: Optional[PositionService] = None,
        layer2_interval: float = 2.0,
        layer3_interval: float = 1.0,
        emergency_threshold: Decimal = Decimal("0.15"),
    ):
        """
        Initialize Stop-Loss Manager

        Args:
            executor: Trade Executor instance for order placement
            position_service: Position Manager instance
            layer2_interval: Layer 2 monitoring interval (seconds)
            layer3_interval: Layer 3 monitoring interval (seconds)
            emergency_threshold: Emergency loss threshold (15% = 0.15)
        """
        self.executor = executor
        self.position_service = position_service
        self._position_service_provided = position_service is not None
        self.layer2_interval = layer2_interval
        self.layer3_interval = layer3_interval
        self.emergency_threshold = emergency_threshold

        # Track active protections
        self.active_protections: Dict[str, StopLossProtection] = {}

        # Track monitoring tasks
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}

    async def start_protection(
        self,
        position_id: str,
        stop_price: Decimal,
    ) -> StopLossProtection:
        """
        Start 3-layer stop-loss protection for a position

        Args:
            position_id: Position ID to protect
            stop_price: Stop-loss trigger price

        Returns:
            StopLossProtection object with protection details

        Example:
            ```python
            protection = await stop_loss_manager.start_protection(
                position_id='pos-123',
                stop_price=Decimal('89000.00')
            )
            print(f"Protection started: Layer 1 order {protection.layer1_order_id}")
            ```
        """
        try:
            # Initialize PositionService if not provided
            if not self._position_service_provided:
                pool = await get_pool()
                self.position_service = PositionService(pool=pool)
                logger.info(
                    "StopLossManager: PositionService initialized with global pool"
                )
                self._position_service_provided = True  # Only initialize once

            # Get position details
            if self.position_service is None:
                raise RuntimeError("Position service not initialized")
            position_uuid = UUID(position_id)
            position = await self.position_service.get_position_by_id(position_uuid)
            if not position:
                raise ValueError(f"Position {position_id} not found")

            logger.info(
                f"Starting 3-layer stop-loss protection for position {position_id} "
                f"(stop price: {stop_price})"
            )

            # Create protection object
            protection = StopLossProtection(
                position_id=position_id,
                stop_price=stop_price,
            )

            # Layer 1: Place exchange stop-loss order
            layer1_result = await self._place_layer1_stop(position, stop_price)
            if layer1_result:
                protection.layer1_order_id = layer1_result.order.exchange_order_id
                protection.layer1_status = layer1_result.order.status
                logger.info(f"Layer 1 protection active: {protection.layer1_order_id}")
            else:
                logger.warning(f"Layer 1 protection failed for position {position_id}")

            # Layer 2: Start application-level monitoring
            protection.layer2_active = True
            layer2_task = asyncio.create_task(
                self._monitor_layer2(position, stop_price, protection)
            )
            self.monitoring_tasks[f"{position_id}_layer2"] = layer2_task
            logger.info(f"Layer 2 monitoring started for position {position_id}")

            # Layer 3: Start emergency monitoring
            protection.layer3_active = True
            layer3_task = asyncio.create_task(
                self._monitor_layer3(position, protection)
            )
            self.monitoring_tasks[f"{position_id}_layer3"] = layer3_task
            logger.info(
                f"Layer 3 emergency monitoring started for position {position_id}"
            )

            # Store protection
            await self._store_protection(protection)
            self.active_protections[position_id] = protection

            logger.info(
                f"3-layer stop-loss protection fully activated for position {position_id}"
            )

            return protection

        except Exception as e:
            logger.error(f"Error starting stop-loss protection: {e}", exc_info=True)
            raise

    async def stop_protection(self, position_id: str):
        """
        Stop all layers of protection for a position

        Args:
            position_id: Position ID
        """
        logger.info(f"Stopping all protection layers for position {position_id}")

        # Cancel monitoring tasks
        for task_key in [f"{position_id}_layer2", f"{position_id}_layer3"]:
            if task_key in self.monitoring_tasks:
                task = self.monitoring_tasks[task_key]
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                del self.monitoring_tasks[task_key]

        # Remove from active protections
        if position_id in self.active_protections:
            del self.active_protections[position_id]

        logger.info(f"All protection stopped for position {position_id}")

    async def _place_layer1_stop(self, position, stop_price: Decimal):
        """
        Place Layer 1 exchange stop-loss order

        Args:
            position: Position object
            stop_price: Stop trigger price

        Returns:
            ExecutionResult or None if failed
        """
        try:
            # Determine order side (opposite of position)
            order_side = OrderSide.SELL if position.side == "long" else OrderSide.BUY

            # Place stop-market order with reduceOnly=True
            result = await self.executor.create_stop_market_order(
                symbol=position.symbol,
                side=order_side,
                quantity=position.quantity,
                stop_price=stop_price,
                reduce_only=True,  # CRITICAL: Only close position, don't open opposite
                position_id=position.id,
                metadata={"layer": "layer1", "protection_type": "stop_loss"},
            )

            if result.success:
                if result.order is not None:
                    logger.info(
                        f"Layer 1 stop-loss order placed: {result.order.exchange_order_id} "
                        f"(trigger: {stop_price})"
                    )
                else:
                    logger.info(
                        f"Layer 1 stop-loss order placed (trigger: {stop_price})"
                    )
                return result
            else:
                logger.error(
                    f"Failed to place Layer 1 stop-loss: {result.error_message}"
                )
                return None

        except Exception as e:
            logger.error(f"Error placing Layer 1 stop-loss: {e}", exc_info=True)
            return None

    async def _monitor_layer2(
        self,
        position,
        stop_price: Decimal,
        protection: StopLossProtection,
    ):
        """
        Layer 2: Application-level stop-loss monitoring

        Monitors price every 2 seconds and executes market order if stop triggered.

        Args:
            position: Position object
            stop_price: Stop trigger price
            protection: StopLossProtection object
        """
        logger.info(
            f"Layer 2 monitoring started for {position.id} "
            f"(interval: {self.layer2_interval}s)"
        )

        try:
            while True:
                await asyncio.sleep(self.layer2_interval)

                # Check if position still exists
                if self.position_service is None:
                    raise RuntimeError("Position service not initialized")
                current_position = await self.position_service.get_position_by_id(
                    position.id
                )
                if not current_position or current_position.status != "open":
                    logger.info(
                        f"Layer 2: Position {position.id} no longer open, stopping monitoring"
                    )
                    break

                # Fetch current price
                try:
                    ticker = await self.executor.exchange.fetch_ticker(position.symbol)
                    current_price = Decimal(str(ticker["last"]))
                except Exception as e:
                    logger.warning(
                        f"Layer 2: Failed to fetch price for {position.symbol}: {e}"
                    )
                    continue

                # Check if stop-loss should trigger
                should_trigger = False
                if position.side == "long" and current_price <= stop_price:
                    should_trigger = True
                elif position.side == "short" and current_price >= stop_price:
                    should_trigger = True

                if should_trigger:
                    logger.warning(
                        f"Layer 2 TRIGGERED for {position.id}: "
                        f"Current price {current_price} crossed stop {stop_price}"
                    )

                    # Execute market order to close position
                    close_result = await self.executor.close_position(
                        position_id=position.id,
                        reason="layer2_stop_loss_triggered",
                    )

                    if close_result.success:
                        if close_result.order is not None:
                            logger.info(
                                f"Layer 2: Position {position.id} closed successfully "
                                f"(Order: {close_result.order.exchange_order_id})"
                            )
                        else:
                            logger.info(
                                f"Layer 2: Position {position.id} closed successfully"
                            )

                        # Update protection
                        protection.triggered_at = datetime.utcnow()
                        protection.triggered_layer = StopLossLayer.APPLICATION
                        await self._update_protection(protection)

                        # Stop all monitoring
                        await self.stop_protection(position.id)
                        break
                    else:
                        logger.error(
                            f"Layer 2: Failed to close position {position.id}: "
                            f"{close_result.error_message}"
                        )
                        # Continue monitoring, Layer 3 will catch it if critical

        except asyncio.CancelledError:
            logger.info(f"Layer 2 monitoring cancelled for {position.id}")
        except Exception as e:
            logger.error(f"Layer 2 monitoring error: {e}", exc_info=True)

    async def _monitor_layer3(self, position, protection: StopLossProtection):
        """
        Layer 3: Emergency liquidation monitoring

        Monitors every 1 second and triggers emergency close if loss exceeds 15%.

        Args:
            position: Position object
            protection: StopLossProtection object
        """
        logger.info(
            f"Layer 3 emergency monitoring started for {position.id} "
            f"(interval: {self.layer3_interval}s, threshold: {self.emergency_threshold * 100:.0f}%)"
        )

        try:
            while True:
                await asyncio.sleep(self.layer3_interval)

                # Check if position still exists
                if self.position_service is None:
                    raise RuntimeError("Position service not initialized")
                current_position = await self.position_service.get_position_by_id(
                    position.id
                )
                if not current_position or current_position.status != "open":
                    logger.info(
                        f"Layer 3: Position {position.id} no longer open, stopping monitoring"
                    )
                    break

                # Fetch current price
                try:
                    ticker = await self.executor.exchange.fetch_ticker(position.symbol)
                    current_price = Decimal(str(ticker["last"]))
                except Exception as e:
                    logger.warning(f"Layer 3: Failed to fetch price: {e}")
                    continue

                # Calculate current loss percentage
                if position.side == "long":
                    loss_pct = (
                        position.entry_price - current_price
                    ) / position.entry_price
                else:  # short
                    loss_pct = (
                        current_price - position.entry_price
                    ) / position.entry_price

                # Check if emergency threshold exceeded
                if loss_pct > self.emergency_threshold:
                    logger.critical(
                        f"Layer 3 EMERGENCY TRIGGERED for {position.id}: "
                        f"Loss {loss_pct * 100:.2f}% exceeds threshold {self.emergency_threshold * 100:.0f}%"
                    )

                    # Send alert (placeholder for now)
                    await self._send_emergency_alert(
                        position.id,
                        loss_pct,
                        current_price,
                    )

                    # Emergency close position
                    close_result = await self.executor.close_position(
                        position_id=position.id,
                        reason="layer3_emergency_liquidation",
                    )

                    if close_result.success:
                        if close_result.order is not None:
                            logger.critical(
                                f"Layer 3: EMERGENCY CLOSE successful for {position.id} "
                                f"(Order: {close_result.order.exchange_order_id})"
                            )
                        else:
                            logger.critical(
                                f"Layer 3: EMERGENCY CLOSE successful for {position.id}"
                            )

                        # Update protection
                        protection.triggered_at = datetime.utcnow()
                        protection.triggered_layer = StopLossLayer.EMERGENCY
                        await self._update_protection(protection)

                        # Stop all monitoring
                        await self.stop_protection(position.id)
                        break
                    else:
                        logger.critical(
                            f"Layer 3: EMERGENCY CLOSE FAILED for {position.id}: "
                            f"{close_result.error_message}"
                        )
                        # Try again next iteration

        except asyncio.CancelledError:
            logger.info(f"Layer 3 monitoring cancelled for {position.id}")
        except Exception as e:
            logger.error(f"Layer 3 monitoring error: {e}", exc_info=True)

    async def _send_emergency_alert(
        self,
        position_id: str,
        loss_pct: Decimal,
        current_price: Decimal,
    ):
        """Send emergency alert (placeholder)"""
        alert_message = (
            f"EMERGENCY: Position {position_id} loss {loss_pct * 100:.2f}% "
            f"(price: {current_price})"
        )
        logger.critical(f"ALERT: {alert_message}")
        # TODO: Integrate with alerting system (email, SMS, Slack, etc.)

    async def _store_protection(self, protection: StopLossProtection):
        """Store stop-loss protection in database"""
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO stop_loss_protections (
                        position_id, layer1_order_id, layer1_status,
                        layer2_active, layer3_active, stop_price,
                        created_at, triggered_at, triggered_layer, metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    """,
                    protection.position_id,
                    protection.layer1_order_id,
                    protection.layer1_status.value,
                    protection.layer2_active,
                    protection.layer3_active,
                    protection.stop_price,
                    protection.created_at,
                    protection.triggered_at,
                    (
                        protection.triggered_layer.value
                        if protection.triggered_layer
                        else None
                    ),
                    protection.metadata,
                )
            logger.debug(f"Stop-loss protection stored: {protection.position_id}")

        except Exception as e:
            logger.error(f"Error storing protection: {e}", exc_info=True)

    async def _update_protection(self, protection: StopLossProtection):
        """Update stop-loss protection in database"""
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE stop_loss_protections SET
                        triggered_at = $1,
                        triggered_layer = $2,
                        metadata = $3
                    WHERE position_id = $4
                    """,
                    protection.triggered_at,
                    (
                        protection.triggered_layer.value
                        if protection.triggered_layer
                        else None
                    ),
                    protection.metadata,
                    protection.position_id,
                )
            logger.debug(f"Stop-loss protection updated: {protection.position_id}")

        except Exception as e:
            logger.error(f"Error updating protection: {e}", exc_info=True)


# Export
__all__ = ["StopLossManager"]
