"""
Unit tests for Position Reconciliation Service

Tests all discrepancy detection types and auto-correction logic.
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from workspace.features.position_reconciliation import (
    DiscrepancySeverity, DiscrepancyType, ExchangePosition,
    PositionReconciliationService, SystemPosition)


@pytest.fixture
def mock_trade_executor():
    """Create mock TradeExecutor"""
    executor = MagicMock()
    executor.exchange = MagicMock()
    executor.position_service = MagicMock()
    executor.position_service.get_open_positions = AsyncMock(return_value=[])
    return executor


@pytest.fixture
def reconciliation_service(mock_trade_executor):
    """Create reconciliation service"""
    return PositionReconciliationService(
        trade_executor=mock_trade_executor,
        quantity_tolerance_percent=Decimal("1.0"),
        price_tolerance_percent=Decimal("0.1"),
    )


@pytest.mark.asyncio
async def test_no_discrepancies_when_positions_match(
    reconciliation_service, mock_trade_executor
):
    """Test no discrepancies when positions match"""
    # Setup matching positions
    exchange_positions = {
        "BTC/USDT:USDT": ExchangePosition(
            symbol="BTC/USDT:USDT",
            side="LONG",
            quantity=Decimal("0.1"),
            entry_price=Decimal("45000.00"),
            current_price=Decimal("45100.00"),
            unrealized_pnl=Decimal("10.00"),
            leverage=Decimal("1"),
            margin=Decimal("4500.00"),
        )
    }

    system_positions = {
        "BTC/USDT:USDT": SystemPosition(
            symbol="BTC/USDT:USDT",
            side="LONG",
            quantity=Decimal("0.1"),
            entry_price=Decimal("45000.00"),
            current_price=Decimal("45100.00"),
            unrealized_pnl=Decimal("10.00"),
            leverage=Decimal("1"),
            last_updated=datetime.utcnow(),
        )
    }

    # Mock methods
    reconciliation_service._fetch_exchange_positions = AsyncMock(
        return_value=exchange_positions
    )
    reconciliation_service._get_system_positions = AsyncMock(
        return_value=system_positions
    )

    # Run reconciliation
    result = await reconciliation_service.reconcile_positions()

    # Verify no discrepancies
    # symbols_checked includes unique symbols from both exchange and system
    assert result.symbols_checked >= 1
    assert result.discrepancies_found == 0
    assert len(result.discrepancies) == 0


@pytest.mark.asyncio
async def test_detect_position_missing_in_system(reconciliation_service):
    """Test detection when position exists on exchange but not in system"""
    exchange_positions = {
        "BTC/USDT:USDT": ExchangePosition(
            symbol="BTC/USDT:USDT",
            side="LONG",
            quantity=Decimal("0.1"),
            entry_price=Decimal("45000.00"),
            current_price=Decimal("45100.00"),
            unrealized_pnl=Decimal("10.00"),
            leverage=Decimal("1"),
            margin=Decimal("4500.00"),
        )
    }

    system_positions = {}  # Empty - position not tracked

    reconciliation_service._fetch_exchange_positions = AsyncMock(
        return_value=exchange_positions
    )
    reconciliation_service._get_system_positions = AsyncMock(
        return_value=system_positions
    )

    result = await reconciliation_service.reconcile_positions()

    assert result.discrepancies_found == 1
    assert (
        result.discrepancies[0].discrepancy_type
        == DiscrepancyType.POSITION_MISSING_IN_SYSTEM
    )
    assert result.discrepancies[0].severity == DiscrepancySeverity.CRITICAL
    assert result.discrepancies[0].requires_manual_intervention is True


@pytest.mark.asyncio
async def test_detect_position_missing_on_exchange(reconciliation_service):
    """Test detection when position tracked in system but closed on exchange"""
    exchange_positions = {}  # Empty - position closed

    system_positions = {
        "BTC/USDT:USDT": SystemPosition(
            symbol="BTC/USDT:USDT",
            side="LONG",
            quantity=Decimal("0.1"),
            entry_price=Decimal("45000.00"),
            current_price=Decimal("45100.00"),
            unrealized_pnl=Decimal("10.00"),
            leverage=Decimal("1"),
            last_updated=datetime.utcnow(),
        )
    }

    reconciliation_service._fetch_exchange_positions = AsyncMock(
        return_value=exchange_positions
    )
    reconciliation_service._get_system_positions = AsyncMock(
        return_value=system_positions
    )

    result = await reconciliation_service.reconcile_positions()

    assert result.discrepancies_found == 1
    assert (
        result.discrepancies[0].discrepancy_type
        == DiscrepancyType.POSITION_MISSING_ON_EXCHANGE
    )
    assert result.discrepancies[0].severity == DiscrepancySeverity.WARNING
    assert result.discrepancies[0].requires_manual_intervention is False


@pytest.mark.asyncio
async def test_detect_quantity_mismatch(reconciliation_service):
    """Test detection of quantity mismatch"""
    exchange_positions = {
        "BTC/USDT:USDT": ExchangePosition(
            symbol="BTC/USDT:USDT",
            side="LONG",
            quantity=Decimal("0.1"),  # 0.1 BTC
            entry_price=Decimal("45000.00"),
            current_price=Decimal("45100.00"),
            unrealized_pnl=Decimal("10.00"),
            leverage=Decimal("1"),
            margin=Decimal("4500.00"),
        )
    }

    system_positions = {
        "BTC/USDT:USDT": SystemPosition(
            symbol="BTC/USDT:USDT",
            side="LONG",
            quantity=Decimal("0.09"),  # 0.09 BTC (10% difference - critical)
            entry_price=Decimal("45000.00"),
            current_price=Decimal("45100.00"),
            unrealized_pnl=Decimal("9.00"),
            leverage=Decimal("1"),
            last_updated=datetime.utcnow(),
        )
    }

    reconciliation_service._fetch_exchange_positions = AsyncMock(
        return_value=exchange_positions
    )
    reconciliation_service._get_system_positions = AsyncMock(
        return_value=system_positions
    )

    result = await reconciliation_service.reconcile_positions()

    assert result.discrepancies_found == 1
    assert result.discrepancies[0].discrepancy_type == DiscrepancyType.QUANTITY_MISMATCH
    assert result.discrepancies[0].quantity_difference == Decimal("0.01")


@pytest.mark.asyncio
async def test_detect_side_mismatch(reconciliation_service):
    """Test detection of side mismatch (CRITICAL)"""
    exchange_positions = {
        "BTC/USDT:USDT": ExchangePosition(
            symbol="BTC/USDT:USDT",
            side="LONG",  # Long on exchange
            quantity=Decimal("0.1"),
            entry_price=Decimal("45000.00"),
            current_price=Decimal("45100.00"),
            unrealized_pnl=Decimal("10.00"),
            leverage=Decimal("1"),
            margin=Decimal("4500.00"),
        )
    }

    system_positions = {
        "BTC/USDT:USDT": SystemPosition(
            symbol="BTC/USDT:USDT",
            side="SHORT",  # Short in system - CRITICAL ERROR
            quantity=Decimal("0.1"),
            entry_price=Decimal("45000.00"),
            current_price=Decimal("45100.00"),
            unrealized_pnl=Decimal("-10.00"),
            leverage=Decimal("1"),
            last_updated=datetime.utcnow(),
        )
    }

    reconciliation_service._fetch_exchange_positions = AsyncMock(
        return_value=exchange_positions
    )
    reconciliation_service._get_system_positions = AsyncMock(
        return_value=system_positions
    )

    result = await reconciliation_service.reconcile_positions()

    assert result.discrepancies_found == 1
    assert result.discrepancies[0].discrepancy_type == DiscrepancyType.SIDE_MISMATCH
    assert result.discrepancies[0].severity == DiscrepancySeverity.CRITICAL
    assert result.discrepancies[0].requires_manual_intervention is True


@pytest.mark.asyncio
async def test_detect_price_mismatch(reconciliation_service):
    """Test detection of price mismatch"""
    exchange_positions = {
        "BTC/USDT:USDT": ExchangePosition(
            symbol="BTC/USDT:USDT",
            side="LONG",
            quantity=Decimal("0.1"),
            entry_price=Decimal("45050.00"),  # Slightly different entry price
            current_price=Decimal("45100.00"),
            unrealized_pnl=Decimal("5.00"),
            leverage=Decimal("1"),
            margin=Decimal("4505.00"),
        )
    }

    system_positions = {
        "BTC/USDT:USDT": SystemPosition(
            symbol="BTC/USDT:USDT",
            side="LONG",
            quantity=Decimal("0.1"),
            entry_price=Decimal("45000.00"),  # Original entry price
            current_price=Decimal("45100.00"),
            unrealized_pnl=Decimal("10.00"),
            leverage=Decimal("1"),
            last_updated=datetime.utcnow(),
        )
    }

    reconciliation_service._fetch_exchange_positions = AsyncMock(
        return_value=exchange_positions
    )
    reconciliation_service._get_system_positions = AsyncMock(
        return_value=system_positions
    )

    result = await reconciliation_service.reconcile_positions()

    assert result.discrepancies_found == 1
    assert result.discrepancies[0].discrepancy_type == DiscrepancyType.PRICE_MISMATCH
    assert result.discrepancies[0].severity == DiscrepancySeverity.WARNING
    assert result.discrepancies[0].requires_manual_intervention is False


@pytest.mark.asyncio
async def test_auto_correction_statistics(reconciliation_service, mock_trade_executor):
    """Test that auto-corrections are tracked"""
    # Setup position missing on exchange (auto-correctable)
    exchange_positions = {}

    # Mock position object
    mock_position = MagicMock()
    mock_position.id = "pos-123"
    mock_position.symbol = "BTC/USDT:USDT"
    mock_position.side = "long"
    mock_position.quantity = Decimal("0.1")
    mock_position.entry_price = Decimal("45000.00")
    mock_position.current_price = Decimal("45100.00")

    system_positions = {
        "BTC/USDT:USDT": SystemPosition(
            symbol="BTC/USDT:USDT",
            side="LONG",
            quantity=Decimal("0.1"),
            entry_price=Decimal("45000.00"),
            current_price=Decimal("45100.00"),
            unrealized_pnl=Decimal("10.00"),
            leverage=Decimal("1"),
            last_updated=datetime.utcnow(),
        )
    }

    reconciliation_service._fetch_exchange_positions = AsyncMock(
        return_value=exchange_positions
    )
    reconciliation_service._get_system_positions = AsyncMock(
        return_value=system_positions
    )
    mock_trade_executor.position_service.get_open_positions = AsyncMock(
        return_value=[mock_position]
    )
    mock_trade_executor.position_service.close_position = AsyncMock()

    await reconciliation_service.reconcile_positions()

    # Check that auto-correction was attempted
    assert mock_trade_executor.position_service.close_position.called


@pytest.mark.asyncio
async def test_quantity_mismatch_severity_levels(reconciliation_service):
    """Test different severity levels for quantity mismatches"""

    # Test 1: <1% difference - no discrepancy
    exchange_pos = ExchangePosition(
        symbol="BTC/USDT:USDT",
        side="LONG",
        quantity=Decimal("1.0"),
        entry_price=Decimal("45000.00"),
        current_price=Decimal("45100.00"),
        unrealized_pnl=Decimal("100.00"),
        leverage=Decimal("1"),
        margin=Decimal("45000.00"),
    )
    system_pos = SystemPosition(
        symbol="BTC/USDT:USDT",
        side="LONG",
        quantity=Decimal("1.005"),  # 0.5% difference
        entry_price=Decimal("45000.00"),
        current_price=Decimal("45100.00"),
        unrealized_pnl=Decimal("100.00"),
        leverage=Decimal("1"),
        last_updated=datetime.utcnow(),
    )

    discrepancy = reconciliation_service._check_position_differences(
        "BTC/USDT:USDT", exchange_pos, system_pos
    )
    assert discrepancy is None  # Below tolerance

    # Test 2: 5-10% difference - WARNING, auto-corrected
    system_pos.quantity = Decimal("1.07")  # 7% difference
    discrepancy = reconciliation_service._check_position_differences(
        "BTC/USDT:USDT", exchange_pos, system_pos
    )
    assert discrepancy is not None
    assert discrepancy.severity == DiscrepancySeverity.WARNING
    assert discrepancy.requires_manual_intervention is False

    # Test 3: >10% difference - CRITICAL, manual intervention
    system_pos.quantity = Decimal("1.15")  # 15% difference
    discrepancy = reconciliation_service._check_position_differences(
        "BTC/USDT:USDT", exchange_pos, system_pos
    )
    assert discrepancy is not None
    assert discrepancy.severity == DiscrepancySeverity.CRITICAL
    assert discrepancy.requires_manual_intervention is True


@pytest.mark.asyncio
async def test_reconciliation_service_start_stop(reconciliation_service):
    """Test starting and stopping reconciliation service"""
    assert not reconciliation_service.is_running

    await reconciliation_service.start()
    assert reconciliation_service.is_running
    assert reconciliation_service.reconciliation_task is not None

    await reconciliation_service.stop()
    assert not reconciliation_service.is_running


@pytest.mark.asyncio
async def test_get_stats(reconciliation_service):
    """Test getting reconciliation statistics"""
    stats = reconciliation_service.get_stats()

    assert "total_reconciliations" in stats
    assert "total_discrepancies" in stats
    assert "total_auto_corrections" in stats
    assert "total_critical_alerts" in stats
    assert "is_running" in stats
    assert "reconciliation_interval_seconds" in stats

    assert stats["total_reconciliations"] == 0
    assert stats["is_running"] is False


@pytest.mark.asyncio
async def test_multiple_discrepancies(reconciliation_service):
    """Test handling multiple discrepancies at once"""
    exchange_positions = {
        "BTC/USDT:USDT": ExchangePosition(
            symbol="BTC/USDT:USDT",
            side="LONG",
            quantity=Decimal("0.1"),
            entry_price=Decimal("45000.00"),
            current_price=Decimal("45100.00"),
            unrealized_pnl=Decimal("10.00"),
            leverage=Decimal("1"),
            margin=Decimal("4500.00"),
        ),
        "ETH/USDT:USDT": ExchangePosition(
            symbol="ETH/USDT:USDT",
            side="SHORT",
            quantity=Decimal("2.0"),
            entry_price=Decimal("3000.00"),
            current_price=Decimal("2950.00"),
            unrealized_pnl=Decimal("100.00"),
            leverage=Decimal("1"),
            margin=Decimal("6000.00"),
        ),
    }

    system_positions = {
        "BTC/USDT:USDT": SystemPosition(
            symbol="BTC/USDT:USDT",
            side="SHORT",  # Side mismatch - CRITICAL
            quantity=Decimal("0.1"),
            entry_price=Decimal("45000.00"),
            current_price=Decimal("45100.00"),
            unrealized_pnl=Decimal("-10.00"),
            leverage=Decimal("1"),
            last_updated=datetime.utcnow(),
        ),
        "ETH/USDT:USDT": SystemPosition(
            symbol="ETH/USDT:USDT",
            side="SHORT",
            quantity=Decimal("1.8"),  # Quantity mismatch (10%)
            entry_price=Decimal("3000.00"),
            current_price=Decimal("2950.00"),
            unrealized_pnl=Decimal("90.00"),
            leverage=Decimal("1"),
            last_updated=datetime.utcnow(),
        ),
    }

    reconciliation_service._fetch_exchange_positions = AsyncMock(
        return_value=exchange_positions
    )
    reconciliation_service._get_system_positions = AsyncMock(
        return_value=system_positions
    )

    result = await reconciliation_service.reconcile_positions()

    assert result.discrepancies_found == 2
    assert result.symbols_checked >= 2  # May count duplicates from both dicts

    # Check that we have one CRITICAL (side mismatch) and one quantity mismatch
    side_mismatch = [
        d
        for d in result.discrepancies
        if d.discrepancy_type == DiscrepancyType.SIDE_MISMATCH
    ]
    quantity_mismatch = [
        d
        for d in result.discrepancies
        if d.discrepancy_type == DiscrepancyType.QUANTITY_MISMATCH
    ]

    assert len(side_mismatch) == 1
    assert len(quantity_mismatch) == 1
    assert side_mismatch[0].severity == DiscrepancySeverity.CRITICAL
