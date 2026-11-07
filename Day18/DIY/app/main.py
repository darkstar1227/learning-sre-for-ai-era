"""
Day 18 DIY - FastAPI application demonstrating SLI event contract.

This module shows:
1. HTTP middleware for request boundary recording
2. Workflow handler with step-by-step timing
3. Mock implementations of retrieval, model, and tool calls
"""

import json
import logging
from time import perf_counter, sleep
from typing import Literal

from fastapi import FastAPI, Request
from pydantic import BaseModel

from .schemas import new_ask_event, AskEvent

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("ai_sli")

app = FastAPI(title="Day 18 SLI Demo")


# ============ HTTP Middleware: Request Boundary ============


@app.middleware("http")
async def record_request_boundary(request: Request, call_next):
    """
    HTTP middleware to record request_received and response_sent boundaries.

    This runs before and after every endpoint handler.
    Logs a simple boundary record without diving into workflow details.
    """
    started_at = perf_counter()
    request_id = request.headers.get("x-request-id", f"auto-{id(request)}")

    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = round((perf_counter() - started_at) * 1000, 2)
        logger.exception(
            "http_request_failed",
            extra={
                "request_id": request_id,
                "route": request.url.path,
                "end_to_end_ms": elapsed_ms,
            },
        )
        raise

    elapsed_ms = round((perf_counter() - started_at) * 1000, 2)
    logger.info(
        "http_request_finished",
        extra={
            "request_id": request_id,
            "route": request.url.path,
            "http_status": response.status_code,
            "end_to_end_ms": elapsed_ms,
        },
    )
    response.headers["x-request-id"] = request_id
    return response


# ============ Mock Dependencies ============


async def retrieve_policy_documents(question: str) -> list[str]:
    """
    Mock retrieval: simulate document lookup.

    In real implementation, this queries a knowledge base or vector store.
    """
    # Simulate retrieval latency
    sleep(0.05)
    if "unknown" in question.lower():
        return []
    return [
        f"Policy doc 1: Information about {question[:20]}",
        f"Policy doc 2: More context on {question[:20]}",
    ]


async def call_model(question: str, documents: list[str]) -> str:
    """
    Mock model call: simulate LLM completion.

    In real implementation, this calls Gemini, GPT, Claude, etc.
    """
    # Simulate streaming: return token-by-token representation
    sleep(0.1)  # Provider latency
    doc_summary = " ".join(documents[:1]) if documents else "No documents"
    return f"Based on {doc_summary}, the answer to '{question}' is: example response."


def parse_answer(completion: str) -> dict:
    """Mock answer parsing."""
    return {
        "text": completion,
        "source_ids": [1, 2],
    }


def validate_sources(parsed: dict, documents: list[str]) -> None:
    """Mock source validation."""
    pass


# ============ Workflow Handler ============


async def answer_policy_question(question: str) -> dict[str, object]:
    """
    Policy Q&A workflow with explicit SLI event recording.

    Key pattern: timing points are recorded at specific events:
    - retrieval_started/finished: before/after retrieval
    - model_started: before calling model
    - first_token: [in real streaming, recorded in token iterator]
    - generation_finished: after model returns
    - response_sent: in finally block

    Outcome is classified: completed, insufficient_context, technical_failed.
    """
    event = new_ask_event()
    event.timing.workflow_started = perf_counter()
    event.technical_status = "running"

    try:
        # ---- Retrieval Phase ----
        event.timing.retrieval_started = perf_counter()
        documents = await retrieve_policy_documents(question)
        event.timing.retrieval_finished = perf_counter()
        event.retrieval_count = len(documents)

        if not documents:
            event.outcome = "insufficient_context"
            event.workflow_status = "completed"
            event.quality_status = "not_evaluated"
            event.safety_status = "not_applicable"
            return {
                "answer": "現有文件沒有足夠資訊可以回答這個問題。",
                "request_id": event.request_id,
            }

        # ---- Model Phase ----
        event.timing.model_started = perf_counter()
        completion = await call_model(question=question, documents=documents)
        # In real streaming, first_token would be recorded in the iterator
        # For now, we skip it (leave as None) to match non-streaming behavior
        event.timing.generation_finished = perf_counter()

        # ---- Parse & Validate ----
        parsed = parse_answer(completion)
        validate_sources(parsed, documents)

        # ---- Success ----
        event.outcome = "completed"
        event.technical_status = "succeeded"
        event.workflow_status = "completed"
        event.quality_status = "not_evaluated"
        event.safety_status = "not_evaluated"
        return {
            "answer": parsed["text"],
            "sources": parsed["source_ids"],
            "request_id": event.request_id,
        }
    except Exception as error:
        event.outcome = "technical_failed"
        event.technical_status = "failed"
        event.error_class = type(error).__name__
        event.notes.append(f"Exception: {error}")
        raise
    finally:
        event.timing.response_sent = perf_counter()
        log_record = event.to_log_record()
        logger.info("ask_event", extra=log_record)


