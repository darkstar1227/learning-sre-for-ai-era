# Day10 Fault-Error-Failure Analysis

Based on Day9's service boundary for the Grounded Q&A `/ask` service (corporate travel policy retrieval).

## Selected User Failure

**Scenario**: Employee submits a travel policy question via the `/ask` endpoint and receives no response or an unclear "try again later" message within 30 seconds.

This is observable through:
- HTTP response status >= 500 or timeout
- User metrics showing request completion rate < expected SLO
- Support tickets indicating "couldn't get answer when I needed it"

---

## Fault → Error → Failure Chain Analysis

### Layer 1: FAILURE (What the user experiences)

| Aspect | Description |
|--------|-------------|
| **User Observable** | Employee cannot retrieve travel policy answer within SLO window (e.g., 30 seconds) |
| **Impact** | Employee makes decision without policy guidance, increasing compliance risk |
| **Boundary** | Response never received, or response marked as "temporarily unavailable" |
| **Evidence to Look For** | HTTP 5xx, timeout, explicit "retry later" message in user-facing response |

### Layer 2: ERROR (System enters incorrect state)

Multiple possible error conditions could trigger the failure above:

| Error Hypothesis | Observable Signals | When It Might Occur |
|------------------|-------------------|-------------------|
| **Upstream Timeout** | `llm_request_latency_ms` > client timeout value; `llm_request_errors_total{error_class=timeout}` increases | LLM Provider slow or overloaded (429, degraded SLA) |
| **Retrieval Failed** | `retrieval_empty_result_rate` spikes; `retrieval_latency_ms` exceeds threshold | Policy documents not indexed, search service down, or query not matching any documents |
| **Validator Rejected** | `ai_response_evaluations_total{quality_status=ungrounded}` increases; response marked `needs_review` internally | LLM cited documents not actually returned by Retriever, or citation format invalid |
| **Circuit Open** | Service explicitly returns 503 "service unavailable"; `circuit_breaker_state=open` metric set | Dependency exhausted (connection pool, rate limit, consecutive failures) |
| **Monitoring Pipeline Down** | No trace data arriving; `monitoring_pipeline_up=0`; Tempo backend unreachable | Control plane failure, not the application itself |

**Note**: The same user failure (no response in 30s) can stem from any of these errors. Do not assume the first one is the root cause.

### Layer 3: FAULT (System configuration or code defect)

Potential faults that enable the errors above:

| Fault Class | Example | Detection Method |
|-------------|---------|------------------|
| **Configuration** | Client timeout set to 60 seconds but SLO is 30 seconds; LLM endpoint URL points to wrong region | Code review, config audit |
| **Missing Error Handler** | Retriever times out, exception bubbles up uncaught instead of returning explicit "no data" | Stack trace in logs, test coverage audit |
| **Resource Constraint** | Connection pool size too small for peak load; HTTP client not releasing connections properly | Capacity planning audit, load testing |
| **Logic Defect** | Validator citation check uses fuzzy string match, sometimes misses valid citations; leads to discarding correct answers | Unit tests, trace inspection |
| **Incomplete Fallback** | Code retries LLM indefinitely without timeout, blocking other requests | Code review, timeout tests |

**Note**: Faults may exist in code for months without causing failures if they're only triggered under specific conditions (e.g., high load, specific query patterns). A fault is not a failure until it propagates.

---

## Actions by Layer

### On Failure (Immediate, User-Facing)

**Goal**: Stop the bleeding. User was promised a response; that promise is broken.

- [ ] Stop any ongoing rollout that increases error rate
- [ ] If available, activate fallback: cached answer, pre-written guidance, or explicit "we're degraded" message
- [ ] Notify on-call engineer (P1 incident if SLA is breached)
- [ ] Start collecting evidence:
  - Request ID from the user
  - Corresponding trace/log in Tempo/Loki
  - Metric spike timeline in Prometheus
  - User outcome (did they get any response, even a degraded one?)

### On Error (Diagnosis, Dependency-Level)

**Goal**: Narrow down which part of the system entered an incorrect state.

- [ ] Inspect trace for this request:
  - Did Retriever respond? (check dependency span)
  - Did LLM Provider respond? (check latency, error status)
  - Did Validator run and reject? (check evaluation signal)
  - Did the response leave the Gateway? (check HTTP status in root span)
- [ ] Cross-check metrics:
  - Is `llm_request_errors_total` trending up for this specific client or query type?
  - Is `retrieval_latency_p95` spiking? Is `retrieval_empty_result_rate` elevated?
  - Is `circuit_breaker_state` open?
- [ ] If error hypothesis is confirmed (e.g., "it's LLM timeout"), escalate to LLM team or re-attempt with explicit backoff

### On Fault (Remediation, Code/Config)

**Goal**: Prevent this fault from ever causing failure again.

- [ ] For configuration faults:
  - Audit settings: timeout values, endpoint URLs, connection pool sizes
  - Validate against documented SLO (if timeout is 60s but SLO is 30s, fix timeout)
  - If external dependency changed, re-read contract and adjust client accordingly
- [ ] For logic faults:
  - Review code path that was taken during this incident
  - Add or strengthen unit tests covering the error case
  - Add observability (structured log, metric, or trace step) so next time the fault triggers, the error is caught earlier
  - Consider adding safety checks: e.g., "if Retriever returns empty, do not call LLM with empty context"
- [ ] For missing error handlers:
  - Ensure all dependency calls are wrapped in try-catch
  - Log the original exception (for debugging) but return user-safe message
  - Add a metric to track how often this exception is caught
- [ ] Deploy fix only after tests pass; consider canary rollout to catch regressions early

---

## Verification Checklist

- [x] **Failure is user-observable** (not just a metric blip): "Employee can't get answer in time"
- [x] **Multiple error hypotheses listed**: Not assuming first hypothesis is correct
- [x] **Each error hypothesis is testable**: Have a trace span, metric, or log field to check
- [x] **Fault examples are specific and actionable**: Not "code is broken", but "timeout value too high" or "connection not released"
- [x] **Failure-layer action is user-focused**: Stop rollout, degrade gracefully, notify
- [x] **Error-layer action is diagnosis-focused**: Inspect trace, check metrics, cross-check dependencies
- [x] **Fault-layer action is prevention-focused**: Code review, tests, monitoring
- [x] **No unproven fault written as root cause**: All faults listed as "hypothesis to investigate", not "the problem was..."
- [x] **Semantic failure considered**: Even if HTTP 200 and no exceptions, could LLM have been fed incomplete context? (Retriever yielded empty result, or citation was wrong.) This is still a failure, observable via `ai_response_evaluations_total{quality_status=ungrounded}`.
- [x] **Control plane failures acknowledged**: Monitoring/tracing system down is a separate SLO failure, not a proof of "application working fine"

---

## References

- Day9 Service Boundary Spec: `../Day9/DIY/service_boundary.yaml`
- Day10 Article: Fault vs Error vs Failure definitions and incident response prioritization
