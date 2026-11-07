#!/usr/bin/env python3
"""
Entry point to validate Day10 failure_analysis.md document.

Usage:
  uv run python scripts/validate_analysis.py
"""

from pathlib import Path
import sys

# Add parent directory to path so we can import app module
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.validator import FailureAnalysisValidator


def main():
    analysis_file = Path(__file__).parent.parent / "failure_analysis.md"

    validator = FailureAnalysisValidator(analysis_file)
    is_valid = validator.run_all_checks()

    print(validator.report())

    return 0 if is_valid else 1


if __name__ == "__main__":
    sys.exit(main())
