"""
Position Service Test Suite

Comprehensive tests for position lifecycle management including:
- Position creation with validation
- Price updates and P&L calculations
- Stop-loss and take-profit detection
- Position closure with final P&L
- Daily P&L tracking
- Circuit breaker monitoring
- Concurrent operations
- Error handling

Run with:
    pytest workspace/features/position_manager/tests/test_position_service.py -v
    pytest workspace/features/position_manager/tests/test_position_service.py::test_create_position_success -v
"""

import asyncio

# Test database setup
import os
from datetime import date as Date
from decimal import Decimal
from uuid import uuid4

import pytest

os.environ["DB_HOST"] = os.getenv("TEST_DB_HOST", "localhost")
os.environ["DB_PORT"] = os.getenv("TEST_DB_PORT", "5432")
os.environ["DB_NAME"] = os.getenv("TEST_DB_NAME", "trading_system_test")
os.environ["DB_USER"] = os.getenv("TEST_DB_USER", "postgres")
os.environ["DB_PASSWORD"] = os.getenv("TEST_DB_PASSWORD", "")

# Imports after environment setup to ensure correct test database configuration
from workspace.features.position_manager.models import (  # noqa: E402
    CIRCUIT_BREAKER_LOSS_CHF,
    MAX_TOTAL_EXPOSURE_CHF,
    PositionNotFoundError,
    RiskLimitError,
    ValidationError,
)
from workspace.features.position_manager.position_service import (  # noqa: E402
    PositionService,
    bulk_update_prices,
)
from workspace.shared.database.connection import DatabasePool  # noqa: E402

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def db_pool():
    """Create database connection pool for tests."""
    pool = DatabasePool(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "trading_system"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
        min_size=2,
        max_size=5,
    )

    await pool.initialize()
    yield pool
    await pool.close()


@pytest.fixture
async def clean_database(db_pool):
    """Clean database before each test."""
    async with db_pool.acquire() as conn:
        # Delete all test data
        await conn.execute("DELETE FROM audit_log")
        await conn.execute("DELETE FROM orders")
        await conn.execute("DELETE FROM positions")
        await conn.execute("DELETE FROM circuit_breaker_state")
    yield


@pytest.fixture
async def position_service(db_pool, clean_database):
    """Create PositionService instance."""
    return PositionService(db_pool)


# ============================================================================
# Position Creation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_position_success(position_service):
    """Test successful position creation with valid parameters."""
    position = await position_service.create_position(
        symbol="BTCUSDT",
        side="LONG",
        quantity=Decimal("0.01"),
        entry_price=Decimal("45000.00"),
        leverage=10,
        stop_loss=Decimal("44000.00"),
        take_profit=Decimal("46000.00"),
    )

    assert position is not None
    assert position.symbol == "BTCUSDT"
    assert position.side.value == "LONG"
    assert position.quantity == Decimal("0.01")
    assert position.entry_price == Decimal("45000.00")
    assert position.leverage == 10
    assert position.stop_loss == Decimal("44000.00")
    assert position.take_profit == Decimal("46000.00")
    assert position.status.value == "OPEN"
    assert position.current_price == Decimal("45000.00")  # Initialized to entry price

    # Check P&L calculations
    assert position.unrealized_pnl_chf == Decimal("0")  # No price change yet
    assert position.position_value_chf is not None
    assert position.position_value_chf > Decimal("0")


@pytest.mark.asyncio
async def test_create_position_no_stop_loss(position_service):
    """Test that position creation fails without stop loss."""
    with pytest.raises(ValidationError, match="Stop loss is REQUIRED"):
        await position_service.create_position(
            symbol="BTCUSDT",
            side="LONG",
            quantity=Decimal("0.01"),
            entry_price=Decimal("45000.00"),
            leverage=10,
            stop_loss=None,  # Missing required stop loss
        )


@pytest.mark.asyncio
async def test_create_position_invalid_leverage(position_service):
    """Test that position creation fails with invalid leverage."""
    # Leverage too low
    with pytest.raises(ValidationError):
        await position_service.create_position(
            symbol="BTCUSDT",
            side="LONG",
            quantity=Decimal("0.01"),
            entry_price=Decimal("45000.00"),
            leverage=3,  # Below minimum 5
            stop_loss=Decimal("44000.00"),
        )

    # Leverage too high
    with pytest.raises(ValidationError):
        await position_service.create_position(
            symbol="BTCUSDT",
            side="LONG",
            quantity=Decimal("0.01"),
            entry_price=Decimal("45000.00"),
            leverage=50,  # Above maximum 40
            stop_loss=Decimal("44000.00"),
        )


