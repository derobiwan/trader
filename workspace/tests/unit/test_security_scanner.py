"""
Unit tests for Security Scanner.

Tests all major functionality:
- Dependency vulnerability scanning
- Code security scanning
- Secret detection
- Best practices validation
- Report generation
- Error handling

Target: 80%+ code coverage
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, patch
from datetime import datetime
from workspace.shared.security.security_scanner import (
    SecurityScanner,
    ScanConfig,
    SecurityIssue,
    ScanResult,
    SeverityLevel,
)


@pytest.fixture
def scan_config(tmp_path):
    """Create scan configuration with temp directory."""
    return ScanConfig(
        project_root=str(tmp_path),
        source_dirs=["workspace"],
        parallel_scans=False,  # Sequential for easier testing
    )


@pytest.fixture
def security_scanner(scan_config):
    """Create SecurityScanner instance."""
    return SecurityScanner(scan_config)


@pytest.mark.asyncio
async def test_scan_dependencies_with_safety(security_scanner):
    """Test dependency scanning with safety tool."""
    # Arrange
    mock_vulnerabilities = [
        {
            "vulnerability_id": "VULN-001",
            "package_name": "requests",
            "advisory": "Security vulnerability in requests",
            "severity": "high",
            "cvss_score": 7.5,
            "safe_version": "2.31.0",
            "references": ["https://example.com/vuln"],
        }
    ]

    with patch("asyncio.create_subprocess_exec") as mock_exec:
        # Mock safety version check
        mock_version = AsyncMock()
        mock_version.communicate = AsyncMock(return_value=(b"", b""))
        mock_version.returncode = 0

        # Mock safety check
        mock_check = AsyncMock()
        mock_check.communicate = AsyncMock(
            return_value=(json.dumps(mock_vulnerabilities).encode(), b"")
        )
        mock_check.returncode = 0

        mock_exec.side_effect = [mock_version, mock_check]

        # Act
        result = await security_scanner.scan_dependencies()

        # Assert
        assert isinstance(result, ScanResult)
        assert result.scan_type == "dependency_vulnerabilities"
        assert result.total_issues == 1
        assert result.high_count == 1


@pytest.mark.asyncio
async def test_scan_dependencies_safety_not_installed(security_scanner):
    """Test dependency scanning when safety is not installed."""
    # Arrange
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_version = AsyncMock()
        mock_version.communicate = AsyncMock(return_value=(b"", b""))
        mock_version.returncode = 1  # Not installed

        mock_exec.return_value = mock_version

        # Act
        result = await security_scanner.scan_dependencies()

        # Assert
        assert result.total_issues == 0


@pytest.mark.asyncio
async def test_scan_dependencies_no_vulnerabilities(security_scanner):
    """Test dependency scanning with no vulnerabilities found."""
    # Arrange
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_version = AsyncMock()
        mock_version.communicate = AsyncMock(return_value=(b"", b""))
        mock_version.returncode = 0

        mock_check = AsyncMock()
        mock_check.communicate = AsyncMock(
            return_value=(
                b"[]",  # Empty array - no vulnerabilities
                b"",
            )
        )
        mock_check.returncode = 0

        mock_exec.side_effect = [mock_version, mock_check]

        # Act
        result = await security_scanner.scan_dependencies()

        # Assert
        assert result.total_issues == 0


@pytest.mark.asyncio
async def test_scan_dependencies_timeout(security_scanner):
    """Test dependency scanning with timeout."""
    # Arrange
    security_scanner.config.timeout_seconds = 0.1

    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_version = AsyncMock()
        mock_version.communicate = AsyncMock(return_value=(b"", b""))
        mock_version.returncode = 0

        mock_check = AsyncMock()
        mock_check.communicate = AsyncMock(side_effect=asyncio.TimeoutError())

        mock_exec.side_effect = [mock_version, mock_check]

        # Act
        result = await security_scanner.scan_dependencies()

        # Assert
        assert result.total_issues == 0


@pytest.mark.asyncio
async def test_scan_code_with_bandit(security_scanner):
    """Test code scanning with bandit."""
    # Arrange
    mock_results = {
        "results": [
            {
                "test_id": "B105",
                "test_name": "hardcoded_password_string",
                "issue_text": "Possible hardcoded password",
                "issue_severity": "HIGH",
                "filename": "/path/to/file.py",
                "line_number": 42,
                "cwe": {"id": "CWE-259"},
                "more_info": "https://bandit.readthedocs.io/en/latest/plugins/b105_hardcoded_password_string.html",
            }
        ]
    }

    with patch("asyncio.create_subprocess_exec") as mock_exec:
        # Mock bandit version check
        mock_version = AsyncMock()
        mock_version.communicate = AsyncMock(return_value=(b"", b""))
        mock_version.returncode = 0

        # Mock bandit scan
        mock_scan = AsyncMock()
        mock_scan.communicate = AsyncMock(
            return_value=(json.dumps(mock_results).encode(), b"")
        )
        mock_scan.returncode = 0

        mock_exec.side_effect = [mock_version, mock_scan]

        # Act
        result = await security_scanner.scan_code()

        # Assert
        assert isinstance(result, ScanResult)
        assert result.scan_type == "code_security"
        assert result.total_issues == 1
        assert result.high_count == 1


@pytest.mark.asyncio
async def test_scan_code_bandit_not_installed(security_scanner):
    """Test code scanning when bandit is not installed."""
    # Arrange
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_version = AsyncMock()
        mock_version.communicate = AsyncMock(return_value=(b"", b""))
        mock_version.returncode = 1  # Not installed

        mock_exec.return_value = mock_version

        # Act
        result = await security_scanner.scan_code()

        # Assert
        assert result.scan_status == "skipped"
        assert result.error_message == "bandit not installed"


@pytest.mark.asyncio
async def test_scan_code_invalid_json(security_scanner):
    """Test code scanning with invalid JSON output."""
    # Arrange
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_version = AsyncMock()
        mock_version.communicate = AsyncMock(return_value=(b"", b""))
        mock_version.returncode = 0

        mock_scan = AsyncMock()
        mock_scan.communicate = AsyncMock(return_value=(b"invalid json", b""))
        mock_scan.returncode = 0

        mock_exec.side_effect = [mock_version, mock_scan]

        # Act
        result = await security_scanner.scan_code()

        # Assert
        assert result.scan_status == "partial"


@pytest.mark.asyncio
async def test_detect_secrets(security_scanner, tmp_path):
    """Test secret detection."""
    # Arrange
    test_file = tmp_path / "workspace" / "test.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text(
        """
