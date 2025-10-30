"""
Dynamic Position Sizing with Kelly Criterion

Calculates optimal position sizes using the Kelly Criterion formula:
Kelly % = W - [(1-W)/R]

Where:
- W = Win rate (probability of winning)
- R = Win/Loss ratio (average win / average loss)

Implements fractional Kelly (25%) for more conservative sizing.

Author: Trading System Implementation Team
Date: 2025-10-29
Sprint: 3, Stream B, Task 044
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class TradeResult:
    """Individual trade result for Kelly calculation"""

    symbol: str
    entry_price: Decimal
    exit_price: Decimal
    quantity: Decimal
    pnl: Decimal  # Realized P&L
    is_win: bool
    timestamp: datetime


@dataclass
class PositionSizingResult:
    """Result of Kelly position sizing calculation"""

    win_rate: float
    avg_win: Decimal
    avg_loss: Decimal
    win_loss_ratio: float
    kelly_percentage: float
    fractional_kelly_percentage: float
    confidence_adjustment: float
    recommended_size_chf: Decimal
    max_kelly_fraction: float
    sample_size: int
    calculation_timestamp: datetime


class KellyPositionSizer:
    """
    Dynamic position sizing using Kelly Criterion.

    The Kelly Criterion optimizes position size to maximize long-term growth
    while managing risk of ruin.

    Features:
    - Full Kelly calculation from win rate and win/loss ratio
    - Fractional Kelly (default 25% of full Kelly) for conservatism
    - Confidence adjustment based on sample size
    - Historical trade analysis
    """

    def __init__(
        self,
        max_kelly_fraction: float = 0.25,
        min_sample_size: int = 20,
    ):
        """
        Initialize Kelly position sizer.

        Args:
            max_kelly_fraction: Maximum fraction of Kelly to use (0.25 = 25%)
            min_sample_size: Minimum trades needed for high confidence
        """
        self.max_kelly_fraction = max_kelly_fraction
        self.min_sample_size = min_sample_size

        logger.info(
            f"KellyPositionSizer initialized: "
            f"max_fraction={max_kelly_fraction:.1%}, "
            f"min_sample_size={min_sample_size}"
        )

    # ========================================================================
    # Kelly Criterion Calculation
    # ========================================================================

    def calculate_kelly_percentage(
        self,
        win_rate: float,
        avg_win: Decimal,
        avg_loss: Decimal,
    ) -> float:
        """
        Calculate full Kelly percentage.

        Formula: Kelly % = W - [(1-W)/R]
        Where:
        - W = Win rate (0.0 to 1.0)
        - R = Win/Loss ratio (avg_win / avg_loss)

        Args:
            win_rate: Probability of winning (0.0 to 1.0)
            avg_win: Average winning trade size
            avg_loss: Average losing trade size (positive value)

        Returns:
            Kelly percentage (0.0 to 1.0)
        """
        # Handle edge cases
        if win_rate <= 0 or win_rate >= 1:
            logger.warning(f"Invalid win rate: {win_rate:.2%}")
            return 0.0

        if avg_loss == 0:
            logger.warning("Average loss is zero, cannot calculate Kelly")
            return 0.0

        if avg_win <= 0:
            logger.warning("Average win is not positive, Kelly is zero")
            return 0.0

        # Calculate win/loss ratio
        win_loss_ratio = float(abs(avg_win / avg_loss))

        # Kelly formula: W - [(1-W)/R]
        kelly_pct = win_rate - ((1 - win_rate) / win_loss_ratio)

        # Kelly can be negative (negative expectancy strategy)
        if kelly_pct < 0:
            logger.warning(
                f"Negative Kelly percentage: {kelly_pct:.2%} "
                f"(win_rate={win_rate:.2%}, W/L ratio={win_loss_ratio:.2f})"
            )
            return 0.0

        # Cap at 100%
        kelly_pct = min(kelly_pct, 1.0)

        return kelly_pct

    def apply_fractional_kelly(
        self,
        full_kelly_pct: float,
        fraction: Optional[float] = None,
    ) -> float:
        """
        Apply fractional Kelly for more conservative sizing.

        Fractional Kelly reduces variance while maintaining positive expectancy.
        Common fractions: 0.5 (half Kelly), 0.25 (quarter Kelly)

        Args:
            full_kelly_pct: Full Kelly percentage
            fraction: Fraction to apply (uses self.max_kelly_fraction if None)

        Returns:
            Fractional Kelly percentage
        """
        if fraction is None:
            fraction = self.max_kelly_fraction

        fractional_kelly = full_kelly_pct * fraction

        logger.debug(
            f"Fractional Kelly: {full_kelly_pct:.2%} * {fraction:.2f} = "
            f"{fractional_kelly:.2%}"
        )

        return fractional_kelly

    def calculate_confidence_adjustment(self, sample_size: int) -> float:
        """
        Adjust Kelly based on sample size confidence.

        Smaller samples get conservative adjustment.

        Args:
            sample_size: Number of historical trades

        Returns:
            Confidence multiplier (0.0 to 1.0)
        """
        if sample_size < 5:
            # Very small sample: 50% confidence
            return 0.5

        if sample_size < 10:
            # Small sample: 70% confidence
            return 0.7

        if sample_size < self.min_sample_size:
            # Below minimum: scale from 70% to 100%
            return 0.7 + (0.3 * sample_size / self.min_sample_size)

        # Sufficient sample: full confidence
        return 1.0

    # ========================================================================
    # Position Size Calculation
    # ========================================================================

    def calculate_position_size(
        self,
        win_rate: float,
        avg_win: Decimal,
        avg_loss: Decimal,
        portfolio_value: Decimal,
        confidence_adjustment: Optional[float] = None,
    ) -> Decimal:
        """
        Calculate optimal position size using Kelly Criterion.

        Args:
            win_rate: Win rate (0.0 to 1.0)
            avg_win: Average winning trade
            avg_loss: Average losing trade (positive value)
            portfolio_value: Current portfolio value
            confidence_adjustment: Manual confidence adjustment (0.0 to 1.0)

        Returns:
            Recommended position size in CHF
        """
        # Calculate full Kelly
        kelly_pct = self.calculate_kelly_percentage(win_rate, avg_win, avg_loss)

        if kelly_pct <= 0:
            logger.info("Kelly percentage is zero or negative, position size = 0")
            return Decimal("0")

        # Apply fractional Kelly
        fractional_kelly = self.apply_fractional_kelly(kelly_pct)

        # Apply confidence adjustment if provided
        if confidence_adjustment is not None:
            fractional_kelly *= confidence_adjustment
            logger.debug(f"Applied confidence adjustment: {confidence_adjustment:.2f}")

        # Calculate position size
        position_size = portfolio_value * Decimal(str(fractional_kelly))

        logger.info(
            f"Position size calculated: {position_size:.2f} CHF "
            f"({fractional_kelly:.2%} of portfolio)"
        )

        return position_size

    # ========================================================================
    # Trade History Analysis
    # ========================================================================

    def analyze_trade_history(
        self,
        trades: List[TradeResult],
    ) -> dict:
        """
        Analyze trade history to extract Kelly parameters.

        Args:
            trades: List of historical trade results

        Returns:
            Dictionary with win_rate, avg_win, avg_loss, sample_size
        """
        if not trades:
            logger.warning("No trades provided for analysis")
            return {
                "win_rate": 0.0,
                "avg_win": Decimal("0"),
                "avg_loss": Decimal("0"),
                "sample_size": 0,
            }

        # Separate wins and losses
        wins = [t for t in trades if t.is_win]
        losses = [t for t in trades if not t.is_win]

        # Calculate win rate
        win_rate = len(wins) / len(trades) if trades else 0.0

        # Calculate average win
        avg_win = sum(t.pnl for t in wins) / len(wins) if wins else Decimal("0")

        # Calculate average loss (as positive value)
        avg_loss = (
            abs(sum(t.pnl for t in losses) / len(losses)) if losses else Decimal("0")
        )

        logger.info(
            f"Trade history analyzed: {len(trades)} trades, "
            f"win_rate={win_rate:.2%}, avg_win={avg_win:.2f}, "
            f"avg_loss={avg_loss:.2f}"
        )

        return {
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "sample_size": len(trades),
        }

    def calculate_from_trade_history(
        self,
        trade_history: List[TradeResult],
        portfolio_value: Decimal,
        lookback_days: Optional[int] = 30,
    ) -> PositionSizingResult:
        """
        Calculate position size from historical trade data.

        Args:
            trade_history: List of historical trades
            portfolio_value: Current portfolio value
            lookback_days: Only use trades from last N days (None = all)

        Returns:
            Complete position sizing result with all metrics
        """
        # Filter by lookback period if specified
        if lookback_days is not None:
            cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
            filtered_trades = [t for t in trade_history if t.timestamp >= cutoff_date]
            logger.info(
                f"Using {len(filtered_trades)} trades from last {lookback_days} days"
            )
        else:
            filtered_trades = trade_history

        # Analyze trade history
        analysis = self.analyze_trade_history(filtered_trades)

        win_rate = analysis["win_rate"]
        avg_win = analysis["avg_win"]
        avg_loss = analysis["avg_loss"]
        sample_size = analysis["sample_size"]

        # Calculate Kelly
        kelly_pct = self.calculate_kelly_percentage(win_rate, avg_win, avg_loss)
        fractional_kelly = self.apply_fractional_kelly(kelly_pct)

        # Apply confidence adjustment based on sample size
        confidence = self.calculate_confidence_adjustment(sample_size)
        adjusted_kelly = fractional_kelly * confidence

        # Calculate win/loss ratio
        win_loss_ratio = float(avg_win / avg_loss) if avg_loss > 0 else 0.0

        # Calculate recommended size
        recommended_size = portfolio_value * Decimal(str(adjusted_kelly))

        return PositionSizingResult(
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            win_loss_ratio=win_loss_ratio,
            kelly_percentage=kelly_pct,
            fractional_kelly_percentage=fractional_kelly,
            confidence_adjustment=confidence,
            recommended_size_chf=recommended_size,
            max_kelly_fraction=self.max_kelly_fraction,
            sample_size=sample_size,
            calculation_timestamp=datetime.utcnow(),
        )

    # ========================================================================
    # Variance and Risk Analysis
    # ========================================================================

    def calculate_variance_of_returns(self, trades: List[TradeResult]) -> Decimal:
        """
        Calculate variance of returns.

        Higher variance suggests more conservative fractional Kelly.

        Args:
            trades: Historical trades

        Returns:
            Variance of returns
        """
        if len(trades) < 2:
            return Decimal("0")

        pnls = [float(t.pnl) for t in trades]
        variance = Decimal(str(np.var(pnls)))

        return variance

    def recommend_kelly_fraction(self, trades: List[TradeResult]) -> float:
        """
        Recommend Kelly fraction based on variance.

        Higher variance → more conservative fraction.

        Args:
            trades: Historical trades

        Returns:
            Recommended Kelly fraction (0.1 to 0.5)
        """
        variance = self.calculate_variance_of_returns(trades)
        std_dev = float(variance) ** 0.5

        # High variance (std dev > 100): use 10% Kelly
        if std_dev > 100:
            return 0.1

        # Medium variance (50-100): use 20% Kelly
        if std_dev > 50:
            return 0.2

        # Low variance (<50): use 25% Kelly (default)
        return 0.25

    # ========================================================================
    # Reporting
    # ========================================================================

    def format_sizing_report(self, result: PositionSizingResult) -> str:
        """
        Format position sizing result as readable report.

        Args:
            result: Position sizing calculation result

        Returns:
            Formatted report string
        """
        report = f"""
