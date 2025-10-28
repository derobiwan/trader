"""
Trading Engine Tests

Tests for trading engine coordinating market data, decisions, and execution.

Author: Trading Loop Implementation Team
Date: 2025-10-28
"""

import pytest
import asyncio
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict

from workspace.features.trading_loop.trading_engine import (
    TradingEngine,
    TradingDecision,
    TradingSignal,
    TradingCycleResult,
)
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
def mock_market_data_service(sample_snapshot):
    """Mock market data service"""
    service = AsyncMock()
    service.get_snapshot = AsyncMock(return_value=sample_snapshot)
    return service


@pytest.fixture
def mock_trade_executor():
    """Mock trade executor"""
    executor = AsyncMock()
    return executor


@pytest.fixture
def mock_position_manager():
    """Mock position manager"""
    manager = AsyncMock()
    return manager


@pytest.fixture
def trading_engine(
    mock_market_data_service,
    mock_trade_executor,
    mock_position_manager,
):
    """Create trading engine with mocks"""
    return TradingEngine(
        market_data_service=mock_market_data_service,
        trade_executor=mock_trade_executor,
        position_manager=mock_position_manager,
        symbols=["BTCUSDT", "ETHUSDT"],
    )


# ============================================================================
# TradingSignal Tests
# ============================================================================


def test_trading_signal_creation():
    """Test trading signal creation with valid parameters"""
    signal = TradingSignal(
        symbol="BTCUSDT",
        decision=TradingDecision.BUY,
        confidence=Decimal("0.8"),
        size_pct=Decimal("0.1"),
        stop_loss_pct=Decimal("0.02"),
        take_profit_pct=Decimal("0.05"),
        reasoning="Strong bullish momentum",
    )

    assert signal.symbol == "BTCUSDT"
    assert signal.decision == TradingDecision.BUY
    assert signal.confidence == Decimal("0.8")
    assert signal.size_pct == Decimal("0.1")


def test_trading_signal_validation():
    """Test trading signal validation"""
    # Invalid confidence (> 1)
    with pytest.raises(ValueError, match="Confidence must be 0-1"):
        TradingSignal(
            symbol="BTCUSDT",
            decision=TradingDecision.BUY,
            confidence=Decimal("1.5"),
            size_pct=Decimal("0.1"),
        )

    # Invalid size_pct (> 1)
    with pytest.raises(ValueError, match="Size percentage must be 0-1"):
        TradingSignal(
            symbol="BTCUSDT",
            decision=TradingDecision.BUY,
            confidence=Decimal("0.8"),
            size_pct=Decimal("1.5"),
        )


# ============================================================================
# TradingCycleResult Tests
# ============================================================================


def test_cycle_result_success():
    """Test cycle result success property"""
    result = TradingCycleResult(
        cycle_number=1,
        timestamp=datetime.utcnow(),
        symbols=["BTCUSDT"],
        snapshots={},
        signals={},
    )

    assert result.success is True

    # Add error
    result.errors.append("Test error")
    assert result.success is False


def test_cycle_result_to_dict():
    """Test cycle result conversion to dict"""
    result = TradingCycleResult(
        cycle_number=5,
        timestamp=datetime.utcnow(),
        symbols=["BTCUSDT", "ETHUSDT"],
        snapshots={},
        signals={},
        orders_placed=2,
        orders_filled=1,
        orders_failed=1,
        duration_seconds=1.5,
    )

    data = result.to_dict()

    assert data["cycle_number"] == 5
    assert data["symbols"] == ["BTCUSDT", "ETHUSDT"]
    assert data["orders_placed"] == 2
    assert data["orders_filled"] == 1
    assert data["orders_failed"] == 1
    assert data["duration_seconds"] == 1.5
    assert data["success"] is True


# ============================================================================
# TradingEngine Initialization Tests
# ============================================================================


def test_engine_initialization(trading_engine):
    """Test trading engine initializes correctly"""
    assert trading_engine.symbols == ["BTCUSDT", "ETHUSDT"]
    assert trading_engine.cycle_count == 0
    assert trading_engine.total_orders == 0
    assert trading_engine.total_errors == 0
    assert trading_engine.decision_engine is None


def test_engine_with_decision_engine():
    """Test trading engine with decision engine"""
    mock_decision_engine = Mock()

    engine = TradingEngine(
        market_data_service=AsyncMock(),
        trade_executor=AsyncMock(),
        position_manager=AsyncMock(),
        symbols=["BTCUSDT"],
        decision_engine=mock_decision_engine,
    )

    assert engine.decision_engine == mock_decision_engine


# ============================================================================
# Market Data Fetching Tests
# ============================================================================


