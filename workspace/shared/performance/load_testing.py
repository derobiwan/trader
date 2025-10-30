"""
Load Testing Framework

Comprehensive load testing and performance benchmarking for the trading system.

Features:
- Simulate trading cycles under load
- Performance benchmarking
- Stress testing with increasing load
- Metrics collection and reporting
- Bottleneck identification

Author: Performance Optimization Team
Date: 2025-10-29
Sprint: 3, Stream C, Task 048
"""

import asyncio
import logging
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)


class LoadTestType(Enum):
    """Types of load tests"""

    BASELINE = "baseline"  # Normal load
    STRESS = "stress"  # Increasing load until failure
    SPIKE = "spike"  # Sudden load increase
    ENDURANCE = "endurance"  # Sustained load over time


@dataclass
class LoadTestConfig:
    """Configuration for a load test"""

    test_type: LoadTestType
    duration_seconds: int
    concurrent_users: int
    requests_per_second: int
    ramp_up_seconds: int = 0
    cooldown_seconds: int = 0


@dataclass
class RequestResult:
    """Result of a single request"""

    request_id: int
    success: bool
    response_time_ms: float
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class LoadTestResult:
    """Result of a load test"""

    test_type: LoadTestType
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_duration_seconds: float
    requests_per_second: float
    avg_response_time_ms: float
    min_response_time_ms: float
    max_response_time_ms: float
    p50_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    error_rate_pct: float
    throughput: float
    bottlenecks: List[str]
    timestamp: datetime = field(default_factory=datetime.utcnow)


