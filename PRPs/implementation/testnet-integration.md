# PRP: Binance Testnet Integration Implementation

## Context Loading

### System State
- **Branch**: feature/integration-testing-testnet
- **Base**: main
- **Test Coverage**: 55% overall, 85%+ on critical components
- **Integration Gap**: No exchange testnet validation

### Existing Infrastructure
```python
# Current exchange setup (executor_service.py)
- Uses ccxt.async_support
- Bybit testnet support exists
- set_sandbox_mode(True) for testnet
- Environment-based configuration

# Configuration pattern (.env.example)
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_API_SECRET=your_binance_api_secret_here
BINANCE_TESTNET=true
```

### Architecture References
- docs/TESTNET_INTEGRATION_ARCHITECTURE.md
- docs/TESTNET_TASK_BREAKDOWN.md
- docs/PRODUCTION_READINESS_CHECKLIST.md

## Implementation Requirements

### Stream A: Exchange Integration (workspace/features/testnet_integration/)

#### A1: Configuration Module (testnet_config.py)
```python
"""
Testnet configuration management
Loads from environment, validates, and provides typed config
"""

from dataclasses import dataclass
from typing import Optional
import os
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class ExchangeType(Enum):
    BINANCE = "binance"
    BYBIT = "bybit"

@dataclass
class TestnetConfig:
    exchange: ExchangeType
    api_key: str
    api_secret: str
    testnet_enabled: bool = True

    # Binance URLs
    binance_testnet_rest: str = "https://testnet.binance.vision"
    binance_testnet_ws: str = "wss://testnet.binance.vision/ws"

    @classmethod
    def from_env(cls, exchange: ExchangeType):
        prefix = exchange.value.upper()

        api_key = os.getenv(f"{prefix}_API_KEY", "")
        api_secret = os.getenv(f"{prefix}_API_SECRET", "")

        if not api_key or not api_secret:
            raise ValueError(f"Missing {prefix} API credentials")

        return cls(
            exchange=exchange,
            api_key=api_key,
            api_secret=api_secret,
            testnet_enabled=os.getenv(f"{prefix}_TESTNET", "true").lower() == "true"
        )

    def validate(self) -> bool:
        """Validate configuration"""
        # Check API key format (64 chars for Binance)
        if self.exchange == ExchangeType.BINANCE:
            if len(self.api_key) != 64:
                logger.warning("Invalid Binance API key length")
                return False
        return True
```

#### A2: Exchange Adapter (testnet_adapter.py)
```python
"""
Testnet exchange adapter using ccxt
Extends existing TradeExecutor patterns
"""

import asyncio
import ccxt.async_support as ccxt
from decimal import Decimal
from typing import Optional, Dict, Any
import logging

from .testnet_config import TestnetConfig, ExchangeType

logger = logging.getLogger(__name__)

class TestnetExchangeAdapter:
    def __init__(self, config: TestnetConfig):
        self.config = config
        self.exchange: Optional[ccxt.Exchange] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize exchange connection"""
        try:
            # Get exchange class
            exchange_class = getattr(ccxt, self.config.exchange.value)

            # Configure options
            options = {
                'apiKey': self.config.api_key,
                'secret': self.config.api_secret,
                'enableRateLimit': True,
                'timeout': 30000,
            }

            # Binance testnet specific
            if self.config.exchange == ExchangeType.BINANCE and self.config.testnet_enabled:
                options['urls'] = {
                    'api': {
                        'public': f'{self.config.binance_testnet_rest}/api',
                        'private': f'{self.config.binance_testnet_rest}/api',
                        'web': self.config.binance_testnet_rest,
                    }
                }

            # Create exchange instance
            self.exchange = exchange_class(options)

            # Enable sandbox mode
            if self.config.testnet_enabled:
                self.exchange.set_sandbox_mode(True)

            # Load markets
            await self.exchange.load_markets()

            self._initialized = True
            logger.info(f"Initialized {self.config.exchange.value} in {'testnet' if self.config.testnet_enabled else 'production'} mode")

        except Exception as e:
            logger.error(f"Failed to initialize exchange: {e}")
            raise

    async def get_balance(self) -> Dict[str, Any]:
        """Get account balance"""
        if not self._initialized:
            await self.initialize()

        balance = await self.exchange.fetch_balance()
        return {
            'free': balance['free'],
            'used': balance['used'],
            'total': balance['total']
        }

    async def place_order(
        self,
        symbol: str,
        side: str,  # 'buy' or 'sell'
        order_type: str,  # 'market' or 'limit'
        amount: float,
        price: Optional[float] = None
    ) -> Dict[str, Any]:
        """Place an order on testnet"""
        if not self._initialized:
            await self.initialize()

        try:
            if order_type == 'market':
                order = await self.exchange.create_market_order(symbol, side, amount)
            else:
                if price is None:
                    raise ValueError("Price required for limit orders")
                order = await self.exchange.create_limit_order(symbol, side, amount, price)

            return {
                'id': order['id'],
                'symbol': order['symbol'],
                'side': order['side'],
                'type': order['type'],
                'amount': order['amount'],
                'price': order.get('price'),
                'status': order['status'],
                'timestamp': order['timestamp']
            }

        except Exception as e:
            logger.error(f"Order placement failed: {e}")
            raise

    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an order"""
        if not self._initialized:
            await self.initialize()

        try:
            await self.exchange.cancel_order(order_id, symbol)
            return True
        except Exception as e:
            logger.error(f"Order cancellation failed: {e}")
            return False

    async def get_positions(self) -> list:
        """Get open positions"""
        if not self._initialized:
            await self.initialize()

        # For spot trading, positions are the non-zero balances
        balance = await self.get_balance()
        positions = []

        for currency, amount in balance['total'].items():
            if amount > 0 and currency != 'USDT':
                positions.append({
                    'symbol': f"{currency}/USDT",
                    'amount': amount,
                    'side': 'long'  # Spot is always long
                })

        return positions

    async def close(self) -> None:
        """Close exchange connection"""
        if self.exchange:
            await self.exchange.close()
            self._initialized = False
```

