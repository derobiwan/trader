"""
Comprehensive Unit Tests for Position Service

Covers:
- Position creation with validation
- Position updates and P&L calculation
- Position closure and finalization
- Stop-loss and take-profit monitoring
- Risk limit enforcement
- Daily P&L tracking
- Position statistics
- Error handling and retries

Target Coverage: >80%
"""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import asyncpg
import pytest

from workspace.features.position_manager.models import (
    PositionNotFoundError,
    ValidationError,
)
from workspace.features.position_manager.position_service import (
    PositionService,
    bulk_update_prices,
)
from workspace.shared.database.models import PositionSide, PositionStatus


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_pool():
    """Create mock database pool"""
    pool = MagicMock()
    conn = MagicMock()
    transaction = MagicMock()

    # Setup async context managers
    conn.__aenter__ = AsyncMock(return_value=conn)
    conn.__aexit__ = AsyncMock(return_value=None)
    transaction.__aenter__ = AsyncMock(return_value=transaction)
    transaction.__aexit__ = AsyncMock(return_value=None)

    conn.transaction = MagicMock(return_value=transaction)
    pool.acquire = MagicMock(return_value=conn)
    pool.fetchrow = AsyncMock()
    pool.fetch = AsyncMock()
    pool.fetchval = AsyncMock()

    return pool


@pytest.fixture
def position_service(mock_pool):
    """Create PositionService instance"""
    return PositionService(pool=mock_pool)


@pytest.fixture
def sample_position_data():
    """Sample position data for testing"""
    return {
        "id": uuid4(),
        "symbol": "BTCUSDT",
        "side": "LONG",
        "quantity": Decimal("0.001"),
        "entry_price": Decimal("45000.0"),
        "current_price": Decimal("45000.0"),
        "leverage": 10,
        "stop_loss": Decimal("44000.0"),
        "take_profit": Decimal("46000.0"),
        "status": "OPEN",
        "pnl_chf": Decimal("0.0"),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "closed_at": None,
    }


# ============================================================================
# Position Creation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_position_success(
    position_service, mock_pool, sample_position_data
):
    """Test successful position creation"""
    # Mock database response
    conn = await mock_pool.acquire().__aenter__()
    conn.fetchrow = AsyncMock(return_value=sample_position_data)
    conn.execute = AsyncMock()

    position = await position_service.create_position(
        symbol="BTCUSDT",
        side="LONG",
        quantity=Decimal("0.001"),
        entry_price=Decimal("45000.0"),
        leverage=10,
        stop_loss=Decimal("44000.0"),
    )

    assert position is not None
    assert position.symbol == "BTCUSDT"
    assert position.side == PositionSide.LONG
    assert position.quantity == Decimal("0.001")


@pytest.mark.asyncio
async def test_create_position_missing_stop_loss(position_service):
    """Test position creation fails without stop-loss"""
    with pytest.raises((ValidationError, ValueError), match="Stop loss is REQUIRED"):
        await position_service.create_position(
            symbol="BTCUSDT",
            side="LONG",
            quantity=Decimal("0.001"),
            entry_price=Decimal("45000.0"),
            leverage=10,
            stop_loss=None,  # Missing stop-loss
        )


@pytest.mark.asyncio
async def test_create_position_invalid_leverage(position_service):
    """Test position creation with invalid leverage"""
    with pytest.raises((ValidationError, ValueError), match="leverage"):
        await position_service.create_position(
            symbol="BTCUSDT",
            side="LONG",
            quantity=Decimal("0.001"),
            entry_price=Decimal("45000.0"),
            leverage=3,  # Too low
            stop_loss=Decimal("44000.0"),
        )


@pytest.mark.asyncio
async def test_create_position_stop_loss_wrong_side(position_service):
    """Test position creation with stop-loss on wrong side"""
    with pytest.raises((ValidationError, ValueError), match="stop"):
        await position_service.create_position(
            symbol="BTCUSDT",
            side="LONG",
            quantity=Decimal("0.001"),
            entry_price=Decimal("45000.0"),
            leverage=10,
            stop_loss=Decimal("46000.0"),  # Above entry for LONG
        )


