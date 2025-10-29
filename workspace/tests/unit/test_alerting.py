"""
Tests for Alerting System

Author: DevOps Engineer (Agent C)
Date: 2025-10-29
Sprint: Sprint 2 Stream C
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from workspace.features.alerting import (
    Alert,
    AlertSeverity,
    AlertCategory,
    AlertService,
    AlertChannel,
    AlertThrottler,
    AlertRoutingRules,
    EmailAlertChannel,
    SlackAlertChannel,
    PagerDutyAlertChannel,
)


class TestAlertModels:
    """Test alert data models"""

    def test_alert_creation(self):
        """Test creating an alert"""
        alert = Alert(
            title="Test Alert",
            message="This is a test",
            severity=AlertSeverity.WARNING,
            category=AlertCategory.SYSTEM,
        )

        assert alert.title == "Test Alert"
        assert alert.message == "This is a test"
        assert alert.severity == AlertSeverity.WARNING
        assert alert.category == AlertCategory.SYSTEM
        assert alert.id is not None
        assert isinstance(alert.timestamp, datetime)

    def test_alert_with_metadata(self):
        """Test alert with metadata"""
        alert = Alert(
            title="Trade Failed",
            message="Order execution failed",
            severity=AlertSeverity.CRITICAL,
            category=AlertCategory.TRADING,
            metadata={
                "symbol": "BTC/USDT",
                "order_id": "12345",
                "error": "Insufficient balance",
            }
        )

        assert alert.metadata is not None
        assert alert.metadata["symbol"] == "BTC/USDT"
        assert alert.metadata["order_id"] == "12345"


class TestAlertThrottler:
    """Test alert throttling"""

    def test_should_send_first_alert(self):
        """First alert should always be sent"""
        throttler = AlertThrottler(throttle_window=300)

        alert = Alert(
            title="Test Alert",
            message="Test",
            severity=AlertSeverity.WARNING,
        )

        assert throttler.should_send(alert) is True

    def test_throttle_duplicate_alert(self):
        """Duplicate alert within window should be throttled"""
        throttler = AlertThrottler(throttle_window=300)

        alert1 = Alert(
            title="Test Alert",
            message="Test",
            severity=AlertSeverity.WARNING,
        )

        alert2 = Alert(
            title="Test Alert",
            message="Test",
            severity=AlertSeverity.WARNING,
        )

        assert throttler.should_send(alert1) is True
        assert throttler.should_send(alert2) is False

    def test_allow_different_alerts(self):
        """Different alerts should not be throttled"""
        throttler = AlertThrottler(throttle_window=300)

        alert1 = Alert(
            title="Alert 1",
            message="Test",
            severity=AlertSeverity.WARNING,
        )

        alert2 = Alert(
            title="Alert 2",
            message="Test",
            severity=AlertSeverity.WARNING,
        )

        assert throttler.should_send(alert1) is True
        assert throttler.should_send(alert2) is True

    def test_allow_different_severity(self):
        """Same alert with different severity should not be throttled"""
        throttler = AlertThrottler(throttle_window=300)

        alert1 = Alert(
            title="Test Alert",
            message="Test",
            severity=AlertSeverity.WARNING,
        )

        alert2 = Alert(
            title="Test Alert",
            message="Test",
            severity=AlertSeverity.CRITICAL,
        )

        assert throttler.should_send(alert1) is True
        assert throttler.should_send(alert2) is True

    def test_reset_throttler(self):
        """Reset should clear throttler state"""
        throttler = AlertThrottler(throttle_window=300)

        alert = Alert(
            title="Test Alert",
            message="Test",
            severity=AlertSeverity.WARNING,
        )

        assert throttler.should_send(alert) is True
        assert throttler.should_send(alert) is False

        throttler.reset()

        assert throttler.should_send(alert) is True


class TestAlertRoutingRules:
    """Test alert routing"""

    def test_default_routing(self):
        """Test default routing rules"""
        rules = AlertRoutingRules()

        # Create mock channels
        email_channel = MagicMock(spec=AlertChannel)
        email_channel.enabled = True
        slack_channel = MagicMock(spec=AlertChannel)
        slack_channel.enabled = True
        pagerduty_channel = MagicMock(spec=AlertChannel)
        pagerduty_channel.enabled = True

        rules.register_channel("email", email_channel)
        rules.register_channel("slack", slack_channel)
        rules.register_channel("pagerduty", pagerduty_channel)

        # Test routing for each severity
        info_channels = rules.get_channels(AlertSeverity.INFO)
        assert len(info_channels) == 1
        assert info_channels[0] == email_channel

        warning_channels = rules.get_channels(AlertSeverity.WARNING)
        assert len(warning_channels) == 2

        critical_channels = rules.get_channels(AlertSeverity.CRITICAL)
        assert len(critical_channels) == 3

    def test_disabled_channel(self):
        """Disabled channels should not be returned"""
        rules = AlertRoutingRules()

        email_channel = MagicMock(spec=AlertChannel)
        email_channel.enabled = False
        rules.register_channel("email", email_channel)

        channels = rules.get_channels(AlertSeverity.INFO)
        assert len(channels) == 0

    def test_custom_routing(self):
        """Test custom routing rules"""
        rules = AlertRoutingRules()

        email_channel = MagicMock(spec=AlertChannel)
        email_channel.enabled = True
        rules.register_channel("email", email_channel)

        # Set custom routing: INFO to email only
        rules.set_routing(AlertSeverity.INFO, ['email'])

        channels = rules.get_channels(AlertSeverity.INFO)
        assert len(channels) == 1
        assert channels[0] == email_channel


class TestMockAlertChannel:
    """Mock alert channel for testing"""

    class MockChannel(AlertChannel):
        """Mock channel for testing"""

        def __init__(self, name: str, should_fail: bool = False):
            super().__init__(name)
            self.should_fail = should_fail
            self.sent_alerts = []

        async def send(self, alert: Alert) -> bool:
            if self.should_fail:
                raise Exception("Mock send failure")
            self.sent_alerts.append(alert)
            return True


class TestAlertService:
    """Test alert service"""

    @pytest.mark.asyncio
    async def test_send_alert_success(self):
        """Test successful alert sending"""
        service = AlertService(throttle_window=300)

        mock_channel = TestMockAlertChannel.MockChannel("test")
        service.register_channel("test", mock_channel)

        # Override routing to use test channel
        service.routing_rules.set_routing(AlertSeverity.WARNING, ["test"])

        alert = Alert(
            title="Test Alert",
            message="Test",
            severity=AlertSeverity.WARNING,
        )

        results = await service.send_alert(alert)

        assert "test" in results
        assert len(mock_channel.sent_alerts) == 1
        assert mock_channel.sent_alerts[0].title == "Test Alert"

    @pytest.mark.asyncio
    async def test_send_alert_throttled(self):
        """Test alert throttling"""
        service = AlertService(throttle_window=300)

        mock_channel = TestMockAlertChannel.MockChannel("test")
        service.register_channel("test", mock_channel)
        service.routing_rules.set_routing(AlertSeverity.WARNING, ["test"])

        alert1 = Alert(
            title="Test Alert",
            message="Test",
            severity=AlertSeverity.WARNING,
        )

        alert2 = Alert(
            title="Test Alert",
            message="Test",
            severity=AlertSeverity.WARNING,
        )

        # First alert should be sent
        results1 = await service.send_alert(alert1)
        assert "test" in results1
        assert len(mock_channel.sent_alerts) == 1

        # Second alert should be throttled
        results2 = await service.send_alert(alert2)
        assert "throttled" in results2
        assert len(mock_channel.sent_alerts) == 1  # Still 1

    @pytest.mark.asyncio
    async def test_send_alert_force(self):
        """Test force sending bypasses throttling"""
        service = AlertService(throttle_window=300)

        mock_channel = TestMockAlertChannel.MockChannel("test")
        service.register_channel("test", mock_channel)
        service.routing_rules.set_routing(AlertSeverity.WARNING, ["test"])

        alert1 = Alert(
            title="Test Alert",
            message="Test",
            severity=AlertSeverity.WARNING,
        )

        alert2 = Alert(
            title="Test Alert",
            message="Test",
            severity=AlertSeverity.WARNING,
        )

        await service.send_alert(alert1)
        await service.send_alert(alert2, force=True)

        assert len(mock_channel.sent_alerts) == 2

    @pytest.mark.asyncio
    async def test_send_alert_channel_failure(self):
        """Test handling of channel failure"""
        service = AlertService(throttle_window=300)

        mock_channel = TestMockAlertChannel.MockChannel("test", should_fail=True)
        service.register_channel("test", mock_channel)
        service.routing_rules.set_routing(AlertSeverity.WARNING, ["test"])

        alert = Alert(
            title="Test Alert",
            message="Test",
            severity=AlertSeverity.WARNING,
        )

        results = await service.send_alert(alert)

        assert "test" in results
        # Service should handle failure gracefully

    def test_delivery_stats(self):
        """Test delivery statistics"""
        service = AlertService()

        # Initially empty
        stats = service.get_delivery_stats()
        assert stats["total"] == 0

    @pytest.mark.asyncio
    async def test_multiple_channels(self):
        """Test sending to multiple channels"""
        service = AlertService(throttle_window=300)

        channel1 = TestMockAlertChannel.MockChannel("channel1")
        channel2 = TestMockAlertChannel.MockChannel("channel2")

        service.register_channel("channel1", channel1)
        service.register_channel("channel2", channel2)

        service.routing_rules.set_routing(
            AlertSeverity.CRITICAL,
            ["channel1", "channel2"]
        )

        alert = Alert(
            title="Critical Alert",
            message="Test",
            severity=AlertSeverity.CRITICAL,
        )

        results = await service.send_alert(alert)

        assert "channel1" in results
        assert "channel2" in results
        assert len(channel1.sent_alerts) == 1
        assert len(channel2.sent_alerts) == 1


class TestEmailChannel:
    """Test email alert channel"""

    @pytest.mark.asyncio
    @patch('smtplib.SMTP')
    async def test_send_email_success(self, mock_smtp):
        """Test successful email sending"""
        channel = EmailAlertChannel(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            username="test@example.com",
            password="password",
            from_email="alerts@example.com",
            to_emails=["admin@example.com"],
        )

        alert = Alert(
            title="Test Alert",
            message="Test message",
            severity=AlertSeverity.WARNING,
        )

        result = await channel.send(alert)

        assert result is True
        mock_smtp.assert_called_once()

    @pytest.mark.asyncio
    @patch('smtplib.SMTP')
    async def test_send_email_failure(self, mock_smtp):
        """Test email sending failure"""
        mock_smtp.side_effect = Exception("SMTP error")

        channel = EmailAlertChannel(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            username="test@example.com",
            password="password",
            from_email="alerts@example.com",
            to_emails=["admin@example.com"],
        )

        alert = Alert(
            title="Test Alert",
            message="Test message",
            severity=AlertSeverity.WARNING,
        )

        result = await channel.send(alert)

        assert result is False


class TestSlackChannel:
    """Test Slack alert channel"""

    @pytest.mark.asyncio
    async def test_send_slack_success(self):
        """Test successful Slack sending"""
        channel = SlackAlertChannel(
            webhook_url="https://hooks.slack.com/test",
        )

        alert = Alert(
            title="Test Alert",
            message="Test message",
            severity=AlertSeverity.WARNING,
        )

        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            result = await channel.send(alert)

            assert result is True
            mock_post.assert_called_once()


class TestPagerDutyChannel:
    """Test PagerDuty alert channel"""

    @pytest.mark.asyncio
    async def test_send_pagerduty_success(self):
        """Test successful PagerDuty sending"""
        channel = PagerDutyAlertChannel(
            integration_key="test_key",
        )

        alert = Alert(
            title="Critical Alert",
            message="Test message",
            severity=AlertSeverity.CRITICAL,
        )

        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 202
            mock_post.return_value = mock_response

            result = await channel.send(alert)

            assert result is True
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_pagerduty_severity_filter(self):
        """Test PagerDuty severity filtering"""
        channel = PagerDutyAlertChannel(
            integration_key="test_key",
            min_severity=AlertSeverity.CRITICAL,
        )

        # Warning alert should be filtered
        alert = Alert(
            title="Warning Alert",
            message="Test message",
            severity=AlertSeverity.WARNING,
        )

        result = await channel.send(alert)

        # Should return True but not actually send
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
