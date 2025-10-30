"""
Tests for Virtual Portfolio Manager

Tests virtual portfolio management including position tracking,
P&L calculation, and portfolio summaries.

Author: Implementation Specialist (Sprint 2 Stream B)
Date: 2025-10-29
"""

from decimal import Decimal

import pytest

from workspace.features.paper_trading import VirtualPortfolio


@pytest.fixture
def portfolio():
    """Create virtual portfolio for testing"""
    return VirtualPortfolio(initial_balance=Decimal("10000"))


def test_portfolio_initialization(portfolio):
    """Test portfolio initialization"""
    assert portfolio.initial_balance == Decimal("10000")
    assert portfolio.balance == Decimal("10000")
    assert len(portfolio.positions) == 0
    assert len(portfolio.trade_history) == 0
    assert len(portfolio.closed_positions) == 0


def test_open_long_position(portfolio):
    """Test opening a long position"""
    portfolio.open_position(
        symbol="BTC/USDT:USDT",
        side="long",
        quantity=Decimal("0.1"),
        entry_price=Decimal("45000"),
        fees=Decimal("4.5"),
    )

    # Verify position created
    assert "BTC/USDT:USDT" in portfolio.positions
    pos = portfolio.positions["BTC/USDT:USDT"]
    assert pos["side"] == "long"
    assert pos["quantity"] == Decimal("0.1")
    assert pos["entry_price"] == Decimal("45000")

    # Verify balance updated
    expected_balance = Decimal("10000") - (
        Decimal("0.1") * Decimal("45000") + Decimal("4.5")
    )
    assert portfolio.balance == expected_balance

    # Verify trade history
    assert len(portfolio.trade_history) == 1


def test_open_short_position(portfolio):
    """Test opening a short position"""
    initial_balance = portfolio.balance

    portfolio.open_position(
        symbol="BTC/USDT:USDT",
        side="short",
        quantity=Decimal("0.1"),
        entry_price=Decimal("45000"),
        fees=Decimal("4.5"),
    )

    # Verify position created
    pos = portfolio.positions["BTC/USDT:USDT"]
    assert pos["side"] == "short"

    # Verify balance (shorts receive proceeds)
    expected_balance = initial_balance + (
        Decimal("0.1") * Decimal("45000") - Decimal("4.5")
    )
    assert portfolio.balance == expected_balance


def test_add_to_existing_position(portfolio):
    """Test adding to existing position (position averaging)"""
    # Open initial position
    portfolio.open_position(
        symbol="BTC/USDT:USDT",
        side="long",
        quantity=Decimal("0.1"),
        entry_price=Decimal("45000"),
        fees=Decimal("4.5"),
    )

    # Add to position at different price
    portfolio.open_position(
        symbol="BTC/USDT:USDT",
        side="long",
        quantity=Decimal("0.1"),
        entry_price=Decimal("46000"),
        fees=Decimal("4.6"),
    )

    # Verify position averaged
    pos = portfolio.positions["BTC/USDT:USDT"]
    assert pos["quantity"] == Decimal("0.2")

    # Calculate expected average price
    expected_avg = (
        Decimal("45000") * Decimal("0.1") + Decimal("46000") * Decimal("0.1")
    ) / Decimal("0.2")
    assert pos["entry_price"] == expected_avg
    assert pos["total_fees"] == Decimal("4.5") + Decimal("4.6")


def test_close_position_profit(portfolio):
    """Test closing position with profit"""
    # Open position
    portfolio.open_position(
        symbol="BTC/USDT:USDT",
        side="long",
        quantity=Decimal("0.1"),
        entry_price=Decimal("45000"),
        fees=Decimal("4.5"),
    )

    # Close at higher price (profit)
    pnl = portfolio.close_position(
        symbol="BTC/USDT:USDT",
        exit_price=Decimal("46000"),
        fees=Decimal("4.6"),
    )

    # Verify P&L
    expected_pnl = (Decimal("46000") - Decimal("45000")) * Decimal("0.1") - Decimal(
        "4.6"
    )
    assert pnl == expected_pnl
    assert pnl > 0  # Profit

    # Verify position closed
    assert "BTC/USDT:USDT" not in portfolio.positions

    # Verify closed positions tracking
    assert len(portfolio.closed_positions) == 1
    closed = portfolio.closed_positions[0]
    assert closed["pnl"] == pnl