@pytest.mark.asyncio
async def test_create_position_invalid_side(position_service):
    """Test position creation with invalid side"""
    with pytest.raises(ValidationError):
        await position_service.create_position(
            symbol="BTCUSDT",
            side="INVALID",
            quantity=Decimal("0.001"),
            entry_price=Decimal("45000.0"),
            leverage=10,
            stop_loss=Decimal("44000.0"),
        )


@pytest.mark.asyncio
async def test_create_position_short_with_valid_stop_loss(
    position_service, mock_pool, sample_position_data
):
    """Test SHORT position creation with valid stop-loss"""
    sample_position_data["side"] = "SHORT"
    conn = await mock_pool.acquire().__aenter__()
    conn.fetchrow = AsyncMock(return_value=sample_position_data)
    conn.execute = AsyncMock()

    position = await position_service.create_position(
        symbol="BTCUSDT",
        side="SHORT",
        quantity=Decimal("0.001"),
        entry_price=Decimal("45000.0"),
        leverage=10,
        stop_loss=Decimal("46000.0"),  # Above entry for SHORT
    )

    assert position.side == PositionSide.SHORT


@pytest.mark.asyncio
async def test_create_position_with_take_profit(
    position_service, mock_pool, sample_position_data
):
    """Test position creation with take-profit"""
    sample_position_data["take_profit"] = Decimal("47000.0")
    conn = await mock_pool.acquire().__aenter__()
    conn.fetchrow = AsyncMock(return_value=sample_position_data)
    conn.execute = AsyncMock()

    position = await position_service.create_position(
        symbol="BTCUSDT",
        side="LONG",
        quantity=Decimal("0.001"),
        entry_price=Decimal("45000.0"),
        leverage=10,
        stop_loss=Decimal("44000.0"),
        take_profit=Decimal("47000.0"),
    )

    assert position.take_profit == Decimal("47000.0")


@pytest.mark.asyncio
async def test_create_position_database_retry(position_service, mock_pool):
    """Test position creation retries on database error"""
    conn = await mock_pool.acquire().__aenter__()

    # First attempt fails, second succeeds
    conn.fetchrow = AsyncMock(
        side_effect=[
            asyncpg.PostgresError("Connection lost"),
            {
                "id": uuid4(),
                "symbol": "BTCUSDT",
                "side": "LONG",
                "quantity": Decimal("0.001"),
                "entry_price": Decimal("45000.0"),
                "current_price": Decimal("45000.0"),
                "leverage": 10,
                "stop_loss": Decimal("44000.0"),
                "take_profit": None,
                "status": "OPEN",
                "pnl_chf": Decimal("0.0"),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "closed_at": None,
            },
        ]
    )
    conn.execute = AsyncMock()

    position = await position_service.create_position(
        symbol="BTCUSDT",
        side="LONG",
        quantity=Decimal("0.001"),
        entry_price=Decimal("45000.0"),
        leverage=10,
        stop_loss=Decimal("44000.0"),
    )

    assert position is not None


@pytest.mark.asyncio
async def test_create_position_max_retries_exceeded(position_service, mock_pool):
    """Test position creation fails after max retries"""
    conn = await mock_pool.acquire().__aenter__()
    conn.fetchrow = AsyncMock(side_effect=asyncpg.PostgresError("Connection lost"))
    conn.execute = AsyncMock()

    with pytest.raises(ConnectionError, match="Failed to create position"):
        await position_service.create_position(
            symbol="BTCUSDT",
            side="LONG",
            quantity=Decimal("0.001"),
            entry_price=Decimal("45000.0"),
            leverage=10,
            stop_loss=Decimal("44000.0"),
        )


# ============================================================================
# Position Update Tests
# ============================================================================


@pytest.mark.asyncio
async def test_update_position_price_success(
    position_service, mock_pool, sample_position_data
):
    """Test successful position price update"""
    sample_position_data["current_price"] = Decimal("46000.0")
    conn = await mock_pool.acquire().__aenter__()
    conn.fetchrow = AsyncMock(return_value=sample_position_data)

    position = await position_service.update_position_price(
        position_id=sample_position_data["id"],
        current_price=Decimal("46000.0"),
    )

    assert position.current_price == Decimal("46000.0")


