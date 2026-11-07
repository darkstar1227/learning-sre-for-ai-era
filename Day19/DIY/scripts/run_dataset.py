#!/usr/bin/env python
"""Run evaluation on golden dataset.

Usage:
    uv run python scripts/run_dataset.py \\
      --dataset data/policy_task_dataset_v1.jsonl \\
      --workflow-version rag-policy-v1 \\
      --output artifacts/policy_task_v1.jsonl

Simulates running each test case through a policy QA workflow and evaluates outputs.
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

from app.evaluator import evaluate_response


def simulate_workflow_response(case: dict) -> dict:
    """Simulate a policy QA workflow response.

    This is a mock implementation for demonstration. In real systems,
    this would call the actual RAG pipeline with retrieval, ranking,
    prompt, and model inference.

    For demonstration, we'll have hard-coded responses that test
    different evaluation scenarios.
    """
    case_id = case["id"]

    # Simulate different response patterns
    # Responses are crafted to match required_facts for proper evaluation
    responses = {
        "remote-days": {
            "outcome": "answered",
            "answer": "全職員工每週最多可遠端 two days，經過主管核可",
            "source_ids": ["remote-work-v1"],
        },
        "remote-approval": {
            "outcome": "answered",
            "answer": "遠端工作需要 manager approval，由主管簽核同意",
            "source_ids": ["remote-work-v1"],
        },
        "unknown-benefit": {
            "outcome": "insufficient_context",
            "answer": "在我們的知識庫中找不到居家設備補助的相關資訊",
            "source_ids": [],
        },
        "salary-export": {
            "outcome": "refused_or_escalated",
            "answer": "此請求涉及敏感個人資料，無法提供",
            "source_ids": [],
        },
        "invalid-tool": {
            "outcome": "needs_review",
            "answer": "請假申請需要經過 approval required 流程，建議聯繫人力資源部",
            "source_ids": ["leave-v1"],
        },
    }

    return responses.get(
        case_id,
        {
            "outcome": "technical_failure",
            "answer": "Unable to process request",
            "source_ids": [],
        }
    )


def main():
    parser = argparse.ArgumentParser(
        description="Run evaluation on golden dataset"
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("data/policy_task_dataset_v1.jsonl"),
        help="Path to golden dataset JSONL file",
    )
    parser.add_argument(
        "--workflow-version",
        type=str,
        default="rag-policy-v1",
        help="Version of the workflow being evaluated",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/policy_task_v1.jsonl"),
        help="Path to write evaluation results JSONL",
    )

    args = parser.parse_args()

    # Ensure output directory exists
    args.output.parent.mkdir(parents=True, exist_ok=True)

    # Known source IDs in the knowledge base
    known_sources = {
        "remote-work-v1",
        "leave-v1",
    }

    print(f"Loading dataset: {args.dataset}")

    if not args.dataset.exists():
        print(f"Error: Dataset file not found: {args.dataset}", file=sys.stderr)
        sys.exit(1)

    cases = []
    try:
        with open(args.dataset, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                if not line.strip():
                    continue
                try:
                    case = json.loads(line)
                    cases.append(case)
                except json.JSONDecodeError as e:
                    print(
                        f"Warning: Line {line_num} is invalid JSON: {e}",
                        file=sys.stderr
                    )
    except IOError as e:
        print(f"Error reading dataset: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(cases)} cases from dataset")
    print(f"Workflow version: {args.workflow_version}")
    print()

    # Process each case
    results = []
    for case in cases:
        case_id = case["id"]
        print(f"Evaluating: {case_id}", end=" ... ")

        # Simulate workflow execution
        response = simulate_workflow_response(case)

        # Evaluate the response
        eval_result = evaluate_response(case, response, known_sources)

        # Convert to dict for JSON serialization
        result_dict = {
            "evaluation_id": f"eval_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{case_id}",
            "case_id": eval_result.case_id,
            "dataset_version": "policy_task_dataset_v1",
            "workflow_version": args.workflow_version,
            "workflow_name": "policy-rag",
            "case_intent": case.get("intent"),
            "case_risk": case.get("risk"),
            "technical_status": eval_result.technical_status,
            "task_status": eval_result.task_status,
            "quality_status": eval_result.quality_status,
            "safety_status": eval_result.safety_status,
            "citation_valid": eval_result.citation_valid,
            "missing_required_facts": eval_result.missing_required_facts,
            "outcome_matches": eval_result.outcome_matches,
            "expected_outcome": case.get("expected_outcome"),
            "actual_outcome": response.get("outcome"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        results.append(result_dict)

        # Print status line
        status = "PASS" if (
            eval_result.outcome_matches and
            eval_result.citation_valid and
            not eval_result.missing_required_facts
        ) else "FAIL"
        print(status)

    # Write results to JSONL
    print()
    print(f"Writing {len(results)} evaluation results to: {args.output}")

    try:
        with open(args.output, "w", encoding="utf-8") as f:
            for result in results:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")
    except IOError as e:
        print(f"Error writing output: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"✓ Evaluation complete. Results saved to {args.output}")
    sys.exit(0)


if __name__ == "__main__":
    main()
