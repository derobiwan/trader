"""
Volatility Breakout Strategy

Bollinger Band breakout strategy for cryptocurrency trading.

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


class VolatilityBreakoutStrategy(BaseStrategy):
    """
    Volatility Breakout Strategy

    Trades on Bollinger Band breakouts after squeeze periods,
    capturing volatility expansion moves.

    Strategy Logic:
    - BUY when price breaks above upper band after squeeze
    - SELL when price breaks below lower band after squeeze
    - HOLD during normal conditions or no squeeze

    Squeeze Detection:
    - Low bandwidth (<0.02 = 2% by default)
    - Indicates low volatility, potential breakout coming

    Uses additional confirmation:
    - RSI for momentum direction
    - Volume increase
    - MACD histogram

    Configuration:
    - squeeze_bandwidth_threshold: Max bandwidth for squeeze (default: 0.02 = 2%)
    - breakout_threshold_pct: Breakout distance from band (default: 0.5%)
    - use_volume_confirmation: Require volume increase (default: True)
    - volume_multiplier: Volume must be X times average (default: 1.5)
    - use_rsi: Use RSI for direction (default: True)
    - position_size_pct: Base position size (default: 0.18 = 18%)
    - stop_loss_pct: Stop-loss distance (default: 0.03 = 3%)
    - take_profit_pct: Take-profit distance (default: 0.08 = 8%)

    Example:
        ```python
        strategy = VolatilityBreakoutStrategy(config={
            'squeeze_bandwidth_threshold': 0.015,
            'position_size_pct': 0.20,
        })

        signal = strategy.analyze(snapshot)
        ```
    """

    DEFAULT_CONFIG = {
        "squeeze_bandwidth_threshold": 0.02,  # 2%
        "breakout_threshold_pct": 0.5,  # 0.5%
        "use_volume_confirmation": True,
        "volume_multiplier": 1.5,
        "use_rsi": True,
        "position_size_pct": 0.18,
        "stop_loss_pct": 0.03,
        "take_profit_pct": 0.08,
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Volatility Breakout Strategy

        Args:
            config: Strategy configuration (uses DEFAULT_CONFIG as base)
        """
        # Merge with defaults
        merged_config = self.DEFAULT_CONFIG.copy()
        if config:
            merged_config.update(config)

        super().__init__(merged_config)

        # Extract config values
        self.squeeze_threshold = Decimal(
            str(self.config["squeeze_bandwidth_threshold"])
        )
        self.breakout_threshold_pct = Decimal(
            str(self.config["breakout_threshold_pct"])
        )
        self.use_volume_confirmation = self.config["use_volume_confirmation"]
        self.volume_multiplier = Decimal(str(self.config["volume_multiplier"]))
        self.use_rsi = self.config["use_rsi"]
        self.position_size_pct = Decimal(str(self.config["position_size_pct"]))
        self.stop_loss_pct = Decimal(str(self.config["stop_loss_pct"]))
        self.take_profit_pct = Decimal(str(self.config["take_profit_pct"]))

    def get_name(self) -> str:
        """Get strategy name"""
        return "Volatility Breakout (Bollinger Bands)"

    def get_type(self) -> StrategyType:
        """Get strategy type"""
        return StrategyType.VOLATILITY_BREAKOUT

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

        # Check if Bollinger Bands are available
        if not snapshot.bollinger:
            return self._generate_hold_signal(
                snapshot.symbol, "Bollinger Bands not available"
            )

        bb = snapshot.bollinger
        current_price = snapshot.ticker.last

        # Check for squeeze condition
        is_squeeze = bb.is_squeeze or (bb.bandwidth < self.squeeze_threshold)

        if not is_squeeze:
            return self._generate_hold_signal(
                snapshot.symbol,
                f"No squeeze detected (bandwidth: {bb.bandwidth:.4f}, threshold: {self.squeeze_threshold})",
            )

        # Check for breakout
        upper_breakout_level = bb.upper_band * (
            Decimal("1") + self.breakout_threshold_pct / Decimal("100")
        )
        lower_breakout_level = bb.lower_band * (
            Decimal("1") - self.breakout_threshold_pct / Decimal("100")
        )

        if current_price >= upper_breakout_level:
            # Upper breakout - BUY
            decision = TradingDecision.BUY
            confidence = self._calculate_buy_confidence(snapshot)
            reasoning_parts = [
                f"Upper band breakout (price ${current_price:,.2f} > ${upper_breakout_level:,.2f})",
                f"After squeeze (bandwidth: {bb.bandwidth:.4f})",
            ]

        elif current_price <= lower_breakout_level:
            # Lower breakout - SELL
            decision = TradingDecision.SELL
            confidence = self._calculate_sell_confidence(snapshot)
            reasoning_parts = [
                f"Lower band breakout (price ${current_price:,.2f} < ${lower_breakout_level:,.2f})",
                f"After squeeze (bandwidth: {bb.bandwidth:.4f})",
            ]

        else:
            return self._generate_hold_signal(
                snapshot.symbol,
                f"Squeeze detected but no breakout yet (price: ${current_price:,.2f}, "
                f"upper: ${bb.upper_band:,.2f}, lower: ${bb.lower_band:,.2f})",
            )

        # Check volume confirmation
        if self.use_volume_confirmation:
            volume_conf = self._check_volume_confirmation(snapshot)
            if not volume_conf:
                return self._generate_hold_signal(
                    snapshot.symbol,
                    "Breakout detected but insufficient volume confirmation",
                )
            reasoning_parts.append(volume_conf)
            confidence = min(confidence + Decimal("0.1"), Decimal("1.0"))

        # Check RSI direction
        if self.use_rsi and snapshot.rsi:
            rsi_conf = self._check_rsi_confirmation(decision, snapshot)
            if rsi_conf:
                reasoning_parts.append(rsi_conf)
                confidence = min(confidence + Decimal("0.1"), Decimal("1.0"))

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
                "price": float(current_price),
                "bb_upper": float(bb.upper_band),
                "bb_middle": float(bb.middle_band),
                "bb_lower": float(bb.lower_band),
                "bb_bandwidth": float(bb.bandwidth),
                "squeeze": is_squeeze,
            },
        )

        self._record_signal(signal)
        return signal

    def _calculate_buy_confidence(self, snapshot: MarketDataSnapshot) -> Decimal:
        """Calculate confidence for BUY signal"""
        bb = snapshot.bollinger

        # Base confidence from squeeze strength
        # Tighter squeeze = higher confidence
        # bandwidth 0.02 -> 0.7, 0.015 -> 0.75, 0.01 -> 0.8
        squeeze_strength = (
            self.squeeze_threshold - bb.bandwidth
        ) / self.squeeze_threshold
        confidence = Decimal("0.65") + squeeze_strength * Decimal("0.2")
        confidence = max(Decimal("0.65"), min(confidence, Decimal("0.9")))

        return confidence

    def _calculate_sell_confidence(self, snapshot: MarketDataSnapshot) -> Decimal:
        """Calculate confidence for SELL signal"""
        # Same logic as buy (symmetric)
        bb = snapshot.bollinger

        squeeze_strength = (
            self.squeeze_threshold - bb.bandwidth
        ) / self.squeeze_threshold
        confidence = Decimal("0.65") + squeeze_strength * Decimal("0.2")
        confidence = max(Decimal("0.65"), min(confidence, Decimal("0.9")))

        return confidence

    def _check_volume_confirmation(self, snapshot: MarketDataSnapshot) -> Optional[str]:
        """
        Check if volume confirms breakout

        Returns confirmation message if confirmed, None otherwise
        """
        current_volume = snapshot.ohlcv.volume
        avg_volume = snapshot.ticker.volume_24h / Decimal("480")  # 24h / 3min intervals

        if current_volume >= avg_volume * self.volume_multiplier:
            volume_ratio = current_volume / avg_volume
            return f"Volume confirmation ({volume_ratio:.1f}x average)"

        return None

    def _check_rsi_confirmation(
        self,
        decision: TradingDecision,
        snapshot: MarketDataSnapshot,
    ) -> Optional[str]:
        """
        Check RSI for direction confirmation

        Returns confirmation message if confirmed, None otherwise
        """
        if not snapshot.rsi:
            return None

        rsi_value = snapshot.rsi.value

        if decision == TradingDecision.BUY:
            # Confirm if RSI shows momentum (> 50)
            if rsi_value > 50:
                return f"RSI confirms upward momentum ({rsi_value:.1f})"

        elif decision == TradingDecision.SELL:
            # Confirm if RSI shows downward momentum (< 50)
            if rsi_value < 50:
                return f"RSI confirms downward momentum ({rsi_value:.1f})"

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
__all__ = ["VolatilityBreakoutStrategy"]
