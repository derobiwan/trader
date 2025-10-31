"""
Comprehensive Unit Tests for Trade Executor Service

Covers:
- Order execution (market, limit, stop-loss)
- Retry logic and error handling
- Circuit breaker integration
- Position management integration
- Exchange API mocking
- Balance fetching and caching
- Trade history logging
- Metrics recording

Target Coverage: >80%
"""

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from ccxt.base.errors import (
    InsufficientFunds,
    InvalidOrder,
    NetworkError,
    RateLimitExceeded,
)

from workspace.features.trade_executor.executor_service import TradeExecutor
from workspace.features.trade_executor.models import (
    OrderSide,
    OrderStatus,
    OrderType,
    TimeInForce,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_exchange():
    """Create mock ccxt exchange"""
    exchange = MagicMock()
    exchange.load_markets = AsyncMock()
    exchange.fetch_balance = AsyncMock(
        return_value={"USDT": {"free": 10000.0, "total": 10000.0}}
    )
    exchange.fetch_ticker = AsyncMock(
        return_value={"last": 45000.0, "symbol": "BTC/USDT:USDT"}
    )
    exchange.create_order = AsyncMock(
        return_value={
            "id": "order-123",
            "status": "closed",
            "filled": 0.001,
            "average": 45000.0,
            "fee": {"cost": 0.45},
        }
    )
    exchange.fetch_order = AsyncMock(
        return_value={
            "id": "order-123",
            "status": "closed",
            "filled": 0.001,
            "average": 45000.0,
        }
    )
    exchange.close = AsyncMock()
    return exchange


@pytest.fixture
def mock_position_service():
    """Create mock PositionService"""
    service = MagicMock()
    service.create_position = AsyncMock(
        return_value=MagicMock(
            id="pos-123", symbol="BTC/USDT:USDT", quantity=Decimal("0.001")
        )
    )
    service.get_position = AsyncMock(
        return_value=MagicMock(
            id="pos-123",
            symbol="BTC/USDT:USDT",
            side="long",
            quantity=Decimal("0.001"),
            entry_price=Decimal("45000.0"),
        )
    )
    service.get_open_positions = AsyncMock(return_value=[])
    service.close_position = AsyncMock()
    return service


@pytest.fixture
def mock_trade_history_service():
    """Create mock TradeHistoryService"""
    service = MagicMock()
    service.log_trade = AsyncMock()
    return service


@pytest.fixture
def mock_metrics_service():
    """Create mock MetricsService"""
    service = MagicMock()
    service.record_trade = MagicMock()
    service.record_order = MagicMock()
    return service


@pytest.fixture
def executor(
    mock_exchange,
    mock_position_service,
    mock_trade_history_service,
    mock_metrics_service,
):
    """Create TradeExecutor instance with mocked dependencies"""
    executor = TradeExecutor(
        api_key="test_key",
        api_secret="test_secret",
        testnet=True,
        exchange=mock_exchange,
        position_service=mock_position_service,
        trade_history_service=mock_trade_history_service,
        metrics_service=mock_metrics_service,
        enable_circuit_breaker=False,  # Disable for unit tests
    )
    return executor


# ============================================================================
# Initialization Tests
# ============================================================================


@pytest.mark.asyncio
async def test_initialize_success(executor, mock_exchange):
    """Test successful initialization"""
    await executor.initialize()

    mock_exchange.load_markets.assert_called_once()
    mock_exchange.fetch_balance.assert_called_once()


@pytest.mark.asyncio
async def test_initialize_failure(executor, mock_exchange):
    """Test initialization failure handling"""
    mock_exchange.load_markets.side_effect = Exception("Connection failed")

    with pytest.raises(Exception, match="Connection failed"):
        await executor.initialize()


@pytest.mark.asyncio
async def test_close(executor, mock_exchange):
    """Test executor cleanup"""
    await executor.close()
    mock_exchange.close.assert_called_once()


# ============================================================================
# Balance Fetching Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_account_balance_success(executor, mock_exchange):
    """Test successful balance fetch"""
    balance = await executor.get_account_balance()

    assert balance > Decimal("0")
    assert isinstance(balance, Decimal)
    mock_exchange.fetch_balance.assert_called_once()


@pytest.mark.asyncio
async def test_get_account_balance_caching(executor, mock_exchange):
    """Test balance caching mechanism"""
    # First call - should hit exchange
    balance1 = await executor.get_account_balance(cache_ttl_seconds=60)
    assert mock_exchange.fetch_balance.call_count == 1

    # Second call within TTL - should use cache
    balance2 = await executor.get_account_balance(cache_ttl_seconds=60)
    assert mock_exchange.fetch_balance.call_count == 1
    assert balance1 == balance2


@pytest.mark.asyncio
async def test_get_account_balance_cache_expiry(executor, mock_exchange):
    """Test balance cache expiry"""
    # First call
    await executor.get_account_balance(cache_ttl_seconds=0)
    assert mock_exchange.fetch_balance.call_count == 1

    # Second call with expired cache
    await asyncio.sleep(0.1)
    await executor.get_account_balance(cache_ttl_seconds=0)
    assert mock_exchange.fetch_balance.call_count == 2


@pytest.mark.asyncio
async def test_get_account_balance_error_with_cache(executor, mock_exchange):
    """Test balance fetch error returns stale cache"""
    # First call succeeds
    balance = await executor.get_account_balance()

    # Second call fails
    mock_exchange.fetch_balance.side_effect = Exception("API Error")
    balance_fallback = await executor.get_account_balance()

    # Should return cached value
    assert balance == balance_fallback


@pytest.mark.asyncio
async def test_get_account_balance_error_no_cache(executor, mock_exchange):
    """Test balance fetch error without cache"""
    mock_exchange.fetch_balance.side_effect = Exception("API Error")

    with pytest.raises(Exception, match="API Error"):
        await executor.get_account_balance()


# ============================================================================
# Market Order Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_market_order_success(executor, mock_exchange):
    """Test successful market order placement"""
    result = await executor.create_market_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
        reduce_only=False,
    )

    assert result.success is True
    assert result.order is not None
    assert result.order.exchange_order_id == "order-123"
    assert result.order.status == OrderStatus.FILLED
    mock_exchange.create_order.assert_called_once()