#### A3: WebSocket Integration (websocket_testnet.py)
```python
"""
WebSocket adapter for testnet streaming data
"""

import asyncio
import json
import logging
from typing import Optional, Callable, Dict, Any
import websockets
from datetime import datetime

from .testnet_config import TestnetConfig, ExchangeType

logger = logging.getLogger(__name__)

class TestnetWebSocketClient:
    def __init__(self, config: TestnetConfig):
        self.config = config
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.running = False
        self.callbacks: Dict[str, Callable] = {}

    def _get_ws_url(self) -> str:
        """Get WebSocket URL for exchange"""
        if self.config.exchange == ExchangeType.BINANCE:
            if self.config.testnet_enabled:
                return self.config.binance_testnet_ws
            else:
                return "wss://stream.binance.com:9443/ws"
        # Add other exchanges as needed
        raise ValueError(f"Unsupported exchange: {self.config.exchange}")

    async def connect(self) -> None:
        """Connect to WebSocket"""
        try:
            url = self._get_ws_url()
            self.ws = await websockets.connect(url)
            self.running = True
            logger.info(f"Connected to {self.config.exchange.value} WebSocket")

            # Start message handler
            asyncio.create_task(self._handle_messages())

        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            raise

    async def _handle_messages(self) -> None:
        """Handle incoming messages"""
        while self.running and self.ws:
            try:
                message = await self.ws.recv()
                data = json.loads(message)

                # Route to appropriate callback
                if 'stream' in data:
                    stream = data['stream']
                    if stream in self.callbacks:
                        await self.callbacks[stream](data['data'])

            except websockets.ConnectionClosed:
                logger.warning("WebSocket connection closed")
                await self._reconnect()
            except Exception as e:
                logger.error(f"Message handling error: {e}")

    async def _reconnect(self) -> None:
        """Reconnect with exponential backoff"""
        retry_count = 0
        while self.running and retry_count < 5:
            try:
                await asyncio.sleep(2 ** retry_count)
                await self.connect()

                # Resubscribe to all streams
                for stream in self.callbacks:
                    await self._subscribe(stream)

                logger.info("Reconnected successfully")
                return

            except Exception as e:
                retry_count += 1
                logger.warning(f"Reconnection attempt {retry_count} failed: {e}")

    async def subscribe_ticker(self, symbol: str, callback: Callable) -> None:
        """Subscribe to ticker updates"""
        stream = f"{symbol.lower()}@ticker"
        self.callbacks[stream] = callback
        await self._subscribe(stream)

    async def subscribe_kline(self, symbol: str, interval: str, callback: Callable) -> None:
        """Subscribe to kline/candlestick updates"""
        stream = f"{symbol.lower()}@kline_{interval}"
        self.callbacks[stream] = callback
        await self._subscribe(stream)

    async def _subscribe(self, stream: str) -> None:
        """Send subscription message"""
        if not self.ws:
            raise RuntimeError("WebSocket not connected")

        if self.config.exchange == ExchangeType.BINANCE:
            msg = {
                "method": "SUBSCRIBE",
                "params": [stream],
                "id": len(self.callbacks)
            }
            await self.ws.send(json.dumps(msg))

    async def close(self) -> None:
        """Close WebSocket connection"""
        self.running = False
        if self.ws:
            await self.ws.close()
```

