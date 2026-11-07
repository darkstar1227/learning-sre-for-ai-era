"""
Data models for AI alerting triage system.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Optional


class TriageRoute(StrEnum):
    """Where a signal should be routed."""
    PAGER = "pager"  # Immediate on-call escalation
    EVALUATION_QUEUE = "evaluation_queue"  # Batch analysis
    SECURITY_REVIEW = "security_review"  # Security incident escalation


class SignalType(StrEnum):
    """Categories of signals in AI systems."""
    INFRASTRUCTURE = "infrastructure"
    MODEL_OUTPUT = "model_output"
    DEPENDENCY = "dependency"
    RESOURCE = "resource"
    SAFETY = "safety"


class ImpactScope(StrEnum):
    """Scope of signal impact."""
    SINGLE_SAMPLE = "single_sample"
    ROLLING_WINDOW_TREND = "rolling_window_trend"
    WIDE_OUTAGE = "wide_outage"


@dataclass
class Signal:
    """A single signal (metric, error, quality issue) from the AI system."""

    name: str
    """Name of the signal (e.g., 'model_timeout_rate', 'citation_valid_ratio')"""

    signal_type: SignalType
    """Category of the signal"""

    current_value: float | str
    """Current value or status"""

    is_actionable: bool
    """Can the on-call engineer do something about it right now?"""

    impact_scope: ImpactScope
    """How many users/requests are affected?"""

    slo_burn_rate: Optional[float] = None
    """For infrastructure signals: how fast is SLO burning? (0-1)"""

    is_safety_risk: bool = False
    """Does this involve high-risk unauthorized actions, data exposure, or harm?"""

    description: str = ""
    """Human-readable description of what triggered this signal"""


@dataclass
class TriageRule:
    """A rule for routing a signal to a destination."""

    name: str
    """Name of the rule (e.g., 'model_outage_rule')"""

    condition: str
    """Human-readable condition (e.g., 'model timeout AND SLO burn > 50% in 5min')"""

    route: TriageRoute
    """Where this signal should go"""

    owner: str
    """Responsible team/person"""

    runbook: Optional[str] = None
    """Link to runbook or playbook"""

    def check(self, signal: Signal) -> bool:
        """
        Evaluate if this rule applies to the given signal.
        (Simplified evaluation logic)
        """
        # This is a placeholder for more complex rule evaluation
        # In production, this would be a proper rule engine
        return True


@dataclass
class TriageResult:
    """Result of triaging a signal."""

    signal: Signal
    routes: list[TriageRoute]
    """All applicable routes (usually 1, but safety events might trigger multiple)"""

    owner: str
    """Responsible team/person"""

    priority: str
    """'urgent' for pager, 'normal' for evaluation queue, 'immediate' for security"""

    reason: str
    """Explanation for this triage decision"""


class TriageEngine:
    """
    Engine for triaging AI system signals.

    Separates signals into three flows:
    1. pager: Model outages, queue backlog, GPU saturation, critical provider failures
    2. evaluation_queue: Quality trends (citation ratio down), performance issues
    3. security_review: Unauthorized actions, data exposure, clear harm
    """

    def __init__(self):
        self.rules: list[TriageRule] = []

    def add_rule(self, rule: TriageRule) -> None:
        """Register a triage rule."""
        self.rules.append(rule)

    def triage(self, signal: Signal) -> TriageResult:
        """Triage a single signal into appropriate route(s)."""
        routes = []
        reason = ""
        owner = "unknown"
        priority = "normal"

        # Rule 1: Wide-impact infrastructure/resource/dependency failures -> pager
        if (signal.signal_type in [SignalType.INFRASTRUCTURE, SignalType.RESOURCE, SignalType.DEPENDENCY]) and \
           signal.impact_scope == ImpactScope.WIDE_OUTAGE and \
           signal.slo_burn_rate is not None and signal.slo_burn_rate > 0.5:
            routes.append(TriageRoute.PAGER)
            owner = "on-call"
            priority = "urgent"
            reason = "Infrastructure/resource failure causing rapid SLO burn"

        # Rule 2: Safety risks -> security review (always, regardless of scope)
        if signal.is_safety_risk:
            routes.append(TriageRoute.SECURITY_REVIEW)
            owner = "security-team"
            priority = "immediate"
            reason = "High-risk safety signal requiring immediate security review"

        # Rule 3: Quality trends (not single samples) -> evaluation queue
        if signal.signal_type == SignalType.MODEL_OUTPUT and \
           signal.impact_scope == ImpactScope.ROLLING_WINDOW_TREND and \
           not signal.is_safety_risk:
            routes.append(TriageRoute.EVALUATION_QUEUE)
            if not routes or routes[-1] != TriageRoute.SECURITY_REVIEW:
                owner = "model-owner"
                priority = "normal"
                reason = "Quality trend detected, route to evaluation for root cause analysis"

        # Rule 4: Single hallucinations without wide impact -> evaluation queue
        if signal.signal_type == SignalType.MODEL_OUTPUT and \
           signal.impact_scope == ImpactScope.SINGLE_SAMPLE and \
           not signal.is_safety_risk:
            routes.append(TriageRoute.EVALUATION_QUEUE)
            if not routes or routes[-1] != TriageRoute.SECURITY_REVIEW:
                owner = "model-owner"
                priority = "normal"
                reason = "Single sample quality issue, route to evaluation queue"

        # Default: evaluation queue if no other route applies
        if not routes:
            routes.append(TriageRoute.EVALUATION_QUEUE)
            owner = "platform-team"
            priority = "normal"
            reason = "No immediate action required, routing to evaluation"

        return TriageResult(
            signal=signal,
            routes=routes,
            owner=owner,
            priority=priority,
            reason=reason,
        )
