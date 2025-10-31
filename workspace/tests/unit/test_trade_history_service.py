"""
Unit Tests for Trade History Service

Tests trade logging, querying, statistics calculation, and reporting.

Coverage target: >60%
Test patterns: Mock database operations, test statistical calculations
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

from workspace.features.trade_history.trade_history_service import TradeHistoryService
from workspace.features.trade_history.models import (
    TradeType,
    TradeStatus,
    TradeStatistics,
)


class TestTradeHistoryService:
    """Test suite for TradeHistoryService"""

    @pytest.fixture
    def service(self):
        """Create trade history service instance"""
        # Use in-memory mode for tests (no database)
        return TradeHistoryService(use_database=False)

    @pytest.fixture
    def sample_trades(self):
        """Sample trade data for testing"""
        return [
            {
                "trade_type": TradeType.ENTRY_LONG,
                "symbol": "BTC/USDT:USDT",
                "order_id": "order_1",
                "side": "buy",
                "quantity": Decimal("0.1"),
                "price": Decimal("50000"),
                "fees": Decimal("5.0"),
                "realized_pnl": None,
            },
            {
                "trade_type": TradeType.EXIT_LONG,
                "symbol": "BTC/USDT:USDT",
                "order_id": "order_2",
                "side": "sell",
                "quantity": Decimal("0.1"),
                "price": Decimal("51000"),
                "fees": Decimal("5.1"),
                "realized_pnl": Decimal("90.0"),  # Profit: 1000 - fees
            },
            {
                "trade_type": TradeType.ENTRY_SHORT,
                "symbol": "ETH/USDT:USDT",
                "order_id": "order_3",
                "side": "sell",
                "quantity": Decimal("1.0"),
                "price": Decimal("3000"),
                "fees": Decimal("3.0"),
                "realized_pnl": None,
            },
            {
                "trade_type": TradeType.EXIT_SHORT,
                "symbol": "ETH/USDT:USDT",
                "order_id": "order_4",
                "side": "buy",
                "quantity": Decimal("1.0"),
                "price": Decimal("2900"),
                "fees": Decimal("2.9"),
                "realized_pnl": Decimal("94.1"),  # Profit: 100 - fees
            },
            {
                "trade_type": TradeType.ENTRY_LONG,
                "symbol": "SOL/USDT:USDT",
                "order_id": "order_5",
                "side": "buy",
                "quantity": Decimal("10"),
                "price": Decimal("100"),
                "fees": Decimal("1.0"),
                "realized_pnl": None,
            },
            {
                "trade_type": TradeType.STOP_LOSS,
                "symbol": "SOL/USDT:USDT",
                "order_id": "order_6",
                "side": "sell",
                "quantity": Decimal("10"),
                "price": Decimal("95"),
                "fees": Decimal("0.95"),
                "realized_pnl": Decimal("-51.95"),  # Loss: -50 - fees
            },
        ]

    @pytest.mark.asyncio
    async def test_service_initialization(self, service):
        """Test service initializes correctly"""
        assert service.use_database is False
        assert len(service._trades) == 0
        assert len(service._trades_by_date) == 0
        assert len(service._trades_by_symbol) == 0

    @pytest.mark.asyncio
    async def test_log_trade_entry(self, service):
        """Test logging entry trade"""
        trade = await service.log_trade(
            trade_type=TradeType.ENTRY_LONG,
            symbol="BTC/USDT:USDT",
            order_id="order_123",
            side="buy",
            quantity=Decimal("0.5"),
            price=Decimal("50000"),
            fees=Decimal("25.0"),
            signal_confidence=Decimal("0.85"),
            signal_reasoning="Strong bullish momentum",
            execution_latency_ms=Decimal("120.5"),
        )

        # Verify trade object
        assert trade.id.startswith("trade_")
        assert trade.trade_type == TradeType.ENTRY_LONG
        assert trade.status == TradeStatus.FILLED
        assert trade.symbol == "BTC/USDT:USDT"
        assert trade.order_id == "order_123"
        assert trade.side == "buy"
        assert trade.quantity == Decimal("0.5")
        assert trade.entry_price == Decimal("50000")
        assert trade.exit_price is None  # Entry trade has no exit price
        assert trade.fees == Decimal("25.0")
        assert trade.realized_pnl is None  # Entry trade has no realized P&L
        assert trade.signal_confidence == Decimal("0.85")
        assert trade.signal_reasoning == "Strong bullish momentum"
        assert trade.execution_latency_ms == Decimal("120.5")

        # Verify trade is stored
        assert trade.id in service._trades
        assert service._trades[trade.id] == trade

        # Verify indexes
        date_key = trade.timestamp.strftime("%Y-%m-%d")
        assert trade.id in service._trades_by_date[date_key]
        assert trade.id in service._trades_by_symbol["BTC/USDT:USDT"]

    @pytest.mark.asyncio
    async def test_log_trade_exit_with_pnl(self, service):
        """Test logging exit trade with realized P&L"""
        trade = await service.log_trade(
            trade_type=TradeType.EXIT_LONG,
            symbol="ETH/USDT:USDT",
            order_id="order_456",
            side="sell",
            quantity=Decimal("2.0"),
            price=Decimal("3100"),
            fees=Decimal("6.2"),
            position_id="pos_123",
            realized_pnl=Decimal("193.8"),  # Example profit
        )

        # Verify exit trade has exit price
        assert trade.exit_price == Decimal("3100")
        assert trade.realized_pnl == Decimal("193.8")
        assert trade.position_id == "pos_123"

    @pytest.mark.asyncio
    async def test_log_stop_loss_trade(self, service):
        """Test logging stop-loss trade"""
        trade = await service.log_trade(
            trade_type=TradeType.STOP_LOSS,
            symbol="SOL/USDT:USDT",
            order_id="order_sl",
            side="sell",
            quantity=Decimal("50"),
            price=Decimal("95"),
            fees=Decimal("4.75"),
            position_id="pos_456",
            realized_pnl=Decimal("-254.75"),  # Loss including fees
        )

        assert trade.trade_type == TradeType.STOP_LOSS
        assert trade.exit_price == Decimal("95")  # Stop loss has exit price
        assert trade.realized_pnl == Decimal("-254.75")

    @pytest.mark.asyncio
    async def test_get_trade(self, service):
        """Test retrieving a specific trade"""
        # Log a trade
        logged_trade = await service.log_trade(
            trade_type=TradeType.ENTRY_LONG,
            symbol="BTC/USDT:USDT",
            order_id="order_get",
            side="buy",
            quantity=Decimal("0.1"),
            price=Decimal("50000"),
        )

        # Retrieve trade
        retrieved = await service.get_trade(logged_trade.id)
        assert retrieved is not None
        assert retrieved.id == logged_trade.id
        assert retrieved.symbol == "BTC/USDT:USDT"

        # Test non-existent trade
        non_existent = await service.get_trade("fake_trade_id")
        assert non_existent is None

    @pytest.mark.asyncio
    async def test_get_trades_no_filter(self, service, sample_trades):
        """Test getting all trades without filters"""
        # Log sample trades
        for trade_data in sample_trades:
            await service.log_trade(**trade_data)

        # Get all trades
        trades = await service.get_trades(limit=100)

        assert len(trades) == 6
        # Should be sorted by timestamp (newest first)
        for i in range(len(trades) - 1):
            assert trades[i].timestamp >= trades[i + 1].timestamp

    @pytest.mark.asyncio
    async def test_get_trades_filter_by_symbol(self, service, sample_trades):
        """Test filtering trades by symbol"""
        # Log sample trades
        for trade_data in sample_trades:
            await service.log_trade(**trade_data)

        # Filter by BTC
        btc_trades = await service.get_trades(symbol="BTC/USDT:USDT")
        assert len(btc_trades) == 2
        assert all(t.symbol == "BTC/USDT:USDT" for t in btc_trades)

        # Filter by ETH
        eth_trades = await service.get_trades(symbol="ETH/USDT:USDT")
        assert len(eth_trades) == 2
        assert all(t.symbol == "ETH/USDT:USDT" for t in eth_trades)

    @pytest.mark.asyncio
    async def test_get_trades_filter_by_date(self, service, sample_trades):
        """Test filtering trades by date range"""
        # Log trades
        for trade_data in sample_trades:
            await service.log_trade(**trade_data)

        # Filter by recent date range
        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)

        trades = await service.get_trades(start_date=yesterday, end_date=now)
        assert len(trades) == 6  # All trades within range

        # Filter to future (should be empty)
        future = now + timedelta(days=1)
        future_trades = await service.get_trades(start_date=future)
        assert len(future_trades) == 0

    @pytest.mark.asyncio
    async def test_get_trades_filter_by_type(self, service, sample_trades):
        """Test filtering trades by trade type"""
        # Log trades
        for trade_data in sample_trades:
            await service.log_trade(**trade_data)

        # Filter entries only
        entries = await service.get_trades(trade_type=TradeType.ENTRY_LONG)
        assert len(entries) == 2
        assert all(t.trade_type == TradeType.ENTRY_LONG for t in entries)

        # Filter exits
        exits = await service.get_trades(trade_type=TradeType.EXIT_LONG)
        assert len(exits) == 1
        assert exits[0].trade_type == TradeType.EXIT_LONG

        # Filter stop losses
        stop_losses = await service.get_trades(trade_type=TradeType.STOP_LOSS)
        assert len(stop_losses) == 1
        assert stop_losses[0].trade_type == TradeType.STOP_LOSS

    @pytest.mark.asyncio
    async def test_get_trades_limit(self, service, sample_trades):
        """Test limiting number of returned trades"""
        # Log trades
        for trade_data in sample_trades:
            await service.log_trade(**trade_data)

        # Get limited results
        trades = await service.get_trades(limit=3)
        assert len(trades) == 3

    @pytest.mark.asyncio
    async def test_get_daily_trades(self, service, sample_trades):
        """Test getting trades for a specific day"""
        # Log trades
        for trade_data in sample_trades:
            await service.log_trade(**trade_data)

        # Get today's trades
        today = datetime.utcnow()
        daily_trades = await service.get_daily_trades(today)

        assert len(daily_trades) == 6  # All trades logged today

        # Check yesterday (should be empty)
        yesterday = today - timedelta(days=1)
        yesterday_trades = await service.get_daily_trades(yesterday)
        assert len(yesterday_trades) == 0

    @pytest.mark.asyncio
    async def test_calculate_statistics_empty(self, service):
        """Test statistics calculation with no trades"""
        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)

        stats = await service.calculate_statistics(yesterday, now)

        assert stats.total_trades == 0
        assert stats.total_volume == Decimal("0")
        assert stats.win_rate == Decimal("0")
        assert stats.total_pnl == Decimal("0")

    @pytest.mark.asyncio
    async def test_calculate_statistics_with_trades(self, service, sample_trades):
        """Test statistics calculation with actual trades"""
        # Log trades
        for trade_data in sample_trades:
            await service.log_trade(**trade_data)

        # Calculate stats
        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)
        stats = await service.calculate_statistics(yesterday, now)

        # Verify counts (only exit trades count for stats)
        assert stats.total_trades == 3  # 2 exits + 1 stop loss
        assert stats.winning_trades == 2  # BTC exit + ETH exit
        assert stats.losing_trades == 1  # SOL stop loss

        # Verify win rate
        expected_win_rate = Decimal("2") / Decimal("3") * Decimal("100")
        assert stats.win_rate == expected_win_rate

        # Verify total P&L: 90 + 94.1 - 51.95 = 132.15
        assert stats.total_pnl == Decimal("132.15")

        # Verify average win: (90 + 94.1) / 2 = 92.05
        assert stats.average_win == Decimal("92.05")

        # Verify average loss: -51.95 / 1 = -51.95
        assert stats.average_loss == Decimal("-51.95")

        # Verify largest win
        assert stats.largest_win == Decimal("94.1")

        # Verify largest loss
        assert stats.largest_loss == Decimal("-51.95")

        # Verify profit factor
        gross_profit = Decimal("90") + Decimal("94.1")
        gross_loss = abs(Decimal("-51.95"))
        expected_pf = gross_profit / gross_loss
        assert stats.profit_factor == expected_pf

        # Verify total fees
        expected_fees = (
            Decimal("5.0")
            + Decimal("5.1")
            + Decimal("3.0")
            + Decimal("2.9")
            + Decimal("1.0")
            + Decimal("0.95")
        )
        assert stats.total_fees == expected_fees

    @pytest.mark.asyncio
    async def test_calculate_statistics_filter_by_symbol(self, service, sample_trades):
        """Test statistics calculation filtered by symbol"""
        # Log trades
        for trade_data in sample_trades:
            await service.log_trade(**trade_data)

        # Calculate stats for BTC only
        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)
        btc_stats = await service.calculate_statistics(
            yesterday, now, symbol="BTC/USDT:USDT"
        )

        assert btc_stats.total_trades == 1  # Only BTC exit
        assert btc_stats.winning_trades == 1
        assert btc_stats.losing_trades == 0
        assert btc_stats.total_pnl == Decimal("90.0")

    @pytest.mark.asyncio
    async def test_calculate_statistics_only_winning_trades(self, service):
        """Test statistics with only winning trades"""
        # Log only winning trades
        await service.log_trade(
            trade_type=TradeType.EXIT_LONG,
            symbol="BTC/USDT:USDT",
            order_id="win1",
            side="sell",
            quantity=Decimal("0.1"),
            price=Decimal("51000"),
            fees=Decimal("5.0"),
            realized_pnl=Decimal("95.0"),
        )
        await service.log_trade(
            trade_type=TradeType.EXIT_LONG,
            symbol="ETH/USDT:USDT",
            order_id="win2",
            side="sell",
            quantity=Decimal("1.0"),
            price=Decimal("3100"),
            fees=Decimal("3.0"),
            realized_pnl=Decimal("97.0"),
        )

        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)
        stats = await service.calculate_statistics(yesterday, now)

        assert stats.total_trades == 2
        assert stats.winning_trades == 2
        assert stats.losing_trades == 0
        assert stats.win_rate == Decimal("100")
        assert stats.total_pnl == Decimal("192.0")
        assert stats.profit_factor == Decimal("0")  # No losses

    @pytest.mark.asyncio
    async def test_calculate_statistics_only_losing_trades(self, service):
        """Test statistics with only losing trades"""
        # Log only losing trades
        await service.log_trade(
            trade_type=TradeType.STOP_LOSS,
            symbol="BTC/USDT:USDT",
            order_id="loss1",
            side="sell",
            quantity=Decimal("0.1"),
            price=Decimal("49000"),
            fees=Decimal("5.0"),
            realized_pnl=Decimal("-105.0"),
        )
        await service.log_trade(
            trade_type=TradeType.EXIT_SHORT,
            symbol="ETH/USDT:USDT",
            order_id="loss2",
            side="buy",
            quantity=Decimal("1.0"),
            price=Decimal("3100"),
            fees=Decimal("3.0"),
            realized_pnl=Decimal("-103.0"),
        )

        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)
        stats = await service.calculate_statistics(yesterday, now)

        assert stats.total_trades == 2
        assert stats.winning_trades == 0
        assert stats.losing_trades == 2
        assert stats.win_rate == Decimal("0")
        assert stats.total_pnl == Decimal("-208.0")
        assert stats.profit_factor == Decimal("0")  # No wins

    @pytest.mark.asyncio
    async def test_generate_daily_report(self, service, sample_trades):
        """Test daily report generation"""
        # Log trades
        for trade_data in sample_trades:
            await service.log_trade(**trade_data)

        # Generate report for today
        today = datetime.utcnow()
        report = await service.generate_daily_report(today)

        # Verify report structure
        assert report.date == today
        assert isinstance(report.statistics, TradeStatistics)

        # Verify trades by symbol
        assert "BTC/USDT:USDT" in report.trades_by_symbol
        assert report.trades_by_symbol["BTC/USDT:USDT"] == 2
        assert "ETH/USDT:USDT" in report.trades_by_symbol
        assert report.trades_by_symbol["ETH/USDT:USDT"] == 2
        assert "SOL/USDT:USDT" in report.trades_by_symbol
        assert report.trades_by_symbol["SOL/USDT:USDT"] == 2

        # Verify trades by hour (all logged in current hour)
        current_hour = today.hour
        assert current_hour in report.trades_by_hour
        assert report.trades_by_hour[current_hour] == 6

        # Verify daily P&L (sum of exit trades)
        assert report.daily_pnl == Decimal("132.15")

    @pytest.mark.asyncio
    async def test_get_stats(self, service, sample_trades):
        """Test getting service statistics"""
        # Initially empty
        stats = service.get_stats()
        assert stats["total_trades_logged"] == 0
        assert stats["unique_symbols"] == 0
        assert stats["trading_days"] == 0
        assert stats["storage_mode"] == "in-memory"

        # Log trades
        for trade_data in sample_trades:
            await service.log_trade(**trade_data)

        # Check stats after logging
        stats = service.get_stats()
        assert stats["total_trades_logged"] == 6
        assert stats["unique_symbols"] == 3  # BTC, ETH, SOL
        assert stats["trading_days"] == 1  # All logged today

    @pytest.mark.asyncio
    async def test_log_trade_with_metadata(self, service):
        """Test logging trade with custom metadata"""
        metadata = {
            "strategy": "momentum",
            "risk_level": "medium",
            "notes": "Strong breakout signal",
        }

        trade = await service.log_trade(
            trade_type=TradeType.ENTRY_LONG,
            symbol="BTC/USDT:USDT",
            order_id="order_meta",
            side="buy",
            quantity=Decimal("0.5"),
            price=Decimal("50000"),
            metadata=metadata,
        )

        assert trade.metadata == metadata
        assert trade.metadata["strategy"] == "momentum"

    @pytest.mark.asyncio
    async def test_log_trade_error_handling(self, service):
        """Test error handling in log_trade"""
        # Patch uuid to cause an error
        with patch("uuid.uuid4", side_effect=Exception("Storage error")):
            with pytest.raises(Exception) as exc_info:
                await service.log_trade(
                    trade_type=TradeType.ENTRY_LONG,
                    symbol="BTC/USDT:USDT",
                    order_id="error_order",
                    side="buy",
                    quantity=Decimal("0.1"),
                    price=Decimal("50000"),
                )
            assert "Storage error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_trades_error_handling(self, service):
        """Test error handling in get_trades"""
        # Patch the list.sort method to cause an error
        with patch("builtins.sorted", side_effect=Exception("Query error")):
            trades = await service.get_trades()
            # Should return empty list on error
            assert trades == []

    @pytest.mark.asyncio
    async def test_calculate_statistics_error_handling(self, service):
        """Test error handling in calculate_statistics"""
        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)

        with patch.object(service, "get_trades", side_effect=Exception("Stats error")):
            stats = await service.calculate_statistics(yesterday, now)
            # Should return empty stats on error
            assert stats.total_trades == 0
            assert stats.total_pnl == Decimal("0")

    @pytest.mark.asyncio
    async def test_volume_calculation(self, service):
        """Test total volume calculation in statistics"""
        # Log entry trades with different volumes
        await service.log_trade(
            trade_type=TradeType.ENTRY_LONG,
            symbol="BTC/USDT:USDT",
            order_id="v1",
            side="buy",
            quantity=Decimal("0.5"),
            price=Decimal("50000"),
        )
        await service.log_trade(
            trade_type=TradeType.EXIT_LONG,
            symbol="BTC/USDT:USDT",
            order_id="v2",
            side="sell",
            quantity=Decimal("0.5"),
            price=Decimal("51000"),
            realized_pnl=Decimal("500"),
        )
        await service.log_trade(
            trade_type=TradeType.ENTRY_LONG,
            symbol="ETH/USDT:USDT",
            order_id="v3",
            side="buy",
            quantity=Decimal("10"),
            price=Decimal("3000"),
        )
        await service.log_trade(
            trade_type=TradeType.EXIT_LONG,
            symbol="ETH/USDT:USDT",
            order_id="v4",
            side="sell",
            quantity=Decimal("10"),
            price=Decimal("3100"),
            realized_pnl=Decimal("1000"),
        )

        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)
        stats = await service.calculate_statistics(yesterday, now)

        # Expected volume: (0.5 * 50000) + (0.5 * 51000) + (10 * 3000) + (10 * 3100)
        expected_volume = (
            Decimal("0.5") * Decimal("50000")
            + Decimal("0.5") * Decimal("51000")
            + Decimal("10") * Decimal("3000")
            + Decimal("10") * Decimal("3100")
        )
        assert stats.total_volume == expected_volume
