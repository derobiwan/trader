# Reusable Components & Implementation Patterns

**Date**: October 27, 2025
**Phase**: Phase 1 - Business Discovery & Requirements
**Researcher**: Context Researcher Agent
**Status**: Complete

---

## Executive Summary

This document catalogs reusable libraries, proven patterns, and code examples for building the LLM-Powered Crypto Trading System. All components listed here are production-ready and widely adopted.

**Key Findings**:
- **ccxt**: Battle-tested exchange integration (103+ exchanges)
- **pandas-ta / ta-lib**: Comprehensive technical indicators
- **pydantic**: Data validation and settings management
- **asyncpg**: High-performance async PostgreSQL driver
- **FastAPI**: Modern async web framework
- **Celery**: Distributed task queue

---

## 1. Exchange Integration Libraries

### 1.1 ccxt - Cryptocurrency Exchange Trading Library

**Repository**: https://github.com/ccxt/ccxt
**License**: MIT
**Language**: Python, JavaScript, PHP, C#
**Stars**: 32,000+
**Maturity**: Production-ready (since 2017)

#### Why Use It

- Unified API for 103+ cryptocurrency exchanges
- Handles authentication, rate limiting, error handling
- Active development and community support
- Extensive documentation and examples
- Both sync and async (ccxt.async) support

#### Installation

```bash
pip install ccxt
# For async support
pip install ccxt[async]
```

#### Key Features

```python
import ccxt

# Initialize exchange
exchange = ccxt.binance({
    'apiKey': 'YOUR_API_KEY',
    'secret': 'YOUR_SECRET',
    'enableRateLimit': True,  # Built-in rate limiting
    'options': {'defaultType': 'future'}  # Perpetual futures
})

# Fetch market data
ticker = exchange.fetch_ticker('BTC/USDT')
ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1m', limit=100)

# Place orders
order = exchange.create_order(
    symbol='BTC/USDT',
    type='market',
    side='buy',
    amount=0.001
)

# Fetch positions (futures)
positions = exchange.fetch_positions()

# Error handling (built-in exceptions)
try:
    exchange.fetch_balance()
except ccxt.NetworkError as e:
    print(f'Network error: {e}')
except ccxt.ExchangeError as e:
    print(f'Exchange error: {e}')
```

#### Async Version

```python
import ccxt.async_support as ccxt
import asyncio

async def fetch_multiple_tickers(symbols):
    exchange = ccxt.binance({'enableRateLimit': True})

    tasks = [exchange.fetch_ticker(symbol) for symbol in symbols]
    tickers = await asyncio.gather(*tasks)

    await exchange.close()
    return tickers

# Run
tickers = asyncio.run(fetch_multiple_tickers(['BTC/USDT', 'ETH/USDT']))
```

#### WebSocket Support (ccxt.pro)

```python
from ccxt.pro import binance

exchange = binance()

async def watch_ticker():
    while True:
        ticker = await exchange.watch_ticker('BTC/USDT')
        print(ticker['last'])

asyncio.run(watch_ticker())
```

**Recommendation**: ✅ **Essential** - Use as primary exchange integration layer

---

### 1.2 python-binance (Alternative for Binance-specific features)

**Repository**: https://github.com/sammchardy/python-binance
**License**: MIT
**Stars**: 6,000+

#### When to Use

- Need Binance-specific features not in ccxt
- More granular control over Binance API
- WebSocket user data stream (account updates)

```python
from binance.client import Client
from binance.streams import BinanceSocketManager

client = Client(api_key, api_secret)

# User data stream (position updates, order updates)
bsm = BinanceSocketManager(client)
user_socket = bsm.user_socket()

async def handle_user_update(msg):
    if msg['e'] == 'ORDER_TRADE_UPDATE':
        print(f"Order update: {msg}")
    elif msg['e'] == 'ACCOUNT_UPDATE':
        print(f"Position update: {msg}")

user_socket.start(handle_user_update)
```

**Recommendation**: 🟡 **Optional** - Use if ccxt doesn't provide needed features

---

## 2. Technical Analysis Libraries

### 2.1 pandas-ta - Technical Analysis Library

**Repository**: https://github.com/twopirllc/pandas-ta
**License**: MIT
**Stars**: 5,000+
**Maturity**: Production-ready

#### Why Use It

