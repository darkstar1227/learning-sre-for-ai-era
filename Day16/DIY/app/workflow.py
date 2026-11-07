"""
Day16 - Mock workflow for policy Q&A.

This module simulates an AI workflow that would normally involve
retrieval, prompt assembly, model inference, and validation.
"""
from dataclasses import dataclass


@dataclass
class WorkflowResult:
    """Result of a policy Q&A workflow."""
    workflow_status: str  # "completed" or "failed"
    model_route: str     # "primary" or "fallback"
    answer: str
    sources: list


async def run_policy_workflow(question: str) -> WorkflowResult:
    """
    Simulate a policy Q&A workflow.

    This is a mock implementation that returns a fixed result.
    In production, this would call retrievers, models, and validators.

    Args:
        question: The policy question to answer

    Returns:
        WorkflowResult with the answer and metadata
    """
    # Mock workflow that simulates the question being answered
    return WorkflowResult(
        workflow_status="completed",
        model_route="primary",
        answer=f"Policy answer for: {question}",
        sources=[],
    )
