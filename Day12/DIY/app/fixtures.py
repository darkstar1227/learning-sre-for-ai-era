"""Test fixtures for AI workflow failure modes.

These fixtures define input data and expected output for each failure mode.
They serve as regression tests and documentation of expected behavior.
"""

from app.schemas import (
    WorkflowResponse,
    ResponseStatus,
    Citation,
    RetrievalResult,
    ToolValidationResult,
    ToolAction,
)


class WorkflowFixture:
    """A test fixture with input, expected output, and description."""

    def __init__(
        self,
        name: str,
        node: str,
        description: str,
        input_data: dict,
        expected_response: WorkflowResponse,
    ):
        self.name = name
        self.node = node
        self.description = description
        self.input_data = input_data
        self.expected_response = expected_response


# Fixture 1: Empty retrieval - retrieve node returns no documents
FIXTURE_EMPTY_RETRIEVAL = WorkflowFixture(
    name="empty_retrieval",
    node="retrieve",
    description=(
        "User query matches no documents in knowledge base. "
        "System must not fabricate answer from general knowledge."
    ),
    input_data={
        "query": "What is the refund policy for wingless dragons?",
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "retrieval_threshold": 0.5,
        "documents_returned": [],
    },
    expected_response=WorkflowResponse(
        answer=None,
        status=ResponseStatus.INSUFFICIENT_CONTEXT,
        requires_human_review=False,
        citations=[],
        error_message="No documents found matching query criteria",
        retrieval_doc_count=0,
        retrieval_version="index-v1.0",
    ),
)


# Fixture 2: LLM timeout - model_output node exceeds timeout
FIXTURE_LLM_TIMEOUT = WorkflowFixture(
    name="llm_timeout",
    node="model_output",
    description=(
        "LLM call takes longer than timeout threshold (e.g., 30s). "
        "System must return structured error, not partial response."
    ),
    input_data={
        "model": "gemini-2.0-flash",
        "prompt": "Please provide a detailed analysis...",  # Long prompt triggers slow response
        "timeout_ms": 30000,
        "actual_duration_ms": 31500,
    },
    expected_response=WorkflowResponse(
        answer=None,
        status=ResponseStatus.LLM_TIMEOUT,
        requires_human_review=True,
        citations=[],
        error_message="LLM call exceeded 30000ms timeout",
        trace_id="trace_xyz_timeout",
        model_name="gemini-2.0-flash",
        model_version="20250101",
    ),
)


# Fixture 3: Tool schema mismatch - tool_call node receives invalid JSON structure
FIXTURE_TOOL_SCHEMA_MISMATCH = WorkflowFixture(
    name="tool_schema_mismatch",
    node="tool_call",
    description=(
        "LLM generates tool call with wrong field types or missing required fields. "
        "E.g., expects 'user_id: int' but receives 'user_id: string'."
    ),
    input_data={
        "generated_json": {
            "action": "update_order",
            "user_id": "user-12345",  # Should be int, not string
            "order_id": 9999,
            "amount": "99.99",  # Should be float, not string
        },
        "expected_schema": {
            "action": "string",
            "user_id": "int",
            "order_id": "int",
            "amount": "float",
        },
    },
    expected_response=WorkflowResponse(
        answer=None,
        status=ResponseStatus.TOOL_VALIDATION_FAILED,
        requires_human_review=True,
        citations=[],
        error_message="Tool schema validation failed",
        trace_id="trace_schema_mismatch",
    ),
)


# Fixture 4: Parser error - response parsing fails
FIXTURE_PARSER_ERROR = WorkflowFixture(
    name="parser_error",
    node="response",
    description=(
        "LLM response cannot be parsed as valid JSON or structured format. "
        "System must not crash or return malformed data to client."
    ),
    input_data={
        "raw_response": '{"answer": "The refund is {incomplete_json}"',  # Malformed JSON
        "format_expected": "json",
    },
    expected_response=WorkflowResponse(
        answer=None,
        status=ResponseStatus.PARSER_ERROR,
        requires_human_review=True,
        citations=[],
        error_message="Failed to parse response as JSON: Expecting ',' delimiter",
        trace_id="trace_parser_error",
    ),
)


# Fixture 5: Agent loop limit - agent exceeds max retries
FIXTURE_AGENT_LOOP_LIMIT = WorkflowFixture(
    name="agent_loop_limit",
    node="agent_loop",
    description=(
        "Agent exhausts retry budget trying to correct tool call failures. "
        "Must break loop and return failure state with full trace."
    ),
    input_data={
        "max_retries": 3,
        "initial_action": "query_database",
        "retry_sequence": [
            {"attempt": 1, "error": "connection_timeout"},
            {"attempt": 2, "error": "connection_timeout"},
            {"attempt": 3, "error": "connection_timeout"},
            # Would attempt 4, but limit reached
        ],
    },
    expected_response=WorkflowResponse(
        answer=None,
        status=ResponseStatus.AGENT_LOOP_LIMIT,
        requires_human_review=True,
        citations=[],
        error_message="Agent exhausted 3 retry attempts. Last error: connection_timeout",
        trace_id="trace_agent_loop_limit",
    ),
)


