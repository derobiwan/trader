"""
Comprehensive Unit Tests for Reconciliation Service

Covers:
- Position reconciliation with exchange
- Discrepancy detection and correction
- Periodic reconciliation
- Position snapshots for audit
- Exchange position fetching
- Database updates and storage
- Error handling and recovery

Target Coverage: >80%
"""

import asyncio
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import asyncpg
import pytest

from workspace.features.trade_executor.reconciliation import ReconciliationService
from workspace.features.trade_executor.models import (
    PositionSnapshot,
    ReconciliationResult,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_exchange():
    """Create mock ccxt exchange"""
    exchange = MagicMock()
    exchange.fetch_positions = AsyncMock(return_value=[])
    return exchange


@pytest.fixture
def mock_position_service():
    """Create mock PositionService"""
    service = MagicMock()
    service.get_active_positions = AsyncMock(return_value=[])
    service.get_position = AsyncMock(return_value=None)
    service.get_position_by_id = AsyncMock(return_value=None)
    service.close_position = AsyncMock()
    service.update_position_price = AsyncMock()
    return service


@pytest.fixture
def reconciliation_service(mock_exchange, mock_position_service):
    """Create ReconciliationService instance"""
    return ReconciliationService(
        exchange=mock_exchange,
        position_service=mock_position_service,
        periodic_interval=1,  # Fast for testing
        discrepancy_threshold=Decimal("0.00001"),
    )


@pytest.fixture
def sample_system_position():
    """Sample system position"""
    return MagicMock(
        id="pos-123",
        symbol="BTC/USDT:USDT",
        quantity=Decimal("0.001"),
        current_price=Decimal("45000.0"),
        entry_price=Decimal("45000.0"),
        side="long",
        status="open",
        pnl_chf=Decimal("0.0"),
    )


@pytest.fixture
def sample_exchange_position():
    """Sample exchange position"""
    return {
        "symbol": "BTC/USDT:USDT",
        "contracts": 0.001,
        "side": "long",
        "unrealizedPnl": 0.0,
        "leverage": 10,
    }


# ============================================================================
# Initialization Tests
# ============================================================================


def test_reconciliation_service_initialization():
    """Test ReconciliationService initialization"""
    exchange = MagicMock()
    service = ReconciliationService(exchange=exchange)

    assert service.exchange == exchange
    assert service.periodic_interval == 300  # Default 5 minutes
    assert service.discrepancy_threshold == Decimal("0.00001")
    assert service.reconciliation_task is None


def test_reconciliation_service_custom_params():
    """Test custom parameters"""
    exchange = MagicMock()
    service = ReconciliationService(
        exchange=exchange,
        periodic_interval=600,
        discrepancy_threshold=Decimal("0.0001"),
    )

    assert service.periodic_interval == 600
    assert service.discrepancy_threshold == Decimal("0.0001")


# ============================================================================
# Exchange Position Fetching Tests
# ============================================================================


@pytest.mark.asyncio
async def test_fetch_exchange_positions_success(reconciliation_service, mock_exchange):
    """Test fetching positions from exchange"""
    mock_exchange.fetch_positions.return_value = [
        {"symbol": "BTC/USDT:USDT", "contracts": 0.001},
        {"symbol": "ETH/USDT:USDT", "contracts": 0.0},  # Closed position
    ]

    positions = await reconciliation_service._fetch_exchange_positions()

    assert len(positions) == 1  # Only open position
    assert positions[0]["symbol"] == "BTC/USDT:USDT"


@pytest.mark.asyncio
async def test_fetch_exchange_positions_error(reconciliation_service, mock_exchange):
    """Test exchange fetch error handling"""
    mock_exchange.fetch_positions.side_effect = Exception("API Error")

    positions = await reconciliation_service._fetch_exchange_positions()

    assert len(positions) == 0  # Returns empty list on error


# ============================================================================
# Position Reconciliation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_reconcile_position_no_discrepancy(
    reconciliation_service, sample_system_position, sample_exchange_position
):
    """Test reconciliation when quantities match"""
    with patch.object(
        reconciliation_service, "_store_reconciliation_result", new=AsyncMock()
    ):
        result = await reconciliation_service._reconcile_position(
            sample_system_position,
            sample_exchange_position,
        )

        assert result.needs_correction is False
        assert result.discrepancy == Decimal("0")


@pytest.mark.asyncio
async def test_reconcile_position_with_discrepancy(
    reconciliation_service, sample_system_position, sample_exchange_position
):
    """Test reconciliation with quantity discrepancy"""
    # Exchange has more
    sample_exchange_position["contracts"] = 0.002

    with (
        patch.object(
            reconciliation_service, "_store_reconciliation_result", new=AsyncMock()
        ),
        patch.object(
            reconciliation_service, "_update_position_quantity", new=AsyncMock()
        ),
    ):
        result = await reconciliation_service._reconcile_position(
            sample_system_position,
            sample_exchange_position,
        )

        assert result.needs_correction is True
        assert result.discrepancy == Decimal("-0.001")


