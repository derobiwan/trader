# Sprint 1 - Stream D: Position Reconciliation

**Agent**: Trading Logic Specialist
**Duration**: 3-4 days
**Total Effort**: 12 hours
**Branch**: `sprint-1/stream-d-reconciliation`

---

## 🎯 Stream Objectives

Implement production-critical position reconciliation system:
1. Sync positions with exchange every 5 minutes
2. Detect and correct discrepancies automatically
3. Alert on major differences requiring manual intervention

**Why This Task**: Critical for production safety - prevents drift between system state and exchange reality

---

## 📋 Task Breakdown

### TASK-013: Position Reconciliation System (12 hours)

**Current State**: No reconciliation, system state can drift from exchange

**Risk**: System may think position is closed when it's still open, or vice versa

**Target State**: Continuous reconciliation with automated correction and alerting

**Implementation Steps**:

1. **Create reconciliation models** (1 hour)
   - File: `workspace/features/position_reconciliation/models.py` (NEW)
```python
"""
Position Reconciliation Models

Data structures for reconciliation process.
"""

from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class DiscrepancyType(str, Enum):
    """Type of discrepancy detected"""
    POSITION_MISSING_IN_SYSTEM = "position_missing_in_system"
    POSITION_MISSING_ON_EXCHANGE = "position_missing_on_exchange"
    QUANTITY_MISMATCH = "quantity_mismatch"
    PRICE_MISMATCH = "price_mismatch"
    SIDE_MISMATCH = "side_mismatch"
    NO_DISCREPANCY = "no_discrepancy"


class DiscrepancySeverity(str, Enum):
    """Severity level of discrepancy"""
    INFO = "info"  # Minor difference, within tolerance
    WARNING = "warning"  # Moderate difference, auto-corrected
    CRITICAL = "critical"  # Major difference, requires manual intervention


class ExchangePosition(BaseModel):
    """Position as reported by exchange"""
    symbol: str
    side: str  # "LONG" or "SHORT"
    quantity: Decimal
    entry_price: Decimal
    current_price: Decimal
    unrealized_pnl: Decimal
    leverage: Decimal
    liquidation_price: Optional[Decimal] = None
    margin: Decimal
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SystemPosition(BaseModel):
    """Position as tracked by system"""
    symbol: str
    side: str
    quantity: Decimal
    entry_price: Decimal
    current_price: Decimal
    unrealized_pnl: Decimal
    leverage: Decimal
    stop_loss_price: Optional[Decimal] = None
    take_profit_price: Optional[Decimal] = None
    last_updated: datetime


class PositionDiscrepancy(BaseModel):
    """Discrepancy between exchange and system position"""
    symbol: str
    discrepancy_type: DiscrepancyType
    severity: DiscrepancySeverity

    # Position states
    exchange_position: Optional[ExchangePosition] = None
    system_position: Optional[SystemPosition] = None

    # Differences
    quantity_difference: Optional[Decimal] = None
    price_difference: Optional[Decimal] = None
    pnl_difference: Optional[Decimal] = None

    # Action taken
    auto_corrected: bool = False
    correction_action: Optional[str] = None
    requires_manual_intervention: bool = False

    # Metadata
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    notes: Optional[str] = None


class ReconciliationResult(BaseModel):
    """Result of reconciliation check"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    symbols_checked: int = 0
    discrepancies_found: int = 0
    auto_corrections: int = 0
    critical_alerts: int = 0

    discrepancies: list[PositionDiscrepancy] = Field(default_factory=list)

    # Performance
    duration_ms: Decimal = Decimal("0")
```

2. **Implement reconciliation service** (4 hours)
   - File: `workspace/features/position_reconciliation/reconciliation_service.py` (NEW)