class LoadTester:
    """
    Load testing framework for the trading system.

    Performs various types of load tests:
    - Baseline: Normal operating conditions
    - Stress: Gradually increasing load until failure
    - Spike: Sudden increase in load
    - Endurance: Sustained load over extended period
    """

    def __init__(self):
        """Initialize load tester"""
        self.results: List[RequestResult] = []
        logger.info("LoadTester initialized")

    # ========================================================================
    # Main Testing Functions
    # ========================================================================

    async def run_load_test(
        self,
        test_config: LoadTestConfig,
        target_function: Callable,
        *args,
        **kwargs,
    ) -> LoadTestResult:
        """
        Run a load test with the specified configuration.

        Args:
            test_config: Load test configuration
            target_function: Function to test (must be async)
            *args: Arguments for target function
            **kwargs: Keyword arguments for target function

        Returns:
            Load test result with performance metrics
        """
        logger.info(
            f"🚀 Starting {test_config.test_type.value} load test: "
            f"{test_config.concurrent_users} users, "
            f"{test_config.duration_seconds}s duration"
        )

        self.results = []
        start_time = time.time()

        # Ramp up phase
        if test_config.ramp_up_seconds > 0:
            logger.info(f"Ramping up over {test_config.ramp_up_seconds}s...")
            await self._ramp_up(test_config, target_function, *args, **kwargs)

        # Main test phase
        await self._execute_load_test(test_config, target_function, *args, **kwargs)

        # Cooldown phase
        if test_config.cooldown_seconds > 0:
            logger.info(f"Cooling down for {test_config.cooldown_seconds}s...")
            await asyncio.sleep(test_config.cooldown_seconds)

        total_duration = time.time() - start_time

        # Analyze results
        result = self._analyze_results(test_config, total_duration)

        logger.info(
            f"✓ Load test complete: {result.total_requests} requests, "
            f"{result.avg_response_time_ms:.2f}ms avg, "
            f"{result.error_rate_pct:.1f}% error rate"
        )

        return result

    async def _execute_load_test(
        self,
        test_config: LoadTestConfig,
        target_function: Callable,
        *args,
        **kwargs,
    ):
        """Execute the main load test phase"""
        duration = test_config.duration_seconds
        concurrent_users = test_config.concurrent_users
        requests_per_second = test_config.requests_per_second

        # Calculate delay between requests
        delay_between_requests = (
            1.0 / requests_per_second if requests_per_second > 0 else 0
        )

        request_id = 0
        start_time = time.time()

        while time.time() - start_time < duration:
            # Create batch of concurrent requests
            batch_tasks = []
            for _ in range(min(concurrent_users, requests_per_second)):
                request_id += 1
                task = self._execute_request(
                    request_id, target_function, *args, **kwargs
                )
                batch_tasks.append(task)

            # Execute batch
            await asyncio.gather(*batch_tasks, return_exceptions=True)

            # Delay before next batch
            if delay_between_requests > 0:
                await asyncio.sleep(delay_between_requests)

    async def _ramp_up(
        self,
        test_config: LoadTestConfig,
        target_function: Callable,
        *args,
        **kwargs,
    ):
        """Gradually increase load during ramp-up phase"""
        ramp_duration = test_config.ramp_up_seconds
        target_concurrent = test_config.concurrent_users
        steps = 10

        for step in range(1, steps + 1):
            concurrent_users = int(target_concurrent * (step / steps))
            await asyncio.sleep(ramp_duration / steps)

            # Execute requests at this step
            tasks = [
                self._execute_request(step * 100 + i, target_function, *args, **kwargs)
                for i in range(concurrent_users)
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _execute_request(
        self,
        request_id: int,
        target_function: Callable,
        *args,
        **kwargs,
    ) -> RequestResult:
        """Execute a single request and record result"""
        start_time = time.time()

        try:
            # Execute target function
            if asyncio.iscoroutinefunction(target_function):
                await target_function(*args, **kwargs)
            else:
                target_function(*args, **kwargs)

            response_time_ms = (time.time() - start_time) * 1000

            result = RequestResult(
                request_id=request_id,
                success=True,
                response_time_ms=response_time_ms,
            )

        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000

            result = RequestResult(
                request_id=request_id,
                success=False,
                response_time_ms=response_time_ms,
                error_message=str(e),
            )

            logger.debug(f"Request {request_id} failed: {e}")

        self.results.append(result)
        return result

    # ========================================================================
    # Specific Test Types
    # ========================================================================

    async def run_baseline_test(
        self,
        target_function: Callable,
        duration_seconds: int = 60,
        concurrent_users: int = 10,
        *args,
        **kwargs,
    ) -> LoadTestResult:
        """
        Run baseline load test with normal operating conditions.

        Args:
            target_function: Function to test
            duration_seconds: Test duration
            concurrent_users: Number of concurrent users
            *args: Arguments for target function
            **kwargs: Keyword arguments for target function

        Returns:
            Load test result
        """
        config = LoadTestConfig(
            test_type=LoadTestType.BASELINE,
            duration_seconds=duration_seconds,
            concurrent_users=concurrent_users,
            requests_per_second=10,
            ramp_up_seconds=5,
            cooldown_seconds=5,
        )

        return await self.run_load_test(config, target_function, *args, **kwargs)

    async def run_stress_test(
        self,
        target_function: Callable,
        max_concurrent_users: int = 100,
        step_duration_seconds: int = 30,
        *args,
        **kwargs,
    ) -> List[LoadTestResult]:
        """
        Run stress test with gradually increasing load.

        Args:
            target_function: Function to test
            max_concurrent_users: Maximum concurrent users to reach
            step_duration_seconds: Duration of each load step
            *args: Arguments for target function
            **kwargs: Keyword arguments for target function

        Returns:
            List of load test results for each step
        """
        logger.info(
            f"Starting stress test: ramping up to {max_concurrent_users} concurrent users"
        )

        results = []
        steps = 5
        step_size = max_concurrent_users // steps

        for step in range(1, steps + 1):
            concurrent_users = step * step_size

            config = LoadTestConfig(
                test_type=LoadTestType.STRESS,
                duration_seconds=step_duration_seconds,
                concurrent_users=concurrent_users,
                requests_per_second=concurrent_users * 2,
            )

            result = await self.run_load_test(config, target_function, *args, **kwargs)
            results.append(result)

            # Check if system is degrading
            if result.error_rate_pct > 10.0:
                logger.warning(
                    f"High error rate detected at {concurrent_users} users, "
                    f"stopping stress test"
                )
                break

            # Brief cooldown between steps
            await asyncio.sleep(5)

        return results

    async def run_spike_test(
        self,
        target_function: Callable,
        baseline_users: int = 10,
        spike_users: int = 100,
        spike_duration_seconds: int = 30,
        *args,
        **kwargs,
    ) -> LoadTestResult:
        """
        Run spike test with sudden increase in load.

        Args:
            target_function: Function to test
            baseline_users: Normal load level
            spike_users: Spike load level
            spike_duration_seconds: Duration of spike
            *args: Arguments for target function
            **kwargs: Keyword arguments for target function

        Returns:
            Load test result during spike
        """
        logger.info(
            f"Starting spike test: {baseline_users} → {spike_users} users for {spike_duration_seconds}s"
        )

        # Run at baseline first
        baseline_config = LoadTestConfig(
            test_type=LoadTestType.BASELINE,
            duration_seconds=30,
            concurrent_users=baseline_users,
            requests_per_second=baseline_users,
        )
        await self.run_load_test(baseline_config, target_function, *args, **kwargs)

        # Spike
        spike_config = LoadTestConfig(
            test_type=LoadTestType.SPIKE,
            duration_seconds=spike_duration_seconds,
            concurrent_users=spike_users,
            requests_per_second=spike_users * 2,
        )
        spike_result = await self.run_load_test(
            spike_config, target_function, *args, **kwargs
        )

        # Return to baseline
        await self.run_load_test(baseline_config, target_function, *args, **kwargs)

        return spike_result

    async def run_endurance_test(
        self,
        target_function: Callable,
        duration_hours: int = 1,
        concurrent_users: int = 20,
        *args,
        **kwargs,
    ) -> LoadTestResult:
        """
        Run endurance test with sustained load over extended period.

        Args:
            target_function: Function to test
            duration_hours: Test duration in hours
            concurrent_users: Number of concurrent users
            *args: Arguments for target function
            **kwargs: Keyword arguments for target function

        Returns:
            Load test result
        """
        logger.info(
            f"Starting endurance test: {concurrent_users} users for {duration_hours}h"
        )

        config = LoadTestConfig(
            test_type=LoadTestType.ENDURANCE,
            duration_seconds=duration_hours * 3600,
            concurrent_users=concurrent_users,
            requests_per_second=concurrent_users,
            ramp_up_seconds=60,
            cooldown_seconds=60,
        )

        return await self.run_load_test(config, target_function, *args, **kwargs)

    # ========================================================================
    # Trading System Specific Tests
    # ========================================================================

    async def test_market_data_fetching(
        self,
        market_data_service,
        symbols: List[str],
        duration_seconds: int = 60,
    ) -> LoadTestResult:
        """
        Test market data fetching under load.

        Args:
            market_data_service: Market data service to test
            symbols: List of symbols to fetch
            duration_seconds: Test duration

        Returns:
            Load test result
        """
        logger.info("Testing market data fetching under load...")

        async def fetch_market_data():
            """Fetch market data for all symbols"""
            tasks = [
                market_data_service.get_ticker(symbol=symbol) for symbol in symbols
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

        config = LoadTestConfig(
            test_type=LoadTestType.BASELINE,
            duration_seconds=duration_seconds,
            concurrent_users=5,
            requests_per_second=10,
        )

        return await self.run_load_test(config, fetch_market_data)

    async def test_trading_decision_cycle(
        self,
        decision_engine,
        duration_seconds: int = 180,
    ) -> LoadTestResult:
        """
        Test full trading decision cycle under load.

        Args:
            decision_engine: Decision engine to test
            duration_seconds: Test duration

        Returns:
            Load test result
        """
        logger.info("Testing trading decision cycle under load...")

        async def execute_decision_cycle():
            """Execute one decision cycle"""
            # Simulate decision cycle
            await decision_engine.analyze_market()
            await decision_engine.generate_signals()
            await decision_engine.evaluate_positions()

        config = LoadTestConfig(
            test_type=LoadTestType.BASELINE,
            duration_seconds=duration_seconds,
            concurrent_users=1,  # Sequential for trading
            requests_per_second=1,  # Once per 3 minutes = 0.33, round to 1
        )

        return await self.run_load_test(config, execute_decision_cycle)

    async def test_llm_request_handling(
        self,
        llm_service,
        duration_seconds: int = 120,
    ) -> LoadTestResult:
        """
        Test LLM request handling under load.

        Args:
            llm_service: LLM service to test
            duration_seconds: Test duration

        Returns:
            Load test result
        """
        logger.info("Testing LLM request handling under load...")

        async def make_llm_request():
            """Make an LLM request"""
            test_prompt = "Analyze BTC/USDT market conditions"
            await llm_service.generate_response(prompt=test_prompt)

        config = LoadTestConfig(
            test_type=LoadTestType.BASELINE,
            duration_seconds=duration_seconds,
            concurrent_users=3,
            requests_per_second=5,
        )

        return await self.run_load_test(config, make_llm_request)

    # ========================================================================
    # Result Analysis
    # ========================================================================

    def _analyze_results(
        self, test_config: LoadTestConfig, total_duration: float
    ) -> LoadTestResult:
        """Analyze load test results and calculate metrics"""
        if not self.results:
            logger.warning("No results to analyze")
            return self._create_empty_result(test_config)

        # Basic metrics
        total_requests = len(self.results)
        successful_requests = sum(1 for r in self.results if r.success)
        failed_requests = total_requests - successful_requests

        # Response time metrics
        response_times = [r.response_time_ms for r in self.results]
        avg_response_time = statistics.mean(response_times)
        min_response_time = min(response_times)
        max_response_time = max(response_times)

        # Percentiles
        sorted_times = sorted(response_times)
        p50 = sorted_times[int(len(sorted_times) * 0.50)]
        p95 = sorted_times[int(len(sorted_times) * 0.95)]
        p99 = sorted_times[int(len(sorted_times) * 0.99)]

        # Error rate
        error_rate = (
            (failed_requests / total_requests * 100) if total_requests > 0 else 0
        )

        # Throughput
        requests_per_second = (
            total_requests / total_duration if total_duration > 0 else 0
        )
        throughput = successful_requests / total_duration if total_duration > 0 else 0

        # Identify bottlenecks
        bottlenecks = self._identify_bottlenecks(
            avg_response_time, error_rate, p95, p99
        )

        return LoadTestResult(
            test_type=test_config.test_type,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            total_duration_seconds=total_duration,
            requests_per_second=requests_per_second,
            avg_response_time_ms=avg_response_time,
            min_response_time_ms=min_response_time,
            max_response_time_ms=max_response_time,
            p50_response_time_ms=p50,
            p95_response_time_ms=p95,
            p99_response_time_ms=p99,
            error_rate_pct=error_rate,
            throughput=throughput,
            bottlenecks=bottlenecks,
        )

    def _identify_bottlenecks(
        self,
        avg_response_time: float,
        error_rate: float,
        p95: float,
        p99: float,
    ) -> List[str]:
        """Identify performance bottlenecks"""
        bottlenecks = []

        # Slow average response time
        if avg_response_time > 2000:  # 2 seconds
            bottlenecks.append(f"High average response time: {avg_response_time:.2f}ms")

        # High error rate
        if error_rate > 5.0:
            bottlenecks.append(f"High error rate: {error_rate:.1f}%")

        # High tail latency
        if p99 > 5000:  # 5 seconds
            bottlenecks.append(f"High p99 latency: {p99:.2f}ms")

        # Large latency variance
        if p99 > p95 * 2:
            bottlenecks.append(
                f"High latency variance: p95={p95:.2f}ms, p99={p99:.2f}ms"
            )

        return bottlenecks

    def _create_empty_result(self, test_config: LoadTestConfig) -> LoadTestResult:
        """Create empty result for failed tests"""
        return LoadTestResult(
            test_type=test_config.test_type,
            total_requests=0,
            successful_requests=0,
            failed_requests=0,
            total_duration_seconds=0,
            requests_per_second=0,
            avg_response_time_ms=0,
            min_response_time_ms=0,
            max_response_time_ms=0,
            p50_response_time_ms=0,
            p95_response_time_ms=0,
            p99_response_time_ms=0,
            error_rate_pct=0,
            throughput=0,
            bottlenecks=[],
        )

    # ========================================================================
    # Reporting
    # ========================================================================

    def generate_load_test_report(self, result: LoadTestResult) -> str:
        """
        Generate comprehensive load test report.

        Args:
            result: Load test result

        Returns:
            Formatted report string
        """
        report = "\n" + "=" * 80 + "\n"
        report += f"LOAD TEST REPORT - {result.test_type.value.upper()}\n"
        report += "=" * 80 + "\n\n"

        report += f"Test Date: {result.timestamp.isoformat()}\n"
        report += f"Duration: {result.total_duration_seconds:.2f}s\n\n"

        # Request metrics
        report += "REQUEST METRICS\n"
        report += "-" * 80 + "\n"
        report += f"Total Requests: {result.total_requests}\n"
        report += f"Successful: {result.successful_requests} ({result.successful_requests / result.total_requests * 100:.1f}%)\n"
        report += f"Failed: {result.failed_requests} ({result.error_rate_pct:.1f}%)\n"
        report += f"Throughput: {result.throughput:.2f} requests/sec\n\n"

        # Response time metrics
        report += "RESPONSE TIME METRICS\n"
        report += "-" * 80 + "\n"
        report += f"Average: {result.avg_response_time_ms:.2f}ms\n"
        report += f"Minimum: {result.min_response_time_ms:.2f}ms\n"
        report += f"Maximum: {result.max_response_time_ms:.2f}ms\n"
        report += f"P50 (Median): {result.p50_response_time_ms:.2f}ms\n"
        report += f"P95: {result.p95_response_time_ms:.2f}ms\n"
        report += f"P99: {result.p99_response_time_ms:.2f}ms\n\n"

        # Bottlenecks
        if result.bottlenecks:
            report += "IDENTIFIED BOTTLENECKS\n"
            report += "-" * 80 + "\n"
            for bottleneck in result.bottlenecks:
                report += f"⚠️  {bottleneck}\n"
            report += "\n"

        # Recommendations
        report += "RECOMMENDATIONS\n"
        report += "-" * 80 + "\n"
        if result.error_rate_pct > 5.0:
            report += "• Investigate and fix errors causing high failure rate\n"
        if result.avg_response_time_ms > 2000:
            report += "• Optimize slow operations to reduce average response time\n"
        if result.p99_response_time_ms > 5000:
            report += "• Address tail latency issues (p99 > 5s)\n"
        if not result.bottlenecks:
            report += "• No major bottlenecks detected\n"

        report += "\n" + "=" * 80 + "\n"

        return report

    def generate_stress_test_report(self, results: List[LoadTestResult]) -> str:
        """
        Generate stress test report showing performance under increasing load.

        Args:
            results: List of load test results

        Returns:
            Formatted report string
        """
        report = "\n" + "=" * 80 + "\n"
        report += "STRESS TEST REPORT\n"
        report += "=" * 80 + "\n\n"

        report += "Performance Under Increasing Load:\n\n"

        report += f"{'Users':<10} {'Req/s':<10} {'Avg(ms)':<12} {'P95(ms)':<12} {'Errors':<10}\n"
        report += "-" * 80 + "\n"

        for i, result in enumerate(results):
            concurrent_users = result.total_requests // result.total_duration_seconds
            report += (
                f"{concurrent_users:<10} "
                f"{result.requests_per_second:<10.2f} "
                f"{result.avg_response_time_ms:<12.2f} "
                f"{result.p95_response_time_ms:<12.2f} "
                f"{result.error_rate_pct:<10.1f}%\n"
            )

        # Find breaking point
        breaking_point = None
        for i, result in enumerate(results):
            if result.error_rate_pct > 10.0 or result.avg_response_time_ms > 5000:
                breaking_point = i
                break

        if breaking_point is not None:
            report += f"\n⚠️  System degradation detected at step {breaking_point + 1}\n"
        else:
            report += "\n✓ System remained stable under all tested load levels\n"

        report += "\n" + "=" * 80 + "\n"

        return report
