"""
Integration Tests: Trade Executor + Signal Execution

Tests the new execute_signal() orchestrator method that integrates:
- Signal validation via Risk Manager
- Position sizing calculation
- Order placement (market orders)
- Stop-loss order placement
- Error handling

Author: Integration Testing Team
Date: 2025-10-28
"""

import pytest
import pytest_asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from workspace.features.trading_loop import TradingSignal, TradingDecision
from workspace.features.trade_executor import TradeExecutor, OrderSide


class TestExecuteSignalIntegration:
    """Integration tests for TradeExecutor.execute_signal() method"""

    @pytest.fixture
    def mock_exchange(self):
        """Create mock exchange with necessary methods"""
        exchange = AsyncMock()
        exchange.fetch_ticker = AsyncMock(return_value={"last": 50000.0})
        exchange.create_order = AsyncMock(
            return_value={
                "id": "test_order_123",
                "status": "closed",
                "filled": 0.002,
                "average": 50000.0,
                "fee": {"cost": 0.1},
            }
        )
        exchange.fetch_balance = AsyncMock(
            return_value={"USDT": {"free": 2500.0, "used": 0.0, "total": 2500.0}}
        )
        exchange.load_markets = AsyncMock()
        exchange.markets = {"BTC/USDT:USDT": {}}
        exchange.set_sandbox_mode = MagicMock()
        return exchange

    @pytest.fixture
    def mock_position_service(self):
        """Create mock position service"""
        service = AsyncMock()
        service.get_open_positions = AsyncMock(return_value=[])
        service.create_position = AsyncMock(return_value=MagicMock(id="pos_123"))
        service.close_position = AsyncMock()
        return service

    @pytest_asyncio.fixture
    async def executor(self, mock_exchange, mock_position_service):
        """Create TradeExecutor with mocked dependencies"""
        executor = TradeExecutor(
            api_key="test_key",
            api_secret="test_secret",
            testnet=True,
            exchange=mock_exchange,
            position_service=mock_position_service,
        )
        return executor

    @pytest.fixture
    def buy_signal(self):
        """Create a BUY signal for testing"""
        return TradingSignal(
            symbol="BTC/USDT:USDT",
            decision=TradingDecision.BUY,
            confidence=Decimal("0.75"),
            size_pct=Decimal("0.15"),
            stop_loss_pct=Decimal("0.02"),
            take_profit_pct=Decimal("0.05"),
            reasoning="Strong bullish momentum with RSI oversold",
        )

    @pytest.fixture
    def sell_signal(self):
        """Create a SELL signal for testing"""
        return TradingSignal(
            symbol="BTC/USDT:USDT",
            decision=TradingDecision.SELL,
            confidence=Decimal("0.70"),
            size_pct=Decimal("0.12"),
            stop_loss_pct=Decimal("0.02"),
            reasoning="Bearish divergence on MACD",
        )

    @pytest.fixture
    def hold_signal(self):
        """Create a HOLD signal for testing"""
        return TradingSignal(
            symbol="BTC/USDT:USDT",
            decision=TradingDecision.HOLD,
            confidence=Decimal("0.50"),
            size_pct=Decimal("0.0"),
            reasoning="Neutral market conditions",
        )

    # ========================================================================
    # Test BUY Signal Execution
    # ========================================================================

    @pytest.mark.asyncio
    async def test_execute_signal_buy_success(self, executor, buy_signal):
        """Test successful BUY signal execution"""
        account_balance_chf = Decimal("2626.96")

        result = await executor.execute_signal(
            signal=buy_signal,
            account_balance_chf=account_balance_chf,
            chf_to_usd_rate=Decimal("1.10"),
            risk_manager=None,  # No risk manager for this test
        )

        # Verify result
        assert result.success is True
        assert result.order is not None
        assert result.order.side == OrderSide.BUY
        assert result.order.symbol == "BTC/USDT:USDT"
        assert result.latency_ms is not None
        assert result.latency_ms > 0

        # Verify orders were created (market order + stop-loss order)
        assert executor.exchange.create_order.call_count == 2

        # Verify market order was placed
        call_args = executor.exchange.create_order.call_args_list[0]
        assert call_args[1]["symbol"] == "BTC/USDT:USDT"
        assert call_args[1]["type"] == "market"
        assert call_args[1]["side"] == "buy"
        assert call_args[1]["amount"] > 0  # Position size calculated

        # Verify stop-loss order was placed
        stop_loss_call = executor.exchange.create_order.call_args_list[1]
        assert stop_loss_call[1]["type"] == "stop_market"
        assert stop_loss_call[1]["side"] == "sell"

    @pytest.mark.asyncio
    async def test_execute_signal_buy_with_stop_loss(self, executor, buy_signal):
        """Test BUY signal execution places stop-loss order"""
        account_balance_chf = Decimal("2626.96")

        result = await executor.execute_signal(
            signal=buy_signal,
            account_balance_chf=account_balance_chf,
        )

        assert result.success is True

        # Should call create_order twice: once for market order, once for stop-loss
        assert executor.exchange.create_order.call_count == 2

        # Verify stop-loss order was placed
        calls = executor.exchange.create_order.call_args_list
        stop_loss_call = calls[1]

        assert stop_loss_call[1]["type"] == "stop_market"
        assert stop_loss_call[1]["side"] == "sell"  # Opposite of entry
        assert "stopPrice" in stop_loss_call[1]["params"]

    @pytest.mark.asyncio
    async def test_execute_signal_buy_position_sizing(self, executor, buy_signal):
        """Test position sizing calculation for BUY signal"""
        account_balance_chf = Decimal("2626.96")
        chf_to_usd_rate = Decimal("1.10")

        # Expected calculation:
        # capital_usd = 2626.96 / 1.10 = 2388.15 USD
        # position_value = 2388.15 * 0.15 (size_pct) = 358.22 USD
        # quantity = 358.22 / 50000 (price) = 0.0071644 BTC

        result = await executor.execute_signal(
            signal=buy_signal,
            account_balance_chf=account_balance_chf,
            chf_to_usd_rate=chf_to_usd_rate,
        )

        assert result.success is True

        # Check the quantity in the order
        call_args = executor.exchange.create_order.call_args_list[0]
        quantity = call_args[1]["amount"]

        # Should be approximately 0.0071644 BTC
        expected_quantity = (
            account_balance_chf / chf_to_usd_rate * buy_signal.size_pct
        ) / 50000
        assert abs(quantity - float(expected_quantity)) < 0.0001

    # ========================================================================
    # Test SELL Signal Execution
    # ========================================================================

    @pytest.mark.asyncio
    async def test_execute_signal_sell_success(self, executor, sell_signal):
        """Test successful SELL signal execution"""
        account_balance_chf = Decimal("2626.96")

        result = await executor.execute_signal(
            signal=sell_signal,
            account_balance_chf=account_balance_chf,
        )

        assert result.success is True
        assert result.order is not None
        assert result.order.side == OrderSide.SELL

        # Verify SELL order was created
        call_args = executor.exchange.create_order.call_args_list[0]
        assert call_args[1]["side"] == "sell"

    @pytest.mark.asyncio
    async def test_execute_signal_sell_with_stop_loss_above_entry(
        self, executor, sell_signal
    ):
        """Test SELL signal places stop-loss ABOVE entry price (short protection)"""
        account_balance_chf = Decimal("2626.96")

        result = await executor.execute_signal(
            signal=sell_signal,
            account_balance_chf=account_balance_chf,
        )

        assert result.success is True

        # Verify stop-loss order
        calls = executor.exchange.create_order.call_args_list
        assert len(calls) == 2

        stop_loss_call = calls[1]
        assert stop_loss_call[1]["type"] == "stop_market"
        assert (
            stop_loss_call[1]["side"] == "buy"
        )  # Opposite of entry (buy to close short)

        # Stop price should be ABOVE entry price for shorts
        stop_price = stop_loss_call[1]["params"]["stopPrice"]
        entry_price = 50000.0
        assert stop_price > entry_price

    # ========================================================================
    # Test HOLD Signal Execution
    # ========================================================================

    @pytest.mark.asyncio
    async def test_execute_signal_hold_no_action(self, executor, hold_signal):
        """Test HOLD signal takes no action"""
        account_balance_chf = Decimal("2626.96")

        result = await executor.execute_signal(
            signal=hold_signal,
            account_balance_chf=account_balance_chf,
        )

        assert result.success is True
        assert result.error_message == "HOLD signal - no action taken"

        # Verify NO orders were created
        executor.exchange.create_order.assert_not_called()

    # ========================================================================
    # Test CLOSE Signal Execution
    # ========================================================================

    @pytest.mark.asyncio
    async def test_execute_signal_close_existing_position(self, executor):
        """Test CLOSE signal closes existing position"""
        close_signal = TradingSignal(
            symbol="BTC/USDT:USDT",
            decision=TradingDecision.CLOSE,
            confidence=Decimal("0.80"),
            size_pct=Decimal("0.0"),
            reasoning="Take profit at target",
        )

        # Mock existing position
        mock_position = MagicMock()
        mock_position.id = "pos_123"
        mock_position.symbol = "BTC/USDT:USDT"
        mock_position.side = "long"
        mock_position.quantity = Decimal("0.01")

        executor.position_service.get_open_positions = AsyncMock(
            return_value=[mock_position]
        )
        executor.position_service.get_position = AsyncMock(return_value=mock_position)

        account_balance_chf = Decimal("2626.96")

        result = await executor.execute_signal(
            signal=close_signal,
            account_balance_chf=account_balance_chf,
        )

        assert result.success is True

        # Verify close_position was called
        executor.position_service.close_position.assert_called_once_with(
            position_id="pos_123",
            close_price=Decimal("50000.0"),
            reason="signal_close",
        )

    @pytest.mark.asyncio
    async def test_execute_signal_close_no_position(self, executor):
        """Test CLOSE signal when no position exists"""
        close_signal = TradingSignal(
            symbol="BTC/USDT:USDT",
            decision=TradingDecision.CLOSE,
            confidence=Decimal("0.80"),
            size_pct=Decimal("0.0"),
        )

        # No positions exist
        executor.position_service.get_open_positions = AsyncMock(return_value=[])

        account_balance_chf = Decimal("2626.96")

        result = await executor.execute_signal(
            signal=close_signal,
            account_balance_chf=account_balance_chf,
        )

        assert result.success is False
        assert result.error_code == "POSITION_NOT_FOUND"
        assert "No open position" in result.error_message

    # ========================================================================
    # Test Risk Manager Integration
    # ========================================================================

    @pytest.mark.asyncio
    async def test_execute_signal_with_risk_manager_approval(
        self, executor, buy_signal
    ):
        """Test signal execution with Risk Manager approval"""
        # Mock risk manager that approves signal
        mock_risk_manager = AsyncMock()
        mock_validation = MagicMock()
        mock_validation.approved = True
        mock_validation.rejection_reasons = []
        mock_risk_manager.validate_signal = AsyncMock(return_value=mock_validation)

        account_balance_chf = Decimal("2626.96")

        result = await executor.execute_signal(
            signal=buy_signal,
            account_balance_chf=account_balance_chf,
            risk_manager=mock_risk_manager,
        )

        assert result.success is True

        # Verify risk manager was called
        mock_risk_manager.validate_signal.assert_called_once_with(buy_signal)

        # Verify order was placed after approval
        executor.exchange.create_order.assert_called()

    @pytest.mark.asyncio
    async def test_execute_signal_with_risk_manager_rejection(
        self, executor, buy_signal
    ):
        """Test signal execution with Risk Manager rejection"""
        # Mock risk manager that rejects signal
        mock_risk_manager = AsyncMock()
        mock_validation = MagicMock()
        mock_validation.approved = False
        mock_validation.rejection_reasons = [
            "Confidence too low",
            "Position limit exceeded",
        ]
        mock_risk_manager.validate_signal = AsyncMock(return_value=mock_validation)

        account_balance_chf = Decimal("2626.96")

        result = await executor.execute_signal(
            signal=buy_signal,
            account_balance_chf=account_balance_chf,
            risk_manager=mock_risk_manager,
        )

        assert result.success is False
        assert result.error_code == "RISK_VALIDATION_FAILED"
        assert "Confidence too low" in result.error_message

        # Verify NO orders were placed after rejection
        executor.exchange.create_order.assert_not_called()

    # ========================================================================
    # Test Error Handling
    # ========================================================================

    @pytest.mark.asyncio
    async def test_execute_signal_exchange_error(self, executor, buy_signal):
        """Test handling of exchange API errors"""
        # Mock exchange error
        executor.exchange.create_order = AsyncMock(
            side_effect=Exception("Exchange API error: Insufficient margin")
        )

        account_balance_chf = Decimal("2626.96")

        result = await executor.execute_signal(
            signal=buy_signal,
            account_balance_chf=account_balance_chf,
        )

        assert result.success is False
        assert result.error_code == "UNKNOWN_ERROR"  # Error from create_market_order()
        assert "Exchange API error" in result.error_message

    @pytest.mark.asyncio
    async def test_execute_signal_invalid_symbol_format(self, executor):
        """Test handling of invalid symbol format"""
        # Signal with invalid symbol (missing settlement currency)
        invalid_signal = TradingSignal(
            symbol="BTC/USDT",  # Missing :USDT suffix
            decision=TradingDecision.BUY,
            confidence=Decimal("0.75"),
            size_pct=Decimal("0.15"),
        )

        account_balance_chf = Decimal("2626.96")

        # Note: execute_signal currently imports TradingDecision
        # We need to call it to see if it validates symbol format
        with patch("workspace.features.trade_executor.executor_service.OrderSide"):
            result = await executor.execute_signal(
                signal=invalid_signal,
                account_balance_chf=account_balance_chf,
            )

        # Should still succeed as exchange.fetch_ticker is mocked
        # In real scenario, exchange would reject invalid symbol

    @pytest.mark.asyncio
    async def test_execute_signal_metadata_preservation(self, executor, buy_signal):
        """Test that signal metadata is preserved in order"""
        account_balance_chf = Decimal("2626.96")

        result = await executor.execute_signal(
            signal=buy_signal,
            account_balance_chf=account_balance_chf,
        )

        assert result.success is True

        # Verify metadata was passed to order
        call_args = executor.exchange.create_order.call_args_list[0]
        # The method should have stored reasoning in metadata

    # ========================================================================
    # Test Performance
    # ========================================================================

    @pytest.mark.asyncio
    async def test_execute_signal_latency_tracking(self, executor, buy_signal):
        """Test that latency is tracked correctly"""
        account_balance_chf = Decimal("2626.96")

        result = await executor.execute_signal(
            signal=buy_signal,
            account_balance_chf=account_balance_chf,
        )

        assert result.success is True
        assert result.latency_ms is not None
        assert result.latency_ms > 0
        assert result.latency_ms < 10000  # Should be less than 10 seconds


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
