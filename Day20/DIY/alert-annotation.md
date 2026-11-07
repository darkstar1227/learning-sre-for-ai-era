# Alert Annotation Template

Based on Day 20 §⑪ Step D: Write a clear alert message.

## Availability Budget Burning Quickly

### Alert Name
`policy-api-availability-burn-rate-high`

### Summary
policy-api availability budget is burning faster than sustainable rate.

### Alert Body

```
🚨 POLICY-API AVAILABILITY ALERT

SLO Target: 99.5% over 28-day rolling window
Acceptable error rate: 0.5%

Observed (Last 1 hour):
  - Burn rate: 12.4x (means consuming budget 12.4x faster than allowed)
  - Error ratio: 6.2% actual bad rate
  - Request volume: 1,860 requests
  - Bad events: 115

Observed (Last 6 hours):
  - Burn rate: 5.1x
  - Error ratio: 2.55% actual bad rate
  - Request volume: 18,500 requests
  - Bad events: 471

Budget Status:
  - Consumed this month: 65%
  - Remaining: 35% (~2,750 bad events)
  - At current rate: budget exhausted in ~3 days

Likely Root Causes (not necessarily in this order):
  [ ] Recent deployment (compare deployment timeline)
  [ ] Dependency issue (check Gemini API status, Redis, database)
  [ ] Database performance degradation
  [ ] Cache invalidation or unusual traffic pattern

Immediate Actions (in order):
1. Check deployment history: was something released in the last hour?
2. Inspect error traces in Day2 DIY Loki/Tempo (if available)
3. Verify dependency health:
   - Gemini API status page
   - Database connection pool
   - Redis availability
4. Check request patterns in Prometheus (request rate, error rate by endpoint)
5. If clear root cause found, decide rollback vs. remediation

Escalation:
  - If burn rate remains > 6x for next 30 minutes: page on-call lead
  - If burn rate > 36x for 1 hour: treat as critical incident, all hands on deck

Runbook: https://your-runbook-url/policy-api-availability-burn

Slack Channel: #sre-incidents
Dashboard: https://grafana-url/d/policy-api-burn-rate
```

---

## Quality Budget Regression Detected

### Alert Name
`policy-api-quality-regression`

### Summary
Quality score or evaluation results show significant regression. Model/prompt changes may have introduced hallucinations or grounding failures.

### Alert Body

```
⚠️ POLICY-API QUALITY ALERT

SLO Target: 99.0% (Quality is separate from availability)
Acceptable quality failure rate: 1.0%

Observed (Last 6 hours):
  - Quality failures: 125 (in sampled evaluation set)
  - Evaluation coverage: 800 responses evaluated
  - Failure ratio: 15.6% (far above 1.0% target)
  - Burn rate: 15.6x

Failure Types (from evaluator):
  - Hallucinations: 78 (62% of failures)
  - Unsupported claims: 35 (28%)
  - Citation mismatches: 12 (10%)

Recent Changes (compare timeline):
  [ ] Model version change (prompt-v12, model-v3)?
  [ ] Retrieval index update?
  [ ] Temperature or system prompt adjustment?
  [ ] Evaluation criteria change?

Immediate Actions:
1. Identify which change triggered the regression (deployment correlation)
2. If found: Rollback or feature-flag the change
3. Pull failing examples for root cause analysis
4. If unclear: Compare current evaluator output against historical baseline
5. Convene ML + Product review to assess severity

Escalation:
  - Pause promotion of affected model/prompt version
  - Do NOT disable other features based on quality issues
  - Separate quality issues from availability incidents

Action Owner: ML Eng Lead
Timeline: Within 2 hours for preliminary assessment

Runbook: https://your-runbook-url/quality-regression
Dashboard: https://grafana-url/d/policy-api-quality-trends
```

---

## Safety Policy Violation Detected

### Alert Name
`policy-api-safety-incident`

### Summary
Safety policy violation detected. Guardrail may have failed or PII may be at risk. Requires immediate investigation and escalation.

### Alert Body

```
🚨 POLICY-API SAFETY INCIDENT

Severity: CRITICAL (no averaging, immediate action required)

Incident Details:
  - Time: 2026-09-21 14:32:15 UTC
  - Violation Type: [Guardrail bypass | PII exposure | Unauthorized tool | Jailbreak]
  - Request ID: req-abc123def456
  - Trace ID: trace-xyz789

Affected Surface:
  - User ID: (if tracked)
  - Session: (if applicable)
  - Endpoint: /api/ask
  - Flow: (describe the request flow)

Evidence to Preserve:
  - [ ] Full request body (redact after capturing)
  - [ ] Full response body
  - [ ] Guardrail state (rules, version)
  - [ ] LLM model version and system prompt
  - [ ] Any tool invocations or policy engine decisions

Immediate Actions (do not skip):
1. STOP: Do not continue deployment or rollout
2. PRESERVE: Lock guardrail parameters until root cause is fixed
3. ESCALATE: Notify Chief Security Officer now
4. ANALYZE: Determine if other requests were affected
5. AUDIT: Check logs for similar patterns in past 7 days

Escalation:
  - Notify: Security Lead, Chief Security Officer, Privacy Officer
  - Level: P0 incident (highest)
  - Timeline: Postmortem required within 24 hours

Do NOT:
  - Treat this as a regular quality issue
  - Wait for batch review
  - Use "SLO consumption %" to dismiss it
  - Rely on averaging with other successful requests

Runbook: https://your-runbook-url/security-incident
Incident Channel: #sre-security
On-Call: Page security lead immediately
```

---

## Template Variables for Production Use

Replace placeholders with your actual infrastructure:

```
Dashboard URL: https://your-grafana-domain/d/policy-api-burn-rate
Runbook URL: https://your-internal-wiki/policy-api-runbook
Slack Channel: #sre-incidents (or team-specific channel)
PagerDuty Service: policy-api-availability
On-Call Group: sre-team (or specific rotation)
Review Board: ML + Product stakeholders (for quality)
Security Lead: [Name/Team]
Chief Security Officer: [Name]
```

---

## How to Use This Template

1. **Pre-Production**: Customize URLs, team names, and escalation contacts
2. **Alert Configuration**: Paste into your AlertManager/PagerDuty annotation fields
3. **Testing**: Simulate alert and verify team receives message and can follow steps
4. **Refinement**: After first real alert, collect feedback and improve wording
5. **Automation**: Eventually, auto-populate some fields (burn_rate, request_volume) from observability queries

This template ensures:
- Alert recipients know SLO context (not just "error rate high")
- Initial troubleshooting steps are clear (no guess work)
- Escalation triggers and owners are pre-determined (no debate during incident)
- Sensitive handling for safety incidents (never averaged away)
