# Postmortem: RAG Retrieval Returning Stale Knowledge Base (v1.2 vs v2.1)

**Incident ID:** INC-2026-005
**Severity:** SEV2
**Service:** ai-retrieval-service
**Date:** 2026-09-23T00:03:01.834793

## Detect Stage

**Alert Name:** Manual user report + Evaluation system catch
**Triggered At:** 2026-09-22T23:48:01.834793
**Threshold:** Retrieval accuracy (golden dataset) should be >95%
**Current Value:** Accuracy dropped to 76% for 'API docs' queries

## Triage Stage

**Incident Commander:** Frank (AI/ML on-call)
**Severity:** SEV2

**Affected Systems:**
- retrieval-service
- knowledge-base-index

**Estimated Impact Scope:** ~40% of queries use retrieval feature. Estimated 500 users saw incorrect/outdated information. No SLA breach (users didn't timeout), but accuracy was severely degraded. Risk of reputational damage if pattern continues.

**Immediate Risk:** Users receiving wrong information (though not catastrophic). If evaluation system hadn't caught this, stale index could have persisted for days.

## Mitigate Stage

### Action 1

**Action:** Checked embedding index timestamp: last updated 2026-09-19 13:00 UTC. Documentation published 2026-09-20 08:00 UTC.
**Executed At:** 2026-09-23T00:18:01.834793
**Expected Effect:** Identify that index is stale
**Actual Effect:** Confirmed: index was 23 hours behind latest docs

### Action 2

**Action:** Triggered immediate re-indexing of knowledge base against v2.1 docs (using app/reindex_knowledge.py --force)
**Executed At:** 2026-09-23T00:33:01.834793
**Expected Effect:** New embeddings generated and pushed to retrieval service within 5 minutes
**Actual Effect:** Reindexing completed in 4m 32s. New index deployed without service restart.

### Action 3

**Action:** Ran evaluation suite against new index (500 golden queries)
**Executed At:** 2026-09-23T00:53:01.834793
**Expected Effect:** Accuracy should return to >95%
**Actual Effect:** Accuracy returned to 96.8%. All previously-failing queries now pass.

## Recover Stage

**Recovery Completed At:** 2026-09-23T01:03:01.834793
**SLI Metric:** Retrieval accuracy (golden dataset)
**Baseline Value:** >95%
**Recovery Value:** 96.8%
**Verification Method:** Ran full evaluation suite (500 golden queries) against new index. Spot-checked 20 user queries in staging environment. Confirmed Tempo traces showing retrieval returning v2.1 docs. No performance regression (latency still <200ms).

## Root Cause Analysis

**Root Cause:**
Knowledge base documentation was updated to v2.1 on 2026-09-20 08:00 UTC, but the trigger for automatic re-indexing (webhook from docs repository) was not firing. The embedding index pipeline continued using stale v1.2 docs. Root cause: webhook auth token expired on 2026-09-18, and no monitoring alerted on failed webhook deliveries.

**Contributing Factors:**
- Webhook auth token was set to 90-day TTL with no renewal reminder
- No monitoring on webhook delivery success rate
- Evaluation system only runs on deployment, not continuously
- Knowledge base update process doesn't explicitly verify index freshness

**Detection Gap:** Evaluation system caught the issue (good!), but only because we ran it after deployment. There was no continuous evaluation in production. A 24-hour delay in detection could mean real users received wrong answers. Missing: webhook delivery monitoring, index freshness alert.

**Prevention Gap:** Should have: (1) automatic webhook token renewal 7 days before expiry; (2) alert if webhook hasn't fired in >24 hours; (3) continuous production evaluation sampling requests; (4) index versioning in response headers so client can detect staleness.

## AI-Specific Factors

**Model Version:** gemini-2.0-flash (same before and after)
**Prompt Version:** v3.2 (same, retrieval prompt unchanged)
**Retrieval Index Version:** v1.2 (stale) → v2.1 (correct)
**Embedding Model:** text-embedding-004 (same model, different source docs)

**Evaluation Coverage Gap:** Golden dataset was based on v1.2 API docs. When v2.1 was released, we didn't update the golden dataset to include new v2.1 API endpoints. This created a blind spot: queries about new v2.1 features would fail evaluation silently. Only existing features (that changed behavior between versions) were caught as failures.

**Safety Check Status:** No safety checks failed. The retrieved documents were valid and not harmful. The issue was semantic: documents were correct, just outdated. This shows safety checks ≠ correctness checks.

**Affected Input Types:** Queries about 'API documentation', 'how to use', 'what is new in v2.1' were most affected. Queries about core product features (not in docs) or very recent features (not in v1.2 or v2.1 yet) were unaffected.

## What Went Well

- Evaluation suite caught the regression (prevented customer-facing bug)
- Root cause identified quickly by checking index timestamp
- Re-indexing pipeline worked correctly once triggered manually
- No cascading failures; system stayed available while returning stale results
- Team communication was clear and incident was resolved in <3 hours

## What We Learned

- Webhook auth tokens need automatic renewal, not manual expiry handling
- Need continuous production evaluation, not just deployment-time checks
- Golden dataset must be updated whenever source data (docs) changes
- Index versioning/freshness must be observable to clients
- Stale data can pass safety checks but still fail correctness checks
- Evaluation coverage gaps can hide whole categories of failures

## Action Items

○ **[AUTOMATION]** Implement webhook auth token auto-renewal (renew at 60 days, TTL 90 days)
  - Owner: George (API infra)
  - Priority: high
  - Deadline: 2026-09-30

○ **[MONITORING]** Add webhook delivery monitoring and alert on failures
  - Owner: Heidi (Observability)
  - Priority: high
  - Deadline: 2026-09-30

○ **[TESTING]** Implement continuous evaluation for production retrieval queries
  - Owner: Frank (AI/ML)
  - Priority: high
  - Deadline: 2026-10-07

○ **[TESTING]** Update golden dataset whenever knowledge base version changes
  - Owner: Iris (Data/Evaluation)
  - Priority: high
  - Deadline: 2026-09-26

○ **[ARCHITECTURE]** Add index version/timestamp to retrieval response headers
  - Owner: George (API infra)
  - Priority: medium
  - Deadline: 2026-10-03

○ **[RUNBOOK]** Document knowledge base update workflow in runbook
  - Owner: Jack (Documentation)
  - Priority: high
  - Deadline: 2026-09-28
