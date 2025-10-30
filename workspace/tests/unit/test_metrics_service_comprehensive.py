"""
Comprehensive tests for MetricsService

Tests cover:
- Metric recording (trades, orders, positions, LLM calls)
- Performance metrics (latency percentiles, Sharpe ratio)
- Risk metrics (circuit breaker, position limits, daily loss)
- Cache metrics (hits, misses, evictions)
- Metric snapshots and history
- Prometheus export format
- System uptime tracking
- Statistics aggregation

Author: Validation Engineer - Market Data Team
Date: 2025-10-30
"""

import time
from datetime import datetime
from decimal import Decimal
from statistics import mean

import pytest

from workspace.features.monitoring.metrics.metrics_service import MetricsService


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def metrics_service():
    """Fixture: MetricsService instance"""
    service = MetricsService()
    yield service


@pytest.fixture
def sample_trading_symbols():
    """Fixture: Sample trading symbols"""
    return ["BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT"]


# =============================================================================
# Initialization Tests
# =============================================================================


class TestMetricsServiceInitialization:
    """Tests for metrics service initialization"""

    def test_initialization(self, metrics_service):
        """Test metrics service initialization"""
        assert metrics_service.metrics is not None
        assert metrics_service.start_time > 0
        assert metrics_service._latency_samples == []
        assert metrics_service._snapshots == []
        assert metrics_service._max_latency_samples == 1000
        assert metrics_service._max_snapshots == 1440

    def test_initial_metrics_state(self, metrics_service):
        """Test initial metrics state"""
        metrics = metrics_service.metrics

        assert metrics.trades_total == 0
        assert metrics.trades_successful == 0
        assert metrics.trades_failed == 0
        assert metrics.orders_placed_total == 0
        assert metrics.orders_filled_total == 0
        assert metrics.positions_open == 0
        assert metrics.realized_pnl_total == Decimal("0")
        assert metrics.unrealized_pnl_current == Decimal("0")


# =============================================================================
# Trade Recording Tests
# =============================================================================


class TestTradeRecording:
    """Tests for trade metric recording"""

    def test_record_successful_trade(self, metrics_service):
        """Test recording successful trade"""
        metrics_service.record_trade(
            success=True,
            realized_pnl=Decimal("100.50"),
            fees=Decimal("10.00"),
            latency_ms=Decimal("150"),
        )

        assert metrics_service.metrics.trades_total == 1
        assert metrics_service.metrics.trades_successful == 1
        assert metrics_service.metrics.trades_failed == 0
        assert metrics_service.metrics.realized_pnl_total == Decimal("100.50")
        assert metrics_service.metrics.fees_paid_total == Decimal("10.00")

    def test_record_failed_trade(self, metrics_service):
        """Test recording failed trade"""
        metrics_service.record_trade(success=False)

        assert metrics_service.metrics.trades_total == 1
        assert metrics_service.metrics.trades_successful == 0
        assert metrics_service.metrics.trades_failed == 1

    def test_record_multiple_trades(self, metrics_service):
        """Test recording multiple trades"""
        for i in range(5):
            metrics_service.record_trade(
                success=True,
                realized_pnl=Decimal("100"),
                fees=Decimal("10"),
            )

        assert metrics_service.metrics.trades_total == 5
        assert metrics_service.metrics.trades_successful == 5
        assert metrics_service.metrics.realized_pnl_total == Decimal("500")
        assert metrics_service.metrics.fees_paid_total == Decimal("50")

    def test_record_mixed_trades(self, metrics_service):
        """Test recording mix of successful and failed trades"""
        for i in range(3):
            metrics_service.record_trade(success=True, realized_pnl=Decimal("100"))

        for i in range(2):
            metrics_service.record_trade(success=False)

        assert metrics_service.metrics.trades_total == 5
        assert metrics_service.metrics.trades_successful == 3
        assert metrics_service.metrics.trades_failed == 2
        assert metrics_service.metrics.realized_pnl_total == Decimal("300")

    def test_trade_timestamp_update(self, metrics_service):
        """Test that last trade timestamp is updated"""
        before = datetime.utcnow()
        metrics_service.record_trade(success=True)
        after = datetime.utcnow()

        assert before <= metrics_service.metrics.last_trade_timestamp <= after

    def test_trade_with_zero_pnl(self, metrics_service):
        """Test trade with zero P&L"""
        metrics_service.record_trade(
            success=True,
            realized_pnl=Decimal("0"),
            fees=Decimal("5"),
        )

        assert metrics_service.metrics.trades_successful == 1
        assert metrics_service.metrics.realized_pnl_total == Decimal("0")


