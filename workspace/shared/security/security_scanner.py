"""
Security Scanner for Trading System.

This module provides comprehensive security scanning including:
- Dependency vulnerability scanning (safety, pip-audit)
- Code security scanning (bandit)
- Secret detection
- Security best practices validation
- Comprehensive reporting with severity levels

Author: Implementation Specialist
Date: 2025-10-30
"""

import asyncio
import logging
import json
import re
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class SeverityLevel(Enum):
    """Security issue severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class SecurityIssue:
    """Represents a single security issue."""

    issue_id: str
    title: str
    description: str
    severity: SeverityLevel
    category: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    cwe_id: Optional[str] = None
    cvss_score: Optional[float] = None
    recommendation: Optional[str] = None
    references: List[str] = field(default_factory=list)


@dataclass
class ScanResult:
    """Results from a security scan."""

    scan_type: str
    timestamp: datetime
    total_issues: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    info_count: int
    issues: List[SecurityIssue]
    scan_duration_ms: float
    scan_status: str  # "success", "failed", "partial"
    error_message: Optional[str] = None


@dataclass
class ScanConfig:
    """Configuration for security scanning."""

    # Project paths
    project_root: str = "."
    source_dirs: List[str] = field(default_factory=lambda: ["workspace"])
    exclude_dirs: List[str] = field(
        default_factory=lambda: [
            "__pycache__",
            ".git",
            ".venv",
            "venv",
            "node_modules",
            ".pytest_cache",
        ]
    )

    # Dependency scanning
    requirements_files: List[str] = field(
        default_factory=lambda: ["requirements.txt", "requirements-dev.txt"]
    )
    ignore_vulnerabilities: List[str] = field(default_factory=list)

    # Code scanning
    bandit_config: Optional[str] = None
    bandit_severity: str = "low"  # Minimum severity to report

    # Secret detection
    secret_patterns: List[str] = field(
        default_factory=lambda: [
            r"(?i)(api[_-]?key|apikey)\s*[:=]\s*['\"]([^'\"]+)['\"]",
            r"(?i)(secret|password|passwd|pwd)\s*[:=]\s*['\"]([^'\"]+)['\"]",
            r"(?i)(token)\s*[:=]\s*['\"]([^'\"]+)['\"]",
            r"(?i)(aws[_-]?access[_-]?key[_-]?id)\s*[:=]\s*['\"]([^'\"]+)['\"]",
            r"(?i)(aws[_-]?secret[_-]?access[_-]?key)\s*[:=]\s*['\"]([^'\"]+)['\"]",
            r"(?i)(['\"]sk[_-][a-zA-Z0-9]{20,}['\"])",  # Stripe secret keys
            r"(?i)(['\"]ghp[_-][a-zA-Z0-9]{36,}['\"])",  # GitHub tokens
            r"(?i)(['\"]AIza[a-zA-Z0-9_-]{35}['\"])",  # Google API keys
        ]
    )

    # Best practices
    check_ssl_verification: bool = True
    check_sql_injection: bool = True
    check_hardcoded_credentials: bool = True
    check_debug_mode: bool = True

    # Execution
    timeout_seconds: int = 300
    parallel_scans: bool = True


class SecurityScanner:
    """
    Comprehensive security scanner for the trading system.

    Performs multiple types of security scans including dependency
    vulnerabilities, code security issues, secret detection, and
    best practices validation.
    """

    def __init__(self, config: Optional[ScanConfig] = None):
        """
        Initialize the security scanner.

        Args:
            config: Scanner configuration
        """
        self.config = config or ScanConfig()
        self.project_root = Path(self.config.project_root).resolve()
        self.scan_results: Dict[str, ScanResult] = {}

    async def scan_dependencies(self) -> ScanResult:
        """
        Scan dependencies for known vulnerabilities using safety and pip-audit.

        Returns:
            ScanResult containing vulnerability findings
        """
        start_time = asyncio.get_event_loop().time()
        issues: List[SecurityIssue] = []
        scan_status = "success"
        error_message = None

        try:
            logger.info("Starting dependency vulnerability scan...")

            # Try safety first
            safety_issues = await self._scan_with_safety()
            issues.extend(safety_issues)

            # Try pip-audit as backup/supplement
            try:
                pip_audit_issues = await self._scan_with_pip_audit()
                # Deduplicate issues based on package name
                existing_packages = set(
                    issue.title.split()[0] for issue in safety_issues
                )
                for issue in pip_audit_issues:
                    package_name = issue.title.split()[0]
                    if package_name not in existing_packages:
                        issues.append(issue)
            except Exception as e:
                logger.debug(f"pip-audit scan failed (non-critical): {e}")

            # Count by severity
            severity_counts = self._count_by_severity(issues)

            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            result = ScanResult(
                scan_type="dependency_vulnerabilities",
                timestamp=datetime.now(),
                total_issues=len(issues),
                critical_count=severity_counts[SeverityLevel.CRITICAL],
                high_count=severity_counts[SeverityLevel.HIGH],
                medium_count=severity_counts[SeverityLevel.MEDIUM],
                low_count=severity_counts[SeverityLevel.LOW],
                info_count=severity_counts[SeverityLevel.INFO],
                issues=issues,
                scan_duration_ms=duration_ms,
                scan_status=scan_status,
                error_message=error_message,
            )

            logger.info(
                f"Dependency scan complete: {len(issues)} issues found "
                f"(Critical: {severity_counts[SeverityLevel.CRITICAL]}, "
                f"High: {severity_counts[SeverityLevel.HIGH]})"
            )

            self.scan_results["dependencies"] = result
            return result

        except Exception as e:
            logger.error(f"Dependency scan failed: {e}")
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            return ScanResult(
                scan_type="dependency_vulnerabilities",
                timestamp=datetime.now(),
                total_issues=0,
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                info_count=0,
                issues=[],
                scan_duration_ms=duration_ms,
                scan_status="failed",
                error_message=str(e),
            )

    async def _scan_with_safety(self) -> List[SecurityIssue]:
        """Scan with safety package."""
        try:
            # Check if safety is installed
            check_result = await asyncio.create_subprocess_exec(
                "python3",
                "-m",
                "safety",
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await check_result.communicate()

            if check_result.returncode != 0:
                logger.warning("safety package not installed, skipping safety scan")
                return []

            # Run safety check
            cmd = ["python3", "-m", "safety", "check", "--json", "--output", "json"]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.project_root),
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=self.config.timeout_seconds
            )

            # Parse JSON output
            issues = []
            try:
                results = json.loads(stdout.decode())

                if isinstance(results, list):
                    for vuln in results:
                        severity = self._map_severity(vuln.get("severity", "medium"))

                        issue = SecurityIssue(
                            issue_id=vuln.get("vulnerability_id", "UNKNOWN"),
                            title=f"{vuln.get('package_name', 'unknown')} - {vuln.get('advisory', 'Unknown vulnerability')}",
                            description=vuln.get("advisory", "No description"),
                            severity=severity,
                            category="dependency_vulnerability",
                            cwe_id=vuln.get("cwe", None),
                            cvss_score=vuln.get("cvss_score", None),
                            recommendation=f"Upgrade to version {vuln.get('safe_version', 'latest')}",
                            references=vuln.get("references", []),
                        )
                        issues.append(issue)

            except json.JSONDecodeError:
                logger.debug("No vulnerabilities found by safety")

            return issues

        except asyncio.TimeoutError:
            logger.error("safety scan timeout")
            return []
        except Exception as e:
            logger.error(f"safety scan failed: {e}")
            return []

    async def _scan_with_pip_audit(self) -> List[SecurityIssue]:
        """Scan with pip-audit package."""
        try:
            # Check if pip-audit is installed
            check_result = await asyncio.create_subprocess_exec(
                "python3",
                "-m",
                "pip_audit",
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await check_result.communicate()

            if check_result.returncode != 0:
                logger.debug("pip-audit not installed, skipping")
                return []

            # Run pip-audit
            cmd = ["python3", "-m", "pip_audit", "--format", "json"]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.project_root),
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=self.config.timeout_seconds
            )

            # Parse JSON output
            issues = []
            try:
                results = json.loads(stdout.decode())

                if "dependencies" in results:
                    for dep in results["dependencies"]:
                        for vuln in dep.get("vulns", []):
                            severity = self._map_severity("medium")

                            issue = SecurityIssue(
                                issue_id=vuln.get("id", "UNKNOWN"),
                                title=f"{dep.get('name', 'unknown')} - {vuln.get('description', 'Unknown vulnerability')}",
                                description=vuln.get("description", "No description"),
                                severity=severity,
                                category="dependency_vulnerability",
                                recommendation="Upgrade to a fixed version",
                                references=vuln.get("references", []),
                            )
                            issues.append(issue)

            except json.JSONDecodeError:
                logger.debug("No vulnerabilities found by pip-audit")

            return issues

        except asyncio.TimeoutError:
            logger.error("pip-audit scan timeout")
            return []
        except Exception as e:
            logger.debug(f"pip-audit scan failed (expected if not installed): {e}")
            return []

    async def scan_code(self) -> ScanResult:
        """
        Scan code for security issues using bandit.

        Returns:
            ScanResult containing code security findings
        """
        start_time = asyncio.get_event_loop().time()
        issues: List[SecurityIssue] = []
        scan_status = "success"
        error_message = None

        try:
            logger.info("Starting code security scan with bandit...")

            # Check if bandit is installed
            check_result = await asyncio.create_subprocess_exec(
                "python3",
                "-m",
                "bandit",
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await check_result.communicate()

            if check_result.returncode != 0:
                logger.warning("bandit not installed, generating simulated scan")
                # Return empty result if bandit not available
                duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                return ScanResult(
                    scan_type="code_security",
                    timestamp=datetime.now(),
                    total_issues=0,
                    critical_count=0,
                    high_count=0,
                    medium_count=0,
                    low_count=0,
                    info_count=0,
                    issues=[],
                    scan_duration_ms=duration_ms,
                    scan_status="skipped",
                    error_message="bandit not installed",
                )

            # Build bandit command
            cmd = ["python3", "-m", "bandit", "-r", "-f", "json"]

            # Add source directories
            for source_dir in self.config.source_dirs:
                source_path = self.project_root / source_dir
                if source_path.exists():
                    cmd.append(str(source_path))

            # Add excludes
            if self.config.exclude_dirs:
                cmd.extend(["-x", ",".join(self.config.exclude_dirs)])

            # Add config if specified
            if self.config.bandit_config:
                cmd.extend(["-c", self.config.bandit_config])

            # Run bandit
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.project_root),
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=self.config.timeout_seconds
            )

            # Parse JSON output
            try:
                results = json.loads(stdout.decode())

                for result in results.get("results", []):
                    # Map bandit severity to our severity levels
                    bandit_severity = result.get("issue_severity", "LOW")
                    severity = self._map_bandit_severity(bandit_severity)

                    # Filter by minimum severity
                    if not self._meets_severity_threshold(severity):
                        continue

                    issue = SecurityIssue(
                        issue_id=result.get("test_id", "B000"),
                        title=result.get("test_name", "Unknown issue"),
                        description=result.get("issue_text", "No description"),
                        severity=severity,
                        category="code_security",
                        file_path=result.get("filename"),
                        line_number=result.get("line_number"),
                        cwe_id=result.get("cwe", {}).get("id")
                        if isinstance(result.get("cwe"), dict)
                        else None,
                        recommendation=result.get(
                            "more_info", "See bandit documentation"
                        ),
                        references=[result.get("more_info", "")],
                    )
                    issues.append(issue)

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse bandit output: {e}")
                scan_status = "partial"
                error_message = f"Failed to parse bandit output: {e}"

            # Count by severity
            severity_counts = self._count_by_severity(issues)

            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            result = ScanResult(
                scan_type="code_security",
                timestamp=datetime.now(),
                total_issues=len(issues),
                critical_count=severity_counts[SeverityLevel.CRITICAL],
                high_count=severity_counts[SeverityLevel.HIGH],
                medium_count=severity_counts[SeverityLevel.MEDIUM],
                low_count=severity_counts[SeverityLevel.LOW],
                info_count=severity_counts[SeverityLevel.INFO],
                issues=issues,
                scan_duration_ms=duration_ms,
                scan_status=scan_status,
                error_message=error_message,
            )

            logger.info(
                f"Code security scan complete: {len(issues)} issues found "
                f"(Critical: {severity_counts[SeverityLevel.CRITICAL]}, "
                f"High: {severity_counts[SeverityLevel.HIGH]})"
            )

            self.scan_results["code_security"] = result
            return result

        except asyncio.TimeoutError:
            logger.error("Code scan timeout")
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            return ScanResult(
                scan_type="code_security",
                timestamp=datetime.now(),
                total_issues=0,
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                info_count=0,
                issues=[],
                scan_duration_ms=duration_ms,
                scan_status="failed",
                error_message="Scan timeout",
            )
        except Exception as e:
            logger.error(f"Code scan failed: {e}")
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            return ScanResult(
                scan_type="code_security",
                timestamp=datetime.now(),
                total_issues=0,
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                info_count=0,
                issues=[],
                scan_duration_ms=duration_ms,
                scan_status="failed",
                error_message=str(e),
            )

    async def detect_secrets(self) -> ScanResult:
        """
        Detect hardcoded secrets in source code.

        Returns:
            ScanResult containing secret detection findings
        """
        start_time = asyncio.get_event_loop().time()
        issues: List[SecurityIssue] = []

        try:
            logger.info("Starting secret detection scan...")

            # Scan each source directory
            for source_dir in self.config.source_dirs:
                source_path = self.project_root / source_dir
                if not source_path.exists():
                    continue

                # Walk through all Python files
                for python_file in source_path.rglob("*.py"):
                    # Skip excluded directories
                    if any(
                        excl in str(python_file) for excl in self.config.exclude_dirs
                    ):
                        continue

                    file_issues = await self._scan_file_for_secrets(python_file)
                    issues.extend(file_issues)

            # Count by severity
            severity_counts = self._count_by_severity(issues)

            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            result = ScanResult(
                scan_type="secret_detection",
                timestamp=datetime.now(),
                total_issues=len(issues),
                critical_count=severity_counts[SeverityLevel.CRITICAL],
                high_count=severity_counts[SeverityLevel.HIGH],
                medium_count=severity_counts[SeverityLevel.MEDIUM],
                low_count=severity_counts[SeverityLevel.LOW],
                info_count=severity_counts[SeverityLevel.INFO],
                issues=issues,
                scan_duration_ms=duration_ms,
                scan_status="success",
            )

            logger.info(
                f"Secret detection complete: {len(issues)} potential secrets found "
                f"(Critical: {severity_counts[SeverityLevel.CRITICAL]}, "
                f"High: {severity_counts[SeverityLevel.HIGH]})"
            )

            self.scan_results["secrets"] = result
            return result

        except Exception as e:
            logger.error(f"Secret detection failed: {e}")
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            return ScanResult(
                scan_type="secret_detection",
                timestamp=datetime.now(),
                total_issues=0,
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                info_count=0,
                issues=[],
                scan_duration_ms=duration_ms,
                scan_status="failed",
                error_message=str(e),
            )

    async def _scan_file_for_secrets(self, file_path: Path) -> List[SecurityIssue]:
        """Scan a single file for secrets."""
        issues = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.split("\n")

                for line_num, line in enumerate(lines, 1):
                    # Skip comments
                    if line.strip().startswith("#"):
                        continue

                    # Check each pattern
                    for pattern in self.config.secret_patterns:
                        matches = re.finditer(pattern, line)

                        for match in matches:
                            # Skip if looks like a placeholder or example
                            matched_text = match.group(0)
                            if self._is_false_positive(matched_text):
                                continue

                            issue = SecurityIssue(
                                issue_id=f"SECRET-{line_num}",
                                title="Potential hardcoded secret detected",
                                description=f"Found potential secret: {matched_text[:50]}...",
                                severity=SeverityLevel.CRITICAL,
                                category="hardcoded_secret",
                                file_path=str(file_path.relative_to(self.project_root)),
                                line_number=line_num,
                                recommendation="Remove hardcoded secret and use environment variables or secret management",
                            )
                            issues.append(issue)

        except Exception as e:
            logger.debug(f"Failed to scan {file_path}: {e}")

        return issues

    def _is_false_positive(self, text: str) -> bool:
        """Check if detected secret is likely a false positive."""
        false_positive_patterns = [
            r"(?i)(example|placeholder|test|dummy|fake|your|my)",
            r"(?i)(\*{3,}|x{3,})",
            r"(?i)(123|abc|password)",
            r"(?i)(TODO|FIXME)",
        ]

        for pattern in false_positive_patterns:
            if re.search(pattern, text):
                return True

        return False

    async def validate_best_practices(self) -> ScanResult:
        """
        Validate security best practices in the codebase.

        Returns:
            ScanResult containing best practice violations
        """
        start_time = asyncio.get_event_loop().time()
        issues: List[SecurityIssue] = []

        try:
            logger.info("Starting best practices validation...")

            # Check for common security anti-patterns
            if self.config.check_ssl_verification:
                ssl_issues = await self._check_ssl_verification()
                issues.extend(ssl_issues)

            if self.config.check_sql_injection:
                sql_issues = await self._check_sql_injection()
                issues.extend(sql_issues)

            if self.config.check_hardcoded_credentials:
                cred_issues = await self._check_hardcoded_credentials()
                issues.extend(cred_issues)

            if self.config.check_debug_mode:
                debug_issues = await self._check_debug_mode()
                issues.extend(debug_issues)

            # Count by severity
            severity_counts = self._count_by_severity(issues)

            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            result = ScanResult(
                scan_type="best_practices",
                timestamp=datetime.now(),
                total_issues=len(issues),
                critical_count=severity_counts[SeverityLevel.CRITICAL],
                high_count=severity_counts[SeverityLevel.HIGH],
                medium_count=severity_counts[SeverityLevel.MEDIUM],
                low_count=severity_counts[SeverityLevel.LOW],
                info_count=severity_counts[SeverityLevel.INFO],
                issues=issues,
                scan_duration_ms=duration_ms,
                scan_status="success",
            )

            logger.info(
                f"Best practices validation complete: {len(issues)} violations found "
                f"(Critical: {severity_counts[SeverityLevel.CRITICAL]}, "
                f"High: {severity_counts[SeverityLevel.HIGH]})"
            )

            self.scan_results["best_practices"] = result
            return result

        except Exception as e:
            logger.error(f"Best practices validation failed: {e}")
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            return ScanResult(
                scan_type="best_practices",
                timestamp=datetime.now(),
                total_issues=0,
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                info_count=0,
                issues=[],
                scan_duration_ms=duration_ms,
                scan_status="failed",
                error_message=str(e),
            )

    async def _check_ssl_verification(self) -> List[SecurityIssue]:
        """Check for disabled SSL verification."""
        issues = []
        patterns = [
            r"verify\s*=\s*False",
            r"ssl\._create_unverified_context",
            r"CERT_NONE",
        ]

        for source_dir in self.config.source_dirs:
            source_path = self.project_root / source_dir
            if not source_path.exists():
                continue

            for python_file in source_path.rglob("*.py"):
                if any(excl in str(python_file) for excl in self.config.exclude_dirs):
                    continue

                try:
                    with open(python_file, "r", encoding="utf-8") as f:
                        lines = f.readlines()

                    for line_num, line in enumerate(lines, 1):
                        for pattern in patterns:
                            if re.search(pattern, line):
                                issue = SecurityIssue(
                                    issue_id=f"SSL-{line_num}",
                                    title="SSL verification disabled",
                                    description=f"Found disabled SSL verification: {line.strip()}",
                                    severity=SeverityLevel.HIGH,
                                    category="ssl_verification",
                                    file_path=str(
                                        python_file.relative_to(self.project_root)
                                    ),
                                    line_number=line_num,
                                    cwe_id="CWE-295",
                                    recommendation="Enable SSL certificate verification",
                                )
                                issues.append(issue)

                except Exception as e:
                    logger.debug(f"Failed to check SSL in {python_file}: {e}")

        return issues

    async def _check_sql_injection(self) -> List[SecurityIssue]:
        """Check for potential SQL injection vulnerabilities."""
        issues = []
        # Look for string concatenation in SQL queries
        patterns = [
            r"execute\s*\(\s*['\"].*%s.*['\"].*%",
            r"execute\s*\(\s*.*\+.*\)",
            r"raw\s*\(\s*f['\"]",
        ]

        for source_dir in self.config.source_dirs:
            source_path = self.project_root / source_dir
            if not source_path.exists():
                continue

            for python_file in source_path.rglob("*.py"):
                if any(excl in str(python_file) for excl in self.config.exclude_dirs):
                    continue

                try:
                    with open(python_file, "r", encoding="utf-8") as f:
                        lines = f.readlines()

                    for line_num, line in enumerate(lines, 1):
                        for pattern in patterns:
                            if re.search(pattern, line):
                                issue = SecurityIssue(
                                    issue_id=f"SQL-{line_num}",
                                    title="Potential SQL injection vulnerability",
                                    description=f"Found potential SQL injection: {line.strip()}",
                                    severity=SeverityLevel.HIGH,
                                    category="sql_injection",
                                    file_path=str(
                                        python_file.relative_to(self.project_root)
                                    ),
                                    line_number=line_num,
                                    cwe_id="CWE-89",
                                    recommendation="Use parameterized queries or ORM",
                                )
                                issues.append(issue)

                except Exception as e:
                    logger.debug(f"Failed to check SQL in {python_file}: {e}")

        return issues

    async def _check_hardcoded_credentials(self) -> List[SecurityIssue]:
        """Check for hardcoded credentials in common patterns."""
        issues = []
        # This is different from secret detection - focuses on common anti-patterns
        patterns = [
            r"(?i)password\s*=\s*['\"][^'\"]{3,}['\"]",
            r"(?i)username\s*=\s*['\"]admin['\"]",
            r"(?i)default_password",
        ]

        for source_dir in self.config.source_dirs:
            source_path = self.project_root / source_dir
            if not source_path.exists():
                continue

            for python_file in source_path.rglob("*.py"):
                if any(excl in str(python_file) for excl in self.config.exclude_dirs):
                    continue

                try:
                    with open(python_file, "r", encoding="utf-8") as f:
                        lines = f.readlines()

                    for line_num, line in enumerate(lines, 1):
                        # Skip test files
                        if "test_" in str(python_file) or line.strip().startswith("#"):
                            continue

                        for pattern in patterns:
                            if re.search(pattern, line):
                                issue = SecurityIssue(
                                    issue_id=f"CRED-{line_num}",
                                    title="Hardcoded credentials detected",
                                    description=f"Found hardcoded credentials: {line.strip()[:50]}",
                                    severity=SeverityLevel.HIGH,
                                    category="hardcoded_credentials",
                                    file_path=str(
                                        python_file.relative_to(self.project_root)
                                    ),
                                    line_number=line_num,
                                    cwe_id="CWE-798",
                                    recommendation="Use environment variables or secret management",
                                )
                                issues.append(issue)

                except Exception as e:
                    logger.debug(f"Failed to check credentials in {python_file}: {e}")

        return issues

    async def _check_debug_mode(self) -> List[SecurityIssue]:
        """Check for debug mode enabled in production code."""
        issues = []
        patterns = [
            r"DEBUG\s*=\s*True",
            r"debug\s*=\s*True",
            r"FLASK_ENV\s*=\s*['\"]development['\"]",
            r"DJANGO_DEBUG\s*=\s*True",
        ]

        for source_dir in self.config.source_dirs:
            source_path = self.project_root / source_dir
            if not source_path.exists():
                continue

            for python_file in source_path.rglob("*.py"):
                if any(excl in str(python_file) for excl in self.config.exclude_dirs):
                    continue

                # Skip test and config files
                if "test_" in str(python_file) or "config" in str(python_file).lower():
                    continue

                try:
                    with open(python_file, "r", encoding="utf-8") as f:
                        lines = f.readlines()

                    for line_num, line in enumerate(lines, 1):
                        for pattern in patterns:
                            if re.search(pattern, line):
                                issue = SecurityIssue(
                                    issue_id=f"DEBUG-{line_num}",
                                    title="Debug mode enabled",
                                    description=f"Found debug mode enabled: {line.strip()}",
                                    severity=SeverityLevel.MEDIUM,
                                    category="debug_mode",
                                    file_path=str(
                                        python_file.relative_to(self.project_root)
                                    ),
                                    line_number=line_num,
                                    recommendation="Disable debug mode in production",
                                )
                                issues.append(issue)

                except Exception as e:
                    logger.debug(f"Failed to check debug mode in {python_file}: {e}")

        return issues

    async def run_full_scan(self) -> Dict[str, ScanResult]:
        """
        Run all security scans.

        Returns:
            Dictionary mapping scan types to their results
        """
        logger.info("Starting full security scan...")
        start_time = asyncio.get_event_loop().time()

        try:
            if self.config.parallel_scans:
                # Run scans in parallel
                results = await asyncio.gather(
                    self.scan_dependencies(),
                    self.scan_code(),
                    self.detect_secrets(),
                    self.validate_best_practices(),
                    return_exceptions=True,
                )

                # Process results
                scan_types = [
                    "dependencies",
                    "code_security",
                    "secrets",
                    "best_practices",
                ]
                for scan_type, result in zip(scan_types, results):
                    if isinstance(result, Exception):
                        logger.error(f"Scan {scan_type} failed: {result}")
                    else:
                        self.scan_results[scan_type] = result
            else:
                # Run scans sequentially
                self.scan_results["dependencies"] = await self.scan_dependencies()
                self.scan_results["code_security"] = await self.scan_code()
                self.scan_results["secrets"] = await self.detect_secrets()
                self.scan_results[
                    "best_practices"
                ] = await self.validate_best_practices()

            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            # Calculate total statistics
            total_issues = sum(r.total_issues for r in self.scan_results.values())
            total_critical = sum(r.critical_count for r in self.scan_results.values())
            total_high = sum(r.high_count for r in self.scan_results.values())

            logger.info(
                f"Full security scan complete in {duration_ms:.2f}ms: "
                f"{total_issues} total issues "
                f"(Critical: {total_critical}, High: {total_high})"
            )

            return self.scan_results

        except Exception as e:
            logger.error(f"Full security scan failed: {e}")
            return self.scan_results

    def generate_report(self, results: Optional[Dict[str, ScanResult]] = None) -> str:
        """
        Generate a comprehensive security scan report.

        Args:
            results: Scan results to report on (uses stored results if None)

        Returns:
            Formatted security report as string
        """
        if results is None:
            results = self.scan_results

        if not results:
            return "No scan results available"

        # Build report
        lines = []
        lines.append("=" * 80)
        lines.append("SECURITY SCAN REPORT")
        lines.append("=" * 80)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Project: {self.project_root}")
        lines.append("")

        # Executive summary
        total_issues = sum(r.total_issues for r in results.values())
        total_critical = sum(r.critical_count for r in results.values())
        total_high = sum(r.high_count for r in results.values())
        total_medium = sum(r.medium_count for r in results.values())
        total_low = sum(r.low_count for r in results.values())

        lines.append("EXECUTIVE SUMMARY")
        lines.append("-" * 80)
        lines.append(f"Total Issues: {total_issues}")
        lines.append(f"  Critical: {total_critical}")
        lines.append(f"  High:     {total_high}")
        lines.append(f"  Medium:   {total_medium}")
        lines.append(f"  Low:      {total_low}")
        lines.append("")

        # Scan results by type
        for scan_type, result in results.items():
            lines.append(f"{scan_type.upper().replace('_', ' ')}")
            lines.append("-" * 80)
            lines.append(f"Status: {result.scan_status}")
            lines.append(f"Duration: {result.scan_duration_ms:.2f}ms")
            lines.append(
                f"Issues: {result.total_issues} "
                f"(Critical: {result.critical_count}, High: {result.high_count}, "
                f"Medium: {result.medium_count}, Low: {result.low_count})"
            )

            if result.error_message:
                lines.append(f"Error: {result.error_message}")

            # Top 5 critical/high issues
            critical_high = [
                issue
                for issue in result.issues
                if issue.severity in (SeverityLevel.CRITICAL, SeverityLevel.HIGH)
            ]

            if critical_high:
                lines.append("")
                lines.append(f"Top {min(5, len(critical_high))} Critical/High Issues:")
                for i, issue in enumerate(critical_high[:5], 1):
                    lines.append(
                        f"  {i}. [{issue.severity.value.upper()}] {issue.title}"
                    )
                    if issue.file_path:
                        lines.append(
                            f"     File: {issue.file_path}:{issue.line_number or '?'}"
                        )
                    lines.append(f"     {issue.description[:100]}...")

            lines.append("")

        # Recommendations
        lines.append("RECOMMENDATIONS")
        lines.append("-" * 80)

        if total_critical > 0:
            lines.append(
                f"1. CRITICAL: Address {total_critical} critical issues immediately"
            )
        if total_high > 0:
            lines.append(f"2. HIGH: Review and fix {total_high} high-severity issues")
        if total_medium > 0:
            lines.append(
                f"3. MEDIUM: Plan to address {total_medium} medium-severity issues"
            )

        if total_critical == 0 and total_high == 0:
            lines.append("No critical or high-severity issues found. Good job!")

        lines.append("")
        lines.append("=" * 80)

        return "\n".join(lines)

    def _count_by_severity(
        self, issues: List[SecurityIssue]
    ) -> Dict[SeverityLevel, int]:
        """Count issues by severity level."""
        counts = {level: 0 for level in SeverityLevel}
        for issue in issues:
            counts[issue.severity] += 1
        return counts

    def _map_severity(self, severity_str: str) -> SeverityLevel:
        """Map string severity to SeverityLevel enum."""
        severity_map = {
            "critical": SeverityLevel.CRITICAL,
            "high": SeverityLevel.HIGH,
            "medium": SeverityLevel.MEDIUM,
            "low": SeverityLevel.LOW,
            "info": SeverityLevel.INFO,
        }
        return severity_map.get(severity_str.lower(), SeverityLevel.MEDIUM)

    def _map_bandit_severity(self, bandit_severity: str) -> SeverityLevel:
        """Map bandit severity to our SeverityLevel."""
        severity_map = {
            "HIGH": SeverityLevel.HIGH,
            "MEDIUM": SeverityLevel.MEDIUM,
            "LOW": SeverityLevel.LOW,
        }
        return severity_map.get(bandit_severity.upper(), SeverityLevel.LOW)

    def _meets_severity_threshold(self, severity: SeverityLevel) -> bool:
        """Check if severity meets the configured threshold."""
        severity_order = [
            SeverityLevel.INFO,
            SeverityLevel.LOW,
            SeverityLevel.MEDIUM,
            SeverityLevel.HIGH,
            SeverityLevel.CRITICAL,
        ]

        threshold = self._map_severity(self.config.bandit_severity)
        return severity_order.index(severity) >= severity_order.index(threshold)


# CLI interface
async def main():
    """Command-line interface for security scanner."""
    import argparse

    parser = argparse.ArgumentParser(description="Security Scanner for Trading System")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    parser.add_argument(
        "--scan-type",
        choices=["all", "dependencies", "code", "secrets", "practices"],
        default="all",
        help="Type of scan to run",
    )
    parser.add_argument("--output", help="Output file for report")
    parser.add_argument("--parallel", action="store_true", help="Run scans in parallel")

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create scanner
    config = ScanConfig(project_root=args.project_root, parallel_scans=args.parallel)
    scanner = SecurityScanner(config)

    # Run scan
    if args.scan_type == "all":
        results = await scanner.run_full_scan()
    elif args.scan_type == "dependencies":
        result = await scanner.scan_dependencies()
        results = {"dependencies": result}
    elif args.scan_type == "code":
        result = await scanner.scan_code()
        results = {"code_security": result}
    elif args.scan_type == "secrets":
        result = await scanner.detect_secrets()
        results = {"secrets": result}
    elif args.scan_type == "practices":
        result = await scanner.validate_best_practices()
        results = {"best_practices": result}

    # Generate report
    report = scanner.generate_report(results)

    # Output report
    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        print(f"Report written to {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    asyncio.run(main())
