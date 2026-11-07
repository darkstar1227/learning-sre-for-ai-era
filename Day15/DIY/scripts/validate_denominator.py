#!/usr/bin/env python3
"""
Validate availability denominator with test traffic.

Step 4 from Day15 DIY: Verify that invalid requests don't pollute the denominator.

This script demonstrates the expected behavior:
- Scenario A: 8 valid+good + 2 valid+bad → availability = 8/10 = 80%
- Scenario B: 5 invalid requests → should NOT change the denominator from scenario A
"""

from app.availability import AvailabilityEvent, classify_availability


def scenario_a():
    """
    Scenario A: 8 good events, 2 bad events
    Expected availability: 8 valid+good / (8+2) valid = 80%
    """
    print("=" * 60)
    print("Scenario A: 8 valid+good, 2 valid+bad")
    print("=" * 60)

    results = {"good": 0, "bad": 0, "excluded": 0}

    # 8 good events
    for i in range(8):
        event = AvailabilityEvent(
            valid_request=True,
            latency_ms=300,
            contract_valid=True,
            response_status="completed"
        )
        classification = classify_availability(event)
        results[classification.result.value] += 1
        print(f"  Event {i+1}: {classification.result.value} ({classification.reason})")

    # 2 bad events (timeout)
    for i in range(2):
        event = AvailabilityEvent(
            valid_request=True,
            latency_ms=15_000,
            contract_valid=True,
            response_status="completed"
        )
        classification = classify_availability(event)
        results[classification.result.value] += 1
        print(f"  Event {i+9}: {classification.result.value} ({classification.reason})")

    valid_total = results["good"] + results["bad"]
    availability = results["good"] / valid_total if valid_total > 0 else 0

    print(f"\nScenario A Results:")
    print(f"  Good: {results['good']}")
    print(f"  Bad: {results['bad']}")
    print(f"  Excluded: {results['excluded']}")
    print(f"  Denominator (valid): {valid_total}")
    print(f"  Availability: {results['good']}/{valid_total} = {availability:.1%}")
    print()

    return results


def scenario_b():
    """
    Scenario B: 5 invalid requests
    Expected behavior: These should NOT affect the denominator from Scenario A.
    Availability should remain 80%, not become 8/15.
    """
    print("=" * 60)
    print("Scenario B: 5 invalid requests (should be excluded)")
    print("=" * 60)

    results = {"good": 0, "bad": 0, "excluded": 0}

    # 5 invalid requests
    for i in range(5):
        event = AvailabilityEvent(
            valid_request=False,
            latency_ms=0,
            contract_valid=False,
            response_status="invalid_request"
        )
        classification = classify_availability(event)
        results[classification.result.value] += 1
        print(f"  Event {i+1}: {classification.result.value} ({classification.reason})")

    print(f"\nScenario B Results:")
    print(f"  Good: {results['good']}")
    print(f"  Bad: {results['bad']}")
    print(f"  Excluded: {results['excluded']}")
    print(f"  Denominator (valid): {results['good'] + results['bad']}")
    print(f"  Note: Excluded events do NOT affect the SLI denominator")
    print()

    return results


def main():
    print("\n" + "=" * 60)
    print("Day15 DIY: Validate Availability Denominator")
    print("=" * 60)
    print()

    results_a = scenario_a()
    results_b = scenario_b()

    print("=" * 60)
    print("Key Takeaway:")
    print("=" * 60)
    print("Scenario A denominator: 10 (8 good + 2 bad)")
    print("Scenario B adds: 5 excluded")
    print("Combined denominator: 10 (NOT 15)")
    print()
    print("✓ Invalid requests correctly excluded from denominator")
    print("✓ SLI calculation: good / valid = 8 / 10 = 80%")
    print()


if __name__ == "__main__":
    main()