### Stream B: Integration Tests (workspace/tests/integration/testnet/)

#### B1: Test Fixtures (conftest.py)
```python
"""
Test fixtures for testnet integration tests
"""

import pytest
import asyncio
import os
from typing import AsyncGenerator
from unittest.mock import MagicMock, AsyncMock

from workspace.features.testnet_integration.testnet_config import TestnetConfig, ExchangeType
from workspace.features.testnet_integration.testnet_adapter import TestnetExchangeAdapter
from workspace.features.testnet_integration.websocket_testnet import TestnetWebSocketClient

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def testnet_config():
    """Create test configuration"""
    # Check if real credentials available
    if os.getenv('BINANCE_API_KEY'):
        return TestnetConfig.from_env(ExchangeType.BINANCE)

    # Use mock configuration
    return TestnetConfig(
        exchange=ExchangeType.BINANCE,
        api_key="mock_api_key" * 8,  # 64 chars
        api_secret="mock_secret",
        testnet_enabled=True
    )

@pytest.fixture
async def exchange_adapter(testnet_config) -> AsyncGenerator[TestnetExchangeAdapter, None]:
    """Create exchange adapter"""
    adapter = TestnetExchangeAdapter(testnet_config)

    # Mock if no real credentials
    if testnet_config.api_key.startswith("mock"):
        adapter.exchange = create_mock_exchange()
    else:
        await adapter.initialize()

    yield adapter

    if adapter.exchange:
        await adapter.close()

@pytest.fixture
async def websocket_client(testnet_config) -> AsyncGenerator[TestnetWebSocketClient, None]:
    """Create WebSocket client"""
    client = TestnetWebSocketClient(testnet_config)

    # Mock if no real credentials
    if not testnet_config.api_key.startswith("mock"):
        await client.connect()

    yield client

    await client.close()

def create_mock_exchange():
    """Create mock exchange for testing"""
    mock = AsyncMock()
    mock.fetch_balance = AsyncMock(return_value={
        'free': {'USDT': 10000, 'BTC': 0},
        'used': {'USDT': 0, 'BTC': 0},
        'total': {'USDT': 10000, 'BTC': 0}
    })
    mock.create_market_order = AsyncMock(return_value={
        'id': '12345',
        'symbol': 'BTC/USDT',
        'side': 'buy',
        'type': 'market',
        'amount': 0.001,
        'status': 'closed',
        'timestamp': 1234567890
    })
    return mock
```

#### B2: Connection Tests (test_connection.py)
```python
"""
Test exchange connections to testnet
"""

import pytest
from workspace.features.testnet_integration.testnet_config import TestnetConfig, ExchangeType

@pytest.mark.asyncio
async def test_exchange_initialization(exchange_adapter):
    """Test exchange can initialize"""
    if not exchange_adapter._initialized:
        await exchange_adapter.initialize()

    assert exchange_adapter._initialized
    assert exchange_adapter.exchange is not None

@pytest.mark.asyncio
async def test_get_balance(exchange_adapter):
    """Test fetching account balance"""
    balance = await exchange_adapter.get_balance()

    assert 'free' in balance
    assert 'used' in balance
    assert 'total' in balance
    assert 'USDT' in balance['total']

@pytest.mark.asyncio
async def test_websocket_connection(websocket_client):
    """Test WebSocket connection"""
    if not websocket_client.ws:
        await websocket_client.connect()

    assert websocket_client.running

    # Test subscription
    callback_called = False
    async def ticker_callback(data):
        nonlocal callback_called
        callback_called = True

    await websocket_client.subscribe_ticker('BTCUSDT', ticker_callback)

    # Wait briefly for potential message
    await asyncio.sleep(2)

@pytest.mark.asyncio
async def test_invalid_credentials():
    """Test handling of invalid credentials"""
    config = TestnetConfig(
        exchange=ExchangeType.BINANCE,
        api_key="invalid_key",
        api_secret="invalid_secret",
        testnet_enabled=True
    )

    adapter = TestnetExchangeAdapter(config)

    with pytest.raises(Exception):
        await adapter.initialize()
```

