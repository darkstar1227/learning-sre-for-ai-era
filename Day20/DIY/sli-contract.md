# SLI Contract for Policy-API

Based on Day 14 DIY and Day 20 requirements.

## SLI Name: policy-api availability

### Good Event
- HTTP 2xx response that is parseable and completes within 2 seconds
- Includes: legitimate "insufficient_context" or "requires_human_review" responses (explicit status)
- Response body is valid JSON conforming to schema

### Bad Event
- HTTP 5xx (server error)
- Timeout (request takes > 2 seconds to complete or client cancels)
- Unparseable response (invalid JSON, response doesn't match schema)
- Other HTTP error codes indicating service fault (not client fault)

### Exclusions
- Synthetic/health check traffic (explicitly tagged `x-synthetic: true`)
- Requests from load test runners (tagged `x-load-test: true` header)
- Scheduled maintenance windows (pre-announced, max 2 hours/month)
- Traffic from regions where upstream dependency (Gemini API, etc.) is confirmed unavailable by provider SLA

### Measurement Window
- Rolling 28 days
- Denominator: all valid requests to `/api/ask` and related endpoints
- Numerator: requests that are NOT bad events (i.e., good responses)

### Owner
- Primary: SRE Team (answer-api on-call)
- Secondary: Engineering Lead (service architecture changes)

### Known Gaps
- **This SLI does not measure**:
  - Factual correctness of answers (see Quality SLI)
  - Safety compliance or guardrail violations (see Safety SLI)
  - User satisfaction or task completion rate
  - Latency beyond the 2-second threshold (separate SLI recommended)

---

## SLI Name: policy-api quality

### Good Event
- Response is factually grounded in provided context
- If refusal, the refusal is honest and traceable to a policy rule
- Claims can be verified against retrieval results or knowledge base
- No hallucination: no invented facts, citations, or tool invocations

### Bad Event
- Hallucination: answer includes facts not in context (unless appropriately noted as general knowledge)
- Incorrect citation: references a source that doesn't support the claim
- Unsupported claim: appears to make up information
- Misattribution: confuses which tool or source provided information

### Exclusions
- Boundary cases currently under human review
- Responses explicitly marked as "exploratory" (low-confidence disclaimers allowed)
- Answers to questions outside the training knowledge that the system appropriately declines

### Measurement Window
- Rolling 28 days
- Denominator: requests with valid responses to evaluate (may not be 100% of traffic; some require human spot-check)
- Numerator: responses that pass quality criteria

### Coverage Note
This SLI relies on evaluation:
- Automated rules (grounding checks, source verification)
- LLM-as-judge evaluator (may vary by version)
- Human spot-check samples (expensive, partial)

Coverage and evaluator version MUST be tracked alongside the score.

### Owner
- Primary: ML Eng Lead + Data Scientist
- Secondary: Product Manager (defines acceptance criteria)
- Tertiary: SRE (ensures measurement pipeline is accurate)

### Known Gaps
- Coverage is incomplete (humans can't check every response)
- Evaluator prompt/model version affects results
- Ground truth is sometimes ambiguous (human disagreement)
- Does NOT directly measure user satisfaction or task success

---

## SLI Name: policy-api safety

### Good Event
- Request handled without safety policy violations
- No guardrail blocks triggered for legitimate requests
- No sensitive data (PII, API keys, passwords) leaked in response
- Tool invocations (if enabled) respect authorization rules

### Bad Event
- Guardrail block triggered (policy engine intercepted unsafe request)
- Response leaked sensitive information (PII, credentials)
- Tool action attempted without proper authorization
- Jailbreak attempt detected (by heuristic or manual flag)

### Exclusions
- Requests explicitly from test environments (tagged `x-test-env: true`)
- Guardrail blocks during authorized red-team testing (pre-announced)
- Unintended data exposure already caught and remediated (log-only, no customer impact)

### Measurement Window
- Rolling 28 days
- Denominator: all requests to the system
- Numerator: requests that did NOT violate safety policy

### Owner
- Primary: Security Lead
- Secondary: Chief Security Officer (escalation for incidents)
- Tertiary: Privacy Officer (if sensitive data types involved)

### Incident Protocol
- Any safety violation → preserve logs, request_id, trace_id, timestamp
- Escalate immediately (not delayed to monthly review)
- Do NOT average safety issues with other budgets
- Do NOT use "SLO consumption %" logic for safety events

### Known Gaps
- Heuristic guardrails may miss novel jailbreaks
- Hard to measure "attempted but blocked" in all cases
- Privacy violations may only be discovered in audit, not in real-time

---

## How This Contract Will Be Verified

**Step A (Article)**: This contract is written such that another team member can read it and understand what is good vs. bad.

**Step B (DIY Script)**: `calculate_budget.py` demonstrates how these SLIs map to bad-event rates and burn rates.

**Step C (Day 21+)**: Once observability pipeline is built, queries will be written to measure each SLI in Prometheus/Loki/Tempo.

**Today (Day 20)**: We have the contract. Measurement infrastructure is Day 21.