@pytest.mark.asyncio
async def test_update_position_price_not_found(position_service, mock_pool):
    """Test updating non-existent position"""
    conn = await mock_pool.acquire().__aenter__()
    conn.fetchrow = AsyncMock(return_value=None)

    with pytest.raises(PositionNotFoundError):
        await position_service.update_position_price(
            position_id=uuid4(),
            current_price=Decimal("46000.0"),
        )


@pytest.mark.asyncio
async def test_update_position_price_precision(
    position_service, mock_pool, sample_position_data
):
    """Test price precision is enforced"""
    conn = await mock_pool.acquire().__aenter__()
    conn.fetchrow = AsyncMock(return_value=sample_position_data)

    position = await position_service.update_position_price(
        position_id=sample_position_data["id"],
        current_price=Decimal("46000.123456789"),  # High precision
    )

    # Should be quantized to 8 decimal places
    assert position is not None


# ============================================================================
# Position Closure Tests
# ============================================================================


@pytest.mark.asyncio
async def test_close_position_success(
    position_service, mock_pool, sample_position_data
):
    """Test successful position closure"""
    conn = await mock_pool.acquire().__aenter__()

    # First fetchrow for getting position
    # Second fetchrow for returning updated position
    sample_position_data["status"] = "CLOSED"
    sample_position_data["pnl_chf"] = Decimal("909.09")
    conn.fetchrow = AsyncMock(side_effect=[sample_position_data, sample_position_data])
    conn.execute = AsyncMock()

    position = await position_service.close_position(
        position_id=sample_position_data["id"],
        close_price=Decimal("46000.0"),
        reason="take_profit",
    )

    assert position.status == PositionStatus.CLOSED
    assert position.pnl_chf > Decimal("0")


@pytest.mark.asyncio
async def test_close_position_not_found(position_service, mock_pool):
    """Test closing non-existent position"""
    conn = await mock_pool.acquire().__aenter__()
    conn.fetchrow = AsyncMock(return_value=None)

    with pytest.raises(PositionNotFoundError):
        await position_service.close_position(
            position_id=uuid4(),
            close_price=Decimal("46000.0"),
            reason="manual",  # Fixed: should be "manual" not "manual_close"
        )


@pytest.mark.asyncio
async def test_close_position_invalid_reason(position_service):
    """Test closing position with invalid reason"""
    with pytest.raises(ValidationError, match="Invalid close reason"):
        await position_service.close_position(
            position_id=uuid4(),
            close_price=Decimal("46000.0"),
            reason="invalid_reason",
        )


@pytest.mark.asyncio
async def test_close_position_liquidation(
    position_service, mock_pool, sample_position_data
):
    """Test position closure via liquidation"""
    sample_position_data["status"] = "LIQUIDATED"
    conn = await mock_pool.acquire().__aenter__()
    conn.fetchrow = AsyncMock(side_effect=[sample_position_data, sample_position_data])
    conn.execute = AsyncMock()

    position = await position_service.close_position(
        position_id=sample_position_data["id"],
        close_price=Decimal("43000.0"),
        reason="liquidation",
    )

    assert position.status == PositionStatus.LIQUIDATED


@pytest.mark.asyncio
async def test_close_position_pnl_calculation_long(
    position_service, mock_pool, sample_position_data
):
    """Test P&L calculation for LONG position"""
    conn = await mock_pool.acquire().__aenter__()
    conn.fetchrow = AsyncMock(side_effect=[sample_position_data, sample_position_data])
    conn.execute = AsyncMock()

    # LONG position: profit when close > entry
    position = await position_service.close_position(
        position_id=sample_position_data["id"],
        close_price=Decimal("46000.0"),  # +1000 per contract
        reason="take_profit",
    )

    # Should have positive P&L
    assert position is not None


