"""
Testnet Exchange Adapter

Provides unified interface for interacting with exchange testnets.
Built on top of ccxt library for standardized exchange access.

Author: Integration Specialist
Date: 2025-10-31
"""

import asyncio
import logging
from decimal import Decimal
from typing import Optional, Dict, Any, List
from datetime import datetime

import ccxt.async_support as ccxt
from ccxt.base.errors import (
    NetworkError,
    ExchangeError,
    RateLimitExceeded,
    InvalidOrder,
    InsufficientFunds,
)

from .testnet_config import TestnetConfig, ExchangeType, TestnetMode

logger = logging.getLogger(__name__)


class TestnetExchangeAdapter:
    """
    Unified adapter for testnet exchange connections

    Provides methods for:
    - Account balance queries
    - Order placement and management
    - Position tracking
    - Market data fetching
    """

    def __init__(self, config: TestnetConfig):
        """
        Initialize testnet exchange adapter

        Args:
            config: Testnet configuration instance
        """
        self.config = config
        self.exchange: Optional[ccxt.Exchange] = None
        self._initialized = False
        self._markets_loaded = False

        # Statistics tracking
        self.stats = {
            "orders_placed": 0,
            "orders_cancelled": 0,
            "orders_failed": 0,
            "total_volume": Decimal("0"),
            "connection_time": None,
        }

    async def initialize(self) -> None:
        """
        Initialize exchange connection

        Raises:
            ExchangeError: If initialization fails
        """
        try:
            logger.info(f"Initializing {self.config.exchange.value} adapter...")

            # Validate configuration
            self.config.validate()

            # Get exchange class
            exchange_class = getattr(ccxt, self.config.exchange.value)

            # Create exchange instance with options
            options = self.config.to_ccxt_options()
            self.exchange = exchange_class(options)

            # Set sandbox mode if testnet
            if self.config.mode == TestnetMode.TESTNET:
                self.exchange.set_sandbox_mode(True)
                logger.info(f"Sandbox mode enabled for {self.config.exchange.value}")

            # Load markets
            await self._load_markets()

            self._initialized = True
            self.stats["connection_time"] = datetime.utcnow()

            logger.info(
                f"Successfully initialized {self.config.exchange.value} "
                f"in {self.config.mode.value} mode"
            )

        except Exception as e:
            logger.error(f"Failed to initialize exchange: {e}")
            raise ExchangeError(f"Exchange initialization failed: {e}")

    async def _load_markets(self) -> None:
        """Load exchange markets with retry logic"""
        for attempt in range(self.config.max_retries):
            try:
                await self.exchange.load_markets()
                self._markets_loaded = True
                logger.info(f"Loaded {len(self.exchange.markets)} markets")
                return
            except RateLimitExceeded:
                wait_time = 2**attempt
                logger.warning(f"Rate limited, waiting {wait_time}s...")
                await asyncio.sleep(wait_time)
            except NetworkError as e:
                if attempt < self.config.max_retries - 1:
                    logger.warning(
                        f"Network error loading markets (attempt {attempt + 1}): {e}"
                    )
                    await asyncio.sleep(1)
                else:
                    raise

    def _ensure_initialized(self) -> None:
        """Ensure exchange is initialized before operations"""
        if not self._initialized or not self.exchange:
            raise RuntimeError("Exchange not initialized. Call initialize() first.")

    async def get_balance(self) -> Dict[str, Any]:
        """
        Get account balance

        Returns:
            Dictionary with 'free', 'used', and 'total' balances

        Raises:
            ExchangeError: If balance fetch fails
        """
        self._ensure_initialized()

        try:
            balance = await self.exchange.fetch_balance()

            # Filter out zero balances for cleaner output
            filtered_balance = {
                "free": {k: v for k, v in balance["free"].items() if v > 0},
                "used": {k: v for k, v in balance["used"].items() if v > 0},
                "total": {k: v for k, v in balance["total"].items() if v > 0},
                "info": balance.get("info", {}),
            }

            logger.debug(
                f"Fetched balance: {len(filtered_balance['total'])} currencies"
            )
            return filtered_balance

        except Exception as e:
            logger.error(f"Failed to fetch balance: {e}")
            raise ExchangeError(f"Balance fetch failed: {e}")

    async def place_order(
        self,
        symbol: str,
        side: str,  # 'buy' or 'sell'
        order_type: str,  # 'market', 'limit', 'stop_loss'
        amount: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Place an order on the exchange

        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            side: Order side ('buy' or 'sell')
            order_type: Order type ('market', 'limit', 'stop_loss')
            amount: Order amount
            price: Limit price (required for limit orders)
            stop_price: Stop price (for stop orders)
            params: Additional exchange-specific parameters

        Returns:
            Order details dictionary

        Raises:
            InvalidOrder: If order parameters are invalid
            InsufficientFunds: If insufficient balance
            ExchangeError: If order placement fails
        """
        self._ensure_initialized()

        try:
            logger.info(
                f"Placing {order_type} {side} order: {amount} {symbol} "
                f"@ {price if price else 'market'}"
            )

            # Place order based on type
            if order_type == "market":
                order = await self.exchange.create_market_order(
                    symbol, side, amount, params
                )
            elif order_type == "limit":
                if price is None:
                    raise InvalidOrder("Price required for limit orders")
                order = await self.exchange.create_limit_order(
                    symbol, side, amount, price, params
                )
            elif order_type == "stop_loss":
                if not stop_price:
                    raise InvalidOrder("Stop price required for stop-loss orders")

                # Different exchanges have different stop-loss implementations
                if self.config.exchange == ExchangeType.BINANCE:
                    params = params or {}
                    params["stopPrice"] = stop_price
                    order = await self.exchange.create_order(
                        symbol, "stop_loss_limit", side, amount, price, params
                    )
                else:
                    # Generic stop-loss
                    order = await self.exchange.create_stop_order(
                        symbol, side, amount, stop_price, params
                    )
            else:
                raise InvalidOrder(f"Unsupported order type: {order_type}")

            # Update statistics
            self.stats["orders_placed"] += 1
            self.stats["total_volume"] += Decimal(str(amount))

            # Format response
            return {
                "id": order["id"],
                "symbol": order["symbol"],
                "side": order["side"],
                "type": order["type"],
                "amount": order["amount"],
                "price": order.get("price"),
                "status": order["status"],
                "timestamp": order["timestamp"],
                "datetime": order["datetime"],
                "info": order.get("info", {}),
            }

        except (InvalidOrder, InsufficientFunds) as e:
            self.stats["orders_failed"] += 1
            logger.error(f"Order rejected: {e}")
            raise
        except Exception as e:
            self.stats["orders_failed"] += 1
            logger.error(f"Order placement failed: {e}")
            raise ExchangeError(f"Failed to place order: {e}")

    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """
        Cancel an order

        Args:
            order_id: Order ID to cancel
            symbol: Trading pair

        Returns:
            True if cancellation successful

        Raises:
            ExchangeError: If cancellation fails
        """
        self._ensure_initialized()

        try:
            logger.info(f"Cancelling order {order_id} for {symbol}")

            await self.exchange.cancel_order(order_id, symbol)

            self.stats["orders_cancelled"] += 1
            logger.info(f"Successfully cancelled order {order_id}")

            return True

        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            raise ExchangeError(f"Order cancellation failed: {e}")

    async def get_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """
        Get order details

        Args:
            order_id: Order ID
            symbol: Trading pair

        Returns:
            Order details dictionary

        Raises:
            ExchangeError: If order fetch fails
        """
        self._ensure_initialized()

        try:
            order = await self.exchange.fetch_order(order_id, symbol)

            return {
                "id": order["id"],
                "symbol": order["symbol"],
                "side": order["side"],
                "type": order["type"],
                "amount": order["amount"],
                "filled": order["filled"],
                "remaining": order["remaining"],
                "price": order.get("price"),
                "average": order.get("average"),
                "status": order["status"],
                "timestamp": order["timestamp"],
            }

        except Exception as e:
            logger.error(f"Failed to fetch order {order_id}: {e}")
            raise ExchangeError(f"Order fetch failed: {e}")

    async def get_open_orders(
        self, symbol: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all open orders

        Args:
            symbol: Optional symbol filter

        Returns:
            List of open orders

        Raises:
            ExchangeError: If fetch fails
        """
        self._ensure_initialized()

        try:
            orders = await self.exchange.fetch_open_orders(symbol)

            return [
                {
                    "id": order["id"],
                    "symbol": order["symbol"],
                    "side": order["side"],
                    "type": order["type"],
                    "amount": order["amount"],
                    "price": order.get("price"),
                    "timestamp": order["timestamp"],
                }
                for order in orders
            ]

        except Exception as e:
            logger.error(f"Failed to fetch open orders: {e}")
            raise ExchangeError(f"Open orders fetch failed: {e}")

    async def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get current positions

        For spot trading, positions are non-zero balances.
        For futures, this would fetch actual positions.

        Returns:
            List of position dictionaries

        Raises:
            ExchangeError: If fetch fails
        """
        self._ensure_initialized()

        try:
            # For spot trading, positions are balances
            if self.exchange.has["fetchPositions"]:
                # Futures/derivatives
                positions = await self.exchange.fetch_positions()
                return positions
            else:
                # Spot trading - use balances as positions
                balance = await self.get_balance()
                positions = []

                for currency, amount in balance["total"].items():
                    if amount > 0 and currency != "USDT":
                        # Create position-like structure
                        positions.append(
                            {
                                "symbol": f"{currency}/USDT",
                                "amount": amount,
                                "side": "long",  # Spot is always long
                                "type": "spot",
                            }
                        )

                return positions

        except Exception as e:
            logger.error(f"Failed to fetch positions: {e}")
            raise ExchangeError(f"Position fetch failed: {e}")

    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get ticker data for a symbol

        Args:
            symbol: Trading pair

        Returns:
            Ticker data dictionary

        Raises:
            ExchangeError: If fetch fails
        """
        self._ensure_initialized()

        try:
            ticker = await self.exchange.fetch_ticker(symbol)

            return {
                "symbol": ticker["symbol"],
                "last": ticker["last"],
                "bid": ticker["bid"],
                "ask": ticker["ask"],
                "high": ticker["high"],
                "low": ticker["low"],
                "volume": ticker["baseVolume"],
                "timestamp": ticker["timestamp"],
            }

        except Exception as e:
            logger.error(f"Failed to fetch ticker for {symbol}: {e}")
            raise ExchangeError(f"Ticker fetch failed: {e}")

    async def get_order_book(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """
        Get order book for a symbol

        Args:
            symbol: Trading pair
            limit: Number of levels to fetch

        Returns:
            Order book dictionary with 'bids' and 'asks'

        Raises:
            ExchangeError: If fetch fails
        """
        self._ensure_initialized()

        try:
            order_book = await self.exchange.fetch_order_book(symbol, limit)

            return {
                "symbol": symbol,
                "bids": order_book["bids"][:limit],
                "asks": order_book["asks"][:limit],
                "timestamp": order_book["timestamp"],
            }

        except Exception as e:
            logger.error(f"Failed to fetch order book for {symbol}: {e}")
            raise ExchangeError(f"Order book fetch failed: {e}")

    async def close(self) -> None:
        """Close exchange connection and cleanup"""
        if self.exchange:
            try:
                await self.exchange.close()
                logger.info(f"Closed {self.config.exchange.value} connection")
            except Exception as e:
                logger.error(f"Error closing exchange: {e}")
            finally:
                self.exchange = None
                self._initialized = False
                self._markets_loaded = False

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get adapter statistics

        Returns:
            Dictionary of usage statistics
        """
        return {
            "exchange": self.config.exchange.value,
            "mode": self.config.mode.value,
            "connected": self._initialized,
            "markets_loaded": self._markets_loaded,
            "orders_placed": self.stats["orders_placed"],
            "orders_cancelled": self.stats["orders_cancelled"],
            "orders_failed": self.stats["orders_failed"],
            "total_volume": str(self.stats["total_volume"]),
            "connection_time": self.stats["connection_time"].isoformat()
            if self.stats["connection_time"]
            else None,
        }

    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
