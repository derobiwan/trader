"""
Integration Tests for Trade History Tracking

Tests the complete integration of trade history tracking with TradeExecutor.

Author: Trading System Implementation Team
Date: 2025-10-28
"""

import pytest
import pytest_asyncio
from decimal import Decimal
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from workspace.features.trade_executor import TradeExecutor
from workspace.features.trade_executor.models import (
    OrderSide,
)
from workspace.features.trading_loop import TradingSignal, TradingDecision
from workspace.features.trade_history import (
    TradeHistoryService,
    TradeType,
    TradeStatus,
)


@pytest.mark.asyncio
class TestTradeHistoryIntegration:
    """Integration tests for trade history tracking"""

    @pytest_asyncio.fixture
    async def trade_history_service(self):
        """Create a real TradeHistoryService instance"""
        return TradeHistoryService()

    @pytest_asyncio.fixture
    async def mock_exchange(self):
        """Create a mocked exchange"""
        exchange = AsyncMock()
        exchange.fetch_ticker = AsyncMock(
            return_value={
                "last": 50000.00,
                "bid": 49990.00,
                "ask": 50010.00,
            }
        )
        exchange.create_order = AsyncMock(
            return_value={
                "id": "order_123",
                "status": "closed",
                "filled": 0.01,
                "average": 50000.00,
                "fee": {"cost": 5.00},
            }
        )
        return exchange

    @pytest_asyncio.fixture
    async def mock_position_service(self):
        """Create a mocked position service"""
        position_service = AsyncMock()

        # Mock position for close operations
        mock_position = MagicMock()
        mock_position.id = "pos_123"
        mock_position.symbol = "BTC/USDT:USDT"
        mock_position.side = "long"
        mock_position.quantity = Decimal("0.01")
        mock_position.entry_price = Decimal("48000.00")

        position_service.get_open_positions = AsyncMock(return_value=[mock_position])
        position_service.get_position = AsyncMock(return_value=mock_position)
        position_service.close_position = AsyncMock()

        return position_service

    @pytest_asyncio.fixture
    async def executor(
        self, mock_exchange, mock_position_service, trade_history_service
    ):
        """Create TradeExecutor with real trade history service"""
        return TradeExecutor(
            api_key="test_key",
            api_secret="test_secret",
            testnet=True,
            exchange=mock_exchange,
            position_service=mock_position_service,
            trade_history_service=trade_history_service,
        )

    @pytest_asyncio.fixture
    def buy_signal(self):
        """Create a BUY signal"""
        return TradingSignal(
            symbol="BTC/USDT:USDT",
            decision=TradingDecision.BUY,
            confidence=Decimal("0.85"),
            size_pct=Decimal("0.02"),
            reasoning="Strong bullish momentum",
            stop_loss_pct=Decimal("0.02"),
        )

    @pytest_asyncio.fixture
    def close_signal(self):
        """Create a CLOSE signal"""
        return TradingSignal(
            symbol="BTC/USDT:USDT",
            decision=TradingDecision.CLOSE,
            confidence=Decimal("0.90"),
            size_pct=Decimal("0"),
            reasoning="Target reached, taking profit",
        )

    async def test_trade_logged_on_buy_signal(
        self,
        executor,
        trade_history_service,
        buy_signal,
    ):
        """Test that BUY signal execution is logged to trade history"""
        # Execute BUY signal
        result = await executor.execute_signal(
            signal=buy_signal,
            account_balance_chf=Decimal("2626.96"),
            chf_to_usd_rate=Decimal("1.10"),
        )

        # Verify signal execution succeeded
        assert result.success is True
        assert result.order is not None
        assert result.order.side == OrderSide.BUY

        # Verify trade was logged to history
        stats = trade_history_service.get_stats()
        assert stats["total_trades_logged"] == 1

        # Get the logged trade
        trades = await trade_history_service.get_trades(limit=10)
        assert len(trades) == 1

        trade = trades[0]
        assert trade.trade_type == TradeType.ENTRY_LONG
        assert trade.status == TradeStatus.FILLED
        assert trade.symbol == "BTC/USDT:USDT"
        assert trade.side == "buy"
        assert trade.quantity == Decimal("0.01")
        assert trade.entry_price == Decimal("50000.00")
        assert trade.fees == Decimal("5.00")
        assert trade.signal_confidence == Decimal("0.85")
        assert trade.signal_reasoning == "Strong bullish momentum"
        assert trade.execution_latency_ms is not None

    async def test_trade_logged_on_close_signal_with_pnl(
        self,
        executor,
        trade_history_service,
        close_signal,
    ):
        """Test that CLOSE signal execution is logged with realized P&L"""
        # Execute CLOSE signal
        result = await executor.execute_signal(
            signal=close_signal,
            account_balance_chf=Decimal("2626.96"),
            chf_to_usd_rate=Decimal("1.10"),
        )

        # Verify signal execution succeeded
        assert result.success is True
        assert result.order is not None
        assert result.order.side == OrderSide.SELL  # Closing long position

        # Verify trade was logged to history
        stats = trade_history_service.get_stats()
        assert stats["total_trades_logged"] == 1

        # Get the logged trade
        trades = await trade_history_service.get_trades(limit=10)
        assert len(trades) == 1

        trade = trades[0]
        assert trade.trade_type == TradeType.EXIT_LONG
        assert trade.status == TradeStatus.FILLED
        assert trade.symbol == "BTC/USDT:USDT"
        assert trade.side == "sell"
        assert trade.quantity == Decimal("0.01")
        assert trade.exit_price == Decimal("50000.00")
        assert trade.fees == Decimal("5.00")

        # Verify realized P&L calculation
        # Entry: 48000, Exit: 50000, Quantity: 0.01
        # P&L = (50000 - 48000) * 0.01 - 5.00 = 20.00 - 5.00 = 15.00
        assert trade.realized_pnl is not None
        assert trade.realized_pnl == Decimal("15.00")

    async def test_trade_statistics_calculation(
        self,
        executor,
        trade_history_service,
        buy_signal,
        close_signal,
    ):
        """Test that trade statistics are calculated correctly"""
        # Execute BUY signal
        await executor.execute_signal(
            signal=buy_signal,
            account_balance_chf=Decimal("2626.96"),
            chf_to_usd_rate=Decimal("1.10"),
        )

        # Execute CLOSE signal
        await executor.execute_signal(
            signal=close_signal,
            account_balance_chf=Decimal("2626.96"),
            chf_to_usd_rate=Decimal("1.10"),
        )

        # Calculate statistics
        start_date = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end_date = datetime.utcnow()

        stats = await trade_history_service.calculate_statistics(
            start_date=start_date,
            end_date=end_date,
        )

        # Verify statistics
        assert stats.total_trades == 1  # Only exit trades count
        assert stats.winning_trades == 1
        assert stats.losing_trades == 0
        assert stats.win_rate == Decimal("100")
        assert stats.total_pnl == Decimal("15.00")
        assert stats.average_win == Decimal("15.00")
        assert stats.largest_win == Decimal("15.00")

    async def test_trade_history_query_filters(
        self,
        executor,
        trade_history_service,
        buy_signal,
    ):
        """Test trade history query filters"""
        # Execute BUY signal
        await executor.execute_signal(
            signal=buy_signal,
            account_balance_chf=Decimal("2626.96"),
            chf_to_usd_rate=Decimal("1.10"),
        )

        # Query by symbol
        trades = await trade_history_service.get_trades(
            symbol="BTC/USDT:USDT",
            limit=10,
        )
        assert len(trades) == 1

        # Query by non-existent symbol
        trades = await trade_history_service.get_trades(
            symbol="ETH/USDT:USDT",
            limit=10,
        )
        assert len(trades) == 0

        # Query by trade type
        trades = await trade_history_service.get_trades(
            trade_type=TradeType.ENTRY_LONG,
            limit=10,
        )
        assert len(trades) == 1

    async def test_daily_report_generation(
        self,
        executor,
        trade_history_service,
        buy_signal,
        close_signal,
    ):
        """Test daily trade report generation"""
        # Execute trades
        await executor.execute_signal(
            signal=buy_signal,
            account_balance_chf=Decimal("2626.96"),
            chf_to_usd_rate=Decimal("1.10"),
        )

        await executor.execute_signal(
            signal=close_signal,
            account_balance_chf=Decimal("2626.96"),
            chf_to_usd_rate=Decimal("1.10"),
        )

        # Generate daily report
        today = datetime.utcnow()
        report = await trade_history_service.generate_daily_report(today)

        # Verify report
        assert report.date.date() == today.date()
        assert report.statistics.total_trades == 1
        assert report.daily_pnl == Decimal("15.00")
        assert len(report.trades_by_symbol) > 0
        assert "BTC/USDT:USDT" in report.trades_by_symbol


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
