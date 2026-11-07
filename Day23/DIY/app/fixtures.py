"""
Test fixtures demonstrating various span tree scenarios.
Each fixture represents a real-world failure mode and tests
whether the span tree can accurately capture it.
"""

from app.span_schema import (
    SpanTree,
    RetrieveSpan, RetrieveOutcome,
    ModelSpan, ModelOutcome,
    ToolSpan, ToolOutcome,
    ValidateSpan, ValidateOutcome,
)


# ============================================================================
# Fixture 1: Happy path - all steps succeed
# ============================================================================

FIXTURE_SUCCESS = SpanTree(
    request_id="req_20250401_001",
    timestamp="2025-04-01T12:00:00Z",
    retrieve=RetrieveSpan(
        index_version="v2.1.0",
        result_count=3,
        outcome=RetrieveOutcome.SUCCESS,
        query_embedding_dimension=1536,
        latency_ms=45.3,
    ),
    model=ModelSpan(
        model_version="gemini-3.6-flash",
        input_token_count=512,
        output_token_count=128,
        outcome=ModelOutcome.SUCCESS,
        ttft_ms=50,
        inference_latency_ms=150.5,
    ),
    tool=None,
    validate=ValidateSpan(
        citation_valid=True,
        safety_status="safe",
        outcome=ValidateOutcome.PASSED,
        citation_count=2,
        validation_latency_ms=10.2,
    ),
)


# ============================================================================
# Fixture 2: Retrieval finds nothing
# ============================================================================

FIXTURE_RETRIEVE_NO_RESULTS = SpanTree(
    request_id="req_20250401_002",
    timestamp="2025-04-01T12:05:00Z",
    retrieve=RetrieveSpan(
        index_version="v2.1.0",
        result_count=0,
        outcome=RetrieveOutcome.NO_RESULTS,
        query_embedding_dimension=1536,
        latency_ms=35.1,
    ),
    model=ModelSpan(
        model_version="gemini-3.6-flash",
        input_token_count=256,
        output_token_count=80,
        outcome=ModelOutcome.SUCCESS,
        ttft_ms=45,
        inference_latency_ms=120.0,
    ),
    tool=None,
    validate=ValidateSpan(
        citation_valid=False,
        safety_status="safe",
        outcome=ValidateOutcome.CITATION_MISSING,
        citation_count=0,
        validation_latency_ms=5.0,
    ),
)


# ============================================================================
# Fixture 3: Model returns rate limit error
# ============================================================================

FIXTURE_MODEL_RATE_LIMITED = SpanTree(
    request_id="req_20250401_003",
    timestamp="2025-04-01T12:10:00Z",
    retrieve=RetrieveSpan(
        index_version="v2.1.0",
        result_count=4,
        outcome=RetrieveOutcome.SUCCESS,
        latency_ms=40.0,
    ),
    model=ModelSpan(
        model_version="gemini-3.6-flash",
        input_token_count=512,
        output_token_count=0,
        outcome=ModelOutcome.RATE_LIMITED,
        inference_latency_ms=2500.0,  # Long wait before rate limit error
    ),
    tool=None,
    validate=ValidateSpan(
        citation_valid=False,
        safety_status="unknown",
        outcome=ValidateOutcome.VALIDATION_ERROR,
        citation_count=0,
        validation_latency_ms=0.0,
    ),
)


# ============================================================================
# Fixture 4: Tool execution fails (PRIMARY TEST CASE)
# ============================================================================

FIXTURE_TOOL_EXECUTION_FAILED = SpanTree(
    request_id="req_20250401_004",
    timestamp="2025-04-01T12:15:00Z",
    retrieve=RetrieveSpan(
        index_version="v2.1.0",
        result_count=2,
        outcome=RetrieveOutcome.SUCCESS,
        latency_ms=38.0,
    ),
    model=ModelSpan(
        model_version="gemini-3.6-flash",
        input_token_count=512,
        output_token_count=256,
        outcome=ModelOutcome.SUCCESS,
        ttft_ms=60,
        inference_latency_ms=200.0,
    ),
    tool=ToolSpan(
        tool_name="web_search",
        outcome=ToolOutcome.EXECUTION_FAILED,
        tool_version="v1.2.0",
        latency_ms=5000.0,  # Tool timed out
        input_hash="sha256:e3b0c44298fc1c14",  # Hash of tool input
    ),
    validate=ValidateSpan(
        citation_valid=False,
        safety_status="safe",
        outcome=ValidateOutcome.VALIDATION_ERROR,
        citation_count=1,
        validation_latency_ms=8.0,
    ),
)


# ============================================================================
# Fixture 5: Validation fails - safety violation
# ============================================================================