api_key = "sk_live_1234567890abcdef"
password = "supersecretpassword"
# This is a comment with api_key = "fake"
"""
    )

    # Act
    result = await security_scanner.detect_secrets()

    # Assert
    assert isinstance(result, ScanResult)
    assert result.scan_type == "secret_detection"
    # Should detect api_key and password (excluding commented line)
    assert result.total_issues >= 1


@pytest.mark.asyncio
async def test_detect_secrets_false_positives(security_scanner, tmp_path):
    """Test secret detection filters false positives."""
    # Arrange
    test_file = tmp_path / "workspace" / "test.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text(
        """
# False positives - should be ignored
api_key = "example"
password = "password123"
token = "***REDACTED***"
secret = "your_secret_here"
"""
    )

    # Act
    result = await security_scanner.detect_secrets()

    # Assert
    # False positives should be filtered
    assert result.total_issues == 0


@pytest.mark.asyncio
async def test_detect_secrets_in_comments(security_scanner, tmp_path):
    """Test that secrets in comments are ignored."""
    # Arrange
    test_file = tmp_path / "workspace" / "test.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text(
        """
# api_key = "sk_live_1234567890"
# This comment should be ignored
"""
    )

    # Act
    result = await security_scanner.detect_secrets()

    # Assert
    assert result.total_issues == 0


def test_is_false_positive(security_scanner):
    """Test false positive detection."""
    # True false positives
    assert security_scanner._is_false_positive("example_api_key")
    assert security_scanner._is_false_positive("placeholder_value")
    assert security_scanner._is_false_positive("*****")
    assert security_scanner._is_false_positive("password123")

    # Real secrets
    assert not security_scanner._is_false_positive("sk_live_a1b2c3d4")
    assert not security_scanner._is_false_positive("ghp_1234567890abcdef")


@pytest.mark.asyncio
async def test_validate_best_practices(security_scanner, tmp_path):
    """Test best practices validation."""
    # Arrange
    test_file = tmp_path / "workspace" / "test.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text(
        """
