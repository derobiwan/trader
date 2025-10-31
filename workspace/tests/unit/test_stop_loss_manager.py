"""
Comprehensive Unit Tests for Stop-Loss Manager

Covers:
- 3-layer stop-loss protection system
- Layer 1: Exchange stop-loss orders
- Layer 2: Application-level monitoring
- Layer 3: Emergency liquidation
- Protection lifecycle (start, stop, trigger)
- Monitoring task management
- Error handling and recovery

Target Coverage: >80%
"""

import asyncio
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from workspace.features.trade_executor.executor_service import TradeExecutor
from workspace.features.trade_executor.models import (
    ExecutionResult,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    StopLossLayer,
)
from workspace.shared.database.models import Position, PositionSide, PositionStatus
from workspace.features.trade_executor.stop_loss_manager import StopLossManager


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_executor():
    """Create mock TradeExecutor"""
    executor = MagicMock(spec=TradeExecutor)
    executor.exchange = MagicMock()
    executor.exchange.fetch_ticker = AsyncMock(return_value={"last": 45000.0})
    executor.create_stop_market_order = AsyncMock(
        return_value=ExecutionResult(
            success=True,
            order=Order(
                exchange_order_id="stop-123",
                symbol="BTC/USDT:USDT",
                type=OrderType.STOP_MARKET,
                side=OrderSide.SELL,
                quantity=Decimal("0.001"),
                status=OrderStatus.OPEN,
            ),
        )
    )
    executor.close_position = AsyncMock(return_value=ExecutionResult(success=True))
    return executor


@pytest.fixture
def mock_position_service():
    """Create mock PositionService"""
    service = MagicMock()
    pos = Position(
        id=uuid4(),
        symbol="BTC/USDT:USDT",
        side=PositionSide.LONG,
        quantity=Decimal("0.001"),
        entry_price=Decimal("45000.0"),
        current_price=Decimal("45000.0"),
        leverage=10,
        stop_loss=Decimal("44000.0"),
        status=PositionStatus.OPEN,
    )
    # Override side and status to match production code expectations (lowercase)
    pos.side = "long"
    pos.status = "open"

    # Both methods return the same mutable position object
    # Tests can override either method and both will use the same underlying object
    def get_position_side_effect(position_id):
        # Return the current value of return_value if it's been set, otherwise return default
        return service.get_position_by_id.return_value

    service.get_position_by_id = AsyncMock(return_value=pos)
    service.get_position = AsyncMock(side_effect=get_position_side_effect)
    return service


@pytest.fixture
def stop_loss_manager(mock_executor, mock_position_service):
    """Create StopLossManager instance"""
    return StopLossManager(
        executor=mock_executor,
        position_service=mock_position_service,
        layer2_interval=0.1,  # Fast for testing
        layer3_interval=0.05,  # Fast for testing
        emergency_threshold=Decimal("0.15"),
    )


@pytest.fixture
def sample_position():
    """Sample position for testing"""
    pos = Position(
        id=uuid4(),
        symbol="BTC/USDT:USDT",
        side=PositionSide.LONG,
        quantity=Decimal("0.001"),
        entry_price=Decimal("45000.0"),
        current_price=Decimal("45000.0"),
        leverage=10,
        stop_loss=Decimal("44000.0"),
        status=PositionStatus.OPEN,
    )
    # Override side and status to match production code expectations (lowercase)
    pos.side = "long"
    pos.status = "open"
    return pos


# ============================================================================
# Initialization Tests
# ============================================================================


def test_stop_loss_manager_initialization():
    """Test StopLossManager initialization"""
    executor = MagicMock()
    position_service = MagicMock()
    manager = StopLossManager(executor=executor, position_service=position_service)

    assert manager.executor == executor
    assert manager.layer2_interval == 2.0  # Default
    assert manager.layer3_interval == 1.0  # Default
    assert manager.emergency_threshold == Decimal("0.15")
    assert len(manager.active_protections) == 0


def test_stop_loss_manager_custom_intervals():
    """Test custom monitoring intervals"""
    executor = MagicMock()
    position_service = MagicMock()
    manager = StopLossManager(
        executor=executor,
        position_service=position_service,
        layer2_interval=5.0,
        layer3_interval=2.0,
    )

    assert manager.layer2_interval == 5.0
    assert manager.layer3_interval == 2.0