@pytest.mark.asyncio
async def test_create_market_order_invalid_symbol(executor):
    """Test market order with invalid symbol format"""
    result = await executor.create_market_order(
        symbol="BTCUSDT",  # Missing ':USDT'
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
    )

    assert result.success is False
    assert result.error_code == "INVALID_SYMBOL"


@pytest.mark.asyncio
async def test_create_market_order_rate_limit(executor, mock_exchange):
    """Test market order rate limit handling with retry"""
    # First attempt fails with rate limit
    mock_exchange.create_order.side_effect = [
        RateLimitExceeded("Rate limit exceeded"),
        {
            "id": "order-123",
            "status": "closed",
            "filled": 0.001,
            "average": 45000.0,
            "fee": {"cost": 0.45},
        },
    ]

    result = await executor.create_market_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
    )

    assert result.success is True
    assert mock_exchange.create_order.call_count == 2


@pytest.mark.asyncio
async def test_create_market_order_rate_limit_max_retries(executor, mock_exchange):
    """Test market order exceeding max retries"""
    mock_exchange.create_order.side_effect = RateLimitExceeded("Rate limit exceeded")

    result = await executor.create_market_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
    )

    assert result.success is False
    assert result.error_code == "RATE_LIMIT_EXCEEDED"
    assert mock_exchange.create_order.call_count == 3  # max_retries


@pytest.mark.asyncio
async def test_create_market_order_invalid_order(executor, mock_exchange):
    """Test market order with invalid parameters"""
    mock_exchange.create_order.side_effect = InvalidOrder("Invalid order size")

    result = await executor.create_market_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
    )

    assert result.success is False
    assert result.error_code == "INVALID_ORDER"


@pytest.mark.asyncio
async def test_create_market_order_insufficient_funds(executor, mock_exchange):
    """Test market order with insufficient funds"""
    mock_exchange.create_order.side_effect = InsufficientFunds("Not enough balance")

    result = await executor.create_market_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
    )

    assert result.success is False
    assert result.error_code == "INSUFFICIENT_FUNDS"


