"""
Unit Tests for Position Reconciliation Service

Tests position reconciliation between system and exchange, discrepancy detection,
and automatic correction logic.

Coverage target: >60%
Test patterns: Mock exchange API, test reconciliation logic, verify corrections
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, patch, MagicMock

from workspace.features.trade_executor.reconciliation import ReconciliationService
from workspace.features.trade_executor.models import (
    ReconciliationResult,
    PositionSnapshot,
)


class MockPosition:
    """Mock position object for testing"""

    def __init__(
        self,
        id,
        symbol,
        quantity,
        entry_price,
        current_price=None,
        side="long",
    ):
        self.id = id
        self.symbol = symbol
        self.quantity = quantity
        self.entry_price = entry_price
        self.current_price = current_price or entry_price
        self.side = side
        self.pnl_chf = Decimal("0")


class TestReconciliationService:
    """Test suite for ReconciliationService"""

    @pytest.fixture
    def mock_exchange(self):
        """Mock exchange instance"""
        exchange = AsyncMock()
        exchange.fetch_positions = AsyncMock(return_value=[])
        return exchange

    @pytest.fixture
    def mock_position_service(self):
        """Mock position service"""
        service = AsyncMock()
        service.get_active_positions = AsyncMock(return_value=[])
        service.get_position = AsyncMock(return_value=None)
        service.close_position = AsyncMock()
        service.update_position_price = AsyncMock()
        return service

    @pytest.fixture
    def reconciliation_service(self, mock_exchange, mock_position_service):
        """Create reconciliation service instance"""
        return ReconciliationService(
            exchange=mock_exchange,
            position_service=mock_position_service,
            periodic_interval=300,
            discrepancy_threshold=Decimal("0.00001"),
        )

    @pytest.mark.asyncio
    async def test_service_initialization(self, mock_exchange, mock_position_service):
        """Test service initializes correctly"""
        service = ReconciliationService(
            exchange=mock_exchange,
            position_service=mock_position_service,
        )

        assert service.exchange == mock_exchange
        assert service.position_service == mock_position_service
        assert service.periodic_interval == 300
        assert service.discrepancy_threshold == Decimal("0.00001")
        assert service.reconciliation_task is None

    @pytest.mark.asyncio
    async def test_reconcile_all_positions_empty(
        self, reconciliation_service, mock_position_service, mock_exchange
    ):
        """Test reconciliation with no positions"""
        # Setup empty positions
        mock_position_service.get_active_positions.return_value = []
        mock_exchange.fetch_positions.return_value = []

        results = await reconciliation_service.reconcile_all_positions()

        assert results == []
        mock_position_service.get_active_positions.assert_called_once()
        mock_exchange.fetch_positions.assert_called_once()

    @pytest.mark.asyncio
    async def test_reconcile_all_positions_matching(
        self, reconciliation_service, mock_position_service, mock_exchange
    ):
        """Test reconciliation with matching positions"""
        # Setup system positions
        system_pos = MockPosition(
            id="pos_1",
            symbol="BTC/USDT:USDT",
            quantity=Decimal("0.5"),
            entry_price=Decimal("50000"),
        )
        mock_position_service.get_active_positions.return_value = [system_pos]

        # Setup exchange positions (matching)
        exchange_pos = {
            "symbol": "BTC/USDT:USDT",
            "contracts": Decimal("0.5"),
            "side": "long",
        }
        mock_exchange.fetch_positions.return_value = [exchange_pos]

        # Mock database operations
        with patch.object(
            reconciliation_service, "_store_reconciliation_result", new=AsyncMock()
        ):
            results = await reconciliation_service.reconcile_all_positions()

        assert len(results) == 1
        result = results[0]
        assert result.position_id == "pos_1"
        assert result.system_quantity == Decimal("0.5")
        assert result.exchange_quantity == Decimal("0.5")
        assert result.discrepancy == Decimal("0")
        assert result.needs_correction is False

    @pytest.mark.asyncio
    async def test_reconcile_all_positions_discrepancy(
        self, reconciliation_service, mock_position_service, mock_exchange
    ):
        """Test reconciliation with quantity discrepancy"""
        # Setup system position
        system_pos = MockPosition(
            id="pos_2",
            symbol="ETH/USDT:USDT",
            quantity=Decimal("2.0"),
            entry_price=Decimal("3000"),
        )
        mock_position_service.get_active_positions.return_value = [system_pos]

        # Setup exchange position (different quantity)
        exchange_pos = {
            "symbol": "ETH/USDT:USDT",
            "contracts": Decimal("1.5"),  # Discrepancy: 0.5
            "side": "long",
        }
        mock_exchange.fetch_positions.return_value = [exchange_pos]

        # Mock database operations
        with (
            patch.object(
                reconciliation_service, "_update_position_quantity", new=AsyncMock()
            ),
            patch.object(
                reconciliation_service, "_store_reconciliation_result", new=AsyncMock()
            ),
        ):
            results = await reconciliation_service.reconcile_all_positions()

        assert len(results) == 1
        result = results[0]
        assert result.position_id == "pos_2"
        assert result.system_quantity == Decimal("2.0")
        assert result.exchange_quantity == Decimal("1.5")
        assert result.discrepancy == Decimal("0.5")
        assert result.needs_correction is True
        assert len(result.corrections_applied) > 0

        # Verify correction was applied
        reconciliation_service._update_position_quantity.assert_called_once_with(
            position_id="pos_2", new_quantity=Decimal("1.5")
        )

    @pytest.mark.asyncio
    async def test_reconcile_all_positions_missing_on_exchange(
        self, reconciliation_service, mock_position_service, mock_exchange
    ):
        """Test reconciliation when position exists in system but not on exchange"""
        # Setup system position
        system_pos = MockPosition(
            id="pos_3",
            symbol="SOL/USDT:USDT",
            quantity=Decimal("10"),
            entry_price=Decimal("100"),
        )
        mock_position_service.get_active_positions.return_value = [system_pos]

        # Exchange has no positions
        mock_exchange.fetch_positions.return_value = []

        # Mock database operations
        with patch.object(
            reconciliation_service, "_store_reconciliation_result", new=AsyncMock()
        ):
            results = await reconciliation_service.reconcile_all_positions()

        assert len(results) == 1
        result = results[0]
        assert result.position_id == "pos_3"
        assert result.system_quantity == Decimal("10")
        assert result.exchange_quantity == Decimal("0")
        assert result.discrepancy == Decimal("10")
        assert result.needs_correction is True

        # Verify position was closed in system
        mock_position_service.close_position.assert_called_once()

    @pytest.mark.asyncio
    async def test_reconcile_all_positions_extra_on_exchange(
        self, reconciliation_service, mock_position_service, mock_exchange
    ):
        """Test reconciliation when position exists on exchange but not in system"""
        # System has no positions
        mock_position_service.get_active_positions.return_value = []

        # Exchange has a position
        exchange_pos = {
            "symbol": "AVAX/USDT:USDT",
            "contracts": Decimal("5.0"),
            "side": "long",
        }
        mock_exchange.fetch_positions.return_value = [exchange_pos]

        results = await reconciliation_service.reconcile_all_positions()

        # Should log warning but not create reconciliation result
        assert results == []

    @pytest.mark.asyncio
    async def test_reconcile_position_success(
        self, reconciliation_service, mock_position_service, mock_exchange
    ):
        """Test reconciling a specific position"""
        # Setup system position
        system_pos = MockPosition(
            id="pos_4",
            symbol="BTC/USDT:USDT",
            quantity=Decimal("0.8"),
            entry_price=Decimal("50000"),
        )
        mock_position_service.get_position.return_value = system_pos

        # Setup exchange position
        exchange_pos = {
            "symbol": "BTC/USDT:USDT",
            "contracts": Decimal("0.8"),
            "side": "long",
        }
        mock_exchange.fetch_positions.return_value = [exchange_pos]

        # Mock database operations
        with patch.object(
            reconciliation_service, "_store_reconciliation_result", new=AsyncMock()
        ):
            result = await reconciliation_service.reconcile_position("pos_4")

        assert result is not None
        assert result.position_id == "pos_4"
        assert result.needs_correction is False

    @pytest.mark.asyncio
    async def test_reconcile_position_not_found_in_system(
        self, reconciliation_service, mock_position_service
    ):
        """Test reconciling position that doesn't exist in system"""
        mock_position_service.get_position.return_value = None

        result = await reconciliation_service.reconcile_position("invalid_pos")

        assert result is None

    @pytest.mark.asyncio
    async def test_reconcile_position_not_found_on_exchange(
        self, reconciliation_service, mock_position_service, mock_exchange
    ):
        """Test reconciling position that doesn't exist on exchange"""
        # Setup system position
        system_pos = MockPosition(
            id="pos_5",
            symbol="DOGE/USDT:USDT",
            quantity=Decimal("1000"),
            entry_price=Decimal("0.1"),
        )
        mock_position_service.get_position.return_value = system_pos

        # Exchange has no matching position
        mock_exchange.fetch_positions.return_value = []

        result = await reconciliation_service.reconcile_position("pos_5")

        assert result is not None
        assert result.exchange_quantity == Decimal("0")
        assert result.needs_correction is True

    @pytest.mark.asyncio
    async def test_fetch_exchange_positions(
        self, reconciliation_service, mock_exchange
    ):
        """Test fetching positions from exchange"""
        # Mock exchange response
        mock_exchange.fetch_positions.return_value = [
            {"symbol": "BTC/USDT:USDT", "contracts": Decimal("0.5"), "side": "long"},
            {"symbol": "ETH/USDT:USDT", "contracts": Decimal("2.0"), "side": "long"},
            {
                "symbol": "SOL/USDT:USDT",
                "contracts": Decimal("0.0"),
                "side": "long",
            },  # Closed
        ]

        positions = await reconciliation_service._fetch_exchange_positions()

        # Should filter out closed positions (contracts = 0)
        assert len(positions) == 2
        assert all(float(p["contracts"]) != 0 for p in positions)

    @pytest.mark.asyncio
    async def test_fetch_exchange_positions_error(
        self, reconciliation_service, mock_exchange
    ):
        """Test error handling when fetching exchange positions"""
        mock_exchange.fetch_positions.side_effect = Exception("Exchange API error")

        positions = await reconciliation_service._fetch_exchange_positions()

        # Should return empty list on error
        assert positions == []

    @pytest.mark.asyncio
    async def test_discrepancy_threshold(
        self, reconciliation_service, mock_position_service, mock_exchange
    ):
        """Test discrepancy threshold logic"""
        # Setup position with tiny discrepancy (below threshold)
        system_pos = MockPosition(
            id="pos_6",
            symbol="BTC/USDT:USDT",
            quantity=Decimal("1.00000001"),
            entry_price=Decimal("50000"),
        )
        mock_position_service.get_active_positions.return_value = [system_pos]

        exchange_pos = {
            "symbol": "BTC/USDT:USDT",
            "contracts": Decimal("1.0"),  # Tiny discrepancy
            "side": "long",
        }
        mock_exchange.fetch_positions.return_value = [exchange_pos]

        # Mock database operations
        with patch.object(
            reconciliation_service, "_store_reconciliation_result", new=AsyncMock()
        ):
            results = await reconciliation_service.reconcile_all_positions()

        result = results[0]
        # Discrepancy is below threshold, should not need correction
        assert result.needs_correction is False

    @pytest.mark.asyncio
    async def test_create_position_snapshot(
        self, reconciliation_service, mock_position_service
    ):
        """Test creating position snapshot"""
        # Setup position
        position = MockPosition(
            id="pos_snap",
            symbol="ETH/USDT:USDT",
            quantity=Decimal("5.0"),
            entry_price=Decimal("3000"),
            current_price=Decimal("3100"),
            side="long",
        )
        position.pnl_chf = Decimal("500")
        mock_position_service.get_position.return_value = position

        # Mock database storage
        with patch.object(
            reconciliation_service, "_store_position_snapshot", new=AsyncMock()
        ):
            snapshot = await reconciliation_service.create_position_snapshot("pos_snap")

        assert snapshot is not None
        assert snapshot.position_id == "pos_snap"
        assert snapshot.symbol == "ETH/USDT:USDT"
        assert snapshot.quantity == Decimal("5.0")
        assert snapshot.entry_price == Decimal("3000")
        assert snapshot.current_price == Decimal("3100")
        assert snapshot.unrealized_pnl == Decimal("500")

    @pytest.mark.asyncio
    async def test_create_position_snapshot_not_found(
        self, reconciliation_service, mock_position_service
    ):
        """Test creating snapshot for non-existent position"""
        mock_position_service.get_position.return_value = None

        snapshot = await reconciliation_service.create_position_snapshot("invalid_pos")

        assert snapshot is None

    @pytest.mark.asyncio
    async def test_periodic_reconciliation_start_stop(self, reconciliation_service):
        """Test starting and stopping periodic reconciliation"""
        # Start periodic reconciliation
        await reconciliation_service.start_periodic_reconciliation()

        assert reconciliation_service.reconciliation_task is not None
        assert not reconciliation_service.reconciliation_task.done()

        # Stop periodic reconciliation
        await reconciliation_service.stop_periodic_reconciliation()

        assert reconciliation_service.reconciliation_task is None

    @pytest.mark.asyncio
    async def test_periodic_reconciliation_already_running(
        self, reconciliation_service
    ):
        """Test starting periodic reconciliation when already running"""
        # Start first time
        await reconciliation_service.start_periodic_reconciliation()
        first_task = reconciliation_service.reconciliation_task

        # Try to start again
        await reconciliation_service.start_periodic_reconciliation()

        # Should still be the same task
        assert reconciliation_service.reconciliation_task == first_task

        # Cleanup
        await reconciliation_service.stop_periodic_reconciliation()

    @pytest.mark.asyncio
    async def test_reconcile_position_error_handling(
        self, reconciliation_service, mock_position_service, mock_exchange
    ):
        """Test error handling in position reconciliation"""
        mock_position_service.get_position.side_effect = Exception("Database error")

        result = await reconciliation_service.reconcile_position("pos_error")

        assert result is None

    @pytest.mark.asyncio
    async def test_reconcile_all_positions_error_handling(
        self, reconciliation_service, mock_position_service
    ):
        """Test error handling in full reconciliation"""
        mock_position_service.get_active_positions.side_effect = Exception(
            "Service error"
        )

        results = await reconciliation_service.reconcile_all_positions()

        # Should return empty list on error
        assert results == []

    @pytest.mark.asyncio
    async def test_update_position_quantity(self, reconciliation_service):
        """Test updating position quantity in database"""
        # Mock database
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()

        # Context manager for acquire
        acquire_ctx = AsyncMock()
        acquire_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        acquire_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "workspace.features.trade_executor.reconciliation.DatabasePool"
        ) as mock_pool_class:
            mock_pool_class.get_connection = MagicMock(return_value=acquire_ctx)

            await reconciliation_service._update_position_quantity(
                position_id="pos_update", new_quantity=Decimal("2.5")
            )

        # Verify database call
        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args
        assert "UPDATE positions" in call_args[0][0]
        assert call_args[0][1] == Decimal("2.5")
        assert call_args[0][2] == "pos_update"

    @pytest.mark.asyncio
    async def test_store_reconciliation_result(self, reconciliation_service):
        """Test storing reconciliation result in database"""
        result = ReconciliationResult(
            position_id="pos_store",
            system_quantity=Decimal("1.0"),
            exchange_quantity=Decimal("0.9"),
            discrepancy=Decimal("0.1"),
            needs_correction=True,
        )

        # Mock database
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()

        # Context manager for acquire
        acquire_ctx = AsyncMock()
        acquire_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        acquire_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "workspace.features.trade_executor.reconciliation.DatabasePool"
        ) as mock_pool_class:
            mock_pool_class.get_connection = MagicMock(return_value=acquire_ctx)

            await reconciliation_service._store_reconciliation_result(result)

        # Verify database call
        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args
        assert "INSERT INTO position_reconciliation" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_store_position_snapshot(self, reconciliation_service):
        """Test storing position snapshot in database"""
        snapshot = PositionSnapshot(
            position_id="snap_store",
            symbol="BTC/USDT:USDT",
            side="long",
            quantity=Decimal("0.5"),
            entry_price=Decimal("50000"),
            current_price=Decimal("51000"),
            unrealized_pnl=Decimal("500"),
        )

        # Mock database
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()

        # Context manager for acquire
        acquire_ctx = AsyncMock()
        acquire_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        acquire_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "workspace.features.trade_executor.reconciliation.DatabasePool"
        ) as mock_pool_class:
            mock_pool_class.get_connection = MagicMock(return_value=acquire_ctx)

            await reconciliation_service._store_position_snapshot(snapshot)

        # Verify database call
        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args
        assert "INSERT INTO position_snapshots" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_multiple_positions_reconciliation(
        self, reconciliation_service, mock_position_service, mock_exchange
    ):
        """Test reconciling multiple positions at once"""
        # Setup multiple system positions
        system_positions = [
            MockPosition("p1", "BTC/USDT:USDT", Decimal("0.5"), Decimal("50000")),
            MockPosition("p2", "ETH/USDT:USDT", Decimal("2.0"), Decimal("3000")),
            MockPosition("p3", "SOL/USDT:USDT", Decimal("10"), Decimal("100")),
        ]
        mock_position_service.get_active_positions.return_value = system_positions

        # Setup matching exchange positions
        exchange_positions = [
            {"symbol": "BTC/USDT:USDT", "contracts": Decimal("0.5")},
            {"symbol": "ETH/USDT:USDT", "contracts": Decimal("2.0")},
            {"symbol": "SOL/USDT:USDT", "contracts": Decimal("10.0")},
        ]
        mock_exchange.fetch_positions.return_value = exchange_positions

        # Mock database operations
        with patch.object(
            reconciliation_service, "_store_reconciliation_result", new=AsyncMock()
        ):
            results = await reconciliation_service.reconcile_all_positions()

        assert len(results) == 3
        assert all(not r.needs_correction for r in results)

    @pytest.mark.asyncio
    async def test_correction_applied_tracking(
        self, reconciliation_service, mock_position_service, mock_exchange
    ):
        """Test that corrections applied are tracked properly"""
        system_pos = MockPosition(
            id="pos_track",
            symbol="BTC/USDT:USDT",
            quantity=Decimal("1.5"),
            entry_price=Decimal("50000"),
        )
        mock_position_service.get_active_positions.return_value = [system_pos]

        exchange_pos = {
            "symbol": "BTC/USDT:USDT",
            "contracts": Decimal("1.0"),
            "side": "long",
        }
        mock_exchange.fetch_positions.return_value = [exchange_pos]

        # Mock database operations
        with (
            patch.object(
                reconciliation_service, "_update_position_quantity", new=AsyncMock()
            ),
            patch.object(
                reconciliation_service, "_store_reconciliation_result", new=AsyncMock()
            ),
        ):
            results = await reconciliation_service.reconcile_all_positions()

        result = results[0]
        assert result.needs_correction is True
        assert len(result.corrections_applied) > 0
        assert "Updated quantity" in result.corrections_applied[0]
