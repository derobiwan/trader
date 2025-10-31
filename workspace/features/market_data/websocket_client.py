"""
Bybit WebSocket Client

Real-time market data streaming via Bybit WebSocket API.
Handles ticker and kline (candle) subscriptions for all trading symbols.

Author: Market Data Service Implementation Team
Date: 2025-10-27
"""

import asyncio
import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional

import websockets
from websockets.client import ClientProtocol

from .models import OHLCV, Ticker, Timeframe

logger = logging.getLogger(__name__)


class BybitWebSocketClient:
    """
    Bybit WebSocket Client for real-time market data

    Connects to Bybit WebSocket API and streams real-time data:
    - Ticker data (bid, ask, last price, 24h stats)
    - Kline/Candle data (OHLCV for various timeframes)

    Attributes:
        symbols: List of trading pairs to subscribe to
        testnet: Whether to use testnet
        on_ticker: Callback for ticker updates
        on_kline: Callback for kline updates
        on_error: Callback for errors
    """

    # WebSocket URLs
    MAINNET_PUBLIC_URL = "wss://stream.bybit.com/v5/public/linear"
    TESTNET_PUBLIC_URL = "wss://stream-testnet.bybit.com/v5/public/linear"

    def __init__(
        self,
        symbols: List[str],
        timeframes: Optional[List[Timeframe]] = None,
        testnet: bool = True,
        on_ticker: Optional[Callable[[Ticker], None]] = None,
        on_kline: Optional[Callable[[OHLCV], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
        ping_interval: int = 20,
    ):
        """
        Initialize Bybit WebSocket Client

        Args:
            symbols: List of trading pairs (e.g., ['BTCUSDT', 'ETHUSDT'])
            timeframes: List of timeframes to subscribe to (default: ['3m'])
            testnet: Use testnet WebSocket (default: True)
            on_ticker: Callback for ticker updates
            on_kline: Callback for kline updates
            on_error: Callback for errors
            ping_interval: Ping interval in seconds (default: 20)

        Example:
            ```python
            client = BybitWebSocketClient(
                symbols=['BTCUSDT', 'ETHUSDT'],
                timeframes=[Timeframe.M3],
                on_ticker=handle_ticker,
                on_kline=handle_kline,
            )
            await client.connect()
            ```
        """
        self.symbols = symbols
        self.timeframes = timeframes or [Timeframe.M3]
        self.testnet = testnet
        self.on_ticker = on_ticker
        self.on_kline = on_kline
        self.on_error = on_error
        self.ping_interval = ping_interval

        # WebSocket connection
        self.ws: Optional[ClientProtocol] = None
        self.running = False

        # Subscription tracking
        self.subscribed_channels: list[str] = []

        # Connection state
        self.url = self.TESTNET_PUBLIC_URL if testnet else self.MAINNET_PUBLIC_URL
        self.reconnect_delay = 5
        self.max_reconnect_delay = 60

    async def connect(self):
        """
        Connect to Bybit WebSocket and start receiving data

        Handles automatic reconnection on disconnect.
        """
        self.running = True
        reconnect_delay = self.reconnect_delay

        while self.running:
            try:
                logger.info(f"Connecting to Bybit WebSocket: {self.url}")

                async with websockets.connect(
                    self.url,
                    ping_interval=self.ping_interval,
                    ping_timeout=10,
                ) as websocket:
                    self.ws = websocket
                    logger.info("WebSocket connected successfully")

                    # Reset reconnect delay on successful connection
                    reconnect_delay = self.reconnect_delay

                    # Subscribe to channels
                    await self._subscribe_to_channels()

                    # Start receiving messages
                    await self._receive_messages()

            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(f"WebSocket connection closed: {e}")
                if self.running:
                    logger.info(f"Reconnecting in {reconnect_delay}s...")
                    await asyncio.sleep(reconnect_delay)
                    # Exponential backoff
                    reconnect_delay = min(reconnect_delay * 2, self.max_reconnect_delay)

            except Exception as e:
                logger.error(f"WebSocket error: {e}", exc_info=True)
                if self.on_error:
                    try:
                        self.on_error(e)
                    except Exception as callback_error:
                        logger.error(f"Error callback failed: {callback_error}")

                if self.running:
                    await asyncio.sleep(reconnect_delay)
                    reconnect_delay = min(reconnect_delay * 2, self.max_reconnect_delay)

    async def disconnect(self):
        """Disconnect from WebSocket"""
        logger.info("Disconnecting from Bybit WebSocket")
        self.running = False
        if self.ws:
            await self.ws.close()
            self.ws = None

    async def _subscribe_to_channels(self):
        """Subscribe to ticker and kline channels for all symbols"""
        channels = []

        # Subscribe to ticker for each symbol
        for symbol in self.symbols:
            channels.append(f"tickers.{symbol}")

        # Subscribe to kline for each symbol and timeframe
        for symbol in self.symbols:
            for timeframe in self.timeframes:
                # Convert timeframe to Bybit format
                bybit_interval = self._convert_timeframe(timeframe)
                channels.append(f"kline.{bybit_interval}.{symbol}")

        # Send subscription request
        subscribe_message = {"op": "subscribe", "args": channels}

        logger.info(f"Subscribing to channels: {channels}")
        await self.ws.send(json.dumps(subscribe_message))

        self.subscribed_channels = channels

    def _convert_timeframe(self, timeframe: Timeframe) -> str:
        """Convert Timeframe enum to Bybit interval string"""
        mapping = {
            Timeframe.M1: "1",
            Timeframe.M3: "3",
            Timeframe.M5: "5",
            Timeframe.M15: "15",
            Timeframe.M30: "30",
            Timeframe.H1: "60",
            Timeframe.H4: "240",
            Timeframe.D1: "D",
        }
        return mapping.get(timeframe, "3")

    async def _receive_messages(self):
        """Receive and process WebSocket messages"""
        async for message in self.ws:
            try:
                data = json.loads(message)

                # Handle different message types
                if "topic" in data:
                    await self._handle_topic_message(data)
                elif "op" in data:
                    await self._handle_operation_message(data)

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse WebSocket message: {e}")
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}", exc_info=True)

    async def _handle_topic_message(self, data: Dict[str, Any]):
        """Handle topic-based messages (ticker, kline)"""
        topic = data.get("topic", "")

        if topic.startswith("tickers."):
            await self._handle_ticker_message(data)
        elif topic.startswith("kline."):
            await self._handle_kline_message(data)
        else:
            logger.debug(f"Unhandled topic: {topic}")

    async def _handle_operation_message(self, data: Dict[str, Any]):
        """Handle operation messages (subscribe, pong, etc.)"""
        op = data.get("op")

        if op == "subscribe":
            success = data.get("success", False)
            if success:
                logger.info("Subscription successful")
            else:
                logger.error(f"Subscription failed: {data.get('ret_msg')}")

        elif op == "pong":
            logger.debug("Received pong")

    async def _handle_ticker_message(self, data: Dict[str, Any]):
        """
        Handle ticker message

        Example Bybit ticker message:
        {
            "topic": "tickers.BTCUSDT",
            "type": "snapshot",
            "data": {
                "symbol": "BTCUSDT",
                "lastPrice": "90000.00",
                "bid1Price": "89999.50",
                "ask1Price": "90000.50",
                "highPrice24h": "91000.00",
                "lowPrice24h": "89000.00",
                "volume24h": "1234.567",
                "turnover24h": "111111111.11",
                "price24hPcnt": "0.0111"
            },
            "ts": 1698765432000
        }
        """
        try:
            topic = data.get("topic", "")
            symbol = topic.split(".")[-1]
            ticker_data = data.get("data", {})

            # Parse ticker data
            ticker = Ticker(
                symbol=self._format_symbol(symbol),
                timestamp=datetime.fromtimestamp(data.get("ts", 0) / 1000),
                bid=Decimal(str(ticker_data.get("bid1Price", 0))),
                ask=Decimal(str(ticker_data.get("ask1Price", 0))),
                last=Decimal(str(ticker_data.get("lastPrice", 0))),
                high_24h=Decimal(str(ticker_data.get("highPrice24h", 0))),
                low_24h=Decimal(str(ticker_data.get("lowPrice24h", 0))),
                volume_24h=Decimal(str(ticker_data.get("volume24h", 0))),
                change_24h=Decimal("0"),  # Will calculate
                change_24h_pct=Decimal(str(ticker_data.get("price24hPcnt", 0)))
                * Decimal("100"),
            )

            # Calculate 24h change
            ticker.change_24h = ticker.last - (
                ticker.last / (Decimal("1") + (ticker.change_24h_pct / Decimal("100")))
            )

            # Invoke callback
            if self.on_ticker:
                try:
                    if asyncio.iscoroutinefunction(self.on_ticker):
                        await self.on_ticker(ticker)
                    else:
                        self.on_ticker(ticker)
                except Exception as e:
                    logger.error(f"Error in ticker callback: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Error handling ticker message: {e}", exc_info=True)

    async def _handle_kline_message(self, data: Dict[str, Any]):
        """
        Handle kline (OHLCV) message

        Example Bybit kline message:
        {
            "topic": "kline.3.BTCUSDT",
            "type": "snapshot",
            "data": [{
                "start": 1698765000000,
                "end": 1698765180000,
                "interval": "3",
                "open": "90000.00",
                "close": "90100.00",
                "high": "90200.00",
                "low": "89900.00",
                "volume": "12.345",
                "turnover": "1111111.11",
                "confirm": false
            }],
            "ts": 1698765432000
        }
        """
        try:
            topic = data.get("topic", "")
            parts = topic.split(".")
            interval = parts[1]
            symbol = parts[2]

            kline_list = data.get("data", [])

            for kline_data in kline_list:
                # Parse kline data
                timeframe = self._parse_interval(interval)

                ohlcv = OHLCV(
                    symbol=self._format_symbol(symbol),
                    timeframe=timeframe,
                    timestamp=datetime.fromtimestamp(kline_data.get("start", 0) / 1000),
                    open=Decimal(str(kline_data.get("open", 0))),
                    high=Decimal(str(kline_data.get("high", 0))),
                    low=Decimal(str(kline_data.get("low", 0))),
                    close=Decimal(str(kline_data.get("close", 0))),
                    volume=Decimal(str(kline_data.get("volume", 0))),
                    quote_volume=Decimal(str(kline_data.get("turnover", 0))),
                )

                # Invoke callback
                if self.on_kline:
                    try:
                        if asyncio.iscoroutinefunction(self.on_kline):
                            await self.on_kline(ohlcv)
                        else:
                            self.on_kline(ohlcv)
                    except Exception as e:
                        logger.error(f"Error in kline callback: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Error handling kline message: {e}", exc_info=True)

    def _format_symbol(self, symbol: str) -> str:
        """
        Format symbol to standard format

        Bybit: 'BTCUSDT'
        Standard: 'BTC/USDT:USDT'
        """
        # For perpetual futures
        if symbol.endswith("USDT"):
            base = symbol[:-4]
            return f"{base}/USDT:USDT"
        return symbol

    def _parse_interval(self, interval: str) -> Timeframe:
        """Parse Bybit interval to Timeframe enum"""
        mapping = {
            "1": Timeframe.M1,
            "3": Timeframe.M3,
            "5": Timeframe.M5,
            "15": Timeframe.M15,
            "30": Timeframe.M30,
            "60": Timeframe.H1,
            "240": Timeframe.H4,
            "D": Timeframe.D1,
        }
        return mapping.get(interval, Timeframe.M3)


# Export
__all__ = ["BybitWebSocketClient"]