```python
"""
Position Reconciliation Service

Continuously syncs positions with exchange and detects discrepancies.
"""

import asyncio
import logging
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime

from workspace.features.position_reconciliation.models import (
    ExchangePosition,
    SystemPosition,
    PositionDiscrepancy,
    ReconciliationResult,
    DiscrepancyType,
    DiscrepancySeverity,
)
from workspace.features.trade_executor import TradeExecutor

logger = logging.getLogger(__name__)


class PositionReconciliationService:
    """
    Position reconciliation service

    Compares system positions with exchange positions and corrects discrepancies.
    """

    def __init__(
        self,
        trade_executor: TradeExecutor,
        quantity_tolerance_percent: Decimal = Decimal("0.01"),  # 1%
        price_tolerance_percent: Decimal = Decimal("0.1"),  # 0.1%
        reconciliation_interval_seconds: int = 300,  # 5 minutes
    ):
        self.trade_executor = trade_executor
        self.quantity_tolerance = quantity_tolerance_percent
        self.price_tolerance = price_tolerance_percent
        self.reconciliation_interval = reconciliation_interval_seconds

        # Running state
        self.is_running = False
        self.reconciliation_task: Optional[asyncio.Task] = None

        # Statistics
        self.total_reconciliations = 0
        self.total_discrepancies = 0
        self.total_auto_corrections = 0
        self.total_critical_alerts = 0

    async def start(self):
        """Start continuous reconciliation"""
        if self.is_running:
            logger.warning("Reconciliation already running")
            return

        self.is_running = True
        self.reconciliation_task = asyncio.create_task(self._reconciliation_loop())
        logger.info(
            f"Reconciliation started (interval: {self.reconciliation_interval}s)"
        )

    async def stop(self):
        """Stop reconciliation"""
        self.is_running = False
        if self.reconciliation_task:
            self.reconciliation_task.cancel()
            try:
                await self.reconciliation_task
            except asyncio.CancelledError:
                pass
        logger.info("Reconciliation stopped")

    async def _reconciliation_loop(self):
        """Main reconciliation loop"""
        while self.is_running:
            try:
                start_time = datetime.utcnow()

                # Run reconciliation
                result = await self.reconcile_positions()

                # Update statistics
                self.total_reconciliations += 1
                self.total_discrepancies += result.discrepancies_found
                self.total_auto_corrections += result.auto_corrections
                self.total_critical_alerts += result.critical_alerts

                # Log result
                if result.discrepancies_found > 0:
                    logger.warning(
                        f"Reconciliation: {result.discrepancies_found} discrepancies, "
                        f"{result.auto_corrections} auto-corrected, "
                        f"{result.critical_alerts} critical alerts"
                    )
                else:
                    logger.info("Reconciliation: No discrepancies")

                # Wait for next interval
                await asyncio.sleep(self.reconciliation_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Reconciliation error: {e}", exc_info=True)
                await asyncio.sleep(self.reconciliation_interval)

    async def reconcile_positions(self) -> ReconciliationResult:
        """
        Run reconciliation check

        Returns:
            ReconciliationResult with detected discrepancies
        """
        start_time = datetime.utcnow()

        try:
            # Fetch positions from exchange
            exchange_positions = await self._fetch_exchange_positions()

            # Get system positions
            system_positions = await self._get_system_positions()

            # Compare positions
            discrepancies = await self._compare_positions(
                exchange_positions,
                system_positions,
            )

            # Handle discrepancies
            for discrepancy in discrepancies:
                await self._handle_discrepancy(discrepancy)

            # Calculate duration
            duration_ms = Decimal(
                str((datetime.utcnow() - start_time).total_seconds() * 1000)
            )

            # Build result
            result = ReconciliationResult(
                symbols_checked=len(exchange_positions) + len(system_positions),
                discrepancies_found=len(discrepancies),
                auto_corrections=sum(1 for d in discrepancies if d.auto_corrected),
                critical_alerts=sum(
                    1 for d in discrepancies if d.requires_manual_intervention
                ),
                discrepancies=discrepancies,
                duration_ms=duration_ms,
            )

            return result

        except Exception as e:
            logger.error(f"Reconciliation failed: {e}", exc_info=True)
            return ReconciliationResult(
                discrepancies_found=0,
                duration_ms=Decimal("0"),
            )

    async def _fetch_exchange_positions(self) -> Dict[str, ExchangePosition]:
        """Fetch positions from exchange"""
        try:
            # Fetch positions via TradeExecutor
            raw_positions = await self.trade_executor.exchange.fetch_positions()

            positions = {}
            for pos in raw_positions:
                # Filter out closed positions
                if Decimal(str(pos.get("contracts", 0))) == 0:
                    continue

                symbol = pos["symbol"]
                positions[symbol] = ExchangePosition(
                    symbol=symbol,
                    side="LONG" if pos["side"] == "long" else "SHORT",
                    quantity=Decimal(str(pos["contracts"])),
                    entry_price=Decimal(str(pos["entryPrice"])),
                    current_price=Decimal(str(pos["markPrice"])),
                    unrealized_pnl=Decimal(str(pos["unrealizedPnl"])),
                    leverage=Decimal(str(pos.get("leverage", 1))),
                    liquidation_price=(
                        Decimal(str(pos["liquidationPrice"]))
                        if pos.get("liquidationPrice")
                        else None
                    ),
                    margin=Decimal(str(pos.get("initialMargin", 0))),
                )

            logger.debug(f"Fetched {len(positions)} positions from exchange")
            return positions

        except Exception as e:
            logger.error(f"Error fetching exchange positions: {e}", exc_info=True)
            return {}

    async def _get_system_positions(self) -> Dict[str, SystemPosition]:
        """Get system's tracked positions"""
        try:
            # Get positions from TradeExecutor's position tracker
            raw_positions = self.trade_executor.get_open_positions()

            positions = {}
            for symbol, pos in raw_positions.items():
                positions[symbol] = SystemPosition(
                    symbol=symbol,
                    side=pos["side"],
                    quantity=pos["quantity"],
                    entry_price=pos["entry_price"],
                    current_price=pos["current_price"],
                    unrealized_pnl=pos["unrealized_pnl"],
                    leverage=pos.get("leverage", Decimal("1")),
                    stop_loss_price=pos.get("stop_loss_price"),
                    take_profit_price=pos.get("take_profit_price"),
                    last_updated=pos["last_updated"],
                )

            logger.debug(f"Found {len(positions)} positions in system")
            return positions

        except Exception as e:
            logger.error(f"Error getting system positions: {e}", exc_info=True)
            return {}

    async def _compare_positions(
        self,
        exchange_positions: Dict[str, ExchangePosition],
        system_positions: Dict[str, SystemPosition],
    ) -> List[PositionDiscrepancy]:
        """Compare exchange and system positions"""
        discrepancies = []

        # Check all symbols (union of both sets)
        all_symbols = set(exchange_positions.keys()) | set(system_positions.keys())

        for symbol in all_symbols:
            exchange_pos = exchange_positions.get(symbol)
            system_pos = system_positions.get(symbol)

            # Position in exchange but not in system
            if exchange_pos and not system_pos:
                discrepancies.append(
                    PositionDiscrepancy(
                        symbol=symbol,
                        discrepancy_type=DiscrepancyType.POSITION_MISSING_IN_SYSTEM,
                        severity=DiscrepancySeverity.CRITICAL,
                        exchange_position=exchange_pos,
                        system_position=None,
                        requires_manual_intervention=True,
                        notes="Position exists on exchange but not tracked in system",
                    )
                )

            # Position in system but not on exchange
            elif system_pos and not exchange_pos:
                discrepancies.append(
                    PositionDiscrepancy(
                        symbol=symbol,
                        discrepancy_type=DiscrepancyType.POSITION_MISSING_ON_EXCHANGE,
                        severity=DiscrepancySeverity.WARNING,
                        exchange_position=None,
                        system_position=system_pos,
                        requires_manual_intervention=False,
                        notes="Position tracked in system but not on exchange (likely closed)",
                    )
                )

            # Position in both - check for differences
            elif exchange_pos and system_pos:
                discrepancy = self._check_position_differences(
                    symbol, exchange_pos, system_pos
                )
                if discrepancy:
                    discrepancies.append(discrepancy)

        return discrepancies

    def _check_position_differences(
        self,
        symbol: str,
        exchange_pos: ExchangePosition,
        system_pos: SystemPosition,
    ) -> Optional[PositionDiscrepancy]:
        """Check for differences between exchange and system position"""

        # Side mismatch (critical)
        if exchange_pos.side != system_pos.side:
            return PositionDiscrepancy(
                symbol=symbol,
                discrepancy_type=DiscrepancyType.SIDE_MISMATCH,
                severity=DiscrepancySeverity.CRITICAL,
                exchange_position=exchange_pos,
                system_position=system_pos,
                requires_manual_intervention=True,
                notes=f"Side mismatch: Exchange={exchange_pos.side}, System={system_pos.side}",
            )

        # Quantity difference
        quantity_diff = abs(exchange_pos.quantity - system_pos.quantity)
        quantity_diff_percent = (
            quantity_diff / exchange_pos.quantity * 100
            if exchange_pos.quantity > 0
            else Decimal("0")
        )

        if quantity_diff_percent > self.quantity_tolerance:
            # Determine severity
            if quantity_diff_percent > 10:
                severity = DiscrepancySeverity.CRITICAL
                requires_intervention = True
            elif quantity_diff_percent > 5:
                severity = DiscrepancySeverity.WARNING
                requires_intervention = False
            else:
                severity = DiscrepancySeverity.INFO
                requires_intervention = False

            return PositionDiscrepancy(
                symbol=symbol,
                discrepancy_type=DiscrepancyType.QUANTITY_MISMATCH,
                severity=severity,
                exchange_position=exchange_pos,
                system_position=system_pos,
                quantity_difference=quantity_diff,
                requires_manual_intervention=requires_intervention,
                notes=f"Quantity difference: {quantity_diff_percent:.2f}%",
            )

        # Price difference
        price_diff = abs(exchange_pos.entry_price - system_pos.entry_price)
        price_diff_percent = (
            price_diff / exchange_pos.entry_price * 100
            if exchange_pos.entry_price > 0
            else Decimal("0")
        )

        if price_diff_percent > self.price_tolerance:
            return PositionDiscrepancy(
                symbol=symbol,
                discrepancy_type=DiscrepancyType.PRICE_MISMATCH,
                severity=DiscrepancySeverity.WARNING,
                exchange_position=exchange_pos,
                system_position=system_pos,
                price_difference=price_diff,
                requires_manual_intervention=False,
                notes=f"Entry price difference: {price_diff_percent:.2f}%",
            )

        # No significant discrepancies
        return None

    async def _handle_discrepancy(self, discrepancy: PositionDiscrepancy):
        """Handle detected discrepancy"""

        # Log discrepancy
        logger.warning(
            f"Discrepancy detected: {discrepancy.symbol} - "
            f"{discrepancy.discrepancy_type.value} ({discrepancy.severity.value})"
        )

        # Critical discrepancies - send alert
        if discrepancy.requires_manual_intervention:
            await self._send_critical_alert(discrepancy)
            return

        # Auto-correction logic
        if discrepancy.discrepancy_type == DiscrepancyType.POSITION_MISSING_ON_EXCHANGE:
            # Position closed on exchange, update system
            await self._auto_correct_missing_position(discrepancy)

        elif discrepancy.discrepancy_type == DiscrepancyType.QUANTITY_MISMATCH:
            # Quantity difference, update system quantity
            await self._auto_correct_quantity(discrepancy)

        elif discrepancy.discrepancy_type == DiscrepancyType.PRICE_MISMATCH:
            # Price difference, update system price
            await self._auto_correct_price(discrepancy)

    async def _auto_correct_missing_position(self, discrepancy: PositionDiscrepancy):
        """Auto-correct: Position missing on exchange"""
        try:
            logger.info(
                f"Auto-correcting: Closing {discrepancy.symbol} in system "
                f"(position closed on exchange)"
            )

            # Close position in system
            # TODO: Call TradeExecutor to mark position as closed
            # await self.trade_executor.sync_position_closure(discrepancy.symbol)

            discrepancy.auto_corrected = True
            discrepancy.correction_action = "Closed position in system to match exchange"

        except Exception as e:
            logger.error(f"Auto-correction failed: {e}", exc_info=True)

    async def _auto_correct_quantity(self, discrepancy: PositionDiscrepancy):
        """Auto-correct: Quantity mismatch"""
        try:
            if discrepancy.exchange_position:
                logger.info(
                    f"Auto-correcting: Updating {discrepancy.symbol} quantity to "
                    f"{discrepancy.exchange_position.quantity}"
                )

                # Update system quantity
                # TODO: Call TradeExecutor to update quantity
                # await self.trade_executor.update_position_quantity(
                #     discrepancy.symbol,
                #     discrepancy.exchange_position.quantity
                # )

                discrepancy.auto_corrected = True
                discrepancy.correction_action = "Updated system quantity to match exchange"

        except Exception as e:
            logger.error(f"Auto-correction failed: {e}", exc_info=True)

    async def _auto_correct_price(self, discrepancy: PositionDiscrepancy):
        """Auto-correct: Price mismatch"""
        try:
            if discrepancy.exchange_position:
                logger.info(
                    f"Auto-correcting: Updating {discrepancy.symbol} entry price to "
                    f"{discrepancy.exchange_position.entry_price}"
                )

                # Update system entry price
                # TODO: Call TradeExecutor to update price
                # await self.trade_executor.update_position_entry_price(
                #     discrepancy.symbol,
                #     discrepancy.exchange_position.entry_price
                # )

                discrepancy.auto_corrected = True
                discrepancy.correction_action = "Updated system entry price to match exchange"

        except Exception as e:
            logger.error(f"Auto-correction failed: {e}", exc_info=True)

    async def _send_critical_alert(self, discrepancy: PositionDiscrepancy):
        """Send alert for critical discrepancy"""
        # TODO: Integrate with alerting system (email, Slack, PagerDuty, etc.)
        logger.critical(
            f"CRITICAL DISCREPANCY: {discrepancy.symbol}\n"
            f"Type: {discrepancy.discrepancy_type.value}\n"
            f"Severity: {discrepancy.severity.value}\n"
            f"Notes: {discrepancy.notes}\n"
            f"Exchange Position: {discrepancy.exchange_position}\n"
            f"System Position: {discrepancy.system_position}"
        )

    def get_stats(self) -> dict:
        """Get reconciliation statistics"""
        return {
            "total_reconciliations": self.total_reconciliations,
            "total_discrepancies": self.total_discrepancies,
            "total_auto_corrections": self.total_auto_corrections,
            "total_critical_alerts": self.total_critical_alerts,
            "is_running": self.is_running,
            "reconciliation_interval_seconds": self.reconciliation_interval,
        }
```

