"""
Market Data Service Tests

Comprehensive tests for models, indicators, WebSocket, and market data service.

Author: Market Data Service Implementation Team
Date: 2025-10-27
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from workspace.features.market_data.indicators import IndicatorCalculator
from workspace.features.market_data.market_data_service import \
    MarketDataService
from workspace.features.market_data.models import (MACD, OHLCV, RSI,
                                                   BollingerBands,
                                                   MarketDataSnapshot, Ticker,
                                                   Timeframe)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_ohlcv_data():
    """Create sample OHLCV data for testing"""
    base_time = datetime(2025, 10, 27, 10, 0, 0)
    candles = []

    # Create 50 candles with slight upward trend
    for i in range(50):
        timestamp = base_time + timedelta(minutes=3 * i)
        base_price = Decimal("90000") + Decimal(str(i * 10))

        candle = OHLCV(
            symbol="BTC/USDT:USDT",
            timeframe=Timeframe.M3,
            timestamp=timestamp,
            open=base_price,
            high=base_price + Decimal("100"),
            low=base_price - Decimal("50"),
            close=base_price + Decimal("50"),
            volume=Decimal("1.5"),
        )
        candles.append(candle)

    return candles


@pytest.fixture
def sample_ticker():
    """Create sample ticker data"""
    return Ticker(
        symbol="BTC/USDT:USDT",
        timestamp=datetime.utcnow(),
        bid=Decimal("89999.50"),
        ask=Decimal("90000.50"),
        last=Decimal("90000.00"),
        high_24h=Decimal("91000.00"),
        low_24h=Decimal("89000.00"),
        volume_24h=Decimal("1234.567"),
        change_24h=Decimal("1000.00"),
        change_24h_pct=Decimal("1.11"),
    )


# ============================================================================
# Model Tests
# ============================================================================


def test_ohlcv_properties():
    """Test OHLCV calculated properties"""
    candle = OHLCV(
        symbol="BTC/USDT:USDT",
        timeframe=Timeframe.M3,
        timestamp=datetime.utcnow(),
        open=Decimal("90000"),
        high=Decimal("90500"),
        low=Decimal("89500"),
        close=Decimal("90200"),
        volume=Decimal("1.5"),
    )

    assert candle.price_change == Decimal("200")  # 90200 - 90000
    assert candle.is_bullish is True
    assert candle.body_size == Decimal("200")
    assert candle.range_size == Decimal("1000")  # 90500 - 89500
    assert candle.upper_wick == Decimal("300")  # 90500 - 90200
    assert candle.lower_wick == Decimal("500")  # 90000 - 89500


def test_ticker_properties(sample_ticker):
    """Test Ticker calculated properties"""
    assert sample_ticker.spread == Decimal("1.00")  # 90000.50 - 89999.50
    assert sample_ticker.mid_price == Decimal("90000.00")
    assert sample_ticker.spread_pct > Decimal("0")


def test_rsi_signal():
    """Test RSI signal generation"""
    # Oversold RSI
    rsi_oversold = RSI(
        symbol="BTC/USDT:USDT",
        timeframe=Timeframe.M3,
        timestamp=datetime.utcnow(),
        value=Decimal("25"),
    )
    assert rsi_oversold.is_oversold is True
    assert rsi_oversold.signal == "buy"

    # Overbought RSI
    rsi_overbought = RSI(
        symbol="BTC/USDT:USDT",
        timeframe=Timeframe.M3,
        timestamp=datetime.utcnow(),
        value=Decimal("75"),
    )
    assert rsi_overbought.is_overbought is True
    assert rsi_overbought.signal == "sell"

    # Neutral RSI
    rsi_neutral = RSI(
        symbol="BTC/USDT:USDT",
        timeframe=Timeframe.M3,
        timestamp=datetime.utcnow(),
        value=Decimal("50"),
    )
    assert rsi_neutral.signal == "neutral"


def test_macd_signal():
    """Test MACD signal generation"""
    # Bullish MACD
    macd_bullish = MACD(
        symbol="BTC/USDT:USDT",
        timeframe=Timeframe.M3,
        timestamp=datetime.utcnow(),
        macd_line=Decimal("100"),
        signal_line=Decimal("50"),
        histogram=Decimal("50"),
    )
    assert macd_bullish.signal == "buy"

    # Bearish MACD
    macd_bearish = MACD(
        symbol="BTC/USDT:USDT",
        timeframe=Timeframe.M3,
        timestamp=datetime.utcnow(),
        macd_line=Decimal("-100"),
        signal_line=Decimal("-50"),
        histogram=Decimal("-50"),
    )
    assert macd_bearish.signal == "sell"


def test_bollinger_bands_position():
    """Test Bollinger Bands position detection"""
    bb = BollingerBands(
        symbol="BTC/USDT:USDT",
        timeframe=Timeframe.M3,
        timestamp=datetime.utcnow(),
        upper_band=Decimal("91000"),
        middle_band=Decimal("90000"),
        lower_band=Decimal("89000"),
        bandwidth=Decimal("2000"),
    )

    assert bb.get_position_relative_to_bands(Decimal("92000")) == "above"
    assert bb.get_position_relative_to_bands(Decimal("90500")) == "upper"
    assert bb.get_position_relative_to_bands(Decimal("89500")) == "lower"
    assert bb.get_position_relative_to_bands(Decimal("88000")) == "below"


def test_market_data_snapshot_llm_format(sample_ohlcv_data, sample_ticker):
    """Test MarketDataSnapshot LLM prompt data formatting"""
    rsi = RSI(
        symbol="BTC/USDT:USDT",
        timeframe=Timeframe.M3,
        timestamp=datetime.utcnow(),
        value=Decimal("65"),
    )

    snapshot = MarketDataSnapshot(
        symbol="BTC/USDT:USDT",
        timeframe=Timeframe.M3,
        timestamp=datetime.utcnow(),
        ohlcv=sample_ohlcv_data[-1],
        ticker=sample_ticker,
        rsi=rsi,
    )

    llm_data = snapshot.to_llm_prompt_data()

    assert "symbol" in llm_data
    assert "price" in llm_data
    assert "candle" in llm_data
    assert "rsi" in llm_data
    assert llm_data["rsi"]["signal"] == "neutral"


# ============================================================================
# Indicator Tests
# ============================================================================


def test_calculate_rsi(sample_ohlcv_data):
    """Test RSI calculation"""
    rsi = IndicatorCalculator.calculate_rsi(sample_ohlcv_data, period=14)

    assert rsi is not None
    assert isinstance(rsi.value, Decimal)
    assert Decimal("0") <= rsi.value <= Decimal("100")


def test_calculate_rsi_insufficient_data():
    """Test RSI with insufficient data"""
    # Only 10 candles, need 15 for period=14
    short_data = [
        OHLCV(
            symbol="BTC/USDT:USDT",
            timeframe=Timeframe.M3,
            timestamp=datetime.utcnow(),
            open=Decimal("90000"),
            high=Decimal("90100"),
            low=Decimal("89900"),
            close=Decimal("90050"),
            volume=Decimal("1"),
        )
        for _ in range(10)
    ]

    rsi = IndicatorCalculator.calculate_rsi(short_data, period=14)
    assert rsi is None


def test_calculate_ema(sample_ohlcv_data):
    """Test EMA calculation"""
    ema = IndicatorCalculator.calculate_ema(sample_ohlcv_data, period=12)

    assert ema is not None
    assert isinstance(ema.value, Decimal)
    assert ema.value > Decimal("0")


def test_calculate_macd(sample_ohlcv_data):
    """Test MACD calculation"""
    macd = IndicatorCalculator.calculate_macd(sample_ohlcv_data)

    assert macd is not None
    assert isinstance(macd.macd_line, Decimal)
    assert isinstance(macd.signal_line, Decimal)
    assert isinstance(macd.histogram, Decimal)
    assert macd.histogram == macd.macd_line - macd.signal_line


def test_calculate_bollinger_bands(sample_ohlcv_data):
    """Test Bollinger Bands calculation"""
    bb = IndicatorCalculator.calculate_bollinger_bands(sample_ohlcv_data, period=20)

    assert bb is not None
    assert bb.upper_band > bb.middle_band
    assert bb.middle_band > bb.lower_band
    assert bb.bandwidth == bb.upper_band - bb.lower_band


def test_calculate_all_indicators(sample_ohlcv_data):
    """Test calculating all indicators at once"""
    indicators = IndicatorCalculator.calculate_all_indicators(sample_ohlcv_data)

    assert "rsi" in indicators
    assert "macd" in indicators
    assert "ema_fast" in indicators
    assert "ema_slow" in indicators
    assert "bollinger" in indicators

    # All should be calculated successfully
    assert indicators["rsi"] is not None
    assert indicators["macd"] is not None
    assert indicators["ema_fast"] is not None
    assert indicators["ema_slow"] is not None
    assert indicators["bollinger"] is not None


# ============================================================================
# Market Data Service Tests
# ============================================================================


@pytest.fixture
def mock_db_pool():
    """Mock database connection pool"""
    with patch(
        "workspace.features.market_data.market_data_service.DatabasePool"
    ) as mock_pool:
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_pool.get_connection.return_value.__aenter__.return_value = mock_conn
        yield mock_pool


@pytest.mark.asyncio
async def test_market_data_service_initialization(mock_db_pool):
    """Test MarketDataService initialization"""
    service = MarketDataService(
        symbols=["BTCUSDT", "ETHUSDT"],
        timeframe=Timeframe.M3,
        testnet=True,
    )

    assert len(service.symbols) == 2
    assert service.timeframe == Timeframe.M3
    assert service.testnet is True
    assert len(service.ohlcv_data) == 2


@pytest.mark.asyncio
async def test_market_data_service_ticker_update(mock_db_pool, sample_ticker):
    """Test handling ticker updates"""
    service = MarketDataService(
        symbols=["BTCUSDT"],
        testnet=True,
    )

    # Simulate ticker update
    await service._handle_ticker_update(sample_ticker)

    # Check if ticker was stored
    assert sample_ticker.symbol in service.latest_tickers
    stored_ticker = service.latest_tickers[sample_ticker.symbol]
    assert stored_ticker.last == sample_ticker.last


@pytest.mark.asyncio
async def test_market_data_service_kline_update(mock_db_pool, sample_ohlcv_data):
    """Test handling kline updates"""
    service = MarketDataService(
        symbols=["BTCUSDT"],
        testnet=True,
    )

    # Simulate kline update
    candle = sample_ohlcv_data[0]
    await service._handle_kline_update(candle)

    # Check if candle was stored
    symbol = candle.symbol
    assert symbol in service.ohlcv_data
    assert len(service.ohlcv_data[symbol]) == 1
    assert service.ohlcv_data[symbol][0].close == candle.close


@pytest.mark.asyncio
async def test_market_data_service_indicator_calculation(
    mock_db_pool, sample_ohlcv_data, sample_ticker
):
    """Test indicator calculation"""
    service = MarketDataService(
        symbols=["BTCUSDT"],
        testnet=True,
    )

    # Add historical data and ticker
    symbol = "BTC/USDT:USDT"
    service.ohlcv_data[symbol] = sample_ohlcv_data
    service.latest_tickers[symbol] = sample_ticker

    # Calculate indicators
    await service._update_indicators(symbol)

    # Check if snapshot was created
    assert symbol in service.latest_snapshots
    snapshot = service.latest_snapshots[symbol]

    assert snapshot.rsi is not None
    assert snapshot.macd is not None
    assert snapshot.ema_fast is not None
    assert snapshot.ema_slow is not None
    assert snapshot.bollinger is not None


@pytest.mark.asyncio
async def test_get_snapshot(mock_db_pool, sample_ohlcv_data, sample_ticker):
    """Test retrieving market data snapshot"""
    service = MarketDataService(
        symbols=["BTCUSDT"],
        testnet=True,
    )

    # Setup data
    symbol = "BTC/USDT:USDT"
    service.ohlcv_data[symbol] = sample_ohlcv_data
    service.latest_tickers[symbol] = sample_ticker
    await service._update_indicators(symbol)

    # Get snapshot
    snapshot = await service.get_snapshot("BTCUSDT")

    assert snapshot is not None
    assert snapshot.symbol == symbol
    assert snapshot.has_all_indicators is True


@pytest.mark.asyncio
async def test_get_ohlcv_history(mock_db_pool, sample_ohlcv_data):
    """Test retrieving OHLCV history"""
    service = MarketDataService(
        symbols=["BTCUSDT"],
        testnet=True,
    )

    # Add data
    symbol = "BTC/USDT:USDT"
    service.ohlcv_data[symbol] = sample_ohlcv_data

    # Get history
    history = await service.get_ohlcv_history("BTCUSDT", limit=10)

    assert len(history) == 10
    assert all(isinstance(candle, OHLCV) for candle in history)


@pytest.mark.asyncio
async def test_format_symbol():
    """Test symbol formatting"""
    service = MarketDataService(symbols=["BTCUSDT"], testnet=True)

    # Test various formats
    assert service._format_symbol("BTCUSDT") == "BTC/USDT:USDT"
    assert service._format_symbol("BTC/USDT:USDT") == "BTC/USDT:USDT"


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_full_data_pipeline(mock_db_pool, sample_ohlcv_data, sample_ticker):
    """Test complete data pipeline from WebSocket to snapshot"""
    service = MarketDataService(
        symbols=["BTCUSDT"],
        timeframe=Timeframe.M3,
        testnet=True,
    )

    symbol = "BTC/USDT:USDT"

    # 1. Receive ticker update
    await service._handle_ticker_update(sample_ticker)
    assert symbol in service.latest_tickers

    # 2. Receive kline updates
    for candle in sample_ohlcv_data:
        await service._handle_kline_update(candle)

    assert len(service.ohlcv_data[symbol]) == len(sample_ohlcv_data)

    # 3. Calculate indicators
    await service._update_indicators(symbol)

    # 4. Get snapshot
    snapshot = await service.get_snapshot("BTCUSDT")

    assert snapshot is not None
    assert snapshot.ticker.last == sample_ticker.last
    assert snapshot.ohlcv.close == sample_ohlcv_data[-1].close
    assert snapshot.has_all_indicators is True

    # 5. Format for LLM
    llm_data = snapshot.to_llm_prompt_data()
    assert "symbol" in llm_data
    assert "price" in llm_data
    assert "rsi" in llm_data
    assert "macd" in llm_data


# ============================================================================
# Performance Tests
# ============================================================================


@pytest.mark.asyncio
async def test_indicator_calculation_performance(sample_ohlcv_data):
    """Test indicator calculation performance"""
    import time

    start = time.time()

    # Calculate all indicators
    indicators = IndicatorCalculator.calculate_all_indicators(sample_ohlcv_data)

    duration = time.time() - start

    # Should complete in under 100ms
    assert duration < 0.1

    # All indicators should be calculated
    assert all(indicators.values())


@pytest.mark.asyncio
async def test_concurrent_symbol_updates(mock_db_pool):
    """Test handling concurrent updates for multiple symbols"""
    service = MarketDataService(
        symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        testnet=True,
    )

    # Create sample data for each symbol
    tickers = []
    for symbol in ["BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT"]:
        ticker = Ticker(
            symbol=symbol,
            timestamp=datetime.utcnow(),
            bid=Decimal("1000"),
            ask=Decimal("1001"),
            last=Decimal("1000.5"),
            high_24h=Decimal("1100"),
            low_24h=Decimal("900"),
            volume_24h=Decimal("1000"),
            change_24h=Decimal("10"),
            change_24h_pct=Decimal("1"),
        )
        tickers.append(ticker)

    # Update all tickers concurrently
    await asyncio.gather(*[service._handle_ticker_update(ticker) for ticker in tickers])

    # All should be stored
    assert len(service.latest_tickers) == 3


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
