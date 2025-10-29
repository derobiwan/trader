"""
Alerting System - Example Usage

Demonstrates how to use the alerting system in the trading application.

Author: DevOps Engineer (Agent C)
Date: 2025-10-29
Sprint: Sprint 2 Stream C
"""

import asyncio
import os
from workspace.features.alerting import (
    Alert,
    AlertSeverity,
    AlertCategory,
    AlertService,
    EmailAlertChannel,
    SlackAlertChannel,
    PagerDutyAlertChannel,
)
from workspace.features.alerting.config import load_alerting_config


async def example_basic_usage():
    """Basic usage example"""
    print("=== Basic Usage Example ===\n")

    # Create alert service
    service = AlertService(throttle_window=300)  # 5 minutes

    # Register channels (with dummy credentials for demo)
    email_channel = EmailAlertChannel(
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        username="your_email@gmail.com",
        password="your_app_password",
        from_email="trading-alerts@yourcompany.com",
        to_emails=["admin@yourcompany.com"],
    )
    service.register_channel("email", email_channel)

    # Create and send an alert
    alert = Alert(
        title="Position Opened",
        message="Long position opened on BTC/USDT with 0.5 BTC",
        severity=AlertSeverity.INFO,
        category=AlertCategory.TRADING,
        metadata={
            "symbol": "BTC/USDT",
            "size": 0.5,
            "entry_price": 45000,
        }
    )

    results = await service.send_alert(alert)
    print(f"Alert sent: {results}\n")


async def example_multi_channel():
    """Multi-channel alerting example"""
    print("=== Multi-Channel Example ===\n")

    # Create service
    service = AlertService(throttle_window=300)

    # Register multiple channels
    email_channel = EmailAlertChannel(
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        username="your_email@gmail.com",
        password="your_app_password",
        from_email="trading-alerts@yourcompany.com",
        to_emails=["admin@yourcompany.com", "ops@yourcompany.com"],
    )

    slack_channel = SlackAlertChannel(
        webhook_url="https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
        username="Trading Bot",
        icon_emoji=":robot_face:",
    )

    pagerduty_channel = PagerDutyAlertChannel(
        integration_key="your_integration_key",
        min_severity=AlertSeverity.CRITICAL,
    )

    service.register_channel("email", email_channel)
    service.register_channel("slack", slack_channel)
    service.register_channel("pagerduty", pagerduty_channel)

    # Send alerts of different severities
    alerts = [
        Alert(
            title="System Started",
            message="Trading system initialized successfully",
            severity=AlertSeverity.INFO,
            category=AlertCategory.SYSTEM,
        ),
        Alert(
            title="High API Latency",
            message="Exchange API latency is above 2 seconds",
            severity=AlertSeverity.WARNING,
            category=AlertCategory.PERFORMANCE,
            metadata={"latency_ms": 2300},
        ),
        Alert(
            title="Daily Loss Limit Exceeded",
            message="Daily loss limit of $4000 exceeded. Trading halted.",
            severity=AlertSeverity.CRITICAL,
            category=AlertCategory.RISK,
            metadata={
                "daily_pnl": -4500,
                "limit": -4000,
            },
        ),
    ]

    for alert in alerts:
        results = await service.send_alert(alert)
        print(f"{alert.severity.upper()} alert sent to: {list(results.keys())}")

    print()


async def example_with_config():
    """Example using configuration loader"""
    print("=== Configuration-Based Example ===\n")

    # Load configuration from environment
    config = load_alerting_config()

    # Create service
    service = AlertService(throttle_window=config.throttle_window)

    # Register configured channels
    if config.email and config.email.enabled:
        email_channel = EmailAlertChannel(
            smtp_host=config.email.smtp_host,
            smtp_port=config.email.smtp_port,
            username=config.email.username,
            password=config.email.password,
            from_email=config.email.from_email,
            to_emails=config.email.to_emails,
            use_tls=config.email.use_tls,
        )
        service.register_channel("email", email_channel)
        print("✓ Email channel registered")

    if config.slack and config.slack.enabled:
        slack_channel = SlackAlertChannel(
            webhook_url=config.slack.webhook_url,
            username=config.slack.username,
            icon_emoji=config.slack.icon_emoji,
        )
        service.register_channel("slack", slack_channel)
        print("✓ Slack channel registered")

    if config.pagerduty and config.pagerduty.enabled:
        pagerduty_channel = PagerDutyAlertChannel(
            integration_key=config.pagerduty.integration_key,
        )
        service.register_channel("pagerduty", pagerduty_channel)
        print("✓ PagerDuty channel registered")

    print()

    # Send a test alert
    alert = Alert(
        title="Configuration Test",
        message="Testing alerting configuration",
        severity=AlertSeverity.INFO,
        category=AlertCategory.SYSTEM,
    )

    results = await service.send_alert(alert)
    print(f"Test alert sent: {results}\n")