# =============================================================================
# Position Recording Tests
# =============================================================================


class TestPositionRecording:
    """Tests for position metric recording"""

    def test_record_position_opened(self, metrics_service):
        """Test recording position opened"""
        metrics_service.record_position_opened()
        assert metrics_service.metrics.positions_open == 1

    def test_record_multiple_positions_opened(self, metrics_service):
        """Test recording multiple positions"""
        for _ in range(3):
            metrics_service.record_position_opened()

        assert metrics_service.metrics.positions_open == 3

    def test_record_position_closed(self, metrics_service):
        """Test recording position closed"""
        metrics_service.record_position_opened()
        metrics_service.record_position_opened()

        metrics_service.record_position_closed()

        assert metrics_service.metrics.positions_open == 1
        assert metrics_service.metrics.positions_closed_total == 1

    def test_record_position_closed_below_zero(self, metrics_service):
        """Test that closed positions don't go below zero"""
        metrics_service.record_position_closed()

        assert metrics_service.metrics.positions_open == 0

    def test_update_unrealized_pnl(self, metrics_service):
        """Test updating unrealized P&L"""
        metrics_service.update_unrealized_pnl(Decimal("500.50"))

        assert metrics_service.metrics.unrealized_pnl_current == Decimal("500.50")

    def test_unrealized_pnl_can_be_negative(self, metrics_service):
        """Test that unrealized P&L can be negative"""
        metrics_service.update_unrealized_pnl(Decimal("-250.00"))

        assert metrics_service.metrics.unrealized_pnl_current == Decimal("-250.00")


# =============================================================================
# Order Recording Tests
# =============================================================================


class TestOrderRecording:
    """Tests for order metric recording"""

    def test_record_order_placed(self, metrics_service):
        """Test recording order placed"""
        metrics_service.record_order(placed=True)

        assert metrics_service.metrics.orders_placed_total == 1

    def test_record_order_filled(self, metrics_service):
        """Test recording order filled"""
        metrics_service.record_order(filled=True)

        assert metrics_service.metrics.orders_filled_total == 1

    def test_record_order_cancelled(self, metrics_service):
        """Test recording order cancelled"""
        metrics_service.record_order(cancelled=True)

        assert metrics_service.metrics.orders_cancelled_total == 1

    def test_record_order_rejected(self, metrics_service):
        """Test recording order rejected"""
        metrics_service.record_order(rejected=True)

        assert metrics_service.metrics.orders_rejected_total == 1

    def test_record_multiple_order_events(self, metrics_service):
        """Test recording multiple order events"""
        metrics_service.record_order(placed=True, filled=True)
        metrics_service.record_order(placed=True, cancelled=True)
        metrics_service.record_order(rejected=True)

        assert metrics_service.metrics.orders_placed_total == 2
        assert metrics_service.metrics.orders_filled_total == 1
        assert metrics_service.metrics.orders_cancelled_total == 1
        assert metrics_service.metrics.orders_rejected_total == 1

    def test_record_order_lifecycle(self, metrics_service):
        """Test complete order lifecycle"""
        # Order placed
        metrics_service.record_order(placed=True)
        assert metrics_service.metrics.orders_placed_total == 1

        # Order filled
        metrics_service.record_order(filled=True)
        assert metrics_service.metrics.orders_filled_total == 1


# =============================================================================
# Performance Metrics Tests
# =============================================================================


class TestPerformanceMetrics:
    """Tests for performance metric recording"""

    def test_update_performance_metrics(self, metrics_service):
        """Test updating performance metrics"""
        metrics_service.update_performance_metrics(
            win_rate=Decimal("0.65"),
            profit_factor=Decimal("1.5"),
            sharpe_ratio=Decimal("0.75"),
        )

        assert metrics_service.metrics.win_rate == Decimal("0.65")
        assert metrics_service.metrics.profit_factor == Decimal("1.5")
        assert metrics_service.metrics.sharpe_ratio == Decimal("0.75")

    def test_performance_metrics_without_sharpe(self, metrics_service):
        """Test updating performance metrics without Sharpe ratio"""
        metrics_service.update_performance_metrics(
            win_rate=Decimal("0.60"),
            profit_factor=Decimal("1.2"),
        )

        assert metrics_service.metrics.win_rate == Decimal("0.60")
        assert metrics_service.metrics.profit_factor == Decimal("1.2")
        # Sharpe ratio should still be None
        assert metrics_service.metrics.sharpe_ratio is None


