"""Test SLI fixtures and evaluation functions.

Demonstrates that:
1. Counter-example fixtures correctly fail their respective SLI evaluations
2. Good case passes all evaluations
3. Event schema has no PII labels
"""

import pytest
from app.sli import (
    build_fixtures,
    evaluate_outcome_sli,
    evaluate_latency_sli,
    evaluate_dependency_sli,
    validate_event_labels_no_pii,
)
from app.schemas import SLIEvent, DependencyOutcome


class TestSLIFixtures:
    """Test fixture definitions."""

    def test_fixtures_exist(self):
        """Verify all fixtures are defined."""
        fixtures = build_fixtures()
        assert len(fixtures) > 0
        assert all(hasattr(f, "sli_name") for f in fixtures)
        assert all(hasattr(f, "user_problem") for f in fixtures)
        assert all(hasattr(f, "fixture_event") for f in fixtures)

    def test_fixtures_have_different_scenarios(self):
        """Verify fixtures cover different SLI candidates."""
        fixtures = build_fixtures()
        sli_names = {f.sli_name for f in fixtures if f.sli_name != "all"}
        # Should have fixtures for the three main SLIs
        assert "good_outcome_ratio" in sli_names
        assert "latency_within_threshold" in sli_names
        assert "dependency_timeout_ratio" in sli_names


class TestOutcomeSLI:
    """Test good outcome ratio SLI."""

    def test_good_case_passes(self):
        """Good outcome should pass outcome SLI."""
        event = SLIEvent(
            route="/ask",
            status="good",
            latency_ms=2000,
            dependency="llm_provider",
            dependency_outcome=DependencyOutcome(
                provider="llm_provider",
                status="success",
                latency_ms=1800,
            ),
        )
        assert evaluate_outcome_sli(event) is True

    def test_malformed_response_fails(self):
        """HTTP 200 but missing fields should fail outcome SLI."""
        event = SLIEvent(
            route="/ask",
            status="malformed",
            latency_ms=2000,
            dependency="llm_provider",
            dependency_outcome=DependencyOutcome(
                provider="llm_provider",
                status="success",
                latency_ms=1800,
            ),
        )
        assert evaluate_outcome_sli(event) is False

    def test_dependency_error_fails(self):
        """Dependency error should fail outcome SLI."""
        event = SLIEvent(
            route="/ask",
            status="error",
            latency_ms=5000,
            dependency="llm_provider",
            dependency_outcome=DependencyOutcome(
                provider="llm_provider",
                status="error",
                latency_ms=4900,
            ),
        )
        assert evaluate_outcome_sli(event) is False


class TestLatencySLI:
    """Test latency within threshold SLI."""

    def test_good_case_passes(self):
        """Request within latency threshold should pass."""
        event = SLIEvent(
            route="/ask",
            status="good",
            latency_ms=3000,  # Within 5000ms threshold
            dependency="llm_provider",
            dependency_outcome=DependencyOutcome(
                provider="llm_provider",
                status="success",
                latency_ms=2800,
            ),
        )
        assert evaluate_latency_sli(event, threshold_ms=5000) is True

    def test_slow_request_fails(self):
        """Request exceeding latency threshold should fail."""
        event = SLIEvent(
            route="/ask",
            status="good",  # Successful but slow
            latency_ms=8000,  # Exceeds 5000ms threshold
            dependency="llm_provider",
            dependency_outcome=DependencyOutcome(
                provider="llm_provider",
                status="success",
                latency_ms=7800,
            ),
        )
        assert evaluate_latency_sli(event, threshold_ms=5000) is False

    def test_timeout_status_fails(self):
        """Timeout status should always fail latency SLI."""
        event = SLIEvent(
            route="/ask",
            status="timeout",
            latency_ms=4000,  # Even if under threshold
            dependency="llm_provider",
            dependency_outcome=DependencyOutcome(
                provider="llm_provider",
                status="timeout",
                latency_ms=3900,
            ),
        )
        assert evaluate_latency_sli(event, threshold_ms=5000) is False


