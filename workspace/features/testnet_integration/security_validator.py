"""
Security Validator

Validates API keys, scans for secrets, and provides security utilities
for testnet integration.

Author: Security Auditor
Date: 2025-10-31
"""

import re
import logging
from typing import List, Tuple, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class SecurityValidator:
    """
    Security validation and scanning utilities

    Provides:
    - API key format validation
    - Secret scanning in code
    - Sensitive data sanitization
    - Configuration security checks
    """

    # Patterns for different API key formats
    API_KEY_PATTERNS = {
        "binance": r"^[A-Za-z0-9]{64}$",
        "bybit": r"^[A-Za-z0-9\-]{36}$",  # UUID format
        "generic": r"^[A-Za-z0-9\-_]{20,}$",
    }

    # Patterns for detecting potential secrets
    SECRET_PATTERNS = [
        (r"[A-Za-z0-9]{64}", "Potential Binance API key"),
        (r"[A-Za-z0-9\-]{36}", "Potential UUID/Bybit key"),
        (
            r'(api[_-]?key|api[_-]?secret|password|token|secret)\s*=\s*["\'][^"\']{10,}["\']',
            "Hardcoded credential",
        ),
        (r"(Bearer|Basic)\s+[A-Za-z0-9+/=]{20,}", "Authorization header"),
        (r"-----BEGIN (RSA |EC )?PRIVATE KEY-----", "Private key"),
    ]

    # Files to exclude from scanning
    EXCLUDE_PATTERNS = [
        ".git",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        "venv",
        ".env.example",
        "*.test.py",
        "*.spec.py",
        "test_*.py",
    ]

    @classmethod
    def validate_api_key(cls, key: str, exchange: str) -> bool:
        """
        Validate API key format for specific exchange

        Args:
            key: API key to validate
            exchange: Exchange name (binance, bybit)

        Returns:
            True if key format is valid

        Raises:
            ValueError: If exchange is not supported
        """
        if not key:
            logger.warning("Empty API key provided")
            return False

        pattern = cls.API_KEY_PATTERNS.get(exchange.lower())
        if not pattern:
            raise ValueError(f"Unsupported exchange: {exchange}")

        is_valid = bool(re.match(pattern, key))

        if not is_valid:
            logger.warning(
                f"Invalid {exchange} API key format. "
                f"Expected pattern: {pattern}, Got length: {len(key)}"
            )

        return is_valid

    @classmethod
    def validate_api_secret(cls, secret: str) -> bool:
        """
        Validate API secret (basic validation)

        Args:
            secret: API secret to validate

        Returns:
            True if secret appears valid
        """
        if not secret:
            logger.warning("Empty API secret provided")
            return False

        # Basic checks
        if len(secret) < 10:
            logger.warning("API secret too short")
            return False

        # Check for common placeholder values
        placeholders = ["your_secret_here", "changeme", "password", "secret"]
        if any(placeholder in secret.lower() for placeholder in placeholders):
            logger.warning("API secret appears to be a placeholder")
            return False

        return True

    @classmethod
    def scan_for_secrets(
        cls, directory: str, exclude_patterns: Optional[List[str]] = None
    ) -> List[Tuple[str, int, str]]:
        """
        Scan directory for potential secrets

        Args:
            directory: Directory path to scan
            exclude_patterns: Additional patterns to exclude

        Returns:
            List of (filepath, line_number, description) tuples

        Raises:
            ValueError: If directory doesn't exist
        """
        directory_path = Path(directory)
        if not directory_path.exists():
            raise ValueError(f"Directory does not exist: {directory}")

        findings = []
        exclude = cls.EXCLUDE_PATTERNS + (exclude_patterns or [])

        for file_path in directory_path.rglob("*"):
            # Skip excluded paths
            if any(cls._matches_pattern(file_path, pattern) for pattern in exclude):
                continue

            # Only scan text files
            if file_path.is_file() and cls._is_text_file(file_path):
                file_findings = cls._scan_file(file_path)
                findings.extend(file_findings)

        return findings

    @classmethod
    def _scan_file(cls, file_path: Path) -> List[Tuple[str, int, str]]:
        """
        Scan a single file for secrets

        Args:
            file_path: Path to file

        Returns:
            List of findings
        """
        findings = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                for line_num, line in enumerate(f, 1):
                    for pattern, description in cls.SECRET_PATTERNS:
                        if re.search(pattern, line, re.IGNORECASE):
                            # Additional context check
                            if not cls._is_false_positive(line, file_path):
                                findings.append((str(file_path), line_num, description))

        except Exception as e:
            logger.debug(f"Could not scan {file_path}: {e}")

        return findings

    @classmethod
    def _is_false_positive(cls, line: str, file_path: Path) -> bool:
        """
        Check if a finding is likely a false positive

        Args:
            line: Line containing potential secret
            file_path: Path to file

        Returns:
            True if likely false positive
        """
        # Check for comments
        if line.strip().startswith(("#", "//", "/*", "*")):
            return True

        # Check for example/test files
        if any(
            x in str(file_path).lower() for x in ["example", "test", "mock", "fixture"]
        ):
            return True

        # Check for documentation
        if file_path.suffix in [".md", ".rst", ".txt"]:
            return True

        # Check for common false positive patterns
        false_positive_patterns = [
            r"\.env\.example",
            r"placeholder",
            r"your_.*_here",
            r"<.*>",  # Template variables
            r"\$\{.*\}",  # Environment variables
        ]

        return any(
            re.search(pattern, line, re.IGNORECASE)
            for pattern in false_positive_patterns
        )

    @classmethod
    def _matches_pattern(cls, path: Path, pattern: str) -> bool:
        """
        Check if path matches pattern

        Args:
            path: Path to check
            pattern: Pattern to match

        Returns:
            True if matches
        """
        path_str = str(path)

        # Handle glob patterns
        if "*" in pattern:
            import fnmatch

            return fnmatch.fnmatch(path_str, pattern)

        # Handle directory/file names
        return pattern in path_str

    @classmethod
    def _is_text_file(cls, file_path: Path) -> bool:
        """
        Check if file is a text file

        Args:
            file_path: Path to file

        Returns:
            True if text file
        """
        text_extensions = [
            ".py",
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            ".java",
            ".c",
            ".cpp",
            ".h",
            ".hpp",
            ".go",
            ".rs",
            ".rb",
            ".php",
            ".yaml",
            ".yml",
            ".json",
            ".xml",
            ".env",
            ".ini",
            ".conf",
            ".config",
            ".sh",
            ".bash",
            ".zsh",
            ".md",
            ".rst",
            ".txt",
        ]

        return file_path.suffix.lower() in text_extensions

    @classmethod
    def sanitize_for_logs(cls, value: str, value_type: str = "api_key") -> str:
        """
        Sanitize sensitive values for safe logging

        Args:
            value: Value to sanitize
            value_type: Type of value (api_key, secret, password)

        Returns:
            Sanitized string safe for logging
        """
        if not value:
            return "[EMPTY]"

        if value_type == "api_key":
            # Show first 4 and last 4 characters
            if len(value) > 8:
                return f"{value[:4]}...{value[-4:]}"
            else:
                return "[REDACTED]"

        elif value_type == "secret" or value_type == "password":
            # Never show any part of secrets
            return f"[{value_type.upper()}]"

        else:
            # Default: show length only
            return f"[REDACTED:{len(value)}]"

    @classmethod
    def validate_configuration(cls, config: Dict[str, Any]) -> List[str]:
        """
        Validate configuration for security issues

        Args:
            config: Configuration dictionary

        Returns:
            List of security warnings
        """
        warnings = []

        # Check for hardcoded credentials
        for key, value in config.items():
            if isinstance(value, str):
                # Check for credential-like keys
                if any(
                    x in key.lower() for x in ["key", "secret", "password", "token"]
                ):
                    # Check if value looks like a real credential (not placeholder)
                    if len(value) > 20 and not any(
                        x in value.lower() for x in ["your_", "changeme", "example"]
                    ):
                        warnings.append(
                            f"Possible hardcoded credential in config: {key}"
                        )

        # Check for insecure settings
        if config.get("ssl_verify") is False:
            warnings.append("SSL verification is disabled")

        if config.get("debug") is True:
            warnings.append("Debug mode is enabled (may expose sensitive data)")

        if config.get("allow_all_origins") is True:
            warnings.append("CORS allows all origins (security risk)")

        return warnings

    @classmethod
    def generate_security_report(
        cls, directory: str, config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive security report

        Args:
            directory: Directory to scan
            config: Optional configuration to validate

        Returns:
            Security report dictionary
        """
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "directory": directory,
            "findings": [],
            "config_warnings": [],
            "summary": {},
        }

        # Scan for secrets
        try:
            findings = cls.scan_for_secrets(directory)
            report["findings"] = [
                {
                    "file": f[0],
                    "line": f[1],
                    "type": f[2],
                }
                for f in findings
            ]
        except Exception as e:
            report["scan_error"] = str(e)

        # Validate configuration
        if config:
            report["config_warnings"] = cls.validate_configuration(config)

        # Generate summary
        report["summary"] = {
            "total_findings": len(report["findings"]),
            "critical": sum(
                1 for f in report["findings"] if "key" in f["type"].lower()
            ),
            "warnings": len(report["config_warnings"]),
            "status": "PASS" if len(report["findings"]) == 0 else "FAIL",
        }

        return report
