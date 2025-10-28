"""
Mean Reversion Strategy

RSI-based mean reversion strategy for cryptocurrency trading.

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


class MeanReversionStrategy(BaseStrategy):
    """
    Mean Reversion Strategy

    Trades based on RSI overbought/oversold conditions,
    assuming prices will revert to the mean.

    Strategy Logic:
    - BUY when RSI < oversold threshold (default: 30)
    - SELL when RSI > overbought threshold (default: 70)
    - HOLD when RSI is neutral (30-70)

    Uses additional confirmation:
    - Price near Bollinger Band boundaries
    - MACD histogram for momentum
    - EMA trend for context

    Configuration:
    - rsi_oversold: RSI oversold threshold (default: 30)
    - rsi_overbought: RSI overbought threshold (default: 70)
    - use_bollinger: Use Bollinger Bands confirmation (default: True)
    - use_macd: Use MACD confirmation (default: True)
    - position_size_pct: Base position size (default: 0.15 = 15%)
    - stop_loss_pct: Stop-loss distance (default: 0.02 = 2%)
    - take_profit_pct: Take-profit distance (default: 0.04 = 4%)

    Example:
        ```python
        strategy = MeanReversionStrategy(config={
            'rsi_oversold': 25,
            'rsi_overbought': 75,
            'position_size_pct': 0.20,
        })

        signal = strategy.analyze(snapshot)
        ```
    """

    DEFAULT_CONFIG = {
        "rsi_oversold": 30,
        "rsi_overbought": 70,
        "use_bollinger": True,
        "use_macd": True,
        "position_size_pct": 0.15,
        "stop_loss_pct": 0.02,
        "take_profit_pct": 0.04,
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Mean Reversion Strategy

        Args:
            config: Strategy configuration (uses DEFAULT_CONFIG as base)
        """
        # Merge with defaults
        merged_config = self.DEFAULT_CONFIG.copy()
        if config:
            merged_config.update(config)

        super().__init__(merged_config)

        # Extract config values
        self.rsi_oversold = Decimal(str(self.config["rsi_oversold"]))
        self.rsi_overbought = Decimal(str(self.config["rsi_overbought"]))
        self.use_bollinger = self.config["use_bollinger"]
        self.use_macd = self.config["use_macd"]
        self.position_size_pct = Decimal(str(self.config["position_size_pct"]))
        self.stop_loss_pct = Decimal(str(self.config["stop_loss_pct"]))
        self.take_profit_pct = Decimal(str(self.config["take_profit_pct"]))

    def get_name(self) -> str:
        """Get strategy name"""
        return "Mean Reversion (RSI-based)"

    def get_type(self) -> StrategyType:
        """Get strategy type"""
        return StrategyType.MEAN_REVERSION

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

        # Check if RSI is available
        if not snapshot.rsi:
            return self._generate_hold_signal(snapshot.symbol, "RSI not available")

        rsi_value = snapshot.rsi.value
        current_price = snapshot.ticker.last

        # Determine base decision from RSI
        if rsi_value < self.rsi_oversold:
            # Oversold - potential BUY
            decision = TradingDecision.BUY
            confidence = self._calculate_buy_confidence(snapshot)
            reasoning_parts = [f"RSI oversold at {rsi_value:.1f}"]

        elif rsi_value > self.rsi_overbought:
            # Overbought - potential SELL
            decision = TradingDecision.SELL
            confidence = self._calculate_sell_confidence(snapshot)
            reasoning_parts = [f"RSI overbought at {rsi_value:.1f}"]

        else:
            # Neutral - HOLD
            return self._generate_hold_signal(
                snapshot.symbol,
                f"RSI neutral at {rsi_value:.1f} (not oversold/overbought)",
            )

        # Add Bollinger Band confirmation
        if self.use_bollinger and snapshot.bollinger:
            bb_conf = self._check_bollinger_confirmation(decision, snapshot)
            if bb_conf:
                confidence = min(confidence + Decimal("0.1"), Decimal("1.0"))
                reasoning_parts.append(bb_conf)

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
                "rsi": float(rsi_value),
                "price": float(current_price),
            },
        )

        self._record_signal(signal)
        return signal

    def _calculate_buy_confidence(self, snapshot: MarketDataSnapshot) -> Decimal:
        """Calculate confidence for BUY signal"""
        rsi_value = snapshot.rsi.value

        # Base confidence from RSI (lower RSI = higher confidence)
        # RSI 30 -> 0.6, RSI 20 -> 0.7, RSI 10 -> 0.8
        rsi_conf = Decimal("0.6") + (self.rsi_oversold - rsi_value) / Decimal("100")
        confidence = max(Decimal("0.5"), min(rsi_conf, Decimal("0.9")))

        return confidence

    def _calculate_sell_confidence(self, snapshot: MarketDataSnapshot) -> Decimal:
        """Calculate confidence for SELL signal"""
        rsi_value = snapshot.rsi.value

        # Base confidence from RSI (higher RSI = higher confidence)
        # RSI 70 -> 0.6, RSI 80 -> 0.7, RSI 90 -> 0.8
        rsi_conf = Decimal("0.6") + (rsi_value - self.rsi_overbought) / Decimal("100")
        confidence = max(Decimal("0.5"), min(rsi_conf, Decimal("0.9")))

        return confidence

    def _check_bollinger_confirmation(
        self,
        decision: TradingDecision,
        snapshot: MarketDataSnapshot,
    ) -> Optional[str]:
        """
        Check Bollinger Bands for confirmation

        Returns confirmation message if confirmed, None otherwise
        """
        if not snapshot.bollinger:
            return None

        current_price = snapshot.ticker.last
        bb = snapshot.bollinger

        if decision == TradingDecision.BUY:
            # Confirm if price near or below lower band
            if current_price <= bb.lower_band * Decimal(
                "1.02"
            ):  # Within 2% of lower band
                return "Price near lower Bollinger Band (support)"

        elif decision == TradingDecision.SELL:
            # Confirm if price near or above upper band
            if current_price >= bb.upper_band * Decimal(
                "0.98"
            ):  # Within 2% of upper band
                return "Price near upper Bollinger Band (resistance)"

        return None

    def _check_macd_confirmation(
        self,
        decision: TradingDecision,
        snapshot: MarketDataSnapshot,
    ) -> Optional[str]:
        """
        Check MACD for confirmation

        Returns confirmation message if confirmed, None otherwise
        """
        if not snapshot.macd:
            return None

        macd = snapshot.macd

        if decision == TradingDecision.BUY:
            # Confirm if MACD histogram is turning positive
            if macd.histogram > 0:
                return "MACD histogram positive (momentum building)"

        elif decision == TradingDecision.SELL:
            # Confirm if MACD histogram is turning negative
            if macd.histogram < 0:
                return "MACD histogram negative (momentum weakening)"

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
__all__ = ["MeanReversionStrategy"]