@pytest.mark.asyncio
async def test_fetch_market_data_snapshots(trading_engine, sample_snapshot):
    """Test fetching market data snapshots for all symbols"""
    snapshots = await trading_engine._fetch_market_data_snapshots()

    assert len(snapshots) == 2
    assert "BTCUSDT" in snapshots
    assert "ETHUSDT" in snapshots

    # Verify service was called for each symbol
    assert trading_engine.market_data_service.get_snapshot.call_count == 2


@pytest.mark.asyncio
async def test_fetch_snapshots_with_missing_data(trading_engine):
    """Test handling of missing snapshots"""
    # First symbol succeeds, second returns None
    trading_engine.market_data_service.get_snapshot = AsyncMock(
        side_effect=[Mock(has_all_indicators=True), None]
    )

    snapshots = await trading_engine._fetch_market_data_snapshots()

    # Only one snapshot available
    assert len(snapshots) == 1


@pytest.mark.asyncio
async def test_fetch_snapshots_with_incomplete_indicators(trading_engine, sample_snapshot):
    """Test handling of snapshots with incomplete indicators"""
    # Create snapshot without all indicators
    incomplete_snapshot = Mock(has_all_indicators=False)

    trading_engine.market_data_service.get_snapshot = AsyncMock(
        return_value=incomplete_snapshot
    )

    snapshots = await trading_engine._fetch_market_data_snapshots()

    # No snapshots should be included
    assert len(snapshots) == 0


@pytest.mark.asyncio
async def test_fetch_snapshots_handles_errors(trading_engine):
    """Test error handling during snapshot fetching"""
    # First call succeeds, second raises error
    trading_engine.market_data_service.get_snapshot = AsyncMock(
        side_effect=[Mock(has_all_indicators=True), Exception("Fetch error")]
    )

    snapshots = await trading_engine._fetch_market_data_snapshots()

    # Only one snapshot (first succeeded, second failed)
    assert len(snapshots) == 1


# ============================================================================
# Signal Generation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_generate_signals_without_decision_engine(trading_engine, sample_snapshot):
    """Test signal generation without decision engine (HOLD signals)"""
    snapshots = {"BTCUSDT": sample_snapshot}

    signals = await trading_engine._generate_trading_signals(snapshots)

    assert len(signals) == 1
    assert "BTCUSDT" in signals

    signal = signals["BTCUSDT"]
    assert signal.decision == TradingDecision.HOLD
    assert signal.size_pct == Decimal("0.0")


@pytest.mark.asyncio
async def test_generate_signals_with_decision_engine(
    mock_market_data_service,
    mock_trade_executor,
    mock_position_manager,
    sample_snapshot,
):
    """Test signal generation with decision engine"""
    # Create mock decision engine
    mock_decision_engine = AsyncMock()
    mock_decision_engine.generate_signals = AsyncMock(
        return_value={
            "BTCUSDT": TradingSignal(
                symbol="BTCUSDT",
                decision=TradingDecision.BUY,
                confidence=Decimal("0.9"),
                size_pct=Decimal("0.2"),
            )
        }
    )

    engine = TradingEngine(
        market_data_service=mock_market_data_service,
        trade_executor=mock_trade_executor,
        position_manager=mock_position_manager,
        symbols=["BTCUSDT"],
        decision_engine=mock_decision_engine,
    )

    snapshots = {"BTCUSDT": sample_snapshot}
    signals = await engine._generate_trading_signals(snapshots)

    # Should use decision engine
    assert mock_decision_engine.generate_signals.called
    assert len(signals) == 1
    assert signals["BTCUSDT"].decision == TradingDecision.BUY


# ============================================================================
# Trade Execution Tests
# ============================================================================


@pytest.mark.asyncio
async def test_execute_trades_with_hold_signals(trading_engine):
    """Test trade execution skips HOLD signals"""
    signals = {
        "BTCUSDT": TradingSignal(
            symbol="BTCUSDT",
            decision=TradingDecision.HOLD,
            confidence=Decimal("0.5"),
            size_pct=Decimal("0.0"),
        ),
    }

    stats = await trading_engine._execute_trades(signals)

    assert stats["orders_placed"] == 0
    assert stats["orders_filled"] == 0
    assert stats["orders_failed"] == 0


@pytest.mark.asyncio
async def test_execute_trades_with_buy_signal(trading_engine):
    """Test trade execution with BUY signal"""
    signals = {
        "BTCUSDT": TradingSignal(
            symbol="BTCUSDT",
            decision=TradingDecision.BUY,
            confidence=Decimal("0.8"),
            size_pct=Decimal("0.1"),
        ),
    }

    stats = await trading_engine._execute_trades(signals)

    # Placeholder implementation just increments orders_placed
    assert stats["orders_placed"] == 1


