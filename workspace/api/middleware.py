"""
Middleware Layer for FastAPI Application

This module provides middleware for:
- Request/response logging with request IDs
- Error handling and exception formatting
- Request ID tracking across async operations
- Basic rate limiting (in-memory)
- Performance monitoring

All middleware is production-ready with proper error handling and logging.
"""

import logging
import time
import uuid
from typing import Callable, Dict
from datetime import datetime, timedelta
from collections import defaultdict, deque

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

from .config import settings


# Configure logger
logger = logging.getLogger(__name__)


# ==================== Request ID Context ====================
class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Add request ID to all requests for tracking across async operations.

    The request ID is:
    - Generated as UUID4
    - Added to request.state for access in endpoints
    - Included in response headers
    - Included in all log messages
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add request ID to request and response."""
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Add to response headers
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response


# ==================== Request Logging ====================
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Log all incoming requests and outgoing responses.

    Logs include:
    - Request ID
    - HTTP method and path
    - Query parameters
    - Response status code
    - Request duration
    - Client IP (if available)
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request and response with timing."""
        if not settings.enable_request_logging:
            return await call_next(request)

        # Get request ID (from RequestContextMiddleware)
        request_id = getattr(request.state, "request_id", "unknown")

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Log request
        logger.info(
            "Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query": str(request.query_params),
                "client_ip": client_ip,
            },
        )

        # Time the request
        start_time = time.time()

        try:
            response = await call_next(request)
            duration = time.time() - start_time

            # Log response
            logger.info(
                "Request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                },
            )

            return response

        except Exception as exc:
            duration = time.time() - start_time

            # Log error
            logger.error(
                "Request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration * 1000, 2),
                    "error": str(exc),
                },
                exc_info=True,
            )

            raise


# ==================== Error Handling ====================
class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Global error handler for unhandled exceptions.

    Returns structured JSON error responses with:
    - Error message
    - Request ID for tracking
    - Timestamp
    - Status code
    - Error type (in development mode)
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Catch and format unhandled exceptions."""
        try:
            return await call_next(request)

        except Exception as exc:
            # Get request ID for tracking
            request_id = getattr(request.state, "request_id", "unknown")

            # Log the error
            logger.error(
                f"Unhandled exception in {request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
                exc_info=True,
            )

            # Build error response
            error_response = {
                "error": "Internal server error",
                "message": (
                    str(exc) if settings.debug else "An unexpected error occurred"
                ),
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Add error type in debug mode
            if settings.debug:
                error_response["error_type"] = type(exc).__name__

            return JSONResponse(status_code=500, content=error_response)


# ==================== Rate Limiting ====================
class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting middleware.

    Uses sliding window algorithm to limit requests per IP address.
    For production, consider using Redis-backed rate limiting.

    Rate limit configuration from settings:
    - rate_limit_requests: Max requests per window
    - rate_limit_window_seconds: Window duration
    """

    def __init__(self, app):
        super().__init__(app)
        # Store: {ip: deque of timestamps}
        self.request_history: Dict[str, deque] = defaultdict(deque)
        self.window = timedelta(seconds=settings.rate_limit_window_seconds)
        self.max_requests = settings.rate_limit_requests

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply rate limiting based on client IP."""
        # Skip rate limiting for health checks
        if request.url.path.startswith("/health"):
            return await call_next(request)

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        if client_ip == "unknown":
            # Can't rate limit without IP
            return await call_next(request)

        # Get current time
        now = datetime.utcnow()

        # Clean old requests outside window
        history = self.request_history[client_ip]
        cutoff = now - self.window

        # Remove timestamps outside window
        while history and history[0] < cutoff:
            history.popleft()

        # Check rate limit
        if len(history) >= self.max_requests:
            request_id = getattr(request.state, "request_id", "unknown")

            logger.warning(
                "Rate limit exceeded",
                extra={
                    "request_id": request_id,
                    "client_ip": client_ip,
                    "requests": len(history),
                    "window_seconds": settings.rate_limit_window_seconds,
                },
            )

            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {self.max_requests} requests per {settings.rate_limit_window_seconds} seconds",
                    "retry_after": int(self.window.total_seconds()),
                    "request_id": request_id,
                },
                headers={"Retry-After": str(int(self.window.total_seconds()))},
            )

        # Add current request timestamp
        history.append(now)

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(
            max(0, self.max_requests - len(history))
        )
        response.headers["X-RateLimit-Reset"] = str(
            int((now + self.window).timestamp())
        )

        return response


# ==================== Middleware Registration ====================
def setup_middleware(app) -> None:
    """
    Register all middleware with FastAPI application.

    Middleware is applied in REVERSE order (last added = first executed).
    Order matters for proper request processing.

    Execution order:
    1. CORS (if request is cross-origin)
    2. Request Context (add request ID)
    3. Rate Limiting (check limits)
    4. Request Logging (log request/response)
    5. Error Handling (catch exceptions)
    """
    # CORS - must be first to handle preflight requests
    app.add_middleware(CORSMiddleware, **settings.get_cors_config())

    # Error handling - catch all exceptions
    app.add_middleware(ErrorHandlingMiddleware)

    # Request logging
    if settings.enable_request_logging:
        app.add_middleware(RequestLoggingMiddleware)

    # Rate limiting
    app.add_middleware(RateLimitMiddleware)

    # Request context - add request ID
    app.add_middleware(RequestContextMiddleware)

    logger.info("Middleware configured successfully")


# ==================== Exception Handlers ====================
async def validation_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """
    Handle validation errors with detailed messages.

    Used for Pydantic validation errors from request bodies.
    """
    request_id = getattr(request.state, "request_id", "unknown")

    logger.warning(
        "Validation error",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "error": str(exc),
        },
    )

    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation error",
            "message": str(exc),
            "request_id": request_id,
        },
    )


async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle 404 Not Found errors."""
    request_id = getattr(request.state, "request_id", "unknown")

    return JSONResponse(
        status_code=404,
        content={
            "error": "Not found",
            "message": f"Endpoint {request.url.path} not found",
            "request_id": request_id,
        },
    )
