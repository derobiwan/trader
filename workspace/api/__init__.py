"""
FastAPI Application Package

Main FastAPI application for LLM Crypto Trading System.

This package provides the REST API for:
- Trading signal generation and management
- Position tracking and management
- Risk management controls
- Market data access
- System monitoring and health checks

Usage:
    uvicorn workspace.api.main:app --reload

For production:
    uvicorn workspace.api.main:app --host 0.0.0.0 --port 8000 --workers 4
"""

__version__ = "0.1.0"

from .main import app

__all__ = ["app"]
