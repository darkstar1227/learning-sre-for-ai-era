#!/usr/bin/env python3
"""
Error Budget Calculation Demo

Demonstrates hand-calculated error budget scenarios based on:
- Day 14 DIY: SLI/SLO definitions
- Day 20: Burn rate & policy actions

All values are symbolic/assumed; no real production data.
"""

import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent))

from app.budget import (
    SLODefinition,
    BudgetType,
    WindowMetrics,
    RollingWindowBudget,
    format_policy_action,
)


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def scenario_1_healthy():
    """Scenario 1: Everything normal, budget healthy."""
    print_section("SCENARIO 1: Healthy Operations (Day 0-5 of month)")

    # Define SLO
    slo = SLODefinition(
        budget_type=BudgetType.AVAILABILITY,
        slo_percentage=99.5,
        window_days=28,
        owner="SRE Team",
        description="answer-api availability"
    )

    print("SLO Definition:")
    print(slo.describe())
    print()

    # Hand-calculated window metrics
    # Assuming 50,000 requests in first 5 days (9,600 req/day avg)
    # With 99.5% SLO: 0.5% * 50,000 = 250 bad events allowed
    # Observed: 40 bad events (realistic performance)
    window = WindowMetrics(
        window_name="Last 5 days (rolling)",
        total_requests=50_000,
        bad_events=40,
    )

    rolling_budget = RollingWindowBudget(
        slo=slo,
        total_requests_in_window=50_000,
        bad_events_in_window=40,
    )

    print(f"Observed Metrics (Day 0-5):")
    print(f"  Total requests: {window.total_requests:,}")
    print(f"  Bad events: {window.bad_events}")
    print(f"  Actual bad rate: {window.actual_bad_rate * 100:.3f}%")
    print(f"  Acceptable bad rate (SLO): {slo.acceptable_bad_event_rate * 100:.1f}%")
    print()

    burn_rate_1h = window.calculate_burn_rate(slo)
    print(f"Burn Rate Calculation:")
    print(f"  burn_rate = {window.actual_bad_rate:.5f} / {slo.acceptable_bad_event_rate:.5f}")
    print(f"  burn_rate = {burn_rate_1h:.2f}x")
    print()

    print(rolling_budget.describe())
    print()

    print(format_policy_action(rolling_budget, burn_rate_1h))
    print()


def scenario_2_spike():
    """Scenario 2: Brief spike in bad events, burn rate spike detected."""
    print_section("SCENARIO 2: 1-Hour Spike → High Burn Rate (Day 10)")

    slo = SLODefinition(
        budget_type=BudgetType.AVAILABILITY,
        slo_percentage=99.5,
        window_days=28,
        owner="SRE Team",
    )

    # 1-hour window with spike
    # Assume 3,000 requests/hour (50 req/min)
    # Baseline: 15 bad events/hour (0.5% error rate)
    # But this hour: 250 bad events (8.3% error rate) -- cache failure scenario
    window_1h = WindowMetrics(
        window_name="Last 1 hour (spike window)",
        total_requests=3_000,
        bad_events=250,
    )

    print(f"1-Hour Snapshot (14:00-15:00 UTC):")
    print(f"  Total requests: {window_1h.total_requests:,}")
    print(f"  Bad events: {window_1h.bad_events}")
    print(f"  Actual bad rate: {window_1h.actual_bad_rate * 100:.1f}%")
    print()

    burn_rate = window_1h.calculate_burn_rate(slo)
    status, rate = window_1h.classify_status(slo)

    print(f"Burn Rate (1-hour window):")
    print(f"  burn_rate = {window_1h.actual_bad_rate:.4f} / {slo.acceptable_bad_event_rate:.5f}")
    print(f"  burn_rate = {burn_rate:.1f}x")
    print(f"  Alert threshold: > 36x for 1-hour = CRITICAL")
    print(f"  Status: {status.value.upper()}")
    print()

    # Rolling window (28-day) impact
    # Assume month so far: 1.2M requests, 4,000 bad events (0.33% observed)
    # Adding this 1-hour spike
    rolling_budget = RollingWindowBudget(
        slo=slo,
        total_requests_in_window=1_203_000,  # 1.2M + this hour
        bad_events_in_window=4_250,  # 4,000 + 250 from spike
    )

    print("28-Day Rolling Window Impact:")
    print(rolling_budget.describe())
    print()

    print(format_policy_action(rolling_budget, burn_rate))
    print()

    if rolling_budget.check_single_event_rule(250):
        print("⚠️ POSTMORTEM REQUIRED: Single event consumed > 20% of monthly budget")
        monthly_budget = slo.monthly_budget_events
        event_pct = (250 / monthly_budget) * 100
        print(f"   Event impact: {event_pct:.1f}% of {monthly_budget:,.0f} monthly bad events")
    else:
        monthly_budget = slo.monthly_budget_events
        event_pct = (250 / monthly_budget) * 100
        print(f"✓ Single event impact: {event_pct:.1f}% (below 20% threshold)")
    print()


