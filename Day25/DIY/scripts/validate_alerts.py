#!/usr/bin/env python3
"""
Validate the three alert rules against Day25 principles.

Usage:
    uv run python scripts/validate_alerts.py
"""

from app.alert_rules import ALL_ALERTS
from app.validator import AlertValidator, print_validation_report


def main():
    """Run validation on all alerts."""
    print("\nValidating alert rules against Day25 principles...")
    print("(See Day25/Day25.md for context: 'What makes a good alert?')\n")

    results = AlertValidator.validate_all(ALL_ALERTS)
    print_validation_report(results)


if __name__ == "__main__":
    main()
