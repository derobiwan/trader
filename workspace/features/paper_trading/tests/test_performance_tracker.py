"""
Tests for Paper Trading Performance Tracker

Tests performance tracking and metrics calculation.

Author: Implementation Specialist (Sprint 2 Stream B)
Date: 2025-10-29
"""

import os
import tempfile
from datetime import datetime
from decimal import Decimal

import pytest

from workspace.features.paper_trading import PaperTradingPerformanceTracker


@pytest.fixture
def tracker():
    """Create performance tracker for testing"""
    return PaperTradingPerformanceTracker()


def test_tracker_initialization(tracker):
    """Test performance tracker initialization"""
    assert len(tracker.trades) == 0
    assert len(tracker.daily_pnl) == 0
    assert tracker.metrics["total_trades"] == 0
    assert tracker.metrics["total_pnl"] == Decimal("0")


def test_record_winning_trade(tracker):
    """Test recording a winning trade"""
    trade = {
        "symbol": "BTC/USDT:USDT",
        "side": "buy",
        "quantity": 0.1,
        "price": 45000.0,
        "fees": 4.5,
        "pnl": 95.4,  # $100 profit - $4.6 fees
        "timestamp": datetime.utcnow(),
    }

    tracker.record_trade(trade)

    # Verify metrics updated
    assert tracker.metrics["total_trades"] == 1
    assert tracker.metrics["winning_trades"] == 1
    assert tracker.metrics["losing_trades"] == 0
    assert tracker.metrics["total_pnl"] == Decimal("95.4")
    assert tracker.metrics["largest_win"] == Decimal("95.4")


def test_record_losing_trade(tracker):
    """Test recording a losing trade"""
    trade = {
        "symbol": "BTC/USDT:USDT",
        "side": "buy",
        "quantity": 0.1,
        "price": 45000.0,
        "fees": 4.5,
        "pnl": -104.5,  # -$100 loss - $4.5 fees
        "timestamp": datetime.utcnow(),
    }

    tracker.record_trade(trade)

    # Verify metrics updated
    assert tracker.metrics["total_trades"] == 1
    assert tracker.metrics["winning_trades"] == 0
    assert tracker.metrics["losing_trades"] == 1
    assert tracker.metrics["total_pnl"] == Decimal("-104.5")
    assert tracker.metrics["largest_loss"] == Decimal("-104.5")


def test_calculate_win_rate(tracker):
    """Test win rate calculation"""
    # Record 3 wins and 2 losses
    for _i in range(3):
        tracker.record_trade(
            {
                "symbol": "BTC/USDT:USDT",
                "side": "buy",
                "quantity": 0.1,
                "price": 45000.0,
                "fees": 4.5,
                "pnl": 50.0,
                "timestamp": datetime.utcnow(),
            }
        )

    for _i in range(2):
        tracker.record_trade(
            {
                "symbol": "BTC/USDT:USDT",
                "side": "buy",
                "quantity": 0.1,
                "price": 45000.0,
                "fees": 4.5,
                "pnl": -30.0,
                "timestamp": datetime.utcnow(),
            }
        )

    # Verify win rate = 3/5 = 60%
    assert tracker.metrics["win_rate"] == Decimal("0.6")
    assert tracker.metrics["total_trades"] == 5
    assert tracker.metrics["winning_trades"] == 3
    assert tracker.metrics["losing_trades"] == 2


def test_calculate_average_winloss(tracker):
    """Test average win/loss calculation"""
    # Record 2 wins with different profits
    tracker.record_trade(
        {
            "symbol": "BTC/USDT:USDT",
            "side": "buy",
            "quantity": 0.1,
            "price": 45000.0,
            "fees": 4.5,
            "pnl": 100.0,
            "timestamp": datetime.utcnow(),
        }
    )

    tracker.record_trade(
        {
            "symbol": "BTC/USDT:USDT",
            "side": "buy",
            "quantity": 0.1,
            "price": 45000.0,
            "fees": 4.5,
            "pnl": 50.0,
            "timestamp": datetime.utcnow(),
        }
    )

    # Record 2 losses
    tracker.record_trade(
        {
            "symbol": "BTC/USDT:USDT",
            "side": "buy",
            "quantity": 0.1,
            "price": 45000.0,
            "fees": 4.5,
            "pnl": -40.0,
            "timestamp": datetime.utcnow(),
        }
    )

    tracker.record_trade(
        {
            "symbol": "BTC/USDT:USDT",
            "side": "buy",
            "quantity": 0.1,
            "price": 45000.0,
            "fees": 4.5,
            "pnl": -60.0,
            "timestamp": datetime.utcnow(),
        }
    )

    # Verify averages
    assert tracker.metrics["avg_win"] == Decimal("75.0")  # (100 + 50) / 2
    assert tracker.metrics["avg_loss"] == Decimal("-50.0")  # (-40 + -60) / 2


