"""
FastAPI Application - LLM Crypto Trading System

Main application entry point for the trading system API.

This API provides:
- Trading signal endpoints
- Position management
- Risk management controls
- Market data access
- System monitoring

Architecture:
- Event-driven with 3-minute decision cycles
- Async/await for non-blocking operations
- Middleware for logging, error handling, rate limiting
- Health checks for orchestration
- Structured logging for debugging

Usage:
    Development:
        uvicorn workspace.api.main:app --reload --host 0.0.0.0 --port 8000

    Production:
        uvicorn workspace.api.main:app --host 0.0.0.0 --port 8000 --workers 4

Environment Variables:
    See config.py for full list of configuration options.
    Critical variables:
    - DB_HOST, DB_USER, DB_PASSWORD - Database connection
    - REDIS_HOST - Redis connection
    - CAPITAL_CHF - Trading capital
    - CIRCUIT_BREAKER_CHF - Loss limit
"""

import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI

from .config import settings
from .middleware import (
    setup_middleware,
    validation_exception_handler,
    not_found_handler,
)
from .routers import register_routers


# ==================== Logging Configuration ====================
def setup_logging() -> None:
    """
    Configure application logging.

    Log format includes:
    - Timestamp
    - Log level
    - Logger name
    - Message
    - Request ID (if available from middleware)

    Logs go to stdout for container-friendly logging.
    """
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Set specific logger levels
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)

    # Reduce noise from some libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured: level={settings.log_level}")


# Configure logging immediately
setup_logging()
logger = logging.getLogger(__name__)


# ==================== Application Lifecycle ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles:
    - Startup: Initialize connections, resources, background tasks
    - Shutdown: Close connections, cleanup resources

    This is called once when the application starts and stops.
    """
    # ==================== STARTUP ====================
    logger.info("=" * 60)
    logger.info("Starting LLM Crypto Trading System API")
    logger.info("=" * 60)

    startup_time = datetime.utcnow()

    # Log configuration
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"API version: {settings.api_version}")
    logger.info(f"Host: {settings.host}:{settings.port}")

    # Log trading configuration
    logger.info(f"Capital: {settings.capital_chf} CHF")
    logger.info(f"Circuit breaker: {settings.circuit_breaker_chf} CHF")
    logger.info(f"Max position size: {settings.max_position_size_pct * 100}%")

    # TODO: Initialize database connection pool
    # Example:
    # try:
    #     logger.info("Initializing database connection pool...")
    #     await database.connect()
    #     logger.info("✓ Database connected")
    # except Exception as e:
    #     logger.error(f"✗ Database connection failed: {e}")
    #     raise

    # TODO: Initialize Redis connection
    # Example:
    # try:
    #     logger.info("Initializing Redis connection...")
    #     await redis.connect()
    #     logger.info("✓ Redis connected")
    # except Exception as e:
    #     logger.error(f"✗ Redis connection failed: {e}")
    #     raise

    # TODO: Start background tasks (market data, decision engine)
    # Example:
    # logger.info("Starting background tasks...")
    # await scheduler.start()
    # logger.info("✓ Background tasks started")

    startup_duration = (datetime.utcnow() - startup_time).total_seconds()
    logger.info(f"Startup complete in {startup_duration:.2f}s")
    logger.info("=" * 60)

    yield

    # ==================== SHUTDOWN ====================
    logger.info("=" * 60)
    logger.info("Shutting down LLM Crypto Trading System API")
    logger.info("=" * 60)

    shutdown_time = datetime.utcnow()

    # TODO: Stop background tasks
    # logger.info("Stopping background tasks...")
    # await scheduler.stop()
    # logger.info("✓ Background tasks stopped")

    # TODO: Close Redis connection
    # logger.info("Closing Redis connection...")
    # await redis.disconnect()
    # logger.info("✓ Redis disconnected")

    # TODO: Close database connection pool
    # logger.info("Closing database connection pool...")
    # await database.disconnect()
    # logger.info("✓ Database disconnected")

    shutdown_duration = (datetime.utcnow() - shutdown_time).total_seconds()
    logger.info(f"Shutdown complete in {shutdown_duration:.2f}s")
    logger.info("=" * 60)


# ==================== Application Creation ====================
def create_application() -> FastAPI:
    """
    Create and configure FastAPI application.

    Returns:
        Configured FastAPI application instance

    This function:
    1. Creates FastAPI app with metadata
    2. Registers middleware
    3. Registers routers
    4. Registers exception handlers
    5. Returns configured app
    """
    # Create FastAPI app
    app = FastAPI(
        title="LLM Crypto Trading System",
        description=(
            "Automated cryptocurrency trading system powered by Large Language Models.\n\n"
            "Features:\n"
            "- Real-time market data analysis\n"
            "- LLM-powered trading signals\n"
            "- Automated position management\n"
            "- Risk management controls\n"
            "- Performance monitoring\n\n"
            "Decision cycle: Every 3 minutes\n"
            "Assets: 6 cryptocurrencies (perpetual futures)\n"
            "Risk management: Stop-loss, position sizing, circuit breaker\n"
        ),
        version="0.1.0",
        docs_url="/docs" if not settings.is_production else None,  # Disable in prod
        redoc_url="/redoc" if not settings.is_production else None,  # Disable in prod
        openapi_url=(
            "/openapi.json" if not settings.is_production else None
        ),  # Disable in prod
        lifespan=lifespan,
    )

    # Setup middleware
    logger.info("Configuring middleware...")
    setup_middleware(app)

    # Register routers
    logger.info("Registering routers...")
    register_routers(app)

    # Register exception handlers
    from fastapi.exceptions import RequestValidationError

    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(404, not_found_handler)

    # Register root endpoint
    @app.get(
        "/",
        summary="Root endpoint",
        description="API information and links to documentation",
        tags=["root"],
    )
    async def root():
        """
        Root endpoint with API information.

        Returns:
            API metadata and links to documentation
        """
        return {
            "name": "LLM Crypto Trading System API",
            "version": "0.1.0",
            "status": "operational",
            "timestamp": datetime.utcnow().isoformat(),
            "environment": settings.environment,
            "endpoints": {
                "health": "/health",
                "readiness": "/health/ready",
                "liveness": "/health/live",
                "metrics": "/health/metrics",
                "docs": "/docs" if not settings.is_production else None,
                "redoc": "/redoc" if not settings.is_production else None,
            },
            "documentation": "https://github.com/yourusername/trading-system",
            "support": "support@example.com",
        }

    logger.info("Application configured successfully")

    return app


# ==================== Application Instance ====================
app = create_application()


# ==================== Development Server ====================
if __name__ == "__main__":
    """
    Run development server.

    This is for development only. In production, use:
        uvicorn workspace.api.main:app --host 0.0.0.0 --port 8000 --workers 4
    """
    import uvicorn

    logger.info("Starting development server...")

    uvicorn.run(
        "workspace.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,  # Auto-reload on code changes
        log_level=settings.log_level.lower(),
        access_log=True,
    )
