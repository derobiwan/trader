"""
LLM Decision Engine Tests

Tests for LLM-powered trading signal generation.

Author: Decision Engine Implementation Team
Date: 2025-10-28
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch

import pytest

from workspace.features.decision_engine.llm_engine import LLMDecisionEngine, LLMProvider
from workspace.features.market_data import (
    OHLCV,
    RSI,
    MarketDataSnapshot,
    Ticker,
    Timeframe,
)
from workspace.features.trading_loop import TradingDecision

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_snapshot():
    """Sample market data snapshot"""
    return MarketDataSnapshot(
        symbol="BTC/USDT:USDT",
        timeframe=Timeframe.M3,
        timestamp=datetime.utcnow(),
        ohlcv=OHLCV(
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
        ),
        ticker=Ticker(
            symbol="BTC/USDT:USDT",
            last=Decimal("50200"),
            bid=Decimal("50190"),
            ask=Decimal("50210"),
            high_24h=Decimal("51000"),
            low_24h=Decimal("49000"),
            volume_24h=Decimal("10000"),
            quote_volume_24h=Decimal("500000000"),
            timestamp=datetime.utcnow(),
        ),
        rsi=RSI(
            symbol="BTC/USDT:USDT",
            timeframe=Timeframe.M3,
            timestamp=datetime.utcnow(),
            value=Decimal("55.5"),
            period=14,
        ),
    )


@pytest.fixture
def llm_engine():
    """LLM decision engine with test configuration"""
    return LLMDecisionEngine(
        provider="openrouter",
        model="anthropic/claude-3.5-sonnet",
        api_key="test-api-key",
    )


# ============================================================================
# Initialization Tests
# ============================================================================


def test_engine_initialization():
    """Test engine initializes with correct defaults"""
    engine = LLMDecisionEngine(
        provider="openrouter",
        model="anthropic/claude-3.5-sonnet",
        api_key="test-key",
    )

    assert engine.config.provider == LLMProvider.OPENROUTER
    assert engine.config.model == "anthropic/claude-3.5-sonnet"
    assert engine.config.api_key == "test-key"
    assert engine.config.temperature == 0.7
    assert engine.config.max_tokens == 2000
    assert engine.prompt_builder is not None
    assert engine.client is not None


def test_engine_custom_config():
    """Test engine with custom configuration"""
    engine = LLMDecisionEngine(
        provider="openrouter",
        model="openai/gpt-4",
        api_key="custom-key",
        temperature=0.5,
        max_tokens=1500,
        timeout=45.0,
    )

    assert engine.config.model == "openai/gpt-4"
    assert engine.config.temperature == 0.5
    assert engine.config.max_tokens == 1500
    assert engine.config.timeout == 45.0


# ============================================================================
# Signal Generation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_generate_signals_basic(llm_engine, sample_snapshot):
    """Test basic signal generation"""
    snapshots = {"BTCUSDT": sample_snapshot}

    # Mock the LLM call
    mock_response = """
```json
{
  "symbol": "BTCUSDT",
  "decision": "BUY",
  "confidence": 0.75,
  "size_pct": 0.15,
  "stop_loss_pct": 0.02,
  "take_profit_pct": 0.05,
  "reasoning": "Bullish momentum with RSI neutral."
}
```
"""

    with patch.object(
        llm_engine, "_call_llm", new=AsyncMock(return_value=mock_response)
    ):
        signals = await llm_engine.generate_signals(
            snapshots=snapshots,
            capital_chf=Decimal("2626.96"),
        )

        assert len(signals) == 1
        assert "BTCUSDT" in signals

        signal = signals["BTCUSDT"]
        assert signal.decision == TradingDecision.BUY
        assert signal.confidence == Decimal("0.75")
        assert signal.size_pct == Decimal("0.15")


@pytest.mark.asyncio
async def test_generate_signals_multiple_symbols(llm_engine, sample_snapshot):
    """Test signal generation for multiple symbols"""
    snapshots = {
        "BTCUSDT": sample_snapshot,
        "ETHUSDT": sample_snapshot,
    }

    # Mock response with multiple signals
    mock_response = """
