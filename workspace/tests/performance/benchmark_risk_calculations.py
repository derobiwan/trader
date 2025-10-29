"""
Performance Benchmarks for Risk Calculations

Validates that risk calculations meet performance targets:
- Risk calculation: <100ms
- Correlation analysis: <500ms
- Circuit breaker trigger: <1s

Author: Risk Management Team
Date: 2025-10-29
"""

import time
import asyncio
from decimal import Decimal
from datetime import datetime, timedelta

from workspace.features.risk_manager import (
    PortfolioRiskManager,
    KellyPositionSizer,
    CorrelationAnalyzer,
    RiskMetricsCalculator,
    PositionInfo,
    TradeResult,
)


def benchmark_portfolio_risk_check():
    """Benchmark portfolio risk limit checks"""
    risk_manager = PortfolioRiskManager(
        max_portfolio_value=Decimal("2626.96")
    )

    # Warm up
    for _ in range(10):
        risk_manager.check_position_limits(Decimal("200.00"))

    # Benchmark
    start = time.perf_counter()
    iterations = 1000

    for _ in range(iterations):
        risk_manager.check_position_limits(Decimal("200.00"))

    end = time.perf_counter()
    avg_time_ms = ((end - start) / iterations) * 1000

    print(f"Portfolio Risk Check: {avg_time_ms:.2f}ms per check (target: <100ms)")
    assert avg_time_ms < 100, f"Performance target missed: {avg_time_ms:.2f}ms"

    return avg_time_ms


def benchmark_kelly_calculation():
    """Benchmark Kelly Criterion position sizing"""
    sizer = KellyPositionSizer()

    # Warm up
    for _ in range(10):
        sizer.calculate_position_size(
            win_rate=0.55,
            avg_win=Decimal("100.00"),
            avg_loss=Decimal("80.00"),
            portfolio_value=Decimal("2626.96"),
        )

    # Benchmark
    start = time.perf_counter()
    iterations = 1000

    for _ in range(iterations):
        sizer.calculate_position_size(
            win_rate=0.55,
            avg_win=Decimal("100.00"),
            avg_loss=Decimal("80.00"),
            portfolio_value=Decimal("2626.96"),
        )

    end = time.perf_counter()
    avg_time_ms = ((end - start) / iterations) * 1000

    print(f"Kelly Calculation: {avg_time_ms:.2f}ms per calculation (target: <100ms)")
    assert avg_time_ms < 100, f"Performance target missed: {avg_time_ms:.2f}ms"

    return avg_time_ms


async def benchmark_correlation_analysis():
    """Benchmark correlation analysis"""
    analyzer = CorrelationAnalyzer()

    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

    # Warm up
    await analyzer.calculate_portfolio_correlation(symbols, days=30)

    # Benchmark
    start = time.perf_counter()
    iterations = 10  # Fewer iterations for async

    for _ in range(iterations):
        await analyzer.calculate_portfolio_correlation(symbols, days=30)

    end = time.perf_counter()
    avg_time_ms = ((end - start) / iterations) * 1000

    print(f"Correlation Analysis: {avg_time_ms:.2f}ms per analysis (target: <500ms)")
    assert avg_time_ms < 500, f"Performance target missed: {avg_time_ms:.2f}ms"

    return avg_time_ms


def benchmark_risk_metrics():
    """Benchmark risk metrics calculation"""
    calculator = RiskMetricsCalculator()

    returns = [0.01, -0.005, 0.02, -0.01, 0.015] * 20  # 100 data points
    equity_curve = [Decimal(str(1000 + i * 10)) for i in range(101)]
    initial_balance = Decimal("1000")

    # Warm up
    for _ in range(10):
        calculator.calculate_all_metrics(returns, equity_curve, initial_balance)

    # Benchmark
    start = time.perf_counter()
    iterations = 1000

    for _ in range(iterations):
        calculator.calculate_all_metrics(returns, equity_curve, initial_balance)

    end = time.perf_counter()
    avg_time_ms = ((end - start) / iterations) * 1000

    print(f"Risk Metrics Calculation: {avg_time_ms:.2f}ms per calculation (target: <100ms)")
    assert avg_time_ms < 100, f"Performance target missed: {avg_time_ms:.2f}ms"

    return avg_time_ms


def benchmark_circuit_breaker():
    """Benchmark circuit breaker trigger"""
    risk_manager = PortfolioRiskManager(
        max_portfolio_value=Decimal("2626.96")
    )

    # Warm up
    for _ in range(10):
        risk_manager.check_daily_loss_limit(Decimal("-50.00"))

    # Benchmark
    start = time.perf_counter()
    iterations = 1000

    for _ in range(iterations):
        risk_manager.check_daily_loss_limit(Decimal("-50.00"))

    end = time.perf_counter()
    avg_time_ms = ((end - start) / iterations) * 1000

    print(f"Circuit Breaker Check: {avg_time_ms:.2f}ms per check (target: <1000ms)")
    assert avg_time_ms < 1000, f"Performance target missed: {avg_time_ms:.2f}ms"

    return avg_time_ms


async def run_all_benchmarks():
    """Run all performance benchmarks"""
    print("\n" + "=" * 70)
    print("Risk Management Performance Benchmarks")
    print("=" * 70 + "\n")

    results = {}

    # Synchronous benchmarks
    results["portfolio_risk"] = benchmark_portfolio_risk_check()
    results["kelly_sizing"] = benchmark_kelly_calculation()
    results["risk_metrics"] = benchmark_risk_metrics()
    results["circuit_breaker"] = benchmark_circuit_breaker()

    # Asynchronous benchmarks
    results["correlation"] = await benchmark_correlation_analysis()

    print("\n" + "=" * 70)
    print("Benchmark Summary")
    print("=" * 70)

    for name, time_ms in results.items():
        status = "✓ PASS" if time_ms < 100 or (name == "correlation" and time_ms < 500) else "✗ FAIL"
        print(f"{status} | {name:20s}: {time_ms:6.2f}ms")

    print("=" * 70 + "\n")

    # Overall pass/fail
    all_passed = all(
        time_ms < 100 if name != "correlation" else time_ms < 500
        for name, time_ms in results.items()
    )

    if all_passed:
        print("✓ All performance targets met!")
    else:
        print("✗ Some performance targets missed")

    return all_passed


if __name__ == "__main__":
    passed = asyncio.run(run_all_benchmarks())
    exit(0 if passed else 1)
