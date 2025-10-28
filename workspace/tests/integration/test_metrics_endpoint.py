"""
Integration tests for Prometheus metrics endpoint

Tests the metrics API including /metrics, /health, /ready, and /live endpoints.

Author: Trading System Implementation Team
Date: 2025-10-28
"""

import pytest
import pytest_asyncio
from decimal import Decimal
from datetime import datetime, timedelta
from httpx import AsyncClient, ASGITransport

from workspace.features.monitoring.metrics import MetricsService
from workspace.features.monitoring.metrics.metrics_api import app, init_metrics_service


class TestMetricsEndpoint:
    """Test suite for Prometheus metrics endpoint"""

    @pytest_asyncio.fixture
    async def metrics_service(self):
        """Create MetricsService with test data"""
        metrics = MetricsService()

        # Add some test metrics
        metrics.record_trade(
            success=True,
            realized_pnl=Decimal("150.50"),
            fees=Decimal("5.25"),
            latency_ms=Decimal("45.2"),
        )
        metrics.record_trade(
            success=True,
            realized_pnl=Decimal("-75.30"),
            fees=Decimal("3.10"),
            latency_ms=Decimal("52.1"),
        )
        metrics.record_trade(
            success=False,
        )

        metrics.record_position_opened()
        metrics.record_llm_call(
            success=True,
            tokens_input=500,
            tokens_output=150,
            cost_usd=Decimal("0.05"),
        )

        return metrics

    @pytest_asyncio.fixture
    async def client(self, metrics_service):
        """Create test client with initialized metrics"""
        init_metrics_service(metrics_service)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    @pytest.mark.asyncio
    async def test_metrics_endpoint_returns_prometheus_format(self, client):
        """Test /metrics endpoint returns Prometheus format"""
        response = await client.get("/metrics")

        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]

        # Check for key metrics
        content = response.text
        assert "trading_trades_total" in content
        assert "trading_trades_successful" in content
        assert "trading_trades_failed" in content
        assert "trading_realized_pnl_total" in content
        assert "trading_fees_paid_total" in content
        assert "trading_positions_open" in content
        assert "trading_llm_calls_total" in content

    @pytest.mark.asyncio
    async def test_metrics_endpoint_contains_correct_values(self, client, metrics_service):
        """Test metrics contain correct values"""
        response = await client.get("/metrics")

        content = response.text

        # Verify trade counts
        assert "trading_trades_total 3" in content  # 3 total trades
        assert "trading_trades_successful 2" in content  # 2 successful
        assert "trading_trades_failed 1" in content  # 1 failed

        # Verify P&L (150.50 - 75.30 = 75.20)
        assert "trading_realized_pnl_total 75.2" in content

        # Verify fees (5.25 + 3.10 = 8.35)
        assert "trading_fees_paid_total 8.35" in content

        # Verify positions
        assert "trading_positions_open 1" in content

        # Verify LLM calls
        assert "trading_llm_calls_total 1" in content
        assert "trading_llm_tokens_input_total 500" in content
        assert "trading_llm_tokens_output_total 150" in content

    @pytest.mark.asyncio
    async def test_metrics_endpoint_without_initialization(self):
        """Test /metrics returns error when service not initialized"""
        # Reset global service
        import workspace.features.monitoring.metrics.metrics_api as api_module
        api_module._metrics_service = None

        # Create new client without initialization
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/metrics")

            assert response.status_code == 200
            assert "Metrics service not initialized" in response.text

    @pytest.mark.asyncio
    async def test_metrics_endpoint_updates_with_new_data(self, client, metrics_service):
        """Test metrics endpoint reflects new data"""
        # Initial fetch
        response1 = await client.get("/metrics")
        content1 = response1.text

        # Add more trades
        metrics_service.record_trade(success=True, fees=Decimal("2.0"))
        metrics_service.record_trade(success=True, fees=Decimal("3.0"))

        # Fetch again
        response2 = await client.get("/metrics")
        content2 = response2.text

        # Verify counts increased
        assert "trading_trades_total 5" in content2  # Was 3, now 5
        assert "trading_trades_successful 4" in content2  # Was 2, now 4

        # Verify fees increased (8.35 + 2.0 + 3.0 = 13.35)
        assert "trading_fees_paid_total 13.35" in content2

    @pytest.mark.asyncio
    async def test_metrics_latency_percentiles(self, client):
        """Test that latency percentiles are included"""
        response = await client.get("/metrics")
        content = response.text

        # Check for latency metrics
        assert "trading_execution_latency_avg_ms" in content
        assert "trading_execution_latency_p95_ms" in content
        assert "trading_execution_latency_p99_ms" in content

    @pytest.mark.asyncio
    async def test_metrics_system_uptime(self, client):
        """Test that system uptime is included"""
        response = await client.get("/metrics")
        content = response.text

        # Check for uptime metric
        assert "trading_system_uptime_seconds" in content

    @pytest.mark.asyncio
    async def test_health_endpoint(self, client):
        """Test /health always returns 200"""
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_ready_endpoint_not_ready_initially(self):
        """Test /ready returns 503 when not initialized"""
        # Reset global service
        import workspace.features.monitoring.metrics.metrics_api as api_module
        api_module._metrics_service = None

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/ready")

            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "not ready"
            assert data["reason"] == "metrics not initialized"

    @pytest.mark.asyncio
    async def test_ready_endpoint_not_ready_during_startup(self, metrics_service):
        """Test /ready returns 503 during startup period"""
        # Create a fresh metrics service (uptime < 10s)
        fresh_metrics = MetricsService()
        init_metrics_service(fresh_metrics)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/ready")

            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "not ready"
            assert "system initializing" in data["reason"]

    @pytest.mark.asyncio
    async def test_ready_endpoint_ready_after_startup(self, client, metrics_service):
        """Test /ready returns 200 after startup period"""
        # Simulate system running for > 10 seconds by manipulating start time
        import time
        metrics_service.start_time = time.time() - 15  # 15 seconds ago

        response = await client.get("/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["uptime_seconds"] >= 15

    @pytest.mark.asyncio
    async def test_live_endpoint_alive(self, client, metrics_service):
        """Test /live returns 200 when system is functioning"""
        # Set recent trade timestamp
        metrics_service.metrics.last_trade_timestamp = datetime.utcnow()

        response = await client.get("/live")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert data["last_trade_seconds_ago"] is not None
        assert data["last_trade_seconds_ago"] < 10  # Recent trade

    @pytest.mark.asyncio
    async def test_live_endpoint_unhealthy_when_frozen(self, client, metrics_service):
        """Test /live returns 503 when no trades for > 10 minutes"""
        # Set old trade timestamp (15 minutes ago)
        metrics_service.metrics.last_trade_timestamp = datetime.utcnow() - timedelta(minutes=15)

        response = await client.get("/live")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "no trades for" in data["reason"]

    @pytest.mark.asyncio
    async def test_live_endpoint_no_metrics_service(self):
        """Test /live returns 503 when metrics service not initialized"""
        # Reset global service
        import workspace.features.monitoring.metrics.metrics_api as api_module
        api_module._metrics_service = None

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/live")

            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "dead"
            assert "metrics not initialized" in data["reason"]

    @pytest.mark.asyncio
    async def test_live_endpoint_no_trades_yet(self, client, metrics_service):
        """Test /live when no trades have been executed yet"""
        # Clear trade timestamp
        metrics_service.metrics.last_trade_timestamp = None

        response = await client.get("/live")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert data["last_trade_seconds_ago"] is None

    @pytest.mark.asyncio
    async def test_all_endpoints_have_timestamps(self, client):
        """Test all endpoints include timestamps"""
        endpoints = ["/health", "/ready", "/live"]

        for endpoint in endpoints:
            response = await client.get(endpoint)
            data = response.json()

            assert "timestamp" in data
            # Verify timestamp is in ISO format
            datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
