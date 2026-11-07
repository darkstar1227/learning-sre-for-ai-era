#!/usr/bin/env python3
"""
Demo: Run workflows and show LangSmith trace structure.

This script demonstrates:
1. How workflows are structured with @traceable
2. What metadata and IDs are recorded
3. How to inspect evaluation results
"""

import os
import sys
import json
from typing import Any

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.workflows import answer_workflow
from app.dataset import create_regression_dataset, get_example_by_id, dataset_statistics
from app.evaluator import (
    evaluate_example,
    make_release_decision,
    classify_failure,
    EvaluationResult,
)


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def demo_workflow():
    """Demo 1: Run a workflow with LangSmith tracing."""
    print_section("Demo 1: Running Workflow with Tracing")

    # Note: If LANGSMITH_TRACING=true and LANGSMITH_API_KEY is set,
    # this workflow will be recorded to LangSmith

    result = answer_workflow(
        question="遠端工作是否需要主管核准？",
        request_id="req-demo-001",
        task_id="task-demo-001",
        deployment_version="answer-v17",
        prompt_version="2026-09-21-a",
    )

    print("\nWorkflow Result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    print("\nLangSmith Trace Structure:")
    print("""
    Root Run: answer-workflow
    ├─ Child Run: retrieve
    │  ├─ name: "retrieve"
    │  ├─ run_type: "tool"
    │  └─ metadata: {index_version: "policy-v3"}
    ├─ Child Run: call_model
    │  ├─ name: "call_model"
    │  ├─ run_type: "llm"
    │  └─ metadata: {model_id: "gemini-2.0-flash-latest"}
    ├─ Child Run: validate
    │  ├─ name: "validate"
    │  ├─ run_type: "tool"
    │  └─ metadata: {safety_status: "approved"}
    └─ Output: {citations, quality_status, ...}
    """)

    print(f"\nTo view in LangSmith:")
    print(f"  Project: {os.getenv('LANGSMITH_PROJECT', 'sre-lab-dev')}")
    print(f"  Look for request_id: {result['request_id']}")


def demo_dataset():
    """Demo 2: Explore regression dataset."""
    print_section("Demo 2: Regression Dataset")

    dataset = create_regression_dataset()

    print(f"\nDataset: {dataset['dataset_id']}")
    print(f"Version: {dataset['version']}")
    print(f"Description: {dataset['description']}")

    # Show statistics
    stats = dataset_statistics(dataset)
    print(f"\nStatistics:")
    print(f"  Total examples: {stats['total_examples']}")
    print(f"  By category: {stats['by_category']}")
    print(f"  By risk level: {stats['by_risk_level']}")

    # Show each example
    print(f"\nExamples:")
    for example in dataset["examples"]:
        print(f"\n  • {example['example_id']}")
        print(f"    Input: {example['inputs']['question']}")
        print(f"    Expected status: {example['reference_outputs']['expected_status']}")
        print(f"    Required sources: {example['reference_outputs']['required_sources']}")
        print(f"    Risk level: {example['metadata']['risk_level']}")
        print(f"    Added reason: {example['metadata']['added_reason']}")


def demo_evaluation():
    """Demo 3: Evaluate baseline vs candidate."""
    print_section("Demo 3: Baseline vs Candidate Evaluation")

    dataset = create_regression_dataset()

    # Simulate baseline output (perfect)
    baseline_output = {
        "question": "遠端工作是否需要主管核准？",
        "answer": "Based on company policy, remote work requires manager approval.",
        "citations": ["company-policy-remote-work"],
        "quality_status": "approved",
    }

    # Simulate candidate output (with a regression)
    candidate_output = {
        "question": "什麼時候可以遠端工作？",
        "answer": "You can work remotely.",  # Missing the "manager approval" fact
        "citations": ["company-policy-remote-work"],
        "quality_status": "approved",  # Status is ok but content is wrong
    }

    baseline_results = []
    candidate_results = []

    print("\nEvaluating against dataset examples:")
    print(f"Dataset has {len(dataset['examples'])} examples\n")

    for i, example in enumerate(dataset["examples"], 1):
        baseline_eval = evaluate_example(
            baseline_output,
            example["reference_outputs"],
            example_id=f"example-{i}-baseline",
        )
        candidate_eval = evaluate_example(
            candidate_output,
            example["reference_outputs"],
            example_id=f"example-{i}-candidate",
        )

        baseline_results.append(baseline_eval)
        candidate_results.append(candidate_eval)

        print(f"Example {i}: {example['example_id']}")
        print(f"  Baseline - required_source: {baseline_eval.required_source_present}, safety: {baseline_eval.safety_approved}")
        print(f"  Candidate - required_source: {candidate_eval.required_source_present}, safety: {candidate_eval.safety_approved}")

    # Make release decision
    decision_result = make_release_decision(baseline_results, candidate_results)

    print(f"\n{'─' * 70}")
    print(f"Release Decision: {decision_result['decision'].upper()}")
    print(f"Rationale: {decision_result['rationale']}")
    print(f"Required source failures: {decision_result['required_source_failures']}")
    print(f"Safety failures: {decision_result['safety_failures']}")
    print(f"Quality regressions: {decision_result['quality_regressions']}")


def demo_failure_classification():
    """Demo 4: Classify a production failure for dataset creation."""
    print_section("Demo 4: Failure Classification → Dataset Creation")

    print("\nScenario: Production incident where model missed critical condition")
    print("  Question: 什麼時候可以遠端工作？")
    print("  Expected: Mention manager approval AND confidentiality restriction")
    print("  Actual: Only mentioned manager approval, missed confidentiality restriction")

    # Step 1: Classify the failure
    failure = classify_failure(
        example_id="inc-2026-09-21-001",
        failure_type="missing_critical_condition",
        root_component="model",
        evidence={
            "http_status": 200,
            "latency_ms": 450,
            "retrieval_count": 1,
            "citations": ["company-policy-remote-work"],
            "missing_source": "company-policy-confidentiality",
        },
    )

    print(f"\nFailure Classification:")
    print(json.dumps(failure, indent=2, ensure_ascii=False))

    # Step 2: Create dataset example from the failure
    print(f"\n\nConverting to dataset example...")

    dataset_example = {
        "example_id": f"regression-{failure['example_id']}",
        "inputs": {
            "question": "什麼時候可以遠端工作？",
            "actor_role": "employee",
        },
        "reference_outputs": {
            "required_facts": [
                "需要主管核准",
                "限制條件：機密案件不可遠端",
            ],
            "required_sources": [
                "company-policy-remote-work",
                "company-policy-confidentiality",
            ],
            "expected_status": "completed",
        },
        "metadata": {
            "category": "policy_qa",
            "risk_level": "high",
            "added_reason": "production_incident",
            "incident_date": failure["timestamp"],
            "incident_ref": failure["example_id"],
            "root_component": failure["root_component"],
        },
    }

    print(f"\nDataset Example:")
    print(json.dumps(dataset_example, indent=2, ensure_ascii=False))

    print(f"\nNext step: Add this example to regression dataset")
    print(f"Then: Run evaluation on baseline/candidate with this example")
    print(f"Finally: Only allow release if candidate passes this example")


def main():
    """Run all demos."""
    print("\n" + "=" * 70)
    print(" Day31 DIY Demo: LangSmith Integration")
    print("=" * 70)

    # Check LangSmith configuration
    tracing_enabled = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
    api_key_set = bool(os.getenv("LANGSMITH_API_KEY"))

    print(f"\nLangSmith Configuration:")
    print(f"  LANGSMITH_TRACING: {tracing_enabled}")
    print(f"  LANGSMITH_API_KEY: {'✓ set' if api_key_set else '✗ not set'}")
    print(f"  LANGSMITH_PROJECT: {os.getenv('LANGSMITH_PROJECT', 'sre-lab-dev')}")

    if tracing_enabled and api_key_set:
        print("\n  ✓ Tracing is ENABLED - workflows will be sent to LangSmith")
    else:
        print("\n  ℹ Tracing is DISABLED - workflows run locally only")

    # Run demos
    demo_workflow()
    demo_dataset()
    demo_evaluation()
    demo_failure_classification()

    print_section("Demo Complete")
    print("\nTo run with LangSmith tracing enabled:")
    print("  export LANGSMITH_TRACING=true")
    print("  export LANGSMITH_API_KEY='your-api-key'")
    print("  export LANGSMITH_PROJECT='sre-lab-dev'")
    print("  uv run python scripts/demo.py")


if __name__ == "__main__":
    main()
