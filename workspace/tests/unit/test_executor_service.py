"""
Unit Tests for Trade Executor Service

Comprehensive test coverage for executor_service.py including:
- Initialization and configuration
- Market order execution (success and failure paths)
- Limit order placement
- Stop-market order placement
- Position opening/closing
- Signal execution workflow
- Error handling (network, rate limit, invalid order, insufficient funds)
- Retry logic with exponential backoff
- Order status tracking
- Balance fetching and caching
- Trade history logging
- Metrics recording
- Circuit breaker integration

Target: 85%+ code coverage

Author: Validation Engineer Team Alpha
Date: 2025-10-30
Sprint: 3, Stream A
"""

import pytest
import pytest_asyncio
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal

import ccxt.async_support as ccxt
from ccxt.base.errors import (
    NetworkError,
    RateLimitExceeded,
    InvalidOrder,
    InsufficientFunds,
)

from workspace.features.trade_executor.executor_service import TradeExecutor
from workspace.features.trade_executor.models import (
    Order,
    OrderType,
    OrderSide,
    OrderStatus,
    TimeInForce,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_exchange():
    """Mock ccxt exchange instance."""
    exchange = AsyncMock(spec=ccxt.bybit)
    exchange.load_markets = AsyncMock()
    exchange.fetch_balance = AsyncMock(
        return_value={
            "USDT": {"free": 1000.0, "used": 0.0, "total": 1000.0},
            "total": 1000.0,
        }
    )
    exchange.fetch_ticker = AsyncMock(
        return_value={"last": 45000.0, "bid": 44999.0, "ask": 45001.0}
    )
    exchange.create_order = AsyncMock(
        return_value={
            "id": "exchange-order-123",
            "status": "closed",
            "filled": 0.001,
            "average": 45000.0,
            "fee": {"cost": 0.05, "currency": "USDT"},
        }
    )
    exchange.fetch_order = AsyncMock(
        return_value={
            "id": "exchange-order-123",
            "status": "closed",
            "filled": 0.001,
            "average": 45000.0,
        }
    )
    exchange.close = AsyncMock()
    exchange.markets = {"BTC/USDT:USDT": {"id": "BTCUSDT"}}

    return exchange


@pytest.fixture
def mock_db_pool():
    """Mock database pool for position service."""
    pool = AsyncMock()
    conn = AsyncMock()
    conn.execute = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchval = AsyncMock(return_value=None)

    # Acquire context manager
    pool.acquire = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

    return pool


@pytest.fixture
def mock_position_service(mock_db_pool):
    """Mock position service."""
    service = AsyncMock()
    service.create_position = AsyncMock(
        return_value=MagicMock(
            id="pos-123", symbol="BTC/USDT:USDT", side="long", quantity=Decimal("0.001")
        )
    )
    service.get_position = AsyncMock(
        return_value=MagicMock(
            id="pos-123",
            symbol="BTC/USDT:USDT",
            side="long",
            quantity=Decimal("0.001"),
            entry_price=Decimal("45000.00"),
        )
    )
    service.get_open_positions = AsyncMock(
        return_value=[MagicMock(id="pos-123", symbol="BTC/USDT:USDT", side="long")]
    )
    service.close_position = AsyncMock()
    return service


@pytest.fixture
def mock_trade_history_service():
    """Mock trade history service."""
    service = AsyncMock()
    service.log_trade = AsyncMock()
    return service


@pytest.fixture
def mock_metrics_service():
    """Mock metrics service."""
    service = AsyncMock()
    service.record_trade = AsyncMock()
    service.record_order = AsyncMock()
    return service


@pytest_asyncio.fixture
async def executor(
    mock_exchange,
    mock_position_service,
    mock_trade_history_service,
    mock_metrics_service,
):
    """Create TradeExecutor with mocked dependencies."""
    executor = TradeExecutor(
        api_key="test_api_key",
        api_secret="test_api_secret",
        testnet=True,
        max_retries=3,
        retry_delay=0.01,  # Fast retries for testing
        exchange=mock_exchange,
        position_service=mock_position_service,
        trade_history_service=mock_trade_history_service,
        metrics_service=mock_metrics_service,
        enable_circuit_breaker=False,  # Disable for unit tests
    )
    yield executor
    # Cleanup
    await executor.close()


@pytest.fixture
def mock_trading_signal():
    """Mock trading signal."""
    signal = MagicMock()
    signal.symbol = "BTC/USDT:USDT"
    signal.decision = MagicMock()
    signal.decision.value = "BUY"
    signal.confidence = Decimal("0.75")
    signal.size_pct = Decimal("0.15")
    signal.stop_loss_pct = Decimal("0.02")
    signal.reasoning = "Strong bullish momentum"
    return signal


# ============================================================================
# Initialization Tests
# ============================================================================


@pytest.mark.asyncio
async def test_executor_initialization_testnet(mock_db_pool, mock_position_service):
    """Test executor initializes correctly in testnet mode."""
    with (
        patch(
            "workspace.features.trade_executor.executor_service.PositionService",
            return_value=mock_position_service,
        ),
        patch("workspace.features.trade_executor.executor_service.TradeHistoryService"),
        patch("workspace.features.trade_executor.executor_service.MetricsService"),
    ):
        executor = TradeExecutor(
            api_key="test_key",
            api_secret="test_secret",
            testnet=True,
        )

        assert executor.testnet is True
        assert executor.max_retries == 3
        assert executor.retry_delay == 1.0
        assert executor.enable_circuit_breaker is True
        assert executor.exchange_circuit_breaker is not None

        await executor.close()


@pytest.mark.asyncio
async def test_executor_initialization_production(mock_db_pool, mock_position_service):
    """Test executor initializes correctly in production mode."""
    with (
        patch(
            "workspace.features.trade_executor.executor_service.PositionService",
            return_value=mock_position_service,
        ),
        patch("workspace.features.trade_executor.executor_service.TradeHistoryService"),
        patch("workspace.features.trade_executor.executor_service.MetricsService"),
    ):
        executor = TradeExecutor(
            api_key="test_key",
            api_secret="test_secret",
            testnet=False,
        )

        assert executor.testnet is False

        await executor.close()


@pytest.mark.asyncio
async def test_executor_initialization_custom_params(
    mock_db_pool, mock_position_service
):
    """Test executor with custom parameters."""
    with (
        patch(
            "workspace.features.trade_executor.executor_service.PositionService",
            return_value=mock_position_service,
        ),
        patch("workspace.features.trade_executor.executor_service.TradeHistoryService"),
        patch("workspace.features.trade_executor.executor_service.MetricsService"),
    ):
        executor = TradeExecutor(
            api_key="test_key",
            api_secret="test_secret",
            max_retries=5,
            retry_delay=2.0,
            rate_limit_buffer=0.5,
            enable_circuit_breaker=False,
        )

        assert executor.max_retries == 5
        assert executor.retry_delay == 2.0
        assert executor.rate_limit_buffer == 0.5
        assert executor.exchange_circuit_breaker is None

        await executor.close()


@pytest.mark.asyncio
async def test_initialize_success(executor, mock_exchange):
    """Test successful initialization with market loading."""
    # Arrange
    mock_exchange.markets = {"BTC/USDT:USDT": {"id": "BTCUSDT"}}

    # Act
    await executor.initialize()

    # Assert
    mock_exchange.load_markets.assert_called_once()
    mock_exchange.fetch_balance.assert_called_once()


@pytest.mark.asyncio
async def test_initialize_failure(executor, mock_exchange):
    """Test initialization failure handling."""
    # Arrange
    mock_exchange.load_markets.side_effect = Exception("Network error")

    # Act & Assert
    with pytest.raises(Exception, match="Network error"):
        await executor.initialize()


# ============================================================================
# Balance Management Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_account_balance_fresh_fetch(executor, mock_exchange):
    """Test fetching fresh account balance."""
    # Arrange
    mock_exchange.fetch_balance.return_value = {
        "USDT": {"free": 1000.0, "used": 0.0, "total": 1000.0}
    }

    # Act
    balance = await executor.get_account_balance()

    # Assert
    assert balance > 0
    assert isinstance(balance, Decimal)
    mock_exchange.fetch_balance.assert_called_once()


@pytest.mark.asyncio
async def test_get_account_balance_cached(executor, mock_exchange):
    """Test balance caching works correctly."""
    # Arrange
    mock_exchange.fetch_balance.return_value = {
        "USDT": {"free": 1000.0, "used": 0.0, "total": 1000.0}
    }

    # Act - First call fetches from exchange
    balance1 = await executor.get_account_balance(cache_ttl_seconds=60)
    # Second call uses cache
    balance2 = await executor.get_account_balance(cache_ttl_seconds=60)

    # Assert
    assert balance1 == balance2
    # Should only fetch once due to caching
    assert mock_exchange.fetch_balance.call_count == 1


@pytest.mark.asyncio
async def test_get_account_balance_cache_expired(executor, mock_exchange):
    """Test balance cache expiration."""
    # Arrange
    mock_exchange.fetch_balance.return_value = {
        "USDT": {"free": 1000.0, "used": 0.0, "total": 1000.0}
    }

    # Act - First call
    balance1 = await executor.get_account_balance(cache_ttl_seconds=0)
    # Wait for cache to expire
    await asyncio.sleep(0.1)
    # Second call should fetch fresh
    balance2 = await executor.get_account_balance(cache_ttl_seconds=0)

    # Assert
    assert balance1 == balance2
    # Should fetch twice due to expiration
    assert mock_exchange.fetch_balance.call_count == 2


@pytest.mark.asyncio
async def test_get_account_balance_fetch_failure_with_cache(executor, mock_exchange):
    """Test balance fetch failure returns stale cache."""
    # Arrange
    mock_exchange.fetch_balance.return_value = {
        "USDT": {"free": 1000.0, "used": 0.0, "total": 1000.0}
    }

    # Act - First call succeeds
    balance1 = await executor.get_account_balance()

    # Second call fails but should return cached value
    mock_exchange.fetch_balance.side_effect = Exception("Network error")
    balance2 = await executor.get_account_balance()

    # Assert
    assert balance1 == balance2


@pytest.mark.asyncio
async def test_get_account_balance_fetch_failure_no_cache(executor, mock_exchange):
    """Test balance fetch failure with no cache raises exception."""
    # Arrange
    mock_exchange.fetch_balance.side_effect = Exception("Network error")

    # Act & Assert
    with pytest.raises(Exception, match="Network error"):
        await executor.get_account_balance()


# ============================================================================
# Market Order Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_market_order_success_buy(executor, mock_exchange):
    """Test successful market buy order."""
    # Act
    result = await executor.create_market_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
        reduce_only=False,
    )

    # Assert
    assert result.success is True
    assert result.order is not None
    assert result.order.symbol == "BTC/USDT:USDT"
    assert result.order.side == OrderSide.BUY
    assert result.order.type == OrderType.MARKET
    assert result.order.exchange_order_id == "exchange-order-123"
    assert result.latency_ms > 0

    mock_exchange.create_order.assert_called_once()


