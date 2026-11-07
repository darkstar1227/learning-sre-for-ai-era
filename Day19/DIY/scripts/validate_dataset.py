#!/usr/bin/env python
"""Validate golden dataset JSONL file.

Usage:
    uv run python scripts/validate_dataset.py [path_to_golden.jsonl]
"""

import sys
from pathlib import Path

from app.validator import validate_dataset, print_summary


def main():
    # Default to golden.jsonl in project root
    dataset_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("golden.jsonl")

    print(f"Validating: {dataset_path.absolute()}")

    summary = validate_dataset(dataset_path, verbose=True)
    print_summary(summary)

    # Exit with error code if validation failed
    if summary["invalid"] > 0:
        sys.exit(1)

    if summary["total"] == 0:
        print("Warning: Dataset is empty")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