# ============================================================================
# Layer 1 (Exchange Stop-Loss) Tests
# ============================================================================


@pytest.mark.asyncio
async def test_layer1_long_position_stop(
    stop_loss_manager, mock_executor, sample_position
):
    """Test Layer 1 stop-loss for LONG position"""
    result = await stop_loss_manager._place_layer1_stop(
        sample_position, Decimal("44000.0")
    )

    assert result.success is True
    mock_executor.create_stop_market_order.assert_called_once()
    call_args = mock_executor.create_stop_market_order.call_args
    assert call_args[1]["side"] == OrderSide.SELL  # Opposite of LONG
    assert call_args[1]["reduce_only"] is True


@pytest.mark.asyncio
async def test_layer1_short_position_stop(stop_loss_manager, mock_executor):
    """Test Layer 1 stop-loss for SHORT position"""
    short_position = Position(
        id=uuid4(),
        symbol="BTC/USDT:USDT",
        side=PositionSide.SHORT,
        quantity=Decimal("0.001"),
        entry_price=Decimal("45000.0"),
        leverage=10,
        stop_loss=Decimal("46000.0"),
        status=PositionStatus.OPEN,
    )
    # Override side to match production code expectations (lowercase)
    short_position.side = "short"

    result = await stop_loss_manager._place_layer1_stop(
        short_position, Decimal("46000.0")
    )

    assert result.success is True
    call_args = mock_executor.create_stop_market_order.call_args
    assert call_args[1]["side"] == OrderSide.BUY  # Opposite of SHORT


@pytest.mark.asyncio
async def test_layer1_placement_failure(
    stop_loss_manager, mock_executor, sample_position
):
    """Test Layer 1 stop-loss placement failure"""
    mock_executor.create_stop_market_order.return_value = ExecutionResult(
        success=False,
        error_code="API_ERROR",
        error_message="Exchange unavailable",
    )

    result = await stop_loss_manager._place_layer1_stop(
        sample_position, Decimal("44000.0")
    )

    assert result is None


@pytest.mark.asyncio
async def test_layer1_exception_handling(
    stop_loss_manager, mock_executor, sample_position
):
    """Test Layer 1 exception handling"""
    mock_executor.create_stop_market_order.side_effect = Exception("Unexpected error")

    result = await stop_loss_manager._place_layer1_stop(
        sample_position, Decimal("44000.0")
    )

    assert result is None


# ============================================================================
# Layer 2 (Application Monitoring) Tests
# ============================================================================


@pytest.mark.asyncio
async def test_layer2_monitoring_price_below_stop(
    stop_loss_manager, mock_executor, mock_position_service, sample_position
):
    """Test Layer 2 triggers when price crosses stop-loss"""
    # Setup position that's still open
    mock_position_service.get_position_by_id.return_value = sample_position

    # Price below stop-loss
    mock_executor.exchange.fetch_ticker.return_value = {"last": 43000.0}

    protection = MagicMock(
        position_id=str(sample_position.id),
        stop_price=Decimal("44000.0"),
        triggered_at=None,
    )

    # Start monitoring task
    task = asyncio.create_task(
        stop_loss_manager._monitor_layer2(
            sample_position, Decimal("44000.0"), protection
        )
    )

    # Wait for monitoring to trigger
    await asyncio.sleep(0.2)

    # Should have closed position
    mock_executor.close_position.assert_called_once()

    # Cleanup
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_layer2_monitoring_no_trigger(
    stop_loss_manager, mock_executor, mock_position_service, sample_position
):
    """Test Layer 2 doesn't trigger when price is above stop"""
    mock_position_service.get_position_by_id.return_value = sample_position

    # Price above stop-loss
    mock_executor.exchange.fetch_ticker.return_value = {"last": 45500.0}

    protection = MagicMock(
        position_id=str(sample_position.id),
        stop_price=Decimal("44000.0"),
    )

    # Start monitoring
    task = asyncio.create_task(
        stop_loss_manager._monitor_layer2(
            sample_position, Decimal("44000.0"), protection
        )
    )

    # Wait briefly
    await asyncio.sleep(0.2)

    # Should NOT have closed position
    mock_executor.close_position.assert_not_called()

    # Cleanup
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_layer2_monitoring_position_closed(
    stop_loss_manager, mock_position_service, sample_position
):
    """Test Layer 2 stops when position is closed"""
    # First return open, then closed
    closed_position = Position(
        id=sample_position.id,
        symbol=sample_position.symbol,
        side=PositionSide.LONG,  # Use enum first
        quantity=sample_position.quantity,
        entry_price=sample_position.entry_price,
        current_price=sample_position.current_price,
        leverage=sample_position.leverage,
        stop_loss=sample_position.stop_loss,
        status=PositionStatus.CLOSED,
    )
    # Override side and status to match sample_position (which has lowercase)
    closed_position.side = sample_position.side
    closed_position.status = "closed"

    # Mock position service to return open first, then closed
    call_count = [0]

    async def get_position_side_effect_closed(position_id):
        call_count[0] += 1
        if call_count[0] == 1:
            return sample_position
        else:
            return closed_position

    mock_position_service.get_position = AsyncMock(
        side_effect=get_position_side_effect_closed
    )

    protection = MagicMock(
        position_id=str(sample_position.id),
        stop_price=Decimal("44000.0"),
    )

    # Start monitoring
    task = asyncio.create_task(
        stop_loss_manager._monitor_layer2(
            sample_position, Decimal("44000.0"), protection
        )
    )

    # Wait for check
    await asyncio.sleep(0.25)

    # Task should complete naturally
    assert task.done()


