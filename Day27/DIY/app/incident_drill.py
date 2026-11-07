"""
Incident drill - demonstrates the step-by-step approach from Day27.

This module implements the 6 steps from Day27's SRE Lab section:
Step 1: Reproduce a fixable failure mode
Step 2: Add correlated fields to requests
Step 3: Define four status dimensions
Step 4: Write sanitized event records
Step 5: Run a 30-minute tabletop exercise
Step 6: Convert findings to regression cases
"""

from dataclasses import dataclass
from enum import StrEnum
from uuid import uuid4
import json
from typing import Optional
from datetime import datetime


# ============================================================================
# Step 1: Define a reproducible failure mode with parse_citations
# ============================================================================

def parse_citations(answer: str) -> list[str]:
    """
    Parse citations from an answer following a specific format.

    This is an example failure mode: the parser expects [source:...] format,
    but the LLM might not follow this format, causing validation to fail.

    In a real system, this would be connected to your retrieval system's
    output validator.
    """
    # For the drill: we require [source:...] format
    # Real implementation would use your actual citation parser
    return [line for line in answer.splitlines() if line.startswith("[source:")]


def test_citation_format():
    """Test the citation parser - demonstrates a reproducible failure."""
    # This answer doesn't have the required [source:...] format
    answer = "遠端工作須經主管核准。\n來源：Remote Work Policy"
    citations = parse_citations(answer)

    print(f"Answer: {answer}")
    print(f"Parsed citations: {citations}")
    print(f"Test passed: {len(citations) > 0}\n")

    return len(citations) > 0


# ============================================================================
# Step 2: Define IncidentContext with correlatable fields
# ============================================================================

@dataclass(frozen=True)
class IncidentContext:
    """
    Incident context with fields that can be correlated across signals.

    These fields allow you to find the same request across:
    - Structured logs (by request_id)
    - Traces (by trace_id)
    - Incident notes (by task_id, deployment_id)
    """
    request_id: str
    trace_id: str
    task_id: str
    prompt_version: str
    deployment_id: str


def create_drill_context() -> IncidentContext:
    """Create a context for the incident drill."""
    context = IncidentContext(
        request_id=str(uuid4()),
        trace_id=str(uuid4()),
        task_id="policy-answer",
        prompt_version="v42-drill",
        deployment_id="local-drill-001",
    )
    return context


# ============================================================================
# Step 3: Define four status dimensions
# ============================================================================

class TechnicalStatus(StrEnum):
    """Technical layer status: did the service respond?"""
    OK = "ok"
    ERROR = "error"


class WorkflowStatus(StrEnum):
    """Workflow layer status: did the task complete?"""
    COMPLETED = "completed"
    DEGRADED = "degraded"
    FAILED = "failed"


class QualityStatus(StrEnum):
    """Quality layer status: is the output correct?"""
    PASS = "pass"
    FAIL = "fail"
    NOT_EVALUATED = "not_evaluated"


class SafetyStatus(StrEnum):
    """Safety layer status: is the output safe?"""
    PASS = "pass"
    BLOCKED = "blocked"
    REVIEW = "review"


# ============================================================================
# Step 4: Define an event structure for sanitized recording
# ============================================================================

@dataclass
class IncidentEvent:
    """
    A sanitized event that can be logged and reviewed during incident.

    High-cardinality fields (request_id) are present for correlation,
    but NOT used as metrics labels. Low-cardinality fields (task_id,
    deployment_id, status) are what go into metrics.
    """
    event: str
    request_id: str
    trace_id: str
    task_id: str
    prompt_version: str
    deployment_id: str
    technical_status: TechnicalStatus
    workflow_status: WorkflowStatus
    quality_status: QualityStatus
    safety_status: SafetyStatus
    failure_reason: Optional[str] = None
    timestamp: Optional[str] = None

    def to_json(self) -> str:
        """Convert to JSON for logging/storage."""
        data = {
            "event": self.event,
            "request_id": self.request_id,
            "trace_id": self.trace_id,
            "task_id": self.task_id,
            "prompt_version": self.prompt_version,
            "deployment_id": self.deployment_id,
            "technical_status": self.technical_status.value,
            "workflow_status": self.workflow_status.value,
            "quality_status": self.quality_status.value,
            "safety_status": self.safety_status.value,
            "failure_reason": self.failure_reason,
            "timestamp": self.timestamp or datetime.now().isoformat(),
        }
        return json.dumps(data, indent=2)


