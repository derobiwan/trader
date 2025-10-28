"""
Risk Manager Tests

Comprehensive tests for risk management system.

Author: Risk Management Team
Date: 2025-10-28
"""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime, timezone
from dataclasses import dataclass

from workspace.features.risk_manager import (
    RiskManager,
    CircuitBreaker,
    StopLossManager,
    RiskValidation,
    ValidationStatus,
    CircuitBreakerState,
    Protection,
)


# ============================================================================
# Mock Classes
# ============================================================================

@dataclass
class MockSignal:
    """Mock trading signal for testing"""
    symbol: str = "BTC/USDT:USDT"
    decision: str = "BUY"
    confidence: Decimal = Decimal("0.75")
    size_pct: Decimal = Decimal("0.15")
    stop_loss_pct: Decimal = Decimal("0.03")
    take_profit_pct: Decimal = Decimal("0.06")
    leverage: int = 10


@dataclass
class MockPosition:
    """Mock position for testing"""
    id: str = "pos_123"
    symbol: str = "BTC/USDT:USDT"
    entry_price: Decimal = Decimal("50000")
    stop_loss_pct: Decimal = Decimal("0.03")
    size_pct: Decimal = Decimal("0.15")
    side: str = "long"


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def risk_manager():
    """Create risk manager instance"""
    return RiskManager(
        starting_balance_chf=Decimal("2626.96"),
        max_daily_loss_chf=Decimal("-183.89"),
    )


@pytest.fixture
def circuit_breaker():
    """Create circuit breaker instance"""
    return CircuitBreaker(
        starting_balance_chf=Decimal("2626.96"),
        max_daily_loss_chf=Decimal("-183.89"),
    )


@pytest.fixture
def stop_loss_manager():
    """Create stop-loss manager instance"""
    return StopLossManager()


# ============================================================================
# Risk Manager Tests
# ============================================================================

class TestRiskManager:
    """Tests for Risk Manager"""

    @pytest.mark.asyncio
    async def test_validate_signal_approved(self, risk_manager):
        """Test signal validation with valid signal"""
        signal = MockSignal(
            confidence=Decimal("0.75"),
            size_pct=Decimal("0.15"),
            stop_loss_pct=Decimal("0.03"),
        )

        validation = await risk_manager.validate_signal(signal)

        assert validation.approved is True
        assert validation.status in [ValidationStatus.APPROVED, ValidationStatus.WARNING]
        assert len(validation.checks) > 0

    @pytest.mark.asyncio
    async def test_validate_signal_low_confidence(self, risk_manager):
        """Test signal rejection due to low confidence"""
        signal = MockSignal(confidence=Decimal("0.50"))  # Below 60% minimum

        validation = await risk_manager.validate_signal(signal)

        assert validation.approved is False
        assert validation.status == ValidationStatus.REJECTED
        assert any("confidence" in r.lower() for r in validation.rejection_reasons)

    @pytest.mark.asyncio
    async def test_validate_signal_large_position(self, risk_manager):
        """Test signal rejection due to large position size"""
        signal = MockSignal(size_pct=Decimal("0.25"))  # Above 20% maximum

        validation = await risk_manager.validate_signal(signal)

        assert validation.approved is False
        assert validation.status == ValidationStatus.REJECTED
        assert any("position size" in r.lower() for r in validation.rejection_reasons)

    @pytest.mark.asyncio
    async def test_validate_signal_invalid_stop_loss(self, risk_manager):
        """Test signal rejection due to invalid stop-loss"""
        signal = MockSignal(stop_loss_pct=Decimal("0.005"))  # Below 1% minimum

        validation = await risk_manager.validate_signal(signal)

        assert validation.approved is False
        assert validation.status == ValidationStatus.REJECTED

    def test_risk_manager_initialization(self, risk_manager):
        """Test risk manager initialization"""
        assert risk_manager.starting_balance_chf == Decimal("2626.96")
        assert risk_manager.circuit_breaker is not None
        assert risk_manager.stop_loss_manager is not None

    def test_get_circuit_breaker_status(self, risk_manager):
        """Test getting circuit breaker status"""
        status = risk_manager.get_circuit_breaker_status()

        assert status.state == CircuitBreakerState.ACTIVE
        assert status.daily_pnl_chf == Decimal("0")


# ============================================================================
# Circuit Breaker Tests
# ============================================================================

