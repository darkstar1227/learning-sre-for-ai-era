"""
FastAPI application with LangSmith integration.

Demonstrates:
1. Minimal FastAPI setup for LangSmith tracing
2. How to call @traceable workflows
3. How to structure request/response with versioning and tracing IDs
"""

import os
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# LangSmith will auto-detect these env vars if set:
# - LANGSMITH_TRACING=true
# - LANGSMITH_API_KEY=...
# - LANGSMITH_PROJECT=sre-lab-dev

from app.workflows import answer_workflow
from app.dataset import create_regression_dataset
from app.evaluator import evaluate_example, make_release_decision


class AskRequest(BaseModel):
    """Request to /ask endpoint."""

    question: str
    actor_role: str = "employee"


class AskResponse(BaseModel):
    """Response from /ask endpoint."""

    request_id: str
    task_id: str
    question: str
    answer: str
    citations: list[str]
    quality_status: str
    task_status: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle management.

    LangSmith auto-initialization happens on import.
    Check LANGSMITH_* environment variables for configuration.
    """
    # Startup
    project_name = os.getenv("LANGSMITH_PROJECT", "sre-lab-dev")
    tracing_enabled = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"

    print(f"[LangSmith] Tracing: {tracing_enabled}, Project: {project_name}")

    yield

    # Shutdown
    print("[Shutdown] Application stopping")


# Initialize FastAPI app
app = FastAPI(
    title="Day31 DIY - LangSmith Integration",
    description="Demonstrates LangSmith integration for AI workflow tracing and evaluation",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/ready")
def readiness_check():
    """Readiness check endpoint."""
    return {"status": "ready"}


@app.post("/ask", response_model=AskResponse)
def ask_endpoint(request: AskRequest) -> AskResponse:
    """
    Main endpoint: answer a question with LangSmith tracing.

    This endpoint:
    1. Generates request_id and task_id for tracing
    2. Calls answer_workflow (which is @traceable)
    3. Returns structured response with versioning

    When LANGSMITH_TRACING=true and LANGSMITH_API_KEY is set,
    the entire workflow and sub-steps are recorded to LangSmith.
    """
    request_id = f"req-{uuid.uuid4().hex[:8]}"
    task_id = f"task-{uuid.uuid4().hex[:8]}"

    try:
        # Call the @traceable workflow
        result = answer_workflow(
            question=request.question,
            request_id=request_id,
            task_id=task_id,
            deployment_version="answer-v17",
            prompt_version="2026-09-21-a",
        )

        return AskResponse(
            request_id=request_id,
            task_id=task_id,
            question=request.question,
            answer=result["answer"],
            citations=result["citations"],
            quality_status=result["quality_status"],
            task_status=result["task_status"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/dataset/regression")
def get_regression_dataset():
    """
    Retrieve the regression dataset.

    This endpoint returns the dataset used for baseline/candidate evaluation.
    """
    return create_regression_dataset()


@app.post("/evaluate")
def evaluate_endpoint(baseline_outputs: dict, candidate_outputs: dict):
    """
    Evaluate candidate against baseline using rule-based evaluators.

    Request body should contain:
    {
        "baseline_outputs": {...},
        "candidate_outputs": {...}
    }

    Returns release decision and rationale.
    """
    dataset = create_regression_dataset()

    baseline_results = []
    candidate_results = []

    for example in dataset["examples"]:
        ex_id = example["example_id"]

        # In production, you'd run actual workflow on each example
        # For this demo, we evaluate the provided outputs
        baseline_eval = evaluate_example(
            baseline_outputs,
            example["reference_outputs"],
            example_id=f"{ex_id}-baseline",
        )
        candidate_eval = evaluate_example(
            candidate_outputs,
            example["reference_outputs"],
            example_id=f"{ex_id}-candidate",
        )

        baseline_results.append(baseline_eval)
        candidate_results.append(candidate_eval)

    release_decision = make_release_decision(baseline_results, candidate_results)

    return {
        "decision": release_decision["decision"],
        "rationale": release_decision["rationale"],
        "baseline_count": release_decision["baseline_count"],
        "candidate_count": release_decision["candidate_count"],
        "required_source_failures": release_decision["required_source_failures"],
        "safety_failures": release_decision["safety_failures"],
        "quality_regressions": release_decision["quality_regressions"],
    }


@app.get("/trace-example")
def trace_example():
    """
    Run a sample workflow and return trace information.

    This demonstrates the structure that would appear in LangSmith:
    - Root run: answer-workflow
    - Child runs: retrieve, call_model, validate
    - Metadata: request_id, task_id, deployment_version, etc.
    """
    request_id = f"req-{uuid.uuid4().hex[:8]}"
    task_id = f"task-{uuid.uuid4().hex[:8]}"

    result = answer_workflow(
        question="Sample question for tracing",
        request_id=request_id,
        task_id=task_id,
    )

    # Structure of trace in LangSmith:
    return {
        "message": "Check LangSmith project for full trace",
        "request_id": request_id,
        "task_id": task_id,
        "langsmith_project": os.getenv("LANGSMITH_PROJECT", "sre-lab-dev"),
        "langsmith_enabled": os.getenv("LANGSMITH_TRACING", "false") == "true",
        "result_summary": {
            "question": result["question"],
            "answer_length": len(result["answer"]),
            "citations_count": len(result["citations"]),
            "quality_status": result["quality_status"],
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