def create_drill_event(context: IncidentContext) -> IncidentEvent:
    """Create a quality gate failure event for the drill."""
    event = IncidentEvent(
        event="quality_gate_failed",
        request_id=context.request_id,
        trace_id=context.trace_id,
        task_id=context.task_id,
        prompt_version=context.prompt_version,
        deployment_id=context.deployment_id,
        technical_status=TechnicalStatus.OK,
        workflow_status=WorkflowStatus.COMPLETED,
        quality_status=QualityStatus.FAIL,
        safety_status=SafetyStatus.PASS,
        failure_reason="citation_format_missing",
    )
    return event


# ============================================================================
# Step 5: Simulate a 30-minute tabletop exercise
# ============================================================================

class TabletopExercise:
    """
    Simulates a 30-minute incident drill.

    This teaches the team to make decisions under pressure with incomplete
    information, not to guess the root cause.
    """

    def __init__(self, context: IncidentContext):
        self.context = context
        self.timeline = []
        self.decisions = []

    def minute_0_alert(self):
        """Minute 0: Citation-valid rate drops below threshold."""
        self.timeline.append({
            "minute": 0,
            "event": "Alert: citation-valid rate dropped 15% below baseline",
            "available_data": [
                "Dashboard showing P50/P95 latency",
                "Error rate (still low)",
            ]
        })
        print("[Minute 0] ALERT: citation-valid rate dropped")
        print("  - Available: Dashboard showing latency trends\n")

    def minute_5_diagnosis(self):
        """Minute 5: Initial diagnosis - is this API or quality issue?"""
        self.timeline.append({
            "minute": 5,
            "event": "Initial diagnosis",
            "finding": "HTTP 2xx rate normal; quality evaluator failing",
            "next_check": "Compare prompt version to release time"
        })
        print("[Minute 5] Diagnosis: HTTP 2xx normal, quality fail high")
        print("  - Conclusion: Not a technical failure, likely prompt/retrieval issue\n")

    def minute_10_version_check(self):
        """Minute 10: Check deployment/prompt version history."""
        self.timeline.append({
            "minute": 10,
            "event": "Version check",
            "finding": f"Prompt {self.context.prompt_version} entered canary at 09:00",
            "decision_needed": "Proceed with investigation or pause canary?"
        })
        print(f"[Minute 10] Version check: {self.context.prompt_version} in canary since 09:00")
        print("  - 2 hours ago - timing matches alert\n")

    def minute_15_decision(self):
        """Minute 15: Make decision - investigate or rollback?"""
        decision = "ROLLBACK prompt version"
        self.decisions.append(decision)
        self.timeline.append({
            "minute": 15,
            "decision": decision,
            "rationale": "Quality failure matches prompt canary start time; low risk to rollback",
        })
        print("[Minute 15] DECISION: Rollback prompt to v41")
        print("  - Rationale: Quality failure timing matches canary\n")

    def minute_20_observe(self):
        """Minute 20: Observe effect of rollback."""
        self.timeline.append({
            "minute": 20,
            "observation": "citation-valid rate rising",
            "effect": "Rollback had positive effect",
        })
        print("[Minute 20] Observation: citation-valid rate recovering")
        print("  - New requests improving\n")

    def minute_25_verify_recovery(self):
        """Minute 25: Verify recovery criteria met."""
        self.timeline.append({
            "minute": 25,
            "check": "SLI verification",
            "condition": "citation-valid rate > baseline for 15 consecutive minutes",
            "status": "PENDING"
        })
        print("[Minute 25] Verify recovery: P95 latency normal, quality metrics recovering")
        print("  - Need 15 minutes stable baseline before declaring recovered\n")

    def minute_30_summary(self):
        """Minute 30: Summarize findings for postmortem."""
        self.timeline.append({
            "minute": 30,
            "action": "Stop drill",
            "output": "Timeline, decisions, and unknowns collected"
        })
        print("[Minute 30] DRILL END")
        print("\n=== DRILL SUMMARY ===")
        print(f"Decisions made: {len(self.decisions)}")
        for i, decision in enumerate(self.decisions, 1):
            print(f"  {i}. {decision}")
        print("\nKey learning: Decisions driven by SLI changes and deployment timing,")
        print("not by guessing the root cause.\n")

    def run(self):
        """Run the full 30-minute drill."""
        print("\n" + "="*70)
        print("30-MINUTE TABLETOP EXERCISE")
        print("="*70 + "\n")

        self.minute_0_alert()
        self.minute_5_diagnosis()
        self.minute_10_version_check()
        self.minute_15_decision()
        self.minute_20_observe()
        self.minute_25_verify_recovery()
        self.minute_30_summary()


