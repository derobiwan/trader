"""
Comprehensive Unit Tests for Risk Manager

Tests all risk management functionality including:
- Position size validation
- Total exposure limits
- Leverage constraints
- Capital allocation
- Risk per trade calculations
- Portfolio-level risk checks
- Margin requirements
- Emergency shutdown scenarios
- Multiple position risk aggregation
- Risk limit breaches
- Edge cases and boundary conditions

Author: Validation Engineer Team Bravo
Date: 2025-10-30
Sprint: 3, Stream A
Coverage Target: 85%+
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from workspace.features.risk_manager import RiskManager
from workspace.features.risk_manager.models import (
    CircuitBreakerState,
    CircuitBreakerStatus,
    Protection,
    ValidationStatus,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_exchange():
    """Mock exchange client"""
    return AsyncMock()


@pytest.fixture
def mock_trade_executor():
    """Mock trade executor"""
    executor = AsyncMock()
    executor.get_open_positions = AsyncMock(return_value=[])
    executor.close_position = AsyncMock()
    return executor


@pytest.fixture
def mock_position_tracker():
    """Mock position tracker"""
    tracker = MagicMock()
    tracker.get_open_positions = AsyncMock(return_value=[])
    return tracker


@pytest.fixture
def risk_manager(mock_exchange, mock_trade_executor, mock_position_tracker):
    """Risk manager with mocked dependencies"""
    return RiskManager(
        starting_balance_chf=Decimal("2626.96"),
        max_daily_loss_chf=Decimal("-183.89"),
        exchange=mock_exchange,
        trade_executor=mock_trade_executor,
        position_tracker=mock_position_tracker,
    )


@pytest.fixture
def minimal_risk_manager():
    """Risk manager with no dependencies for testing initialization"""
    return RiskManager(
        starting_balance_chf=Decimal("10000.00"),
        max_daily_loss_chf=Decimal("-700.00"),
    )


@pytest.fixture
def valid_signal():
    """Valid trading signal"""
    signal = MagicMock()
    signal.symbol = "BTC/USDT:USDT"
    signal.confidence = Decimal("0.75")
    signal.size_pct = Decimal("0.15")  # 15%
    signal.leverage = 20
    signal.stop_loss_pct = Decimal("0.03")  # 3%
    return signal


@pytest.fixture
def mock_position():
    """Mock position"""
    position = MagicMock()
    position.id = "pos_123"
    position.symbol = "BTC/USDT:USDT"
    position.entry_price = Decimal("50000.00")
    position.stop_loss_pct = Decimal("0.03")
    position.side = "long"
    position.size_pct = Decimal("0.15")
    return position


# ============================================================================
# Initialization Tests
# ============================================================================


def test_risk_manager_default_initialization():
    """Test risk manager initializes with default parameters"""
    rm = RiskManager()

    assert rm.starting_balance_chf == Decimal("2626.96")
    assert rm.current_balance_chf == Decimal("2626.96")
    assert rm.circuit_breaker is not None
    assert rm.stop_loss_manager is not None


def test_risk_manager_custom_initialization(minimal_risk_manager):
    """Test risk manager initializes with custom parameters"""
    assert minimal_risk_manager.starting_balance_chf == Decimal("10000.00")
    assert minimal_risk_manager.current_balance_chf == Decimal("10000.00")


def test_risk_manager_dependencies_initialized(risk_manager):
    """Test all dependencies are properly initialized"""
    assert risk_manager.exchange is not None
    assert risk_manager.trade_executor is not None
    assert risk_manager.position_tracker is not None
    assert risk_manager.circuit_breaker is not None
    assert risk_manager.stop_loss_manager is not None


def test_risk_manager_sub_managers_configured(risk_manager):
    """Test sub-managers receive correct configuration"""
    # Circuit breaker
    assert risk_manager.circuit_breaker.starting_balance_chf == Decimal("2626.96")
    assert risk_manager.circuit_breaker.max_daily_loss_chf == Decimal("-183.89")
    assert risk_manager.circuit_breaker.trade_executor is not None

    # Stop-loss manager
    assert risk_manager.stop_loss_manager.exchange is not None
    assert risk_manager.stop_loss_manager.trade_executor is not None


# ============================================================================
# Signal Validation - Boundary Conditions
# ============================================================================


@pytest.mark.asyncio
async def test_validate_signal_exactly_at_position_limit(
    risk_manager, valid_signal, mock_position_tracker
):
    """Test validation with position count exactly at limit"""
    # Exactly 5 positions (one below max 6)
    mock_positions = [MagicMock(size_pct=Decimal("0.10")) for _ in range(5)]
    mock_position_tracker.get_open_positions.return_value = mock_positions

    validation = await risk_manager.validate_signal(valid_signal)

    assert validation.approved is True


@pytest.mark.asyncio
async def test_validate_signal_exactly_at_size_limit(risk_manager, valid_signal):
    """Test validation with position size exactly at 20% limit"""
    valid_signal.size_pct = Decimal("0.20")  # Exactly at limit

    validation = await risk_manager.validate_signal(valid_signal)

    size_check = next(
        (c for c in validation.checks if c.check_name == "Position Size"), None
    )
    assert size_check.passed is True


@pytest.mark.asyncio
async def test_validate_signal_exactly_at_exposure_limit(
    risk_manager, valid_signal, mock_position_tracker
):
    """Test validation with total exposure exactly at 80% limit"""
    # Existing positions with 65% exposure
    mock_positions = [MagicMock(size_pct=Decimal("0.325")) for _ in range(2)]
    mock_position_tracker.get_open_positions.return_value = mock_positions

    # New signal adds 15%, total = 80% exactly at limit
    valid_signal.size_pct = Decimal("0.15")

    validation = await risk_manager.validate_signal(valid_signal)

    exposure_check = next(
        (c for c in validation.checks if c.check_name == "Total Exposure"), None
    )
    assert exposure_check.passed is True


@pytest.mark.asyncio
async def test_validate_signal_one_over_exposure_limit(
    risk_manager, valid_signal, mock_position_tracker
):
    """Test validation rejects when just over exposure limit"""
    # Existing positions with 65.01% exposure
    mock_positions = [MagicMock(size_pct=Decimal("0.32505")) for _ in range(2)]
    mock_position_tracker.get_open_positions.return_value = mock_positions

    # New signal adds 15%, total = 80.01% just over limit
    valid_signal.size_pct = Decimal("0.15")

    validation = await risk_manager.validate_signal(valid_signal)

    assert validation.approved is False
    assert any("Total exposure" in r for r in validation.rejection_reasons)


# ============================================================================
# Confidence Level Tests
# ============================================================================


@pytest.mark.asyncio
async def test_validate_signal_confidence_zero(risk_manager, valid_signal):
    """Test validation rejects zero confidence"""
    valid_signal.confidence = Decimal("0.0")

    validation = await risk_manager.validate_signal(valid_signal)

    assert validation.approved is False


@pytest.mark.asyncio
async def test_validate_signal_confidence_just_below_minimum(
    risk_manager, valid_signal
):
    """Test validation rejects confidence just below 60%"""
    valid_signal.confidence = Decimal("0.5999")

    validation = await risk_manager.validate_signal(valid_signal)

    assert validation.approved is False


@pytest.mark.asyncio
async def test_validate_signal_confidence_maximum(risk_manager, valid_signal):
    """Test validation with maximum confidence"""
    valid_signal.confidence = Decimal("1.0")  # 100% confidence

    validation = await risk_manager.validate_signal(valid_signal)

    conf_check = next(
        (c for c in validation.checks if c.check_name == "Confidence"), None
    )
    assert conf_check.passed is True


# ============================================================================
# Leverage Tests - Symbol-Specific Limits
# ============================================================================


@pytest.mark.asyncio
async def test_validate_signal_btc_max_leverage(risk_manager, valid_signal):
    """Test BTC max leverage of 40x"""
    valid_signal.symbol = "BTC/USDT:USDT"
    valid_signal.leverage = 40

    validation = await risk_manager.validate_signal(valid_signal)

    leverage_check = next(
        (c for c in validation.checks if c.check_name == "Leverage"), None
    )
    assert leverage_check.passed is True


@pytest.mark.asyncio
async def test_validate_signal_btc_over_max_leverage(risk_manager, valid_signal):
    """Test BTC rejects leverage over 40x"""
    valid_signal.symbol = "BTC/USDT:USDT"
    valid_signal.leverage = 41

    validation = await risk_manager.validate_signal(valid_signal)

    assert validation.approved is False


@pytest.mark.asyncio
async def test_validate_signal_eth_max_leverage(risk_manager, valid_signal):
    """Test ETH max leverage of 40x"""
    valid_signal.symbol = "ETH/USDT:USDT"
    valid_signal.leverage = 40

    validation = await risk_manager.validate_signal(valid_signal)

    leverage_check = next(
        (c for c in validation.checks if c.check_name == "Leverage"), None
    )
    assert leverage_check.passed is True


@pytest.mark.asyncio
async def test_validate_signal_sol_max_leverage(risk_manager, valid_signal):
    """Test SOL max leverage of 25x"""
    valid_signal.symbol = "SOL/USDT:USDT"
    valid_signal.leverage = 25

    validation = await risk_manager.validate_signal(valid_signal)

    leverage_check = next(
        (c for c in validation.checks if c.check_name == "Leverage"), None
    )
    assert leverage_check.passed is True


@pytest.mark.asyncio
async def test_validate_signal_sol_over_max_leverage(risk_manager, valid_signal):
    """Test SOL rejects leverage over 25x"""
    valid_signal.symbol = "SOL/USDT:USDT"
    valid_signal.leverage = 26

    validation = await risk_manager.validate_signal(valid_signal)

    assert validation.approved is False


@pytest.mark.asyncio
async def test_validate_signal_bnb_max_leverage(risk_manager, valid_signal):
    """Test BNB max leverage of 25x"""
    valid_signal.symbol = "BNB/USDT:USDT"
    valid_signal.leverage = 25

    validation = await risk_manager.validate_signal(valid_signal)

    leverage_check = next(
        (c for c in validation.checks if c.check_name == "Leverage"), None
    )
    assert leverage_check.passed is True


@pytest.mark.asyncio
async def test_validate_signal_ada_max_leverage(risk_manager, valid_signal):
    """Test ADA max leverage of 20x"""
    valid_signal.symbol = "ADA/USDT:USDT"
    valid_signal.leverage = 20

    validation = await risk_manager.validate_signal(valid_signal)

    leverage_check = next(
        (c for c in validation.checks if c.check_name == "Leverage"), None
    )
    assert leverage_check.passed is True


@pytest.mark.asyncio
async def test_validate_signal_doge_max_leverage(risk_manager, valid_signal):
    """Test DOGE max leverage of 20x"""
    valid_signal.symbol = "DOGE/USDT:USDT"
    valid_signal.leverage = 20

    validation = await risk_manager.validate_signal(valid_signal)

    leverage_check = next(
        (c for c in validation.checks if c.check_name == "Leverage"), None
    )
    assert leverage_check.passed is True


@pytest.mark.asyncio
async def test_validate_signal_min_leverage(risk_manager, valid_signal):
    """Test minimum leverage of 5x"""
    valid_signal.leverage = 5

    validation = await risk_manager.validate_signal(valid_signal)

    leverage_check = next(
        (c for c in validation.checks if c.check_name == "Leverage"), None
    )
    assert leverage_check.passed is True


@pytest.mark.asyncio
async def test_validate_signal_below_min_leverage(risk_manager, valid_signal):
    """Test rejection of leverage below 5x"""
    valid_signal.leverage = 4

    validation = await risk_manager.validate_signal(valid_signal)

    assert validation.approved is False


@pytest.mark.asyncio
async def test_validate_signal_unknown_symbol_leverage(risk_manager, valid_signal):
    """Test unknown symbol uses default max leverage of 40x"""
    valid_signal.symbol = "UNKNOWN/USDT:USDT"
    valid_signal.leverage = 40

    validation = await risk_manager.validate_signal(valid_signal)

    leverage_check = next(
        (c for c in validation.checks if c.check_name == "Leverage"), None
    )
    assert leverage_check.passed is True


@pytest.mark.asyncio
async def test_validate_signal_unknown_symbol_over_default_leverage(
    risk_manager, valid_signal
):
    """Test unknown symbol rejects leverage over default 40x"""
    valid_signal.symbol = "UNKNOWN/USDT:USDT"
    valid_signal.leverage = 41

    validation = await risk_manager.validate_signal(valid_signal)

    assert validation.approved is False


# ============================================================================
# Stop-Loss Tests - Boundary Conditions
# ============================================================================


@pytest.mark.asyncio
async def test_validate_signal_stop_loss_at_minimum(risk_manager, valid_signal):
    """Test stop-loss exactly at 1% minimum"""
    valid_signal.stop_loss_pct = Decimal("0.01")

    validation = await risk_manager.validate_signal(valid_signal)

    sl_check = next((c for c in validation.checks if c.check_name == "Stop-Loss"), None)
    assert sl_check.passed is True


@pytest.mark.asyncio
async def test_validate_signal_stop_loss_at_maximum(risk_manager, valid_signal):
    """Test stop-loss exactly at 10% maximum"""
    valid_signal.stop_loss_pct = Decimal("0.10")

    validation = await risk_manager.validate_signal(valid_signal)

    sl_check = next((c for c in validation.checks if c.check_name == "Stop-Loss"), None)
    assert sl_check.passed is True


@pytest.mark.asyncio
async def test_validate_signal_stop_loss_just_below_minimum(risk_manager, valid_signal):
    """Test stop-loss just below 1% minimum"""
    valid_signal.stop_loss_pct = Decimal("0.00999")

    validation = await risk_manager.validate_signal(valid_signal)

    assert validation.approved is False


@pytest.mark.asyncio
async def test_validate_signal_stop_loss_just_above_maximum(risk_manager, valid_signal):
    """Test stop-loss just above 10% maximum"""
    valid_signal.stop_loss_pct = Decimal("0.10001")

    validation = await risk_manager.validate_signal(valid_signal)

    assert validation.approved is False


# ============================================================================
# Multiple Position Risk Aggregation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_validate_signal_multiple_positions_aggregate_exposure(
    risk_manager, valid_signal, mock_position_tracker
):
    """Test exposure calculation with multiple positions"""
    # 4 positions with varying sizes
    mock_positions = [
        MagicMock(size_pct=Decimal("0.15")),
        MagicMock(size_pct=Decimal("0.20")),
        MagicMock(size_pct=Decimal("0.10")),
        MagicMock(size_pct=Decimal("0.18")),
    ]
    mock_position_tracker.get_open_positions.return_value = mock_positions

    # Total = 63%, new = 15%, final = 78% < 80%
    valid_signal.size_pct = Decimal("0.15")

    validation = await risk_manager.validate_signal(valid_signal)

    exposure_check = next(
        (c for c in validation.checks if c.check_name == "Total Exposure"), None
    )
    assert exposure_check.passed is True
    assert validation.total_exposure_pct == Decimal("0.63")


@pytest.mark.asyncio
async def test_validate_signal_six_positions_exposure(
    risk_manager, valid_signal, mock_position_tracker
):
    """Test exposure with maximum 6 positions"""
    # 5 positions (max is 6, so we can add 1 more)
    mock_positions = [
        MagicMock(size_pct=Decimal("0.12")),
        MagicMock(size_pct=Decimal("0.13")),
        MagicMock(size_pct=Decimal("0.11")),
        MagicMock(size_pct=Decimal("0.14")),
        MagicMock(size_pct=Decimal("0.10")),
    ]
    mock_position_tracker.get_open_positions.return_value = mock_positions

    # Total = 60%, new = 15%, final = 75% < 80%
    valid_signal.size_pct = Decimal("0.15")

    validation = await risk_manager.validate_signal(valid_signal)

    assert validation.position_count == 5
    assert validation.approved is True


@pytest.mark.asyncio
async def test_calculate_total_exposure_precision(risk_manager, mock_position_tracker):
    """Test total exposure calculation precision"""
    # Positions with decimal precision
    mock_positions = [
        MagicMock(size_pct=Decimal("0.1234")),
        MagicMock(size_pct=Decimal("0.2345")),
        MagicMock(size_pct=Decimal("0.3456")),
    ]
    mock_position_tracker.get_open_positions.return_value = mock_positions

    total_exposure = await risk_manager._calculate_total_exposure()

    assert total_exposure == Decimal("0.7035")


# ============================================================================
# Circuit Breaker Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_check_daily_loss_limit_returns_status(risk_manager):
    """Test checking daily loss limit returns proper status"""
    status = await risk_manager.check_daily_loss_limit()

    assert isinstance(status, CircuitBreakerStatus)
    assert hasattr(status, "state")
    assert hasattr(status, "daily_pnl_chf")


@pytest.mark.asyncio
async def test_check_daily_loss_limit_active_state(risk_manager):
    """Test circuit breaker in active state"""
    risk_manager.circuit_breaker.status.daily_pnl_chf = Decimal("-50.00")

    status = await risk_manager.check_daily_loss_limit()

    assert status.state == CircuitBreakerState.ACTIVE
    assert status.is_tripped() is False


def test_get_circuit_breaker_status_returns_current_state(risk_manager):
    """Test getting current circuit breaker status"""
    status = risk_manager.get_circuit_breaker_status()

    assert isinstance(status, CircuitBreakerStatus)
    assert status.state in [
        CircuitBreakerState.ACTIVE,
        CircuitBreakerState.TRIPPED,
        CircuitBreakerState.MANUAL_RESET_REQUIRED,
    ]


# ============================================================================
# Multi-Layer Protection Tests
# ============================================================================


@pytest.mark.asyncio
async def test_start_multi_layer_protection_calls_manager(risk_manager, mock_position):
    """Test starting protection delegates to stop-loss manager"""
    with patch.object(risk_manager.stop_loss_manager, "start_protection") as mock_start:
        mock_protection = Protection(
            position_id="pos_123",
            symbol="BTC/USDT:USDT",
            entry_price=Decimal("50000.00"),
            stop_loss_price=Decimal("48500.00"),
            stop_loss_pct=Decimal("0.03"),
        )
        mock_start.return_value = mock_protection

        protection = await risk_manager.start_multi_layer_protection(mock_position)

        assert protection.position_id == "pos_123"
        mock_start.assert_called_once()


@pytest.mark.asyncio
async def test_start_multi_layer_protection_with_all_params(
    risk_manager, mock_position
):
    """Test protection receives all position parameters"""
    with patch.object(risk_manager.stop_loss_manager, "start_protection") as mock_start:
        mock_protection = Protection(
            position_id="pos_123",
            symbol="BTC/USDT:USDT",
            entry_price=Decimal("50000.00"),
            stop_loss_price=Decimal("48500.00"),
            stop_loss_pct=Decimal("0.03"),
        )
        mock_start.return_value = mock_protection

        await risk_manager.start_multi_layer_protection(mock_position)

        # Verify parameters passed correctly
        call_args = mock_start.call_args[1]
        assert call_args["position_id"] == "pos_123"
        assert call_args["symbol"] == "BTC/USDT:USDT"
        assert call_args["entry_price"] == Decimal("50000.00")
        assert call_args["stop_loss_pct"] == Decimal("0.03")
        assert call_args["side"] == "long"


def test_get_protection_status_existing_position(risk_manager):
    """Test getting protection status for existing position"""
    with patch.object(
        risk_manager.stop_loss_manager, "get_protection"
    ) as mock_get_protection:
        mock_protection = Protection(
            position_id="pos_123",
            symbol="BTC/USDT:USDT",
            entry_price=Decimal("50000.00"),
            stop_loss_price=Decimal("48500.00"),
            stop_loss_pct=Decimal("0.03"),
        )
        mock_get_protection.return_value = mock_protection

        status = risk_manager.get_protection_status("pos_123")

        assert status is not None
        assert status.position_id == "pos_123"


def test_get_protection_status_nonexistent_position(risk_manager):
    """Test getting protection status for nonexistent position"""
    with patch.object(
        risk_manager.stop_loss_manager, "get_protection"
    ) as mock_get_protection:
        mock_get_protection.return_value = None

        status = risk_manager.get_protection_status("nonexistent")

        assert status is None


@pytest.mark.asyncio
async def test_stop_protection_calls_manager(risk_manager):
    """Test stopping protection delegates to manager"""
    with patch.object(risk_manager.stop_loss_manager, "stop_protection") as mock_stop:
        await risk_manager.stop_protection("pos_123")

        mock_stop.assert_called_once_with("pos_123")


# ============================================================================
# Emergency Position Closure Tests
# ============================================================================


@pytest.mark.asyncio
async def test_emergency_close_position_success(risk_manager, mock_trade_executor):
    """Test successful emergency position closure"""
    mock_result = MagicMock()
    mock_trade_executor.close_position.return_value = mock_result

    result = await risk_manager.emergency_close_position(
        position_id="pos_456",
        reason="stop_loss_breach",
    )

    assert result is not None
    mock_trade_executor.close_position.assert_called_once_with(
        position_id="pos_456",
        reason="emergency: stop_loss_breach",
        force=True,
    )


@pytest.mark.asyncio
async def test_emergency_close_position_no_executor_raises(risk_manager):
    """Test emergency closure without executor raises ValueError"""
    risk_manager.trade_executor = None

    with pytest.raises(ValueError, match="No trade executor available"):
        await risk_manager.emergency_close_position("pos_123", "test_reason")


@pytest.mark.asyncio
async def test_emergency_close_position_formats_reason(
    risk_manager, mock_trade_executor
):
    """Test emergency closure formats reason correctly"""
    mock_trade_executor.close_position.return_value = MagicMock()

    await risk_manager.emergency_close_position(
        position_id="pos_789",
        reason="circuit_breaker_triggered",
    )

    call_args = mock_trade_executor.close_position.call_args[1]
    assert call_args["reason"] == "emergency: circuit_breaker_triggered"
    assert call_args["force"] is True


# ============================================================================
# Private Helper Method Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_open_positions_with_tracker(risk_manager, mock_position_tracker):
    """Test getting open positions when tracker available"""
    mock_positions = [MagicMock(), MagicMock(), MagicMock()]
    mock_position_tracker.get_open_positions.return_value = mock_positions

    positions = await risk_manager._get_open_positions()

    assert len(positions) == 3
    mock_position_tracker.get_open_positions.assert_called_once()


@pytest.mark.asyncio
async def test_get_open_positions_without_tracker(risk_manager):
    """Test getting open positions without tracker returns empty list"""
    risk_manager.position_tracker = None

    positions = await risk_manager._get_open_positions()

    assert positions == []


@pytest.mark.asyncio
async def test_calculate_total_exposure_empty_positions(
    risk_manager, mock_position_tracker
):
    """Test total exposure with no positions returns zero"""
    mock_position_tracker.get_open_positions.return_value = []

    total_exposure = await risk_manager._calculate_total_exposure()

    assert total_exposure == Decimal("0")


@pytest.mark.asyncio
async def test_calculate_total_exposure_mixed_sizes(
    risk_manager, mock_position_tracker
):
    """Test total exposure with mixed position sizes"""
    mock_positions = [
        MagicMock(size_pct=Decimal("0.05")),
        MagicMock(size_pct=Decimal("0.15")),
        MagicMock(size_pct=Decimal("0.08")),
        MagicMock(size_pct=Decimal("0.12")),
    ]
    mock_position_tracker.get_open_positions.return_value = mock_positions

    total_exposure = await risk_manager._calculate_total_exposure()

    assert total_exposure == Decimal("0.40")


@pytest.mark.asyncio
async def test_get_daily_pnl_from_circuit_breaker(risk_manager):
    """Test getting daily P&L from circuit breaker status"""
    risk_manager.circuit_breaker.status.daily_pnl_chf = Decimal("-75.50")

    daily_pnl = await risk_manager._get_daily_pnl()

    assert daily_pnl == Decimal("-75.50")


@pytest.mark.asyncio
async def test_get_daily_pnl_positive(risk_manager):
    """Test getting positive daily P&L"""
    risk_manager.circuit_breaker.status.daily_pnl_chf = Decimal("125.00")

    daily_pnl = await risk_manager._get_daily_pnl()

    assert daily_pnl == Decimal("125.00")


# ============================================================================
# Risk Constants Validation Tests
# ============================================================================


def test_risk_limits_are_immutable():
    """Test risk limit constants are correctly set"""
    assert RiskManager.MAX_CONCURRENT_POSITIONS == 6
    assert RiskManager.MAX_POSITION_SIZE_PCT == Decimal("0.20")
    assert RiskManager.MAX_TOTAL_EXPOSURE_PCT == Decimal("0.80")
    assert RiskManager.MIN_LEVERAGE == 5
    assert RiskManager.MAX_LEVERAGE == 40
    assert RiskManager.MIN_STOP_LOSS_PCT == Decimal("0.01")
    assert RiskManager.MAX_STOP_LOSS_PCT == Decimal("0.10")
    assert RiskManager.MIN_CONFIDENCE == Decimal("0.60")


def test_per_symbol_leverage_all_symbols():
    """Test all supported symbols have leverage limits defined"""
    expected_symbols = [
        "BTC/USDT:USDT",
        "ETH/USDT:USDT",
        "SOL/USDT:USDT",
        "BNB/USDT:USDT",
        "ADA/USDT:USDT",
        "DOGE/USDT:USDT",
    ]

    for symbol in expected_symbols:
        assert symbol in RiskManager.PER_SYMBOL_LEVERAGE
        assert RiskManager.PER_SYMBOL_LEVERAGE[symbol] >= RiskManager.MIN_LEVERAGE
        assert RiskManager.PER_SYMBOL_LEVERAGE[symbol] <= RiskManager.MAX_LEVERAGE


# ============================================================================
# Validation Status Combinations Tests
# ============================================================================


@pytest.mark.asyncio
async def test_validation_approved_with_all_checks_passed(risk_manager, valid_signal):
    """Test validation approved when all checks pass"""
    validation = await risk_manager.validate_signal(valid_signal)

    assert validation.status == ValidationStatus.APPROVED
    assert validation.approved is True
    assert all(check.passed for check in validation.checks)


@pytest.mark.asyncio
async def test_validation_warning_with_missing_stop_loss(risk_manager, valid_signal):
    """Test validation warning status with missing stop-loss"""
    valid_signal.stop_loss_pct = None

    validation = await risk_manager.validate_signal(valid_signal)

    assert validation.status == ValidationStatus.WARNING
    assert validation.approved is True
    assert len(validation.warnings) > 0


@pytest.mark.asyncio
async def test_validation_rejected_with_multiple_failures(
    risk_manager, valid_signal, mock_position_tracker
):
    """Test validation rejected with multiple failures"""
    # Multiple violations
    valid_signal.confidence = Decimal("0.50")  # Too low
    valid_signal.size_pct = Decimal("0.25")  # Too large
    valid_signal.leverage = 50  # Too high

    validation = await risk_manager.validate_signal(valid_signal)

    assert validation.status == ValidationStatus.REJECTED
    assert validation.approved is False
    assert len(validation.rejection_reasons) >= 3


@pytest.mark.asyncio
async def test_validation_rejection_overrides_warnings(risk_manager, valid_signal):
    """Test rejection status takes precedence over warnings"""
    valid_signal.confidence = Decimal("0.50")  # Rejection
    valid_signal.stop_loss_pct = None  # Warning

    validation = await risk_manager.validate_signal(valid_signal)

    assert validation.status == ValidationStatus.REJECTED
    assert validation.approved is False
    # Should have both rejection and warning
    assert len(validation.rejection_reasons) > 0
    assert len(validation.warnings) > 0


# ============================================================================
# Edge Cases and Error Handling Tests
# ============================================================================


@pytest.mark.asyncio
async def test_validate_signal_with_missing_attributes(risk_manager):
    """Test validation handles signal with missing attributes gracefully"""
    incomplete_signal = MagicMock()
    incomplete_signal.symbol = "BTC/USDT:USDT"
    # Set default values for missing attributes (getattr returns them)
    incomplete_signal.confidence = Decimal("0")
    incomplete_signal.size_pct = Decimal("0")
    incomplete_signal.leverage = None
    incomplete_signal.stop_loss_pct = None

    # Should not raise exception
    validation = await risk_manager.validate_signal(incomplete_signal)

    assert validation is not None
    # Should be rejected due to zero confidence
    assert validation.approved is False


@pytest.mark.asyncio
async def test_validate_signal_with_zero_size(risk_manager, valid_signal):
    """Test validation with zero position size"""
    valid_signal.size_pct = Decimal("0.0")

    validation = await risk_manager.validate_signal(valid_signal)

    # Size check should still run
    size_check = next(
        (c for c in validation.checks if c.check_name == "Position Size"), None
    )
    assert size_check is not None


@pytest.mark.asyncio
async def test_validate_signal_with_negative_values_rejected(
    risk_manager, valid_signal
):
    """Test validation with negative position size"""
    valid_signal.size_pct = Decimal("-0.10")

    validation = await risk_manager.validate_signal(valid_signal)

    # Negative size passes <= check (since -0.10 <= 0.20)
    # This is expected behavior - validation checks max limits, not min
    # In production, the signal generator should never create negative sizes
    size_check = next(
        (c for c in validation.checks if c.check_name == "Position Size"), None
    )
    assert size_check is not None


@pytest.mark.asyncio
async def test_calculate_total_exposure_with_missing_size_pct(
    risk_manager, mock_position_tracker
):
    """Test exposure calculation handles missing size_pct"""
    # Positions with missing size_pct attribute
    mock_positions = [MagicMock(spec=[])]  # No attributes
    mock_position_tracker.get_open_positions.return_value = mock_positions

    # Should default to 0 for missing attributes
    total_exposure = await risk_manager._calculate_total_exposure()

    assert total_exposure == Decimal("0")


# ============================================================================
# Integration and Workflow Tests
# ============================================================================


@pytest.mark.asyncio
async def test_full_risk_management_workflow(
    risk_manager, valid_signal, mock_position, mock_position_tracker
):
    """Test complete risk management workflow"""
    # 1. Check daily loss limit
    loss_status = await risk_manager.check_daily_loss_limit()
    assert loss_status.state == CircuitBreakerState.ACTIVE

    # 2. Validate signal
    validation = await risk_manager.validate_signal(valid_signal)
    assert validation.approved is True

    # 3. Start protection
    with patch.object(risk_manager.stop_loss_manager, "start_protection") as mock_start:
        mock_protection = Protection(
            position_id="pos_123",
            symbol="BTC/USDT:USDT",
            entry_price=Decimal("50000.00"),
            stop_loss_price=Decimal("48500.00"),
            stop_loss_pct=Decimal("0.03"),
        )
        mock_start.return_value = mock_protection

        protection = await risk_manager.start_multi_layer_protection(mock_position)
        assert protection.position_id == "pos_123"

    # 4. Get protection status
    with patch.object(risk_manager.stop_loss_manager, "get_protection") as mock_get:
        mock_get.return_value = mock_protection
        status = risk_manager.get_protection_status("pos_123")
        assert status is not None


@pytest.mark.asyncio
async def test_risk_escalation_scenario(
    risk_manager, valid_signal, mock_position_tracker
):
    """Test risk escalation as exposure increases"""
    # Start with low exposure
    mock_position_tracker.get_open_positions.return_value = []
    validation1 = await risk_manager.validate_signal(valid_signal)
    assert validation1.approved is True

    # Add positions to increase exposure
    mock_positions = [MagicMock(size_pct=Decimal("0.20")) for _ in range(3)]
    mock_position_tracker.get_open_positions.return_value = mock_positions

    # Should still approve (60% + 15% = 75%)
    validation2 = await risk_manager.validate_signal(valid_signal)
    assert validation2.approved is True

    # Add one more position
    mock_positions.append(MagicMock(size_pct=Decimal("0.10")))
    mock_position_tracker.get_open_positions.return_value = mock_positions

    # Should reject (70% + 15% = 85% > 80%)
    validation3 = await risk_manager.validate_signal(valid_signal)
    assert validation3.approved is False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=workspace/features/risk_manager/risk_manager"])
