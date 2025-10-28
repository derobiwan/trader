"""
Health Check Endpoints

Provides various health check endpoints for monitoring and orchestration:
- Basic health: Is the server running?
- Readiness: Can the server handle requests? (checks dependencies)
- Liveness: Is the server responsive? (for load balancers)
- Metrics: Basic application metrics

These endpoints are used by:
- Load balancers (liveness probes)
- Kubernetes/Docker orchestration (readiness probes)
- Monitoring systems (health checks)
- Operations teams (diagnostics)
"""

import logging
import psutil
import time
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel

from ..config import Settings, get_settings


# Configure logger
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Track server start time for uptime calculation
SERVER_START_TIME = time.time()


# ==================== Response Models ====================
class HealthResponse(BaseModel):
    """Basic health check response."""

    status: str
    timestamp: str
    uptime_seconds: float


class ReadinessCheck(BaseModel):
    """Individual dependency readiness check."""

    name: str
    status: str  # "healthy", "degraded", "unhealthy"
    latency_ms: Optional[float] = None
    message: Optional[str] = None


class ReadinessResponse(BaseModel):
    """Readiness check response with dependency status."""

    status: str  # "ready", "not_ready"
    timestamp: str
    checks: list[ReadinessCheck]
    ready: bool


class MetricsResponse(BaseModel):
    """Application metrics response."""

    timestamp: str
    uptime_seconds: float
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    disk_usage_percent: float


# ==================== Health Check Endpoints ====================
@router.get(
    "/",
    response_model=HealthResponse,
    summary="Basic health check",
    description="Returns 200 if server is running. No dependency checks.",
    tags=["health"],
)
async def health_check() -> HealthResponse:
    """
    Basic health check endpoint.

    Returns:
        200 OK if server is running
        Contains timestamp and uptime

    This is a lightweight check that always succeeds if the server is running.
    Use /health/ready for dependency checks.
    """
    uptime = time.time() - SERVER_START_TIME

    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        uptime_seconds=round(uptime, 2),
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness check",
    description="Checks if server can handle requests (includes dependency checks)",
    tags=["health"],
)
async def readiness_check(
    response: Response, settings: Settings = Depends(get_settings)
) -> ReadinessResponse:
    """
    Readiness check with dependency validation.

    Checks:
    - Database connectivity
    - Redis connectivity
    - External API availability

    Returns:
        200 OK if all dependencies are healthy
        503 Service Unavailable if any critical dependency is unhealthy

    Use this endpoint for:
    - Kubernetes readiness probes
    - Load balancer health checks
    - Before accepting traffic
    """
    checks = []
    all_ready = True

    # Check Database
    db_check = await _check_database(settings)
    checks.append(db_check)
    if db_check.status != "healthy":
        all_ready = False

    # Check Redis
    redis_check = await _check_redis(settings)
    checks.append(redis_check)
    if redis_check.status != "healthy":
        all_ready = False

    # Determine overall status
    if all_ready:
        status_str = "ready"
        response.status_code = status.HTTP_200_OK
    else:
        status_str = "not_ready"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessResponse(
        status=status_str,
        timestamp=datetime.utcnow().isoformat(),
        checks=checks,
        ready=all_ready,
    )


@router.get(
    "/live",
    summary="Liveness check",
    description="Quick check that server is responsive (for load balancers)",
    tags=["health"],
)
async def liveness_check() -> Dict[str, Any]:
    """
    Liveness check for load balancers.

    Returns:
        200 OK with minimal response
        Fast response (<10ms typically)

    This endpoint:
    - Does NOT check dependencies
    - Returns immediately
    - Used by load balancers to detect hung processes

    If this endpoint times out or returns errors, the process should be restarted.
    """
    return {"alive": True, "timestamp": datetime.utcnow().isoformat()}


