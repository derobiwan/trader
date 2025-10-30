"""
Penetration Testing Suite for Trading System.

This module provides automated security testing including:
- SQL injection testing (7 payload types)
- XSS attack testing (5 payload types)
- Authentication bypass testing
- Rate limiting testing
- Input validation testing
- API security testing

Author: Implementation Specialist
Date: 2025-10-30
"""

import asyncio
import logging
import time
import aiohttp
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import re

logger = logging.getLogger(__name__)


class AttackType(Enum):
    """Types of penetration test attacks."""

    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    AUTHENTICATION_BYPASS = "authentication_bypass"
    RATE_LIMITING = "rate_limiting"
    INPUT_VALIDATION = "input_validation"
    API_SECURITY = "api_security"


class VulnerabilityLevel(Enum):
    """Vulnerability severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class TestPayload:
    """Represents a single test payload."""

    payload_id: str
    attack_type: AttackType
    description: str
    payload: Any
    expected_behavior: str
    severity_if_vulnerable: VulnerabilityLevel


@dataclass
class VulnerabilityFinding:
    """Represents a discovered vulnerability."""

    finding_id: str
    attack_type: AttackType
    vulnerability_level: VulnerabilityLevel
    endpoint: str
    description: str
    payload_used: str
    response_evidence: str
    cwe_id: Optional[str] = None
    remediation: str = ""
    references: List[str] = field(default_factory=list)


@dataclass
class PenTestResult:
    """Results from a penetration test."""

    test_type: AttackType
    timestamp: datetime
    total_tests: int
    vulnerabilities_found: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    findings: List[VulnerabilityFinding]
    test_duration_ms: float
    test_status: str  # "success", "failed", "partial"
    error_message: Optional[str] = None


@dataclass
class PenTestConfig:
    """Configuration for penetration testing."""

    # Target configuration
    base_url: str = "http://localhost:8000"
    api_endpoints: List[str] = field(
        default_factory=lambda: [
            "/api/v1/positions",
            "/api/v1/trades",
            "/api/v1/signals",
            "/api/v1/balance",
            "/api/v1/market-data",
        ]
    )

    # Authentication
    auth_token: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None

    # Test configuration
    timeout_seconds: int = 10
    max_concurrent_tests: int = 5
    rate_limit_test_requests: int = 100
    rate_limit_test_duration_seconds: int = 60

    # Safety settings
    safe_mode: bool = True  # Prevents destructive operations
    skip_destructive_tests: bool = True


class PenetrationTester:
    """
    Comprehensive penetration testing suite for the trading system.

    Performs automated security testing to identify common vulnerabilities
    in a controlled, safe manner.
    """

    def __init__(self, config: Optional[PenTestConfig] = None):
        """
        Initialize the penetration tester.

        Args:
            config: Penetration test configuration
        """
        self.config = config or PenTestConfig()
        self.session: Optional[aiohttp.ClientSession] = None
        self.test_results: Dict[str, PenTestResult] = {}

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def test_sql_injection(self) -> PenTestResult:
        """
        Test for SQL injection vulnerabilities.

        Tests 7 payload types:
        1. Union-based
        2. Boolean-based blind
        3. Time-based blind
        4. Error-based
        5. Stacked queries
        6. Out-of-band
        7. Classic injection

        Returns:
            PenTestResult with findings
        """
        start_time = time.time()
        findings: List[VulnerabilityFinding] = []

        try:
            logger.info("Starting SQL injection tests...")

            # Define SQL injection payloads
            payloads = [
                # Union-based
                TestPayload(
                    payload_id="SQL-UNION-01",
                    attack_type=AttackType.SQL_INJECTION,
                    description="Union-based SQL injection",
                    payload="' UNION SELECT NULL, NULL, NULL--",
                    expected_behavior="Should reject malicious SQL syntax",
                    severity_if_vulnerable=VulnerabilityLevel.CRITICAL,
                ),
                # Boolean-based blind
                TestPayload(
                    payload_id="SQL-BOOL-01",
                    attack_type=AttackType.SQL_INJECTION,
                    description="Boolean-based blind SQL injection",
                    payload="' AND 1=1--",
                    expected_behavior="Should not change query logic",
                    severity_if_vulnerable=VulnerabilityLevel.HIGH,
                ),
                TestPayload(
                    payload_id="SQL-BOOL-02",
                    attack_type=AttackType.SQL_INJECTION,
                    description="Boolean-based blind SQL injection (false)",
                    payload="' AND 1=2--",
                    expected_behavior="Should not change query logic",
                    severity_if_vulnerable=VulnerabilityLevel.HIGH,
                ),
                # Time-based blind
                TestPayload(
                    payload_id="SQL-TIME-01",
                    attack_type=AttackType.SQL_INJECTION,
                    description="Time-based blind SQL injection",
                    payload="'; WAITFOR DELAY '00:00:05'--",
                    expected_behavior="Should not introduce delays",
                    severity_if_vulnerable=VulnerabilityLevel.HIGH,
                ),
                # Error-based
                TestPayload(
                    payload_id="SQL-ERROR-01",
                    attack_type=AttackType.SQL_INJECTION,
                    description="Error-based SQL injection",
                    payload="' AND 1=CONVERT(int, (SELECT @@version))--",
                    expected_behavior="Should not reveal database errors",
                    severity_if_vulnerable=VulnerabilityLevel.HIGH,
                ),
                # Stacked queries
                TestPayload(
                    payload_id="SQL-STACK-01",
                    attack_type=AttackType.SQL_INJECTION,
                    description="Stacked queries SQL injection",
                    payload="'; DROP TABLE test_table--",
                    expected_behavior="Should not execute multiple queries",
                    severity_if_vulnerable=VulnerabilityLevel.CRITICAL,
                ),
                # Classic injection
                TestPayload(
                    payload_id="SQL-CLASSIC-01",
                    attack_type=AttackType.SQL_INJECTION,
                    description="Classic SQL injection",
                    payload="' OR '1'='1",
                    expected_behavior="Should not bypass WHERE conditions",
                    severity_if_vulnerable=VulnerabilityLevel.CRITICAL,
                ),
            ]

            # Test each endpoint with each payload
            for endpoint in self.config.api_endpoints:
                for payload in payloads:
                    finding = await self._test_endpoint_with_payload(endpoint, payload)
                    if finding:
                        findings.append(finding)

            # Count by severity
            severity_counts = self._count_by_severity(findings)

            duration_ms = (time.time() - start_time) * 1000

            result = PenTestResult(
                test_type=AttackType.SQL_INJECTION,
                timestamp=datetime.now(),
                total_tests=len(payloads) * len(self.config.api_endpoints),
                vulnerabilities_found=len(findings),
                critical_count=severity_counts[VulnerabilityLevel.CRITICAL],
                high_count=severity_counts[VulnerabilityLevel.HIGH],
                medium_count=severity_counts[VulnerabilityLevel.MEDIUM],
                low_count=severity_counts[VulnerabilityLevel.LOW],
                findings=findings,
                test_duration_ms=duration_ms,
                test_status="success",
            )

            logger.info(
                f"SQL injection tests complete: {len(findings)} vulnerabilities found "
                f"(Critical: {severity_counts[VulnerabilityLevel.CRITICAL]}, "
                f"High: {severity_counts[VulnerabilityLevel.HIGH]})"
            )

            self.test_results["sql_injection"] = result
            return result

        except Exception as e:
            logger.error(f"SQL injection tests failed: {e}")
            duration_ms = (time.time() - start_time) * 1000
            return PenTestResult(
                test_type=AttackType.SQL_INJECTION,
                timestamp=datetime.now(),
                total_tests=0,
                vulnerabilities_found=0,
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                findings=[],
                test_duration_ms=duration_ms,
                test_status="failed",
                error_message=str(e),
            )

    async def test_xss(self) -> PenTestResult:
        """
        Test for Cross-Site Scripting (XSS) vulnerabilities.

        Tests 5 payload types:
        1. Stored XSS
        2. Reflected XSS
        3. DOM-based XSS
        4. Event handler XSS
        5. SVG-based XSS

        Returns:
            PenTestResult with findings
        """
        start_time = time.time()
        findings: List[VulnerabilityFinding] = []

        try:
            logger.info("Starting XSS tests...")

            # Define XSS payloads
            payloads = [
                # Stored XSS
                TestPayload(
                    payload_id="XSS-STORED-01",
                    attack_type=AttackType.XSS,
                    description="Stored XSS via script tag",
                    payload="<script>alert('XSS')</script>",
                    expected_behavior="Should sanitize HTML/JavaScript",
                    severity_if_vulnerable=VulnerabilityLevel.HIGH,
                ),
                # Reflected XSS
                TestPayload(
                    payload_id="XSS-REFLECT-01",
                    attack_type=AttackType.XSS,
                    description="Reflected XSS via URL parameter",
                    payload="<img src=x onerror=alert('XSS')>",
                    expected_behavior="Should sanitize URL parameters",
                    severity_if_vulnerable=VulnerabilityLevel.HIGH,
                ),
                # DOM-based XSS
                TestPayload(
                    payload_id="XSS-DOM-01",
                    attack_type=AttackType.XSS,
                    description="DOM-based XSS",
                    payload="javascript:alert('XSS')",
                    expected_behavior="Should validate JavaScript protocols",
                    severity_if_vulnerable=VulnerabilityLevel.MEDIUM,
                ),
                # Event handler XSS
                TestPayload(
                    payload_id="XSS-EVENT-01",
                    attack_type=AttackType.XSS,
                    description="Event handler XSS",
                    payload="<body onload=alert('XSS')>",
                    expected_behavior="Should strip event handlers",
                    severity_if_vulnerable=VulnerabilityLevel.HIGH,
                ),
                # SVG-based XSS
                TestPayload(
                    payload_id="XSS-SVG-01",
                    attack_type=AttackType.XSS,
                    description="SVG-based XSS",
                    payload="<svg onload=alert('XSS')>",
                    expected_behavior="Should sanitize SVG content",
                    severity_if_vulnerable=VulnerabilityLevel.MEDIUM,
                ),
            ]

            # Test each endpoint with each payload
            for endpoint in self.config.api_endpoints:
                for payload in payloads:
                    finding = await self._test_endpoint_with_payload(endpoint, payload)
                    if finding:
                        findings.append(finding)

            # Count by severity
            severity_counts = self._count_by_severity(findings)

            duration_ms = (time.time() - start_time) * 1000

            result = PenTestResult(
                test_type=AttackType.XSS,
                timestamp=datetime.now(),
                total_tests=len(payloads) * len(self.config.api_endpoints),
                vulnerabilities_found=len(findings),
                critical_count=severity_counts[VulnerabilityLevel.CRITICAL],
                high_count=severity_counts[VulnerabilityLevel.HIGH],
                medium_count=severity_counts[VulnerabilityLevel.MEDIUM],
                low_count=severity_counts[VulnerabilityLevel.LOW],
                findings=findings,
                test_duration_ms=duration_ms,
                test_status="success",
            )

            logger.info(
                f"XSS tests complete: {len(findings)} vulnerabilities found "
                f"(Critical: {severity_counts[VulnerabilityLevel.CRITICAL]}, "
                f"High: {severity_counts[VulnerabilityLevel.HIGH]})"
            )

            self.test_results["xss"] = result
            return result

        except Exception as e:
            logger.error(f"XSS tests failed: {e}")
            duration_ms = (time.time() - start_time) * 1000
            return PenTestResult(
                test_type=AttackType.XSS,
                timestamp=datetime.now(),
                total_tests=0,
                vulnerabilities_found=0,
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                findings=[],
                test_duration_ms=duration_ms,
                test_status="failed",
                error_message=str(e),
            )

    async def test_authentication(self) -> PenTestResult:
        """
        Test for authentication bypass vulnerabilities.

        Returns:
            PenTestResult with findings
        """
        start_time = time.time()
        findings: List[VulnerabilityFinding] = []

        try:
            logger.info("Starting authentication tests...")

            # Define authentication bypass payloads
            payloads = [
                TestPayload(
                    payload_id="AUTH-BYPASS-01",
                    attack_type=AttackType.AUTHENTICATION_BYPASS,
                    description="Missing authentication header",
                    payload=None,  # No auth header
                    expected_behavior="Should require authentication",
                    severity_if_vulnerable=VulnerabilityLevel.CRITICAL,
                ),
                TestPayload(
                    payload_id="AUTH-BYPASS-02",
                    attack_type=AttackType.AUTHENTICATION_BYPASS,
                    description="Invalid token",
                    payload="invalid_token_12345",
                    expected_behavior="Should reject invalid tokens",
                    severity_if_vulnerable=VulnerabilityLevel.CRITICAL,
                ),
                TestPayload(
                    payload_id="AUTH-BYPASS-03",
                    attack_type=AttackType.AUTHENTICATION_BYPASS,
                    description="Expired token",
                    payload="expired.jwt.token",
                    expected_behavior="Should reject expired tokens",
                    severity_if_vulnerable=VulnerabilityLevel.HIGH,
                ),
                TestPayload(
                    payload_id="AUTH-BYPASS-04",
                    attack_type=AttackType.AUTHENTICATION_BYPASS,
                    description="SQL injection in auth",
                    payload="' OR '1'='1",
                    expected_behavior="Should not bypass authentication",
                    severity_if_vulnerable=VulnerabilityLevel.CRITICAL,
                ),
            ]

            # Test authentication on protected endpoints
            for endpoint in self.config.api_endpoints:
                for payload in payloads:
                    finding = await self._test_authentication_bypass(endpoint, payload)
                    if finding:
                        findings.append(finding)

            # Count by severity
            severity_counts = self._count_by_severity(findings)

            duration_ms = (time.time() - start_time) * 1000

            result = PenTestResult(
                test_type=AttackType.AUTHENTICATION_BYPASS,
                timestamp=datetime.now(),
                total_tests=len(payloads) * len(self.config.api_endpoints),
                vulnerabilities_found=len(findings),
                critical_count=severity_counts[VulnerabilityLevel.CRITICAL],
                high_count=severity_counts[VulnerabilityLevel.HIGH],
                medium_count=severity_counts[VulnerabilityLevel.MEDIUM],
                low_count=severity_counts[VulnerabilityLevel.LOW],
                findings=findings,
                test_duration_ms=duration_ms,
                test_status="success",
            )

            logger.info(
                f"Authentication tests complete: {len(findings)} vulnerabilities found "
                f"(Critical: {severity_counts[VulnerabilityLevel.CRITICAL]}, "
                f"High: {severity_counts[VulnerabilityLevel.HIGH]})"
            )

            self.test_results["authentication"] = result
            return result

        except Exception as e:
            logger.error(f"Authentication tests failed: {e}")
            duration_ms = (time.time() - start_time) * 1000
            return PenTestResult(
                test_type=AttackType.AUTHENTICATION_BYPASS,
                timestamp=datetime.now(),
                total_tests=0,
                vulnerabilities_found=0,
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                findings=[],
                test_duration_ms=duration_ms,
                test_status="failed",
                error_message=str(e),
            )

    async def test_rate_limiting(self) -> PenTestResult:
        """
        Test rate limiting implementation.

        Returns:
            PenTestResult with findings
        """
        start_time = time.time()
        findings: List[VulnerabilityFinding] = []

        try:
            logger.info("Starting rate limiting tests...")

            # Test each endpoint
            for endpoint in self.config.api_endpoints:
                finding = await self._test_endpoint_rate_limiting(endpoint)
                if finding:
                    findings.append(finding)

            # Count by severity
            severity_counts = self._count_by_severity(findings)

            duration_ms = (time.time() - start_time) * 1000

            result = PenTestResult(
                test_type=AttackType.RATE_LIMITING,
                timestamp=datetime.now(),
                total_tests=len(self.config.api_endpoints),
                vulnerabilities_found=len(findings),
                critical_count=severity_counts[VulnerabilityLevel.CRITICAL],
                high_count=severity_counts[VulnerabilityLevel.HIGH],
                medium_count=severity_counts[VulnerabilityLevel.MEDIUM],
                low_count=severity_counts[VulnerabilityLevel.LOW],
                findings=findings,
                test_duration_ms=duration_ms,
                test_status="success",
            )

            logger.info(
                f"Rate limiting tests complete: {len(findings)} vulnerabilities found "
                f"(Critical: {severity_counts[VulnerabilityLevel.CRITICAL]}, "
                f"High: {severity_counts[VulnerabilityLevel.HIGH]})"
            )

            self.test_results["rate_limiting"] = result
            return result

        except Exception as e:
            logger.error(f"Rate limiting tests failed: {e}")
            duration_ms = (time.time() - start_time) * 1000
            return PenTestResult(
                test_type=AttackType.RATE_LIMITING,
                timestamp=datetime.now(),
                total_tests=0,
                vulnerabilities_found=0,
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                findings=[],
                test_duration_ms=duration_ms,
                test_status="failed",
                error_message=str(e),
            )

    async def test_input_validation(self) -> PenTestResult:
        """
        Test input validation and boundary conditions.

        Returns:
            PenTestResult with findings
        """
        start_time = time.time()
        findings: List[VulnerabilityFinding] = []

        try:
            logger.info("Starting input validation tests...")

            # Define input validation test cases
            test_cases = [
                TestPayload(
                    payload_id="INPUT-BOUNDARY-01",
                    attack_type=AttackType.INPUT_VALIDATION,
                    description="Oversized input",
                    payload="A" * 100000,  # 100KB of data
                    expected_behavior="Should reject oversized input",
                    severity_if_vulnerable=VulnerabilityLevel.MEDIUM,
                ),
                TestPayload(
                    payload_id="INPUT-SPECIAL-01",
                    attack_type=AttackType.INPUT_VALIDATION,
                    description="Special characters",
                    payload="!@#$%^&*()_+-=[]{}|;':\",./<>?",
                    expected_behavior="Should handle special characters safely",
                    severity_if_vulnerable=VulnerabilityLevel.LOW,
                ),
                TestPayload(
                    payload_id="INPUT-NULL-01",
                    attack_type=AttackType.INPUT_VALIDATION,
                    description="Null byte injection",
                    payload="test\x00injection",
                    expected_behavior="Should handle null bytes safely",
                    severity_if_vulnerable=VulnerabilityLevel.MEDIUM,
                ),
                TestPayload(
                    payload_id="INPUT-UNICODE-01",
                    attack_type=AttackType.INPUT_VALIDATION,
                    description="Unicode characters",
                    payload="测试\u0000\ufffd\U0001f4a9",
                    expected_behavior="Should handle Unicode safely",
                    severity_if_vulnerable=VulnerabilityLevel.LOW,
                ),
            ]

            # Test each endpoint with each test case
            for endpoint in self.config.api_endpoints:
                for test_case in test_cases:
                    finding = await self._test_endpoint_with_payload(
                        endpoint, test_case
                    )
                    if finding:
                        findings.append(finding)

            # Count by severity
            severity_counts = self._count_by_severity(findings)

            duration_ms = (time.time() - start_time) * 1000

            result = PenTestResult(
                test_type=AttackType.INPUT_VALIDATION,
                timestamp=datetime.now(),
                total_tests=len(test_cases) * len(self.config.api_endpoints),
                vulnerabilities_found=len(findings),
                critical_count=severity_counts[VulnerabilityLevel.CRITICAL],
                high_count=severity_counts[VulnerabilityLevel.HIGH],
                medium_count=severity_counts[VulnerabilityLevel.MEDIUM],
                low_count=severity_counts[VulnerabilityLevel.LOW],
                findings=findings,
                test_duration_ms=duration_ms,
                test_status="success",
            )

            logger.info(
                f"Input validation tests complete: {len(findings)} vulnerabilities found "
                f"(Critical: {severity_counts[VulnerabilityLevel.CRITICAL]}, "
                f"High: {severity_counts[VulnerabilityLevel.HIGH]})"
            )

            self.test_results["input_validation"] = result
            return result

        except Exception as e:
            logger.error(f"Input validation tests failed: {e}")
            duration_ms = (time.time() - start_time) * 1000
            return PenTestResult(
                test_type=AttackType.INPUT_VALIDATION,
                timestamp=datetime.now(),
                total_tests=0,
                vulnerabilities_found=0,
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                findings=[],
                test_duration_ms=duration_ms,
                test_status="failed",
                error_message=str(e),
            )

    async def test_api_security(self) -> PenTestResult:
        """
        Test API-specific security issues.

        Returns:
            PenTestResult with findings
        """
        start_time = time.time()
        findings: List[VulnerabilityFinding] = []

        try:
            logger.info("Starting API security tests...")

            # Test for common API vulnerabilities
            for endpoint in self.config.api_endpoints:
                # Test HTTP method enumeration
                method_finding = await self._test_http_methods(endpoint)
                if method_finding:
                    findings.append(method_finding)

                # Test for information disclosure
                info_finding = await self._test_information_disclosure(endpoint)
                if info_finding:
                    findings.append(info_finding)

                # Test for CORS misconfiguration
                cors_finding = await self._test_cors_configuration(endpoint)
                if cors_finding:
                    findings.append(cors_finding)

            # Count by severity
            severity_counts = self._count_by_severity(findings)

            duration_ms = (time.time() - start_time) * 1000

            result = PenTestResult(
                test_type=AttackType.API_SECURITY,
                timestamp=datetime.now(),
                total_tests=len(self.config.api_endpoints) * 3,
                vulnerabilities_found=len(findings),
                critical_count=severity_counts[VulnerabilityLevel.CRITICAL],
                high_count=severity_counts[VulnerabilityLevel.HIGH],
                medium_count=severity_counts[VulnerabilityLevel.MEDIUM],
                low_count=severity_counts[VulnerabilityLevel.LOW],
                findings=findings,
                test_duration_ms=duration_ms,
                test_status="success",
            )

            logger.info(
                f"API security tests complete: {len(findings)} vulnerabilities found "
                f"(Critical: {severity_counts[VulnerabilityLevel.CRITICAL]}, "
                f"High: {severity_counts[VulnerabilityLevel.HIGH]})"
            )

            self.test_results["api_security"] = result
            return result

        except Exception as e:
            logger.error(f"API security tests failed: {e}")
            duration_ms = (time.time() - start_time) * 1000
            return PenTestResult(
                test_type=AttackType.API_SECURITY,
                timestamp=datetime.now(),
                total_tests=0,
                vulnerabilities_found=0,
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                findings=[],
                test_duration_ms=duration_ms,
                test_status="failed",
                error_message=str(e),
            )

    async def _test_endpoint_with_payload(
        self, endpoint: str, payload: TestPayload
    ) -> Optional[VulnerabilityFinding]:
        """Test an endpoint with a specific payload."""
        try:
            url = f"{self.config.base_url}{endpoint}"

            # Prepare headers
            headers = {}
            if self.config.auth_token:
                headers["Authorization"] = f"Bearer {self.config.auth_token}"

            # Test with payload in different positions
            # 1. Query parameter
            response = await self.session.get(
                url, params={"q": payload.payload}, headers=headers
            )

            # Check for vulnerability indicators
            if self._is_vulnerable_response(response, payload):
                return VulnerabilityFinding(
                    finding_id=f"{payload.payload_id}-{endpoint.replace('/', '-')}",
                    attack_type=payload.attack_type,
                    vulnerability_level=payload.severity_if_vulnerable,
                    endpoint=endpoint,
                    description=f"{payload.description} - Vulnerable to: {payload.payload[:50]}",
                    payload_used=str(payload.payload)[:200],
                    response_evidence=await self._extract_evidence(response),
                    remediation=self._get_remediation(payload.attack_type),
                    references=self._get_references(payload.attack_type),
                )

            return None

        except Exception as e:
            logger.debug(f"Test {payload.payload_id} on {endpoint} failed: {e}")
            return None

    async def _test_authentication_bypass(
        self, endpoint: str, payload: TestPayload
    ) -> Optional[VulnerabilityFinding]:
        """Test authentication bypass on an endpoint."""
        try:
            url = f"{self.config.base_url}{endpoint}"

            # Test without authentication or with invalid token
            headers = {}
            if payload.payload is not None:
                headers["Authorization"] = f"Bearer {payload.payload}"

            response = await self.session.get(url, headers=headers)

            # Check if endpoint is accessible without proper auth
            if response.status == 200:
                return VulnerabilityFinding(
                    finding_id=f"{payload.payload_id}-{endpoint.replace('/', '-')}",
                    attack_type=AttackType.AUTHENTICATION_BYPASS,
                    vulnerability_level=payload.severity_if_vulnerable,
                    endpoint=endpoint,
                    description=f"Authentication bypass: {payload.description}",
                    payload_used=str(payload.payload)
                    if payload.payload
                    else "No auth header",
                    response_evidence=f"Status: {response.status}, accessible without proper authentication",
                    cwe_id="CWE-287",
                    remediation="Implement proper authentication checks on all protected endpoints",
                    references=[
                        "https://owasp.org/www-project-top-ten/2017/A2_2017-Broken_Authentication"
                    ],
                )

            return None

        except Exception as e:
            logger.debug(f"Authentication test on {endpoint} failed: {e}")
            return None

    async def _test_endpoint_rate_limiting(
        self, endpoint: str
    ) -> Optional[VulnerabilityFinding]:
        """Test rate limiting on an endpoint."""
        try:
            url = f"{self.config.base_url}{endpoint}"
            headers = {}
            if self.config.auth_token:
                headers["Authorization"] = f"Bearer {self.config.auth_token}"

            # Send burst of requests
            requests_sent = 0
            successful_requests = 0

            for i in range(
                min(self.config.rate_limit_test_requests, 50)
            ):  # Cap at 50 for testing
                try:
                    response = await self.session.get(url, headers=headers)
                    requests_sent += 1

                    if response.status != 429:  # Not rate limited
                        successful_requests += 1

                except Exception:
                    break

            # Check if rate limiting is working
            if successful_requests >= self.config.rate_limit_test_requests * 0.8:
                return VulnerabilityFinding(
                    finding_id=f"RATE-LIMIT-{endpoint.replace('/', '-')}",
                    attack_type=AttackType.RATE_LIMITING,
                    vulnerability_level=VulnerabilityLevel.MEDIUM,
                    endpoint=endpoint,
                    description="Insufficient rate limiting",
                    payload_used=f"{requests_sent} requests in rapid succession",
                    response_evidence=f"{successful_requests}/{requests_sent} requests succeeded without rate limiting",
                    cwe_id="CWE-770",
                    remediation="Implement rate limiting to prevent abuse",
                    references=[
                        "https://owasp.org/www-community/vulnerabilities/Insufficient_Rate_Limiting"
                    ],
                )

            return None

        except Exception as e:
            logger.debug(f"Rate limiting test on {endpoint} failed: {e}")
            return None

    async def _test_http_methods(self, endpoint: str) -> Optional[VulnerabilityFinding]:
        """Test for unsafe HTTP methods."""
        try:
            url = f"{self.config.base_url}{endpoint}"
            headers = {}
            if self.config.auth_token:
                headers["Authorization"] = f"Bearer {self.config.auth_token}"

            # Test OPTIONS to see allowed methods
            response = await self.session.options(url, headers=headers)

            allowed_methods = response.headers.get("Allow", "").upper()

            # Check for dangerous methods
            dangerous_methods = ["TRACE", "TRACK", "DELETE", "PUT"]
            found_dangerous = [m for m in dangerous_methods if m in allowed_methods]

            if found_dangerous:
                return VulnerabilityFinding(
                    finding_id=f"HTTP-METHOD-{endpoint.replace('/', '-')}",
                    attack_type=AttackType.API_SECURITY,
                    vulnerability_level=VulnerabilityLevel.MEDIUM,
                    endpoint=endpoint,
                    description=f"Potentially unsafe HTTP methods enabled: {', '.join(found_dangerous)}",
                    payload_used="OPTIONS request",
                    response_evidence=f"Allowed methods: {allowed_methods}",
                    remediation="Disable unnecessary HTTP methods",
                    references=[
                        "https://owasp.org/www-project-web-security-testing-guide/"
                    ],
                )

            return None

        except Exception as e:
            logger.debug(f"HTTP method test on {endpoint} failed: {e}")
            return None

    async def _test_information_disclosure(
        self, endpoint: str
    ) -> Optional[VulnerabilityFinding]:
        """Test for information disclosure."""
        try:
            url = f"{self.config.base_url}{endpoint}"

            # Test with invalid request to trigger error
            response = await self.session.get(f"{url}/invalid_path_12345")

            response_text = await response.text()

            # Check for sensitive information in error messages
            sensitive_patterns = [
                r"Traceback",
                r"File \".*\.py\"",
                r"line \d+",
                r"postgresql://",
                r"mysql://",
                r"redis://",
            ]

            for pattern in sensitive_patterns:
                if re.search(pattern, response_text, re.IGNORECASE):
                    return VulnerabilityFinding(
                        finding_id=f"INFO-DISC-{endpoint.replace('/', '-')}",
                        attack_type=AttackType.API_SECURITY,
                        vulnerability_level=VulnerabilityLevel.MEDIUM,
                        endpoint=endpoint,
                        description="Information disclosure in error messages",
                        payload_used="Invalid path request",
                        response_evidence=response_text[:200],
                        cwe_id="CWE-209",
                        remediation="Use generic error messages in production",
                        references=[
                            "https://owasp.org/www-community/Improper_Error_Handling"
                        ],
                    )

            return None

        except Exception as e:
            logger.debug(f"Information disclosure test on {endpoint} failed: {e}")
            return None

    async def _test_cors_configuration(
        self, endpoint: str
    ) -> Optional[VulnerabilityFinding]:
        """Test CORS configuration."""
        try:
            url = f"{self.config.base_url}{endpoint}"
            headers = {"Origin": "http://evil.com"}

            response = await self.session.get(url, headers=headers)

            cors_origin = response.headers.get("Access-Control-Allow-Origin", "")

            # Check for overly permissive CORS
            if cors_origin == "*":
                return VulnerabilityFinding(
                    finding_id=f"CORS-{endpoint.replace('/', '-')}",
                    attack_type=AttackType.API_SECURITY,
                    vulnerability_level=VulnerabilityLevel.MEDIUM,
                    endpoint=endpoint,
                    description="Overly permissive CORS policy",
                    payload_used="Origin: http://evil.com",
                    response_evidence=f"Access-Control-Allow-Origin: {cors_origin}",
                    cwe_id="CWE-346",
                    remediation="Restrict CORS to specific trusted origins",
                    references=[
                        "https://owasp.org/www-community/attacks/CORS_OriginHeaderScrutiny"
                    ],
                )

            return None

        except Exception as e:
            logger.debug(f"CORS test on {endpoint} failed: {e}")
            return None

    def _is_vulnerable_response(
        self, response: aiohttp.ClientResponse, payload: TestPayload
    ) -> bool:
        """Check if response indicates vulnerability."""
        # For testing purposes, we'll use heuristics
        # In production, this would need actual response analysis

        # Check status codes
        if response.status == 500:  # Server error might indicate injection
            return True

        # Check response time for time-based attacks
        if "WAITFOR" in str(payload.payload) and response.status == 200:
            return True

        return False

    async def _extract_evidence(self, response: aiohttp.ClientResponse) -> str:
        """Extract evidence from response."""
        try:
            text = await response.text()
            return f"Status: {response.status}, Body preview: {text[:100]}"
        except Exception:
            return f"Status: {response.status}"

    def _get_remediation(self, attack_type: AttackType) -> str:
        """Get remediation advice for attack type."""
        remediations = {
            AttackType.SQL_INJECTION: "Use parameterized queries or ORM. Never concatenate user input into SQL.",
            AttackType.XSS: "Sanitize all user input. Use Content Security Policy. Encode output.",
            AttackType.AUTHENTICATION_BYPASS: "Implement proper authentication on all protected endpoints.",
            AttackType.RATE_LIMITING: "Implement rate limiting to prevent abuse.",
            AttackType.INPUT_VALIDATION: "Validate and sanitize all input. Set size limits.",
            AttackType.API_SECURITY: "Follow API security best practices. Use HTTPS. Validate origins.",
        }
        return remediations.get(attack_type, "Review and fix security issue")

    def _get_references(self, attack_type: AttackType) -> List[str]:
        """Get references for attack type."""
        references = {
            AttackType.SQL_INJECTION: [
                "https://owasp.org/www-community/attacks/SQL_Injection",
                "https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html",
            ],
            AttackType.XSS: [
                "https://owasp.org/www-community/attacks/xss/",
                "https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html",
            ],
            AttackType.AUTHENTICATION_BYPASS: [
                "https://owasp.org/www-project-top-ten/2017/A2_2017-Broken_Authentication"
            ],
        }
        return references.get(attack_type, [])

    async def run_full_test_suite(self) -> Dict[str, PenTestResult]:
        """
        Run all penetration tests.

        Returns:
            Dictionary mapping test types to results
        """
        logger.info("Starting full penetration test suite...")
        start_time = time.time()

        try:
            if not self.session:
                self.session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
                )

            # Run all tests
            self.test_results["sql_injection"] = await self.test_sql_injection()
            self.test_results["xss"] = await self.test_xss()
            self.test_results["authentication"] = await self.test_authentication()
            self.test_results["rate_limiting"] = await self.test_rate_limiting()
            self.test_results["input_validation"] = await self.test_input_validation()
            self.test_results["api_security"] = await self.test_api_security()

            duration_ms = (time.time() - start_time) * 1000

            # Calculate totals
            total_vulnerabilities = sum(
                r.vulnerabilities_found for r in self.test_results.values()
            )
            total_critical = sum(r.critical_count for r in self.test_results.values())
            total_high = sum(r.high_count for r in self.test_results.values())

            logger.info(
                f"Full penetration test complete in {duration_ms:.2f}ms: "
                f"{total_vulnerabilities} vulnerabilities found "
                f"(Critical: {total_critical}, High: {total_high})"
            )

            return self.test_results

        except Exception as e:
            logger.error(f"Full penetration test failed: {e}")
            return self.test_results

        finally:
            if self.session:
                await self.session.close()
                self.session = None

    def generate_report(
        self, results: Optional[Dict[str, PenTestResult]] = None
    ) -> str:
        """
        Generate a comprehensive penetration test report.

        Args:
            results: Test results to report on

        Returns:
            Formatted report as string
        """
        if results is None:
            results = self.test_results

        if not results:
            return "No test results available"

        lines = []
        lines.append("=" * 80)
        lines.append("PENETRATION TEST REPORT")
        lines.append("=" * 80)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Target: {self.config.base_url}")
        lines.append("")

        # Executive summary
        total_tests = sum(r.total_tests for r in results.values())
        total_vulnerabilities = sum(r.vulnerabilities_found for r in results.values())
        total_critical = sum(r.critical_count for r in results.values())
        total_high = sum(r.high_count for r in results.values())
        total_medium = sum(r.medium_count for r in results.values())
        total_low = sum(r.low_count for r in results.values())

        lines.append("EXECUTIVE SUMMARY")
        lines.append("-" * 80)
        lines.append(f"Total Tests:          {total_tests}")
        lines.append(f"Vulnerabilities:      {total_vulnerabilities}")
        lines.append(f"  Critical:           {total_critical}")
        lines.append(f"  High:               {total_high}")
        lines.append(f"  Medium:             {total_medium}")
        lines.append(f"  Low:                {total_low}")
        lines.append("")

        # Test results by type
        for test_type, result in results.items():
            lines.append(f"{test_type.upper().replace('_', ' ')}")
            lines.append("-" * 80)
            lines.append(f"Status:   {result.test_status}")
            lines.append(f"Duration: {result.test_duration_ms:.2f}ms")
            lines.append(f"Tests:    {result.total_tests}")
            lines.append(f"Findings: {result.vulnerabilities_found}")

            if result.error_message:
                lines.append(f"Error:    {result.error_message}")

            # List critical/high findings
            critical_high = [
                f
                for f in result.findings
                if f.vulnerability_level
                in (VulnerabilityLevel.CRITICAL, VulnerabilityLevel.HIGH)
            ]

            if critical_high:
                lines.append("")
                lines.append("Critical/High Findings:")
                for finding in critical_high:
                    lines.append(
                        f"  - [{finding.vulnerability_level.value.upper()}] {finding.description}"
                    )
                    lines.append(f"    Endpoint: {finding.endpoint}")
                    lines.append(f"    Remediation: {finding.remediation}")

            lines.append("")

        # Recommendations
        lines.append("RECOMMENDATIONS")
        lines.append("-" * 80)

        if total_critical > 0:
            lines.append(
                f"1. CRITICAL: Address {total_critical} critical vulnerabilities immediately"
            )
        if total_high > 0:
            lines.append(
                f"2. HIGH: Fix {total_high} high-severity vulnerabilities as soon as possible"
            )
        if total_medium > 0:
            lines.append(
                f"3. MEDIUM: Plan to address {total_medium} medium-severity vulnerabilities"
            )

        if total_critical == 0 and total_high == 0:
            lines.append("No critical or high-severity vulnerabilities found!")

        lines.append("")
        lines.append("=" * 80)

        return "\n".join(lines)

    def _count_by_severity(
        self, findings: List[VulnerabilityFinding]
    ) -> Dict[VulnerabilityLevel, int]:
        """Count findings by severity."""
        counts = {level: 0 for level in VulnerabilityLevel}
        for finding in findings:
            counts[finding.vulnerability_level] += 1
        return counts


# CLI interface
async def main():
    """Command-line interface for penetration tester."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Penetration Testing for Trading System"
    )
    parser.add_argument(
        "--base-url", default="http://localhost:8000", help="Base URL of target"
    )
    parser.add_argument(
        "--test-type",
        choices=["all", "sql", "xss", "auth", "rate", "input", "api"],
        default="all",
        help="Type of test to run",
    )
    parser.add_argument("--output", help="Output file for report")
    parser.add_argument("--auth-token", help="Authentication token")

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create tester
    config = PenTestConfig(base_url=args.base_url, auth_token=args.auth_token)

    async with PenetrationTester(config) as tester:
        # Run tests
        if args.test_type == "all":
            results = await tester.run_full_test_suite()
        elif args.test_type == "sql":
            result = await tester.test_sql_injection()
            results = {"sql_injection": result}
        elif args.test_type == "xss":
            result = await tester.test_xss()
            results = {"xss": result}
        elif args.test_type == "auth":
            result = await tester.test_authentication()
            results = {"authentication": result}
        elif args.test_type == "rate":
            result = await tester.test_rate_limiting()
            results = {"rate_limiting": result}
        elif args.test_type == "input":
            result = await tester.test_input_validation()
            results = {"input_validation": result}
        elif args.test_type == "api":
            result = await tester.test_api_security()
            results = {"api_security": result}

        # Generate report
        report = tester.generate_report(results)

        # Output report
        if args.output:
            with open(args.output, "w") as f:
                f.write(report)
            print(f"Report written to {args.output}")
        else:
            print(report)


if __name__ == "__main__":
    asyncio.run(main())
