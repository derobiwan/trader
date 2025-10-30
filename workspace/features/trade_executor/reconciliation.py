"""
Position Reconciliation Service

Ensures consistency between system positions and exchange positions.
Runs after every order execution and periodically (every 5 minutes).

Author: Trade Executor Implementation Team
Date: 2025-10-27
"""

import asyncio
import logging
from decimal import Decimal
from typing import List, Dict, Optional

import ccxt.async_support as ccxt

from .models import (
    ReconciliationResult,
    PositionSnapshot,
)
from workspace.features.position_manager import PositionService
from workspace.shared.database.connection import DatabasePool


logger = logging.getLogger(__name__)


class ReconciliationService:
    """
    Position Reconciliation Service

    Compares system positions with exchange positions and corrects
    discrepancies. Critical for handling partial fills, exchange errors,
    and maintaining accurate position state.

    Reconciliation Triggers:
    - After every order execution
    - Periodically every 5 minutes
    - On-demand via manual trigger

    Attributes:
        exchange: ccxt exchange instance
        position_service: Position Manager service
        periodic_interval: Interval for periodic reconciliation (seconds)
        discrepancy_threshold: Minimum discrepancy to trigger correction
    """

    def __init__(
        self,
        exchange: ccxt.Exchange,
        position_service: Optional[PositionService] = None,
        periodic_interval: int = 300,  # 5 minutes
        discrepancy_threshold: Decimal = Decimal("0.00001"),
    ):
        """
        Initialize Reconciliation Service

        Args:
            exchange: ccxt exchange instance
            position_service: Position Manager instance
            periodic_interval: Periodic reconciliation interval (seconds)
            discrepancy_threshold: Minimum discrepancy to flag (0.001%)
        """
        self.exchange = exchange
        self.position_service = position_service or PositionService()
        self.periodic_interval = periodic_interval
        self.discrepancy_threshold = discrepancy_threshold

        # Periodic reconciliation task
        self.reconciliation_task: Optional[asyncio.Task] = None

    async def start_periodic_reconciliation(self):
        """Start periodic reconciliation task"""
        if self.reconciliation_task and not self.reconciliation_task.done():
            logger.warning("Periodic reconciliation already running")
            return

        logger.info(
            f"Starting periodic reconciliation (interval: {self.periodic_interval}s)"
        )

        self.reconciliation_task = asyncio.create_task(
            self._periodic_reconciliation_loop()
        )

    async def stop_periodic_reconciliation(self):
        """Stop periodic reconciliation task"""
        if self.reconciliation_task and not self.reconciliation_task.done():
            logger.info("Stopping periodic reconciliation")
            self.reconciliation_task.cancel()
            try:
                await self.reconciliation_task
            except asyncio.CancelledError:
                pass
            self.reconciliation_task = None

    async def reconcile_all_positions(self) -> List[ReconciliationResult]:
        """
        Reconcile all active positions

        Compares system positions with exchange positions and corrects
        any discrepancies found.

        Returns:
            List of ReconciliationResult objects
        """
        try:
            logger.info("Starting full position reconciliation")

            # Get all active positions from system
            system_positions = await self.position_service.get_active_positions()

            # Get all positions from exchange
            exchange_positions = await self._fetch_exchange_positions()

            # Create position maps
            system_map = {pos.symbol: pos for pos in system_positions}
            exchange_map = {pos["symbol"]: pos for pos in exchange_positions}

            results = []

            # Reconcile each system position
            for symbol, sys_pos in system_map.items():
                exch_pos = exchange_map.get(symbol)

                if exch_pos:
                    # Position exists on both sides - check quantity
                    result = await self._reconcile_position(
                        sys_pos,
                        exch_pos,
                    )
                    results.append(result)
                else:
                    # Position in system but not on exchange - flag as error
                    logger.error(
                        f"Position {sys_pos.id} exists in system but not on exchange: "
                        f"{symbol}"
                    )
                    result = ReconciliationResult(
                        position_id=sys_pos.id,
                        system_quantity=sys_pos.quantity,
                        exchange_quantity=Decimal("0"),
                        discrepancy=sys_pos.quantity,
                        needs_correction=True,
                    )
                    result.corrections_applied.append(
                        "Position not found on exchange - closing in system"
                    )
                    results.append(result)

                    # Close position in system
                    await self.position_service.close_position(
                        position_id=sys_pos.id,
                        close_price=sys_pos.current_price or sys_pos.entry_price,
                        reason="reconciliation_not_on_exchange",
                    )

            # Check for positions on exchange but not in system
            for symbol, exch_pos in exchange_map.items():
                if symbol not in system_map:
                    logger.warning(
                        f"Position exists on exchange but not in system: {symbol} "
                        f"(quantity: {exch_pos['contracts']})"
                    )
                    # This is unusual - manual intervention may be needed

            logger.info(
                f"Reconciliation complete: {len(results)} positions checked, "
                f"{sum(1 for r in results if r.needs_correction)} discrepancies found"
            )

            return results

        except Exception as e:
            logger.error(f"Error during reconciliation: {e}", exc_info=True)
            return []

    async def reconcile_position(
        self, position_id: str
    ) -> Optional[ReconciliationResult]:
        """
        Reconcile a specific position

        Args:
            position_id: Position ID to reconcile

        Returns:
            ReconciliationResult or None if position not found
        """
        try:
            # Get system position
            sys_pos = await self.position_service.get_position(position_id)
            if not sys_pos:
                logger.error(f"Position {position_id} not found in system")
                return None

            # Get exchange position
            exchange_positions = await self._fetch_exchange_positions()
            exch_pos = next(
                (p for p in exchange_positions if p["symbol"] == sys_pos.symbol), None
            )

            if not exch_pos:
                logger.error(
                    f"Position {position_id} ({sys_pos.symbol}) not found on exchange"
                )
                return ReconciliationResult(
                    position_id=position_id,
                    system_quantity=sys_pos.quantity,
                    exchange_quantity=Decimal("0"),
                    discrepancy=sys_pos.quantity,
                    needs_correction=True,
                )

            # Reconcile
            result = await self._reconcile_position(sys_pos, exch_pos)
            return result

        except Exception as e:
            logger.error(
                f"Error reconciling position {position_id}: {e}", exc_info=True
            )
            return None

    async def _reconcile_position(
        self,
        sys_pos,
        exch_pos: Dict,
    ) -> ReconciliationResult:
        """
        Reconcile a single position

        Args:
            sys_pos: System position object
            exch_pos: Exchange position dict

        Returns:
            ReconciliationResult
        """
        # Extract quantities
        system_quantity = sys_pos.quantity
        exchange_quantity = Decimal(str(exch_pos["contracts"])).quantize(
            Decimal("0.00000001")
        )

        # Calculate discrepancy
        discrepancy = (system_quantity - exchange_quantity).quantize(
            Decimal("0.00000001")
        )
        abs_discrepancy = abs(discrepancy)

        # Create result
        result = ReconciliationResult(
            position_id=sys_pos.id,
            system_quantity=system_quantity,
            exchange_quantity=exchange_quantity,
            discrepancy=discrepancy,
        )

        # Check if correction needed (discrepancy > threshold)
        if abs_discrepancy > self.discrepancy_threshold:
            logger.warning(
                f"Discrepancy detected for {sys_pos.symbol}: "
                f"System={system_quantity}, Exchange={exchange_quantity}, "
                f"Diff={discrepancy}"
            )

            result.needs_correction = True

            # Apply correction - update system to match exchange
            try:
                # Update position quantity in database
                await self._update_position_quantity(
                    position_id=sys_pos.id,
                    new_quantity=exchange_quantity,
                )

                # Recalculate P&L with corrected quantity
                await self.position_service.update_position_price(
                    position_id=sys_pos.id,
                    current_price=sys_pos.current_price or sys_pos.entry_price,
                )

                result.corrections_applied.append(
                    f"Updated quantity from {system_quantity} to {exchange_quantity}"
                )

                logger.info(
                    f"Position {sys_pos.id} corrected: quantity updated to {exchange_quantity}"
                )

            except Exception as e:
                logger.error(f"Error applying correction: {e}", exc_info=True)
                result.corrections_applied.append(f"Correction failed: {e}")

        else:
            logger.debug(
                f"Position {sys_pos.symbol} reconciled: "
                f"No discrepancy (diff: {abs_discrepancy})"
            )

        # Store reconciliation result
        try:
            await self._store_reconciliation_result(result)
        except Exception as e:
            logger.error(f"Error storing reconciliation result: {e}", exc_info=True)
            # Continue even if storage fails - result is still valid

        return result

    async def _fetch_exchange_positions(self) -> List[Dict]:
        """
        Fetch all positions from exchange

        Returns:
            List of exchange position dicts
        """
        try:
            positions = await self.exchange.fetch_positions()

            # Filter to only open positions
            open_positions = [p for p in positions if float(p.get("contracts", 0)) != 0]

            logger.debug(f"Fetched {len(open_positions)} open positions from exchange")

            return open_positions

        except Exception as e:
            logger.error(f"Error fetching exchange positions: {e}", exc_info=True)
            return []

    async def _periodic_reconciliation_loop(self):
        """Periodic reconciliation loop"""
        logger.info("Periodic reconciliation loop started")

        try:
            while True:
                await asyncio.sleep(self.periodic_interval)

                logger.info("Running periodic reconciliation")
                results = await self.reconcile_all_positions()

                # Log summary
                discrepancies = sum(1 for r in results if r.needs_correction)
                if discrepancies > 0:
                    logger.warning(
                        f"Periodic reconciliation found {discrepancies} discrepancies"
                    )
                else:
                    logger.info("Periodic reconciliation: All positions in sync")

        except asyncio.CancelledError:
            logger.info("Periodic reconciliation loop cancelled")
        except Exception as e:
            logger.error(f"Error in periodic reconciliation loop: {e}", exc_info=True)

    async def _update_position_quantity(self, position_id: str, new_quantity: Decimal):
        """Update position quantity in database"""
        try:
            async with DatabasePool.get_connection() as conn:
                await conn.execute(
                    """
                    UPDATE positions
                    SET quantity = $1, updated_at = NOW()
                    WHERE id = $2
                    """,
                    new_quantity,
                    position_id,
                )
            logger.debug(f"Position {position_id} quantity updated to {new_quantity}")

        except Exception as e:
            logger.error(f"Error updating position quantity: {e}", exc_info=True)
            raise

    async def _store_reconciliation_result(self, result: ReconciliationResult):
        """Store reconciliation result in database"""
        try:
            async with DatabasePool.get_connection() as conn:
                await conn.execute(
                    """
                    INSERT INTO position_reconciliation (
                        position_id, system_quantity, exchange_quantity,
                        discrepancy, needs_correction, corrections_applied,
                        timestamp
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    result.position_id,
                    result.system_quantity,
                    result.exchange_quantity,
                    result.discrepancy,
                    result.needs_correction,
                    result.corrections_applied,
                    result.timestamp,
                )
            logger.debug(f"Reconciliation result stored for {result.position_id}")

        except Exception as e:
            logger.error(f"Error storing reconciliation result: {e}", exc_info=True)

    async def create_position_snapshot(
        self, position_id: str
    ) -> Optional[PositionSnapshot]:
        """
        Create a position snapshot for audit trail

        Args:
            position_id: Position ID

        Returns:
            PositionSnapshot or None if position not found
        """
        try:
            position = await self.position_service.get_position(position_id)
            if not position:
                return None

            snapshot = PositionSnapshot(
                position_id=position.id,
                symbol=position.symbol,
                side=position.side,
                quantity=position.quantity,
                entry_price=position.entry_price,
                current_price=position.current_price or position.entry_price,
                unrealized_pnl=position.pnl_chf,
            )

            # Store snapshot in database
            await self._store_position_snapshot(snapshot)

            return snapshot

        except Exception as e:
            logger.error(f"Error creating position snapshot: {e}", exc_info=True)
            return None

    async def _store_position_snapshot(self, snapshot: PositionSnapshot):
        """Store position snapshot in database"""
        try:
            async with DatabasePool.get_connection() as conn:
                await conn.execute(
                    """
                    INSERT INTO position_snapshots (
                        position_id, symbol, side, quantity,
                        entry_price, current_price, unrealized_pnl, timestamp
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    """,
                    snapshot.position_id,
                    snapshot.symbol,
                    snapshot.side,
                    snapshot.quantity,
                    snapshot.entry_price,
                    snapshot.current_price,
                    snapshot.unrealized_pnl,
                    snapshot.timestamp,
                )
            logger.debug(f"Position snapshot stored for {snapshot.position_id}")

        except Exception as e:
            logger.error(f"Error storing position snapshot: {e}", exc_info=True)


# Export
__all__ = ["ReconciliationService"]
