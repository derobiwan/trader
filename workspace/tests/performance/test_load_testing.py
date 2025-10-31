"""
Tests for Load Testing Framework

Author: Performance Optimizer Agent
Date: 2025-10-29
Sprint: 3 Stream C Task-048
"""

import asyncio

import pytest
from performance.load_testing import LoadTester


@pytest.fixture
def load_tester():
    """Create load tester instance."""
    return LoadTester()


class TestLoadTester:
    """Test load testing functionality."""

    @pytest.mark.asyncio
    async def test_simulate_trading_cycle(self, load_tester):
        """Test trading cycle simulation."""
        symbols = ["BTCUSDT"]

        result = await load_tester.simulate_trading_cycle(symbols)

        assert "success" in result
        assert "total_time" in result
        assert "market_data_time" in result
        assert "decision_time" in result
        assert "trade_time" in result
        assert "position_time" in result
        assert "risk_time" in result
        assert "memory_mb" in result

    @pytest.mark.asyncio
    async def test_run_load_test_short_duration(self, load_tester):
        """Test short duration load test."""
        # Run 5-second test
        results = await load_tester.run_load_test(
            duration_seconds=5,
            cycles_per_second=1.0,  # 1 per second
        )

        assert "summary" in results
        assert "latency_metrics" in results
        assert results["summary"]["total_cycles"] >= 4  # Should complete ~5 cycles
        assert results["summary"]["success_rate_percent"] > 0

    @pytest.mark.asyncio
    async def test_load_test_metrics(self, load_tester):
        """Test load test metrics calculation."""
        # Run minimal test
        results = await load_tester.run_load_test(
            duration_seconds=3, cycles_per_second=1.0
        )

        metrics = results["latency_metrics"]

        assert "total_time" in metrics
        assert "mean_ms" in metrics["total_time"]
        assert "p95_ms" in metrics["total_time"]
        assert "max_ms" in metrics["total_time"]

    @pytest.mark.asyncio
    async def test_stop_load_test(self, load_tester):
        """Test stopping load test."""
        # Start test in background
        task = asyncio.create_task(load_tester.run_load_test(duration_seconds=60))

        # Wait a bit then stop
        await asyncio.sleep(0.5)
        load_tester.stop()

        # Wait for task to complete
        results = await task

        assert not load_tester.is_running
        assert "summary" in results


class TestLoadTestReporting:
    """Test load test reporting."""

    @pytest.mark.asyncio
    async def test_generate_report_with_successful_cycles(self, load_tester):
        """Test report generation with successful cycles."""
        # Simulate some successful cycles
        load_tester.results = [
            {
                "success": True,
                "total_time": 1.0,
                "market_data_time": 0.1,
                "decision_time": 0.5,
                "trade_time": 0.2,
                "position_time": 0.1,
                "risk_time": 0.05,
                "memory_mb": 100.0,
            }
            for _ in range(10)
        ]

        report = await load_tester.generate_report(duration=10.0)

        assert report["summary"]["total_cycles"] == 10
        assert report["summary"]["successful_cycles"] == 10
        assert report["summary"]["success_rate_percent"] == 100.0

    @pytest.mark.asyncio
    async def test_generate_report_with_failures(self, load_tester):
        """Test report generation with failures."""
        # Simulate mixed results
        load_tester.results = [
            {
                "success": True,
                "total_time": 1.0,
                "market_data_time": 0.1,
                "decision_time": 0.5,
                "trade_time": 0.0,
                "position_time": 0.1,
                "risk_time": 0.05,
                "memory_mb": 100.0,
            }
            for _ in range(8)
        ] + [
            {
                "success": False,
                "error": "Test error",
                "cycle_number": 9,
                "elapsed_time": 9.0,
            },
            {
                "success": False,
                "error": "Test error",
                "cycle_number": 10,
                "elapsed_time": 10.0,
            },
        ]

        report = await load_tester.generate_report(duration=10.0)

        assert report["summary"]["total_cycles"] == 10
        assert report["summary"]["successful_cycles"] == 8
        assert report["summary"]["failed_cycles"] == 2
        assert report["summary"]["success_rate_percent"] == 80.0
        assert len(report["failures"]) == 2
