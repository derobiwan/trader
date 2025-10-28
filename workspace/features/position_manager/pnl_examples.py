"""
P&L Calculation Examples

Demonstrates P&L calculations for various trading scenarios.
Used for validation and documentation purposes.

Run:
    python workspace/features/position_manager/pnl_examples.py
"""

from decimal import Decimal


def calculate_long_pnl(
    entry_price: Decimal, current_price: Decimal, quantity: Decimal, leverage: int
) -> dict:
    """Calculate P&L for LONG position."""
    pnl_usd = (current_price - entry_price) * quantity * leverage
    pnl_chf = pnl_usd * Decimal("0.85")  # USD/CHF rate
    pnl_pct = ((current_price - entry_price) / entry_price) * leverage * Decimal("100")

    return {
        "pnl_usd": round(pnl_usd, 2),
        "pnl_chf": round(pnl_chf, 2),
        "pnl_pct": round(pnl_pct, 2),
    }


def calculate_short_pnl(
    entry_price: Decimal, current_price: Decimal, quantity: Decimal, leverage: int
) -> dict:
    """Calculate P&L for SHORT position."""
    pnl_usd = (entry_price - current_price) * quantity * leverage
    pnl_chf = pnl_usd * Decimal("0.85")  # USD/CHF rate
    pnl_pct = ((entry_price - current_price) / entry_price) * leverage * Decimal("100")

    return {
        "pnl_usd": round(pnl_usd, 2),
        "pnl_chf": round(pnl_chf, 2),
        "pnl_pct": round(pnl_pct, 2),
    }


