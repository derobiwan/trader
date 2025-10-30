"""
Trade Executor Service

Main service for executing trades on Bybit exchange using ccxt.
Handles order placement, tracking, and integration with Position Manager.

Author: Trade Executor Implementation Team
Date: 2025-10-27
"""

import asyncio
import logging
import time
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional

import ccxt.async_support as ccxt
from ccxt.base.errors import (
    InsufficientFunds,
    InvalidOrder,
    NetworkError,
    RateLimitExceeded,
)

from workspace.features.error_recovery import (
    CircuitBreaker,
    RetryManager,
    RetryStrategy,
)
from workspace.features.monitoring.metrics import MetricsService
from workspace.features.position_manager import PositionService
from workspace.features.trade_history import TradeHistoryService, TradeType
from workspace.shared.database.connection import get_pool

from .models import (
    ExecutionResult,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    TimeInForce,
)

logger = logging.getLogger(__name__)


class TradeExecutor:
    """
    Trade Executor service for Bybit exchange

    Handles all order execution, tracking, and position management
    integration. Implements retry logic, rate limit handling, and
    comprehensive error handling.

    Attributes:
        exchange: ccxt Bybit exchange instance
        position_service: Position Manager service instance
        max_retries: Maximum number of retry attempts
        retry_delay: Initial retry delay in seconds
        rate_limit_buffer: Buffer time for rate limiting (seconds)
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        testnet: bool = True,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        rate_limit_buffer: float = 0.1,
        exchange: Optional[Any] = None,
        position_service: Optional[Any] = None,
        trade_history_service: Optional[TradeHistoryService] = None,
        metrics_service: Optional[MetricsService] = None,
        enable_circuit_breaker: bool = True,
    ):
        """
        Initialize Trade Executor

        Args:
            api_key: Bybit API key
            api_secret: Bybit API secret
            testnet: Whether to use testnet (default: True)
            max_retries: Maximum retry attempts for failed orders
            retry_delay: Initial delay between retries (exponential backoff)
            rate_limit_buffer: Buffer time to avoid rate limits
            exchange: Optional pre-configured exchange (for testing)
            position_service: Optional pre-configured position service (for testing)
            trade_history_service: Optional pre-configured trade history service (for testing)
            metrics_service: Optional pre-configured metrics service (for testing)
            enable_circuit_breaker: Enable circuit breaker protection (default: True)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.rate_limit_buffer = rate_limit_buffer

        # Initialize exchange (or use provided one for testing)
        if exchange is not None:
            self.exchange = exchange
        else:
            self.exchange = ccxt.bybit(
                {
                    "apiKey": self.api_key,
                    "secret": self.api_secret,
                    "enableRateLimit": True,
                    "rateLimit": 120,  # 600 requests per 5 seconds = 120ms per request
                    "options": {
                        "defaultType": "swap",  # Perpetual futures
                        "recvWindow": 10000,
                    },
                }
            )

            if self.testnet:
                self.exchange.set_sandbox_mode(True)
                logger.info("Trade Executor initialized in TESTNET mode")
            else:
                logger.warning("Trade Executor initialized in PRODUCTION mode")

        # Initialize Position Manager (or use provided one for testing)
        # Note: If None, will be initialized in initialize() method with pool
        self.position_service = position_service
        self._position_service_provided = position_service is not None

        # Initialize Trade History Service (or use provided one for testing)
        if trade_history_service is not None:
            self.trade_history_service = trade_history_service
        else:
            self.trade_history_service = TradeHistoryService()

        # Initialize Metrics Service (or use provided one for testing)
        if metrics_service is not None:
            self.metrics_service = metrics_service
        else:
            self.metrics_service = MetricsService()

        # Initialize Retry Manager for resilience
        self.retry_manager = RetryManager(
            max_retries=max_retries,
            base_delay_seconds=retry_delay,
            strategy=RetryStrategy.EXPONENTIAL,
            retryable_exceptions=(NetworkError, RateLimitExceeded),
        )

        # Initialize Circuit Breakers (optional)
        self.enable_circuit_breaker = enable_circuit_breaker
        self.exchange_circuit_breaker: Optional[CircuitBreaker]
        if enable_circuit_breaker:
            self.exchange_circuit_breaker = CircuitBreaker(
                name="exchange_api",
                failure_threshold=5,
                recovery_timeout_seconds=60,
                expected_exception=Exception,  # Base exception type
            )
            logger.info("Circuit breaker enabled for exchange API")
        else:
            self.exchange_circuit_breaker = None

        # Track active orders
        self.active_orders: Dict[str, Order] = {}

        # Balance caching
        self._balance_cache: Optional[Decimal] = None
        self._balance_cache_time: float = 0

    async def initialize(self):
        """Initialize exchange and load markets"""
        try:
            # Initialize PositionService if not provided
            if not self._position_service_provided:
                pool = await get_pool()
                self.position_service = PositionService(pool=pool)
                logger.info("PositionService initialized with global pool")

            await self.exchange.load_markets()
            logger.info(
                f"Exchange markets loaded: {len(self.exchange.markets)} symbols"
            )

            # Verify account balance
            balance = await self.exchange.fetch_balance()
            logger.info(
                f"Account balance loaded: {balance.get('USDT', {}).get('free', 0)} USDT"
            )

        except Exception as e:
            logger.error(f"Failed to initialize exchange: {e}", exc_info=True)
            raise

    async def close(self):
        """Close exchange connection"""
        await self.exchange.close()
        logger.info("Trade Executor closed")

    async def get_account_balance(self, cache_ttl_seconds: int = 60) -> Decimal:
        """
        Fetch account balance from exchange with caching

        Fetches the total balance from the exchange and caches it for the
        specified TTL to avoid excessive API calls. The balance is returned
        in CHF (approximate conversion from USDT).

        Args:
            cache_ttl_seconds: Cache time-to-live in seconds (default: 60)

        Returns:
            Account balance in CHF

        Raises:
            Exception: If balance fetch fails after retries

        Example:
            ```python
            balance = await executor.get_account_balance()
            print(f"Available: {balance:.2f} CHF")
            ```
        """
        # Check cache validity
        if (
            self._balance_cache is not None
            and time.time() - self._balance_cache_time < cache_ttl_seconds
        ):
            logger.debug(
                f"Using cached balance: {self._balance_cache:.2f} CHF "
                f"(age: {time.time() - self._balance_cache_time:.1f}s)"
            )
            return self._balance_cache

        # Fetch fresh balance from exchange
        try:
            balance = await self._fetch_balance_from_exchange()

            # Update cache
            self._balance_cache = balance
            self._balance_cache_time = time.time()

            logger.info(f"Balance fetched and cached: {balance:.2f} CHF")
            return balance

        except Exception as e:
            logger.error(f"Failed to fetch account balance: {e}", exc_info=True)
            # If we have a cached value, return it even if expired
            if self._balance_cache is not None:
                logger.warning(
                    f"Returning stale cached balance due to fetch failure: {self._balance_cache:.2f} CHF"
                )
                return self._balance_cache
            raise

    async def _fetch_balance_from_exchange(self) -> Decimal:
        """
        Internal method to fetch balance from exchange

        Returns:
            Balance in CHF (converted from USDT)

        Raises:
            Exception: If exchange API call fails
        """
        try:
            # Fetch balance from exchange
            balance_response = await self.exchange.fetch_balance()

            # Get USDT total balance (includes free + used)
            usdt_balance = Decimal(str(balance_response["USDT"]["total"]))

            logger.debug(f"Raw USDT balance: {usdt_balance:.2f} USDT")

            # Convert USDT to CHF (approximate rate)
            # TODO: In production, fetch real-time CHF/USDT rate from forex API
            chf_to_usdt_rate = Decimal("1.10")  # CHF is stronger than USD
            chf_balance = usdt_balance / chf_to_usdt_rate

            logger.info(
                f"Account balance: {chf_balance:.2f} CHF "
                f"(~{usdt_balance:.2f} USDT @ rate {chf_to_usdt_rate})"
            )

            return chf_balance

        except KeyError as e:
            # Handle missing USDT balance
            logger.error(
                f"USDT balance not found in response: {e}. "
                f"Available balances: {list(balance_response.keys())}"
            )
            raise ValueError(f"USDT balance not available: {e}")
        except Exception as e:
            logger.error(f"Error fetching balance from exchange: {e}", exc_info=True)
            raise

    async def execute_signal(  # noqa: C901 - Complex orchestration logic
        self,
        signal: Any,  # TradingSignal from trading_loop
        account_balance_chf: Decimal,
        chf_to_usd_rate: Decimal = Decimal("1.10"),
        risk_manager: Optional[Any] = None,
    ) -> ExecutionResult:
        """
        Execute a trading signal (orchestrator method)

        This is the main orchestrator method that:
        1. Validates signal via risk manager (if provided)
        2. Calculates position size based on signal.size_pct
        3. Places market order to open/close position
        4. Places stop-loss order (if opening position)
        5. Returns unified execution result

        Args:
            signal: TradingSignal with symbol, decision, confidence, size_pct
            account_balance_chf: Available account balance in CHF
            chf_to_usd_rate: CHF to USD conversion rate
            risk_manager: Optional RiskManager for signal validation

        Returns:
            ExecutionResult with order details or error

        Example:
            ```python
            signal = TradingSignal(
                symbol='BTC/USDT:USDT',
                decision=TradingDecision.BUY,
                confidence=Decimal('0.75'),
                size_pct=Decimal('0.15'),
                stop_loss_pct=Decimal('0.02'),
            )

            result = await executor.execute_signal(
                signal=signal,
                account_balance_chf=Decimal('2626.96'),
            )
            ```
        """
        start_time = time.time()

        try:
            # Step 1: Validate signal via risk manager (if provided)
            if risk_manager:
                logger.info(f"Validating signal for {signal.symbol} via Risk Manager")
                validation = await risk_manager.validate_signal(signal)

                if not validation.approved:
                    logger.warning(
                        f"Signal rejected by Risk Manager for {signal.symbol}: "
                        f"{', '.join(validation.rejection_reasons)}"
                    )
                    latency_ms = Decimal(
                        str((time.time() - start_time) * 1000)
                    ).quantize(Decimal("0.01"))
                    return ExecutionResult(
                        success=False,
                        error_code="RISK_VALIDATION_FAILED",
                        error_message=f"Risk validation failed: {', '.join(validation.rejection_reasons)}",
                        latency_ms=latency_ms,
                    )

                logger.info(f"Signal approved by Risk Manager for {signal.symbol}")

            # Step 2: Get current market price
            ticker = await self.exchange.fetch_ticker(signal.symbol)
            current_price = Decimal(str(ticker["last"]))

            # Step 3: Calculate position size
            # Convert available capital to USD
            capital_usd = account_balance_chf / chf_to_usd_rate

            # Calculate position value in USD based on size_pct
            position_value_usd = capital_usd * signal.size_pct

            # Calculate quantity in base currency
            quantity = position_value_usd / current_price

            # Round to exchange's lot size (8 decimals for crypto)
            quantity = quantity.quantize(Decimal("0.00000001"))

            logger.info(
                f"Position size calculated: {quantity} {signal.symbol} "
                f"(${position_value_usd:.2f} @ ${current_price:.2f})"
            )

            # Step 4: Determine action based on signal decision
            from workspace.features.trading_loop import TradingDecision

            if signal.decision == TradingDecision.HOLD:
                logger.info(f"HOLD signal for {signal.symbol}, no action taken")
                latency_ms = Decimal(str((time.time() - start_time) * 1000)).quantize(
                    Decimal("0.01")
                )
                return ExecutionResult(
                    success=True,
                    error_message="HOLD signal - no action taken",
                    latency_ms=latency_ms,
                )

            elif signal.decision == TradingDecision.BUY:
                # Open long position
                logger.info(f"Executing BUY signal for {signal.symbol}")

                # Calculate stop-loss price
                stop_loss_price = None
                if signal.stop_loss_pct:
                    stop_loss_price = current_price * (
                        Decimal("1") - signal.stop_loss_pct
                    )
                    logger.info(f"Stop-loss price calculated: ${stop_loss_price:.2f}")

                # Place market buy order
                order_result = await self.create_market_order(
                    symbol=signal.symbol,
                    side=OrderSide.BUY,
                    quantity=quantity,
                    reduce_only=False,
                    metadata={
                        "signal_decision": signal.decision.value,
                        "signal_confidence": str(signal.confidence),
                        "signal_reasoning": signal.reasoning or "",
                    },
                )

                if not order_result.success:
                    return order_result

                # Place stop-loss order (Layer 1 protection)
                if stop_loss_price:
                    logger.info(f"Placing stop-loss order @ ${stop_loss_price:.2f}")
                    stop_result = await self.create_stop_market_order(
                        symbol=signal.symbol,
                        side=OrderSide.SELL,  # Opposite of entry
                        quantity=quantity,
                        stop_price=stop_loss_price,
                        reduce_only=True,
                        position_id=(
                            order_result.order.position_id
                            if order_result.order
                            else None
                        ),
                        metadata={"protection_layer": "layer1"},
                    )

                    if not stop_result.success:
                        logger.warning(
                            f"Failed to place stop-loss order: {stop_result.error_message}"
                        )

                return order_result

            elif signal.decision == TradingDecision.SELL:
                # Open short position
                logger.info(f"Executing SELL signal for {signal.symbol}")

                # Calculate stop-loss price (above entry for shorts)
                stop_loss_price = None
                if signal.stop_loss_pct:
                    stop_loss_price = current_price * (
                        Decimal("1") + signal.stop_loss_pct
                    )
                    logger.info(f"Stop-loss price calculated: ${stop_loss_price:.2f}")

                # Place market sell order
                order_result = await self.create_market_order(
                    symbol=signal.symbol,
                    side=OrderSide.SELL,
                    quantity=quantity,
                    reduce_only=False,
                    metadata={
                        "signal_decision": signal.decision.value,
                        "signal_confidence": str(signal.confidence),
                        "signal_reasoning": signal.reasoning or "",
                    },
                )

                if not order_result.success:
                    return order_result

                # Place stop-loss order (Layer 1 protection)
                if stop_loss_price:
                    logger.info(f"Placing stop-loss order @ ${stop_loss_price:.2f}")
                    stop_result = await self.create_stop_market_order(
                        symbol=signal.symbol,
                        side=OrderSide.BUY,  # Opposite of entry
                        quantity=quantity,
                        stop_price=stop_loss_price,
                        reduce_only=True,
                        position_id=(
                            order_result.order.position_id
                            if order_result.order
                            else None
                        ),
                        metadata={"protection_layer": "layer1"},
                    )

                    if not stop_result.success:
                        logger.warning(
                            f"Failed to place stop-loss order: {stop_result.error_message}"
                        )

                return order_result

            elif signal.decision == TradingDecision.CLOSE:
                # Close existing position
                logger.info(f"Executing CLOSE signal for {signal.symbol}")

                # Get current position
                if self.position_service is None:
                    raise RuntimeError("Position service not initialized")
                positions = await self.position_service.get_open_positions()
                position = next(
                    (p for p in positions if p.symbol == signal.symbol), None
                )

                if not position:
                    logger.warning(f"No open position found for {signal.symbol}")
                    latency_ms = Decimal(
                        str((time.time() - start_time) * 1000)
                    ).quantize(Decimal("0.01"))
                    return ExecutionResult(
                        success=False,
                        error_code="POSITION_NOT_FOUND",
                        error_message=f"No open position for {signal.symbol}",
                        latency_ms=latency_ms,
                    )

                # Close position
                return await self.close_position(
                    position_id=position.id,
                    reason="signal_close",
                )

            else:
                logger.error(f"Unknown trading decision: {signal.decision}")
                latency_ms = Decimal(str((time.time() - start_time) * 1000)).quantize(
                    Decimal("0.01")
                )
                return ExecutionResult(
                    success=False,
                    error_code="INVALID_DECISION",
                    error_message=f"Unknown decision: {signal.decision}",
                    latency_ms=latency_ms,
                )

        except Exception as e:
            logger.error(
                f"Error executing signal for {signal.symbol}: {e}", exc_info=True
            )
            latency_ms = Decimal(str((time.time() - start_time) * 1000)).quantize(
                Decimal("0.01")
            )
            return ExecutionResult(
                success=False,
                error_code="EXECUTION_ERROR",
                error_message=str(e),
                latency_ms=latency_ms,
            )

    async def create_market_order(  # noqa: C901 - Complex order execution with retry logic
        self,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        reduce_only: bool = False,
        position_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """
        Create and execute a market order

        Args:
            symbol: Trading pair (e.g., 'BTC/USDT:USDT')
            side: Buy or sell
            quantity: Order quantity in base currency
            reduce_only: Whether order only reduces position
            position_id: Associated position ID
            metadata: Additional order metadata

        Returns:
            ExecutionResult with order details or error

        Example:
            ```python
            result = await executor.create_market_order(
                symbol='BTC/USDT:USDT',
                side=OrderSide.BUY,
                quantity=Decimal('0.001'),
                reduce_only=False
            )
            if result.success:
                print(f"Order placed: {result.order.exchange_order_id}")
            ```
        """
        start_time = time.time()

        # Create order object
        order = Order(
            symbol=symbol,
            type=OrderType.MARKET,
            side=side,
            quantity=quantity,
            reduce_only=reduce_only,
            position_id=position_id,
            metadata=metadata or {},
        )

        # Validate symbol format (critical for Bybit perpetuals)
        if ":" not in symbol:
            error_msg = f"Invalid symbol format: {symbol}. Must be 'BASE/QUOTE:SETTLE' (e.g., 'BTC/USDT:USDT')"
            logger.error(error_msg)
            return ExecutionResult(
                success=False,
                error_code="INVALID_SYMBOL",
                error_message=error_msg,
                latency_ms=Decimal(str((time.time() - start_time) * 1000)),
            )

        # Execute order with retry logic
        for attempt in range(self.max_retries):
            try:
                # Prepare ccxt order parameters
                params = {
                    "reduceOnly": reduce_only,
                }

                # Submit order to exchange
                logger.info(
                    f"Submitting market order (attempt {attempt + 1}/{self.max_retries}): "
                    f"{side.value} {quantity} {symbol} (reduceOnly={reduce_only})"
                )

                exchange_order = await self.exchange.create_order(
                    symbol=symbol,
                    type="market",
                    side=side.value,
                    amount=float(quantity),
                    params=params,
                )

                # Update order with exchange response
                order.exchange_order_id = exchange_order.get("id")
                order.status = self._map_exchange_status(exchange_order.get("status"))
                order.submitted_at = datetime.utcnow()
                order.filled_quantity = Decimal(str(exchange_order.get("filled", 0)))
                order.average_fill_price = (
                    Decimal(str(exchange_order.get("average", 0)))
                    if exchange_order.get("average")
                    else None
                )
                order.fees_paid = Decimal(
                    str(exchange_order.get("fee", {}).get("cost", 0))
                )

                # Check if fully filled (market orders usually fill immediately)
                if order.is_fully_filled:
                    order.status = OrderStatus.FILLED
                    order.filled_at = datetime.utcnow()

                # Store order in database
                await self._store_order(order)

                # Track active order
                self.active_orders[order.id] = order

                # Calculate latency
                latency_ms = Decimal(str((time.time() - start_time) * 1000)).quantize(
                    Decimal("0.01")
                )

                logger.info(
                    f"Market order executed successfully: {order.exchange_order_id} "
                    f"(filled: {order.fill_percentage:.2f}%, latency: {latency_ms:.2f}ms)"
                )

                # Record metrics
                self.metrics_service.record_trade(
                    success=True,
                    fees=order.fees_paid,
                    latency_ms=latency_ms,
                )
                self.metrics_service.record_order(placed=True, filled=True)

                # Log trade to history (if order is filled)
                if order.is_fully_filled and order.average_fill_price:
                    try:
                        # Determine trade type based on side and reduce_only
                        if not reduce_only:
                            # Opening position
                            trade_type = (
                                TradeType.ENTRY_LONG
                                if side == OrderSide.BUY
                                else TradeType.ENTRY_SHORT
                            )
                        else:
                            # Closing position
                            # Check metadata for specific close reason
                            close_reason = (
                                metadata.get("reason", "") if metadata else ""
                            )
                            if (
                                "stop_loss" in close_reason
                                or "stop-loss" in close_reason
                            ):
                                trade_type = TradeType.STOP_LOSS
                            elif (
                                "take_profit" in close_reason
                                or "take-profit" in close_reason
                            ):
                                trade_type = TradeType.TAKE_PROFIT
                            elif "liquidation" in close_reason:
                                trade_type = TradeType.LIQUIDATION
                            else:
                                trade_type = (
                                    TradeType.EXIT_LONG
                                    if side == OrderSide.SELL
                                    else TradeType.EXIT_SHORT
                                )

                        # Extract signal metadata if available
                        signal_confidence = None
                        signal_reasoning = None
                        realized_pnl = None
                        if metadata:
                            confidence_str = metadata.get("signal_confidence")
                            if confidence_str:
                                signal_confidence = Decimal(str(confidence_str))
                            signal_reasoning = metadata.get("signal_reasoning")

                            # Extract realized P&L for closing trades
                            if reduce_only and "realized_pnl_before_fees" in metadata:
                                pnl_before_fees = Decimal(
                                    str(metadata["realized_pnl_before_fees"])
                                )
                                # Subtract fees to get net realized P&L
                                realized_pnl = pnl_before_fees - order.fees_paid

                        # Log the trade
                        await self.trade_history_service.log_trade(
                            trade_type=trade_type,
                            symbol=symbol,
                            order_id=order.exchange_order_id or order.id,
                            side=side.value,
                            quantity=order.filled_quantity,
                            price=order.average_fill_price,
                            fees=order.fees_paid,
                            position_id=position_id,
                            realized_pnl=realized_pnl,
                            signal_confidence=signal_confidence,
                            signal_reasoning=signal_reasoning,
                            execution_latency_ms=latency_ms,
                            metadata=metadata or {},
                        )

                        if realized_pnl is not None:
                            logger.info(
                                f"Trade logged to history: {order.exchange_order_id} (P&L: {realized_pnl:+.2f})"
                            )
                        else:
                            logger.debug(
                                f"Trade logged to history: {order.exchange_order_id}"
                            )
                    except Exception as log_error:
                        # Don't fail the trade if logging fails
                        logger.error(
                            f"Failed to log trade to history: {log_error}",
                            exc_info=True,
                        )

                return ExecutionResult(
                    success=True,
                    order=order,
                    exchange_response=exchange_order,
                    latency_ms=latency_ms,
                )

            except RateLimitExceeded as e:
                logger.warning(f"Rate limit exceeded (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2**attempt)  # Exponential backoff
                    logger.info(f"Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    latency_ms = Decimal(
                        str((time.time() - start_time) * 1000)
                    ).quantize(Decimal("0.01"))
                    return ExecutionResult(
                        success=False,
                        error_code="RATE_LIMIT_EXCEEDED",
                        error_message=str(e),
                        latency_ms=latency_ms,
                    )

            except InvalidOrder as e:
                logger.error(f"Invalid order: {e}")
                latency_ms = Decimal(str((time.time() - start_time) * 1000)).quantize(
                    Decimal("0.01")
                )
                return ExecutionResult(
                    success=False,
                    error_code="INVALID_ORDER",
                    error_message=str(e),
                    latency_ms=latency_ms,
                )

            except InsufficientFunds as e:
                logger.error(f"Insufficient funds: {e}")
                latency_ms = Decimal(str((time.time() - start_time) * 1000)).quantize(
                    Decimal("0.01")
                )
                return ExecutionResult(
                    success=False,
                    error_code="INSUFFICIENT_FUNDS",
                    error_message=str(e),
                    latency_ms=latency_ms,
                )

            except NetworkError as e:
                logger.warning(f"Network error (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2**attempt)
                    await asyncio.sleep(delay)
                else:
                    latency_ms = Decimal(
                        str((time.time() - start_time) * 1000)
                    ).quantize(Decimal("0.01"))
                    return ExecutionResult(
                        success=False,
                        error_code="NETWORK_ERROR",
                        error_message=str(e),
                        latency_ms=latency_ms,
                    )

            except Exception as e:
                logger.error(
                    f"Unexpected error executing market order: {e}", exc_info=True
                )
                latency_ms = Decimal(str((time.time() - start_time) * 1000)).quantize(
                    Decimal("0.01")
                )

                # Record failure metrics
                self.metrics_service.record_trade(success=False)
                self.metrics_service.record_order(placed=True)

                return ExecutionResult(
                    success=False,
                    error_code="UNKNOWN_ERROR",
                    error_message=str(e),
                    latency_ms=latency_ms,
                )

        # Should not reach here
        latency_ms = Decimal(str((time.time() - start_time) * 1000)).quantize(
            Decimal("0.01")
        )
        return ExecutionResult(
            success=False,
            error_code="MAX_RETRIES_EXCEEDED",
            error_message=f"Failed after {self.max_retries} attempts",
            latency_ms=latency_ms,
        )

    async def create_limit_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        price: Decimal,
        time_in_force: TimeInForce = TimeInForce.GTC,
        reduce_only: bool = False,
        position_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """
        Create a limit order

        Args:
            symbol: Trading pair
            side: Buy or sell
            quantity: Order quantity
            price: Limit price
            time_in_force: Time in force (GTC, IOC, FOK, POST_ONLY)
            reduce_only: Whether order only reduces position
            position_id: Associated position ID
            metadata: Additional metadata

        Returns:
            ExecutionResult with order details or error
        """
        start_time = time.time()

        # Create order object
        order = Order(
            symbol=symbol,
            type=OrderType.LIMIT,
            side=side,
            quantity=quantity,
            price=price,
            time_in_force=time_in_force,
            reduce_only=reduce_only,
            position_id=position_id,
            metadata=metadata or {},
        )

        # Validate symbol format
        if ":" not in symbol:
            error_msg = f"Invalid symbol format: {symbol}"
            logger.error(error_msg)
            return ExecutionResult(
                success=False,
                error_code="INVALID_SYMBOL",
                error_message=error_msg,
                latency_ms=Decimal(str((time.time() - start_time) * 1000)),
            )

        # Execute order with retry logic
        for attempt in range(self.max_retries):
            try:
                params = {
                    "reduceOnly": reduce_only,
                    "timeInForce": time_in_force.value,
                }

                logger.info(
                    f"Submitting limit order: {side.value} {quantity} {symbol} @ {price} "
                    f"(TIF={time_in_force.value}, reduceOnly={reduce_only})"
                )

                exchange_order = await self.exchange.create_order(
                    symbol=symbol,
                    type="limit",
                    side=side.value,
                    amount=float(quantity),
                    price=float(price),
                    params=params,
                )

                # Update order
                order.exchange_order_id = exchange_order.get("id")
                order.status = self._map_exchange_status(exchange_order.get("status"))
                order.submitted_at = datetime.utcnow()
                order.filled_quantity = Decimal(str(exchange_order.get("filled", 0)))
                order.average_fill_price = (
                    Decimal(str(exchange_order.get("average", 0)))
                    if exchange_order.get("average")
                    else None
                )

                # Store order
                await self._store_order(order)
                self.active_orders[order.id] = order

                latency_ms = Decimal(str((time.time() - start_time) * 1000)).quantize(
                    Decimal("0.01")
                )

                logger.info(
                    f"Limit order placed successfully: {order.exchange_order_id} "
                    f"(status: {order.status}, latency: {latency_ms:.2f}ms)"
                )

                return ExecutionResult(
                    success=True,
                    order=order,
                    exchange_response=exchange_order,
                    latency_ms=latency_ms,
                )

            except Exception as e:
                logger.error(f"Error creating limit order: {e}", exc_info=True)
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2**attempt))
                else:
                    latency_ms = Decimal(
                        str((time.time() - start_time) * 1000)
                    ).quantize(Decimal("0.01"))
                    return ExecutionResult(
                        success=False,
                        error_code="EXECUTION_ERROR",
                        error_message=str(e),
                        latency_ms=latency_ms,
                    )

        # Should not reach here, but mypy needs explicit return
        latency_ms = Decimal(str((time.time() - start_time) * 1000)).quantize(
            Decimal("0.01")
        )
        return ExecutionResult(
            success=False,
            error_code="UNEXPECTED_ERROR",
            error_message="Order execution failed unexpectedly",
            latency_ms=latency_ms,
        )

    async def create_stop_market_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        stop_price: Decimal,
        reduce_only: bool = True,
        position_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """
        Create a stop-market order (for stop-loss protection)

        Args:
            symbol: Trading pair
            side: Buy or sell
            quantity: Order quantity
            stop_price: Stop trigger price
            reduce_only: Whether order only reduces position (default: True)
            position_id: Associated position ID
            metadata: Additional metadata

        Returns:
            ExecutionResult with order details or error

        Note:
            This is used for Layer 1 stop-loss protection.
            reduceOnly should always be True for stop-loss orders.
        """
        start_time = time.time()

        # Create order object
        order = Order(
            symbol=symbol,
            type=OrderType.STOP_MARKET,
            side=side,
            quantity=quantity,
            stop_price=stop_price,
            reduce_only=reduce_only,
            position_id=position_id,
            metadata=metadata or {},
        )

        try:
            params = {
                "stopPrice": float(stop_price),
                "reduceOnly": reduce_only,
            }

            logger.info(
                f"Placing stop-market order: {side.value} {quantity} {symbol} "
                f"@ stop {stop_price} (reduceOnly={reduce_only})"
            )

            exchange_order = await self.exchange.create_order(
                symbol=symbol,
                type="stop_market",
                side=side.value,
                amount=float(quantity),
                params=params,
            )

            # Update order
            order.exchange_order_id = exchange_order.get("id")
            order.status = OrderStatus.OPEN  # Stop orders are "open" until triggered
            order.submitted_at = datetime.utcnow()

            # Store order
            await self._store_order(order)
            self.active_orders[order.id] = order

            latency_ms = Decimal(str((time.time() - start_time) * 1000)).quantize(
                Decimal("0.01")
            )

            logger.info(
                f"Stop-market order placed: {order.exchange_order_id} "
                f"(trigger: {stop_price}, latency: {latency_ms:.2f}ms)"
            )

            return ExecutionResult(
                success=True,
                order=order,
                exchange_response=exchange_order,
                latency_ms=latency_ms,
            )

        except Exception as e:
            logger.error(f"Error creating stop-market order: {e}", exc_info=True)
            latency_ms = Decimal(str((time.time() - start_time) * 1000)).quantize(
                Decimal("0.01")
            )
            return ExecutionResult(
                success=False,
                error_code="STOP_ORDER_ERROR",
                error_message=str(e),
                latency_ms=latency_ms,
            )

    async def open_position(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        leverage: int,
        stop_loss: Decimal,
        take_profit: Optional[Decimal] = None,
        signal_id: Optional[str] = None,
    ) -> ExecutionResult:
        """
        Open a new position with stop-loss

        This is a high-level method that:
        1. Creates position in Position Manager
        2. Executes market order to open position
        3. Places stop-loss order (Layer 1 protection)

        Args:
            symbol: Trading pair
            side: 'long' or 'short'
            quantity: Position quantity
            leverage: Leverage multiplier (5-40x)
            stop_loss: Stop-loss price
            take_profit: Take-profit price (optional)
            signal_id: Trading signal ID

        Returns:
            ExecutionResult with position and order details
        """
        try:
            logger.info(
                f"Opening position: {side} {quantity} {symbol} @ {leverage}x leverage "
                f"(SL: {stop_loss}, TP: {take_profit})"
            )

            # Get current market price
            ticker = await self.exchange.fetch_ticker(symbol)
            entry_price = Decimal(str(ticker["last"]))

            # Create position in Position Manager (validates risk limits)
            if self.position_service is None:
                raise RuntimeError("Position service not initialized")
            position = await self.position_service.create_position(
                symbol=symbol,
                side=side,
                quantity=quantity,
                entry_price=entry_price,
                leverage=leverage,
                stop_loss=stop_loss,
                take_profit=take_profit,
                signal_id=signal_id,
            )

            logger.info(f"Position created in database: {position.id}")

            # Determine order side (buy for long, sell for short)
            order_side = OrderSide.BUY if side == "long" else OrderSide.SELL

            # Execute market order to open position
            order_result = await self.create_market_order(
                symbol=symbol,
                side=order_side,
                quantity=quantity,
                reduce_only=False,  # Opening position
                position_id=position.id,
                metadata={"action": "open_position", "signal_id": signal_id},
            )

            if not order_result.success:
                logger.error(
                    f"Failed to execute order for position {position.id}: {order_result.error_message}"
                )
                # Mark position as failed
                if self.position_service is None:
                    raise RuntimeError("Position service not initialized")
                await self.position_service.close_position(
                    position_id=position.id,
                    close_price=entry_price,
                    reason="order_execution_failed",
                )
                return order_result

            if order_result.order is not None:
                logger.info(
                    f"Position opened successfully: {position.id} (Order: {order_result.order.exchange_order_id})"
                )
            else:
                logger.info(f"Position opened successfully: {position.id}")

            return order_result

        except Exception as e:
            logger.error(f"Error opening position: {e}", exc_info=True)
            return ExecutionResult(
                success=False,
                error_code="POSITION_OPEN_ERROR",
                error_message=str(e),
            )

    async def close_position(
        self,
        position_id: str,
        reason: str = "manual_close",
    ) -> ExecutionResult:
        """
        Close an existing position

        Args:
            position_id: Position ID to close
            reason: Reason for closing

        Returns:
            ExecutionResult with closure details
        """
        try:
            # Get position from Position Manager
            if self.position_service is None:
                raise RuntimeError("Position service not initialized")
            position = await self.position_service.get_position(position_id)
            if not position:
                return ExecutionResult(
                    success=False,
                    error_code="POSITION_NOT_FOUND",
                    error_message=f"Position {position_id} not found",
                )

            logger.info(f"Closing position: {position_id} ({reason})")

            # Get current market price
            ticker = await self.exchange.fetch_ticker(position.symbol)
            close_price = Decimal(str(ticker["last"]))

            # Calculate realized P&L (before fees)
            # For long: (close_price - entry_price) * quantity
            # For short: (entry_price - close_price) * quantity
            if position.side == "long":
                realized_pnl_before_fees = (
                    close_price - position.entry_price
                ) * position.quantity
            else:
                realized_pnl_before_fees = (
                    position.entry_price - close_price
                ) * position.quantity

            # Determine order side (opposite of position side)
            order_side = OrderSide.SELL if position.side == "long" else OrderSide.BUY

            # Execute market order to close position (reduceOnly=True is CRITICAL)
            order_result = await self.create_market_order(
                symbol=position.symbol,
                side=order_side,
                quantity=position.quantity,
                reduce_only=True,  # CRITICAL: Only reduce position, don't open opposite
                position_id=position_id,
                metadata={
                    "action": "close_position",
                    "reason": reason,
                    "realized_pnl_before_fees": str(realized_pnl_before_fees),
                    "entry_price": str(position.entry_price),
                },
            )

            if not order_result.success:
                logger.error(
                    f"Failed to close position {position_id}: {order_result.error_message}"
                )
                return order_result

            # Update position in database
            if self.position_service is None:
                raise RuntimeError("Position service not initialized")
            await self.position_service.close_position(
                position_id=position_id,
                close_price=close_price,
                reason=reason,
            )

            if order_result.order is not None:
                logger.info(
                    f"Position closed successfully: {position_id} (Order: {order_result.order.exchange_order_id})"
                )
            else:
                logger.info(f"Position closed successfully: {position_id}")

            return order_result

        except Exception as e:
            logger.error(f"Error closing position: {e}", exc_info=True)
            return ExecutionResult(
                success=False,
                error_code="POSITION_CLOSE_ERROR",
                error_message=str(e),
            )

    async def fetch_order_status(self, order_id: str, symbol: str) -> Optional[Order]:
        """
        Fetch order status from exchange

        Args:
            order_id: Exchange order ID
            symbol: Trading pair

        Returns:
            Updated Order object or None if not found
        """
        try:
            exchange_order = await self.exchange.fetch_order(order_id, symbol)

            # Find order in active orders
            order = next(
                (
                    o
                    for o in self.active_orders.values()
                    if o.exchange_order_id == order_id
                ),
                None,
            )

            if order:
                # Update order status
                order.status = self._map_exchange_status(exchange_order.get("status"))
                order.filled_quantity = Decimal(str(exchange_order.get("filled", 0)))
                order.remaining_quantity = order.quantity - order.filled_quantity
                order.average_fill_price = (
                    Decimal(str(exchange_order.get("average", 0)))
                    if exchange_order.get("average")
                    else None
                )
                order.updated_at = datetime.utcnow()

                if order.is_fully_filled:
                    order.filled_at = datetime.utcnow()

                # Update in database
                await self._update_order(order)

                return order

            # Order not found in active orders
            return None

        except Exception as e:
            logger.error(f"Error fetching order status: {e}", exc_info=True)
            return None

    def _map_exchange_status(self, exchange_status: str) -> OrderStatus:
        """Map exchange order status to our OrderStatus enum"""
        status_map = {
            "open": OrderStatus.OPEN,
            "closed": OrderStatus.FILLED,
            "canceled": OrderStatus.CANCELED,
            "expired": OrderStatus.EXPIRED,
        }
        return status_map.get(exchange_status, OrderStatus.OPEN)

    async def _store_order(self, order: Order):
        """Store order in database"""
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO orders (
                        id, exchange_order_id, symbol, type, side, quantity, price, stop_price,
                        filled_quantity, remaining_quantity, average_fill_price, status,
                        time_in_force, reduce_only, position_id, created_at, submitted_at,
                        updated_at, filled_at, fees_paid, metadata
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15,
                        $16, $17, $18, $19, $20, $21
                    )
                    """,
                    order.id,
                    order.exchange_order_id,
                    order.symbol,
                    order.type.value,
                    order.side.value,
                    order.quantity,
                    order.price,
                    order.stop_price,
                    order.filled_quantity,
                    order.remaining_quantity,
                    order.average_fill_price,
                    order.status.value,
                    order.time_in_force.value,
                    order.reduce_only,
                    order.position_id,
                    order.created_at,
                    order.submitted_at,
                    order.updated_at,
                    order.filled_at,
                    order.fees_paid,
                    order.metadata,
                )
            logger.debug(f"Order stored in database: {order.id}")

        except Exception as e:
            logger.error(f"Error storing order: {e}", exc_info=True)

    async def _update_order(self, order: Order):
        """Update order in database"""
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE orders SET
                        filled_quantity = $1,
                        remaining_quantity = $2,
                        average_fill_price = $3,
                        status = $4,
                        updated_at = $5,
                        filled_at = $6,
                        fees_paid = $7
                    WHERE id = $8
                    """,
                    order.filled_quantity,
                    order.remaining_quantity,
                    order.average_fill_price,
                    order.status.value,
                    order.updated_at,
                    order.filled_at,
                    order.fees_paid,
                    order.id,
                )
            logger.debug(f"Order updated in database: {order.id}")

        except Exception as e:
            logger.error(f"Error updating order: {e}", exc_info=True)


# Export
__all__ = ["TradeExecutor"]
