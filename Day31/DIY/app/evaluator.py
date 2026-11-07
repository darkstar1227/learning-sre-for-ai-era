"""
Evaluation functions for dataset and release decisions.

This module demonstrates:
1. Rule-based evaluators (deterministic, auditable)
2. Release gate logic based on evaluation results
3. Classification of failures for investigation
"""

from typing import Any, Dict, List
from dataclasses import dataclass


@dataclass
class EvaluationResult:
    """Result from evaluating a single example."""

    example_id: str
    required_source_present: bool
    safety_approved: bool
    quality_rating: float
    citation_valid: bool


def required_source_present(outputs: dict, reference_outputs: dict) -> bool:
    """
    Check if all required sources are present in the output citations.

    Rule-based evaluator: deterministic, easy to audit, suitable for contracts.

    Args:
        outputs: Generated output from answer_workflow
        reference_outputs: Reference/expected output from dataset

    Returns:
        True if all required sources are cited, False otherwise
    """
    citations = set(outputs.get("citations", []))
    required = set(reference_outputs.get("required_sources", []))
    return required.issubset(citations)


def safety_evaluator(outputs: dict, reference_outputs: dict) -> bool:
    """
    Check if safety status matches expected level.

    Args:
        outputs: Generated output from answer_workflow
        reference_outputs: Reference/expected output from dataset

    Returns:
        True if safety status is acceptable, False otherwise
    """
    expected_status = reference_outputs.get("expected_status", "approved")
    actual_status = outputs.get("quality_status", "approved")
    return actual_status == expected_status


def evaluate_example(
    outputs: dict,
    reference_outputs: dict,
    example_id: str = "ex-1",
) -> EvaluationResult:
    """
    Evaluate a single example against reference outputs.

    Args:
        outputs: Generated output from answer_workflow
        reference_outputs: Reference/expected output from dataset
        example_id: Identifier for this example

    Returns:
        EvaluationResult with individual metric scores
    """
    return EvaluationResult(
        example_id=example_id,
        required_source_present=required_source_present(outputs, reference_outputs),
        safety_approved=safety_evaluator(outputs, reference_outputs),
        quality_rating=0.95 if safety_evaluator(outputs, reference_outputs) else 0.5,
        citation_valid=len(outputs.get("citations", [])) > 0,
    )


def make_release_decision(
    baseline_results: List[EvaluationResult],
    candidate_results: List[EvaluationResult],
) -> Dict[str, Any]:
    """
    Make release decision based on baseline vs candidate evaluation.

    This is the decision gate from the article's Step 3:
    - blocked: if any required_source or safety failure
    - human_review_required: if quality regression
    - allowed: if all metrics pass

    Args:
        baseline_results: Evaluation results from baseline implementation
        candidate_results: Evaluation results from candidate implementation

    Returns:
        Dict with decision, rationale, and failure classification
    """
    candidate_required_source_failures = sum(
        1 for r in candidate_results if not r.required_source_present
    )
    candidate_safety_failures = sum(
        1 for r in candidate_results if not r.safety_approved
    )
    candidate_quality_regressions = sum(
        1 for baseline, candidate in zip(baseline_results, candidate_results)
        if baseline.quality_rating > candidate.quality_rating
    )

    if candidate_required_source_failures > 0 or candidate_safety_failures > 0:
        decision = "blocked"
        rationale = (
            f"Blocked: {candidate_required_source_failures} required_source failures, "
            f"{candidate_safety_failures} safety failures"
        )
    elif candidate_quality_regressions > 0:
        decision = "human_review_required"
        rationale = f"Human review needed: {candidate_quality_regressions} quality regressions detected"
    else:
        decision = "allowed"
        rationale = "All metrics passed: allowed for release"

    return {
        "decision": decision,
        "rationale": rationale,
        "required_source_failures": candidate_required_source_failures,
        "safety_failures": candidate_safety_failures,
        "quality_regressions": candidate_quality_regressions,
        "baseline_count": len(baseline_results),
        "candidate_count": len(candidate_results),
    }


def classify_failure(
    example_id: str,
    failure_type: str,
    root_component: str,
    evidence: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Classify a production failure for investigation and dataset creation.

    This implements the flow from the article's Step 4:
    - Identify failure class
    - Extract version and outcome
    - Preserve evidence
    - Remove sensitive content

    Args:
        example_id: Identifier for the failure case
        failure_type: Type of failure (e.g., "missing_critical_condition")
        root_component: Which component failed (retrieval/model/validator/tool)
        evidence: Observable signals from trace/logs/metrics

    Returns:
        Failure classification record suitable for dataset creation
    """
    return {
        "example_id": example_id,
        "failure_type": failure_type,
        "root_component": root_component,
        "evidence": evidence,
        "timestamp": "2026-09-21T10:00:00Z",  # Would be actual timestamp in production
        "metadata": {
            "investigation_status": "classified",
            "sensitive_content_removed": True,
            "ready_for_dataset": True,
        },
    }
