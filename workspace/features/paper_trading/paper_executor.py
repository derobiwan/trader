"""
Paper Trading Executor

Simulates trade execution without real capital. Mimics real trading behavior
including latency, partial fills, fees, and slippage.

Key Features:
- Realistic order execution simulation
- Virtual balance and position tracking
- Simulated fees (0.1% maker/taker)
- Simulated slippage (0-0.2%)
- Partial fill simulation (95-100%)
- Realistic latency (50-150ms)

Author: Implementation Specialist (Sprint 2 Stream B)
Date: 2025-10-29
"""

import asyncio
import logging
import random
import time
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List
from uuid import uuid4


from workspace.features.trade_executor.executor_service import TradeExecutor
from workspace.features.trade_executor.models import (
    Order,
    OrderType,
    OrderSide,
    OrderStatus,
)
from .virtual_portfolio import VirtualPortfolio
from .performance_tracker import PaperTradingPerformanceTracker

logger = logging.getLogger(__name__)


class PaperTradingExecutor(TradeExecutor):
    """
    Paper trading executor - simulates trades without real money

    Extends TradeExecutor to simulate all exchange operations in a virtual
    environment. All trades are executed against virtual balance and positions.

    Attributes:
        initial_balance: Starting USDT balance
        virtual_portfolio: Virtual portfolio manager
        performance_tracker: Performance metrics tracker
        simulated_trades: List of all simulated trades
        enable_slippage: Whether to simulate slippage
        enable_partial_fills: Whether to simulate partial fills
        maker_fee_pct: Maker fee percentage (default: 0.1%)
        taker_fee_pct: Taker fee percentage (default: 0.1%)
    """

    def __init__(
        self,
        initial_balance: Decimal = Decimal("10000"),
        enable_slippage: bool = True,
        enable_partial_fills: bool = True,
        maker_fee_pct: Decimal = Decimal("0.001"),
        taker_fee_pct: Decimal = Decimal("0.001"),
        **kwargs,
    ):
        """
        Initialize Paper Trading Executor

        Args:
            initial_balance: Starting USDT balance
            enable_slippage: Enable slippage simulation
            enable_partial_fills: Enable partial fill simulation
            maker_fee_pct: Maker fee percentage (default: 0.1%)
            taker_fee_pct: Taker fee percentage (default: 0.1%)
            **kwargs: Additional arguments for TradeExecutor base class
        """
        # Initialize base TradeExecutor with testnet mode
        kwargs["testnet"] = True
        super().__init__(**kwargs)

        # Paper trading specific attributes
        self.initial_balance = initial_balance
        self.virtual_portfolio = VirtualPortfolio(initial_balance=initial_balance)
        self.performance_tracker = PaperTradingPerformanceTracker()
        self.simulated_trades: List[Dict[str, Any]] = []

        # Simulation settings
        self.enable_slippage = enable_slippage
        self.enable_partial_fills = enable_partial_fills
        self.maker_fee_pct = maker_fee_pct
        self.taker_fee_pct = taker_fee_pct

        logger.info(f"Paper Trading Executor initialized with ${initial_balance} USDT")

    async def initialize(self):
        """Initialize exchange (read-only for paper trading)"""
        try:
            await self.exchange.load_markets()
            logger.info(
                f"Paper Trading: Exchange markets loaded (read-only): "
                f"{len(self.exchange.markets)} symbols"
            )
        except Exception as e:
            logger.error(f"Failed to initialize exchange: {e}", exc_info=True)
            raise

    async def _simulate_latency(self):
        """Simulate realistic execution latency (50-150ms)"""
        latency = random.uniform(0.05, 0.15)
        await asyncio.sleep(latency)

    def _calculate_slippage(self, side: OrderSide, current_price: Decimal) -> Decimal:
        """
        Calculate price slippage

        Simulates realistic slippage based on order side:
        - Buy orders: slight price increase (0-0.2%)
        - Sell orders: slight price decrease (0-0.2%)

        Args:
            side: Order side (buy/sell)
            current_price: Current market price

        Returns:
            Slipped price
        """
        if not self.enable_slippage:
            return current_price

        # Simulate 0-0.2% slippage
        slippage_pct = Decimal(str(random.uniform(0, 0.002)))

        if side == OrderSide.BUY:
            # Buy at slightly higher price
            return current_price * (Decimal("1") + slippage_pct)
        else:
            # Sell at slightly lower price
            return current_price * (Decimal("1") - slippage_pct)

    def _calculate_partial_fill(self, quantity: Decimal) -> Decimal:
        """
        Calculate partial fill quantity

        Simulates realistic partial fills (95-100% of order).

        Args:
            quantity: Requested quantity

        Returns:
            Filled quantity
        """
        if not self.enable_partial_fills:
            return quantity

        # Simulate 95-100% fill
        fill_percentage = Decimal(str(random.uniform(0.95, 1.0)))
        return quantity * fill_percentage

    def _calculate_fees(
        self, quantity: Decimal, price: Decimal, order_type: OrderType
    ) -> Decimal:
        """
        Calculate trading fees

        Args:
            quantity: Order quantity
            price: Execution price
            order_type: Order type (market uses taker, limit uses maker)

        Returns:
            Fees in USDT
        """
        notional_value = quantity * price

        if order_type == OrderType.MARKET:
            return notional_value * self.taker_fee_pct
        else:
            return notional_value * self.maker_fee_pct

    async def create_market_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        reduce_only: bool = False,
        position_id: Optional[str] = None,
        **kwargs,
    ) -> Order:
        """
        Simulate market order execution

        Args:
            symbol: Trading pair (e.g., 'BTC/USDT:USDT')
            side: Buy or sell
            quantity: Order quantity
            reduce_only: Whether order reduces position only
            position_id: Associated position ID
            **kwargs: Additional order parameters

        Returns:
            Simulated Order object
        """
        start_time = time.time()

        # Simulate latency
        await self._simulate_latency()

        try:
            # Get current market price from exchange
            ticker = await self.exchange.fetch_ticker(symbol)
            current_price = Decimal(str(ticker["last"]))

            # Apply slippage
            execution_price = self._calculate_slippage(side, current_price)

            # Apply partial fills
            filled_quantity = self._calculate_partial_fill(quantity)

            # Calculate fees
            fees = self._calculate_fees(
                filled_quantity, execution_price, OrderType.MARKET
            )

            # Check if sufficient balance
            if side == OrderSide.BUY:
                cost = filled_quantity * execution_price + fees
                if cost > self.virtual_portfolio.balance:
                    raise ValueError(
                        f"Insufficient balance: need ${cost:.2f}, "
                        f"have ${self.virtual_portfolio.balance:.2f}"
                    )

            # Update virtual portfolio
            if reduce_only:
                # Closing position
                pnl = self.virtual_portfolio.close_position(
                    symbol=symbol,
                    exit_price=execution_price,
                    fees=fees,
                    quantity=filled_quantity,
                )
                logger.info(f"Paper Trade: Closed position {symbol} - P&L: ${pnl:.2f}")
            else:
                # Opening position
                self.virtual_portfolio.open_position(
                    symbol=symbol,
                    side="long" if side == OrderSide.BUY else "short",
                    quantity=filled_quantity,
                    entry_price=execution_price,
                    fees=fees,
                )
                logger.info(
                    f"Paper Trade: Opened position {symbol} - "
                    f"Qty: {filled_quantity}, Price: ${execution_price:.2f}"
                )

            # Create order object
            order = Order(
                id=str(uuid4()),
                exchange_order_id=f"paper_{len(self.simulated_trades)}",
                symbol=symbol,
                type=OrderType.MARKET,
                side=side,
                quantity=quantity,
                filled_quantity=filled_quantity,
                average_fill_price=execution_price,
                status=OrderStatus.FILLED,
                position_id=position_id,
                submitted_at=datetime.utcnow(),
                filled_at=datetime.utcnow(),
                fees_paid=fees,
                metadata={
                    "paper_trading": True,
                    "slippage_enabled": self.enable_slippage,
                    "partial_fills_enabled": self.enable_partial_fills,
                },
            )

            # Record trade
            trade_record = {
                "order": order,
                "timestamp": datetime.utcnow(),
                "pnl": pnl if reduce_only else Decimal("0"),
            }
            self.simulated_trades.append(trade_record)

            # Track performance
            if reduce_only:
                self.performance_tracker.record_trade(
                    {
                        "symbol": symbol,
                        "side": side.value,
                        "quantity": float(filled_quantity),
                        "price": float(execution_price),
                        "fees": float(fees),
                        "pnl": float(pnl),
                        "timestamp": datetime.utcnow(),
                    }
                )

            # Record metrics
            latency_ms = (time.time() - start_time) * 1000
            self.metrics_service.record_order_execution(
                symbol=symbol,
                side=side.value,
                order_type=OrderType.MARKET.value,
                success=True,
                latency_ms=latency_ms,
            )

            logger.info(
                f"Paper market order executed: {side.value} {filled_quantity} "
                f"{symbol} @ ${execution_price:.2f} (fees: ${fees:.4f})"
            )

            return order

        except Exception as e:
            logger.error(f"Paper market order failed: {e}", exc_info=True)

            # Record failure metrics
            latency_ms = (time.time() - start_time) * 1000
            self.metrics_service.record_order_execution(
                symbol=symbol,
                side=side.value,
                order_type=OrderType.MARKET.value,
                success=False,
                latency_ms=latency_ms,
            )

            raise

    async def create_stop_loss_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        stop_price: Decimal,
        position_id: Optional[str] = None,
        **kwargs,
    ) -> Order:
        """
        Simulate stop-loss order creation

        Args:
            symbol: Trading pair
            side: Buy or sell
            quantity: Order quantity
            stop_price: Stop trigger price
            position_id: Associated position ID
            **kwargs: Additional order parameters

        Returns:
            Simulated Order object
        """
        # Simulate latency
        await self._simulate_latency()

        # Create stop-loss order (not triggered yet)
        order = Order(
            id=str(uuid4()),
            exchange_order_id=f"paper_sl_{len(self.simulated_trades)}",
            symbol=symbol,
            type=OrderType.STOP_MARKET,
            side=side,
            quantity=quantity,
            stop_price=stop_price,
            status=OrderStatus.OPEN,
            position_id=position_id,
            submitted_at=datetime.utcnow(),
            metadata={
                "paper_trading": True,
                "stop_loss": True,
            },
        )

        logger.info(
            f"Paper stop-loss order created: {side.value} {quantity} "
            f"{symbol} @ ${stop_price:.2f}"
        )

        return order

    async def get_account_balance(self) -> Decimal:
        """
        Get virtual account balance

        Returns:
            Virtual balance in USDT
        """
        return self.virtual_portfolio.balance

    async def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get virtual position for symbol

        Args:
            symbol: Trading pair

        Returns:
            Position data or None
        """
        return self.virtual_portfolio.positions.get(symbol)

    def get_performance_report(self) -> Dict[str, Any]:
        """
        Get performance report

        Returns:
            Performance metrics and statistics
        """
        report = self.performance_tracker.generate_report()

        # Add portfolio information
        report["portfolio"] = {
            "initial_balance": float(self.initial_balance),
            "current_balance": float(self.virtual_portfolio.balance),
            "total_return": float(
                (self.virtual_portfolio.balance - self.initial_balance)
                / self.initial_balance
                * 100
            ),
            "open_positions": len(self.virtual_portfolio.positions),
        }

        return report

    async def reset(self, initial_balance: Optional[Decimal] = None):
        """
        Reset paper trading state

        Args:
            initial_balance: New initial balance (optional)
        """
        if initial_balance is not None:
            self.initial_balance = initial_balance

        self.virtual_portfolio = VirtualPortfolio(initial_balance=self.initial_balance)
        self.performance_tracker = PaperTradingPerformanceTracker()
        self.simulated_trades = []

        logger.info(f"Paper Trading reset with ${self.initial_balance} USDT")
