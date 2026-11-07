#!/usr/bin/env python
"""
Day 18 DIY - Demonstration of SLI event contract.

Shows how different scenarios (happy path, queue delay, timeout, etc.)
produce correct SLI log records with proper null handling.

Run: uv run python scripts/demo_sli.py
"""

import json
from time import perf_counter
from typing import Literal

from app.schemas import new_ask_event


def simulate_scenario(
    name: str,
    outcome: Literal["completed", "technical_failed", "insufficient_context"],
    queue_delay_seconds: float = 0.0,
    retrieval_seconds: float = 0.05,
    has_retrieval: bool = True,
    has_first_token: bool = False,
    generation_seconds: float = 0.1,
) -> None:
    """
    Simulate a workflow scenario and print its SLI record.

    Parameters:
    - name: scenario name (for printing)
    - outcome: how the request ended
    - queue_delay_seconds: time between request_received and workflow_started
    - retrieval_seconds: time between retrieval_started and retrieval_finished
    - has_retrieval: whether retrieval happened
    - has_first_token: whether streaming produced a first token
    - generation_seconds: time between model_started and generation_finished
    """
    print(f"\n{'='*60}")
    print(f"Scenario: {name}")
    print(f"{'='*60}")

    event = new_ask_event()

    # Request boundary (external)
    request_received = event.timing.request_received

    # Queue delay
    workflow_started = request_received + queue_delay_seconds
    event.timing.workflow_started = workflow_started

    if has_retrieval:
        # Retrieval phase
        retrieval_started = workflow_started + 0.01
        retrieval_finished = retrieval_started + retrieval_seconds
        event.timing.retrieval_started = retrieval_started
        event.timing.retrieval_finished = retrieval_finished
        event.retrieval_count = 2

        # Model phase starts after retrieval
        model_started = retrieval_finished + 0.01
    else:
        model_started = workflow_started + 0.01

    event.timing.model_started = model_started

    # First token (only if streaming)
    if has_first_token:
        first_token = model_started + 0.05
        event.timing.first_token = first_token
    else:
        event.timing.first_token = None

    # Generation
    generation_finished = model_started + generation_seconds
    event.timing.generation_finished = generation_finished

    # Response sent
    response_sent = generation_finished + 0.01
    event.timing.response_sent = response_sent

    # Set outcome and status
    event.outcome = outcome
    if outcome == "completed":
        event.technical_status = "succeeded"
        event.workflow_status = "completed"
    elif outcome == "technical_failed":
        event.technical_status = "failed"
        event.workflow_status = "failed"
        event.error_class = "TimeoutError"
    elif outcome == "insufficient_context":
        event.outcome = "insufficient_context"
        event.workflow_status = "completed"
        event.quality_status = "no_context"
        event.retrieval_count = 0

    # Convert to log record
    record = event.to_log_record()

    # Print key metrics
    print(f"Request ID: {record['request_id']}")
    print(f"Outcome: {record['outcome']}")
    print(f"Technical Status: {record['technical_status']}")
    print(f"\nTiming (milliseconds):")
    print(f"  queue_delay_ms: {record['queue_delay_ms']}")
    print(f"  retrieval_ms: {record['retrieval_ms']}")
    print(f"  ttft_ms: {record['ttft_ms']}")
    print(f"  generation_ms: {record['generation_ms']}")
    print(f"  end_to_end_ms: {record['end_to_end_ms']}")

    print(f"\nRaw timestamps:")
    print(f"  request_received: {record['timing']['request_received']:.4f}")
    print(f"  workflow_started: {record['timing']['workflow_started']:.4f}")
    print(f"  retrieval_started: {record['timing']['retrieval_started']}")
    print(f"  retrieval_finished: {record['timing']['retrieval_finished']}")
    print(f"  model_started: {record['timing']['model_started']:.4f}")
    print(f"  first_token: {record['timing']['first_token']}")
    print(f"  generation_finished: {record['timing']['generation_finished']:.4f}")
    print(f"  response_sent: {record['timing']['response_sent']:.4f}")

    # Verify contract invariants
    print(f"\nContract Validation:")
    errors = []

    # Check: null values are None, not 0
    if record['ttft_ms'] == 0 and event.timing.first_token is None:
        errors.append("ERROR: ttft_ms should be None, not 0")
    if record['retrieval_ms'] == 0 and event.timing.retrieval_started is None:
        errors.append("ERROR: retrieval_ms should be None, not 0")

    # Check: outcome matches status
    if outcome == "completed" and record['technical_status'] != "succeeded":
        errors.append(f"ERROR: completed outcome should have succeeded status, got {record['technical_status']}")

    # Check: end_to_end always present
    if record['end_to_end_ms'] is None:
        errors.append("ERROR: end_to_end_ms should never be None")

    if errors:
        for err in errors:
            print(f"  ✗ {err}")
    else:
        print(f"  ✓ All contract checks passed")


def main():
    """Run all demonstration scenarios."""
    print("\n" + "="*60)
    print("Day 18 DIY - SLI Event Contract Demonstrations")
    print("="*60)

    # Scenario 1: Happy path - streaming with retrieval
    simulate_scenario(
        name="Happy Path (Streaming with Retrieval)",
        outcome="completed",
        queue_delay_seconds=0.01,
        retrieval_seconds=0.05,
        has_retrieval=True,
        has_first_token=True,  # Streaming!
        generation_seconds=0.15,
    )

    # Scenario 2: Queue congestion
    simulate_scenario(
        name="Queue Congestion (Long wait before workflow starts)",
        outcome="completed",
        queue_delay_seconds=0.5,  # 500ms queue delay
        retrieval_seconds=0.05,
        has_retrieval=True,
        has_first_token=False,  # Non-streaming
        generation_seconds=0.1,
    )

    # Scenario 3: Insufficient context (no documents)
    simulate_scenario(
        name="Insufficient Context (No documents found)",
        outcome="insufficient_context",
        queue_delay_seconds=0.01,
        retrieval_seconds=0.02,  # Quick to discover empty
        has_retrieval=True,
        has_first_token=False,
        generation_seconds=0.0,  # No generation step
    )

    # Scenario 4: Provider timeout (error during model call)
    simulate_scenario(
        name="Provider Timeout (Technical failure)",
        outcome="technical_failed",
        queue_delay_seconds=0.01,
        retrieval_seconds=0.05,
        has_retrieval=True,
        has_first_token=False,  # Never got first token
        generation_seconds=3.0,  # Hung trying to reach model
    )

    # Scenario 5: Non-streaming, no retrieval
    simulate_scenario(
        name="Non-Streaming, No Retrieval (Simple model call)",
        outcome="completed",
        queue_delay_seconds=0.0,
        retrieval_seconds=0.0,
        has_retrieval=False,
        has_first_token=False,
        generation_seconds=0.2,
    )

    print(f"\n{'='*60}")
    print("All scenarios completed!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
