"""
Prompt Builder

Constructs optimized prompts for LLM trading decisions based on market data.

Author: Decision Engine Implementation Team
Date: 2025-10-28
"""

from typing import Dict, Optional
from datetime import datetime
from decimal import Decimal

from workspace.features.market_data import MarketDataSnapshot


class PromptBuilder:
    """
    Prompt Builder for LLM Trading Decisions

    Constructs structured prompts that provide market data context and
    request trading decisions from the LLM.

    Features:
    - Structured market data formatting
    - Technical indicator summary
    - Risk management context
    - Clear output format specification

    Example:
        ```python
        builder = PromptBuilder()
        prompt = builder.build_trading_prompt(
            snapshots={'BTCUSDT': snapshot},
            capital_chf=Decimal("2626.96"),
            max_position_size_chf=Decimal("525.39"),
        )
        ```
    """

    def __init__(self):
        """Initialize prompt builder"""
        pass

    def build_trading_prompt(
        self,
        snapshots: Dict[str, MarketDataSnapshot],
        capital_chf: Decimal,
        max_position_size_chf: Decimal,
        current_positions: Optional[Dict[str, Dict]] = None,
        risk_context: Optional[Dict] = None,
    ) -> str:
        """
        Build trading decision prompt for LLM

        Args:
            snapshots: Market data snapshots for each symbol
            capital_chf: Available trading capital
            max_position_size_chf: Maximum position size per trade
            current_positions: Current open positions (optional)
            risk_context: Additional risk context (optional)

        Returns:
            Formatted prompt string for LLM
        """
        prompt_parts = []

        # System context
        prompt_parts.append(self._build_system_context())

        # Trading capital and risk limits
        prompt_parts.append(
            self._build_capital_context(
                capital_chf=capital_chf,
                max_position_size_chf=max_position_size_chf,
                risk_context=risk_context,
            )
        )

        # Current positions (if any)
        if current_positions:
            prompt_parts.append(self._build_positions_context(current_positions))

        # Market data for each symbol
        prompt_parts.append(self._build_market_data_section(snapshots))

        # Output format specification
        prompt_parts.append(self._build_output_format())

        return "\n\n".join(prompt_parts)

    def _build_system_context(self) -> str:
        """Build system context section"""
        return """# Trading Decision System

You are an expert cryptocurrency trading advisor analyzing market data to make informed trading decisions.

Your role is to:
1. Analyze market data including price action, technical indicators, and trends
2. Generate trading signals (BUY, SELL, HOLD, CLOSE) for each asset
3. Provide clear reasoning for each decision
4. Set appropriate position sizes and risk parameters

Focus on:
- Technical analysis (RSI, MACD, EMA, Bollinger Bands)
- Price momentum and trend direction
- Risk-reward ratios
- Position sizing based on confidence and available capital"""

    def _build_capital_context(
        self,
        capital_chf: Decimal,
        max_position_size_chf: Decimal,
        risk_context: Optional[Dict] = None,
    ) -> str:
        """Build capital and risk context"""
        lines = [
            "# Trading Capital & Risk Parameters",
            f"- Available Capital: CHF {capital_chf:,.2f}",
            f"- Maximum Position Size: CHF {max_position_size_chf:,.2f} (20% of capital)",
            "- Stop-Loss: Required for all positions (typically 1-3%)",
            "- Take-Profit: Optional but recommended",
        ]

        if risk_context:
            lines.append("\n## Additional Risk Context:")
            for key, value in risk_context.items():
                lines.append(f"- {key}: {value}")

        return "\n".join(lines)

    def _build_positions_context(self, positions: Dict[str, Dict]) -> str:
        """Build current positions context"""
        lines = [
            "# Current Open Positions",
            "",
        ]

        if not positions:
            lines.append("No open positions currently.")
        else:
            for symbol, pos in positions.items():
                lines.append(f"## {symbol}")
                lines.append(f"- Side: {pos.get('side', 'N/A')}")
                lines.append(f"- Size: {pos.get('size', 'N/A')}")
                lines.append(f"- Entry Price: {pos.get('entry_price', 'N/A')}")
                lines.append(f"- Current P&L: {pos.get('pnl', 'N/A')}")
                lines.append(f"- Stop-Loss: {pos.get('stop_loss', 'N/A')}")
                lines.append("")

        return "\n".join(lines)

    def _build_market_data_section(
        self,
        snapshots: Dict[str, MarketDataSnapshot],
    ) -> str:
        """Build market data section for all symbols"""
        lines = [
            "# Market Data Analysis",
            "",
            f"Analysis Time: {datetime.utcnow().isoformat()}",
            f"Number of Assets: {len(snapshots)}",
            "",
        ]

        for symbol, snapshot in snapshots.items():
            lines.append(self._format_snapshot(symbol, snapshot))
            lines.append("")

        return "\n".join(lines)

    def _format_snapshot(
        self,
        symbol: str,
        snapshot: MarketDataSnapshot,
    ) -> str:
        """Format a single market data snapshot"""
        lines = [
            f"## {symbol}",
            "",
            "### Price Action",
        ]

        # Current price and candle
        ohlcv = snapshot.ohlcv
        ticker = snapshot.ticker

        lines.append(f"- Current Price: ${ticker.last:,.2f}")
        lines.append(f"- 24h Change: {ticker.change_24h_pct:+.2f}%")
        lines.append(f"- 24h High: ${ticker.high_24h:,.2f}")
        lines.append(f"- 24h Low: ${ticker.low_24h:,.2f}")
        lines.append(f"- 24h Volume: ${ticker.quote_volume_24h:,.0f}")
        lines.append("")

        # Latest candle (3-minute)
        lines.append("### Latest Candle (3min)")
        lines.append(f"- Open: ${ohlcv.open:,.2f}")
        lines.append(f"- High: ${ohlcv.high:,.2f}")
        lines.append(f"- Low: ${ohlcv.low:,.2f}")
        lines.append(f"- Close: ${ohlcv.close:,.2f}")
        lines.append(
            f"- Direction: {'🟢 Bullish' if ohlcv.is_bullish else '🔴 Bearish'}"
        )
        lines.append(f"- Change: {ohlcv.price_change_pct:+.2f}%")
        lines.append(f"- Volume: ${ohlcv.quote_volume:,.0f}")
        lines.append("")

        # Technical indicators
        lines.append("### Technical Indicators")

        if snapshot.rsi:
            rsi = snapshot.rsi
            lines.append(f"- **RSI(14)**: {rsi.value:.1f} - {rsi.signal.upper()}")
            if rsi.is_oversold:
                lines.append("  - Status: Oversold (< 30) - Potential BUY signal")
            elif rsi.is_overbought:
                lines.append("  - Status: Overbought (> 70) - Potential SELL signal")
            else:
                lines.append("  - Status: Neutral (30-70)")

        if snapshot.macd:
            macd = snapshot.macd
            lines.append(
                f"- **MACD**: {macd.value:.2f}, Signal: {macd.signal:.2f}, Histogram: {macd.histogram:.2f}"
            )
            if macd.is_bullish:
                lines.append("  - Trend: Bullish (MACD > Signal)")
            else:
                lines.append("  - Trend: Bearish (MACD < Signal)")

        if snapshot.ema_fast and snapshot.ema_slow:
            ema_fast = snapshot.ema_fast
            ema_slow = snapshot.ema_slow
            lines.append(f"- **EMA(12)**: ${ema_fast.value:,.2f}")
            lines.append(f"- **EMA(26)**: ${ema_slow.value:,.2f}")

            if ema_fast.value > ema_slow.value:
                lines.append("  - Trend: Bullish (Fast EMA > Slow EMA)")
            else:
                lines.append("  - Trend: Bearish (Fast EMA < Slow EMA)")

        if snapshot.bollinger:
            bb = snapshot.bollinger
            lines.append("- **Bollinger Bands**:")
            lines.append(f"  - Upper: ${bb.upper:,.2f}")
            lines.append(f"  - Middle: ${bb.middle:,.2f}")
            lines.append(f"  - Lower: ${bb.lower:,.2f}")
            lines.append(f"  - Bandwidth: {bb.bandwidth:.4f}")

            if bb.is_squeeze:
                lines.append(
                    "  - Status: Squeeze detected (low volatility) - Potential breakout"
                )

            # Price position relative to bands
            current_price = ticker.last
            if current_price > bb.upper:
                lines.append("  - Price: Above upper band (overbought)")
            elif current_price < bb.lower:
                lines.append("  - Price: Below lower band (oversold)")
            else:
                lines.append("  - Price: Within bands (normal)")

        return "\n".join(lines)

    def _build_output_format(self) -> str:
        """Build output format specification"""
        return """# Output Format

For each asset, provide your trading decision in the following JSON format:

```json
{
  "symbol": "BTCUSDT",
  "decision": "BUY",  // One of: BUY, SELL, HOLD, CLOSE
  "confidence": 0.75,  // 0.0 to 1.0 (higher = more confident)
  "size_pct": 0.15,    // Percentage of available capital (0.0 to 1.0)
  "stop_loss_pct": 0.02,  // Stop-loss distance as decimal (e.g., 0.02 = 2%)
  "take_profit_pct": 0.05,  // Take-profit distance as decimal (optional)
  "reasoning": "RSI shows oversold conditions at 28. MACD histogram is turning positive. EMA crossover suggests bullish momentum. Price bounced off lower Bollinger Band. Risk-reward ratio is favorable at 1:2.5."
}
```

## Decision Guidelines:

**BUY**: Open new long position
- Use when: Bullish indicators, oversold conditions, upward momentum
- Consider: RSI < 40, MACD turning positive, price near support

**SELL**: Open new short position (perpetual futures)
- Use when: Bearish indicators, overbought conditions, downward momentum
- Consider: RSI > 60, MACD turning negative, price near resistance

**HOLD**: Do nothing (no trade)
- Use when: Unclear signals, low confidence, waiting for better entry
- Consider: Mixed indicators, low volume, consolidation phase

**CLOSE**: Close existing position
- Use when: Position should be exited (profit target reached or stop-loss)
- Only use if a position is currently open for this symbol

## Position Sizing Guidelines:
- High confidence (0.8-1.0): 15-20% of capital
- Medium confidence (0.6-0.8): 10-15% of capital
- Low confidence (0.4-0.6): 5-10% of capital
- Very low confidence (< 0.4): Use HOLD instead

## Stop-Loss Guidelines:
- Volatile assets (BTC, ETH): 2-3%
- Less volatile: 1-2%
- Always required for risk management

Provide decisions for ALL assets analyzed above."""


# Export
__all__ = ["PromptBuilder"]