```json
{
  "symbol": "BTCUSDT",
  "decision": "BUY",
  "confidence": 0.75,
  "size_pct": 0.15,
  "reasoning": "Bullish"
}
```

```json
{
  "symbol": "ETHUSDT",
  "decision": "HOLD",
  "confidence": 0.5,
  "size_pct": 0.0,
  "reasoning": "Wait"
}
```
"""

    with patch.object(
        llm_engine, "_call_llm", new=AsyncMock(return_value=mock_response)
    ):
        signals = await llm_engine.generate_signals(snapshots=snapshots)

        assert len(signals) == 2
        assert signals["BTCUSDT"].decision == TradingDecision.BUY
        assert signals["ETHUSDT"].decision == TradingDecision.HOLD


@pytest.mark.asyncio
async def test_generate_signals_with_positions(llm_engine, sample_snapshot):
    """Test signal generation with current positions"""
    snapshots = {"BTCUSDT": sample_snapshot}
    positions = {
        "BTCUSDT": {
            "side": "long",
            "entry_price": Decimal("49500"),
            "pnl": Decimal("70"),
        }
    }

    mock_response = """
```json
{
  "symbol": "BTCUSDT",
  "decision": "CLOSE",
  "confidence": 0.8,
  "size_pct": 0.0,
  "reasoning": "Take profit"
}
```
"""

    with patch.object(
        llm_engine, "_call_llm", new=AsyncMock(return_value=mock_response)
    ):
        signals = await llm_engine.generate_signals(
            snapshots=snapshots,
            current_positions=positions,
        )

        assert signals["BTCUSDT"].decision == TradingDecision.CLOSE


@pytest.mark.asyncio
async def test_generate_signals_error_fallback(llm_engine, sample_snapshot):
    """Test fallback to HOLD signals on error"""
    snapshots = {"BTCUSDT": sample_snapshot}

    # Mock LLM error
    with patch.object(
        llm_engine, "_call_llm", new=AsyncMock(side_effect=Exception("API error"))
    ):
        signals = await llm_engine.generate_signals(snapshots=snapshots)

        # Should return fallback HOLD signals
        assert len(signals) == 1
        assert signals["BTCUSDT"].decision == TradingDecision.HOLD
        assert "Fallback" in signals["BTCUSDT"].reasoning


# ============================================================================
# Response Parsing Tests
# ============================================================================


def test_parse_response_valid_single(llm_engine, sample_snapshot):
    """Test parsing valid single-signal response"""
    response = """
```json
{
  "symbol": "BTCUSDT",
  "decision": "BUY",
  "confidence": 0.8,
  "size_pct": 0.2,
  "stop_loss_pct": 0.02,
  "reasoning": "Strong buy signal"
}
```
"""

    snapshots = {"BTCUSDT": sample_snapshot}
    signals = llm_engine._parse_response(response, snapshots)

    assert len(signals) == 1
    assert signals["BTCUSDT"].decision == TradingDecision.BUY


def test_parse_response_valid_multiple(llm_engine, sample_snapshot):
    """Test parsing multiple signals"""
    response = """
```json
{
  "symbol": "BTCUSDT",
  "decision": "BUY",
  "confidence": 0.8,
  "size_pct": 0.2,
  "reasoning": "Buy"
}
```

```json
{
  "symbol": "ETHUSDT",
  "decision": "SELL",
  "confidence": 0.7,
  "size_pct": 0.15,
  "reasoning": "Sell"
}
```
"""

    snapshots = {
        "BTCUSDT": sample_snapshot,
        "ETHUSDT": sample_snapshot,
    }
    signals = llm_engine._parse_response(response, snapshots)

    assert len(signals) == 2
    assert signals["BTCUSDT"].decision == TradingDecision.BUY
    assert signals["ETHUSDT"].decision == TradingDecision.SELL


def test_parse_response_missing_symbol(llm_engine, sample_snapshot):
    """Test parsing handles missing symbol in response"""
    response = """
