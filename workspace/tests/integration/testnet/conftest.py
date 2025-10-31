"""
Test Fixtures for Testnet Integration Tests

Provides reusable fixtures for testing exchange testnet connectivity.

Author: Validation Engineer
Date: 2025-10-31
"""

import pytest
import pytest_asyncio
import asyncio
import os
from typing import AsyncGenerator
from unittest.mock import MagicMock, AsyncMock

from workspace.features.testnet_integration.testnet_config import (
    TestnetConfig,
    ExchangeType,
    TestnetMode,
)
from workspace.features.testnet_integration.testnet_adapter import (
    TestnetExchangeAdapter,
)
from workspace.features.testnet_integration.websocket_testnet import (
    TestnetWebSocketClient,
)


# Check if running in CI environment
IS_CI = os.getenv("CI", "false").lower() == "true"

# Check if real credentials are available
HAS_BINANCE_CREDENTIALS = bool(os.getenv("BINANCE_API_KEY"))
HAS_BYBIT_CREDENTIALS = bool(os.getenv("BYBIT_API_KEY"))


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_testnet_config():
    """Create mock testnet configuration for testing without real credentials"""
    return TestnetConfig(
        exchange=ExchangeType.BINANCE,
        mode=TestnetMode.TESTNET,
        api_key="mock_" + "a" * 60,  # 64 chars total
        api_secret="mock_secret_key_for_testing",
        testnet_enabled=True,
    )


@pytest.fixture
def real_testnet_config():
    """
    Create real testnet configuration if credentials available

    Skips test if no credentials found.
    """
    if not HAS_BINANCE_CREDENTIALS:
        pytest.skip("No Binance testnet credentials available")

    return TestnetConfig.from_env(ExchangeType.BINANCE)


@pytest_asyncio.fixture
async def mock_exchange_adapter(
    mock_testnet_config,
) -> AsyncGenerator[TestnetExchangeAdapter, None]:
    """Create mock exchange adapter for testing without real connection"""
    adapter = TestnetExchangeAdapter(mock_testnet_config)

    # Mock the exchange
    mock_exchange = create_mock_exchange()
    adapter.exchange = mock_exchange
    adapter._initialized = True
    adapter._markets_loaded = True

    yield adapter

    # Cleanup
    adapter.exchange = None


@pytest_asyncio.fixture
async def real_exchange_adapter(
    real_testnet_config,
) -> AsyncGenerator[TestnetExchangeAdapter, None]:
    """
    Create real exchange adapter for integration testing

    Only runs if real credentials are available.
    """
    adapter = TestnetExchangeAdapter(real_testnet_config)

    try:
        await adapter.initialize()
        yield adapter
    finally:
        await adapter.close()


@pytest_asyncio.fixture
async def exchange_adapter(request) -> AsyncGenerator[TestnetExchangeAdapter, None]:
    """
    Smart fixture that provides mock or real adapter based on environment

    Uses real adapter if credentials available, otherwise uses mock.
    """
    if HAS_BINANCE_CREDENTIALS and not IS_CI:
        # Use real adapter for local testing
        config = TestnetConfig.from_env(ExchangeType.BINANCE)
        adapter = TestnetExchangeAdapter(config)
        await adapter.initialize()
        yield adapter
        await adapter.close()
    else:
        # Use mock adapter for CI or when no credentials
        config = TestnetConfig(
            exchange=ExchangeType.BINANCE,
            mode=TestnetMode.TESTNET,
            api_key="mock_" + "a" * 60,
            api_secret="mock_secret",
            testnet_enabled=True,
        )
        adapter = TestnetExchangeAdapter(config)
        adapter.exchange = create_mock_exchange()
        adapter._initialized = True
        adapter._markets_loaded = True
        yield adapter


@pytest_asyncio.fixture
async def mock_websocket_client(
    mock_testnet_config,
) -> AsyncGenerator[TestnetWebSocketClient, None]:
    """Create mock WebSocket client for testing"""
    client = TestnetWebSocketClient(mock_testnet_config)

    # Mock the websocket connection
    mock_ws = AsyncMock()
    mock_ws.closed = False
    mock_ws.recv = AsyncMock(return_value='{"result":null,"id":1}')
    mock_ws.send = AsyncMock()
    mock_ws.close = AsyncMock()
    mock_ws.ping = AsyncMock(return_value=asyncio.Future())

    client.ws = mock_ws
    client.running = True

    yield client

    client.running = False


@pytest_asyncio.fixture
async def websocket_client(request) -> AsyncGenerator[TestnetWebSocketClient, None]:
    """
    Smart fixture for WebSocket client

    Uses real client if credentials available, otherwise uses mock.
    """
    if HAS_BINANCE_CREDENTIALS and not IS_CI:
        config = TestnetConfig.from_env(ExchangeType.BINANCE)
        client = TestnetWebSocketClient(config)
        await client.connect()
        yield client
        await client.close()
    else:
        config = TestnetConfig(
            exchange=ExchangeType.BINANCE,
            mode=TestnetMode.TESTNET,
            api_key="mock_" + "a" * 60,
            api_secret="mock_secret",
            testnet_enabled=True,
        )
        client = TestnetWebSocketClient(config)

        # Mock WebSocket
        mock_ws = AsyncMock()
        mock_ws.closed = False
        mock_ws.recv = AsyncMock(return_value='{"result":null,"id":1}')
        mock_ws.send = AsyncMock()
        mock_ws.close = AsyncMock()

        client.ws = mock_ws
        client.running = True

        yield client

        client.running = False


