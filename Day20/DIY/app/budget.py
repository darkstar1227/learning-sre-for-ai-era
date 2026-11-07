"""
Error Budget Calculator for SLO-based reliability management.

Demonstrates the concepts from Day 20: how to calculate burn rate,
remaining budget, and classify policy actions based on budget consumption.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class BudgetStatus(str, Enum):
    """Status classification for budget consumption."""
    HEALTHY = "healthy"
    CAUTION = "caution"
    WARNING = "warning"
    CRITICAL = "critical"


class BudgetType(str, Enum):
    """Types of error budgets managed separately."""
    AVAILABILITY = "availability"
    QUALITY = "quality"
    SAFETY = "safety"


@dataclass
class SLODefinition:
    """Definition of a Service Level Objective."""
    budget_type: BudgetType
    slo_percentage: float  # e.g., 99.5 for 99.5% SLO
    window_days: int = 28  # Rolling window in days
    description: str = ""
    owner: str = ""

    @property
    def acceptable_bad_event_rate(self) -> float:
        """Calculate acceptable bad event rate (0-1 range)."""
        return (100 - self.slo_percentage) / 100.0

    @property
    def monthly_budget_events(self) -> float:
        """Estimate monthly bad events for 1M requests."""
        return self.acceptable_bad_event_rate * 1_000_000

    def describe(self) -> str:
        """Human-readable description of the SLO."""
        return (
            f"{self.budget_type.value.capitalize()} SLO: {self.slo_percentage}% "
            f"({self.window_days}-day window)\n"
            f"  Bad event rate: {self.acceptable_bad_event_rate * 100:.2f}%\n"
            f"  Per 1M requests: {self.monthly_budget_events:,.0f} bad events\n"
            f"  Owner: {self.owner or 'TBD'}"
        )


@dataclass
class WindowMetrics:
    """Metrics for a time window (actual observed values)."""
    window_name: str  # e.g., "Last 1 hour", "Last 6 hours"
    total_requests: int
    bad_events: int

    @property
    def actual_bad_rate(self) -> float:
        """Actual bad event rate (0-1 range)."""
        if self.total_requests == 0:
            return 0.0
        return self.bad_events / self.total_requests

    def calculate_burn_rate(self, slo: SLODefinition) -> float:
        """Calculate burn rate relative to SLO.

        burn_rate = actual_bad_rate / acceptable_bad_rate

        > 1.0: consuming faster than long-term allowance
        <= 1.0: within sustainable pace
        """
        acceptable_rate = slo.acceptable_bad_event_rate
        if acceptable_rate == 0:
            return float('inf') if self.actual_bad_rate > 0 else 0.0
        return self.actual_bad_rate / acceptable_rate

    def classify_status(self, slo: SLODefinition) -> tuple[BudgetStatus, float]:
        """Classify budget status based on burn rate.

        Different thresholds for different budget types.
        Returns (status, burn_rate).
        """
        burn_rate = self.calculate_burn_rate(slo)

        # Type-specific threshold definitions
        if slo.budget_type == BudgetType.AVAILABILITY:
            # Short window (1h) uses stricter threshold than long window (6h)
            if "1" in self.window_name.lower():
                # 1-hour window: detect acute spikes
                if burn_rate > 36:
                    return BudgetStatus.CRITICAL, burn_rate
                elif burn_rate > 6:
                    return BudgetStatus.WARNING, burn_rate
                else:
                    return BudgetStatus.HEALTHY, burn_rate
            else:
                # 6-hour+ window: avoid false alarms from temporary spikes
                if burn_rate > 6:
                    return BudgetStatus.CRITICAL, burn_rate
                elif burn_rate > 2:
                    return BudgetStatus.WARNING, burn_rate
                else:
                    return BudgetStatus.HEALTHY, burn_rate

        elif slo.budget_type == BudgetType.QUALITY:
            if burn_rate > 10:
                return BudgetStatus.CRITICAL, burn_rate
            elif burn_rate > 3:
                return BudgetStatus.WARNING, burn_rate
            else:
                return BudgetStatus.HEALTHY, burn_rate

        elif slo.budget_type == BudgetType.SAFETY:
            # Safety is always strict: any anomaly is critical
            if burn_rate > 3:
                return BudgetStatus.CRITICAL, burn_rate
            elif burn_rate > 1:
                return BudgetStatus.WARNING, burn_rate
            else:
                return BudgetStatus.HEALTHY, burn_rate

        return BudgetStatus.HEALTHY, burn_rate


@dataclass
class RollingWindowBudget:
    """Tracks budget consumption over a rolling window."""
    slo: SLODefinition
    total_requests_in_window: int
    bad_events_in_window: int

    @property
    def consumed_percentage(self) -> float:
        """What percentage of monthly budget has been consumed?"""
        monthly_budget = self.slo.monthly_budget_events
        if monthly_budget == 0:
            return 0.0
        return min((self.bad_events_in_window / monthly_budget) * 100, 100.0)

    @property
    def remaining_percentage(self) -> float:
        """What percentage of monthly budget remains?"""
        return max(100.0 - self.consumed_percentage, 0.0)

    @property
    def remaining_bad_events(self) -> int:
        """How many more bad events can occur before SLO is breached?"""
        monthly_budget = self.slo.monthly_budget_events
        return max(int(monthly_budget - self.bad_events_in_window), 0)

    def status_for_consumption(self) -> BudgetStatus:
        """Classify status based on cumulative consumption."""
        consumed = self.consumed_percentage
        if consumed > 80:
            return BudgetStatus.CRITICAL
        elif consumed > 50:
            return BudgetStatus.WARNING
        elif consumed > 20:
            return BudgetStatus.CAUTION
        else:
            return BudgetStatus.HEALTHY

    def check_single_event_rule(self, event_bad_count: int) -> bool:
        """Check if a single event exceeds 20% of monthly budget.

        Google SRE rule: single event > 20% requires postmortem.
        """
        monthly_budget = self.slo.monthly_budget_events
        if monthly_budget == 0:
            return False
        return (event_bad_count / monthly_budget) > 0.20

    def describe(self) -> str:
        """Human-readable budget status."""
        lines = [
            f"{self.slo.budget_type.value.upper()} BUDGET STATUS",
            f"  SLO Target: {self.slo.slo_percentage}%",
            f"  Window: {self.slo.window_days} days (rolling)",
            f"",
            f"  Consumption: {self.consumed_percentage:.1f}% ({self.bad_events_in_window:,} bad events)",
            f"  Remaining: {self.remaining_percentage:.1f}% ({self.remaining_bad_events:,} more allowed)",
            f"  Status: {self.status_for_consumption().value.upper()}",
            f"",
            f"  Safe range: < 20% consumed = {int(0.20 * self.slo.monthly_budget_events):,} bad events",
        ]
        return "\n".join(lines)


def format_policy_action(budget: RollingWindowBudget, burn_rate: Optional[float] = None) -> str:
    """Generate policy action based on budget status."""
    status = budget.status_for_consumption()
    budget_type = budget.slo.budget_type.value

    actions = {
        BudgetStatus.HEALTHY: f"✓ {budget_type.capitalize()} budget healthy. Continue normal operations.",
        BudgetStatus.CAUTION: f"⚠ {budget_type.capitalize()} budget 20-50% consumed. Monitor closely, reduce velocity.",
        BudgetStatus.WARNING: f"⚠️ {budget_type.capitalize()} budget 50-80% consumed. Pause non-critical rollouts.",
        BudgetStatus.CRITICAL: f"🚨 {budget_type.capitalize()} budget > 80% consumed. FREEZE deployments.",
    }

    action = actions.get(status, "Unknown status")
    if burn_rate is not None:
        action += f"\n   Current burn rate: {burn_rate:.1f}x (acceptable: 1.0x)"

    return action
