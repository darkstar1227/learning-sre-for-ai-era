#!/usr/bin/env python
"""
Day21 DIY Demo: Generate observability data (metrics, logs, traces) for a fixture request.

Demonstrates how the same request generates three different types of data:
1. Metrics: Low-cardinality counters for alerting (outcome-level aggregation)
2. Logs: Structured JSON with correlation fields (request_id, dependency, error_class)
3. Traces: Span hierarchy with timing information (where request spent time)

All three share request_id for correlation, but metrics avoid high-cardinality labels.
"""

import sys
import json

# Add parent directory to path for imports
sys.path.insert(0, "/Users/ds-anxing/GitHub/learning-sre-for-ai-era/Day21/DIY")

from app.fixture import create_fixture_requests
from app.queries import print_query_summary, MetricsQueries
from prometheus_client import REGISTRY
from app.metrics import timeout_incidents, answer_requests


def print_metrics_snapshot():
    """Print current Prometheus metrics."""
    print("\n=== METRICS SNAPSHOT (Prometheus format) ===")
    found_metrics = False
    for metric_family in REGISTRY.collect():
        # Look for counter metrics (without _total/_created suffix)
        if metric_family.name in ("dependency_timeout_incidents", "answer_requests"):
            found_metrics = True
            print(f"\n# HELP {metric_family.name} {metric_family.documentation}")
            print(f"# TYPE {metric_family.name} counter")
            for sample in metric_family.samples:
                # Skip _created samples, only show _total
                if sample.name.endswith("_created"):
                    continue
                # Print in Prometheus format: name{label1="value1",...} value
                labels = ",".join(f'{k}="{v}"' for k, v in sorted(sample.labels.items()))
                if labels:
                    print(f"{sample.name}{{{labels}}} {int(sample.value)}")
                else:
                    print(f"{sample.name} {int(sample.value)}")

    if not found_metrics:
        print("Note: Metrics registered but filtering applied")


def main():
    """Run the demo."""
    print("=" * 70)
    print("Day21 DIY: Metrics + Logs + Traces for One Request")
    print("=" * 70)

    print("\n1. Generating fixture requests with timeout scenario...")

    # Create 3 fixture requests: 2 timeout, 1 success
    requests = create_fixture_requests(count=3, mix_outcomes=True)

    print(f"   Generated {len(requests)} requests:")
    for req in requests:
        status = "timeout" if req["timeout"] else "success"
        print(f"   - {req['request_id']}: {status} on {req['dependency']}")

    print("\n2. All requests share request_id for correlation in logs/traces,")
    print("   but metrics use only low-cardinality labels (outcome, dependency).")

    print_metrics_snapshot()

    print("\n3. Structured logs emitted to stdout (JSON format)")
    print("   ↓ In production, these go to Loki via Alloy")
    print("   ↓ Query by: {service='api'} | json | event='dependency_timeout'")

    print_query_summary()

    print("\nDemo complete! To verify in real stack:")
    print("  • Metrics: Query Prometheus for request outcome trends")
    print("  • Logs: Query Loki for which dependency(ies) failed")
    print("  • Traces: Query Tempo for per-request span waterfall")


if __name__ == "__main__":
    main()
