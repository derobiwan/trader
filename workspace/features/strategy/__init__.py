"""
Trading Strategy Module

Algorithmic trading strategies for cryptocurrency markets.

Author: Strategy Implementation Team
Date: 2025-10-28
"""

from .base_strategy import BaseStrategy, StrategySignal, StrategyType
from .mean_reversion import MeanReversionStrategy
from .trend_following import TrendFollowingStrategy
from .volatility_breakout import VolatilityBreakoutStrategy

__all__ = [
    "BaseStrategy",
    "StrategySignal",
    "StrategyType",
    "MeanReversionStrategy",
    "TrendFollowingStrategy",
    "VolatilityBreakoutStrategy",
]
