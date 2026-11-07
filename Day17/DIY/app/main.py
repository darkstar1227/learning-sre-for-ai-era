"""FastAPI application for Day 17 DIY: SLI Fixture Testing with Middleware.

Implements the complete Day 17 article requirements:
1. Middleware to measure complete request lifecycle
2. Handler responsible for providing technical_status
3. Prometheus metrics (low-cardinality labels only)
4. Structured logging of outcomes
"""

import json
import logging
from time import perf_counter
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from prometheus_client import Counter, Histogram, generate_latest
from fastapi.responses import Response

from app.schemas import AskRequest, AskResponse, SLIEvent, DependencyOutcome

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}',
)
logger = logging.getLogger("sli")

app = FastAPI(title="Day 17 DIY: SLI Testing")

# In-memory event log (for testing; production sends to observability platform)
event_log = []

# =============================================================================
# Prometheus Metrics (Day 17 Article: Low-cardinality labels only)
# =============================================================================

REQUESTS = Counter(
    "answer_requests_total",
    "Completed answer requests grouped by technical outcome.",
    ["route", "technical_status", "release_channel"],
)

LATENCY = Histogram(
    "answer_request_duration_seconds",
    "End-to-end HTTP request duration for the answer route.",
    ["route", "release_channel"],
    buckets=(0.1, 0.3, 0.5, 1, 2, 3, 5, 10),
)


# =============================================================================
# Domain Exceptions (Step 7 requirement: explicit exception types)
# =============================================================================


class ProviderTimeoutError(Exception):
    """Raised when LLM provider times out."""

    pass


class ProviderError(Exception):
    """Raised when LLM provider returns an error."""

    pass


class OutputValidationError(Exception):
    """Raised when provider output is invalid."""

    pass


# =============================================================================
# SLI Classification Function (Step 1 requirement)
# =============================================================================


def classify_status(status_code: int, error_kind: Optional[str]) -> str:
    """Classify HTTP status code and error kind into technical_status.

    This pure function makes the classification logic testable without
    needing to call external provider.
    """
    if error_kind == "provider_timeout":
        return "dependency_timeout"
    if error_kind == "provider_error":
        return "dependency_error"
    if error_kind == "invalid_output":
        return "validation_error"
    if status_code >= 500:
        return "internal_error"
    return "success"


# =============================================================================
# Middleware: Record SLI for all requests (Day 17 Article Section ⑤)
# =============================================================================


@app.middleware("http")
async def record_request_sli(request: Request, call_next):
    """Middleware to measure complete request lifecycle.

    Article requirement:
    - Measure from request entry to response return
    - Use request.state to pass technical_status from handler to middleware
    - Record both metrics and structured logs
    - Skip non-/ask endpoints to avoid cardinality explosion
    """
    # Skip non-/ask endpoints to avoid cardinality issues
    if request.url.path != "/ask":
        return await call_next(request)

    started = perf_counter()
    technical_status = "internal_error"
    release_channel = "stable"

    try:
        response = await call_next(request)
        # Handler sets technical_status on request.state
        technical_status = getattr(
            request.state,
            "technical_status",
            "success" if response.status_code < 500 else "internal_error",
        )
        release_channel = getattr(request.state, "release_channel", "stable")
        return response
    except Exception:
        logger.exception("unhandled request failure")
        raise
    finally:
        elapsed_seconds = perf_counter() - started
        route = request.url.path

        # Record Prometheus metrics
        REQUESTS.labels(route, technical_status, release_channel).inc()
        LATENCY.labels(route, release_channel).observe(elapsed_seconds)

        # Structured log (JSON format for ingestion)
        logger.info(
            "request_outcome",
            extra={
                "route": route,
                "technical_status": technical_status,
                "latency_ms": round(elapsed_seconds * 1000, 2),
                "release_channel": release_channel,
            },
        )


# =============================================================================
# Endpoints
# =============================================================================


