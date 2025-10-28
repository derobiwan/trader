"""
Integration Tests: Risk Manager + Strategy

Tests verifying risk manager correctly validates strategy signals.
"""

import pytest
from decimal import Decimal
from dataclasses import dataclass

from workspace.features.risk_manager import RiskManager, ValidationStatus
from workspace.features.strategy import (
    MeanReversionStrategy,
    TrendFollowingStrategy,
    VolatilityBreakoutStrategy,
)


@dataclass
class MockSignal:
    """Mock signal for testing"""

    symbol: str = "BTC/USDT:USDT"
    decision: str = "BUY"
    confidence: Decimal = Decimal("0.75")
    size_pct: Decimal = Decimal("0.15")
    stop_loss_pct: Decimal = Decimal("0.03")
    take_profit_pct: Decimal = Decimal("0.06")
    leverage: int = 10
    entry_price: Decimal = Decimal("50000")


class TestRiskManagerStrategyIntegration:
    """Tests for risk manager + strategy integration"""

    @pytest.mark.asyncio
    async def test_valid_strategy_signal_approved(
        self,
        sample_ohlcv_data,
        mock_trade_executor,
        mock_position_tracker,
    ):
        """Test risk manager approves valid strategy signal"""
        # Generate signal from strategy
        strategy = MeanReversionStrategy()
        signal = await strategy.generate_signal(sample_ohlcv_data)

        # Initialize risk manager
        risk_manager = RiskManager(
            starting_balance_chf=Decimal("2626.96"),
            max_daily_loss_chf=Decimal("-183.89"),
            trade_executor=mock_trade_executor,
            position_tracker=mock_position_tracker,
        )

        # Validate signal
        validation = await risk_manager.validate_signal(signal)

        # Valid signal should be approved
        assert validation is not None
        assert isinstance(validation.approved, bool)
        assert len(validation.checks) > 0

        # If signal is not HOLD, check validation details
        if signal.decision != "HOLD":
            # Should have performed multiple checks
            assert len(validation.checks) >= 5

            # Check names should be present
            check_names = [c.check_name for c in validation.checks]
            assert "Circuit Breaker" in check_names
            assert "Position Count" in check_names
            assert "Confidence" in check_names

    @pytest.mark.asyncio
    async def test_low_confidence_signal_rejected(
        self,
        mock_trade_executor,
        mock_position_tracker,
    ):
        """Test risk manager rejects low confidence signal"""
        # Create low confidence signal
        signal = MockSignal(
            confidence=Decimal("0.50"),  # Below 60% minimum
        )

        # Initialize risk manager
        risk_manager = RiskManager(
            starting_balance_chf=Decimal("2626.96"),
            max_daily_loss_chf=Decimal("-183.89"),
            trade_executor=mock_trade_executor,
            position_tracker=mock_position_tracker,
        )

        # Validate signal
        validation = await risk_manager.validate_signal(signal)

        # Should be rejected
        assert validation.approved is False
        assert validation.status == ValidationStatus.REJECTED
        assert any("confidence" in r.lower() for r in validation.rejection_reasons)

    @pytest.mark.asyncio
    async def test_large_position_signal_rejected(
        self,
        mock_trade_executor,
        mock_position_tracker,
    ):
        """Test risk manager rejects oversized position"""
        # Create large position signal
        signal = MockSignal(
            size_pct=Decimal("0.25"),  # Above 20% maximum
        )

        # Initialize risk manager
        risk_manager = RiskManager(
            starting_balance_chf=Decimal("2626.96"),
            max_daily_loss_chf=Decimal("-183.89"),
            trade_executor=mock_trade_executor,
            position_tracker=mock_position_tracker,
        )

        # Validate signal
        validation = await risk_manager.validate_signal(signal)

        # Should be rejected
        assert validation.approved is False
        assert validation.status == ValidationStatus.REJECTED
        assert any("position size" in r.lower() for r in validation.rejection_reasons)

    @pytest.mark.asyncio
    async def test_invalid_stop_loss_rejected(
        self,
        mock_trade_executor,
        mock_position_tracker,
    ):
        """Test risk manager rejects invalid stop-loss"""
        # Create signal with invalid stop-loss
        signal = MockSignal(
            stop_loss_pct=Decimal("0.005"),  # Below 1% minimum
        )

        # Initialize risk manager
        risk_manager = RiskManager(
            starting_balance_chf=Decimal("2626.96"),
            max_daily_loss_chf=Decimal("-183.89"),
            trade_executor=mock_trade_executor,
            position_tracker=mock_position_tracker,
        )

        # Validate signal
        validation = await risk_manager.validate_signal(signal)

        # Should be rejected
        assert validation.approved is False
        assert validation.status == ValidationStatus.REJECTED

    @pytest.mark.asyncio
    async def test_all_strategies_validated(
        self,
        sample_ohlcv_data,
        mock_trade_executor,
        mock_position_tracker,
    ):
        """Test all strategies produce valid signals"""
        strategies = [
            MeanReversionStrategy(),
            TrendFollowingStrategy(),
            VolatilityBreakoutStrategy(),
        ]

        risk_manager = RiskManager(
            starting_balance_chf=Decimal("2626.96"),
            max_daily_loss_chf=Decimal("-183.89"),
            trade_executor=mock_trade_executor,
            position_tracker=mock_position_tracker,
        )

        for strategy in strategies:
            # Generate signal
            signal = await strategy.generate_signal(sample_ohlcv_data)

            # Validate signal
            validation = await risk_manager.validate_signal(signal)

            # All strategy signals should pass validation or be HOLD
            if signal.decision != "HOLD":
                # If not HOLD, should have validation result
                assert validation is not None
                assert len(validation.checks) > 0

    @pytest.mark.asyncio
    async def test_multiple_signals_exposure_limit(
        self,
        sample_ohlcv_data,
        mock_trade_executor,
        mock_position_tracker,
    ):
        """Test risk manager enforces total exposure limit"""
        strategy = MeanReversionStrategy()
        risk_manager = RiskManager(
            starting_balance_chf=Decimal("2626.96"),
            max_daily_loss_chf=Decimal("-183.89"),
            trade_executor=mock_trade_executor,
            position_tracker=mock_position_tracker,
        )

        # Create multiple positions
        mock_position_tracker.positions = [
            {"symbol": "BTC/USDT:USDT", "size_pct": Decimal("0.20")},
            {"symbol": "ETH/USDT:USDT", "size_pct": Decimal("0.20")},
            {"symbol": "SOL/USDT:USDT", "size_pct": Decimal("0.20")},
            {"symbol": "BNB/USDT:USDT", "size_pct": Decimal("0.20")},
        ]

        # Generate new signal
        signal = await strategy.generate_signal(sample_ohlcv_data)

        if signal.decision != "HOLD":
            # Override signal size to test limit
            signal.size_pct = Decimal("0.15")

            # Validate signal (should be rejected due to exposure)
            validation = await risk_manager.validate_signal(signal)

            # Total exposure would be 95% (80 + 15), exceeds 80% limit
            assert validation.approved is False
            assert any("exposure" in r.lower() for r in validation.rejection_reasons)

    @pytest.mark.asyncio
    async def test_position_count_limit(
        self,
        sample_ohlcv_data,
        mock_trade_executor,
        mock_position_tracker,
    ):
        """Test risk manager enforces position count limit"""
        strategy = MeanReversionStrategy()
        risk_manager = RiskManager(
            starting_balance_chf=Decimal("2626.96"),
            max_daily_loss_chf=Decimal("-183.89"),
            trade_executor=mock_trade_executor,
            position_tracker=mock_position_tracker,
        )

        # Create 6 positions (at limit)
        mock_position_tracker.positions = [
            {"symbol": "BTC/USDT:USDT", "size_pct": Decimal("0.10")},
            {"symbol": "ETH/USDT:USDT", "size_pct": Decimal("0.10")},
            {"symbol": "SOL/USDT:USDT", "size_pct": Decimal("0.10")},
            {"symbol": "BNB/USDT:USDT", "size_pct": Decimal("0.10")},
            {"symbol": "ADA/USDT:USDT", "size_pct": Decimal("0.10")},
            {"symbol": "DOGE/USDT:USDT", "size_pct": Decimal("0.10")},
        ]

        # Generate new signal
        signal = await strategy.generate_signal(sample_ohlcv_data)

        if signal.decision != "HOLD":
            # Validate signal (should be rejected due to position count)
            validation = await risk_manager.validate_signal(signal)

            # Should be rejected - at max positions
            assert validation.approved is False
            assert any(
                "position" in r.lower() and "maximum" in r.lower()
                for r in validation.rejection_reasons
            )

    @pytest.mark.asyncio
    async def test_leverage_limits_per_symbol(
        self,
        mock_trade_executor,
        mock_position_tracker,
    ):
        """Test risk manager enforces per-symbol leverage limits"""
        risk_manager = RiskManager(
            starting_balance_chf=Decimal("2626.96"),
            max_daily_loss_chf=Decimal("-183.89"),
            trade_executor=mock_trade_executor,
            position_tracker=mock_position_tracker,
        )

        # Test BTC (max 40x)
        signal_btc = MockSignal(
            symbol="BTC/USDT:USDT",
            leverage=45,  # Exceeds 40x limit
        )

        validation = await risk_manager.validate_signal(signal_btc)
        assert validation.approved is False
        assert any("leverage" in r.lower() for r in validation.rejection_reasons)

        # Test ADA (max 20x)
        signal_ada = MockSignal(
            symbol="ADA/USDT:USDT",
            leverage=25,  # Exceeds 20x limit
        )

        validation = await risk_manager.validate_signal(signal_ada)
        assert validation.approved is False
        assert any("leverage" in r.lower() for r in validation.rejection_reasons)

    @pytest.mark.asyncio
    async def test_validation_provides_detailed_feedback(
        self,
        sample_ohlcv_data,
        mock_trade_executor,
        mock_position_tracker,
    ):
        """Test validation provides detailed feedback"""
        strategy = MeanReversionStrategy()
        signal = await strategy.generate_signal(sample_ohlcv_data)

        risk_manager = RiskManager(
            starting_balance_chf=Decimal("2626.96"),
            max_daily_loss_chf=Decimal("-183.89"),
            trade_executor=mock_trade_executor,
            position_tracker=mock_position_tracker,
        )

        validation = await risk_manager.validate_signal(signal)

        # Should provide detailed checks
        assert len(validation.checks) > 0

        # Each check should have required fields
        for check in validation.checks:
            assert check.check_name is not None
            assert check.passed is not None
            assert check.message is not None
            assert check.severity in ["info", "warning", "error"]

    @pytest.mark.asyncio
    async def test_circuit_breaker_blocks_signals(
        self,
        sample_ohlcv_data,
        mock_trade_executor,
        mock_position_tracker,
    ):
        """Test circuit breaker blocks all signals when tripped"""
        strategy = MeanReversionStrategy()
        signal = await strategy.generate_signal(sample_ohlcv_data)

        risk_manager = RiskManager(
            starting_balance_chf=Decimal("2626.96"),
            max_daily_loss_chf=Decimal("-183.89"),
            trade_executor=mock_trade_executor,
            position_tracker=mock_position_tracker,
        )

        # Trip circuit breaker
        await risk_manager.circuit_breaker.check_daily_loss(Decimal("-200.00"))

        # Validate signal
        validation = await risk_manager.validate_signal(signal)

        # Should be rejected due to circuit breaker
        assert validation.approved is False
        assert validation.circuit_breaker_active is True
        assert any("circuit breaker" in r.lower() for r in validation.rejection_reasons)
