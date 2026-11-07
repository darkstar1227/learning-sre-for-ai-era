"""FastAPI app with metrics, structured logging, and OpenTelemetry traces."""

from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import generate_latest, REGISTRY

from app.tracing import setup_tracing
from app.logging_setup import setup_logging
from app.fixture import SimulatedRequest
from app.metrics import answer_requests


# Initialize tracing
setup_tracing(service_name="day21-api")
logger = setup_logging()


class AskRequest(BaseModel):
    """Request schema for /ask endpoint."""
    question: str = Field(..., min_length=1)


class AskResponse(BaseModel):
    """Response schema for /ask endpoint."""
    request_id: str
    answer: str
    outcome: str


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Middleware to manage X-Request-ID header and store in request state."""

    async def dispatch(self, request: Request, call_next):
        # Get or generate request_id from header
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.request_id = request_id

        # Process the request
        response = await call_next(request)

        # Echo request_id back in response headers
        response.headers["X-Request-ID"] = request_id
        return response


# Create FastAPI app
app = FastAPI(title="Day21 Observability Demo")

# Add middleware for request ID management
app.add_middleware(RequestContextMiddleware)


@app.get("/healthz")
async def healthz():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/metrics")
async def metrics_endpoint():
    """Prometheus metrics endpoint in text format."""
    metrics_output = generate_latest(REGISTRY)
    return Response(content=metrics_output, media_type="text/plain; version=0.0.4")


@app.post("/ask")
async def ask(request_body: AskRequest, request: Request):
    """
    Main /ask endpoint that simulates a retrieval + model workflow.

    Demonstrates:
    1. Request ID correlation across logs and traces
    2. Low-cardinality metrics labels (outcome, dependency)
    3. Structured JSON logs with event, request_id, dependency, outcome
    4. OpenTelemetry spans for workflow, retrieval, model steps
    """
    request_id = request.state.request_id
    question = request_body.question

    try:
        # Determine if this is a timeout fixture
        # "fixture: retriever timeout" in the question triggers timeout behavior
        is_timeout = "fixture: retriever timeout" in question.lower()

        # Create a simulated request that generates metrics, logs, and traces
        simulated_req = SimulatedRequest(
            request_id=request_id,
            dependency="retriever",
            timeout=is_timeout,
        )
        result = simulated_req.execute()

        # Determine outcome for metrics
        outcome = "upstream_timeout" if is_timeout else "success"
        answer_requests.labels(outcome=outcome).inc()

        return AskResponse(
            request_id=request_id,
            answer=f"Processed: {question}",
            outcome=outcome,
        )

    except Exception as exc:
        # Log exception and record failure in metrics
        logger.exception(f"Error processing request {request_id}", exc_info=True)
        answer_requests.labels(outcome="error").inc()

        return JSONResponse(
            status_code=500,
            content={
                "request_id": request_id,
                "detail": "Internal server error",
            },
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
