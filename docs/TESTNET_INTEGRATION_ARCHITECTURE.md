# Testnet Integration Architecture

## Executive Summary
Complete architecture for integrating Binance testnet API with the LLM-powered cryptocurrency trading system. This design leverages existing ccxt integration while adding comprehensive testnet support, integration testing, and secure configuration management.

## System Context

### Existing Infrastructure
- **Trade Executor**: Already using ccxt with Bybit testnet support
- **Configuration**: Environment-based with .env files
- **Testing**: Established patterns in workspace/tests/
- **WebSocket**: WebsocketClient for real-time data
- **Risk Management**: Circuit breaker and stop-loss manager

### Integration Goals
1. Add Binance testnet support alongside existing Bybit
2. Create comprehensive integration test suite (80%+ coverage)
3. Validate end-to-end trading cycle on testnet
4. Ensure secure API key management
5. Document setup and troubleshooting

## Architecture Design

### 1. Configuration Layer

```python
# workspace/features/testnet_integration/config.py

from dataclasses import dataclass
from typing import Optional, Dict, Any
import os
from enum import Enum

class ExchangeType(Enum):
    BINANCE = "binance"
    BYBIT = "bybit"

class TestnetMode(Enum):
    PRODUCTION = "production"
    TESTNET = "testnet"
    PAPER = "paper"

@dataclass
class TestnetConfig:
    """Testnet configuration for exchange connections"""
    exchange: ExchangeType
    mode: TestnetMode
    api_key: str
    api_secret: str

    # Binance-specific
    binance_testnet_rest_url: str = "https://testnet.binance.vision"
    binance_testnet_ws_url: str = "wss://testnet.binance.vision/ws"

    # Bybit-specific (existing)
    bybit_testnet_rest_url: str = "https://api-testnet.bybit.com"
    bybit_testnet_ws_url: str = "wss://stream-testnet.bybit.com"

    # Common settings
    rate_limit_buffer_ms: int = 100
    max_retries: int = 3
    timeout_ms: int = 5000

    @classmethod
    def from_env(cls, exchange: ExchangeType) -> 'TestnetConfig':
        """Load configuration from environment variables"""
        prefix = exchange.value.upper()
        return cls(
            exchange=exchange,
            mode=TestnetMode.TESTNET if os.getenv(f"{prefix}_TESTNET", "true").lower() == "true" else TestnetMode.PRODUCTION,
            api_key=os.getenv(f"{prefix}_API_KEY", ""),
            api_secret=os.getenv(f"{prefix}_API_SECRET", ""),
        )
```

### 2. Exchange Adapter Layer

```python
# workspace/features/testnet_integration/exchange_adapter.py

import ccxt.async_support as ccxt
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class TestnetExchangeAdapter:
    """
    Unified adapter for testnet exchanges
    Extends existing TradeExecutor with testnet-specific features
    """

    def __init__(self, config: TestnetConfig):
        self.config = config
        self.exchange: Optional[ccxt.Exchange] = None

    async def initialize(self) -> None:
        """Initialize exchange connection with testnet configuration"""
        exchange_class = getattr(ccxt, self.config.exchange.value)

        options = {
            'apiKey': self.config.api_key,
            'secret': self.config.api_secret,
            'enableRateLimit': True,
            'rateLimit': self.config.rate_limit_buffer_ms,
        }

        if self.config.exchange == ExchangeType.BINANCE:
            if self.config.mode == TestnetMode.TESTNET:
                options['urls'] = {
                    'api': {
                        'public': f'{self.config.binance_testnet_rest_url}/api',
                        'private': f'{self.config.binance_testnet_rest_url}/api',
                    }
                }
                options['test'] = True

        self.exchange = exchange_class(options)

        if self.config.mode == TestnetMode.TESTNET:
            self.exchange.set_sandbox_mode(True)

        await self.exchange.load_markets()
        logger.info(f"Initialized {self.config.exchange.value} in {self.config.mode.value} mode")
```

### 3. WebSocket Integration

