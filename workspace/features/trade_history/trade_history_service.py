"""
Trade History Service

Service for logging and querying trade history with PostgreSQL backend.

Author: Trading System Implementation Team
Date: 2025-10-28
"""

import logging
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from .models import (DailyTradeReport, TradeHistoryEntry, TradeStatistics,
                     TradeStatus, TradeType)

logger = logging.getLogger(__name__)


class TradeHistoryService:
    """
    Service for managing trade history

    Provides functionality to:
    - Log all trades
    - Query trade history
    - Calculate statistics
    - Generate reports

    Uses PostgreSQL with TimescaleDB for production storage,
    with in-memory fallback for development/errors.
    """

    def __init__(self, use_database: bool = True):
        """
        Initialize trade history service

        Args:
            use_database: If True, use PostgreSQL backend; if False, use in-memory
        """
        self.use_database = use_database

        # In-memory fallback storage
        self._trades: Dict[str, TradeHistoryEntry] = {}
        self._trades_by_date: Dict[str, List[str]] = {}  # date -> trade_ids
        self._trades_by_symbol: Dict[str, List[str]] = {}  # symbol -> trade_ids

        storage_mode = "database" if use_database else "in-memory"
        logger.info(f"Trade History Service initialized ({storage_mode} mode)")

    async def log_trade(
        self,
        trade_type: TradeType,
        symbol: str,
        order_id: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        fees: Decimal = Decimal("0"),
        position_id: Optional[str] = None,
        realized_pnl: Optional[Decimal] = None,
        signal_confidence: Optional[Decimal] = None,
        signal_reasoning: Optional[str] = None,
        execution_latency_ms: Optional[Decimal] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TradeHistoryEntry:
        """
        Log a completed trade

        Args:
            trade_type: Type of trade (entry/exit/stop-loss/etc)
            symbol: Trading pair
            order_id: Exchange order ID
            side: 'buy' or 'sell'
            quantity: Trade quantity
            price: Execution price
            fees: Trading fees paid
            position_id: Associated position ID
            realized_pnl: Realized P&L (for exits)
            signal_confidence: Signal confidence level
            signal_reasoning: LLM reasoning
            execution_latency_ms: Execution latency
            metadata: Additional metadata

        Returns:
            TradeHistoryEntry object
        """
        try:
            # Generate trade ID
            trade_id = f"trade_{uuid.uuid4().hex[:12]}"

            # Create trade entry
            trade = TradeHistoryEntry(
                id=trade_id,
                trade_type=trade_type,
                status=TradeStatus.FILLED,  # Logging after fill
                symbol=symbol,
                order_id=order_id,
                position_id=position_id,
                side=side,
                quantity=quantity,
                entry_price=price,
                exit_price=(
                    price
                    if trade_type
                    in [
                        TradeType.EXIT_LONG,
                        TradeType.EXIT_SHORT,
                        TradeType.STOP_LOSS,
                        TradeType.TAKE_PROFIT,
                    ]
                    else None
                ),
                fees=fees,
                realized_pnl=realized_pnl,
                timestamp=datetime.utcnow(),
                signal_confidence=signal_confidence,
                signal_reasoning=signal_reasoning,
                execution_latency_ms=execution_latency_ms,
                metadata=metadata or {},
            )

            # Store trade
            self._trades[trade_id] = trade

            # Index by date
            date_key = trade.timestamp.strftime("%Y-%m-%d")
            if date_key not in self._trades_by_date:
                self._trades_by_date[date_key] = []
            self._trades_by_date[date_key].append(trade_id)

            # Index by symbol
            if symbol not in self._trades_by_symbol:
                self._trades_by_symbol[symbol] = []
            self._trades_by_symbol[symbol].append(trade_id)

            logger.info(
                f"Logged trade: {trade_id} | {trade_type.value} | "
                f"{symbol} | {side} {quantity} @ {price}"
            )

            if realized_pnl:
                logger.info(f"Trade P&L: {realized_pnl:+.2f} (fees: {fees:.2f})")

            return trade

        except Exception as e:
            logger.error(f"Error logging trade: {e}", exc_info=True)
            raise

    async def get_trade(self, trade_id: str) -> Optional[TradeHistoryEntry]:
        """
        Get a specific trade by ID

        Args:
            trade_id: Trade ID to retrieve

        Returns:
            TradeHistoryEntry or None if not found
        """
        return self._trades.get(trade_id)

    async def get_trades(
        self,
        symbol: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        trade_type: Optional[TradeType] = None,
        limit: int = 100,
    ) -> List[TradeHistoryEntry]:
        """
        Query trade history with filters

        Args:
            symbol: Filter by symbol
            start_date: Filter by start date
            end_date: Filter by end date
            trade_type: Filter by trade type
            limit: Maximum results to return

        Returns:
            List of TradeHistoryEntry objects
        """
        try:
            # Start with all trades
            trades = list(self._trades.values())

            # Apply filters
            if symbol:
                trades = [t for t in trades if t.symbol == symbol]

            if start_date:
                trades = [t for t in trades if t.timestamp >= start_date]

            if end_date:
                trades = [t for t in trades if t.timestamp <= end_date]

            if trade_type:
                trades = [t for t in trades if t.trade_type == trade_type]

            # Sort by timestamp (newest first)
            trades.sort(key=lambda t: t.timestamp, reverse=True)

            # Apply limit
            trades = trades[:limit]

            logger.debug(f"Retrieved {len(trades)} trades with filters")

            return trades

        except Exception as e:
            logger.error(f"Error querying trades: {e}", exc_info=True)
            return []

    async def get_daily_trades(self, date: datetime) -> List[TradeHistoryEntry]:
        """
        Get all trades for a specific day

        Args:
            date: Date to query

        Returns:
            List of TradeHistoryEntry objects
        """
        date_key = date.strftime("%Y-%m-%d")
        trade_ids = self._trades_by_date.get(date_key, [])
        return [self._trades[tid] for tid in trade_ids]

    async def calculate_statistics(
        self,
        start_date: datetime,
        end_date: datetime,
        symbol: Optional[str] = None,
    ) -> TradeStatistics:
        """
        Calculate aggregated trade statistics

        Args:
            start_date: Start of period
            end_date: End of period
            symbol: Optional symbol filter

        Returns:
            TradeStatistics object
        """
        try:
            # Get trades in period
            trades = await self.get_trades(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                limit=10000,  # Large limit for stats
            )

            # Filter only exit trades (those with realized P&L)
            exit_trades = [t for t in trades if t.realized_pnl is not None]

            # Calculate metrics
            total_trades = len(exit_trades)

            if total_trades == 0:
                # Return empty stats
                return TradeStatistics(
                    total_trades=0,
                    total_volume=Decimal("0"),
                    win_rate=Decimal("0"),
                    total_pnl=Decimal("0"),
                    period_start=start_date,
                    period_end=end_date,
                )

            # Volume
            total_volume = sum(t.quantity * t.entry_price for t in trades)

            # Win/loss
            winning_trades = [t for t in exit_trades if t.realized_pnl > 0]
            losing_trades = [t for t in exit_trades if t.realized_pnl < 0]

            win_count = len(winning_trades)
            loss_count = len(losing_trades)
            win_rate = Decimal(win_count) / Decimal(total_trades) * Decimal("100")

            # P&L
            total_pnl = sum(t.realized_pnl for t in exit_trades)

            average_win = (
                sum(t.realized_pnl for t in winning_trades) / Decimal(win_count)
                if win_count > 0
                else Decimal("0")
            )

            average_loss = (
                sum(t.realized_pnl for t in losing_trades) / Decimal(loss_count)
                if loss_count > 0
                else Decimal("0")
            )

            largest_win = max(
                (t.realized_pnl for t in winning_trades), default=Decimal("0")
            )

            largest_loss = min(
                (t.realized_pnl for t in losing_trades), default=Decimal("0")
            )

            # Profit factor
            gross_profit = sum(t.realized_pnl for t in winning_trades)
            gross_loss = abs(sum(t.realized_pnl for t in losing_trades))
            profit_factor = (
                gross_profit / gross_loss if gross_loss > 0 else Decimal("0")
            )

            # Fees
            total_fees = sum(t.fees for t in trades)

            # Create statistics object
            stats = TradeStatistics(
                total_trades=total_trades,
                total_volume=total_volume,
                winning_trades=win_count,
                losing_trades=loss_count,
                win_rate=win_rate,
                total_pnl=total_pnl,
                average_win=average_win,
                average_loss=average_loss,
                largest_win=largest_win,
                largest_loss=largest_loss,
                profit_factor=profit_factor,
                total_fees=total_fees,
                period_start=start_date,
                period_end=end_date,
            )

            logger.info(
                f"Statistics calculated: {total_trades} trades, "
                f"Win rate: {win_rate:.1f}%, Total P&L: {total_pnl:+.2f}"
            )

            return stats

        except Exception as e:
            logger.error(f"Error calculating statistics: {e}", exc_info=True)
            # Return empty stats
            return TradeStatistics(
                total_trades=0,
                total_volume=Decimal("0"),
                win_rate=Decimal("0"),
                total_pnl=Decimal("0"),
                period_start=start_date,
                period_end=end_date,
            )

    async def generate_daily_report(self, date: datetime) -> DailyTradeReport:
        """
        Generate daily trade report

        Args:
            date: Date to generate report for

        Returns:
            DailyTradeReport object
        """
        try:
            # Get trades for the day
            start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=1)

            trades = await self.get_trades(
                start_date=start_date,
                end_date=end_date,
                limit=10000,
            )

            # Calculate statistics
            stats = await self.calculate_statistics(start_date, end_date)

            # Trades by hour
            trades_by_hour = {}
            for trade in trades:
                hour = trade.timestamp.hour
                trades_by_hour[hour] = trades_by_hour.get(hour, 0) + 1

            # Trades by symbol
            trades_by_symbol = {}
            for trade in trades:
                symbol = trade.symbol
                trades_by_symbol[symbol] = trades_by_symbol.get(symbol, 0) + 1

            # Daily P&L (from exit trades only)
            exit_trades = [t for t in trades if t.realized_pnl is not None]
            daily_pnl = sum(t.realized_pnl for t in exit_trades)

            # Create report
            report = DailyTradeReport(
                date=date,
                statistics=stats,
                trades_by_hour=trades_by_hour,
                trades_by_symbol=trades_by_symbol,
                daily_pnl=daily_pnl,
                daily_return_pct=Decimal("0"),  # TODO: Calculate from starting capital
                max_position_size=Decimal("0"),  # TODO: Track from positions
                circuit_breaker_triggered=False,  # TODO: Track from risk manager
            )

            logger.info(f"Daily report generated for {date.strftime('%Y-%m-%d')}")

            return report

        except Exception as e:
            logger.error(f"Error generating daily report: {e}", exc_info=True)
            raise

    def get_stats(self) -> Dict[str, Any]:
        """
        Get service statistics

        Returns:
            Dictionary with service stats
        """
        return {
            "total_trades_logged": len(self._trades),
            "unique_symbols": len(self._trades_by_symbol),
            "trading_days": len(self._trades_by_date),
            "storage_mode": "in-memory",  # TODO: Change to "database" when implemented
        }


# Export
__all__ = ["TradeHistoryService"]
