"""
Risk Metrics Calculator

Calculates comprehensive risk and performance metrics:
- Sharpe Ratio: Risk-adjusted return
- Sortino Ratio: Downside risk-adjusted return
- Maximum Drawdown: Peak-to-trough decline
- Value at Risk (VaR): Loss at confidence level
- Conditional VaR (CVaR): Expected loss beyond VaR
- Calmar Ratio: Return / Max Drawdown
- Win Rate, Profit Factor, and other performance metrics

Author: Trading System Implementation Team
Date: 2025-10-29
Sprint: 3, Stream B, Task 045
"""

import logging
from decimal import Decimal
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class RiskMetrics:
    """Complete set of risk and performance metrics"""

    # Return metrics
    total_return: Decimal
    total_return_pct: float
    annualized_return: float

    # Risk metrics
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: Decimal
    max_drawdown_pct: float
    value_at_risk_95: float
    value_at_risk_99: float
    conditional_var_95: float
    calmar_ratio: float

    # Volatility metrics
    volatility: float
    downside_deviation: float

    # Performance metrics
    win_rate: float
    profit_factor: float
    win_loss_ratio: float

    # Trade statistics
    total_trades: int
    winning_trades: int
    losing_trades: int
    largest_win: Decimal
    largest_loss: Decimal
    average_win: Decimal
    average_loss: Decimal

    # Meta
    calculation_period_days: int
    calculation_timestamp: datetime