def main():
    """Run P&L calculation examples."""
    print("=" * 70)
    print("P&L CALCULATION EXAMPLES")
    print("=" * 70)

    # Example 1: LONG BTC with profit
    print("\n1. LONG BTC - Profit Scenario")
    print("-" * 70)
    entry = Decimal("45000.00")
    current = Decimal("45500.00")
    quantity = Decimal("0.01")
    leverage = 10

    result = calculate_long_pnl(entry, current, quantity, leverage)

    print(f"Entry Price:    ${entry:,.2f}")
    print(f"Current Price:  ${current:,.2f}")
    print(f"Quantity:       {quantity} BTC")
    print(f"Leverage:       {leverage}x")
    print("")
    print(f"P&L (USD):      ${result['pnl_usd']:+,.2f}")
    print(f"P&L (CHF):      CHF {result['pnl_chf']:+,.2f}")
    print(f"P&L (%):        {result['pnl_pct']:+.2f}%")

    # Example 2: LONG BTC with loss
    print("\n2. LONG BTC - Loss Scenario")
    print("-" * 70)
    current = Decimal("44500.00")
    result = calculate_long_pnl(entry, current, quantity, leverage)

    print(f"Entry Price:    ${entry:,.2f}")
    print(f"Current Price:  ${current:,.2f}")
    print(f"Quantity:       {quantity} BTC")
    print(f"Leverage:       {leverage}x")
    print("")
    print(f"P&L (USD):      ${result['pnl_usd']:+,.2f}")
    print(f"P&L (CHF):      CHF {result['pnl_chf']:+,.2f}")
    print(f"P&L (%):        {result['pnl_pct']:+.2f}%")

    # Example 3: SHORT BTC with profit
    print("\n3. SHORT BTC - Profit Scenario")
    print("-" * 70)
    entry = Decimal("45000.00")
    current = Decimal("44500.00")  # Price went down = profit for SHORT
    result = calculate_short_pnl(entry, current, quantity, leverage)

    print(f"Entry Price:    ${entry:,.2f}")
    print(f"Current Price:  ${current:,.2f}")
    print(f"Quantity:       {quantity} BTC")
    print(f"Leverage:       {leverage}x")
    print("")
    print(f"P&L (USD):      ${result['pnl_usd']:+,.2f}")
    print(f"P&L (CHF):      CHF {result['pnl_chf']:+,.2f}")
    print(f"P&L (%):        {result['pnl_pct']:+.2f}%")

    # Example 4: HIGH LEVERAGE scenario
    print("\n4. LONG BTC - High Leverage (40x)")
    print("-" * 70)
    entry = Decimal("45000.00")
    current = Decimal("45100.00")  # Small price move
    leverage = 40  # Maximum leverage
    result = calculate_long_pnl(entry, current, quantity, leverage)

    print(f"Entry Price:    ${entry:,.2f}")
    print(f"Current Price:  ${current:,.2f}")
    print(f"Quantity:       {quantity} BTC")
    print(f"Leverage:       {leverage}x")
    print("")
    print(f"P&L (USD):      ${result['pnl_usd']:+,.2f}")
    print(f"P&L (CHF):      CHF {result['pnl_chf']:+,.2f}")
    print(f"P&L (%):        {result['pnl_pct']:+.2f}%")
    print("Note: Small price move (0.22%) = large P&L (8.89%) due to 40x leverage")

    # Example 5: STOP-LOSS scenario
    print("\n5. LONG BTC - Stop-Loss Hit (-7% target)")
    print("-" * 70)
    entry = Decimal("45000.00")
    stop_loss = Decimal("44000.00")  # Stop-loss price
    result = calculate_long_pnl(entry, stop_loss, quantity, leverage)

    print(f"Entry Price:    ${entry:,.2f}")
    print(f"Stop-Loss:      ${stop_loss:,.2f}")
    print(f"Quantity:       {quantity} BTC")
    print(f"Leverage:       {leverage}x")
    print("")
    print(f"P&L (USD):      ${result['pnl_usd']:+,.2f}")
    print(f"P&L (CHF):      CHF {result['pnl_chf']:+,.2f}")
    print(f"P&L (%):        {result['pnl_pct']:+.2f}%")

    # Example 6: CIRCUIT BREAKER scenario
    print("\n6. Circuit Breaker Scenario (-7% daily loss)")
    print("-" * 70)
    capital_chf = Decimal("2626.96")
    circuit_breaker_threshold = capital_chf * Decimal("-0.07")

    print(f"Total Capital:        CHF {capital_chf:,.2f}")
    print(f"Circuit Breaker:      CHF {circuit_breaker_threshold:+,.2f} (-7%)")
    print("")

    # Simulate position that triggers circuit breaker
    entry = Decimal("45000.00")
    close = Decimal("40000.00")  # Large loss
    quantity = Decimal("0.1")  # Larger position
    leverage = 10
    result = calculate_long_pnl(entry, close, quantity, leverage)

    print("Single Position Loss:")
    print(f"  Entry:         ${entry:,.2f}")
    print(f"  Close:         ${close:,.2f}")
    print(f"  Quantity:      {quantity} BTC")
    print(f"  Leverage:      {leverage}x")
    print(f"  Loss (CHF):    CHF {result['pnl_chf']:+,.2f}")
    print("")

    if result["pnl_chf"] <= circuit_breaker_threshold:
        print("⚠️  CIRCUIT BREAKER TRIGGERED!")
        print(
            f"   Daily loss (CHF {result['pnl_chf']:+,.2f}) exceeds threshold (CHF {circuit_breaker_threshold:+,.2f})"
        )
        print("   System will close all positions and halt trading for the day.")

    # Risk Limits Summary
    print("\n" + "=" * 70)
    print("RISK LIMITS SUMMARY")
    print("=" * 70)
    print(f"Capital:                    CHF {capital_chf:,.2f}")
    print(f"Max Position Size (20%):    CHF {capital_chf * Decimal('0.20'):,.2f}")
    print(f"Max Total Exposure (80%):   CHF {capital_chf * Decimal('0.80'):,.2f}")
    print(f"Circuit Breaker (-7%):      CHF {circuit_breaker_threshold:+,.2f}")
    print("Leverage Range:             5x - 40x")
    print("Stop-Loss:                  REQUIRED (100% enforcement)")
    print("=" * 70)


if __name__ == "__main__":
    main()
