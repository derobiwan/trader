"""
Prometheus Metrics HTTP Endpoint

Exposes /metrics endpoint for Prometheus scraping, along with health check endpoints.

Author: Trading System Implementation Team
Date: 2025-10-28
"""

from datetime import datetime
from typing import Dict, Any, Optional
import logging

from fastapi import FastAPI, Response
from workspace.features.monitoring.metrics import MetricsService

logger = logging.getLogger(__name__)

# Global metrics service (shared across requests)
_metrics_service: Optional[MetricsService] = None

# Create FastAPI app
app = FastAPI(
    title="Trading System Metrics API",
    description="Prometheus metrics and health check endpoints for the trading system",
    version="1.0.0",
)


def init_metrics_service(metrics_service: MetricsService):
    """
    Initialize the global metrics service

    Args:
        metrics_service: MetricsService instance to use for this API

    Example:
        ```python
        from workspace.features.monitoring.metrics import MetricsService
        from workspace.features.monitoring.metrics.metrics_api import app, init_metrics_service

        metrics = MetricsService()
        init_metrics_service(metrics)
        ```
    """
    global _metrics_service
    _metrics_service = metrics_service
    logger.info("Metrics API initialized with MetricsService")


@app.get("/metrics")
async def prometheus_metrics():
    """
    Prometheus metrics endpoint

    Returns all trading system metrics in Prometheus text exposition format.
    This endpoint is designed to be scraped by Prometheus at regular intervals.

    Returns:
        Plain text response with Prometheus metrics

    Example response:
        ```
        # HELP trading_trades_total Total number of trades executed
        # TYPE trading_trades_total counter
        trading_trades_total 42

        # HELP trading_trades_successful Number of successful trades
        # TYPE trading_trades_successful counter
        trading_trades_successful 38
        ...
        ```
    """
    if _metrics_service is None:
        logger.warning("Metrics service not initialized, returning empty metrics")
        return Response(
            content="# Metrics service not initialized\n",
            media_type="text/plain",
        )

    # Get metrics in Prometheus format
    prometheus_text = _metrics_service.get_prometheus_text()

    return Response(
        content=prometheus_text,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint

    Returns 200 if the service process is alive. This is the most basic
    health check and should always return 200 if the process is running.

    Use this for:
    - Load balancer health checks
    - Basic uptime monitoring

    Returns:
        JSON with status and timestamp

    Example response:
        ```json
        {
            "status": "healthy",
            "timestamp": "2025-10-28T12:34:56.789Z"
        }
        ```
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@app.get("/ready")
async def readiness_check():
    """
    Readiness check for orchestration

    Returns 200 if the service is ready to accept traffic and handle requests.
    Returns 503 if the service is initializing or not ready.

    Use this for:
    - Kubernetes readiness probe
    - Container orchestration
    - Load balancer traffic routing

    Returns:
        JSON with status and details, or 503 if not ready

    Example responses:
        Ready:
        ```json
        {
            "status": "ready",
            "uptime_seconds": 120,
            "timestamp": "2025-10-28T12:34:56.789Z"
        }
        ```

        Not ready:
        ```json
        {
            "status": "not ready",
            "reason": "system initializing"
        }
        ```
    """
    if _metrics_service is None:
        return Response(
            content='{"status": "not ready", "reason": "metrics not initialized"}',
            status_code=503,
            media_type="application/json",
        )

    # Check if we have recent metrics (system has been running for at least 10s)
    stats = _metrics_service.get_stats()
    uptime = stats.get("uptime_seconds", 0)

    if uptime < 10:
        # Not ready yet, system just started
        return Response(
            content=f'{{"status": "not ready", "reason": "system initializing", "uptime_seconds": {uptime}}}',
            status_code=503,
            media_type="application/json",
        )

    return {
        "status": "ready",
        "uptime_seconds": uptime,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@app.get("/live")
async def liveness_check():
    """
    Liveness check for orchestration

    Returns 200 if the service is functioning normally and should NOT be restarted.
    Returns 503 if the service is frozen, deadlocked, or otherwise broken and
    SHOULD be restarted.

    Use this for:
    - Kubernetes liveness probe (will restart pod if failing)
    - Detecting frozen/deadlocked systems
    - Auto-recovery from stuck states

    Detection criteria:
    - No trades executed in last 10 minutes (system might be frozen)

    Returns:
        JSON with status and details, or 503 if unhealthy

    Example responses:
        Alive:
        ```json
        {
            "status": "alive",
            "last_trade_seconds_ago": 45.3,
            "timestamp": "2025-10-28T12:34:56.789Z"
        }
        ```

        Unhealthy:
        ```json
        {
            "status": "unhealthy",
            "reason": "no trades for 612s"
        }
        ```
    """
    if _metrics_service is None:
        # No metrics service = dead
        return Response(
            content='{"status": "dead", "reason": "metrics not initialized"}',
            status_code=503,
            media_type="application/json",
        )

    # Check if system is frozen (no trades in last 10 minutes)
    last_trade = _metrics_service.metrics.last_trade_timestamp

    if last_trade:
        time_since_trade = (datetime.utcnow() - last_trade).total_seconds()
        if time_since_trade > 600:  # 10 minutes
            # System might be frozen
            return Response(
                content=f'{{"status": "unhealthy", "reason": "no trades for {time_since_trade:.0f}s"}}',
                status_code=503,
                media_type="application/json",
            )

        last_trade_seconds = time_since_trade
    else:
        last_trade_seconds = None

    return {
        "status": "alive",
        "last_trade_seconds_ago": last_trade_seconds,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


# Export
__all__ = ["app", "init_metrics_service"]