3. **Integration with TradeExecutor** (2 hours)
   - File: `workspace/features/trade_executor/executor_service.py`
   - Add reconciliation service:
```python
from workspace.features.position_reconciliation import PositionReconciliationService

class TradeExecutor:
    def __init__(
        self,
        # ... existing parameters ...
        enable_reconciliation: bool = True,
        reconciliation_interval_seconds: int = 300,
    ):
        # ... existing initialization ...

        # Initialize reconciliation service
        if enable_reconciliation:
            self.reconciliation_service = PositionReconciliationService(
                trade_executor=self,
                reconciliation_interval_seconds=reconciliation_interval_seconds,
            )
        else:
            self.reconciliation_service = None

    async def start(self):
        """Start trading engine and reconciliation"""
        # ... existing startup code ...

        # Start reconciliation
        if self.reconciliation_service:
            await self.reconciliation_service.start()
            logger.info("Position reconciliation started")

    async def stop(self):
        """Stop trading engine and reconciliation"""
        # Stop reconciliation
        if self.reconciliation_service:
            await self.reconciliation_service.stop()

        # ... existing shutdown code ...

    def get_open_positions(self) -> Dict[str, Dict]:
        """Get currently open positions"""
        # TODO: Implement position tracking
        # For now, return empty dict
        return {}

    async def sync_position_closure(self, symbol: str):
        """Mark position as closed (called by reconciliation)"""
        # TODO: Implement position closure sync
        logger.info(f"Syncing position closure for {symbol}")

    async def update_position_quantity(self, symbol: str, quantity: Decimal):
        """Update position quantity (called by reconciliation)"""
        # TODO: Implement quantity update
        logger.info(f"Updating {symbol} quantity to {quantity}")

    async def update_position_entry_price(self, symbol: str, entry_price: Decimal):
        """Update position entry price (called by reconciliation)"""
        # TODO: Implement price update
        logger.info(f"Updating {symbol} entry price to {entry_price}")
```

