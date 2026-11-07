"""
Alert rule schema and validators.

Based on Day25: "What makes a good alert?"
Each alert must answer three questions:
1. Which SLO/user commitment is threatened?
2. Who owns the response?
3. What's the first safe action?
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Runbook:
    """Runbook structure - must be actionable and testable."""
    title: str
    steps: list[str]
    is_tested: bool = False  # Mark as False if not yet verified in production

    def __post_init__(self):
        if not self.steps:
            raise ValueError("Runbook must have at least one step")


@dataclass
class AlertRule:
    """
    Alert rule template following Day25 principles.

    A good alert connects to user impact, has clear ownership,
    and includes a runbook the on-call engineer can execute in 5 minutes.
    """
    name: str
    description: str

    # Which SLO/commitment is threatened?
    sli: str  # e.g., "Success rate (HTTP 2xx / total)"
    slo: str  # e.g., "99.9% over 30 days"
    user_impact: str  # Explicit statement of how users are affected

    # Who responds?
    owner_team: str

    # How is it triggered?
    condition: str  # e.g., "error_budget_burn_rate > 10x"
    window: str  # e.g., "5 minute"

    # What to do?
    runbook: Runbook

    # When to suppress/resolve?
    resolution_condition: str

    # Optional fields
    owner_oncall: Optional[str] = None
    suppression_condition: Optional[str] = None  # e.g., "maintenance window"
    actionable: bool = True
    actionability_reason: str = ""

    def validate_actionability(self) -> tuple[bool, str]:
        """
        Check if this alert is actionable - can on-call do something about it in 5 minutes?

        Returns:
            (is_actionable, reason)
        """
        issues = []

        if not self.owner_team:
            issues.append("No owner team specified")

        if not self.runbook.steps:
            issues.append("Runbook has no steps")

        if not self.user_impact:
            issues.append("User impact not clearly stated")

        if not self.condition:
            issues.append("Trigger condition not specified")

        # Check if first step is safe and feasible
        if self.runbook.steps:
            first_step = self.runbook.steps[0]
            if "wait" in first_step.lower() or "escalate" in first_step.lower():
                # Escalation is acceptable, but there should be other steps first
                if len(self.runbook.steps) < 2:
                    issues.append("First step is escalation with no investigation step")

        is_actionable = len(issues) == 0
        reason = "; ".join(issues) if issues else "All checks passed"

        return is_actionable, reason
