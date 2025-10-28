"""
Metrics Service

Collects and exports metrics for Prometheus monitoring.

Author: Trading System Implementation Team
Date: 2025-10-28
"""

import logging
import time
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List
import statistics

from .models import (
    TradingMetrics,
    MetricSnapshot,
    PrometheusExportFormat,
)

logger = logging.getLogger(__name__)


class MetricsService:
    """
    Metrics collection and export service

    Collects metrics from:
    - Trade execution
    - Position management
    - LLM calls
    - Market data fetching
    - System health

    Exports to:
    - Prometheus (HTTP endpoint)
    - Local storage (for analysis)
    """

    def __init__(self):
        """Initialize metrics service"""
        self.metrics = TradingMetrics()
        self.start_time = time.time()

        # Latency tracking (for percentiles)
        self._latency_samples: List[float] = []
        self._max_latency_samples = 1000  # Keep last 1000 samples

        # Snapshots history
        self._snapshots: List[MetricSnapshot] = []
        self._max_snapshots = 1440  # Keep 24 hours at 1-minute intervals

        logger.info("Metrics Service initialized")

    # ========================================================================
    # Trade Metrics
    # ========================================================================

    def record_trade(
        self,
        success: bool,
        realized_pnl: Optional[Decimal] = None,
        fees: Decimal = Decimal("0"),
        latency_ms: Optional[Decimal] = None,
    ):
        """Record trade execution"""
        self.metrics.trades_total += 1

        if success:
            self.metrics.trades_successful += 1
            self.metrics.last_trade_timestamp = datetime.utcnow()

            if realized_pnl is not None:
                self.metrics.realized_pnl_total += realized_pnl

            self.metrics.fees_paid_total += fees

            if latency_ms is not None:
                self._record_latency(float(latency_ms))
        else:
            self.metrics.trades_failed += 1

    def record_position_opened(self):
        """Record position opened"""
        self.metrics.positions_open += 1

    def record_position_closed(self):
        """Record position closed"""
        self.metrics.positions_open = max(0, self.metrics.positions_open - 1)
        self.metrics.positions_closed_total += 1

    def update_unrealized_pnl(self, unrealized_pnl: Decimal):
        """Update current unrealized P&L"""
        self.metrics.unrealized_pnl_current = unrealized_pnl

    # ========================================================================
    # Order Metrics
    # ========================================================================

    def record_order(
        self,
        placed: bool = False,
        filled: bool = False,
        cancelled: bool = False,
        rejected: bool = False,
    ):
        """Record order event"""
        if placed:
            self.metrics.orders_placed_total += 1
        if filled:
            self.metrics.orders_filled_total += 1
        if cancelled:
            self.metrics.orders_cancelled_total += 1
        if rejected:
            self.metrics.orders_rejected_total += 1

    # ========================================================================
    # Performance Metrics
    # ========================================================================

    def update_performance_metrics(
        self,
        win_rate: Decimal,
        profit_factor: Decimal,
        sharpe_ratio: Optional[Decimal] = None,
    ):
        """Update performance metrics"""
        self.metrics.win_rate = win_rate
        self.metrics.profit_factor = profit_factor
        if sharpe_ratio is not None:
            self.metrics.sharpe_ratio = sharpe_ratio

    def _record_latency(self, latency_ms: float):
        """Record execution latency"""
        self._latency_samples.append(latency_ms)

        # Trim to max samples
        if len(self._latency_samples) > self._max_latency_samples:
            self._latency_samples = self._latency_samples[-self._max_latency_samples :]

        # Update metrics
        if self._latency_samples:
            self.metrics.execution_latency_avg_ms = Decimal(
                str(statistics.mean(self._latency_samples))
            )

            sorted_samples = sorted(self._latency_samples)
            p95_index = int(len(sorted_samples) * 0.95)
            p99_index = int(len(sorted_samples) * 0.99)

            self.metrics.execution_latency_p95_ms = Decimal(
                str(sorted_samples[p95_index])
            )
            self.metrics.execution_latency_p99_ms = Decimal(
                str(sorted_samples[p99_index])
            )

    # ========================================================================
    # LLM Metrics
    # ========================================================================

    def record_llm_call(
        self,
        success: bool,
        tokens_input: int = 0,
        tokens_output: int = 0,
        cost_usd: Decimal = Decimal("0"),
    ):
        """Record LLM API call"""
        self.metrics.llm_calls_total += 1

        if success:
            self.metrics.llm_tokens_input_total += tokens_input
            self.metrics.llm_tokens_output_total += tokens_output
            self.metrics.llm_cost_total_usd += cost_usd
            self.metrics.last_signal_timestamp = datetime.utcnow()
        else:
            self.metrics.llm_errors_total += 1

    # ========================================================================
    # Market Data Metrics
    # ========================================================================

    def record_market_data_fetch(self, success: bool):
        """Record market data fetch"""
        self.metrics.market_data_fetches_total += 1
        if not success:
            self.metrics.market_data_errors_total += 1

    def record_websocket_reconnection(self):
        """Record WebSocket reconnection"""
        self.metrics.websocket_reconnections_total += 1

    # ========================================================================
    # Risk Metrics
    # ========================================================================

    def record_circuit_breaker_trigger(self):
        """Record circuit breaker trigger"""
        self.metrics.circuit_breaker_triggers_total += 1

    def record_position_size_violation(self):
        """Record max position size violation"""
        self.metrics.max_position_size_exceeded_total += 1

    def record_daily_loss_limit_trigger(self):
        """Record daily loss limit trigger"""
        self.metrics.daily_loss_limit_triggers_total += 1

    # ========================================================================
    # Cache Metrics
    # ========================================================================

    def record_cache_hit(self):
        """Record cache hit"""
        self.metrics.cache_hits_total += 1

    def record_cache_miss(self):
        """Record cache miss"""
        self.metrics.cache_misses_total += 1

    def record_cache_eviction(self):
        """Record cache eviction"""
        self.metrics.cache_evictions_total += 1

    # ========================================================================
    # System Health
    # ========================================================================

    def get_uptime_seconds(self) -> int:
        """Get system uptime"""
        return int(time.time() - self.start_time)

    def update_system_metrics(self):
        """Update system health metrics"""
        self.metrics.system_uptime_seconds = self.get_uptime_seconds()

    # ========================================================================
    # Snapshot & Export
    # ========================================================================

    def create_snapshot(self, trading_symbols: List[str]) -> MetricSnapshot:
        """
        Create metrics snapshot

        Args:
            trading_symbols: List of active trading symbols

        Returns:
            MetricSnapshot object
        """
        self.update_system_metrics()

        snapshot = MetricSnapshot(
            timestamp=datetime.utcnow(),
            metrics=self.metrics.copy(deep=True),
            trading_symbols=trading_symbols,
        )

        # Store snapshot
        self._snapshots.append(snapshot)

        # Trim to max snapshots
        if len(self._snapshots) > self._max_snapshots:
            self._snapshots = self._snapshots[-self._max_snapshots :]

        return snapshot

    def export_prometheus(self) -> PrometheusExportFormat:
        """
        Export metrics in Prometheus format

        Returns:
            PrometheusExportFormat object
        """
        self.update_system_metrics()

        metrics_dict = {}

        # Convert Pydantic model to dict
        metrics_data = self.metrics.dict()

        for key, value in metrics_data.items():
            # Convert to Prometheus metric name (snake_case)
            metric_name = f"trading_{key}"

            # Convert Decimal to float
            if isinstance(value, Decimal):
                value = float(value)
            elif isinstance(value, datetime):
                value = value.timestamp()
            elif value is None:
                continue

            metrics_dict[metric_name] = value

        return PrometheusExportFormat(
            metrics=metrics_dict,
            timestamp=datetime.utcnow(),
        )

    def get_prometheus_text(self) -> str:
        """
        Get metrics in Prometheus text format

        Returns:
            Prometheus exposition format string
        """
        export = self.export_prometheus()
        return export.to_prometheus_text()

    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        return {
            "uptime_seconds": self.get_uptime_seconds(),
            "total_trades": self.metrics.trades_total,
            "successful_trades": self.metrics.trades_successful,
            "failed_trades": self.metrics.trades_failed,
            "open_positions": self.metrics.positions_open,
            "realized_pnl": str(self.metrics.realized_pnl_total),
            "unrealized_pnl": str(self.metrics.unrealized_pnl_current),
            "total_fees": str(self.metrics.fees_paid_total),
            "llm_calls": self.metrics.llm_calls_total,
            "llm_cost_usd": str(self.metrics.llm_cost_total_usd),
            "snapshots_stored": len(self._snapshots),
        }


# Export
__all__ = ["MetricsService"]
