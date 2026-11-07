"""
SLI (Service Level Indicator) event contract for LLM application.

This module defines the event schema for tracking LLM workflow timing,
following the Day 18 "Defining the Contract" approach.

Key events: request_received, retrieval_started, retrieval_finished,
model_started, first_token, generation_finished, tool_finished, response_sent.

Outcomes: completed, technical_failed, quality_failed, safety_blocked, insufficient_context.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from time import perf_counter
from typing import Literal
from uuid import uuid4


Outcome = Literal[
    "completed",
    "technical_failed",
    "quality_failed",
    "safety_blocked",
    "insufficient_context",
]


@dataclass
class AskTiming:
    """
    Explicit time points for a single request journey.

    All timestamps are float (seconds since epoch via perf_counter).
    Use None for unmeasured/unavailable events—never 0.
    """
    request_received: float
    workflow_started: float | None = None
    retrieval_started: float | None = None
    retrieval_finished: float | None = None
    model_started: float | None = None
    first_token: float | None = None
    generation_finished: float | None = None
    tool_finished: float | None = None
    response_sent: float | None = None

    def duration_ms(self, start: str, end: str) -> float | None:
        """
        Calculate duration in milliseconds between two events.
        Returns None if either event is missing.
        """
        start_at = getattr(self, start)
        end_at = getattr(self, end)
        if start_at is None or end_at is None:
            return None
        return round((end_at - start_at) * 1000, 2)


@dataclass
class AskEvent:
    """
    Complete event record for one /ask workflow execution.

    Combines:
    - Explicit timing points (via AskTiming)
    - Workflow/version metadata
    - Outcome classification (technical, quality, safety)
    - Operational status flags (fallback, retrieval count, tool count)
    """
    request_id: str
    trace_id: str
    workflow_name: str
    workflow_version: str
    model_name: str
    retrieval_index_version: str
    timing: AskTiming
    outcome: Outcome = "completed"
    technical_status: str = "unknown"
    workflow_status: str = "unknown"
    quality_status: str = "unknown"
    safety_status: str = "unknown"
    retrieval_count: int = 0
    tool_count: int = 0
    fallback_triggered: bool = False
    error_class: str | None = None
    notes: list[str] = field(default_factory=list)

    def to_log_record(self) -> dict[str, object]:
        """
        Convert to a flat dict for structured logging.

        Includes:
        - All event fields as-is
        - Computed SLI durations: queue_delay_ms, retrieval_ms, ttft_ms, generation_ms, end_to_end_ms
        - timing fields for detailed inspection
        """
        record = asdict(self)

        # Flatten timing into record
        record["queue_delay_ms"] = self.timing.duration_ms(
            "request_received", "workflow_started"
        )
        record["retrieval_ms"] = self.timing.duration_ms(
            "retrieval_started", "retrieval_finished"
        )
        record["ttft_ms"] = self.timing.duration_ms(
            "request_received", "first_token"
        )
        record["generation_ms"] = self.timing.duration_ms(
            "model_started", "generation_finished"
        )
        record["end_to_end_ms"] = self.timing.duration_ms(
            "request_received", "response_sent"
        )

        # Keep timing as nested dict for inspection
        record["timing"] = {
            "request_received": self.timing.request_received,
            "workflow_started": self.timing.workflow_started,
            "retrieval_started": self.timing.retrieval_started,
            "retrieval_finished": self.timing.retrieval_finished,
            "model_started": self.timing.model_started,
            "first_token": self.timing.first_token,
            "generation_finished": self.timing.generation_finished,
            "tool_finished": self.timing.tool_finished,
            "response_sent": self.timing.response_sent,
        }

        return record


def new_ask_event() -> AskEvent:
    """
    Factory: create a fresh AskEvent with current timestamp.

    Initializes request_received and IDs; caller fills in other timing points.
    """
    now = perf_counter()
    return AskEvent(
        request_id=f"req_{uuid4().hex[:12]}",
        trace_id=f"trace_{uuid4().hex[:12]}",
        workflow_name="policy_qa",
        workflow_version="2026-09-22",
        model_name="configured-at-deploy-time",
        retrieval_index_version="policy-v1",
        timing=AskTiming(request_received=now),
    )