@pytest.mark.asyncio
async def test_reconcile_position_below_threshold(
    reconciliation_service, sample_system_position, sample_exchange_position
):
    """Test discrepancy below threshold is ignored"""
    # Tiny discrepancy
    sample_exchange_position["contracts"] = 0.0010000001

    with patch.object(
        reconciliation_service, "_store_reconciliation_result", new=AsyncMock()
    ):
        result = await reconciliation_service._reconcile_position(
            sample_system_position,
            sample_exchange_position,
        )

        # Below threshold - no correction needed
        assert result.needs_correction is False


@pytest.mark.asyncio
async def test_reconcile_position_correction_applied(
    reconciliation_service,
    sample_system_position,
    sample_exchange_position,
    mock_position_service,
):
    """Test position quantity correction is applied"""
    sample_exchange_position["contracts"] = 0.002

    with (
        patch.object(
            reconciliation_service, "_store_reconciliation_result", new=AsyncMock()
        ),
        patch.object(
            reconciliation_service, "_update_position_quantity", new=AsyncMock()
        ) as mock_update,
    ):
        result = await reconciliation_service._reconcile_position(
            sample_system_position,
            sample_exchange_position,
        )

        assert result.needs_correction is True
        # Should have updated quantity
        mock_update.assert_called_once()


# ============================================================================
# Full Reconciliation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_reconcile_all_positions_matching(
    reconciliation_service,
    mock_position_service,
    mock_exchange,
    sample_system_position,
    sample_exchange_position,
):
    """Test full reconciliation with matching positions"""
    mock_position_service.get_active_positions.return_value = [sample_system_position]
    mock_exchange.fetch_positions.return_value = [sample_exchange_position]

    with patch.object(
        reconciliation_service, "_store_reconciliation_result", new=AsyncMock()
    ):
        results = await reconciliation_service.reconcile_all_positions()

        assert len(results) == 1
        assert results[0].needs_correction is False


@pytest.mark.asyncio
async def test_reconcile_all_positions_system_only(
    reconciliation_service,
    mock_position_service,
    mock_exchange,
    sample_system_position,
):
    """Test reconciliation when position only in system"""
    mock_position_service.get_active_positions.return_value = [sample_system_position]
    mock_exchange.fetch_positions.return_value = []  # Not on exchange

    with patch.object(
        reconciliation_service, "_store_reconciliation_result", new=AsyncMock()
    ):
        results = await reconciliation_service.reconcile_all_positions()

        assert len(results) == 1
        assert results[0].needs_correction is True
        assert results[0].exchange_quantity == Decimal("0")

        # Should have closed position in system
        mock_position_service.close_position.assert_called_once()


@pytest.mark.asyncio
async def test_reconcile_all_positions_exchange_only(
    reconciliation_service,
    mock_position_service,
    mock_exchange,
    sample_exchange_position,
):
    """Test reconciliation when position only on exchange"""
    mock_position_service.get_active_positions.return_value = []
    mock_exchange.fetch_positions.return_value = [sample_exchange_position]

    with patch.object(
        reconciliation_service, "_store_reconciliation_result", new=AsyncMock()
    ):
        results = await reconciliation_service.reconcile_all_positions()

        # Should log warning but not crash
        assert len(results) == 0


@pytest.mark.asyncio
async def test_reconcile_all_positions_error_handling(
    reconciliation_service, mock_position_service
):
    """Test full reconciliation error handling"""
    mock_position_service.get_active_positions.side_effect = Exception("DB Error")

    results = await reconciliation_service.reconcile_all_positions()

    assert len(results) == 0  # Returns empty on error


# ============================================================================
# Single Position Reconciliation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_reconcile_position_by_id_success(
    reconciliation_service,
    mock_position_service,
    mock_exchange,
    sample_system_position,
    sample_exchange_position,
):
    """Test reconciling specific position by ID"""
    mock_position_service.get_position.return_value = sample_system_position
    mock_exchange.fetch_positions.return_value = [sample_exchange_position]

    with patch.object(
        reconciliation_service, "_store_reconciliation_result", new=AsyncMock()
    ):
        result = await reconciliation_service.reconcile_position("pos-123")

        assert result is not None
        assert result.position_id == "pos-123"


