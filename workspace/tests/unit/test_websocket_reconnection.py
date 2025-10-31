"""
Tests for WebSocket Reconnection Manager

Author: Sprint 2 Stream A - WebSocket Stability Team
Date: 2025-10-29
"""

import pytest
import asyncio
from datetime import datetime
from workspace.features.market_data.websocket_reconnection import (
    WebSocketReconnectionManager,
    ReconnectionStats,
)


class TestReconnectionStats:
    """Tests for ReconnectionStats"""

    def test_initial_stats(self):
        """Test initial statistics"""
        stats = ReconnectionStats()
        assert stats.total_attempts == 0
        assert stats.successful_reconnections == 0
        assert stats.failed_attempts == 0
        assert stats.last_disconnect is None
        assert stats.last_reconnect is None

    def test_uptime_calculation_no_connection(self):
        """Test uptime calculation with no connection"""
        stats = ReconnectionStats()
        assert stats.calculate_uptime_percentage() == 0.0

    def test_uptime_calculation_100_percent(self):
        """Test uptime calculation with 100% uptime"""
        stats = ReconnectionStats()
        stats.current_uptime_start = datetime.utcnow()
        stats.total_downtime_seconds = 0.0

        uptime = stats.calculate_uptime_percentage()
        assert uptime >= 99.0  # Should be close to 100%

    def test_uptime_calculation_with_downtime(self):
        """Test uptime calculation with some downtime"""
        stats = ReconnectionStats()
        stats.current_uptime_start = datetime.utcnow()
        stats.total_downtime_seconds = 0.05  # 50ms downtime

        # Wait a bit to have some uptime
        import time

        time.sleep(0.1)

        uptime = stats.calculate_uptime_percentage()
        assert 0 < uptime < 100