@pytest.mark.asyncio
async def test_create_market_order_success_sell(executor, mock_exchange):
    """Test successful market sell order."""
    # Act
    result = await executor.create_market_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.SELL,
        quantity=Decimal("0.001"),
        reduce_only=True,
    )

    # Assert
    assert result.success is True
    assert result.order.side == OrderSide.SELL
    assert result.order.reduce_only is True


@pytest.mark.asyncio
async def test_create_market_order_invalid_symbol(executor):
    """Test market order with invalid symbol format."""
    # Act
    result = await executor.create_market_order(
        symbol="BTCUSDT",  # Missing settlement currency
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
    )

    # Assert
    assert result.success is False
    assert result.error_code == "INVALID_SYMBOL"
    assert "Must be" in result.error_message


@pytest.mark.asyncio
async def test_create_market_order_network_error_retry(executor, mock_exchange):
    """Test market order retries on network error."""
    # Arrange
    mock_exchange.create_order.side_effect = [
        NetworkError("Connection timeout"),
        {
            "id": "exchange-order-123",
            "status": "closed",
            "filled": 0.001,
            "average": 45000.0,
            "fee": {"cost": 0.05, "currency": "USDT"},
        },
    ]

    # Act
    result = await executor.create_market_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
    )

    # Assert
    assert result.success is True
    assert mock_exchange.create_order.call_count == 2


