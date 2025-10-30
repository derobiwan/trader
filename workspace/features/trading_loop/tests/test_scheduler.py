"""
Trading Scheduler Tests

Tests for 3-minute trading scheduler with state management and error recovery.

Author: Trading Loop Implementation Team
Date: 2025-10-28
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from workspace.features.trading_loop.scheduler import SchedulerState, TradingScheduler

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_cycle_callback():
    """Mock cycle callback"""
    return AsyncMock()


@pytest.fixture
def scheduler(mock_cycle_callback):
    """Create scheduler with short interval for testing"""
    return TradingScheduler(
        interval_seconds=1,  # 1 second for fast tests
        on_cycle=mock_cycle_callback,
        align_to_interval=False,  # Disable alignment for predictable tests
    )


@pytest.fixture
def aligned_scheduler(mock_cycle_callback):
    """Create scheduler with interval alignment"""
    return TradingScheduler(
        interval_seconds=180,  # 3 minutes
        on_cycle=mock_cycle_callback,
        align_to_interval=True,
    )


# ============================================================================
# Initialization Tests
# ============================================================================


def test_scheduler_initialization():
    """Test scheduler initializes with correct defaults"""
    scheduler = TradingScheduler(interval_seconds=180)

    assert scheduler.interval_seconds == 180
    assert scheduler.state == SchedulerState.IDLE
    assert scheduler.cycle_count == 0
    assert scheduler.error_count == 0
    assert scheduler.last_cycle_time is None
    assert scheduler.next_cycle_time is None


def test_scheduler_custom_config():
    """Test scheduler with custom configuration"""
    callback = AsyncMock()
    scheduler = TradingScheduler(
        interval_seconds=60,
        on_cycle=callback,
        max_retries=5,
        retry_delay=10,
        align_to_interval=True,
    )

    assert scheduler.interval_seconds == 60
    assert scheduler.on_cycle == callback
    assert scheduler.max_retries == 5
    assert scheduler.retry_delay == 10
    assert scheduler.align_to_interval is True


# ============================================================================
# Start/Stop Tests
# ============================================================================


@pytest.mark.asyncio
async def test_scheduler_start_stop(scheduler, mock_cycle_callback):
    """Test scheduler starts and stops correctly"""
    # Start scheduler
    await scheduler.start()

    assert scheduler.state == SchedulerState.RUNNING
    assert scheduler.scheduler_task is not None

    # Wait for at least one cycle
    await asyncio.sleep(1.5)

    # Stop scheduler
    await scheduler.stop(graceful=True)

    assert scheduler.state == SchedulerState.STOPPED
    assert mock_cycle_callback.call_count >= 1


@pytest.mark.asyncio
async def test_scheduler_immediate_stop(scheduler, mock_cycle_callback):
    """Test scheduler stops immediately without waiting"""
    await scheduler.start()
    await asyncio.sleep(0.5)

    # Stop immediately (non-graceful)
    await scheduler.stop(graceful=False)

    assert scheduler.state == SchedulerState.STOPPED


@pytest.mark.asyncio
async def test_scheduler_already_running(scheduler):
    """Test starting already running scheduler logs warning"""
    await scheduler.start()

    # Try to start again
    await scheduler.start()

    await scheduler.stop()


# ============================================================================
# Cycle Execution Tests
# ============================================================================


@pytest.mark.asyncio
async def test_scheduler_executes_cycles(scheduler, mock_cycle_callback):
    """Test scheduler executes cycles at correct interval"""
    await scheduler.start()

    # Wait for 3 cycles (3 seconds)
    await asyncio.sleep(3.5)

    await scheduler.stop()

    # Should have executed ~3 cycles
    assert 2 <= mock_cycle_callback.call_count <= 4
    assert scheduler.cycle_count >= 2


@pytest.mark.asyncio
async def test_scheduler_cycle_timing(scheduler, mock_cycle_callback):
    """Test cycles execute at correct intervals"""
    await scheduler.start()

    # Wait for 2 cycles
    await asyncio.sleep(2.5)

    await scheduler.stop()

    assert scheduler.last_cycle_time is not None
    assert scheduler.cycle_count >= 2


@pytest.mark.asyncio
async def test_scheduler_no_callback(mock_cycle_callback):
    """Test scheduler without callback still tracks cycles"""
    scheduler = TradingScheduler(
        interval_seconds=1,
        on_cycle=None,  # No callback
        align_to_interval=False,
    )

    await scheduler.start()
    await asyncio.sleep(2.5)
    await scheduler.stop()

    assert scheduler.cycle_count >= 2


# ============================================================================
# Pause/Resume Tests
# ============================================================================


@pytest.mark.asyncio
async def test_scheduler_pause_resume(scheduler, mock_cycle_callback):
    """Test scheduler pause and resume"""
    await scheduler.start()

    # Wait for 1 cycle
    await asyncio.sleep(1.5)
    initial_count = mock_cycle_callback.call_count

    # Pause
    await scheduler.pause()
    assert scheduler.state == SchedulerState.PAUSED

    # Wait (should not execute cycles)
    await asyncio.sleep(2)

    # Should not have executed more cycles
    assert mock_cycle_callback.call_count == initial_count

    # Resume
    await scheduler.resume()
    assert scheduler.state == SchedulerState.RUNNING

    # Wait for cycles to resume
    await asyncio.sleep(2)

    # Should have executed more cycles
    assert mock_cycle_callback.call_count > initial_count

    await scheduler.stop()


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.asyncio
async def test_scheduler_handles_callback_error():
    """Test scheduler handles and recovers from callback errors"""
    error_callback = AsyncMock(side_effect=Exception("Callback error"))

    scheduler = TradingScheduler(
        interval_seconds=1,
        on_cycle=error_callback,
        align_to_interval=False,
        max_retries=1,  # Fail fast
        retry_delay=0,
    )

    await scheduler.start()

    # Wait for error to occur
    await asyncio.sleep(2)

    await scheduler.stop()

    # Error count should be incremented
    assert scheduler.error_count > 0


@pytest.mark.asyncio
async def test_scheduler_retry_on_error():
    """Test scheduler retries on callback error"""
    # Fail first attempt, succeed on second
    call_count = 0

    async def failing_callback():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("First attempt fails")

    scheduler = TradingScheduler(
        interval_seconds=1,
        on_cycle=failing_callback,
        align_to_interval=False,
        max_retries=2,
        retry_delay=0,
    )

    await scheduler.start()
    await asyncio.sleep(1.5)
    await scheduler.stop()

    # Should have retried and succeeded
    assert call_count == 2


# ============================================================================
# Status Tests
# ============================================================================


@pytest.mark.asyncio
async def test_scheduler_status_idle():
    """Test status when scheduler is idle"""
    scheduler = TradingScheduler(interval_seconds=180)

    status = scheduler.get_status()

    assert status["state"] == SchedulerState.IDLE.value
    assert status["cycle_count"] == 0
    assert status["error_count"] == 0
    assert status["last_cycle"] is None


@pytest.mark.asyncio
async def test_scheduler_status_running(scheduler, mock_cycle_callback):
    """Test status when scheduler is running"""
    await scheduler.start()
    await asyncio.sleep(1.5)

    status = scheduler.get_status()

    assert status["state"] == SchedulerState.RUNNING.value
    assert status["cycle_count"] >= 1
    assert status["last_cycle"] is not None
    assert status["next_cycle"] is not None
    assert "seconds_until_next_cycle" in status

    await scheduler.stop()


# ============================================================================
# Interval Alignment Tests
# ============================================================================


def test_calculate_next_aligned_time():
    """Test interval alignment calculation"""
    scheduler = TradingScheduler(interval_seconds=180)  # 3 minutes

    # Calculate next aligned time
    next_time = scheduler._calculate_next_aligned_time()

    # Should be aligned to 3-minute boundary
    seconds_since_midnight = (
        next_time.hour * 3600 + next_time.minute * 60 + next_time.second
    )
    assert seconds_since_midnight % 180 == 0

    # Should be in the future
    assert next_time > datetime.utcnow()


@pytest.mark.asyncio
async def test_scheduler_alignment(aligned_scheduler, mock_cycle_callback):
    """Test scheduler aligns to interval boundary"""
    # This test may take up to 3 minutes to align, so we use a shorter timeout
    # and verify the next_cycle_time is properly aligned

    await aligned_scheduler.start()

    # Check that next cycle is aligned
    next_cycle = aligned_scheduler.next_cycle_time
    assert next_cycle is not None

    # Verify alignment (should be multiple of 180 seconds since midnight)
    midnight = next_cycle.replace(hour=0, minute=0, second=0, microsecond=0)
    seconds_since_midnight = (next_cycle - midnight).total_seconds()
    assert seconds_since_midnight % 180 == 0

    await aligned_scheduler.stop()


# ============================================================================
# Edge Cases
# ============================================================================


@pytest.mark.asyncio
async def test_scheduler_long_cycle_duration():
    """Test scheduler handles cycles that take longer than interval"""
    slow_callback = AsyncMock()

    async def slow_cycle():
        await asyncio.sleep(2)  # Longer than 1s interval
        await slow_callback()

    scheduler = TradingScheduler(
        interval_seconds=1,
        on_cycle=slow_cycle,
        align_to_interval=False,
    )

    await scheduler.start()
    await asyncio.sleep(3)
    await scheduler.stop()

    # Should still execute cycles (may skip to next boundary)
    assert slow_callback.call_count >= 1


@pytest.mark.asyncio
async def test_scheduler_graceful_shutdown_timeout():
    """Test scheduler force-stops on graceful shutdown timeout"""

    # Create callback that never completes
    async def blocking_callback():
        await asyncio.sleep(100)

    scheduler = TradingScheduler(
        interval_seconds=1,
        on_cycle=blocking_callback,
        align_to_interval=False,
    )

    await scheduler.start()
    await asyncio.sleep(1.5)  # Let one cycle start

    # Stop with graceful (should timeout and force stop)
    start = datetime.utcnow()
    await scheduler.stop(graceful=True)
    duration = (datetime.utcnow() - start).total_seconds()

    # Should timeout after 30s and force stop
    assert duration < 35  # Some buffer for test execution
    assert scheduler.state == SchedulerState.STOPPED
