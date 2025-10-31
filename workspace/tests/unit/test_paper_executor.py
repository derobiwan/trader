"""
Unit Tests for Paper Trading Executor

Tests simulated order execution, virtual balance management, paper trading P&L tracking,
and realistic simulation features (slippage, fees, partial fills).

Coverage target: >60%
Test patterns: Mock exchange API, verify paper trading isolation, test simulation accuracy
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch

from workspace.features.paper_trading.paper_executor import PaperTradingExecutor
from workspace.features.trade_executor.models import (
    OrderType,
    OrderSide,
    OrderStatus,
)


class TestPaperTradingExecutor:
    """Test suite for PaperTradingExecutor"""

    @pytest.fixture
    def mock_exchange(self):
        """Mock exchange for testing"""
        exchange = AsyncMock()
        exchange.load_markets = AsyncMock()
        exchange.markets = {"BTC/USDT:USDT": {}, "ETH/USDT:USDT": {}}
        exchange.fetch_ticker = AsyncMock(
            return_value={"last": 50000, "bid": 49999, "ask": 50001}
        )
        return exchange

    @pytest.fixture
    def paper_executor(self, mock_exchange):
        """Create paper executor instance"""
        with patch(
            "workspace.features.paper_trading.paper_executor.TradeExecutor.__init__",
            return_value=None,
        ):
            executor = PaperTradingExecutor(
                initial_balance=Decimal("10000"),
                enable_slippage=True,
                enable_partial_fills=True,
                maker_fee_pct=Decimal("0.001"),
                taker_fee_pct=Decimal("0.001"),
            )
            executor.exchange = mock_exchange
            executor.metrics_service = Mock()
            executor.metrics_service.record_order_execution = Mock()
            return executor

    @pytest.fixture
    def paper_executor_no_slippage(self, mock_exchange):
        """Create paper executor with slippage disabled"""
        with patch(
            "workspace.features.paper_trading.paper_executor.TradeExecutor.__init__",
            return_value=None,
        ):
            executor = PaperTradingExecutor(
                initial_balance=Decimal("10000"),
                enable_slippage=False,
                enable_partial_fills=False,
            )
            executor.exchange = mock_exchange
            executor.metrics_service = Mock()
            executor.metrics_service.record_order_execution = Mock()
            return executor

    def test_initialization(self, paper_executor):
        """Test paper executor initializes correctly"""
        assert paper_executor.initial_balance == Decimal("10000")
        assert paper_executor.virtual_portfolio.balance == Decimal("10000")
        assert paper_executor.enable_slippage is True
        assert paper_executor.enable_partial_fills is True
        assert paper_executor.maker_fee_pct == Decimal("0.001")
        assert paper_executor.taker_fee_pct == Decimal("0.001")
        assert len(paper_executor.simulated_trades) == 0

    @pytest.mark.asyncio
    async def test_initialize_exchange(self, paper_executor, mock_exchange):
        """Test exchange initialization in read-only mode"""
        await paper_executor.initialize()

        mock_exchange.load_markets.assert_called_once()

    @pytest.mark.asyncio
    async def test_simulate_latency(self, paper_executor):
        """Test latency simulation"""
        import time

        start = time.time()
        await paper_executor._simulate_latency()
        duration = time.time() - start

        # Should be between 50ms and 150ms
        assert 0.05 <= duration <= 0.16  # Add small buffer for execution time

    def test_calculate_slippage_buy(self, paper_executor):
        """Test slippage calculation for buy orders"""
        price = Decimal("50000")
        slipped_price = paper_executor._calculate_slippage(OrderSide.BUY, price)

        # Buy should have higher price (positive slippage)
        assert slipped_price >= price
        # Slippage should be 0-0.2%
        assert slipped_price <= price * Decimal("1.002")

    def test_calculate_slippage_sell(self, paper_executor):
        """Test slippage calculation for sell orders"""
        price = Decimal("50000")
        slipped_price = paper_executor._calculate_slippage(OrderSide.SELL, price)

        # Sell should have lower price (negative slippage)
        assert slipped_price <= price
        # Slippage should be 0-0.2%
        assert slipped_price >= price * Decimal("0.998")

    def test_calculate_slippage_disabled(self, paper_executor_no_slippage):
        """Test slippage when disabled"""
        price = Decimal("50000")

        buy_price = paper_executor_no_slippage._calculate_slippage(OrderSide.BUY, price)
        sell_price = paper_executor_no_slippage._calculate_slippage(
            OrderSide.SELL, price
        )

        # No slippage when disabled
        assert buy_price == price
        assert sell_price == price

    def test_calculate_partial_fill(self, paper_executor):
        """Test partial fill calculation"""
        quantity = Decimal("1.0")
        filled = paper_executor._calculate_partial_fill(quantity)

        # Should be 95-100% of quantity
        assert filled >= quantity * Decimal("0.95")
        assert filled <= quantity

    def test_calculate_partial_fill_disabled(self, paper_executor_no_slippage):
        """Test partial fill when disabled"""
        quantity = Decimal("1.0")
        filled = paper_executor_no_slippage._calculate_partial_fill(quantity)

        # Should be exactly the requested quantity
        assert filled == quantity

    def test_calculate_fees_market_order(self, paper_executor):
        """Test fee calculation for market orders"""
        quantity = Decimal("1.0")
        price = Decimal("50000")

        fees = paper_executor._calculate_fees(quantity, price, OrderType.MARKET)

        # Should use taker fee (0.1%)
        expected_fees = quantity * price * Decimal("0.001")
        assert fees == expected_fees

    def test_calculate_fees_limit_order(self, paper_executor):
        """Test fee calculation for limit orders"""
        quantity = Decimal("1.0")
        price = Decimal("50000")

        fees = paper_executor._calculate_fees(quantity, price, OrderType.LIMIT)

        # Should use maker fee (0.1%)
        expected_fees = quantity * price * Decimal("0.001")
        assert fees == expected_fees

    @pytest.mark.asyncio
    async def test_create_market_order_buy(self, paper_executor, mock_exchange):
        """Test creating a buy market order"""
        # Mock ticker price
        mock_exchange.fetch_ticker.return_value = {"last": 50000}

        order = await paper_executor.create_market_order(
            symbol="BTC/USDT:USDT",
            side=OrderSide.BUY,
            quantity=Decimal("0.1"),
            reduce_only=False,
        )

        # Verify order
        assert order.symbol == "BTC/USDT:USDT"
        assert order.type == OrderType.MARKET
        assert order.side == OrderSide.BUY
        assert order.quantity == Decimal("0.1")
        assert order.status == OrderStatus.FILLED
        assert order.filled_quantity > 0
        assert order.average_fill_price > 0
        assert order.fees_paid > 0

        # Verify position opened
        assert "BTC/USDT:USDT" in paper_executor.virtual_portfolio.positions
        position = paper_executor.virtual_portfolio.positions["BTC/USDT:USDT"]
        assert position["side"] == "long"
        assert position["quantity"] > 0

        # Verify balance decreased
        assert paper_executor.virtual_portfolio.balance < Decimal("10000")

        # Verify trade recorded
        assert len(paper_executor.simulated_trades) == 1

    @pytest.mark.asyncio
    async def test_create_market_order_sell(self, paper_executor, mock_exchange):
        """Test creating a sell market order (close position)"""
        # First open a position
        mock_exchange.fetch_ticker.return_value = {"last": 50000}
        await paper_executor.create_market_order(
            symbol="BTC/USDT:USDT",
            side=OrderSide.BUY,
            quantity=Decimal("0.1"),
            reduce_only=False,
        )

        # Now close it
        mock_exchange.fetch_ticker.return_value = {"last": 51000}
        close_order = await paper_executor.create_market_order(
            symbol="BTC/USDT:USDT",
            side=OrderSide.SELL,
            quantity=Decimal("0.1"),
            reduce_only=True,
            position_id="test_pos",
        )

        # Verify close order
        assert close_order.side == OrderSide.SELL
        assert close_order.status == OrderStatus.FILLED

        # Verify position closed
        assert "BTC/USDT:USDT" not in paper_executor.virtual_portfolio.positions

        # Verify trades recorded
        assert len(paper_executor.simulated_trades) == 2

    @pytest.mark.asyncio
    async def test_create_market_order_insufficient_balance(
        self, paper_executor, mock_exchange
    ):
        """Test market order fails with insufficient balance"""
        # Try to buy more than balance allows
        mock_exchange.fetch_ticker.return_value = {"last": 50000}

        with pytest.raises(ValueError) as exc_info:
            await paper_executor.create_market_order(
                symbol="BTC/USDT:USDT",
                side=OrderSide.BUY,
                quantity=Decimal("10.0"),  # Cost: 500,000 > balance
                reduce_only=False,
            )

        assert "Insufficient balance" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_stop_loss_order(self, paper_executor):
        """Test creating a stop-loss order"""
        order = await paper_executor.create_stop_loss_order(
            symbol="BTC/USDT:USDT",
            side=OrderSide.SELL,
            quantity=Decimal("0.1"),
            stop_price=Decimal("49000"),
            position_id="test_pos",
        )

        # Verify stop-loss order
        assert order.symbol == "BTC/USDT:USDT"
        assert order.type == OrderType.STOP_MARKET
        assert order.side == OrderSide.SELL
        assert order.stop_price == Decimal("49000")
        assert order.status == OrderStatus.OPEN  # Not triggered yet
        assert order.position_id == "test_pos"

    @pytest.mark.asyncio
    async def test_get_account_balance(self, paper_executor):
        """Test getting virtual account balance"""
        balance = await paper_executor.get_account_balance()

        assert balance == Decimal("10000")

        # After a trade, balance should change
        paper_executor.virtual_portfolio.balance = Decimal("9500")
        new_balance = await paper_executor.get_account_balance()
        assert new_balance == Decimal("9500")

    @pytest.mark.asyncio
    async def test_get_position(self, paper_executor, mock_exchange):
        """Test getting virtual position"""
        # No position initially
        position = await paper_executor.get_position("BTC/USDT:USDT")
        assert position is None

        # Open position
        mock_exchange.fetch_ticker.return_value = {"last": 50000}
        await paper_executor.create_market_order(
            symbol="BTC/USDT:USDT",
            side=OrderSide.BUY,
            quantity=Decimal("0.1"),
            reduce_only=False,
        )

        # Get position
        position = await paper_executor.get_position("BTC/USDT:USDT")
        assert position is not None
        assert position["symbol"] == "BTC/USDT:USDT"
        assert position["side"] == "long"

    def test_get_performance_report(self, paper_executor):
        """Test getting performance report"""
        report = paper_executor.get_performance_report()

        # Verify report structure
        assert "portfolio" in report
        assert "profitability" in report
        assert "summary" in report

        # Verify portfolio info
        assert report["portfolio"]["initial_balance"] == Decimal("10000.0")
        assert report["portfolio"]["current_balance"] == Decimal("10000.0")
        assert report["portfolio"]["open_positions"] == 0

    @pytest.mark.asyncio
    async def test_get_performance_report_with_trades(
        self, paper_executor, mock_exchange
    ):
        """Test performance report after trades"""
        # Execute some trades
        mock_exchange.fetch_ticker.return_value = {"last": 50000}
        await paper_executor.create_market_order(
            symbol="BTC/USDT:USDT",
            side=OrderSide.BUY,
            quantity=Decimal("0.1"),
            reduce_only=False,
        )

        mock_exchange.fetch_ticker.return_value = {"last": 51000}
        await paper_executor.create_market_order(
            symbol="BTC/USDT:USDT",
            side=OrderSide.SELL,
            quantity=Decimal("0.1"),
            reduce_only=True,
        )

        report = paper_executor.get_performance_report()

        # Should have trade data
        assert report["summary"]["total_trades"] >= 1
        assert "total_pnl" in report["profitability"]

    @pytest.mark.asyncio
    async def test_reset(self, paper_executor, mock_exchange):
        """Test resetting paper trading state"""
        # Execute a trade
        mock_exchange.fetch_ticker.return_value = {"last": 50000}
        await paper_executor.create_market_order(
            symbol="BTC/USDT:USDT",
            side=OrderSide.BUY,
            quantity=Decimal("0.1"),
            reduce_only=False,
        )

        # Verify state changed
        assert paper_executor.virtual_portfolio.balance < Decimal("10000")
        assert len(paper_executor.simulated_trades) > 0

        # Reset
        await paper_executor.reset()

        # Verify state reset
        assert paper_executor.virtual_portfolio.balance == Decimal("10000")
        assert len(paper_executor.simulated_trades) == 0
        assert len(paper_executor.virtual_portfolio.positions) == 0

    @pytest.mark.asyncio
    async def test_reset_with_new_balance(self, paper_executor):
        """Test resetting with new initial balance"""
        await paper_executor.reset(initial_balance=Decimal("20000"))

        assert paper_executor.initial_balance == Decimal("20000")
        assert paper_executor.virtual_portfolio.balance == Decimal("20000")

    @pytest.mark.asyncio
    async def test_order_metadata(self, paper_executor, mock_exchange):
        """Test that orders include paper trading metadata"""
        mock_exchange.fetch_ticker.return_value = {"last": 50000}

        order = await paper_executor.create_market_order(
            symbol="BTC/USDT:USDT",
            side=OrderSide.BUY,
            quantity=Decimal("0.1"),
            reduce_only=False,
        )

        # Verify metadata
        assert order.metadata["paper_trading"] is True
        assert "slippage_enabled" in order.metadata
        assert "partial_fills_enabled" in order.metadata

    @pytest.mark.asyncio
    async def test_metrics_recording(self, paper_executor, mock_exchange):
        """Test that execution metrics are recorded"""
        mock_exchange.fetch_ticker.return_value = {"last": 50000}

        await paper_executor.create_market_order(
            symbol="BTC/USDT:USDT",
            side=OrderSide.BUY,
            quantity=Decimal("0.1"),
            reduce_only=False,
        )

        # Verify metrics were recorded
        paper_executor.metrics_service.record_order_execution.assert_called()
        call_args = paper_executor.metrics_service.record_order_execution.call_args
        assert call_args[1]["symbol"] == "BTC/USDT:USDT"
        assert call_args[1]["success"] is True

    @pytest.mark.asyncio
    async def test_order_execution_error_metrics(self, paper_executor, mock_exchange):
        """Test that failed orders record error metrics"""
        # Force an error
        mock_exchange.fetch_ticker.side_effect = Exception("Exchange error")

        with pytest.raises(Exception):
            await paper_executor.create_market_order(
                symbol="BTC/USDT:USDT",
                side=OrderSide.BUY,
                quantity=Decimal("0.1"),
                reduce_only=False,
            )

        # Verify error metrics were recorded
        call_args = paper_executor.metrics_service.record_order_execution.call_args
        assert call_args[1]["success"] is False

    @pytest.mark.asyncio
    async def test_performance_tracker_integration(self, paper_executor, mock_exchange):
        """Test integration with performance tracker"""
        # Open and close a position
        mock_exchange.fetch_ticker.return_value = {"last": 50000}
        await paper_executor.create_market_order(
            symbol="BTC/USDT:USDT",
            side=OrderSide.BUY,
            quantity=Decimal("0.1"),
            reduce_only=False,
        )

        mock_exchange.fetch_ticker.return_value = {"last": 51000}
        await paper_executor.create_market_order(
            symbol="BTC/USDT:USDT",
            side=OrderSide.SELL,
            quantity=Decimal("0.1"),
            reduce_only=True,
        )

        # Verify performance tracker has data
        assert len(paper_executor.performance_tracker.trades) > 0

    @pytest.mark.asyncio
    async def test_realistic_slippage_range(self, paper_executor):
        """Test that slippage stays within realistic bounds"""
        price = Decimal("50000")

        # Test multiple times to ensure randomness stays in bounds
        for _ in range(100):
            buy_slipped = paper_executor._calculate_slippage(OrderSide.BUY, price)
            sell_slipped = paper_executor._calculate_slippage(OrderSide.SELL, price)

            # Buy slippage: 0-0.2% higher
            assert buy_slipped >= price
            assert buy_slipped <= price * Decimal("1.002")

            # Sell slippage: 0-0.2% lower
            assert sell_slipped <= price
            assert sell_slipped >= price * Decimal("0.998")

    @pytest.mark.asyncio
    async def test_realistic_partial_fill_range(self, paper_executor):
        """Test that partial fills stay within realistic bounds"""
        quantity = Decimal("1.0")

        # Test multiple times to ensure randomness stays in bounds
        for _ in range(100):
            filled = paper_executor._calculate_partial_fill(quantity)

            # Partial fill: 95-100%
            assert filled >= quantity * Decimal("0.95")
            assert filled <= quantity

    @pytest.mark.asyncio
    async def test_short_position_simulation(self, paper_executor, mock_exchange):
        """Test simulating short positions"""
        # Open short position
        mock_exchange.fetch_ticker.return_value = {"last": 50000}
        await paper_executor.create_market_order(
            symbol="BTC/USDT:USDT",
            side=OrderSide.SELL,
            quantity=Decimal("0.1"),
            reduce_only=False,
        )

        # Verify short position opened
        position = await paper_executor.get_position("BTC/USDT:USDT")
        assert position is not None
        assert position["side"] == "short"

        # Close short position (price went down = profit)
        mock_exchange.fetch_ticker.return_value = {"last": 49000}
        await paper_executor.create_market_order(
            symbol="BTC/USDT:USDT",
            side=OrderSide.BUY,
            quantity=Decimal("0.1"),
            reduce_only=True,
        )

        # Verify position closed
        position = await paper_executor.get_position("BTC/USDT:USDT")
        assert position is None

    @pytest.mark.asyncio
    async def test_multiple_open_positions(self, paper_executor, mock_exchange):
        """Test managing multiple open positions"""
        # Open BTC position
        mock_exchange.fetch_ticker.return_value = {"last": 50000}
        await paper_executor.create_market_order(
            symbol="BTC/USDT:USDT",
            side=OrderSide.BUY,
            quantity=Decimal("0.1"),
            reduce_only=False,
        )

        # Open ETH position
        mock_exchange.fetch_ticker.return_value = {"last": 3000}
        await paper_executor.create_market_order(
            symbol="ETH/USDT:USDT",
            side=OrderSide.BUY,
            quantity=Decimal("1.0"),
            reduce_only=False,
        )

        # Verify both positions exist
        btc_pos = await paper_executor.get_position("BTC/USDT:USDT")
        eth_pos = await paper_executor.get_position("ETH/USDT:USDT")

        assert btc_pos is not None
        assert eth_pos is not None
        assert len(paper_executor.virtual_portfolio.positions) == 2

    @pytest.mark.asyncio
    async def test_paper_trading_never_touches_real_exchange(
        self, paper_executor, mock_exchange
    ):
        """Critical test: Verify paper trading never executes real orders"""
        # Execute paper trades
        mock_exchange.fetch_ticker.return_value = {"last": 50000}
        await paper_executor.create_market_order(
            symbol="BTC/USDT:USDT",
            side=OrderSide.BUY,
            quantity=Decimal("0.1"),
            reduce_only=False,
        )

        # Verify exchange was ONLY called for market data (ticker)
        # NEVER for order creation
        mock_exchange.fetch_ticker.assert_called()

        # Ensure no order creation methods were called
        assert (
            not hasattr(mock_exchange, "create_order")
            or not mock_exchange.create_order.called
        )
        assert (
            not hasattr(mock_exchange, "create_market_order")
            or not mock_exchange.create_market_order.called
        )
