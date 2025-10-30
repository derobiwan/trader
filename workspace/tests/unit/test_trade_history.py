"""
Trade History Service Tests

Comprehensive test suite for trade history logging and statistics.

Author: Validation Engineer
Date: 2025-10-30
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from workspace.features.trade_history.models import TradeStatus, TradeType
from workspace.features.trade_history.trade_history_service import TradeHistoryService

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def trade_history_service():
    """Create trade history service instance"""
    return TradeHistoryService(use_database=False)


@pytest.fixture
def sample_trade_data():
    """Sample trade data"""
    return {
        "trade_type": TradeType.ENTRY_LONG,
        "symbol": "BTCUSDT",
        "order_id": "order_123",
        "side": "buy",
        "quantity": Decimal("0.5"),
        "price": Decimal("50000"),
        "fees": Decimal("25"),
    }


# ============================================================================
# Initialization Tests
# ============================================================================


def test_trade_history_initialization():
    """Test trade history service initializes correctly"""
    service = TradeHistoryService(use_database=False)

    assert service.use_database is False
    assert len(service._trades) == 0
    assert len(service._trades_by_date) == 0
    assert len(service._trades_by_symbol) == 0


def test_trade_history_with_database_mode():
    """Test trade history service in database mode"""
    service = TradeHistoryService(use_database=True)

    assert service.use_database is True


# ============================================================================
# Trade Logging Tests
# ============================================================================


@pytest.mark.asyncio
async def test_log_entry_trade(trade_history_service, sample_trade_data):
    """Test logging an entry trade"""
    trade = await trade_history_service.log_trade(**sample_trade_data)

    assert trade.id is not None
    assert trade.trade_type == TradeType.ENTRY_LONG
    assert trade.symbol == "BTCUSDT"
    assert trade.order_id == "order_123"
    assert trade.side == "buy"
    assert trade.quantity == Decimal("0.5")
    assert trade.entry_price == Decimal("50000")
    assert trade.fees == Decimal("25")
    assert trade.status == TradeStatus.FILLED


@pytest.mark.asyncio
async def test_log_exit_trade(trade_history_service):
    """Test logging an exit trade"""
    trade = await trade_history_service.log_trade(
        trade_type=TradeType.EXIT_LONG,
        symbol="ETHUSDT",
        order_id="order_456",
        side="sell",
        quantity=Decimal("1.0"),
        price=Decimal("3000"),
        fees=Decimal("15"),
        realized_pnl=Decimal("500"),
    )

    assert trade.trade_type == TradeType.EXIT_LONG
    assert trade.exit_price == Decimal("3000")
    assert trade.realized_pnl == Decimal("500")


@pytest.mark.asyncio
async def test_log_stop_loss_trade(trade_history_service):
    """Test logging a stop-loss trade"""
    trade = await trade_history_service.log_trade(
        trade_type=TradeType.STOP_LOSS,
        symbol="BTCUSDT",
        order_id="order_789",
        side="sell",
        quantity=Decimal("0.2"),
        price=Decimal("49000"),
        fees=Decimal("10"),
        realized_pnl=Decimal("-200"),
    )

    assert trade.trade_type == TradeType.STOP_LOSS
    assert trade.realized_pnl == Decimal("-200")


@pytest.mark.asyncio
async def test_log_take_profit_trade(trade_history_service):
    """Test logging a take-profit trade"""
    trade = await trade_history_service.log_trade(
        trade_type=TradeType.TAKE_PROFIT,
        symbol="ETHUSDT",
        order_id="order_101",
        side="sell",
        quantity=Decimal("0.5"),
        price=Decimal("3500"),
        fees=Decimal("12"),
        realized_pnl=Decimal("1000"),
    )

    assert trade.trade_type == TradeType.TAKE_PROFIT
    assert trade.realized_pnl == Decimal("1000")


@pytest.mark.asyncio
async def test_log_trade_with_signal_info(trade_history_service):
    """Test logging trade with signal information"""
    trade = await trade_history_service.log_trade(
        trade_type=TradeType.ENTRY_LONG,
        symbol="BTCUSDT",
        order_id="order_202",
        side="buy",
        quantity=Decimal("0.1"),
        price=Decimal("50000"),
        signal_confidence=Decimal("0.85"),
        signal_reasoning="Strong bullish setup",
        execution_latency_ms=Decimal("150"),
    )

    assert trade.signal_confidence == Decimal("0.85")
    assert trade.signal_reasoning == "Strong bullish setup"
    assert trade.execution_latency_ms == Decimal("150")


@pytest.mark.asyncio
async def test_log_trade_with_metadata(trade_history_service):
    """Test logging trade with custom metadata"""
    metadata = {
        "model_used": "gpt-4",
        "risk_level": "medium",
        "strategy": "mean_reversion",
    }

    trade = await trade_history_service.log_trade(
        trade_type=TradeType.ENTRY_LONG,
        symbol="BTCUSDT",
        order_id="order_303",
        side="buy",
        quantity=Decimal("0.1"),
        price=Decimal("50000"),
        metadata=metadata,
    )

    assert trade.metadata == metadata


# ============================================================================
# Trade Retrieval Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_trade_by_id(trade_history_service):
    """Test retrieving trade by ID"""
    # Log a trade
    logged_trade = await trade_history_service.log_trade(
        trade_type=TradeType.ENTRY_LONG,
        symbol="BTCUSDT",
        order_id="order_400",
        side="buy",
        quantity=Decimal("0.1"),
        price=Decimal("50000"),
    )

    # Retrieve by ID
    retrieved_trade = await trade_history_service.get_trade(logged_trade.id)

    assert retrieved_trade is not None
    assert retrieved_trade.id == logged_trade.id
    assert retrieved_trade.symbol == "BTCUSDT"


@pytest.mark.asyncio
async def test_get_nonexistent_trade(trade_history_service):
    """Test retrieving nonexistent trade returns None"""
    result = await trade_history_service.get_trade("nonexistent_id")
    assert result is None


# ============================================================================
# Trade Query Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_trades_all(trade_history_service):
    """Test retrieving all trades"""
    # Log multiple trades
    for i in range(5):
        await trade_history_service.log_trade(
            trade_type=TradeType.ENTRY_LONG,
            symbol="BTCUSDT",
            order_id=f"order_{i}",
            side="buy",
            quantity=Decimal("0.1"),
            price=Decimal("50000"),
        )

    trades = await trade_history_service.get_trades()

    assert len(trades) == 5


@pytest.mark.asyncio
async def test_get_trades_by_symbol(trade_history_service):
    """Test querying trades by symbol"""
    # Log trades for different symbols
    await trade_history_service.log_trade(
        trade_type=TradeType.ENTRY_LONG,
        symbol="BTCUSDT",
        order_id="order_501",
        side="buy",
        quantity=Decimal("0.1"),
        price=Decimal("50000"),
    )

    await trade_history_service.log_trade(
        trade_type=TradeType.ENTRY_LONG,
        symbol="ETHUSDT",
        order_id="order_502",
        side="buy",
        quantity=Decimal("1.0"),
        price=Decimal("3000"),
    )

    btc_trades = await trade_history_service.get_trades(symbol="BTCUSDT")
    eth_trades = await trade_history_service.get_trades(symbol="ETHUSDT")

    assert len(btc_trades) == 1
    assert btc_trades[0].symbol == "BTCUSDT"
    assert len(eth_trades) == 1
    assert eth_trades[0].symbol == "ETHUSDT"


@pytest.mark.asyncio
async def test_get_trades_by_date_range(trade_history_service):
    """Test querying trades by date range"""
    now = datetime.utcnow()

    # Log trade
    await trade_history_service.log_trade(
        trade_type=TradeType.ENTRY_LONG,
        symbol="BTCUSDT",
        order_id="order_601",
        side="buy",
        quantity=Decimal("0.1"),
        price=Decimal("50000"),
    )

    # Query with date range
    start = now - timedelta(hours=1)
    end = now + timedelta(hours=1)

    trades = await trade_history_service.get_trades(start_date=start, end_date=end)

    assert len(trades) == 1


@pytest.mark.asyncio
async def test_get_trades_by_type(trade_history_service):
    """Test querying trades by type"""
    # Log different trade types
    await trade_history_service.log_trade(
        trade_type=TradeType.ENTRY_LONG,
        symbol="BTCUSDT",
        order_id="order_701",
        side="buy",
        quantity=Decimal("0.1"),
        price=Decimal("50000"),
    )

    await trade_history_service.log_trade(
        trade_type=TradeType.EXIT_LONG,
        symbol="BTCUSDT",
        order_id="order_702",
        side="sell",
        quantity=Decimal("0.1"),
        price=Decimal("52000"),
    )

    entry_trades = await trade_history_service.get_trades(
        trade_type=TradeType.ENTRY_LONG
    )
    exit_trades = await trade_history_service.get_trades(trade_type=TradeType.EXIT_LONG)

    assert len(entry_trades) == 1
    assert len(exit_trades) == 1


@pytest.mark.asyncio
async def test_get_trades_with_limit(trade_history_service):
    """Test limiting query results"""
    # Log multiple trades
    for i in range(10):
        await trade_history_service.log_trade(
            trade_type=TradeType.ENTRY_LONG,
            symbol="BTCUSDT",
            order_id=f"order_{i}",
            side="buy",
            quantity=Decimal("0.1"),
            price=Decimal("50000"),
        )

    # Query with limit
    trades = await trade_history_service.get_trades(limit=5)

    assert len(trades) == 5


# ============================================================================
# Daily Trade Query Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_daily_trades(trade_history_service):
    """Test retrieving trades for a specific day"""
    today = datetime.utcnow()

    await trade_history_service.log_trade(
        trade_type=TradeType.ENTRY_LONG,
        symbol="BTCUSDT",
        order_id="order_801",
        side="buy",
        quantity=Decimal("0.1"),
        price=Decimal("50000"),
    )

    daily_trades = await trade_history_service.get_daily_trades(today)

    assert len(daily_trades) >= 1


# ============================================================================
# Statistics Calculation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_calculate_statistics_empty_period(trade_history_service):
    """Test calculating statistics with no trades"""
    start = datetime.utcnow() - timedelta(days=1)
    end = datetime.utcnow()

    stats = await trade_history_service.calculate_statistics(start, end)

    assert stats.total_trades == 0
    assert stats.win_rate == Decimal("0")
    assert stats.total_pnl == Decimal("0")


@pytest.mark.asyncio
async def test_calculate_statistics_with_trades(trade_history_service):
    """Test calculating statistics with trades"""
    # Log some exit trades with P&L
    await trade_history_service.log_trade(
        trade_type=TradeType.EXIT_LONG,
        symbol="BTCUSDT",
        order_id="order_901",
        side="sell",
        quantity=Decimal("0.1"),
        price=Decimal("52000"),
        realized_pnl=Decimal("200"),
    )

    await trade_history_service.log_trade(
        trade_type=TradeType.EXIT_LONG,
        symbol="BTCUSDT",
        order_id="order_902",
        side="sell",
        quantity=Decimal("0.1"),
        price=Decimal("48000"),
        realized_pnl=Decimal("-200"),
    )

    start = datetime.utcnow() - timedelta(hours=1)
    end = datetime.utcnow() + timedelta(hours=1)

    stats = await trade_history_service.calculate_statistics(start, end)

    assert stats.total_trades == 2
    assert stats.winning_trades == 1
    assert stats.losing_trades == 1
    assert stats.win_rate == Decimal("50")
    assert stats.total_pnl == Decimal("0")  # 200 - 200


@pytest.mark.asyncio
async def test_calculate_statistics_winning_trades(trade_history_service):
    """Test statistics calculation for winning trades"""
    # Log 3 winning trades
    for i in range(3):
        await trade_history_service.log_trade(
            trade_type=TradeType.EXIT_LONG,
            symbol="BTCUSDT",
            order_id=f"order_{1000 + i}",
            side="sell",
            quantity=Decimal("0.1"),
            price=Decimal("52000"),
            realized_pnl=Decimal("200"),
        )

    start = datetime.utcnow() - timedelta(hours=1)
    end = datetime.utcnow() + timedelta(hours=1)

    stats = await trade_history_service.calculate_statistics(start, end)

    assert stats.total_trades == 3
    assert stats.winning_trades == 3
    assert stats.losing_trades == 0
    assert stats.win_rate == Decimal("100")
    assert stats.total_pnl == Decimal("600")
    assert stats.largest_win == Decimal("200")


@pytest.mark.asyncio
async def test_calculate_statistics_losing_trades(trade_history_service):
    """Test statistics calculation for losing trades"""
    # Log 2 losing trades
    for i in range(2):
        await trade_history_service.log_trade(
            trade_type=TradeType.STOP_LOSS,
            symbol="BTCUSDT",
            order_id=f"order_{1100 + i}",
            side="sell",
            quantity=Decimal("0.1"),
            price=Decimal("49000"),
            realized_pnl=Decimal("-100"),
        )

    start = datetime.utcnow() - timedelta(hours=1)
    end = datetime.utcnow() + timedelta(hours=1)

    stats = await trade_history_service.calculate_statistics(start, end)

    assert stats.total_trades == 2
    assert stats.winning_trades == 0
    assert stats.losing_trades == 2
    assert stats.win_rate == Decimal("0")
    assert stats.total_pnl == Decimal("-200")
    assert stats.largest_loss == Decimal("-100")


@pytest.mark.asyncio
async def test_calculate_statistics_profit_factor(trade_history_service):
    """Test profit factor calculation"""
    # Log winning and losing trades
    await trade_history_service.log_trade(
        trade_type=TradeType.EXIT_LONG,
        symbol="BTCUSDT",
        order_id="order_1200",
        side="sell",
        quantity=Decimal("0.1"),
        price=Decimal("52000"),
        realized_pnl=Decimal("500"),
    )

    await trade_history_service.log_trade(
        trade_type=TradeType.STOP_LOSS,
        symbol="BTCUSDT",
        order_id="order_1201",
        side="sell",
        quantity=Decimal("0.1"),
        price=Decimal("49000"),
        realized_pnl=Decimal("-200"),
    )

    start = datetime.utcnow() - timedelta(hours=1)
    end = datetime.utcnow() + timedelta(hours=1)

    stats = await trade_history_service.calculate_statistics(start, end)

    # Profit factor = 500 / 200 = 2.5
    assert stats.profit_factor == Decimal("2.5")


@pytest.mark.asyncio
async def test_calculate_statistics_by_symbol(trade_history_service):
    """Test calculating statistics for specific symbol"""
    # Log trades for different symbols
    await trade_history_service.log_trade(
        trade_type=TradeType.EXIT_LONG,
        symbol="BTCUSDT",
        order_id="order_1300",
        side="sell",
        quantity=Decimal("0.1"),
        price=Decimal("52000"),
        realized_pnl=Decimal("500"),
    )

    await trade_history_service.log_trade(
        trade_type=TradeType.EXIT_LONG,
        symbol="ETHUSDT",
        order_id="order_1301",
        side="sell",
        quantity=Decimal("1.0"),
        price=Decimal("3500"),
        realized_pnl=Decimal("1000"),
    )

    start = datetime.utcnow() - timedelta(hours=1)
    end = datetime.utcnow() + timedelta(hours=1)

    btc_stats = await trade_history_service.calculate_statistics(
        start, end, symbol="BTCUSDT"
    )

    assert btc_stats.total_trades == 1
    assert btc_stats.total_pnl == Decimal("500")


# ============================================================================
# Daily Report Tests
# ============================================================================


@pytest.mark.asyncio
async def test_generate_daily_report(trade_history_service):
    """Test generating daily trade report"""
    today = datetime.utcnow()

    # Log some trades
    for i in range(3):
        await trade_history_service.log_trade(
            trade_type=TradeType.ENTRY_LONG,
            symbol="BTCUSDT",
            order_id=f"order_{1400 + i}",
            side="buy",
            quantity=Decimal("0.1"),
            price=Decimal("50000"),
        )

    report = await trade_history_service.generate_daily_report(today)

    assert report.date.date() == today.date()
    assert report.statistics is not None
    assert len(report.trades_by_hour) >= 0
    assert len(report.trades_by_symbol) >= 0


@pytest.mark.asyncio
async def test_daily_report_trades_by_symbol(trade_history_service):
    """Test daily report groups trades by symbol"""
    today = datetime.utcnow()

    # Log trades for different symbols
    await trade_history_service.log_trade(
        trade_type=TradeType.ENTRY_LONG,
        symbol="BTCUSDT",
        order_id="order_1500",
        side="buy",
        quantity=Decimal("0.1"),
        price=Decimal("50000"),
    )

    await trade_history_service.log_trade(
        trade_type=TradeType.ENTRY_LONG,
        symbol="ETHUSDT",
        order_id="order_1501",
        side="buy",
        quantity=Decimal("1.0"),
        price=Decimal("3000"),
    )

    report = await trade_history_service.generate_daily_report(today)

    assert "BTCUSDT" in report.trades_by_symbol
    assert "ETHUSDT" in report.trades_by_symbol


# ============================================================================
# Service Statistics Tests
# ============================================================================


def test_get_service_stats(trade_history_service):
    """Test getting service statistics"""
    stats = trade_history_service.get_stats()

    assert "total_trades_logged" in stats
    assert "unique_symbols" in stats
    assert "trading_days" in stats
    assert "storage_mode" in stats


@pytest.mark.asyncio
async def test_service_stats_after_logging(trade_history_service):
    """Test service stats update after logging trades"""
    # Log trades
    for i in range(5):
        await trade_history_service.log_trade(
            trade_type=TradeType.ENTRY_LONG,
            symbol="BTCUSDT" if i < 3 else "ETHUSDT",
            order_id=f"order_{1600 + i}",
            side="buy",
            quantity=Decimal("0.1"),
            price=Decimal("50000"),
        )

    stats = trade_history_service.get_stats()

    assert stats["total_trades_logged"] == 5
    assert stats["unique_symbols"] == 2
    assert stats["trading_days"] >= 1


# ============================================================================
# Trade Indexing Tests
# ============================================================================


@pytest.mark.asyncio
async def test_trades_indexed_by_date(trade_history_service):
    """Test trades are properly indexed by date"""
    today = datetime.utcnow()

    await trade_history_service.log_trade(
        trade_type=TradeType.ENTRY_LONG,
        symbol="BTCUSDT",
        order_id="order_1700",
        side="buy",
        quantity=Decimal("0.1"),
        price=Decimal("50000"),
    )

    date_key = today.strftime("%Y-%m-%d")
    assert date_key in trade_history_service._trades_by_date
    assert len(trade_history_service._trades_by_date[date_key]) == 1


@pytest.mark.asyncio
async def test_trades_indexed_by_symbol(trade_history_service):
    """Test trades are properly indexed by symbol"""
    await trade_history_service.log_trade(
        trade_type=TradeType.ENTRY_LONG,
        symbol="BTCUSDT",
        order_id="order_1800",
        side="buy",
        quantity=Decimal("0.1"),
        price=Decimal("50000"),
    )

    assert "BTCUSDT" in trade_history_service._trades_by_symbol
    assert len(trade_history_service._trades_by_symbol["BTCUSDT"]) == 1


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.asyncio
async def test_log_trade_with_zero_quantity():
    """Test logging trade with zero quantity"""
    service = TradeHistoryService()

    # Should still work (validation elsewhere)
    trade = await service.log_trade(
        trade_type=TradeType.ENTRY_LONG,
        symbol="BTCUSDT",
        order_id="order_1900",
        side="buy",
        quantity=Decimal("0"),
        price=Decimal("50000"),
    )

    assert trade.quantity == Decimal("0")


@pytest.mark.asyncio
async def test_log_trade_with_negative_pnl():
    """Test logging trade with negative realized P&L"""
    service = TradeHistoryService()

    trade = await service.log_trade(
        trade_type=TradeType.STOP_LOSS,
        symbol="BTCUSDT",
        order_id="order_2000",
        side="sell",
        quantity=Decimal("0.1"),
        price=Decimal("49000"),
        realized_pnl=Decimal("-500"),
    )

    assert trade.realized_pnl == Decimal("-500")


# ============================================================================
# Sorting and Ordering Tests
# ============================================================================


@pytest.mark.asyncio
async def test_trades_returned_newest_first(trade_history_service):
    """Test trades are returned with newest first"""
    # Log trades with slight delay
    import asyncio

    await trade_history_service.log_trade(
        trade_type=TradeType.ENTRY_LONG,
        symbol="BTCUSDT",
        order_id="order_2100",
        side="buy",
        quantity=Decimal("0.1"),
        price=Decimal("50000"),
    )

    await asyncio.sleep(0.1)

    await trade_history_service.log_trade(
        trade_type=TradeType.ENTRY_LONG,
        symbol="BTCUSDT",
        order_id="order_2101",
        side="buy",
        quantity=Decimal("0.1"),
        price=Decimal("50100"),
    )

    trades = await trade_history_service.get_trades()

    # Should be ordered newest first
    assert trades[0].order_id == "order_2101"
    assert trades[1].order_id == "order_2100"