@pytest.mark.asyncio
async def test_create_position_invalid_symbol(position_service):
    """Test that position creation fails with invalid symbol."""
    with pytest.raises(ValidationError, match="Invalid symbol"):
        await position_service.create_position(
            symbol="FAKECOIN",
            side="LONG",
            quantity=Decimal("0.01"),
            entry_price=Decimal("45000.00"),
            leverage=10,
            stop_loss=Decimal("44000.00"),
        )


@pytest.mark.asyncio
async def test_create_position_wrong_side_stop_loss(position_service):
    """Test that stop loss must be on correct side of entry price."""
    # LONG position with stop loss above entry (wrong side)
    with pytest.raises(ValidationError, match="must be below entry price"):
        await position_service.create_position(
            symbol="BTCUSDT",
            side="LONG",
            quantity=Decimal("0.01"),
            entry_price=Decimal("45000.00"),
            leverage=10,
            stop_loss=Decimal("46000.00"),  # Above entry (wrong)
        )

    # SHORT position with stop loss below entry (wrong side)
    with pytest.raises(ValidationError, match="must be above entry price"):
        await position_service.create_position(
            symbol="BTCUSDT",
            side="SHORT",
            quantity=Decimal("0.01"),
            entry_price=Decimal("45000.00"),
            leverage=10,
            stop_loss=Decimal("44000.00"),  # Below entry (wrong)
        )


@pytest.mark.asyncio
async def test_create_position_exceeds_size_limit(position_service):
    """Test that position creation fails when exceeding size limit."""
    # Create position that exceeds 20% of capital
    with pytest.raises(RiskLimitError, match="exceeds maximum"):
        await position_service.create_position(
            symbol="BTCUSDT",
            side="LONG",
            quantity=Decimal("1.0"),  # Large quantity
            entry_price=Decimal("45000.00"),
            leverage=40,  # Max leverage to maximize position size
            stop_loss=Decimal("44000.00"),
        )


@pytest.mark.asyncio
async def test_create_position_exceeds_exposure_limit(position_service):
    """Test that position creation fails when exceeding total exposure limit."""
    # Create multiple positions to approach exposure limit
    # Position 1: 15% of capital
    position1 = await position_service.create_position(
        symbol="BTCUSDT",
        side="LONG",
        quantity=Decimal("0.008"),
        entry_price=Decimal("45000.00"),
        leverage=20,
        stop_loss=Decimal("44000.00"),
    )
    assert position1 is not None

    # Position 2: 15% of capital
    position2 = await position_service.create_position(
        symbol="ETHUSDT",
        side="LONG",
        quantity=Decimal("0.15"),
        entry_price=Decimal("2500.00"),
        leverage=20,
        stop_loss=Decimal("2400.00"),
    )
    assert position2 is not None

    # Position 3: 15% of capital
    position3 = await position_service.create_position(
        symbol="SOLUSDT",
        side="LONG",
        quantity=Decimal("1.5"),
        entry_price=Decimal("100.00"),
        leverage=20,
        stop_loss=Decimal("95.00"),
    )
    assert position3 is not None

    # Position 4: 15% of capital
    position4 = await position_service.create_position(
        symbol="BNBUSDT",
        side="LONG",
        quantity=Decimal("0.3"),
        entry_price=Decimal("300.00"),
        leverage=20,
        stop_loss=Decimal("290.00"),
    )
    assert position4 is not None

    # Position 5: 15% of capital - should fail (total would be 75%)
    # But next position would exceed 80% limit
    with pytest.raises(RiskLimitError, match="would exceed maximum"):
        await position_service.create_position(
            symbol="ADAUSDT",
            side="LONG",
            quantity=Decimal("10.0"),
            entry_price=Decimal("0.50"),
            leverage=30,
            stop_loss=Decimal("0.48"),
        )


# ============================================================================
# Position Update Tests
# ============================================================================


