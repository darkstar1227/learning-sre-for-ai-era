#!/usr/bin/env python3
"""
Display all alert rules in a readable format.

Usage:
    uv run python scripts/show_alerts.py
"""

from app.alert_rules import ALL_ALERTS


def print_alert_detail(alert, index):
    """Print a single alert rule in detail."""
    print(f"\n{'=' * 80}")
    print(f"ALERT {index}: {alert.name}")
    print('=' * 80)
    print(f"\n📋 Description:\n{alert.description}\n")

    print("📊 SLI/SLO:")
    print(f"  SLI: {alert.sli}")
    print(f"  SLO: {alert.slo}")
    print(f"  User Impact: {alert.user_impact}\n")

    print("👤 Ownership:")
    print(f"  Team: {alert.owner_team}")
    if alert.owner_oncall:
        print(f"  On-Call: {alert.owner_oncall}\n")

    print("🔔 Trigger:")
    print(f"  Condition: {alert.condition}")
    print(f"  Window: {alert.window}\n")

    print("📖 Runbook: " + alert.runbook.title)
    print(f"  Status: {'✓ Tested' if alert.runbook.is_tested else '⚠ Untested (draft)'}")
    print("  Steps:")
    for i, step in enumerate(alert.runbook.steps, 1):
        print(f"    {i}. {step}")
    print()

    print("⚙️ Conditions:")
    print(f"  Suppression: {alert.suppression_condition or '(none)'}")
    print(f"  Resolution: {alert.resolution_condition}\n")

    print("✓ Actionability Assessment:")
    is_actionable, reason = alert.validate_actionability()
    status = "✓ YES" if is_actionable else "✗ NO"
    print(f"  {status}")
    if reason:
        print(f"  {reason}")


def main():
    """Display all alerts."""
    print("\n" + "=" * 80)
    print("DAY25 - ALERT RULE REVIEW")
    print("Three alert rule drafts for: Availability, Latency, Dependency")
    print("=" * 80)

    for i, alert in enumerate(ALL_ALERTS, 1):
        print_alert_detail(alert, i)

    print("\n" + "=" * 80)
    print("KEY QUESTIONS (from Day25):")
    print("=" * 80)
    print("1. Which SLO/user commitment is threatened? → Check 'User Impact' section")
    print("2. Who owns the response? → Check 'Ownership' section")
    print("3. What's the first safe action? → Check 'Runbook' steps")
    print("4. Can on-call execute within 5 minutes? → Check 'Actionability Assessment'")
    print()
    print("If you can't answer all four, the alert should be downgraded to dashboard/ticket")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