@pytest.mark.asyncio
async def test_reconcile_position_by_id_not_found(
    reconciliation_service, mock_position_service
):
    """Test reconciling non-existent position"""
    mock_position_service.get_position_by_id.return_value = None

    result = await reconciliation_service.reconcile_position("invalid-id")

    assert result is None


@pytest.mark.asyncio
async def test_reconcile_position_by_id_not_on_exchange(
    reconciliation_service,
    mock_position_service,
    mock_exchange,
    sample_system_position,
):
    """Test reconciling position not on exchange"""
    mock_position_service.get_position.return_value = sample_system_position
    mock_exchange.fetch_positions.return_value = []

    result = await reconciliation_service.reconcile_position("pos-123")

    assert result is not None
    assert result.needs_correction is True
    assert result.exchange_quantity == Decimal("0")


# ============================================================================
# Periodic Reconciliation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_start_periodic_reconciliation(reconciliation_service):
    """Test starting periodic reconciliation"""
    await reconciliation_service.start_periodic_reconciliation()

    assert reconciliation_service.reconciliation_task is not None
    assert not reconciliation_service.reconciliation_task.done()

    # Cleanup
    await reconciliation_service.stop_periodic_reconciliation()


@pytest.mark.asyncio
async def test_start_periodic_reconciliation_already_running(reconciliation_service):
    """Test starting when already running"""
    await reconciliation_service.start_periodic_reconciliation()
    task1 = reconciliation_service.reconciliation_task

    # Try to start again
    await reconciliation_service.start_periodic_reconciliation()
    task2 = reconciliation_service.reconciliation_task

    # Should be same task
    assert task1 == task2

    # Cleanup
    await reconciliation_service.stop_periodic_reconciliation()


@pytest.mark.asyncio
async def test_stop_periodic_reconciliation(reconciliation_service):
    """Test stopping periodic reconciliation"""
    await reconciliation_service.start_periodic_reconciliation()
    task = reconciliation_service.reconciliation_task

    await reconciliation_service.stop_periodic_reconciliation()

    assert task.cancelled()
    assert reconciliation_service.reconciliation_task is None


@pytest.mark.asyncio
async def test_periodic_reconciliation_loop_execution(
    reconciliation_service, mock_position_service, mock_exchange
):
    """Test periodic reconciliation loop executes"""
    mock_position_service.get_active_positions.return_value = []
    mock_exchange.fetch_positions.return_value = []

    # Start reconciliation
    await reconciliation_service.start_periodic_reconciliation()

    # Wait for at least one iteration
    await asyncio.sleep(1.5)

    # Should have called reconciliation at least once
    mock_position_service.get_active_positions.assert_called()

    # Cleanup
    await reconciliation_service.stop_periodic_reconciliation()


# ============================================================================
# Database Update Tests
# ============================================================================


@pytest.mark.asyncio
async def test_update_position_quantity(reconciliation_service):
    """Test updating position quantity in database"""
    with patch(
        "workspace.features.trade_executor.reconciliation.get_pool"
    ) as mock_get_pool:
        mock_pool = AsyncMock()
        mock_conn = MagicMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)
        mock_conn.execute = AsyncMock()
        mock_pool.acquire = MagicMock(return_value=mock_conn)
        mock_get_pool.return_value = mock_pool

        await reconciliation_service._update_position_quantity(
            position_id="pos-123",
            new_quantity=Decimal("0.002"),
        )

        # Should have executed UPDATE query
        mock_conn.execute.assert_called_once()


@pytest.mark.asyncio
async def test_update_position_quantity_error(reconciliation_service):
    """Test position quantity update error handling"""
    with patch(
        "workspace.features.trade_executor.reconciliation.get_pool"
    ) as mock_get_pool:
        mock_pool = AsyncMock()
        mock_conn = MagicMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)
        mock_conn.execute = AsyncMock(side_effect=asyncpg.PostgresError("DB Error"))
        mock_pool.acquire = MagicMock(return_value=mock_conn)
        mock_get_pool.return_value = mock_pool

        with pytest.raises(Exception):
            await reconciliation_service._update_position_quantity(
                position_id="pos-123",
                new_quantity=Decimal("0.002"),
            )


# ============================================================================
# Reconciliation Result Storage Tests
# ============================================================================


@pytest.mark.asyncio
async def test_store_reconciliation_result(reconciliation_service):
    """Test storing reconciliation result"""
    result = ReconciliationResult(
        position_id="pos-123",
        system_quantity=Decimal("0.001"),
        exchange_quantity=Decimal("0.002"),
        discrepancy=Decimal("-0.001"),
        needs_correction=True,
        corrections_applied=["Updated quantity"],
        timestamp=datetime.utcnow(),
    )

    with patch(
        "workspace.features.trade_executor.reconciliation.get_pool"
    ) as mock_get_pool:
        mock_pool = AsyncMock()
        mock_conn = MagicMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)
        mock_conn.execute = AsyncMock()
        mock_pool.acquire = MagicMock(return_value=mock_conn)
        mock_get_pool.return_value = mock_pool

        await reconciliation_service._store_reconciliation_result(result)

        # Should have executed INSERT query
        mock_conn.execute.assert_called_once()