# Fixture 6: Hallucination in citations - response cites docs that don't exist
FIXTURE_HALLUCINATED_CITATION = WorkflowFixture(
    name="hallucinated_citation",
    node="response",
    description=(
        "LLM generates citation to document that was not in retrieval results. "
        "Classic hallucination: plausible reference, wrong source."
    ),
    input_data={
        "retrieved_documents": [
            {
                "id": "doc_001",
                "title": "Company Refund Policy 2024",
                "content": "Standard refunds take 5-7 business days.",
            }
        ],
        "llm_response": {
            "answer": "According to our policy document, refunds are processed within 3 business days.",
            "citations": [
                {
                    "text": "refunds are processed within 3 business days",
                    "source_id": "doc_premium_24h",  # This document doesn't exist!
                    "version": "2024",
                }
            ],
        },
    },
    expected_response=WorkflowResponse(
        answer=None,  # Don't return potentially false answer
        status=ResponseStatus.QUALITY_FAILED,
        requires_human_review=True,
        citations=[],
        error_message="Citation source not found in retrieval results: doc_premium_24h",
        trace_id="trace_hallucination",
    ),
)


# Fixture 7: Stale embedding index - retrieval uses outdated embeddings
FIXTURE_STALE_INDEX = WorkflowFixture(
    name="stale_index",
    node="retrieve",
    description=(
        "Documents were updated but embedding index hasn't been rebuilt. "
        "Retrieval returns outdated versions of documents."
    ),
    input_data={
        "query": "What is current COVID leave policy?",
        "current_index_version": "index-v0.8",  # Created 3 months ago
        "latest_document_version": "doc-v2.1",  # Updated last week
        "documents_in_index": 500,
        "documents_actual": 542,
    },
    expected_response=WorkflowResponse(
        answer=None,
        status=ResponseStatus.INSUFFICIENT_CONTEXT,
        requires_human_review=True,
        citations=[],
        error_message="Retrieval index is stale (v0.8). Current docs: v2.1. Re-indexing required.",
        retrieval_version="index-v0.8",
        trace_id="trace_stale_index",
    ),
)


# Fixture 8: Model version regression - same input, different quality
FIXTURE_MODEL_REGRESSION = WorkflowFixture(
    name="model_regression",
    node="model_output",
    description=(
        "Model was updated; baseline evaluation case now produces lower quality. "
        "Must be caught by regression test suite, not auto-promoted to production."
    ),
    input_data={
        "evaluation_case_id": "eval_case_789",
        "query": "Summarize customer satisfaction trends",
        "documents": [
            {"id": "doc_1", "content": "Q3 CSAT: 85%, Q4: 82%"},
            {"id": "doc_2", "content": "Complaints about shipping delays increased 15%"},
        ],
        "old_model": "gpt-4-turbo-v1",
        "new_model": "gpt-4-turbo-v2",
        "old_quality_score": 8.5,
        "new_quality_score": 6.2,  # Lower! Regression detected
    },
    expected_response=WorkflowResponse(
        answer="Customer satisfaction declined from Q3 to Q4, primarily due to shipping delays.",
        status=ResponseStatus.SUCCESS,  # Response itself is valid, but quality regressed
        requires_human_review=True,  # Must review before production deployment
        citations=[
            Citation(text="Q3 CSAT: 85%, Q4: 82%", source_id="doc_1", version="current"),
            Citation(
                text="Complaints about shipping delays increased 15%",
                source_id="doc_2",
                version="current",
            ),
        ],
        model_name="gpt-4-turbo-v2",
        model_version="20250101",
        trace_id="trace_regression_eval_789",
    ),
)


ALL_FIXTURES = [
    FIXTURE_EMPTY_RETRIEVAL,
    FIXTURE_LLM_TIMEOUT,
    FIXTURE_TOOL_SCHEMA_MISMATCH,
    FIXTURE_PARSER_ERROR,
    FIXTURE_AGENT_LOOP_LIMIT,
    FIXTURE_HALLUCINATED_CITATION,
    FIXTURE_STALE_INDEX,
    FIXTURE_MODEL_REGRESSION,
]


def get_fixture_by_name(name: str) -> WorkflowFixture | None:
    """Look up a fixture by name."""
    for fixture in ALL_FIXTURES:
        if fixture.name == name:
            return fixture
    return None


def get_fixtures_by_node(node: str) -> list[WorkflowFixture]:
    """Get all fixtures for a specific workflow node."""
    return [f for f in ALL_FIXTURES if f.node == node]


def get_required_fixtures() -> list[WorkflowFixture]:
    """Get the minimum 4 required fixtures from Day 12 spec."""
    required_names = [
        "empty_retrieval",
        "llm_timeout",
        "tool_schema_mismatch",
        "parser_error",
    ]
    return [f for f in ALL_FIXTURES if f.name in required_names]


def get_agent_guardrail_fixtures() -> list[WorkflowFixture]:
    """Get fixtures testing agent loop guardrails."""
    return [f for f in ALL_FIXTURES if f.name == "agent_loop_limit"]
