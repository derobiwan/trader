#!/usr/bin/env python3
"""
7-Day Paper Trading Test Runner

Runs paper trading for 7 days (simulated or real-time) and generates
comprehensive performance reports.

Usage:
    # Simulated (fast) mode - completes in minutes
    python scripts/run_paper_trading_test.py --mode simulated --cycles 3360

    # Real-time mode - runs for 7 days
    python scripts/run_paper_trading_test.py --mode realtime --duration-days 7

Author: Implementation Specialist (Sprint 2 Stream B)
Date: 2025-10-29
"""

import asyncio
import logging
import argparse
import os
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from workspace.features.trading_loop import TradingEngine  # noqa: E402
from workspace.features.market_data import MarketDataService  # noqa: E402


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("paper_trading_test.log"), logging.StreamHandler()],
)

logger = logging.getLogger(__name__)


class PaperTradingTestRunner:
    """
    7-Day Paper Trading Test Runner

    Runs paper trading simulation for specified duration and generates
    comprehensive performance reports.
    """

    def __init__(
        self,
        mode: str = "simulated",
        duration_days: int = 7,
        cycles: int = 3360,  # 7 days * 480 cycles/day
        initial_balance: Decimal = Decimal("10000"),
        symbols: list = None,
    ):
        """
        Initialize test runner

        Args:
            mode: 'simulated' (fast) or 'realtime' (actual 7 days)
            duration_days: Duration in days (for realtime mode)
            cycles: Number of cycles to run (for simulated mode)
            initial_balance: Starting balance in USDT
            symbols: List of trading pairs (default: BTC, ETH, SOL)
        """
        self.mode = mode
        self.duration_days = duration_days
        self.cycles = cycles
        self.initial_balance = initial_balance
        self.symbols = symbols or [
            "BTC/USDT:USDT",
            "ETH/USDT:USDT",
            "SOL/USDT:USDT",
        ]

        self.engine = None
        self.start_time = None
        self.end_time = None
        self.results = []

    async def setup(self):
        """Setup trading engine and services"""
        logger.info(f"Setting up paper trading test ({self.mode} mode)")

        # Get API credentials from environment
        api_key = os.getenv("BYBIT_API_KEY")
        api_secret = os.getenv("BYBIT_API_SECRET")

        if not api_key or not api_secret:
            raise ValueError(
                "BYBIT_API_KEY and BYBIT_API_SECRET environment variables required"
            )

        # Initialize market data service
        market_data = MarketDataService(
            api_key=api_key,
            api_secret=api_secret,
            testnet=True,
        )
        await market_data.initialize()

        # Initialize trading engine in paper trading mode
        self.engine = TradingEngine(
            market_data_service=market_data,
            symbols=self.symbols,
            paper_trading=True,
            paper_trading_initial_balance=self.initial_balance,
            api_key=api_key,
            api_secret=api_secret,
        )

        await self.engine.trade_executor.initialize()

        logger.info(
            f"Paper trading engine initialized with ${self.initial_balance} USDT"
        )

    async def run_simulated(self):
        """Run simulated paper trading (fast mode)"""
        logger.info(f"Running {self.cycles} simulated trading cycles")

        self.start_time = datetime.utcnow()

        for cycle in range(1, self.cycles + 1):
            try:
                # Execute trading cycle
                result = await self.engine.execute_trading_cycle(cycle)
                self.results.append(result)

                # Log progress every 100 cycles
                if cycle % 100 == 0:
                    logger.info(
                        f"Progress: {cycle}/{self.cycles} cycles "
                        f"({cycle / self.cycles * 100:.1f}%)"
                    )

                    # Log current performance
                    report = self.engine.get_paper_trading_report()
                    if report:
                        logger.info(
                            f"Current balance: ${report['portfolio']['current_balance']:.2f} "
                            f"(Return: {report['portfolio']['total_return']:.2f}%)"
                        )

                # Small delay to avoid rate limits
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Cycle {cycle} failed: {e}", exc_info=True)

        self.end_time = datetime.utcnow()

        logger.info(
            f"Simulated test complete: {self.cycles} cycles in "
            f"{(self.end_time - self.start_time).total_seconds():.1f} seconds"
        )

    async def run_realtime(self):
        """Run real-time paper trading (7-day mode)"""
        logger.info(f"Running real-time paper trading for {self.duration_days} days")

        self.start_time = datetime.utcnow()
        end_time = self.start_time + timedelta(days=self.duration_days)

        cycle = 1

        while datetime.utcnow() < end_time:
            try:
                # Execute trading cycle
                result = await self.engine.execute_trading_cycle(cycle)
                self.results.append(result)

                # Log progress
                elapsed = datetime.utcnow() - self.start_time
                remaining = end_time - datetime.utcnow()

                logger.info(
                    f"Cycle {cycle} complete | "
                    f"Elapsed: {elapsed} | Remaining: {remaining}"
                )

                # Log performance every hour
                if cycle % 20 == 0:  # 20 cycles = 1 hour
                    report = self.engine.get_paper_trading_report()
                    if report:
                        logger.info(
                            f"Current balance: ${report['portfolio']['current_balance']:.2f} "
                            f"(Return: {report['portfolio']['total_return']:.2f}%)"
                        )

                cycle += 1

                # Wait for next cycle (3 minutes)
                await asyncio.sleep(180)

            except Exception as e:
                logger.error(f"Cycle {cycle} failed: {e}", exc_info=True)
                await asyncio.sleep(180)

        self.end_time = datetime.utcnow()

        logger.info(
            f"Real-time test complete: {cycle} cycles over {self.duration_days} days"
        )

    async def generate_report(self):
        """Generate comprehensive test report"""
        logger.info("Generating test report")

        # Get paper trading performance report
        report = self.engine.get_paper_trading_report()

        if not report:
            logger.error("Failed to generate report")
            return

        # Add test metadata
        report["test_metadata"] = {
            "mode": self.mode,
            "duration_days": self.duration_days,
            "total_cycles": len(self.results),
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "elapsed_seconds": (self.end_time - self.start_time).total_seconds(),
            "symbols": self.symbols,
        }

        # Add cycle statistics
        successful_cycles = sum(1 for r in self.results if r.success)
        report["cycle_statistics"] = {
            "total_cycles": len(self.results),
            "successful_cycles": successful_cycles,
            "failed_cycles": len(self.results) - successful_cycles,
            "success_rate": (
                successful_cycles / len(self.results) * 100 if self.results else 0
            ),
            "avg_cycle_duration": (
                sum(r.duration_seconds for r in self.results) / len(self.results)
                if self.results
                else 0
            ),
        }

        # Save report to file
        report_filename = (
            f"paper_trading_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        )
        report_path = Path("reports") / report_filename

        # Create reports directory if needed
        report_path.parent.mkdir(parents=True, exist_ok=True)

        with open(report_path, "w") as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"Report saved to {report_path}")

        # Print summary to console
        print("\n" + "=" * 80)
        print("PAPER TRADING TEST REPORT")
        print("=" * 80)
        print(f"\nTest Mode: {self.mode}")
        print(f"Duration: {self.duration_days} days")
        print(f"Total Cycles: {len(self.results)}")
        print(f"Success Rate: {report['cycle_statistics']['success_rate']:.2f}%")

        print("\n--- Portfolio Performance ---")
        print(f"Initial Balance: ${report['portfolio']['initial_balance']:.2f}")
        print(f"Final Balance: ${report['portfolio']['current_balance']:.2f}")
        print(f"Total Return: {report['portfolio']['total_return']:.2f}%")
        print(f"Open Positions: {report['portfolio']['open_positions']}")

        print("\n--- Trading Statistics ---")
        print(f"Total Trades: {report['summary']['total_trades']}")
        print(f"Winning Trades: {report['summary']['winning_trades']}")
        print(f"Losing Trades: {report['summary']['losing_trades']}")
        print(f"Win Rate: {report['profitability']['win_rate']:.2f}%")

        print("\n--- Profitability ---")
        print(f"Total P&L: ${report['profitability']['total_pnl']:.2f}")
        print(f"Total Fees: ${report['profitability']['total_fees']:.2f}")
        print(f"Net P&L: ${report['profitability']['net_pnl']:.2f}")
        print(f"Profit Factor: {report['profitability']['profit_factor']:.2f}")

        print("\n--- Risk Metrics ---")
        print(f"Max Drawdown: ${report['risk_metrics']['max_drawdown']:.2f}")
        print(f"Sharpe Ratio: {report['risk_metrics']['sharpe_ratio']:.2f}")
        print(f"Risk/Reward: {report['risk_metrics']['risk_reward_ratio']:.2f}")

        print("\n" + "=" * 80)
        print(f"Full report: {report_path}")
        print("=" * 80 + "\n")

        return report

    async def run(self):
        """Run complete test"""
        try:
            # Setup
            await self.setup()

            # Run test based on mode
            if self.mode == "simulated":
                await self.run_simulated()
            else:
                await self.run_realtime()

            # Generate report
            await self.generate_report()

        except Exception as e:
            logger.error(f"Test failed: {e}", exc_info=True)
            raise

        finally:
            # Cleanup
            if self.engine and self.engine.trade_executor:
                await self.engine.trade_executor.close()


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Run 7-day paper trading test")

    parser.add_argument(
        "--mode",
        choices=["simulated", "realtime"],
        default="simulated",
        help="Test mode: simulated (fast) or realtime (actual 7 days)",
    )

    parser.add_argument(
        "--duration-days",
        type=int,
        default=7,
        help="Duration in days (for realtime mode)",
    )

    parser.add_argument(
        "--cycles",
        type=int,
        default=3360,
        help="Number of cycles (for simulated mode, default: 3360 = 7 days)",
    )

    parser.add_argument(
        "--initial-balance",
        type=float,
        default=10000.0,
        help="Initial balance in USDT (default: 10000)",
    )

    args = parser.parse_args()

    # Create and run test
    runner = PaperTradingTestRunner(
        mode=args.mode,
        duration_days=args.duration_days,
        cycles=args.cycles,
        initial_balance=Decimal(str(args.initial_balance)),
    )

    await runner.run()


if __name__ == "__main__":
    asyncio.run(main())