# ============ FastAPI Endpoints ============


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


class AskRequest(BaseModel):
    """Request body for /ask endpoint."""
    question: str
    mode: Literal["normal", "timeout", "no_docs"] = "normal"


@app.post("/ask")
async def ask_endpoint(req: AskRequest) -> dict[str, object]:
    """
    Ask a policy question and get SLI trace.

    Query parameters for testing different outcomes:
    - mode=normal: standard flow (retrieval + model)
    - mode=timeout: simulate provider timeout
    - mode=no_docs: force insufficient_context
    """
    if req.mode == "timeout":
        event = new_ask_event()
        event.timing.workflow_started = perf_counter()
        try:
            event.timing.retrieval_started = perf_counter()
            sleep(0.05)
            event.timing.retrieval_finished = perf_counter()
            event.retrieval_count = 2

            event.timing.model_started = perf_counter()
            sleep(0.2)  # Simulate timeout
            raise TimeoutError("Model provider timeout")
        except TimeoutError as error:
            event.outcome = "technical_failed"
            event.technical_status = "failed"
            event.error_class = "TimeoutError"
            raise
        finally:
            event.timing.response_sent = perf_counter()
            log_record = event.to_log_record()
            logger.info("ask_event", extra=log_record)

    if req.mode == "no_docs":
        question = "unknown topic xyz"
    else:
        question = req.question

    result = await answer_policy_question(question)
    return result


@app.get("/schema/ask-event")
async def schema_ask_event() -> dict[str, object]:
    """Return AskEvent schema documentation."""
    event = new_ask_event()
    event.timing.workflow_started = perf_counter() + 0.1
    event.timing.retrieval_started = perf_counter() + 0.15
    event.timing.retrieval_finished = perf_counter() + 0.2
    event.timing.model_started = perf_counter() + 0.2
    event.timing.first_token = None  # Not streaming in this example
    event.timing.generation_finished = perf_counter() + 0.3
    event.timing.response_sent = perf_counter() + 0.31

    return {
        "description": "AskEvent contract for LLM workflow SLI",
        "example": event.to_log_record(),
        "fields": {
            "request_id": "Unique ID per request",
            "trace_id": "Distributed trace context ID",
            "workflow_name": "Name of workflow (e.g., 'policy_qa')",
            "workflow_version": "Version deployed",
            "model_name": "Which model endpoint was used",
            "retrieval_index_version": "Which doc index version",
            "outcome": "One of: completed, technical_failed, quality_failed, safety_blocked, insufficient_context",
            "timing": {
                "request_received": "When HTTP request arrived",
                "workflow_started": "When worker took the job",
                "retrieval_started": "Before querying knowledge base",
                "retrieval_finished": "After documents retrieved or confirmed empty",
                "model_started": "Before calling model API",
                "first_token": "When first token received (None if not streaming)",
                "generation_finished": "When model output complete",
                "tool_finished": "When tool calls (if any) complete",
                "response_sent": "When response fully sent to client",
            },
            "computed_sli": {
                "queue_delay_ms": "workflow_started - request_received",
                "retrieval_ms": "retrieval_finished - retrieval_started",
                "ttft_ms": "first_token - request_received (None if not streaming)",
                "generation_ms": "model_started - generation_finished",
                "end_to_end_ms": "response_sent - request_received",
            },
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