@pytest.mark.asyncio
async def test_update_position_price(position_service):
    """Test updating position price and P&L calculation."""
    # Create position
    position = await position_service.create_position(
        symbol="BTCUSDT",
        side="LONG",
        quantity=Decimal("0.01"),
        entry_price=Decimal("45000.00"),
        leverage=10,
        stop_loss=Decimal("44000.00"),
    )

    # Update price (profit)
    updated = await position_service.update_position_price(
        position_id=position.id, current_price=Decimal("45500.00")
    )

    assert updated.current_price == Decimal("45500.00")
    assert updated.unrealized_pnl_usd > Decimal("0")  # Profit
    assert updated.unrealized_pnl_chf > Decimal("0")  # Profit in CHF
    assert updated.unrealized_pnl_pct > Decimal("0")  # Positive percentage

    # Expected: (45500 - 45000) * 0.01 * 10 = 50 USD
    expected_pnl_usd = Decimal("50.00")
    assert abs(updated.unrealized_pnl_usd - expected_pnl_usd) < Decimal("0.01")


@pytest.mark.asyncio
async def test_update_position_price_loss(position_service):
    """Test updating position price with loss."""
    # Create position
    position = await position_service.create_position(
        symbol="BTCUSDT",
        side="LONG",
        quantity=Decimal("0.01"),
        entry_price=Decimal("45000.00"),
        leverage=10,
        stop_loss=Decimal("44000.00"),
    )

    # Update price (loss)
    updated = await position_service.update_position_price(
        position_id=position.id, current_price=Decimal("44500.00")
    )

    assert updated.current_price == Decimal("44500.00")
    assert updated.unrealized_pnl_usd < Decimal("0")  # Loss
    assert updated.unrealized_pnl_chf < Decimal("0")  # Loss in CHF
    assert updated.unrealized_pnl_pct < Decimal("0")  # Negative percentage

    # Expected: (44500 - 45000) * 0.01 * 10 = -50 USD
    expected_pnl_usd = Decimal("-50.00")
    assert abs(updated.unrealized_pnl_usd - expected_pnl_usd) < Decimal("0.01")


@pytest.mark.asyncio
async def test_update_position_short_profit(position_service):
    """Test updating SHORT position price with profit."""
    # Create SHORT position
    position = await position_service.create_position(
        symbol="BTCUSDT",
        side="SHORT",
        quantity=Decimal("0.01"),
        entry_price=Decimal("45000.00"),
        leverage=10,
        stop_loss=Decimal("46000.00"),  # Above entry for SHORT
    )

    # Update price (price goes down = profit for SHORT)
    updated = await position_service.update_position_price(
        position_id=position.id, current_price=Decimal("44500.00")
    )

    assert updated.current_price == Decimal("44500.00")
    assert updated.unrealized_pnl_usd > Decimal("0")  # Profit
    assert updated.unrealized_pnl_chf > Decimal("0")  # Profit in CHF

    # Expected: (45000 - 44500) * 0.01 * 10 = 50 USD
    expected_pnl_usd = Decimal("50.00")
    assert abs(updated.unrealized_pnl_usd - expected_pnl_usd) < Decimal("0.01")


@pytest.mark.asyncio
async def test_update_nonexistent_position(position_service):
    """Test updating position that doesn't exist."""
    fake_id = uuid4()
    with pytest.raises(PositionNotFoundError):
        await position_service.update_position_price(
            position_id=fake_id, current_price=Decimal("45000.00")
        )


# ============================================================================
# Position Closure Tests
# ============================================================================


@pytest.mark.asyncio
async def test_close_position_profit(position_service):
    """Test closing position with profit."""
    # Create position
    position = await position_service.create_position(
        symbol="BTCUSDT",
        side="LONG",
        quantity=Decimal("0.01"),
        entry_price=Decimal("45000.00"),
        leverage=10,
        stop_loss=Decimal("44000.00"),
    )

    # Close with profit
    closed = await position_service.close_position(
        position_id=position.id, close_price=Decimal("46000.00"), reason="take_profit"
    )

    assert closed.status.value == "CLOSED"
    assert closed.current_price == Decimal("46000.00")
    assert closed.pnl_chf > Decimal("0")  # Profit
    assert closed.closed_at is not None

    # Expected: (46000 - 45000) * 0.01 * 10 = 100 USD
    # 100 USD * 0.85 CHF/USD = 85 CHF
    expected_pnl_usd = Decimal("100.00")
    expected_pnl_chf = expected_pnl_usd * Decimal("0.85")
    assert abs(closed.pnl_chf - expected_pnl_chf) < Decimal("0.01")