class RiskMetricsCalculator:
    """
    Calculate comprehensive risk and performance metrics.

    All metrics are industry-standard implementations used by
    professional traders and fund managers.
    """

    def __init__(
        self,
        risk_free_rate: float = 0.02,  # 2% annual risk-free rate
        trading_days_per_year: int = 365,  # Crypto trades 365 days/year
    ):
        """
        Initialize risk metrics calculator.

        Args:
            risk_free_rate: Annual risk-free rate (default 2%)
            trading_days_per_year: Trading days per year (365 for crypto)
        """
        self.risk_free_rate = risk_free_rate
        self.trading_days_per_year = trading_days_per_year

        logger.info(
            f"RiskMetricsCalculator initialized: "
            f"risk_free_rate={risk_free_rate:.2%}, "
            f"trading_days={trading_days_per_year}"
        )

    # ========================================================================
    # Risk-Adjusted Return Metrics
    # ========================================================================

    def calculate_sharpe_ratio(
        self,
        returns: List[float],
        risk_free_rate: Optional[float] = None,
    ) -> float:
        """
        Calculate Sharpe Ratio.

        Sharpe Ratio = (Return - Risk Free Rate) / Standard Deviation

        Higher is better. Typical values:
        - < 1.0: Subpar
        - 1.0-2.0: Good
        - 2.0-3.0: Very good
        - > 3.0: Excellent

        Args:
            returns: List of period returns
            risk_free_rate: Risk-free rate (uses self.risk_free_rate if None)

        Returns:
            Sharpe ratio
        """
        if not returns or len(returns) < 2:
            return 0.0

        if risk_free_rate is None:
            risk_free_rate = self.risk_free_rate

        # Convert annual risk-free rate to period rate
        period_rf_rate = risk_free_rate / self.trading_days_per_year

        # Calculate excess returns
        excess_returns = [r - period_rf_rate for r in returns]

        # Mean excess return
        mean_excess = np.mean(excess_returns)

        # Standard deviation of returns
        std_dev = np.std(returns, ddof=1)

        if std_dev == 0:
            return 0.0

        # Annualize Sharpe ratio
        sharpe = (mean_excess / std_dev) * np.sqrt(self.trading_days_per_year)

        return float(sharpe)

    def calculate_sortino_ratio(
        self,
        returns: List[float],
        risk_free_rate: Optional[float] = None,
    ) -> float:
        """
        Calculate Sortino Ratio.

        Sortino Ratio = (Return - Risk Free Rate) / Downside Deviation

        Similar to Sharpe but only penalizes downside volatility.
        Higher is better.

        Args:
            returns: List of period returns
            risk_free_rate: Risk-free rate (uses self.risk_free_rate if None)

        Returns:
            Sortino ratio
        """
        if not returns or len(returns) < 2:
            return 0.0

        if risk_free_rate is None:
            risk_free_rate = self.risk_free_rate

        period_rf_rate = risk_free_rate / self.trading_days_per_year

        # Mean return
        mean_return = np.mean(returns)

        # Downside deviation (only negative returns)
        downside_returns = [r for r in returns if r < 0]

        if not downside_returns:
            # No losses: infinite Sortino (cap at 10.0)
            return 10.0

        downside_dev = np.std(downside_returns, ddof=1)

        if downside_dev == 0:
            return 0.0

        # Annualize Sortino ratio
        sortino = ((mean_return - period_rf_rate) / downside_dev) * np.sqrt(
            self.trading_days_per_year
        )

        return float(sortino)

    # ========================================================================
    # Drawdown Metrics
    # ========================================================================

    def calculate_max_drawdown(
        self, equity_curve: List[Decimal]
    ) -> tuple[Decimal, float]:
        """
        Calculate maximum drawdown.

        Maximum Drawdown = (Trough Value - Peak Value) / Peak Value

        Measures worst peak-to-trough decline.

        Args:
            equity_curve: List of portfolio values over time

        Returns:
            Tuple of (max_drawdown_abs, max_drawdown_pct)
        """
        if not equity_curve or len(equity_curve) < 2:
            return Decimal("0"), 0.0

        peak = equity_curve[0]
        max_dd = Decimal("0")
        max_dd_pct = 0.0

        for value in equity_curve:
            # Update peak if new high
            if value > peak:
                peak = value

            # Calculate drawdown from peak
            dd = peak - value
            dd_pct = float(dd / peak) if peak > 0 else 0.0

            # Update max drawdown
            if dd > max_dd:
                max_dd = dd
                max_dd_pct = dd_pct

        return max_dd, max_dd_pct

    def calculate_calmar_ratio(
        self,
        annualized_return: float,
        max_drawdown_pct: float,
    ) -> float:
        """
        Calculate Calmar Ratio.

        Calmar Ratio = Annualized Return / Maximum Drawdown

        Higher is better. Typical values:
        - < 0.5: Poor
        - 0.5-1.0: Average
        - 1.0-3.0: Good
        - > 3.0: Excellent

        Args:
            annualized_return: Annualized return (as decimal, e.g., 0.25 for 25%)
            max_drawdown_pct: Maximum drawdown (as decimal, e.g., 0.15 for 15%)

        Returns:
            Calmar ratio
        """
        if max_drawdown_pct == 0:
            # No drawdown: cap at 10.0
            return 10.0 if annualized_return > 0 else 0.0

        calmar = annualized_return / max_drawdown_pct

        return float(calmar)

    # ========================================================================
    # Value at Risk (VaR) and CVaR
    # ========================================================================

    def calculate_var(
        self,
        returns: List[float],
        confidence: float = 0.95,
    ) -> float:
        """
        Calculate Value at Risk (VaR).

        VaR = Loss threshold at given confidence level

        Example: VaR(95%) = -2.5% means 95% of days have losses < 2.5%

        Args:
            returns: List of period returns
            confidence: Confidence level (0.95 or 0.99)

        Returns:
            VaR (as negative return, e.g., -0.025 for -2.5%)
        """
        if not returns or len(returns) < 2:
            return 0.0

        # Calculate percentile (lower tail)
        percentile = (1 - confidence) * 100
        var = float(np.percentile(returns, percentile))

        return var

    def calculate_cvar(
        self,
        returns: List[float],
        confidence: float = 0.95,
    ) -> float:
        """
        Calculate Conditional Value at Risk (CVaR / Expected Shortfall).

        CVaR = Expected loss given that loss exceeds VaR

        More conservative than VaR (measures tail risk).

        Args:
            returns: List of period returns
            confidence: Confidence level (0.95 or 0.99)

        Returns:
            CVaR (as negative return)
        """
        if not returns or len(returns) < 2:
            return 0.0

        # Calculate VaR
        var = self.calculate_var(returns, confidence)

        # Calculate expected value of returns below VaR
        tail_returns = [r for r in returns if r <= var]

        if not tail_returns:
            return var

        cvar = float(np.mean(tail_returns))

        return cvar

    # ========================================================================
    # Performance Metrics
    # ========================================================================

    def calculate_win_rate(
        self,
        winning_trades: int,
        total_trades: int,
    ) -> float:
        """
        Calculate win rate.

        Win Rate = Winning Trades / Total Trades

        Args:
            winning_trades: Number of winning trades
            total_trades: Total number of trades

        Returns:
            Win rate (0.0 to 1.0)
        """
        if total_trades == 0:
            return 0.0

        return winning_trades / total_trades

    def calculate_profit_factor(
        self,
        total_wins: Decimal,
        total_losses: Decimal,
    ) -> float:
        """
        Calculate profit factor.

        Profit Factor = Total Wins / Total Losses

        Typical values:
        - < 1.0: Losing strategy
        - 1.0-1.5: Marginal
        - 1.5-2.0: Good
        - > 2.0: Excellent

        Args:
            total_wins: Sum of all winning trades
            total_losses: Sum of all losing trades (as positive value)

        Returns:
            Profit factor
        """
        if total_losses == 0:
            return 10.0 if total_wins > 0 else 0.0

        return float(total_wins / total_losses)

    def calculate_win_loss_ratio(
        self,
        avg_win: Decimal,
        avg_loss: Decimal,
    ) -> float:
        """
        Calculate win/loss ratio.

        Win/Loss Ratio = Average Win / Average Loss

        Args:
            avg_win: Average winning trade
            avg_loss: Average losing trade (as positive value)

        Returns:
            Win/loss ratio
        """
        if avg_loss == 0:
            return 10.0 if avg_win > 0 else 0.0

        return float(avg_win / avg_loss)

    # ========================================================================
    # Volatility Metrics
    # ========================================================================

    def calculate_volatility(self, returns: List[float]) -> float:
        """
        Calculate annualized volatility (standard deviation).

        Args:
            returns: List of period returns

        Returns:
            Annualized volatility
        """
        if not returns or len(returns) < 2:
            return 0.0

        # Calculate standard deviation
        std_dev = np.std(returns, ddof=1)

        # Annualize
        annualized_vol = std_dev * np.sqrt(self.trading_days_per_year)

        return float(annualized_vol)

    def calculate_downside_deviation(self, returns: List[float]) -> float:
        """
        Calculate downside deviation (volatility of negative returns).

        Args:
            returns: List of period returns

        Returns:
            Annualized downside deviation
        """
        if not returns or len(returns) < 2:
            return 0.0

        # Extract negative returns
        downside_returns = [r for r in returns if r < 0]

        if not downside_returns:
            return 0.0

        # Calculate standard deviation of downside
        downside_std = np.std(downside_returns, ddof=1)

        # Annualize
        annualized_downside = downside_std * np.sqrt(self.trading_days_per_year)

        return float(annualized_downside)

    # ========================================================================
    # All Metrics Calculation
    # ========================================================================

    def calculate_all_metrics(
        self,
        returns: List[float],
        equity_curve: List[Decimal],
        initial_balance: Decimal,
        winning_trades: Optional[int] = None,
        losing_trades: Optional[int] = None,
        total_wins: Optional[Decimal] = None,
        total_losses: Optional[Decimal] = None,
        largest_win: Optional[Decimal] = None,
        largest_loss: Optional[Decimal] = None,
    ) -> RiskMetrics:
        """
        Calculate all risk and performance metrics.

        Args:
            returns: List of period returns
            equity_curve: List of portfolio values over time
            initial_balance: Starting portfolio value
            winning_trades: Number of winning trades (calculated if None)
            losing_trades: Number of losing trades (calculated if None)
            total_wins: Sum of winning trades (calculated if None)
            total_losses: Sum of losing trades (calculated if None)
            largest_win: Largest single win (calculated if None)
            largest_loss: Largest single loss (calculated if None)

        Returns:
            Complete RiskMetrics object
        """
        # Calculate from returns if trade stats not provided
        if winning_trades is None:
            winning_trades = sum(1 for r in returns if r > 0)
        if losing_trades is None:
            losing_trades = sum(1 for r in returns if r < 0)

        total_trades = winning_trades + losing_trades

        # Calculate totals if not provided
        if total_wins is None:
            total_wins = Decimal(str(sum(r for r in returns if r > 0)))
        if total_losses is None:
            total_losses = Decimal(str(abs(sum(r for r in returns if r < 0))))

        # Calculate averages
        avg_win = total_wins / winning_trades if winning_trades > 0 else Decimal("0")
        avg_loss = total_losses / losing_trades if losing_trades > 0 else Decimal("0")

        # Find largest win/loss if not provided
        if largest_win is None:
            largest_win = (
                Decimal(str(max(r for r in returns if r > 0)))
                if winning_trades > 0
                else Decimal("0")
            )
        if largest_loss is None:
            largest_loss = (
                Decimal(str(min(r for r in returns if r < 0)))
                if losing_trades > 0
                else Decimal("0")
            )

        # Calculate return metrics
        final_balance = equity_curve[-1] if equity_curve else initial_balance
        total_return = final_balance - initial_balance
        total_return_pct = (
            float(total_return / initial_balance) if initial_balance > 0 else 0.0
        )

        # Annualize return
        num_periods = len(returns) if returns else 1
        annualized_return = (1 + total_return_pct) ** (
            self.trading_days_per_year / num_periods
        ) - 1

        # Calculate risk metrics
        sharpe = self.calculate_sharpe_ratio(returns)
        sortino = self.calculate_sortino_ratio(returns)
        max_dd, max_dd_pct = self.calculate_max_drawdown(equity_curve)
        var_95 = self.calculate_var(returns, 0.95)
        var_99 = self.calculate_var(returns, 0.99)
        cvar_95 = self.calculate_cvar(returns, 0.95)
        calmar = self.calculate_calmar_ratio(annualized_return, max_dd_pct)

        # Calculate volatility metrics
        volatility = self.calculate_volatility(returns)
        downside_dev = self.calculate_downside_deviation(returns)

        # Calculate performance metrics
        win_rate = self.calculate_win_rate(winning_trades, total_trades)
        profit_factor = self.calculate_profit_factor(total_wins, total_losses)
        win_loss_ratio = self.calculate_win_loss_ratio(avg_win, avg_loss)

        return RiskMetrics(
            # Return metrics
            total_return=total_return,
            total_return_pct=total_return_pct,
            annualized_return=annualized_return,
            # Risk metrics
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            max_drawdown=max_dd,
            max_drawdown_pct=max_dd_pct,
            value_at_risk_95=var_95,
            value_at_risk_99=var_99,
            conditional_var_95=cvar_95,
            calmar_ratio=calmar,
            # Volatility metrics
            volatility=volatility,
            downside_deviation=downside_dev,
            # Performance metrics
            win_rate=win_rate,
            profit_factor=profit_factor,
            win_loss_ratio=win_loss_ratio,
            # Trade statistics
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            largest_win=largest_win,
            largest_loss=largest_loss,
            average_win=avg_win,
            average_loss=avg_loss,
            # Meta
            calculation_period_days=len(returns),
            calculation_timestamp=datetime.utcnow(),
        )

    # ========================================================================
    # Reporting
    # ========================================================================

    def format_metrics_report(self, metrics: RiskMetrics) -> str:
        """
        Format risk metrics as readable report.

        Args:
            metrics: Calculated risk metrics

        Returns:
            Formatted report string
        """
        report = "\n" + "═" * 80 + "\n"
        report += "RISK & PERFORMANCE METRICS\n"
        report += "═" * 80 + "\n\n"

        # Return Metrics
        report += "📊 RETURN METRICS:\n"
        report += f"  Total Return:        {metrics.total_return:>10.2f} CHF ({metrics.total_return_pct:>6.2%})\n"
        report += f"  Annualized Return:   {metrics.annualized_return:>13.2%}\n\n"

        # Risk-Adjusted Returns
        report += "📈 RISK-ADJUSTED RETURNS:\n"
        report += f"  Sharpe Ratio:        {metrics.sharpe_ratio:>10.2f}\n"
        report += f"  Sortino Ratio:       {metrics.sortino_ratio:>10.2f}\n"
        report += f"  Calmar Ratio:        {metrics.calmar_ratio:>10.2f}\n\n"

        # Drawdown
        report += "📉 DRAWDOWN:\n"
        report += f"  Maximum Drawdown:    {metrics.max_drawdown:>10.2f} CHF ({metrics.max_drawdown_pct:>6.2%})\n\n"

        # Value at Risk
        report += "⚠️  VALUE AT RISK:\n"
        report += f"  VaR (95%):           {metrics.value_at_risk_95:>13.2%}\n"
        report += f"  VaR (99%):           {metrics.value_at_risk_99:>13.2%}\n"
        report += f"  CVaR (95%):          {metrics.conditional_var_95:>13.2%}\n\n"

        # Volatility
        report += "📊 VOLATILITY:\n"
        report += f"  Volatility:          {metrics.volatility:>13.2%}\n"
        report += f"  Downside Deviation:  {metrics.downside_deviation:>13.2%}\n\n"

        # Performance
        report += "🎯 PERFORMANCE:\n"
        report += f"  Win Rate:            {metrics.win_rate:>13.2%}\n"
        report += f"  Profit Factor:       {metrics.profit_factor:>10.2f}\n"
        report += f"  Win/Loss Ratio:      {metrics.win_loss_ratio:>10.2f}\n\n"

        # Trade Statistics
        report += "📝 TRADE STATISTICS:\n"
        report += f"  Total Trades:        {metrics.total_trades:>10}\n"
        report += f"  Winning Trades:      {metrics.winning_trades:>10}\n"
        report += f"  Losing Trades:       {metrics.losing_trades:>10}\n"
        report += f"  Largest Win:         {metrics.largest_win:>10.2f} CHF\n"
        report += f"  Largest Loss:        {metrics.largest_loss:>10.2f} CHF\n"
        report += f"  Average Win:         {metrics.average_win:>10.2f} CHF\n"
        report += f"  Average Loss:        {metrics.average_loss:>10.2f} CHF\n\n"

        report += "═" * 80 + "\n"

        return report