╔════════════════════════════════════════════════════════════════╗
║              KELLY CRITERION POSITION SIZING                   ║
╠════════════════════════════════════════════════════════════════╣
║ Trade Statistics:                                              ║
║   Sample Size:        {result.sample_size:>4} trades                        ║
║   Win Rate:           {result.win_rate:>6.2%}                             ║
║   Average Win:        CHF {result.avg_win:>8.2f}                      ║
║   Average Loss:       CHF {result.avg_loss:>8.2f}                      ║
║   Win/Loss Ratio:     {result.win_loss_ratio:>6.2f}                             ║
║                                                                ║
║ Kelly Calculation:                                             ║
║   Full Kelly %:       {result.kelly_percentage:>6.2%}                             ║
║   Fractional Kelly:   {result.fractional_kelly_percentage:>6.2%} (×{result.max_kelly_fraction:.2f})                    ║
║   Confidence Adj:     {result.confidence_adjustment:>6.2%}                             ║
║                                                                ║
║ Recommendation:                                                ║
║   Position Size:      CHF {result.recommended_size_chf:>8.2f}                      ║
║                                                                ║
║ Calculated: {result.calculation_timestamp.strftime("%Y-%m-%d %H:%M:%S")}                      ║
╚════════════════════════════════════════════════════════════════╝
        """
        return report
