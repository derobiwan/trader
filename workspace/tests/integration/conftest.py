"""
Integration Test Fixtures

Shared fixtures for integration testing.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def sample_ohlcv_data() -> pd.DataFrame:
    """Generate sample OHLCV data for testing"""
    periods = 100
    dates = [
        datetime.now(timezone.utc) - timedelta(minutes=3 * i) for i in range(periods)
    ]
    dates.reverse()

    # Generate realistic-looking price data
    base_price = 50000
    prices: list[int] = [base_price]
    for _ in range(periods - 1):
        change = np.random.normal(0, 100)
        prices.append(int(prices[-1] + change))

    data = {
        "timestamp": dates,
        "open": prices,
        "high": [p * (1 + abs(np.random.normal(0, 0.002))) for p in prices],
        "low": [p * (1 - abs(np.random.normal(0, 0.002))) for p in prices],
        "close": [p + np.random.normal(0, 50) for p in prices],
        "volume": [np.random.uniform(10, 100) for _ in range(periods)],
    }

    df = pd.DataFrame(data)
    df.set_index("timestamp", inplace=True)

    return df


@pytest.fixture
def sample_market_data() -> Dict[str, Any]:
    """Generate sample market data dictionary"""
    return {
        "symbol": "BTC/USDT:USDT",
        "timeframe": "3m",
        "current_price": Decimal("50000"),
        "ohlcv": None,  # Will be set in tests
    }


@pytest.fixture
def trading_config() -> Dict[str, Any]:
    """Generate trading configuration"""
    return {
        "starting_balance_chf": Decimal("2626.96"),
        "max_daily_loss_chf": Decimal("-183.89"),
        "max_concurrent_positions": 6,
        "max_position_size_pct": Decimal("0.20"),
        "max_total_exposure_pct": Decimal("0.80"),
        "min_confidence": Decimal("0.60"),
    }


@pytest.fixture
def mock_exchange_client():
    """Mock exchange client for testing"""

    class MockExchange:
        def __init__(self):
            self.orders = {}
            self.positions = {}
            self.balance = Decimal("2626.96")

        async def fetch_ticker(self, symbol: str):
            """Mock fetch ticker"""
            return {"last": 50000.0}

        async def create_order(
            self, symbol: str, type: str, side: str, amount: float, **params
        ):
            """Mock create order"""
            order_id = f"order_{len(self.orders) + 1}"
            order = {
                "id": order_id,
                "symbol": symbol,
                "type": type,
                "side": side,
                "amount": amount,
                "price": params.get("price", 50000.0),
                "status": "open",
            }
            self.orders[order_id] = order
            return order

        async def cancel_order(self, order_id: str, symbol: str):
            """Mock cancel order"""
            if order_id in self.orders:
                self.orders[order_id]["status"] = "canceled"
            return self.orders.get(order_id)

        async def fetch_balance(self):
            """Mock fetch balance"""
            return {
                "USDT": {
                    "free": float(self.balance),
                    "used": 0.0,
                    "total": float(self.balance),
                }
            }

    return MockExchange()


@pytest.fixture
def mock_trade_executor():
    """Mock trade executor for testing"""

    class MockTradeExecutor:
        def __init__(self):
            self.positions = []
            self.closed_positions = []

        async def execute_signal(self, signal):
            """Mock execute signal"""
            position = {
                "id": f"pos_{len(self.positions) + 1}",
                "symbol": signal.symbol,
                "entry_price": (
                    signal.entry_price
                    if hasattr(signal, "entry_price")
                    else Decimal("50000")
                ),
                "size_pct": signal.size_pct,
                "stop_loss_pct": signal.stop_loss_pct,
                "side": signal.decision.lower(),
            }
            self.positions.append(position)
            return position

        async def close_position(
            self, position_id: str, reason: Optional[str] = None, force: bool = False
        ):
            """Mock close position"""
            for i, pos in enumerate(self.positions):
                if pos["id"] == position_id:
                    closed = self.positions.pop(i)
                    self.closed_positions.append(closed)
                    return {"status": "closed", "position": closed}
            return None

        async def get_open_positions(self):
            """Mock get open positions"""
            return self.positions

    return MockTradeExecutor()


@pytest.fixture
def mock_position_tracker():
    """Mock position tracker for testing"""

    class MockPositionTracker:
        def __init__(self):
            self.positions = []

        async def get_open_positions(self):
            """Mock get open positions"""
            return self.positions

        async def get_position(self, position_id: str):
            """Mock get position"""
            for pos in self.positions:
                if pos.get("id") == position_id:
                    return pos
            return None

        async def update_position(self, position_id: str, updates: dict):
            """Mock update position"""
            for pos in self.positions:
                if pos.get("id") == position_id:
                    pos.update(updates)
                    return pos
            return None

    return MockPositionTracker()


# ============================================================================
# Market Data Snapshot Helpers
# ============================================================================


def create_ticker(last_price: Decimal = Decimal("50000.00")):
    """Create a ticker with required fields"""
    from workspace.features.market_data import Ticker

    return Ticker(
        symbol="BTC/USDT:USDT",
        timestamp=datetime.now(timezone.utc),
        bid=last_price - Decimal("50"),
        ask=last_price + Decimal("50"),
        last=last_price,
        high_24h=last_price * Decimal("1.02"),
        low_24h=last_price * Decimal("0.98"),
        volume_24h=Decimal("48000.0"),
        change_24h=Decimal("500.00"),
        change_24h_pct=Decimal("1.00"),
    )


def create_ohlcv(close_price: Decimal = Decimal("50000.00")):
    """Create OHLCV with required fields"""
    from workspace.features.market_data import OHLCV, Timeframe

    return OHLCV(
        symbol="BTC/USDT:USDT",
        timeframe=Timeframe.M3,
        timestamp=datetime.now(timezone.utc),
        open=close_price - Decimal("100"),
        high=close_price + Decimal("200"),
        low=close_price - Decimal("200"),
        close=close_price,
        volume=Decimal("100.0"),
    )


def create_rsi(value: Decimal = Decimal("50.0")):
    """Create RSI indicator with required fields"""
    from workspace.features.market_data import RSI, Timeframe

    return RSI(
        symbol="BTC/USDT:USDT",
        timeframe=Timeframe.M3,
        timestamp=datetime.now(timezone.utc),
        value=value,
    )


def create_macd(is_bullish: bool = True):
    """Create MACD indicator with required fields"""
    from workspace.features.market_data import MACD, Timeframe

    macd_val = Decimal("100.0") if is_bullish else Decimal("-100.0")
    signal_val = Decimal("50.0") if is_bullish else Decimal("-50.0")
    return MACD(
        symbol="BTC/USDT:USDT",
        timeframe=Timeframe.M3,
        timestamp=datetime.now(timezone.utc),
        macd_line=macd_val,
        signal_line=signal_val,
        histogram=macd_val - signal_val,
    )


def create_ema(value: Decimal, period: int):
    """Create EMA indicator with required fields"""
    from workspace.features.market_data import EMA, Timeframe

    return EMA(
        symbol="BTC/USDT:USDT",
        timeframe=Timeframe.M3,
        timestamp=datetime.now(timezone.utc),
        value=value,
        period=period,
    )


def create_bollinger_bands(upper: Decimal, middle: Decimal, lower: Decimal):
    """Create Bollinger Bands with required fields"""
    from workspace.features.market_data import BollingerBands, Timeframe

    return BollingerBands(
        symbol="BTC/USDT:USDT",
        timeframe=Timeframe.M3,
        timestamp=datetime.now(timezone.utc),
        upper_band=upper,
        middle_band=middle,
        lower_band=lower,
        bandwidth=upper - lower,
    )


def create_snapshot(
    price: Decimal = Decimal("50000.00"),
    rsi_value: Optional[Decimal] = None,
    is_bullish: bool = True,
):
    """Create a market data snapshot with optional indicators"""
    from workspace.features.market_data import MarketDataSnapshot, Timeframe

    return MarketDataSnapshot(
        symbol="BTC/USDT:USDT",
        timeframe=Timeframe.M3,
        timestamp=datetime.now(timezone.utc),
        ohlcv=create_ohlcv(price),
        ticker=create_ticker(price),
        rsi=create_rsi(rsi_value) if rsi_value else create_rsi(Decimal("50.0")),
        macd=create_macd(is_bullish),
        ema_fast=create_ema(price + Decimal("100"), 12),
        ema_slow=create_ema(price - Decimal("100"), 26),
        bollinger=create_bollinger_bands(
            price + Decimal("1000"),
            price,
            price - Decimal("1000"),
        ),
    )


@pytest.fixture
def market_snapshot_oversold():
    """Create market snapshot indicating oversold conditions (RSI < 30)"""
    return create_snapshot(
        price=Decimal("50000.00"),
        rsi_value=Decimal("25.0"),  # Oversold
        is_bullish=True,
    )


@pytest.fixture
def market_snapshot_overbought():
    """Create market snapshot indicating overbought conditions (RSI > 70)"""
    return create_snapshot(
        price=Decimal("50000.00"),
        rsi_value=Decimal("75.0"),  # Overbought
        is_bullish=False,
    )


@pytest.fixture
def market_snapshot_neutral():
    """Create market snapshot indicating neutral conditions"""
    return create_snapshot(
        price=Decimal("50000.00"),
        rsi_value=Decimal("50.0"),  # Neutral
        is_bullish=True,
    )
