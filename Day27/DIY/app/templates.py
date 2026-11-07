"""
Template generators for postmortem documentation.

Generates markdown-formatted postmortem documents from incident data.
"""

from datetime import datetime
from .models import Incident, RunbookEntry


def generate_postmortem_markdown(incident: Incident) -> str:
    """Generate a postmortem markdown document from incident data."""

    lines = [
        f"# Postmortem: {incident.title}",
        f"",
        f"**Incident ID:** {incident.incident_id}",
        f"**Severity:** {incident.severity.value}",
        f"**Service:** {incident.service_affected}",
        f"**Date:** {incident.created_at.isoformat()}",
        f"",
    ]

    # Detect Stage
    if incident.detect:
        lines.extend([
            "## Detect Stage",
            f"",
            f"**Alert Name:** {incident.detect.name}",
            f"**Triggered At:** {incident.detect.triggered_at.isoformat()}",
            f"**Threshold:** {incident.detect.threshold}",
            f"**Current Value:** {incident.detect.current_value}",
            f"",
        ])

    # Triage Stage
    if incident.triage:
        lines.extend([
            "## Triage Stage",
            f"",
            f"**Incident Commander:** {incident.triage.incident_commander}",
            f"**Severity:** {incident.triage.severity.value}",
            f"",
            f"**Affected Systems:**",
        ])
        for system in incident.triage.affected_systems:
            lines.append(f"- {system}")
        lines.extend([
            f"",
            f"**Estimated Impact Scope:** {incident.triage.estimated_impact_scope}",
            f"",
            f"**Immediate Risk:** {incident.triage.immediate_risk}",
            f"",
        ])

    # Mitigate Stage
    if incident.mitigations:
        lines.extend([
            "## Mitigate Stage",
            f"",
        ])
        for i, step in enumerate(incident.mitigations, 1):
            lines.extend([
                f"### Action {i}",
                f"",
                f"**Action:** {step.action}",
                f"**Executed At:** {step.executed_at.isoformat()}",
                f"**Expected Effect:** {step.expected_effect}",
                f"**Actual Effect:** {step.actual_effect}",
                f"",
            ])

    # Recover Stage
    if incident.recovery:
        lines.extend([
            "## Recover Stage",
            f"",
            f"**Recovery Completed At:** {incident.recovery.recovery_completed_at.isoformat()}",
            f"**SLI Metric:** {incident.recovery.sli_metric}",
            f"**Baseline Value:** {incident.recovery.baseline_value}",
            f"**Recovery Value:** {incident.recovery.recovery_value}",
            f"**Verification Method:** {incident.recovery.verification_method}",
            f"",
        ])

    # Root Cause Analysis
    if incident.root_cause:
        lines.extend([
            "## Root Cause Analysis",
            f"",
            f"**Root Cause:**",
            f"{incident.root_cause.root_cause}",
            f"",
        ])

        if incident.root_cause.contributing_factors:
            lines.extend([
                "**Contributing Factors:**",
            ])
            for factor in incident.root_cause.contributing_factors:
                lines.append(f"- {factor}")
            lines.append("")

        if incident.root_cause.detection_gap:
            lines.extend([
                f"**Detection Gap:** {incident.root_cause.detection_gap}",
                f"",
            ])

        if incident.root_cause.prevention_gap:
            lines.extend([
                f"**Prevention Gap:** {incident.root_cause.prevention_gap}",
                f"",
            ])

    # AI-Specific Factors
    if incident.ai_factors:
        lines.extend([
            "## AI-Specific Factors",
            f"",
        ])

        if incident.ai_factors.model_version:
            lines.append(f"**Model Version:** {incident.ai_factors.model_version}")
        if incident.ai_factors.prompt_version:
            lines.append(f"**Prompt Version:** {incident.ai_factors.prompt_version}")
        if incident.ai_factors.retrieval_index_version:
            lines.append(f"**Retrieval Index Version:** {incident.ai_factors.retrieval_index_version}")
        if incident.ai_factors.embedding_model:
            lines.append(f"**Embedding Model:** {incident.ai_factors.embedding_model}")

        lines.append("")

        if incident.ai_factors.evaluation_coverage_gap:
            lines.extend([
                f"**Evaluation Coverage Gap:** {incident.ai_factors.evaluation_coverage_gap}",
                f"",
            ])

        if incident.ai_factors.safety_check_status:
            lines.extend([
                f"**Safety Check Status:** {incident.ai_factors.safety_check_status}",
                f"",
            ])

        if incident.ai_factors.affected_input_types:
            lines.extend([
                f"**Affected Input Types:** {incident.ai_factors.affected_input_types}",
                f"",
            ])

    # What Went Well
    if incident.what_went_well:
        lines.extend([
            "## What Went Well",
            f"",
        ])
        for item in incident.what_went_well:
            lines.append(f"- {item}")
        lines.append("")

    # What We Learned
    if incident.what_we_learned:
        lines.extend([
            "## What We Learned",
            f"",
        ])
        for item in incident.what_we_learned:
            lines.append(f"- {item}")
        lines.append("")

    # Action Items
    if incident.action_items:
        lines.extend([
            "## Action Items",
            f"",
        ])
        for item in incident.action_items:
            status_marker = "✓" if item.status == "closed" else "○"
            lines.append(f"{status_marker} **[{item.category.upper()}]** {item.title}")
            lines.append(f"  - Owner: {item.owner}")
            lines.append(f"  - Priority: {item.priority}")
            if item.deadline:
                lines.append(f"  - Deadline: {item.deadline.date()}")
            lines.append(f"")

    return "\n".join(lines)


