"""Golden dataset validator.

Validates JSONL dataset against schema and checks for:
- Schema compliance
- Version tracking
- Reviewer accountability
- Citation verification (when available)
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

from app.schemas import GoldenDatasetEntry


def validate_dataset(
    dataset_path: Path,
    verbose: bool = False,
) -> dict:
    """Validate a golden dataset JSONL file.

    Args:
        dataset_path: Path to golden.jsonl
        verbose: Print detailed validation info

    Returns:
        Summary dict with counts and any errors
    """
    summary = {
        "total": 0,
        "valid": 0,
        "invalid": 0,
        "by_status": {},
        "reviewed_by": {},
        "errors": [],
    }

    if not dataset_path.exists():
        summary["errors"].append(f"File not found: {dataset_path}")
        return summary

    try:
        with open(dataset_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                summary["total"] += 1

                if not line.strip():
                    summary["errors"].append(f"Line {line_num}: Empty line")
                    summary["invalid"] += 1
                    continue

                try:
                    raw_data = json.loads(line)
                    entry = GoldenDatasetEntry(**raw_data)
                    summary["valid"] += 1

                    # Track by status
                    status = entry.expected_status
                    summary["by_status"][status] = summary["by_status"].get(status, 0) + 1

                    # Track reviewers
                    reviewer = entry.reviewed_by
                    summary["reviewed_by"][reviewer] = summary["reviewed_by"].get(reviewer, 0) + 1

                    if verbose:
                        print(f"✓ Line {line_num}: {entry.id} ({status})")

                except json.JSONDecodeError as e:
                    summary["errors"].append(f"Line {line_num}: Invalid JSON - {e}")
                    summary["invalid"] += 1
                except ValidationError as e:
                    summary["errors"].append(
                        f"Line {line_num}: Schema validation failed - {e.error_count()} error(s)"
                    )
                    summary["invalid"] += 1
                    if verbose:
                        print(f"  Details: {e}")

    except IOError as e:
        summary["errors"].append(f"Cannot read file: {e}")

    return summary


def print_summary(summary: dict) -> None:
    """Print validation summary in human-readable format."""
    print("\n" + "=" * 60)
    print("Golden Dataset Validation Summary")
    print("=" * 60)
    print(f"Total entries: {summary['total']}")
    print(f"Valid: {summary['valid']}")
    print(f"Invalid: {summary['invalid']}")

    if summary["valid"] > 0:
        print("\nBreakdown by status:")
        for status, count in sorted(summary["by_status"].items()):
            print(f"  - {status}: {count}")

        print("\nReviewers:")
        for reviewer, count in sorted(summary["reviewed_by"].items()):
            print(f"  - {reviewer}: {count} cases")

    if summary["errors"]:
        print(f"\nErrors ({len(summary['errors'])}):")
        for error in summary["errors"][:10]:  # Show first 10
            print(f"  - {error}")
        if len(summary["errors"]) > 10:
            print(f"  ... and {len(summary['errors']) - 10} more")

    print("=" * 60 + "\n")
