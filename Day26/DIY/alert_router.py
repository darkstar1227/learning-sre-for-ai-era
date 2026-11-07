from dataclasses import dataclass
from enum import StrEnum


class Destination(StrEnum):
    PAGER = "pager"
    EVALUATION_QUEUE = "evaluation_queue"
    SECURITY_ESCALATION = "security_escalation"
    REVIEW_SAMPLE = "review_sample"
    DASHBOARD = "dashboard"


@dataclass(frozen=True)
class AIEvent:
    event_type: str
    error_budget_fast_burn: bool = False
    task_failure_rate: float = 0.0
    quality_ratio: float | None = None
    baseline_quality_ratio: float | None = None
    sample_size: int = 0
    unsafe_tool_attempt: bool = False
    tool_execution_blocked: bool = False
    tool_execution_succeeded: bool = False


def route(event: AIEvent) -> Destination:
    if event.unsafe_tool_attempt and event.tool_execution_succeeded:
        return Destination.SECURITY_ESCALATION

    if event.unsafe_tool_attempt and not event.tool_execution_blocked:
        return Destination.SECURITY_ESCALATION

    if event.error_budget_fast_burn:
        return Destination.PAGER

    if (
        event.quality_ratio is not None
        and event.baseline_quality_ratio is not None
        and event.sample_size >= 100
        and event.quality_ratio < event.baseline_quality_ratio - 0.03
    ):
        return Destination.EVALUATION_QUEUE

    if event.event_type == "single_bad_answer":
        return Destination.REVIEW_SAMPLE

    return Destination.DASHBOARD