def generate_runbook_markdown(entries: list[RunbookEntry]) -> str:
    """Generate a runbook markdown document from runbook entries."""

    lines = [
        "# Runbook: Incident Response Procedures",
        "",
        "This runbook documents known issues, their symptoms, diagnosis procedures, and mitigation strategies.",
        "",
    ]

    for i, entry in enumerate(entries, 1):
        lines.extend([
            f"## {i}. {entry.issue_name}",
            f"",
            f"### Symptoms",
            f"",
        ])

        for symptom in entry.symptoms:
            lines.append(f"- {symptom}")

        lines.extend([
            f"",
            f"### Diagnosis Steps",
            f"",
        ])

        for j, step in enumerate(entry.diagnosis_steps, 1):
            lines.append(f"{j}. {step}")

        lines.extend([
            f"",
            f"### Mitigation Strategies",
            f"",
        ])

        for strategy in entry.mitigation_strategies:
            lines.append(f"- {strategy}")

        if entry.escalation_criteria:
            lines.extend([
                f"",
                f"### Escalation Criteria",
                f"",
                f"{entry.escalation_criteria}",
            ])

        if entry.reference_incidents:
            lines.extend([
                f"",
                f"### Reference Incidents",
                f"",
            ])
            for inc_id in entry.reference_incidents:
                lines.append(f"- {inc_id}")

        lines.append("")

    return "\n".join(lines)


