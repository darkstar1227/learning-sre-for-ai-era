# Release Checklist for Policy-API

Based on Day 20 §⑩: Rollout gates & Day 20 §⑪ verification.

This checklist ensures error budget policy is actively used at deployment time, not just reviewed post-mortem.

## Pre-Release: Budget & Health Check

- [ ] **Availability budget review**
  - [ ] Current consumption: ___% (target: < 80% for rollout)
  - [ ] Burn rate (1h): ___x (target: < 6x for rollout)
  - [ ] Burn rate (6h): ___x (target: < 2x for rollout)
  - [ ] Last 24h trend: improving / stable / degrading
  - Dashboard link: ________________________________
  
- [ ] **Quality budget review**
  - [ ] Current consumption: ___% (target: < 80% for new model/prompt)
  - [ ] Recent hallucination rate: ___%
  - [ ] Evaluator version: ___________________
  - [ ] Coverage (% of traffic evaluated): ___%
  - Dashboard link: ________________________________

- [ ] **Safety status**
  - [ ] No critical incidents in last 30 days: Yes / No
  - [ ] Guardrail version & rules hash: ___________________
  - [ ] Any unresolved violations: Yes / No (if Yes, STOP release)

## Change Details

- [ ] **What is this release?**
  - Type: Bug fix / Feature / Model change / Prompt change / Infrastructure update
  - Affected components: ________________
  - Reason for change: ________________________________

- [ ] **Golden Dataset results (for model/prompt changes)**
  - [ ] Dataset used: _________________
  - [ ] Evaluator used: _________________ (include version)
  - [ ] Comparison baseline: _________________ (previous prompt/model)
  - [ ] Results attached: Yes / No
    - If yes, file/link: ________________________________
    - Factual accuracy improvement: ___% → ___% ✓ (or explain regression)
    - Latency impact: no change / + ___ms / - ___ms

- [ ] **Known quality regressions or concerns**
  - [ ] Describe: ________________________________
  - [ ] Risk assessment: Low / Medium / High
  - [ ] Mitigation: ________________________________

- [ ] **Safety & tool changes**
  - [ ] Any new tool invocations? Yes / No (if Yes: security review required)
  - [ ] Any guardrail parameter changes? Yes / No (if Yes: safety lead sign-off required)
  - [ ] Any permission or scope escalations? Yes / No (if Yes: security review)

## Release Strategy

- [ ] **Deployment style**
  - Strategy: All-at-once / Canary (%) / Blue-green
  - Canary percentage: __% (if applicable)
  - Observation window: __ minutes (before rollout to 100%)

- [ ] **Monitoring & automated rollback**
  - [ ] Automated rollback trigger: burn_rate > __ for __ minutes
  - [ ] Manual rollback trigger: _________________ (e.g., error rate spike)
  - [ ] Rollback owner: _________________
  - [ ] Rollback target version: _________________

- [ ] **Communication**
  - [ ] Affected teams notified: Yes / No
  - [ ] On-call team briefed: Yes / No
  - [ ] #announcements post: Yes / No
  - [ ] Runbook updated: Yes / No

## Sign-Off (Must match deployment authority)

### Green Status (All budgets healthy, low risk)

- [ ] Product Manager approval: _________________ (Date: _____)
- [ ] Engineering Lead approval: _________________ (Date: _____)
- [ ] SRE/Reliability owner approval: _________________ (Date: _____)

**Release authorized to proceed as planned.**

---

### Yellow Status (One budget caution/warning, medium risk)

- [ ] Budget owner (SRE/ML/Security) acknowledges: _________________ (Date: _____)
- [ ] Engineering Lead approval with mitigation plan: _________________ (Date: _____)
- [ ] Product Manager approval with risk acceptance: _________________ (Date: _____)

**Release authorized with following restrictions:**
- [ ] Canary only (not full rollout)
- [ ] Reduced rollout percentage: __% instead of 100%
- [ ] Increased monitoring: check burn rate every __ minutes
- [ ] Explicit rollback condition: _________________ 

**Owner responsible for monitoring:** _________________

---

### Red Status (Critical burn, quality regression, or safety incident)

**Release BLOCKED.**

- [ ] Reason: ________________________________
- [ ] Remediation required: ________________________________
- [ ] Expected fix date: _________________
- [ ] Retry checklist after fix: reschedule pre-release review above

---

## Post-Release Validation (After canary or full rollout)

- [ ] **Monitor burn rate for __ minutes (at least 2-3x normal observation window)**
  - [ ] Availability burn rate stable: Yes / No
  - [ ] Quality metrics stable: Yes / No
  - [ ] No new safety incidents: Yes / No
  - [ ] Error traces reviewed and understood: Yes / No

- [ ] **Decision: Continue or rollback?**
  - [ ] All green → Proceed to full rollout / mark complete
  - [ ] Concerning signal but not critical → Extend observation __ more minutes
  - [ ] Clear issue detected → Initiate rollback immediately

## Release Retrospective (24 hours post-release)

- [ ] **Was the release successful?**
  - Success criteria met: Yes / No
  - Any production issues: Yes / No (if Yes: detail below)
  - ________________________________

- [ ] **Budget impact assessment**
  - Availability: ___% consumed (delta from pre-release: +___ %)
  - Quality: ___% consumed (delta from pre-release: +___ %)
  - Safety: No incidents ✓

- [ ] **What did we learn?**
  - [ ] Anything surprising in metrics/traces?
  - [ ] Any monitoring blind spots discovered?
  - [ ] Changes to next release strategy?

---

## Example Scenarios

### Scenario A: Low-risk bug fix
✓ Availability 10% consumed, Quality 25% consumed, no recent incidents
→ GREEN: Approve, full rollout

### Scenario B: New prompt version
⚠️ Availability 15% consumed, Quality 65% consumed (high but acceptable)
→ YELLOW: Canary 10% only, must review golden dataset results, 60-min observation window

### Scenario C: Post-spike rollout attempt
🚨 Availability 85% consumed (was 50% yesterday)
→ RED: BLOCKED. Wait for burn rate to normalize before trying new release.

### Scenario D: Quality regression found
🚨 Hallucination rate 8.5% (baseline 2%)
→ RED: BLOCKED. Rollback candidate or investigate root cause before retry.

### Scenario E: Safety guardrail parameter change
🚨 Security review pending
→ RED (conditional): Cannot release until security lead signs off.

---

## How This Connects to Day 20 Policy

| Step | Checklist Section | Policy Reference |
|------|------------------|------------------|
| A | Pre-Release | Day 20 §⑩ rollout gate requirement |
| B | Change Details | Day 20 §⑦ SLI as measurable fact, not assumption |
| C | Release Strategy | Day 20 §⑩ automation + manual override |
| D | Sign-Off | Day 20 §⑫ ownership clarity |
| E | Post-Release | Day 20 §⑩ decision based on budget, not debate |
| F | Retrospective | Day 20 §⑫ exception logging for policy review |

This is not a bureaucratic gate. It's a tool to capture decisions and make them repeatable, reducing both risk and decision fatigue.