@pytest.mark.asyncio
async def test_create_market_order_rate_limit_retry(executor, mock_exchange):
    """Test market order retries on rate limit."""
    # Arrange
    mock_exchange.create_order.side_effect = [
        RateLimitExceeded("Rate limit exceeded"),
        {
            "id": "exchange-order-123",
            "status": "closed",
            "filled": 0.001,
            "average": 45000.0,
            "fee": {"cost": 0.05, "currency": "USDT"},
        },
    ]

    # Act
    result = await executor.create_market_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
    )

    # Assert
    assert result.success is True
    assert mock_exchange.create_order.call_count == 2


@pytest.mark.asyncio
async def test_create_market_order_max_retries_exceeded(executor, mock_exchange):
    """Test market order fails after max retries."""
    # Arrange
    mock_exchange.create_order.side_effect = NetworkError("Connection timeout")

    # Act
    result = await executor.create_market_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
    )

    # Assert
    assert result.success is False
    assert result.error_code == "NETWORK_ERROR"
    assert mock_exchange.create_order.call_count == 3


@pytest.mark.asyncio
async def test_create_market_order_invalid_order_error(executor, mock_exchange):
    """Test market order handles invalid order error."""
    # Arrange
    mock_exchange.create_order.side_effect = InvalidOrder("Invalid quantity")

    # Act
    result = await executor.create_market_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
    )

    # Assert
    assert result.success is False
    assert result.error_code == "INVALID_ORDER"
    assert "Invalid quantity" in result.error_message