@pytest.mark.asyncio
async def test_create_market_order_network_error_retry(executor, mock_exchange):
    """Test market order network error with retry"""
    mock_exchange.create_order.side_effect = [
        NetworkError("Connection timeout"),
        {
            "id": "order-123",
            "status": "closed",
            "filled": 0.001,
            "average": 45000.0,
            "fee": {"cost": 0.45},
        },
    ]

    result = await executor.create_market_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
    )

    assert result.success is True
    assert mock_exchange.create_order.call_count == 2


@pytest.mark.asyncio
async def test_create_market_order_metrics_recording(
    executor, mock_metrics_service, mock_exchange
):
    """Test metrics are recorded for market order"""
    await executor.create_market_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
    )

    mock_metrics_service.record_trade.assert_called_once()
    mock_metrics_service.record_order.assert_called_once()


@pytest.mark.asyncio
async def test_create_market_order_trade_history_logging(
    executor, mock_trade_history_service
):
    """Test trade is logged to history"""
    result = await executor.create_market_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
        metadata={"signal_confidence": "0.85"},
    )

    assert result.success is True
    mock_trade_history_service.log_trade.assert_called_once()


# ============================================================================
# Limit Order Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_limit_order_success(executor, mock_exchange):
    """Test successful limit order placement"""
    result = await executor.create_limit_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
        price=Decimal("44000.0"),
        time_in_force=TimeInForce.GTC,
    )

    assert result.success is True
    assert result.order is not None
    mock_exchange.create_order.assert_called_once()


@pytest.mark.asyncio
async def test_create_limit_order_invalid_symbol(executor):
    """Test limit order with invalid symbol"""
    result = await executor.create_limit_order(
        symbol="INVALID",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
        price=Decimal("44000.0"),
    )

    assert result.success is False
    assert result.error_code == "INVALID_SYMBOL"


@pytest.mark.asyncio
async def test_create_limit_order_post_only(executor, mock_exchange):
    """Test limit order with POST_ONLY time in force"""
    await executor.create_limit_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
        price=Decimal("44000.0"),
        time_in_force=TimeInForce.POST_ONLY,
    )

    # Verify POST_ONLY is passed to exchange
    call_args = mock_exchange.create_order.call_args
    assert call_args[1]["params"]["timeInForce"] == "POST_ONLY"


# ============================================================================
# Stop Market Order Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_stop_market_order_success(executor, mock_exchange):
    """Test successful stop-market order placement"""
    result = await executor.create_stop_market_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.SELL,
        quantity=Decimal("0.001"),
        stop_price=Decimal("44000.0"),
        reduce_only=True,
    )

    assert result.success is True
    assert result.order is not None
    assert result.order.type == OrderType.STOP_MARKET
    mock_exchange.create_order.assert_called_once()


@pytest.mark.asyncio
async def test_create_stop_market_order_error(executor, mock_exchange):
    """Test stop-market order error handling"""
    mock_exchange.create_order.side_effect = Exception("Stop order failed")

    result = await executor.create_stop_market_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.SELL,
        quantity=Decimal("0.001"),
        stop_price=Decimal("44000.0"),
    )

    assert result.success is False
    assert result.error_code == "STOP_ORDER_ERROR"


# ============================================================================
# Position Management Tests
# ============================================================================


@pytest.mark.asyncio
async def test_open_position_success(executor, mock_position_service, mock_exchange):
    """Test successful position opening"""
    result = await executor.open_position(
        symbol="BTC/USDT:USDT",
        side="long",
        quantity=Decimal("0.001"),
        leverage=10,
        stop_loss=Decimal("44000.0"),
    )

    assert result.success is True
    mock_position_service.create_position.assert_called_once()
    mock_exchange.create_order.assert_called()


@pytest.mark.asyncio
async def test_open_position_order_failure(
    executor, mock_position_service, mock_exchange
):
    """Test position opening when order fails"""
    mock_exchange.create_order.side_effect = Exception("Order failed")

    result = await executor.open_position(
        symbol="BTC/USDT:USDT",
        side="long",
        quantity=Decimal("0.001"),
        leverage=10,
        stop_loss=Decimal("44000.0"),
    )

    assert result.success is False
    # Position should be closed in database
    mock_position_service.close_position.assert_called_once()


@pytest.mark.asyncio
async def test_close_position_success(executor, mock_position_service, mock_exchange):
    """Test successful position closing"""
    result = await executor.close_position(
        position_id="pos-123",
        reason="manual_close",
    )

    assert result.success is True
    mock_position_service.get_position.assert_called_once()
    mock_position_service.close_position.assert_called_once()