```json
{
  "symbol": "BTCUSDT",
  "decision": "BUY",
  "confidence": 0.8,
  "size_pct": 0.2,
  "reasoning": "Buy"
}
```
"""

    snapshots = {
        "BTCUSDT": sample_snapshot,
        "ETHUSDT": sample_snapshot,  # No signal for ETH
    }
    signals = llm_engine._parse_response(response, snapshots)

    # Should have signal for BTC
    assert signals["BTCUSDT"].decision == TradingDecision.BUY

    # Should generate HOLD for missing ETH
    assert signals["ETHUSDT"].decision == TradingDecision.HOLD


def test_parse_response_invalid_json(llm_engine, sample_snapshot):
    """Test parsing handles invalid JSON"""
    response = "This is not JSON"

    snapshots = {"BTCUSDT": sample_snapshot}
    signals = llm_engine._parse_response(response, snapshots)

    # Should return fallback HOLD signals
    assert len(signals) == 1
    assert signals["BTCUSDT"].decision == TradingDecision.HOLD


def test_parse_response_empty(llm_engine, sample_snapshot):
    """Test parsing empty response"""
    response = ""

    snapshots = {"BTCUSDT": sample_snapshot}
    signals = llm_engine._parse_response(response, snapshots)

    # Should return fallback HOLD signals
    assert len(signals) == 1
    assert signals["BTCUSDT"].decision == TradingDecision.HOLD


# ============================================================================
# JSON Extraction Tests
# ============================================================================


def test_extract_json_blocks_code_fence(llm_engine):
    """Test extracting JSON from code fences"""
    text = """
Here is the analysis:

```json
{"symbol": "BTCUSDT", "decision": "BUY"}
```

And another:

```json
{"symbol": "ETHUSDT", "decision": "SELL"}
```
"""

    blocks = llm_engine._extract_json_blocks(text)

    assert len(blocks) == 2
    assert "BTCUSDT" in blocks[0]
    assert "ETHUSDT" in blocks[1]


def test_extract_json_blocks_standalone(llm_engine):
    """Test extracting standalone JSON objects"""
    text = """
