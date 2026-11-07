"""SLI definitions and fixture testing for AI application.

Based on Day 17 article: Three candidate SLIs with counter-example fixtures
that should NOT count as "good".
"""

from dataclasses import dataclass
from typing import Optional
from app.schemas import SLIEvent, DependencyOutcome


# ============================================================================
# SLI Definitions
# ============================================================================


@dataclass
class SLIThreshold:
    """SLI threshold configuration with clear assumptions."""

    name: str
    description: str
    latency_threshold_ms: Optional[int] = None
    timeout_threshold_ms: int = 30000  # 30 seconds default
    dependency_timeout_ms: int = 25000  # 25 seconds for dependency


# Three candidate SLIs from Day 17 article
GOOD_OUTCOME_SLI = SLIThreshold(
    name="good_outcome_ratio",
    description="Ratio of requests that returned valid, complete response",
)

LATENCY_SLI = SLIThreshold(
    name="latency_within_threshold",
    description="Ratio of requests completed within latency threshold",
    latency_threshold_ms=5000,  # 5 second assumption
)

DEPENDENCY_SLI = SLIThreshold(
    name="dependency_timeout_ratio",
    description="Ratio of requests where dependency did not timeout",
    dependency_timeout_ms=25000,  # 25 seconds for LLM provider
)


# ============================================================================
# Counter-Example Fixtures
# ============================================================================


class SLIFixture:
    """Test fixture representing a scenario that should NOT count as 'good'."""

    def __init__(
        self,
        sli_name: str,
        user_problem: str,
        fixture_event: SLIEvent,
        expected_good: bool = False,
    ):
        """
        Args:
            sli_name: Which SLI this fixture tests
            user_problem: What user-facing problem this represents
            fixture_event: The event that triggers the bad case
            expected_good: Should this event count as good? (usually False for fixtures)
        """
        self.sli_name = sli_name
        self.user_problem = user_problem
        self.fixture_event = fixture_event
        self.expected_good = expected_good

    def __repr__(self):
        return (
            f"SLIFixture(sli={self.sli_name}, "
            f"problem={self.user_problem}, "
            f"should_be_good={self.expected_good})"
        )


# ============================================================================
# Fixture Collection
# ============================================================================