@pytest.mark.asyncio
async def test_close_position_loss(position_service):
    """Test closing position with loss."""
    # Create position
    position = await position_service.create_position(
        symbol="BTCUSDT",
        side="LONG",
        quantity=Decimal("0.01"),
        entry_price=Decimal("45000.00"),
        leverage=10,
        stop_loss=Decimal("44000.00"),
    )

    # Close with loss
    closed = await position_service.close_position(
        position_id=position.id, close_price=Decimal("44000.00"), reason="stop_loss"
    )

    assert closed.status.value == "CLOSED"
    assert closed.current_price == Decimal("44000.00")
    assert closed.pnl_chf < Decimal("0")  # Loss
    assert closed.closed_at is not None

    # Expected: (44000 - 45000) * 0.01 * 10 = -100 USD
    # -100 USD * 0.85 CHF/USD = -85 CHF
    expected_pnl_usd = Decimal("-100.00")
    expected_pnl_chf = expected_pnl_usd * Decimal("0.85")
    assert abs(closed.pnl_chf - expected_pnl_chf) < Decimal("0.01")


@pytest.mark.asyncio
async def test_close_position_short_profit(position_service):
    """Test closing SHORT position with profit."""
    # Create SHORT position
    position = await position_service.create_position(
        symbol="BTCUSDT",
        side="SHORT",
        quantity=Decimal("0.01"),
        entry_price=Decimal("45000.00"),
        leverage=10,
        stop_loss=Decimal("46000.00"),
    )

    # Close with profit (price went down)
    closed = await position_service.close_position(
        position_id=position.id, close_price=Decimal("44000.00"), reason="take_profit"
    )

    assert closed.status.value == "CLOSED"
    assert closed.pnl_chf > Decimal("0")  # Profit

    # Expected: (45000 - 44000) * 0.01 * 10 = 100 USD
    expected_pnl_usd = Decimal("100.00")
    expected_pnl_chf = expected_pnl_usd * Decimal("0.85")
    assert abs(closed.pnl_chf - expected_pnl_chf) < Decimal("0.01")


@pytest.mark.asyncio
async def test_close_nonexistent_position(position_service):
    """Test closing position that doesn't exist."""
    fake_id = uuid4()
    with pytest.raises(PositionNotFoundError):
        await position_service.close_position(
            position_id=fake_id, close_price=Decimal("45000.00"), reason="manual"
        )


# ============================================================================
# Stop-Loss Detection Tests
# ============================================================================


@pytest.mark.asyncio
async def test_check_stop_loss_triggers_long(position_service):
    """Test stop-loss detection for LONG position."""
    # Create LONG position
    position = await position_service.create_position(
        symbol="BTCUSDT",
        side="LONG",
        quantity=Decimal("0.01"),
        entry_price=Decimal("45000.00"),
        leverage=10,
        stop_loss=Decimal("44000.00"),
    )

    # Update price above stop loss (not triggered)
    await position_service.update_position_price(position.id, Decimal("45500.00"))
    triggered = await position_service.check_stop_loss_triggers()
    assert len(triggered) == 0

    # Update price at stop loss (triggered)
    await position_service.update_position_price(position.id, Decimal("44000.00"))
    triggered = await position_service.check_stop_loss_triggers()
    assert len(triggered) == 1
    assert triggered[0].id == position.id
    assert triggered[0].is_stop_loss_triggered is True


