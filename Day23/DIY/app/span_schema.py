"""
Day 23 DIY: LLM Observability Trace Schema Contract

Defines span schemas for tracing LLM workflows.
Each span has strict requirements about what MUST be recorded,
what MAY be recorded, and what MUST NOT be recorded.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# Enums for span outcomes
# ============================================================================

class RetrieveOutcome(str, Enum):
    """Possible outcomes for retrieve span."""
    SUCCESS = "success"
    NO_RESULTS = "no_results"
    INDEX_ERROR = "index_error"
    TIMEOUT = "timeout"


class ModelOutcome(str, Enum):
    """Possible outcomes for model span."""
    SUCCESS = "success"
    RATE_LIMITED = "rate_limited"
    INVALID_REQUEST = "invalid_request"
    MODEL_ERROR = "model_error"
    TIMEOUT = "timeout"


class ToolOutcome(str, Enum):
    """Possible outcomes for tool span."""
    SUCCESS = "success"
    NOT_CALLED = "not_called"
    EXECUTION_FAILED = "execution_failed"
    TIMEOUT = "timeout"


class ValidateOutcome(str, Enum):
    """Possible outcomes for validate span."""
    PASSED = "passed"
    CITATION_MISSING = "citation_missing"
    SAFETY_VIOLATION = "safety_violation"
    VALIDATION_ERROR = "validation_error"


# ============================================================================
# Span Schemas - These match the tree in POST /ask
# ============================================================================

class RetrieveSpan(BaseModel):
    """
    RETRIEVE span: Document retrieval step.

    Required fields:
    - index_version: Semantic version of retrieval index
    - result_count: Number of documents returned
    - outcome: One of RetrieveOutcome

    Optional fields:
    - query_embedding_dimension: For debugging mismatch issues
    - latency_ms: How long retrieval took

    FORBIDDEN fields (must NEVER be included):
    - query (full text): Store hash or count only
    - document_snippets: Store metadata/reference only
    - user_id: Never include identity info
    """
    model_config = ConfigDict(extra="forbid")

    index_version: str = Field(..., description="e.g. 'v2.1.0' or 'sha256:abc123'")
    result_count: int = Field(..., ge=0, description="Number of documents returned")
    outcome: RetrieveOutcome = Field(..., description="Success or failure reason")

    query_embedding_dimension: Optional[int] = Field(
        None,
        description="Dimension of query embedding (for debugging)"
    )
    latency_ms: Optional[float] = Field(
        None,
        ge=0,
        description="Time spent in retrieval operation"
    )


class ModelSpan(BaseModel):
    """
    MODEL span: LLM inference step.

    Required fields:
    - model_version: Version/variant of the model
    - input_token_count: Number of input tokens
    - output_token_count: Number of output tokens
    - outcome: One of ModelOutcome

    Optional fields:
    - ttft_ms: Time to first token (if streaming)
    - inference_latency_ms: Total time for inference

    FORBIDDEN fields (must NEVER be included):
    - prompt (full text): Store hash or token count only
    - response (full text): Store hash or token count only
    - user_id, session_id: Never include identity info
    - sensitive_data: No PII, API keys, passwords
    """
    model_config = ConfigDict(extra="forbid")

    model_version: str = Field(..., description="e.g. 'gemini-3.6-flash' or 'claude-3.5-sonnet'")
    input_token_count: int = Field(..., ge=0, description="Tokens in the input")
    output_token_count: int = Field(..., ge=0, description="Tokens in the output")
    outcome: ModelOutcome = Field(..., description="Success or failure reason")

    ttft_ms: Optional[float] = Field(
        None,
        ge=0,
        description="Time to first token (for streaming models)"
    )
    inference_latency_ms: Optional[float] = Field(
        None,
        ge=0,
        description="Total inference latency"
    )


class ToolSpan(BaseModel):
    """
    TOOL span: External tool invocation (search, calculator, etc).

    Required fields:
    - tool_name: Name of the tool called
    - outcome: One of ToolOutcome

    Optional fields:
    - tool_version: Version of the tool
    - latency_ms: Execution time
    - input_hash: Hash of tool input (not the input itself)

    FORBIDDEN fields:
    - tool_input (full): Use hash or length only
    - tool_output (full): Use hash or length only
    - user_data: No identity info
    """
    model_config = ConfigDict(extra="forbid")

    tool_name: str = Field(..., description="Name of the tool")
    outcome: ToolOutcome = Field(..., description="Success or failure reason")

    tool_version: Optional[str] = Field(None, description="Version of the tool")
    latency_ms: Optional[float] = Field(None, ge=0, description="Tool execution time")
    input_hash: Optional[str] = Field(None, description="Hash of tool input (SHA256)")


class ValidateSpan(BaseModel):
    """
    VALIDATE span: Response validation and safety checks.

    Required fields:
    - citation_valid: Whether response can be traced to retrieval
    - safety_status: One of ValidateOutcome
    - outcome: Overall validation result

    Optional fields:
    - citation_count: How many citations found
    - validation_latency_ms: Time spent validating

    FORBIDDEN fields:
    - response_content: No response text
    - citation_sources: Reference metadata only
    - user_query: No user identity or data
    """
    model_config = ConfigDict(extra="forbid")

    citation_valid: bool = Field(..., description="Can response be traced to retrieval?")
    safety_status: str = Field(..., description="e.g. 'safe', 'warning', 'violation'")
    outcome: ValidateOutcome = Field(..., description="Overall validation result")

    citation_count: Optional[int] = Field(None, ge=0, description="Number of citations found")
    validation_latency_ms: Optional[float] = Field(None, ge=0, description="Validation time")


# ============================================================================
# Span Tree - Represents the full workflow trace
# ============================================================================

class SpanTree(BaseModel):
    """
    Complete trace of a single POST /ask request.

    Structure:
      POST /ask (root)
      ├── retrieve
      ├── model
      ├── tool (optional)
      └── validate
    """
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    request_id: str = Field(..., description="Unique request ID")
    timestamp: str = Field(..., description="ISO 8601 timestamp")

    retrieve: RetrieveSpan
    model: ModelSpan
    tool: Optional[ToolSpan] = None
    validate_span: ValidateSpan = Field(..., alias="validate")