#### B3: Order Execution Tests (test_orders.py)
```python
"""
Test order execution on testnet
"""

import pytest
from decimal import Decimal

@pytest.mark.asyncio
async def test_place_market_order(exchange_adapter):
    """Test placing a market order"""
    order = await exchange_adapter.place_order(
        symbol='BTC/USDT',
        side='buy',
        order_type='market',
        amount=0.001  # Small amount for testing
    )

    assert order['id'] is not None
    assert order['symbol'] == 'BTC/USDT'
    assert order['side'] == 'buy'
    assert order['type'] == 'market'
    assert order['amount'] == 0.001

@pytest.mark.asyncio
async def test_place_limit_order(exchange_adapter):
    """Test placing a limit order"""
    # Get current price first
    ticker = await exchange_adapter.exchange.fetch_ticker('BTC/USDT')
    price = ticker['last'] * 0.95  # 5% below current price

    order = await exchange_adapter.place_order(
        symbol='BTC/USDT',
        side='buy',
        order_type='limit',
        amount=0.001,
        price=price
    )

    assert order['id'] is not None
    assert order['type'] == 'limit'
    assert order['price'] == price

@pytest.mark.asyncio
async def test_cancel_order(exchange_adapter):
    """Test cancelling an order"""
    # Place a limit order first
    ticker = await exchange_adapter.exchange.fetch_ticker('BTC/USDT')
    price = ticker['last'] * 0.90  # 10% below to ensure not filled

    order = await exchange_adapter.place_order(
        symbol='BTC/USDT',
        side='buy',
        order_type='limit',
        amount=0.001,
        price=price
    )

    # Cancel it
    cancelled = await exchange_adapter.cancel_order(order['id'], 'BTC/USDT')
    assert cancelled is True

@pytest.mark.asyncio
async def test_batch_orders(exchange_adapter):
    """Test placing multiple orders"""
    orders = []

    for i in range(10):
        order = await exchange_adapter.place_order(
            symbol='BTC/USDT',
            side='buy' if i % 2 == 0 else 'sell',
            order_type='market',
            amount=0.001
        )
        orders.append(order)

    assert len(orders) == 10
    assert all(o['status'] in ['closed', 'open'] for o in orders)
```

### Stream C: Configuration & Security

#### C1: Environment Configuration (.env.testnet)
```bash
# Binance Testnet Configuration
# Get API keys from: https://testnet.binance.vision/

# API Credentials (NEVER COMMIT)
BINANCE_API_KEY=your_testnet_api_key_here_64_chars
BINANCE_API_SECRET=your_testnet_api_secret_here

# Testnet Mode
BINANCE_TESTNET=true

# Connection Settings
BINANCE_RATE_LIMIT_MS=100
BINANCE_TIMEOUT_MS=30000
BINANCE_MAX_RETRIES=3

# WebSocket Settings
BINANCE_WS_PING_INTERVAL=30
BINANCE_WS_RECONNECT_DELAY=5
```

#### C2: Security Validation (security_validator.py)
```python
"""
Security validation for API keys and configuration
"""

import re
import os
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

class SecurityValidator:

    @staticmethod
    def validate_api_key(key: str, exchange: str) -> bool:
        """Validate API key format"""
        if exchange == "binance":
            # Binance keys are 64 alphanumeric characters
            return bool(re.match(r'^[A-Za-z0-9]{64}$', key))
        elif exchange == "bybit":
            # Bybit keys are UUID format
            return bool(re.match(r'^[A-Za-z0-9\-]{36}$', key))
        return False

    @staticmethod
    def scan_for_secrets(directory: str) -> List[Tuple[str, int, str]]:
        """Scan directory for potential secrets"""
        patterns = [
            (r'[A-Za-z0-9]{64}', 'Potential API key'),
            (r'[A-Za-z0-9\-]{36}', 'Potential UUID'),
            (r'(api[_-]?key|api[_-]?secret|password)\s*=\s*["\'][^"\']+["\']', 'Hardcoded credential'),
        ]

        findings = []

        for root, dirs, files in os.walk(directory):
            # Skip .git and node_modules
            dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', '__pycache__'}]

            for file in files:
                if file.endswith(('.py', '.js', '.ts', '.yaml', '.yml', '.json')):
                    filepath = os.path.join(root, file)

                    try:
                        with open(filepath, 'r') as f:
                            for line_num, line in enumerate(f, 1):
                                for pattern, desc in patterns:
                                    if re.search(pattern, line, re.IGNORECASE):
                                        # Exclude test files and examples
                                        if not any(x in filepath for x in ['test', 'example', '.env.example']):
                                            findings.append((filepath, line_num, desc))
                    except:
                        pass

        return findings

    @staticmethod
    def sanitize_for_logs(value: str, key_type: str = "api_key") -> str:
        """Sanitize sensitive values for logging"""
        if not value:
            return "[EMPTY]"

        if key_type == "api_key":
            # Show first 4 and last 4 characters
            if len(value) > 8:
                return f"{value[:4]}...{value[-4:]}"

        return "[REDACTED]"
```

