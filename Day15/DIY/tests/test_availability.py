"""
Pytest fixtures for availability classifier.

These fixtures translate product discussions into executable test cases,
validating that our classification matches the SLO spec in Day15/Day15.md
"""

import pytest

from app.availability import (
    AvailabilityEvent,
    SliResult,
    classify_availability,
)


@pytest.mark.parametrize(
    ("event", "eligible", "result", "reason"),
    [
        # Normal completion: valid request, fast, good contract, completed status
        (
            AvailabilityEvent(True, 230, True, "completed"),
            True,
            SliResult.GOOD,
            "contract_satisfied",
        ),
        # Insufficient context: valid and contract-compliant failure mode
        (
            AvailabilityEvent(True, 340, True, "insufficient_context"),
            True,
            SliResult.GOOD,
            "contract_satisfied",
        ),
        # Requires human review: valid and contract-compliant delay
        (
            AvailabilityEvent(True, 420, True, "requires_human_review"),
            True,
            SliResult.GOOD,
            "contract_satisfied",
        ),
        # Deadline exceeded: valid request but latency > 10s
        (
            AvailabilityEvent(True, 10_001, True, "completed"),
            True,
            SliResult.BAD,
            "deadline_exceeded",
        ),
        # Invalid response contract: valid request but response doesn't match contract
        (
            AvailabilityEvent(True, 400, False, "completed"),
            True,
            SliResult.BAD,
            "invalid_response_contract",
        ),
        # Workflow failed: valid request but status not in acceptable list
        (
            AvailabilityEvent(True, 500, True, "workflow_failed"),
            True,
            SliResult.BAD,
            "workflow_failed",
        ),
        # Invalid request: malformed JSON or missing required fields
        (
            AvailabilityEvent(False, 0, False, "invalid_request"),
            False,
            SliResult.EXCLUDED,
            "invalid_request",
        ),
        # Invalid request even with fast latency
        (
            AvailabilityEvent(False, 100, True, "completed"),
            False,
            SliResult.EXCLUDED,
            "invalid_request",
        ),
        # Edge case: exactly at latency boundary (10_000 ms) should pass
        (
            AvailabilityEvent(True, 10_000, True, "completed"),
            True,
            SliResult.GOOD,
            "contract_satisfied",
        ),
        # Honest refusal but malformed contract: model said "insufficient_context"
        # (a status the whitelist accepts) but the JSON itself is missing a
        # required field. contract_valid is checked before response_status, so
        # this must still land on invalid_response_contract, not on GOOD.
        (
            AvailabilityEvent(True, 280, False, "insufficient_context"),
            True,
            SliResult.BAD,
            "invalid_response_contract",
        ),
    ],
)
def test_classify_availability(event, eligible, result, reason):
    """
    Test availability classification against expected outcomes.

    These fixtures represent real product scenarios:
    - Completed work is good.
    - Honest refusals (insufficient_context, requires_human_review) are good.
    - Timeouts and contract violations are bad.
    - Malformed requests are excluded from the SLI denominator.
    """
    actual = classify_availability(event)

    assert actual.eligible is eligible, f"Expected eligible={eligible}, got {actual.eligible}"
    assert actual.result is result, f"Expected result={result}, got {actual.result}"
    assert actual.reason == reason, f"Expected reason={reason}, got {actual.reason}"
