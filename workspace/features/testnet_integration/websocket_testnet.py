"""
Testnet WebSocket Client

Provides WebSocket connectivity for real-time market data from testnets.
Supports automatic reconnection and message routing.

Author: Integration Specialist
Date: 2025-10-31
"""

import asyncio
import json
import logging
from typing import Optional, Callable, Dict, Any, Set
from datetime import datetime
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from .testnet_config import TestnetConfig, ExchangeType

logger = logging.getLogger(__name__)


class TestnetWebSocketClient:
    """
    WebSocket client for testnet real-time data streams

    Features:
    - Automatic reconnection with exponential backoff
    - Multiple stream subscriptions
    - Message routing to callbacks
    - Health monitoring
    """

    def __init__(self, config: TestnetConfig):
        """
        Initialize WebSocket client

        Args:
            config: Testnet configuration
        """
        self.config = config
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.running = False
        self.callbacks: Dict[str, Callable] = {}
        self.subscriptions: Set[str] = set()

        # Connection management
        self._reconnect_count = 0
        self._max_reconnect_attempts = 5
        self._message_count = 0
        self._last_message_time: Optional[datetime] = None

        # Tasks
        self._message_handler_task: Optional[asyncio.Task] = None
        self._ping_task: Optional[asyncio.Task] = None

    def _get_ws_url(self) -> str:
        """Get WebSocket URL based on configuration"""
        return self.config.get_ws_url()

    async def connect(self) -> None:
        """
        Connect to WebSocket server

        Raises:
            WebSocketException: If connection fails after max attempts
        """
        url = self._get_ws_url()
        logger.info(f"Connecting to {self.config.exchange.value} WebSocket at {url}")

        try:
            self.ws = await websockets.connect(
                url,
                ping_interval=self.config.websocket_ping_interval,
                ping_timeout=10,
            )

            self.running = True
            self._reconnect_count = 0

            # Start background tasks
            self._message_handler_task = asyncio.create_task(self._handle_messages())
            self._ping_task = asyncio.create_task(self._ping_loop())

            logger.info(
                f"Successfully connected to {self.config.exchange.value} WebSocket"
            )

            # Resubscribe to existing streams
            if self.subscriptions:
                logger.info(f"Resubscribing to {len(self.subscriptions)} streams")
                for stream in self.subscriptions:
                    await self._send_subscribe(stream)

        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            raise WebSocketException(f"Failed to connect: {e}")

    async def _handle_messages(self) -> None:
        """Handle incoming WebSocket messages"""
        while self.running and self.ws:
            try:
                message = await self.ws.recv()
                self._message_count += 1
                self._last_message_time = datetime.utcnow()

                # Parse message
                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse message: {message[:100]}")
                    continue

                # Route message to callback
                await self._route_message(data)

            except ConnectionClosed:
                logger.warning("WebSocket connection closed")
                if self.running:
                    await self._reconnect()
                break
            except Exception as e:
                logger.error(f"Error handling message: {e}")

    async def _route_message(self, data: Dict[str, Any]) -> None:
        """
        Route message to appropriate callback

        Args:
            data: Parsed message data
        """
        try:
            # Binance message routing
            if self.config.exchange == ExchangeType.BINANCE:
                # Stream messages have 'stream' field
                if "stream" in data and "data" in data:
                    stream = data["stream"]
                    if stream in self.callbacks:
                        await self._execute_callback(
                            self.callbacks[stream], data["data"]
                        )

                # Direct messages (subscriptions, errors)
                elif "id" in data and "result" in data:
                    logger.debug(f"Subscription response: {data}")

                # Event messages
                elif "e" in data:
                    # Find matching stream by event type and symbol
                    event_type = data["e"]
                    symbol = data.get("s", "").lower()

                    # Try to match stream
                    for stream, callback in self.callbacks.items():
                        if symbol in stream and event_type in stream:
                            await self._execute_callback(callback, data)
                            break

            # Bybit message routing
            elif self.config.exchange == ExchangeType.BYBIT:
                # Bybit uses 'topic' field
                if "topic" in data:
                    topic = data["topic"]
                    if topic in self.callbacks:
                        await self._execute_callback(
                            self.callbacks[topic], data.get("data", data)
                        )

        except Exception as e:
            logger.error(f"Error routing message: {e}")

    async def _execute_callback(self, callback: Callable, data: Any) -> None:
        """
        Execute callback safely

        Args:
            callback: Callback function
            data: Data to pass to callback
        """
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(data)
            else:
                callback(data)
        except Exception as e:
            logger.error(f"Callback execution failed: {e}")

    async def _reconnect(self) -> None:
        """Reconnect with exponential backoff"""
        if self._reconnect_count >= self._max_reconnect_attempts:
            logger.error(
                f"Max reconnection attempts ({self._max_reconnect_attempts}) reached"
            )
            self.running = False
            return

        self._reconnect_count += 1
        wait_time = min(2**self._reconnect_count, 30)  # Max 30 seconds

        logger.info(
            f"Reconnecting in {wait_time}s (attempt {self._reconnect_count})..."
        )
        await asyncio.sleep(wait_time)

        try:
            await self.connect()
        except Exception as e:
            logger.error(f"Reconnection attempt {self._reconnect_count} failed: {e}")
            if self.running:
                await self._reconnect()

    async def _ping_loop(self) -> None:
        """Send periodic pings to keep connection alive"""
        while self.running and self.ws:
            try:
                await asyncio.sleep(self.config.websocket_ping_interval)

                if self.ws and not self.ws.closed:
                    # Send ping based on exchange
                    if self.config.exchange == ExchangeType.BINANCE:
                        pong = await self.ws.ping()
                        await asyncio.wait_for(pong, timeout=10)
                    elif self.config.exchange == ExchangeType.BYBIT:
                        await self.ws.send(json.dumps({"op": "ping"}))

            except Exception as e:
                logger.warning(f"Ping failed: {e}")

    async def subscribe_ticker(self, symbol: str, callback: Callable) -> None:
        """
        Subscribe to ticker updates

        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            callback: Callback function for ticker data
        """
        stream = self._format_stream_name(symbol.lower(), "ticker")
        self.callbacks[stream] = callback
        self.subscriptions.add(stream)

        if self.ws and not self.ws.closed:
            await self._send_subscribe(stream)

        logger.info(f"Subscribed to ticker stream: {stream}")

    async def subscribe_kline(
        self, symbol: str, interval: str, callback: Callable
    ) -> None:
        """
        Subscribe to kline/candlestick updates

        Args:
            symbol: Trading symbol
            interval: Kline interval (e.g., '1m', '5m', '1h')
            callback: Callback function for kline data
        """
        stream = self._format_stream_name(symbol.lower(), f"kline_{interval}")
        self.callbacks[stream] = callback
        self.subscriptions.add(stream)

        if self.ws and not self.ws.closed:
            await self._send_subscribe(stream)

        logger.info(f"Subscribed to kline stream: {stream}")

    async def subscribe_depth(self, symbol: str, callback: Callable) -> None:
        """
        Subscribe to order book depth updates

        Args:
            symbol: Trading symbol
            callback: Callback function for depth data
        """
        stream = self._format_stream_name(symbol.lower(), "depth")
        self.callbacks[stream] = callback
        self.subscriptions.add(stream)

        if self.ws and not self.ws.closed:
            await self._send_subscribe(stream)

        logger.info(f"Subscribed to depth stream: {stream}")

    def _format_stream_name(self, symbol: str, stream_type: str) -> str:
        """
        Format stream name based on exchange

        Args:
            symbol: Trading symbol
            stream_type: Type of stream

        Returns:
            Formatted stream name
        """
        if self.config.exchange == ExchangeType.BINANCE:
            return f"{symbol}@{stream_type}"
        elif self.config.exchange == ExchangeType.BYBIT:
            return f"{stream_type}.{symbol}"
        else:
            return f"{symbol}_{stream_type}"

    async def _send_subscribe(self, stream: str) -> None:
        """
        Send subscription message

        Args:
            stream: Stream name to subscribe
        """
        if not self.ws or self.ws.closed:
            logger.warning(f"Cannot subscribe to {stream}: WebSocket not connected")
            return

        try:
            if self.config.exchange == ExchangeType.BINANCE:
                msg = {
                    "method": "SUBSCRIBE",
                    "params": [stream],
                    "id": self._message_count,
                }
            elif self.config.exchange == ExchangeType.BYBIT:
                msg = {
                    "op": "subscribe",
                    "args": [stream],
                }
            else:
                logger.warning(
                    f"Unsupported exchange for subscription: {self.config.exchange}"
                )
                return

            await self.ws.send(json.dumps(msg))
            logger.debug(f"Sent subscription for {stream}")

        except Exception as e:
            logger.error(f"Failed to subscribe to {stream}: {e}")

    async def unsubscribe(self, stream: str) -> None:
        """
        Unsubscribe from a stream

        Args:
            stream: Stream name to unsubscribe
        """
        if stream in self.callbacks:
            del self.callbacks[stream]
            self.subscriptions.discard(stream)

            if self.ws and not self.ws.closed:
                await self._send_unsubscribe(stream)

            logger.info(f"Unsubscribed from {stream}")

    async def _send_unsubscribe(self, stream: str) -> None:
        """
        Send unsubscribe message

        Args:
            stream: Stream name to unsubscribe
        """
        if not self.ws or self.ws.closed:
            return

        try:
            if self.config.exchange == ExchangeType.BINANCE:
                msg = {
                    "method": "UNSUBSCRIBE",
                    "params": [stream],
                    "id": self._message_count,
                }
            elif self.config.exchange == ExchangeType.BYBIT:
                msg = {
                    "op": "unsubscribe",
                    "args": [stream],
                }
            else:
                return

            await self.ws.send(json.dumps(msg))

        except Exception as e:
            logger.error(f"Failed to unsubscribe from {stream}: {e}")

    async def close(self) -> None:
        """Close WebSocket connection and cleanup"""
        logger.info("Closing WebSocket connection...")
        self.running = False

        # Cancel background tasks
        if self._message_handler_task:
            self._message_handler_task.cancel()
        if self._ping_task:
            self._ping_task.cancel()

        # Close WebSocket
        if self.ws and not self.ws.closed:
            await self.ws.close()
            self.ws = None

        logger.info("WebSocket connection closed")

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get client statistics

        Returns:
            Dictionary of statistics
        """
        return {
            "connected": self.ws is not None and not self.ws.closed,
            "running": self.running,
            "subscriptions": list(self.subscriptions),
            "message_count": self._message_count,
            "last_message_time": self._last_message_time.isoformat()
            if self._last_message_time
            else None,
            "reconnect_count": self._reconnect_count,
        }

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