class TestWebSocketReconnectionManager:
    """Tests for WebSocketReconnectionManager"""

    def test_initialization(self):
        """Test manager initialization"""
        manager = WebSocketReconnectionManager(base_delay=1.0, max_delay=60.0)
        assert manager.base_delay == 1.0
        assert manager.max_delay == 60.0
        assert manager.attempt == 0
        assert not manager.is_connected
        assert not manager.is_connecting

    def test_exponential_backoff_calculation(self):
        """Test exponential backoff calculation"""
        manager = WebSocketReconnectionManager(base_delay=1.0, max_delay=10.0)

        delays = []
        for i in range(5):
            manager.attempt = i
            delay = manager.calculate_backoff()
            delays.append(delay)

        # Should increase exponentially (with some jitter)
        assert delays[1] > delays[0] * 1.5  # ~2x with jitter
        assert delays[2] > delays[1] * 1.5  # ~2x with jitter

        # Should cap at max_delay (with jitter tolerance)
        assert all(d <= 11.0 for d in delays)  # max + 10% jitter
        assert all(d >= 0 for d in delays)  # Non-negative

    def test_backoff_respects_max_delay(self):
        """Test that backoff respects max_delay"""
        manager = WebSocketReconnectionManager(base_delay=1.0, max_delay=5.0)

        # Set high attempt number
        manager.attempt = 10
        delay = manager.calculate_backoff()

        # Should not exceed max_delay + jitter
        assert delay <= 5.5  # 5.0 + 10% jitter

    def test_backoff_with_zero_jitter(self):
        """Test backoff with zero jitter"""
        manager = WebSocketReconnectionManager(
            base_delay=2.0,
            max_delay=60.0,
            jitter_range=0.0,  # No jitter
        )

        expected_delays = [2.0, 4.0, 8.0, 16.0, 32.0, 60.0]

        for i, expected in enumerate(expected_delays):
            manager.attempt = i
            delay = manager.calculate_backoff()
            assert delay == expected

    @pytest.mark.asyncio
    async def test_successful_connection_first_attempt(self):
        """Test successful connection on first attempt"""
        manager = WebSocketReconnectionManager()

        call_count = 0

        async def mock_connect():
            nonlocal call_count
            call_count += 1
            # Success immediately

        success = await manager.connect_with_retry(mock_connect)

        assert success
        assert manager.is_connected
        assert not manager.is_connecting
        assert call_count == 1
        assert manager.stats.successful_reconnections == 1
        assert manager.stats.total_attempts == 1

    @pytest.mark.asyncio
    async def test_successful_connection_after_retries(self):
        """Test successful connection after multiple retries"""
        manager = WebSocketReconnectionManager(base_delay=0.01, max_delay=0.1)

        call_count = 0

        async def mock_connect():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Connection failed")
            # Success on 3rd attempt

        success = await manager.connect_with_retry(mock_connect)

        assert success
        assert manager.is_connected
        assert call_count == 3
        assert manager.stats.successful_reconnections == 1
        assert manager.stats.total_attempts == 3

    @pytest.mark.asyncio
    async def test_max_attempts_reached(self):
        """Test connection fails after max attempts"""
        manager = WebSocketReconnectionManager(
            base_delay=0.01, max_delay=0.1, max_attempts=3
        )

        call_count = 0

        async def mock_connect():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Always fails")

        success = await manager.connect_with_retry(mock_connect)

        assert not success
        assert not manager.is_connected
        assert not manager.is_connecting
        assert call_count == 3  # Should stop at max_attempts
        assert manager.stats.total_attempts == 3

    @pytest.mark.asyncio
    async def test_on_attempt_callback(self):
        """Test on_attempt callback is called"""
        manager = WebSocketReconnectionManager(base_delay=0.01, max_delay=0.1)

        attempts = []
        delays = []

        def on_attempt(attempt, delay):
            attempts.append(attempt)
            delays.append(delay)

        call_count = 0

        async def mock_connect():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Connection failed")

        await manager.connect_with_retry(mock_connect, on_attempt=on_attempt)

        # Callback should be called for failed attempts
        assert len(attempts) == 2  # 2 failures before success
        assert len(delays) == 2
        assert all(d > 0 for d in delays)

    @pytest.mark.asyncio
    async def test_on_attempt_async_callback(self):
        """Test async on_attempt callback works"""
        manager = WebSocketReconnectionManager(base_delay=0.01, max_delay=0.1)

        attempts = []

        async def on_attempt_async(attempt, delay):
            await asyncio.sleep(0.001)  # Simulate async work
            attempts.append(attempt)

        call_count = 0

        async def mock_connect():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Connection failed")

        await manager.connect_with_retry(mock_connect, on_attempt=on_attempt_async)

        assert len(attempts) == 1  # 1 failure before success

    def test_mark_disconnected(self):
        """Test marking connection as disconnected"""
        manager = WebSocketReconnectionManager()
        manager.is_connected = True

        manager.mark_disconnected()

        assert not manager.is_connected
        assert manager.stats.last_disconnect is not None

    def test_mark_disconnected_when_already_disconnected(self):
        """Test marking disconnected when already disconnected"""
        manager = WebSocketReconnectionManager()
        manager.is_connected = False

        manager.mark_disconnected()

        # Should not update last_disconnect
        assert manager.stats.last_disconnect is None

    def test_reset_backoff(self):
        """Test resetting backoff counter"""
        manager = WebSocketReconnectionManager()
        manager.attempt = 5

        manager.reset()

        assert manager.attempt == 0

    def test_get_stats(self):
        """Test getting reconnection statistics"""
        manager = WebSocketReconnectionManager()
        manager.is_connected = True
        manager.stats.total_attempts = 5
        manager.stats.successful_reconnections = 2
        manager.stats.failed_attempts = 3

        stats = manager.get_stats()

        assert stats["is_connected"] is True
        assert stats["is_connecting"] is False
        assert stats["total_attempts"] == 5
        assert stats["successful_reconnections"] == 2
        assert stats["failed_attempts"] == 3
        assert "uptime_percentage" in stats
        assert "total_downtime_seconds" in stats

    @pytest.mark.asyncio
    async def test_downtime_tracking(self):
        """Test that downtime is tracked correctly"""
        manager = WebSocketReconnectionManager(base_delay=0.01, max_delay=0.1)

        # Simulate initial connection
        manager.is_connected = True
        manager.stats.current_uptime_start = datetime.utcnow()

        # Simulate disconnect
        manager.mark_disconnected()
        datetime.utcnow()

        # Wait a bit
        await asyncio.sleep(0.1)

        # Reconnect
        async def mock_connect():
            pass

        await manager.connect_with_retry(mock_connect)

        # Check downtime was recorded
        assert manager.stats.total_downtime_seconds >= 0.1

    @pytest.mark.asyncio
    async def test_uptime_percentage_after_reconnect(self):
        """Test uptime percentage calculation after reconnection"""
        manager = WebSocketReconnectionManager(base_delay=0.01, max_delay=0.1)

        # Initial connection
        async def mock_connect():
            pass

        await manager.connect_with_retry(mock_connect)

        # Wait for some uptime
        await asyncio.sleep(0.1)

        # Disconnect
        manager.mark_disconnected()
        await asyncio.sleep(0.05)  # 50ms downtime

        # Reconnect
        await manager.connect_with_retry(mock_connect)

        # Check uptime percentage
        uptime = manager.stats.calculate_uptime_percentage()
        assert 0 < uptime < 100  # Should be between 0 and 100
        assert uptime > 50  # Should be more than 50% uptime


class TestReconnectionManagerIntegration:
    """Integration tests for reconnection manager"""

    @pytest.mark.asyncio
    async def test_multiple_reconnection_cycles(self):
        """Test multiple connect/disconnect/reconnect cycles"""
        manager = WebSocketReconnectionManager(base_delay=0.01, max_delay=0.1)

        async def mock_connect():
            await asyncio.sleep(0.01)

        # First connection
        await manager.connect_with_retry(mock_connect)
        assert manager.is_connected

        # Disconnect and reconnect
        manager.mark_disconnected()
        await manager.connect_with_retry(mock_connect)
        assert manager.is_connected

        # Another cycle
        manager.mark_disconnected()
        await manager.connect_with_retry(mock_connect)
        assert manager.is_connected

        # Check stats
        assert manager.stats.successful_reconnections == 3
        assert manager.stats.total_attempts >= 3

    @pytest.mark.asyncio
    async def test_concurrent_connection_attempts_prevented(self):
        """Test that concurrent connection attempts are properly handled"""
        manager = WebSocketReconnectionManager(base_delay=0.01, max_delay=0.1)

        async def slow_connect():
            await asyncio.sleep(0.1)

        # Start connection
        task1 = asyncio.create_task(manager.connect_with_retry(slow_connect))

        # Verify is_connecting is set
        await asyncio.sleep(0.01)
        assert manager.is_connecting

        # Wait for completion
        await task1
        assert manager.is_connected
        assert not manager.is_connecting
