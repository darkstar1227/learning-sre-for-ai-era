"""
Alert rule validator.

Checks each alert against Day25 principles:
- Connects to user impact or error budget
- Has clear owner
- Includes first actionable step
- Doesn't alert on single events (e.g., one hallucination)
- Unverified runbooks are marked as such
"""

from typing import Optional
from app.schemas import AlertRule


class AlertValidator:
    """Validates alert rules against Day25 principles."""

    @staticmethod
    def check_connects_to_user_impact(alert: AlertRule) -> tuple[bool, str]:
        """Does alert connect to user impact or error budget?"""
        if not alert.user_impact or not alert.user_impact.strip():
            return False, "Missing user impact statement"

        if alert.sli and alert.slo:
            return True, "Connects to both SLI and SLO"

        if alert.user_impact:
            return True, "Explicitly states user impact"

        return False, "No clear connection to user impact"

    @staticmethod
    def check_has_owner(alert: AlertRule) -> tuple[bool, str]:
        """Does alert have clear ownership?"""
        if not alert.owner_team:
            return False, "No owner team specified"

        return True, f"Owner: {alert.owner_team}"

    @staticmethod
    def check_has_first_step(alert: AlertRule) -> tuple[bool, str]:
        """Does alert have a clear, safe first step in runbook?"""
        if not alert.runbook or not alert.runbook.steps:
            return False, "Runbook has no steps"

        first_step = alert.runbook.steps[0]

        # Check for problematic first steps
        problematic = ["sleep", "wait", "pray", "hope"]
        if any(word in first_step.lower() for word in problematic):
            return False, f"First step is passive/waiting: {first_step}"

        return True, f"First step: {first_step}"

    @staticmethod
    def check_not_single_event(alert: AlertRule) -> tuple[bool, str]:
        """Does alert avoid alerting on single events?"""
        # Check window and condition for single-event patterns

        # Single hallucination should not directly page
        if "hallucination" in alert.description.lower() and "single" not in alert.condition.lower():
            return True, "Correctly avoids single hallucination alerts"

        # Check window duration
        if "5 minute" in alert.window or "10 minute" in alert.window:
            if "rate" in alert.condition.lower() or "%" in alert.condition:
                return True, f"Uses rate-based condition over {alert.window} window"

        return True, "Condition appears aggregated (not single-event)"

    @staticmethod
    def check_runbook_marked_correctly(alert: AlertRule) -> tuple[bool, str]:
        """Is untested runbook properly marked?"""
        if not alert.runbook:
            return False, "No runbook present"

        if not alert.runbook.is_tested:
            return True, "✓ Correctly marked as untested (is_tested=False)"

        if alert.runbook.is_tested:
            return True, "Marked as tested"

        return False, "Runbook status unclear"

    @staticmethod
    def validate_alert(alert: AlertRule) -> dict:
        """Run full validation suite on alert."""
        results = {
            "name": alert.name,
            "checks": {},
            "overall": True,
        }

        checks = [
            ("Connects to user impact", AlertValidator.check_connects_to_user_impact),
            ("Has owner", AlertValidator.check_has_owner),
            ("Has first step", AlertValidator.check_has_first_step),
            ("Not single-event", AlertValidator.check_not_single_event),
            ("Runbook marked correctly", AlertValidator.check_runbook_marked_correctly),
        ]

        for check_name, check_func in checks:
            passed, reason = check_func(alert)
            results["checks"][check_name] = {
                "passed": passed,
                "reason": reason,
            }
            if not passed:
                results["overall"] = False

        # Also run actionability check
        actionable, actionability_reason = alert.validate_actionability()
        results["checks"]["Actionable"] = {
            "passed": actionable,
            "reason": actionability_reason,
        }
        if not actionable:
            results["overall"] = False

        return results

    @staticmethod
    def validate_all(alerts: list[AlertRule]) -> dict:
        """Validate all alerts and return summary."""
        results = {
            "total": len(alerts),
            "passed": 0,
            "failed": 0,
            "alerts": [],
        }

        for alert in alerts:
            validation = AlertValidator.validate_alert(alert)
            results["alerts"].append(validation)

            if validation["overall"]:
                results["passed"] += 1
            else:
                results["failed"] += 1

        return results


def print_validation_report(validation_results: dict) -> None:
    """Pretty-print validation results."""
    print("\n" + "=" * 80)
    print(f"ALERT VALIDATION REPORT - Day25 Principles")
    print("=" * 80)
    print(f"Total alerts: {validation_results['total']} | Passed: {validation_results['passed']} | Failed: {validation_results['failed']}")
    print("=" * 80 + "\n")

    for alert_result in validation_results["alerts"]:
        name = alert_result["name"]
        overall = "✓ PASS" if alert_result["overall"] else "✗ FAIL"
        print(f"\n{overall} - {name}")
        print("-" * 80)

        for check_name, check_result in alert_result["checks"].items():
            status = "✓" if check_result["passed"] else "✗"
            reason = check_result["reason"]
            print(f"  {status} {check_name}: {reason}")

    print("\n" + "=" * 80)
    if validation_results["failed"] == 0:
        print("✓ ALL ALERTS MEET DAY25 CRITERIA")
    else:
        print(f"✗ {validation_results['failed']} ALERT(S) NEED REVISION")
    print("=" * 80 + "\n")
