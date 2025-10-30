"""
Unit Tests for Risk Manager Circuit Breaker

Tests comprehensive circuit breaker functionality including:
- Daily loss limit monitoring
- Emergency position closure
- Manual reset requirements
- Alert callbacks
- Daily reset scheduling

Author: Validation Engineer Team 2
Date: 2025-10-30
Sprint: 3, Stream A
"""

import asyncio
from datetime import time
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from workspace.features.risk_manager import CircuitBreaker
from workspace.features.risk_manager.models import (
    CircuitBreakerState,
    CircuitBreakerStatus,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_trade_executor():
    """Mock trade executor"""
    executor = AsyncMock()
    executor.get_open_positions = AsyncMock(return_value=[])
    executor.close_position = AsyncMock()
    return executor


@pytest.fixture
def circuit_breaker(mock_trade_executor):
    """Circuit breaker with default settings"""
    return CircuitBreaker(
        starting_balance_chf=Decimal("2626.96"),
        max_daily_loss_chf=Decimal("-183.89"),
        max_daily_loss_pct=Decimal("-0.07"),
        reset_time_utc=time(0, 0),
        trade_executor=mock_trade_executor,
    )


@pytest.fixture
def mock_position():
    """Mock position object"""
    position = MagicMock()
    position.id = "pos_123"
    position.symbol = "BTC/USDT:USDT"
    return position


# ============================================================================
# Initialization Tests
# ============================================================================


def test_circuit_breaker_initialization(circuit_breaker):
    """Test circuit breaker initializes with correct defaults"""
    assert circuit_breaker.starting_balance_chf == Decimal("2626.96")
    assert circuit_breaker.max_daily_loss_chf == Decimal("-183.89")
    assert circuit_breaker.max_daily_loss_pct == Decimal("-0.07")
    assert circuit_breaker.status.state == CircuitBreakerState.ACTIVE
    assert circuit_breaker.status.daily_pnl_chf == Decimal("0")


def test_circuit_breaker_custom_settings():
    """Test circuit breaker with custom settings"""
    cb = CircuitBreaker(
        starting_balance_chf=Decimal("5000.00"),
        max_daily_loss_chf=Decimal("-500.00"),
        max_daily_loss_pct=Decimal("-0.10"),
    )

    assert cb.starting_balance_chf == Decimal("5000.00")
    assert cb.max_daily_loss_chf == Decimal("-500.00")
    assert cb.status.starting_balance_chf == Decimal("5000.00")


# ============================================================================
# Daily Loss Checking Tests
# ============================================================================


@pytest.mark.asyncio
async def test_check_daily_loss_within_limit(circuit_breaker):
    """Test daily loss check when within limit"""
    status = await circuit_breaker.check_daily_loss(Decimal("-50.00"))

    assert status.state == CircuitBreakerState.ACTIVE
    assert not status.is_tripped()
    assert status.daily_pnl_chf == Decimal("-50.00")


@pytest.mark.asyncio
async def test_check_daily_loss_positive_pnl(circuit_breaker):
    """Test daily loss check with positive P&L"""
    status = await circuit_breaker.check_daily_loss(Decimal("100.00"))

    assert status.state == CircuitBreakerState.ACTIVE
    assert not status.is_tripped()
    assert status.daily_pnl_chf == Decimal("100.00")


@pytest.mark.asyncio
async def test_check_daily_loss_at_limit(circuit_breaker):
    """Test daily loss check at exact limit"""
    # At limit but not exceeded
    status = await circuit_breaker.check_daily_loss(Decimal("-183.89"))

    # Should NOT trip (at limit, not exceeded)
    assert status.state == CircuitBreakerState.ACTIVE
    assert not status.is_tripped()


@pytest.mark.asyncio
async def test_check_daily_loss_exceeds_limit_trips(
    circuit_breaker, mock_trade_executor
):
    """Test circuit breaker trips when loss exceeds limit"""
    # Exceed limit by CHF 0.01
    status = await circuit_breaker.check_daily_loss(Decimal("-183.90"))

    assert status.state == CircuitBreakerState.MANUAL_RESET_REQUIRED
    assert status.is_tripped() or status.is_manual_reset_required()
    assert status.manual_reset_required
    assert status.manual_reset_token is not None


@pytest.mark.asyncio
async def test_check_daily_loss_already_tripped(circuit_breaker):
    """Test check when circuit breaker already tripped"""
    # Trip it first
    await circuit_breaker.check_daily_loss(Decimal("-200.00"))

    # Check again
    status = await circuit_breaker.check_daily_loss(Decimal("-210.00"))

    # Should remain in manual reset state
    assert status.state == CircuitBreakerState.MANUAL_RESET_REQUIRED
    assert status.is_manual_reset_required()


@pytest.mark.asyncio
async def test_trip_closes_positions(
    circuit_breaker, mock_trade_executor, mock_position
):
    """Test circuit breaker closes all positions when tripped"""
    mock_trade_executor.get_open_positions.return_value = [mock_position]

    await circuit_breaker.check_daily_loss(Decimal("-200.00"))

    # Should attempt to close position
    mock_trade_executor.get_open_positions.assert_called_once()
    mock_trade_executor.close_position.assert_called_once_with(
        position_id="pos_123",
        reason="circuit_breaker_triggered",
    )


@pytest.mark.asyncio
async def test_trip_continues_without_executor(circuit_breaker):
    """Test circuit breaker trips even without trade executor"""
    circuit_breaker.trade_executor = None

    status = await circuit_breaker.check_daily_loss(Decimal("-200.00"))

    # Should still trip
    assert status.state == CircuitBreakerState.MANUAL_RESET_REQUIRED


@pytest.mark.asyncio
async def test_trip_continues_on_close_error(circuit_breaker, mock_trade_executor):
    """Test circuit breaker trips even if position close fails"""
    mock_trade_executor.get_open_positions.side_effect = Exception("Close failed")

    status = await circuit_breaker.check_daily_loss(Decimal("-200.00"))

    # Should still complete trip process
    assert status.state == CircuitBreakerState.MANUAL_RESET_REQUIRED


# ============================================================================
# Manual Reset Tests
# ============================================================================


@pytest.mark.asyncio
async def test_manual_reset_success(circuit_breaker):
    """Test successful manual reset"""
    # Trip circuit breaker
    await circuit_breaker.check_daily_loss(Decimal("-200.00"))
    token = circuit_breaker.status.manual_reset_token

    # Reset with correct token
    result = await circuit_breaker.manual_reset(token)

    assert result is True
    assert circuit_breaker.status.state == CircuitBreakerState.ACTIVE
    assert not circuit_breaker.status.manual_reset_required


@pytest.mark.asyncio
async def test_manual_reset_invalid_token(circuit_breaker):
    """Test manual reset with invalid token"""
    # Trip circuit breaker
    await circuit_breaker.check_daily_loss(Decimal("-200.00"))

    # Reset with wrong token
    result = await circuit_breaker.manual_reset("wrong_token")

    assert result is False
    assert circuit_breaker.status.state == CircuitBreakerState.MANUAL_RESET_REQUIRED


@pytest.mark.asyncio
async def test_manual_reset_not_required(circuit_breaker):
    """Test manual reset when not in manual reset state"""
    result = await circuit_breaker.manual_reset("any_token")

    assert result is False


# ============================================================================
# Daily Reset Tests
# ============================================================================


@pytest.mark.asyncio
async def test_daily_reset(circuit_breaker):
    """Test daily automatic reset"""
    # Set some daily P&L
    await circuit_breaker.update_daily_pnl(Decimal("-50.00"))
    await circuit_breaker.update_trade_stats(is_winning_trade=True)

    # Perform daily reset
    await circuit_breaker.daily_reset()

    assert circuit_breaker.status.state == CircuitBreakerState.ACTIVE
    assert circuit_breaker.status.daily_pnl_chf == Decimal("0")
    assert circuit_breaker.status.daily_trade_count == 0
    assert circuit_breaker.status.last_reset_at is not None


@pytest.mark.asyncio
async def test_daily_reset_after_trip(circuit_breaker):
    """Test daily reset after circuit breaker tripped"""
    # Trip circuit breaker
    await circuit_breaker.check_daily_loss(Decimal("-200.00"))

    # Daily reset
    await circuit_breaker.daily_reset()

    # Should be reset to ACTIVE
    assert circuit_breaker.status.state == CircuitBreakerState.ACTIVE
    assert circuit_breaker.status.daily_pnl_chf == Decimal("0")


# ============================================================================
# Trade Statistics Tests
# ============================================================================


@pytest.mark.asyncio
async def test_update_trade_stats_winning(circuit_breaker):
    """Test updating trade statistics for winning trade"""
    await circuit_breaker.update_trade_stats(is_winning_trade=True)

    assert circuit_breaker.status.daily_trade_count == 1
    assert circuit_breaker.status.daily_winning_trades == 1
    assert circuit_breaker.status.daily_losing_trades == 0


@pytest.mark.asyncio
async def test_update_trade_stats_losing(circuit_breaker):
    """Test updating trade statistics for losing trade"""
    await circuit_breaker.update_trade_stats(is_winning_trade=False)

    assert circuit_breaker.status.daily_trade_count == 1
    assert circuit_breaker.status.daily_winning_trades == 0
    assert circuit_breaker.status.daily_losing_trades == 1


@pytest.mark.asyncio
async def test_update_trade_stats_multiple(circuit_breaker):
    """Test updating trade statistics multiple times"""
    await circuit_breaker.update_trade_stats(is_winning_trade=True)
    await circuit_breaker.update_trade_stats(is_winning_trade=False)
    await circuit_breaker.update_trade_stats(is_winning_trade=True)

    assert circuit_breaker.status.daily_trade_count == 3
    assert circuit_breaker.status.daily_winning_trades == 2
    assert circuit_breaker.status.daily_losing_trades == 1


# ============================================================================
# Daily P&L Update Tests
# ============================================================================


@pytest.mark.asyncio
async def test_update_daily_pnl(circuit_breaker):
    """Test updating daily P&L"""
    await circuit_breaker.update_daily_pnl(Decimal("-75.00"))

    assert circuit_breaker.status.daily_pnl_chf == Decimal("-75.00")
    assert circuit_breaker.status.current_balance_chf == Decimal("2551.96")


@pytest.mark.asyncio
async def test_update_daily_pnl_positive(circuit_breaker):
    """Test updating daily P&L with profit"""
    await circuit_breaker.update_daily_pnl(Decimal("100.00"))

    assert circuit_breaker.status.daily_pnl_chf == Decimal("100.00")
    assert circuit_breaker.status.current_balance_chf == Decimal("2726.96")


@pytest.mark.asyncio
async def test_update_daily_pnl_triggers_trip(circuit_breaker):
    """Test that updating P&L can trigger circuit breaker"""
    await circuit_breaker.update_daily_pnl(Decimal("-200.00"))

    assert circuit_breaker.status.state == CircuitBreakerState.MANUAL_RESET_REQUIRED


# ============================================================================
# Alert Callback Tests
# ============================================================================


@pytest.mark.asyncio
async def test_register_alert_callback(circuit_breaker):
    """Test registering alert callback"""
    alert_received = []

    async def callback(level: str, message: str):
        alert_received.append((level, message))

    circuit_breaker.register_alert_callback(callback)

    # Trigger alert
    await circuit_breaker._send_alert("info", "Test message")

    assert len(alert_received) == 1
    assert alert_received[0] == ("info", "Test message")


@pytest.mark.asyncio
async def test_multiple_alert_callbacks(circuit_breaker):
    """Test multiple alert callbacks"""
    alerts1 = []
    alerts2 = []

    async def callback1(level: str, message: str):
        alerts1.append((level, message))

    async def callback2(level: str, message: str):
        alerts2.append((level, message))

    circuit_breaker.register_alert_callback(callback1)
    circuit_breaker.register_alert_callback(callback2)

    await circuit_breaker._send_alert("warning", "Test")

    assert len(alerts1) == 1
    assert len(alerts2) == 1


@pytest.mark.asyncio
async def test_alert_callback_on_trip(circuit_breaker):
    """Test alert callbacks are called when circuit breaker trips"""
    alerts = []

    async def callback(level: str, message: str):
        alerts.append((level, message))

    circuit_breaker.register_alert_callback(callback)

    await circuit_breaker.check_daily_loss(Decimal("-200.00"))

    # Should have received multiple alerts (trip + manual reset required)
    assert len(alerts) >= 2
    assert any("TRIPPED" in msg for _, msg in alerts)


@pytest.mark.asyncio
async def test_alert_callback_error_handling(circuit_breaker):
    """Test alert callback error handling"""

    async def bad_callback(level: str, message: str):
        raise Exception("Callback error")

    circuit_breaker.register_alert_callback(bad_callback)

    # Should not raise exception
    await circuit_breaker._send_alert("info", "Test")


# ============================================================================
# Status Query Tests
# ============================================================================


def test_get_status(circuit_breaker):
    """Test getting circuit breaker status"""
    status = circuit_breaker.get_status()

    assert isinstance(status, CircuitBreakerStatus)
    assert status.state == CircuitBreakerState.ACTIVE


def test_is_trading_allowed_active(circuit_breaker):
    """Test trading allowed when active"""
    assert circuit_breaker.is_trading_allowed() is True


@pytest.mark.asyncio
async def test_is_trading_allowed_tripped(circuit_breaker):
    """Test trading not allowed when tripped"""
    await circuit_breaker.check_daily_loss(Decimal("-200.00"))

    assert circuit_breaker.is_trading_allowed() is False


# ============================================================================
# Daily Reset Scheduler Tests
# ============================================================================


def test_is_reset_time_exact(circuit_breaker):
    """Test reset time detection at exact time"""
    circuit_breaker.reset_time_utc = time(12, 0)
    current_time = time(12, 0)

    assert circuit_breaker._is_reset_time(current_time) is True


def test_is_reset_time_within_minute(circuit_breaker):
    """Test reset time detection within 1 minute"""
    circuit_breaker.reset_time_utc = time(12, 0)
    current_time = time(12, 1)

    assert circuit_breaker._is_reset_time(current_time) is True


def test_is_reset_time_outside_window(circuit_breaker):
    """Test reset time detection outside window"""
    circuit_breaker.reset_time_utc = time(12, 0)
    current_time = time(12, 5)

    assert circuit_breaker._is_reset_time(current_time) is False


@pytest.mark.asyncio
async def test_daily_reset_scheduler_basic(circuit_breaker):
    """Test daily reset scheduler (basic logic)"""
    # Mock the _is_reset_time to return True immediately
    circuit_breaker._is_reset_time = MagicMock(return_value=True)

    # Track if daily_reset was called
    reset_called = []

    original_daily_reset = circuit_breaker.daily_reset

    async def mock_daily_reset():
        reset_called.append(True)
        await original_daily_reset()

    circuit_breaker.daily_reset = mock_daily_reset

    # Run scheduler for a short time
    task = asyncio.create_task(circuit_breaker.start_daily_reset_scheduler())

    # Wait a bit for scheduler to run
    await asyncio.sleep(0.2)

    # Cancel scheduler
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Should have called daily_reset at least once
    assert len(reset_called) >= 1


# ============================================================================
# Reset Token Generation Tests
# ============================================================================


def test_generate_reset_token(circuit_breaker):
    """Test reset token generation"""
    token1 = circuit_breaker._generate_reset_token()
    token2 = circuit_breaker._generate_reset_token()

    assert isinstance(token1, str)
    assert len(token1) == 16  # 8 bytes * 2 hex chars
    assert token1 != token2  # Should be unique


# ============================================================================
# Circuit Breaker Status Model Tests
# ============================================================================


def test_circuit_breaker_status_should_trip_true():
    """Test should_trip returns True when limit exceeded"""
    status = CircuitBreakerStatus(
        state=CircuitBreakerState.ACTIVE,
        daily_pnl_chf=Decimal("-200.00"),
        daily_loss_limit_chf=Decimal("-183.89"),
    )

    assert status.should_trip() is True


def test_circuit_breaker_status_should_trip_false():
    """Test should_trip returns False when within limit"""
    status = CircuitBreakerStatus(
        state=CircuitBreakerState.ACTIVE,
        daily_pnl_chf=Decimal("-100.00"),
        daily_loss_limit_chf=Decimal("-183.89"),
    )

    assert status.should_trip() is False


def test_circuit_breaker_status_loss_percentage():
    """Test loss percentage calculation"""
    status = CircuitBreakerStatus(
        state=CircuitBreakerState.ACTIVE,
        daily_pnl_chf=Decimal("-100.00"),
        starting_balance_chf=Decimal("2000.00"),
    )

    loss_pct = status.loss_percentage()
    assert loss_pct == Decimal("-5.00")  # -100 / 2000 * 100 = -5%


def test_circuit_breaker_status_remaining_allowance():
    """Test remaining loss allowance calculation"""
    status = CircuitBreakerStatus(
        state=CircuitBreakerState.ACTIVE,
        daily_pnl_chf=Decimal("-100.00"),
        daily_loss_limit_chf=Decimal("-183.89"),
        starting_balance_chf=Decimal("2626.96"),
    )

    remaining = status.remaining_loss_allowance_chf()
    assert remaining == Decimal("-83.89")  # -183.89 - (-100.00)


def test_circuit_breaker_status_summary():
    """Test status summary generation"""
    status = CircuitBreakerStatus(
        state=CircuitBreakerState.ACTIVE,
        daily_pnl_chf=Decimal("-50.00"),
        daily_loss_limit_chf=Decimal("-183.89"),
        starting_balance_chf=Decimal("2626.96"),
        daily_trade_count=5,
        daily_winning_trades=3,
        daily_losing_trades=2,
    )

    summary = status.status_summary()

    assert "Circuit Breaker: ACTIVE" in summary
    assert "CHF -50.00" in summary
    assert "Trades Today: 5" in summary


if __name__ == "__main__":
    pytest.main(
        [__file__, "-v", "--cov=workspace/features/risk_manager/circuit_breaker"]
    )
