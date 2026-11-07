"""Deterministic evaluation rules for policy QA system.

Implements the evaluation logic from Step 3 of Day19:
- Citation validity checking
- Required facts coverage
- Outcome matching
"""

from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class EvaluationResult:
    """Result of evaluating a single response against a test case.

    Tracks technical, task, quality, and safety dimensions separately.
    """
    case_id: str
    citation_valid: bool
    missing_required_facts: list[str]
    outcome_matches: bool
    technical_status: str = "completed"  # completed, timeout, error
    task_status: str = "unknown"  # completed, blocked, needs_review
    quality_status: str = "unknown"  # pass, fail, unknown
    safety_status: str = "unknown"  # allowed, blocked, escalated


def evaluate_response(
    case: dict,
    response: dict,
    known_source_ids: set[str],
) -> EvaluationResult:
    """Evaluate a single response against a test case.

    This is a deterministic check that validates:
    1. Whether cited sources actually exist
    2. Whether required facts appear in the answer
    3. Whether the outcome type matches expectation

    Args:
        case: Golden dataset entry with expected outcomes
        response: Workflow output with answer and source citations
        known_source_ids: Set of valid source document IDs in the knowledge base

    Returns:
        EvaluationResult with pass/fail for each dimension

    Note:
        This intentionally uses naive string matching to demonstrate
        the principle. Real implementations should handle synonyms,
        negation, and language variations.
    """
    cited = set(response.get("source_ids", []))
    answer = response.get("answer", "").lower()

    # Check for missing required facts
    missing = [
        fact
        for fact in case["required_facts"]
        if fact.lower() not in answer
    ]

    # Check citation validity
    citation_valid = cited.issubset(known_source_ids) if cited else True

    # Check outcome type matching
    outcome_matches = response.get("outcome") == case["expected_outcome"]

    # Determine status based on outcome type
    task_status = "completed" if response.get("outcome") == "answered" else "needs_review"
    quality_status = "pass" if not missing else "fail"

    return EvaluationResult(
        case_id=case["id"],
        citation_valid=citation_valid,
        missing_required_facts=missing,
        outcome_matches=outcome_matches,
        technical_status="completed",
        task_status=task_status,
        quality_status=quality_status,
        safety_status="unknown",  # Would require policy checker
    )


def evaluate_batch(
    cases: list[dict],
    responses: list[dict],
    known_source_ids: set[str],
) -> list[dict]:
    """Evaluate multiple responses and return results in JSONL format.

    Args:
        cases: List of golden dataset entries
        responses: List of workflow responses (should match case order)
        known_source_ids: Set of valid source IDs

    Returns:
        List of dicts ready to serialize to JSONL
    """
    results = []
    for case, response in zip(cases, responses):
        eval_result = evaluate_response(case, response, known_source_ids)
        result_dict = asdict(eval_result)
        result_dict["case_intent"] = case.get("intent")
        result_dict["case_risk"] = case.get("risk")
        results.append(result_dict)

    return results