```python
# workspace/features/testnet_integration/websocket_adapter.py

import asyncio
import json
from typing import Optional, Callable, Dict, Any
import websockets
import logging

logger = logging.getLogger(__name__)

class TestnetWebSocketAdapter:
    """WebSocket adapter for testnet connections"""

    def __init__(self, config: TestnetConfig):
        self.config = config
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.subscriptions: Dict[str, Callable] = {}

    async def connect(self) -> None:
        """Connect to testnet WebSocket"""
        ws_url = self._get_ws_url()
        self.ws = await websockets.connect(ws_url)
        logger.info(f"Connected to {self.config.exchange.value} testnet WebSocket")

    def _get_ws_url(self) -> str:
        """Get WebSocket URL based on exchange and mode"""
        if self.config.exchange == ExchangeType.BINANCE:
            return self.config.binance_testnet_ws_url if self.config.mode == TestnetMode.TESTNET else "wss://stream.binance.com:9443/ws"
        else:  # Bybit
            return self.config.bybit_testnet_ws_url if self.config.mode == TestnetMode.TESTNET else "wss://stream.bybit.com/v5/public"

    async def subscribe_ticker(self, symbol: str, callback: Callable) -> None:
        """Subscribe to ticker updates"""
        if self.config.exchange == ExchangeType.BINANCE:
            stream_name = f"{symbol.lower()}@ticker"
            await self._subscribe_binance(stream_name, callback)

    async def _subscribe_binance(self, stream: str, callback: Callable) -> None:
        """Binance-specific subscription"""
        subscribe_msg = {
            "method": "SUBSCRIBE",
            "params": [stream],
            "id": 1
        }
        await self.ws.send(json.dumps(subscribe_msg))
        self.subscriptions[stream] = callback
```

### 4. Integration Test Infrastructure

```python
# workspace/tests/integration/testnet/conftest.py

import pytest
import asyncio
from typing import AsyncGenerator
import os

from workspace.features.testnet_integration.config import TestnetConfig, ExchangeType
from workspace.features.testnet_integration.exchange_adapter import TestnetExchangeAdapter

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def binance_testnet_config():
    """Binance testnet configuration"""
    return TestnetConfig.from_env(ExchangeType.BINANCE)

@pytest.fixture
async def binance_testnet_adapter(binance_testnet_config) -> AsyncGenerator[TestnetExchangeAdapter, None]:
    """Initialize Binance testnet adapter"""
    adapter = TestnetExchangeAdapter(binance_testnet_config)
    await adapter.initialize()
    yield adapter
    if adapter.exchange:
        await adapter.exchange.close()

@pytest.fixture
def testnet_credentials():
    """Load testnet credentials from environment"""
    return {
        'binance': {
            'api_key': os.getenv('BINANCE_TESTNET_API_KEY', ''),
            'api_secret': os.getenv('BINANCE_TESTNET_API_SECRET', ''),
        }
    }
```

### 5. Security Architecture

```yaml
# .github/workflows/security-scan.yml

name: Security Scan

on:
  pull_request:
    branches: [main]

jobs:
  secret-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Scan for secrets
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: ${{ github.event.pull_request.base.sha }}
          head: ${{ github.event.pull_request.head.sha }}
```

```python
# workspace/features/testnet_integration/security.py

import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class APIKeyValidator:
    """Validate and sanitize API keys"""

    @staticmethod
    def validate_api_key(key: str) -> bool:
        """Validate API key format"""
        # Binance API keys are 64 characters
        # Bybit API keys are 36 characters (UUID format)
        if len(key) in [36, 64]:
            return bool(re.match(r'^[A-Za-z0-9\-]+$', key))
        return False

    @staticmethod
    def sanitize_for_logging(value: str) -> str:
        """Sanitize sensitive data for logging"""
        if not value:
            return "[EMPTY]"
        if len(value) > 8:
            return f"{value[:4]}...{value[-4:]}"
        return "[REDACTED]"
```

## API Contracts

### REST API Endpoints

```yaml
# PRPs/contracts/testnet-api-contracts.yaml

testnet_api:
  connection:
    endpoint: POST /testnet/connect
    request:
      exchange: string (binance|bybit)
      mode: string (testnet|production)
    response:
      connected: boolean
      exchange: string
      mode: string
      balance: object

  order_placement:
    endpoint: POST /testnet/order
    request:
      symbol: string
      side: string (buy|sell)
      type: string (market|limit|stop_loss)
      quantity: number
      price?: number
    response:
      order_id: string
      status: string
      filled_qty: number
      avg_price: number

  position_query:
    endpoint: GET /testnet/positions
    response:
      positions: array
        - symbol: string
        - side: string
        - quantity: number
        - entry_price: number
        - pnl: number
        - stop_loss: number
```