@pytest.mark.asyncio
async def test_layer2_monitoring_short_position(
    stop_loss_manager, mock_executor, mock_position_service
):
    """Test Layer 2 for SHORT position"""
    short_position = Position(
        id=uuid4(),
        symbol="BTC/USDT:USDT",
        side=PositionSide.SHORT,
        quantity=Decimal("0.001"),
        entry_price=Decimal("45000.0"),
        leverage=10,
        stop_loss=Decimal("46000.0"),
        status=PositionStatus.OPEN,
    )
    # Override side and status to match production code expectations (lowercase)
    short_position.side = "short"
    short_position.status = "open"

    mock_position_service.get_position = AsyncMock(return_value=short_position)

    # Price above stop-loss (bad for short)
    mock_executor.exchange.fetch_ticker.return_value = {"last": 47000.0}

    protection = MagicMock(
        position_id=str(short_position.id),
        stop_price=Decimal("46000.0"),
    )

    # Start monitoring
    task = asyncio.create_task(
        stop_loss_manager._monitor_layer2(
            short_position, Decimal("46000.0"), protection
        )
    )

    # Wait for trigger
    await asyncio.sleep(0.2)

    # Should have closed position
    mock_executor.close_position.assert_called_once()

    # Cleanup
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_layer2_monitoring_fetch_price_error(
    stop_loss_manager, mock_executor, mock_position_service, sample_position
):
    """Test Layer 2 continues on price fetch error"""
    mock_position_service.get_position_by_id.return_value = sample_position

    # Price fetch fails
    mock_executor.exchange.fetch_ticker.side_effect = Exception("API Error")

    protection = MagicMock(
        position_id=str(sample_position.id),
        stop_price=Decimal("44000.0"),
    )

    # Start monitoring
    task = asyncio.create_task(
        stop_loss_manager._monitor_layer2(
            sample_position, Decimal("44000.0"), protection
        )
    )

    # Wait briefly
    await asyncio.sleep(0.2)

    # Should NOT have crashed, should NOT have closed position
    mock_executor.close_position.assert_not_called()

    # Cleanup
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


# ============================================================================
# Layer 3 (Emergency Liquidation) Tests
# ============================================================================