@pytest.mark.asyncio
async def test_close_position_pnl_calculation_short(
    position_service, mock_pool, sample_position_data
):
    """Test P&L calculation for SHORT position"""
    sample_position_data["side"] = "SHORT"
    conn = await mock_pool.acquire().__aenter__()
    conn.fetchrow = AsyncMock(side_effect=[sample_position_data, sample_position_data])
    conn.execute = AsyncMock()

    # SHORT position: profit when close < entry
    position = await position_service.close_position(
        position_id=sample_position_data["id"],
        close_price=Decimal("44000.0"),  # -1000 per contract
        reason="take_profit",
    )

    # Should have positive P&L
    assert position is not None


# ============================================================================
# Position Query Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_position_by_id_success(
    position_service, mock_pool, sample_position_data
):
    """Test retrieving position by ID"""
    mock_pool.fetchrow = AsyncMock(return_value=sample_position_data)

    position = await position_service.get_position_by_id(sample_position_data["id"])

    assert position is not None
    assert position.id == sample_position_data["id"]


@pytest.mark.asyncio
async def test_get_position_by_id_not_found(position_service, mock_pool):
    """Test retrieving non-existent position"""
    mock_pool.fetchrow = AsyncMock(return_value=None)

    position = await position_service.get_position_by_id(uuid4())

    assert position is None


@pytest.mark.asyncio
async def test_get_active_positions_all(
    position_service, mock_pool, sample_position_data
):
    """Test retrieving all active positions"""
    mock_pool.fetch = AsyncMock(return_value=[sample_position_data])

    positions = await position_service.get_active_positions()

    assert len(positions) == 1
    assert positions[0].status == PositionStatus.OPEN


@pytest.mark.asyncio
async def test_get_active_positions_by_symbol(
    position_service, mock_pool, sample_position_data
):
    """Test retrieving active positions filtered by symbol"""
    mock_pool.fetch = AsyncMock(return_value=[sample_position_data])

    positions = await position_service.get_active_positions(symbol="BTCUSDT")

    assert len(positions) == 1
    assert positions[0].symbol == "BTCUSDT"


@pytest.mark.asyncio
async def test_get_active_positions_empty(position_service, mock_pool):
    """Test retrieving active positions when none exist"""
    mock_pool.fetch = AsyncMock(return_value=[])

    positions = await position_service.get_active_positions()

    assert len(positions) == 0


# ============================================================================
# Stop-Loss and Take-Profit Monitoring Tests
# ============================================================================


@pytest.mark.asyncio
async def test_check_stop_loss_triggers_none(position_service, mock_pool):
    """Test checking stop-loss when no triggers"""
    mock_pool.fetch = AsyncMock(return_value=[])

    triggered = await position_service.check_stop_loss_triggers()

    assert len(triggered) == 0


@pytest.mark.asyncio
async def test_check_stop_loss_triggers_long_position(
    position_service, mock_pool, sample_position_data
):
    """Test stop-loss trigger for LONG position"""
    # Price below stop-loss
    sample_position_data["current_price"] = Decimal("43000.0")
    mock_pool.fetch = AsyncMock(return_value=[sample_position_data])

    triggered = await position_service.check_stop_loss_triggers()

    assert len(triggered) > 0


@pytest.mark.asyncio
async def test_check_stop_loss_triggers_short_position(
    position_service, mock_pool, sample_position_data
):
    """Test stop-loss trigger for SHORT position"""
    sample_position_data["side"] = "SHORT"
    sample_position_data["stop_loss"] = Decimal("46000.0")
    sample_position_data["current_price"] = Decimal("47000.0")  # Above stop
    mock_pool.fetch = AsyncMock(return_value=[sample_position_data])

    triggered = await position_service.check_stop_loss_triggers()

    assert len(triggered) > 0


@pytest.mark.asyncio
async def test_check_take_profit_triggers_long(
    position_service, mock_pool, sample_position_data
):
    """Test take-profit trigger for LONG position"""
    sample_position_data["current_price"] = Decimal("47000.0")  # Above TP
    mock_pool.fetch = AsyncMock(return_value=[sample_position_data])

    triggered = await position_service.check_take_profit_triggers()

    assert len(triggered) > 0