- 130+ technical indicators
- Pandas DataFrame integration (perfect for OHLCV data)
- Well-documented, active development
- Easy to use and extend

#### Installation

```bash
pip install pandas-ta
```

#### Usage Examples

```python
import pandas as pd
import pandas_ta as ta

# Load OHLCV data into DataFrame
df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

# Calculate indicators
df['ema_20'] = ta.ema(df['close'], length=20)
df['rsi_7'] = ta.rsi(df['close'], length=7)
df['macd'] = ta.macd(df['close'])['MACD_12_26_9']
df['macd_signal'] = ta.macd(df['close'])['MACDs_12_26_9']
df['macd_hist'] = ta.macd(df['close'])['MACDh_12_26_9']

# Bollinger Bands
bb = ta.bbands(df['close'], length=20, std=2)
df['bb_upper'] = bb['BBU_20_2.0']
df['bb_middle'] = bb['BBM_20_2.0']
df['bb_lower'] = bb['BBL_20_2.0']

# ATR (Average True Range)
df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)

# Volume indicators
df['obv'] = ta.obv(df['close'], df['volume'])

# All indicators at once
df.ta.strategy("all")  # Calculate all available indicators
```

#### Common Indicators for Trading

```python
# Trend indicators
'ema_20', 'ema_50', 'ema_200'  # Exponential Moving Averages
'sma_20', 'sma_50', 'sma_200'  # Simple Moving Averages
'macd', 'macd_signal', 'macd_hist'  # MACD

# Momentum indicators
'rsi_14'  # Relative Strength Index
'stoch_k', 'stoch_d'  # Stochastic Oscillator
'cci'  # Commodity Channel Index

# Volatility indicators
'atr'  # Average True Range
'bbands'  # Bollinger Bands

# Volume indicators
'obv'  # On-Balance Volume
'vwap'  # Volume-Weighted Average Price
```

**Recommendation**: ✅ **Essential** - Use for all technical indicator calculations

---

### 2.2 ta-lib (Alternative - C-based, faster)

**Repository**: https://github.com/mrjbq7/ta-lib
**License**: BSD
**Stars**: 9,000+

#### Why Use It

- Extremely fast (C implementation)
- Industry standard (used by professional traders)
- 150+ indicators

#### Installation (requires TA-Lib C library)

```bash
# macOS
brew install ta-lib

# Ubuntu
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
sudo make install

# Install Python wrapper
pip install TA-Lib
```

#### Usage

```python
import talib
import numpy as np

close = np.array(df['close'])
high = np.array(df['high'])
low = np.array(df['low'])
volume = np.array(df['volume'])

# Calculate indicators
ema20 = talib.EMA(close, timeperiod=20)
rsi7 = talib.RSI(close, timeperiod=7)
macd, macdsignal, macdhist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
upper, middle, lower = talib.BBANDS(close, timeperiod=20)
```

**Recommendation**: 🟡 **Optional** - Use if performance is critical (pandas-ta sufficient for MVP)

---

## 3. Data Validation & Settings Management

### 3.1 pydantic - Data Validation Library

**Repository**: https://github.com/pydantic/pydantic
**License**: MIT
**Stars**: 20,000+
**Maturity**: Production-ready

#### Why Use It

- Type validation at runtime
- Automatic data parsing and validation
- Integration with FastAPI (automatic API docs)
- Settings management from environment variables
- JSON schema generation

#### Installation

```bash
pip install pydantic pydantic-settings
```

#### Usage for Trading Signals

