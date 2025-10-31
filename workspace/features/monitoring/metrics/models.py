"""
Prometheus Metrics Models

Data models for tracking and exporting system metrics.

Author: Trading System Implementation Team
Date: 2025-10-28
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class MetricType(str, Enum):
    """Prometheus metric types"""

    COUNTER = "counter"  # Monotonically increasing counter
    GAUGE = "gauge"  # Value that can go up or down
    HISTOGRAM = "histogram"  # Distribution of values
    SUMMARY = "summary"  # Similar to histogram but calculated client-side


class TradingMetrics(BaseModel):
    """
    Core trading metrics for Prometheus export

    Tracks operational metrics for monitoring and alerting.
    """

    # Trade counts
    trades_total: int = Field(default=0, description="Total trades executed")
    trades_successful: int = Field(default=0, description="Successful trades")
    trades_failed: int = Field(default=0, description="Failed trades")

    # Position metrics
    positions_open: int = Field(default=0, description="Currently open positions")
    positions_closed_total: int = Field(default=0, description="Total positions closed")

    # Order metrics
    orders_placed_total: int = Field(default=0, description="Total orders placed")
    orders_filled_total: int = Field(default=0, description="Total orders filled")
    orders_cancelled_total: int = Field(default=0, description="Total orders cancelled")
    orders_rejected_total: int = Field(default=0, description="Total orders rejected")

    # Financial metrics
    realized_pnl_total: Decimal = Field(
        default=Decimal("0"), description="Total realized P&L"
    )
    unrealized_pnl_current: Decimal = Field(
        default=Decimal("0"), description="Current unrealized P&L"
    )
    fees_paid_total: Decimal = Field(
        default=Decimal("0"), description="Total fees paid"
    )

    # Performance metrics
    win_rate: Decimal = Field(default=Decimal("0"), description="Win rate percentage")
    profit_factor: Decimal = Field(default=Decimal("0"), description="Profit factor")
    sharpe_ratio: Optional[Decimal] = Field(default=None, description="Sharpe ratio")

    # Execution metrics
    execution_latency_avg_ms: Decimal = Field(
        default=Decimal("0"), description="Average execution latency"
    )
    execution_latency_p95_ms: Decimal = Field(
        default=Decimal("0"), description="95th percentile latency"
    )
    execution_latency_p99_ms: Decimal = Field(
        default=Decimal("0"), description="99th percentile latency"
    )

    # System health
    system_uptime_seconds: int = Field(
        default=0, description="System uptime in seconds"
    )
    last_trade_timestamp: Optional[datetime] = Field(
        default=None, description="Last trade timestamp"
    )
    last_signal_timestamp: Optional[datetime] = Field(
        default=None, description="Last signal timestamp"
    )

    # LLM metrics
    llm_calls_total: int = Field(default=0, description="Total LLM API calls")
    llm_tokens_input_total: int = Field(default=0, description="Total input tokens")
    llm_tokens_output_total: int = Field(default=0, description="Total output tokens")
    llm_cost_total_usd: Decimal = Field(
        default=Decimal("0"), description="Total LLM cost"
    )
    llm_errors_total: int = Field(default=0, description="Total LLM errors")

    # Market data metrics
    market_data_fetches_total: int = Field(
        default=0, description="Total market data fetches"
    )
    market_data_errors_total: int = Field(
        default=0, description="Market data fetch errors"
    )
    websocket_reconnections_total: int = Field(
        default=0, description="WebSocket reconnections"
    )

    # Risk metrics
    circuit_breaker_triggers_total: int = Field(
        default=0, description="Circuit breaker triggers"
    )
    max_position_size_exceeded_total: int = Field(
        default=0, description="Max position size violations"
    )
    daily_loss_limit_triggers_total: int = Field(
        default=0, description="Daily loss limit triggers"
    )

    # Cache metrics
    cache_hits_total: int = Field(default=0, description="Cache hits")
    cache_misses_total: int = Field(default=0, description="Cache misses")
    cache_evictions_total: int = Field(default=0, description="Cache evictions")

    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat(),
        }


class MetricSnapshot(BaseModel):
    """
    Point-in-time snapshot of metrics

    Used for time-series storage and analysis.
    """

    timestamp: datetime = Field(description="Snapshot timestamp")
    metrics: TradingMetrics = Field(description="Metrics at this point in time")

    # Additional context
    trading_symbols: list[str] = Field(
        default_factory=list, description="Active trading symbols"
    )
    system_version: str = Field(default="1.0.0", description="System version")
    environment: str = Field(
        default="production", description="Environment (production/testnet)"
    )

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class AlertRule(BaseModel):
    """
    Alert rule configuration

    Defines conditions for triggering alerts.
    """

    name: str = Field(description="Alert rule name")
    metric: str = Field(description="Metric to monitor")
    condition: str = Field(description="Alert condition (e.g., '> 0.5', '< 100')")
    threshold: Decimal = Field(description="Alert threshold value")
    severity: str = Field(description="Alert severity (info/warning/critical)")
    enabled: bool = Field(default=True, description="Whether alert is enabled")

    # Alert actions
    notify_channels: list[str] = Field(
        default_factory=list, description="Notification channels"
    )
    cooldown_seconds: int = Field(default=300, description="Cooldown between alerts")

    # Tracking
    last_triggered: Optional[datetime] = Field(
        default=None, description="Last trigger timestamp"
    )
    trigger_count: int = Field(default=0, description="Total trigger count")


class PrometheusExportFormat(BaseModel):
    """
    Prometheus exposition format

    Formatted metrics ready for Prometheus scraping.
    """

    metrics: Dict[str, Any] = Field(description="Metrics in Prometheus format")
    timestamp: datetime = Field(description="Export timestamp")

    def to_prometheus_text(self) -> str:
        """
        Convert metrics to Prometheus text format

        Returns:
            String in Prometheus exposition format
        """
        lines = []
        lines.append(f"# Generated at {self.timestamp.isoformat()}")
        lines.append("")

        for metric_name, metric_value in self.metrics.items():
            # Add HELP line
            lines.append(f"# HELP {metric_name} Trading system metric")

            # Add TYPE line
            metric_type = "gauge"  # Default to gauge
            if "_total" in metric_name:
                metric_type = "counter"
            elif "_bucket" in metric_name:
                metric_type = "histogram"
            lines.append(f"# TYPE {metric_name} {metric_type}")

            # Add metric value
            if isinstance(metric_value, dict):
                # Handle labeled metrics
                for label_set, value in metric_value.items():
                    lines.append(f"{metric_name}{{{label_set}}} {value}")
            else:
                lines.append(f"{metric_name} {metric_value}")

            lines.append("")

        return "\n".join(lines)


# Export all models
__all__ = [
    "MetricType",
    "TradingMetrics",
    "MetricSnapshot",
    "AlertRule",
    "PrometheusExportFormat",
]