@app.get("/healthz")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/ask")
async def ask(question: AskRequest, request: Request) -> AskResponse:
    """Ask endpoint that demonstrates SLI recording with proper exception handling.

    Article requirement (Section ⑤):
    - Handler knows about provider-specific failures
    - Handler uses domain exceptions to classify failures
    - Handler sets request.state.technical_status for middleware
    - Don't mix business logic classification with web framework decisions
    """
    request.state.release_channel = "stable"
    start_time = perf_counter()

    try:
        # Simulate LLM provider call with mock routing
        answer = await answer_policy_question(question.question)
        dependency_outcome = DependencyOutcome(
            provider="llm_provider", status="success", latency_ms=100
        )

    except ProviderTimeoutError as exc:
        # Handler classifies timeout; middleware will record it
        request.state.technical_status = "dependency_timeout"
        dependency_outcome = DependencyOutcome(
            provider="llm_provider", status="timeout", latency_ms=30000
        )
        elapsed_ms = int((perf_counter() - start_time) * 1000)
        event = SLIEvent(
            route="/ask",
            status="timeout",
            latency_ms=elapsed_ms,
            dependency="llm_provider",
            dependency_outcome=dependency_outcome,
        )
        event_log.append(event.model_dump())
        raise HTTPException(
            status_code=504, detail="upstream timeout"
        ) from exc

    except ProviderError as exc:
        # Handler classifies provider error; middleware will record it
        request.state.technical_status = "dependency_error"
        dependency_outcome = DependencyOutcome(
            provider="llm_provider", status="error", latency_ms=5000
        )
        elapsed_ms = int((perf_counter() - start_time) * 1000)
        event = SLIEvent(
            route="/ask",
            status="error",
            latency_ms=elapsed_ms,
            dependency="llm_provider",
            dependency_outcome=dependency_outcome,
        )
        event_log.append(event.model_dump())
        raise HTTPException(status_code=502, detail="dependency error") from exc

    except OutputValidationError as exc:
        # Handler classifies validation error; middleware will record it
        request.state.technical_status = "validation_error"
        dependency_outcome = DependencyOutcome(
            provider="llm_provider", status="error", latency_ms=100
        )
        elapsed_ms = int((perf_counter() - start_time) * 1000)
        event = SLIEvent(
            route="/ask",
            status="malformed",
            latency_ms=elapsed_ms,
            dependency="llm_provider",
            dependency_outcome=dependency_outcome,
        )
        event_log.append(event.model_dump())
        raise HTTPException(status_code=502, detail="invalid upstream response") from exc

    except Exception:
        # Catch-all for unexpected errors
        request.state.technical_status = "internal_error"
        raise

    # Success case: record event
    elapsed_ms = int((perf_counter() - start_time) * 1000)
    event = SLIEvent(
        route="/ask",
        status="good",
        latency_ms=elapsed_ms,
        dependency="llm_provider",
        dependency_outcome=dependency_outcome,
    )
    event_log.append(event.model_dump())

    request.state.technical_status = "success"
    return AskResponse(answer=answer)


async def answer_policy_question(question: str) -> str:
    """Mock LLM provider call.

    In DIY testing, we simulate different outcomes by detecting keywords.
    In production, this would call real LLM provider.
    """
    # Mock routing based on question keyword (Step 4 requirement)
    if "timeout" in question.lower():
        # Simulate provider timeout
        raise ProviderTimeoutError("LLM provider did not respond within timeout")

    if "error" in question.lower():
        # Simulate provider error (not timeout)
        raise ProviderError("LLM provider returned error")

    if "malformed" in question.lower():
        # Simulate invalid output (Step 5 requirement: HTTP 200 but missing fields)
        raise OutputValidationError("Provider response missing required fields")

    # Normal response
    return f"Mock response to: {question}"


# =============================================================================
# Observability Endpoints (for testing/verification)
# =============================================================================


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type="text/plain")


@app.get("/events")
async def get_events(limit: int = 100):
    """Retrieve recorded SLI events (for testing/verification).

    In production, this would be in observability platform,
    not served from application.
    """
    return {"events": event_log[-limit:], "count": len(event_log)}


@app.post("/events/reset")
async def reset_events():
    """Reset event log (for testing)."""
    global event_log
    event_log.clear()
    return {"status": "reset"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
