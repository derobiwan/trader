"""
Tests for WebSocket Health Monitor

Author: Sprint 2 Stream A - WebSocket Stability Team
Date: 2025-10-29
"""

import asyncio
from datetime import datetime

import pytest

from workspace.features.market_data.websocket_health import (
    HealthMetrics, WebSocketHealthMonitor)


class TestHealthMetrics:
    """Tests for HealthMetrics dataclass"""

    def test_initial_metrics(self):
        """Test initial health metrics"""
        metrics = HealthMetrics()
        assert metrics.total_messages == 0
        assert metrics.messages_per_minute == 0.0
        assert metrics.total_errors == 0
        assert metrics.error_rate == 0.0
        assert metrics.health_check_count == 0


class TestWebSocketHealthMonitor:
    """Tests for WebSocketHealthMonitor"""

    def test_initialization(self):
        """Test monitor initialization"""
        monitor = WebSocketHealthMonitor(heartbeat_interval=30)
        assert monitor.heartbeat_interval == 30
        assert monitor.is_healthy is True
        assert monitor.last_message_time is None
        assert monitor.disconnect_count == 0

    def test_record_message_updates_timestamp(self):
        """Test recording a message updates timestamp"""
        monitor = WebSocketHealthMonitor()

        before = datetime.utcnow()
        monitor.record_message()
        after = datetime.utcnow()

        assert monitor.last_message_time is not None
        assert before <= monitor.last_message_time <= after
        assert monitor.is_healthy is True
        assert monitor.metrics.total_messages == 1

    def test_record_multiple_messages(self):
        """Test recording multiple messages"""
        monitor = WebSocketHealthMonitor()

        for i in range(10):
            monitor.record_message()

        assert monitor.metrics.total_messages == 10
        assert monitor.is_healthy is True

    def test_record_error(self):
        """Test recording errors"""
        monitor = WebSocketHealthMonitor()

        # Record some messages first
        for _ in range(10):
            monitor.record_message()

        # Record error
        error = Exception("Test error")
        monitor.record_error(error)

        assert monitor.metrics.total_errors == 1
        assert monitor.metrics.error_rate == 0.1  # 1 error / 10 messages

    def test_high_error_rate_marks_unhealthy(self):
        """Test high error rate marks connection as unhealthy"""
        monitor = WebSocketHealthMonitor(error_rate_threshold=0.5)

        # Record messages and errors to exceed threshold
        monitor.record_message()
        monitor.record_error(Exception("Error 1"))
        monitor.record_error(Exception("Error 2"))

        # Error rate = 2 / 1 = 2.0 (200%) > 0.5 threshold
        assert not monitor.is_healthy

    def test_record_disconnect(self):
        """Test recording disconnect"""
        monitor = WebSocketHealthMonitor()
        monitor.is_healthy = True

        monitor.record_disconnect()

        assert monitor.disconnect_count == 1
        assert not monitor.is_healthy
        assert monitor.last_disconnect is not None

    def test_check_health_no_messages(self):
        """Test health check with no messages"""
        monitor = WebSocketHealthMonitor()

        is_healthy = monitor.check_health()

        assert not is_healthy
        assert monitor.metrics.health_check_count == 1

    def test_check_health_recent_message(self):
        """Test health check with recent message"""
        monitor = WebSocketHealthMonitor(heartbeat_interval=30)

        monitor.record_message()
        is_healthy = monitor.check_health()

        assert is_healthy
        assert monitor.metrics.health_check_count == 1

    @pytest.mark.asyncio
    async def test_check_health_stale_message(self):
        """Test health check with stale message (exceeds threshold)"""
        monitor = WebSocketHealthMonitor(
            heartbeat_interval=1,  # 1 second
            unhealthy_threshold=2.0,  # 2x = 2 seconds max
        )

        monitor.record_message()

        # Wait for message to become stale
        await asyncio.sleep(2.5)

        is_healthy = monitor.check_health()

        assert not is_healthy
        assert monitor.metrics.consecutive_unhealthy_checks == 1

    def test_consecutive_unhealthy_checks(self):
        """Test consecutive unhealthy checks counter"""
        monitor = WebSocketHealthMonitor(heartbeat_interval=1)

        # No messages recorded
        monitor.check_health()
        assert monitor.metrics.consecutive_unhealthy_checks == 1

        monitor.check_health()
        assert monitor.metrics.consecutive_unhealthy_checks == 2

        # Record message to reset counter
        monitor.record_message()
        monitor.check_health()
        assert monitor.metrics.consecutive_unhealthy_checks == 0

    def test_get_seconds_since_last_message(self):
        """Test getting seconds since last message"""
        monitor = WebSocketHealthMonitor()

        # No messages
        assert monitor.get_seconds_since_last_message() is None

        # Record message
        monitor.record_message()
        seconds = monitor.get_seconds_since_last_message()

        assert seconds is not None
        assert seconds >= 0
        assert seconds < 1  # Should be very recent

    @pytest.mark.asyncio
    async def test_get_seconds_since_last_message_with_delay(self):
        """Test seconds since last message with delay"""
        monitor = WebSocketHealthMonitor()

        monitor.record_message()
        await asyncio.sleep(0.1)

        seconds = monitor.get_seconds_since_last_message()
        assert seconds >= 0.1

    def test_get_uptime_seconds(self):
        """Test getting uptime seconds"""
        monitor = WebSocketHealthMonitor()

        # No messages
        assert monitor.get_uptime_seconds() is None

        # Record message
        monitor.record_message()
        uptime = monitor.get_uptime_seconds()

        assert uptime is not None
        assert uptime >= 0
        assert uptime < 1

    @pytest.mark.asyncio
    async def test_get_uptime_seconds_with_duration(self):
        """Test uptime calculation over time"""
        monitor = WebSocketHealthMonitor()

        monitor.record_message()
        await asyncio.sleep(0.1)

        uptime = monitor.get_uptime_seconds()
        assert uptime >= 0.1

    @pytest.mark.asyncio
    async def test_message_rate_calculation(self):
        """Test messages per minute calculation"""
        monitor = WebSocketHealthMonitor()

        # Record multiple messages over time
        for _ in range(10):
            monitor.record_message()
            await asyncio.sleep(0.01)

        # Should have calculated a rate
        assert monitor.metrics.messages_per_minute > 0

    def test_get_stats(self):
        """Test getting comprehensive statistics"""
        monitor = WebSocketHealthMonitor()

        monitor.record_message()
        monitor.record_error(Exception("Test"))
        monitor.check_health()

        stats = monitor.get_stats()

        # Verify all expected keys exist
        assert "is_healthy" in stats
        assert "last_message_seconds_ago" in stats
        assert "uptime_seconds" in stats
        assert "total_messages" in stats
        assert "messages_per_minute" in stats
        assert "total_errors" in stats
        assert "error_rate" in stats
        assert "disconnect_count" in stats
        assert "health_check_count" in stats
        assert "heartbeat_interval" in stats

        # Verify values
        assert stats["total_messages"] == 1
        assert stats["total_errors"] == 1
        assert stats["health_check_count"] == 1

    def test_reset_metrics(self):
        """Test resetting metrics"""
        monitor = WebSocketHealthMonitor()

        # Generate some metrics
        for _ in range(10):
            monitor.record_message()
        monitor.record_error(Exception("Test"))
        monitor.check_health()

        # Reset
        monitor.reset_metrics()

        # Verify reset
        assert monitor.metrics.total_messages == 0
        assert monitor.metrics.total_errors == 0
        assert monitor.metrics.health_check_count == 0
        assert monitor.metrics.messages_per_minute == 0.0

    def test_custom_thresholds(self):
        """Test custom heartbeat and threshold values"""
        monitor = WebSocketHealthMonitor(
            heartbeat_interval=60,
            unhealthy_threshold=3.0,
            error_rate_threshold=0.2,
        )

        assert monitor.heartbeat_interval == 60
        assert monitor.unhealthy_threshold == 3.0
        assert monitor.error_rate_threshold == 0.2

        # Max silence should be 60 * 3 = 180 seconds
        stats = monitor.get_stats()
        assert stats["max_silence_seconds"] == 180

    @pytest.mark.asyncio
    async def test_health_degradation_over_time(self):
        """Test that health degrades when no messages received"""
        monitor = WebSocketHealthMonitor(
            heartbeat_interval=0.1, unhealthy_threshold=2.0
        )

        # Initial message
        monitor.record_message()
        assert monitor.check_health()

        # Wait and check - should still be healthy
        await asyncio.sleep(0.1)
        assert monitor.check_health()

        # Wait longer - should become unhealthy
        await asyncio.sleep(0.15)
        assert not monitor.check_health()

    def test_error_rate_calculation(self):
        """Test error rate calculation accuracy"""
        monitor = WebSocketHealthMonitor()

        # 8 messages, 2 errors = 25% error rate
        for _ in range(8):
            monitor.record_message()

        monitor.record_error(Exception("Error 1"))
        monitor.record_error(Exception("Error 2"))

        assert monitor.metrics.total_messages == 8
        assert monitor.metrics.total_errors == 2
        assert monitor.metrics.error_rate == 0.25  # 2/8 = 0.25

    def test_multiple_disconnects(self):
        """Test tracking multiple disconnects"""
        monitor = WebSocketHealthMonitor()

        for i in range(5):
            monitor.record_disconnect()

        assert monitor.disconnect_count == 5
        assert monitor.last_disconnect is not None


