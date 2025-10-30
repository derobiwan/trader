"""
Security Scanner

Comprehensive security scanning and vulnerability detection for the trading system.

Features:
- Dependency vulnerability scanning (safety, bandit)
- Secret detection in code and configuration files
- Code security analysis
- Docker image vulnerability scanning
- Configuration security validation
- Security reporting and recommendations

Author: Performance Optimization Team
Date: 2025-10-29
Sprint: 3, Stream C, Task 047
"""

import json
import logging
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class Severity(Enum):
    """Security issue severity levels"""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass
class SecurityIssue:
    """Information about a detected security issue"""

    category: str  # "dependency", "secret", "code", "docker", "config"
    severity: Severity
    title: str
    description: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    cve_id: Optional[str] = None
    recommendation: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ScanResult:
    """Result of a security scan"""

    scan_type: str
    issues_found: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    time_taken_ms: float
    issues: List[SecurityIssue]
    success: bool
    error_message: Optional[str] = None


class SecurityScanner:
    """
    Comprehensive security scanning system.

    Performs multiple types of security scans:
    - Dependency vulnerability scanning
    - Secret detection
    - Code security analysis
    - Docker image scanning
    - Configuration validation
    """

    # Common secret patterns
    SECRET_PATTERNS = {
        "api_key": r"(?i)(api[_-]?key|apikey)[\s]*[=:]\s*['\"]?([a-zA-Z0-9_\-]{20,})['\"]?",
        "aws_key": r"(?i)(aws[_-]?access[_-]?key[_-]?id)[\s]*[=:]\s*['\"]?([A-Z0-9]{20})['\"]?",
        "aws_secret": r"(?i)(aws[_-]?secret[_-]?access[_-]?key)[\s]*[=:]\s*['\"]?([A-Za-z0-9/+=]{40})['\"]?",
        "private_key": r"-----BEGIN (RSA |EC )?PRIVATE KEY-----",
        "password": r"(?i)(password|passwd|pwd)[\s]*[=:]\s*['\"]?([^'\"\s]{8,})['\"]?",
        "token": r"(?i)(token|bearer)[\s]*[=:]\s*['\"]?([a-zA-Z0-9_\-\.]{20,})['\"]?",
        "database_url": r"(?i)(database[_-]?url|db[_-]?url)[\s]*[=:]\s*['\"]?(postgres|mysql|mongodb)://[^\s'\"]+['\"]?",
    }

    # Files to skip during secret scanning
    SKIP_PATTERNS = {
        ".git/",
        ".venv/",
        "venv/",
        "node_modules/",
        "__pycache__/",
        ".pytest_cache/",
        "*.pyc",
        "*.log",
        ".DS_Store",
    }

    def __init__(self, project_root: Path):
        """
        Initialize security scanner.

        Args:
            project_root: Root directory of the project to scan
        """
        self.project_root = Path(project_root)
        logger.info(f"SecurityScanner initialized for {self.project_root}")

    # ========================================================================
    # Main Scanning Functions
    # ========================================================================

    async def scan_all(self) -> Dict[str, ScanResult]:
        """
        Run all security scans.

        Returns:
            Dictionary mapping scan type to scan result
        """
        logger.info("🔒 Starting comprehensive security scan...")

        results = {}

        # Run all scans
        results["dependencies"] = await self.scan_dependencies()
        results["secrets"] = await self.scan_secrets()
        results["code"] = await self.scan_code_security()
        results["docker"] = await self.scan_docker_images()
        results["config"] = await self.scan_configurations()

        # Summary
        total_issues = sum(r.issues_found for r in results.values())
        critical_issues = sum(r.critical_count for r in results.values())
        high_issues = sum(r.high_count for r in results.values())

        logger.info(
            f"✓ Security scan complete: {total_issues} issues found "
            f"({critical_issues} critical, {high_issues} high)"
        )

        if critical_issues > 0:
            logger.critical(f"🚨 {critical_issues} CRITICAL security issues found!")

        return results

    # ========================================================================
    # Dependency Vulnerability Scanning
    # ========================================================================

    async def scan_dependencies(self) -> ScanResult:
        """
        Scan dependencies for known vulnerabilities.

        Uses:
        - safety: Check Python dependencies against vulnerability database
        - pip-audit: Additional vulnerability checking

        Returns:
            Scan result for dependencies
        """
        logger.info("Scanning dependencies for vulnerabilities...")
        start_time = datetime.utcnow()
        issues: List[SecurityIssue] = []

        try:
            # Check if pyproject.toml exists
            pyproject_path = self.project_root / "pyproject.toml"
            if not pyproject_path.exists():
                logger.warning("No pyproject.toml found, skipping dependency scan")
                return self._create_scan_result("dependencies", issues, 0)

            # Try using safety (if installed)
            safety_issues = await self._scan_with_safety()
            issues.extend(safety_issues)

            # Try using pip-audit (if installed)
            pip_audit_issues = await self._scan_with_pip_audit()
            issues.extend(pip_audit_issues)

            time_taken = (datetime.utcnow() - start_time).total_seconds() * 1000

            logger.info(
                f"✓ Dependency scan complete: {len(issues)} vulnerabilities found "
                f"in {time_taken:.2f}ms"
            )

            return self._create_scan_result("dependencies", issues, time_taken)

        except Exception as e:
            time_taken = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(f"✗ Dependency scan failed: {e}")

            return ScanResult(
                scan_type="dependencies",
                issues_found=0,
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                time_taken_ms=time_taken,
                issues=[],
                success=False,
                error_message=str(e),
            )

    async def _scan_with_safety(self) -> List[SecurityIssue]:
        """Scan with safety tool"""
        issues = []

        try:
            # Run safety check
            result = subprocess.run(
                ["safety", "check", "--json", "--output", "json"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0 and result.stdout:
                # Parse safety JSON output
                try:
                    safety_data = json.loads(result.stdout)
                    for vuln in safety_data.get("vulnerabilities", []):
                        issues.append(
                            SecurityIssue(
                                category="dependency",
                                severity=self._map_cvss_to_severity(
                                    vuln.get("cvss_score", 0)
                                ),
                                title=f"Vulnerable dependency: {vuln.get('package_name')}",
                                description=vuln.get("advisory", ""),
                                cve_id=vuln.get("vulnerability_id"),
                                recommendation=f"Update {vuln.get('package_name')} to version {vuln.get('fixed_version', 'latest')}",
                            )
                        )
                except json.JSONDecodeError:
                    logger.warning("Could not parse safety output")

        except FileNotFoundError:
            logger.debug("safety tool not found, skipping")
        except subprocess.TimeoutExpired:
            logger.warning("safety scan timed out")
        except Exception as e:
            logger.error(f"Error running safety: {e}")

        return issues

    async def _scan_with_pip_audit(self) -> List[SecurityIssue]:
        """Scan with pip-audit tool"""
        issues = []

        try:
            # Run pip-audit
            result = subprocess.run(
                ["pip-audit", "--format", "json"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.stdout:
                # Parse pip-audit JSON output
                try:
                    audit_data = json.loads(result.stdout)
                    for vuln in audit_data.get("vulnerabilities", []):
                        issues.append(
                            SecurityIssue(
                                category="dependency",
                                severity=Severity.HIGH,
                                title=f"Vulnerable package: {vuln.get('name')}",
                                description=vuln.get("description", ""),
                                cve_id=vuln.get("id"),
                                recommendation=f"Update to version {vuln.get('fix_versions', ['latest'])[0]}",
                            )
                        )
                except json.JSONDecodeError:
                    logger.warning("Could not parse pip-audit output")

        except FileNotFoundError:
            logger.debug("pip-audit tool not found, skipping")
        except subprocess.TimeoutExpired:
            logger.warning("pip-audit scan timed out")
        except Exception as e:
            logger.error(f"Error running pip-audit: {e}")

        return issues

    def _map_cvss_to_severity(self, cvss_score: float) -> Severity:
        """Map CVSS score to severity level"""
        if cvss_score >= 9.0:
            return Severity.CRITICAL
        elif cvss_score >= 7.0:
            return Severity.HIGH
        elif cvss_score >= 4.0:
            return Severity.MEDIUM
        else:
            return Severity.LOW

    # ========================================================================
    # Secret Detection
    # ========================================================================

    async def scan_secrets(self) -> ScanResult:
        """
        Scan for hardcoded secrets in code and configuration files.

        Returns:
            Scan result for secrets
        """
        logger.info("Scanning for hardcoded secrets...")
        start_time = datetime.utcnow()
        issues = []

        try:
            # Scan Python files
            python_files = self.project_root.rglob("*.py")
            for file_path in python_files:
                if self._should_skip_file(file_path):
                    continue

                file_issues = await self._scan_file_for_secrets(file_path)
                issues.extend(file_issues)

            # Scan configuration files
            config_patterns = ["*.yaml", "*.yml", "*.json", "*.env", "*.config"]
            for pattern in config_patterns:
                config_files = self.project_root.rglob(pattern)
                for file_path in config_files:
                    if self._should_skip_file(file_path):
                        continue

                    file_issues = await self._scan_file_for_secrets(file_path)
                    issues.extend(file_issues)

            time_taken = (datetime.utcnow() - start_time).total_seconds() * 1000

            logger.info(
                f"✓ Secret scan complete: {len(issues)} potential secrets found "
                f"in {time_taken:.2f}ms"
            )

            return self._create_scan_result("secrets", issues, time_taken)

        except Exception as e:
            time_taken = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(f"✗ Secret scan failed: {e}")

            return ScanResult(
                scan_type="secrets",
                issues_found=0,
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                time_taken_ms=time_taken,
                issues=[],
                success=False,
                error_message=str(e),
            )

    async def _scan_file_for_secrets(self, file_path: Path) -> List[SecurityIssue]:
        """Scan a single file for secrets"""
        issues = []

        try:
            content = file_path.read_text(encoding="utf-8")
            lines = content.split("\n")

            for pattern_name, pattern in self.SECRET_PATTERNS.items():
                for line_num, line in enumerate(lines, start=1):
                    # Skip comments
                    if line.strip().startswith("#") or line.strip().startswith("//"):
                        continue

                    matches = re.finditer(pattern, line)
                    for match in matches:
                        # Filter out common false positives
                        if self._is_false_positive(line, match.group(0)):
                            continue

                        issues.append(
                            SecurityIssue(
                                category="secret",
                                severity=Severity.CRITICAL,
                                title=f"Potential {pattern_name} detected",
                                description="Hardcoded secret detected in file",
                                file_path=str(file_path.relative_to(self.project_root)),
                                line_number=line_num,
                                recommendation="Move sensitive data to environment variables or secure vault",
                            )
                        )

        except UnicodeDecodeError:
            # Skip binary files
            pass
        except Exception as e:
            logger.warning(f"Error scanning {file_path}: {e}")

        return issues

    def _is_false_positive(self, line: str, match: str) -> bool:
        """Check if a match is likely a false positive"""
        # Check for common false positives
        false_positive_indicators = [
            "example",
            "placeholder",
            "dummy",
            "test",
            "fake",
            "mock",
            "your_",
            "<your_",
            "xxxx",
            "****",
            "TODO",
            "FIXME",
        ]

        line_lower = line.lower()
        match_lower = match.lower()

        for indicator in false_positive_indicators:
            if indicator in line_lower or indicator in match_lower:
                return True

        return False

    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped during scanning"""
        path_str = str(file_path)

        for pattern in self.SKIP_PATTERNS:
            if pattern in path_str:
                return True

        return False

    # ========================================================================
    # Code Security Analysis
    # ========================================================================

    async def scan_code_security(self) -> ScanResult:
        """
        Scan code for security issues using bandit.

        Returns:
            Scan result for code security
        """
        logger.info("Scanning code for security issues...")
        start_time = datetime.utcnow()
        issues = []

        try:
            # Run bandit (result unused, reads from output file instead)
            _result = subprocess.run(  # noqa: F841
                [
                    "bandit",
                    "-r",
                    str(self.project_root / "workspace"),
                    "-f",
                    "json",
                    "-o",
                    "/tmp/bandit_results.json",
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=120,
            )

            # Parse bandit results
            bandit_output = Path("/tmp/bandit_results.json")
            if bandit_output.exists():
                try:
                    bandit_data = json.loads(bandit_output.read_text())

                    for result_item in bandit_data.get("results", []):
                        severity_map = {
                            "HIGH": Severity.HIGH,
                            "MEDIUM": Severity.MEDIUM,
                            "LOW": Severity.LOW,
                        }

                        issues.append(
                            SecurityIssue(
                                category="code",
                                severity=severity_map.get(
                                    result_item.get("issue_severity", "MEDIUM"),
                                    Severity.MEDIUM,
                                ),
                                title=result_item.get("issue_text", ""),
                                description=result_item.get("issue_text", ""),
                                file_path=result_item.get("filename", ""),
                                line_number=result_item.get("line_number"),
                                cve_id=result_item.get("test_id"),
                                recommendation=result_item.get("more_info", ""),
                            )
                        )

                    # Clean up
                    bandit_output.unlink()

                except json.JSONDecodeError:
                    logger.warning("Could not parse bandit output")

            time_taken = (datetime.utcnow() - start_time).total_seconds() * 1000

            logger.info(
                f"✓ Code security scan complete: {len(issues)} issues found "
                f"in {time_taken:.2f}ms"
            )

            return self._create_scan_result("code", issues, time_taken)

        except FileNotFoundError:
            logger.warning("bandit tool not found, skipping code security scan")
            return self._create_scan_result("code", [], 0)
        except subprocess.TimeoutExpired:
            logger.warning("bandit scan timed out")
            return self._create_scan_result("code", [], 0)
        except Exception as e:
            time_taken = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(f"✗ Code security scan failed: {e}")

            return ScanResult(
                scan_type="code",
                issues_found=0,
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                time_taken_ms=time_taken,
                issues=[],
                success=False,
                error_message=str(e),
            )

    # ========================================================================
    # Docker Image Scanning
    # ========================================================================

    async def scan_docker_images(self) -> ScanResult:
        """
        Scan Docker images for vulnerabilities.

        Returns:
            Scan result for Docker images
        """
        logger.info("Scanning Docker images...")
        start_time = datetime.utcnow()
        issues = []

        try:
            # Find Dockerfiles
            dockerfiles = list(self.project_root.rglob("Dockerfile*"))

            if not dockerfiles:
                logger.info("No Dockerfiles found, skipping Docker scan")
                return self._create_scan_result("docker", [], 0)

            # Check base images
            for dockerfile in dockerfiles:
                dockerfile_issues = await self._scan_dockerfile(dockerfile)
                issues.extend(dockerfile_issues)

            time_taken = (datetime.utcnow() - start_time).total_seconds() * 1000

            logger.info(
                f"✓ Docker scan complete: {len(issues)} issues found "
                f"in {time_taken:.2f}ms"
            )

            return self._create_scan_result("docker", issues, time_taken)

        except Exception as e:
            time_taken = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(f"✗ Docker scan failed: {e}")

            return ScanResult(
                scan_type="docker",
                issues_found=0,
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                time_taken_ms=time_taken,
                issues=[],
                success=False,
                error_message=str(e),
            )

    async def _scan_dockerfile(self, dockerfile: Path) -> List[SecurityIssue]:
        """Scan a Dockerfile for security issues"""
        issues = []

        try:
            content = dockerfile.read_text(encoding="utf-8")
            lines = content.split("\n")

            # Check for insecure patterns
            for line_num, line in enumerate(lines, start=1):
                line_stripped = line.strip()

                # Check for running as root
                if line_stripped.startswith("USER root"):
                    issues.append(
                        SecurityIssue(
                            category="docker",
                            severity=Severity.MEDIUM,
                            title="Docker container running as root",
                            description="Container should not run as root user",
                            file_path=str(dockerfile.relative_to(self.project_root)),
                            line_number=line_num,
                            recommendation="Use USER directive to run as non-root user",
                        )
                    )

                # Check for latest tag
                if "FROM" in line_stripped and ":latest" in line_stripped:
                    issues.append(
                        SecurityIssue(
                            category="docker",
                            severity=Severity.LOW,
                            title="Using ':latest' tag in base image",
                            description="Latest tag can lead to unexpected changes",
                            file_path=str(dockerfile.relative_to(self.project_root)),
                            line_number=line_num,
                            recommendation="Pin to specific version tag",
                        )
                    )

                # Check for curl/wget without verification
                if ("curl" in line_stripped or "wget" in line_stripped) and (
                    "-k" in line_stripped or "--insecure" in line_stripped
                ):
                    issues.append(
                        SecurityIssue(
                            category="docker",
                            severity=Severity.HIGH,
                            title="Insecure download in Dockerfile",
                            description="Using curl/wget without SSL verification",
                            file_path=str(dockerfile.relative_to(self.project_root)),
                            line_number=line_num,
                            recommendation="Remove -k/--insecure flags",
                        )
                    )

        except Exception as e:
            logger.warning(f"Error scanning Dockerfile {dockerfile}: {e}")

        return issues

    # ========================================================================
    # Configuration Security
    # ========================================================================

    async def scan_configurations(self) -> ScanResult:
        """
        Scan configuration files for security issues.

        Returns:
            Scan result for configurations
        """
        logger.info("Scanning configurations...")
        start_time = datetime.utcnow()
        issues = []

        try:
            # Check for insecure configurations
            config_files = [
                self.project_root / "pyproject.toml",
                self.project_root / "docker-compose.yml",
                self.project_root / ".env.example",
            ]

            for config_file in config_files:
                if not config_file.exists():
                    continue

                config_issues = await self._scan_configuration_file(config_file)
                issues.extend(config_issues)

            time_taken = (datetime.utcnow() - start_time).total_seconds() * 1000

            logger.info(
                f"✓ Configuration scan complete: {len(issues)} issues found "
                f"in {time_taken:.2f}ms"
            )

            return self._create_scan_result("config", issues, time_taken)

        except Exception as e:
            time_taken = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(f"✗ Configuration scan failed: {e}")

            return ScanResult(
                scan_type="config",
                issues_found=0,
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                time_taken_ms=time_taken,
                issues=[],
                success=False,
                error_message=str(e),
            )

    async def _scan_configuration_file(self, config_file: Path) -> List[SecurityIssue]:
        """Scan a configuration file for security issues"""
        issues = []

        try:
            content = config_file.read_text(encoding="utf-8")

            # Check for insecure settings
            if "debug = true" in content.lower():
                issues.append(
                    SecurityIssue(
                        category="config",
                        severity=Severity.MEDIUM,
                        title="Debug mode enabled",
                        description="Debug mode should be disabled in production",
                        file_path=str(config_file.relative_to(self.project_root)),
                        recommendation="Set debug = false for production",
                    )
                )

            if "ssl = false" in content.lower() or "tls = false" in content.lower():
                issues.append(
                    SecurityIssue(
                        category="config",
                        severity=Severity.HIGH,
                        title="SSL/TLS disabled",
                        description="SSL/TLS should be enabled for secure communication",
                        file_path=str(config_file.relative_to(self.project_root)),
                        recommendation="Enable SSL/TLS for all connections",
                    )
                )

        except Exception as e:
            logger.warning(f"Error scanning config file {config_file}: {e}")

        return issues

    # ========================================================================
    # Reporting
    # ========================================================================

    def _create_scan_result(
        self, scan_type: str, issues: List[SecurityIssue], time_taken_ms: float
    ) -> ScanResult:
        """Create a scan result from issues"""
        critical_count = sum(1 for i in issues if i.severity == Severity.CRITICAL)
        high_count = sum(1 for i in issues if i.severity == Severity.HIGH)
        medium_count = sum(1 for i in issues if i.severity == Severity.MEDIUM)
        low_count = sum(1 for i in issues if i.severity == Severity.LOW)

        return ScanResult(
            scan_type=scan_type,
            issues_found=len(issues),
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count,
            time_taken_ms=time_taken_ms,
            issues=issues,
            success=True,
        )

    def generate_security_report(self, scan_results: Dict[str, ScanResult]) -> str:
        """
        Generate comprehensive security report.

        Args:
            scan_results: Dictionary of scan results

        Returns:
            Formatted security report
        """
        report = "\n" + "=" * 80 + "\n"
        report += "SECURITY SCAN REPORT\n"
        report += "=" * 80 + "\n\n"

        report += f"Scan Date: {datetime.utcnow().isoformat()}\n"
        report += f"Project: {self.project_root.name}\n\n"

        # Summary
        total_issues = sum(r.issues_found for r in scan_results.values())
        total_critical = sum(r.critical_count for r in scan_results.values())
        total_high = sum(r.high_count for r in scan_results.values())
        total_medium = sum(r.medium_count for r in scan_results.values())
        total_low = sum(r.low_count for r in scan_results.values())

        report += "SUMMARY\n"
        report += "-" * 80 + "\n"
        report += f"Total Issues: {total_issues}\n"
        report += f"  Critical: {total_critical}\n"
        report += f"  High: {total_high}\n"
        report += f"  Medium: {total_medium}\n"
        report += f"  Low: {total_low}\n\n"

        # Per-scan results
        for scan_type, result in scan_results.items():
            report += f"{scan_type.upper()} SCAN\n"
            report += "-" * 80 + "\n"
            report += f"Issues Found: {result.issues_found}\n"
            report += f"Time Taken: {result.time_taken_ms:.2f}ms\n"

            if result.issues:
                report += "\nIssues:\n"
                for issue in result.issues[:10]:  # Limit to first 10
                    report += f"  [{issue.severity.value}] {issue.title}\n"
                    if issue.file_path:
                        report += f"    File: {issue.file_path}"
                        if issue.line_number:
                            report += f":{issue.line_number}"
                        report += "\n"
                    if issue.recommendation:
                        report += f"    Fix: {issue.recommendation}\n"

                if result.issues_found > 10:
                    report += f"  ... and {result.issues_found - 10} more\n"

            report += "\n"

        report += "=" * 80 + "\n"

        return report