@pytest.mark.asyncio
async def test_close_position_not_found(executor, mock_position_service):
    """Test closing non-existent position"""
    mock_position_service.get_position.return_value = None

    result = await executor.close_position(
        position_id="invalid-id",
        reason="manual_close",
    )

    assert result.success is False
    assert result.error_code == "POSITION_NOT_FOUND"


# ============================================================================
# Signal Execution Tests
# ============================================================================


@pytest.mark.asyncio
async def test_execute_signal_buy(executor, mock_exchange):
    """Test executing BUY signal"""
    from workspace.features.trading_loop import TradingDecision, TradingSignal

    signal = TradingSignal(
        symbol="BTC/USDT:USDT",
        decision=TradingDecision.BUY,
        confidence=Decimal("0.85"),
        size_pct=Decimal("0.10"),
        stop_loss_pct=Decimal("0.02"),
    )

    result = await executor.execute_signal(
        signal=signal,
        account_balance_chf=Decimal("10000.0"),
    )

    assert result.success is True
    # Should place market order and stop-loss
    assert mock_exchange.create_order.call_count >= 1


@pytest.mark.asyncio
async def test_execute_signal_sell(executor, mock_exchange):
    """Test executing SELL signal"""
    from workspace.features.trading_loop import TradingDecision, TradingSignal

    signal = TradingSignal(
        symbol="BTC/USDT:USDT",
        decision=TradingDecision.SELL,
        confidence=Decimal("0.85"),
        size_pct=Decimal("0.10"),
        stop_loss_pct=Decimal("0.02"),
    )

    result = await executor.execute_signal(
        signal=signal,
        account_balance_chf=Decimal("10000.0"),
    )

    assert result.success is True


@pytest.mark.asyncio
async def test_execute_signal_hold(executor):
    """Test executing HOLD signal"""
    from workspace.features.trading_loop import TradingDecision, TradingSignal

    signal = TradingSignal(
        symbol="BTC/USDT:USDT",
        decision=TradingDecision.HOLD,
        confidence=Decimal("0.50"),
        size_pct=Decimal("0.0"),
    )

    result = await executor.execute_signal(
        signal=signal,
        account_balance_chf=Decimal("10000.0"),
    )

    assert result.success is True
    assert "HOLD" in result.error_message


@pytest.mark.asyncio
async def test_execute_signal_close(executor, mock_position_service):
    """Test executing CLOSE signal"""
    from workspace.features.trading_loop import TradingDecision, TradingSignal

    # Setup open position
    mock_position_service.get_open_positions.return_value = [
        MagicMock(
            id="pos-123",
            symbol="BTC/USDT:USDT",
            side="long",
            quantity=Decimal("0.001"),
        )
    ]

    signal = TradingSignal(
        symbol="BTC/USDT:USDT",
        decision=TradingDecision.CLOSE,
        confidence=Decimal("0.70"),
        size_pct=Decimal("0.0"),
    )

    result = await executor.execute_signal(
        signal=signal,
        account_balance_chf=Decimal("10000.0"),
    )

    assert result.success is True


@pytest.mark.asyncio
async def test_execute_signal_close_no_position(executor, mock_position_service):
    """Test CLOSE signal when no position exists"""
    from workspace.features.trading_loop import TradingDecision, TradingSignal

    mock_position_service.get_open_positions.return_value = []

    signal = TradingSignal(
        symbol="BTC/USDT:USDT",
        decision=TradingDecision.CLOSE,
        confidence=Decimal("0.70"),
        size_pct=Decimal("0.0"),
    )

    result = await executor.execute_signal(
        signal=signal,
        account_balance_chf=Decimal("10000.0"),
    )

    assert result.success is False
    assert result.error_code == "POSITION_NOT_FOUND"


