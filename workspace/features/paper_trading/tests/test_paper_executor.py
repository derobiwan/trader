"""
Tests for Paper Trading Executor

Tests paper trading functionality including order execution, balance tracking,
and performance reporting.

Author: Implementation Specialist (Sprint 2 Stream B)
Date: 2025-10-29
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock

from workspace.features.paper_trading import PaperTradingExecutor
from workspace.features.trade_executor.models import OrderSide, OrderType


@pytest.fixture
async def paper_executor():
    """Create paper trading executor for testing"""
    executor = PaperTradingExecutor(
        initial_balance=Decimal("10000"),
        api_key="test_key",
        api_secret="test_secret",
        enable_slippage=False,  # Disable for predictable testing
        enable_partial_fills=False,
    )

    # Mock exchange
    executor.exchange = AsyncMock()
    executor.exchange.fetch_ticker = AsyncMock(return_value={"last": 45000.0})
    executor.exchange.load_markets = AsyncMock()

    await executor.initialize()

    yield executor

    await executor.close()


@pytest.mark.asyncio
async def test_paper_trading_initialization(paper_executor):
    """Test paper trading executor initialization"""
    assert paper_executor.initial_balance == Decimal("10000")
    assert paper_executor.virtual_portfolio.balance == Decimal("10000")
    assert len(paper_executor.simulated_trades) == 0
    assert not paper_executor.enable_slippage
    assert not paper_executor.enable_partial_fills


@pytest.mark.asyncio
async def test_paper_trading_buy_order(paper_executor):
    """Test paper trading buy order execution"""
    # Execute buy order
    order = await paper_executor.create_market_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.1"),
    )

    # Verify order
    assert order.symbol == "BTC/USDT:USDT"
    assert order.side == OrderSide.BUY
    assert order.quantity == Decimal("0.1")
    assert order.filled_quantity == Decimal("0.1")
    assert order.status.value == "filled"
    assert order.metadata["paper_trading"]

    # Verify balance updated
    expected_cost = Decimal("0.1") * Decimal("45000") + order.fees_paid
    expected_balance = Decimal("10000") - expected_cost
    assert paper_executor.virtual_portfolio.balance == expected_balance

    # Verify position opened
    assert "BTC/USDT:USDT" in paper_executor.virtual_portfolio.positions


@pytest.mark.asyncio
async def test_paper_trading_sell_order(paper_executor):
    """Test paper trading sell order (close position)"""
    # First, open a position
    await paper_executor.create_market_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.1"),
    )

    initial_balance = paper_executor.virtual_portfolio.balance

    # Now close it
    # Mock price increase
    paper_executor.exchange.fetch_ticker = AsyncMock(return_value={"last": 46000.0})

    sell_order = await paper_executor.create_market_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.SELL,
        quantity=Decimal("0.1"),
        reduce_only=True,
    )

    # Verify order
    assert sell_order.status.value == "filled"

    # Verify position closed
    assert "BTC/USDT:USDT" not in paper_executor.virtual_portfolio.positions

    # Verify profit realized
    final_balance = paper_executor.virtual_portfolio.balance
    assert final_balance > initial_balance  # Made profit on price increase


@pytest.mark.asyncio
async def test_paper_trading_insufficient_balance(paper_executor):
    """Test paper trading with insufficient balance"""
    with pytest.raises(ValueError, match="Insufficient balance"):
        await paper_executor.create_market_order(
            symbol="BTC/USDT:USDT",
            side=OrderSide.BUY,
            quantity=Decimal("10"),  # Too large
        )


@pytest.mark.asyncio
async def test_paper_trading_fees_calculation(paper_executor):
    """Test paper trading fee calculation"""
    order = await paper_executor.create_market_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.1"),
    )

    # Calculate expected fees (0.1% of notional)
    notional = Decimal("0.1") * Decimal("45000")
    expected_fees = notional * Decimal("0.001")

    assert order.fees_paid == expected_fees


@pytest.mark.asyncio
async def test_paper_trading_with_slippage():
    """Test paper trading with slippage enabled"""
    executor = PaperTradingExecutor(
        initial_balance=Decimal("10000"),
        api_key="test_key",
        api_secret="test_secret",
        enable_slippage=True,
        enable_partial_fills=False,
    )

    executor.exchange = AsyncMock()
    executor.exchange.fetch_ticker = AsyncMock(return_value={"last": 45000.0})
    executor.exchange.load_markets = AsyncMock()

    await executor.initialize()

    # Execute order
    order = await executor.create_market_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.1"),
    )

    # With slippage, execution price should be slightly different
    # (either equal or slightly higher for buy orders)
    assert order.average_fill_price >= Decimal("45000")

    await executor.close()


@pytest.mark.asyncio
async def test_paper_trading_with_partial_fills():
    """Test paper trading with partial fills enabled"""
    executor = PaperTradingExecutor(
        initial_balance=Decimal("10000"),
        api_key="test_key",
        api_secret="test_secret",
        enable_slippage=False,
        enable_partial_fills=True,
    )

    executor.exchange = AsyncMock()
    executor.exchange.fetch_ticker = AsyncMock(return_value={"last": 45000.0})
    executor.exchange.load_markets = AsyncMock()

    await executor.initialize()

    # Execute order
    order = await executor.create_market_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.1"),
    )

    # With partial fills, filled quantity should be 95-100% of requested
    assert order.filled_quantity >= Decimal("0.095")
    assert order.filled_quantity <= Decimal("0.1")

    await executor.close()


@pytest.mark.asyncio
async def test_paper_trading_performance_report(paper_executor):
    """Test paper trading performance report generation"""
    # Execute some trades
    await paper_executor.create_market_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.1"),
    )

    # Mock price increase and close
    paper_executor.exchange.fetch_ticker = AsyncMock(return_value={"last": 46000.0})

    await paper_executor.create_market_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.SELL,
        quantity=Decimal("0.1"),
        reduce_only=True,
    )

    # Get performance report
    report = paper_executor.get_performance_report()

    # Verify report structure
    assert "summary" in report
    assert "profitability" in report
    assert "portfolio" in report

    # Verify portfolio metrics
    assert report["portfolio"]["initial_balance"] == 10000.0
    assert "current_balance" in report["portfolio"]
    assert "total_return" in report["portfolio"]


@pytest.mark.asyncio
async def test_paper_trading_reset(paper_executor):
    """Test paper trading reset functionality"""
    # Execute a trade
    await paper_executor.create_market_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.1"),
    )

    # Verify trade recorded
    assert len(paper_executor.simulated_trades) > 0
    assert paper_executor.virtual_portfolio.balance < Decimal("10000")

    # Reset
    await paper_executor.reset(initial_balance=Decimal("15000"))

    # Verify reset
    assert paper_executor.initial_balance == Decimal("15000")
    assert paper_executor.virtual_portfolio.balance == Decimal("15000")
    assert len(paper_executor.simulated_trades) == 0
    assert len(paper_executor.virtual_portfolio.positions) == 0


@pytest.mark.asyncio
async def test_paper_trading_multiple_symbols(paper_executor):
    """Test paper trading with multiple symbols"""

    # Mock different prices for different symbols
    async def mock_fetch_ticker(symbol):
        prices = {
            "BTC/USDT:USDT": {"last": 45000.0},
            "ETH/USDT:USDT": {"last": 2500.0},
        }
        return prices.get(symbol, {"last": 1000.0})

    paper_executor.exchange.fetch_ticker = mock_fetch_ticker

    # Open positions in both symbols
    await paper_executor.create_market_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.1"),
    )

    await paper_executor.create_market_order(
        symbol="ETH/USDT:USDT",
        side=OrderSide.BUY,
        quantity=Decimal("1.0"),
    )

    # Verify both positions
    assert "BTC/USDT:USDT" in paper_executor.virtual_portfolio.positions
    assert "ETH/USDT:USDT" in paper_executor.virtual_portfolio.positions
    assert len(paper_executor.simulated_trades) == 2


@pytest.mark.asyncio
async def test_paper_trading_stop_loss_order(paper_executor):
    """Test paper trading stop-loss order creation"""
    order = await paper_executor.create_stop_loss_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.SELL,
        quantity=Decimal("0.1"),
        stop_price=Decimal("44000"),
    )

    # Verify stop-loss order
    assert order.type == OrderType.STOP_MARKET
    assert order.stop_price == Decimal("44000")
    assert order.status.value == "open"
    assert order.metadata["stop_loss"]


@pytest.mark.asyncio
async def test_paper_trading_get_account_balance(paper_executor):
    """Test getting virtual account balance"""
    balance = await paper_executor.get_account_balance()

    assert balance == Decimal("10000")

    # Execute trade
    await paper_executor.create_market_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.1"),
    )

    # Balance should be reduced
    new_balance = await paper_executor.get_account_balance()
    assert new_balance < Decimal("10000")


@pytest.mark.asyncio
async def test_paper_trading_get_position(paper_executor):
    """Test getting virtual position"""
    # No position initially
    position = await paper_executor.get_position("BTC/USDT:USDT")
    assert position is None

    # Open position
    await paper_executor.create_market_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.1"),
    )

    # Position should exist
    position = await paper_executor.get_position("BTC/USDT:USDT")
    assert position is not None
    assert position["symbol"] == "BTC/USDT:USDT"
    assert position["quantity"] == Decimal("0.1")
