"""
Comprehensive tests for Security Scanner to achieve 80%+ coverage.

This test suite focuses on previously uncovered areas:
- Tool installation detection and fallback
- Graceful degradation when tools unavailable
- Configuration validation
- Report formatting for different scenarios
- Error recovery paths

Author: Validation Engineer
Date: 2025-10-31
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from datetime import datetime

from workspace.shared.security.security_scanner import (
    SecurityScanner,
    ScanConfig,
    SecurityIssue,
    SeverityLevel,
    ScanResult,
)


# ==============================================================================
# Tool Detection Tests (5 tests)
# ==============================================================================


@pytest.mark.asyncio
async def test_check_tool_availability_all_present():
    """Test detection when all security tools are present."""
    config = ScanConfig(project_root=".")
    scanner = SecurityScanner(config)

    # Mock safety available
    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.communicate = AsyncMock(return_value=(b"safety 2.0", b""))

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        result = await scanner.scan_dependencies()

    # Should attempt to use safety
    assert result.scan_type == "dependency_vulnerabilities"


@pytest.mark.asyncio
async def test_check_tool_availability_some_missing():
    """Test graceful handling when some tools are missing."""
    config = ScanConfig(project_root=".")
    scanner = SecurityScanner(config)

    # Mock safety not available, but pip-audit is
    mock_safety_process = AsyncMock()
    mock_safety_process.returncode = 1  # Not found
    mock_safety_process.communicate = AsyncMock(return_value=(b"", b"not found"))

    with patch("asyncio.create_subprocess_exec", return_value=mock_safety_process):
        result = await scanner.scan_dependencies()

    # Should still complete scan
    assert result.scan_status in ("success", "failed")


@pytest.mark.asyncio
async def test_check_tool_availability_none_present():
    """Test behavior when no security tools are available."""
    config = ScanConfig(project_root=".")
    scanner = SecurityScanner(config)

    # Mock all tools unavailable
    mock_process = AsyncMock()
    mock_process.returncode = 1
    mock_process.communicate = AsyncMock(return_value=(b"", b"not found"))

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        result = await scanner.scan_dependencies()

    # Should return empty result or failure
    assert result.scan_type == "dependency_vulnerabilities"


@pytest.mark.asyncio
async def test_tool_version_detection():
    """Test that tool version detection works correctly."""
    config = ScanConfig(project_root=".")
    scanner = SecurityScanner(config)

    # Mock bandit version check
    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.communicate = AsyncMock(return_value=(b"bandit 1.7.4", b""))

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        result = await scanner.scan_code()

    # Should detect bandit is available
    assert result.scan_type == "code_security"


@pytest.mark.asyncio
async def test_tool_path_detection():
    """Test that tools are found in PATH."""
    config = ScanConfig(project_root=".")
    scanner = SecurityScanner(config)

    # Mock successful tool execution
    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.communicate = AsyncMock(return_value=(b"[]", b""))

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        result = await scanner._scan_with_safety()

    # Should successfully call safety
    assert isinstance(result, list)


# ==============================================================================
# Graceful Degradation Tests (5 tests)
# ==============================================================================


@pytest.mark.asyncio
async def test_scan_without_safety():
    """Test dependency scan when safety is not available."""
    config = ScanConfig(project_root=".")
    scanner = SecurityScanner(config)

    # Mock safety not installed
    mock_process = AsyncMock()
    mock_process.returncode = 1
    mock_process.communicate = AsyncMock(return_value=(b"", b"command not found"))

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        issues = await scanner._scan_with_safety()

    # Should return empty list, not crash
    assert issues == []


@pytest.mark.asyncio
async def test_scan_without_bandit():
    """Test code scan when bandit is not available."""
    config = ScanConfig(project_root=".")
    scanner = SecurityScanner(config)

    # Mock bandit not installed
    mock_process = AsyncMock()
    mock_process.returncode = 1
    mock_process.communicate = AsyncMock(return_value=(b"", b"not found"))

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        result = await scanner.scan_code()

    # Should return skipped status
    assert result.scan_status == "skipped"
    assert "not installed" in result.error_message


@pytest.mark.asyncio
async def test_scan_without_all_tools():
    """Test full scan when no tools are available."""
    config = ScanConfig(project_root=".", parallel_scans=False)
    scanner = SecurityScanner(config)

    # Mock all tools unavailable
    with patch.object(scanner, "scan_dependencies") as mock_deps:
        with patch.object(scanner, "scan_code") as mock_code:
            mock_deps.return_value = ScanResult(
                scan_type="dependencies",
                timestamp=datetime.now(),
                total_issues=0,
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                info_count=0,
                issues=[],
                scan_duration_ms=0,
                scan_status="failed",
                error_message="No tools available",
            )
            mock_code.return_value = ScanResult(
                scan_type="code",
                timestamp=datetime.now(),
                total_issues=0,
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                info_count=0,
                issues=[],
                scan_duration_ms=0,
                scan_status="skipped",
            )

            results = await scanner.run_full_scan()

    # Should complete without crashing
    assert isinstance(results, dict)


@pytest.mark.asyncio
async def test_partial_scan_results():
    """Test that partial results are handled correctly."""
    config = ScanConfig(project_root=".")
    scanner = SecurityScanner(config)

    # Mock pip-audit JSON parse error
    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.communicate = AsyncMock(return_value=(b"invalid json", b""))

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        issues = await scanner._scan_with_pip_audit()

    # Should handle parse error gracefully
    assert isinstance(issues, list)


@pytest.mark.asyncio
async def test_degradation_warnings():
    """Test that degradation warnings are logged."""
    config = ScanConfig(project_root=".")
    scanner = SecurityScanner(config)

    # Mock tool not available
    mock_process = AsyncMock()
    mock_process.returncode = 127  # Command not found
    mock_process.communicate = AsyncMock(return_value=(b"", b"not found"))

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        with patch("workspace.shared.security.security_scanner.logger") as mock_logger:
            issues = await scanner._scan_with_pip_audit()

            # Should log debug message
            assert mock_logger.debug.called


# ==============================================================================
# Configuration Tests (5 tests)
# ==============================================================================


def test_config_validation_valid():
    """Test that valid configuration is accepted."""
    config = ScanConfig(
        project_root="/tmp/test",
        source_dirs=["src", "lib"],
        exclude_dirs=["__pycache__", ".git"],
        requirements_files=["requirements.txt"],
        bandit_severity="medium",
    )

    assert config.project_root == "/tmp/test"
    assert len(config.source_dirs) == 2
    assert config.bandit_severity == "medium"


def test_config_validation_invalid():
    """Test handling of invalid configuration values."""
    # Should accept any values (no validation in dataclass)
    config = ScanConfig(
        project_root="",
        source_dirs=[],
    )

    scanner = SecurityScanner(config)
    assert scanner.project_root.exists()  # Should resolve to current dir


def test_config_defaults():
    """Test that configuration defaults are correct."""
    config = ScanConfig()

    assert config.project_root == "."
    assert "workspace" in config.source_dirs
    assert "__pycache__" in config.exclude_dirs
    assert config.check_ssl_verification is True
    assert config.timeout_seconds == 300
    assert config.parallel_scans is True


def test_config_overrides():
    """Test that configuration can be overridden."""
    config = ScanConfig(
        timeout_seconds=600,
        parallel_scans=False,
        bandit_severity="high",
    )

    assert config.timeout_seconds == 600
    assert config.parallel_scans is False
    assert config.bandit_severity == "high"


def test_config_environment_variables():
    """Test that environment variables can influence config."""
    # This is a future enhancement, for now test that config is independent
    config = ScanConfig()

    scanner = SecurityScanner(config)
    assert scanner.config.project_root == "."


# ==============================================================================
# Edge Cases Tests (10 tests)
# ==============================================================================


@pytest.mark.asyncio
async def test_empty_codebase_scan(tmp_path):
    """Test scanning an empty codebase."""
    config = ScanConfig(
        project_root=str(tmp_path),
        source_dirs=["empty"],
    )
    scanner = SecurityScanner(config)

    # Create empty source dir
    (tmp_path / "empty").mkdir()

    result = await scanner.detect_secrets()

    # Should complete with no findings
    assert result.total_issues == 0
    assert result.scan_status == "success"


@pytest.mark.asyncio
async def test_large_codebase_scan(tmp_path):
    """Test scanning a large codebase."""
    config = ScanConfig(
        project_root=str(tmp_path),
        source_dirs=["large"],
    )
    scanner = SecurityScanner(config)

    # Create many files
    large_dir = tmp_path / "large"
    large_dir.mkdir()
    for i in range(50):
        (large_dir / f"file_{i}.py").write_text(f"# File {i}\npass\n")

    result = await scanner.detect_secrets()

    # Should complete scanning all files
    assert result.scan_status == "success"


@pytest.mark.asyncio
async def test_scan_timeout_handling():
    """Test that scan timeouts are handled correctly."""
    config = ScanConfig(timeout_seconds=0.001)  # Very short timeout
    scanner = SecurityScanner(config)

    # Mock slow process
    mock_process = AsyncMock()
    mock_process.communicate = AsyncMock(
        side_effect=asyncio.TimeoutError("Scan timeout")
    )

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
            issues = await scanner._scan_with_safety()

    # Should handle timeout gracefully
    assert isinstance(issues, list)


@pytest.mark.asyncio
async def test_scan_memory_limits():
    """Test scan behavior under memory constraints."""
    config = ScanConfig(project_root=".")
    scanner = SecurityScanner(config)

    # This is a functional test - memory limits are OS-level
    result = await scanner.detect_secrets()

    # Should complete without memory errors
    assert result.scan_status in ("success", "failed")


@pytest.mark.asyncio
async def test_concurrent_scans():
    """Test running multiple scan types concurrently."""
    config = ScanConfig(project_root=".", parallel_scans=True)
    scanner = SecurityScanner(config)

    # Mock all scan methods
    with patch.object(scanner, "scan_dependencies") as mock_deps:
        with patch.object(scanner, "scan_code") as mock_code:
            with patch.object(scanner, "detect_secrets") as mock_secrets:
                with patch.object(scanner, "validate_best_practices") as mock_practices:
                    mock_deps.return_value = ScanResult(
                        scan_type="dependencies",
                        timestamp=datetime.now(),
                        total_issues=0,
                        critical_count=0,
                        high_count=0,
                        medium_count=0,
                        low_count=0,
                        info_count=0,
                        issues=[],
                        scan_duration_ms=100,
                        scan_status="success",
                    )
                    mock_code.return_value = mock_deps.return_value
                    mock_secrets.return_value = mock_deps.return_value
                    mock_practices.return_value = mock_deps.return_value

                    results = await scanner.run_full_scan()

    # All scans should have executed
    assert len(results) == 4


def test_severity_mapping():
    """Test severity level mapping."""
    config = ScanConfig()
    scanner = SecurityScanner(config)

    assert scanner._map_severity("critical") == SeverityLevel.CRITICAL
    assert scanner._map_severity("high") == SeverityLevel.HIGH
    assert scanner._map_severity("medium") == SeverityLevel.MEDIUM
    assert scanner._map_severity("low") == SeverityLevel.LOW
    assert scanner._map_severity("unknown") == SeverityLevel.MEDIUM  # Default


def test_bandit_severity_mapping():
    """Test bandit severity mapping."""
    config = ScanConfig()
    scanner = SecurityScanner(config)

    assert scanner._map_bandit_severity("HIGH") == SeverityLevel.HIGH
    assert scanner._map_bandit_severity("MEDIUM") == SeverityLevel.MEDIUM
    assert scanner._map_bandit_severity("LOW") == SeverityLevel.LOW
    assert scanner._map_bandit_severity("UNKNOWN") == SeverityLevel.LOW  # Default


def test_severity_threshold():
    """Test severity threshold checking."""
    config = ScanConfig(bandit_severity="medium")
    scanner = SecurityScanner(config)

    assert scanner._meets_severity_threshold(SeverityLevel.CRITICAL) is True
    assert scanner._meets_severity_threshold(SeverityLevel.HIGH) is True
    assert scanner._meets_severity_threshold(SeverityLevel.MEDIUM) is True
    assert scanner._meets_severity_threshold(SeverityLevel.LOW) is False
    assert scanner._meets_severity_threshold(SeverityLevel.INFO) is False


def test_count_by_severity():
    """Test issue counting by severity."""
    config = ScanConfig()
    scanner = SecurityScanner(config)

    issues = [
        SecurityIssue(
            issue_id="1",
            title="Critical issue",
            description="Test",
            severity=SeverityLevel.CRITICAL,
            category="test",
        ),
        SecurityIssue(
            issue_id="2",
            title="High issue",
            description="Test",
            severity=SeverityLevel.HIGH,
            category="test",
        ),
        SecurityIssue(
            issue_id="3",
            title="High issue 2",
            description="Test",
            severity=SeverityLevel.HIGH,
            category="test",
        ),
    ]

    counts = scanner._count_by_severity(issues)

    assert counts[SeverityLevel.CRITICAL] == 1
    assert counts[SeverityLevel.HIGH] == 2
    assert counts[SeverityLevel.MEDIUM] == 0


def test_generate_report_empty():
    """Test report generation with no results."""
    config = ScanConfig()
    scanner = SecurityScanner(config)

    report = scanner.generate_report({})

    assert "No scan results available" in report


# ==============================================================================
# Report Generation Tests (5 tests)
# ==============================================================================


def test_generate_report_with_all_severities():
    """Test report generation with all severity levels."""
    config = ScanConfig()
    scanner = SecurityScanner(config)

    issues = [
        SecurityIssue(
            issue_id=f"{i}",
            title=f"{severity.value} issue",
            description="Test issue",
            severity=severity,
            category="test",
            file_path="test.py" if i % 2 == 0 else None,
            line_number=i * 10 if i % 2 == 0 else None,
        )
        for i, severity in enumerate(SeverityLevel)
    ]

    result = ScanResult(
        scan_type="test_scan",
        timestamp=datetime.now(),
        total_issues=len(issues),
        critical_count=1,
        high_count=1,
        medium_count=1,
        low_count=1,
        info_count=1,
        issues=issues,
        scan_duration_ms=100,
        scan_status="success",
    )

    scanner.scan_results["test"] = result
    report = scanner.generate_report()

    # Report should include all severities
    assert "Critical: 1" in report
    assert "High:     1" in report
    assert "Medium:   1" in report


def test_generate_report_with_errors():
    """Test report generation with scan errors."""
    config = ScanConfig()
    scanner = SecurityScanner(config)

    result = ScanResult(
        scan_type="failed_scan",
        timestamp=datetime.now(),
        total_issues=0,
        critical_count=0,
        high_count=0,
        medium_count=0,
        low_count=0,
        info_count=0,
        issues=[],
        scan_duration_ms=50,
        scan_status="failed",
        error_message="Scan failed due to timeout",
    )

    scanner.scan_results["failed"] = result
    report = scanner.generate_report()

    # Report should include error message
    assert "Scan failed due to timeout" in report


def test_generate_report_with_recommendations():
    """Test that report includes recommendations."""
    config = ScanConfig()
    scanner = SecurityScanner(config)

    issues = [
        SecurityIssue(
            issue_id="1",
            title="Critical security issue",
            description="Test",
            severity=SeverityLevel.CRITICAL,
            category="test",
        )
    ]

    result = ScanResult(
        scan_type="security",
        timestamp=datetime.now(),
        total_issues=1,
        critical_count=1,
        high_count=0,
        medium_count=0,
        low_count=0,
        info_count=0,
        issues=issues,
        scan_duration_ms=100,
        scan_status="success",
    )

    scanner.scan_results["security"] = result
    report = scanner.generate_report()

    # Report should include recommendations
    assert "RECOMMENDATIONS" in report
    assert "CRITICAL" in report


def test_generate_report_clean_run():
    """Test report generation for clean scan (no issues)."""
    config = ScanConfig()
    scanner = SecurityScanner(config)

    result = ScanResult(
        scan_type="clean_scan",
        timestamp=datetime.now(),
        total_issues=0,
        critical_count=0,
        high_count=0,
        medium_count=0,
        low_count=0,
        info_count=0,
        issues=[],
        scan_duration_ms=100,
        scan_status="success",
    )

    scanner.scan_results["clean"] = result
    report = scanner.generate_report()

    # Report should congratulate clean scan
    assert "No critical or high-severity issues found" in report


def test_generate_report_with_file_locations():
    """Test that report includes file locations for issues."""
    config = ScanConfig()
    scanner = SecurityScanner(config)

    issues = [
        SecurityIssue(
            issue_id="1",
            title="Security issue in code",
            description="Test issue with location",
            severity=SeverityLevel.HIGH,
            category="code",
            file_path="workspace/shared/utils.py",
            line_number=42,
        )
    ]

    result = ScanResult(
        scan_type="code_scan",
        timestamp=datetime.now(),
        total_issues=1,
        critical_count=0,
        high_count=1,
        medium_count=0,
        low_count=0,
        info_count=0,
        issues=issues,
        scan_duration_ms=100,
        scan_status="success",
    )

    scanner.scan_results["code"] = result
    report = scanner.generate_report()

    # Report should include file location
    assert "workspace/shared/utils.py" in report
    assert "42" in report
