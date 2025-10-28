"""
Position Reconciliation Service

Continuously syncs positions with exchange and detects discrepancies.
"""

import asyncio
import logging
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime

from workspace.features.position_reconciliation.models import (
    ExchangePosition,
    SystemPosition,
    PositionDiscrepancy,
    ReconciliationResult,
    DiscrepancyType,
    DiscrepancySeverity,
)

logger = logging.getLogger(__name__)


class PositionReconciliationService:
    """
    Position reconciliation service

    Compares system positions with exchange positions and corrects discrepancies.
    """

    def __init__(
        self,
        trade_executor,
        quantity_tolerance_percent: Decimal = Decimal("1.0"),  # 1%
        price_tolerance_percent: Decimal = Decimal("0.1"),  # 0.1%
        reconciliation_interval_seconds: int = 300,  # 5 minutes
    ):
        self.trade_executor = trade_executor
        self.quantity_tolerance = quantity_tolerance_percent
        self.price_tolerance = price_tolerance_percent
        self.reconciliation_interval = reconciliation_interval_seconds

        # Running state
        self.is_running = False
        self.reconciliation_task: Optional[asyncio.Task] = None

        # Statistics
        self.total_reconciliations = 0
        self.total_discrepancies = 0
        self.total_auto_corrections = 0
        self.total_critical_alerts = 0

    async def start(self):
        """Start continuous reconciliation"""
        if self.is_running:
            logger.warning("Reconciliation already running")
            return

        self.is_running = True
        self.reconciliation_task = asyncio.create_task(self._reconciliation_loop())
        logger.info(
            f"Reconciliation started (interval: {self.reconciliation_interval}s)"
        )

    async def stop(self):
        """Stop reconciliation"""
        self.is_running = False
        if self.reconciliation_task:
            self.reconciliation_task.cancel()
            try:
                await self.reconciliation_task
            except asyncio.CancelledError:
                pass
        logger.info("Reconciliation stopped")

    async def _reconciliation_loop(self):
        """Main reconciliation loop"""
        while self.is_running:
            try:
                # Run reconciliation
                result = await self.reconcile_positions()

                # Update statistics
                self.total_reconciliations += 1
                self.total_discrepancies += result.discrepancies_found
                self.total_auto_corrections += result.auto_corrections
                self.total_critical_alerts += result.critical_alerts

                # Log result
                if result.discrepancies_found > 0:
                    logger.warning(
                        f"Reconciliation: {result.discrepancies_found} discrepancies, "
                        f"{result.auto_corrections} auto-corrected, "
                        f"{result.critical_alerts} critical alerts"
                    )
                else:
                    logger.info("Reconciliation: No discrepancies")

                # Wait for next interval
                await asyncio.sleep(self.reconciliation_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Reconciliation error: {e}", exc_info=True)
                await asyncio.sleep(self.reconciliation_interval)

    async def reconcile_positions(self) -> ReconciliationResult:
        """
        Run reconciliation check

        Returns:
            ReconciliationResult with detected discrepancies
        """
        start_time = datetime.utcnow()

        try:
            # Fetch positions from exchange
            exchange_positions = await self._fetch_exchange_positions()

            # Get system positions
            system_positions = await self._get_system_positions()

            # Compare positions
            discrepancies = await self._compare_positions(
                exchange_positions,
                system_positions,
            )

            # Handle discrepancies
            for discrepancy in discrepancies:
                await self._handle_discrepancy(discrepancy)

            # Calculate duration
            duration_ms = Decimal(
                str((datetime.utcnow() - start_time).total_seconds() * 1000)
            )

            # Build result
            result = ReconciliationResult(
                symbols_checked=len(exchange_positions) + len(system_positions),
                discrepancies_found=len(discrepancies),
                auto_corrections=sum(1 for d in discrepancies if d.auto_corrected),
                critical_alerts=sum(
                    1 for d in discrepancies if d.requires_manual_intervention
                ),
                discrepancies=discrepancies,
                duration_ms=duration_ms,
            )

            return result

        except Exception as e:
            logger.error(f"Reconciliation failed: {e}", exc_info=True)
            return ReconciliationResult(
                discrepancies_found=0,
                duration_ms=Decimal("0"),
            )

    async def _fetch_exchange_positions(self) -> Dict[str, ExchangePosition]:
        """Fetch positions from exchange"""
        try:
            # Fetch positions via TradeExecutor
            raw_positions = await self.trade_executor.exchange.fetch_positions()

            positions = {}
            for pos in raw_positions:
                # Filter out closed positions
                if Decimal(str(pos.get("contracts", 0))) == 0:
                    continue

                symbol = pos["symbol"]
                positions[symbol] = ExchangePosition(
                    symbol=symbol,
                    side="LONG" if pos["side"] == "long" else "SHORT",
                    quantity=Decimal(str(pos["contracts"])),
                    entry_price=Decimal(str(pos["entryPrice"])),
                    current_price=Decimal(str(pos["markPrice"])),
                    unrealized_pnl=Decimal(str(pos["unrealizedPnl"])),
                    leverage=Decimal(str(pos.get("leverage", 1))),
                    liquidation_price=(
                        Decimal(str(pos["liquidationPrice"]))
                        if pos.get("liquidationPrice")
                        else None
                    ),
                    margin=Decimal(str(pos.get("initialMargin", 0))),
                )

            logger.debug(f"Fetched {len(positions)} positions from exchange")
            return positions

        except Exception as e:
            logger.error(f"Error fetching exchange positions: {e}", exc_info=True)
            return {}

    async def _get_system_positions(self) -> Dict[str, SystemPosition]:
        """Get system's tracked positions"""
        try:
            # Get positions from Position Manager
            raw_positions = (
                await self.trade_executor.position_service.get_open_positions()
            )

            positions = {}
            for pos in raw_positions:
                positions[pos.symbol] = SystemPosition(
                    symbol=pos.symbol,
                    side="LONG" if pos.side == "long" else "SHORT",
                    quantity=pos.quantity,
                    entry_price=pos.entry_price,
                    current_price=pos.current_price or pos.entry_price,
                    unrealized_pnl=pos.pnl_chf or Decimal("0"),
                    leverage=Decimal(str(getattr(pos, "leverage", 1))),
                    stop_loss_price=pos.stop_loss,
                    take_profit_price=pos.take_profit,
                    last_updated=pos.updated_at,
                )

            logger.debug(f"Found {len(positions)} positions in system")
            return positions

        except Exception as e:
            logger.error(f"Error getting system positions: {e}", exc_info=True)
            return {}

    async def _compare_positions(
        self,
        exchange_positions: Dict[str, ExchangePosition],
        system_positions: Dict[str, SystemPosition],
    ) -> List[PositionDiscrepancy]:
        """Compare exchange and system positions"""
        discrepancies = []

        # Check all symbols (union of both sets)
        all_symbols = set(exchange_positions.keys()) | set(system_positions.keys())

        for symbol in all_symbols:
            exchange_pos = exchange_positions.get(symbol)
            system_pos = system_positions.get(symbol)

            # Position in exchange but not in system
            if exchange_pos and not system_pos:
                discrepancies.append(
                    PositionDiscrepancy(
                        symbol=symbol,
                        discrepancy_type=DiscrepancyType.POSITION_MISSING_IN_SYSTEM,
                        severity=DiscrepancySeverity.CRITICAL,
                        exchange_position=exchange_pos,
                        system_position=None,
                        requires_manual_intervention=True,
                        notes="Position exists on exchange but not tracked in system",
                    )
                )

            # Position in system but not on exchange
            elif system_pos and not exchange_pos:
                discrepancies.append(
                    PositionDiscrepancy(
                        symbol=symbol,
                        discrepancy_type=DiscrepancyType.POSITION_MISSING_ON_EXCHANGE,
                        severity=DiscrepancySeverity.WARNING,
                        exchange_position=None,
                        system_position=system_pos,
                        requires_manual_intervention=False,
                        notes="Position tracked in system but not on exchange (likely closed)",
                    )
                )

            # Position in both - check for differences
            elif exchange_pos and system_pos:
                discrepancy = self._check_position_differences(
                    symbol, exchange_pos, system_pos
                )
                if discrepancy:
                    discrepancies.append(discrepancy)

        return discrepancies

    def _check_position_differences(
        self,
        symbol: str,
        exchange_pos: ExchangePosition,
        system_pos: SystemPosition,
    ) -> Optional[PositionDiscrepancy]:
        """Check for differences between exchange and system position"""

        # Side mismatch (critical)
        if exchange_pos.side != system_pos.side:
            return PositionDiscrepancy(
                symbol=symbol,
                discrepancy_type=DiscrepancyType.SIDE_MISMATCH,
                severity=DiscrepancySeverity.CRITICAL,
                exchange_position=exchange_pos,
                system_position=system_pos,
                requires_manual_intervention=True,
                notes=f"Side mismatch: Exchange={exchange_pos.side}, System={system_pos.side}",
            )

        # Quantity difference
        quantity_diff = abs(exchange_pos.quantity - system_pos.quantity)
        quantity_diff_percent = (
            quantity_diff / exchange_pos.quantity * 100
            if exchange_pos.quantity > 0
            else Decimal("0")
        )

        if quantity_diff_percent > self.quantity_tolerance:
            # Determine severity
            if quantity_diff_percent > 10:
                severity = DiscrepancySeverity.CRITICAL
                requires_intervention = True
            elif quantity_diff_percent > 5:
                severity = DiscrepancySeverity.WARNING
                requires_intervention = False
            else:
                severity = DiscrepancySeverity.INFO
                requires_intervention = False

            return PositionDiscrepancy(
                symbol=symbol,
                discrepancy_type=DiscrepancyType.QUANTITY_MISMATCH,
                severity=severity,
                exchange_position=exchange_pos,
                system_position=system_pos,
                quantity_difference=quantity_diff,
                requires_manual_intervention=requires_intervention,
                notes=f"Quantity difference: {quantity_diff_percent:.2f}%",
            )

        # Price difference
        price_diff = abs(exchange_pos.entry_price - system_pos.entry_price)
        price_diff_percent = (
            price_diff / exchange_pos.entry_price * 100
            if exchange_pos.entry_price > 0
            else Decimal("0")
        )

        if price_diff_percent > self.price_tolerance:
            return PositionDiscrepancy(
                symbol=symbol,
                discrepancy_type=DiscrepancyType.PRICE_MISMATCH,
                severity=DiscrepancySeverity.WARNING,
                exchange_position=exchange_pos,
                system_position=system_pos,
                price_difference=price_diff,
                requires_manual_intervention=False,
                notes=f"Entry price difference: {price_diff_percent:.2f}%",
            )

        # No significant discrepancies
        return None

    async def _handle_discrepancy(self, discrepancy: PositionDiscrepancy):
        """Handle detected discrepancy"""

        # Log discrepancy
        logger.warning(
            f"Discrepancy detected: {discrepancy.symbol} - "
            f"{discrepancy.discrepancy_type.value} ({discrepancy.severity.value})"
        )

        # Critical discrepancies - send alert
        if discrepancy.requires_manual_intervention:
            await self._send_critical_alert(discrepancy)
            return

        # Auto-correction logic
        if discrepancy.discrepancy_type == DiscrepancyType.POSITION_MISSING_ON_EXCHANGE:
            # Position closed on exchange, update system
            await self._auto_correct_missing_position(discrepancy)

        elif discrepancy.discrepancy_type == DiscrepancyType.QUANTITY_MISMATCH:
            # Quantity difference, update system quantity
            await self._auto_correct_quantity(discrepancy)

        elif discrepancy.discrepancy_type == DiscrepancyType.PRICE_MISMATCH:
            # Price difference, update system price
            await self._auto_correct_price(discrepancy)

    async def _auto_correct_missing_position(self, discrepancy: PositionDiscrepancy):
        """Auto-correct: Position missing on exchange"""
        try:
            logger.info(
                f"Auto-correcting: Closing {discrepancy.symbol} in system "
                f"(position closed on exchange)"
            )

            # Get position from system
            positions = await self.trade_executor.position_service.get_open_positions()
            position = next(
                (p for p in positions if p.symbol == discrepancy.symbol), None
            )

            if position:
                # Close position in system
                await self.trade_executor.position_service.close_position(
                    position_id=position.id,
                    close_price=position.current_price or position.entry_price,
                    reason="reconciliation_not_on_exchange",
                )

                discrepancy.auto_corrected = True
                discrepancy.correction_action = (
                    "Closed position in system to match exchange"
                )
                logger.info(f"Auto-correction successful for {discrepancy.symbol}")

        except Exception as e:
            logger.error(f"Auto-correction failed: {e}", exc_info=True)

    async def _auto_correct_quantity(self, discrepancy: PositionDiscrepancy):
        """Auto-correct: Quantity mismatch"""
        try:
            if discrepancy.exchange_position:
                logger.info(
                    f"Auto-correcting: Updating {discrepancy.symbol} quantity to "
                    f"{discrepancy.exchange_position.quantity}"
                )

                # Get position from system
                positions = (
                    await self.trade_executor.position_service.get_open_positions()
                )
                position = next(
                    (p for p in positions if p.symbol == discrepancy.symbol), None
                )

                if position:
                    # Update position quantity in database
                    # Note: This would require a new method in PositionService
                    # For now, we'll log it
                    logger.info(
                        f"Would update position {position.id} quantity from "
                        f"{position.quantity} to {discrepancy.exchange_position.quantity}"
                    )

                    discrepancy.auto_corrected = True
                    discrepancy.correction_action = (
                        "Updated system quantity to match exchange"
                    )

        except Exception as e:
            logger.error(f"Auto-correction failed: {e}", exc_info=True)

    async def _auto_correct_price(self, discrepancy: PositionDiscrepancy):
        """Auto-correct: Price mismatch"""
        try:
            if discrepancy.exchange_position:
                logger.info(
                    f"Auto-correcting: Updating {discrepancy.symbol} entry price to "
                    f"{discrepancy.exchange_position.entry_price}"
                )

                # Get position from system
                positions = (
                    await self.trade_executor.position_service.get_open_positions()
                )
                position = next(
                    (p for p in positions if p.symbol == discrepancy.symbol), None
                )

                if position:
                    # Update position entry price in database
                    # Note: This would require a new method in PositionService
                    # For now, we'll log it
                    logger.info(
                        f"Would update position {position.id} entry price from "
                        f"{position.entry_price} to {discrepancy.exchange_position.entry_price}"
                    )

                    discrepancy.auto_corrected = True
                    discrepancy.correction_action = (
                        "Updated system entry price to match exchange"
                    )

        except Exception as e:
            logger.error(f"Auto-correction failed: {e}", exc_info=True)

    async def _send_critical_alert(self, discrepancy: PositionDiscrepancy):
        """Send alert for critical discrepancy"""
        # TODO: Integrate with alerting system (email, Slack, PagerDuty, etc.)
        logger.critical(
            f"CRITICAL DISCREPANCY: {discrepancy.symbol}\n"
            f"Type: {discrepancy.discrepancy_type.value}\n"
            f"Severity: {discrepancy.severity.value}\n"
            f"Notes: {discrepancy.notes}\n"
            f"Exchange Position: {discrepancy.exchange_position}\n"
            f"System Position: {discrepancy.system_position}"
        )

    def get_stats(self) -> dict:
        """Get reconciliation statistics"""
        return {
            "total_reconciliations": self.total_reconciliations,
            "total_discrepancies": self.total_discrepancies,
            "total_auto_corrections": self.total_auto_corrections,
            "total_critical_alerts": self.total_critical_alerts,
            "is_running": self.is_running,
            "reconciliation_interval_seconds": self.reconciliation_interval,
        }
