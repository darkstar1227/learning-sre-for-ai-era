"""
Demo: Load real events from JSON and route them using alert_router.

This script demonstrates loading events from the events/ folder
and applying the routing logic from alert_router.py.
"""

import json
import sys
from pathlib import Path

# Add parent directory to path so we can import alert_router
sys.path.insert(0, str(Path(__file__).parent.parent))

from alert_router import AIEvent, route


def demo_event_routing():
    """Load and route events from JSON files."""

    events_dir = Path(__file__).parent.parent / "events"

    print("=" * 80)
    print("AI Alerting: Event Routing Demo")
    print("=" * 80)
    print()

    event_files = sorted(events_dir.glob("*.json"))

    if not event_files:
        print("No event files found in events/ directory")
        return False

    results = {}

    for event_file in event_files:
        print(f"Processing: {event_file.name}")

        with open(event_file, "r") as f:
            event_data = json.load(f)

        # Create AIEvent from JSON
        event = AIEvent(**event_data)

        # Route the event
        destination = route(event)

        print(f"  Event type: {event.event_type}")
        print(f"  → Routed to: {destination.value}")

        results[event_file.name] = destination.value
        print()

    # Summary
    print("=" * 80)
    print("Routing Summary")
    print("=" * 80)

    by_destination = {}
    for filename, dest in results.items():
        if dest not in by_destination:
            by_destination[dest] = []
        by_destination[dest].append(filename)

    for dest in sorted(by_destination.keys()):
        files = by_destination[dest]
        print(f"\n{dest}:")
        for filename in files:
            print(f"  - {filename}")

    print()
    return True


if __name__ == "__main__":
    try:
        success = demo_event_routing()
        if success:
            print("✓ Event routing demo completed successfully")
        else:
            print("✗ Event routing demo failed")
            exit(1)
    except Exception as e:
        print(f"✗ Error during event routing: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
