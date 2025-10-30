"""
Trade Executor Tests

Comprehensive tests for order execution, stop-loss protection,
and position reconciliation.

Author: Trade Executor Implementation Team
Date: 2025-10-27
"""

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch

import pytest

from workspace.features.trade_executor.executor_service import TradeExecutor
from workspace.features.trade_executor.models import (
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    ReconciliationResult,
    StopLossProtection,
    TimeInForce,
)
from workspace.features.trade_executor.reconciliation import ReconciliationService
from workspace.features.trade_executor.stop_loss_manager import StopLossManager

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_exchange():
    """Mock ccxt exchange"""
    exchange = Mock()
    exchange.fetch_ticker = AsyncMock(return_value={"last": 90000})
    exchange.fetch_order = AsyncMock(
        return_value={
            "id": "order123",
            "status": "closed",
            "filled": 0.001,
            "average": 90000,
            "fee": {"cost": 0.5},
        }
    )
    exchange.fetch_positions = AsyncMock(return_value=[])
    exchange.create_order = AsyncMock(
        return_value={
            "id": "order123",
            "status": "closed",
            "filled": 0.001,
            "remaining": 0,
            "average": 90000,
            "fee": {"cost": 0.5},
        }
    )
    exchange.load_markets = AsyncMock()
    exchange.fetch_balance = AsyncMock(return_value={"USDT": {"free": 10000}})
    exchange.markets = {"BTC/USDT:USDT": {}}
    return exchange


@pytest.fixture
def mock_position_service():
    """Mock Position Manager service"""
    service = Mock()

    # Mock position object
    mock_position = Mock()
    mock_position.id = "pos123"
    mock_position.symbol = "BTC/USDT:USDT"
    mock_position.side = "long"
    mock_position.quantity = Decimal("0.001")
    mock_position.entry_price = Decimal("90000")
    mock_position.current_price = Decimal("90000")
    mock_position.leverage = 10
    mock_position.stop_loss = Decimal("89000")
    mock_position.status = "open"

    service.create_position = AsyncMock(return_value=mock_position)
    service.get_position = AsyncMock(return_value=mock_position)
    service.close_position = AsyncMock()
    service.get_active_positions = AsyncMock(return_value=[mock_position])
    service.update_position_price = AsyncMock()

    return service


@pytest.fixture
def mock_db_pool():
    """Mock database connection pool"""
    with patch(
        "workspace.features.trade_executor.executor_service.DatabasePool"
    ) as mock_pool:
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.fetchrow = AsyncMock()
        mock_pool.get_connection.return_value.__aenter__.return_value = mock_conn
        yield mock_pool


@pytest.fixture
async def executor(mock_exchange, mock_db_pool):
    """Create TradeExecutor instance with mocks"""
    with patch("workspace.features.trade_executor.executor_service.ccxt") as mock_ccxt:
        mock_ccxt.bybit.return_value = mock_exchange

        executor = TradeExecutor(
            api_key="test_key", api_secret="test_secret", testnet=True
        )
        executor.exchange = mock_exchange

        yield executor

        await executor.close()


# ============================================================================
# Model Tests
# ============================================================================


def test_order_model_creation():
    """Test Order model creation with validation"""
    order = Order(
        symbol="BTC/USDT:USDT",
        type=OrderType.MARKET,
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
    )

    assert order.symbol == "BTC/USDT:USDT"
    assert order.type == OrderType.MARKET
    assert order.side == OrderSide.BUY
    assert order.quantity == Decimal("0.001")
    assert order.status == OrderStatus.PENDING
    assert order.filled_quantity == Decimal("0")
    assert order.remaining_quantity == Decimal("0.001")


def test_order_fill_percentage():
    """Test order fill percentage calculation"""
    order = Order(
        symbol="BTC/USDT:USDT",
        type=OrderType.LIMIT,
        side=OrderSide.BUY,
        quantity=Decimal("1.0"),
        price=Decimal("90000"),
    )

    # No fill
    assert order.fill_percentage == Decimal("0")

    # Partial fill (50%)
    order.filled_quantity = Decimal("0.5")
    assert order.fill_percentage == Decimal("50")

    # Full fill
    order.filled_quantity = Decimal("1.0")
    assert order.fill_percentage == Decimal("100")
    assert order.is_fully_filled


def test_reconciliation_result_discrepancy():
    """Test ReconciliationResult discrepancy calculation"""
    result = ReconciliationResult(
        position_id="pos123",
        system_quantity=Decimal("1.0"),
        exchange_quantity=Decimal("0.998"),
        discrepancy=Decimal("0"),  # Will be calculated
    )

    # Discrepancy should be auto-calculated
    assert result.discrepancy == Decimal("0.002")
    assert result.needs_correction is False  # Below threshold


