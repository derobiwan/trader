"""
Virtual Portfolio Manager

Manages virtual positions, balance, and P&L tracking for paper trading.
Provides realistic portfolio management without real capital.

Key Features:
- Virtual balance tracking
- Position management (open/close/update)
- Unrealized P&L calculation
- Position averaging for multiple entries
- Trade history tracking

Author: Implementation Specialist (Sprint 2 Stream B)
Date: 2025-10-29
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class VirtualPortfolio:
    """
    Virtual portfolio for paper trading

    Manages virtual balance, positions, and P&L tracking.

    Attributes:
        initial_balance: Starting balance in USDT
        balance: Current balance in USDT
        positions: Dictionary of open positions by symbol
        trade_history: List of all trades
        closed_positions: List of closed positions with P&L
    """

    def __init__(self, initial_balance: Decimal):
        """
        Initialize virtual portfolio

        Args:
            initial_balance: Starting balance in USDT
        """
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.trade_history: List[Dict[str, Any]] = []
        self.closed_positions: List[Dict[str, Any]] = []

        logger.info(f"Virtual Portfolio initialized with ${initial_balance} USDT")

    def open_position(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        entry_price: Decimal,
        fees: Decimal,
    ):
        """
        Open or add to virtual position

        If position already exists, calculates weighted average entry price.

        Args:
            symbol: Trading pair
            side: 'long' or 'short'
            quantity: Position quantity
            entry_price: Entry price
            fees: Trading fees paid
        """
        if symbol in self.positions:
            # Update existing position
            pos = self.positions[symbol]

            # Calculate weighted average entry price
            total_quantity = pos["quantity"] + quantity
            avg_price = (
                pos["entry_price"] * pos["quantity"] + entry_price * quantity
            ) / total_quantity

            # Update position
            pos["quantity"] = total_quantity
            pos["entry_price"] = avg_price
            pos["total_fees"] += fees
            pos["last_updated"] = datetime.utcnow()

            logger.info(
                f"Added to position {symbol}: "
                f"New qty: {total_quantity}, Avg price: ${avg_price:.2f}"
            )

        else:
            # Create new position
            self.positions[symbol] = {
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "entry_price": entry_price,
                "total_fees": fees,
                "opened_at": datetime.utcnow(),
                "last_updated": datetime.utcnow(),
            }

            logger.info(
                f"Opened position {symbol}: "
                f"Side: {side}, Qty: {quantity}, Price: ${entry_price:.2f}"
            )

        # Deduct cost from balance
        cost = quantity * entry_price + fees
        if side == "long":
            self.balance -= cost
        else:
            # For shorts, we receive proceeds
            self.balance += quantity * entry_price - fees

        # Record trade
        self.trade_history.append(
            {
                "action": "open",
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": entry_price,
                "fees": fees,
                "timestamp": datetime.utcnow(),
            }
        )

    def close_position(
        self,
        symbol: str,
        exit_price: Decimal,
        fees: Decimal,
        quantity: Optional[Decimal] = None,
    ) -> Decimal:
        """
        Close virtual position (fully or partially)

        Args:
            symbol: Trading pair
            exit_price: Exit price
            fees: Trading fees paid
            quantity: Quantity to close (None = close all)

        Returns:
            Realized P&L in USDT

        Raises:
            ValueError: If position doesn't exist
        """
        if symbol not in self.positions:
            raise ValueError(f"No position for {symbol}")

        pos = self.positions[symbol]
        close_quantity = quantity if quantity is not None else pos["quantity"]

        # Validate quantity
        if close_quantity > pos["quantity"]:
            raise ValueError(
                f"Cannot close {close_quantity} - only {pos['quantity']} available"
            )

        # Calculate P&L
        if pos["side"] == "long":
            pnl = (exit_price - pos["entry_price"]) * close_quantity
        else:
            pnl = (pos["entry_price"] - exit_price) * close_quantity

        # Subtract fees
        pnl -= fees

        # Update balance
        if pos["side"] == "long":
            proceeds = close_quantity * exit_price - fees
            self.balance += proceeds
        else:
            cost = close_quantity * exit_price + fees
            self.balance -= cost

        # Record closed position
        closed_pos = {
            "symbol": symbol,
            "side": pos["side"],
            "quantity": close_quantity,
            "entry_price": pos["entry_price"],
            "exit_price": exit_price,
            "pnl": pnl,
            "total_fees": pos["total_fees"] + fees,
            "opened_at": pos["opened_at"],
            "closed_at": datetime.utcnow(),
            "holding_period": (datetime.utcnow() - pos["opened_at"]).total_seconds(),
        }
        self.closed_positions.append(closed_pos)

        # Update or remove position
        if close_quantity >= pos["quantity"]:
            # Fully closed
            del self.positions[symbol]
            logger.info(f"Closed position {symbol} fully: P&L: ${pnl:.2f}")
        else:
            # Partially closed
            pos["quantity"] -= close_quantity
            pos["last_updated"] = datetime.utcnow()
            logger.info(
                f"Partially closed position {symbol}: "
                f"Closed: {close_quantity}, Remaining: {pos['quantity']}, "
                f"P&L: ${pnl:.2f}"
            )

        # Record trade
        self.trade_history.append(
            {
                "action": "close",
                "symbol": symbol,
                "side": pos["side"],
                "quantity": close_quantity,
                "price": exit_price,
                "fees": fees,
                "pnl": pnl,
                "timestamp": datetime.utcnow(),
            }
        )

        return pnl

    def get_unrealized_pnl(self, current_prices: Dict[str, Decimal]) -> Decimal:
        """
        Calculate total unrealized P&L for all open positions

        Args:
            current_prices: Dictionary of current prices by symbol

        Returns:
            Total unrealized P&L in USDT
        """
        total_pnl = Decimal("0")

        for symbol, pos in self.positions.items():
            if symbol in current_prices:
                current_price = current_prices[symbol]

                if pos["side"] == "long":
                    position_pnl = (current_price - pos["entry_price"]) * pos[
                        "quantity"
                    ]
                else:
                    position_pnl = (pos["entry_price"] - current_price) * pos[
                        "quantity"
                    ]

                total_pnl += position_pnl

        return total_pnl

    def get_position_pnl(
        self, symbol: str, current_price: Decimal
    ) -> Optional[Decimal]:
        """
        Calculate unrealized P&L for specific position

        Args:
            symbol: Trading pair
            current_price: Current market price

        Returns:
            Unrealized P&L or None if position doesn't exist
        """
        if symbol not in self.positions:
            return None

        pos = self.positions[symbol]

        if pos["side"] == "long":
            return (current_price - pos["entry_price"]) * pos["quantity"]
        else:
            return (pos["entry_price"] - current_price) * pos["quantity"]

    def get_total_equity(self, current_prices: Dict[str, Decimal]) -> Decimal:
        """
        Calculate total portfolio equity (balance + unrealized P&L)

        Args:
            current_prices: Dictionary of current prices by symbol

        Returns:
            Total equity in USDT
        """
        unrealized_pnl = self.get_unrealized_pnl(current_prices)
        return self.balance + unrealized_pnl

    def get_portfolio_summary(
        self, current_prices: Optional[Dict[str, Decimal]] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive portfolio summary

        Args:
            current_prices: Optional dictionary of current prices

        Returns:
            Portfolio summary with balance, positions, and P&L
        """
        summary = {
            "initial_balance": float(self.initial_balance),
            "current_balance": float(self.balance),
            "open_positions": len(self.positions),
            "closed_positions": len(self.closed_positions),
            "total_trades": len(self.trade_history),
        }

        # Add unrealized P&L if prices provided
        if current_prices:
            unrealized_pnl = self.get_unrealized_pnl(current_prices)
            total_equity = self.get_total_equity(current_prices)

            summary["unrealized_pnl"] = float(unrealized_pnl)
            summary["total_equity"] = float(total_equity)
            summary["return_pct"] = float(
                (total_equity - self.initial_balance) / self.initial_balance * 100
            )

        # Calculate realized P&L
        realized_pnl = sum(pos["pnl"] for pos in self.closed_positions)
        summary["realized_pnl"] = float(realized_pnl)

        # Position details
        summary["positions"] = [
            {
                "symbol": pos["symbol"],
                "side": pos["side"],
                "quantity": float(pos["quantity"]),
                "entry_price": float(pos["entry_price"]),
                "unrealized_pnl": (
                    float(
                        self.get_position_pnl(
                            pos["symbol"], current_prices[pos["symbol"]]
                        )
                    )
                    if current_prices and pos["symbol"] in current_prices
                    else None
                ),
            }
            for pos in self.positions.values()
        ]

        return summary

    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Calculate performance statistics

        Returns:
            Performance metrics
        """
        if not self.closed_positions:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "total_pnl": 0.0,
                "largest_win": 0.0,
                "largest_loss": 0.0,
            }

        winning_trades = [pos for pos in self.closed_positions if pos["pnl"] > 0]
        losing_trades = [pos for pos in self.closed_positions if pos["pnl"] < 0]

        total_pnl = sum(pos["pnl"] for pos in self.closed_positions)
        avg_win = (
            sum(pos["pnl"] for pos in winning_trades) / len(winning_trades)
            if winning_trades
            else Decimal("0")
        )
        avg_loss = (
            sum(pos["pnl"] for pos in losing_trades) / len(losing_trades)
            if losing_trades
            else Decimal("0")
        )

        return {
            "total_trades": len(self.closed_positions),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": float(len(winning_trades) / len(self.closed_positions) * 100),
            "avg_win": float(avg_win),
            "avg_loss": float(avg_loss),
            "total_pnl": float(total_pnl),
            "largest_win": float(
                max((pos["pnl"] for pos in winning_trades), default=Decimal("0"))
            ),
            "largest_loss": float(
                min((pos["pnl"] for pos in losing_trades), default=Decimal("0"))
            ),
            "avg_holding_period_seconds": (
                sum(pos["holding_period"] for pos in self.closed_positions)
                / len(self.closed_positions)
            ),
        }
