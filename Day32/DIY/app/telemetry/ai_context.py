"""
Neutral AI Telemetry Schema
Defined independently of any observability platform (LangSmith, Langfuse, OTel, etc.)
Maps to each platform on export.
"""

from dataclasses import dataclass


@dataclass
class AITraceContext:
    """
    AI workflow context for a single request.

    This schema is intentionally neutral — not coupled to LangSmith, Langfuse, or OTel.
    It can be mapped to each platform's attributes, events, or spans on export.
    """

    # Business/Request Identity
    request_id: str
    trace_id: str
    task_id: str

    # Workflow & Component Versioning
    workflow_name: str
    workflow_version: str
    prompt_version: str
    model_provider: str
    model_name: str
    retrieval_index_version: str
    service_version: str
    deployment_id: str

    # Status Fields
    technical_status: str  # "success", "timeout", "error", "degraded"
    quality_status: str    # "passed", "failed", "uncertain"
    safety_status: str     # "safe", "unsafe", "review_needed"
    task_status: str       # "completed", "partial", "failed"
    tool_policy_decision: str  # "approved", "rejected", "requires_review"

    # Observability Flags
    degraded: bool = False

    @classmethod
    def from_request(cls, request_id: str, trace_id: str) -> "AITraceContext":
        """
        Minimal constructor for test/demo purposes.
        Production should pass all fields explicitly.
        """
        return cls(
            request_id=request_id,
            trace_id=trace_id,
            task_id=f"{request_id}-task",
            workflow_name="answer-workflow",
            workflow_version="v1",
            prompt_version="v1",
            model_provider="google",
            model_name="gemini-2.0-flash",
            retrieval_index_version="v1",
            service_version="v0.1.0",
            deployment_id="lab-local",
            technical_status="pending",
            quality_status="pending",
            safety_status="pending",
            task_status="pending",
            tool_policy_decision="pending",
        )