# ============================================================================
# Trade Executor Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_market_order_success(executor, mock_exchange):
    """Test successful market order creation"""
    result = await executor.create_market_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
        reduce_only=False,
    )

    assert result.success is True
    assert result.order is not None
    assert result.order.type == OrderType.MARKET
    assert result.order.side == OrderSide.BUY
    assert result.order.exchange_order_id == "order123"
    assert result.order.status == OrderStatus.FILLED
    assert result.latency_ms is not None


@pytest.mark.asyncio
async def test_create_market_order_invalid_symbol(executor):
    """Test market order with invalid symbol format"""
    result = await executor.create_market_order(
        symbol="BTC/USDT",  # Missing :USDT
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
    )

    assert result.success is False
    assert result.error_code == "INVALID_SYMBOL"
    assert "BTC/USDT:USDT" in result.error_message


@pytest.mark.asyncio
async def test_create_limit_order_success(executor, mock_exchange):
    """Test successful limit order creation"""
    result = await executor.create_limit_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
        price=Decimal("89000"),
        time_in_force=TimeInForce.GTC,
    )

    assert result.success is True
    assert result.order.type == OrderType.LIMIT
    assert result.order.price == Decimal("89000")


@pytest.mark.asyncio
async def test_create_stop_market_order(executor, mock_exchange):
    """Test stop-market order creation (for stop-loss)"""
    result = await executor.create_stop_market_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.SELL,
        quantity=Decimal("0.001"),
        stop_price=Decimal("89000"),
        reduce_only=True,
    )

    assert result.success is True
    assert result.order.type == OrderType.STOP_MARKET
    assert result.order.stop_price == Decimal("89000")
    assert result.order.reduce_only is True


@pytest.mark.asyncio
async def test_open_position(executor, mock_exchange, mock_position_service):
    """Test opening a position"""
    executor.position_service = mock_position_service

    result = await executor.open_position(
        symbol="BTC/USDT:USDT",
        side="long",
        quantity=Decimal("0.001"),
        leverage=10,
        stop_loss=Decimal("89000"),
    )

    assert result.success is True
    mock_position_service.create_position.assert_called_once()


@pytest.mark.asyncio
async def test_close_position(executor, mock_exchange, mock_position_service):
    """Test closing a position with reduceOnly=True"""
    executor.position_service = mock_position_service

    result = await executor.close_position(
        position_id="pos123",
        reason="manual_close",
    )

    assert result.success is True
    assert result.order.reduce_only is True  # CRITICAL: Must be True
    mock_position_service.close_position.assert_called_once()


@pytest.mark.asyncio
async def test_order_status_tracking(executor, mock_exchange):
    """Test order status tracking and updates"""
    # Create order
    result = await executor.create_market_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
    )

    order_id = result.order.exchange_order_id

    # Fetch status
    updated_order = await executor.fetch_order_status(
        order_id=order_id,
        symbol="BTC/USDT:USDT",
    )

    assert updated_order is not None
    assert updated_order.exchange_order_id == order_id


@pytest.mark.asyncio
async def test_retry_on_rate_limit(executor, mock_exchange):
    """Test retry logic on rate limit exceeded"""
    # First call fails with rate limit, second succeeds
    mock_exchange.create_order.side_effect = [
        Exception("RateLimitExceeded"),
        {
            "id": "order123",
            "status": "closed",
            "filled": 0.001,
            "average": 90000,
            "fee": {"cost": 0.5},
        },
    ]

    await executor.create_market_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
    )

    # Should succeed after retry
    assert mock_exchange.create_order.call_count == 2


# ============================================================================
# Stop-Loss Manager Tests
# ============================================================================


@pytest.mark.asyncio
async def test_start_stop_loss_protection(executor, mock_position_service):
    """Test starting 3-layer stop-loss protection"""
    stop_loss_manager = StopLossManager(
        executor=executor,
        position_service=mock_position_service,
    )

    with patch.object(stop_loss_manager, "_store_protection", new_callable=AsyncMock):
        protection = await stop_loss_manager.start_protection(
            position_id="pos123",
            stop_price=Decimal("89000"),
        )

    assert protection.position_id == "pos123"
    assert protection.stop_price == Decimal("89000")
    assert protection.layer1_order_id is not None
    assert protection.layer2_active is True
    assert protection.layer3_active is True


