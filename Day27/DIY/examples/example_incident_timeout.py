"""
Example incident: Cascading timeout failure from Day3 Chaos Engineering scenario.

This demonstrates how to structure a real incident postmortem based on actual
chaos engineering test results from Day3.
"""

from datetime import datetime, timedelta
from app.models import (
    Incident, AlertInfo, TriageInfo, MitigationStep, RecoveryInfo,
    RootCauseAnalysis, AISpecificFactors, ActionItem, SeverityLevel
)


def create_example_timeout_incident() -> Incident:
    """
    Create an example incident: Database connection timeout cascading to API errors.

    Scenario: During a chaos test, database response latency increased from 10ms
    to 5000ms. The API's connection pool exhausted waiting for responses, causing
    cascading failures and 500 errors for all users.
    """

    now = datetime.utcnow()

    incident = Incident(
        incident_id="INC-2026-001",
        title="Database Latency Spike Causes API Connection Pool Exhaustion",
        severity=SeverityLevel.SEV2,
        service_affected="api-service",
        created_at=now - timedelta(hours=2),

        # Detect Stage: Alert triggered
        detect=AlertInfo(
            name="API P99 latency > 5s",
            triggered_at=now - timedelta(hours=2),
            threshold="P99 latency < 2000ms",
            current_value="P99 latency = 8500ms"
        ),

        # Triage Stage: Initial assessment
        triage=TriageInfo(
            incident_commander="Alice (SRE on-call)",
            severity=SeverityLevel.SEV2,
            affected_systems=["api-service", "postgresql"],
            estimated_impact_scope=(
                "~85% of requests experiencing >5s latency. "
                "Approximately 2,000 active users affected. "
                "SLA risk: 10% error rate vs 0.1% threshold."
            ),
            immediate_risk=(
                "If cascading timeouts continue, connection pool will completely "
                "exhaust, leading to total API unavailability (SEV1 escalation)."
            )
        ),

        # Mitigate Stage: Actions taken
        mitigations=[
            MitigationStep(
                action="Checked database metrics: discovered CPU at 95%, lock contention on user_session table",
                executed_at=now - timedelta(minutes=90),
                expected_effect="Identify root cause at database layer",
                actual_effect="Successfully identified: ongoing VACUUM on user_session table blocking reads"
            ),
            MitigationStep(
                action="Killed long-running VACUUM job (PID 12345) using pg_terminate_backend()",
                executed_at=now - timedelta(minutes=75),
                expected_effect="Database latency should drop immediately, API recovery follows",
                actual_effect="Database latency dropped from 5000ms to 15ms within 30 seconds"
            ),
            MitigationStep(
                action="Verified API P99 latency returned to <500ms",
                executed_at=now - timedelta(minutes=60),
                expected_effect="User experience normalized",
                actual_effect="Confirmed: no requests timeout, error rate back to baseline 0.01%"
            ),
        ],

        # Recover Stage: Proof of recovery
        recovery=RecoveryInfo(
            recovery_completed_at=now - timedelta(minutes=60),
            sli_metric="P99 latency (API)",
            baseline_value="<500ms",
            recovery_value="245ms",
            verification_method=(
                "Grafana Tempo: sampled 10 random traces from 14:45-14:50 UTC, "
                "all completed in <300ms. Prometheus: P99 latency stable at 245ms for >10min. "
                "Manual user testing: feature workflows complete normally."
            )
        ),

        # Root Cause Analysis
        root_cause=RootCauseAnalysis(
            root_cause=(
                "PostgreSQL initiated an automatic VACUUM ANALYZE on the user_session table "
                "at 14:32 UTC due to autovacuum_naptime. This VACUUM acquired AccessExclusiveLock, "
                "blocking all read queries on the table. Since user session lookup is on the critical "
                "path of every request, the blocked queries filled the API connection pool (max 50 connections), "
                "causing all new requests to timeout or fail."
            ),
            contributing_factors=[
                "VACUUM was not scheduled; it ran automatically during peak traffic hours",
                "No monitoring alert for database lock contention existed",
                "API connection pool timeout was set to 30s (aggressive but reasonable)",
                "No circuit breaker between API and database",
            ],
            detection_gap=(
                "Monitoring alerted on API P99 latency but not on database lock contention. "
                "Query performance metrics (avg query time) were available but not dashboarded. "
                "Database pg_stat_statements was not queried during triage (would have shown "
                "blocked queries immediately)."
            ),
            prevention_gap=(
                "VACUUM should not run during peak hours (06:00-22:00 UTC). "
                "Need alert on pg_locks where waiters > 0. "
                "Should add circuit breaker pattern at API ↔ DB boundary. "
                "Connection pool exhaustion should trigger alert before user impact."
            )
        ),

        # AI-Specific Factors (this was not an AI-related failure, but showing the structure)
        # Not applicable to this example, but would include if incident involved LLM/RAG

        # What went well
        what_went_well=[
            "Alert fired within 15 seconds of the cascade starting",
            "On-call engineer found root cause in <10 minutes (killed VACUUM immediately)",
            "Database recovered instantly once VACUUM was killed",
            "No data loss, no customer data exposed",
            "Team communication was clear; timeline documented in real-time",
        ],

        # Lessons learned
        what_we_learned=[
            "Database automatic maintenance (VACUUM) should not run during peak hours",
            "Need to monitor database lock contention, not just query latency",
            "API connection pool exhaustion is a cascade point - needs separate alerting",
            "Circuit breaker pattern would have prevented user impact even if DB was slow",
            "pg_stat_statements is powerful for diagnosis but not integrated into dashboards",
        ],

        # Action items
        action_items=[
            ActionItem(
                title="Disable autovacuum during peak hours (06:00-22:00 UTC)",
                owner="Bob (Database team)",
                deadline=now + timedelta(days=7),
                category="database",
                priority="high",
                status="open"
            ),
            ActionItem(
                title="Create alert for pg_locks with waiters > 0",
                owner="Charlie (Monitoring/SRE)",
                deadline=now + timedelta(days=7),
                category="monitoring",
                priority="high",
                status="open"
            ),
            ActionItem(
                title="Add database lock contention dashboard to Grafana",
                owner="Charlie (Monitoring/SRE)",
                deadline=now + timedelta(days=14),
                category="monitoring",
                priority="high",
                status="open"
            ),
            ActionItem(
                title="Implement circuit breaker for API ↔ Database calls",
                owner="David (API team)",
                deadline=now + timedelta(days=21),
                category="architecture",
                priority="medium",
                status="open"
            ),
            ActionItem(
                title="Add connection pool exhaustion alert",
                owner="Charlie (Monitoring/SRE)",
                deadline=now + timedelta(days=10),
                category="monitoring",
                priority="high",
                status="open"
            ),
            ActionItem(
                title="Document emergency procedures for killing stuck VACUUM in runbook",
                owner="Eve (Documentation)",
                deadline=now + timedelta(days=3),
                category="runbook",
                priority="high",
                status="open"
            ),
        ]
    )

    return incident


if __name__ == "__main__":
    from app.templates import generate_postmortem_markdown

    incident = create_example_timeout_incident()
    markdown = generate_postmortem_markdown(incident)

    print(markdown)