@pytest.mark.asyncio
async def test_check_stop_loss_triggers_short(position_service):
    """Test stop-loss detection for SHORT position."""
    # Create SHORT position
    position = await position_service.create_position(
        symbol="BTCUSDT",
        side="SHORT",
        quantity=Decimal("0.01"),
        entry_price=Decimal("45000.00"),
        leverage=10,
        stop_loss=Decimal("46000.00"),  # Above entry for SHORT
    )

    # Update price below stop loss (not triggered)
    await position_service.update_position_price(position.id, Decimal("44500.00"))
    triggered = await position_service.check_stop_loss_triggers()
    assert len(triggered) == 0

    # Update price at stop loss (triggered)
    await position_service.update_position_price(position.id, Decimal("46000.00"))
    triggered = await position_service.check_stop_loss_triggers()
    assert len(triggered) == 1
    assert triggered[0].id == position.id
    assert triggered[0].is_stop_loss_triggered is True


@pytest.mark.asyncio
async def test_check_take_profit_triggers(position_service):
    """Test take-profit detection."""
    # Create position with take profit
    position = await position_service.create_position(
        symbol="BTCUSDT",
        side="LONG",
        quantity=Decimal("0.01"),
        entry_price=Decimal("45000.00"),
        leverage=10,
        stop_loss=Decimal("44000.00"),
        take_profit=Decimal("46000.00"),
    )

    # Update price below take profit (not triggered)
    await position_service.update_position_price(position.id, Decimal("45500.00"))
    triggered = await position_service.check_take_profit_triggers()
    assert len(triggered) == 0

    # Update price at take profit (triggered)
    await position_service.update_position_price(position.id, Decimal("46000.00"))
    triggered = await position_service.check_take_profit_triggers()
    assert len(triggered) == 1
    assert triggered[0].id == position.id
    assert triggered[0].is_take_profit_triggered is True


# ============================================================================
# Daily P&L Tests
# ============================================================================


@pytest.mark.asyncio
async def test_daily_pnl_with_open_positions(position_service):
    """Test daily P&L calculation with open positions."""
    # Create position
    position = await position_service.create_position(
        symbol="BTCUSDT",
        side="LONG",
        quantity=Decimal("0.01"),
        entry_price=Decimal("45000.00"),
        leverage=10,
        stop_loss=Decimal("44000.00"),
    )

    # Update price to generate unrealized P&L
    await position_service.update_position_price(position.id, Decimal("45500.00"))

    # Get daily P&L
    summary = await position_service.get_daily_pnl()

    assert summary.date == Date.today()
    assert summary.open_positions_count == 1
    assert summary.closed_positions_count == 0
    assert summary.unrealized_pnl_chf > Decimal("0")  # Profit
    assert summary.realized_pnl_chf == Decimal("0")  # No closed positions
    assert summary.total_pnl_chf == summary.unrealized_pnl_chf


@pytest.mark.asyncio
async def test_daily_pnl_with_closed_positions(position_service):
    """Test daily P&L calculation with closed positions."""
    # Create and close position with profit
    position = await position_service.create_position(
        symbol="BTCUSDT",
        side="LONG",
        quantity=Decimal("0.01"),
        entry_price=Decimal("45000.00"),
        leverage=10,
        stop_loss=Decimal("44000.00"),
    )

    await position_service.close_position(
        position_id=position.id, close_price=Decimal("46000.00"), reason="take_profit"
    )

    # Get daily P&L
    summary = await position_service.get_daily_pnl()

    assert summary.date == Date.today()
    assert summary.open_positions_count == 0
    assert summary.closed_positions_count == 1
    assert summary.realized_pnl_chf > Decimal("0")  # Profit
    assert summary.unrealized_pnl_chf == Decimal("0")  # No open positions
    assert summary.total_pnl_chf == summary.realized_pnl_chf


@pytest.mark.asyncio
async def test_circuit_breaker_detection(position_service):
    """Test circuit breaker detection when daily loss exceeds threshold."""
    # Create position
    position = await position_service.create_position(
        symbol="BTCUSDT",
        side="LONG",
        quantity=Decimal("0.1"),  # Larger position
        entry_price=Decimal("45000.00"),
        leverage=10,
        stop_loss=Decimal("40000.00"),
    )

    # Close with large loss (simulating circuit breaker scenario)
    await position_service.close_position(
        position_id=position.id, close_price=Decimal("40000.00"), reason="stop_loss"
    )

    # Get daily P&L
    summary = await position_service.get_daily_pnl()

    # Check if circuit breaker triggered
    # Loss should be: (40000 - 45000) * 0.1 * 10 = -5000 USD = -4250 CHF
    # Threshold is -183.89 CHF, so this should trigger
    assert summary.total_pnl_chf < CIRCUIT_BREAKER_LOSS_CHF
    assert summary.is_circuit_breaker_triggered is True


