"""
Trade Executor Module

Handles order execution, position management, and stop-loss protection
for the LLM Crypto Trading System.

Author: Trade Executor Implementation Team
Date: 2025-10-27
"""

from .executor_service import TradeExecutor
from .models import (ExecutionResult, Order, OrderSide, OrderStatus, OrderType,
                     PositionSnapshot, ReconciliationResult, StopLossLayer,
                     StopLossProtection, TimeInForce)
from .reconciliation import ReconciliationService
from .stop_loss_manager import StopLossManager

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
