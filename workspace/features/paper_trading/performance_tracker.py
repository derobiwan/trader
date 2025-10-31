"""
Paper Trading Performance Tracker

Tracks and analyzes paper trading performance with comprehensive metrics.

Key Metrics:
- Win rate and profit factor
- Average win/loss and risk-reward ratio
- Maximum drawdown
- Sharpe ratio (annualized)
- Daily P&L tracking
- Trade frequency and holding periods

Author: Implementation Specialist (Sprint 2 Stream B)
Date: 2025-10-29
"""

import logging
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional, Any
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)


class PaperTradingPerformanceTracker:
    """
    Performance tracker for paper trading

    Tracks all trades and calculates comprehensive performance metrics.

    Attributes:
        trades: List of all executed trades
        daily_pnl: Dictionary of P&L by date
        metrics: Current performance metrics
        equity_curve: Historical equity values
    """

    def __init__(self):
        """Initialize performance tracker"""
        self.trades: List[Dict[str, Any]] = []
        self.daily_pnl: Dict[date, Decimal] = defaultdict(lambda: Decimal("0"))
        self.equity_curve: List[Dict[str, Any]] = []

        self.metrics = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "breakeven_trades": 0,
            "total_pnl": Decimal("0"),
            "total_fees": Decimal("0"),
            "win_rate": Decimal("0"),
            "avg_win": Decimal("0"),
            "avg_loss": Decimal("0"),
            "largest_win": Decimal("0"),
            "largest_loss": Decimal("0"),
            "profit_factor": Decimal("0"),
            "max_drawdown": Decimal("0"),
            "sharpe_ratio": Decimal("0"),
        }

        logger.info("Performance tracker initialized")

    def record_trade(self, trade: Dict[str, Any]):
        """
        Record a completed trade

        Args:
            trade: Trade dictionary with symbol, side, quantity, price, fees, pnl, timestamp
        """
        self.trades.append(trade)

        # Update daily P&L
        trade_date = trade["timestamp"].date()
        self.daily_pnl[trade_date] += trade["pnl"]

        # Update metrics
        self.metrics["total_trades"] += 1
        self.metrics["total_pnl"] += trade["pnl"]
        self.metrics["total_fees"] += trade["fees"]

        # Categorize trade
        if trade["pnl"] > 0:
            self.metrics["winning_trades"] += 1
            if trade["pnl"] > self.metrics["largest_win"]:
                self.metrics["largest_win"] = trade["pnl"]
        elif trade["pnl"] < 0:
            self.metrics["losing_trades"] += 1
            if trade["pnl"] < self.metrics["largest_loss"]:
                self.metrics["largest_loss"] = trade["pnl"]
        else:
            self.metrics["breakeven_trades"] += 1

        # Recalculate derived metrics
        self._calculate_metrics()

        logger.debug(
            f"Trade recorded: {trade['symbol']} - "
            f"P&L: ${trade['pnl']:.2f}, Total P&L: ${self.metrics['total_pnl']:.2f}"
        )

    def _calculate_metrics(self):
        """Calculate derived performance metrics"""
        if self.metrics["total_trades"] == 0:
            return

        # Calculate win rate
        self.metrics["win_rate"] = (
            self.metrics["winning_trades"] / self.metrics["total_trades"]
        )

        # Calculate average win/loss
        winning_trades = [t for t in self.trades if t["pnl"] > 0]
        losing_trades = [t for t in self.trades if t["pnl"] < 0]

        if winning_trades:
            total_wins = sum(t["pnl"] for t in winning_trades)
            self.metrics["avg_win"] = total_wins / len(winning_trades)

        if losing_trades:
            total_losses = sum(t["pnl"] for t in losing_trades)
            self.metrics["avg_loss"] = total_losses / len(losing_trades)

        # Calculate profit factor
        if losing_trades:
            gross_profit = (
                sum(t["pnl"] for t in winning_trades)
                if winning_trades
                else Decimal("0")
            )
            gross_loss = abs(sum(t["pnl"] for t in losing_trades))
            self.metrics["profit_factor"] = (
                gross_profit / gross_loss if gross_loss > 0 else Decimal("0")
            )

        # Calculate maximum drawdown
        self._calculate_max_drawdown()

        # Calculate Sharpe ratio
        self._calculate_sharpe_ratio()

    def _calculate_max_drawdown(self):
        """Calculate maximum drawdown from equity curve"""
        if not self.trades:
            self.metrics["max_drawdown"] = Decimal("0")
            return

        # Build equity curve
        running_pnl = Decimal("0")
        peak = Decimal("0")
        max_dd = Decimal("0")

        for trade in self.trades:
            running_pnl += trade["pnl"]

            # Update peak
            if running_pnl > peak:
                peak = running_pnl

            # Calculate drawdown from peak
            drawdown = peak - running_pnl

            # Update max drawdown
            if drawdown > max_dd:
                max_dd = drawdown

        self.metrics["max_drawdown"] = max_dd

    def _calculate_sharpe_ratio(self):
        """Calculate annualized Sharpe ratio"""
        if len(self.daily_pnl) < 2:
            self.metrics["sharpe_ratio"] = Decimal("0")
            return

        # Get daily returns
        daily_returns = [float(pnl) for pnl in self.daily_pnl.values()]

        if not daily_returns:
            self.metrics["sharpe_ratio"] = Decimal("0")
            return

        # Calculate mean and std dev
        mean_return = statistics.mean(daily_returns)
        std_return = statistics.stdev(daily_returns) if len(daily_returns) > 1 else 0

        if std_return == 0:
            self.metrics["sharpe_ratio"] = Decimal("0")
            return

        # Annualize (assuming 365 trading days for crypto)
        sharpe = (mean_return / std_return) * (365**0.5)
        self.metrics["sharpe_ratio"] = Decimal(str(sharpe))

    def generate_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive performance report

        Returns:
            Performance report dictionary
        """
        report = {
            "summary": {
                "total_trades": self.metrics["total_trades"],
                "winning_trades": self.metrics["winning_trades"],
                "losing_trades": self.metrics["losing_trades"],
                "breakeven_trades": self.metrics["breakeven_trades"],
            },
            "profitability": {
                "total_pnl": float(self.metrics["total_pnl"]),
                "total_fees": float(self.metrics["total_fees"]),
                "net_pnl": float(
                    self.metrics["total_pnl"] - self.metrics["total_fees"]
                ),
                "win_rate": float(self.metrics["win_rate"] * 100),
                "profit_factor": float(self.metrics["profit_factor"]),
            },
            "trade_statistics": {
                "avg_win": float(self.metrics["avg_win"]),
                "avg_loss": float(self.metrics["avg_loss"]),
                "largest_win": float(self.metrics["largest_win"]),
                "largest_loss": float(self.metrics["largest_loss"]),
                "avg_trade_pnl": (
                    float(self.metrics["total_pnl"] / self.metrics["total_trades"])
                    if self.metrics["total_trades"] > 0
                    else 0.0
                ),
            },
            "risk_metrics": {
                "max_drawdown": float(self.metrics["max_drawdown"]),
                "sharpe_ratio": float(self.metrics["sharpe_ratio"]),
                "risk_reward_ratio": (
                    float(abs(self.metrics["avg_win"] / self.metrics["avg_loss"]))
                    if self.metrics["avg_loss"] != 0
                    else 0.0
                ),
            },
            "time_analysis": {
                "trading_days": len(self.daily_pnl),
                "avg_trades_per_day": (
                    float(self.metrics["total_trades"] / len(self.daily_pnl))
                    if self.daily_pnl
                    else 0.0
                ),
            },
        }

        # Add daily P&L breakdown
        report["daily_pnl"] = [
            {
                "date": d.isoformat(),
                "pnl": float(pnl),
            }
            for d, pnl in sorted(self.daily_pnl.items())
        ]

        return report

    def get_trade_history(
        self,
        limit: Optional[int] = None,
        winning_only: bool = False,
        losing_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Get trade history with optional filtering

        Args:
            limit: Maximum number of trades to return
            winning_only: Return only winning trades
            losing_only: Return only losing trades

        Returns:
            List of trades
        """
        trades = self.trades.copy()

        # Apply filters
        if winning_only:
            trades = [t for t in trades if t["pnl"] > 0]
        elif losing_only:
            trades = [t for t in trades if t["pnl"] < 0]

        # Sort by timestamp (most recent first)
        trades.sort(key=lambda t: t["timestamp"], reverse=True)

        # Apply limit
        if limit:
            trades = trades[:limit]

        return trades

    def get_symbol_performance(self) -> Dict[str, Dict[str, Any]]:
        """
        Get performance breakdown by symbol

        Returns:
            Dictionary of performance metrics by symbol
        """
        symbol_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "trades": 0,
                "wins": 0,
                "losses": 0,
                "total_pnl": Decimal("0"),
                "total_fees": Decimal("0"),
            }
        )

        for trade in self.trades:
            symbol = trade["symbol"]
            stats = symbol_stats[symbol]

            stats["trades"] += 1
            stats["total_pnl"] += trade["pnl"]
            stats["total_fees"] += trade["fees"]

            if trade["pnl"] > 0:
                stats["wins"] += 1
            elif trade["pnl"] < 0:
                stats["losses"] += 1

        # Calculate derived metrics for each symbol
        result = {}
        for symbol, stats in symbol_stats.items():
            result[symbol] = {
                "trades": stats["trades"],
                "wins": stats["wins"],
                "losses": stats["losses"],
                "win_rate": (
                    float(stats["wins"] / stats["trades"] * 100)
                    if stats["trades"] > 0
                    else 0.0
                ),
                "total_pnl": float(stats["total_pnl"]),
                "total_fees": float(stats["total_fees"]),
                "net_pnl": float(stats["total_pnl"] - stats["total_fees"]),
                "avg_pnl_per_trade": (
                    float(stats["total_pnl"] / stats["trades"])
                    if stats["trades"] > 0
                    else 0.0
                ),
            }

        return result

    def reset(self):
        """Reset all performance tracking"""
        self.trades = []
        self.daily_pnl = defaultdict(lambda: Decimal("0"))
        self.equity_curve = []

        self.metrics = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "breakeven_trades": 0,
            "total_pnl": Decimal("0"),
            "total_fees": Decimal("0"),
            "win_rate": Decimal("0"),
            "avg_win": Decimal("0"),
            "avg_loss": Decimal("0"),
            "largest_win": Decimal("0"),
            "largest_loss": Decimal("0"),
            "profit_factor": Decimal("0"),
            "max_drawdown": Decimal("0"),
            "sharpe_ratio": Decimal("0"),
        }

        logger.info("Performance tracker reset")

    def export_trades_csv(self, filepath: str):
        """
        Export trades to CSV file

        Args:
            filepath: Path to CSV file
        """
        import csv

        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "timestamp",
                    "symbol",
                    "side",
                    "quantity",
                    "price",
                    "fees",
                    "pnl",
                ],
            )
            writer.writeheader()

            for trade in self.trades:
                writer.writerow(
                    {
                        "timestamp": trade["timestamp"].isoformat(),
                        "symbol": trade["symbol"],
                        "side": trade["side"],
                        "quantity": float(trade["quantity"]),
                        "price": float(trade["price"]),
                        "fees": float(trade["fees"]),
                        "pnl": float(trade["pnl"]),
                    }
                )

        logger.info(f"Exported {len(self.trades)} trades to {filepath}")
