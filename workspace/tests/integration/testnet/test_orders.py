"""
Order Execution Tests for Testnet Integration

Tests order placement, cancellation, and management on testnet.

Author: Validation Engineer
Date: 2025-10-31
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock

from ccxt.base.errors import InvalidOrder, InsufficientFunds


class TestOrderExecution:
    """Test suite for order execution"""

    @pytest.mark.asyncio
    async def test_place_market_order(self, exchange_adapter, sample_order_data):
        """Test placing a market order"""
        order_data = sample_order_data["market_order"]

        order = await exchange_adapter.place_order(
            symbol=order_data["symbol"],
            side=order_data["side"],
            order_type=order_data["type"],
            amount=order_data["amount"],
        )

        assert order["id"] is not None
        assert order["symbol"] == order_data["symbol"]
        assert order["side"] == order_data["side"]
        assert order["type"] == order_data["type"]
        assert order["amount"] == order_data["amount"]

        # Check statistics updated
        stats = exchange_adapter.get_statistics()
        assert stats["orders_placed"] > 0

    @pytest.mark.asyncio
    async def test_place_limit_order(self, exchange_adapter, sample_order_data):
        """Test placing a limit order"""
        order_data = sample_order_data["limit_order"]

        order = await exchange_adapter.place_order(
            symbol=order_data["symbol"],
            side=order_data["side"],
            order_type=order_data["type"],
            amount=order_data["amount"],
            price=order_data["price"],
        )

        assert order["id"] is not None
        assert order["symbol"] == order_data["symbol"]
        assert order["side"] == order_data["side"]
        assert order["type"] == order_data["type"]
        assert order["price"] == order_data["price"]

    @pytest.mark.asyncio
    async def test_limit_order_requires_price(self, exchange_adapter):
        """Test that limit orders require a price"""
        with pytest.raises(InvalidOrder, match="Price required"):
            await exchange_adapter.place_order(
                symbol="BTC/USDT",
                side="buy",
                order_type="limit",
                amount=0.001,
                price=None,  # Missing price
            )

    @pytest.mark.asyncio
    async def test_cancel_order(self, exchange_adapter):
        """Test cancelling an order"""
        # First place a limit order (unlikely to fill immediately)
        order = await exchange_adapter.place_order(
            symbol="BTC/USDT",
            side="buy",
            order_type="limit",
            amount=0.001,
            price=30000.0,  # Very low price to avoid fill
        )

        # Cancel it
        cancelled = await exchange_adapter.cancel_order(
            order_id=order["id"],
            symbol="BTC/USDT",
        )

        assert cancelled is True

        # Check statistics
        stats = exchange_adapter.get_statistics()
        assert stats["orders_cancelled"] > 0

    @pytest.mark.asyncio
    async def test_get_order_details(self, exchange_adapter):
        """Test fetching order details"""
        # Place an order first
        order = await exchange_adapter.place_order(
            symbol="BTC/USDT",
            side="buy",
            order_type="market",
            amount=0.001,
        )

        # Fetch details
        details = await exchange_adapter.get_order(
            order_id=order["id"],
            symbol="BTC/USDT",
        )

        assert details["id"] == order["id"]
        assert details["symbol"] == order["symbol"]
        assert "filled" in details
        assert "remaining" in details
        assert "status" in details

    @pytest.mark.asyncio
    async def test_get_open_orders(self, exchange_adapter):
        """Test fetching open orders"""
        # Place a limit order that won't fill
        await exchange_adapter.place_order(
            symbol="BTC/USDT",
            side="buy",
            order_type="limit",
            amount=0.001,
            price=20000.0,  # Very low price
        )

        # Get open orders
        open_orders = await exchange_adapter.get_open_orders()

        # Should have at least our order
        assert isinstance(open_orders, list)

        # If we have open orders, check structure
        if open_orders:
            order = open_orders[0]
            assert "id" in order
            assert "symbol" in order
            assert "side" in order
            assert "type" in order

    @pytest.mark.asyncio
    async def test_get_open_orders_by_symbol(self, exchange_adapter):
        """Test fetching open orders for specific symbol"""
        open_orders = await exchange_adapter.get_open_orders(symbol="BTC/USDT")

        assert isinstance(open_orders, list)

        # All orders should be for BTC/USDT
        for order in open_orders:
            assert order["symbol"] == "BTC/USDT"

    @pytest.mark.asyncio
    async def test_batch_order_placement(self, exchange_adapter):
        """Test placing multiple orders in sequence"""
        orders = []

        for i in range(5):
            order = await exchange_adapter.place_order(
                symbol="BTC/USDT",
                side="buy" if i % 2 == 0 else "sell",
                order_type="market",
                amount=0.001,
            )
            orders.append(order)

        assert len(orders) == 5

        # Check statistics
        stats = exchange_adapter.get_statistics()
        assert stats["orders_placed"] >= 5

    @pytest.mark.asyncio
    async def test_order_with_invalid_symbol(self, exchange_adapter):
        """Test placing order with invalid symbol"""
        # This should be handled by the exchange
        with pytest.raises(Exception):  # Could be InvalidOrder or ExchangeError
            await exchange_adapter.place_order(
                symbol="INVALID/PAIR",
                side="buy",
                order_type="market",
                amount=0.001,
            )

    @pytest.mark.asyncio
    async def test_order_statistics_tracking(self, exchange_adapter):
        """Test that order statistics are properly tracked"""
        initial_stats = exchange_adapter.get_statistics()
        initial_placed = initial_stats["orders_placed"]

        # Place a successful order
        await exchange_adapter.place_order(
            symbol="BTC/USDT",
            side="buy",
            order_type="market",
            amount=0.001,
        )

        # Check stats updated
        final_stats = exchange_adapter.get_statistics()
        assert final_stats["orders_placed"] == initial_placed + 1
        assert Decimal(final_stats["total_volume"]) > 0


class TestStopLossOrders:
    """Test stop-loss order functionality"""

    @pytest.mark.asyncio
    async def test_stop_loss_order_binance(self, exchange_adapter):
        """Test stop-loss order for Binance"""
        if exchange_adapter.config.exchange.value != "binance":
            pytest.skip("Binance-specific test")

        # Binance requires stop-loss with limit price
        with pytest.raises(InvalidOrder, match="Stop price required"):
            await exchange_adapter.place_order(
                symbol="BTC/USDT",
                side="sell",
                order_type="stop_loss",
                amount=0.001,
                price=45000.0,  # Limit price
                stop_price=None,  # Missing stop price
            )

    @pytest.mark.asyncio
    async def test_stop_loss_with_stop_price(self, mock_exchange_adapter):
        """Test stop-loss order with stop price"""
        # Mock the exchange to handle stop-loss
        mock_exchange_adapter.exchange.create_order = AsyncMock(
            return_value={
                "id": "stop123",
                "symbol": "BTC/USDT",
                "side": "sell",
                "type": "stop_loss_limit",
                "amount": 0.001,
                "price": 45000.0,
                "stopPrice": 45500.0,
                "status": "open",
                "timestamp": 1234567890,
                "datetime": "2025-10-31T00:00:00Z",
                "info": {},
            }
        )

        order = await mock_exchange_adapter.place_order(
            symbol="BTC/USDT",
            side="sell",
            order_type="stop_loss",
            amount=0.001,
            price=45000.0,
            stop_price=45500.0,
        )

        assert order["id"] == "stop123"
        assert order["type"] in ["stop_loss", "stop_loss_limit"]


class TestPositionManagement:
    """Test position tracking and management"""

    @pytest.mark.asyncio
    async def test_get_positions_spot(self, exchange_adapter):
        """Test getting positions for spot trading"""
        positions = await exchange_adapter.get_positions()

        assert isinstance(positions, list)

        # For spot, positions are non-zero balances
        for position in positions:
            assert "symbol" in position
            assert "amount" in position
            assert position["amount"] > 0

    @pytest.mark.asyncio
    async def test_positions_from_balance(self, mock_exchange_adapter):
        """Test that positions are derived from balance in spot mode"""
        # Set up mock balance with BTC
        mock_exchange_adapter.exchange.fetch_balance = AsyncMock(
            return_value={
                "free": {"USDT": 10000.0, "BTC": 0.5},
                "used": {"USDT": 0.0, "BTC": 0.0},
                "total": {"USDT": 10000.0, "BTC": 0.5},
                "info": {},
            }
        )

        positions = await mock_exchange_adapter.get_positions()

        # Should have BTC position
        btc_positions = [p for p in positions if "BTC" in p["symbol"]]
        assert len(btc_positions) > 0
        assert btc_positions[0]["amount"] == 0.5
        assert btc_positions[0]["side"] == "long"  # Spot is always long


class TestMarketData:
    """Test market data fetching"""

    @pytest.mark.asyncio
    async def test_get_ticker(self, exchange_adapter):
        """Test fetching ticker data"""
        ticker = await exchange_adapter.get_ticker("BTC/USDT")

        assert ticker["symbol"] == "BTC/USDT"
        assert "last" in ticker
        assert "bid" in ticker
        assert "ask" in ticker
        assert "high" in ticker
        assert "low" in ticker
        assert "volume" in ticker
        assert "timestamp" in ticker

        # Prices should be positive
        assert ticker["last"] > 0
        assert ticker["bid"] > 0
        assert ticker["ask"] > 0

    @pytest.mark.asyncio
    async def test_get_order_book(self, exchange_adapter):
        """Test fetching order book"""
        order_book = await exchange_adapter.get_order_book("BTC/USDT", limit=10)

        assert order_book["symbol"] == "BTC/USDT"
        assert "bids" in order_book
        assert "asks" in order_book
        assert "timestamp" in order_book

        # Check bid/ask structure
        if order_book["bids"]:
            bid = order_book["bids"][0]
            assert len(bid) == 2  # [price, amount]
            assert bid[0] > 0  # Price
            assert bid[1] > 0  # Amount

        if order_book["asks"]:
            ask = order_book["asks"][0]
            assert len(ask) == 2
            assert ask[0] > 0
            assert ask[1] > 0

        # Bids should be lower than asks
        if order_book["bids"] and order_book["asks"]:
            assert order_book["bids"][0][0] < order_book["asks"][0][0]


class TestErrorHandling:
    """Test error handling in order execution"""

    @pytest.mark.asyncio
    async def test_insufficient_funds_handling(self, mock_exchange_adapter):
        """Test handling of insufficient funds error"""
        # Mock insufficient funds error
        mock_exchange_adapter.exchange.create_market_order = AsyncMock(
            side_effect=InsufficientFunds("Insufficient balance")
        )

        with pytest.raises(InsufficientFunds):
            await mock_exchange_adapter.place_order(
                symbol="BTC/USDT",
                side="buy",
                order_type="market",
                amount=1000.0,  # Large amount
            )

        # Check failed order counted
        stats = mock_exchange_adapter.get_statistics()
        assert stats["orders_failed"] > 0

    @pytest.mark.asyncio
    async def test_invalid_order_handling(self, mock_exchange_adapter):
        """Test handling of invalid order errors"""
        # Mock invalid order error
        mock_exchange_adapter.exchange.create_limit_order = AsyncMock(
            side_effect=InvalidOrder("Invalid order parameters")
        )

        with pytest.raises(InvalidOrder):
            await mock_exchange_adapter.place_order(
                symbol="BTC/USDT",
                side="buy",
                order_type="limit",
                amount=-1,  # Invalid negative amount
                price=50000.0,
            )

    @pytest.mark.asyncio
    async def test_network_error_handling(self, mock_exchange_adapter):
        """Test handling of network errors"""
        from ccxt.base.errors import NetworkError

        # Mock network error
        mock_exchange_adapter.exchange.fetch_balance = AsyncMock(
            side_effect=NetworkError("Connection timeout")
        )

        with pytest.raises(Exception):  # Will be wrapped in ExchangeError
            await mock_exchange_adapter.get_balance()
