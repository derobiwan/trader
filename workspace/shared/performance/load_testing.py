"""
Load Testing Framework for Trading System.

This module provides comprehensive load testing capabilities to:
- Simulate complete trading cycles under load
- Measure performance metrics (latency, throughput, success rate)
- Monitor resource usage (CPU, memory, connections)
- Test graceful degradation under stress
- Generate detailed performance reports

Author: Implementation Specialist
Date: 2025-10-30
"""

import asyncio
import logging
import time
import psutil
from datetime import datetime
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)


@dataclass
class LoadTestConfig:
    """Configuration for load testing."""

    # Test configuration
    test_name: str = "Trading System Load Test"
    target_cycles: int = 1000
    concurrent_workers: int = 10
    ramp_up_seconds: int = 30  # Gradually increase load
    test_duration_seconds: Optional[int] = (
        None  # Max duration (None = until cycles complete)
    )
    cooldown_seconds: int = 10

    # Target performance thresholds
    target_success_rate: float = 0.995  # 99.5%
    target_p50_latency_ms: float = 1000.0  # 1 second
    target_p95_latency_ms: float = 2000.0  # 2 seconds
    target_p99_latency_ms: float = 3000.0  # 3 seconds

    # Resource monitoring
    monitor_interval_seconds: float = 1.0
    max_cpu_percent: float = 80.0
    max_memory_percent: float = 85.0

    # Failure handling
    max_consecutive_failures: int = 5
    failure_backoff_seconds: float = 1.0


@dataclass
class CycleResult:
    """Result from a single trading cycle execution."""

    cycle_id: int
    worker_id: int
    timestamp: datetime
    success: bool
    latency_ms: float
    error_message: Optional[str] = None
    stages: Dict[str, float] = field(default_factory=dict)  # Stage-wise latencies


@dataclass
class ResourceSnapshot:
    """Snapshot of system resource usage."""

    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    open_connections: int
    thread_count: int
    disk_io_read_mb: float = 0.0
    disk_io_write_mb: float = 0.0


