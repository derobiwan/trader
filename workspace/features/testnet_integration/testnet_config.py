"""
Testnet Configuration Module

Manages configuration for exchange testnet connections.
Loads from environment variables and validates settings.

Author: Integration Specialist
Date: 2025-10-31
"""

import os
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any

logger = logging.getLogger(__name__)


class ExchangeType(Enum):
    """Supported exchanges"""

    BINANCE = "binance"
    BYBIT = "bybit"


class TestnetMode(Enum):
    """Trading modes"""

    PRODUCTION = "production"
    TESTNET = "testnet"
    PAPER = "paper"


@dataclass
class TestnetConfig:
    """
    Configuration for testnet exchange connections

    Attributes:
        exchange: Exchange type (binance or bybit)
        mode: Trading mode (testnet, production, or paper)
        api_key: Exchange API key
        api_secret: Exchange API secret
        testnet_enabled: Whether testnet mode is enabled
        binance_testnet_rest: Binance testnet REST API URL
        binance_testnet_ws: Binance testnet WebSocket URL
        bybit_testnet_rest: Bybit testnet REST API URL
        bybit_testnet_ws: Bybit testnet WebSocket URL
        rate_limit_buffer_ms: Rate limit buffer in milliseconds
        max_retries: Maximum number of retry attempts
        timeout_ms: Request timeout in milliseconds
        websocket_ping_interval: WebSocket ping interval in seconds
        websocket_reconnect_delay: WebSocket reconnect delay in seconds
    """

    exchange: ExchangeType
    mode: TestnetMode
    api_key: str
    api_secret: str
    testnet_enabled: bool = True

    # Binance testnet URLs
    binance_testnet_rest: str = "https://testnet.binance.vision"
    binance_testnet_ws: str = "wss://testnet.binance.vision/ws"
    binance_prod_rest: str = "https://api.binance.com"
    binance_prod_ws: str = "wss://stream.binance.com:9443/ws"

    # Bybit testnet URLs
    bybit_testnet_rest: str = "https://api-testnet.bybit.com"
    bybit_testnet_ws: str = "wss://stream-testnet.bybit.com/v5/public"
    bybit_prod_rest: str = "https://api.bybit.com"
    bybit_prod_ws: str = "wss://stream.bybit.com/v5/public"

    # Connection settings
    rate_limit_buffer_ms: int = 100
    max_retries: int = 3
    timeout_ms: int = 30000

    # WebSocket settings
    websocket_ping_interval: int = 30
    websocket_reconnect_delay: int = 5

    # Additional settings
    extra_settings: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_env(cls, exchange: ExchangeType) -> "TestnetConfig":
        """
        Load configuration from environment variables

        Args:
            exchange: Exchange type to load configuration for

        Returns:
            TestnetConfig instance

        Raises:
            ValueError: If required environment variables are missing
        """
        prefix = exchange.value.upper()

        # Load API credentials
        api_key = os.getenv(f"{prefix}_API_KEY", "")
        api_secret = os.getenv(f"{prefix}_API_SECRET", "")

        if not api_key or not api_secret:
            raise ValueError(
                f"Missing {prefix} API credentials. "
                f"Please set {prefix}_API_KEY and {prefix}_API_SECRET environment variables."
            )

        # Determine mode
        testnet_enabled = os.getenv(f"{prefix}_TESTNET", "true").lower() == "true"
        mode = TestnetMode.TESTNET if testnet_enabled else TestnetMode.PRODUCTION

        # Load optional settings
        rate_limit = int(os.getenv(f"{prefix}_RATE_LIMIT_MS", "100"))
        max_retries = int(os.getenv(f"{prefix}_MAX_RETRIES", "3"))
        timeout = int(os.getenv(f"{prefix}_TIMEOUT_MS", "30000"))
        ws_ping = int(os.getenv(f"{prefix}_WS_PING_INTERVAL", "30"))
        ws_reconnect = int(os.getenv(f"{prefix}_WS_RECONNECT_DELAY", "5"))

        config = cls(
            exchange=exchange,
            mode=mode,
            api_key=api_key,
            api_secret=api_secret,
            testnet_enabled=testnet_enabled,
            rate_limit_buffer_ms=rate_limit,
            max_retries=max_retries,
            timeout_ms=timeout,
            websocket_ping_interval=ws_ping,
            websocket_reconnect_delay=ws_reconnect,
        )

        logger.info(f"Loaded {exchange.value} configuration in {mode.value} mode")

        return config

    def validate(self) -> bool:
        """
        Validate configuration settings

        Returns:
            True if configuration is valid

        Raises:
            ValueError: If configuration is invalid
        """
        errors = []

        # Validate API key format
        if self.exchange == ExchangeType.BINANCE:
            if len(self.api_key) != 64:
                errors.append(
                    f"Invalid Binance API key length: {len(self.api_key)} (expected 64)"
                )
        elif self.exchange == ExchangeType.BYBIT:
            if len(self.api_key) != 36:
                errors.append(
                    f"Invalid Bybit API key length: {len(self.api_key)} (expected 36)"
                )

        # Validate API secret is not empty
        if not self.api_secret:
            errors.append("API secret is empty")

        # Validate connection settings
        if self.rate_limit_buffer_ms < 0:
            errors.append(f"Invalid rate limit buffer: {self.rate_limit_buffer_ms}")

        if self.max_retries < 0 or self.max_retries > 10:
            errors.append(f"Invalid max retries: {self.max_retries} (expected 0-10)")

        if self.timeout_ms < 1000 or self.timeout_ms > 60000:
            errors.append(f"Invalid timeout: {self.timeout_ms}ms (expected 1000-60000)")

        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(
                f"  - {e}" for e in errors
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info("Configuration validation passed")
        return True

    def get_rest_url(self) -> str:
        """
        Get REST API URL based on exchange and mode

        Returns:
            REST API URL
        """
        if self.exchange == ExchangeType.BINANCE:
            return (
                self.binance_testnet_rest
                if self.testnet_enabled
                else self.binance_prod_rest
            )
        else:  # Bybit
            return (
                self.bybit_testnet_rest
                if self.testnet_enabled
                else self.bybit_prod_rest
            )

    def get_ws_url(self) -> str:
        """
        Get WebSocket URL based on exchange and mode

        Returns:
            WebSocket URL
        """
        if self.exchange == ExchangeType.BINANCE:
            return (
                self.binance_testnet_ws
                if self.testnet_enabled
                else self.binance_prod_ws
            )
        else:  # Bybit
            return self.bybit_testnet_ws if self.testnet_enabled else self.bybit_prod_ws

    def to_ccxt_options(self) -> Dict[str, Any]:
        """
        Convert configuration to ccxt exchange options

        Returns:
            Dictionary of ccxt options
        """
        options = {
            "apiKey": self.api_key,
            "secret": self.api_secret,
            "enableRateLimit": True,
            "rateLimit": self.rate_limit_buffer_ms,
            "timeout": self.timeout_ms,
        }

        # Add testnet URLs for Binance
        if self.exchange == ExchangeType.BINANCE and self.testnet_enabled:
            options["urls"] = {
                "api": {
                    "public": f"{self.binance_testnet_rest}/api",
                    "private": f"{self.binance_testnet_rest}/api",
                    "web": self.binance_testnet_rest,
                }
            }
            options["test"] = True

        # Add any extra settings
        options.update(self.extra_settings)

        return options

    def __repr__(self) -> str:
        """String representation with sensitive data masked"""
        from workspace.features.testnet_integration.security_validator import (
            SecurityValidator,
        )

        masked_key = SecurityValidator.sanitize_for_logs(self.api_key)
        masked_secret = SecurityValidator.sanitize_for_logs(self.api_secret)

        return (
            f"TestnetConfig("
            f"exchange={self.exchange.value}, "
            f"mode={self.mode.value}, "
            f"api_key={masked_key}, "
            f"api_secret={masked_secret})"
        )
