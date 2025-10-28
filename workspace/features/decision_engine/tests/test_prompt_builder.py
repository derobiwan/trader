"""
Prompt Builder Tests

Tests for trading decision prompt construction.

Author: Decision Engine Implementation Team
Date: 2025-10-28
"""

import pytest
from datetime import datetime
from decimal import Decimal

from workspace.features.decision_engine.prompt_builder import PromptBuilder
from workspace.features.market_data import (
    MarketDataSnapshot,
    OHLCV,
    Ticker,
    Timeframe,
    RSI,
    MACD,
    EMA,
    BollingerBands,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_ohlcv():
    """Sample OHLCV candle"""
    return OHLCV(
        symbol="BTC/USDT:USDT",
        timeframe=Timeframe.M3,
        timestamp=datetime.utcnow(),
        open=Decimal("50000"),
        high=Decimal("50500"),
        low=Decimal("49500"),
        close=Decimal("50200"),
        volume=Decimal("100"),
        quote_volume=Decimal("5000000"),
        trades_count=1000,
    )


@pytest.fixture
def sample_ticker():
    """Sample ticker data"""
    return Ticker(
        symbol="BTC/USDT:USDT",
        last=Decimal("50200"),
        bid=Decimal("50190"),
        ask=Decimal("50210"),
        high_24h=Decimal("51000"),
        low_24h=Decimal("49000"),
        volume_24h=Decimal("10000"),
        quote_volume_24h=Decimal("500000000"),
        timestamp=datetime.utcnow(),
    )


@pytest.fixture
def sample_snapshot(sample_ohlcv, sample_ticker):
    """Sample market data snapshot with all indicators"""
    return MarketDataSnapshot(
        symbol="BTC/USDT:USDT",
        timeframe=Timeframe.M3,
        timestamp=datetime.utcnow(),
        ohlcv=sample_ohlcv,
        ticker=sample_ticker,
        rsi=RSI(
            symbol="BTC/USDT:USDT",
            timeframe=Timeframe.M3,
            timestamp=datetime.utcnow(),
            value=Decimal("55.5"),
            period=14,
        ),
        macd=MACD(
            symbol="BTC/USDT:USDT",
            timeframe=Timeframe.M3,
            timestamp=datetime.utcnow(),
            value=Decimal("100"),
            signal=Decimal("80"),
            histogram=Decimal("20"),
            fast_period=12,
            slow_period=26,
            signal_period=9,
        ),
        ema_fast=EMA(
            symbol="BTC/USDT:USDT",
            timeframe=Timeframe.M3,
            timestamp=datetime.utcnow(),
            value=Decimal("50100"),
            period=12,
        ),
        ema_slow=EMA(
            symbol="BTC/USDT:USDT",
            timeframe=Timeframe.M3,
            timestamp=datetime.utcnow(),
            value=Decimal("50000"),
            period=26,
        ),
        bollinger=BollingerBands(
            symbol="BTC/USDT:USDT",
            timeframe=Timeframe.M3,
            timestamp=datetime.utcnow(),
            middle=Decimal("50000"),
            upper=Decimal("51000"),
            lower=Decimal("49000"),
            bandwidth=Decimal("0.04"),
            period=20,
            std_dev=2,
        ),
    )


@pytest.fixture
def prompt_builder():
    """Prompt builder instance"""
    return PromptBuilder()


# ============================================================================
# Initialization Tests
# ============================================================================


def test_prompt_builder_initialization(prompt_builder):
    """Test prompt builder initializes correctly"""
    assert prompt_builder is not None


# ============================================================================
# Full Prompt Building Tests
# ============================================================================


def test_build_trading_prompt_basic(prompt_builder, sample_snapshot):
    """Test basic prompt building with single symbol"""
    snapshots = {"BTCUSDT": sample_snapshot}
    capital_chf = Decimal("2626.96")
    max_position_chf = Decimal("525.39")

    prompt = prompt_builder.build_trading_prompt(
        snapshots=snapshots,
        capital_chf=capital_chf,
        max_position_size_chf=max_position_chf,
    )

    # Verify prompt contains key sections
    assert "# Trading Decision System" in prompt
    assert "# Trading Capital & Risk Parameters" in prompt
    assert "# Market Data Analysis" in prompt
    assert "# Output Format" in prompt

    # Verify capital information
    assert "CHF 2,626.96" in prompt
    assert "CHF 525.39" in prompt

    # Verify symbol appears
    assert "BTCUSDT" in prompt or "BTC/USDT:USDT" in prompt


def test_build_trading_prompt_multiple_symbols(prompt_builder, sample_snapshot):
    """Test prompt building with multiple symbols"""
    # Create snapshots for multiple symbols
    snapshots = {
        "BTCUSDT": sample_snapshot,
        "ETHUSDT": sample_snapshot,
        "SOLUSDT": sample_snapshot,
    }

    prompt = prompt_builder.build_trading_prompt(
        snapshots=snapshots,
        capital_chf=Decimal("2626.96"),
        max_position_size_chf=Decimal("525.39"),
    )

    # Verify number of assets
    assert "Number of Assets: 3" in prompt

    # Verify all symbols mentioned
    assert "BTCUSDT" in prompt or "BTC/USDT:USDT" in prompt
    assert "ETHUSDT" in prompt or "ETH/USDT:USDT" in prompt
    assert "SOLUSDT" in prompt or "SOL/USDT:USDT" in prompt


def test_build_trading_prompt_with_positions(prompt_builder, sample_snapshot):
    """Test prompt building with current positions"""
    snapshots = {"BTCUSDT": sample_snapshot}

    positions = {
        "BTCUSDT": {
            "side": "long",
            "size": 0.01,
            "entry_price": Decimal("49500"),
            "pnl": Decimal("70"),
            "stop_loss": Decimal("48525"),
        }
    }

    prompt = prompt_builder.build_trading_prompt(
        snapshots=snapshots,
        capital_chf=Decimal("2626.96"),
        max_position_size_chf=Decimal("525.39"),
        current_positions=positions,
    )

    # Verify positions section
    assert "# Current Open Positions" in prompt
    assert "long" in prompt
    assert "49500" in prompt or "49,500" in prompt


def test_build_trading_prompt_with_risk_context(prompt_builder, sample_snapshot):
    """Test prompt building with risk context"""
    snapshots = {"BTCUSDT": sample_snapshot}

    risk_context = {
        "daily_loss": "CHF -150",
        "circuit_breaker": "CHF -183.89",
        "open_positions": "2/6",
    }

    prompt = prompt_builder.build_trading_prompt(
        snapshots=snapshots,
        capital_chf=Decimal("2626.96"),
        max_position_size_chf=Decimal("525.39"),
        risk_context=risk_context,
    )

    # Verify risk context appears
    assert "Additional Risk Context" in prompt
    assert "CHF -150" in prompt
    assert "CHF -183.89" in prompt


# ============================================================================
# Section Building Tests
# ============================================================================


def test_build_system_context(prompt_builder):
    """Test system context section"""
    context = prompt_builder._build_system_context()

    assert "Trading Decision System" in context
    assert "expert cryptocurrency trading advisor" in context
    assert "BUY, SELL, HOLD, CLOSE" in context
    assert "Technical analysis" in context


def test_build_capital_context(prompt_builder):
    """Test capital context section"""
    context = prompt_builder._build_capital_context(
        capital_chf=Decimal("2626.96"),
        max_position_size_chf=Decimal("525.39"),
        risk_context=None,
    )

    assert "Trading Capital & Risk Parameters" in context
    assert "2,626.96" in context
    assert "525.39" in context
    assert "Stop-Loss" in context


def test_build_positions_context_empty(prompt_builder):
    """Test positions context with no positions"""
    context = prompt_builder._build_positions_context({})

    assert "Current Open Positions" in context
    assert "No open positions" in context


def test_build_positions_context_with_positions(prompt_builder):
    """Test positions context with positions"""
    positions = {
        "BTCUSDT": {
            "side": "long",
            "size": 0.01,
            "entry_price": Decimal("49500"),
            "pnl": Decimal("70"),
        }
    }

    context = prompt_builder._build_positions_context(positions)

    assert "Current Open Positions" in context
    assert "BTCUSDT" in context
    assert "long" in context


def test_build_market_data_section(prompt_builder, sample_snapshot):
    """Test market data section"""
    snapshots = {"BTCUSDT": sample_snapshot}

    section = prompt_builder._build_market_data_section(snapshots)

    assert "Market Data Analysis" in section
    assert "Number of Assets: 1" in section
    assert "BTCUSDT" in section or "BTC/USDT:USDT" in section


# ============================================================================
# Snapshot Formatting Tests
# ============================================================================


def test_format_snapshot_complete(prompt_builder, sample_snapshot):
    """Test formatting a complete snapshot with all indicators"""
    formatted = prompt_builder._format_snapshot("BTCUSDT", sample_snapshot)

    # Verify sections
    assert "## BTCUSDT" in formatted
    assert "### Price Action" in formatted
    assert "### Latest Candle (3min)" in formatted
    assert "### Technical Indicators" in formatted

    # Verify price data
    assert "50,200" in formatted or "50200" in formatted
    assert "24h Change:" in formatted

    # Verify indicators
    assert "RSI(14)" in formatted
    assert "55.1" in formatted or "55.5" in formatted  # RSI value
    assert "MACD" in formatted
    assert "EMA(12)" in formatted
    assert "EMA(26)" in formatted
    assert "Bollinger Bands" in formatted


def test_format_snapshot_bullish_candle(prompt_builder, sample_ohlcv, sample_ticker):
    """Test formatting bullish candle"""
    # Create bullish candle (close > open)
    ohlcv = OHLCV(
        symbol="BTC/USDT:USDT",
        timeframe=Timeframe.M3,
        timestamp=datetime.utcnow(),
        open=Decimal("49000"),
        high=Decimal("50500"),
        low=Decimal("48900"),
        close=Decimal("50200"),  # Higher than open
        volume=Decimal("100"),
        quote_volume=Decimal("5000000"),
        trades_count=1000,
    )

    snapshot = MarketDataSnapshot(
        symbol="BTC/USDT:USDT",
        timeframe=Timeframe.M3,
        timestamp=datetime.utcnow(),
        ohlcv=ohlcv,
        ticker=sample_ticker,
    )

    formatted = prompt_builder._format_snapshot("BTCUSDT", snapshot)

    assert "Bullish" in formatted or "🟢" in formatted


def test_format_snapshot_bearish_candle(prompt_builder, sample_ohlcv, sample_ticker):
    """Test formatting bearish candle"""
    # Create bearish candle (close < open)
    ohlcv = OHLCV(
        symbol="BTC/USDT:USDT",
        timeframe=Timeframe.M3,
        timestamp=datetime.utcnow(),
        open=Decimal("50200"),
        high=Decimal("50500"),
        low=Decimal("49000"),
        close=Decimal("49500"),  # Lower than open
        volume=Decimal("100"),
        quote_volume=Decimal("5000000"),
        trades_count=1000,
    )

    snapshot = MarketDataSnapshot(
        symbol="BTC/USDT:USDT",
        timeframe=Timeframe.M3,
        timestamp=datetime.utcnow(),
        ohlcv=ohlcv,
        ticker=sample_ticker,
    )

    formatted = prompt_builder._format_snapshot("BTCUSDT", snapshot)

    assert "Bearish" in formatted or "🔴" in formatted


def test_format_snapshot_rsi_oversold(prompt_builder, sample_ohlcv, sample_ticker):
    """Test formatting RSI oversold condition"""
    snapshot = MarketDataSnapshot(
        symbol="BTC/USDT:USDT",
        timeframe=Timeframe.M3,
        timestamp=datetime.utcnow(),
        ohlcv=sample_ohlcv,
        ticker=sample_ticker,
        rsi=RSI(
            symbol="BTC/USDT:USDT",
            timeframe=Timeframe.M3,
            timestamp=datetime.utcnow(),
            value=Decimal("25.0"),  # Oversold
            period=14,
        ),
    )

    formatted = prompt_builder._format_snapshot("BTCUSDT", snapshot)

    assert "Oversold" in formatted
    assert "BUY signal" in formatted or "BUY" in formatted


def test_format_snapshot_rsi_overbought(prompt_builder, sample_ohlcv, sample_ticker):
    """Test formatting RSI overbought condition"""
    snapshot = MarketDataSnapshot(
        symbol="BTC/USDT:USDT",
        timeframe=Timeframe.M3,
        timestamp=datetime.utcnow(),
        ohlcv=sample_ohlcv,
        ticker=sample_ticker,
        rsi=RSI(
            symbol="BTC/USDT:USDT",
            timeframe=Timeframe.M3,
            timestamp=datetime.utcnow(),
            value=Decimal("75.0"),  # Overbought
            period=14,
        ),
    )

    formatted = prompt_builder._format_snapshot("BTCUSDT", snapshot)

    assert "Overbought" in formatted
    assert "SELL signal" in formatted or "SELL" in formatted


def test_format_snapshot_macd_bullish(prompt_builder, sample_ohlcv, sample_ticker):
    """Test formatting bullish MACD"""
    snapshot = MarketDataSnapshot(
        symbol="BTC/USDT:USDT",
        timeframe=Timeframe.M3,
        timestamp=datetime.utcnow(),
        ohlcv=sample_ohlcv,
        ticker=sample_ticker,
        macd=MACD(
            symbol="BTC/USDT:USDT",
            timeframe=Timeframe.M3,
            timestamp=datetime.utcnow(),
            value=Decimal("150"),  # MACD > Signal
            signal=Decimal("100"),
            histogram=Decimal("50"),
            fast_period=12,
            slow_period=26,
            signal_period=9,
        ),
    )

    formatted = prompt_builder._format_snapshot("BTCUSDT", snapshot)

    assert "MACD" in formatted
    assert "Bullish" in formatted


def test_format_snapshot_bollinger_squeeze(prompt_builder, sample_ohlcv, sample_ticker):
    """Test formatting Bollinger Band squeeze"""
    snapshot = MarketDataSnapshot(
        symbol="BTC/USDT:USDT",
        timeframe=Timeframe.M3,
        timestamp=datetime.utcnow(),
        ohlcv=sample_ohlcv,
        ticker=sample_ticker,
        bollinger=BollingerBands(
            symbol="BTC/USDT:USDT",
            timeframe=Timeframe.M3,
            timestamp=datetime.utcnow(),
            middle=Decimal("50000"),
            upper=Decimal("50500"),
            lower=Decimal("49500"),
            bandwidth=Decimal("0.015"),  # Low bandwidth = squeeze
            period=20,
            std_dev=2,
        ),
    )

    formatted = prompt_builder._format_snapshot("BTCUSDT", snapshot)

    assert "Bollinger Bands" in formatted
    assert "Squeeze" in formatted or "low volatility" in formatted


# ============================================================================
# Output Format Tests
# ============================================================================


def test_build_output_format(prompt_builder):
    """Test output format specification"""
    output_format = prompt_builder._build_output_format()

    assert "# Output Format" in output_format
    assert "```json" in output_format
    assert '"decision": "BUY"' in output_format
    assert '"confidence":' in output_format
    assert '"size_pct":' in output_format
    assert '"reasoning":' in output_format

    # Verify decision guidelines
    assert "BUY:" in output_format
    assert "SELL:" in output_format
    assert "HOLD:" in output_format
    assert "CLOSE:" in output_format

    # Verify position sizing
    assert "Position Sizing Guidelines" in output_format
    assert "High confidence" in output_format

    # Verify stop-loss
    assert "Stop-Loss Guidelines" in output_format
