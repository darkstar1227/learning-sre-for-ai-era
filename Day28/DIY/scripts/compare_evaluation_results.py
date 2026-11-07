"""
Script to compare baseline vs candidate evaluation results.
Corresponds to Day28.md section ④ (Step 3-5: baseline table & promotion conditions).
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Tuple


def load_evaluation_results(file_path: str) -> Dict[str, Any]:
    """Load evaluation results from JSON file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Evaluation results file not found: {file_path}")

    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def check_promotion_gates(results: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Check if evaluation results meet promotion gates.
    Corresponds to Day28.md section ④ (step 5: 宣告 promotion 條件).

    Returns:
        (all_gates_passed: bool, failures: list of gate failure descriptions)
    """
    failures = []

    # Check each gate
    gates = results.get("gate_results", {})

    for gate_name, gate_result in gates.items():
        if not gate_result.get("passed", False):
            failures.append(
                f"Gate '{gate_name}' failed: "
                f"requirement={gate_result.get('requirement')}, "
                f"actual={gate_result.get('actual')}"
            )

    return len(failures) == 0, failures


def compare_with_baseline(results: Dict[str, Any]) -> str:
    """
    Generate comparison report with baseline.

    Returns:
        Formatted comparison report
    """
    report = []
    report.append("\n" + "="*70)
    report.append("Baseline vs Candidate Comparison")
    report.append("="*70)

    change_id = results.get("change_id", "unknown")
    dataset_version = results.get("dataset_version", "unknown")

    report.append(f"\nCandidate: {change_id}")
    report.append(f"Dataset: {dataset_version}")

    # Metrics
    report.append("\n📊 Key Metrics:")
    metrics = results.get("metrics", {})
    for metric_name, value in metrics.items():
        report.append(f"  {metric_name}: {value}")

    # Baseline comparison
    report.append("\n📈 Delta vs Baseline:")
    baseline_cmp = results.get("baseline_comparison", {})
    if baseline_cmp:
        baseline_id = baseline_cmp.get("baseline_id", "unknown")
        report.append(f"  Baseline: {baseline_id}")

        for metric_name, delta in baseline_cmp.items():
            if metric_name != "baseline_id":
                direction = "+" if delta > 0 else ""
                report.append(f"    {metric_name}: {direction}{delta}")

    # Gate checks
    report.append("\n🚪 Promotion Gates:")
    gates = results.get("gate_results", {})
    for gate_name, gate_result in gates.items():
        status = "✓" if gate_result.get("passed") else "✗"
        report.append(
            f"  {status} {gate_name}: "
            f"{gate_result.get('actual')} (requirement: {gate_result.get('requirement')})"
        )

    # Failed cases
    failed_cases = results.get("failed_case_ids", [])
    if failed_cases:
        report.append(f"\n❌ Failed Cases ({len(failed_cases)}):")
        for case_id in failed_cases[:5]:  # Show first 5
            report.append(f"  - {case_id}")
        if len(failed_cases) > 5:
            report.append(f"  ... and {len(failed_cases) - 5} more")

    return "\n".join(report)


def make_promotion_decision(results: Dict[str, Any]) -> str:
    """
    Make a promotion decision based on evaluation results.
    Corresponds to Day28.md section ④ (step 7: gate failure handling).

    Returns:
        Decision rationale
    """
    all_passed, failures = check_promotion_gates(results)

    decision = []
    decision.append("\n" + "="*70)
    decision.append("Promotion Decision")
    decision.append("="*70)

    if all_passed:
        decision.append("\n✓ DECISION: APPROVE for next stage")
        decision.append("  All gates passed. Safe to promote to next canary stage.")
    else:
        decision.append("\n✗ DECISION: BLOCK promotion")
        decision.append("  The following gates failed:")
        for failure in failures:
            decision.append(f"    - {failure}")

        change_id = results.get("change_id")
        decision.append(f"\n  Rollback target: Check manifest for {change_id}")
        decision.append("  Action: Halt promotion, investigate failures, consider rollback")

    return "\n".join(decision)


def print_baseline_table():
    """
    Print an example baseline table for manual evaluation.
    Corresponds to Day28.md section ④ (step 3: baseline 表).
    """
    print("\n" + "="*70)
    print("Example Baseline Evaluation Table")
    print("(Step 3: Do a small baseline table)")
    print("="*70)

    print("\n| case_id | input type | baseline expected | candidate expected | risk |")
    print("|---------|------------|------------------|-------------------|------|")
    print("| p-01    | normal     | can cite          | can cite           | citation loss |")
    print("| p-02    | insufficient data | honest refusal | honest refusal | hallucination |")
    print("| p-03    | false premise | correction | correction | false acceptance |")
    print("| p-04    | sensitive tool | reject/escalate | reject/escalate | overpermission |")

    print("\nThis table helps identify expected changes & risks BEFORE running evaluation.")
    print("Use it to guide what metrics & signals to watch during and after promotion.")


def main():
    """Run the evaluation comparison demo."""
    print("\n🚀 Day28 Evaluation Results Comparison Demo")
    print("Demonstrates how to evaluate changes & make promotion decisions")

    # Step 1: Show baseline table
    print_baseline_table()

    # Step 2: Load and analyze evaluation results
    eval_file = Path("manifests/evaluation-results.json")

    if not eval_file.exists():
        print(f"\n⚠️  {eval_file} not found. Creating example...")
        print("\nTo use this script with real evaluation results:")
        print(f"  1. Run evaluation on baseline & candidate versions")
        print(f"  2. Save results to {eval_file} in JSON format")
        print(f"  3. Run this script again")
        return

    results = load_evaluation_results(str(eval_file))

    # Step 3: Show comparison
    print(compare_with_baseline(results))

    # Step 4: Check gates
    print("\n" + "="*70)
    print("Gate Validation")
    print("="*70)

    all_passed, failures = check_promotion_gates(results)
    if all_passed:
        print("\n✓ All gates PASSED")
    else:
        print(f"\n✗ {len(failures)} gate(s) FAILED:")
        for failure in failures:
            print(f"  - {failure}")

    # Step 5: Make decision
    print(make_promotion_decision(results))

    print("\n" + "="*70)
    print("Next Steps")
    print("="*70)
    print("""
For this example:
  1. Review failed case (policy-042) - is it acceptable?
  2. If acceptable: approve with manual note
  3. If not: fix candidate & re-run evaluation
  4. If critical: prepare rollback card & rollback plan

Real-world process would involve:
  - Canary deployment with metadata tracking
  - Live SLI monitoring (error rate, latency, quality signals)
  - Automated rollback triggers
  - Post-incident analysis if things go wrong
    """)

    print("="*70 + "\n")


if __name__ == "__main__":
    main()
