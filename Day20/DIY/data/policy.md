# Error Budget Policy: answer-api

## Policy Version
- Date: 2026-09-21
- Owner: SRE Team
- Next Review: 2026-10-21
- Stakeholders: Product Manager, Engineering Lead, Security Owner

## SLO Definition (from Day 14 DIY)

### Availability Budget
- **SLI**: Good requests / Valid requests
  - Good events: `completed`, `insufficient_context`, `requires_human_review` (answered within 10s or explicit status)
  - Bad events: timeout (>10s), 5xx errors, unrecognized response contract
  - Exclusions: Marked load test traffic, maintenance windows
- **SLO Target**: 99.5% over rolling 28-day window
- **Monthly Error Budget**: 0.5% = 21,600 bad events per million requests
  - Assuming ~43,200 requests/day: ~9.7 bad events allowed per day on average

### Quality Budget (Semantic Failures)
- **SLI**: Grounded answers / Valid requests
  - Good events: Factually correct or honest refusal
  - Bad events: Hallucination, incorrect facts, unsubstantiated claims
  - Exclusions: Boundary cases under review by humans
- **SLO Target**: 99.0% (stricter than availability, shared context + model uncertainty)
- **Monthly Error Budget**: 1.0% = 43,200 bad events per million requests

### Safety Budget
- **SLI**: Safe responses / Valid requests
  - Good events: No safety violations, proper guardrails applied
  - Bad events: Blocked safety issue, unexpected tool invocation, jailbreak attempt, sensitive data leak
  - Exclusions: Testing with explicitly marked test credentials
- **SLO Target**: 99.9% (strictest; safety is non-negotiable)
- **Monthly Error Budget**: 0.1% = 4,320 bad events per million requests

## Burn Rate Definition

```
burn_rate = (actual_bad_event_rate / acceptable_bad_event_rate) for a time window

burn_rate > 1.0  ⟹  consuming faster than long-term allowance
burn_rate <= 1.0 ⟹  within sustainable pace
```

**Short window (1h)** detects acute spikes; **Long window (6h)** avoids single noise trigger.

### Burn Rate Thresholds

- Availability burn_rate > 36x (1-hour window): Critical alert, immediate incident response
- Availability burn_rate > 6x (6-hour window): Major incident, escalate to on-call lead
- Quality burn_rate > 10x (6-hour window): Stop model updates, pull for human review
- Safety burn_rate > 3x (1-hour window): Critical alert, immediate safety review

## Policy Actions by Budget Status

### Availability Budget

| Status | Threshold | Action | Owner | Timeline |
|--------|-----------|--------|-------|----------|
| Healthy | < 20% consumed | Continue normal rollouts | PM + Eng | Ongoing |
| Caution | 20-50% consumed | Reduce rollout velocity, monitor closely | Eng Lead | Next 24h |
| Warning | 50-80% consumed | Pause non-critical rollouts, focus on stability | Eng Lead + PM | Immediate |
| Critical | > 80% consumed | **Freeze all rollouts** except critical stability fixes | Director + Eng | Immediate |

### Quality Budget

| Status | Threshold | Action | Owner | Timeline |
|--------|-----------|--------|-------|----------|
| Healthy | < 30% consumed | Enable new prompt experiments | ML Eng | Ongoing |
| Caution | 30-60% consumed | Manual review before promotion | ML Eng + Review Board | 24h turnaround |
| Warning | 60-90% consumed | **Stop all new model/prompt promotions** | ML Lead | Immediate |
| Critical | > 90% consumed | Revert recent changes, investigate root cause | ML Lead + SRE | Immediate |

### Safety Budget

| Status | Threshold | Action | Owner | Timeline |
|--------|-----------|--------|-------|----------|
| Healthy | < 50% consumed | Normal operations | Sec Lead | Ongoing |
| Warning | 50-100% consumed | **Escalate to Chief Security Officer**, preserve all evidence | Sec Lead | Immediate |
| Critical (any incident) | Single safety block unexpectedly high | Lock guardrail parameters, human-only decisions | Chief Sec Eng | Immediate |

## Single-Event Rules

**Single event consuming > 20% monthly budget ⟹ Mandatory postmortem**:
  - Must include 1+ P0 improvements (permanent reliability/quality/safety changes)
  - Due within 5 business days
  - Reviewed by respective domain owner (Eng/ML/Security)

**Safety incidents (any) ⟹ Preserve evidence & escalate**:
  - No "averaging out" with other events
  - Risk score must be documented and approved before reverting guardrails

## Exceptions (Not Charged to Budget)

1. **Infrastructure Failures**
   - Company-wide network outages (confirmed by Ops)
   - Regional cloud provider downtime (AWS/GCP SLA events)
   - DNS/CDN provider failures

2. **Dependency Failures**
   - Third-party API outages (Gemini, embedding providers, etc.)
   - Database/Redis cluster failover (operational, not code-caused)

3. **Load Test Traffic**
   - Explicitly tagged `x-load-test: true` header
   - Separated by upstream LB or test runner config

4. **User-Initiated Cancellations**
   - Client sends `cancel` signal after request started
   - Counted as N/A in denominator

5. **Maintenance Windows**
   - Pre-announced, scheduled, < 2 hours/month
   - Excluded from SLO measurement window

## Definitions of Ownership

- **Product Manager** (PM): Quality & Feature risk, schedule, user impact
- **Engineering Lead (Eng)**: Architecture, availability, deployment gates
- **ML Engineer Lead**: Model/Prompt selection, evaluation policies
- **Security Lead (Sec)**: Safety guardrails, incident response, risk scoring
- **SRE (Reliability)**: Observability, postmortem facilitation, metrics infrastructure

## Measurement & Monitoring

- **Data Source**: Prometheus + custom event logger
  - Availability: HTTP/business logic status codes
  - Quality: Semantic checks (grounding, hallucination detection)
  - Safety: Guardrail blocks, sensitive field detection
- **Reporting Frequency**: Daily dashboard, weekly summary email
- **Burn Rate Dashboard**: Updated every 5 minutes (1h window), 30 minutes (6h window)
- **Budget Calculation**: Every Sunday 00:00 UTC for the rolling 28-day window

## Policy Changes & Review

- This policy is reviewed **quarterly** (next: 2026-12-21)
- Threshold adjustments require 2 domain leads + PM sign-off
- Budget splitting (e.g., per-feature or per-region) discussed in monthly SRE sync
- Exceptions are logged and reviewed for potential policy improvements

## Reference

- Day 14 DIY: SLI / SLO / SLA definitions
- Day 15: Availability measurement (numerator/denominator details)
- [Google SRE: Error Budget Policy](https://sre.google/workbook/error-budget-policy/)
- Netflix incident (2012-12-25): Exemplary use of budget to prioritize core reliability