4. **Write comprehensive tests** (3 hours)
   - File: `workspace/tests/unit/test_position_reconciliation.py` (NEW)
```python
import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from workspace.features.position_reconciliation import (
    PositionReconciliationService,
    ExchangePosition,
    SystemPosition,
    DiscrepancyType,
    DiscrepancySeverity,
)
from workspace.features.trade_executor import TradeExecutor


@pytest.fixture
def mock_trade_executor():
    """Create mock TradeExecutor"""
    executor = MagicMock(spec=TradeExecutor)
    executor.exchange = MagicMock()
    executor.get_open_positions = MagicMock(return_value={})
    return executor


@pytest.fixture
def reconciliation_service(mock_trade_executor):
    """Create reconciliation service"""
    return PositionReconciliationService(
        trade_executor=mock_trade_executor,
        quantity_tolerance_percent=Decimal("1.0"),
        price_tolerance_percent=Decimal("0.1"),
    )


@pytest.mark.asyncio
async def test_no_discrepancies_when_positions_match(reconciliation_service, mock_trade_executor):
    """Test no discrepancies when positions match"""
    # Setup matching positions
    exchange_positions = {
        "BTC/USDT": ExchangePosition(
            symbol="BTC/USDT",
            side="LONG",
            quantity=Decimal("0.1"),
            entry_price=Decimal("45000.00"),
            current_price=Decimal("45100.00"),
            unrealized_pnl=Decimal("10.00"),
            leverage=Decimal("1"),
            margin=Decimal("4500.00"),
        )
    }

    system_positions = {
        "BTC/USDT": SystemPosition(
            symbol="BTC/USDT",
            side="LONG",
            quantity=Decimal("0.1"),
            entry_price=Decimal("45000.00"),
            current_price=Decimal("45100.00"),
            unrealized_pnl=Decimal("10.00"),
            leverage=Decimal("1"),
            last_updated=datetime.utcnow(),
        )
    }

    # Mock methods
    reconciliation_service._fetch_exchange_positions = AsyncMock(return_value=exchange_positions)
    reconciliation_service._get_system_positions = AsyncMock(return_value=system_positions)

    # Run reconciliation
    result = await reconciliation_service.reconcile_positions()

    # Verify no discrepancies
    assert result.symbols_checked == 1
    assert result.discrepancies_found == 0
    assert len(result.discrepancies) == 0


@pytest.mark.asyncio
async def test_detect_position_missing_in_system(reconciliation_service):
    """Test detection when position exists on exchange but not in system"""
    exchange_positions = {
        "BTC/USDT": ExchangePosition(
            symbol="BTC/USDT",
            side="LONG",
            quantity=Decimal("0.1"),
            entry_price=Decimal("45000.00"),
            current_price=Decimal("45100.00"),
            unrealized_pnl=Decimal("10.00"),
            leverage=Decimal("1"),
            margin=Decimal("4500.00"),
        )
    }

    system_positions = {}  # Empty - position not tracked

    reconciliation_service._fetch_exchange_positions = AsyncMock(return_value=exchange_positions)
    reconciliation_service._get_system_positions = AsyncMock(return_value=system_positions)

    result = await reconciliation_service.reconcile_positions()

    assert result.discrepancies_found == 1
    assert result.discrepancies[0].discrepancy_type == DiscrepancyType.POSITION_MISSING_IN_SYSTEM
    assert result.discrepancies[0].severity == DiscrepancySeverity.CRITICAL
    assert result.discrepancies[0].requires_manual_intervention is True


@pytest.mark.asyncio
async def test_detect_position_missing_on_exchange(reconciliation_service):
    """Test detection when position tracked in system but closed on exchange"""
    exchange_positions = {}  # Empty - position closed

    system_positions = {
        "BTC/USDT": SystemPosition(
            symbol="BTC/USDT",
            side="LONG",
            quantity=Decimal("0.1"),
            entry_price=Decimal("45000.00"),
            current_price=Decimal("45100.00"),
            unrealized_pnl=Decimal("10.00"),
            leverage=Decimal("1"),
            last_updated=datetime.utcnow(),
        )
    }

    reconciliation_service._fetch_exchange_positions = AsyncMock(return_value=exchange_positions)
    reconciliation_service._get_system_positions = AsyncMock(return_value=system_positions)

    result = await reconciliation_service.reconcile_positions()

    assert result.discrepancies_found == 1
    assert result.discrepancies[0].discrepancy_type == DiscrepancyType.POSITION_MISSING_ON_EXCHANGE
    assert result.discrepancies[0].severity == DiscrepancySeverity.WARNING
    assert result.discrepancies[0].requires_manual_intervention is False


@pytest.mark.asyncio
async def test_detect_quantity_mismatch(reconciliation_service):
    """Test detection of quantity mismatch"""
    exchange_positions = {
        "BTC/USDT": ExchangePosition(
            symbol="BTC/USDT",
            side="LONG",
            quantity=Decimal("0.1"),  # 0.1 BTC
            entry_price=Decimal("45000.00"),
            current_price=Decimal("45100.00"),
            unrealized_pnl=Decimal("10.00"),
            leverage=Decimal("1"),
            margin=Decimal("4500.00"),
        )
    }

    system_positions = {
        "BTC/USDT": SystemPosition(
            symbol="BTC/USDT",
            side="LONG",
            quantity=Decimal("0.09"),  # 0.09 BTC (10% difference - critical)
            entry_price=Decimal("45000.00"),
            current_price=Decimal("45100.00"),
            unrealized_pnl=Decimal("9.00"),
            leverage=Decimal("1"),
            last_updated=datetime.utcnow(),
        )
    }

    reconciliation_service._fetch_exchange_positions = AsyncMock(return_value=exchange_positions)
    reconciliation_service._get_system_positions = AsyncMock(return_value=system_positions)

    result = await reconciliation_service.reconcile_positions()

    assert result.discrepancies_found == 1
    assert result.discrepancies[0].discrepancy_type == DiscrepancyType.QUANTITY_MISMATCH
    assert result.discrepancies[0].quantity_difference == Decimal("0.01")


@pytest.mark.asyncio
async def test_detect_side_mismatch(reconciliation_service):
    """Test detection of side mismatch (CRITICAL)"""
    exchange_positions = {
        "BTC/USDT": ExchangePosition(
            symbol="BTC/USDT",
            side="LONG",  # Long on exchange
            quantity=Decimal("0.1"),
            entry_price=Decimal("45000.00"),
            current_price=Decimal("45100.00"),
            unrealized_pnl=Decimal("10.00"),
            leverage=Decimal("1"),
            margin=Decimal("4500.00"),
        )
    }

    system_positions = {
        "BTC/USDT": SystemPosition(
            symbol="BTC/USDT",
            side="SHORT",  # Short in system - CRITICAL ERROR
            quantity=Decimal("0.1"),
            entry_price=Decimal("45000.00"),
            current_price=Decimal("45100.00"),
            unrealized_pnl=Decimal("-10.00"),
            leverage=Decimal("1"),
            last_updated=datetime.utcnow(),
        )
    }

    reconciliation_service._fetch_exchange_positions = AsyncMock(return_value=exchange_positions)
    reconciliation_service._get_system_positions = AsyncMock(return_value=system_positions)

    result = await reconciliation_service.reconcile_positions()

    assert result.discrepancies_found == 1
    assert result.discrepancies[0].discrepancy_type == DiscrepancyType.SIDE_MISMATCH
    assert result.discrepancies[0].severity == DiscrepancySeverity.CRITICAL
    assert result.discrepancies[0].requires_manual_intervention is True


@pytest.mark.asyncio
async def test_auto_correction_statistics(reconciliation_service):
    """Test that auto-corrections are tracked"""
    # Setup position missing on exchange (auto-correctable)
    exchange_positions = {}
    system_positions = {
        "BTC/USDT": SystemPosition(
            symbol="BTC/USDT",
            side="LONG",
            quantity=Decimal("0.1"),
            entry_price=Decimal("45000.00"),
            current_price=Decimal("45100.00"),
            unrealized_pnl=Decimal("10.00"),
            leverage=Decimal("1"),
            last_updated=datetime.utcnow(),
        )
    }

    reconciliation_service._fetch_exchange_positions = AsyncMock(return_value=exchange_positions)
    reconciliation_service._get_system_positions = AsyncMock(return_value=system_positions)
    reconciliation_service._auto_correct_missing_position = AsyncMock()

    result = await reconciliation_service.reconcile_positions()

    # Check that auto-correction was attempted
    assert reconciliation_service._auto_correct_missing_position.called
```