@pytest.mark.asyncio
async def test_layer3_emergency_trigger(
    stop_loss_manager, mock_executor, mock_position_service, sample_position
):
    """Test Layer 3 triggers on 15% loss"""
    mock_position_service.get_position_by_id.return_value = sample_position

    # Price causing >15% loss for LONG
    mock_executor.exchange.fetch_ticker.return_value = {"last": 38000.0}  # ~15.5% loss

    protection = MagicMock(
        position_id=str(sample_position.id),
        triggered_at=None,
    )

    # Start monitoring
    task = asyncio.create_task(
        stop_loss_manager._monitor_layer3(sample_position, protection)
    )

    # Wait for trigger
    await asyncio.sleep(0.2)

    # Should have emergency closed
    mock_executor.close_position.assert_called_once()
    call_args = mock_executor.close_position.call_args
    assert "emergency" in call_args[1]["reason"]

    # Cleanup
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_layer3_no_trigger_below_threshold(
    stop_loss_manager, mock_executor, mock_position_service, sample_position
):
    """Test Layer 3 doesn't trigger below emergency threshold"""
    mock_position_service.get_position_by_id.return_value = sample_position

    # Loss below 15% threshold
    mock_executor.exchange.fetch_ticker.return_value = {"last": 41000.0}  # ~8.9% loss

    protection = MagicMock(
        position_id=str(sample_position.id),
    )

    # Start monitoring
    task = asyncio.create_task(
        stop_loss_manager._monitor_layer3(sample_position, protection)
    )

    # Wait briefly
    await asyncio.sleep(0.2)

    # Should NOT have emergency closed
    mock_executor.close_position.assert_not_called()

    # Cleanup
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_layer3_short_position_emergency(
    stop_loss_manager, mock_executor, mock_position_service
):
    """Test Layer 3 for SHORT position"""
    short_position = Position(
        id=uuid4(),
        symbol="BTC/USDT:USDT",
        side=PositionSide.SHORT,
        quantity=Decimal("0.001"),
        entry_price=Decimal("45000.0"),
        leverage=10,
        status=PositionStatus.OPEN,
    )
    # Override side and status to match production code expectations (lowercase)
    short_position.side = "short"
    short_position.status = "open"

    mock_position_service.get_position = AsyncMock(return_value=short_position)

    # Price causing >15% loss for SHORT
    mock_executor.exchange.fetch_ticker.return_value = {"last": 52000.0}  # ~15.5% loss

    protection = MagicMock(
        position_id=str(short_position.id),
        triggered_at=None,
    )

    # Start monitoring
    task = asyncio.create_task(
        stop_loss_manager._monitor_layer3(short_position, protection)
    )

    # Wait for trigger
    await asyncio.sleep(0.2)

    # Should have emergency closed
    mock_executor.close_position.assert_called_once()

    # Cleanup
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_layer3_position_already_closed(
    stop_loss_manager, mock_position_service, sample_position
):
    """Test Layer 3 stops when position is closed"""
    # First return open, then closed
    closed_position = Position(
        id=sample_position.id,
        symbol=sample_position.symbol,
        side=PositionSide.LONG,  # Use enum first
        quantity=sample_position.quantity,
        entry_price=sample_position.entry_price,
        current_price=sample_position.current_price,
        leverage=sample_position.leverage,
        stop_loss=sample_position.stop_loss,
        status=PositionStatus.CLOSED,
    )
    # Override side and status to match sample_position (which has lowercase)
    closed_position.side = sample_position.side
    closed_position.status = "closed"

    # Mock position service to return open first, then closed
    call_count = [0]

    async def get_position_side_effect_closed(position_id):
        call_count[0] += 1
        if call_count[0] == 1:
            return sample_position
        else:
            return closed_position

    mock_position_service.get_position = AsyncMock(
        side_effect=get_position_side_effect_closed
    )

    protection = MagicMock(
        position_id=str(sample_position.id),
    )

    # Start monitoring
    task = asyncio.create_task(
        stop_loss_manager._monitor_layer3(sample_position, protection)
    )

    # Wait for check
    await asyncio.sleep(0.15)

    # Task should complete naturally
    assert task.done()


# ============================================================================
# Full Protection Lifecycle Tests
# ============================================================================


@pytest.mark.asyncio
async def test_start_protection_success(
    stop_loss_manager, mock_executor, mock_position_service
):
    """Test starting 3-layer protection"""
    with patch.object(stop_loss_manager, "_store_protection", new=AsyncMock()):
        protection = await stop_loss_manager.start_protection(
            position_id="pos-123",
            stop_price=Decimal("44000.0"),
        )

        assert protection is not None
        assert protection.layer1_order_id == "stop-123"
        assert protection.layer2_active is True
        assert protection.layer3_active is True

        # Should have started monitoring tasks
        assert "pos-123_layer2" in stop_loss_manager.monitoring_tasks
        assert "pos-123_layer3" in stop_loss_manager.monitoring_tasks

        # Cleanup
        await stop_loss_manager.stop_protection("pos-123")