FIXTURE_VALIDATE_SAFETY_VIOLATION = SpanTree(
    request_id="req_20250401_005",
    timestamp="2025-04-01T12:20:00Z",
    retrieve=RetrieveSpan(
        index_version="v2.1.0",
        result_count=5,
        outcome=RetrieveOutcome.SUCCESS,
        latency_ms=42.0,
    ),
    model=ModelSpan(
        model_version="gemini-3.6-flash",
        input_token_count=512,
        output_token_count=200,
        outcome=ModelOutcome.SUCCESS,
        ttft_ms=55,
        inference_latency_ms=180.0,
    ),
    tool=None,
    validate=ValidateSpan(
        citation_valid=True,
        safety_status="violation",
        outcome=ValidateOutcome.SAFETY_VIOLATION,
        citation_count=3,
        validation_latency_ms=25.0,  # Safety check took longer
    ),
)


# ============================================================================
# Fixture 6: Retrieval timeout
# ============================================================================

FIXTURE_RETRIEVE_TIMEOUT = SpanTree(
    request_id="req_20250401_006",
    timestamp="2025-04-01T12:25:00Z",
    retrieve=RetrieveSpan(
        index_version="v2.1.0",
        result_count=0,
        outcome=RetrieveOutcome.TIMEOUT,
        latency_ms=30000.0,  # Query hit time limit
    ),
    model=ModelSpan(
        model_version="gemini-3.6-flash",
        input_token_count=256,  # Fallback: use only user query
        output_token_count=90,
        outcome=ModelOutcome.SUCCESS,
        ttft_ms=40,
        inference_latency_ms=140.0,
    ),
    tool=None,
    validate=ValidateSpan(
        citation_valid=False,
        safety_status="safe",
        outcome=ValidateOutcome.CITATION_MISSING,
        citation_count=0,
        validation_latency_ms=5.0,
    ),
)


# ============================================================================
# Fixture 7: Complete failure - model error prevents further processing
# ============================================================================

FIXTURE_MODEL_ERROR = SpanTree(
    request_id="req_20250401_007",
    timestamp="2025-04-01T12:30:00Z",
    retrieve=RetrieveSpan(
        index_version="v2.1.0",
        result_count=3,
        outcome=RetrieveOutcome.SUCCESS,
        latency_ms=45.0,
    ),
    model=ModelSpan(
        model_version="gemini-3.6-flash",
        input_token_count=512,
        output_token_count=0,
        outcome=ModelOutcome.MODEL_ERROR,
        inference_latency_ms=250.0,
    ),
    tool=None,
    validate=ValidateSpan(
        citation_valid=False,
        safety_status="unknown",
        outcome=ValidateOutcome.VALIDATION_ERROR,
        citation_count=0,
        validation_latency_ms=0.0,
    ),
)


# ============================================================================
# Fixture 8: Tool not called because precondition wasn't met
# ============================================================================

FIXTURE_TOOL_NOT_CALLED = SpanTree(
    request_id="req_20250401_008",
    timestamp="2025-04-01T12:35:00Z",
    retrieve=RetrieveSpan(
        index_version="v2.1.0",
        result_count=5,
        outcome=RetrieveOutcome.SUCCESS,
        latency_ms=40.0,
    ),
    model=ModelSpan(
        model_version="gemini-3.6-flash",
        input_token_count=512,
        output_token_count=150,
        outcome=ModelOutcome.SUCCESS,
        ttft_ms=50,
        inference_latency_ms=160.0,
    ),
    tool=ToolSpan(
        tool_name="web_search",
        outcome=ToolOutcome.NOT_CALLED,
        tool_version="v1.2.0",
        latency_ms=0.0,
    ),
    validate=ValidateSpan(
        citation_valid=True,
        safety_status="safe",
        outcome=ValidateOutcome.PASSED,
        citation_count=4,
        validation_latency_ms=10.0,
    ),
)


# ============================================================================
# Collection of all fixtures for testing
# ============================================================================

FIXTURES = {
    "success": FIXTURE_SUCCESS,
    "retrieve_no_results": FIXTURE_RETRIEVE_NO_RESULTS,
    "model_rate_limited": FIXTURE_MODEL_RATE_LIMITED,
    "tool_execution_failed": FIXTURE_TOOL_EXECUTION_FAILED,
    "validate_safety_violation": FIXTURE_VALIDATE_SAFETY_VIOLATION,
    "retrieve_timeout": FIXTURE_RETRIEVE_TIMEOUT,
    "model_error": FIXTURE_MODEL_ERROR,
    "tool_not_called": FIXTURE_TOOL_NOT_CALLED,
}