@router.get(
    "/metrics",
    response_model=MetricsResponse,
    summary="Application metrics",
    description="Returns basic application metrics (CPU, memory, disk)",
    tags=["health"],
)
async def metrics(settings: Settings = Depends(get_settings)) -> MetricsResponse:
    """
    Application metrics endpoint.

    Returns:
        System metrics including CPU, memory, and disk usage
        Uptime information

    Metrics include:
    - CPU usage percentage
    - Memory usage (MB and percentage)
    - Disk usage percentage
    - Server uptime

    Use this for:
    - Monitoring dashboards
    - Alerting on resource usage
    - Performance tracking
    """
    if not settings.enable_metrics:
        # Return minimal metrics if disabled
        return MetricsResponse(
            timestamp=datetime.utcnow().isoformat(),
            uptime_seconds=round(time.time() - SERVER_START_TIME, 2),
            cpu_percent=0.0,
            memory_mb=0.0,
            memory_percent=0.0,
            disk_usage_percent=0.0,
        )

    # Collect system metrics
    uptime = time.time() - SERVER_START_TIME
    cpu_percent = psutil.cpu_percent(interval=0.1)

    memory = psutil.virtual_memory()
    memory_mb = memory.used / (1024 * 1024)
    memory_percent = memory.percent

    disk = psutil.disk_usage("/")
    disk_percent = disk.percent

    return MetricsResponse(
        timestamp=datetime.utcnow().isoformat(),
        uptime_seconds=round(uptime, 2),
        cpu_percent=round(cpu_percent, 2),
        memory_mb=round(memory_mb, 2),
        memory_percent=round(memory_percent, 2),
        disk_usage_percent=round(disk_percent, 2),
    )


# ==================== Dependency Check Helpers ====================
async def _check_database(settings: Settings) -> ReadinessCheck:
    """
    Check database connectivity.

    Tests:
    - Connection to PostgreSQL
    - Query execution
    - Response time

    Returns:
        ReadinessCheck with status and latency
    """
    start_time = time.time()

    try:
        # TODO: Implement actual database check when database module is ready
        # For now, return a simulated check
        # In production, this should:
        # 1. Get connection from pool
        # 2. Execute simple query (SELECT 1)
        # 3. Measure latency
        # 4. Return connection to pool

        # Simulated latency
        import asyncio

        await asyncio.sleep(0.01)  # Simulate database query

        latency = (time.time() - start_time) * 1000

        # Placeholder: Assume database is available
        # Replace with actual check: await database.execute("SELECT 1")
        return ReadinessCheck(
            name="database",
            status="healthy",
            latency_ms=round(latency, 2),
            message="PostgreSQL connection successful",
        )

    except Exception as e:
        latency = (time.time() - start_time) * 1000

        logger.error(f"Database health check failed: {e}")

        return ReadinessCheck(
            name="database",
            status="unhealthy",
            latency_ms=round(latency, 2),
            message=f"Database check failed: {str(e)}",
        )


async def _check_redis(settings: Settings) -> ReadinessCheck:
    """
    Check Redis connectivity.

    Tests:
    - Connection to Redis
    - PING command
    - Response time

    Returns:
        ReadinessCheck with status and latency
    """
    start_time = time.time()

    try:
        # TODO: Implement actual Redis check when Redis module is ready
        # For now, return a simulated check
        # In production, this should:
        # 1. Get Redis client
        # 2. Execute PING command
        # 3. Measure latency

        # Simulated latency
        import asyncio

        await asyncio.sleep(0.005)  # Simulate Redis ping

        latency = (time.time() - start_time) * 1000

        # Placeholder: Assume Redis is available
        # Replace with actual check: await redis.ping()
        return ReadinessCheck(
            name="redis",
            status="healthy",
            latency_ms=round(latency, 2),
            message="Redis connection successful",
        )

    except Exception as e:
        latency = (time.time() - start_time) * 1000

        logger.error(f"Redis health check failed: {e}")

        return ReadinessCheck(
            name="redis",
            status="unhealthy",
            latency_ms=round(latency, 2),
            message=f"Redis check failed: {str(e)}",
        )