class TestCircuitBreaker:
    """Tests for Circuit Breaker"""

    @pytest.mark.asyncio
    async def test_circuit_breaker_active_state(self, circuit_breaker):
        """Test circuit breaker starts in active state"""
        status = await circuit_breaker.check_daily_loss(Decimal("0"))

        assert status.state == CircuitBreakerState.ACTIVE
        assert status.is_tripped() is False

    @pytest.mark.asyncio
    async def test_circuit_breaker_trips_on_loss(self, circuit_breaker):
        """Test circuit breaker trips when loss limit exceeded"""
        # Set daily P&L below limit
        daily_pnl = Decimal("-200.00")  # Below -183.89 limit

        status = await circuit_breaker.check_daily_loss(daily_pnl)

        assert status.state in [CircuitBreakerState.TRIPPED, CircuitBreakerState.MANUAL_RESET_REQUIRED]
        assert status.daily_pnl_chf == daily_pnl

    @pytest.mark.asyncio
    async def test_circuit_breaker_no_trip_within_limit(self, circuit_breaker):
        """Test circuit breaker doesn't trip within limit"""
        daily_pnl = Decimal("-100.00")  # Above -183.89 limit

        status = await circuit_breaker.check_daily_loss(daily_pnl)

        assert status.state == CircuitBreakerState.ACTIVE
        assert status.is_tripped() is False

    def test_circuit_breaker_loss_percentage(self, circuit_breaker):
        """Test loss percentage calculation"""
        circuit_breaker.status.daily_pnl_chf = Decimal("-131.35")  # -5%

        loss_pct = circuit_breaker.status.loss_percentage()

        # Allow for small floating point precision differences
        assert abs(loss_pct - Decimal("-5.0")) < Decimal("0.01")

    def test_circuit_breaker_remaining_allowance(self, circuit_breaker):
        """Test remaining loss allowance calculation"""
        circuit_breaker.status.daily_pnl_chf = Decimal("-100.00")

        remaining = circuit_breaker.status.remaining_loss_allowance_chf()

        assert remaining == Decimal("-83.89")  # -183.89 - (-100) = -83.89

    @pytest.mark.asyncio
    async def test_daily_reset(self, circuit_breaker):
        """Test daily circuit breaker reset"""
        # Set some loss
        circuit_breaker.status.daily_pnl_chf = Decimal("-50.00")

        # Reset
        await circuit_breaker.daily_reset()

        assert circuit_breaker.status.daily_pnl_chf == Decimal("0")
        assert circuit_breaker.status.state == CircuitBreakerState.ACTIVE


# ============================================================================
# Stop-Loss Manager Tests
# ============================================================================

class TestStopLossManager:
    """Tests for Stop-Loss Manager"""

    @pytest.mark.asyncio
    async def test_start_protection_creates_protection(self, stop_loss_manager):
        """Test starting protection creates Protection object"""
        protection = await stop_loss_manager.start_protection(
            position_id="pos_123",
            symbol="BTC/USDT:USDT",
            entry_price=Decimal("50000"),
            stop_loss_pct=Decimal("0.03"),
            side="long",
        )

        assert protection.position_id == "pos_123"
        assert protection.symbol == "BTC/USDT:USDT"
        assert protection.entry_price == Decimal("50000")
        assert protection.stop_loss_price == Decimal("48500")  # 50000 * (1 - 0.03)

    @pytest.mark.asyncio
    async def test_protection_layer_count(self, stop_loss_manager):
        """Test protection reports correct layer count"""
        protection = await stop_loss_manager.start_protection(
            position_id="pos_123",
            symbol="BTC/USDT:USDT",
            entry_price=Decimal("50000"),
            stop_loss_pct=Decimal("0.03"),
        )

        # Without exchange client, should have 2 layers active (app + emergency)
        assert protection.layer_count() >= 2

    @pytest.mark.asyncio
    async def test_stop_protection_removes_protection(self, stop_loss_manager):
        """Test stopping protection removes it from tracking"""
        await stop_loss_manager.start_protection(
            position_id="pos_123",
            symbol="BTC/USDT:USDT",
            entry_price=Decimal("50000"),
            stop_loss_pct=Decimal("0.03"),
        )

        await stop_loss_manager.stop_protection("pos_123")

        protection = stop_loss_manager.get_protection("pos_123")
        assert protection is None

    def test_get_all_protections(self, stop_loss_manager):
        """Test getting all protections"""
        protections = stop_loss_manager.get_all_protections()

        assert isinstance(protections, dict)


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