Here is my decision: {"symbol": "BTCUSDT", "decision": "BUY", "confidence": 0.8}
"""

    blocks = llm_engine._extract_json_blocks(text)

    assert len(blocks) >= 1
    assert any("BTCUSDT" in block for block in blocks)


def test_extract_json_blocks_no_json(llm_engine):
    """Test extraction with no JSON"""
    text = "This text has no JSON at all."

    blocks = llm_engine._extract_json_blocks(text)

    assert len(blocks) == 0


# ============================================================================
# Signal Creation Tests
# ============================================================================


def test_create_signal_from_json_valid(llm_engine):
    """Test creating signal from valid JSON"""
    data = {
        "symbol": "BTCUSDT",
        "decision": "BUY",
        "confidence": 0.8,
        "size_pct": 0.15,
        "stop_loss_pct": 0.02,
        "take_profit_pct": 0.05,
        "reasoning": "Strong buy",
    }

    signal = llm_engine._create_signal_from_json(data)

    assert signal is not None
    assert signal.symbol == "BTCUSDT"
    assert signal.decision == TradingDecision.BUY
    assert signal.confidence == Decimal("0.8")
    assert signal.size_pct == Decimal("0.15")
    assert signal.stop_loss_pct == Decimal("0.02")
    assert signal.reasoning == "Strong buy"


def test_create_signal_from_json_minimal(llm_engine):
    """Test creating signal with minimal fields"""
    data = {
        "symbol": "BTCUSDT",
        "decision": "HOLD",
        "confidence": 0.5,
        "size_pct": 0.0,
    }

    signal = llm_engine._create_signal_from_json(data)

    assert signal is not None
    assert signal.symbol == "BTCUSDT"
    assert signal.decision == TradingDecision.HOLD
    assert signal.stop_loss_pct is None
    assert signal.take_profit_pct is None


def test_create_signal_from_json_invalid_decision(llm_engine):
    """Test handling invalid decision"""
    data = {
        "symbol": "BTCUSDT",
        "decision": "INVALID",
        "confidence": 0.5,
        "size_pct": 0.0,
    }

    signal = llm_engine._create_signal_from_json(data)

    assert signal is None


def test_create_signal_from_json_missing_symbol(llm_engine):
    """Test handling missing symbol"""
    data = {
        "decision": "BUY",
        "confidence": 0.8,
        "size_pct": 0.15,
    }

    signal = llm_engine._create_signal_from_json(data)

    assert signal is None


def test_create_signal_from_json_case_insensitive(llm_engine):
    """Test decision is case-insensitive"""
    for decision_str in ["buy", "BUY", "Buy", "bUy"]:
        data = {
            "symbol": "BTCUSDT",
            "decision": decision_str,
            "confidence": 0.8,
            "size_pct": 0.15,
        }

        signal = llm_engine._create_signal_from_json(data)

        assert signal is not None
        assert signal.decision == TradingDecision.BUY


# ============================================================================
# Fallback Signals Tests
# ============================================================================


def test_generate_fallback_signals(llm_engine, sample_snapshot):
    """Test fallback signal generation"""
    snapshots = {
        "BTCUSDT": sample_snapshot,
        "ETHUSDT": sample_snapshot,
    }

    signals = llm_engine._generate_fallback_signals(snapshots)

    assert len(signals) == 2

    for _symbol, signal in signals.items():
        assert signal.decision == TradingDecision.HOLD
        assert signal.confidence == Decimal("0.5")
        assert signal.size_pct == Decimal("0.0")
        assert "Fallback" in signal.reasoning


# ============================================================================
# API Call Tests (Mocked)
# ============================================================================


@pytest.mark.asyncio
async def test_call_openrouter_success(llm_engine):
    """Test successful OpenRouter API call"""
    mock_response = {"choices": [{"message": {"content": "Test response"}}]}

    # Mock httpx client
    with patch.object(llm_engine.client, "post", new=AsyncMock()) as mock_post:
        mock_post.return_value.json.return_value = mock_response
        mock_post.return_value.raise_for_status = Mock()

        response = await llm_engine._call_openrouter("Test prompt")

        assert response == "Test response"
        assert mock_post.called


@pytest.mark.asyncio
async def test_call_openrouter_empty_response(llm_engine):
    """Test handling empty OpenRouter response"""
    mock_response = {"choices": [{"message": {"content": ""}}]}

    with patch.object(llm_engine.client, "post", new=AsyncMock()) as mock_post:
        mock_post.return_value.json.return_value = mock_response
        mock_post.return_value.raise_for_status = Mock()

        with pytest.raises(ValueError, match="Empty response"):
            await llm_engine._call_openrouter("Test prompt")


@pytest.mark.asyncio
async def test_call_openrouter_api_error(llm_engine):
    """Test handling API error"""
    with patch.object(llm_engine.client, "post", new=AsyncMock()) as mock_post:
        import httpx

        mock_post.side_effect = httpx.HTTPStatusError(
            "API error",
            request=Mock(),
            response=Mock(status_code=500, text="Internal error"),
        )

        with pytest.raises(Exception, match="OpenRouter API error"):
            await llm_engine._call_openrouter("Test prompt")


@pytest.mark.asyncio
async def test_call_openrouter_network_error(llm_engine):
    """Test handling network error"""
    with patch.object(llm_engine.client, "post", new=AsyncMock()) as mock_post:
        mock_post.side_effect = Exception("Network timeout")

        with pytest.raises(
            Exception
        ):  # noqa: B017 - Testing generic exception handling for network errors
            await llm_engine._call_openrouter("Test prompt")


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_close_engine(llm_engine):
    """Test engine cleanup"""
    await llm_engine.close()

    # Client should be closed (no more requests possible)
    # This is mainly to ensure no resource leaks