# =============================================================================
# Latency Tracking Tests
# =============================================================================


class TestLatencyTracking:
    """Tests for execution latency tracking"""

    def test_record_single_latency(self, metrics_service):
        """Test recording single latency sample"""
        metrics_service.record_trade(success=True, latency_ms=Decimal("150"))

        assert len(metrics_service._latency_samples) == 1
        assert metrics_service._latency_samples[0] == 150.0

    def test_record_multiple_latencies(self, metrics_service):
        """Test recording multiple latency samples"""
        latencies = [100, 150, 120, 180, 140]

        for latency in latencies:
            metrics_service.record_trade(success=True, latency_ms=Decimal(str(latency)))

        assert len(metrics_service._latency_samples) == 5
        assert metrics_service.metrics.execution_latency_avg_ms == Decimal(
            str(mean(latencies))
        )

    def test_latency_p95_calculation(self, metrics_service):
        """Test P95 latency calculation"""
        latencies = list(range(100, 200, 10))

        for latency in latencies:
            metrics_service.record_trade(success=True, latency_ms=Decimal(str(latency)))

        # P95 should be calculated
        assert metrics_service.metrics.execution_latency_p95_ms is not None
        assert (
            metrics_service.metrics.execution_latency_p95_ms
            > metrics_service.metrics.execution_latency_avg_ms
        )

    def test_latency_p99_calculation(self, metrics_service):
        """Test P99 latency calculation"""
        # Create 100 latencies to ensure P99 is different from P95
        latencies = list(range(100, 200)) + list(range(100, 200))  # 200 samples total

        for latency in latencies:
            metrics_service.record_trade(success=True, latency_ms=Decimal(str(latency)))

        # P99 should be calculated
        assert metrics_service.metrics.execution_latency_p99_ms is not None
        # P99 should be >= P95 (with enough samples, P99 should typically be higher or equal)
        assert (
            metrics_service.metrics.execution_latency_p99_ms
            >= metrics_service.metrics.execution_latency_p95_ms
        )

    def test_latency_samples_trimmed(self, metrics_service):
        """Test that latency samples are trimmed to max"""
        # Record more than max samples
        for i in range(1500):
            metrics_service.record_trade(
                success=True, latency_ms=Decimal(str(100 + (i % 100)))
            )

        # Should be trimmed to max_latency_samples
        assert (
            len(metrics_service._latency_samples)
            <= metrics_service._max_latency_samples
        )


# =============================================================================
# LLM Call Recording Tests
# =============================================================================


class TestLLMCallRecording:
    """Tests for LLM API call recording"""

    def test_record_successful_llm_call(self, metrics_service):
        """Test recording successful LLM call"""
        metrics_service.record_llm_call(
            success=True,
            tokens_input=1000,
            tokens_output=500,
            cost_usd=Decimal("0.05"),
        )

        assert metrics_service.metrics.llm_calls_total == 1
        assert metrics_service.metrics.llm_tokens_input_total == 1000
        assert metrics_service.metrics.llm_tokens_output_total == 500
        assert metrics_service.metrics.llm_cost_total_usd == Decimal("0.05")

    def test_record_failed_llm_call(self, metrics_service):
        """Test recording failed LLM call"""
        metrics_service.record_llm_call(success=False)

        assert metrics_service.metrics.llm_calls_total == 1
        assert metrics_service.metrics.llm_errors_total == 1

    def test_record_multiple_llm_calls(self, metrics_service):
        """Test recording multiple LLM calls"""
        for i in range(10):
            metrics_service.record_llm_call(
                success=True,
                tokens_input=1000,
                tokens_output=500,
                cost_usd=Decimal("0.05"),
            )

        assert metrics_service.metrics.llm_calls_total == 10
        assert metrics_service.metrics.llm_tokens_input_total == 10000
        assert metrics_service.metrics.llm_cost_total_usd == Decimal("0.50")

    def test_llm_call_timestamp_update(self, metrics_service):
        """Test that last signal timestamp is updated"""
        before = datetime.utcnow()
        metrics_service.record_llm_call(success=True)
        after = datetime.utcnow()

        assert before <= metrics_service.metrics.last_signal_timestamp <= after