@pytest.mark.asyncio
async def test_layer2_monitoring(executor, mock_position_service):
    """Test Layer 2 application-level monitoring"""
    stop_loss_manager = StopLossManager(
        executor=executor,
        position_service=mock_position_service,
        layer2_interval=0.1,  # Fast for testing
    )

    # Mock position
    mock_position = mock_position_service.get_position.return_value
    mock_position.side = "long"
    mock_position.status = "open"

    # Mock protection
    protection = StopLossProtection(
        position_id="pos123",
        stop_price=Decimal("89000"),
    )

    # Mock price drops below stop
    executor.exchange.fetch_ticker = AsyncMock(return_value={"last": 88000})

    # Start monitoring (will trigger immediately)
    with patch.object(stop_loss_manager, "_update_protection", new_callable=AsyncMock):
        task = asyncio.create_task(
            stop_loss_manager._monitor_layer2(
                mock_position, Decimal("89000"), protection
            )
        )

        # Wait a bit for monitoring to trigger
        await asyncio.sleep(0.3)

        # Cancel task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    # Should have triggered close
    executor.close_position.assert_called_once()


@pytest.mark.asyncio
async def test_layer3_emergency(executor, mock_position_service):
    """Test Layer 3 emergency liquidation"""
    stop_loss_manager = StopLossManager(
        executor=executor,
        position_service=mock_position_service,
        layer3_interval=0.1,  # Fast for testing
        emergency_threshold=Decimal("0.15"),  # 15% loss
    )

    # Mock position with 20% loss
    mock_position = mock_position_service.get_position.return_value
    mock_position.side = "long"
    mock_position.entry_price = Decimal("90000")
    mock_position.status = "open"

    # Mock price at 20% loss
    executor.exchange.fetch_ticker = AsyncMock(return_value={"last": 72000})

    protection = StopLossProtection(
        position_id="pos123",
        stop_price=Decimal("89000"),
    )

    # Start monitoring
    with patch.object(
        stop_loss_manager, "_send_emergency_alert", new_callable=AsyncMock
    ):
        with patch.object(
            stop_loss_manager, "_update_protection", new_callable=AsyncMock
        ):
            task = asyncio.create_task(
                stop_loss_manager._monitor_layer3(mock_position, protection)
            )

            await asyncio.sleep(0.3)

            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    # Should have triggered emergency close
    executor.close_position.assert_called_once()


@pytest.mark.asyncio
async def test_stop_protection(executor, mock_position_service):
    """Test stopping all protection layers"""
    stop_loss_manager = StopLossManager(
        executor=executor,
        position_service=mock_position_service,
    )

    # Create mock tasks
    stop_loss_manager.monitoring_tasks["pos123_layer2"] = AsyncMock()
    stop_loss_manager.monitoring_tasks["pos123_layer3"] = AsyncMock()
    stop_loss_manager.active_protections["pos123"] = Mock()

    # Stop protection
    await stop_loss_manager.stop_protection("pos123")

    # Tasks should be removed
    assert "pos123_layer2" not in stop_loss_manager.monitoring_tasks
    assert "pos123_layer3" not in stop_loss_manager.monitoring_tasks
    assert "pos123" not in stop_loss_manager.active_protections


# ============================================================================
# Reconciliation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_reconcile_position_match(mock_exchange, mock_position_service):
    """Test position reconciliation when quantities match"""
    reconciliation_service = ReconciliationService(
        exchange=mock_exchange,
        position_service=mock_position_service,
    )

    # Mock exchange position matches system position
    mock_exchange.fetch_positions = AsyncMock(
        return_value=[
            {
                "symbol": "BTC/USDT:USDT",
                "contracts": 0.001,
                "side": "long",
            }
        ]
    )

    with patch.object(
        reconciliation_service, "_store_reconciliation_result", new_callable=AsyncMock
    ):
        results = await reconciliation_service.reconcile_all_positions()

    assert len(results) > 0
    assert not results[0].needs_correction


@pytest.mark.asyncio
async def test_reconcile_position_discrepancy(mock_exchange, mock_position_service):
    """Test reconciliation with quantity discrepancy"""
    reconciliation_service = ReconciliationService(
        exchange=mock_exchange,
        position_service=mock_position_service,
        discrepancy_threshold=Decimal("0.00001"),
    )

    # Mock exchange position differs from system
    mock_exchange.fetch_positions = AsyncMock(
        return_value=[
            {
                "symbol": "BTC/USDT:USDT",
                "contracts": 0.0008,  # Differs from 0.001 in system
                "side": "long",
            }
        ]
    )

    with patch.object(
        reconciliation_service, "_update_position_quantity", new_callable=AsyncMock
    ):
        with patch.object(
            reconciliation_service,
            "_store_reconciliation_result",
            new_callable=AsyncMock,
        ):
            results = await reconciliation_service.reconcile_all_positions()

    assert len(results) > 0
    result = results[0]
    assert result.needs_correction
    assert result.discrepancy == Decimal("0.0002")
    assert len(result.corrections_applied) > 0


