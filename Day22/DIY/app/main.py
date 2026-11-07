"""
FastAPI application demonstrating observability frameworks (RED, USE, Golden Signals).

Reference: Day22/Day22.md section ⑥
"""

from time import monotonic
from fastapi import FastAPI, HTTPException
from prometheus_client import make_asgi_app

from app.metrics import (
    QUEUE_DEPTH,
    QUEUE_WAIT,
    REQUEST_DURATION,
    REQUESTS,
    TTFT,
    WORKFLOW_STEPS,
)

app = FastAPI(title="Day22 Observability Demo")


def answer_from_workflow(question: str) -> dict[str, str]:
    """
    Stub workflow: returns a canned answer.

    In a real system, this would:
    - Call retrieval (embedding + vector search)
    - Call LLM with context
    - Call tools if needed
    - Validate output
    - Run evaluation

    This stub returns a simple answer with outcome="ok".
    """
    return {"answer": f"stub answer for: {question}", "outcome": "ok"}


@app.post("/ask")
def ask(question: str) -> dict[str, str]:
    """
    Main endpoint demonstrating RED and USE metrics.

    Timing points:
    1. request_started: request accepted
    2. queued_at: added to queue
    3. worker_acquired_at: worker started processing
    4. retrieval_started: workflow begins
    5. monotonic() after workflow: TTFT observed
    6. finally block: REQUEST_DURATION observed
    """
    route = "/ask"
    model_route = "primary"
    request_started = monotonic()
    queue_name = "inference"
    outcome = "technical_error"

    QUEUE_DEPTH.labels(queue=queue_name).inc()
    queued_at = monotonic()

    try:
        # In a real system, this waits for a semaphore or worker queue.
        # Stub: worker is acquired immediately.
        worker_acquired_at = monotonic()
        QUEUE_WAIT.labels(
            queue=queue_name,
            model_route=model_route,
        ).observe(worker_acquired_at - queued_at)

        # Workflow execution (retrieval, LLM, tools, validation)
        retrieval_started = monotonic()
        result = answer_from_workflow(question)
        WORKFLOW_STEPS.labels(step="workflow", outcome=result["outcome"]).inc()

        # TTFT: Time to First Token
        # In a streaming service, observe when first token is sent.
        # Here we simulate it after workflow completes.
        TTFT.labels(route=route, model_route=model_route).observe(
            monotonic() - retrieval_started
        )

        outcome = result["outcome"]
        REQUESTS.labels(
            route=route,
            outcome=outcome,
            model_route=model_route,
        ).inc()
        return result
    except TimeoutError as exc:
        outcome = "upstream_timeout"
        REQUESTS.labels(
            route=route,
            outcome=outcome,
            model_route=model_route,
        ).inc()
        raise HTTPException(status_code=504, detail="upstream timeout") from exc
    finally:
        QUEUE_DEPTH.labels(queue=queue_name).dec()
        REQUEST_DURATION.labels(route=route, outcome=outcome).observe(
            monotonic() - request_started
        )


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


# Mount Prometheus metrics exporter at /metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
