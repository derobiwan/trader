"""
Integration Tests for Alerting System

Tests the complete alerting system with real-world scenarios.

Author: DevOps Engineer (Agent C)
Date: 2025-10-29
Sprint: Sprint 2 Stream C
"""

import asyncio

import pytest

from workspace.features.alerting import (Alert, AlertCategory, AlertService,
                                         AlertSeverity, EmailAlertChannel,
                                         PagerDutyAlertChannel,
                                         SlackAlertChannel)


class MockEmailChannel(EmailAlertChannel):
    """Mock email channel for integration testing"""

    def __init__(self):
        # Use mock credentials
        super().__init__(
            smtp_host="smtp.example.com",
            smtp_port=587,
            username="test@example.com",
            password="password",
            from_email="alerts@example.com",
            to_emails=["admin@example.com"],
        )
        self.sent_alerts = []

    async def send(self, alert: Alert) -> bool:
        """Mock send"""
        self.sent_alerts.append(alert)
        return True


class MockSlackChannel(SlackAlertChannel):
    """Mock Slack channel for integration testing"""

    def __init__(self):
        super().__init__(webhook_url="https://hooks.slack.com/mock")
        self.sent_alerts = []

    async def send(self, alert: Alert) -> bool:
        """Mock send"""
        self.sent_alerts.append(alert)
        return True


class MockPagerDutyChannel(PagerDutyAlertChannel):
    """Mock PagerDuty channel for integration testing"""

    def __init__(self):
        super().__init__(integration_key="mock_key")
        self.sent_alerts = []

    async def send(self, alert: Alert) -> bool:
        """Mock send"""
        if alert.severity == AlertSeverity.CRITICAL:
            self.sent_alerts.append(alert)
        return True