### Stream D: Documentation

#### D1: Setup Guide (docs/testnet/SETUP_GUIDE.md)
```markdown
# Binance Testnet Setup Guide

## Prerequisites
- Python 3.10+
- Active Binance account
- Access to testnet.binance.vision

## Step 1: Create Testnet Account

1. Go to [https://testnet.binance.vision/](https://testnet.binance.vision/)
2. Click "Log In with GitHub" (uses GitHub OAuth)
3. Authorize the application

## Step 2: Generate API Keys

1. After login, go to "API Management"
2. Click "Create API"
3. Label your API key (e.g., "Trading Bot Testnet")
4. Complete 2FA verification if required
5. Save your API Key and Secret immediately

⚠️ **Important**: API secrets are shown only once!

## Step 3: Get Test Funds

1. Go to "Faucet" in the testnet interface
2. Request test USDT (usually 10,000 USDT)
3. Request test BTC if needed for testing

## Step 4: Configure Environment

1. Copy `.env.example` to `.env.testnet`:
   ```bash
   cp .env.example .env.testnet
   ```

2. Add your testnet credentials:
   ```bash
   BINANCE_API_KEY=your_64_character_api_key_here
   BINANCE_API_SECRET=your_api_secret_here
   BINANCE_TESTNET=true
   ```

3. Verify configuration:
   ```bash
   python -m workspace.features.testnet_integration.verify_setup
   ```

## Step 5: Run Integration Tests

```bash
# Run all testnet tests
pytest workspace/tests/integration/testnet/ -v

# Run specific test
pytest workspace/tests/integration/testnet/test_connection.py -v

# Run with coverage
pytest workspace/tests/integration/testnet/ --cov=workspace.features.testnet_integration --cov-report=html
```

## Troubleshooting

### "Invalid API Key" Error
- Ensure you're using testnet API keys, not production
- Check for extra spaces or newlines in .env file
- Verify BINANCE_TESTNET=true is set

### "Insufficient Balance" Error
- Use the testnet faucet to get test funds
- Check you have USDT for buying
- Reduce order amounts (use 0.001 BTC minimum)

### Connection Timeouts
- Testnet may be slower than production
- Increase timeout settings if needed
- Check your internet connection
```

## Validation Loops

### V1: Unit Test Loop
```python
# Run after each module implementation
pytest workspace/tests/unit/testnet/ -v
# Target: 100% pass rate
```

### V2: Integration Test Loop
```python
# Run after integration complete
pytest workspace/tests/integration/testnet/ -v
# Target: 100% pass rate, 80%+ coverage
```

### V3: End-to-End Test Loop
```python
# Full trading cycle test
python -m workspace.features.testnet_integration.e2e_test
# Success: 100+ orders placed, WebSocket stable >1hr
```

### V4: Security Validation Loop
```python
# Security scan
python -m workspace.features.testnet_integration.security_validator scan .
# Target: Zero findings

# Secret detection
trufflehog filesystem . --json
# Target: Zero secrets detected
```

## Success Criteria

### Technical Requirements
- [ ] Binance testnet connection established
- [ ] 100+ orders successfully placed
- [ ] WebSocket streaming stable for >1 hour
- [ ] Stop-loss orders execute correctly
- [ ] Circuit breaker integration verified
- [ ] 80%+ code coverage achieved

### Security Requirements
- [ ] No hardcoded credentials
- [ ] API keys properly managed
- [ ] Secrets scanning passed
- [ ] Secure logging implemented

### Documentation Requirements
- [ ] Setup guide complete with screenshots
- [ ] API reference documented
- [ ] Troubleshooting guide comprehensive
- [ ] Test execution guide clear

## Error Handling Patterns

```python
# Network errors: Retry with exponential backoff
# Rate limits: Linear backoff with jitter
# Invalid orders: Fail fast with clear error
# Insufficient funds: Alert and halt
# WebSocket disconnect: Auto-reconnect with state recovery
```

## Rollback Plan

If issues arise:
1. Revert to previous commit
2. Run existing test suite to verify
3. Document issues in TESTNET_ISSUES.md
4. Create hotfix branch if needed

## PR Checklist

Before creating PR:
- [ ] All tests passing (100%)
- [ ] Coverage ≥80% on new code
- [ ] Documentation complete
- [ ] Security scan clean
- [ ] No linting errors
- [ ] Commit messages follow convention
- [ ] PR description comprehensive