@pytest.mark.asyncio
async def test_start_protection_position_not_found(
    stop_loss_manager, mock_position_service
):
    """Test starting protection for non-existent position"""
    mock_position_service.get_position_by_id.return_value = None

    with pytest.raises(ValueError, match="Position .* not found"):
        await stop_loss_manager.start_protection(
            position_id="invalid-id",
            stop_price=Decimal("44000.0"),
        )


@pytest.mark.asyncio
async def test_start_protection_layer1_failure(
    stop_loss_manager, mock_executor, mock_position_service
):
    """Test protection continues even if Layer 1 fails"""
    mock_executor.create_stop_market_order.return_value = ExecutionResult(
        success=False,
        error_message="API Error",
    )

    with patch.object(stop_loss_manager, "_store_protection", new=AsyncMock()):
        protection = await stop_loss_manager.start_protection(
            position_id="pos-123",
            stop_price=Decimal("44000.0"),
        )

        # Layer 2 and 3 should still be active
        assert protection.layer2_active is True
        assert protection.layer3_active is True

        # Cleanup
        await stop_loss_manager.stop_protection("pos-123")


@pytest.mark.asyncio
async def test_stop_protection(stop_loss_manager):
    """Test stopping all protection layers"""
    # Create fake monitoring tasks
    task1 = asyncio.create_task(asyncio.sleep(10))
    task2 = asyncio.create_task(asyncio.sleep(10))

    stop_loss_manager.monitoring_tasks["pos-123_layer2"] = task1
    stop_loss_manager.monitoring_tasks["pos-123_layer3"] = task2
    stop_loss_manager.active_protections["pos-123"] = MagicMock()

    await stop_loss_manager.stop_protection("pos-123")

    # Tasks should be cancelled
    assert task1.cancelled()
    assert task2.cancelled()

    # Should be removed from tracking
    assert "pos-123_layer2" not in stop_loss_manager.monitoring_tasks
    assert "pos-123_layer3" not in stop_loss_manager.monitoring_tasks
    assert "pos-123" not in stop_loss_manager.active_protections


# ============================================================================
# Alert and Notification Tests
# ============================================================================


@pytest.mark.asyncio
async def test_send_emergency_alert(stop_loss_manager):
    """Test emergency alert sending"""
    # Should not raise exception
    await stop_loss_manager._send_emergency_alert(
        position_id="pos-123",
        loss_pct=Decimal("0.18"),
        current_price=Decimal("37000.0"),
    )


# ============================================================================
# Database Storage Tests
# ============================================================================


@pytest.mark.asyncio
async def test_store_protection(stop_loss_manager):
    """Test storing protection in database"""
    from workspace.shared.database.connection import DatabasePool

    protection = MagicMock(
        position_id="pos-123",
        layer1_order_id="stop-123",
        layer1_status=OrderStatus.OPEN,
        layer2_active=True,
        layer3_active=True,
        stop_price=Decimal("44000.0"),
        created_at=datetime.utcnow(),
        triggered_at=None,
        triggered_layer=None,
        metadata={},
    )

    mock_conn = MagicMock()
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=None)
    mock_conn.execute = AsyncMock()

    # Create a mock context manager for get_connection
    async def mock_get_connection():
        return mock_conn

    with patch.object(
        DatabasePool, "get_connection", new=mock_get_connection, create=True
    ):
        # Should not raise exception
        await stop_loss_manager._store_protection(protection)


@pytest.mark.asyncio
async def test_update_protection(stop_loss_manager):
    """Test updating protection in database"""
    from workspace.shared.database.connection import DatabasePool

    protection = MagicMock(
        position_id="pos-123",
        triggered_at=datetime.utcnow(),
        triggered_layer=StopLossLayer.APPLICATION,
        metadata={"reason": "price_crossed_stop"},
    )

    mock_conn = MagicMock()
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=None)
    mock_conn.execute = AsyncMock()

    # Create a mock context manager for get_connection
    async def mock_get_connection():
        return mock_conn

    with patch.object(
        DatabasePool, "get_connection", new=mock_get_connection, create=True
    ):
        # Should not raise exception
        await stop_loss_manager._update_protection(protection)
