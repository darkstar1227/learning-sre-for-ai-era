# Incident Simulation & Decision Log

Based on Day 20 §⑪ Step E: Practice three decisions without touching production.

This document simulates real incidents and walks through the decision process using error budget policy.

---

## Scenario 1: Brief 5xx Spike (Transient Issue)

### Observation

```
Time: 2026-09-22 15:30:00 UTC
Alert: policy-api-availability-burn-rate-high

Metrics (collected by monitoring):
  1-hour window:
    - Total requests: 3,000
    - Bad events (5xx): 180
    - Burn rate: (180/3000=6%) / (0.5%=0.005) = 1.2x
    - Status: CAUTION (not yet WARNING)
  
  6-hour window:
    - Total requests: 18,000
    - Bad events: 120
    - Burn rate: (120/18000=0.67%) / 0.005 = 1.34x
    - Status: HEALTHY (within normal)

Current consumption (28-day rolling):
  - 60% of monthly budget consumed
  - Trending: stable

Recent changes:
  - Deployment 2 hours ago (unrelated service)
  - No recent Gemini API changes announced
```

### Decision Process

**Question 1: Short vs. Long window disagreement. What does it mean?**

> Short window is elevated but long window is normal. This typically indicates a brief spike that's already passing.

**Question 2: Should we page on-call?**

> No. Policy says:
> - Page threshold for availability: 1h > 36x or 6h > 6x
> - Current: 1h = 1.2x, 6h = 1.34x (both far below threshold)

**Question 3: Should we rollback the deployment?**

> No. Deployment was 2 hours ago, spike is 30 minutes old. Timing mismatch suggests unrelated. Monitor the next 30 minutes. If spike continues and timing aligns, reconsider rollback.

**Question 4: What's the first action?**