@dataclass
class LoadTestResult:
    """Complete load test results."""

    test_name: str
    start_time: datetime
    end_time: datetime
    duration_seconds: float

    # Execution statistics
    total_cycles: int
    successful_cycles: int
    failed_cycles: int
    success_rate: float

    # Latency statistics (milliseconds)
    mean_latency_ms: float
    median_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    stddev_latency_ms: float

    # Throughput statistics
    cycles_per_second: float
    peak_throughput: float

    # Resource statistics
    peak_cpu_percent: float
    peak_memory_percent: float
    peak_memory_mb: float
    avg_cpu_percent: float
    avg_memory_percent: float

    # Threshold compliance
    meets_success_rate_target: bool
    meets_p50_latency_target: bool
    meets_p95_latency_target: bool
    meets_p99_latency_target: bool

    # Detailed data
    cycle_results: List[CycleResult] = field(default_factory=list)
    resource_snapshots: List[ResourceSnapshot] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class LoadTester:
    """
    Comprehensive load testing framework for the trading system.

    Simulates complete trading cycles under configurable load to validate
    system performance, stability, and resource usage under stress.
    """

    def __init__(self, config: Optional[LoadTestConfig] = None):
        """
        Initialize the load tester.

        Args:
            config: Load test configuration
        """
        self.config = config or LoadTestConfig()
        self.process = psutil.Process()
        self.results: List[CycleResult] = []
        self.resource_snapshots: List[ResourceSnapshot] = []
        self._stop_monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None

    async def simulate_trading_cycle(
        self, cycle_id: int, worker_id: int
    ) -> CycleResult:
        """
        Simulate a complete trading cycle.

        This simulates:
        1. Market data fetch (50-100ms)
        2. LLM decision making (500-1500ms)
        3. Trade execution (100-200ms)

        Args:
            cycle_id: Unique cycle identifier
            worker_id: Worker executing this cycle

        Returns:
            CycleResult with execution metrics
        """
        start_time = time.time()
        stages = {}

        try:
            # Stage 1: Fetch market data
            stage_start = time.time()
            await self._simulate_market_data_fetch()
            stages["market_data_fetch"] = (time.time() - stage_start) * 1000

            # Stage 2: LLM decision
            stage_start = time.time()
            await self._simulate_llm_decision()
            stages["llm_decision"] = (time.time() - stage_start) * 1000

            # Stage 3: Trade execution
            stage_start = time.time()
            await self._simulate_trade_execution()
            stages["trade_execution"] = (time.time() - stage_start) * 1000

            # Calculate total latency
            total_latency_ms = (time.time() - start_time) * 1000

            return CycleResult(
                cycle_id=cycle_id,
                worker_id=worker_id,
                timestamp=datetime.now(),
                success=True,
                latency_ms=total_latency_ms,
                stages=stages,
            )

        except Exception as e:
            total_latency_ms = (time.time() - start_time) * 1000

            return CycleResult(
                cycle_id=cycle_id,
                worker_id=worker_id,
                timestamp=datetime.now(),
                success=False,
                latency_ms=total_latency_ms,
                error_message=str(e),
                stages=stages,
            )

    async def _simulate_market_data_fetch(self) -> None:
        """Simulate market data fetching operation."""
        # Simulate API call latency (50-100ms)
        import random

        await asyncio.sleep(random.uniform(0.05, 0.1))

        # Simulate occasional API errors (1% failure rate)
        if random.random() < 0.01:
            raise Exception("Market data fetch failed")

    async def _simulate_llm_decision(self) -> None:
        """Simulate LLM decision making."""
        # Simulate LLM API latency (500-1500ms)
        import random

        await asyncio.sleep(random.uniform(0.5, 1.5))

        # Simulate occasional LLM errors (2% failure rate)
        if random.random() < 0.02:
            raise Exception("LLM decision failed")

    async def _simulate_trade_execution(self) -> None:
        """Simulate trade execution."""
        # Simulate exchange API latency (100-200ms)
        import random

        await asyncio.sleep(random.uniform(0.1, 0.2))

        # Simulate occasional execution errors (0.5% failure rate)
        if random.random() < 0.005:
            raise Exception("Trade execution failed")

    async def run_load_test(
        self, cycles: Optional[int] = None, custom_cycle_fn: Optional[Callable] = None
    ) -> LoadTestResult:
        """
        Run a comprehensive load test.

        Args:
            cycles: Number of cycles to execute (overrides config)
            custom_cycle_fn: Custom function to simulate trading cycle

        Returns:
            LoadTestResult with comprehensive metrics
        """
        target_cycles = cycles or self.config.target_cycles
        cycle_fn = custom_cycle_fn or self.simulate_trading_cycle

        logger.info(
            f"Starting load test: {target_cycles} cycles, "
            f"{self.config.concurrent_workers} workers"
        )

        # Reset state
        self.results = []
        self.resource_snapshots = []
        self._stop_monitoring = False

        # Start resource monitoring
        self._monitor_task = asyncio.create_task(self._monitor_resources())

        test_start = datetime.now()
        start_time = time.time()

        try:
            # Execute load test with ramp-up
            await self._execute_load_test(target_cycles, cycle_fn)

            # Wait for cooldown
            logger.info(f"Cooling down for {self.config.cooldown_seconds}s...")
            await asyncio.sleep(self.config.cooldown_seconds)

        finally:
            # Stop monitoring
            self._stop_monitoring = True
            if self._monitor_task:
                await self._monitor_task

        test_end = datetime.now()
        duration = time.time() - start_time

        # Calculate metrics
        result = self.calculate_metrics(
            test_start=test_start, test_end=test_end, duration=duration
        )

        logger.info(
            f"Load test complete: {result.total_cycles} cycles, "
            f"{result.success_rate * 100:.2f}% success, "
            f"P95: {result.p95_latency_ms:.2f}ms"
        )

        return result

    async def _execute_load_test(self, target_cycles: int, cycle_fn: Callable) -> None:
        """Execute the load test with worker pool and ramp-up."""

        # Calculate ramp-up schedule
        ramp_up_workers = self._calculate_ramp_up_schedule()

        # Create worker queues
        work_queue = asyncio.Queue()
        result_queue = asyncio.Queue()

        # Populate work queue
        for i in range(target_cycles):
            await work_queue.put(i)

        # Create worker tasks with ramp-up
        worker_tasks = []
        for worker_id in range(self.config.concurrent_workers):
            # Delay worker start for ramp-up
            if worker_id < len(ramp_up_workers):
                delay = ramp_up_workers[worker_id]
            else:
                delay = self.config.ramp_up_seconds

            task = asyncio.create_task(
                self._worker(
                    worker_id=worker_id,
                    work_queue=work_queue,
                    result_queue=result_queue,
                    cycle_fn=cycle_fn,
                    start_delay=delay,
                )
            )
            worker_tasks.append(task)

        # Collect results
        result_collector = asyncio.create_task(
            self._collect_results(result_queue, target_cycles)
        )

        # Wait for completion
        await asyncio.gather(*worker_tasks, return_exceptions=True)
        await result_collector

    def _calculate_ramp_up_schedule(self) -> List[float]:
        """Calculate worker start delays for ramp-up."""
        if self.config.ramp_up_seconds == 0:
            return [0.0] * self.config.concurrent_workers

        # Linear ramp-up
        delays = []
        interval = self.config.ramp_up_seconds / self.config.concurrent_workers

        for i in range(self.config.concurrent_workers):
            delays.append(i * interval)

        return delays

    async def _worker(
        self,
        worker_id: int,
        work_queue: asyncio.Queue,
        result_queue: asyncio.Queue,
        cycle_fn: Callable,
        start_delay: float,
    ) -> None:
        """Worker that processes trading cycles."""
        # Wait for ramp-up delay
        if start_delay > 0:
            await asyncio.sleep(start_delay)

        consecutive_failures = 0

        while not work_queue.empty():
            try:
                cycle_id = await asyncio.wait_for(work_queue.get(), timeout=1.0)

                # Execute cycle
                if cycle_fn == self.simulate_trading_cycle:
                    result = await cycle_fn(cycle_id, worker_id)
                else:
                    # Custom function may have different signature
                    result = await cycle_fn(cycle_id, worker_id)

                # Put result
                await result_queue.put(result)

                # Reset failure counter on success
                if result.success:
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1

                # Check failure threshold
                if consecutive_failures >= self.config.max_consecutive_failures:
                    logger.error(
                        f"Worker {worker_id} hit failure threshold, backing off..."
                    )
                    await asyncio.sleep(self.config.failure_backoff_seconds)
                    consecutive_failures = 0

                work_queue.task_done()

            except asyncio.TimeoutError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                consecutive_failures += 1

    async def _collect_results(
        self, result_queue: asyncio.Queue, target_cycles: int
    ) -> None:
        """Collect results from workers."""
        collected = 0

        while collected < target_cycles:
            try:
                result = await asyncio.wait_for(result_queue.get(), timeout=5.0)
                self.results.append(result)
                collected += 1

                # Log progress
                if collected % 100 == 0:
                    logger.info(f"Completed {collected}/{target_cycles} cycles")

            except asyncio.TimeoutError:
                # Check if we should continue waiting
                if collected < target_cycles * 0.9:  # Wait if less than 90% complete
                    continue
                else:
                    logger.warning(
                        f"Timeout waiting for results, got {collected}/{target_cycles}"
                    )
                    break

    async def _monitor_resources(self) -> None:
        """Monitor system resources during load test."""
        logger.info("Starting resource monitoring...")

        while not self._stop_monitoring:
            try:
                snapshot = await self.monitor_resources()
                self.resource_snapshots.append(snapshot)

                # Check resource limits
                if snapshot.cpu_percent > self.config.max_cpu_percent:
                    logger.warning(
                        f"CPU usage high: {snapshot.cpu_percent:.1f}% "
                        f"(limit: {self.config.max_cpu_percent}%)"
                    )

                if snapshot.memory_percent > self.config.max_memory_percent:
                    logger.warning(
                        f"Memory usage high: {snapshot.memory_percent:.1f}% "
                        f"(limit: {self.config.max_memory_percent}%)"
                    )

                await asyncio.sleep(self.config.monitor_interval_seconds)

            except Exception as e:
                logger.error(f"Resource monitoring error: {e}")

    async def monitor_resources(self) -> ResourceSnapshot:
        """
        Capture current system resource usage.

        Returns:
            ResourceSnapshot with current metrics
        """
        try:
            # CPU usage
            cpu_percent = self.process.cpu_percent(interval=0.1)

            # Memory usage
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)
            memory_percent = self.process.memory_percent()

            # Connections and threads
            try:
                connections = len(self.process.connections())
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                connections = 0

            thread_count = self.process.num_threads()

            # Disk I/O (not available on all platforms, e.g., macOS)
            try:
                io_counters = self.process.io_counters()
                disk_read_mb = io_counters.read_bytes / (1024 * 1024)
                disk_write_mb = io_counters.write_bytes / (1024 * 1024)
            except (
                psutil.AccessDenied,
                psutil.NoSuchProcess,
                AttributeError,
                NotImplementedError,
            ):
                # I/O counters not available on this platform
                disk_read_mb = 0.0
                disk_write_mb = 0.0

            return ResourceSnapshot(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_mb=memory_mb,
                open_connections=connections,
                thread_count=thread_count,
                disk_io_read_mb=disk_read_mb,
                disk_io_write_mb=disk_write_mb,
            )

        except Exception as e:
            logger.error(f"Failed to capture resource snapshot: {e}")
            return ResourceSnapshot(
                timestamp=datetime.now(),
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_mb=0.0,
                open_connections=0,
                thread_count=0,
            )

    def calculate_metrics(
        self, test_start: datetime, test_end: datetime, duration: float
    ) -> LoadTestResult:
        """
        Calculate comprehensive metrics from test results.

        Args:
            test_start: Test start timestamp
            test_end: Test end timestamp
            duration: Test duration in seconds

        Returns:
            LoadTestResult with all metrics
        """
        if not self.results:
            logger.warning("No results to calculate metrics from")
            return LoadTestResult(
                test_name=self.config.test_name,
                start_time=test_start,
                end_time=test_end,
                duration_seconds=duration,
                total_cycles=0,
                successful_cycles=0,
                failed_cycles=0,
                success_rate=0.0,
                mean_latency_ms=0.0,
                median_latency_ms=0.0,
                p50_latency_ms=0.0,
                p95_latency_ms=0.0,
                p99_latency_ms=0.0,
                min_latency_ms=0.0,
                max_latency_ms=0.0,
                stddev_latency_ms=0.0,
                cycles_per_second=0.0,
                peak_throughput=0.0,
                peak_cpu_percent=0.0,
                peak_memory_percent=0.0,
                peak_memory_mb=0.0,
                avg_cpu_percent=0.0,
                avg_memory_percent=0.0,
                meets_success_rate_target=False,
                meets_p50_latency_target=False,
                meets_p95_latency_target=False,
                meets_p99_latency_target=False,
            )

        # Execution statistics
        total_cycles = len(self.results)
        successful_cycles = sum(1 for r in self.results if r.success)
        failed_cycles = total_cycles - successful_cycles
        success_rate = successful_cycles / total_cycles if total_cycles > 0 else 0.0

        # Latency statistics (only successful cycles)
        successful_latencies = [r.latency_ms for r in self.results if r.success]

        if successful_latencies:
            mean_latency = statistics.mean(successful_latencies)
            median_latency = statistics.median(successful_latencies)
            min_latency = min(successful_latencies)
            max_latency = max(successful_latencies)
            stddev_latency = (
                statistics.stdev(successful_latencies)
                if len(successful_latencies) > 1
                else 0.0
            )

            # Calculate percentiles
            sorted_latencies = sorted(successful_latencies)
            p50_latency = self._percentile(sorted_latencies, 50)
            p95_latency = self._percentile(sorted_latencies, 95)
            p99_latency = self._percentile(sorted_latencies, 99)
        else:
            mean_latency = median_latency = min_latency = max_latency = (
                stddev_latency
            ) = 0.0
            p50_latency = p95_latency = p99_latency = 0.0

        # Throughput statistics
        cycles_per_second = total_cycles / duration if duration > 0 else 0.0

        # Calculate peak throughput (cycles per second in 10-second windows)
        peak_throughput = self._calculate_peak_throughput()

        # Resource statistics
        if self.resource_snapshots:
            peak_cpu = max(s.cpu_percent for s in self.resource_snapshots)
            peak_memory_percent = max(s.memory_percent for s in self.resource_snapshots)
            peak_memory_mb = max(s.memory_mb for s in self.resource_snapshots)
            avg_cpu = statistics.mean(s.cpu_percent for s in self.resource_snapshots)
            avg_memory_percent = statistics.mean(
                s.memory_percent for s in self.resource_snapshots
            )
        else:
            peak_cpu = peak_memory_percent = peak_memory_mb = avg_cpu = (
                avg_memory_percent
            ) = 0.0

        # Check threshold compliance
        meets_success_rate = success_rate >= self.config.target_success_rate
        meets_p50_latency = p50_latency <= self.config.target_p50_latency_ms
        meets_p95_latency = p95_latency <= self.config.target_p95_latency_ms
        meets_p99_latency = p99_latency <= self.config.target_p99_latency_ms

        return LoadTestResult(
            test_name=self.config.test_name,
            start_time=test_start,
            end_time=test_end,
            duration_seconds=duration,
            total_cycles=total_cycles,
            successful_cycles=successful_cycles,
            failed_cycles=failed_cycles,
            success_rate=success_rate,
            mean_latency_ms=mean_latency,
            median_latency_ms=median_latency,
            p50_latency_ms=p50_latency,
            p95_latency_ms=p95_latency,
            p99_latency_ms=p99_latency,
            min_latency_ms=min_latency,
            max_latency_ms=max_latency,
            stddev_latency_ms=stddev_latency,
            cycles_per_second=cycles_per_second,
            peak_throughput=peak_throughput,
            peak_cpu_percent=peak_cpu,
            peak_memory_percent=peak_memory_percent,
            peak_memory_mb=peak_memory_mb,
            avg_cpu_percent=avg_cpu,
            avg_memory_percent=avg_memory_percent,
            meets_success_rate_target=meets_success_rate,
            meets_p50_latency_target=meets_p50_latency,
            meets_p95_latency_target=meets_p95_latency,
            meets_p99_latency_target=meets_p99_latency,
            cycle_results=self.results,
            resource_snapshots=self.resource_snapshots,
            errors=[
                r.error_message
                for r in self.results
                if not r.success and r.error_message
            ],
        )

    def _percentile(self, sorted_values: List[float], percentile: float) -> float:
        """Calculate percentile from sorted values."""
        if not sorted_values:
            return 0.0

        index = (percentile / 100) * (len(sorted_values) - 1)
        lower_index = int(index)
        upper_index = min(lower_index + 1, len(sorted_values) - 1)

        # Linear interpolation
        weight = index - lower_index
        return (
            sorted_values[lower_index] * (1 - weight)
            + sorted_values[upper_index] * weight
        )

    def _calculate_peak_throughput(self) -> float:
        """Calculate peak throughput in cycles/second."""
        if not self.results:
            return 0.0

        # Group results by 10-second windows
        window_size_seconds = 10.0
        windows = defaultdict(int)

        for result in self.results:
            window_key = int(result.timestamp.timestamp() / window_size_seconds)
            windows[window_key] += 1

        # Find peak window
        if windows:
            peak_cycles = max(windows.values())
            return peak_cycles / window_size_seconds

        return 0.0

    def generate_report(self, result: LoadTestResult) -> str:
        """
        Generate a comprehensive load test report.

        Args:
            result: Load test result to report on

        Returns:
            Formatted report as string
        """
        lines = []
        lines.append("=" * 80)
        lines.append(f"LOAD TEST REPORT: {result.test_name}")
        lines.append("=" * 80)
        lines.append(f"Start Time: {result.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"End Time:   {result.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Duration:   {result.duration_seconds:.2f}s")
        lines.append("")

        # Execution summary
        lines.append("EXECUTION SUMMARY")
        lines.append("-" * 80)
        lines.append(f"Total Cycles:      {result.total_cycles}")
        lines.append(f"Successful:        {result.successful_cycles}")
        lines.append(f"Failed:            {result.failed_cycles}")
        lines.append(
            f"Success Rate:      {result.success_rate * 100:.2f}% "
            f"{'✓' if result.meets_success_rate_target else '✗'} "
            f"(Target: {self.config.target_success_rate * 100:.2f}%)"
        )
        lines.append("")

        # Latency statistics
        lines.append("LATENCY STATISTICS (milliseconds)")
        lines.append("-" * 80)
        lines.append(f"Mean:     {result.mean_latency_ms:.2f}ms")
        lines.append(f"Median:   {result.median_latency_ms:.2f}ms")
        lines.append(
            f"P50:      {result.p50_latency_ms:.2f}ms "
            f"{'✓' if result.meets_p50_latency_target else '✗'} "
            f"(Target: {self.config.target_p50_latency_ms:.2f}ms)"
        )
        lines.append(
            f"P95:      {result.p95_latency_ms:.2f}ms "
            f"{'✓' if result.meets_p95_latency_target else '✗'} "
            f"(Target: {self.config.target_p95_latency_ms:.2f}ms)"
        )
        lines.append(
            f"P99:      {result.p99_latency_ms:.2f}ms "
            f"{'✓' if result.meets_p99_latency_target else '✗'} "
            f"(Target: {self.config.target_p99_latency_ms:.2f}ms)"
        )
        lines.append(f"Min:      {result.min_latency_ms:.2f}ms")
        lines.append(f"Max:      {result.max_latency_ms:.2f}ms")
        lines.append(f"Std Dev:  {result.stddev_latency_ms:.2f}ms")
        lines.append("")

        # Throughput statistics
        lines.append("THROUGHPUT STATISTICS")
        lines.append("-" * 80)
        lines.append(f"Average:  {result.cycles_per_second:.2f} cycles/second")
        lines.append(f"Peak:     {result.peak_throughput:.2f} cycles/second")
        lines.append("")

        # Resource statistics
        lines.append("RESOURCE USAGE")
        lines.append("-" * 80)
        lines.append("CPU:")
        lines.append(f"  Peak:    {result.peak_cpu_percent:.1f}%")
        lines.append(f"  Average: {result.avg_cpu_percent:.1f}%")
        lines.append("Memory:")
        lines.append(
            f"  Peak:    {result.peak_memory_percent:.1f}% ({result.peak_memory_mb:.1f} MB)"
        )
        lines.append(f"  Average: {result.avg_memory_percent:.1f}%")
        lines.append("")

        # Compliance status
        lines.append("COMPLIANCE STATUS")
        lines.append("-" * 80)
        all_passed = (
            result.meets_success_rate_target
            and result.meets_p50_latency_target
            and result.meets_p95_latency_target
            and result.meets_p99_latency_target
        )

        if all_passed:
            lines.append("✓ ALL TARGETS MET - System meets performance requirements")
        else:
            lines.append("✗ SOME TARGETS MISSED - Review failures below:")
            if not result.meets_success_rate_target:
                lines.append(
                    f"  - Success rate: {result.success_rate * 100:.2f}% < {self.config.target_success_rate * 100:.2f}%"
                )
            if not result.meets_p50_latency_target:
                lines.append(
                    f"  - P50 latency: {result.p50_latency_ms:.2f}ms > {self.config.target_p50_latency_ms:.2f}ms"
                )
            if not result.meets_p95_latency_target:
                lines.append(
                    f"  - P95 latency: {result.p95_latency_ms:.2f}ms > {self.config.target_p95_latency_ms:.2f}ms"
                )
            if not result.meets_p99_latency_target:
                lines.append(
                    f"  - P99 latency: {result.p99_latency_ms:.2f}ms > {self.config.target_p99_latency_ms:.2f}ms"
                )

        lines.append("")

        # Error summary
        if result.errors:
            lines.append("ERROR SUMMARY")
            lines.append("-" * 80)
            error_counts = defaultdict(int)
            for error in result.errors:
                error_counts[error] += 1

            for error, count in sorted(
                error_counts.items(), key=lambda x: x[1], reverse=True
            )[:10]:
                lines.append(f"  {count}x: {error}")
            lines.append("")

        lines.append("=" * 80)

        return "\n".join(lines)


# CLI interface
async def main():
    """Command-line interface for load tester."""
    import argparse

    parser = argparse.ArgumentParser(description="Load Testing for Trading System")
    parser.add_argument(
        "--cycles", type=int, default=1000, help="Number of cycles to run"
    )
    parser.add_argument(
        "--workers", type=int, default=10, help="Number of concurrent workers"
    )
    parser.add_argument(
        "--ramp-up", type=int, default=30, help="Ramp-up time in seconds"
    )
    parser.add_argument("--output", help="Output file for report")

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create load tester
    config = LoadTestConfig(
        target_cycles=args.cycles,
        concurrent_workers=args.workers,
        ramp_up_seconds=args.ramp_up,
    )

    tester = LoadTester(config)

    # Run load test
    result = await tester.run_load_test()

    # Generate report
    report = tester.generate_report(result)

    # Output report
    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        print(f"Report written to {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    asyncio.run(main())
