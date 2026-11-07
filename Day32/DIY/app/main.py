"""
FastAPI application with OpenTelemetry instrumentation.
This is a minimal Lab scaffolding where the same workflow can be observed by Langfuse and LangSmith.
"""

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from opentelemetry import trace

from app.config import settings
from app.telemetry.ai_context import AITraceContext
from app.telemetry.otel_setup import setup_otel_to_collector, setup_otel_to_langfuse


# Global tracer (set during startup)
tracer: trace.Tracer = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize observability on startup, cleanup on shutdown."""
    global tracer

    # Setup observability based on configuration
    if settings.observability_mode == "langfuse":
        print("🚀 Starting with Langfuse observability...")
        tracer = setup_otel_to_langfuse(
            langfuse_base_url=settings.langfuse_base_url,
            langfuse_public_key=settings.langfuse_public_key,
            langfuse_secret_key=settings.langfuse_secret_key,
            service_name=settings.service_name,
        )
    elif settings.observability_mode == "collector":
        print("🚀 Starting with OpenTelemetry Collector...")
        tracer = setup_otel_to_collector(
            collector_otlp_endpoint=settings.otel_collector_endpoint,
            service_name=settings.service_name,
        )
    else:
        print("⚠️  Starting without instrumentation (observability_mode=disabled)")
        tracer = trace.get_tracer(settings.service_name)

    yield

    # Cleanup: flush any pending spans
    tracer_provider = trace.get_tracer_provider()
    if hasattr(tracer_provider, "force_flush"):
        tracer_provider.force_flush()


app = FastAPI(
    title="Day32 DIY: Langfuse vs LangSmith Lab",
    version=settings.service_version,
    lifespan=lifespan,
)


# Schemas
class AskRequest:
    """Input schema for the /ask endpoint."""
    def __init__(self, question: str):
        if not question or len(question.strip()) == 0:
            raise ValueError("question must be non-empty")
        self.question = question


class AskResponse:
    """Output schema for the /ask endpoint."""
    def __init__(self, request_id: str, answer: str, quality_status: str):
        self.request_id = request_id
        self.answer = answer
        self.quality_status = quality_status


# Business logic (from article Step 4)
def retrieve(question: str):
    """Mock retrieval step."""
    return [
        f"Document 1 relevant to: {question}",
        f"Document 2 relevant to: {question}",
    ]


def call_model(question: str, documents: list) -> str:
    """Mock LLM call step."""
    # In production, this would call the actual LLM
    context = "\n".join(documents)
    return f"Answer to '{question}' based on: {context[:50]}..."


def validate(answer: str, documents: list) -> dict:
    """Mock validation step."""
    # In production, this would run quality checks
    return {
        "status": "passed" if answer else "failed",
        "is_grounded": len(documents) > 0,
    }


def answer_workflow(question: str, request_id: str) -> dict:
    """
    Main AI workflow (from article Step 4).
    Uses OpenTelemetry spans to structure the workflow.
    """
    if tracer is None:
        raise RuntimeError("Tracer not initialized")

    with tracer.start_as_current_span("ai.workflow") as workflow:
        # Set Langfuse-compatible attributes
        workflow.set_attribute("langfuse.trace.name", "answer-workflow")
        workflow.set_attribute("langfuse.trace.metadata.request_id", request_id)
        workflow.set_attribute("langfuse.trace.metadata.workflow_version", "v1")

        # Also set generic attributes for other platforms
        workflow.set_attribute("ai.workflow.question", question)
        workflow.set_attribute("service.version", settings.service_version)

        # Retrieval span
        with tracer.start_as_current_span("retrieval") as retrieval:
            documents = retrieve(question)
            retrieval.set_attribute("retrieval.result_count", len(documents))
            retrieval.set_attribute("langfuse.level", "retrieval")

        # Validator span (containing model call)
        with tracer.start_as_current_span("validator") as validator:
            answer = call_model(question, documents)
            result = validate(answer, documents)
            validator.set_attribute("ai.quality_status", result["status"])
            validator.set_attribute("ai.grounded", result["is_grounded"])

        workflow.set_attribute("ai.workflow.status", "completed")

        return {
            "request_id": request_id,
            "answer": answer,
            "quality_status": result["status"],
        }


# Endpoints
@app.get("/healthz")
async def healthz():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/ask")
async def ask_endpoint(request: dict):
    """
    Ask endpoint: receives question, returns answer.
    Observes the full workflow via OpenTelemetry.
    """
    # Validate input
    question = request.get("question", "").strip()
    if not question:
        raise HTTPException(status_code=422, detail="question is required and non-empty")

    # Generate request ID for correlation
    request_id = str(uuid.uuid4())
    trace_id = str(uuid.uuid4())

    try:
        # Run the workflow
        result = answer_workflow(question, request_id)

        # Return response
        return {
            "request_id": result["request_id"],
            "trace_id": trace_id,
            "answer": result["answer"],
            "quality_status": result["quality_status"],
        }

    except Exception as e:
        # Log error and return 500
        print(f"Error in ask workflow: {e}")
        raise HTTPException(status_code=500, detail="Workflow execution failed")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
