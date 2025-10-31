#!/usr/bin/env python3
"""
Dependency Verification Script

Verifies that all required dependencies for the LLM Crypto Trading System
are properly installed and importable.

Usage:
    python scripts/verify-dependencies.py
    python scripts/verify-dependencies.py --verbose
"""

import sys
import importlib
from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class DependencyCheck:
    """Result of a dependency check."""

    category: str
    package: str
    import_name: str
    installed: bool
    version: str = ""
    error: str = ""


class DependencyVerifier:
    """Verifies Python dependencies are properly installed."""

    # Define critical dependencies by category
    DEPENDENCIES = {
        "Core Framework": [
            ("fastapi", "fastapi"),
            ("uvicorn", "uvicorn"),
            ("pydantic", "pydantic"),
        ],
        "Web & HTTP": [
            ("httpx", "httpx"),
            ("aiohttp", "aiohttp"),
            ("websockets", "websockets"),
        ],
        "Database": [
            ("sqlalchemy", "sqlalchemy"),
            ("alembic", "alembic"),
            ("asyncpg", "asyncpg"),
            ("psycopg2", "psycopg2"),
        ],
        "Cache & Queue": [
            ("redis", "redis"),
            ("celery", "celery"),
        ],
        "LLM Integration": [
            ("openai", "openai"),
            ("anthropic", "anthropic"),
            ("tiktoken", "tiktoken"),
        ],
        "Trading": [
            ("ccxt", "ccxt"),
            ("binance", "binance"),
        ],
        "Data Processing": [
            ("pandas", "pandas"),
            ("numpy", "numpy"),
            ("pandas_ta", "pandas_ta"),
            ("scipy", "scipy"),
        ],
        "Configuration": [
            ("dotenv", "dotenv"),
            ("yaml", "yaml"),
        ],
        "Monitoring": [
            ("prometheus_client", "prometheus_client"),
            ("pythonjsonlogger", "pythonjsonlogger"),
        ],
        "Utilities": [
            ("tenacity", "tenacity"),
            ("cachetools", "cachetools"),
            ("dateutil", "dateutil"),
            ("pytz", "pytz"),
        ],
        "Testing": [
            ("pytest", "pytest"),
        ],
        "Code Quality": [
            ("black", "black"),
            ("isort", "isort"),
            ("mypy", "mypy"),
        ],
    }

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: List[DependencyCheck] = []

    def check_import(
        self, package: str, import_name: str, category: str
    ) -> DependencyCheck:
        """Check if a package can be imported."""
        try:
            module = importlib.import_module(import_name)
            version = getattr(module, "__version__", "unknown")
            return DependencyCheck(
                category=category,
                package=package,
                import_name=import_name,
                installed=True,
                version=version,
            )
        except ImportError as e:
            return DependencyCheck(
                category=category,
                package=package,
                import_name=import_name,
                installed=False,
                error=str(e),
            )

    def verify_all(self) -> Tuple[int, int]:
        """Verify all dependencies."""
        total = 0
        successful = 0

        for category, packages in self.DEPENDENCIES.items():
            if self.verbose:
                print(f"\n{'=' * 60}")
                print(f"Category: {category}")
                print("=" * 60)

            for package, import_name in packages:
                total += 1
                result = self.check_import(package, import_name, category)
                self.results.append(result)

                if result.installed:
                    successful += 1
                    if self.verbose:
                        print(f"✓ {package:20s} v{result.version:15s} OK")
                else:
                    print(f"✗ {package:20s} FAILED: {result.error}")

        return successful, total

    def print_summary(self, successful: int, total: int):
        """Print verification summary."""
        print(f"\n{'=' * 60}")
        print("DEPENDENCY VERIFICATION SUMMARY")
        print("=" * 60)
        print(f"Total dependencies checked: {total}")
        print(f"Successfully imported: {successful}")
        print(f"Failed imports: {total - successful}")

        success_rate = (successful / total * 100) if total > 0 else 0
        print(f"Success rate: {success_rate:.1f}%")

        if successful == total:
            print("\n✓ All dependencies are properly installed!")
            return 0
        else:
            print("\n✗ Some dependencies are missing or failed to import.")
            print("\nTo install missing dependencies, run:")
            print("  pip install -r requirements.txt")
            return 1

    def print_category_breakdown(self):
        """Print breakdown by category."""
        print(f"\n{'=' * 60}")
        print("CATEGORY BREAKDOWN")
        print("=" * 60)

        categories = {}
        for result in self.results:
            if result.category not in categories:
                categories[result.category] = {"total": 0, "success": 0}
            categories[result.category]["total"] += 1
            if result.installed:
                categories[result.category]["success"] += 1

        for category, stats in sorted(categories.items()):
            total = stats["total"]
            success = stats["success"]
            rate = (success / total * 100) if total > 0 else 0
            status = "✓" if success == total else "✗"
            print(f"{status} {category:20s} {success:2d}/{total:2d} ({rate:5.1f}%)")

    def print_failed_imports(self):
        """Print detailed information about failed imports."""
        failed = [r for r in self.results if not r.installed]
        if not failed:
            return

        print(f"\n{'=' * 60}")
        print("FAILED IMPORTS DETAILS")
        print("=" * 60)

        for result in failed:
            print(f"\nPackage: {result.package}")
            print(f"Import name: {result.import_name}")
            print(f"Category: {result.category}")
            print(f"Error: {result.error}")
            print(f"Install command: pip install {result.package}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Verify LLM Crypto Trading System dependencies"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show detailed output for all dependencies",
    )
    parser.add_argument(
        "--breakdown", action="store_true", help="Show category breakdown"
    )
    parser.add_argument(
        "--failed-only", action="store_true", help="Show only failed imports"
    )

    args = parser.parse_args()

    print("LLM Crypto Trading System - Dependency Verification")
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")

    verifier = DependencyVerifier(verbose=args.verbose)
    successful, total = verifier.verify_all()

    if args.breakdown:
        verifier.print_category_breakdown()

    if args.failed_only or not args.verbose:
        verifier.print_failed_imports()

    exit_code = verifier.print_summary(successful, total)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
