"""Workflow response schemas and contracts.

These schemas define the contract between workflow nodes.
Each failure mode must map to a distinct response status.
"""

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class ResponseStatus(str, Enum):
    """Status codes for workflow response contract."""

    SUCCESS = "success"
    INSUFFICIENT_CONTEXT = "insufficient_context"
    TOOL_VALIDATION_FAILED = "tool_validation_failed"
    QUALITY_FAILED = "quality_failed"
    LLM_TIMEOUT = "llm_timeout"
    PARSER_ERROR = "parser_error"
    AGENT_LOOP_LIMIT = "agent_loop_limit"
    DATABASE_UNAVAILABLE = "database_unavailable"
    TOOL_EXECUTION_ERROR = "tool_execution_error"


class Citation(BaseModel):
    """A citation reference in workflow response."""

    text: str = Field(..., description="Cited text snippet")
    source_id: str = Field(..., description="Document/retrieval source identifier")
    version: str = Field(default="1.0", description="Source version at time of retrieval")


class WorkflowResponse(BaseModel):
    """Standard AI workflow response contract.

    This schema ensures every response—success or failure—is machine-readable
    and actionable by downstream systems.
    """

    answer: Optional[str] = Field(
        default=None, description="Generated answer, null if not available"
    )
    status: ResponseStatus = Field(..., description="Status code for this response")
    requires_human_review: bool = Field(
        default=False, description="Flag for escalation to review queue"
    )
    citations: list[Citation] = Field(
        default_factory=list, description="Citations supporting the answer"
    )
    error_message: Optional[str] = Field(
        default=None, description="Details if status is not SUCCESS"
    )
    trace_id: Optional[str] = Field(
        default=None, description="Request trace ID for debugging"
    )
    retrieval_doc_count: int = Field(
        default=0, description="Number of documents retrieved"
    )
    retrieval_version: Optional[str] = Field(
        default=None, description="Embedding/retrieval index version used"
    )
    model_name: Optional[str] = Field(
        default=None, description="LLM model identifier used for this request"
    )
    model_version: Optional[str] = Field(
        default=None, description="LLM version/checkpoint identifier"
    )


class ToolAction(BaseModel):
    """Tool action request from agent."""

    action_type: str = Field(..., description="Type of action: read, write, delete, etc.")
    target: str = Field(..., description="Target resource identifier")
    params: dict[str, Any] = Field(default_factory=dict, description="Action parameters")
    idempotency_key: Optional[str] = Field(
        default=None, description="Idempotency key to prevent duplicate writes"
    )


class ToolValidationResult(BaseModel):
    """Result of tool action validation."""

    valid: bool = Field(..., description="Whether action passes validation")
    schema_errors: list[str] = Field(
        default_factory=list, description="Schema validation errors if any"
    )
    permission_granted: bool = Field(
        default=False, description="Whether caller has permission for this action"
    )
    action: Optional[ToolAction] = Field(
        default=None, description="The original action if valid"
    )


class RetrievalResult(BaseModel):
    """Result from retrieval node."""

    documents: list[dict[str, Any]] = Field(default_factory=list)
    doc_count: int = Field(default=0)
    index_version: str = Field(default="unknown")
    total_score: float = Field(
        default=0.0, description="Aggregate relevance score, 0-1"
    )
    has_sufficient_context: bool = Field(
        default=False, description="Whether retrieval found enough context"
    )