@pytest.mark.asyncio
async def test_create_market_order_insufficient_funds(executor, mock_exchange):
    """Test market order handles insufficient funds."""
    # Arrange
    mock_exchange.create_order.side_effect = InsufficientFunds("Not enough balance")

    # Act
    result = await executor.create_market_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
    )

    # Assert
    assert result.success is False
    assert result.error_code == "INSUFFICIENT_FUNDS"


@pytest.mark.asyncio
async def test_create_market_order_with_metadata(executor, mock_exchange):
    """Test market order with metadata."""
    # Arrange
    metadata = {"signal_id": "sig-123", "strategy": "momentum"}

    # Act
    result = await executor.create_market_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
        metadata=metadata,
    )

    # Assert
    assert result.success is True
    assert result.order.metadata == metadata


# ============================================================================
# Limit Order Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_limit_order_success(executor, mock_exchange):
    """Test successful limit order creation."""
    # Arrange
    mock_exchange.create_order.return_value = {
        "id": "limit-order-123",
        "status": "open",
        "filled": 0.0,
        "average": None,
    }

    # Act
    result = await executor.create_limit_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
        price=Decimal("44000.00"),
        time_in_force=TimeInForce.GTC,
    )

    # Assert
    assert result.success is True
    assert result.order.type == OrderType.LIMIT
    assert result.order.price == Decimal("44000.00")
    assert result.order.time_in_force == TimeInForce.GTC


