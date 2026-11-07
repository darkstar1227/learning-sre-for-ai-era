"""
Three alert rule drafts: Availability, Latency, Dependency.

Day25 DIY Exercise: Review three alert rules.
Each covers one dimension and must answer:
1. Which SLO/user commitment is threatened?
2. Who is responsible?
3. What can on-call do in 5 minutes?
"""

from app.schemas import AlertRule, Runbook


# ===== Alert 1: Availability =====

availability_alert = AlertRule(
    name="Availability - Fast Burn",
    description="Alert when error budget is being consumed at >10x normal rate",

    # SLI/SLO
    sli="Success rate = (HTTP 2xx / total requests)",
    slo="99.9% availability over 30-day rolling window",
    user_impact="Users see 5xx errors; feature becomes unavailable if burn continues unchecked",

    # Ownership
    owner_team="Platform SRE Team",
    owner_oncall="On-call SRE (rotate daily)",

    # Trigger
    condition="error_budget_burn_rate > 10x for 5 minutes",
    window="5 minute evaluation window",

    # Runbook
    runbook=Runbook(
        title="Fast Burn Availability Response",
        steps=[
            "Check alert time & SLI window; confirm 10x+ burn in Prometheus dashboard",
            "Find affected route/outcome using `/api/logs` with failed request samples",
            "Open corresponding trace in Tempo; check upstream timeout vs local error",
            "If upstream timeout: apply predefined degradation (return stale cache) without infinite retry",
            "If local error (DB connection, OOM): follow /runbook/local-failure playbook",
            "Declare incident owner & estimate user impact (# requests/minute affected)",
            "If unresolved in 5 min: escalate to on-call engineer or page backend team",
        ],
        is_tested=False,
    ),

    # Conditions
    suppression_condition="Maintenance window (4 hours max, must be declared in Slack #incidents)",
    resolution_condition="SLI recovers to >95% success rate for 10 minutes",

    actionable=True,
    actionability_reason="Clear owner, concrete first step (check dashboard), connects to error budget burndown",
)


# ===== Alert 2: Latency =====

latency_alert = AlertRule(
    name="Latency - P95 Threshold",
    description="Alert when P95 latency exceeds SLO target for sustained period",

    # SLI/SLO
    sli="P95 response latency for /api/ask endpoint",
    slo="P95 latency < 500ms over 30-day rolling window",
    user_impact="User requests hang; perceived unresponsiveness may cause abandonment if latency stays >2s",

    # Ownership
    owner_team="Platform SRE Team + Backend Team (shared response)",
    owner_oncall="On-call SRE (initial triage) → Backend engineer (if code change needed)",

    # Trigger
    condition="histogram_quantile(0.95, http_request_duration_seconds) > 500ms for 10 minutes",
    window="10 minute evaluation window",

    # Runbook
    runbook=Runbook(
        title="P95 Latency Response",
        steps=[
            "Confirm P95 threshold breach in Prometheus (check graph for trend, not single spike)",
            "Check if breach coincides with code deploy, config change, or traffic spike",
            "Open Tempo traces filtered by P95+ duration; identify slowest step (DB, LLM call, Retriever)",
            "If DB query slow: check connection pool exhaustion, slow query log, index missing",
            "If LLM call slow: check Gemini API status page, reduce context size, or enable response timeout",
            "If acceptable (e.g., surge traffic + caching helps): extend SLO window, don't escalate",
            "If code-level: page backend engineer to review, deploy fix, or increase resource limits",
        ],
        is_tested=False,
    ),

    # Conditions
    suppression_condition="Known traffic surge (on-call manually disables for 2 hours max)",
    resolution_condition="P95 latency < 500ms for 15 consecutive minutes",

    actionable=True,
    actionability_reason="Owner identified, first step is dashboard inspection, connects to user-facing SLO",
)


# ===== Alert 3: Dependency Failure =====

dependency_alert = AlertRule(
    name="Dependency - Gemini API Unavailable",
    description="Alert when dependency critical to SLI becomes unavailable or degraded",

    # SLI/SLO
    sli="LLM availability = (successful Gemini calls / total calls)",
    slo="99% LLM availability; user feature degrades gracefully if <99% for 30 minutes",
    user_impact="Questions cannot be answered; feature returns 'service temporarily unavailable' message",

    # Ownership
    owner_team="Platform SRE Team (owns graceful degradation) + Backend Team (owns Gemini integration)",
    owner_oncall="On-call SRE (escalate to Gemini support ticket if needed)",

    # Trigger
    condition="(gemini_call_error_rate > 5% for 10 minutes) OR (gemini_call_timeout > 10%) for 5 minutes",
    window="5-10 minute window (depends on metric; see condition)",

    # Runbook
    runbook=Runbook(
        title="Dependency Failure - Gemini Response",
        steps=[
            "Check Gemini API status page (https://status.ai.google.dev/) for known outages",
            "Verify error rate in Prometheus: is it Gemini 5xx, timeout, or our auth failure?",
            "If 5xx or timeout from Gemini: follow caching strategy (return stale context if available)",
            "If auth failure (401/403): check API key expiry, quota limits in Google Cloud Console",
            "Enable circuit breaker: stop calling Gemini for 5 minutes, return cached/degraded response",
            "Notify Backend team; open ticket with Gemini support if outage confirmed on their side",
            "Users see: 'AI feature temporarily unavailable, please refresh in 5 minutes'",
        ],
        is_tested=False,
    ),

    # Conditions
    suppression_condition="Scheduled Gemini maintenance (Google announces >2 hours in advance)",
    resolution_condition="Gemini error rate < 1% for 5 consecutive minutes AND circuit breaker re-enabled",

    actionable=True,
    actionability_reason="Identifies dependency, owner clear, runbook specifies fallback (caching), doesn't require code change in first 5 min",
)


# ===== Collection =====

ALL_ALERTS = [
    availability_alert,
    latency_alert,
    dependency_alert,
]
