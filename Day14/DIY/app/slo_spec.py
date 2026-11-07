"""
SLI Classifier for answer-api availability

Based on Day 14 definition:
- SLI: good events / valid requests
- Good event: completed, insufficient_context, requires_human_review (within 10s, HTTP 200)
- Bad event: timeout (>10s), 5xx, contract invalid, system rejection
- Exclusions: malformed requests, load tests

This module provides a pure Python classifier (no framework dependencies) that can
be used for specification testing and future integration with production metrics.
"""

from dataclasses import dataclass


# Constants
GOOD_WORKFLOW_STATUSES = {
    "completed",
    "insufficient_context",
    "requires_human_review",
}

LATENCY_LIMIT_MS = 10_000


@dataclass(frozen=True)
class AskEvent:
    """Represents a completed /ask request for SLI classification."""
    valid_request: bool
    workflow_status: str
    response_contract_valid: bool
    latency_ms: int | None
    system_rejection: bool = False


def is_sli_eligible(event: AskEvent) -> bool:
    """
    Determine if an event should be included in the availability SLI denominator.
    Only product-meaningful /ask requests enter this SLI.

    Excludes: malformed requests, obvious invalid input.
    """
    return event.valid_request


def is_good_event(event: AskEvent, latency_limit_ms: int = LATENCY_LIMIT_MS) -> bool:
    """
    Determine if an event is a good outcome for the availability SLI.

    Good events:
    - Eligible for SLI (valid_request=True)
    - No system rejection
    - Response contract is valid
    - Completed within latency limit
    - Workflow status is in approved list

    Args:
        event: The event to classify
        latency_limit_ms: SLA threshold in milliseconds (default: 10_000)

    Returns:
        True if event meets all good-event criteria
    """
    if not is_sli_eligible(event):
        return False

    if event.system_rejection:
        return False

    if event.latency_ms is None or event.latency_ms > latency_limit_ms:
        return False

    if not event.response_contract_valid:
        return False

    return event.workflow_status in GOOD_WORKFLOW_STATUSES


# Test fixtures from Day 14 article (section ④)
CASES = {
    "grounded_answer": AskEvent(
        valid_request=True,
        workflow_status="completed",
        response_contract_valid=True,
        latency_ms=820,
    ),
    "honest_unknown": AskEvent(
        valid_request=True,
        workflow_status="insufficient_context",
        response_contract_valid=True,
        latency_ms=640,
    ),
    "provider_timeout": AskEvent(
        valid_request=True,
        workflow_status="timed_out",
        response_contract_valid=False,
        latency_ms=10_001,
    ),
    "http_200_but_invalid": AskEvent(
        valid_request=True,
        workflow_status="completed",
        response_contract_valid=False,
        latency_ms=510,
    ),
    "malformed_payload": AskEvent(
        valid_request=False,
        workflow_status="invalid_request",
        response_contract_valid=False,
        latency_ms=0,
    ),
    "system_denied_user": AskEvent(
        valid_request=True,
        workflow_status="authorization_error",
        response_contract_valid=False,
        latency_ms=220,
        system_rejection=True,
    ),
}