@pytest.mark.asyncio
async def test_create_limit_order_post_only(executor, mock_exchange):
    """Test limit order with POST_ONLY time in force."""
    # Arrange
    mock_exchange.create_order.return_value = {
        "id": "limit-order-123",
        "status": "open",
        "filled": 0.0,
    }

    # Act
    result = await executor.create_limit_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
        price=Decimal("44000.00"),
        time_in_force=TimeInForce.POST_ONLY,
    )

    # Assert
    assert result.success is True
    assert result.order.time_in_force == TimeInForce.POST_ONLY


@pytest.mark.asyncio
async def test_create_limit_order_invalid_symbol(executor):
    """Test limit order with invalid symbol."""
    # Act
    result = await executor.create_limit_order(
        symbol="INVALID",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
        price=Decimal("44000.00"),
    )

    # Assert
    assert result.success is False
    assert result.error_code == "INVALID_SYMBOL"


# ============================================================================
# Stop-Market Order Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_stop_market_order_success(executor, mock_exchange):
    """Test successful stop-market order creation."""
    # Arrange
    mock_exchange.create_order.return_value = {
        "id": "stop-order-123",
        "status": "open",
    }

    # Act
    result = await executor.create_stop_market_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.SELL,
        quantity=Decimal("0.001"),
        stop_price=Decimal("43000.00"),
        reduce_only=True,
    )

    # Assert
    assert result.success is True
    assert result.order.type == OrderType.STOP_MARKET
    assert result.order.stop_price == Decimal("43000.00")
    assert result.order.status == OrderStatus.OPEN


@pytest.mark.asyncio
async def test_create_stop_market_order_failure(executor, mock_exchange):
    """Test stop-market order creation failure."""
    # Arrange
    mock_exchange.create_order.side_effect = Exception("Exchange error")

    # Act
    result = await executor.create_stop_market_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.SELL,
        quantity=Decimal("0.001"),
        stop_price=Decimal("43000.00"),
    )

    # Assert
    assert result.success is False
    assert result.error_code == "STOP_ORDER_ERROR"


# ============================================================================
# Position Management Tests
# ============================================================================


@pytest.mark.asyncio
async def test_open_position_success(executor, mock_exchange, mock_position_service):
    """Test successful position opening."""
    # Arrange
    mock_exchange.fetch_ticker.return_value = {"last": 45000.0}

    # Act
    result = await executor.open_position(
        symbol="BTC/USDT:USDT",
        side="long",
        quantity=Decimal("0.001"),
        leverage=10,
        stop_loss=Decimal("44000.00"),
        take_profit=Decimal("46000.00"),
        signal_id="sig-123",
    )

    # Assert
    assert result.success is True
    mock_position_service.create_position.assert_called_once()
    mock_exchange.create_order.assert_called()


@pytest.mark.asyncio
async def test_open_position_order_execution_failed(
    executor, mock_exchange, mock_position_service
):
    """Test position opening when order execution fails."""
    # Arrange
    mock_exchange.create_order.side_effect = Exception("Order failed")

    # Act
    result = await executor.open_position(
        symbol="BTC/USDT:USDT",
        side="long",
        quantity=Decimal("0.001"),
        leverage=10,
        stop_loss=Decimal("44000.00"),
    )

    # Assert
    assert result.success is False
    # Position should be closed/failed
    mock_position_service.close_position.assert_called_once()


@pytest.mark.asyncio
async def test_close_position_success(executor, mock_position_service):
    """Test successful position closing."""
    # Act
    result = await executor.close_position(
        position_id="pos-123",
        reason="manual_close",
    )

    # Assert
    assert result.success is True
    mock_position_service.get_position.assert_called_once()
    mock_position_service.close_position.assert_called_once()


@pytest.mark.asyncio
async def test_close_position_not_found(executor, mock_position_service):
    """Test closing non-existent position."""
    # Arrange
    mock_position_service.get_position.return_value = None

    # Act
    result = await executor.close_position(
        position_id="pos-999",
        reason="manual_close",
    )

    # Assert
    assert result.success is False
    assert result.error_code == "POSITION_NOT_FOUND"