def create_mock_exchange():
    """Create a mock exchange object with common methods"""
    mock = AsyncMock()

    # Mock balance
    mock.fetch_balance = AsyncMock(
        return_value={
            "free": {"USDT": 10000.0, "BTC": 0.0},
            "used": {"USDT": 0.0, "BTC": 0.0},
            "total": {"USDT": 10000.0, "BTC": 0.0},
            "info": {},
        }
    )

    # Mock markets
    mock.load_markets = AsyncMock()
    mock.markets = {
        "BTC/USDT": {
            "symbol": "BTC/USDT",
            "base": "BTC",
            "quote": "USDT",
            "active": True,
            "limits": {
                "amount": {"min": 0.001, "max": 10000},
                "price": {"min": 0.01, "max": 1000000},
            },
        },
        "ETH/USDT": {
            "symbol": "ETH/USDT",
            "base": "ETH",
            "quote": "USDT",
            "active": True,
        },
    }

    # Mock order creation
    mock.create_market_order = AsyncMock(
        return_value={
            "id": "12345",
            "symbol": "BTC/USDT",
            "side": "buy",
            "type": "market",
            "amount": 0.001,
            "filled": 0.001,
            "remaining": 0,
            "status": "closed",
            "timestamp": 1234567890,
            "datetime": "2025-10-31T00:00:00Z",
            "info": {},
        }
    )

    mock.create_limit_order = AsyncMock(
        return_value={
            "id": "12346",
            "symbol": "BTC/USDT",
            "side": "buy",
            "type": "limit",
            "amount": 0.001,
            "price": 50000.0,
            "filled": 0,
            "remaining": 0.001,
            "status": "open",
            "timestamp": 1234567891,
            "datetime": "2025-10-31T00:00:01Z",
            "info": {},
        }
    )

    # Mock order cancellation
    mock.cancel_order = AsyncMock(
        return_value={
            "id": "12346",
            "status": "canceled",
        }
    )

    # Mock order fetching
    mock.fetch_order = AsyncMock(
        return_value={
            "id": "12345",
            "symbol": "BTC/USDT",
            "side": "buy",
            "type": "market",
            "amount": 0.001,
            "filled": 0.001,
            "remaining": 0,
            "status": "closed",
            "timestamp": 1234567890,
        }
    )

    # Mock open orders
    mock.fetch_open_orders = AsyncMock(return_value=[])

    # Mock ticker
    mock.fetch_ticker = AsyncMock(
        return_value={
            "symbol": "BTC/USDT",
            "last": 50000.0,
            "bid": 49999.0,
            "ask": 50001.0,
            "high": 51000.0,
            "low": 49000.0,
            "baseVolume": 1000.0,
            "timestamp": 1234567890,
        }
    )

    # Mock order book
    mock.fetch_order_book = AsyncMock(
        return_value={
            "symbol": "BTC/USDT",
            "bids": [[49999.0, 1.0], [49998.0, 2.0]],
            "asks": [[50001.0, 1.0], [50002.0, 2.0]],
            "timestamp": 1234567890,
        }
    )

    # Mock positions (for futures)
    mock.has = {"fetchPositions": False}
    mock.fetch_positions = AsyncMock(return_value=[])

    # Mock close
    mock.close = AsyncMock()

    # Mock sandbox mode
    mock.set_sandbox_mode = MagicMock()

    return mock


@pytest.fixture
def sample_order_data():
    """Sample order data for testing"""
    return {
        "market_order": {
            "symbol": "BTC/USDT",
            "side": "buy",
            "type": "market",
            "amount": 0.001,
        },
        "limit_order": {
            "symbol": "BTC/USDT",
            "side": "buy",
            "type": "limit",
            "amount": 0.001,
            "price": 45000.0,  # Below market for testing
        },
        "stop_loss_order": {
            "symbol": "BTC/USDT",
            "side": "sell",
            "type": "stop_loss",
            "amount": 0.001,
            "stop_price": 48000.0,
            "price": 47900.0,
        },
    }


@pytest.fixture
def sample_ticker_data():
    """Sample ticker data for testing"""
    return {
        "e": "24hrTicker",
        "s": "BTCUSDT",
        "p": "1000.00",  # Price change
        "P": "2.00",  # Price change percent
        "w": "50000.00",  # Weighted average price
        "c": "50500.00",  # Last price
        "Q": "0.1",  # Last quantity
        "b": "50499.00",  # Best bid
        "B": "1.0",  # Best bid quantity
        "a": "50501.00",  # Best ask
        "A": "1.0",  # Best ask quantity
        "o": "49500.00",  # Open price
        "h": "51000.00",  # High price
        "l": "49000.00",  # Low price
        "v": "1000.00",  # Total traded base asset volume
        "q": "50000000.00",  # Total traded quote asset volume
        "O": 1234567890,  # Statistics open time
        "C": 1234567890,  # Statistics close time
        "F": 100,  # First trade ID
        "L": 200,  # Last trade ID
        "n": 100,  # Total number of trades
    }


@pytest.fixture
def sample_kline_data():
    """Sample kline/candlestick data for testing"""
    return {
        "e": "kline",
        "s": "BTCUSDT",
        "k": {
            "t": 1234567890000,  # Kline start time
            "T": 1234567950000,  # Kline close time
            "s": "BTCUSDT",  # Symbol
            "i": "1m",  # Interval
            "f": 100,  # First trade ID
            "L": 200,  # Last trade ID
            "o": "50000.00",  # Open price
            "c": "50100.00",  # Close price
            "h": "50200.00",  # High price
            "l": "49900.00",  # Low price
            "v": "10.00",  # Base asset volume
            "n": 100,  # Number of trades
            "x": False,  # Is this kline closed?
            "q": "500000.00",  # Quote asset volume
            "V": "5.00",  # Taker buy base asset volume
            "Q": "250000.00",  # Taker buy quote asset volume
            "B": "0",  # Ignore
        },
    }