def generate_postmortem_template() -> str:
    """Generate a blank postmortem template for filling in."""

    return """# Postmortem Template

**Incident ID:** [e.g., INC-2026-001]
**Title:** [Brief description of the incident]
**Severity:** [SEV1/SEV2/SEV3/SEV4]
**Service Affected:** [Service name]
**Date:** [YYYY-MM-DD]
**Postmortem Owner:** [Name]
**Postmortem Completed:** [Date]

---

## Detect Stage

**Alert Name:** [What alert triggered?]
**Triggered At:** [Timestamp UTC]
**Threshold:** [What was the threshold?]
**Actual Value:** [What was the observed value?]

---

## Triage Stage

**Incident Commander:** [Name]
**Initial Severity Assessment:** [SEV1/SEV2/SEV3/SEV4]

**Affected Systems:**
- [System 1]
- [System 2]

**Estimated Impact:**
- Users affected: [number/percentage]
- SLA risk: [Yes/No]
- Customer notifications needed: [Yes/No]

**Immediate Risk:**
[What happens if this isn't addressed?]

---

## Mitigate Stage

### Mitigation Action 1
- **Action:** [What was done?]
- **Executed At:** [Timestamp UTC]
- **Expected Effect:** [What should happen?]
- **Actual Effect:** [What actually happened?]

### Mitigation Action 2
[Repeat as needed]

---

## Recover Stage

**Recovery Completed At:** [Timestamp UTC]
**SLI Metric:** [Which metric proved recovery?]
**Baseline Value:** [Normal value]
**Recovery Value:** [Value at recovery time]

**Verification Method:**
[How did we verify recovery? Metrics? Traces? User testing?]

---

## Root Cause Analysis

**Root Cause:**
[System condition that led to the fault - not human error]

**Contributing Factors:**
- [Factor 1]
- [Factor 2]

**Detection Gap:**
[Why didn't existing monitoring catch this?]

**Prevention Gap:**
[What preventive measure was missing?]

---

## AI-Specific Factors (if applicable)

**Model/Prompt/Index Versions:**
- Model version: [version]
- Prompt version: [version]
- Retrieval index: [version]
- Embedding model: [model]

**Evaluation Coverage:**
[Did evaluation golden datasets cover this failure mode? Why not?]

**Safety Checks:**
[Did existing safety checks work? Where did they fail?]

**Affected Input Types:**
[Which types of inputs triggered this? Long context? Specific domain?]

---

## What Went Well

- [What defensive measures worked well?]
- [What did the team handle effectively?]
- [Any heroic efforts that should be recognized?]

---

## What We Learned

- [Key insight 1]
- [Key insight 2]
- [What would we do differently next time?]

---

## Action Items

| Item | Owner | Priority | Deadline | Status |
|------|-------|----------|----------|--------|
| [Title] | [Name] | high/medium/low | [Date] | open/closed |
| [Title] | [Name] | high/medium/low | [Date] | open/closed |

---

## Timeline

| Time (UTC) | Event |
|-----------|-------|
| HH:MM | [What happened?] |
| HH:MM | [What happened?] |
| HH:MM | [What happened?] |
"""


def generate_runbook_template() -> str:
    """Generate a blank runbook template."""

    return """# Runbook Template

## Issue Name: [e.g., Database Connection Pool Exhaustion]

### Symptoms

- [Observable symptom 1 - e.g., "API responses take >30s"]
- [Observable symptom 2 - e.g., "Database CPU at 100%"]
- [Observable symptom 3]

### Quick Diagnosis (run in order)

1. Check database connections:
   ```bash
   # Query to run
   SELECT * FROM pg_stat_activity WHERE state = 'active';
   ```

2. Check application logs:
   ```bash
   # Command to check logs
   docker logs <container-id> | grep "connection"
   ```

3. Check metrics:
   - Grafana dashboard: [link or name]
   - Look for: [metric name, threshold]

### Mitigation Strategies

**Option 1: Restart the affected service**
```bash
docker restart <service-name>
```
⚠️ This will cause brief downtime. Use only if other measures don't help.

**Option 2: Scale up the service**
```bash
docker-compose up -d --scale <service-name>=3
```
This increases capacity without downtime.

**Option 3: Enable fallback/degraded mode**
- Disable non-critical features: [Feature names]
- Redirect to cached responses: [Which endpoints?]
- Enable rate limiting: [Rate limit rules]

### Escalation Criteria

Escalate to architecture team if:
- Mitigation takes >15 minutes
- Issue recurs >2 times per week
- Requires database schema changes

### Reference Incidents

- INC-2026-001: [Brief description]
- INC-2025-012: [Brief description]

### Prevention

*From postmortem analysis:*
- [Preventive measure 1 - e.g., implement connection pool monitoring]
- [Preventive measure 2 - e.g., set up alerts at 80% capacity]
"""