# ============================================================================
# Signal Execution Tests
# ============================================================================


@pytest.mark.asyncio
async def test_execute_signal_buy(executor, mock_exchange, mock_trading_signal):
    """Test executing BUY signal."""
    # Arrange
    from workspace.features.trading_loop import TradingDecision

    mock_trading_signal.decision = TradingDecision.BUY

    # Act
    result = await executor.execute_signal(
        signal=mock_trading_signal,
        account_balance_chf=Decimal("2626.96"),
        chf_to_usd_rate=Decimal("1.10"),
    )

    # Assert
    assert result.success is True
    mock_exchange.create_order.assert_called()


@pytest.mark.asyncio
async def test_execute_signal_sell(executor, mock_exchange, mock_trading_signal):
    """Test executing SELL signal."""
    # Arrange
    from workspace.features.trading_loop import TradingDecision

    mock_trading_signal.decision = TradingDecision.SELL

    # Act
    result = await executor.execute_signal(
        signal=mock_trading_signal,
        account_balance_chf=Decimal("2626.96"),
        chf_to_usd_rate=Decimal("1.10"),
    )

    # Assert
    assert result.success is True
    mock_exchange.create_order.assert_called()


@pytest.mark.asyncio
async def test_execute_signal_hold(executor, mock_trading_signal):
    """Test executing HOLD signal (no action)."""
    # Arrange
    from workspace.features.trading_loop import TradingDecision

    mock_trading_signal.decision = TradingDecision.HOLD

    # Act
    result = await executor.execute_signal(
        signal=mock_trading_signal,
        account_balance_chf=Decimal("2626.96"),
    )

    # Assert
    assert result.success is True
    assert "HOLD signal" in result.error_message


@pytest.mark.asyncio
async def test_execute_signal_close(
    executor, mock_position_service, mock_trading_signal
):
    """Test executing CLOSE signal."""
    # Arrange
    from workspace.features.trading_loop import TradingDecision

    mock_trading_signal.decision = TradingDecision.CLOSE

    # Act
    result = await executor.execute_signal(
        signal=mock_trading_signal,
        account_balance_chf=Decimal("2626.96"),
    )

    # Assert
    assert result.success is True
    mock_position_service.get_open_positions.assert_called_once()


@pytest.mark.asyncio
async def test_execute_signal_close_no_position(
    executor, mock_position_service, mock_trading_signal
):
    """Test CLOSE signal when no position exists."""
    # Arrange
    from workspace.features.trading_loop import TradingDecision

    mock_trading_signal.decision = TradingDecision.CLOSE
    mock_position_service.get_open_positions.return_value = []

    # Act
    result = await executor.execute_signal(
        signal=mock_trading_signal,
        account_balance_chf=Decimal("2626.96"),
    )

    # Assert
    assert result.success is False
    assert result.error_code == "POSITION_NOT_FOUND"


@pytest.mark.asyncio
async def test_execute_signal_with_risk_manager_approved(
    executor, mock_exchange, mock_trading_signal
):
    """Test signal execution with risk manager approval."""
    # Arrange
    from workspace.features.trading_loop import TradingDecision

    mock_trading_signal.decision = TradingDecision.BUY

    mock_risk_manager = AsyncMock()
    mock_risk_manager.validate_signal = AsyncMock(
        return_value=MagicMock(approved=True, rejection_reasons=[])
    )

    # Act
    result = await executor.execute_signal(
        signal=mock_trading_signal,
        account_balance_chf=Decimal("2626.96"),
        risk_manager=mock_risk_manager,
    )

    # Assert
    assert result.success is True
    mock_risk_manager.validate_signal.assert_called_once()


