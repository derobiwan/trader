#!/usr/bin/env python3
"""
Script to convert float literals to Decimal in test files for type consistency.
Fixes ~50 failing tests related to Decimal/float type mismatches.
"""

import re
from pathlib import Path


def convert_float_to_decimal(content: str) -> str:
    """Convert float literals to Decimal("...") format."""

    # Pattern 1: Dictionary values like "quantity": 0.1,
    # Replace with "quantity": Decimal("0.1"),
    content = re.sub(
        r'("(?:quantity|price|fees|pnl|contracts)"\s*:\s*)(-?\d+\.?\d*)',
        r'\1Decimal("\2")',
        content,
    )

    # Pattern 2: Function call arguments with floats
    # Replace quantity=0.1 with quantity=Decimal("0.1")
    content = re.sub(
        r"\b(quantity|price|fees|pnl|contracts)=(-?\d+\.?\d*)\b",
        r'\1=Decimal("\2")',
        content,
    )

    # Pattern 3: Assert comparisons with floats
    # Replace == 95.0 with == Decimal("95.0")
    content = re.sub(
        r"(==|!=)\s*(-?\d+\.\d+)(?!\d)",
        lambda m: f'{m.group(1)} Decimal("{m.group(2)}")',
        content,
    )

    # Pattern 4: Already wrapped decimals - clean up double wrapping
    content = re.sub(r'Decimal\("Decimal\(\\"(.+?)\\"\)"\)', r'Decimal("\1")', content)
    content = re.sub(r'Decimal\(Decimal\("(.+?)"\)\)', r'Decimal("\1")', content)

    return content


def process_file(filepath: Path) -> tuple[int, int]:
    """Process a test file and convert floats to Decimal."""
    print(f"Processing {filepath}...")

    with open(filepath, "r") as f:
        original_content = f.read()

    # Convert floats to Decimal
    new_content = convert_float_to_decimal(original_content)

    # Count changes
    original_lines = original_content.splitlines()
    new_lines = new_content.splitlines()

    changes = sum(1 for old, new in zip(original_lines, new_lines) if old != new)

    if changes > 0:
        with open(filepath, "w") as f:
            f.write(new_content)
        print(f"  ✓ Made {changes} changes")
    else:
        print("  - No changes needed")

    return changes, len(original_lines)


def main():
    """Main execution function."""
    workspace_dir = Path(__file__).parent / "workspace" / "tests" / "unit"

    test_files = [
        workspace_dir / "test_performance_tracker.py",
        workspace_dir / "test_reconciliation.py",
        workspace_dir / "test_paper_executor.py",
    ]

    total_changes = 0
    total_lines = 0

    for test_file in test_files:
        if test_file.exists():
            changes, lines = process_file(test_file)
            total_changes += changes
            total_lines += lines
        else:
            print(f"⚠️  File not found: {test_file}")

    print(f"\n{'=' * 60}")
    print(f"Total: {total_changes} changes across {total_lines} lines")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
