"""Reference implementations of AI workflow failure-mode handling.

These functions implement the patterns discussed in Day 12:
- Empty retrieval handling
- LLM timeout with deadline management
- Tool schema validation
- Response parser with citation verification
- Agent loop guardrails

These are meant as educational examples and can serve as templates for actual
production implementations. This DIY project focuses on testing these patterns
via fixtures rather than running them against real services.
"""

import json
from time import monotonic
from typing import Optional
from pydantic import ValidationError

from app.schemas import (
    WorkflowResponse,
    ResponseStatus,
    ToolAction,
    ToolValidationResult,
)


def handle_retrieval(documents: list[dict], index_version: str) -> dict:
    """Handle empty retrieval result.

    When retrieval returns no documents, this ensures the system does not
    fabricate an answer from general knowledge. Instead, it returns a
    structured response indicating insufficient context.

    Args:
        documents: Retrieved documents from knowledge base
        index_version: Version identifier of the retrieval index

    Returns:
        Dict with answer=None and status=insufficient_context if no docs,
        otherwise returns {status: "continue"} to proceed with workflow
    """
    if not documents:
        return {
            "answer": None,
            "status": ResponseStatus.INSUFFICIENT_CONTEXT,
            "citations": [],
            "retrieval_doc_count": 0,
            "retrieval_version": index_version,
        }
    return {"status": "continue"}


def call_model_with_deadline(
    client, prompt: str, timeout_seconds: float
) -> dict:
    """Call LLM model with timeout and deadline tracking.

    This implementation distinguishes between:
    - Request deadline: How long the user is willing to wait
    - Model timeout: How long a single provider call can take
    - Retry budget: How many additional attempts are allowed

    The key principle: if deadline is 8 seconds and single call timeout is 30
    seconds, the backend should not burn tokens and connections for an
    already-disconnected client.

    Args:
        client: LLM provider client
        prompt: Prompt text to send to model
        timeout_seconds: Maximum time in seconds for this call

    Returns:
        Dict with answer and status, or structured timeout error
    """
    started_at = monotonic()
    try:
        # In a real implementation, this would call the actual provider
        # response = client.generate(prompt=prompt, timeout=timeout_seconds)
        response_text = "Simulated model response"
    except TimeoutError:
        return {
            "answer": None,
            "status": ResponseStatus.LLM_TIMEOUT,
            "error_message": "model call exceeded configured timeout",
            "model_latency_ms": int((monotonic() - started_at) * 1000),
        }
    return {"answer": response_text, "status": ResponseStatus.SUCCESS}


def validate_tool_call(raw_action: dict, actor_can_write: bool) -> dict:
    """Validate tool action before execution.

    Schema validation alone is not enough. Before executing any tool action,
    the system must also verify:
    - The caller has permission (authorization check)
    - The action is not on an allowlist of forbidden operations
    - For write/delete/payment actions, human confirmation may be required

    The OWASP Top 10 for LLM Applications identifies "excessive agency"
    (LLM output triggering harmful actions without guardrails) as a key risk.

    Args:
        raw_action: JSON/dict object from LLM output
        actor_can_write: Whether caller is authorized to write

    Returns:
        Dict with validation result and execution decision
    """
    try:
        # In a real implementation, this would use actual Pydantic validation
        # action = CreateRefundTicket.model_validate(raw_action)
        action_type = raw_action.get("action_type")
        order_id = raw_action.get("order_id")
        reason = raw_action.get("reason")
        idempotency_key = raw_action.get("idempotency_key")

        # Basic validation
        if not action_type or not order_id or not reason or not idempotency_key:
            return {
                "status": ResponseStatus.TOOL_VALIDATION_FAILED,
                "error_message": "Missing required fields",
                "execute": False,
            }
    except ValidationError as error:
        return {
            "status": ResponseStatus.TOOL_VALIDATION_FAILED,
            "error_message": str(error),
            "execute": False,
        }

    if not actor_can_write:
        return {
            "status": ResponseStatus.TOOL_VALIDATION_FAILED,
            "error_message": "caller is not authorized",
            "execute": False,
        }

    return {"status": "continue", "execute": True, "action": raw_action}


def parse_model_response(raw_text: str, retrieved_ids: set[str]) -> dict:
    """Parse model response with citation validation.

    The response must satisfy two conditions:
    1. Must be valid JSON/structured format (parser_error if not)
    2. Must cite only documents from retrieval results (quality_failed if not)

    These are different failure modes that require different investigation paths:
    - parser_error → check if model output is malformed
    - quality_failed → check if retrieval results are adequate or index is stale

    Args:
        raw_text: Raw response text from model
        retrieved_ids: Set of document IDs from retrieval phase

    Returns:
        Dict with parsed answer and status, or error details
    """
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as error:
        return {
            "answer": None,
            "status": ResponseStatus.PARSER_ERROR,
            "error_message": str(error),
            "citations": [],
        }

    cited_ids = {
        item["source_id"] for item in payload.get("citations", [])
    }
    if not cited_ids.issubset(retrieved_ids):
        return {
            "answer": None,
            "status": ResponseStatus.QUALITY_FAILED,
            "error_message": "citation is absent from retrieval results",
            "citations": [],
        }

    return {
        "answer": payload.get("answer"),
        "status": ResponseStatus.SUCCESS,
        "citations": payload.get("citations", []),
    }


def may_continue_agent(state: dict, now_monotonic: float) -> tuple[bool, str]:
    """Check if agent loop may continue.

    Before each agent planning or tool execution step, verify that at least
    one of these guardrails has not been exceeded:
    - max_steps: Total number of planning/tool steps
    - max_same_tool_calls: Repeated calls with same tool and parameters
    - deadline: Absolute cutoff time for the entire workflow
    - max_tokens / max_cost: Token budget or cost limit

    The key point: multiple small budgets are better than one large one, and
    all must be checked together.

    Args:
        state: Agent state dict with step_count, deadlines, budgets, etc.
        now_monotonic: Current time from monotonic clock

    Returns:
        Tuple of (may_continue: bool, reason: str)
    """
    if state.get("step_count", 0) >= state.get("max_steps", float("inf")):
        return False, ResponseStatus.AGENT_LOOP_LIMIT

    if state.get("same_tool_calls", 0) >= state.get(
        "max_same_tool_calls", float("inf")
    ):
        return False, ResponseStatus.AGENT_LOOP_LIMIT

    if now_monotonic >= state.get("deadline_monotonic", float("inf")):
        return False, ResponseStatus.LLM_TIMEOUT

    if state.get("spent_tokens", 0) >= state.get("max_tokens", float("inf")):
        return False, ResponseStatus.AGENT_LOOP_LIMIT

    return True, "continue"
