"""
Demo script showing how to use the alerting triage engine.

This script demonstrates the signal triage logic from Day26:
- Model outages causing SLO burn -> pager
- Quality trends (not single samples) -> evaluation queue
- Safety risks -> security review
"""

import json
from app.models import (
    Signal, TriageEngine, SignalType, ImpactScope, TriageRoute
)


def demo_triage():
    """Run demo triage scenarios."""

    engine = TriageEngine()

    # Test scenarios from Day26
    scenarios = [
        # Scenario 1: Model timeout + SLO burn -> PAGER
        Signal(
            name="model_timeout_spike",
            signal_type=SignalType.INFRASTRUCTURE,
            current_value="95th percentile latency 45s (baseline 2s)",
            is_actionable=True,
            impact_scope=ImpactScope.WIDE_OUTAGE,
            slo_burn_rate=0.72,  # Burning through SLO at 72% rate
            description="Model provider experiencing outage, timeout rate jumped from 0.1% to 8% in 3min"
        ),

        # Scenario 2: Citation ratio downward trend -> EVALUATION_QUEUE
        Signal(
            name="citation_valid_ratio_trend",
            signal_type=SignalType.MODEL_OUTPUT,
            current_value=0.94,  # Down from 0.98
            is_actionable=False,  # Requires deeper investigation
            impact_scope=ImpactScope.ROLLING_WINDOW_TREND,
            description="Rolling 24h citation-valid ratio dropped from 98% to 94% over 6 hours"
        ),

        # Scenario 3: Single hallucination -> EVALUATION_QUEUE
        Signal(
            name="single_hallucination",
            signal_type=SignalType.MODEL_OUTPUT,
            current_value="'each subscription limited to one device' policy (does not exist)",
            is_actionable=False,
            impact_scope=ImpactScope.SINGLE_SAMPLE,
            description="One user report of incorrect policy statement in model response"
        ),

        # Scenario 4: High-risk unauthorized action -> SECURITY_REVIEW
        Signal(
            name="unauthorized_tool_action",
            signal_type=SignalType.SAFETY,
            current_value="agent attempted transfer without proper approval",
            is_actionable=True,
            impact_scope=ImpactScope.SINGLE_SAMPLE,
            is_safety_risk=True,
            description="Agent tried to execute 'transfer funds' action despite permission restrictions"
        ),

        # Scenario 5: Data exposure risk -> SECURITY_REVIEW
        Signal(
            name="sensitive_field_exposure",
            signal_type=SignalType.SAFETY,
            current_value="salary data in response",
            is_actionable=True,
            impact_scope=ImpactScope.SINGLE_SAMPLE,
            is_safety_risk=True,
            description="Model included employee salary information in response to unauthorized requester"
        ),

        # Scenario 6: Queue backlog -> PAGER
        Signal(
            name="inference_queue_backlog",
            signal_type=SignalType.RESOURCE,
            current_value="18000 pending requests (baseline <500)",
            is_actionable=True,
            impact_scope=ImpactScope.WIDE_OUTAGE,
            slo_burn_rate=0.85,
            description="GPU cluster utilization maxed out, inference requests queuing with 15min+ delays"
        ),
    ]

    print("=" * 80)
    print("AI Alerting Triage Demo")
    print("=" * 80)
    print()

    for scenario in scenarios:
        print(f"Signal: {scenario.name}")
        print(f"  Type: {scenario.signal_type}")
        print(f"  Current Value: {scenario.current_value}")
        print(f"  Impact Scope: {scenario.impact_scope}")
        if scenario.slo_burn_rate is not None:
            print(f"  SLO Burn Rate: {scenario.slo_burn_rate:.1%}")
        print(f"  Actionable: {scenario.is_actionable}")
        print(f"  Description: {scenario.description}")

        # Triage the signal
        result = engine.triage(scenario)

        print(f"  -> Routes: {', '.join(r.value for r in result.routes)}")
        print(f"  -> Owner: {result.owner}")
        print(f"  -> Priority: {result.priority}")
        print(f"  -> Reason: {result.reason}")
        print()

    print("=" * 80)
    print("Triage Summary")
    print("=" * 80)

    pager_count = 0
    eval_count = 0
    security_count = 0

    for scenario in scenarios:
        result = engine.triage(scenario)
        for route in result.routes:
            if route == TriageRoute.PAGER:
                pager_count += 1
            elif route == TriageRoute.EVALUATION_QUEUE:
                eval_count += 1
            elif route == TriageRoute.SECURITY_REVIEW:
                security_count += 1

    print(f"Signals routed to pager: {pager_count}")
    print(f"Signals routed to evaluation_queue: {eval_count}")
    print(f"Signals routed to security_review: {security_count}")
    print()

    return True


if __name__ == "__main__":
    try:
        success = demo_triage()
        if success:
            print("✓ All triage scenarios completed successfully")
        else:
            print("✗ Triage demo failed")
            exit(1)
    except Exception as e:
        print(f"✗ Error during triage demo: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
