# Strategy Module

Algorithmic trading strategies for cryptocurrency markets. Provides a flexible, extensible framework for implementing technical analysis-based trading strategies.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Implemented Strategies](#implemented-strategies)
  - [Mean Reversion Strategy](#mean-reversion-strategy)
  - [Trend Following Strategy](#trend-following-strategy)
  - [Volatility Breakout Strategy](#volatility-breakout-strategy)
- [Usage](#usage)
- [Configuration](#configuration)
- [Integration](#integration)
- [Testing](#testing)
- [Creating Custom Strategies](#creating-custom-strategies)

## Overview

The Strategy Module provides algorithmic trading strategies that analyze market data and generate trading signals. Each strategy implements a specific trading approach based on technical indicators.

**Key Features:**
- Abstract base class for consistent interface
- Multiple strategy types (mean reversion, trend following, breakout)
- Configurable parameters per strategy
- Multi-indicator confirmation for higher confidence
- Position sizing based on confidence levels
- Comprehensive testing framework

## Architecture

```
strategy/
├── __init__.py              # Module exports
├── base_strategy.py         # Abstract base class
├── mean_reversion.py        # RSI-based mean reversion
├── trend_following.py       # EMA crossover trend following
├── volatility_breakout.py   # Bollinger Band breakout
└── tests/                   # Test suite
    └── test_strategies_simplified.py
```

### Core Components

**BaseStrategy** (`base_strategy.py`)
- Abstract base class defining the strategy interface
- Common functionality for all strategies
- Signal recording and statistics tracking

**StrategySignal** (`base_strategy.py`)
- Data class representing a trading signal
- Contains decision, confidence, position size, stops
- Similar to TradingSignal but from algorithmic strategies

**StrategyType** (`base_strategy.py`)
- Enum of available strategy types
- Used for strategy classification and routing

## Implemented Strategies

### Mean Reversion Strategy

**File:** `mean_reversion.py`
**Type:** `MEAN_REVERSION`
**Approach:** RSI-based mean reversion

**Logic:**
- BUY when RSI < oversold threshold (default: 30)
- SELL when RSI > overbought threshold (default: 70)
- HOLD when RSI is neutral (30-70)

**Confirmation Indicators:**
- Bollinger Bands: Price near band boundaries
- MACD: Histogram direction for momentum

**Default Configuration:**
```python
{
    'rsi_oversold': 30,
    'rsi_overbought': 70,
    'use_bollinger': True,
    'use_macd': True,
    'position_size_pct': 0.15,  # 15%
    'stop_loss_pct': 0.02,      # 2%
    'take_profit_pct': 0.04,    # 4%
}
```

**Usage Example:**
```python
from workspace.features.strategy import MeanReversionStrategy

# Initialize with default config
strategy = MeanReversionStrategy()

# Or with custom config
strategy = MeanReversionStrategy(config={
    'rsi_oversold': 25,
    'rsi_overbought': 75,
    'position_size_pct': 0.20,
})

# Analyze market data
signal = strategy.analyze(snapshot)
print(f"Decision: {signal.decision}")
print(f"Confidence: {signal.confidence}")
print(f"Size: {signal.size_pct}")
```

**When to Use:**
- Ranging markets with clear support/resistance
- High volatility with frequent price swings
- Cryptocurrencies with mean-reverting behavior

### Trend Following Strategy

**File:** `trend_following.py`
**Type:** `TREND_FOLLOWING`
**Approach:** EMA crossover with filters

**Logic:**
- BUY when Fast EMA (12) > Slow EMA (26)
- SELL when Fast EMA (12) < Slow EMA (26)
- HOLD when EMA distance too small (whipsaw protection)

**Confirmation Indicators:**
- RSI: Filter extreme conditions (avoid buying > 80, selling < 20)
- MACD: Confirm trend direction
- EMA Distance: Minimum 0.5% to avoid false signals

**Default Configuration:**
```python
{
    'ema_fast_period': 12,
    'ema_slow_period': 26,
    'min_ema_distance_pct': 0.5,
    'use_macd': True,
    'use_rsi_filter': True,
    'rsi_extreme_low': 20,
    'rsi_extreme_high': 80,
    'position_size_pct': 0.15,  # 15%
    'stop_loss_pct': 0.025,     # 2.5%
    'take_profit_pct': 0.06,    # 6%
}
```

**Usage Example:**
```python
from workspace.features.strategy import TrendFollowingStrategy

# Initialize strategy
strategy = TrendFollowingStrategy(config={
    'min_ema_distance_pct': 0.8,  # Stricter filter
    'position_size_pct': 0.18,
})

# Analyze market data
signal = strategy.analyze(snapshot)

if signal.decision == TradingDecision.BUY:
    print(f"Bullish trend detected (confidence: {signal.confidence})")
elif signal.decision == TradingDecision.SELL:
    print(f"Bearish trend detected (confidence: {signal.confidence})")
```

**When to Use:**
- Trending markets with clear direction
- Low-volatility periods with sustained moves
- Cryptocurrencies showing strong momentum

### Volatility Breakout Strategy

**File:** `volatility_breakout.py`
**Type:** `VOLATILITY_BREAKOUT`
**Approach:** Bollinger Band squeeze and breakout

**Logic:**
- Detect squeeze: Bollinger bandwidth < 2% (low volatility)
- BUY: Price breaks above upper band after squeeze
- SELL: Price breaks below lower band after squeeze
- HOLD: No squeeze or no breakout yet

**Confirmation Indicators:**
- Volume: Must be > 1.5x average for valid breakout
- RSI: Direction confirmation (BUY: RSI > 50, SELL: RSI < 50)
- Squeeze Detection: Bandwidth < threshold

**Default Configuration:**
```python
{
    'squeeze_bandwidth_threshold': 0.02,  # 2%
    'breakout_threshold_pct': 0.5,        # 0.5%
    'use_volume_confirmation': True,
    'volume_multiplier': 1.5,
    'use_rsi': True,
    'position_size_pct': 0.18,  # 18%
    'stop_loss_pct': 0.03,      # 3%
    'take_profit_pct': 0.08,    # 8%
}
```

**Usage Example:**
```python
from workspace.features.strategy import VolatilityBreakoutStrategy

# Initialize strategy
strategy = VolatilityBreakoutStrategy(config={
    'squeeze_bandwidth_threshold': 0.015,  # Tighter squeeze
    'position_size_pct': 0.20,
})

# Analyze market data
signal = strategy.analyze(snapshot)

if signal.decision != TradingDecision.HOLD:
    print(f"Breakout detected!")
    print(f"Direction: {signal.decision}")
    print(f"Confidence: {signal.confidence}")
    print(f"Reasoning: {signal.reasoning}")
```

**When to Use:**
- Consolidation periods before major moves
- Low-volatility compression patterns
- Cryptocurrencies showing squeeze patterns

## Usage

### Basic Usage

```python
from workspace.features.strategy import (
    MeanReversionStrategy,
    TrendFollowingStrategy,
    VolatilityBreakoutStrategy,
)
from workspace.features.market_data import MarketDataSnapshot

# Create strategies
mean_reversion = MeanReversionStrategy()
trend_following = TrendFollowingStrategy()
volatility_breakout = VolatilityBreakoutStrategy()

# Analyze same snapshot with multiple strategies
snapshot = market_data_service.get_snapshot("BTC/USDT:USDT")

mr_signal = mean_reversion.analyze(snapshot)
tf_signal = trend_following.analyze(snapshot)
vb_signal = volatility_breakout.analyze(snapshot)

# Compare signals
print(f"Mean Reversion: {mr_signal.decision} (confidence: {mr_signal.confidence})")
print(f"Trend Following: {tf_signal.decision} (confidence: {tf_signal.confidence})")
print(f"Volatility Breakout: {vb_signal.decision} (confidence: {vb_signal.confidence})")
```

### With Custom Configuration

```python
# Create strategy with custom parameters
custom_config = {
    'rsi_oversold': 25,
    'rsi_overbought': 75,
    'use_bollinger': True,
    'position_size_pct': 0.20,
    'stop_loss_pct': 0.015,
    'take_profit_pct': 0.05,
}

strategy = MeanReversionStrategy(config=custom_config)
signal = strategy.analyze(snapshot)
```

### Strategy Selection

```python
def select_strategy(market_conditions: dict) -> BaseStrategy:
    """Select appropriate strategy based on market conditions"""
    if market_conditions['volatility'] == 'low':
        return VolatilityBreakoutStrategy()
    elif market_conditions['trend'] == 'strong':
        return TrendFollowingStrategy()
    else:
        return MeanReversionStrategy()

# Usage
strategy = select_strategy({'volatility': 'low', 'trend': 'weak'})
signal = strategy.analyze(snapshot)
```

## Configuration

### Common Parameters

All strategies support these common configuration parameters:

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `position_size_pct` | Decimal | Base position size (0-1) | Varies |
| `stop_loss_pct` | Decimal | Stop-loss distance | Varies |
| `take_profit_pct` | Decimal | Take-profit distance | Varies |

### Strategy-Specific Parameters

**Mean Reversion:**
- `rsi_oversold`: RSI oversold threshold (default: 30)
- `rsi_overbought`: RSI overbought threshold (default: 70)
- `use_bollinger`: Use Bollinger Band confirmation (default: True)
- `use_macd`: Use MACD confirmation (default: True)

**Trend Following:**
- `ema_fast_period`: Fast EMA period (default: 12)
- `ema_slow_period`: Slow EMA period (default: 26)
- `min_ema_distance_pct`: Minimum EMA distance (default: 0.5%)
- `use_macd`: Use MACD confirmation (default: True)
- `use_rsi_filter`: Filter extreme RSI (default: True)
- `rsi_extreme_low`: RSI lower bound (default: 20)
- `rsi_extreme_high`: RSI upper bound (default: 80)

**Volatility Breakout:**
- `squeeze_bandwidth_threshold`: Max bandwidth for squeeze (default: 0.02 = 2%)
- `breakout_threshold_pct`: Breakout distance (default: 0.5%)
- `use_volume_confirmation`: Require volume increase (default: True)
- `volume_multiplier`: Required volume multiplier (default: 1.5)
- `use_rsi`: Use RSI confirmation (default: True)

## Integration

### With Trading Loop

```python
from workspace.features.trading_loop import TradingEngine
from workspace.features.strategy import MeanReversionStrategy

# Initialize strategy
strategy = MeanReversionStrategy()

# Integrate with Trading Engine
async def trading_cycle(symbol: str):
    # Get market data
    snapshot = await market_data_service.get_snapshot(symbol)

    # Get strategy signal
    strategy_signal = strategy.analyze(snapshot)

    # Convert to trading decision
    if strategy_signal.decision != TradingDecision.HOLD:
        # Execute trade based on signal
        await execute_trade(
            symbol=symbol,
            decision=strategy_signal.decision,
            size_pct=strategy_signal.size_pct,
            stop_loss_pct=strategy_signal.stop_loss_pct,
            take_profit_pct=strategy_signal.take_profit_pct,
        )
```

### Multi-Strategy Approach

```python
class StrategyEnsemble:
    """Combine multiple strategies with voting or weighting"""

    def __init__(self):
        self.strategies = [
            MeanReversionStrategy(),
            TrendFollowingStrategy(),
            VolatilityBreakoutStrategy(),
        ]

    def analyze(self, snapshot: MarketDataSnapshot) -> StrategySignal:
        """Get signals from all strategies and combine"""
        signals = [s.analyze(snapshot) for s in self.strategies]

        # Weighted voting based on confidence
        buy_weight = sum(s.confidence for s in signals if s.decision == TradingDecision.BUY)
        sell_weight = sum(s.confidence for s in signals if s.decision == TradingDecision.SELL)

        if buy_weight > sell_weight and buy_weight > 1.0:
            return StrategySignal(
                symbol=snapshot.symbol,
                decision=TradingDecision.BUY,
                confidence=buy_weight / len(signals),
                size_pct=Decimal("0.15"),
                reasoning=f"Ensemble BUY (weight: {buy_weight:.2f})",
            )
        elif sell_weight > buy_weight and sell_weight > 1.0:
            return StrategySignal(
                symbol=snapshot.symbol,
                decision=TradingDecision.SELL,
                confidence=sell_weight / len(signals),
                size_pct=Decimal("0.15"),
                reasoning=f"Ensemble SELL (weight: {sell_weight:.2f})",
            )
        else:
            return StrategySignal(
                symbol=snapshot.symbol,
                decision=TradingDecision.HOLD,
                confidence=Decimal("0.5"),
                size_pct=Decimal("0.0"),
                reasoning="No consensus",
            )

# Usage
ensemble = StrategyEnsemble()
signal = ensemble.analyze(snapshot)
```

## Testing

The module includes comprehensive tests in `tests/test_strategies_simplified.py`.

### Running Tests

```bash
# Run all strategy tests
python -m pytest workspace/features/strategy/tests/test_strategies_simplified.py -v

# Run specific test class
python -m pytest workspace/features/strategy/tests/test_strategies_simplified.py::TestMeanReversionStrategy -v

# Run with coverage
python -m pytest workspace/features/strategy/tests/ --cov=workspace.features.strategy --cov-report=html
```

### Test Structure

```python
# Example test
def test_buy_signal_on_oversold():
    """Test BUY signal when RSI is oversold"""
    snapshot = create_snapshot(
        rsi=create_rsi(Decimal("25.0")),  # Oversold
        bollinger=create_bollinger_bands(
            Decimal("51000"), Decimal("50000"), Decimal("49000")
        ),
    )

    strategy = MeanReversionStrategy()
    signal = strategy.analyze(snapshot)

    assert signal.decision == TradingDecision.BUY
    assert signal.confidence > Decimal("0.5")
```

### Writing Strategy Tests

When creating tests for new strategies:

1. **Use helper functions** to create snapshots with required fields
2. **Test all decision paths**: BUY, SELL, HOLD
3. **Test edge cases**: Missing indicators, extreme values
4. **Test configuration**: Custom configs, validation
5. **Test confirmation logic**: Multi-indicator interactions

## Creating Custom Strategies

### Step 1: Extend BaseStrategy

```python
from workspace.features.strategy import BaseStrategy, StrategySignal, StrategyType
from workspace.features.market_data import MarketDataSnapshot
from workspace.features.trading_loop import TradingDecision
from decimal import Decimal
from typing import Dict, Any, Optional

class MyCustomStrategy(BaseStrategy):
    """
    Custom trading strategy

    Implement your own trading logic here.
    """

    DEFAULT_CONFIG = {
        'param1': 10,
        'param2': 0.5,
        'position_size_pct': 0.15,
        'stop_loss_pct': 0.02,
        'take_profit_pct': 0.04,
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        # Merge with defaults
        merged_config = self.DEFAULT_CONFIG.copy()
        if config:
            merged_config.update(config)

        super().__init__(merged_config)

        # Extract config values
        self.param1 = self.config['param1']
        self.param2 = Decimal(str(self.config['param2']))
        self.position_size_pct = Decimal(str(self.config['position_size_pct']))
        self.stop_loss_pct = Decimal(str(self.config['stop_loss_pct']))
        self.take_profit_pct = Decimal(str(self.config['take_profit_pct']))

    def get_name(self) -> str:
        """Get strategy name"""
        return "My Custom Strategy"

    def get_type(self) -> StrategyType:
        """Get strategy type"""
        return StrategyType.CUSTOM

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
            return self._generate_hold_signal(snapshot.symbol, "Invalid snapshot")

        # Implement your logic here
        # Check indicators, calculate signals, etc.

        # Example: Simple logic
        if snapshot.rsi and snapshot.rsi.value < 30:
            decision = TradingDecision.BUY
            confidence = Decimal("0.7")
            reasoning = "RSI oversold"
        elif snapshot.rsi and snapshot.rsi.value > 70:
            decision = TradingDecision.SELL
            confidence = Decimal("0.7")
            reasoning = "RSI overbought"
        else:
            return self._generate_hold_signal(snapshot.symbol, "No clear signal")

        # Calculate position size
        size_pct = self.position_size_pct * confidence

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
        )

        self._record_signal(signal)
        return signal

    def _generate_hold_signal(self, symbol: str, reasoning: str) -> StrategySignal:
        """Generate HOLD signal"""
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
```

### Step 2: Register Strategy

Add your strategy to `__init__.py`:

```python
from .my_custom_strategy import MyCustomStrategy

__all__ = [
    # ... existing exports
    "MyCustomStrategy",
]
```

### Step 3: Write Tests

Create tests in `tests/test_my_custom_strategy.py`:

```python
from workspace.features.strategy import MyCustomStrategy

def test_custom_strategy():
    strategy = MyCustomStrategy()
    signal = strategy.analyze(snapshot)
    assert signal.decision in [TradingDecision.BUY, TradingDecision.SELL, TradingDecision.HOLD]
```

## Best Practices

1. **Always validate snapshots** before analyzing
2. **Use multi-indicator confirmation** for higher confidence
3. **Implement HOLD logic** for unclear market conditions
4. **Calculate dynamic position sizes** based on confidence
5. **Include detailed reasoning** in signals for debugging
6. **Test thoroughly** with various market conditions
7. **Document configuration parameters** clearly
8. **Use Decimal** for all price/percentage calculations
9. **Record signals** for statistics tracking
10. **Follow the BaseStrategy interface** consistently

## Future Enhancements

Potential improvements for the strategy module:

- **Backtesting Framework**: Historical strategy performance analysis
- **Parameter Optimization**: Automated config optimization
- **Machine Learning Integration**: ML-based signal generation
- **More Strategies**: Momentum, arbitrage, etc.
- **Risk-Adjusted Sizing**: Kelly Criterion, Sharpe-based sizing
- **Multi-Timeframe Analysis**: Combine signals across timeframes
- **Performance Metrics**: Sharpe ratio, win rate, drawdown tracking

---

**Module:** workspace/features/strategy
**Author:** Strategy Implementation Team
**Date:** 2025-10-28
**Status:** Production Ready
**Tests:** 10 tests passing
