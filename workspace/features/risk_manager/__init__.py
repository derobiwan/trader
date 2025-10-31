"""
Risk Manager Module

Multi-layered risk management system with position limits,
stop-loss protection, and daily loss circuit breaker.

Author: Risk Management Team
Date: 2025-10-28
"""

from .circuit_breaker import CircuitBreaker
from .correlation_analysis import (
    CorrelationAnalyzer,
    CorrelationMatrix,
    CorrelationPair,
    PriceHistory,
)
from .models import (
    CircuitBreakerState,
    CircuitBreakerStatus,
    Protection,
    ProtectionLayer,
    RiskCheckResult,
    RiskValidation,
    ValidationStatus,
)

# Advanced risk management (Sprint 3 Stream B)
from .portfolio_risk import (
    PortfolioLimits,
    PortfolioRiskManager,
    PortfolioStatus,
    PositionInfo,
)
from .position_sizing import KellyPositionSizer, PositionSizingResult, TradeResult
from .risk_manager import RiskManager
from .risk_metrics import RiskMetrics, RiskMetricsCalculator
from .stop_loss_manager import StopLossManager

__all__ = [
    # Core risk management (Sprint 1)
    "RiskValidation",
    "RiskCheckResult",
    "ValidationStatus",
    "ProtectionLayer",
    "Protection",
    "CircuitBreakerStatus",
    "CircuitBreakerState",
    "RiskManager",
    "CircuitBreaker",
    "StopLossManager",
    # Advanced risk management (Sprint 3 Stream B)
    "PortfolioRiskManager",
    "PortfolioLimits",
    "PortfolioStatus",
    "PositionInfo",
    "KellyPositionSizer",
    "TradeResult",
    "PositionSizingResult",
    "CorrelationAnalyzer",
    "CorrelationMatrix",
    "CorrelationPair",
    "PriceHistory",
    "RiskMetricsCalculator",
    "RiskMetrics",
]