import requests

# Disabled SSL verification - bad practice
response = requests.get('https://api.example.com', verify=False)
"""
    )

    # Act
    result = await security_scanner.validate_best_practices()

    # Assert
    assert isinstance(result, ScanResult)
    assert result.scan_type == "best_practices"
    assert result.high_count >= 1  # Should detect SSL verification issue


@pytest.mark.asyncio
async def test_check_ssl_verification(security_scanner, tmp_path):
    """Test SSL verification checking."""
    # Arrange
    test_file = tmp_path / "workspace" / "test.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text(
        """
import ssl
import requests

# Bad practices
ctx = ssl._create_unverified_context()
response = requests.get('url', verify=False)
ssl.CERT_NONE
"""
    )

    # Act
    issues = await security_scanner._check_ssl_verification()

    # Assert
    assert len(issues) >= 2  # Should find multiple SSL issues


@pytest.mark.asyncio
async def test_check_sql_injection(security_scanner, tmp_path):
    """Test SQL injection checking."""
    # Arrange
    test_file = tmp_path / "workspace" / "test.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text(
        """
# Bad practice - SQL injection vulnerable
cursor.execute("SELECT * FROM users WHERE id = " + user_id)
cursor.execute(f"SELECT * FROM users WHERE name = '{name}'")
"""
    )

    # Act
    issues = await security_scanner._check_sql_injection()

    # Assert
    assert len(issues) >= 1  # Should find SQL injection issues


@pytest.mark.asyncio
async def test_check_hardcoded_credentials(security_scanner, tmp_path):
    """Test hardcoded credentials checking."""
    # Arrange
    test_file = tmp_path / "workspace" / "app.py"  # Not a test file
    test_file.parent.mkdir(parents=True)
    test_file.write_text(
        """
# Bad practices
password = "mysecretpassword"
username = "admin"
default_password = "changeme"
"""
    )

    # Act
    issues = await security_scanner._check_hardcoded_credentials()

    # Assert
    assert len(issues) >= 1  # Should find hardcoded credentials


@pytest.mark.asyncio
async def test_check_hardcoded_credentials_skip_tests(security_scanner, tmp_path):
    """Test that hardcoded credentials in test files are skipped."""
    # Arrange
    test_file = tmp_path / "workspace" / "test_auth.py"  # Test file
    test_file.parent.mkdir(parents=True)
    test_file.write_text(
        """
# This is a test file - should be ignored
password = "test_password"
"""
    )

    # Act
    issues = await security_scanner._check_hardcoded_credentials()

    # Assert
    # Should not find issues in test files
    assert len(issues) == 0


@pytest.mark.asyncio
async def test_check_debug_mode(security_scanner, tmp_path):
    """Test debug mode checking."""
    # Arrange
    test_file = tmp_path / "workspace" / "app.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text(
        """