class TestDependencySLI:
    """Test dependency timeout ratio SLI."""

    def test_good_case_passes(self):
        """Successful dependency within timeout should pass."""
        event = SLIEvent(
            route="/ask",
            status="good",
            latency_ms=2000,
            dependency="llm_provider",
            dependency_outcome=DependencyOutcome(
                provider="llm_provider",
                status="success",
                latency_ms=1800,
            ),
        )
        assert evaluate_dependency_sli(event, timeout_ms=25000) is True

    def test_dependency_timeout_fails(self):
        """Dependency timeout should fail."""
        event = SLIEvent(
            route="/ask",
            status="timeout",
            latency_ms=30000,
            dependency="llm_provider",
            dependency_outcome=DependencyOutcome(
                provider="llm_provider",
                status="timeout",
                latency_ms=29900,
            ),
        )
        assert evaluate_dependency_sli(event, timeout_ms=25000) is False

    def test_dependency_error_fails(self):
        """Dependency error should fail."""
        event = SLIEvent(
            route="/ask",
            status="error",
            latency_ms=5000,
            dependency="llm_provider",
            dependency_outcome=DependencyOutcome(
                provider="llm_provider",
                status="error",
                latency_ms=4900,
            ),
        )
        assert evaluate_dependency_sli(event, timeout_ms=25000) is False

    def test_missing_dependency_outcome_fails(self):
        """Event without dependency outcome should fail."""
        event = SLIEvent(
            route="/ask",
            status="good",
            latency_ms=2000,
            dependency="llm_provider",
            dependency_outcome=None,
        )
        assert evaluate_dependency_sli(event, timeout_ms=25000) is False


class TestEventValidation:
    """Test that event schema prevents PII in labels."""

    def test_event_has_no_pii_fields(self):
        """Verify event schema doesn't include sensitive fields."""
        event = SLIEvent(
            route="/ask",
            status="good",
            latency_ms=2000,
            dependency="llm_provider",
            dependency_outcome=DependencyOutcome(
                provider="llm_provider",
                status="success",
                latency_ms=1800,
            ),
        )

        # These low-cardinality fields should exist
        assert hasattr(event, "route")
        assert hasattr(event, "status")
        assert hasattr(event, "latency_ms")

        # These high-cardinality fields should NOT exist in event schema
        # (e.g., prompt, user_id, complete_answer)
        assert not hasattr(event, "prompt")
        assert not hasattr(event, "user_id")
        assert not hasattr(event, "answer")

    def test_validate_no_pii(self):
        """Verify validation function accepts event."""
        event = SLIEvent(
            route="/ask",
            status="good",
            latency_ms=2000,
            dependency="llm_provider",
            dependency_outcome=DependencyOutcome(
                provider="llm_provider",
                status="success",
                latency_ms=1800,
            ),
        )
        assert validate_event_labels_no_pii(event) is True


class TestFixtureParity:
    """Test that fixtures correctly represent their counter-examples."""

    def test_outcome_fixture_fails_outcome_sli(self):
        """Outcome SLI counter-example should fail outcome evaluation."""
        fixtures = build_fixtures()
        outcome_fixtures = [f for f in fixtures if f.sli_name == "good_outcome_ratio"]

        for fixture in outcome_fixtures:
            result = evaluate_outcome_sli(fixture.fixture_event)
            # All outcome fixtures should represent bad cases (expected_good=False)
            if fixture.expected_good is False:
                assert result is False, f"Fixture should fail: {fixture}"

    def test_latency_fixture_fails_latency_sli(self):
        """Latency SLI counter-example should fail latency evaluation."""
        fixtures = build_fixtures()
        latency_fixtures = [f for f in fixtures if f.sli_name == "latency_within_threshold"]

        for fixture in latency_fixtures:
            result = evaluate_latency_sli(fixture.fixture_event, threshold_ms=5000)
            # All latency fixtures should represent bad cases
            if fixture.expected_good is False:
                assert result is False, f"Fixture should fail: {fixture}"

    def test_dependency_fixture_fails_dependency_sli(self):
        """Dependency SLI counter-example should fail dependency evaluation."""
        fixtures = build_fixtures()
        dependency_fixtures = [f for f in fixtures if f.sli_name == "dependency_timeout_ratio"]

        for fixture in dependency_fixtures:
            result = evaluate_dependency_sli(fixture.fixture_event, timeout_ms=25000)
            # All dependency fixtures should represent bad cases
            if fixture.expected_good is False:
                assert result is False, f"Fixture should fail: {fixture}"

    def test_good_case_passes_all_slis(self):
        """Good case fixture should pass all SLI evaluations."""
        fixtures = build_fixtures()
        good_fixtures = [f for f in fixtures if f.expected_good is True]

        assert len(good_fixtures) > 0, "Should have at least one good case"

        for fixture in good_fixtures:
            assert evaluate_outcome_sli(fixture.fixture_event) is True
            assert evaluate_latency_sli(fixture.fixture_event, threshold_ms=5000) is True
            assert evaluate_dependency_sli(fixture.fixture_event, timeout_ms=25000) is True