@pytest.mark.asyncio
async def test_execute_signal_with_risk_manager_rejected(executor, mock_trading_signal):
    """Test signal execution with risk manager rejection."""
    # Arrange
    from workspace.features.trading_loop import TradingDecision

    mock_trading_signal.decision = TradingDecision.BUY

    mock_risk_manager = AsyncMock()
    mock_risk_manager.validate_signal = AsyncMock(
        return_value=MagicMock(
            approved=False, rejection_reasons=["Position size too large"]
        )
    )

    # Act
    result = await executor.execute_signal(
        signal=mock_trading_signal,
        account_balance_chf=Decimal("2626.96"),
        risk_manager=mock_risk_manager,
    )

    # Assert
    assert result.success is False
    assert result.error_code == "RISK_VALIDATION_FAILED"


# ============================================================================
# Order Status Tracking Tests
# ============================================================================


@pytest.mark.asyncio
async def test_fetch_order_status_success(executor, mock_exchange):
    """Test fetching order status from exchange."""
    # Arrange
    order = Order(
        symbol="BTC/USDT:USDT",
        type=OrderType.MARKET,
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
    )
    order.exchange_order_id = "exchange-order-123"
    executor.active_orders[order.id] = order

    # Act
    updated_order = await executor.fetch_order_status(
        order_id="exchange-order-123", symbol="BTC/USDT:USDT"
    )

    # Assert
    assert updated_order is not None
    assert updated_order.exchange_order_id == "exchange-order-123"
    mock_exchange.fetch_order.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_order_status_not_found(executor, mock_exchange):
    """Test fetching status for non-existent order."""
    # Act
    updated_order = await executor.fetch_order_status(
        order_id="non-existent", symbol="BTC/USDT:USDT"
    )

    # Assert
    assert updated_order is None


@pytest.mark.asyncio
async def test_fetch_order_status_error(executor, mock_exchange):
    """Test error handling in order status fetch."""
    # Arrange
    mock_exchange.fetch_order.side_effect = Exception("Network error")

    order = Order(
        symbol="BTC/USDT:USDT",
        type=OrderType.MARKET,
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
    )
    order.exchange_order_id = "exchange-order-123"
    executor.active_orders[order.id] = order

    # Act
    updated_order = await executor.fetch_order_status(
        order_id="exchange-order-123", symbol="BTC/USDT:USDT"
    )

    # Assert
    assert updated_order is None


# ============================================================================
# Helper Method Tests
# ============================================================================


def test_map_exchange_status(mock_position_service):
    """Test exchange status mapping."""
    with (
        patch(
            "workspace.features.trade_executor.executor_service.PositionService",
            return_value=mock_position_service,
        ),
        patch("workspace.features.trade_executor.executor_service.TradeHistoryService"),
        patch("workspace.features.trade_executor.executor_service.MetricsService"),
    ):
        executor = TradeExecutor(api_key="test", api_secret="test")

        assert executor._map_exchange_status("open") == OrderStatus.OPEN
        assert executor._map_exchange_status("closed") == OrderStatus.FILLED
        assert executor._map_exchange_status("canceled") == OrderStatus.CANCELED
        assert executor._map_exchange_status("expired") == OrderStatus.EXPIRED
        assert executor._map_exchange_status("unknown") == OrderStatus.OPEN  # Default


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_full_trade_lifecycle(executor, mock_exchange, mock_position_service):
    """Test complete trade lifecycle from signal to close."""
    # Arrange
    from workspace.features.trading_loop import TradingDecision

    buy_signal = MagicMock()
    buy_signal.symbol = "BTC/USDT:USDT"
    buy_signal.decision = TradingDecision.BUY
    buy_signal.confidence = Decimal("0.75")
    buy_signal.size_pct = Decimal("0.15")
    buy_signal.stop_loss_pct = Decimal("0.02")
    buy_signal.reasoning = "Bullish"

    # Act - Open position
    open_result = await executor.execute_signal(
        signal=buy_signal,
        account_balance_chf=Decimal("2626.96"),
    )

    # Assert open
    assert open_result.success is True

    # Act - Close position
    close_result = await executor.close_position(
        position_id="pos-123",
        reason="take_profit",
    )

    # Assert close
    assert close_result.success is True