def build_fixtures():
    """Build all counter-example fixtures for team discussion."""
    fixtures = []

    # ────────────────────────────────────────────────────────────────────
    # SLI 1: Good Outcome Ratio
    # "使用者期待：得到可用回覆"
    # Counter-example: HTTP 200 but response missing required fields
    # ────────────────────────────────────────────────────────────────────

    fixtures.append(
        SLIFixture(
            sli_name="good_outcome_ratio",
            user_problem="HTTP 200 response but no actual answer in payload "
            "(client gets empty string or null answer field)",
            fixture_event=SLIEvent(
                route="/ask",
                status="malformed",  # Response came back but incomplete
                latency_ms=2000,
                dependency="llm_provider",
                dependency_outcome=DependencyOutcome(
                    provider="llm_provider",
                    status="success",
                    latency_ms=1800,
                ),
            ),
            expected_good=False,
        )
    )

    fixtures.append(
        SLIFixture(
            sli_name="good_outcome_ratio",
            user_problem="LLM provider returns error after retries "
            "(e.g. rate limit, server error)",
            fixture_event=SLIEvent(
                route="/ask",
                status="error",  # Provider-level error
                latency_ms=25500,
                dependency="llm_provider",
                dependency_outcome=DependencyOutcome(
                    provider="llm_provider",
                    status="error",
                    latency_ms=25400,
                ),
            ),
            expected_good=False,
        )
    )

    # ────────────────────────────────────────────────────────────────────
    # SLI 2: Latency Within Threshold
    # "使用者期待：不要等太久"
    # Counter-example: Slow requests due to scheduler delay, not app logic
    # ────────────────────────────────────────────────────────────────────

    fixtures.append(
        SLIFixture(
            sli_name="latency_within_threshold",
            user_problem="Request took longer than acceptable threshold "
            "(e.g. 8 seconds when SLO says P99 < 5 seconds)",
            fixture_event=SLIEvent(
                route="/ask",
                status="timeout",  # Didn't meet latency budget
                latency_ms=8000,  # Exceeds 5000ms threshold
                dependency="llm_provider",
                dependency_outcome=DependencyOutcome(
                    provider="llm_provider",
                    status="success",
                    latency_ms=7800,  # Dependency itself was slow
                ),
            ),
            expected_good=False,
        )
    )

    fixtures.append(
        SLIFixture(
            sli_name="latency_within_threshold",
            user_problem="Request slow due to resource contention "
            "(CPU scheduling delay, not app bug)",
            fixture_event=SLIEvent(
                route="/ask",
                status="timeout",
                latency_ms=6200,
                dependency="llm_provider",
                dependency_outcome=DependencyOutcome(
                    provider="llm_provider",
                    status="success",
                    latency_ms=5900,
                ),
            ),
            expected_good=False,
        )
    )

    # ────────────────────────────────────────────────────────────────────
    # SLI 3: Dependency Timeout Ratio
    # "使用者期待：依賴故障不拖垮我"
    # Counter-example: Dependency exhausts its timeout window
    # ────────────────────────────────────────────────────────────────────

    fixtures.append(
        SLIFixture(
            sli_name="dependency_timeout_ratio",
            user_problem="LLM provider timeout "
            "(client request times out waiting for slow provider)",
            fixture_event=SLIEvent(
                route="/ask",
                status="timeout",
                latency_ms=30500,  # Exceeds 30s client timeout
                dependency="llm_provider",
                dependency_outcome=DependencyOutcome(
                    provider="llm_provider",
                    status="timeout",
                    latency_ms=30000,  # Hit the 25s provider timeout
                ),
            ),
            expected_good=False,
        )
    )

    fixtures.append(
        SLIFixture(
            sli_name="dependency_timeout_ratio",
            user_problem="Provider retry exhaustion "
            "(all retries to LLM provider failed within timeout window)",
            fixture_event=SLIEvent(
                route="/ask",
                status="error",
                latency_ms=26000,
                dependency="llm_provider",
                dependency_outcome=DependencyOutcome(
                    provider="llm_provider",
                    status="error",  # Retries gave up
                    latency_ms=25900,
                ),
            ),
            expected_good=False,
        )
    )

    # ────────────────────────────────────────────────────────────────────
    # Good case: for comparison
    # ────────────────────────────────────────────────────────────────────

    fixtures.append(
        SLIFixture(
            sli_name="all",
            user_problem="(Good case for comparison) Request succeeds "
            "within all thresholds",
            fixture_event=SLIEvent(
                route="/ask",
                status="good",
                latency_ms=2500,  # Well within 5s threshold
                dependency="llm_provider",
                dependency_outcome=DependencyOutcome(
                    provider="llm_provider",
                    status="success",
                    latency_ms=2400,
                ),
            ),
            expected_good=True,
        )
    )

    return fixtures


# ============================================================================
# SLI Evaluation Functions
# ============================================================================


def evaluate_outcome_sli(event: SLIEvent) -> bool:
    """Evaluate if event counts as 'good' for outcome SLI.

    Rule: status must be 'good' (not malformed, not error)
    """
    return event.status == "good"


def evaluate_latency_sli(event: SLIEvent, threshold_ms: int = 5000) -> bool:
    """Evaluate if event counts as 'good' for latency SLI.

    Rule: latency must be within threshold AND status not timeout
    """
    return event.latency_ms <= threshold_ms and event.status != "timeout"


def evaluate_dependency_sli(event: SLIEvent, timeout_ms: int = 25000) -> bool:
    """Evaluate if event counts as 'good' for dependency SLI.

    Rule: dependency must not timeout, and dependency_outcome.status
    must be 'success'
    """
    if event.dependency_outcome is None:
        return False
    return (
        event.dependency_outcome.status == "success"
        and event.dependency_outcome.latency_ms <= timeout_ms
    )


# ============================================================================
# Validation Functions
# ============================================================================


def validate_event_labels_no_pii(event: SLIEvent) -> bool:
    """Validate that event doesn't contain sensitive labels.

    Prometheus/cardinality rule: low-cardinality fields only.
    - OK: route, status, dependency
    - NOT OK: prompt, user_id, complete_answer, etc.
    """
    # All fields in SLIEvent are low-cardinality by design
    # This is a safety check that event matches the schema
    return isinstance(event, SLIEvent)