```python
from pydantic import BaseModel, Field, validator
from typing import Literal
from datetime import datetime

class TradingSignal(BaseModel):
    symbol: str = Field(..., regex=r'^[A-Z]{3,10}$')
    action: Literal['buy_to_enter', 'sell_to_enter', 'hold', 'close_position']
    confidence: float = Field(..., ge=0.0, le=1.0)
    risk_usd: float = Field(..., gt=0)
    leverage: int = Field(..., ge=1, le=125)
    stop_loss_pct: float = Field(..., gt=0, lt=1)
    take_profit_pct: float | None = Field(None, gt=0)
    reasoning: str = Field(..., min_length=10)
    timestamp: datetime = Field(default_factory=datetime.now)

    @validator('symbol')
    def validate_symbol(cls, v):
        allowed_symbols = ['BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA']
        symbol_base = v.split('/')[0] if '/' in v else v
        if symbol_base not in allowed_symbols:
            raise ValueError(f'Symbol must be one of {allowed_symbols}')
        return v

    @validator('leverage')
    def validate_leverage(cls, v, values):
        # Adjust max leverage based on symbol
        symbol = values.get('symbol', '')
        max_leverage = {'BTC': 125, 'ETH': 100, 'SOL': 50}.get(symbol.split('/')[0], 50)
        if v > max_leverage:
            raise ValueError(f'Leverage for {symbol} cannot exceed {max_leverage}x')
        return v

# Usage
signal_data = {
    'symbol': 'BTC/USDT',
    'action': 'buy_to_enter',
    'confidence': 0.75,
    'risk_usd': 100.0,
    'leverage': 10,
    'stop_loss_pct': 0.02,
    'reasoning': 'Bullish MACD crossover with RSI oversold'
}

signal = TradingSignal(**signal_data)  # Automatic validation
print(signal.json())  # Convert to JSON
```

#### Settings Management

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Exchange settings
    binance_api_key: str
    binance_secret: str
    bybit_api_key: str
    bybit_secret: str

    # LLM settings
    openrouter_api_key: str
    llm_model: str = 'google/gemini-1.5-flash'
    llm_temperature: float = 0.2
    llm_max_tokens: int = 500

    # Database settings
    database_url: str
    db_pool_min_size: int = 10
    db_pool_max_size: int = 50

    # Trading settings
    max_position_size: float = 0.1  # 10% of portfolio per position
    max_leverage: int = 20
    daily_loss_limit: float = 0.05  # 5% daily loss limit

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'

# Load settings from environment variables
settings = Settings()

# Usage
exchange = ccxt.binance({
    'apiKey': settings.binance_api_key,
    'secret': settings.binance_secret,
})
```

**Recommendation**: ✅ **Essential** - Use for data validation and settings management

---

## 4. Database & ORM Libraries

### 4.1 asyncpg - Async PostgreSQL Driver

**Repository**: https://github.com/MagicStack/asyncpg
**License**: Apache 2.0
**Stars**: 6,800+
**Maturity**: Production-ready

#### Why Use It

- Fastest PostgreSQL driver for Python (3x faster than psycopg2)
- Native async/await support
- Connection pooling built-in
- Type conversion and prepared statements

#### Installation

```bash
pip install asyncpg
```

#### Usage with Connection Pool

```python
import asyncpg
import asyncio

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(
            database='trading_db',
            user='trading_user',
            password='password',
            host='localhost',
            port=5432,
            min_size=10,
            max_size=50,
            command_timeout=30
        )

    async def insert_trading_signal(self, signal: TradingSignal):
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO trading_signals
                (symbol, action, confidence, reasoning, timestamp)
                VALUES ($1, $2, $3, $4, $5)
            ''', signal.symbol, signal.action, signal.confidence,
                signal.reasoning, signal.timestamp)

    async def fetch_active_positions(self):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT * FROM positions WHERE status = 'open'
            ''')
            return [dict(row) for row in rows]

    async def close(self):
        await self.pool.close()

# Usage
db = Database()
await db.connect()
await db.insert_trading_signal(signal)
positions = await db.fetch_active_positions()
await db.close()
```

#### Batch Inserts (for market data)

```python
async def insert_market_data_batch(self, data):
    async with self.pool.acquire() as conn:
        await conn.copy_records_to_table(
            'market_data',
            records=data,
            columns=['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']
        )
```

**Recommendation**: ✅ **Essential** - Use for all database operations

---

### 4.2 SQLAlchemy (Alternative ORM)

**Repository**: https://github.com/sqlalchemy/sqlalchemy
**License**: MIT
**Stars**: 9,000+

#### When to Use

- Need ORM for complex relationships
- Want database-agnostic code
- Prefer declarative models

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, Float, DateTime

Base = declarative_base()

class Position(Base):
    __tablename__ = 'positions'

    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False)
    side = Column(String(10), nullable=False)
    entry_price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    leverage = Column(Integer, nullable=False)
    stop_loss = Column(Float)
    created_at = Column(DateTime)

# Async engine
engine = create_async_engine('postgresql+asyncpg://user:pass@localhost/db')
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Usage
async with async_session() as session:
    position = Position(symbol='BTC/USDT', side='long', ...)
    session.add(position)
    await session.commit()
```