def test_close_position_loss(portfolio):
    """Test closing position with loss"""
    # Open position
    portfolio.open_position(
        symbol="BTC/USDT:USDT",
        side="long",
        quantity=Decimal("0.1"),
        entry_price=Decimal("45000"),
        fees=Decimal("4.5"),
    )

    # Close at lower price (loss)
    pnl = portfolio.close_position(
        symbol="BTC/USDT:USDT",
        exit_price=Decimal("44000"),
        fees=Decimal("4.4"),
    )

    # Verify P&L
    expected_pnl = (Decimal("44000") - Decimal("45000")) * Decimal("0.1") - Decimal(
        "4.4"
    )
    assert pnl == expected_pnl
    assert pnl < 0  # Loss


def test_close_position_short_profit(portfolio):
    """Test closing short position with profit"""
    # Open short position
    portfolio.open_position(
        symbol="BTC/USDT:USDT",
        side="short",
        quantity=Decimal("0.1"),
        entry_price=Decimal("45000"),
        fees=Decimal("4.5"),
    )

    # Close at lower price (profit for short)
    pnl = portfolio.close_position(
        symbol="BTC/USDT:USDT",
        exit_price=Decimal("44000"),
        fees=Decimal("4.4"),
    )

    # Verify P&L (profit when price goes down)
    expected_pnl = (Decimal("45000") - Decimal("44000")) * Decimal("0.1") - Decimal(
        "4.4"
    )
    assert pnl == expected_pnl
    assert pnl > 0  # Profit


def test_partial_position_close(portfolio):
    """Test partially closing a position"""
    # Open position
    portfolio.open_position(
        symbol="BTC/USDT:USDT",
        side="long",
        quantity=Decimal("0.2"),
        entry_price=Decimal("45000"),
        fees=Decimal("9.0"),
    )

    # Close half
    pnl = portfolio.close_position(
        symbol="BTC/USDT:USDT",
        exit_price=Decimal("46000"),
        fees=Decimal("4.6"),
        quantity=Decimal("0.1"),
    )

    # Verify position still exists with remaining quantity
    assert "BTC/USDT:USDT" in portfolio.positions
    pos = portfolio.positions["BTC/USDT:USDT"]
    assert pos["quantity"] == Decimal("0.1")

    # Verify P&L for closed portion
    expected_pnl = (Decimal("46000") - Decimal("45000")) * Decimal("0.1") - Decimal(
        "4.6"
    )
    assert pnl == expected_pnl


def test_close_nonexistent_position(portfolio):
    """Test closing position that doesn't exist"""
    with pytest.raises(ValueError, match="No position for"):
        portfolio.close_position(
            symbol="BTC/USDT:USDT",
            exit_price=Decimal("45000"),
            fees=Decimal("4.5"),
        )


def test_close_too_large_quantity(portfolio):
    """Test closing more than available quantity"""
    # Open position
    portfolio.open_position(
        symbol="BTC/USDT:USDT",
        side="long",
        quantity=Decimal("0.1"),
        entry_price=Decimal("45000"),
        fees=Decimal("4.5"),
    )

    # Try to close more than available
    with pytest.raises(ValueError, match="Cannot close"):
        portfolio.close_position(
            symbol="BTC/USDT:USDT",
            exit_price=Decimal("46000"),
            fees=Decimal("4.6"),
            quantity=Decimal("0.2"),
        )


def test_get_unrealized_pnl(portfolio):
    """Test unrealized P&L calculation"""
    # Open positions
    portfolio.open_position(
        symbol="BTC/USDT:USDT",
        side="long",
        quantity=Decimal("0.1"),
        entry_price=Decimal("45000"),
        fees=Decimal("4.5"),
    )

    portfolio.open_position(
        symbol="ETH/USDT:USDT",
        side="long",
        quantity=Decimal("1.0"),
        entry_price=Decimal("2500"),
        fees=Decimal("2.5"),
    )

    # Calculate unrealized P&L
    current_prices = {
        "BTC/USDT:USDT": Decimal("46000"),
        "ETH/USDT:USDT": Decimal("2600"),
    }

    unrealized_pnl = portfolio.get_unrealized_pnl(current_prices)

    # Verify calculation
    btc_pnl = (Decimal("46000") - Decimal("45000")) * Decimal("0.1")
    eth_pnl = (Decimal("2600") - Decimal("2500")) * Decimal("1.0")
    expected_pnl = btc_pnl + eth_pnl

    assert unrealized_pnl == expected_pnl