# =============================================================================
# Market Data Metrics Tests
# =============================================================================


class TestMarketDataMetrics:
    """Tests for market data metrics"""

    def test_record_market_data_fetch_success(self, metrics_service):
        """Test recording successful market data fetch"""
        metrics_service.record_market_data_fetch(success=True)

        assert metrics_service.metrics.market_data_fetches_total == 1
        assert metrics_service.metrics.market_data_errors_total == 0

    def test_record_market_data_fetch_failure(self, metrics_service):
        """Test recording failed market data fetch"""
        metrics_service.record_market_data_fetch(success=False)

        assert metrics_service.metrics.market_data_fetches_total == 1
        assert metrics_service.metrics.market_data_errors_total == 1

    def test_record_websocket_reconnection(self, metrics_service):
        """Test recording WebSocket reconnection"""
        metrics_service.record_websocket_reconnection()

        assert metrics_service.metrics.websocket_reconnections_total == 1


# =============================================================================
# Risk Metrics Tests
# =============================================================================


class TestRiskMetrics:
    """Tests for risk-related metrics"""

    def test_record_circuit_breaker_trigger(self, metrics_service):
        """Test recording circuit breaker trigger"""
        metrics_service.record_circuit_breaker_trigger()

        assert metrics_service.metrics.circuit_breaker_triggers_total == 1

    def test_record_position_size_violation(self, metrics_service):
        """Test recording position size violation"""
        metrics_service.record_position_size_violation()

        assert metrics_service.metrics.max_position_size_exceeded_total == 1

    def test_record_daily_loss_limit_trigger(self, metrics_service):
        """Test recording daily loss limit trigger"""
        metrics_service.record_daily_loss_limit_trigger()

        assert metrics_service.metrics.daily_loss_limit_triggers_total == 1

    def test_multiple_risk_events(self, metrics_service):
        """Test recording multiple risk events"""
        metrics_service.record_circuit_breaker_trigger()
        metrics_service.record_position_size_violation()
        metrics_service.record_daily_loss_limit_trigger()

        assert metrics_service.metrics.circuit_breaker_triggers_total == 1
        assert metrics_service.metrics.max_position_size_exceeded_total == 1
        assert metrics_service.metrics.daily_loss_limit_triggers_total == 1


# =============================================================================
# Cache Metrics Tests
# =============================================================================


class TestCacheMetrics:
    """Tests for cache metrics"""

    def test_record_cache_hit(self, metrics_service):
        """Test recording cache hit"""
        metrics_service.record_cache_hit()

        assert metrics_service.metrics.cache_hits_total == 1

    def test_record_cache_miss(self, metrics_service):
        """Test recording cache miss"""
        metrics_service.record_cache_miss()

        assert metrics_service.metrics.cache_misses_total == 1

    def test_record_cache_eviction(self, metrics_service):
        """Test recording cache eviction"""
        metrics_service.record_cache_eviction()

        assert metrics_service.metrics.cache_evictions_total == 1

    def test_cache_hit_miss_ratio(self, metrics_service):
        """Test cache hit/miss tracking"""
        # Record hits and misses
        for _ in range(7):
            metrics_service.record_cache_hit()

        for _ in range(3):
            metrics_service.record_cache_miss()

        total_accesses = 10
        hit_rate = metrics_service.metrics.cache_hits_total / total_accesses

        assert hit_rate == 0.7  # 70% hit rate


# =============================================================================
# System Health Tests
# =============================================================================


class TestSystemHealth:
    """Tests for system health metrics"""

    def test_get_uptime_seconds(self, metrics_service):
        """Test uptime calculation"""
        time.sleep(0.1)  # Small delay
        uptime = metrics_service.get_uptime_seconds()

        assert uptime >= 0
        assert isinstance(uptime, int)

    def test_update_system_metrics(self, metrics_service):
        """Test system metrics update"""
        metrics_service.update_system_metrics()

        assert metrics_service.metrics.system_uptime_seconds >= 0

    def test_uptime_increases(self, metrics_service):
        """Test that uptime increases over time"""
        uptime1 = metrics_service.get_uptime_seconds()
        time.sleep(0.1)
        uptime2 = metrics_service.get_uptime_seconds()

        assert uptime2 >= uptime1