### WebSocket Streams

```yaml
websocket_streams:
  ticker:
    format: "{symbol}@ticker"
    message:
      e: string (event type)
      s: string (symbol)
      c: string (close price)
      v: string (volume)

  kline:
    format: "{symbol}@kline_{interval}"
    message:
      e: string (event type)
      k:
        t: number (open time)
        o: string (open)
        h: string (high)
        l: string (low)
        c: string (close)
        v: string (volume)
```

## Implementation Phases

### Phase 1: Core Infrastructure (4 hours)
1. Create configuration module
2. Implement exchange adapter
3. Setup WebSocket adapter
4. Add security validators

### Phase 2: Integration Testing (6 hours)
1. Create test fixtures
2. Connection tests
3. Order execution tests
4. WebSocket streaming tests
5. Error handling tests

### Phase 3: Documentation (2 hours)
1. Setup guide
2. API reference
3. Troubleshooting guide

## Performance Requirements

### Latency Targets
- Connection establishment: <2s
- Order placement: <500ms
- WebSocket message processing: <100ms
- Position query: <300ms

### Throughput Targets
- 100 orders/minute
- 1000 WebSocket messages/second
- 10 concurrent WebSocket streams

### Reliability Targets
- 99.5% uptime
- <0.1% order failure rate
- Automatic reconnection within 5s

## Security Considerations

### API Key Management
1. Environment variables only
2. Never in code or config files
3. Separate testnet/production keys
4. Regular rotation (monthly)

### Access Control
1. Read-only keys for monitoring
2. Trade keys with IP restrictions
3. Withdrawal disabled on trade keys
4. Audit logging for all API calls

### CI/CD Security
1. Secret scanning on all PRs
2. Environment-specific secrets
3. No production keys in CI
4. Secure artifact storage

## Error Handling Strategy

### Retry Logic
```python
class RetryStrategy:
    NETWORK_ERROR: (max_retries=5, backoff=exponential)
    RATE_LIMIT: (max_retries=3, backoff=linear)
    INVALID_ORDER: (max_retries=0, fail_fast=True)
    INSUFFICIENT_FUNDS: (max_retries=0, alert=True)
```

### Circuit Breaker Integration
- Trip on 5 consecutive failures
- Reset after 60 seconds
- Fallback to paper trading
- Alert on circuit breaker events

## Monitoring & Observability

### Metrics to Track
- Connection status
- Order success rate
- WebSocket message latency
- API call latency
- Rate limit usage
- Error rates by type

### Logging Strategy
- INFO: Connections, orders, positions
- WARNING: Rate limits, retries
- ERROR: Failed orders, disconnections
- DEBUG: Message content (sanitized)

## Migration Path

### From Current to Target State
1. **Current**: Bybit testnet only
2. **Phase 1**: Add Binance testnet config
3. **Phase 2**: Implement adapters
4. **Phase 3**: Integration tests
5. **Phase 4**: Documentation
6. **Target**: Multi-exchange testnet support

## Risk Mitigation

### Identified Risks
1. **Testnet unavailability**: Use mock responses
2. **Rate limiting**: Implement backoff
3. **API changes**: Version pinning
4. **Key exposure**: Secret scanning

### Mitigation Strategies
- Fallback to paper trading
- Comprehensive error handling
- Regular dependency updates
- Security audits

## Success Criteria

### Must Have
- ✅ Binance testnet connection working
- ✅ 100+ successful test orders
- ✅ WebSocket stable >1 hour
- ✅ 80%+ test coverage
- ✅ Zero security vulnerabilities

### Should Have
- ✅ Sub-500ms order latency
- ✅ Automatic reconnection
- ✅ Comprehensive logging
- ✅ Performance monitoring

### Nice to Have
- Multiple exchange support
- Order book depth integration
- Historical data replay