def scenario_3_quality():
    """Scenario 3: Quality budget approaching critical."""
    print_section("SCENARIO 3: Quality Budget Warning (Day 15)")

    slo_quality = SLODefinition(
        budget_type=BudgetType.QUALITY,
        slo_percentage=99.0,
        window_days=28,
        owner="ML Team",
        description="Grounded answers (semantic correctness)"
    )

    print("SLO Definition:")
    print(slo_quality.describe())
    print()

    # 15 days into month: 900k requests
    # Quality SLO: 99.0% = 1% bad events
    # Allowance: 0.01 * 900k = 9,000 bad events
    # Observed: 7,500 bad events (high model error rate)
    rolling_budget = RollingWindowBudget(
        slo=slo_quality,
        total_requests_in_window=900_000,
        bad_events_in_window=7_500,
    )

    print("15-Day Window:")
    print(f"  Requests: {rolling_budget.total_requests_in_window:,}")
    print(f"  Bad events (hallucinations, inaccuracies): {rolling_budget.bad_events_in_window:,}")
    print(f"  Actual quality rate: {(1 - rolling_budget.bad_events_in_window / rolling_budget.total_requests_in_window) * 100:.2f}%")
    print()

    print(rolling_budget.describe())
    print()

    print(format_policy_action(rolling_budget))
    print()

    print("Recommended Actions:")
    print("  1. STOP all new model/prompt promotions (per policy)")
    print("  2. Investigate recent model changes / prompt updates")
    print("  3. Consider rollback or in-context fine-tuning")
    print("  4. Convene quality review board")
    print()


def scenario_4_safety():
    """Scenario 4: Safety incident - single bad event."""
    print_section("SCENARIO 4: Safety Block Anomaly (Day 7, Single Incident)")

    slo_safety = SLODefinition(
        budget_type=BudgetType.SAFETY,
        slo_percentage=99.9,
        window_days=28,
        owner="Security Team",
        description="Safe responses (no guardrail violations)"
    )

    print("SLO Definition:")
    print(slo_safety.describe())
    print()

    # Baseline: Week 1 had 2 legitimate safety blocks (tool invocation errors)
    # Today: Unexpected high-risk failure - guardrail unexpectedly allows sensitive request
    rolling_budget = RollingWindowBudget(
        slo=slo_safety,
        total_requests_in_window=350_000,  # 7 days of traffic
        bad_events_in_window=3,  # 2 baseline + 1 anomalous
    )

    print("7-Day Window:")
    print(f"  Requests: {rolling_budget.total_requests_in_window:,}")
    print(f"  Safety violations: {rolling_budget.bad_events_in_window}")
    print()

    # Show the anomalous event
    print("Incident Details:")
    print("  Time: 2026-09-21 14:32:15 UTC")
    print("  Issue: Guardrail failed to block PII extraction attempt (medium severity)")
    print("  Impact: 1 request got sensitive data, no user harm (caught by downstream log filter)")
    print()

    print(rolling_budget.describe())
    print()

    # Single event rule for safety
    if rolling_budget.check_single_event_rule(1):
        print("⚠️ ESCALATION REQUIRED: Safety incident demands immediate action")
    else:
        print("✓ Single event impact < 20% monthly budget")
        monthly_budget = slo_safety.monthly_budget_events
        event_pct = (1 / monthly_budget) * 100
        print(f"   Impact: {event_pct:.2f}% of {monthly_budget:,.0f} monthly limit")
    print()

    print("Policy Actions (Safety):")
    print("  1. ✗ DO NOT average with other events or use consumption %, safety is strict")
    print("  2. Preserve all evidence (logs, request replay, guardrail state)")
    print("  3. Escalate to Chief Security Officer immediately")
    print("  4. Lock guardrail parameters (no rollout until root cause fixed)")
    print("  5. Mandatory postmortem with P0 fix required")
    print()