# ============================================================================
# Step 6: Convert findings to regression cases
# ============================================================================

def citation_gate(answer: str) -> bool:
    """
    A quality gate that checks citation format.

    This gate would be part of your release validation pipeline.
    It protects against the regression discovered in the drill.
    """
    return "[source:" in answer


def test_missing_citation_is_not_a_success() -> bool:
    """
    Regression test: ensure missing citation format is caught.

    This test prevents the same prompt regression from happening again.
    It converts a one-time incident into a permanently protected scenario.
    """
    answer = "遠端工作須經主管核准。\n來源：Remote Work Policy"
    result = citation_gate(answer)

    # The test PASSES when the gate correctly rejects the bad answer
    expected = False  # Citation format is missing, so gate should return False
    success = result == expected

    print(f"Regression test: test_missing_citation_is_not_a_success")
    print(f"  Answer: '{answer}'")
    print(f"  citation_gate() returned: {result}")
    print(f"  Expected: {expected}")
    print(f"  Test {'PASSED' if success else 'FAILED'}\n")

    return success


# ============================================================================
# Main drill execution
# ============================================================================

def run_full_drill():
    """Run all steps of the incident drill."""
    print("\n" + "="*70)
    print("DAY 27 INCIDENT DRILL - ALL STEPS")
    print("="*70)

    # Step 1: Parse citations
    print("\n[STEP 1] Reproduce failure mode")
    print("-" * 70)
    test_citation_format()

    # Step 2: Create context
    print("[STEP 2] Add incident context")
    print("-" * 70)
    context = create_drill_context()
    print(f"Context created:")
    print(f"  request_id: {context.request_id}")
    print(f"  trace_id: {context.trace_id}")
    print(f"  task_id: {context.task_id}")
    print(f"  prompt_version: {context.prompt_version}")
    print(f"  deployment_id: {context.deployment_id}\n")

    # Step 3: Status enums
    print("[STEP 3] Define four status dimensions")
    print("-" * 70)
    print(f"Technical statuses: {[s.value for s in TechnicalStatus]}")
    print(f"Workflow statuses: {[s.value for s in WorkflowStatus]}")
    print(f"Quality statuses: {[s.value for s in QualityStatus]}")
    print(f"Safety statuses: {[s.value for s in SafetyStatus]}\n")

    # Step 4: Event record
    print("[STEP 4] Create sanitized event record")
    print("-" * 70)
    event = create_drill_event(context)
    print(event.to_json())

    # Step 5: Tabletop exercise
    print("[STEP 5] Run tabletop exercise")
    print("-" * 70)
    exercise = TabletopExercise(context)
    exercise.run()

    # Step 6: Regression test
    print("[STEP 6] Convert to regression case")
    print("-" * 70)
    test_missing_citation_is_not_a_success()

    print("="*70)
    print("DRILL COMPLETE")
    print("="*70)


if __name__ == "__main__":
    run_full_drill()
