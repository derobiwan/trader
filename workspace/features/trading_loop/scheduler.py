"""
Trading Scheduler

Manages the 3-minute trading cycle with precise timing, state management,
and error recovery.

Author: Trading Loop Implementation Team
Date: 2025-10-28
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Callable, Optional, Awaitable
from enum import Enum

logger = logging.getLogger(__name__)


class SchedulerState(str, Enum):
    """Scheduler state"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class TradingScheduler:
    """
    Trading Scheduler

    Manages 3-minute trading cycles with precise timing and error recovery.

    Features:
    - Precise 3-minute intervals (180 seconds)
    - State management (running/paused/stopped)
    - Error recovery with configurable retry
    - Cycle tracking and metrics
    - Graceful shutdown

    Attributes:
        interval_seconds: Trading interval (default: 180s = 3min)
        on_cycle: Callback function executed each cycle
        max_retries: Maximum retry attempts on error
        retry_delay: Delay between retries (seconds)

    Example:
        ```python
        async def trading_cycle():
            print("Executing trading cycle...")

        scheduler = TradingScheduler(
            interval_seconds=180,
            on_cycle=trading_cycle,
        )
        await scheduler.start()
        ```
    """

    def __init__(
        self,
        interval_seconds: int = 180,  # 3 minutes
        on_cycle: Optional[Callable[[], Awaitable[None]]] = None,
        max_retries: int = 3,
        retry_delay: int = 5,
        align_to_interval: bool = True,
    ):
        """
        Initialize Trading Scheduler

        Args:
            interval_seconds: Trading cycle interval (default: 180s)
            on_cycle: Async callback function for each cycle
            max_retries: Maximum retry attempts on error (default: 3)
            retry_delay: Delay between retries in seconds (default: 5)
            align_to_interval: Align start time to interval boundary (default: True)
                              If True, waits until next multiple of interval_seconds
                              e.g., for 3min interval, starts at 00:00, 00:03, 00:06, etc.
        """
        self.interval_seconds = interval_seconds
        self.on_cycle = on_cycle
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.align_to_interval = align_to_interval

        # State
        self.state = SchedulerState.IDLE
        self.cycle_count = 0
        self.error_count = 0
        self.last_cycle_time: Optional[datetime] = None
        self.next_cycle_time: Optional[datetime] = None

        # Background task
        self.scheduler_task: Optional[asyncio.Task] = None

    async def start(self):
        """
        Start the trading scheduler

        If align_to_interval is True, waits until the next interval boundary
        before starting the first cycle.
        """
        if self.state == SchedulerState.RUNNING:
            logger.warning("Scheduler already running")
            return

        logger.info(
            f"Starting Trading Scheduler (interval: {self.interval_seconds}s, "
            f"align: {self.align_to_interval})"
        )

        self.state = SchedulerState.RUNNING
        self.cycle_count = 0
        self.error_count = 0

        # Calculate next cycle time
        if self.align_to_interval:
            self.next_cycle_time = self._calculate_next_aligned_time()
            wait_seconds = (self.next_cycle_time - datetime.utcnow()).total_seconds()
            logger.info(
                f"Aligning to interval boundary. First cycle at {self.next_cycle_time} "
                f"(waiting {wait_seconds:.1f}s)"
            )
        else:
            self.next_cycle_time = datetime.utcnow()

        # Start scheduler loop
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())

        logger.info("Trading Scheduler started successfully")

    async def stop(self, graceful: bool = True):
        """
        Stop the trading scheduler

        Args:
            graceful: If True, waits for current cycle to complete
                     If False, immediately cancels the scheduler
        """
        logger.info(f"Stopping Trading Scheduler (graceful: {graceful})")

        if self.state != SchedulerState.RUNNING:
            logger.warning(f"Scheduler not running (state: {self.state})")
            return

        self.state = SchedulerState.STOPPED

        if self.scheduler_task:
            if graceful:
                # Wait for current cycle to complete (with timeout)
                try:
                    await asyncio.wait_for(self.scheduler_task, timeout=30.0)
                except asyncio.TimeoutError:
                    logger.warning("Graceful shutdown timeout, forcing stop")
                    self.scheduler_task.cancel()
            else:
                # Immediately cancel
                self.scheduler_task.cancel()

            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass

        logger.info(
            f"Trading Scheduler stopped (cycles: {self.cycle_count}, "
            f"errors: {self.error_count})"
        )

    async def pause(self):
        """Pause the scheduler (can be resumed)"""
        if self.state == SchedulerState.RUNNING:
            logger.info("Pausing Trading Scheduler")
            self.state = SchedulerState.PAUSED

    async def resume(self):
        """Resume the scheduler from paused state"""
        if self.state == SchedulerState.PAUSED:
            logger.info("Resuming Trading Scheduler")
            self.state = SchedulerState.RUNNING
            # Recalculate next cycle time
            self.next_cycle_time = datetime.utcnow() + timedelta(seconds=self.interval_seconds)

    def get_status(self) -> dict:
        """
        Get scheduler status

        Returns:
            Dictionary with scheduler metrics
        """
        now = datetime.utcnow()

        status = {
            "state": self.state.value,
            "cycle_count": self.cycle_count,
            "error_count": self.error_count,
            "last_cycle": self.last_cycle_time.isoformat() if self.last_cycle_time else None,
            "next_cycle": self.next_cycle_time.isoformat() if self.next_cycle_time else None,
        }

        if self.next_cycle_time and self.state == SchedulerState.RUNNING:
            seconds_until_next = (self.next_cycle_time - now).total_seconds()
            status["seconds_until_next_cycle"] = max(0, seconds_until_next)

        return status

    async def _scheduler_loop(self):
        """Main scheduler loop"""
        logger.info("Scheduler loop started")

        try:
            # Wait for first cycle if aligned
            if self.align_to_interval and self.next_cycle_time:
                wait_seconds = (self.next_cycle_time - datetime.utcnow()).total_seconds()
                if wait_seconds > 0:
                    await asyncio.sleep(wait_seconds)

            while self.state in [SchedulerState.RUNNING, SchedulerState.PAUSED]:
                # Skip execution if paused
                if self.state == SchedulerState.PAUSED:
                    await asyncio.sleep(1)
                    continue

                # Execute trading cycle
                cycle_start = datetime.utcnow()
                self.cycle_count += 1

                logger.info(f"=== Trading Cycle #{self.cycle_count} START ===")

                try:
                    if self.on_cycle:
                        await self._execute_cycle_with_retry()

                    self.last_cycle_time = cycle_start

                except Exception as e:
                    logger.error(f"Trading cycle #{self.cycle_count} failed: {e}", exc_info=True)
                    self.error_count += 1
                    self.state = SchedulerState.ERROR
                    # Try to recover on next cycle
                    await asyncio.sleep(self.retry_delay)
                    self.state = SchedulerState.RUNNING

                cycle_duration = (datetime.utcnow() - cycle_start).total_seconds()
                logger.info(
                    f"=== Trading Cycle #{self.cycle_count} END "
                    f"(duration: {cycle_duration:.2f}s) ==="
                )

                # Calculate next cycle time
                self.next_cycle_time = cycle_start + timedelta(seconds=self.interval_seconds)

                # Wait until next cycle
                wait_seconds = (self.next_cycle_time - datetime.utcnow()).total_seconds()

                if wait_seconds > 0:
                    logger.debug(f"Waiting {wait_seconds:.1f}s until next cycle")
                    await asyncio.sleep(wait_seconds)
                else:
                    # We're behind schedule
                    logger.warning(
                        f"Cycle #{self.cycle_count} took too long "
                        f"(behind by {-wait_seconds:.1f}s)"
                    )
                    # Skip to next interval boundary
                    self.next_cycle_time = self._calculate_next_aligned_time()

        except asyncio.CancelledError:
            logger.info("Scheduler loop cancelled")
            raise

        except Exception as e:
            logger.error(f"Fatal error in scheduler loop: {e}", exc_info=True)
            self.state = SchedulerState.ERROR
            raise

        finally:
            logger.info("Scheduler loop stopped")

    async def _execute_cycle_with_retry(self):
        """Execute cycle with retry logic"""
        for attempt in range(self.max_retries):
            try:
                await self.on_cycle()
                return  # Success

            except Exception as e:
                if attempt < self.max_retries - 1:
                    logger.warning(
                        f"Cycle execution failed (attempt {attempt + 1}/{self.max_retries}): {e}. "
                        f"Retrying in {self.retry_delay}s..."
                    )
                    await asyncio.sleep(self.retry_delay)
                else:
                    # Final attempt failed
                    logger.error(
                        f"Cycle execution failed after {self.max_retries} attempts: {e}",
                        exc_info=True
                    )
                    raise

    def _calculate_next_aligned_time(self) -> datetime:
        """
        Calculate next interval-aligned timestamp

        For 3-minute interval (180s):
        - If now is 10:01:30, next is 10:03:00
        - If now is 10:02:59, next is 10:03:00
        - If now is 10:03:00, next is 10:06:00

        Returns:
            Next aligned datetime (UTC)
        """
        now = datetime.utcnow()

        # Calculate seconds since midnight
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        seconds_since_midnight = (now - midnight).total_seconds()

        # Calculate next interval boundary
        intervals_passed = seconds_since_midnight // self.interval_seconds
        next_interval = (intervals_passed + 1) * self.interval_seconds

        # Calculate next aligned time
        next_time = midnight + timedelta(seconds=next_interval)

        return next_time


# Export
__all__ = ["TradingScheduler", "SchedulerState"]
