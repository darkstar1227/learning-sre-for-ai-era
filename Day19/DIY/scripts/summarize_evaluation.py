#!/usr/bin/env python
"""Summarize evaluation results.

Usage:
    uv run python scripts/summarize_evaluation.py \\
      --input artifacts/policy_task_v1.jsonl

Reads evaluation JSONL and prints human-readable summary matching
the format from Day19 article Step 5.
"""

import argparse
import json
import sys
from pathlib import Path
from collections import defaultdict


def main():
    parser = argparse.ArgumentParser(
        description="Summarize evaluation results"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("artifacts/policy_task_v1.jsonl"),
        help="Path to evaluation results JSONL file",
    )

    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    # Read and aggregate results
    results = []
    try:
        with open(args.input, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    result = json.loads(line)
                    results.append(result)
                except json.JSONDecodeError as e:
                    print(f"Warning: Invalid JSON line: {e}", file=sys.stderr)
    except IOError as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)

    if not results:
        print("No results to summarize", file=sys.stderr)
        sys.exit(1)

    # Aggregate statistics
    dataset_version = results[0].get("dataset_version", "unknown")
    workflow_version = results[0].get("workflow_version", "unknown")
    workflow_name = results[0].get("workflow_name", "unknown")

    completed_cases = sum(1 for r in results if r.get("technical_status") == "completed")
    technical_failures = len(results) - completed_cases

    # Count outcomes
    outcome_counts = defaultdict(int)
    for result in results:
        outcome = result.get("actual_outcome", "unknown")
        outcome_counts[outcome] += 1

    # Count quality status
    quality_counts = defaultdict(int)
    for result in results:
        quality = result.get("quality_status", "unknown")
        quality_counts[quality] += 1

    # Count by risk level
    risk_counts = defaultdict(int)
    for result in results:
        risk = result.get("case_risk", "unknown")
        risk_counts[risk] += 1

    # Count pass/fail
    pass_count = sum(
        1 for r in results
        if r.get("outcome_matches") and
           r.get("citation_valid") and
           not r.get("missing_required_facts", [])
    )
    fail_count = len(results) - pass_count

    # Print summary
    print()
    print("=" * 60)
    print("Evaluation Summary")
    print("=" * 60)
    print()
    print(f"dataset_version={dataset_version}")
    print(f"workflow_version={workflow_version}")
    print(f"workflow_name={workflow_name}")
    print()

    print(f"completed_cases={completed_cases}")
    print(f"technical_failures={technical_failures}")
    print()

    print("Outcome Distribution:")
    for outcome in sorted(outcome_counts.keys()):
        count = outcome_counts[outcome]
        print(f"  {outcome}={count}")
    print()

    print("Quality Status Distribution:")
    for status in sorted(quality_counts.keys()):
        count = quality_counts[status]
        print(f"  {status}={count}")
    print()

    print("Risk Level Distribution:")
    for risk in sorted(risk_counts.keys()):
        count = risk_counts[risk]
        print(f"  {risk}={count}")
    print()

    print("Pass/Fail:")
    print(f"  pass={pass_count} / {len(results)}")
    print(f"  fail={fail_count} / {len(results)}")
    print()

    # Show failing cases
    failing_cases = [
        r for r in results
        if not (r.get("outcome_matches") and
                r.get("citation_valid") and
                not r.get("missing_required_facts", []))
    ]

    if failing_cases:
        print("Failing Cases:")
        for result in failing_cases:
            case_id = result.get("case_id")
            reasons = []

            if not result.get("outcome_matches"):
                reasons.append(f"outcome mismatch (expected {result.get('expected_outcome')}, got {result.get('actual_outcome')})")

            if not result.get("citation_valid"):
                reasons.append("invalid citation")

            missing = result.get("missing_required_facts", [])
            if missing:
                reasons.append(f"missing facts: {', '.join(missing)}")

            print(f"  {case_id}: {'; '.join(reasons)}")
        print()

    print("=" * 60)
    print()

    sys.exit(0)


if __name__ == "__main__":
    main()
