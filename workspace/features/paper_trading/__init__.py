"""
Paper Trading Module

Provides paper trading functionality for safe testing without real capital.

Components:
- PaperTradingExecutor: Simulates trade execution
- VirtualPortfolio: Manages virtual positions and balance
- PaperTradingPerformanceTracker: Tracks performance metrics

Author: Implementation Specialist (Sprint 2 Stream B)
Date: 2025-10-29
"""

from .paper_executor import PaperTradingExecutor
from .performance_tracker import PaperTradingPerformanceTracker
from .virtual_portfolio import VirtualPortfolio

__all__ = [
    "PaperTradingExecutor",
    "VirtualPortfolio",
    "PaperTradingPerformanceTracker",
]
