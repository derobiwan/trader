"""
Position Manager

Core service for managing trading position lifecycle including creation,
updates, P&L tracking, stop-loss monitoring, and closure.

Usage:
    from workspace.features.position_manager import (
        PositionService,
        PositionCreateRequest,
        PositionWithPnL,
        ValidationError,
        RiskLimitError
    )
"""

from workspace.features.position_manager.models import (  # Request Models; Response Models; Enums; Exceptions; Constants
    CAPITAL_CHF,
    CIRCUIT_BREAKER_LOSS_CHF,
    MAX_LEVERAGE,
    MAX_POSITION_SIZE_CHF,
    MAX_TOTAL_EXPOSURE_CHF,
    MIN_LEVERAGE,
    VALID_SYMBOLS,
    CloseReason,
    DailyPnLSummary,
    InsufficientCapitalError,
    PositionCloseRequest,
    PositionCreateRequest,
    PositionNotFoundError,
    PositionStatistics,
    PositionUpdateRequest,
    PositionWithPnL,
    RiskLimitError,
    ValidationError,
)
from workspace.features.position_manager.position_service import (
    PositionService,
    bulk_update_prices,
)

# Alias for consistency with other modules
PositionManager = PositionService

__all__ = [
    # Service
    "PositionService",
    "PositionManager",  # Alias for PositionService
    "bulk_update_prices",
    # Request Models
    "PositionCreateRequest",
    "PositionUpdateRequest",
    "PositionCloseRequest",
    # Response Models
    "PositionWithPnL",
    "DailyPnLSummary",
    "PositionStatistics",
    # Enums
    "CloseReason",
    # Exceptions
    "ValidationError",
    "RiskLimitError",
    "PositionNotFoundError",
    "InsufficientCapitalError",
    # Constants
    "CAPITAL_CHF",
    "CIRCUIT_BREAKER_LOSS_CHF",
    "MAX_POSITION_SIZE_CHF",
    "MAX_TOTAL_EXPOSURE_CHF",
    "MIN_LEVERAGE",
    "MAX_LEVERAGE",
    "VALID_SYMBOLS",
]

__version__ = "1.0.0"