**Recommendation**: 🟡 **Optional** - Use if ORM features needed (raw SQL + asyncpg sufficient for MVP)

---

## 5. Task Queue & Scheduling

### 5.1 Celery - Distributed Task Queue

**Repository**: https://github.com/celery/celery
**License**: BSD
**Stars**: 24,000+
**Maturity**: Production-ready (industry standard)

#### Installation

```bash
pip install celery[redis]
```

#### Configuration

```python
# celery_app.py
from celery import Celery
from celery.schedules import crontab

app = Celery('trading_system',
             broker='redis://localhost:6379/0',
             backend='redis://localhost:6379/1')

app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    beat_schedule={
        'trading-cycle-every-3-minutes': {
            'task': 'tasks.execute_trading_cycle',
            'schedule': 180.0,  # 3 minutes
        },
        'position-reconciliation-every-5-minutes': {
            'task': 'tasks.reconcile_positions',
            'schedule': 300.0,  # 5 minutes
        },
    },
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)
```

#### Task Definition

```python
# tasks.py
from celery_app import app
import asyncio

@app.task(bind=True, max_retries=3, retry_backoff=True)
def execute_trading_cycle(self):
    try:
        # Run async trading cycle
        asyncio.run(async_trading_cycle())
    except Exception as exc:
        # Retry on failure
        raise self.retry(exc=exc, countdown=60)

async def async_trading_cycle():
    # 1. Fetch market data
    market_data = await fetch_market_data()

    # 2. Get LLM decisions
    signals = await get_llm_decisions(market_data)

    # 3. Execute trades
    await execute_signals(signals)

    # 4. Update positions
    await update_positions()
```

#### Running Workers

```bash
# Start worker
celery -A celery_app worker --loglevel=info --concurrency=2

# Start beat scheduler (for periodic tasks)
celery -A celery_app beat --loglevel=info
```

**Recommendation**: ✅ **Essential** - Use for task scheduling and periodic jobs

---

## 6. Web Framework & API

### 6.1 FastAPI - Modern Web Framework

**Repository**: https://github.com/tiangolo/fastapi
**License**: MIT
**Stars**: 75,000+
**Maturity**: Production-ready

#### Installation

```bash
pip install fastapi[all]  # Includes uvicorn server
```

#### Basic Application

```python
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_database()
    await init_exchange_connections()
    yield
    # Shutdown
    await cleanup_resources()

app = FastAPI(title="Trading System API", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST endpoints
@app.get("/api/positions/current")
async def get_positions():
    positions = await db.fetch_active_positions()
    return {"positions": positions}

@app.post("/api/trading/manual-trigger")
async def manual_trigger(symbols: list[str]):
    result = await execute_trading_cycle(symbols)
    return {"status": "success", "signals": result}

@app.get("/api/performance/metrics")
async def get_metrics(timeframe: str = "1d"):
    metrics = await calculate_performance_metrics(timeframe)
    return metrics

# WebSocket endpoint
@app.websocket("/ws/positions")
async def websocket_positions(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            # Send position updates every second
            positions = await db.fetch_active_positions()
            await websocket.send_json({"positions": positions})
            await asyncio.sleep(1)
    except Exception as e:
        print(f"WebSocket error: {e}")

# Run server
# uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Recommendation**: ✅ **Essential** - Use as primary web framework

---

## 7. Utility Libraries

### 7.1 python-dotenv - Environment Variable Management

```bash
pip install python-dotenv
```

```python
from dotenv import load_dotenv
import os

load_dotenv()  # Load .env file

api_key = os.getenv('BINANCE_API_KEY')
```

### 7.2 loguru - Advanced Logging

```bash
pip install loguru
```

```python
from loguru import logger

# Configure logging
logger.add(
    "logs/trading_{time}.log",
    rotation="1 day",
    retention="30 days",
    level="INFO"
)

logger.info("Trading cycle started")
logger.warning("Rate limit approaching")
logger.error("Failed to execute order")
logger.critical("Emergency stop triggered")
```

### 7.3 tenacity - Retry Library

```bash
pip install tenacity
```

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=60))
async def fetch_with_retry(url):
    response = await http_client.get(url)
    response.raise_for_status()
    return response.json()
```

---

## 8. Proven Design Patterns

### 8.1 Singleton Pattern for Exchange Connection

