"""
Position Management Service

Core service for managing trading position lifecycle including creation,
updates, P&L tracking, stop-loss monitoring, and closure.

This is the critical path service that all trading logic depends on.
All position operations go through this service to ensure consistency,
validation, and proper risk management.

Key Responsibilities:
- Create positions with risk validation
- Update position prices and P&L in real-time
- Monitor stop-loss and take-profit triggers
- Close positions with final P&L calculation
- Track daily P&L for circuit breaker
- Calculate total exposure across all positions
- Audit all position changes

Usage:
    from workspace.features.position_manager.position_service import PositionService
    from workspace.shared.database.connection import init_pool

    # Initialize database pool
    pool = await init_pool(
        host="localhost",
        database="trading_system",
        user="postgres",
        password="secure_password"
    )

    # Create service
    service = PositionService(pool)

    # Create position
    position = await service.create_position(
        symbol="BTCUSDT",
        side="LONG",
        quantity=Decimal("0.01"),
        entry_price=Decimal("45000.00"),
        leverage=10,
        stop_loss=Decimal("44000.00")
    )

    # Update price
    updated = await service.update_position_price(
        position_id=position.id,
        current_price=Decimal("45500.00")
    )

    # Check stop losses
    triggered = await service.check_stop_loss_triggers()

    # Close position
    closed = await service.close_position(
        position_id=position.id,
        close_price=Decimal("45500.00"),
        reason="take_profit"
    )
"""

import asyncio
import logging
from datetime import date as Date
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID, uuid4

import asyncpg

from workspace.features.position_manager.models import (
    CIRCUIT_BREAKER_LOSS_CHF,
    USD_CHF_RATE,
    CloseReason,
    DailyPnLSummary,
    PositionCreateRequest,
    PositionNotFoundError,
    PositionStatistics,
    PositionWithPnL,
    RiskLimitError,
    ValidationError,
)
from workspace.shared.database.connection import DatabasePool
from workspace.shared.database.models import (
    Position,
    PositionSide,
    PositionStatus,
    usd_to_chf,
)

logger = logging.getLogger(__name__)