def test_calculate_profit_factor(tracker):
    """Test profit factor calculation"""
    # Gross profit: $150
    tracker.record_trade(
        {
            "symbol": "BTC/USDT:USDT",
            "side": "buy",
            "quantity": 0.1,
            "price": 45000.0,
            "fees": 4.5,
            "pnl": 150.0,
            "timestamp": datetime.utcnow(),
        }
    )

    # Gross loss: $50
    tracker.record_trade(
        {
            "symbol": "BTC/USDT:USDT",
            "side": "buy",
            "quantity": 0.1,
            "price": 45000.0,
            "fees": 4.5,
            "pnl": -50.0,
            "timestamp": datetime.utcnow(),
        }
    )

    # Profit factor = 150 / 50 = 3.0
    assert tracker.metrics["profit_factor"] == Decimal("3.0")


def test_daily_pnl_tracking(tracker):
    """Test daily P&L tracking"""
    today = datetime.utcnow()

    # Record multiple trades on same day
    for _i in range(3):
        tracker.record_trade(
            {
                "symbol": "BTC/USDT:USDT",
                "side": "buy",
                "quantity": 0.1,
                "price": 45000.0,
                "fees": 4.5,
                "pnl": 30.0,
                "timestamp": today,
            }
        )

    # Verify daily P&L
    today_date = today.date()
    assert today_date in tracker.daily_pnl
    assert tracker.daily_pnl[today_date] == Decimal("90.0")  # 3 * 30


def test_generate_report(tracker):
    """Test report generation"""
    # Record some trades
    tracker.record_trade(
        {
            "symbol": "BTC/USDT:USDT",
            "side": "buy",
            "quantity": 0.1,
            "price": 45000.0,
            "fees": 4.5,
            "pnl": 100.0,
            "timestamp": datetime.utcnow(),
        }
    )

    tracker.record_trade(
        {
            "symbol": "BTC/USDT:USDT",
            "side": "buy",
            "quantity": 0.1,
            "price": 45000.0,
            "fees": 4.5,
            "pnl": -50.0,
            "timestamp": datetime.utcnow(),
        }
    )

    # Generate report
    report = tracker.generate_report()

    # Verify report structure
    assert "summary" in report
    assert "profitability" in report
    assert "trade_statistics" in report
    assert "risk_metrics" in report
    assert "time_analysis" in report
    assert "daily_pnl" in report

    # Verify summary
    assert report["summary"]["total_trades"] == 2
    assert report["summary"]["winning_trades"] == 1
    assert report["summary"]["losing_trades"] == 1

    # Verify profitability
    assert report["profitability"]["total_pnl"] == 50.0
    assert report["profitability"]["win_rate"] == 50.0


def test_get_trade_history(tracker):
    """Test trade history retrieval"""
    # Record trades
    for i in range(5):
        tracker.record_trade(
            {
                "symbol": "BTC/USDT:USDT",
                "side": "buy",
                "quantity": 0.1,
                "price": 45000.0,
                "fees": 4.5,
                "pnl": 10.0 * (i + 1),
                "timestamp": datetime.utcnow(),
            }
        )

    # Get all trades
    trades = tracker.get_trade_history()
    assert len(trades) == 5

    # Get limited trades
    trades = tracker.get_trade_history(limit=3)
    assert len(trades) == 3

    # Get winning trades only
    winning_trades = tracker.get_trade_history(winning_only=True)
    assert len(winning_trades) == 5
    assert all(t["pnl"] > 0 for t in winning_trades)