class TestAlertingIntegration:
    """Integration tests for alerting system"""

    @pytest.mark.asyncio
    async def test_complete_alerting_flow(self):
        """Test complete alerting flow with all channels"""
        # Create service
        service = AlertService(throttle_window=1)  # 1 second for testing

        # Register mock channels
        email_channel = MockEmailChannel()
        slack_channel = MockSlackChannel()
        pagerduty_channel = MockPagerDutyChannel()

        service.register_channel("email", email_channel)
        service.register_channel("slack", slack_channel)
        service.register_channel("pagerduty", pagerduty_channel)

        # Send INFO alert (email only)
        info_alert = Alert(
            title="System Started",
            message="Trading system has started successfully",
            severity=AlertSeverity.INFO,
            category=AlertCategory.SYSTEM,
        )

        results = await service.send_alert(info_alert)

        assert "email" in results
        assert len(email_channel.sent_alerts) == 1
        assert len(slack_channel.sent_alerts) == 0
        assert len(pagerduty_channel.sent_alerts) == 0

        # Send WARNING alert (email + slack)
        warning_alert = Alert(
            title="High Latency Detected",
            message="API latency is above threshold",
            severity=AlertSeverity.WARNING,
            category=AlertCategory.PERFORMANCE,
            metadata={"latency_ms": 2500},
        )

        results = await service.send_alert(warning_alert)

        assert "email" in results
        assert "slack" in results
        assert len(email_channel.sent_alerts) == 2
        assert len(slack_channel.sent_alerts) == 1
        assert len(pagerduty_channel.sent_alerts) == 0

        # Send CRITICAL alert (all channels)
        critical_alert = Alert(
            title="Daily Loss Limit Exceeded",
            message="Daily loss limit has been exceeded. Trading halted.",
            severity=AlertSeverity.CRITICAL,
            category=AlertCategory.RISK,
            metadata={
                "daily_pnl": -5000,
                "limit": -4000,
            },
        )

        results = await service.send_alert(critical_alert)

        assert "email" in results
        assert "slack" in results
        assert "pagerduty" in results
        assert len(email_channel.sent_alerts) == 3
        assert len(slack_channel.sent_alerts) == 2
        assert len(pagerduty_channel.sent_alerts) == 1

    @pytest.mark.asyncio
    async def test_alert_throttling_integration(self):
        """Test alert throttling in real scenario"""
        service = AlertService(throttle_window=2)  # 2 seconds

        email_channel = MockEmailChannel()
        service.register_channel("email", email_channel)

        # Send first alert
        alert1 = Alert(
            title="Market Data Fetch Failed",
            message="Failed to fetch market data",
            severity=AlertSeverity.WARNING,
            category=AlertCategory.DATA,
        )

        results1 = await service.send_alert(alert1)
        assert "email" in results1
        assert len(email_channel.sent_alerts) == 1

        # Send duplicate immediately (should be throttled)
        alert2 = Alert(
            title="Market Data Fetch Failed",
            message="Failed to fetch market data",
            severity=AlertSeverity.WARNING,
            category=AlertCategory.DATA,
        )

        results2 = await service.send_alert(alert2)
        assert "throttled" in results2
        assert len(email_channel.sent_alerts) == 1  # Still 1

        # Wait for throttle window to expire
        await asyncio.sleep(2.1)

        # Send again (should go through)
        alert3 = Alert(
            title="Market Data Fetch Failed",
            message="Failed to fetch market data",
            severity=AlertSeverity.WARNING,
            category=AlertCategory.DATA,
        )

        results3 = await service.send_alert(alert3)
        assert "email" in results3
        assert len(email_channel.sent_alerts) == 2  # Now 2

    @pytest.mark.asyncio
    async def test_trading_scenario_alerts(self):
        """Test alerts in a realistic trading scenario"""
        service = AlertService(throttle_window=1)

        email_channel = MockEmailChannel()
        slack_channel = MockSlackChannel()
        pagerduty_channel = MockPagerDutyChannel()

        service.register_channel("email", email_channel)
        service.register_channel("slack", slack_channel)
        service.register_channel("pagerduty", pagerduty_channel)

        # Scenario: Trading system experiencing issues

        # 1. Position opened (INFO)
        await service.send_alert(
            Alert(
                title="Position Opened",
                message="Long position opened on BTC/USDT",
                severity=AlertSeverity.INFO,
                category=AlertCategory.TRADING,
                metadata={"symbol": "BTC/USDT", "size": 0.5},
            )
        )

        # 2. High drawdown (WARNING)
        await service.send_alert(
            Alert(
                title="High Drawdown",
                message="Position drawdown exceeds 5%",
                severity=AlertSeverity.WARNING,
                category=AlertCategory.RISK,
                metadata={"symbol": "BTC/USDT", "drawdown_pct": 5.2},
            )
        )

        # 3. Stop loss triggered (WARNING)
        await service.send_alert(
            Alert(
                title="Stop Loss Triggered",
                message="Stop loss triggered on BTC/USDT",
                severity=AlertSeverity.WARNING,
                category=AlertCategory.TRADING,
                metadata={"symbol": "BTC/USDT", "loss": -250},
            )
        )

        # 4. System error (CRITICAL)
        await service.send_alert(
            Alert(
                title="Exchange API Error",
                message="Critical error connecting to exchange API",
                severity=AlertSeverity.CRITICAL,
                category=AlertCategory.SYSTEM,
                metadata={"exchange": "Binance", "error": "Connection timeout"},
            )
        )

        # Verify alerts were routed correctly
        assert len(email_channel.sent_alerts) == 4  # All alerts
        assert len(slack_channel.sent_alerts) == 3  # WARNING + CRITICAL
        assert len(pagerduty_channel.sent_alerts) == 1  # CRITICAL only

    @pytest.mark.asyncio
    async def test_delivery_statistics(self):
        """Test delivery statistics tracking"""
        service = AlertService(throttle_window=1)

        email_channel = MockEmailChannel()
        service.register_channel("email", email_channel)

        # Send multiple alerts
        for i in range(5):
            alert = Alert(
                title=f"Alert {i}",
                message=f"Test alert {i}",
                severity=AlertSeverity.INFO,
            )
            await service.send_alert(alert)
            await asyncio.sleep(0.1)  # Small delay to avoid throttling

        # Check statistics
        stats = service.get_delivery_stats()
        assert stats["total"] >= 5
        assert stats["sent"] >= 5
        assert stats["success_rate"] > 0.9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
