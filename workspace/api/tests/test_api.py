"""
API Tests - FastAPI Application

Tests for:
- Health check endpoints
- Middleware functionality
- Error handling
- Configuration
- Request/response flow

Uses FastAPI TestClient for synchronous testing.
"""

import pytest
from fastapi.testclient import TestClient
import time

from workspace.api.config import Settings


# ==================== Fixtures ====================
@pytest.fixture
def client():
    """Create test client for API testing."""
    # Create a fresh TestClient for each test to avoid rate limit carryover
    from workspace.api.main import create_application

    test_app = create_application()
    return TestClient(test_app)


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    return Settings(
        app_name="test-app",
        environment="test",
        debug=True,
        host="localhost",
        port=8000,
        db_host="localhost",
        db_user="test",
        db_password="test",
        redis_host="localhost",
    )


# ==================== Health Check Tests ====================
class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_basic_health_check(self, client):
        """Test basic health check returns 200 and correct structure."""
        response = client.get("/health/")

        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "uptime_seconds" in data
        assert isinstance(data["uptime_seconds"], (int, float))
        assert data["uptime_seconds"] >= 0

    def test_liveness_check(self, client):
        """Test liveness check is fast and returns correct structure."""
        start_time = time.time()
        response = client.get("/health/live")
        duration = time.time() - start_time

        assert response.status_code == 200

        data = response.json()
        assert data["alive"] is True
        assert "timestamp" in data

        # Should be very fast (< 100ms)
        assert duration < 0.1

    def test_readiness_check_structure(self, client):
        """Test readiness check returns correct structure."""
        response = client.get("/health/ready")

        # May return 200 or 503 depending on dependencies
        assert response.status_code in [200, 503]

        data = response.json()
        assert "status" in data
        assert data["status"] in ["ready", "not_ready"]
        assert "timestamp" in data
        assert "checks" in data
        assert isinstance(data["checks"], list)
        assert "ready" in data
        assert isinstance(data["ready"], bool)

        # Check each dependency check has required fields
        for check in data["checks"]:
            assert "name" in check
            assert "status" in check
            assert check["status"] in ["healthy", "degraded", "unhealthy"]

    def test_metrics_endpoint(self, client):
        """Test metrics endpoint returns system metrics."""
        response = client.get("/health/metrics")

        assert response.status_code == 200

        data = response.json()
        assert "timestamp" in data
        assert "uptime_seconds" in data
        assert "cpu_percent" in data
        assert "memory_mb" in data
        assert "memory_percent" in data
        assert "disk_usage_percent" in data

        # Validate metric types
        assert isinstance(data["uptime_seconds"], (int, float))
        assert isinstance(data["cpu_percent"], (int, float))
        assert isinstance(data["memory_mb"], (int, float))
        assert isinstance(data["memory_percent"], (int, float))
        assert isinstance(data["disk_usage_percent"], (int, float))

        # Validate metric ranges
        assert data["cpu_percent"] >= 0
        assert data["memory_percent"] >= 0
        assert data["disk_usage_percent"] >= 0


