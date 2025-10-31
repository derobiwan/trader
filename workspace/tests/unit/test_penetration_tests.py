"""
Unit tests for Penetration Testing Suite.

Tests core functionality:
- SQL injection testing
- XSS testing
- Authentication bypass
- Rate limiting
- Report generation

Target: 80%+ code coverage
"""

import pytest
import pytest_asyncio
import aiohttp
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from workspace.shared.security.penetration_tests import (
    PenetrationTester,
    PenTestConfig,
    VulnerabilityFinding,
    PenTestResult,
    AttackType,
    VulnerabilityLevel,
)


@pytest.fixture
def pentest_config():
    """Create penetration test configuration."""
    return PenTestConfig(
        base_url="http://localhost:8000", safe_mode=True, skip_destructive_tests=True
    )


@pytest_asyncio.fixture
async def penetration_tester(pentest_config):
    """Create PenetrationTester instance."""
    async with PenetrationTester(pentest_config) as tester:
        yield tester


@pytest.mark.asyncio
async def test_context_manager(pentest_config):
    """Test async context manager."""
    async with PenetrationTester(pentest_config) as tester:
        assert tester.session is not None
        assert isinstance(tester.session, aiohttp.ClientSession)


@pytest.mark.asyncio
async def test_sql_injection_test_structure(penetration_tester):
    """Test SQL injection test structure."""
    # Mock HTTP responses
    with patch.object(
        penetration_tester, "_test_endpoint_with_payload", return_value=None
    ):
        # Act
        result = await penetration_tester.test_sql_injection()

        # Assert
        assert isinstance(result, PenTestResult)
        assert result.test_type == AttackType.SQL_INJECTION
        assert result.total_tests > 0


@pytest.mark.asyncio
async def test_sql_injection_vulnerability_found(penetration_tester):
    """Test SQL injection with vulnerability found."""
    # Arrange
    mock_finding = VulnerabilityFinding(
        finding_id="SQL-001",
        attack_type=AttackType.SQL_INJECTION,
        vulnerability_level=VulnerabilityLevel.CRITICAL,
        endpoint="/api/test",
        description="SQL injection found",
        payload_used="' OR '1'='1",
        response_evidence="Unexpected behavior",
        cwe_id="CWE-89",
    )

    with patch.object(
        penetration_tester, "_test_endpoint_with_payload", return_value=mock_finding
    ):
        # Act
        result = await penetration_tester.test_sql_injection()

        # Assert
        assert result.vulnerabilities_found > 0
        assert result.critical_count > 0


@pytest.mark.asyncio
async def test_xss_test_structure(penetration_tester):
    """Test XSS test structure."""
    # Mock HTTP responses
    with patch.object(
        penetration_tester, "_test_endpoint_with_payload", return_value=None
    ):
        # Act
        result = await penetration_tester.test_xss()

        # Assert
        assert isinstance(result, PenTestResult)
        assert result.test_type == AttackType.XSS
        assert result.total_tests > 0


@pytest.mark.asyncio
async def test_authentication_bypass(penetration_tester):
    """Test authentication bypass testing."""
    # Mock HTTP responses
    mock_response = Mock()
    mock_response.status = 401
    mock_response.text = AsyncMock(return_value="Unauthorized")

    with patch.object(
        penetration_tester.session,
        "get",
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)),
    ):
        # Act
        result = await penetration_tester.test_authentication()

        # Assert
        assert isinstance(result, PenTestResult)
        assert result.test_type == AttackType.AUTHENTICATION_BYPASS


@pytest.mark.asyncio
async def test_rate_limiting(penetration_tester):
    """Test rate limiting detection."""
    # Mock HTTP responses
    mock_response = Mock()
    mock_response.status = 200

    with patch.object(
        penetration_tester.session,
        "get",
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)),
    ):
        # Act
        result = await penetration_tester.test_rate_limiting()

        # Assert
        assert isinstance(result, PenTestResult)
        assert result.test_type == AttackType.RATE_LIMITING