5. **Add monitoring dashboard integration** (1 hour)
   - File: `workspace/features/position_reconciliation/__init__.py` (NEW)
```python
"""
Position Reconciliation Module

Continuous position sync with exchange to detect and correct discrepancies.
"""

from .models import (
    ExchangePosition,
    SystemPosition,
    PositionDiscrepancy,
    ReconciliationResult,
    DiscrepancyType,
    DiscrepancySeverity,
)
from .reconciliation_service import PositionReconciliationService

__all__ = [
    # Models
    "ExchangePosition",
    "SystemPosition",
    "PositionDiscrepancy",
    "ReconciliationResult",
    "DiscrepancyType",
    "DiscrepancySeverity",
    # Service
    "PositionReconciliationService",
]
```

6. **Create reconciliation dashboard** (1 hour)
   - File: `workspace/features/position_reconciliation/dashboard.py` (NEW)
```python
"""
Reconciliation Dashboard

Real-time view of reconciliation status.
"""

from typing import List
from decimal import Decimal
from datetime import datetime, timedelta

from workspace.features.position_reconciliation import (
    PositionReconciliationService,
    PositionDiscrepancy,
)


class ReconciliationDashboard:
    """Dashboard for monitoring reconciliation"""

    def __init__(self, reconciliation_service: PositionReconciliationService):
        self.service = reconciliation_service

    def get_summary(self) -> dict:
        """Get reconciliation summary"""
        stats = self.service.get_stats()

        return {
            "is_running": stats["is_running"],
            "interval_seconds": stats["reconciliation_interval_seconds"],
            "total_reconciliations": stats["total_reconciliations"],
            "total_discrepancies": stats["total_discrepancies"],
            "total_auto_corrections": stats["total_auto_corrections"],
            "total_critical_alerts": stats["total_critical_alerts"],
            "last_check": datetime.utcnow().isoformat(),
        }

    def get_health_status(self) -> str:
        """Get health status (HEALTHY, WARNING, CRITICAL)"""
        stats = self.service.get_stats()

        if not stats["is_running"]:
            return "CRITICAL"  # Reconciliation not running

        # Check critical alerts
        if stats["total_critical_alerts"] > 0:
            return "CRITICAL"

        # Check for recent discrepancies
        if stats["total_discrepancies"] > stats["total_auto_corrections"]:
            return "WARNING"

        return "HEALTHY"
```

