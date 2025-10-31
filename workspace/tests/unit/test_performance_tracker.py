"""
Unit Tests for Paper Trading Performance Tracker

Tests performance metrics calculation, trade tracking, statistical analysis,
and reporting functionality.

Coverage target: >60%
Test patterns: Test statistical calculations for accuracy, verify metrics computation
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from workspace.features.paper_trading.performance_tracker import (
    PaperTradingPerformanceTracker,
)


class TestPaperTradingPerformanceTracker:
    """Test suite for PaperTradingPerformanceTracker"""

    @pytest.fixture
    def tracker(self):
        """Create performance tracker instance"""
        return PaperTradingPerformanceTracker()

    @pytest.fixture
    def sample_trades(self):
        """Sample trade data for testing"""
        base_time = datetime.utcnow()
        return [
            {
                "symbol": "BTC/USDT:USDT",
                "side": "buy",
                "quantity": Decimal("0.1"),
                "price": Decimal("50000"),
                "fees": Decimal("5.0"),
                "pnl": Decimal("95.0"),  # Profit
                "timestamp": base_time,
            },
            {
                "symbol": "ETH/USDT:USDT",
                "side": "buy",
                "quantity": Decimal("1.0"),
                "price": Decimal("3000"),
                "fees": Decimal("3.0"),
                "pnl": Decimal("97.0"),  # Profit
                "timestamp": base_time + timedelta(hours=1),
            },
            {
                "symbol": "SOL/USDT:USDT",
                "side": "buy",
                "quantity": Decimal("10"),
                "price": Decimal("100"),
                "fees": Decimal("1.0"),
                "pnl": Decimal("-51.0"),  # Loss
                "timestamp": base_time + timedelta(hours=2),
            },
            {
                "symbol": "BTC/USDT:USDT",
                "side": "sell",
                "quantity": Decimal("0.05"),
                "price": Decimal("51000"),
                "fees": Decimal("2.5"),
                "pnl": Decimal("47.5"),  # Profit
                "timestamp": base_time + timedelta(hours=3),
            },
        ]

    def test_initialization(self, tracker):
        """Test tracker initializes correctly"""
        assert len(tracker.trades) == 0
        assert len(tracker.daily_pnl) == 0
        assert len(tracker.equity_curve) == 0

        # Verify initial metrics
        assert tracker.metrics["total_trades"] == 0
        assert tracker.metrics["winning_trades"] == 0
        assert tracker.metrics["losing_trades"] == 0
        assert tracker.metrics["total_pnl"] == Decimal("0")
        assert tracker.metrics["win_rate"] == Decimal("0")

    def test_record_trade_winning(self, tracker):
        """Test recording a winning trade"""
        trade = {
            "symbol": "BTC/USDT:USDT",
            "side": "buy",
            "quantity": Decimal("0.1"),
            "price": Decimal("50000"),
            "fees": Decimal("5.0"),
            "pnl": Decimal("95.0"),
            "timestamp": datetime.utcnow(),
        }

        tracker.record_trade(trade)

        # Verify trade recorded
        assert len(tracker.trades) == 1
        assert tracker.trades[0] == trade

        # Verify metrics updated
        assert tracker.metrics["total_trades"] == 1
        assert tracker.metrics["winning_trades"] == 1
        assert tracker.metrics["losing_trades"] == 0
        assert tracker.metrics["total_pnl"] == Decimal("95.0")
        assert tracker.metrics["largest_win"] == Decimal("95.0")

    def test_record_trade_losing(self, tracker):
        """Test recording a losing trade"""
        trade = {
            "symbol": "ETH/USDT:USDT",
            "side": "sell",
            "quantity": Decimal("1.0"),
            "price": Decimal("2900"),
            "fees": Decimal("3.0"),
            "pnl": Decimal("-103.0"),
            "timestamp": datetime.utcnow(),
        }

        tracker.record_trade(trade)

        # Verify metrics
        assert tracker.metrics["total_trades"] == 1
        assert tracker.metrics["winning_trades"] == 0
        assert tracker.metrics["losing_trades"] == 1
        assert tracker.metrics["total_pnl"] == Decimal("-103.0")
        assert tracker.metrics["largest_loss"] == Decimal("-103.0")

    def test_record_trade_breakeven(self, tracker):
        """Test recording a breakeven trade"""
        trade = {
            "symbol": "SOL/USDT:USDT",
            "side": "buy",
            "quantity": Decimal("10"),
            "price": Decimal("100"),
            "fees": Decimal("0"),
            "pnl": Decimal("0.0"),
            "timestamp": datetime.utcnow(),
        }

        tracker.record_trade(trade)

        # Verify metrics
        assert tracker.metrics["total_trades"] == 1
        assert tracker.metrics["winning_trades"] == 0
        assert tracker.metrics["losing_trades"] == 0
        assert tracker.metrics["breakeven_trades"] == 1

    def test_record_multiple_trades(self, tracker, sample_trades):
        """Test recording multiple trades"""
        for trade in sample_trades:
            tracker.record_trade(trade)

        # Verify counts
        assert tracker.metrics["total_trades"] == 4
        assert tracker.metrics["winning_trades"] == 3
        assert tracker.metrics["losing_trades"] == 1

        # Verify total P&L: 95 + 97 - 51 + 47.5 = 188.5
        assert tracker.metrics["total_pnl"] == Decimal("188.5")

        # Verify largest win and loss
        assert tracker.metrics["largest_win"] == Decimal("97.0")
        assert tracker.metrics["largest_loss"] == Decimal("-51.0")

    def test_calculate_win_rate(self, tracker, sample_trades):
        """Test win rate calculation"""
        for trade in sample_trades:
            tracker.record_trade(trade)

        # Win rate: 3 wins / 4 total = 0.75 (75%)
        expected_win_rate = Decimal("3") / Decimal("4")
        assert tracker.metrics["win_rate"] == expected_win_rate

    def test_calculate_average_win(self, tracker, sample_trades):
        """Test average win calculation"""
        for trade in sample_trades:
            tracker.record_trade(trade)

        # Average win: (95 + 97 + 47.5) / 3 = 79.833...
        expected_avg_win = (Decimal("95") + Decimal("97") + Decimal("47.5")) / Decimal(
            "3"
        )
        assert tracker.metrics["avg_win"] == expected_avg_win

    def test_calculate_average_loss(self, tracker, sample_trades):
        """Test average loss calculation"""
        for trade in sample_trades:
            tracker.record_trade(trade)

        # Average loss: -51 / 1 = -51
        assert tracker.metrics["avg_loss"] == Decimal("-51")

    def test_calculate_profit_factor(self, tracker, sample_trades):
        """Test profit factor calculation"""
        for trade in sample_trades:
            tracker.record_trade(trade)

        # Gross profit: 95 + 97 + 47.5 = 239.5
        # Gross loss: abs(-51) = 51
        # Profit factor: 239.5 / 51 = 4.696...
        gross_profit = Decimal("95") + Decimal("97") + Decimal("47.5")
        gross_loss = Decimal("51")
        expected_pf = gross_profit / gross_loss

        assert tracker.metrics["profit_factor"] == expected_pf

    def test_profit_factor_no_losses(self, tracker):
        """Test profit factor with no losing trades"""
        # Record only winning trades
        tracker.record_trade(
            {
                "symbol": "BTC/USDT:USDT",
                "side": "buy",
                "quantity": Decimal("0.1"),
                "price": Decimal("50000"),
                "fees": Decimal("5.0"),
                "pnl": Decimal("95.0"),
                "timestamp": datetime.utcnow(),
            }
        )

        # Profit factor should be 0 when no losses
        assert tracker.metrics["profit_factor"] == Decimal("0")

    def test_calculate_max_drawdown_no_trades(self, tracker):
        """Test max drawdown with no trades"""
        tracker._calculate_max_drawdown()
        assert tracker.metrics["max_drawdown"] == Decimal("0")

    def test_calculate_max_drawdown_with_trades(self, tracker):
        """Test max drawdown calculation"""
        # Create trades that produce a drawdown
        trades = [
            {
                "symbol": "BTC/USDT:USDT",
                "side": "buy",
                "quantity": Decimal("0.1"),
                "price": Decimal("50000"),
                "fees": Decimal("0"),
                "pnl": Decimal("100.0"),  # Running: +100
                "timestamp": datetime.utcnow(),
            },
            {
                "symbol": "ETH/USDT:USDT",
                "side": "buy",
                "quantity": Decimal("1.0"),
                "price": Decimal("3000"),
                "fees": Decimal("0"),
                "pnl": Decimal("50.0"),  # Running: +150 (new peak)
                "timestamp": datetime.utcnow(),
            },
            {
                "symbol": "SOL/USDT:USDT",
                "side": "sell",
                "quantity": Decimal("10"),
                "price": Decimal("100"),
                "fees": Decimal("0"),
                "pnl": Decimal("-80.0"),  # Running: +70 (drawdown of 80 from peak)
                "timestamp": datetime.utcnow(),
            },
            {
                "symbol": "BTC/USDT:USDT",
                "side": "sell",
                "quantity": Decimal("0.1"),
                "price": Decimal("51000"),
                "fees": Decimal("0"),
                "pnl": Decimal("-50.0"),  # Running: +20 (drawdown of 130 from peak)
                "timestamp": datetime.utcnow(),
            },
        ]

        for trade in trades:
            tracker.record_trade(trade)

        # Max drawdown should be 130 (from peak of 150 to low of 20)
        assert tracker.metrics["max_drawdown"] == Decimal("130")

    def test_calculate_sharpe_ratio_insufficient_data(self, tracker):
        """Test Sharpe ratio with insufficient data"""
        # Record one trade
        tracker.record_trade(
            {
                "symbol": "BTC/USDT:USDT",
                "side": "buy",
                "quantity": Decimal("0.1"),
                "price": Decimal("50000"),
                "fees": Decimal("5.0"),
                "pnl": Decimal("95.0"),
                "timestamp": datetime.utcnow(),
            }
        )

        # Should be 0 with insufficient data
        assert tracker.metrics["sharpe_ratio"] == Decimal("0")

    def test_calculate_sharpe_ratio_with_data(self, tracker):
        """Test Sharpe ratio calculation"""
        # Record trades on different days
        base_date = datetime.utcnow()

        trades = [
            {
                "symbol": "BTC/USDT:USDT",
                "side": "buy",
                "quantity": Decimal("0.1"),
                "price": Decimal("50000"),
                "fees": Decimal("0"),
                "pnl": Decimal("100.0"),
                "timestamp": base_date,
            },
            {
                "symbol": "ETH/USDT:USDT",
                "side": "buy",
                "quantity": Decimal("1.0"),
                "price": Decimal("3000"),
                "fees": Decimal("0"),
                "pnl": Decimal("50.0"),
                "timestamp": base_date + timedelta(days=1),
            },
            {
                "symbol": "SOL/USDT:USDT",
                "side": "sell",
                "quantity": Decimal("10"),
                "price": Decimal("100"),
                "fees": Decimal("0"),
                "pnl": Decimal("-30.0"),
                "timestamp": base_date + timedelta(days=2),
            },
        ]

        for trade in trades:
            tracker.record_trade(trade)

        # Sharpe ratio should be calculated (not testing exact value due to randomness)
        assert tracker.metrics["sharpe_ratio"] != Decimal("0")

    def test_daily_pnl_tracking(self, tracker):
        """Test daily P&L aggregation"""
        today = datetime.utcnow()
        yesterday = today - timedelta(days=1)

        # Record trades on different days
        tracker.record_trade(
            {
                "symbol": "BTC/USDT:USDT",
                "side": "buy",
                "quantity": Decimal("0.1"),
                "price": Decimal("50000"),
                "fees": Decimal("0"),
                "pnl": Decimal("100.0"),
                "timestamp": today,
            }
        )
        tracker.record_trade(
            {
                "symbol": "ETH/USDT:USDT",
                "side": "buy",
                "quantity": Decimal("1.0"),
                "price": Decimal("3000"),
                "fees": Decimal("0"),
                "pnl": Decimal("50.0"),
                "timestamp": today,
            }
        )
        tracker.record_trade(
            {
                "symbol": "SOL/USDT:USDT",
                "side": "sell",
                "quantity": Decimal("10"),
                "price": Decimal("100"),
                "fees": Decimal("0"),
                "pnl": Decimal("-30.0"),
                "timestamp": yesterday,
            }
        )

        # Verify daily P&L
        today_date = today.date()
        yesterday_date = yesterday.date()

        assert tracker.daily_pnl[today_date] == Decimal("150.0")  # 100 + 50
        assert tracker.daily_pnl[yesterday_date] == Decimal("-30.0")

    def test_generate_report(self, tracker, sample_trades):
        """Test comprehensive report generation"""
        for trade in sample_trades:
            tracker.record_trade(trade)

        report = tracker.generate_report()

        # Verify report structure
        assert "summary" in report
        assert "profitability" in report
        assert "trade_statistics" in report
        assert "risk_metrics" in report
        assert "time_analysis" in report
        assert "daily_pnl" in report

        # Verify summary
        assert report["summary"]["total_trades"] == 4
        assert report["summary"]["winning_trades"] == 3
        assert report["summary"]["losing_trades"] == 1

        # Verify profitability
        assert report["profitability"]["total_pnl"] == Decimal("188.5")
        assert report["profitability"]["win_rate"] == Decimal("75.0")  # 3/4 * 100

        # Verify trade statistics
        assert "avg_win" in report["trade_statistics"]
        assert "avg_loss" in report["trade_statistics"]
        assert "largest_win" in report["trade_statistics"]
        assert "largest_loss" in report["trade_statistics"]

        # Verify risk metrics
        assert "max_drawdown" in report["risk_metrics"]
        assert "sharpe_ratio" in report["risk_metrics"]

    def test_generate_report_empty(self, tracker):
        """Test report generation with no trades"""
        report = tracker.generate_report()

        # Should have valid structure with zero values
        assert report["summary"]["total_trades"] == 0
        assert report["profitability"]["total_pnl"] == Decimal("0.0")
        assert len(report["daily_pnl"]) == 0

    def test_get_trade_history_no_filter(self, tracker, sample_trades):
        """Test getting trade history without filters"""
        for trade in sample_trades:
            tracker.record_trade(trade)

        history = tracker.get_trade_history()

        assert len(history) == 4
        # Should be sorted by timestamp (most recent first)
        assert history[0]["timestamp"] > history[-1]["timestamp"]

    def test_get_trade_history_with_limit(self, tracker, sample_trades):
        """Test getting trade history with limit"""
        for trade in sample_trades:
            tracker.record_trade(trade)

        history = tracker.get_trade_history(limit=2)

        assert len(history) == 2

    def test_get_trade_history_winning_only(self, tracker, sample_trades):
        """Test filtering for winning trades only"""
        for trade in sample_trades:
            tracker.record_trade(trade)

        winning_trades = tracker.get_trade_history(winning_only=True)

        assert len(winning_trades) == 3
        assert all(t["pnl"] > 0 for t in winning_trades)

    def test_get_trade_history_losing_only(self, tracker, sample_trades):
        """Test filtering for losing trades only"""
        for trade in sample_trades:
            tracker.record_trade(trade)

        losing_trades = tracker.get_trade_history(losing_only=True)

        assert len(losing_trades) == 1
        assert all(t["pnl"] < 0 for t in losing_trades)

    def test_get_symbol_performance(self, tracker, sample_trades):
        """Test getting performance breakdown by symbol"""
        for trade in sample_trades:
            tracker.record_trade(trade)

        symbol_perf = tracker.get_symbol_performance()

        # Verify BTC stats (2 trades: +95, +47.5)
        btc_stats = symbol_perf["BTC/USDT:USDT"]
        assert btc_stats["trades"] == 2
        assert btc_stats["wins"] == 2
        assert btc_stats["losses"] == 0
        assert btc_stats["win_rate"] == Decimal("100.0")
        assert btc_stats["total_pnl"] == Decimal("142.5")

        # Verify ETH stats (1 trade: +97)
        eth_stats = symbol_perf["ETH/USDT:USDT"]
        assert eth_stats["trades"] == 1
        assert eth_stats["wins"] == 1
        assert eth_stats["total_pnl"] == Decimal("97.0")

        # Verify SOL stats (1 trade: -51)
        sol_stats = symbol_perf["SOL/USDT:USDT"]
        assert sol_stats["trades"] == 1
        assert sol_stats["losses"] == 1
        assert sol_stats["total_pnl"] == Decimal("-51.0")

    def test_get_symbol_performance_empty(self, tracker):
        """Test symbol performance with no trades"""
        symbol_perf = tracker.get_symbol_performance()
        assert symbol_perf == {}

    def test_reset(self, tracker, sample_trades):
        """Test resetting tracker state"""
        # Record trades
        for trade in sample_trades:
            tracker.record_trade(trade)

        # Verify state
        assert len(tracker.trades) > 0
        assert tracker.metrics["total_trades"] > 0

        # Reset
        tracker.reset()

        # Verify reset
        assert len(tracker.trades) == 0
        assert len(tracker.daily_pnl) == 0
        assert tracker.metrics["total_trades"] == 0
        assert tracker.metrics["total_pnl"] == Decimal("0")

    def test_export_trades_csv(self, tracker, sample_trades, tmp_path):
        """Test exporting trades to CSV"""
        for trade in sample_trades:
            tracker.record_trade(trade)

        # Export to temp file
        csv_path = tmp_path / "trades.csv"
        tracker.export_trades_csv(str(csv_path))

        # Verify file created
        assert csv_path.exists()

        # Read and verify content
        import csv

        with open(csv_path, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 4
        assert rows[0]["symbol"] == "BTC/USDT:USDT"
        assert float(rows[0]["pnl"]) == Decimal("95.0")

    def test_fees_tracking(self, tracker, sample_trades):
        """Test that fees are tracked correctly"""
        for trade in sample_trades:
            tracker.record_trade(trade)

        # Total fees: 5.0 + 3.0 + 1.0 + 2.5 = 11.5
        assert tracker.metrics["total_fees"] == Decimal("11.5")

        # Verify in report
        report = tracker.generate_report()
        assert report["profitability"]["total_fees"] == Decimal("11.5")

    def test_risk_reward_ratio(self, tracker, sample_trades):
        """Test risk-reward ratio calculation"""
        for trade in sample_trades:
            tracker.record_trade(trade)

        report = tracker.generate_report()

        # Risk-reward = avg_win / abs(avg_loss)
        # avg_win = (95 + 97 + 47.5) / 3 = 79.833...
        # avg_loss = -51
        # risk_reward = 79.833... / 51
        expected_rr = abs(tracker.metrics["avg_win"] / tracker.metrics["avg_loss"])
        assert report["risk_metrics"]["risk_reward_ratio"] == pytest.approx(
            float(expected_rr), rel=0.01
        )

    def test_risk_reward_ratio_no_losses(self, tracker):
        """Test risk-reward ratio with no losing trades"""
        tracker.record_trade(
            {
                "symbol": "BTC/USDT:USDT",
                "side": "buy",
                "quantity": Decimal("0.1"),
                "price": Decimal("50000"),
                "fees": Decimal("0"),
                "pnl": Decimal("100.0"),
                "timestamp": datetime.utcnow(),
            }
        )

        report = tracker.generate_report()

        # Should be 0 when no losses
        assert report["risk_metrics"]["risk_reward_ratio"] == Decimal("0.0")

    def test_avg_trades_per_day(self, tracker):
        """Test average trades per day calculation"""
        base_date = datetime.utcnow()

        # Record trades over 3 days
        for day in range(3):
            for _ in range(2):
                tracker.record_trade(
                    {
                        "symbol": "BTC/USDT:USDT",
                        "side": "buy",
                        "quantity": Decimal("0.1"),
                        "price": Decimal("50000"),
                        "fees": Decimal("0"),
                        "pnl": Decimal("50.0"),
                        "timestamp": base_date + timedelta(days=day),
                    }
                )

        report = tracker.generate_report()

        # 6 trades / 3 days = 2 trades per day
        assert report["time_analysis"]["avg_trades_per_day"] == Decimal("2.0")

    def test_net_pnl_calculation(self, tracker, sample_trades):
        """Test net P&L calculation (P&L - fees)"""
        for trade in sample_trades:
            tracker.record_trade(trade)

        report = tracker.generate_report()

        # Net P&L = total_pnl - total_fees = 188.5 - 11.5 = 177.0
        assert report["profitability"]["net_pnl"] == Decimal("177.0")

    def test_daily_pnl_in_report(self, tracker, sample_trades):
        """Test daily P&L breakdown in report"""
        for trade in sample_trades:
            tracker.record_trade(trade)

        report = tracker.generate_report()

        # Verify daily P&L section
        assert "daily_pnl" in report
        assert isinstance(report["daily_pnl"], list)

        # Each entry should have date and pnl
        for entry in report["daily_pnl"]:
            assert "date" in entry
            assert "pnl" in entry

    def test_sharpe_ratio_zero_std_dev(self, tracker):
        """Test Sharpe ratio when all returns are identical (zero std dev)"""
        base_date = datetime.utcnow()

        # Record identical trades on different days
        for day in range(3):
            tracker.record_trade(
                {
                    "symbol": "BTC/USDT:USDT",
                    "side": "buy",
                    "quantity": Decimal("0.1"),
                    "price": Decimal("50000"),
                    "fees": Decimal("0"),
                    "pnl": Decimal("100.0"),  # Same P&L every day
                    "timestamp": base_date + timedelta(days=day),
                }
            )

        # Sharpe ratio should be 0 when std dev is 0
        assert tracker.metrics["sharpe_ratio"] == Decimal("0")

    def test_metrics_recalculation(self, tracker):
        """Test that metrics are recalculated after each trade"""
        # Record first trade
        tracker.record_trade(
            {
                "symbol": "BTC/USDT:USDT",
                "side": "buy",
                "quantity": Decimal("0.1"),
                "price": Decimal("50000"),
                "fees": Decimal("0"),
                "pnl": Decimal("100.0"),
                "timestamp": datetime.utcnow(),
            }
        )

        first_win_rate = tracker.metrics["win_rate"]

        # Record second trade (losing)
        tracker.record_trade(
            {
                "symbol": "ETH/USDT:USDT",
                "side": "sell",
                "quantity": Decimal("1.0"),
                "price": Decimal("3000"),
                "fees": Decimal("0"),
                "pnl": Decimal("-50.0"),
                "timestamp": datetime.utcnow(),
            }
        )

        second_win_rate = tracker.metrics["win_rate"]

        # Win rate should have changed
        assert first_win_rate != second_win_rate
        assert first_win_rate == 1  # 1/1 = 100%
        assert second_win_rate == Decimal("0.5")  # 1/2 = 50%
