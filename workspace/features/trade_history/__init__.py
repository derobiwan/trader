"""
Trade History Module

Comprehensive trade history tracking and reporting.

Components:
- TradeHistoryEntry: Individual trade records
- TradeHistoryService: Service for logging and querying trades
- TradeStatistics: Aggregated performance metrics
- DailyTradeReport: Daily summary reports

Author: Trading System Implementation Team
Date: 2025-10-28
"""

from .models import (DailyTradeReport, TradeHistoryEntry, TradeStatistics,
                     TradeStatus, TradeType)
from .trade_history_service import TradeHistoryService

__all__ = [
    # Enums
    "TradeType",
    "TradeStatus",
    # Models
    "TradeHistoryEntry",
    "TradeStatistics",
    "DailyTradeReport",
    # Service
    "TradeHistoryService",
]
