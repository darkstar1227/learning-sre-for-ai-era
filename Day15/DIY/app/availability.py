"""
Availability Classifier - determines if a request-based event represents good availability.

Reference: Day15/Day15.md - Availability: not just counting 200s
"""

from dataclasses import dataclass
from enum import StrEnum


class SliResult(StrEnum):
    GOOD = "good"
    BAD = "bad"
    EXCLUDED = "excluded"


@dataclass(frozen=True)
class AvailabilityEvent:
    """
    Normalized event for availability classification.

    Attributes:
        valid_request: Whether this is a valid user request (affects denominator)
        latency_ms: Response latency in milliseconds
        contract_valid: Whether response satisfies the service contract
        response_status: Terminal status (e.g., 'completed', 'insufficient_context', etc.)
    """
    valid_request: bool
    latency_ms: int
    contract_valid: bool
    response_status: str


@dataclass(frozen=True)
class Classification:
    """
    Result of availability classification.

    Attributes:
        eligible: Whether this event counts toward the denominator of availability SLI
        result: Classification result (good/bad/excluded)
        reason: Human-readable reason for classification
    """
    eligible: bool
    result: SliResult
    reason: str


# Good response statuses according to our service contract
GOOD_RESPONSE_STATUSES = frozenset(
    {"completed", "insufficient_context", "requires_human_review"}
)

# Maximum acceptable latency in milliseconds
# This is a Lab example; production SLO must match your actual contract
MAX_LATENCY_MS = 10_000


def classify_availability(event: AvailabilityEvent) -> Classification:
    """
    Classify whether an event represents good availability.

    Classification order matters:
    1. Invalid requests are excluded from the denominator
    2. Valid requests exceeding latency SLO are bad
    3. Valid requests with invalid contract are bad
    4. Valid requests with contract-compliant status are good
    5. Everything else is bad

    Args:
        event: AvailabilityEvent to classify

    Returns:
        Classification with eligible, result, and reason
    """
    if not event.valid_request:
        return Classification(False, SliResult.EXCLUDED, "invalid_request")

    if event.latency_ms > MAX_LATENCY_MS:
        return Classification(True, SliResult.BAD, "deadline_exceeded")

    if not event.contract_valid:
        return Classification(True, SliResult.BAD, "invalid_response_contract")

    if event.response_status in GOOD_RESPONSE_STATUSES:
        return Classification(True, SliResult.GOOD, "contract_satisfied")

    return Classification(True, SliResult.BAD, "workflow_failed")
