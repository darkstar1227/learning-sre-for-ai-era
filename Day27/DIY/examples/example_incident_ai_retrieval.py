"""
Example incident: AI Retrieval workflow returning stale knowledge base results.

This demonstrates postmortem structure for AI-specific failures involving
model versions, evaluation gaps, and safety checks.
"""

from datetime import datetime, timedelta
from app.models import (
    Incident, AlertInfo, TriageInfo, MitigationStep, RecoveryInfo,
    RootCauseAnalysis, AISpecificFactors, ActionItem, SeverityLevel
)


def create_example_ai_retrieval_incident() -> Incident:
    """
    Create an example AI incident: RAG retrieval returning stale documentation.

    Scenario: User reported that the AI assistant's retrieval workflow was returning
    outdated API documentation (v1.2) instead of current version (v2.1). This was
    because the embedding index wasn't updated after the new documentation was published.
    """

    now = datetime.utcnow()

    incident = Incident(
        incident_id="INC-2026-005",
        title="RAG Retrieval Returning Stale Knowledge Base (v1.2 vs v2.1)",
        severity=SeverityLevel.SEV2,
        service_affected="ai-retrieval-service",
        created_at=now - timedelta(hours=3),

        # Detect Stage
        detect=AlertInfo(
            name="Manual user report + Evaluation system catch",
            triggered_at=now - timedelta(hours=3, minutes=15),
            threshold="Retrieval accuracy (golden dataset) should be >95%",
            current_value="Accuracy dropped to 76% for 'API docs' queries"
        ),

        # Triage Stage
        triage=TriageInfo(
            incident_commander="Frank (AI/ML on-call)",
            severity=SeverityLevel.SEV2,
            affected_systems=["retrieval-service", "knowledge-base-index"],
            estimated_impact_scope=(
                "~40% of queries use retrieval feature. "
                "Estimated 500 users saw incorrect/outdated information. "
                "No SLA breach (users didn't timeout), but accuracy was severely degraded. "
                "Risk of reputational damage if pattern continues."
            ),
            immediate_risk=(
                "Users receiving wrong information (though not catastrophic). "
                "If evaluation system hadn't caught this, stale index could have persisted for days."
            )
        ),

        # Mitigate Stage
        mitigations=[
            MitigationStep(
                action="Checked embedding index timestamp: last updated 2026-09-19 13:00 UTC. Documentation published 2026-09-20 08:00 UTC.",
                executed_at=now - timedelta(hours=2, minutes=45),
                expected_effect="Identify that index is stale",
                actual_effect="Confirmed: index was 23 hours behind latest docs"
            ),
            MitigationStep(
                action="Triggered immediate re-indexing of knowledge base against v2.1 docs (using app/reindex_knowledge.py --force)",
                executed_at=now - timedelta(hours=2, minutes=30),
                expected_effect="New embeddings generated and pushed to retrieval service within 5 minutes",
                actual_effect="Reindexing completed in 4m 32s. New index deployed without service restart."
            ),
            MitigationStep(
                action="Ran evaluation suite against new index (500 golden queries)",
                executed_at=now - timedelta(hours=2, minutes=10),
                expected_effect="Accuracy should return to >95%",
                actual_effect="Accuracy returned to 96.8%. All previously-failing queries now pass."
            ),
        ],

        # Recover Stage
        recovery=RecoveryInfo(
            recovery_completed_at=now - timedelta(hours=2),
            sli_metric="Retrieval accuracy (golden dataset)",
            baseline_value=">95%",
            recovery_value="96.8%",
            verification_method=(
                "Ran full evaluation suite (500 golden queries) against new index. "
                "Spot-checked 20 user queries in staging environment. "
                "Confirmed Tempo traces showing retrieval returning v2.1 docs. "
                "No performance regression (latency still <200ms)."
            )
        ),

        # Root Cause Analysis
        root_cause=RootCauseAnalysis(
            root_cause=(
                "Knowledge base documentation was updated to v2.1 on 2026-09-20 08:00 UTC, "
                "but the trigger for automatic re-indexing (webhook from docs repository) "
                "was not firing. The embedding index pipeline continued using stale v1.2 docs. "
                "Root cause: webhook auth token expired on 2026-09-18, and no monitoring "
                "alerted on failed webhook deliveries."
            ),
            contributing_factors=[
                "Webhook auth token was set to 90-day TTL with no renewal reminder",
                "No monitoring on webhook delivery success rate",
                "Evaluation system only runs on deployment, not continuously",
                "Knowledge base update process doesn't explicitly verify index freshness",
            ],
            detection_gap=(
                "Evaluation system caught the issue (good!), but only because we ran it "
                "after deployment. There was no continuous evaluation in production. "
                "A 24-hour delay in detection could mean real users received wrong answers. "
                "Missing: webhook delivery monitoring, index freshness alert."
            ),
            prevention_gap=(
                "Should have: (1) automatic webhook token renewal 7 days before expiry; "
                "(2) alert if webhook hasn't fired in >24 hours; "
                "(3) continuous production evaluation sampling requests; "
                "(4) index versioning in response headers so client can detect staleness."
            )
        ),

        # AI-Specific Factors
        ai_factors=AISpecificFactors(
            model_version="gemini-2.0-flash (same before and after)",
            prompt_version="v3.2 (same, retrieval prompt unchanged)",
            retrieval_index_version="v1.2 (stale) → v2.1 (correct)",
            embedding_model="text-embedding-004 (same model, different source docs)",
            evaluation_coverage_gap=(
                "Golden dataset was based on v1.2 API docs. When v2.1 was released, "
                "we didn't update the golden dataset to include new v2.1 API endpoints. "
                "This created a blind spot: queries about new v2.1 features would fail "
                "evaluation silently. Only existing features (that changed behavior between versions) "
                "were caught as failures."
            ),
            safety_check_status=(
                "No safety checks failed. The retrieved documents were valid and not harmful. "
                "The issue was semantic: documents were correct, just outdated. "
                "This shows safety checks ≠ correctness checks."
            ),
            affected_input_types=(
                "Queries about 'API documentation', 'how to use', 'what is new in v2.1' "
                "were most affected. Queries about core product features (not in docs) "
                "or very recent features (not in v1.2 or v2.1 yet) were unaffected."
            )
        ),

        # What went well
        what_went_well=[
            "Evaluation suite caught the regression (prevented customer-facing bug)",
            "Root cause identified quickly by checking index timestamp",
            "Re-indexing pipeline worked correctly once triggered manually",
            "No cascading failures; system stayed available while returning stale results",
            "Team communication was clear and incident was resolved in <3 hours",
        ],

        # Lessons learned
        what_we_learned=[
            "Webhook auth tokens need automatic renewal, not manual expiry handling",
            "Need continuous production evaluation, not just deployment-time checks",
            "Golden dataset must be updated whenever source data (docs) changes",
            "Index versioning/freshness must be observable to clients",
            "Stale data can pass safety checks but still fail correctness checks",
            "Evaluation coverage gaps can hide whole categories of failures",
        ],

        # Action items
        action_items=[
            ActionItem(
                title="Implement webhook auth token auto-renewal (renew at 60 days, TTL 90 days)",
                owner="George (API infra)",
                deadline=now + timedelta(days=7),
                category="automation",
                priority="high",
                status="open"
            ),
            ActionItem(
                title="Add webhook delivery monitoring and alert on failures",
                owner="Heidi (Observability)",
                deadline=now + timedelta(days=7),
                category="monitoring",
                priority="high",
                status="open"
            ),
            ActionItem(
                title="Implement continuous evaluation for production retrieval queries",
                owner="Frank (AI/ML)",
                deadline=now + timedelta(days=14),
                category="testing",
                priority="high",
                status="open"
            ),
            ActionItem(
                title="Update golden dataset whenever knowledge base version changes",
                owner="Iris (Data/Evaluation)",
                deadline=now + timedelta(days=3),
                category="testing",
                priority="high",
                status="open"
            ),
            ActionItem(
                title="Add index version/timestamp to retrieval response headers",
                owner="George (API infra)",
                deadline=now + timedelta(days=10),
                category="architecture",
                priority="medium",
                status="open"
            ),
            ActionItem(
                title="Document knowledge base update workflow in runbook",
                owner="Jack (Documentation)",
                deadline=now + timedelta(days=5),
                category="runbook",
                priority="high",
                status="open"
            ),
        ]
    )

    return incident


if __name__ == "__main__":
    from app.templates import generate_postmortem_markdown

    incident = create_example_ai_retrieval_incident()
    markdown = generate_postmortem_markdown(incident)

    print(markdown)