def test_get_symbol_performance(tracker):
    """Test symbol performance breakdown"""
    # Record trades for different symbols
    tracker.record_trade(
        {
            "symbol": "BTC/USDT:USDT",
            "side": "buy",
            "quantity": 0.1,
            "price": 45000.0,
            "fees": 4.5,
            "pnl": 100.0,
            "timestamp": datetime.utcnow(),
        }
    )

    tracker.record_trade(
        {
            "symbol": "BTC/USDT:USDT",
            "side": "buy",
            "quantity": 0.1,
            "price": 45000.0,
            "fees": 4.5,
            "pnl": -50.0,
            "timestamp": datetime.utcnow(),
        }
    )

    tracker.record_trade(
        {
            "symbol": "ETH/USDT:USDT",
            "side": "buy",
            "quantity": 1.0,
            "price": 2500.0,
            "fees": 2.5,
            "pnl": 75.0,
            "timestamp": datetime.utcnow(),
        }
    )

    # Get symbol performance
    performance = tracker.get_symbol_performance()

    # Verify BTC stats
    assert "BTC/USDT:USDT" in performance
    btc_stats = performance["BTC/USDT:USDT"]
    assert btc_stats["trades"] == 2
    assert btc_stats["wins"] == 1
    assert btc_stats["losses"] == 1
    assert btc_stats["win_rate"] == 50.0
    assert btc_stats["total_pnl"] == 50.0

    # Verify ETH stats
    assert "ETH/USDT:USDT" in performance
    eth_stats = performance["ETH/USDT:USDT"]
    assert eth_stats["trades"] == 1
    assert eth_stats["wins"] == 1
    assert eth_stats["win_rate"] == 100.0


def test_reset(tracker):
    """Test tracker reset"""
    # Record trades
    tracker.record_trade(
        {
            "symbol": "BTC/USDT:USDT",
            "side": "buy",
            "quantity": 0.1,
            "price": 45000.0,
            "fees": 4.5,
            "pnl": 100.0,
            "timestamp": datetime.utcnow(),
        }
    )

    # Verify state
    assert tracker.metrics["total_trades"] > 0

    # Reset
    tracker.reset()

    # Verify reset
    assert len(tracker.trades) == 0
    assert len(tracker.daily_pnl) == 0
    assert tracker.metrics["total_trades"] == 0
    assert tracker.metrics["total_pnl"] == Decimal("0")


def test_export_trades_csv(tracker):
    """Test CSV export"""
    # Record trades
    tracker.record_trade(
        {
            "symbol": "BTC/USDT:USDT",
            "side": "buy",
            "quantity": 0.1,
            "price": 45000.0,
            "fees": 4.5,
            "pnl": 100.0,
            "timestamp": datetime.utcnow(),
        }
    )

    # Export to temp file
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as f:
        filepath = f.name

    try:
        tracker.export_trades_csv(filepath)

        # Verify file exists and has content
        assert os.path.exists(filepath)

        with open(filepath, "r") as f:
            content = f.read()
            assert "timestamp" in content
            assert "symbol" in content
            assert "BTC/USDT:USDT" in content

    finally:
        # Cleanup
        if os.path.exists(filepath):
            os.remove(filepath)


def test_max_drawdown_calculation(tracker):
    """Test maximum drawdown calculation"""
    # Create trades that create a drawdown scenario
    # Peak at $200, then down to $50 (drawdown of $150)
    tracker.record_trade(
        {
            "symbol": "BTC/USDT:USDT",
            "side": "buy",
            "quantity": 0.1,
            "price": 45000.0,
            "fees": 4.5,
            "pnl": 200.0,
            "timestamp": datetime.utcnow(),
        }
    )

    tracker.record_trade(
        {
            "symbol": "BTC/USDT:USDT",
            "side": "buy",
            "quantity": 0.1,
            "price": 45000.0,
            "fees": 4.5,
            "pnl": -150.0,
            "timestamp": datetime.utcnow(),
        }
    )

    # Max drawdown should be $150
    assert tracker.metrics["max_drawdown"] == Decimal("150")
