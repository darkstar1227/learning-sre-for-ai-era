#!/usr/bin/env python
"""
Day 18 DIY - Contract verification tests.

Tests that the SLI event contract behaves correctly:
- null values stay null
- duration calculations are accurate
- outcome classifications are distinct

Run: uv run python -m pytest scripts/test_contract.py -v
Or simply: uv run python scripts/test_contract.py
"""

from time import perf_counter

from app.schemas import new_ask_event, AskEvent, AskTiming, Outcome


def test_missing_first_token_stays_unknown() -> None:
    """Verify TTFT stays None when first_token is not recorded."""
    event = new_ask_event()
    event.timing.workflow_started = event.timing.request_received + 0.2
    event.timing.response_sent = event.timing.request_received + 1.2

    record = event.to_log_record()

    assert record["queue_delay_ms"] == 200.0, "queue_delay should be 200ms"
    assert record["ttft_ms"] is None, "ttft_ms should be None when no first_token"
    assert record["end_to_end_ms"] == 1200.0, "end_to_end should be 1200ms"
    print("✓ test_missing_first_token_stays_unknown passed")


def test_missing_retrieval_stays_unknown() -> None:
    """Verify retrieval_ms stays None when retrieval events are absent."""
    event = new_ask_event()
    event.timing.workflow_started = event.timing.request_received + 0.1
    event.timing.model_started = event.timing.request_received + 0.15
    event.timing.generation_finished = event.timing.request_received + 0.5
    event.timing.response_sent = event.timing.request_received + 0.6

    record = event.to_log_record()

    assert record["retrieval_ms"] is None, "retrieval_ms should be None when no retrieval"
    assert record["generation_ms"] == 350.0, "generation_ms should be 350ms"
    print("✓ test_missing_retrieval_stays_unknown passed")


def test_complete_workflow_timing() -> None:
    """Verify a complete workflow with all events produces correct metrics."""
    event = new_ask_event()
    base = event.timing.request_received

    event.timing.workflow_started = base + 0.05
    event.timing.retrieval_started = base + 0.1
    event.timing.retrieval_finished = base + 0.2
    event.timing.model_started = base + 0.25
    event.timing.first_token = base + 0.35
    event.timing.generation_finished = base + 0.5
    event.timing.response_sent = base + 0.55

    record = event.to_log_record()

    assert record["queue_delay_ms"] == 50.0
    assert record["retrieval_ms"] == 100.0
    assert record["ttft_ms"] == 350.0  # first_token - request_received
    assert record["generation_ms"] == 250.0  # generation_finished - model_started
    assert record["end_to_end_ms"] == 550.0
    print("✓ test_complete_workflow_timing passed")


def test_outcome_values() -> None:
    """Verify outcome is correctly classified."""
    outcomes = [
        "completed",
        "technical_failed",
        "quality_failed",
        "safety_blocked",
        "insufficient_context",
    ]

    for outcome in outcomes:
        event = new_ask_event()
        event.outcome = outcome  # type: ignore
        record = event.to_log_record()
        assert record["outcome"] == outcome, f"outcome should be {outcome}"

    print("✓ test_outcome_values passed")


def test_default_statuses() -> None:
    """Verify default status fields start as 'unknown'."""
    event = new_ask_event()
    record = event.to_log_record()

    assert record["technical_status"] == "unknown"
    assert record["workflow_status"] == "unknown"
    assert record["quality_status"] == "unknown"
    assert record["safety_status"] == "unknown"
    print("✓ test_default_statuses passed")


def test_request_and_trace_ids_unique() -> None:
    """Verify each new event gets unique IDs."""
    event1 = new_ask_event()
    event2 = new_ask_event()

    assert event1.request_id != event2.request_id
    assert event1.trace_id != event2.trace_id
    print("✓ test_request_and_trace_ids_unique passed")


def test_version_fields_populated() -> None:
    """Verify version fields are populated."""
    event = new_ask_event()
    record = event.to_log_record()

    assert record["workflow_version"] == "2026-09-22"
    assert record["model_name"] == "configured-at-deploy-time"
    assert record["retrieval_index_version"] == "policy-v1"
    print("✓ test_version_fields_populated passed")


def test_duration_with_partial_timestamps() -> None:
    """Verify duration_ms handles partial timestamps correctly."""
    event = new_ask_event()
    base = event.timing.request_received

    event.timing.workflow_started = base + 0.1
    event.timing.retrieval_started = base + 0.2
    # retrieval_finished NOT set

    # retrieval_ms should be None because retrieval_finished is missing
    assert event.timing.duration_ms("retrieval_started", "retrieval_finished") is None
    # queue_delay_ms should be 100ms
    assert event.timing.duration_ms("request_received", "workflow_started") == 100.0
    print("✓ test_duration_with_partial_timestamps passed")


def test_notes_list_default() -> None:
    """Verify notes list starts empty."""
    event = new_ask_event()
    assert event.notes == []
    event.notes.append("Something happened")
    assert len(event.notes) == 1
    print("✓ test_notes_list_default passed")


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("Day 18 DIY - Contract Verification Tests")
    print("="*60 + "\n")

    tests = [
        test_missing_first_token_stays_unknown,
        test_missing_retrieval_stays_unknown,
        test_complete_workflow_timing,
        test_outcome_values,
        test_default_statuses,
        test_request_and_trace_ids_unique,
        test_version_fields_populated,
        test_duration_with_partial_timestamps,
        test_notes_list_default,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__} FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} ERROR: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'='*60}\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit(main())