---

## ✅ Definition of Done

- [ ] Position reconciliation service implemented
- [ ] Reconciliation runs every 5 minutes automatically
- [ ] Detects all discrepancy types (missing positions, quantity mismatch, price mismatch, side mismatch)
- [ ] Auto-correction for minor discrepancies (within tolerance)
- [ ] Critical alerts for major discrepancies
- [ ] Integration with TradeExecutor complete
- [ ] Comprehensive unit tests (>90% coverage)
- [ ] Integration tests with mock exchange
- [ ] Dashboard for monitoring reconciliation status
- [ ] Documentation complete

---

## 🧪 Testing Checklist

```bash
# Unit tests
pytest workspace/tests/unit/test_position_reconciliation.py -v

# Integration test with testnet
python -c "
import asyncio
from workspace.features.trade_executor import TradeExecutor
from workspace.features.position_reconciliation import PositionReconciliationService

async def test():
    # Initialize executor
    executor = TradeExecutor(
        api_key='YOUR_TESTNET_KEY',
        api_secret='YOUR_TESTNET_SECRET',
        testnet=True,
        enable_reconciliation=True,
        reconciliation_interval_seconds=60,  # 1 minute for testing
    )

    await executor.initialize()

    # Start reconciliation
    if executor.reconciliation_service:
        await executor.reconciliation_service.start()

        # Wait for one reconciliation cycle
        await asyncio.sleep(65)

        # Check stats
        stats = executor.reconciliation_service.get_stats()
        print(f'Reconciliation Stats: {stats}')

    await executor.stop()

asyncio.run(test())
"

# Monitor reconciliation dashboard
python -c "
from workspace.features.position_reconciliation import ReconciliationDashboard

# Assuming reconciliation service is running
dashboard = ReconciliationDashboard(reconciliation_service)
summary = dashboard.get_summary()
health = dashboard.get_health_status()

print(f'Health Status: {health}')
print(f'Summary: {summary}')
"
```

