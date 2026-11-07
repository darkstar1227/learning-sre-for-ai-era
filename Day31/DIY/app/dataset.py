"""
Dataset management for regression testing and evaluation.

This module demonstrates:
1. How to structure dataset examples for AI workflows
2. How to move from production failures to regression dataset cases
3. How to keep versioning and metadata organized
"""

from typing import Dict, List, Any
from dataclasses import dataclass, asdict


@dataclass
class DatasetExample:
    """A single example in a regression dataset."""

    example_id: str
    inputs: Dict[str, Any]
    reference_outputs: Dict[str, Any]
    metadata: Dict[str, Any]


def create_regression_dataset() -> Dict[str, Any]:
    """
    Create a minimal regression dataset.

    This corresponds to the article's Step 3:
    - Multiple examples covering different failure modes
    - Each with inputs, expected behavior, and metadata
    - Ready for baseline and candidate evaluation
    """
    examples = [
        {
            "example_id": "ex-policy-qa-normal",
            "inputs": {
                "question": "遠端工作是否需要主管核准？",
                "actor_role": "employee",
            },
            "reference_outputs": {
                "required_facts": ["需要主管核准"],
                "required_sources": ["company-policy-remote-work"],
                "expected_status": "completed",
            },
            "metadata": {
                "category": "policy_qa",
                "risk_level": "medium",
                "added_reason": "golden_case",
                "version": "2026-09-21-a",
            },
        },
        {
            "example_id": "ex-policy-qa-missing-condition",
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
                "added_reason": "missing_critical_condition",
                "version": "2026-09-21-a",
                "incident_ref": "day31-regression-001",
            },
        },
        {
            "example_id": "ex-insufficient-context",
            "inputs": {
                "question": "政策",
                "actor_role": "employee",
            },
            "reference_outputs": {
                "required_facts": ["應要求澄清問題"],
                "required_sources": [],
                "expected_status": "insufficient_context",
            },
            "metadata": {
                "category": "insufficient_context",
                "risk_level": "low",
                "added_reason": "safety_edge_case",
                "version": "2026-09-21-a",
            },
        },
    ]

    return {
        "dataset_id": "policy-qa-regression",
        "version": "2026-09-21",
        "description": "Regression dataset for policy QA workflow",
        "examples": examples,
        "metadata": {
            "created_date": "2026-09-21",
            "purpose": "regression_testing",
            "coverage": [
                "normal_case",
                "missing_critical_condition",
                "insufficient_context",
            ],
        },
    }


def create_example_from_failure(
    request_id: str,
    question: str,
    expected_behavior: str,
    forbidden_behavior: str,
    failure_classification: Dict[str, Any],
) -> DatasetExample:
    """
    Create a dataset example from a classified production failure.

    This implements the article's Step 4 flow:
    1. Take a failure trace (sanitized)
    2. Extract inputs and expected behavior
    3. Document what should NOT happen
    4. Create example for future evaluation

    Args:
        request_id: Original request that failed
        question: The question that was asked
        expected_behavior: What should have happened
        forbidden_behavior: What must not happen again
        failure_classification: Result from classify_failure()

    Returns:
        DatasetExample ready to be added to dataset
    """
    return DatasetExample(
        example_id=f"regression-{request_id}",
        inputs={
            "question": question,
            "request_id": request_id,
        },
        reference_outputs={
            "required_facts": [expected_behavior],
            "forbidden_behaviors": [forbidden_behavior],
            "required_sources": [failure_classification.get("root_component", "unknown")],
            "expected_status": "completed",
        },
        metadata={
            "category": failure_classification.get("failure_type", "unknown"),
            "risk_level": "high",
            "added_reason": "production_incident",
            "original_request_id": request_id,
            "incident_date": failure_classification.get("timestamp"),
            "root_component": failure_classification.get("root_component"),
        },
    )


def get_example_by_id(
    dataset: Dict[str, Any],
    example_id: str,
) -> Dict[str, Any] | None:
    """
    Retrieve a specific example from dataset by ID.

    Args:
        dataset: The dataset dict (from create_regression_dataset)
        example_id: ID of example to retrieve

    Returns:
        The example dict, or None if not found
    """
    for example in dataset.get("examples", []):
        if example["example_id"] == example_id:
            return example
    return None


def dataset_statistics(dataset: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate statistics about the dataset.

    Args:
        dataset: The dataset dict

    Returns:
        Dict with coverage and metadata stats
    """
    examples = dataset.get("examples", [])
    categories = {}
    risk_levels = {}

    for example in examples:
        metadata = example.get("metadata", {})
        category = metadata.get("category", "unknown")
        risk = metadata.get("risk_level", "unknown")

        categories[category] = categories.get(category, 0) + 1
        risk_levels[risk] = risk_levels.get(risk, 0) + 1

    return {
        "total_examples": len(examples),
        "by_category": categories,
        "by_risk_level": risk_levels,
        "version": dataset.get("version"),
        "dataset_id": dataset.get("dataset_id"),
    }
