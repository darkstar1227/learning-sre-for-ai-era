# Postmortem: Database Latency Spike Causes API Connection Pool Exhaustion

**Incident ID:** INC-2026-001
**Severity:** SEV2
**Service:** api-service
**Date:** 2026-09-23T01:03:01.833772

## Detect Stage

**Alert Name:** API P99 latency > 5s
**Triggered At:** 2026-09-23T01:03:01.833772
**Threshold:** P99 latency < 2000ms
**Current Value:** P99 latency = 8500ms

## Triage Stage

**Incident Commander:** Alice (SRE on-call)
**Severity:** SEV2

**Affected Systems:**
- api-service
- postgresql

**Estimated Impact Scope:** ~85% of requests experiencing >5s latency. Approximately 2,000 active users affected. SLA risk: 10% error rate vs 0.1% threshold.

**Immediate Risk:** If cascading timeouts continue, connection pool will completely exhaust, leading to total API unavailability (SEV1 escalation).

## Mitigate Stage

### Action 1

**Action:** Checked database metrics: discovered CPU at 95%, lock contention on user_session table
**Executed At:** 2026-09-23T01:33:01.833772
**Expected Effect:** Identify root cause at database layer
**Actual Effect:** Successfully identified: ongoing VACUUM on user_session table blocking reads

### Action 2

**Action:** Killed long-running VACUUM job (PID 12345) using pg_terminate_backend()
**Executed At:** 2026-09-23T01:48:01.833772
**Expected Effect:** Database latency should drop immediately, API recovery follows
**Actual Effect:** Database latency dropped from 5000ms to 15ms within 30 seconds

### Action 3

**Action:** Verified API P99 latency returned to <500ms
**Executed At:** 2026-09-23T02:03:01.833772
**Expected Effect:** User experience normalized
**Actual Effect:** Confirmed: no requests timeout, error rate back to baseline 0.01%

## Recover Stage

**Recovery Completed At:** 2026-09-23T02:03:01.833772
**SLI Metric:** P99 latency (API)
**Baseline Value:** <500ms
**Recovery Value:** 245ms
**Verification Method:** Grafana Tempo: sampled 10 random traces from 14:45-14:50 UTC, all completed in <300ms. Prometheus: P99 latency stable at 245ms for >10min. Manual user testing: feature workflows complete normally.

## Root Cause Analysis

**Root Cause:**
PostgreSQL initiated an automatic VACUUM ANALYZE on the user_session table at 14:32 UTC due to autovacuum_naptime. This VACUUM acquired AccessExclusiveLock, blocking all read queries on the table. Since user session lookup is on the critical path of every request, the blocked queries filled the API connection pool (max 50 connections), causing all new requests to timeout or fail.

**Contributing Factors:**
- VACUUM was not scheduled; it ran automatically during peak traffic hours
- No monitoring alert for database lock contention existed
- API connection pool timeout was set to 30s (aggressive but reasonable)
- No circuit breaker between API and database

**Detection Gap:** Monitoring alerted on API P99 latency but not on database lock contention. Query performance metrics (avg query time) were available but not dashboarded. Database pg_stat_statements was not queried during triage (would have shown blocked queries immediately).

**Prevention Gap:** VACUUM should not run during peak hours (06:00-22:00 UTC). Need alert on pg_locks where waiters > 0. Should add circuit breaker pattern at API ↔ DB boundary. Connection pool exhaustion should trigger alert before user impact.

## What Went Well

- Alert fired within 15 seconds of the cascade starting
- On-call engineer found root cause in <10 minutes (killed VACUUM immediately)
- Database recovered instantly once VACUUM was killed
- No data loss, no customer data exposed
- Team communication was clear; timeline documented in real-time

## What We Learned

- Database automatic maintenance (VACUUM) should not run during peak hours
- Need to monitor database lock contention, not just query latency
- API connection pool exhaustion is a cascade point - needs separate alerting
- Circuit breaker pattern would have prevented user impact even if DB was slow
- pg_stat_statements is powerful for diagnosis but not integrated into dashboards

## Action Items

○ **[DATABASE]** Disable autovacuum during peak hours (06:00-22:00 UTC)
  - Owner: Bob (Database team)
  - Priority: high
  - Deadline: 2026-09-30

○ **[MONITORING]** Create alert for pg_locks with waiters > 0
  - Owner: Charlie (Monitoring/SRE)
  - Priority: high
  - Deadline: 2026-09-30

○ **[MONITORING]** Add database lock contention dashboard to Grafana
  - Owner: Charlie (Monitoring/SRE)
  - Priority: high
  - Deadline: 2026-10-07

○ **[ARCHITECTURE]** Implement circuit breaker for API ↔ Database calls
  - Owner: David (API team)
  - Priority: medium
  - Deadline: 2026-10-14

○ **[MONITORING]** Add connection pool exhaustion alert
  - Owner: Charlie (Monitoring/SRE)
  - Priority: high
  - Deadline: 2026-10-03

○ **[RUNBOOK]** Document emergency procedures for killing stuck VACUUM in runbook
  - Owner: Eve (Documentation)
  - Priority: high
  - Deadline: 2026-09-26
