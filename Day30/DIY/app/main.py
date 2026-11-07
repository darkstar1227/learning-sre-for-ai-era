import logging
import uuid
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from app.chaos import ChaosContext, parse_chaos_context
from app.monitoring import (
    ask_outcomes_total,
    dependency_failures_total,
    metrics_app,
    record_ask_request,
)
from app.providers import ProviderTimeout
from app.workflow import AskResult, answer_workflow

app = FastAPI(title="Day30 Chaos Engineering Lab")

# Mount Prometheus metrics endpoint
app.mount("/metrics", metrics_app)

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Question to ask")


class AskResponse(BaseModel):
    request_id: str
    technical_status: str
    workflow_status: str
    task_status: str
    quality_status: str
    safety_status: str
    degraded: bool
    answer: Optional[str] = None
    reason: Optional[str] = None


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.post("/ask")
def ask(
    request: AskRequest,
    x_chaos_scenario: Optional[str] = Header(default=None),
    x_tenant: Optional[str] = Header(default=None),
) -> dict:
    request_id = str(uuid.uuid4())[:8]

    try:
        chaos = parse_chaos_context(x_chaos_scenario, x_tenant)
    except (PermissionError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    result: AskResult = answer_workflow(question=request.question, chaos=chaos)

    # Record metrics
    ask_outcomes_total.labels(
        workflow_status=result.workflow_status,
        degraded=str(result.degraded).lower(),
    ).inc()

    if result.reason == "model_provider_timeout":
        dependency_failures_total.labels(
            dependency="model_provider",
            failure_class="timeout",
        ).inc()

    # Log with structured format
    logger.info(
        "ask workflow finished",
        extra={
            "request_id": request_id,
            "chaos_scenario": chaos.scenario.value,
            "technical_status": result.technical_status,
            "workflow_status": result.workflow_status,
            "task_status": result.task_status,
            "degraded": result.degraded,
        },
    )

    response = AskResponse(
        request_id=request_id,
        technical_status=result.technical_status,
        workflow_status=result.workflow_status,
        task_status=result.task_status,
        quality_status=result.quality_status,
        safety_status=result.safety_status,
        degraded=result.degraded,
        answer=result.answer,
        reason=result.reason,
    )

    return response.model_dump()
