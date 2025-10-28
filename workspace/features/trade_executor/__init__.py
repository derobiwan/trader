"""
Trade Executor Module

Handles order execution, position management, and stop-loss protection
for the LLM Crypto Trading System.

Author: Trade Executor Implementation Team
Date: 2025-10-27
"""

from .models import (
    OrderType,
    OrderSide,
    OrderStatus,
    TimeInForce,
    StopLossLayer,
    Order,
    ExecutionResult,
    StopLossProtection,
    ReconciliationResult,
    PositionSnapshot,
)
from .executor_service import TradeExecutor
from .stop_loss_manager import StopLossManager
from .reconciliation import ReconciliationService

__all__ = [
    "OrderType",
    "OrderSide",
    "OrderStatus",
    "TimeInForce",
    "StopLossLayer",
    "Order",
    "ExecutionResult",
    "StopLossProtection",
    "ReconciliationResult",
    "PositionSnapshot",
    "TradeExecutor",
    "StopLossManager",
    "ReconciliationService",
]
