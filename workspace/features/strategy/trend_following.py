"""
Trend Following Strategy

EMA crossover trend following strategy for cryptocurrency trading.

Author: Strategy Implementation Team
Date: 2025-10-28
"""

import logging
from decimal import Decimal
from typing import Dict, Any, Optional

from workspace.features.market_data import MarketDataSnapshot
from workspace.features.trading_loop import TradingDecision
from .base_strategy import BaseStrategy, StrategySignal, StrategyType


logger = logging.getLogger(__name__)


class TrendFollowingStrategy(BaseStrategy):
    """
    Trend Following Strategy

    Trades based on EMA crossovers and trend strength,
    following established market trends.

    Strategy Logic:
    - BUY when Fast EMA crosses above Slow EMA (bullish crossover)
    - SELL when Fast EMA crosses below Slow EMA (bearish crossover)
    - HOLD when no clear trend or crossover

    Uses additional confirmation:
    - MACD histogram for momentum
    - RSI to avoid extreme conditions
    - Price action (higher highs/lower lows)

    Configuration:
    - ema_fast_period: Fast EMA period (default: 12)
    - ema_slow_period: Slow EMA period (default: 26)
    - min_ema_distance_pct: Minimum distance between EMAs (default: 0.5%)
    - use_macd: Use MACD confirmation (default: True)
    - use_rsi_filter: Filter trades in extreme RSI (default: True)
    - position_size_pct: Base position size (default: 0.15 = 15%)
    - stop_loss_pct: Stop-loss distance (default: 0.025 = 2.5%)
    - take_profit_pct: Take-profit distance (default: 0.06 = 6%)

    Example:
        ```python
        strategy = TrendFollowingStrategy(config={
            'min_ema_distance_pct': 0.8,
            'position_size_pct': 0.18,
        })

        signal = strategy.analyze(snapshot)
        ```
    """

    DEFAULT_CONFIG = {
        "ema_fast_period": 12,
        "ema_slow_period": 26,
        "min_ema_distance_pct": 0.5,  # 0.5% minimum distance
        "use_macd": True,
        "use_rsi_filter": True,
        "rsi_extreme_low": 20,  # Don't sell below this
        "rsi_extreme_high": 80,  # Don't buy above this
        "position_size_pct": 0.15,
        "stop_loss_pct": 0.025,
        "take_profit_pct": 0.06,
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Trend Following Strategy

        Args:
            config: Strategy configuration (uses DEFAULT_CONFIG as base)
        """
        # Merge with defaults
        merged_config = self.DEFAULT_CONFIG.copy()
        if config:
            merged_config.update(config)

        super().__init__(merged_config)

        # Extract config values
        self.ema_fast_period = self.config["ema_fast_period"]
        self.ema_slow_period = self.config["ema_slow_period"]
        self.min_ema_distance_pct = Decimal(str(self.config["min_ema_distance_pct"]))
        self.use_macd = self.config["use_macd"]
        self.use_rsi_filter = self.config["use_rsi_filter"]
        self.rsi_extreme_low = Decimal(str(self.config["rsi_extreme_low"]))
        self.rsi_extreme_high = Decimal(str(self.config["rsi_extreme_high"]))
        self.position_size_pct = Decimal(str(self.config["position_size_pct"]))
        self.stop_loss_pct = Decimal(str(self.config["stop_loss_pct"]))
        self.take_profit_pct = Decimal(str(self.config["take_profit_pct"]))

    def get_name(self) -> str:
        """Get strategy name"""
        return "Trend Following (EMA Crossover)"

    def get_type(self) -> StrategyType:
        """Get strategy type"""
        return StrategyType.TREND_FOLLOWING

    def analyze(self, snapshot: MarketDataSnapshot) -> StrategySignal:
        """
        Analyze market data and generate signal

        Args:
            snapshot: Market data snapshot

        Returns:
            StrategySignal with trading decision
        """
        # Validate snapshot
        if not self.validate_snapshot(snapshot):
            return self._generate_hold_signal(snapshot.symbol, "Invalid snapshot data")

        # Check if EMAs are available
        if not snapshot.ema_fast or not snapshot.ema_slow:
            return self._generate_hold_signal(snapshot.symbol, "EMAs not available")

        ema_fast = snapshot.ema_fast.value
        ema_slow = snapshot.ema_slow.value
        current_price = snapshot.ticker.last

        # Calculate EMA distance
        ema_distance = abs(ema_fast - ema_slow)
        ema_distance_pct = (ema_distance / ema_slow) * Decimal("100")

        # Check minimum distance (avoid whipsaws)
        if ema_distance_pct < self.min_ema_distance_pct:
            return self._generate_hold_signal(
                snapshot.symbol,
                f"EMA distance too small ({ema_distance_pct:.2f}%), potential whipsaw",
            )

        # Determine trend direction
        if ema_fast > ema_slow:
            # Bullish trend
            decision = TradingDecision.BUY
            confidence = self._calculate_buy_confidence(snapshot, ema_distance_pct)
            reasoning_parts = [
                f"Bullish trend (Fast EMA ${ema_fast:,.2f} > Slow EMA ${ema_slow:,.2f})"
            ]

        else:
            # Bearish trend
            decision = TradingDecision.SELL
            confidence = self._calculate_sell_confidence(snapshot, ema_distance_pct)
            reasoning_parts = [
                f"Bearish trend (Fast EMA ${ema_fast:,.2f} < Slow EMA ${ema_slow:,.2f})"
            ]

        # Apply RSI filter
        if self.use_rsi_filter and snapshot.rsi:
            rsi_filter = self._apply_rsi_filter(decision, snapshot.rsi.value)
            if rsi_filter:
                return self._generate_hold_signal(snapshot.symbol, rsi_filter)

        # Add MACD confirmation
        if self.use_macd and snapshot.macd:
            macd_conf = self._check_macd_confirmation(decision, snapshot)
            if macd_conf:
                confidence = min(confidence + Decimal("0.1"), Decimal("1.0"))
                reasoning_parts.append(macd_conf)

        # Calculate position size based on confidence
        size_pct = self.position_size_pct * confidence

        # Build reasoning
        reasoning = ". ".join(reasoning_parts) + "."

        # Create signal
        signal = StrategySignal(
            symbol=snapshot.symbol,
            decision=decision,
            confidence=confidence,
            size_pct=size_pct,
            stop_loss_pct=self.stop_loss_pct,
            take_profit_pct=self.take_profit_pct,
            reasoning=reasoning,
            strategy_name=self.get_name(),
            metadata={
                "ema_fast": float(ema_fast),
                "ema_slow": float(ema_slow),
                "ema_distance_pct": float(ema_distance_pct),
                "price": float(current_price),
            },
        )

        self._record_signal(signal)
        return signal

    def _calculate_buy_confidence(
        self,
        snapshot: MarketDataSnapshot,
        ema_distance_pct: Decimal,
    ) -> Decimal:
        """Calculate confidence for BUY signal"""
        # Base confidence from EMA distance (wider = stronger trend)
        # 0.5% distance -> 0.6, 1.0% -> 0.7, 2.0% -> 0.8
        distance_conf = Decimal("0.6") + (ema_distance_pct / Decimal("5"))
        confidence = max(Decimal("0.6"), min(distance_conf, Decimal("0.9")))

        return confidence

    def _calculate_sell_confidence(
        self,
        snapshot: MarketDataSnapshot,
        ema_distance_pct: Decimal,
    ) -> Decimal:
        """Calculate confidence for SELL signal"""
        # Same logic as buy (symmetric)
        distance_conf = Decimal("0.6") + (ema_distance_pct / Decimal("5"))
        confidence = max(Decimal("0.6"), min(distance_conf, Decimal("0.9")))

        return confidence

    def _apply_rsi_filter(
        self,
        decision: TradingDecision,
        rsi_value: Decimal,
    ) -> Optional[str]:
        """
        Apply RSI filter to avoid extreme conditions

        Returns filter message if trade should be filtered, None otherwise
        """
        if decision == TradingDecision.BUY:
            # Don't buy if RSI is extremely overbought
            if rsi_value > self.rsi_extreme_high:
                return (
                    f"RSI too high ({rsi_value:.1f}), avoiding BUY in overbought market"
                )

        elif decision == TradingDecision.SELL:
            # Don't sell if RSI is extremely oversold
            if rsi_value < self.rsi_extreme_low:
                return (
                    f"RSI too low ({rsi_value:.1f}), avoiding SELL in oversold market"
                )

        return None

    def _check_macd_confirmation(
        self,
        decision: TradingDecision,
        snapshot: MarketDataSnapshot,
    ) -> Optional[str]:
        """
        Check MACD for trend confirmation

        Returns confirmation message if confirmed, None otherwise
        """
        if not snapshot.macd:
            return None

        macd = snapshot.macd

        if decision == TradingDecision.BUY:
            # Confirm if MACD is bullish (value > signal)
            if macd.is_bullish:
                return "MACD confirms bullish trend"

        elif decision == TradingDecision.SELL:
            # Confirm if MACD is bearish (value < signal)
            if not macd.is_bullish:
                return "MACD confirms bearish trend"

        return None

    def _generate_hold_signal(self, symbol: str, reasoning: str) -> StrategySignal:
        """Generate HOLD signal with reasoning"""
        signal = StrategySignal(
            symbol=symbol,
            decision=TradingDecision.HOLD,
            confidence=Decimal("0.5"),
            size_pct=Decimal("0.0"),
            reasoning=reasoning,
            strategy_name=self.get_name(),
        )

        self._record_signal(signal)
        return signal


# Export
__all__ = ["TrendFollowingStrategy"]