> 1. Check error traces in Tempo (which endpoint is 5xx'ing?)
> 2. Check dependency status (Gemini API, database)
> 3. If trending back down in next 15 min, close ticket with "transient spike resolved"

### Decision & Outcome

**Decision**: Observe, do not page. Set escalation trigger: if burn rate stays above 6x for 6h, then page.

**Owner**: On-call engineer (doesn't need to wake anyone else yet)

**Outcome (Simulated)**: 
- 16:00 UTC: burn rate drops to 0.8x (1h) and 0.9x (6h)
- Root cause: brief Redis connection pool exhaustion (normal during high load, recovered)
- Action: No code change needed. Ticket closed as "infrastructure resilience validated."
- Policy implication: No. Exceptions (infrastructure hiccup) don't count against budget.

---

## Scenario 2: Persistent Dependency Timeout (Action Required)

### Observation

```
Time: 2026-09-22 18:15:00 UTC
Alert: policy-api-availability-burn-rate-high (critical)

Metrics:
  1-hour window (most recent):
    - Total requests: 2,900
    - Bad events (Gemini timeouts): 1,740 (60% of requests!)
    - Burn rate: 0.60 / 0.005 = 120x
    - Status: CRITICAL

  6-hour window:
    - Total requests: 17,200
    - Bad events: 5,500
    - Burn rate: 0.32 / 0.005 = 64x
    - Status: CRITICAL

Current consumption (28-day rolling):
  - Was 60%, now 75% (15% burned in last few hours)

Duration:
  - Issue started ~90 minutes ago
  - Continuing to worsen
```

### Decision Process

**Question 1: Is this a page-worthy incident?**

> YES. Both 1h and 6h burn rates are CRITICAL (1h=120x > 36x threshold, 6h=64x > 6x threshold).

**Question 2: Page to whom?**

> 1. SRE on-call engineer (now)
> 2. SRE Lead / Eng Lead (within 5 minutes)
> 3. If root cause is external (Gemini API down), escalate to Gemini account team

**Question 3: What's the root cause?**

> Check traces and error pattern:
> - All errors are Gemini API timeouts (error type consistent)
> - Gemini API status page: check for announced issues
> - Your Gemini API quota/rate limits: still within bounds?
> - Network path to Gemini: any known issues?

**Question 4: What actions can we take immediately?**

> Option A (if Gemini is confirmed down for all users):
> - This is a dependency failure (exception)
> - Cannot improve our code if provider is down
> - Action: Update status page, notify users, wait for provider recovery
> 
> Option B (if it's affecting only us):
> - May be our circuit breaker triggering (too many retries)
> - Action: Check retry logic, disable aggressive retries, add fallback
>
> Option C (if Gemini is intermittent):
> - Add exponential backoff, increase timeout slightly, implement caching
> - Action: Deploy canary fix, monitor burn rate in next 30 min

**Question 5: Should we freeze deployments?**

> Policy says: burn rate > 80% consumed OR multiple window thresholds hit = FREEZE.
> Current: 75% consumed, but 6-hour burn rate is critical.
> → YES, FREEZE all non-critical deployments until resolved.

### Decision & Outcome

**Decision**: PAGE SRE on-call. Investigate dependency (Gemini). If confirmed external, set exception and escalate. If our code issue, deploy targeted fix and monitor recovery.

**Owner**: SRE on-call, with Eng Lead for code changes

**Action Items**:
1. [ ] Confirm Gemini API status (check status page + direct test call with test key)
2. [ ] If external: Exception applied, notify stakeholders, ETA from provider?
3. [ ] If internal: Deploy circuit breaker tuning / retry logic fix, re-enable in canary
4. [ ] Every 15 min: report burn rate trend to stakeholders
5. [ ] When burn rate drops to < 6x (6h window): consider releasing freeze
6. [ ] Postmortem within 24 hours (burn rate > 20% consumed in a single event)

**Outcome (Simulated)**:
- 19:00 UTC: Gemini API status page shows "degraded service in us-central1"
- 19:15 UTC: Applied exception (dependency failure), not charged to budget
- 19:45 UTC: Gemini recovered, burn rate drops to 0.8x within 15 min
- 20:00 UTC: Deployment freeze lifted, all systems green
- Postmortem: No code change needed, exception documented

---

## Scenario 3: Quality Regression Without Availability Change (Process Required)

### Observation

```
Time: 2026-09-23 09:00:00 UTC
Alert: policy-api-quality-regression

Discovery method:
  - Morning QA check: recent responses in audit log show more hallucinations
  - Correlation check: HTTP status codes all 200, no availability issues
  - Timeline match: Spike in errors matches "prompt-v12 promotion" last night

Metrics:
  Quality SLI (rolling 28-day):
    - Good responses (grounded): 198,000 / 200,000
    - Bad responses (hallucinations): 2,000
    - Error rate: 1.0% (at SLO target, not above)
    - BUT: Last 12 hours shows 2.5% error rate

  Availability SLI (same window):
    - Good responses (HTTP 2xx): 199,800 / 200,000
    - Bad responses (5xx/timeout): 200
    - Error rate: 0.1% (WELL below 0.5% SLO)
    - Status: HEALTHY (no alert)

Last night's change:
  - Promoted prompt-v12 to 50% traffic (was prompt-v11)
  - Offline evaluation: showed improvement in some areas
  - No regression noted before release
```

### Decision Process

**Question 1: Why no availability alert, but quality is poor?**

> This is exactly why we SEPARATE budgets.
> - Availability: "Did we respond?" → Mostly yes (200 errors in 200k)
> - Quality: "Was the response correct?" → Increasingly no (2k errors)
> - If we mixed them, 200 availability errors might obscure 2,000 quality issues.

**Question 2: Who owns this decision?**

> Not SRE. This is ML + Product.
> - SRE detects and alerts.
> - ML Eng + Product Manager decides next step.

**Question 3: What are the options?**

> Option A: Rollback prompt-v12 to prompt-v11 immediately.
> - Pro: Quick resolution, users see quality improve.
> - Con: You don't get to learn why v12 failed.
>
> Option B: Roll back canary (drop from 50% to 10%) and investigate.
> - Pro: Limit damage, collect data on v12's failure mode.
> - Con: Some users still see poor quality.
>
> Option C: Freeze v12, keep v11, but add extra evaluation to understand why.
> - Pro: Thorough root cause analysis.
> - Con: Delayed for users already on v12 (still 50% of traffic).

**Question 4: What does the policy say about this?**

> From `data/policy.md` Quality section:
> - Quality budget is 99.0% (stricter than availability's 99.5%)
> - Consumption > 80% = CRITICAL = **Stop all new model/prompt promotions**
> - Consumption 60-90% = WARNING = **Stop promotion, pull for review**
>
> Current: 1% error rate measured, but trend is 2.5% in last 12h.
> If 2.5% continues and extrapolated over 28 days: very close to "critical".

### Decision & Outcome

**Decision**: Immediate rollback to prompt-v11 (50% → 0%), preserve prompt-v12 trace data for analysis.

**Owner**: ML Eng Lead + Product Manager (joint decision)

**Action Items**:
1. [ ] Rollback execution: prompt-v12 traffic to 0% (takes 5 min to propagate)
2. [ ] Preserve: All traces, evaluations, requests where v12 was used (for post-mortem)
3. [ ] Notify: Users via status page ("quality improvement deployed")
4. [ ] Analysis: Within 4 hours, present findings on why v12 failed offline but failed online
5. [ ] Re-attempt: After fix, re-run offline eval + smaller canary before full rollout

**Question 5: Do we postmortem this?**

> Policy says: > 20% single event = mandatory postmortem.
> This regression didn't consume 20% of budget (it's 1%, well below 20%).
> BUT: It's a clear learning opportunity.
> → Lightweight postmortem (30 min, not full incident post-mortem): "Why did offline eval miss this?"

**Outcome (Simulated)**:
- 09:30 UTC: prompt-v12 rolled back to 0%
- 09:35 UTC: Quality rate improves to 0.7% error (back to baseline)
- 10:00 UTC: Lightweight review held. Finding: evaluator was using 50 samples, but production has different prompt structures. Offline eval needs larger, more representative dataset.
- Next step: v12 re-evaluated with expanded dataset, retry with 10% canary (not 50%)

---

## Summary of Decision-Making

| Scenario | Trigger | Metric Signal | Decision | Owner | Timeline |
|----------|---------|---------------|----------|-------|----------|
| Scenario 1 (Spike) | Burn rate 1.2x | 1h high, 6h normal | Observe, don't page | On-call eng | 30 min |
| Scenario 2 (Dependency) | Burn rate 120x | Both 1h and 6h critical | PAGE, investigate, freeze | SRE on-call + Lead | Immediate |
| Scenario 3 (Quality) | Trend 2.5% err | Availability OK, quality high | Rollback v12, analyze | ML Lead + PM | 30 min |

## Key Principles Practiced Here

1. **Separate budgets → separate decisions**: Availability issue ≠ Quality issue (even if both bad, handled differently)
2. **Windows matter**: 1h vs 6h tells you if it's temporary or persistent
3. **Thresholds are pre-decided**: No debate during incident. Policy says "do this when burn rate is X"
4. **Ownership is clear**: SRE handles availability, ML handles quality, both coordinate on rollback
5. **Exceptions are documented**: Dependency failure = exception = not charged to budget
6. **Postmortem is proportional**: Small issues don't need full incident review, but they do need some reflection

---

## How to Practice This

1. **Run through each scenario** with your team (SRE + ML + Product)
2. **Ask the questions** in "Decision Process" section
3. **Decide together** based on policy (not "who talks louder")
4. **Simulate the action** (dry run the rollback command, confirm it works)
5. **Record the decision** in this doc so next time it's faster

Once this feels natural, your actual incident response will be much calmer.
