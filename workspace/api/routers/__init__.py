"""
API Router Registration

This module handles registration of all API routers with versioning support.

Router Organization:
- /health/* - Health check endpoints (no version prefix)
- /v1/* - Version 1 API endpoints
- Future: /v2/* - Version 2 API endpoints

All routers should be imported and registered here for centralized management.
"""

from fastapi import APIRouter

from . import health

# ==================== Version 1 API Router ====================
api_v1_router = APIRouter(prefix="/v1")

# Register v1 endpoints here as they're implemented
# Example:
# from . import positions, signals, trading
# api_v1_router.include_router(positions.router, prefix="/positions", tags=["positions"])
# api_v1_router.include_router(signals.router, prefix="/signals", tags=["signals"])
# api_v1_router.include_router(trading.router, prefix="/trading", tags=["trading"])


# ==================== Router Registration Function ====================
def register_routers(app) -> None:
    """
    Register all routers with the FastAPI application.

    Args:
        app: FastAPI application instance

    Routers are registered in order:
    1. Health checks (no prefix) - for monitoring
    2. v1 API endpoints - business logic

    Health endpoints don't have version prefix because:
    - They're used by infrastructure (load balancers, k8s)
    - They should remain stable across API versions
    - They don't contain business logic
    """
    # Health endpoints - no version prefix
    app.include_router(health.router, prefix="/health", tags=["health"])

    # Version 1 API - with /v1 prefix
    app.include_router(api_v1_router, tags=["v1"])


# Export routers for testing
__all__ = ["register_routers", "api_v1_router", "health"]