# ============================================================================
# Query Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_position_by_id(position_service):
    """Test retrieving position by ID."""
    # Create position
    created = await position_service.create_position(
        symbol="BTCUSDT",
        side="LONG",
        quantity=Decimal("0.01"),
        entry_price=Decimal("45000.00"),
        leverage=10,
        stop_loss=Decimal("44000.00"),
    )

    # Retrieve position
    retrieved = await position_service.get_position_by_id(created.id)

    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.symbol == "BTCUSDT"
    assert retrieved.side.value == "LONG"


@pytest.mark.asyncio
async def test_get_position_by_id_not_found(position_service):
    """Test retrieving nonexistent position returns None."""
    fake_id = uuid4()
    position = await position_service.get_position_by_id(fake_id)
    assert position is None


@pytest.mark.asyncio
async def test_get_active_positions(position_service):
    """Test retrieving all active positions."""
    # Create multiple positions
    position1 = await position_service.create_position(
        symbol="BTCUSDT",
        side="LONG",
        quantity=Decimal("0.01"),
        entry_price=Decimal("45000.00"),
        leverage=10,
        stop_loss=Decimal("44000.00"),
    )

    position2 = await position_service.create_position(
        symbol="ETHUSDT",
        side="SHORT",
        quantity=Decimal("0.1"),
        entry_price=Decimal("2500.00"),
        leverage=10,
        stop_loss=Decimal("2600.00"),
    )

    # Close one position
    await position_service.close_position(position1.id, Decimal("45500.00"), "manual")

    # Get active positions
    active = await position_service.get_active_positions()

    assert len(active) == 1
    assert active[0].id == position2.id
    assert active[0].status.value == "OPEN"


@pytest.mark.asyncio
async def test_get_active_positions_by_symbol(position_service):
    """Test retrieving active positions filtered by symbol."""
    # Create positions for different symbols
    await position_service.create_position(
        symbol="BTCUSDT",
        side="LONG",
        quantity=Decimal("0.01"),
        entry_price=Decimal("45000.00"),
        leverage=10,
        stop_loss=Decimal("44000.00"),
    )

    await position_service.create_position(
        symbol="ETHUSDT",
        side="LONG",
        quantity=Decimal("0.1"),
        entry_price=Decimal("2500.00"),
        leverage=10,
        stop_loss=Decimal("2400.00"),
    )

    # Get active positions for BTC
    btc_positions = await position_service.get_active_positions(symbol="BTCUSDT")
    assert len(btc_positions) == 1
    assert btc_positions[0].symbol == "BTCUSDT"

    # Get active positions for ETH
    eth_positions = await position_service.get_active_positions(symbol="ETHUSDT")
    assert len(eth_positions) == 1
    assert eth_positions[0].symbol == "ETHUSDT"


# ============================================================================
# Statistics Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_total_exposure(position_service):
    """Test calculating total exposure across positions."""
    # Create multiple positions
    await position_service.create_position(
        symbol="BTCUSDT",
        side="LONG",
        quantity=Decimal("0.01"),
        entry_price=Decimal("45000.00"),
        leverage=10,
        stop_loss=Decimal("44000.00"),
    )

    await position_service.create_position(
        symbol="ETHUSDT",
        side="LONG",
        quantity=Decimal("0.1"),
        entry_price=Decimal("2500.00"),
        leverage=10,
        stop_loss=Decimal("2400.00"),
    )

    # Get total exposure
    exposure = await position_service.get_total_exposure()

    assert exposure > Decimal("0")
    assert exposure <= MAX_TOTAL_EXPOSURE_CHF  # Within limit