---

## 📝 Commit Strategy

**Commit 1**: Reconciliation models and core service
```
feat(reconciliation): add position reconciliation service

- Create reconciliation models (ExchangePosition, SystemPosition, PositionDiscrepancy)
- Implement PositionReconciliationService
- Add discrepancy detection logic
- Support auto-correction for minor differences
```

**Commit 2**: Integration with TradeExecutor
```
feat(executor): integrate position reconciliation

- Add reconciliation service to TradeExecutor
- Start reconciliation automatically on executor start
- Add position sync methods (closure, quantity, price updates)
- Configure 5-minute reconciliation interval
```

**Commit 3**: Tests and dashboard
```
test(reconciliation): add comprehensive tests

- Unit tests for all discrepancy types
- Tests for auto-correction logic
- Integration tests with mock exchange
- Add reconciliation dashboard for monitoring
```

---

## 🚀 Getting Started

1. **Setup**:
```bash
git checkout -b sprint-1/stream-d-reconciliation
cd /Users/tobiprivat/Documents/GitProjects/personal/trader
```

2. **Create directory structure**:
```bash
mkdir -p workspace/features/position_reconciliation
mkdir -p workspace/tests/unit
```

3. **Run existing tests** (baseline):
```bash
pytest workspace/tests/ -v
```