@pytest.mark.asyncio
async def test_input_validation(penetration_tester):
    """Test input validation checks."""
    # Mock HTTP responses
    with patch.object(
        penetration_tester, "_test_endpoint_with_payload", return_value=None
    ):
        # Act
        result = await penetration_tester.test_input_validation()

        # Assert
        assert isinstance(result, PenTestResult)
        assert result.test_type == AttackType.INPUT_VALIDATION


@pytest.mark.asyncio
async def test_api_security(penetration_tester):
    """Test API security checks."""
    # Mock HTTP responses
    mock_response = Mock()
    mock_response.status = 200
    mock_response.headers = {}

    with patch.object(
        penetration_tester.session,
        "options",
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)),
    ):
        # Act
        result = await penetration_tester.test_api_security()

        # Assert
        assert isinstance(result, PenTestResult)
        assert result.test_type == AttackType.API_SECURITY


@pytest.mark.asyncio
async def test_run_all_tests(penetration_tester):
    """Test running all penetration tests."""
    # Mock all test methods
    with (
        patch.object(
            penetration_tester,
            "test_sql_injection",
            return_value=PenTestResult(
                test_type=AttackType.SQL_INJECTION,
                timestamp=datetime.now(),
                total_tests=10,
                vulnerabilities_found=0,
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                findings=[],
                test_duration_ms=100.0,
                test_status="success",
            ),
        ),
        patch.object(
            penetration_tester,
            "test_xss",
            return_value=PenTestResult(
                test_type=AttackType.XSS,
                timestamp=datetime.now(),
                total_tests=10,
                vulnerabilities_found=0,
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                findings=[],
                test_duration_ms=100.0,
                test_status="success",
            ),
        ),
    ):
        # Act
        results = await penetration_tester.run_full_test_suite()

        # Assert
        assert len(results) >= 2


def test_count_by_severity(penetration_tester):
    """Test counting vulnerabilities by severity."""
    # Arrange
    findings = [
        VulnerabilityFinding(
            "1",
            AttackType.SQL_INJECTION,
            VulnerabilityLevel.CRITICAL,
            "/test",
            "desc",
            "payload",
            "evidence",
        ),
        VulnerabilityFinding(
            "2",
            AttackType.XSS,
            VulnerabilityLevel.HIGH,
            "/test",
            "desc",
            "payload",
            "evidence",
        ),
        VulnerabilityFinding(
            "3",
            AttackType.XSS,
            VulnerabilityLevel.HIGH,
            "/test",
            "desc",
            "payload",
            "evidence",
        ),
    ]

    # Act
    counts = penetration_tester._count_by_severity(findings)

    # Assert
    assert counts[VulnerabilityLevel.CRITICAL] == 1
    assert counts[VulnerabilityLevel.HIGH] == 2


def test_generate_report_no_results(penetration_tester):
    """Test report generation with no results."""
    # Act
    report = penetration_tester.generate_report()

    # Assert
    assert "No test results available" in report


def test_generate_report_with_vulnerabilities(penetration_tester):
    """Test report generation with vulnerabilities."""
    # Arrange
    finding = VulnerabilityFinding(
        finding_id="SQL-001",
        attack_type=AttackType.SQL_INJECTION,
        vulnerability_level=VulnerabilityLevel.CRITICAL,
        endpoint="/api/test",
        description="SQL injection vulnerability",
        payload_used="' OR '1'='1",
        response_evidence="Authentication bypassed",
        cwe_id="CWE-89",
        remediation="Use parameterized queries",
    )

    result = PenTestResult(
        test_type=AttackType.SQL_INJECTION,
        timestamp=datetime.now(),
        total_tests=10,
        vulnerabilities_found=1,
        critical_count=1,
        high_count=0,
        medium_count=0,
        low_count=0,
        findings=[finding],
        test_duration_ms=100.0,
        test_status="success",
    )

    penetration_tester.test_results = {"sql_injection": result}

    # Act
    report = penetration_tester.generate_report()

    # Assert
    assert "PENETRATION TEST REPORT" in report
    assert "SQL injection vulnerability" in report
    assert "Use parameterized queries" in report  # Check remediation instead