# Bad practice
DEBUG = True
app.run(debug=True)
"""
    )

    # Act
    issues = await security_scanner._check_debug_mode()

    # Assert
    assert len(issues) >= 1  # Should find debug mode enabled


@pytest.mark.asyncio
async def test_run_full_scan_parallel(security_scanner):
    """Test running full scan in parallel."""
    # Arrange
    security_scanner.config.parallel_scans = True

    with (
        patch.object(
            security_scanner,
            "scan_dependencies",
            return_value=ScanResult(
                scan_type="dependencies",
                timestamp=datetime.now(),
                total_issues=0,
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                info_count=0,
                issues=[],
                scan_duration_ms=100.0,
                scan_status="success",
            ),
        ),
        patch.object(
            security_scanner,
            "scan_code",
            return_value=ScanResult(
                scan_type="code_security",
                timestamp=datetime.now(),
                total_issues=0,
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                info_count=0,
                issues=[],
                scan_duration_ms=100.0,
                scan_status="success",
            ),
        ),
        patch.object(
            security_scanner,
            "detect_secrets",
            return_value=ScanResult(
                scan_type="secrets",
                timestamp=datetime.now(),
                total_issues=0,
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                info_count=0,
                issues=[],
                scan_duration_ms=100.0,
                scan_status="success",
            ),
        ),
        patch.object(
            security_scanner,
            "validate_best_practices",
            return_value=ScanResult(
                scan_type="best_practices",
                timestamp=datetime.now(),
                total_issues=0,
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                info_count=0,
                issues=[],
                scan_duration_ms=100.0,
                scan_status="success",
            ),
        ),
    ):
        # Act
        results = await security_scanner.run_full_scan()

        # Assert
        assert len(results) == 4
        assert "dependencies" in results
        assert "code_security" in results
        assert "secrets" in results
        assert "best_practices" in results


@pytest.mark.asyncio
async def test_run_full_scan_sequential(security_scanner):
    """Test running full scan sequentially."""
    # Arrange
    security_scanner.config.parallel_scans = False

    with (
        patch.object(
            security_scanner,
            "scan_dependencies",
            return_value=ScanResult(
                scan_type="dependencies",
                timestamp=datetime.now(),
                total_issues=0,
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                info_count=0,
                issues=[],
                scan_duration_ms=100.0,
                scan_status="success",
            ),
        ),
        patch.object(
            security_scanner,
            "scan_code",
            return_value=ScanResult(
                scan_type="code_security",
                timestamp=datetime.now(),
                total_issues=0,
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                info_count=0,
                issues=[],
                scan_duration_ms=100.0,
                scan_status="success",
            ),
        ),
        patch.object(
            security_scanner,
            "detect_secrets",
            return_value=ScanResult(
                scan_type="secrets",
                timestamp=datetime.now(),
                total_issues=0,
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                info_count=0,
                issues=[],
                scan_duration_ms=100.0,
                scan_status="success",
            ),
        ),
        patch.object(
            security_scanner,
            "validate_best_practices",
            return_value=ScanResult(
                scan_type="best_practices",
                timestamp=datetime.now(),
                total_issues=0,
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                info_count=0,
                issues=[],
                scan_duration_ms=100.0,
                scan_status="success",
            ),
        ),
    ):
        # Act
        results = await security_scanner.run_full_scan()

        # Assert
        assert len(results) == 4


def test_generate_report_no_results(security_scanner):
    """Test report generation with no results."""
    # Act
    report = security_scanner.generate_report()

    # Assert
    assert "No scan results available" in report


def test_generate_report_with_results(security_scanner):
    """Test report generation with results."""
    # Arrange
    issue = SecurityIssue(
        issue_id="TEST-001",
        title="Test vulnerability",
        description="Test description",
        severity=SeverityLevel.HIGH,
        category="test",
        file_path="/test/file.py",
        line_number=42,
    )

    result = ScanResult(
        scan_type="test_scan",
        timestamp=datetime.now(),
        total_issues=1,
        critical_count=0,
        high_count=1,
        medium_count=0,
        low_count=0,
        info_count=0,
        issues=[issue],
        scan_duration_ms=100.0,
        scan_status="success",
    )

    security_scanner.scan_results = {"test_scan": result}

    # Act
    report = security_scanner.generate_report()

    # Assert
    assert "SECURITY SCAN REPORT" in report
    assert "EXECUTIVE SUMMARY" in report
    assert "TEST_SCAN" in report
    assert "Test vulnerability" in report
    assert "RECOMMENDATIONS" in report


def test_generate_report_with_no_critical_issues(security_scanner):
    """Test report generation with no critical/high issues."""
    # Arrange
    issue = SecurityIssue(
        issue_id="TEST-001",
        title="Low severity issue",
        description="Test description",
        severity=SeverityLevel.LOW,
        category="test",
    )

    result = ScanResult(
        scan_type="test_scan",
        timestamp=datetime.now(),
        total_issues=1,
        critical_count=0,
        high_count=0,
        medium_count=0,
        low_count=1,
        info_count=0,
        issues=[issue],
        scan_duration_ms=100.0,
        scan_status="success",
    )

    security_scanner.scan_results = {"test_scan": result}

    # Act
    report = security_scanner.generate_report()

    # Assert
    assert "No critical or high-severity issues found" in report


def test_count_by_severity(security_scanner):
    """Test counting issues by severity."""
    # Arrange
    issues = [
        SecurityIssue("ID1", "Title1", "Desc1", SeverityLevel.CRITICAL, "cat1"),
        SecurityIssue("ID2", "Title2", "Desc2", SeverityLevel.HIGH, "cat2"),
        SecurityIssue("ID3", "Title3", "Desc3", SeverityLevel.HIGH, "cat3"),
        SecurityIssue("ID4", "Title4", "Desc4", SeverityLevel.MEDIUM, "cat4"),
    ]

    # Act
    counts = security_scanner._count_by_severity(issues)

    # Assert
    assert counts[SeverityLevel.CRITICAL] == 1
    assert counts[SeverityLevel.HIGH] == 2
    assert counts[SeverityLevel.MEDIUM] == 1
    assert counts[SeverityLevel.LOW] == 0


def test_map_severity(security_scanner):
    """Test severity mapping."""
    assert security_scanner._map_severity("critical") == SeverityLevel.CRITICAL
    assert security_scanner._map_severity("high") == SeverityLevel.HIGH
    assert security_scanner._map_severity("medium") == SeverityLevel.MEDIUM
    assert security_scanner._map_severity("low") == SeverityLevel.LOW
    assert security_scanner._map_severity("unknown") == SeverityLevel.MEDIUM  # Default


def test_map_bandit_severity(security_scanner):
    """Test bandit severity mapping."""
    assert security_scanner._map_bandit_severity("HIGH") == SeverityLevel.HIGH
    assert security_scanner._map_bandit_severity("MEDIUM") == SeverityLevel.MEDIUM
    assert security_scanner._map_bandit_severity("LOW") == SeverityLevel.LOW
    assert (
        security_scanner._map_bandit_severity("UNKNOWN") == SeverityLevel.LOW
    )  # Default


def test_meets_severity_threshold(security_scanner):
    """Test severity threshold checking."""
    # Arrange
    security_scanner.config.bandit_severity = "medium"

    # Act & Assert
    assert security_scanner._meets_severity_threshold(SeverityLevel.CRITICAL)
    assert security_scanner._meets_severity_threshold(SeverityLevel.HIGH)
    assert security_scanner._meets_severity_threshold(SeverityLevel.MEDIUM)
    assert not security_scanner._meets_severity_threshold(SeverityLevel.LOW)
    assert not security_scanner._meets_severity_threshold(SeverityLevel.INFO)


def test_scan_config_defaults():
    """Test ScanConfig default values."""
    config = ScanConfig()

    assert config.project_root == "."
    assert "workspace" in config.source_dirs
    assert "__pycache__" in config.exclude_dirs
    assert config.timeout_seconds == 300
    assert config.parallel_scans is True


def test_severity_level_enum():
    """Test SeverityLevel enum values."""
    assert SeverityLevel.CRITICAL.value == "critical"
    assert SeverityLevel.HIGH.value == "high"
    assert SeverityLevel.MEDIUM.value == "medium"
    assert SeverityLevel.LOW.value == "low"
    assert SeverityLevel.INFO.value == "info"