def test_get_position_pnl(portfolio):
    """Test P&L calculation for specific position"""
    # Open position
    portfolio.open_position(
        symbol="BTC/USDT:USDT",
        side="long",
        quantity=Decimal("0.1"),
        entry_price=Decimal("45000"),
        fees=Decimal("4.5"),
    )

    # Calculate P&L
    pnl = portfolio.get_position_pnl(
        symbol="BTC/USDT:USDT",
        current_price=Decimal("46000"),
    )

    expected_pnl = (Decimal("46000") - Decimal("45000")) * Decimal("0.1")
    assert pnl == expected_pnl

    # Nonexistent position
    pnl = portfolio.get_position_pnl(
        symbol="ETH/USDT:USDT",
        current_price=Decimal("2500"),
    )
    assert pnl is None


def test_get_total_equity(portfolio):
    """Test total equity calculation"""
    # Open position
    portfolio.open_position(
        symbol="BTC/USDT:USDT",
        side="long",
        quantity=Decimal("0.1"),
        entry_price=Decimal("45000"),
        fees=Decimal("4.5"),
    )

    # Calculate total equity
    current_prices = {
        "BTC/USDT:USDT": Decimal("46000"),
    }

    total_equity = portfolio.get_total_equity(current_prices)

    # Verify: balance + unrealized P&L
    unrealized_pnl = (Decimal("46000") - Decimal("45000")) * Decimal("0.1")
    expected_equity = portfolio.balance + unrealized_pnl

    assert total_equity == expected_equity


def test_get_portfolio_summary(portfolio):
    """Test portfolio summary generation"""
    # Open and close some positions
    portfolio.open_position(
        symbol="BTC/USDT:USDT",
        side="long",
        quantity=Decimal("0.1"),
        entry_price=Decimal("45000"),
        fees=Decimal("4.5"),
    )

    portfolio.close_position(
        symbol="BTC/USDT:USDT",
        exit_price=Decimal("46000"),
        fees=Decimal("4.6"),
    )

    # Get summary
    summary = portfolio.get_portfolio_summary()

    # Verify structure
    assert summary["initial_balance"] == 10000.0
    assert "current_balance" in summary
    assert summary["open_positions"] == 0
    assert summary["closed_positions"] == 1
    assert summary["total_trades"] == 2  # Open + close
    assert "realized_pnl" in summary


def test_get_portfolio_summary_with_current_prices(portfolio):
    """Test portfolio summary with current prices"""
    # Open position
    portfolio.open_position(
        symbol="BTC/USDT:USDT",
        side="long",
        quantity=Decimal("0.1"),
        entry_price=Decimal("45000"),
        fees=Decimal("4.5"),
    )

    current_prices = {
        "BTC/USDT:USDT": Decimal("46000"),
    }

    summary = portfolio.get_portfolio_summary(current_prices=current_prices)

    # Verify additional fields
    assert "unrealized_pnl" in summary
    assert "total_equity" in summary
    assert "return_pct" in summary

    # Verify position details
    assert len(summary["positions"]) == 1
    assert summary["positions"][0]["symbol"] == "BTC/USDT:USDT"
    assert summary["positions"][0]["unrealized_pnl"] is not None


def test_get_performance_stats(portfolio):
    """Test performance statistics calculation"""
    # Execute multiple trades
    # Trade 1: Win
    portfolio.open_position(
        symbol="BTC/USDT:USDT",
        side="long",
        quantity=Decimal("0.1"),
        entry_price=Decimal("45000"),
        fees=Decimal("4.5"),
    )
    portfolio.close_position(
        symbol="BTC/USDT:USDT",
        exit_price=Decimal("46000"),
        fees=Decimal("4.6"),
    )

    # Trade 2: Loss
    portfolio.open_position(
        symbol="ETH/USDT:USDT",
        side="long",
        quantity=Decimal("1.0"),
        entry_price=Decimal("2500"),
        fees=Decimal("2.5"),
    )
    portfolio.close_position(
        symbol="ETH/USDT:USDT",
        exit_price=Decimal("2400"),
        fees=Decimal("2.4"),
    )

    # Get stats
    stats = portfolio.get_performance_stats()

    # Verify structure
    assert stats["total_trades"] == 2
    assert stats["winning_trades"] == 1
    assert stats["losing_trades"] == 1
    assert 0 < stats["win_rate"] < 100
    assert stats["avg_win"] > 0
    assert stats["avg_loss"] < 0
    assert "largest_win" in stats
    assert "largest_loss" in stats


def test_get_performance_stats_empty(portfolio):
    """Test performance stats with no trades"""
    stats = portfolio.get_performance_stats()

    assert stats["total_trades"] == 0
    assert stats["winning_trades"] == 0
    assert stats["losing_trades"] == 0
    assert stats["win_rate"] == 0.0
    assert stats["avg_win"] == 0.0
    assert stats["avg_loss"] == 0.0