class PositionService:
    """
    Position management service with full lifecycle support.

    Handles all position operations with validation, risk management,
    and comprehensive audit logging.

    Attributes:
        pool: Database connection pool
        _max_retries: Maximum retry attempts for database operations
    """

    def __init__(self, pool: DatabasePool, max_retries: int = 3):
        """
        Initialize position service.

        Args:
            pool: Database connection pool
            max_retries: Maximum retry attempts (default: 3)
        """
        self.pool = pool
        self._max_retries = max_retries
        logger.info("PositionService initialized")

    # ========================================================================
    # Position Creation
    # ========================================================================

    async def create_position(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        entry_price: Decimal,
        leverage: int,
        stop_loss: Decimal,
        take_profit: Optional[Decimal] = None,
        signal_id: Optional[UUID] = None,
        notes: Optional[str] = None,
    ) -> PositionWithPnL:
        """
        Create a new trading position with full validation.

        Validates:
        - Stop-loss is set (required)
        - Leverage in range 5-40
        - Position size < 20% of capital
        - Total exposure < 80% of capital
        - Symbol is valid
        - Stop-loss on correct side of entry

        Args:
            symbol: Trading pair (e.g., BTCUSDT)
            side: Position side (LONG or SHORT)
            quantity: Position quantity
            entry_price: Entry price in USD
            leverage: Position leverage (5-40x)
            stop_loss: Stop loss price (REQUIRED)
            take_profit: Optional take profit price
            signal_id: Associated trading signal ID
            notes: Optional position notes

        Returns:
            PositionWithPnL: Created position with P&L metrics

        Raises:
            ValidationError: If validation fails
            RiskLimitError: If risk limits exceeded
            ConnectionError: If database operation fails
        """
        logger.info(
            f"Creating position: {symbol} {side} qty={quantity} "
            f"entry={entry_price} leverage={leverage}x stop_loss={stop_loss}"
        )

        # Create validation request
        try:
            request = PositionCreateRequest(
                symbol=symbol,
                side=PositionSide(side.upper()),
                quantity=quantity,
                entry_price=entry_price,
                leverage=leverage,
                stop_loss=stop_loss,
                take_profit=take_profit,
                signal_id=signal_id,
                notes=notes,
            )
        except ValueError as e:
            raise ValidationError(f"Invalid position parameters: {e}") from e

        # Get current exposure
        current_exposure = await self.get_total_exposure()

        # Run all validations
        try:
            request.validate_all(current_exposure_chf=current_exposure)
        except (ValidationError, RiskLimitError) as e:
            logger.error(f"Position validation failed: {e}")
            raise

        # Create position with retry logic
        for attempt in range(self._max_retries):
            try:
                async with self.pool.acquire() as conn:
                    async with conn.transaction():
                        # Insert position
                        position_id = uuid4()
                        now = datetime.utcnow()

                        row = await conn.fetchrow(
                            """
                            INSERT INTO positions (
                                id, symbol, side, quantity, entry_price, current_price,
                                leverage, stop_loss, take_profit, status, created_at, updated_at
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                            RETURNING *
                            """,
                            position_id,
                            request.symbol,
                            request.side.value,
                            request.quantity,
                            request.entry_price,
                            request.entry_price,
                            request.leverage,
                            request.stop_loss,
                            request.take_profit,
                            PositionStatus.OPEN.value,
                            now,
                            now,
                        )

                        # Log to audit_log
                        await conn.execute(
                            """
                            INSERT INTO audit_log (
                                timestamp, event_type, entity_type, entity_id, details
                            ) VALUES ($1, $2, $3, $4, $5)
                            """,
                            now,
                            "POSITION_CREATED",
                            "position",
                            position_id,
                            {
                                "symbol": request.symbol,
                                "side": request.side.value,
                                "quantity": str(request.quantity),
                                "entry_price": str(request.entry_price),
                                "leverage": request.leverage,
                                "stop_loss": str(request.stop_loss),
                                "take_profit": (
                                    str(request.take_profit)
                                    if request.take_profit
                                    else None
                                ),
                                "signal_id": str(signal_id) if signal_id else None,
                                "notes": notes,
                            },
                        )

                # Convert to Position model
                position = Position(
                    id=row["id"],
                    symbol=row["symbol"],
                    side=PositionSide(row["side"]),
                    quantity=row["quantity"],
                    entry_price=row["entry_price"],
                    current_price=row["current_price"],
                    leverage=row["leverage"],
                    stop_loss=row["stop_loss"],
                    take_profit=row["take_profit"],
                    status=PositionStatus(row["status"]),
                    pnl_chf=row["pnl_chf"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    closed_at=row["closed_at"],
                )

                position_with_pnl = PositionWithPnL.from_position(position)

                logger.info(
                    f"Position created successfully: {position_id} "
                    f"value={position_with_pnl.position_value_chf:.2f} CHF"
                )

                return position_with_pnl

            except asyncpg.PostgresError as e:
                logger.warning(
                    f"Database error on attempt {attempt + 1}/{self._max_retries}: {e}"
                )
                if attempt == self._max_retries - 1:
                    raise ConnectionError(
                        f"Failed to create position after {self._max_retries} attempts"
                    ) from e
                await asyncio.sleep(0.5 * (attempt + 1))  # Exponential backoff

    # ========================================================================
    # Position Updates
    # ========================================================================

    async def update_position_price(
        self, position_id: UUID, current_price: Decimal
    ) -> PositionWithPnL:
        """
        Update position with current market price and recalculate P&L.

        Does NOT close positions - only updates price and flags if
        stop-loss or take-profit is hit.

        Args:
            position_id: Position ID to update
            current_price: Current market price in USD

        Returns:
            PositionWithPnL: Updated position with P&L metrics

        Raises:
            PositionNotFoundError: If position not found
            ConnectionError: If database operation fails
        """
        logger.debug(f"Updating position {position_id} price to {current_price}")

        # Validate price precision
        current_price = current_price.quantize(Decimal("0.00000001"))

        for attempt in range(self._max_retries):
            try:
                async with self.pool.acquire() as conn:
                    async with conn.transaction():
                        # Update position
                        row = await conn.fetchrow(
                            """
                            UPDATE positions
                            SET current_price = $1,
                                updated_at = $2
                            WHERE id = $3 AND status = $4
                            RETURNING *
                            """,
                            current_price,
                            datetime.utcnow(),
                            position_id,
                            PositionStatus.OPEN.value,
                        )

                        if not row:
                            raise PositionNotFoundError(
                                f"Position {position_id} not found or not open"
                            )

                # Convert to Position model
                position = Position(
                    id=row["id"],
                    symbol=row["symbol"],
                    side=PositionSide(row["side"]),
                    quantity=row["quantity"],
                    entry_price=row["entry_price"],
                    current_price=row["current_price"],
                    leverage=row["leverage"],
                    stop_loss=row["stop_loss"],
                    take_profit=row["take_profit"],
                    status=PositionStatus(row["status"]),
                    pnl_chf=row["pnl_chf"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    closed_at=row["closed_at"],
                )

                position_with_pnl = PositionWithPnL.from_position(position)

                logger.debug(
                    f"Position {position_id} updated: price={current_price} "
                    f"pnl={position_with_pnl.unrealized_pnl_chf:.2f} CHF "
                    f"({position_with_pnl.unrealized_pnl_pct:.2f}%)"
                )

                return position_with_pnl

            except asyncpg.PostgresError as e:
                logger.warning(
                    f"Database error on attempt {attempt + 1}/{self._max_retries}: {e}"
                )
                if attempt == self._max_retries - 1:
                    raise ConnectionError(
                        f"Failed to update position after {self._max_retries} attempts"
                    ) from e
                await asyncio.sleep(0.5 * (attempt + 1))

    # ========================================================================
    # Position Closure
    # ========================================================================

    async def close_position(
        self,
        position_id: UUID,
        close_price: Decimal,
        reason: str,
        notes: Optional[str] = None,
    ) -> PositionWithPnL:
        """
        Close a position and calculate final P&L.

        Updates position status, calculates final P&L in CHF,
        and logs to audit_log. Updates daily P&L tracking.

        Args:
            position_id: Position ID to close
            close_price: Close price in USD
            reason: Close reason (stop_loss, take_profit, manual, circuit_breaker)
            notes: Optional closure notes

        Returns:
            PositionWithPnL: Closed position with final P&L

        Raises:
            PositionNotFoundError: If position not found
            ConnectionError: If database operation fails
        """
        logger.info(
            f"Closing position {position_id}: price={close_price} reason={reason}"
        )

        # Validate close reason
        try:
            close_reason = CloseReason(reason)
        except ValueError:
            raise ValidationError(f"Invalid close reason: {reason}")

        # Validate price precision
        close_price = close_price.quantize(Decimal("0.00000001"))

        for attempt in range(self._max_retries):
            try:
                async with self.pool.acquire() as conn:
                    async with conn.transaction():
                        # Get position
                        row = await conn.fetchrow(
                            """
                            SELECT * FROM positions
                            WHERE id = $1 AND status = $2
                            FOR UPDATE
                            """,
                            position_id,
                            PositionStatus.OPEN.value,
                        )

                        if not row:
                            raise PositionNotFoundError(
                                f"Position {position_id} not found or not open"
                            )

                        # Calculate final P&L
                        entry_price = row["entry_price"]
                        quantity = row["quantity"]
                        leverage = row["leverage"]
                        side = row["side"]

                        if side == PositionSide.LONG.value:
                            pnl_usd = (close_price - entry_price) * quantity * leverage
                        else:  # SHORT
                            pnl_usd = (entry_price - close_price) * quantity * leverage

                        pnl_chf = usd_to_chf(pnl_usd, USD_CHF_RATE)

                        # Update position to closed
                        now = datetime.utcnow()
                        status = (
                            PositionStatus.LIQUIDATED
                            if close_reason == CloseReason.LIQUIDATION
                            else PositionStatus.CLOSED
                        )

                        updated_row = await conn.fetchrow(
                            """
                            UPDATE positions
                            SET status = $1,
                                current_price = $2,
                                pnl_chf = $3,
                                closed_at = $4,
                                updated_at = $5
                            WHERE id = $6
                            RETURNING *
                            """,
                            status.value,
                            close_price,
                            pnl_chf,
                            now,
                            now,
                            position_id,
                        )

                        # Log to audit_log
                        await conn.execute(
                            """
                            INSERT INTO audit_log (
                                timestamp, event_type, entity_type, entity_id, details
                            ) VALUES ($1, $2, $3, $4, $5)
                            """,
                            now,
                            "POSITION_CLOSED",
                            "position",
                            position_id,
                            {
                                "symbol": row["symbol"],
                                "side": side,
                                "close_price": str(close_price),
                                "pnl_chf": str(pnl_chf),
                                "pnl_usd": str(pnl_usd),
                                "reason": close_reason.value,
                                "notes": notes,
                            },
                        )

                        # Update daily P&L tracking
                        today = Date.today()
                        await conn.execute(
                            """
                            INSERT INTO circuit_breaker_state (date, current_pnl_chf)
                            VALUES ($1, $2)
                            ON CONFLICT (date) DO UPDATE
                            SET current_pnl_chf = circuit_breaker_state.current_pnl_chf + EXCLUDED.current_pnl_chf
                            """,
                            today,
                            pnl_chf,
                        )

                # Convert to Position model
                position = Position(
                    id=updated_row["id"],
                    symbol=updated_row["symbol"],
                    side=PositionSide(updated_row["side"]),
                    quantity=updated_row["quantity"],
                    entry_price=updated_row["entry_price"],
                    current_price=updated_row["current_price"],
                    leverage=updated_row["leverage"],
                    stop_loss=updated_row["stop_loss"],
                    take_profit=updated_row["take_profit"],
                    status=PositionStatus(updated_row["status"]),
                    pnl_chf=updated_row["pnl_chf"],
                    created_at=updated_row["created_at"],
                    updated_at=updated_row["updated_at"],
                    closed_at=updated_row["closed_at"],
                )

                position_with_pnl = PositionWithPnL.from_position(position)

                logger.info(
                    f"Position {position_id} closed: "
                    f"pnl={pnl_chf:.2f} CHF reason={close_reason.value}"
                )

                return position_with_pnl

            except asyncpg.PostgresError as e:
                logger.warning(
                    f"Database error on attempt {attempt + 1}/{self._max_retries}: {e}"
                )
                if attempt == self._max_retries - 1:
                    raise ConnectionError(
                        f"Failed to close position after {self._max_retries} attempts"
                    ) from e
                await asyncio.sleep(0.5 * (attempt + 1))

    # ========================================================================
    # Position Queries
    # ========================================================================

    async def get_position_by_id(self, position_id: UUID) -> Optional[PositionWithPnL]:
        """
        Retrieve a single position by ID.

        Args:
            position_id: Position ID

        Returns:
            PositionWithPnL or None if not found
        """
        try:
            row = await self.pool.fetchrow(
                "SELECT * FROM positions WHERE id = $1", position_id
            )

            if not row:
                return None

            position = Position(
                id=row["id"],
                symbol=row["symbol"],
                side=PositionSide(row["side"]),
                quantity=row["quantity"],
                entry_price=row["entry_price"],
                current_price=row["current_price"],
                leverage=row["leverage"],
                stop_loss=row["stop_loss"],
                take_profit=row["take_profit"],
                status=PositionStatus(row["status"]),
                pnl_chf=row["pnl_chf"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                closed_at=row["closed_at"],
            )

            return PositionWithPnL.from_position(position)

        except asyncpg.PostgresError as e:
            logger.error(f"Failed to fetch position {position_id}: {e}")
            raise ConnectionError(f"Database query failed: {e}") from e

    async def get_active_positions(
        self, symbol: Optional[str] = None
    ) -> List[PositionWithPnL]:
        """
        Get all active (open) positions.

        Args:
            symbol: Optional symbol filter

        Returns:
            List of PositionWithPnL
        """
        try:
            if symbol:
                rows = await self.pool.fetch(
                    "SELECT * FROM positions WHERE status = $1 AND symbol = $2 ORDER BY created_at DESC",
                    PositionStatus.OPEN.value,
                    symbol,
                )
            else:
                rows = await self.pool.fetch(
                    "SELECT * FROM positions WHERE status = $1 ORDER BY created_at DESC",
                    PositionStatus.OPEN.value,
                )

            positions = []
            for row in rows:
                position = Position(
                    id=row["id"],
                    symbol=row["symbol"],
                    side=PositionSide(row["side"]),
                    quantity=row["quantity"],
                    entry_price=row["entry_price"],
                    current_price=row["current_price"],
                    leverage=row["leverage"],
                    stop_loss=row["stop_loss"],
                    take_profit=row["take_profit"],
                    status=PositionStatus(row["status"]),
                    pnl_chf=row["pnl_chf"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    closed_at=row["closed_at"],
                )
                positions.append(PositionWithPnL.from_position(position))

            logger.debug(f"Retrieved {len(positions)} active positions")
            return positions

        except asyncpg.PostgresError as e:
            logger.error(f"Failed to fetch active positions: {e}")
            raise ConnectionError(f"Database query failed: {e}") from e

    # ========================================================================
    # Stop-Loss Monitoring
    # ========================================================================

    async def check_stop_loss_triggers(self) -> List[PositionWithPnL]:
        """
        Check all active positions for stop-loss triggers.

        Does NOT close positions - just identifies which ones
        have hit their stop-loss. Trade Executor should close them.

        Returns:
            List of positions that hit stop-loss
        """
        try:
            # Get all open positions
            positions = await self.get_active_positions()

            triggered_positions = []
            for position in positions:
                if position.is_stop_loss_triggered:
                    triggered_positions.append(position)
                    logger.warning(
                        f"Stop-loss triggered: {position.symbol} {position.side.value} "
                        f"current={position.current_price} stop_loss={position.stop_loss}"
                    )

            if triggered_positions:
                logger.info(f"Found {len(triggered_positions)} positions at stop-loss")

            return triggered_positions

        except Exception as e:
            logger.error(f"Failed to check stop-loss triggers: {e}")
            raise

    async def check_take_profit_triggers(self) -> List[PositionWithPnL]:
        """
        Check all active positions for take-profit triggers.

        Does NOT close positions - just identifies which ones
        have hit their take-profit.

        Returns:
            List of positions that hit take-profit
        """
        try:
            # Get all open positions
            positions = await self.get_active_positions()

            triggered_positions = []
            for position in positions:
                if position.is_take_profit_triggered:
                    triggered_positions.append(position)
                    logger.info(
                        f"Take-profit triggered: {position.symbol} {position.side.value} "
                        f"current={position.current_price} take_profit={position.take_profit}"
                    )

            if triggered_positions:
                logger.info(
                    f"Found {len(triggered_positions)} positions at take-profit"
                )

            return triggered_positions

        except Exception as e:
            logger.error(f"Failed to check take-profit triggers: {e}")
            raise

    # ========================================================================
    # Risk Management
    # ========================================================================

    async def get_total_exposure(self) -> Decimal:
        """
        Calculate total exposure across all open positions in CHF.

        Total exposure = sum of (position_value * leverage) for all open positions.

        Returns:
            Decimal: Total exposure in CHF
        """
        try:
            positions = await self.get_active_positions()

            total_exposure = Decimal("0")
            for position in positions:
                if position.position_value_chf:
                    total_exposure += position.position_value_chf

            logger.debug(f"Total exposure: CHF {total_exposure:.2f}")
            return total_exposure.quantize(Decimal("0.00000001"))

        except Exception as e:
            logger.error(f"Failed to calculate total exposure: {e}")
            raise

    async def get_daily_pnl(
        self, target_date: Optional[Date] = None
    ) -> DailyPnLSummary:
        """
        Calculate total P&L for a specific date (defaults to today).

        Includes:
        - Realized P&L from positions closed today
        - Unrealized P&L from currently open positions

        Args:
            target_date: Date to calculate (defaults to today)

        Returns:
            DailyPnLSummary with P&L breakdown
        """
        if target_date is None:
            target_date = Date.today()

        try:
            async with self.pool.acquire() as conn:
                # Get realized P&L from closed positions
                realized_row = await conn.fetchrow(
                    """
                    SELECT COALESCE(SUM(pnl_chf), 0) as realized_pnl, COUNT(*) as closed_count
                    FROM positions
                    WHERE DATE(closed_at) = $1
                    AND status IN ($2, $3)
                    """,
                    target_date,
                    PositionStatus.CLOSED.value,
                    PositionStatus.LIQUIDATED.value,
                )

                realized_pnl_chf = realized_row["realized_pnl"]
                closed_count = realized_row["closed_count"]

            # Get unrealized P&L from open positions
            open_positions = await self.get_active_positions()
            unrealized_pnl_chf = Decimal("0")
            total_exposure_chf = Decimal("0")

            for position in open_positions:
                if position.unrealized_pnl_chf:
                    unrealized_pnl_chf += position.unrealized_pnl_chf
                if position.position_value_chf:
                    total_exposure_chf += position.position_value_chf

            # Calculate totals
            total_pnl_chf = realized_pnl_chf + unrealized_pnl_chf

            summary = DailyPnLSummary(
                date=target_date,
                total_pnl_chf=total_pnl_chf,
                realized_pnl_chf=realized_pnl_chf,
                unrealized_pnl_chf=unrealized_pnl_chf,
                open_positions_count=len(open_positions),
                closed_positions_count=closed_count,
                total_exposure_chf=total_exposure_chf,
                is_circuit_breaker_triggered=total_pnl_chf <= CIRCUIT_BREAKER_LOSS_CHF,
            )

            logger.info(
                f"Daily P&L for {target_date}: "
                f"total={total_pnl_chf:.2f} CHF "
                f"(realized={realized_pnl_chf:.2f}, unrealized={unrealized_pnl_chf:.2f})"
            )

            return summary

        except Exception as e:
            logger.error(f"Failed to calculate daily P&L: {e}")
            raise

    async def get_statistics(self) -> PositionStatistics:
        """
        Get aggregated position statistics.

        Returns:
            PositionStatistics with comprehensive metrics
        """
        try:
            async with self.pool.acquire() as conn:
                # Get position counts
                counts_row = await conn.fetchrow(
                    """
                    SELECT
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE status = $1) as open,
                        COUNT(*) FILTER (WHERE status IN ($2, $3)) as closed
                    FROM positions
                    """,
                    PositionStatus.OPEN.value,
                    PositionStatus.CLOSED.value,
                    PositionStatus.LIQUIDATED.value,
                )

                # Get realized P&L
                realized_pnl = await conn.fetchval(
                    """
                    SELECT COALESCE(SUM(pnl_chf), 0)
                    FROM positions
                    WHERE status IN ($1, $2) AND pnl_chf IS NOT NULL
                    """,
                    PositionStatus.CLOSED.value,
                    PositionStatus.LIQUIDATED.value,
                )

            # Get open positions for unrealized P&L and exposure
            open_positions = await self.get_active_positions()
            total_exposure_chf = Decimal("0")
            total_unrealized_pnl_chf = Decimal("0")
            positions_at_stop_loss = 0
            positions_at_take_profit = 0

            for position in open_positions:
                if position.position_value_chf:
                    total_exposure_chf += position.position_value_chf
                if position.unrealized_pnl_chf:
                    total_unrealized_pnl_chf += position.unrealized_pnl_chf
                if position.is_stop_loss_triggered:
                    positions_at_stop_loss += 1
                if position.is_take_profit_triggered:
                    positions_at_take_profit += 1

            statistics = PositionStatistics(
                total_positions=counts_row["total"],
                open_positions=counts_row["open"],
                closed_positions=counts_row["closed"],
                total_exposure_chf=total_exposure_chf,
                total_unrealized_pnl_chf=total_unrealized_pnl_chf,
                total_realized_pnl_chf=realized_pnl or Decimal("0"),
                positions_at_stop_loss=positions_at_stop_loss,
                positions_at_take_profit=positions_at_take_profit,
            )

            logger.debug(f"Position statistics: {statistics.model_dump()}")
            return statistics

        except Exception as e:
            logger.error(f"Failed to get position statistics: {e}")
            raise


# ============================================================================
# Utility Functions
# ============================================================================


async def bulk_update_prices(
    service: PositionService, price_updates: Dict[str, Decimal]
) -> Dict[UUID, PositionWithPnL]:
    """
    Update prices for multiple positions efficiently.

    Args:
        service: PositionService instance
        price_updates: Dict mapping symbol to current price

    Returns:
        Dict mapping position ID to updated position

    Example:
        prices = {
            "BTCUSDT": Decimal("45000.00"),
            "ETHUSDT": Decimal("2500.00")
        }
        updated = await bulk_update_prices(service, prices)
    """
    updated_positions = {}

    # Get all open positions
    open_positions = await service.get_active_positions()

    # Update each position with matching symbol
    for position in open_positions:
        if position.symbol in price_updates:
            new_price = price_updates[position.symbol]
            try:
                updated = await service.update_position_price(position.id, new_price)
                updated_positions[position.id] = updated
            except Exception as e:
                logger.error(f"Failed to update position {position.id}: {e}")

    logger.info(f"Bulk updated {len(updated_positions)} positions")
    return updated_positions
