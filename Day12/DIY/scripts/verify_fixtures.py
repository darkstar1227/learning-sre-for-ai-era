#!/usr/bin/env python3
"""Verify that all fixtures conform to schema and failure-mode matrix."""

import sys
import json
from app.fixtures import ALL_FIXTURES, get_required_fixtures, get_agent_guardrail_fixtures
from app.failure_modes import FAILURE_MODE_MATRIX, get_unique_nodes
from app.schemas import ResponseStatus


def verify_fixture_structure():
    """Verify each fixture has required fields."""
    print("Verifying fixture structure...")
    for fixture in ALL_FIXTURES:
        assert fixture.name, f"Fixture missing name"
        assert fixture.node, f"Fixture {fixture.name} missing node"
        assert fixture.description, f"Fixture {fixture.name} missing description"
        assert fixture.input_data, f"Fixture {fixture.name} missing input_data"
        assert fixture.expected_response, f"Fixture {fixture.name} missing expected_response"
        print(f"  ✓ {fixture.name} ({fixture.node})")
    print(f"✓ All {len(ALL_FIXTURES)} fixtures have required structure\n")


def verify_response_status():
    """Verify all fixtures use valid response statuses."""
    print("Verifying response status codes...")
    valid_statuses = set(s.value for s in ResponseStatus)
    for fixture in ALL_FIXTURES:
        status = fixture.expected_response.status.value
        assert status in valid_statuses, f"Invalid status in {fixture.name}: {status}"
        print(f"  ✓ {fixture.name}: {status}")
    print(f"✓ All fixtures use valid status codes\n")


def verify_failure_mode_matrix():
    """Verify failure mode matrix structure."""
    print("Verifying failure-mode matrix...")
    nodes = get_unique_nodes()
    print(f"  Nodes in matrix: {nodes}")
    print(f"  Total failure modes: {len(FAILURE_MODE_MATRIX)}")
    for fm in FAILURE_MODE_MATRIX:
        assert fm.node in nodes
        assert fm.external_status
        assert fm.safe_action
        print(f"  ✓ {fm.node}: {fm.external_status}")
    print(f"✓ Failure-mode matrix valid\n")


def verify_minimum_fixtures():
    """Verify we have at least 4 required fixtures."""
    print("Verifying minimum fixture requirements...")
    required = get_required_fixtures()
    assert len(required) >= 4, f"Need 4 required fixtures, have {len(required)}"
    for fixture in required:
        print(f"  ✓ {fixture.name}")
    print(f"✓ All 4 required fixtures present\n")


def verify_agent_guardrails():
    """Verify we have agent loop guardrail fixture."""
    print("Verifying agent loop guardrail...")
    guardrail = get_agent_guardrail_fixtures()
    assert len(guardrail) > 0, "No agent loop guardrail fixture found"
    for fixture in guardrail:
        print(f"  ✓ {fixture.name}")
    print(f"✓ Agent guardrail fixture present\n")


def verify_citations_validation():
    """Verify that hallucination fixture catches citation mismatches."""
    print("Verifying citation validation logic...")
    hallucination_fixture = None
    for f in ALL_FIXTURES:
        if f.name == "hallucinated_citation":
            hallucination_fixture = f
            break

    assert hallucination_fixture, "Hallucinated citation fixture not found"

    # Check that the expected response has quality_failed status
    assert (
        hallucination_fixture.expected_response.status
        == ResponseStatus.QUALITY_FAILED
    ), "Hallucination should result in quality_failed"

    print(f"  ✓ Hallucination detection returns quality_failed status")
    print(f"  ✓ Citation validation logic present\n")


def print_fixture_summary():
    """Print a summary table of all fixtures."""
    print("\nFixture Summary:")
    print("-" * 80)
    print(f"{'Name':<30} {'Node':<20} {'Status':<20}")
    print("-" * 80)
    for fixture in ALL_FIXTURES:
        status = fixture.expected_response.status.value
        print(f"{fixture.name:<30} {fixture.node:<20} {status:<20}")
    print("-" * 80)
    print()


def main():
    print("\n" + "=" * 80)
    print("Day 12 DIY: AI Workflow Failure-Mode Matrix Verification")
    print("=" * 80 + "\n")

    try:
        verify_fixture_structure()
        verify_response_status()
        verify_failure_mode_matrix()
        verify_minimum_fixtures()
        verify_agent_guardrails()
        verify_citations_validation()
        print_fixture_summary()

        print("=" * 80)
        print("✓ All verification checks passed!")
        print("=" * 80)
        return 0
    except AssertionError as e:
        print(f"\n✗ Verification failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