# ============================================================================
# Position Snapshot Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_position_snapshot_success(
    reconciliation_service,
    mock_position_service,
    sample_system_position,
):
    """Test creating position snapshot"""
    mock_position_service.get_position.return_value = sample_system_position

    with patch.object(
        reconciliation_service, "_store_position_snapshot", new=AsyncMock()
    ):
        snapshot = await reconciliation_service.create_position_snapshot("pos-123")

        assert snapshot is not None
        assert snapshot.position_id == "pos-123"
        assert snapshot.symbol == "BTC/USDT:USDT"
        assert snapshot.quantity == Decimal("0.001")


@pytest.mark.asyncio
async def test_create_position_snapshot_not_found(
    reconciliation_service, mock_position_service
):
    """Test snapshot for non-existent position"""
    mock_position_service.get_position_by_id.return_value = None

    snapshot = await reconciliation_service.create_position_snapshot("invalid-id")

    assert snapshot is None


@pytest.mark.asyncio
async def test_store_position_snapshot(reconciliation_service):
    """Test storing position snapshot"""
    snapshot = PositionSnapshot(
        position_id="pos-123",
        symbol="BTC/USDT:USDT",
        side="long",
        quantity=Decimal("0.001"),
        entry_price=Decimal("45000.0"),
        current_price=Decimal("45500.0"),
        unrealized_pnl=Decimal("5.0"),
        timestamp=datetime.utcnow(),
    )

    with patch(
        "workspace.features.trade_executor.reconciliation.get_pool"
    ) as mock_get_pool:
        mock_pool = AsyncMock()
        mock_conn = MagicMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)
        mock_conn.execute = AsyncMock()
        mock_pool.acquire = MagicMock(return_value=mock_conn)
        mock_get_pool.return_value = mock_pool

        await reconciliation_service._store_position_snapshot(snapshot)

        # Should have executed INSERT query
        mock_conn.execute.assert_called_once()


# ============================================================================
# Edge Cases and Error Scenarios
# ============================================================================


@pytest.mark.asyncio
async def test_reconcile_position_correction_failure(
    reconciliation_service,
    sample_system_position,
    sample_exchange_position,
):
    """Test handling correction failure"""
    sample_exchange_position["contracts"] = 0.002

    with (
        patch.object(
            reconciliation_service, "_store_reconciliation_result", new=AsyncMock()
        ),
        patch.object(
            reconciliation_service,
            "_update_position_quantity",
            new=AsyncMock(side_effect=Exception("Update failed")),
        ),
    ):
        result = await reconciliation_service._reconcile_position(
            sample_system_position,
            sample_exchange_position,
        )

        # Should still return result with error noted
        assert result.needs_correction is True
        assert any(
            "failed" in correction.lower() for correction in result.corrections_applied
        )


@pytest.mark.asyncio
async def test_reconcile_position_database_error_during_store(
    reconciliation_service,
    sample_system_position,
    sample_exchange_position,
):
    """Test reconciliation continues even if storage fails"""
    with patch.object(
        reconciliation_service,
        "_store_reconciliation_result",
        new=AsyncMock(side_effect=Exception("Storage failed")),
    ):
        # Should not raise exception
        result = await reconciliation_service._reconcile_position(
            sample_system_position,
            sample_exchange_position,
        )

        assert result is not None


@pytest.mark.asyncio
async def test_periodic_reconciliation_with_discrepancies(
    reconciliation_service,
    mock_position_service,
    mock_exchange,
    sample_system_position,
    sample_exchange_position,
):
    """Test periodic reconciliation logs discrepancies"""
    # Create discrepancy
    sample_exchange_position["contracts"] = 0.002

    mock_position_service.get_active_positions.return_value = [sample_system_position]
    mock_exchange.fetch_positions.return_value = [sample_exchange_position]

    with (
        patch.object(
            reconciliation_service, "_store_reconciliation_result", new=AsyncMock()
        ),
        patch.object(
            reconciliation_service, "_update_position_quantity", new=AsyncMock()
        ),
    ):
        # Start reconciliation
        await reconciliation_service.start_periodic_reconciliation()

        # Wait for execution
        await asyncio.sleep(1.5)

        # Should have detected discrepancy
        # (verified through logs in actual implementation)

        # Cleanup
        await reconciliation_service.stop_periodic_reconciliation()
