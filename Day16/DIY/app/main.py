"""
Day16 DIY - Histogram latency recording and tail latency demonstration.

This implements the /ask endpoint with:
- Server-side end-to-end latency measurement using perf_counter()
- Prometheus histogram recording with proper labels
- Controllable test delay injection for Lab experiments
- Proper timing boundary definition (from handler entry to exit)
"""
import asyncio
import json
import logging
from time import perf_counter

from fastapi import FastAPI, HTTPException
from prometheus_client import make_asgi_app

from app.metrics import ask_request_duration_seconds
from app.workflow import run_policy_workflow

# Structured logging for deep latency investigation
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = FastAPI(title="Day16 - Tail Latency Measurement")

# Mount /metrics endpoint for Prometheus scraping
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


async def inject_delay_if_requested(delay_ms: int | None) -> None:
    """
    Inject a controlled delay for Lab testing purposes.

    Only allowed in Lab environment (0-10000 ms range).
    Do NOT use this in production public APIs.

    Args:
        delay_ms: Milliseconds to sleep (None = no delay)

    Raises:
        ValueError: If delay_ms is outside allowed range
    """
    if delay_ms is None:
        return
    if not 0 <= delay_ms <= 10_000:
        raise ValueError("delay_ms must be between 0 and 10000 in this Lab")
    await asyncio.sleep(delay_ms / 1_000)


@app.post("/ask")
async def ask(question: str, test_delay_ms: int | None = None) -> dict:
    """
    Handle policy Q&A requests with latency measurement.

    Timing boundary: from handler entry to handler exit
    (does not include client network time or gateway time)

    Args:
        question: The policy question to answer
        test_delay_ms: Optional test delay injection (Lab only)

    Returns:
        Dictionary with answer and sources
    """
    started_at = perf_counter()
    workflow_status = "failed"
    model_route = "primary"

    try:
        # Inject test delay if requested (Lab only)
        await inject_delay_if_requested(test_delay_ms)

        # Run the workflow
        result = await run_policy_workflow(question)
        workflow_status = result.workflow_status
        model_route = result.model_route

        if workflow_status != "completed":
            raise HTTPException(status_code=503, detail="workflow not completed")

        # Log the successful completion with detailed metrics
        elapsed_seconds = perf_counter() - started_at
        log_event = {
            "event": "ask.completed",
            "question": question[:50],  # Truncate to avoid logging full prompt
            "workflow_status": workflow_status,
            "model_route": model_route,
            "end_to_end_ms": int(elapsed_seconds * 1000),
        }
        logger.info(json.dumps(log_event))

        return {"answer": result.answer, "sources": result.sources}

    finally:
        # Record histogram observation regardless of success/failure
        # This ensures we capture latency for all requests
        elapsed_seconds = perf_counter() - started_at
        ask_request_duration_seconds.labels(
            route="/ask",
            workflow_status=workflow_status,
            model_route=model_route,
        ).observe(elapsed_seconds)


@app.get("/healthz")
async def healthz():
    """Health check endpoint."""
    return {"status": "ok"}