@pytest.mark.asyncio
async def test_get_statistics(position_service):
    """Test getting position statistics."""
    # Create and close some positions
    position1 = await position_service.create_position(
        symbol="BTCUSDT",
        side="LONG",
        quantity=Decimal("0.01"),
        entry_price=Decimal("45000.00"),
        leverage=10,
        stop_loss=Decimal("44000.00"),
    )

    await position_service.create_position(
        symbol="ETHUSDT",
        side="LONG",
        quantity=Decimal("0.1"),
        entry_price=Decimal("2500.00"),
        leverage=10,
        stop_loss=Decimal("2400.00"),
    )

    # Close one with profit
    await position_service.close_position(
        position1.id, Decimal("46000.00"), "take_profit"
    )

    # Get statistics
    stats = await position_service.get_statistics()

    assert stats.total_positions == 2
    assert stats.open_positions == 1
    assert stats.closed_positions == 1
    assert stats.total_realized_pnl_chf > Decimal("0")  # Profit from closed position
    assert stats.total_exposure_chf > Decimal("0")  # From open position


# ============================================================================
# Concurrent Operations Tests
# ============================================================================


@pytest.mark.asyncio
async def test_concurrent_price_updates(position_service):
    """Test concurrent price updates on multiple positions."""
    # Create multiple positions
    positions = []
    for _i in range(5):
        position = await position_service.create_position(
            symbol="BTCUSDT",
            side="LONG",
            quantity=Decimal("0.001"),
            entry_price=Decimal("45000.00"),
            leverage=5,
            stop_loss=Decimal("44000.00"),
        )
        positions.append(position)

    # Update all positions concurrently
    tasks = [
        position_service.update_position_price(p.id, Decimal("45500.00"))
        for p in positions
    ]
    updated = await asyncio.gather(*tasks)

    # Verify all updates succeeded
    assert len(updated) == 5
    for position in updated:
        assert position.current_price == Decimal("45500.00")


@pytest.mark.asyncio
async def test_bulk_update_prices(position_service):
    """Test bulk price update utility function."""
    # Create positions for different symbols
    await position_service.create_position(
        symbol="BTCUSDT",
        side="LONG",
        quantity=Decimal("0.01"),
        entry_price=Decimal("45000.00"),
        leverage=10,
        stop_loss=Decimal("44000.00"),
    )

    await position_service.create_position(
        symbol="ETHUSDT",
        side="LONG",
        quantity=Decimal("0.1"),
        entry_price=Decimal("2500.00"),
        leverage=10,
        stop_loss=Decimal("2400.00"),
    )

    # Bulk update prices
    price_updates = {"BTCUSDT": Decimal("45500.00"), "ETHUSDT": Decimal("2550.00")}
    updated = await bulk_update_prices(position_service, price_updates)

    assert len(updated) == 2
    for position in updated.values():
        assert position.current_price == price_updates[position.symbol]


# ============================================================================
# Edge Cases
# ============================================================================


@pytest.mark.asyncio
async def test_zero_pnl(position_service):
    """Test position with zero P&L (entry price = current price)."""
    position = await position_service.create_position(
        symbol="BTCUSDT",
        side="LONG",
        quantity=Decimal("0.01"),
        entry_price=Decimal("45000.00"),
        leverage=10,
        stop_loss=Decimal("44000.00"),
    )

    # Price hasn't changed yet
    assert position.unrealized_pnl_chf == Decimal("0")
    assert position.unrealized_pnl_pct == Decimal("0")


@pytest.mark.asyncio
async def test_very_high_leverage(position_service):
    """Test position with maximum leverage."""
    position = await position_service.create_position(
        symbol="BTCUSDT",
        side="LONG",
        quantity=Decimal("0.001"),
        entry_price=Decimal("45000.00"),
        leverage=40,  # Maximum
        stop_loss=Decimal("44000.00"),
    )

    # Update price
    updated = await position_service.update_position_price(
        position.id, Decimal("45100.00")
    )

    # With 40x leverage, small price change should result in large % P&L
    # (45100 - 45000) / 45000 * 40 * 100 = 8.89%
    assert updated.unrealized_pnl_pct > Decimal("8")


@pytest.mark.asyncio
async def test_decimal_precision(position_service):
    """Test that all decimal values maintain 8-digit precision."""
    position = await position_service.create_position(
        symbol="BTCUSDT",
        side="LONG",
        quantity=Decimal("0.01234567"),
        entry_price=Decimal("45123.45678901"),
        leverage=10,
        stop_loss=Decimal("44000.00"),
    )

    # Verify precision maintained
    assert str(position.quantity) == "0.01234567"
    assert len(str(position.entry_price).split(".")[-1]) <= 8