def scenario_5_multiple_budgets():
    """Scenario 5: Visibility across multiple budget types."""
    print_section("SCENARIO 5: Multi-Budget View (Day 20)")

    # Create three budget snapshots for availability, quality, safety
    budgets = [
        (
            "Availability",
            RollingWindowBudget(
                slo=SLODefinition(BudgetType.AVAILABILITY, 99.5, owner="SRE"),
                total_requests_in_window=2_000_000,
                bad_events_in_window=6_500,  # 0.325% actual
            )
        ),
        (
            "Quality",
            RollingWindowBudget(
                slo=SLODefinition(BudgetType.QUALITY, 99.0, owner="ML"),
                total_requests_in_window=2_000_000,
                bad_events_in_window=12_000,  # 0.6% actual
            )
        ),
        (
            "Safety",
            RollingWindowBudget(
                slo=SLODefinition(BudgetType.SAFETY, 99.9, owner="Security"),
                total_requests_in_window=2_000_000,
                bad_events_in_window=100,  # 0.005% actual
            )
        ),
    ]

    print("20-Day Summary (All Budgets):\n")
    for name, budget in budgets:
        print(f"{name.upper()}:")
        print(f"  {budget.status_for_consumption().value.upper():12} ({budget.consumed_percentage:5.1f}% spent)")
        print(f"  {budget.bad_events_in_window:,} / {int(budget.slo.monthly_budget_events):,} bad events")
        print()

    print("Overall Status Matrix:")
    print("┌─────────────┬─────────┬───────────────┬──────────────┐")
    print("│ Budget Type │ Status  │ % Consumed    │ Policy Implication │")
    print("├─────────────┼─────────┼───────────────┼──────────────┤")
    for name, budget in budgets:
        status = budget.status_for_consumption().value.upper()
        consumed_str = f"{budget.consumed_percentage:5.1f}%"
        policy_map = {
            "healthy": "Continue normal ops",
            "caution": "Monitor closely",
            "warning": "Pause non-critical",
            "critical": "FREEZE deployments"
        }
        policy = policy_map.get(budget.status_for_consumption().value, "Unknown")
        name_pad = name.ljust(11)
        status_pad = status.ljust(7)
        print(f"│ {name_pad} │ {status_pad} │ {consumed_str:13} │ {policy:16} │")
    print("└─────────────┴─────────┴───────────────┴──────────────┘")
    print()

    print("Recommended Team Sync:")
    print("  - SRE: Availability on track, continue monitoring")
    print("  - ML: Quality budget at 60%, consider prompt review")
    print("  - Security: Safety excellent, no changes needed")
    print()


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════╗
║     ERROR BUDGET & BURN RATE CALCULATION EXAMPLES                ║
║     (Day 20 DIY - Symbolic Values / Hand-Calculated)             ║
╚══════════════════════════════════════════════════════════════════╝
    """)

    scenario_1_healthy()
    scenario_2_spike()
    scenario_3_quality()
    scenario_4_safety()
    scenario_5_multiple_budgets()

    print_section("KEY TAKEAWAYS")
    print("""
1. Burn Rate ≠ Error Rate
   - Burn rate tells you if you're consuming faster than SLO allows
   - burn_rate = actual_bad_rate / acceptable_bad_rate
   - > 1.0 means unsustainable pace; <= 1.0 means OK

2. Short Window vs. Long Window
   - 1-hour window detects acute spikes (set alert at 36x for availability)
   - 6-hour window avoids false alarms (set alert at 6x)

3. Single Event Rule (Google SRE practice)
   - Event consuming > 20% monthly budget = mandatory postmortem
   - Postmortem must include P0 improvements

4. Budget Separation
   - Availability, Quality, Safety are separate buckets
   - Don't mix them: high availability doesn't excuse quality failure
   - Safety violations are always strict (no averaging)

5. Policy Actions Need Owners & Timelines
   - Each status level (Healthy/Caution/Warning/Critical) has a trigger
   - Owner (SRE/PM/ML/Security) must be assigned
   - Action timeline: immediate vs. 24h vs. ongoing

6. Exceptions Matter
   - Infrastructure/dependency failures ≠ your fault
   - Log exceptions explicitly to avoid policy confusion

    """)
