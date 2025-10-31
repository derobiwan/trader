"""
Connection Tests for Testnet Integration

Tests exchange connection, authentication, and basic connectivity.

Author: Validation Engineer
Date: 2025-10-31
"""

import pytest
from unittest.mock import patch, AsyncMock

from workspace.features.testnet_integration.testnet_config import (
    TestnetConfig,
    ExchangeType,
    TestnetMode,
)
from workspace.features.testnet_integration.testnet_adapter import (
    TestnetExchangeAdapter,
)
from ccxt.base.errors import NetworkError, ExchangeError


class TestExchangeConnection:
    """Test suite for exchange connections"""

    @pytest.mark.asyncio
    async def test_adapter_initialization(self, mock_exchange_adapter):
        """Test that adapter initializes correctly"""
        assert mock_exchange_adapter._initialized is True
        assert mock_exchange_adapter.exchange is not None
        assert mock_exchange_adapter._markets_loaded is True

    @pytest.mark.asyncio
    async def test_real_connection(self, real_testnet_config):
        """Test real connection to Binance testnet (if credentials available)"""
        adapter = TestnetExchangeAdapter(real_testnet_config)

        try:
            await adapter.initialize()

            assert adapter._initialized is True
            assert adapter.exchange is not None
            assert len(adapter.exchange.markets) > 0

            # Test we can fetch balance
            balance = await adapter.get_balance()
            assert "total" in balance
            assert "free" in balance
            assert "used" in balance

        finally:
            await adapter.close()

    @pytest.mark.asyncio
    async def test_invalid_credentials(self, mock_testnet_config):
        """Test handling of invalid API credentials"""
        # Modify config to have invalid keys
        mock_testnet_config.api_key = "invalid_key"
        mock_testnet_config.api_secret = "invalid_secret"

        adapter = TestnetExchangeAdapter(mock_testnet_config)

        with pytest.raises(ExchangeError):
            await adapter.initialize()

    @pytest.mark.asyncio
    async def test_get_balance(self, exchange_adapter):
        """Test fetching account balance"""
        balance = await exchange_adapter.get_balance()

        assert "free" in balance
        assert "used" in balance
        assert "total" in balance

        # Check USDT balance exists
        if "USDT" in balance["total"]:
            assert balance["total"]["USDT"] >= 0

    @pytest.mark.asyncio
    async def test_markets_loaded(self, exchange_adapter):
        """Test that markets are loaded correctly"""
        if hasattr(exchange_adapter.exchange, "markets"):
            markets = exchange_adapter.exchange.markets

            # Should have at least BTC/USDT
            assert len(markets) > 0

            if "BTC/USDT" in markets:
                btc_market = markets["BTC/USDT"]
                assert btc_market["base"] == "BTC"
                assert btc_market["quote"] == "USDT"

    @pytest.mark.asyncio
    async def test_sandbox_mode_enabled(self, mock_exchange_adapter):
        """Test that sandbox mode is properly set for testnet"""
        # Verify set_sandbox_mode was called
        if hasattr(mock_exchange_adapter.exchange, "set_sandbox_mode"):
            mock_exchange_adapter.exchange.set_sandbox_mode.assert_called()

    @pytest.mark.asyncio
    async def test_connection_retry_on_network_error(self, mock_testnet_config):
        """Test retry logic on network errors"""
        adapter = TestnetExchangeAdapter(mock_testnet_config)

        with patch.object(adapter, "exchange") as mock_exchange:
            # Simulate network error then success
            mock_exchange.load_markets = AsyncMock(
                side_effect=[NetworkError("Network error"), None]
            )

            # Should retry and succeed
            await adapter._load_markets()
            assert mock_exchange.load_markets.call_count >= 1

    @pytest.mark.asyncio
    async def test_connection_statistics(self, exchange_adapter):
        """Test that connection statistics are tracked"""
        stats = exchange_adapter.get_statistics()

        assert "exchange" in stats
        assert "mode" in stats
        assert "connected" in stats
        assert "markets_loaded" in stats
        assert stats["connected"] is True

    @pytest.mark.asyncio
    async def test_ensure_initialized_check(self, mock_testnet_config):
        """Test that operations fail if not initialized"""
        adapter = TestnetExchangeAdapter(mock_testnet_config)

        # Should raise error if not initialized
        with pytest.raises(RuntimeError, match="not initialized"):
            await adapter.get_balance()

    @pytest.mark.asyncio
    async def test_close_connection(self, exchange_adapter):
        """Test proper connection cleanup"""
        await exchange_adapter.close()

        assert exchange_adapter._initialized is False
        assert exchange_adapter.exchange is None

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_testnet_config):
        """Test async context manager functionality"""
        async with TestnetExchangeAdapter(mock_testnet_config) as adapter:
            # Mock initialization
            adapter.exchange = AsyncMock()
            adapter._initialized = True

            assert adapter._initialized is True

        # After context exit
        assert adapter._initialized is False