# =============================================================================
# Snapshot Tests
# =============================================================================


class TestMetricsSnapshot:
    """Tests for metric snapshots"""

    def test_create_snapshot(self, metrics_service, sample_trading_symbols):
        """Test creating metrics snapshot"""
        metrics_service.record_trade(success=True, realized_pnl=Decimal("100"))

        snapshot = metrics_service.create_snapshot(sample_trading_symbols)

        assert snapshot is not None
        assert snapshot.timestamp is not None
        assert snapshot.trading_symbols == sample_trading_symbols
        assert snapshot.metrics.trades_successful == 1

    def test_snapshot_history_limit(self, metrics_service, sample_trading_symbols):
        """Test that snapshot history is limited"""
        # Create more snapshots than max
        for i in range(1500):
            metrics_service.record_trade(success=True)
            metrics_service.create_snapshot(sample_trading_symbols)

        # Should be trimmed to max
        assert len(metrics_service._snapshots) <= metrics_service._max_snapshots

    def test_snapshot_contains_metrics_copy(
        self, metrics_service, sample_trading_symbols
    ):
        """Test that snapshot contains copy of metrics"""
        metrics_service.record_trade(success=True, realized_pnl=Decimal("100"))
        snapshot = metrics_service.create_snapshot(sample_trading_symbols)

        # Modify original metrics
        metrics_service.record_trade(success=True, realized_pnl=Decimal("50"))

        # Snapshot should not be affected
        assert snapshot.metrics.realized_pnl_total == Decimal("100")
        assert metrics_service.metrics.realized_pnl_total == Decimal("150")


# =============================================================================
# Export Tests
# =============================================================================


class TestPrometheusExport:
    """Tests for Prometheus export format"""

    def test_export_prometheus(self, metrics_service):
        """Test Prometheus export"""
        metrics_service.record_trade(success=True, realized_pnl=Decimal("100"))

        export = metrics_service.export_prometheus()

        assert export is not None
        assert export.timestamp is not None
        assert isinstance(export.metrics, dict)
        assert len(export.metrics) > 0

    def test_get_prometheus_text(self, metrics_service):
        """Test getting Prometheus text format"""
        metrics_service.record_trade(success=True)

        text = metrics_service.get_prometheus_text()

        assert isinstance(text, str)
        assert len(text) > 0


# =============================================================================
# Statistics Tests
# =============================================================================


class TestStatistics:
    """Tests for metrics statistics"""

    def test_get_stats(self, metrics_service):
        """Test getting service statistics"""
        metrics_service.record_trade(
            success=True, realized_pnl=Decimal("100"), fees=Decimal("10")
        )
        metrics_service.record_position_opened()
        metrics_service.record_position_opened()
        metrics_service.record_llm_call(success=True, cost_usd=Decimal("0.05"))

        stats = metrics_service.get_stats()

        assert stats["total_trades"] == 1
        assert stats["successful_trades"] == 1
        assert stats["open_positions"] == 2
        assert stats["llm_calls"] == 1
        assert stats["uptime_seconds"] >= 0

    def test_stats_all_fields(self, metrics_service):
        """Test that stats contain all expected fields"""
        stats = metrics_service.get_stats()

        expected_fields = [
            "uptime_seconds",
            "total_trades",
            "successful_trades",
            "failed_trades",
            "open_positions",
            "realized_pnl",
            "unrealized_pnl",
            "total_fees",
            "llm_calls",
            "llm_cost_usd",
            "snapshots_stored",
        ]

        for field in expected_fields:
            assert field in stats


# =============================================================================
# Export
# =============================================================================

__all__ = [
    "TestMetricsServiceInitialization",
    "TestTradeRecording",
    "TestPositionRecording",
    "TestOrderRecording",
    "TestPerformanceMetrics",
    "TestLatencyTracking",
    "TestLLMCallRecording",
    "TestMarketDataMetrics",
    "TestRiskMetrics",
    "TestCacheMetrics",
    "TestSystemHealth",
    "TestMetricsSnapshot",
    "TestPrometheusExport",
    "TestStatistics",
]