# ==================== Middleware Tests ====================
class TestMiddleware:
    """Tests for middleware functionality."""

    def test_request_id_header(self, client):
        """Test that request ID is added to response headers."""
        response = client.get("/health/")

        assert "x-request-id" in response.headers
        request_id = response.headers["x-request-id"]

        # Should be a valid UUID format
        assert len(request_id) == 36  # UUID4 format: 8-4-4-4-12
        assert request_id.count("-") == 4

    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.options(
            "/health/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        # Should have CORS headers
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers

    def test_rate_limit_headers(self, client):
        """Test rate limit headers are added to responses."""
        response = client.get("/")

        # Rate limit headers should be present
        assert "x-ratelimit-limit" in response.headers
        assert "x-ratelimit-remaining" in response.headers
        assert "x-ratelimit-reset" in response.headers

        # Validate header values
        limit = int(response.headers["x-ratelimit-limit"])
        remaining = int(response.headers["x-ratelimit-remaining"])
        reset = int(response.headers["x-ratelimit-reset"])

        assert limit > 0
        assert remaining >= 0
        assert remaining <= limit
        # Reset time should be a valid unix timestamp
        assert reset > 0

    def test_rate_limiting_enforcement(self, client):
        """Test that rate limiting blocks excessive requests."""
        # Make many requests quickly
        responses = []
        for _ in range(150):  # More than default limit (100)
            response = client.get("/")
            responses.append(response)

        # Should eventually get rate limited
        status_codes = [r.status_code for r in responses]
        assert 429 in status_codes  # Too Many Requests

        # Find the rate limit response
        rate_limited = [r for r in responses if r.status_code == 429][0]

        # Should have rate limit error
        data = rate_limited.json()
        assert "error" in data
        assert "rate limit" in data["error"].lower()
        assert "retry_after" in data


# ==================== Root Endpoint Tests ====================
class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root_endpoint(self, client):
        """Test root endpoint returns API information."""
        response = client.get("/")

        assert response.status_code == 200

        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "status" in data
        assert "timestamp" in data
        assert "environment" in data
        assert "endpoints" in data

        # Check endpoints dictionary
        endpoints = data["endpoints"]
        assert "health" in endpoints
        assert "readiness" in endpoints
        assert "liveness" in endpoints
        assert "metrics" in endpoints


# ==================== Error Handling Tests ====================
class TestErrorHandling:
    """Tests for error handling."""

    def test_404_not_found(self, client):
        """Test 404 error returns proper JSON response."""
        response = client.get("/nonexistent-endpoint")

        assert response.status_code == 404

        data = response.json()
        assert "error" in data
        assert data["error"] == "Not found"
        assert "request_id" in data

    def test_validation_error_structure(self, client):
        """Test validation errors return proper structure."""
        # Test with a non-existent endpoint to verify error handling
        # This will be more relevant when we have POST endpoints with validation
        response = client.get("/nonexistent")

        # Should return 404
        assert response.status_code == 404
        data = response.json()
        assert "error" in data


# ==================== Configuration Tests ====================
class TestConfiguration:
    """Tests for configuration management."""

    def test_settings_load_defaults(self):
        """Test settings load with default values."""
        settings = Settings()

        assert settings.app_name == "trading-system"
        assert settings.environment == "development"
        assert settings.host == "0.0.0.0"
        assert settings.port == 8000

    def test_settings_validation_environment(self):
        """Test environment validation."""
        # Valid environments
        for env in ["development", "staging", "production"]:
            settings = Settings(environment=env)
            assert settings.environment == env

        # Invalid environment should raise error
        with pytest.raises(ValueError):
            Settings(environment="invalid")

    def test_settings_validation_capital(self):
        """Test capital validation."""
        # Positive capital should work
        settings = Settings(capital_chf=1000.0)
        assert settings.capital_chf > 0

        # Negative capital should fail
        with pytest.raises(ValueError):
            Settings(capital_chf=-1000.0)

    def test_settings_validation_circuit_breaker(self):
        """Test circuit breaker validation."""
        # Negative value (loss limit) should work
        settings = Settings(circuit_breaker_chf=-100.0)
        assert settings.circuit_breaker_chf < 0

        # Positive value should fail
        with pytest.raises(ValueError):
            Settings(circuit_breaker_chf=100.0)

    def test_database_url_generation(self):
        """Test database URL is generated correctly."""
        settings = Settings(
            db_user="testuser",
            db_password="testpass",
            db_host="testhost",
            db_port=5432,
            db_name="testdb",
        )

        expected = "postgresql://testuser:testpass@testhost:5432/testdb"
        assert settings.database_url == expected

    def test_redis_url_generation(self):
        """Test Redis URL is generated correctly."""
        # Without password
        settings = Settings(
            redis_host="localhost", redis_port=6379, redis_db=0, redis_password=None
        )
        assert settings.redis_url == "redis://localhost:6379/0"

        # With password
        settings = Settings(
            redis_host="localhost", redis_port=6379, redis_db=0, redis_password="secret"
        )
        assert settings.redis_url == "redis://:secret@localhost:6379/0"

    def test_cors_config_generation(self):
        """Test CORS configuration generation."""
        settings = Settings(
            cors_origins=["http://localhost:3000"], cors_allow_credentials=True
        )

        cors_config = settings.get_cors_config()

        assert "allow_origins" in cors_config
        assert "allow_credentials" in cors_config
        assert "allow_methods" in cors_config
        assert "allow_headers" in cors_config

        assert cors_config["allow_origins"] == ["http://localhost:3000"]
        assert cors_config["allow_credentials"] is True


# ==================== Integration Tests ====================
class TestIntegration:
    """Integration tests for full request flow."""

    def test_full_request_flow(self, client):
        """Test complete request flow through all middleware."""
        # Use root endpoint since health endpoints skip rate limiting
        response = client.get("/")

        # Should succeed
        assert response.status_code == 200

        # Should have request ID
        assert "x-request-id" in response.headers

        # Should have rate limit headers (not on health endpoints)
        assert "x-ratelimit-limit" in response.headers

        # Response should be valid JSON
        data = response.json()
        assert isinstance(data, dict)

    def test_concurrent_requests(self, client):
        """Test handling of concurrent requests."""
        import concurrent.futures

        def make_request():
            return client.get("/health/")

        # Make 10 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            responses = [f.result() for f in futures]

        # All should succeed
        assert all(r.status_code == 200 for r in responses)

        # All should have unique request IDs
        request_ids = [r.headers["x-request-id"] for r in responses]
        assert len(set(request_ids)) == len(request_ids)


# ==================== Performance Tests ====================
class TestPerformance:
    """Performance tests for API endpoints."""

    def test_health_check_performance(self, client):
        """Test health check is fast."""
        start_time = time.time()
        response = client.get("/health/")
        duration = time.time() - start_time

        assert response.status_code == 200
        assert duration < 0.1  # Should be < 100ms

    def test_liveness_check_performance(self, client):
        """Test liveness check is very fast."""
        start_time = time.time()
        response = client.get("/health/live")
        duration = time.time() - start_time

        assert response.status_code == 200
        assert duration < 0.05  # Should be < 50ms


if __name__ == "__main__":
    """Run tests with pytest."""
    pytest.main([__file__, "-v", "--tb=short"])