@pytest.mark.asyncio
async def test_reconcile_position_not_on_exchange(mock_exchange, mock_position_service):
    """Test reconciliation when position exists in system but not on exchange"""
    reconciliation_service = ReconciliationService(
        exchange=mock_exchange,
        position_service=mock_position_service,
    )

    # Mock no positions on exchange
    mock_exchange.fetch_positions = AsyncMock(return_value=[])

    with patch.object(
        reconciliation_service, "_store_reconciliation_result", new_callable=AsyncMock
    ):
        results = await reconciliation_service.reconcile_all_positions()

    assert len(results) > 0
    result = results[0]
    assert result.needs_correction
    assert result.exchange_quantity == Decimal("0")

    # Should have closed position in system
    mock_position_service.close_position.assert_called_once()


@pytest.mark.asyncio
async def test_periodic_reconciliation(mock_exchange, mock_position_service):
    """Test periodic reconciliation loop"""
    reconciliation_service = ReconciliationService(
        exchange=mock_exchange,
        position_service=mock_position_service,
        periodic_interval=0.2,  # Fast for testing
    )

    mock_exchange.fetch_positions = AsyncMock(
        return_value=[
            {
                "symbol": "BTC/USDT:USDT",
                "contracts": 0.001,
                "side": "long",
            }
        ]
    )

    # Start periodic reconciliation
    await reconciliation_service.start_periodic_reconciliation()

    # Let it run a bit
    await asyncio.sleep(0.5)

    # Stop reconciliation
    await reconciliation_service.stop_periodic_reconciliation()

    # Should have run at least once
    assert mock_exchange.fetch_positions.call_count >= 2


@pytest.mark.asyncio
async def test_position_snapshot_creation(mock_exchange, mock_position_service):
    """Test position snapshot creation for audit trail"""
    reconciliation_service = ReconciliationService(
        exchange=mock_exchange,
        position_service=mock_position_service,
    )

    with patch.object(
        reconciliation_service, "_store_position_snapshot", new_callable=AsyncMock
    ):
        snapshot = await reconciliation_service.create_position_snapshot("pos123")

    assert snapshot is not None
    assert snapshot.position_id == "pos123"
    assert snapshot.symbol == "BTC/USDT:USDT"
    assert snapshot.quantity == Decimal("0.001")


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_full_position_lifecycle(executor, mock_exchange, mock_position_service):
    """Test complete position lifecycle: open -> monitor -> close"""
    executor.position_service = mock_position_service

    # 1. Open position
    open_result = await executor.open_position(
        symbol="BTC/USDT:USDT",
        side="long",
        quantity=Decimal("0.001"),
        leverage=10,
        stop_loss=Decimal("89000"),
    )
    assert open_result.success is True

    # 2. Start stop-loss protection
    stop_loss_manager = StopLossManager(executor=executor)
    with patch.object(stop_loss_manager, "_store_protection", new_callable=AsyncMock):
        protection = await stop_loss_manager.start_protection(
            position_id="pos123",
            stop_price=Decimal("89000"),
        )
    assert protection.layer1_order_id is not None

    # 3. Close position
    close_result = await executor.close_position(
        position_id="pos123",
        reason="take_profit",
    )
    assert close_result.success is True

    # 4. Stop protection
    await stop_loss_manager.stop_protection("pos123")


# ============================================================================
# Performance Tests
# ============================================================================


@pytest.mark.asyncio
async def test_order_execution_latency(executor, mock_exchange):
    """Test order execution latency < 100ms"""
    result = await executor.create_market_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
    )

    assert result.latency_ms < Decimal("100")  # Should be fast with mocks


@pytest.mark.asyncio
async def test_concurrent_order_execution(executor, mock_exchange):
    """Test concurrent order execution"""
    # Execute 3 orders concurrently
    tasks = [
        executor.create_market_order(
            symbol="BTC/USDT:USDT",
            side=OrderSide.BUY,
            quantity=Decimal("0.001"),
        )
        for _ in range(3)
    ]

    results = await asyncio.gather(*tasks)

    # All should succeed
    assert all(r.success for r in results)
    assert len(results) == 3


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.asyncio
async def test_order_execution_network_error(executor, mock_exchange):
    """Test handling of network errors during order execution"""
    mock_exchange.create_order.side_effect = Exception(
        "NetworkError: Connection timeout"
    )

    result = await executor.create_market_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
    )

    assert result.success is False
    assert result.error_code in [
        "NETWORK_ERROR",
        "UNKNOWN_ERROR",
        "MAX_RETRIES_EXCEEDED",
    ]


@pytest.mark.asyncio
async def test_insufficient_funds_error(executor, mock_exchange):
    """Test handling of insufficient funds error"""
    mock_exchange.create_order.side_effect = Exception("InsufficientFunds")

    result = await executor.create_market_order(
        symbol="BTC/USDT:USDT",
        side=OrderSide.BUY,
        quantity=Decimal("100"),  # Large order
    )

    assert result.success is False


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