@pytest.mark.asyncio
async def test_execute_signal_with_risk_manager_rejection(executor):
    """Test signal rejected by risk manager"""
    from workspace.features.trading_loop import TradingDecision, TradingSignal

    signal = TradingSignal(
        symbol="BTC/USDT:USDT",
        decision=TradingDecision.BUY,
        confidence=Decimal("0.85"),
        size_pct=Decimal("0.10"),
    )

    # Mock risk manager that rejects signal
    risk_manager = MagicMock()
    risk_manager.validate_signal = AsyncMock(
        return_value=MagicMock(
            approved=False,
            rejection_reasons=["Exposure limit exceeded"],
        )
    )

    result = await executor.execute_signal(
        signal=signal,
        account_balance_chf=Decimal("10000.0"),
        risk_manager=risk_manager,
    )

    assert result.success is False
    assert result.error_code == "RISK_VALIDATION_FAILED"


# ============================================================================
# Order Status Fetching Tests
# ============================================================================


@pytest.mark.asyncio
async def test_fetch_order_status_success(executor, mock_exchange):
    """Test fetching order status"""
    # Add order to active orders
    from workspace.features.trade_executor.models import Order

    order = Order(
        id="ord-123",
        exchange_order_id="order-123",
        symbol="BTC/USDT:USDT",
        type=OrderType.MARKET,
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
    )
    executor.active_orders[order.id] = order

    updated_order = await executor.fetch_order_status("order-123", "BTC/USDT:USDT")

    assert updated_order is not None
    assert updated_order.status == OrderStatus.FILLED
    mock_exchange.fetch_order.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_order_status_not_found(executor, mock_exchange):
    """Test fetching status for unknown order"""
    result = await executor.fetch_order_status("unknown-order", "BTC/USDT:USDT")
    assert result is None


@pytest.mark.asyncio
async def test_fetch_order_status_error(executor, mock_exchange):
    """Test fetch order status error handling"""
    mock_exchange.fetch_order.side_effect = Exception("API Error")

    result = await executor.fetch_order_status("order-123", "BTC/USDT:USDT")
    assert result is None


# ============================================================================
# Circuit Breaker Tests
# ============================================================================


@pytest.mark.asyncio
async def test_circuit_breaker_initialization(mock_exchange, mock_position_service):
    """Test circuit breaker is initialized when enabled"""
    executor = TradeExecutor(
        api_key="test",
        api_secret="test",
        enable_circuit_breaker=True,
        exchange=mock_exchange,
        position_service=mock_position_service,
    )

    assert executor.exchange_circuit_breaker is not None


@pytest.mark.asyncio
async def test_circuit_breaker_disabled(mock_exchange, mock_position_service):
    """Test circuit breaker is not initialized when disabled"""
    executor = TradeExecutor(
        api_key="test",
        api_secret="test",
        enable_circuit_breaker=False,
        exchange=mock_exchange,
        position_service=mock_position_service,
    )

    assert executor.exchange_circuit_breaker is None


# ============================================================================
# Edge Cases and Error Scenarios
# ============================================================================


@pytest.mark.asyncio
async def test_create_market_order_partial_fill(executor, mock_exchange):
    """Test market order with partial fill"""
    mock_exchange.create_order.return_value = {
        "id": "order-123",
        "status": "open",
        "filled": 0.0005,
        "average": 45000.0,
        "fee": {"cost": 0.225},
    }

    result = await executor.create_market_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
    )

    assert result.success is True
    assert result.order.filled_quantity == Decimal("0.0005")
    assert result.order.status != OrderStatus.FILLED


@pytest.mark.asyncio
async def test_create_market_order_metadata(executor, mock_exchange):
    """Test market order with metadata"""
    metadata = {
        "signal_decision": "BUY",
        "signal_confidence": "0.85",
        "signal_reasoning": "Strong bullish signal",
    }

    result = await executor.create_market_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
        metadata=metadata,
    )

    assert result.success is True
    assert result.order.metadata == metadata


@pytest.mark.asyncio
async def test_execute_signal_error_handling(executor, mock_exchange):
    """Test signal execution error handling"""
    from workspace.features.trading_loop import TradingDecision, TradingSignal

    mock_exchange.fetch_ticker.side_effect = Exception("API Error")

    signal = TradingSignal(
        symbol="BTC/USDT:USDT",
        decision=TradingDecision.BUY,
        confidence=Decimal("0.85"),
        size_pct=Decimal("0.10"),
    )

    result = await executor.execute_signal(
        signal=signal,
        account_balance_chf=Decimal("10000.0"),
    )

    assert result.success is False
    assert result.error_code == "EXECUTION_ERROR"