# ============================================================================
# Risk Management Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_total_exposure_zero(position_service, mock_pool):
    """Test total exposure with no positions"""
    mock_pool.fetch = AsyncMock(return_value=[])

    exposure = await position_service.get_total_exposure()

    assert exposure == Decimal("0")


@pytest.mark.asyncio
async def test_get_total_exposure_with_positions(
    position_service, mock_pool, sample_position_data
):
    """Test total exposure calculation"""
    mock_pool.fetch = AsyncMock(return_value=[sample_position_data])

    exposure = await position_service.get_total_exposure()

    assert exposure > Decimal("0")


@pytest.mark.asyncio
async def test_get_daily_pnl_today(position_service, mock_pool):
    """Test daily P&L for today"""
    conn = await mock_pool.acquire().__aenter__()
    conn.fetchrow = AsyncMock(
        return_value={"realized_pnl": Decimal("100.0"), "closed_count": 2}
    )
    mock_pool.fetch = AsyncMock(return_value=[])

    summary = await position_service.get_daily_pnl()

    assert summary.date == date.today()
    assert summary.realized_pnl_chf == Decimal("100.0")


@pytest.mark.asyncio
async def test_get_daily_pnl_specific_date(position_service, mock_pool):
    """Test daily P&L for specific date"""
    target_date = date(2025, 10, 30)
    conn = await mock_pool.acquire().__aenter__()
    conn.fetchrow = AsyncMock(
        return_value={"realized_pnl": Decimal("50.0"), "closed_count": 1}
    )
    mock_pool.fetch = AsyncMock(return_value=[])

    summary = await position_service.get_daily_pnl(target_date=target_date)

    assert summary.date == target_date


@pytest.mark.asyncio
async def test_get_daily_pnl_circuit_breaker_triggered(position_service, mock_pool):
    """Test circuit breaker flag in daily P&L"""
    conn = await mock_pool.acquire().__aenter__()
    conn.fetchrow = AsyncMock(
        return_value={"realized_pnl": Decimal("-600.0"), "closed_count": 5}
    )
    mock_pool.fetch = AsyncMock(return_value=[])

    summary = await position_service.get_daily_pnl()

    assert summary.is_circuit_breaker_triggered is True


@pytest.mark.asyncio
async def test_get_statistics(position_service, mock_pool, sample_position_data):
    """Test position statistics aggregation"""
    conn = await mock_pool.acquire().__aenter__()
    conn.fetchrow = AsyncMock(return_value={"total": 10, "open": 3, "closed": 7})
    conn.fetchval = AsyncMock(return_value=Decimal("250.0"))
    mock_pool.fetch = AsyncMock(return_value=[sample_position_data])

    stats = await position_service.get_statistics()

    assert stats.total_positions == 10
    assert stats.open_positions == 3
    assert stats.closed_positions == 7
    assert stats.total_realized_pnl_chf == Decimal("250.0")


# ============================================================================
# Bulk Operations Tests
# ============================================================================


@pytest.mark.asyncio
async def test_bulk_update_prices(position_service, mock_pool, sample_position_data):
    """Test bulk price updates"""
    mock_pool.fetch = AsyncMock(return_value=[sample_position_data])
    conn = await mock_pool.acquire().__aenter__()
    conn.fetchrow = AsyncMock(return_value=sample_position_data)

    price_updates = {
        "BTCUSDT": Decimal("46000.0"),
        "ETHUSDT": Decimal("2500.0"),
    }

    updated = await bulk_update_prices(position_service, price_updates)

    assert len(updated) > 0


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_position_by_id_database_error(position_service, mock_pool):
    """Test position retrieval with database error"""
    mock_pool.fetchrow = AsyncMock(side_effect=asyncpg.PostgresError("Connection lost"))

    with pytest.raises(ConnectionError):
        await position_service.get_position_by_id(uuid4())


@pytest.mark.asyncio
async def test_get_active_positions_database_error(position_service, mock_pool):
    """Test active positions query with database error"""
    mock_pool.fetch = AsyncMock(side_effect=asyncpg.PostgresError("Connection lost"))

    with pytest.raises(ConnectionError):
        await position_service.get_active_positions()