```python
class ExchangeManager:
    _instance = None
    _exchange = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_exchange(self):
        if self._exchange is None:
            self._exchange = ccxt.binance({
                'apiKey': settings.binance_api_key,
                'secret': settings.binance_secret,
                'enableRateLimit': True
            })
        return self._exchange

# Usage
exchange = ExchangeManager().get_exchange()
```

### 8.2 Strategy Pattern for LLM Providers

```python
from abc import ABC, abstractmethod

class LLMProvider(ABC):
    @abstractmethod
    async def get_completion(self, messages: list) -> dict:
        pass

class OpenRouterProvider(LLMProvider):
    async def get_completion(self, messages: list) -> dict:
        # OpenRouter-specific implementation
        pass

class DirectOpenAIProvider(LLMProvider):
    async def get_completion(self, messages: list) -> dict:
        # Direct OpenAI implementation
        pass

class LLMProviderFactory:
    @staticmethod
    def create(provider_type: str) -> LLMProvider:
        if provider_type == 'openrouter':
            return OpenRouterProvider()
        elif provider_type == 'openai':
            return DirectOpenAIProvider()
        else:
            raise ValueError(f"Unknown provider: {provider_type}")

# Usage
provider = LLMProviderFactory.create('openrouter')
response = await provider.get_completion(messages)
```

### 8.3 Circuit Breaker Pattern for API Failures

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN

    async def call(self, func, *args, **kwargs):
        if self.state == 'OPEN':
            if (datetime.now() - self.last_failure_time).total_seconds() > self.timeout:
                self.state = 'HALF_OPEN'
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            if self.state == 'HALF_OPEN':
                self.state = 'CLOSED'
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = datetime.now()

            if self.failure_count >= self.failure_threshold:
                self.state = 'OPEN'
                logger.critical(f"Circuit breaker opened after {self.failure_count} failures")

            raise

# Usage
llm_circuit_breaker = CircuitBreaker(failure_threshold=3, timeout=300)

async def safe_llm_call(messages):
    return await llm_circuit_breaker.call(llm_provider.get_completion, messages)
```

---

## 9. Code Organization Structure

```
workspace/
├── features/
│   ├── market_data/
│   │   ├── __init__.py
│   │   ├── fetcher.py          # Market data fetching logic
│   │   ├── processor.py        # Indicator calculations
│   │   └── models.py           # Pydantic models
│   │
│   ├── llm_engine/
│   │   ├── __init__.py
│   │   ├── providers.py        # LLM provider implementations
│   │   ├── prompt_builder.py  # Prompt construction
│   │   └── response_parser.py # JSON parsing and validation
│   │
│   ├── decision_engine/
│   │   ├── __init__.py
│   │   ├── signal_generator.py # Trading signal generation
│   │   ├── validator.py        # Signal validation
│   │   └── models.py
│   │
│   ├── trade_executor/
│   │   ├── __init__.py
│   │   ├── order_manager.py    # Order placement logic
│   │   ├── position_manager.py # Position tracking
│   │   └── reconciliation.py   # Position reconciliation
│   │
│   ├── risk_manager/
│   │   ├── __init__.py
│   │   ├── position_sizer.py   # Kelly Criterion implementation
│   │   ├── stop_loss_manager.py # Stop-loss logic
│   │   └── portfolio_risk.py   # Portfolio-level risk
│   │
│   └── monitoring/
│       ├── __init__.py
│       ├── metrics.py          # Performance calculations
│       ├── alerting.py         # Alert system
│       └── logging_config.py
│
├── shared/
│   ├── database.py             # Database connection pool
│   ├── exchange.py             # Exchange manager
│   ├── config.py               # Settings (pydantic-settings)
│   └── utils.py                # Common utilities
│
├── api/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app
│   ├── routes.py               # API endpoints
│   └── websockets.py           # WebSocket handlers
│
├── tasks/
│   ├── __init__.py
│   ├── celery_app.py           # Celery configuration
│   └── trading_tasks.py        # Celery tasks
│
└── tests/
    ├── test_market_data.py
    ├── test_llm_engine.py
    ├── test_decision_engine.py
    ├── test_trade_executor.py
    └── test_risk_manager.py
```

---

## 10. Testing Libraries

### 10.1 pytest - Testing Framework

```bash
pip install pytest pytest-asyncio pytest-cov
```

```python
# test_signal_generator.py
import pytest
from features.decision_engine.signal_generator import generate_signals