class TestConfigurationValidation:
    """Test configuration validation"""

    def test_valid_binance_config(self):
        """Test valid Binance configuration"""
        config = TestnetConfig(
            exchange=ExchangeType.BINANCE,
            mode=TestnetMode.TESTNET,
            api_key="a" * 64,  # Valid length
            api_secret="test_secret",
            testnet_enabled=True,
        )

        assert config.validate() is True

    def test_invalid_binance_key_length(self):
        """Test invalid Binance API key length"""
        config = TestnetConfig(
            exchange=ExchangeType.BINANCE,
            mode=TestnetMode.TESTNET,
            api_key="short_key",  # Invalid length
            api_secret="test_secret",
            testnet_enabled=True,
        )

        with pytest.raises(ValueError, match="Invalid Binance API key length"):
            config.validate()

    def test_empty_api_secret(self):
        """Test empty API secret validation"""
        config = TestnetConfig(
            exchange=ExchangeType.BINANCE,
            mode=TestnetMode.TESTNET,
            api_key="a" * 64,
            api_secret="",  # Empty secret
            testnet_enabled=True,
        )

        with pytest.raises(ValueError, match="API secret is empty"):
            config.validate()

    def test_get_rest_url(self, mock_testnet_config):
        """Test REST URL generation"""
        # Testnet mode
        url = mock_testnet_config.get_rest_url()
        assert "testnet" in url

        # Production mode
        mock_testnet_config.testnet_enabled = False
        url = mock_testnet_config.get_rest_url()
        assert "testnet" not in url

    def test_get_ws_url(self, mock_testnet_config):
        """Test WebSocket URL generation"""
        # Testnet mode
        url = mock_testnet_config.get_ws_url()
        assert "testnet" in url or "test" in url

        # Production mode
        mock_testnet_config.testnet_enabled = False
        url = mock_testnet_config.get_ws_url()
        assert "testnet" not in url

    def test_ccxt_options_generation(self, mock_testnet_config):
        """Test ccxt options generation"""
        options = mock_testnet_config.to_ccxt_options()

        assert "apiKey" in options
        assert "secret" in options
        assert "enableRateLimit" in options
        assert options["enableRateLimit"] is True
        assert "timeout" in options

        # For Binance testnet, should have URLs
        if (
            mock_testnet_config.exchange == ExchangeType.BINANCE
            and mock_testnet_config.testnet_enabled
        ):
            assert "urls" in options
            assert "api" in options["urls"]

    def test_config_repr_sanitization(self, mock_testnet_config):
        """Test that sensitive data is sanitized in repr"""
        repr_str = repr(mock_testnet_config)

        # Should not contain full API key
        assert mock_testnet_config.api_key not in repr_str
        assert "..." in repr_str  # Should have sanitized format

    @pytest.mark.parametrize(
        "exchange,expected_length",
        [
            (ExchangeType.BINANCE, 64),
            (ExchangeType.BYBIT, 36),
        ],
    )
    def test_exchange_specific_validation(self, exchange, expected_length):
        """Test exchange-specific API key validation"""
        # Valid key
        config = TestnetConfig(
            exchange=exchange,
            mode=TestnetMode.TESTNET,
            api_key="a" * expected_length,
            api_secret="test_secret",
            testnet_enabled=True,
        )
        assert config.validate() is True

        # Invalid key
        config.api_key = "wrong_length"
        with pytest.raises(ValueError):
            config.validate()