class TestWebSocketHealthMonitorIntegration:
    """Integration tests for health monitor"""

    @pytest.mark.asyncio
    async def test_realistic_healthy_scenario(self):
        """Test realistic scenario with healthy connection"""
        monitor = WebSocketHealthMonitor(heartbeat_interval=1)

        # Simulate messages arriving regularly
        for _ in range(10):
            monitor.record_message()
            await asyncio.sleep(0.1)
            assert monitor.check_health()

        stats = monitor.get_stats()
        assert stats["is_healthy"]
        assert stats["total_messages"] == 10
        assert stats["consecutive_unhealthy_checks"] == 0

    @pytest.mark.asyncio
    async def test_realistic_unhealthy_scenario(self):
        """Test realistic scenario with unhealthy connection"""
        monitor = WebSocketHealthMonitor(
            heartbeat_interval=0.5, unhealthy_threshold=2.0
        )

        # Start healthy
        monitor.record_message()
        assert monitor.check_health()

        # Simulate connection problems - no messages
        await asyncio.sleep(1.5)

        # Should be unhealthy now
        assert not monitor.check_health()
        assert monitor.metrics.consecutive_unhealthy_checks > 0

    @pytest.mark.asyncio
    async def test_recovery_scenario(self):
        """Test recovery from unhealthy state"""
        monitor = WebSocketHealthMonitor(
            heartbeat_interval=0.5, unhealthy_threshold=2.0
        )

        # Start healthy
        monitor.record_message()
        assert monitor.check_health()

        # Become unhealthy
        await asyncio.sleep(1.5)
        assert not monitor.check_health()

        # Recover with new message
        monitor.record_message()
        assert monitor.check_health()
        assert monitor.metrics.consecutive_unhealthy_checks == 0

    @pytest.mark.asyncio
    async def test_high_message_rate(self):
        """Test with high message rate"""
        monitor = WebSocketHealthMonitor()

        # Simulate high rate (100 messages in 1 second)
        start = datetime.utcnow()
        for _ in range(100):
            monitor.record_message()
            await asyncio.sleep(0.01)

        (datetime.utcnow() - start).total_seconds()

        # Should have high messages per minute
        assert monitor.metrics.messages_per_minute > 0
        assert monitor.metrics.total_messages == 100
        assert monitor.check_health()