@pytest.mark.asyncio
async def test_generate_signals():
    market_data = {
        'BTC/USDT': {'price': 50000, 'rsi': 30, 'macd': 0.5},
    }

    signals = await generate_signals(market_data)

    assert len(signals) > 0
    assert signals[0]['symbol'] == 'BTC/USDT'
    assert signals[0]['confidence'] >= 0 and signals[0]['confidence'] <= 1
```

### 10.2 pytest-vcr - Record/Replay HTTP Requests

```bash
pip install pytest-vcr
```

```python
import pytest
import vcr

@pytest.mark.vcr()
async def test_fetch_ticker():
    ticker = await exchange.fetch_ticker('BTC/USDT')
    assert 'last' in ticker
    assert ticker['last'] > 0
```

---

## 11. Library Dependency Matrix

| Feature | Primary Library | Backup/Alternative | Priority |
|---------|----------------|-------------------|----------|
| **Exchange Integration** | ccxt | python-binance (Binance-specific) | 🔴 Critical |
| **Technical Indicators** | pandas-ta | ta-lib | 🔴 Critical |
| **Data Validation** | pydantic | marshmallow | 🔴 Critical |
| **Database Driver** | asyncpg | SQLAlchemy (ORM) | 🔴 Critical |
| **Web Framework** | FastAPI | Flask | 🔴 Critical |
| **Task Queue** | Celery | RQ, Dramatiq | 🔴 Critical |
| **HTTP Client** | httpx | aiohttp | 🟡 High |
| **Logging** | loguru | structlog | 🟢 Medium |
| **Retry Logic** | tenacity | backoff | 🟢 Medium |
| **Environment Vars** | python-dotenv | environs | 🟢 Medium |
| **Testing** | pytest | unittest | 🔴 Critical |

---

## 12. Installation & Setup

### 12.1 requirements.txt

```txt
# Core dependencies
ccxt==4.4.14
pandas==2.2.3
pandas-ta==0.3.14b0
pydantic==2.10.0
pydantic-settings==2.6.1
asyncpg==0.30.0
fastapi==0.115.5
uvicorn[standard]==0.32.1
celery[redis]==5.4.0
redis==5.2.0

# HTTP clients
httpx==0.27.2
aiohttp==3.11.0

# Utilities
python-dotenv==1.0.1
loguru==0.7.3
tenacity==9.0.0

# Testing
pytest==8.3.3
pytest-asyncio==0.24.0
pytest-cov==6.0.0
pytest-mock==3.14.0

# Optional
TA-Lib==0.4.32  # Requires system library
```

### 12.2 pyproject.toml (Alternative)

```toml
[tool.poetry]
name = "llm-crypto-trading"
version = "0.1.0"
description = "LLM-Powered Cryptocurrency Trading System"
authors = ["Your Name <you@example.com>"]

[tool.poetry.dependencies]
python = "^3.11"
ccxt = "^4.4"
pandas = "^2.2"
pandas-ta = "^0.3"
pydantic = "^2.10"
pydantic-settings = "^2.6"
asyncpg = "^0.30"
fastapi = "^0.115"
uvicorn = {extras = ["standard"], version = "^0.32"}
celery = {extras = ["redis"], version = "^5.4"}
httpx = "^0.27"
python-dotenv = "^1.0"
loguru = "^0.7"
tenacity = "^9.0"

[tool.poetry.group.dev.dependencies]
pytest = "^8.3"
pytest-asyncio = "^0.24"
pytest-cov = "^6.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

---

## 13. Conclusion

**Reusable Components Summary**:
- ✅ **Exchange**: ccxt (battle-tested, 103+ exchanges)
- ✅ **Indicators**: pandas-ta (130+ indicators, easy to use)
- ✅ **Validation**: pydantic (type-safe, FastAPI integration)
- ✅ **Database**: asyncpg (fastest, async-native)
- ✅ **Web**: FastAPI (modern, high-performance)
- ✅ **Tasks**: Celery (industry standard, reliable)

**Implementation Readiness**: 🟢 **GREEN LIGHT** - All components production-ready

**Next Steps**:
1. Set up project structure (see Section 9)
2. Install dependencies (see Section 12)
3. Implement core components using patterns from this document
4. Write tests for each component (see Section 10)

---

**End of Reusable Components Document**