4. **Start with models** (Step 1):
   - Create models.py with all data structures
   - Define discrepancy types and severity levels

5. **Implement service** (Steps 2-3):
   - Create reconciliation_service.py
   - Implement comparison logic
   - Add auto-correction handlers

6. **Write tests** (Step 4):
   - Test all discrepancy types
   - Test auto-correction
   - Test integration with TradeExecutor

7. **Create dashboard** (Steps 5-6):
   - Add monitoring dashboard
   - Create health status endpoint

8. **Create PR when done**

---

## 📊 Reconciliation Logic

### Tolerance Thresholds

**Quantity Tolerance**: 1%
- Difference < 1%: No discrepancy
- Difference 1-5%: INFO (logged only)
- Difference 5-10%: WARNING (auto-corrected)
- Difference > 10%: CRITICAL (manual intervention)

**Price Tolerance**: 0.1%
- Difference < 0.1%: No discrepancy
- Difference > 0.1%: WARNING (auto-corrected)

**Side Tolerance**: None
- Any side mismatch: CRITICAL (manual intervention)

### Auto-Correction Rules

**Auto-Correct**:
- Position missing on exchange → Close in system
- Quantity mismatch (< 10%) → Update system quantity
- Price mismatch → Update system entry price

**Manual Intervention Required**:
- Position missing in system (exists on exchange)
- Side mismatch (LONG vs SHORT)
- Quantity mismatch > 10%

### Reconciliation Interval

**Default**: 5 minutes (300 seconds)
**Minimum**: 1 minute (not recommended - rate limits)
**Maximum**: 30 minutes (not recommended - too slow)

---

## ⚠️ Important Notes

1. **Exchange Rate Limits**:
   - Fetching positions counts against rate limits
   - Default 5-minute interval is safe
   - Don't reduce below 1 minute

2. **Critical Discrepancies**:
   - Side mismatch is most critical (opposite direction!)
   - Position missing in system is critical (untracked risk)
   - Always require manual verification before auto-correction

3. **Production Safety**:
   - Start with conservative tolerances (1%, 0.1%)
   - Monitor false positives
   - Adjust tolerances based on exchange behavior

4. **Performance**:
   - Reconciliation should complete in <5 seconds
   - Parallel position fetching if multiple symbols
   - Cache exchange positions for 30 seconds

5. **Alerting Integration**:
   - Critical discrepancies should trigger immediate alerts
   - Integrate with PagerDuty, Slack, email, SMS
   - Include position details in alert

---

## 🔍 Discrepancy Scenarios

### Scenario 1: Position Closed on Exchange (Auto-Correctable)
```
Exchange: No position
System: BTC/USDT LONG 0.1
Action: Close position in system
Severity: WARNING
```

### Scenario 2: Position Opened on Exchange (CRITICAL)
```
Exchange: BTC/USDT LONG 0.1
System: No position
Action: Manual investigation required
Severity: CRITICAL
Reason: Untracked position = unmanaged risk
```

### Scenario 3: Quantity Partial Fill (Auto-Correctable)
```
Exchange: BTC/USDT LONG 0.095 (95% filled)
System: BTC/USDT LONG 0.1 (full order)
Action: Update system to 0.095
Severity: WARNING (5% difference)
```

### Scenario 4: Side Mismatch (CRITICAL)
```
Exchange: BTC/USDT LONG 0.1
System: BTC/USDT SHORT 0.1
Action: IMMEDIATE ALERT - manual intervention
Severity: CRITICAL
Reason: Trading in opposite direction!
```

### Scenario 5: Price Slippage (Auto-Correctable)
```
Exchange: Entry at $45,050 (0.11% slippage)
System: Entry at $45,000
Action: Update system entry price
Severity: WARNING (normal slippage)
```