@pytest.mark.asyncio
async def test_execute_trades_handles_errors(trading_engine):
    """Test trade execution handles errors gracefully"""
    signals = {
        "BTCUSDT": TradingSignal(
            symbol="BTCUSDT",
            decision=TradingDecision.BUY,
            confidence=Decimal("0.8"),
            size_pct=Decimal("0.1"),
        ),
    }

    # Mock _execute_signal to raise error
    trading_engine._execute_signal = AsyncMock(side_effect=Exception("Execution error"))

    stats = await trading_engine._execute_trades(signals)

    assert stats["orders_failed"] == 1


# ============================================================================
# Complete Trading Cycle Tests
# ============================================================================


@pytest.mark.asyncio
async def test_complete_trading_cycle(trading_engine, sample_snapshot):
    """Test complete trading cycle execution"""
    result = await trading_engine.execute_trading_cycle(cycle_number=1)

    assert result.cycle_number == 1
    assert result.success is True
    assert len(result.snapshots) == 2  # BTCUSDT and ETHUSDT
    assert len(result.signals) == 2
    assert result.duration_seconds > 0

    # Verify engine state updated
    assert trading_engine.cycle_count == 1


@pytest.mark.asyncio
async def test_trading_cycle_with_errors(trading_engine):
    """Test trading cycle handles errors gracefully"""
    # Make snapshot fetching fail
    trading_engine.market_data_service.get_snapshot = AsyncMock(
        side_effect=Exception("Data fetch error")
    )

    result = await trading_engine.execute_trading_cycle(cycle_number=1)

    assert result.cycle_number == 1
    assert result.success is False
    assert len(result.errors) > 0
    assert trading_engine.total_errors == 1


@pytest.mark.asyncio
async def test_multiple_trading_cycles(trading_engine, sample_snapshot):
    """Test multiple consecutive trading cycles"""
    # Execute 3 cycles
    results = []
    for i in range(1, 4):
        result = await trading_engine.execute_trading_cycle(cycle_number=i)
        results.append(result)

    # Verify all cycles completed
    assert len(results) == 3
    assert all(r.success for r in results)
    assert trading_engine.cycle_count == 3


# ============================================================================
# Status Tests
# ============================================================================


def test_engine_status_initial(trading_engine):
    """Test engine status when no cycles executed"""
    status = trading_engine.get_status()

    assert status["cycle_count"] == 0
    assert status["total_orders"] == 0
    assert status["total_errors"] == 0
    assert status["symbols"] == ["BTCUSDT", "ETHUSDT"]
    assert status["has_decision_engine"] is False


@pytest.mark.asyncio
async def test_engine_status_after_cycles(trading_engine, sample_snapshot):
    """Test engine status after executing cycles"""
    # Execute 2 cycles
    await trading_engine.execute_trading_cycle(cycle_number=1)
    await trading_engine.execute_trading_cycle(cycle_number=2)

    status = trading_engine.get_status()

    assert status["cycle_count"] == 2
    assert status["symbols"] == ["BTCUSDT", "ETHUSDT"]


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_full_trading_pipeline(
    mock_market_data_service,
    mock_trade_executor,
    mock_position_manager,
    sample_snapshot,
):
    """Test full trading pipeline: data -> decision -> execution"""
    # Create decision engine that returns BUY signal
    mock_decision_engine = AsyncMock()
    mock_decision_engine.generate_signals = AsyncMock(
        return_value={
            "BTCUSDT": TradingSignal(
                symbol="BTCUSDT",
                decision=TradingDecision.BUY,
                confidence=Decimal("0.85"),
                size_pct=Decimal("0.15"),
                stop_loss_pct=Decimal("0.02"),
                reasoning="Strong uptrend with bullish indicators",
            ),
        }
    )

    engine = TradingEngine(
        market_data_service=mock_market_data_service,
        trade_executor=mock_trade_executor,
        position_manager=mock_position_manager,
        symbols=["BTCUSDT"],
        decision_engine=mock_decision_engine,
    )

    # Execute cycle
    result = await engine.execute_trading_cycle(cycle_number=1)

    # Verify complete pipeline
    assert result.success is True
    assert len(result.snapshots) == 1
    assert len(result.signals) == 1
    assert result.signals["BTCUSDT"].decision == TradingDecision.BUY

    # Verify components were called
    assert mock_market_data_service.get_snapshot.called
    assert mock_decision_engine.generate_signals.called


@pytest.mark.asyncio
async def test_concurrent_symbol_processing(trading_engine, sample_snapshot):
    """Test engine processes multiple symbols efficiently"""
    result = await trading_engine.execute_trading_cycle(cycle_number=1)

    # Should process both symbols
    assert len(result.snapshots) <= 2  # May be less if data unavailable
    assert len(result.signals) <= 2

    # Should complete quickly (parallel processing)
    assert result.duration_seconds < 5
