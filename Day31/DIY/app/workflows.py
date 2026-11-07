"""
Workflow functions with LangSmith tracing.

This module demonstrates:
1. How to structure AI workflows with @traceable
2. How to record versioning and outcome metadata
3. How to maintain clear boundaries between workflow steps
"""

from langsmith import traceable
from typing import Any


@traceable(name="retrieve", run_type="tool")
def retrieve(question: str) -> dict:
    """
    Retrieve documents based on question.

    In production, this would call a real retrieval system.
    For now, it returns mock data with version metadata.
    """
    # Mock retrieval
    documents = [
        {
            "id": "company-policy-remote-work",
            "content": "Remote work requires manager approval.",
            "relevance": 0.95,
        }
    ]
    return {
        "question": question,
        "documents": documents,
        "index_version": "policy-v3",
        "result_count": len(documents),
    }


@traceable(name="call_model", run_type="llm")
def call_model(question: str, documents: list) -> dict:
    """
    Call LLM to generate answer based on question and retrieved documents.

    In production, this would call Gemini or another provider.
    For now, it returns a mock answer with model metadata.
    """
    # Mock model call
    answer = "Based on company policy, remote work requires manager approval."

    return {
        "question": question,
        "answer": answer,
        "model_id": "gemini-2.0-flash-latest",
        "ttft_ms": 150,
        "output_tokens": 25,
    }


@traceable(name="validate", run_type="tool")
def validate(answer: str, documents: list) -> dict:
    """
    Validate answer for citation and safety.

    In production, this would check:
    - Citations are properly sourced
    - Safety filters are satisfied
    - Quality metrics are within bounds
    """
    # Mock validation
    citations = ["company-policy-remote-work"]

    return {
        "answer": answer,
        "citations": citations,
        "citation_valid": True,
        "safety_status": "approved",
    }


@traceable(name="answer-workflow", run_type="chain")
def answer_workflow(
    question: str,
    *,
    request_id: str,
    task_id: str,
    deployment_version: str = "answer-v17",
    prompt_version: str = "2026-09-21-a",
) -> dict:
    """
    Complete workflow to answer a question with tracing and versioning.

    Args:
        question: The user's question
        request_id: Request identifier for logging/tracing
        task_id: Task identifier for grouping related requests
        deployment_version: Version of deployed application
        prompt_version: Version of prompt used

    Returns:
        Dict with answer, citations, and quality status
    """
    # Step 1: Retrieve
    retrieval_result = retrieve(question)
    documents = retrieval_result["documents"]

    # Step 2: Call model
    model_result = call_model(question, documents)
    answer = model_result["answer"]

    # Step 3: Validate
    validation_result = validate(answer, documents)

    # Compose result with metadata
    result = {
        "request_id": request_id,
        "task_id": task_id,
        "question": question,
        "answer": answer,
        "citations": validation_result["citations"],
        "quality_status": validation_result["safety_status"],
        "task_status": "completed",
        "metadata": {
            "deployment_version": deployment_version,
            "prompt_version": prompt_version,
            "index_version": retrieval_result["index_version"],
        },
    }

    return result
