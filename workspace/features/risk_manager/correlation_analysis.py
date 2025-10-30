"""
Portfolio Correlation Analysis

Analyzes correlation between positions to assess portfolio diversification:
- Calculates correlation matrix for all positions
- Identifies highly correlated position pairs
- Calculates diversification score
- Monitors concentration risk

Author: Trading System Implementation Team
Date: 2025-10-29
Sprint: 3, Stream B, Task 045
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class PriceHistory:
    """Historical price data for a symbol"""

    symbol: str
    prices: List[Decimal]
    timestamps: List[datetime]


@dataclass
class CorrelationPair:
    """Pair of correlated positions"""

    symbol1: str
    symbol2: str
    correlation: float
    strength: str  # "WEAK", "MODERATE", "STRONG", "VERY_STRONG"


@dataclass
class CorrelationMatrix:
    """Complete correlation matrix for portfolio"""

    symbols: List[str]
    matrix: Dict[str, Dict[str, float]]
    highly_correlated_pairs: List[CorrelationPair]
    diversification_score: float
    timestamp: datetime


class CorrelationAnalyzer:
    """
    Analyzes correlation between portfolio positions.

    Features:
    - Calculate pairwise correlations
    - Identify highly correlated pairs
    - Calculate portfolio diversification score
    - Monitor concentration risk
    """

    def __init__(
        self,
        market_data_service,
        max_correlation_threshold: float = 0.7,
        lookback_days: int = 30,
    ):
        """
        Initialize correlation analyzer.

        Args:
            market_data_service: Service to fetch historical price data
            max_correlation_threshold: Correlation above this triggers alert
            lookback_days: Days of historical data to analyze
        """
        self.market_data_service = market_data_service
        self.max_correlation_threshold = max_correlation_threshold
        self.lookback_days = lookback_days

        logger.info(
            f"CorrelationAnalyzer initialized: "
            f"threshold={max_correlation_threshold:.2f}, "
            f"lookback={lookback_days} days"
        )

    # ========================================================================
    # Historical Data Fetching
    # ========================================================================

    async def fetch_price_history(
        self,
        symbols: List[str],
        days: Optional[int] = None,
    ) -> Dict[str, PriceHistory]:
        """
        Fetch historical price data for symbols.

        Args:
            symbols: List of trading symbols
            days: Days of history to fetch (uses lookback_days if None)

        Returns:
            Dictionary mapping symbol to PriceHistory
        """
        if days is None:
            days = self.lookback_days

        price_histories = {}

        for symbol in symbols:
            try:
                # Fetch OHLCV data
                ohlcv = await self.market_data_service.get_ohlcv(
                    symbol=symbol,
                    timeframe="1d",  # Daily candles
                    limit=days,
                )

                # Extract closing prices
                prices = [Decimal(str(candle[4])) for candle in ohlcv]
                timestamps = [
                    datetime.fromtimestamp(candle[0] / 1000) for candle in ohlcv
                ]

                price_histories[symbol] = PriceHistory(
                    symbol=symbol,
                    prices=prices,
                    timestamps=timestamps,
                )

                logger.debug(f"Fetched {len(prices)} price points for {symbol}")

            except Exception as e:
                logger.error(f"Failed to fetch price history for {symbol}: {e}")
                # Return empty history on error
                price_histories[symbol] = PriceHistory(
                    symbol=symbol,
                    prices=[],
                    timestamps=[],
                )

        return price_histories

    # ========================================================================
    # Returns Calculation
    # ========================================================================

    def calculate_returns(self, prices: List[Decimal]) -> List[float]:
        """
        Calculate percentage returns from price series.

        Args:
            prices: List of prices

        Returns:
            List of returns (price[i] - price[i-1]) / price[i-1]
        """
        if len(prices) < 2:
            return []

        returns = []
        for i in range(1, len(prices)):
            if prices[i - 1] == 0:
                continue
            ret = float((prices[i] - prices[i - 1]) / prices[i - 1])
            returns.append(ret)

        return returns

    # ========================================================================
    # Correlation Calculation
    # ========================================================================

    def calculate_correlation(
        self,
        returns1: List[float],
        returns2: List[float],
    ) -> float:
        """
        Calculate Pearson correlation coefficient between two return series.

        Args:
            returns1: First return series
            returns2: Second return series

        Returns:
            Correlation coefficient (-1.0 to 1.0)
        """
        if len(returns1) < 2 or len(returns2) < 2:
            return 0.0

        if len(returns1) != len(returns2):
            logger.warning(
                f"Return series lengths differ: {len(returns1)} vs {len(returns2)}"
            )
            # Truncate to shorter length
            min_len = min(len(returns1), len(returns2))
            returns1 = returns1[:min_len]
            returns2 = returns2[:min_len]

        try:
            correlation = float(np.corrcoef(returns1, returns2)[0, 1])

            # Handle NaN (can occur with constant returns)
            if np.isnan(correlation):
                return 0.0

            return correlation

        except Exception as e:
            logger.error(f"Error calculating correlation: {e}")
            return 0.0

    async def calculate_portfolio_correlation(
        self,
        symbols: List[str],
        days: Optional[int] = None,
    ) -> CorrelationMatrix:
        """
        Calculate full correlation matrix for portfolio.

        Args:
            symbols: List of symbols in portfolio
            days: Days of history to analyze

        Returns:
            Complete correlation matrix
        """
        if len(symbols) < 2:
            logger.info("Less than 2 symbols, no correlation to calculate")
            return CorrelationMatrix(
                symbols=symbols,
                matrix={},
                highly_correlated_pairs=[],
                diversification_score=1.0,
                timestamp=datetime.utcnow(),
            )

        # Fetch price histories
        price_histories = await self.fetch_price_history(symbols, days)

        # Calculate returns for each symbol
        returns_map = {}
        for symbol, history in price_histories.items():
            returns = self.calculate_returns(history.prices)
            returns_map[symbol] = returns
            logger.debug(f"{symbol}: {len(returns)} return points")

        # Calculate correlation matrix
        matrix: dict[str, dict[str, float]] = {}
        for symbol1 in symbols:
            matrix[symbol1] = {}
            for symbol2 in symbols:
                if symbol1 == symbol2:
                    correlation = 1.0
                else:
                    correlation = self.calculate_correlation(
                        returns_map.get(symbol1, []),
                        returns_map.get(symbol2, []),
                    )
                matrix[symbol1][symbol2] = correlation

        # Identify highly correlated pairs
        highly_correlated = self.check_correlation_limits(matrix)

        # Calculate diversification score
        diversification_score = self.calculate_diversification_score(matrix)

        logger.info(
            f"Correlation matrix calculated for {len(symbols)} symbols, "
            f"diversification score: {diversification_score:.2f}"
        )

        return CorrelationMatrix(
            symbols=symbols,
            matrix=matrix,
            highly_correlated_pairs=highly_correlated,
            diversification_score=diversification_score,
            timestamp=datetime.utcnow(),
        )

    # ========================================================================
    # Correlation Analysis
    # ========================================================================

    def check_correlation_limits(
        self,
        correlation_matrix: Dict[str, Dict[str, float]],
        max_correlation: Optional[float] = None,
    ) -> List[CorrelationPair]:
        """
        Identify pairs exceeding correlation threshold.

        Args:
            correlation_matrix: Full correlation matrix
            max_correlation: Threshold (uses self.max_correlation_threshold if None)

        Returns:
            List of highly correlated pairs
        """
        if max_correlation is None:
            max_correlation = self.max_correlation_threshold

        highly_correlated = []

        # Check all pairs (only once per pair)
        processed_pairs = set()

        for symbol1, correlations in correlation_matrix.items():
            for symbol2, corr in correlations.items():
                # Skip self-correlation
                if symbol1 == symbol2:
                    continue

                # Skip if pair already processed (avoid duplicates)
                pair_key = tuple(sorted([symbol1, symbol2]))
                if pair_key in processed_pairs:
                    continue

                processed_pairs.add(pair_key)

                # Check if correlation exceeds threshold
                if abs(corr) > max_correlation:
                    strength = self.classify_correlation_strength(abs(corr))

                    pair = CorrelationPair(
                        symbol1=symbol1,
                        symbol2=symbol2,
                        correlation=corr,
                        strength=strength,
                    )

                    highly_correlated.append(pair)

                    logger.warning(
                        f"High correlation detected: {symbol1} <-> {symbol2} "
                        f"= {corr:.3f} ({strength})"
                    )

        return highly_correlated

    def classify_correlation_strength(self, correlation: float) -> str:
        """
        Classify correlation strength.

        Args:
            correlation: Absolute correlation value

        Returns:
            Strength classification
        """
        if correlation < 0.3:
            return "WEAK"
        elif correlation < 0.5:
            return "MODERATE"
        elif correlation < 0.7:
            return "STRONG"
        else:
            return "VERY_STRONG"

    def calculate_diversification_score(
        self,
        correlation_matrix: Dict[str, Dict[str, float]],
    ) -> float:
        """
        Calculate portfolio diversification score (0.0 to 1.0).

        Lower average correlation = higher diversification.

        Score:
        - 1.0 = Perfect diversification (zero correlation)
        - 0.5 = Moderate diversification
        - 0.0 = No diversification (perfect correlation)

        Args:
            correlation_matrix: Full correlation matrix

        Returns:
            Diversification score (0.0 to 1.0)
        """
        if not correlation_matrix:
            return 1.0

        # Collect all off-diagonal correlations (excluding self-correlation)
        correlations = []
        for symbol1, corrs in correlation_matrix.items():
            for symbol2, corr in corrs.items():
                if symbol1 != symbol2:
                    correlations.append(abs(corr))

        if not correlations:
            return 1.0

        # Calculate average absolute correlation
        avg_correlation = sum(correlations) / len(correlations)

        # Diversification score = 1 - average correlation
        diversification_score = 1.0 - avg_correlation

        return max(0.0, min(1.0, diversification_score))

    # ========================================================================
    # Risk Assessment
    # ========================================================================

    def assess_correlation_risk(
        self,
        correlation_matrix: CorrelationMatrix,
    ) -> Tuple[str, List[str]]:
        """
        Assess overall correlation risk level.

        Args:
            correlation_matrix: Portfolio correlation matrix

        Returns:
            Tuple of (risk_level, warnings)
        """
        warnings = []

        # Check diversification score
        if correlation_matrix.diversification_score < 0.3:
            warnings.append(
                f"Poor diversification (score: {correlation_matrix.diversification_score:.2f})"
            )
            risk_level = "HIGH"

        elif correlation_matrix.diversification_score < 0.5:
            warnings.append(
                f"Moderate diversification (score: {correlation_matrix.diversification_score:.2f})"
            )
            risk_level = "MEDIUM"

        else:
            risk_level = "LOW"

        # Check highly correlated pairs
        num_high_corr = len(correlation_matrix.highly_correlated_pairs)
        if num_high_corr > 0:
            warnings.append(
                f"{num_high_corr} highly correlated position pair(s) detected"
            )

            # Count VERY_STRONG correlations
            very_strong = [
                p
                for p in correlation_matrix.highly_correlated_pairs
                if p.strength == "VERY_STRONG"
            ]

            if very_strong:
                warnings.append(
                    f"{len(very_strong)} position pair(s) with VERY STRONG correlation"
                )
                if risk_level == "LOW":
                    risk_level = "MEDIUM"

        if risk_level != "LOW":
            logger.warning(
                f"Correlation risk level: {risk_level}, warnings: {warnings}"
            )

        return risk_level, warnings

    # ========================================================================
    # Reporting
    # ========================================================================

    def format_correlation_report(
        self,
        correlation_matrix: CorrelationMatrix,
    ) -> str:
        """
        Format correlation matrix as readable report.

        Args:
            correlation_matrix: Correlation matrix to format

        Returns:
            Formatted report string
        """
        symbols = correlation_matrix.symbols

        # Header
        report = "\n" + "═" * 80 + "\n"
        report += "PORTFOLIO CORRELATION ANALYSIS\n"
        report += "═" * 80 + "\n\n"

        # Diversification score
        score = correlation_matrix.diversification_score
        report += f"Diversification Score: {score:.2f} / 1.00 "

        if score >= 0.7:
            report += "(Excellent)\n"
        elif score >= 0.5:
            report += "(Good)\n"
        elif score >= 0.3:
            report += "(Moderate)\n"
        else:
            report += "(Poor)\n"

        report += "\n"

        # Correlation matrix
        report += "Correlation Matrix:\n"
        report += "-" * 80 + "\n"

        # Table header
        report += f"{'Symbol':<12}"
        for symbol in symbols:
            report += f"{symbol:<12}"
        report += "\n"

        # Table rows
        for symbol1 in symbols:
            report += f"{symbol1:<12}"
            for symbol2 in symbols:
                corr = correlation_matrix.matrix[symbol1][symbol2]
                report += f"{corr:>11.3f} "
            report += "\n"

        # Highly correlated pairs
        if correlation_matrix.highly_correlated_pairs:
            report += "\n"
            report += (
                "⚠️  Highly Correlated Pairs (>"
                + f"{self.max_correlation_threshold:.0%}):\n"
            )
            report += "-" * 80 + "\n"

            for pair in correlation_matrix.highly_correlated_pairs:
                report += (
                    f"  {pair.symbol1} <-> {pair.symbol2}: "
                    f"{pair.correlation:>6.3f} ({pair.strength})\n"
                )

        report += "\n" + "═" * 80 + "\n"

        return report
