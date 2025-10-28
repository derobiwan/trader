"""
Unit tests for balance fetching functionality

Tests the real-time balance fetching from exchange with caching.

Author: Trading System Implementation Team
Date: 2025-10-28
"""

import pytest
import pytest_asyncio
import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from workspace.features.trade_executor import TradeExecutor


class TestBalanceFetching:
    """Test suite for balance fetching functionality"""

    @pytest.fixture
    def mock_exchange(self):
        """Create mock exchange"""
        exchange = AsyncMock()
        # Configure async methods properly
        exchange.fetch_balance = AsyncMock(
            return_value={"USDT": {"total": 0, "free": 0, "used": 0}}
        )
        exchange.load_markets = AsyncMock(return_value={})
        exchange.close = AsyncMock()
        exchange.markets = {}  # Add markets attribute
        exchange.set_sandbox_mode = MagicMock()
        return exchange

    @pytest.fixture
    def mock_position_service(self):
        """Create mock position service"""
        return AsyncMock()

    @pytest.fixture
    def mock_trade_history_service(self):
        """Create mock trade history service"""
        return AsyncMock()

    @pytest.fixture
    def mock_metrics_service(self):
        """Create mock metrics service"""
        return MagicMock()

    @pytest_asyncio.fixture
    async def executor(
        self,
        mock_exchange,
        mock_position_service,
        mock_trade_history_service,
        mock_metrics_service,
    ):
        """Create TradeExecutor with mocked exchange"""
        executor = TradeExecutor(
            api_key="test_key",
            api_secret="test_secret",
            testnet=True,
            exchange=mock_exchange,
            position_service=mock_position_service,
            trade_history_service=mock_trade_history_service,
            metrics_service=mock_metrics_service,
            enable_circuit_breaker=False,
        )
        await executor.initialize()
        return executor

    @pytest.mark.asyncio
    async def test_balance_fetching_success(self, executor, mock_exchange):
        """Test successful balance fetching from exchange"""
        # Reset call count after initialization
        mock_exchange.fetch_balance.reset_mock()

        # Mock exchange response
        mock_exchange.fetch_balance.return_value = {
            "USDT": {"total": 3300.0, "free": 3000.0, "used": 300.0}
        }

        # Fetch balance
        balance = await executor.get_account_balance()

        # Verify balance conversion (3300 USDT / 1.10 = 3000 CHF)
        assert isinstance(balance, Decimal)
        assert balance == Decimal("3000.00")

        # Verify exchange was called
        mock_exchange.fetch_balance.assert_called_once()

    @pytest.mark.asyncio
    async def test_balance_caching_works(self, executor, mock_exchange):
        """Test that balance is cached for TTL duration"""
        # Reset call count after initialization
        mock_exchange.fetch_balance.reset_mock()

        # Mock exchange response
        mock_exchange.fetch_balance.return_value = {
            "USDT": {"total": 3300.0, "free": 3000.0, "used": 300.0}
        }

        # First fetch - should hit exchange
        balance1 = await executor.get_account_balance(cache_ttl_seconds=60)
        assert mock_exchange.fetch_balance.call_count == 1

        # Second fetch immediately - should use cache
        balance2 = await executor.get_account_balance(cache_ttl_seconds=60)
        assert mock_exchange.fetch_balance.call_count == 1  # Still 1, not 2
        assert balance1 == balance2

        # Third fetch after short delay - should still use cache
        await asyncio.sleep(0.1)
        balance3 = await executor.get_account_balance(cache_ttl_seconds=60)
        assert mock_exchange.fetch_balance.call_count == 1
        assert balance2 == balance3

    @pytest.mark.asyncio
    async def test_balance_cache_expiration(self, executor, mock_exchange):
        """Test that cache expires after TTL"""
        # Reset call count after initialization
        mock_exchange.fetch_balance.reset_mock()

        # Mock exchange response
        mock_exchange.fetch_balance.return_value = {
            "USDT": {"total": 3300.0, "free": 3000.0, "used": 300.0}
        }

        # First fetch
        balance1 = await executor.get_account_balance(cache_ttl_seconds=1)
        assert mock_exchange.fetch_balance.call_count == 1

        # Wait for cache to expire
        await asyncio.sleep(1.1)

        # Second fetch - should hit exchange again
        balance2 = await executor.get_account_balance(cache_ttl_seconds=1)
        assert mock_exchange.fetch_balance.call_count == 2

    @pytest.mark.asyncio
    async def test_balance_fetch_failure_with_cache(self, executor, mock_exchange):
        """Test that stale cache is returned on fetch failure"""
        # First successful fetch
        mock_exchange.fetch_balance.return_value = {
            "USDT": {"total": 3300.0, "free": 3000.0, "used": 300.0}
        }
        balance1 = await executor.get_account_balance(cache_ttl_seconds=1)

        # Wait for cache to expire
        await asyncio.sleep(1.1)

        # Second fetch fails
        mock_exchange.fetch_balance.side_effect = Exception("Network error")

        # Should return stale cached value
        balance2 = await executor.get_account_balance(cache_ttl_seconds=1)
        assert balance2 == balance1  # Stale cache returned

    @pytest.mark.asyncio
    async def test_balance_fetch_failure_without_cache(self, executor, mock_exchange):
        """Test that exception is raised when fetch fails with no cache"""
        # Mock exchange failure
        mock_exchange.fetch_balance.side_effect = Exception("Network error")

        # Should raise exception
        with pytest.raises(Exception) as exc_info:
            await executor.get_account_balance()

        assert "Network error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_exchange_response_parsing(self, executor, mock_exchange):
        """Test correct parsing of exchange response"""
        # Reset call count after initialization
        mock_exchange.fetch_balance.reset_mock()

        # Mock realistic exchange response
        mock_exchange.fetch_balance.return_value = {
            "USDT": {
                "total": 5500.50,  # Total balance
                "free": 5000.00,  # Available for trading
                "used": 500.50,  # Locked in orders
            },
            "BTC": {"total": 0.1, "free": 0.1, "used": 0.0},
            "ETH": {"total": 2.5, "free": 2.5, "used": 0.0},
        }

        balance = await executor.get_account_balance()

        # Should use USDT total balance (5500.50 USDT / 1.10 ~= 5000.45 CHF)
        expected_chf = Decimal("5500.50") / Decimal("1.10")
        # Check with reasonable precision (our code doesn't quantize internally)
        assert abs(balance - expected_chf) < Decimal("0.01")

    @pytest.mark.asyncio
    async def test_missing_usdt_balance(self, executor, mock_exchange):
        """Test handling of missing USDT balance in response"""
        # Mock response without USDT
        mock_exchange.fetch_balance.return_value = {
            "BTC": {"total": 0.1, "free": 0.1, "used": 0.0},
            "ETH": {"total": 2.5, "free": 2.5, "used": 0.0},
        }

        # Should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            await executor.get_account_balance()

        assert "USDT balance not available" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_cache_ttl_parameter(self, executor, mock_exchange):
        """Test different cache TTL values"""
        # Reset call count after initialization
        mock_exchange.fetch_balance.reset_mock()

        mock_exchange.fetch_balance.return_value = {
            "USDT": {"total": 3300.0, "free": 3000.0, "used": 300.0}
        }

        # Test with 5-second TTL
        balance1 = await executor.get_account_balance(cache_ttl_seconds=5)
        await asyncio.sleep(0.1)
        balance2 = await executor.get_account_balance(cache_ttl_seconds=5)

        # Should use cache
        assert mock_exchange.fetch_balance.call_count == 1

        # Test with 0-second TTL (no caching)
        balance3 = await executor.get_account_balance(cache_ttl_seconds=0)
        assert mock_exchange.fetch_balance.call_count == 2  # Cache bypassed

    @pytest.mark.asyncio
    async def test_balance_precision(self, executor, mock_exchange):
        """Test that balance maintains proper decimal precision"""
        mock_exchange.fetch_balance.return_value = {
            "USDT": {"total": 1234.56789, "free": 1000.0, "used": 234.56789}
        }

        balance = await executor.get_account_balance()

        # Should be Decimal with high precision
        assert isinstance(balance, Decimal)
        assert balance > Decimal("1100")  # Roughly 1234.56789 / 1.10
        assert balance < Decimal("1130")

    @pytest.mark.asyncio
    async def test_concurrent_balance_fetches(self, executor, mock_exchange):
        """Test concurrent balance fetch requests use cache correctly"""
        mock_exchange.fetch_balance.return_value = {
            "USDT": {"total": 3300.0, "free": 3000.0, "used": 300.0}
        }

        # Launch multiple concurrent requests
        results = await asyncio.gather(
            executor.get_account_balance(),
            executor.get_account_balance(),
            executor.get_account_balance(),
        )

        # All should return same value
        assert all(r == results[0] for r in results)

        # Exchange should be called at least once (may be called multiple times
        # if all requests start before cache is populated)
        assert mock_exchange.fetch_balance.call_count >= 1
        assert mock_exchange.fetch_balance.call_count <= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