async def example_trading_integration():
    """Example of integrating alerts into trading workflow"""
    print("=== Trading Integration Example ===\n")

    # Initialize alert service (in real app, this would be a singleton)
    alert_service = AlertService(throttle_window=300)

    # Register channels...
    # (same as previous examples)

    # Example: Alert on position opening
    async def on_position_opened(symbol: str, size: float, price: float):
        """Called when position is opened"""
        await alert_service.send_alert(Alert(
            title=f"Position Opened: {symbol}",
            message=f"Opened {size} {symbol} at ${price:,.2f}",
            severity=AlertSeverity.INFO,
            category=AlertCategory.TRADING,
            metadata={
                "symbol": symbol,
                "size": size,
                "price": price,
            }
        ))

    # Example: Alert on risk limit breach
    async def on_risk_limit_breach(limit_type: str, current: float, limit: float):
        """Called when risk limit is breached"""
        await alert_service.send_alert(Alert(
            title=f"Risk Limit Breached: {limit_type}",
            message=f"{limit_type} limit breached: {current} > {limit}",
            severity=AlertSeverity.CRITICAL,
            category=AlertCategory.RISK,
            metadata={
                "limit_type": limit_type,
                "current_value": current,
                "limit_value": limit,
            }
        ))

    # Example: Alert on system error
    async def on_system_error(error_msg: str, component: str):
        """Called on system error"""
        await alert_service.send_alert(Alert(
            title=f"System Error: {component}",
            message=error_msg,
            severity=AlertSeverity.CRITICAL,
            category=AlertCategory.SYSTEM,
            metadata={
                "component": component,
                "error": error_msg,
            }
        ))

    # Simulate some events
    print("Simulating trading events...\n")

    await on_position_opened("BTC/USDT", 0.5, 45000)
    await on_risk_limit_breach("Daily Loss", -4500, -4000)
    await on_system_error("Exchange API connection timeout", "MarketDataService")

    print("Integration example complete\n")


async def example_throttling():
    """Example demonstrating alert throttling"""
    print("=== Throttling Example ===\n")

    service = AlertService(throttle_window=5)  # 5 seconds for demo

    # Simulate rapid identical alerts (like in a loop error)
    print("Sending 5 identical alerts rapidly...")

    for i in range(5):
        alert = Alert(
            title="Market Data Fetch Failed",
            message="Failed to fetch market data from exchange",
            severity=AlertSeverity.WARNING,
            category=AlertCategory.DATA,
        )

        results = await service.send_alert(alert)

        if "throttled" in results:
            print(f"  Alert {i+1}: Throttled (prevented spam)")
        else:
            print(f"  Alert {i+1}: Sent")

        await asyncio.sleep(0.5)

    print("\nWaiting for throttle window to expire...")
    await asyncio.sleep(5.5)

    print("Sending alert after throttle window...")
    alert = Alert(
        title="Market Data Fetch Failed",
        message="Failed to fetch market data from exchange",
        severity=AlertSeverity.WARNING,
        category=AlertCategory.DATA,
    )

    results = await service.send_alert(alert)
    print(f"  Result: {'Sent' if 'throttled' not in results else 'Throttled'}\n")


async def main():
    """Run all examples"""
    print("\n" + "="*60)
    print("ALERTING SYSTEM - USAGE EXAMPLES")
    print("="*60 + "\n")

    # Note: These examples use dummy credentials
    # In production, load from environment variables

    try:
        await example_basic_usage()
        await example_multi_channel()
        await example_with_config()
        await example_trading_integration()
        await example_throttling()
    except Exception as e:
        print(f"Example execution error: {e}")
        print("(This is expected with dummy credentials)")

    print("="*60)
    print("Examples complete!")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
