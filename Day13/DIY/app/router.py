from dataclasses import dataclass

from app.models import ModelClient, ModelResult, ModelUnavailable


SAFE_TO_FALLBACK = {"policy_question", "document_summary"}


def may_fallback(task_type: str, error: Exception) -> bool:
    return (
        task_type in SAFE_TO_FALLBACK
        and isinstance(error, ModelUnavailable)
    )


@dataclass
class RouteOutcome:
    result: ModelResult | None
    status: str
    fallback_triggered: bool
    reason: str


def generate_with_fallback(
    *,
    request_id: str,
    task_type: str,
    prompt: str,
    primary: ModelClient,
    fallback: ModelClient,
) -> RouteOutcome:
    try:
        result = primary.generate(prompt, timeout_seconds=2.0)
        return RouteOutcome(
            result=result,
            status="completed",
            fallback_triggered=False,
            reason="primary_completed",
        )
    except Exception as error:
        if not may_fallback(task_type, error):
            return RouteOutcome(
                result=None,
                status="unavailable",
                fallback_triggered=False,
                reason=type(error).__name__,
            )

        fallback_result = fallback.generate(prompt, timeout_seconds=2.0)
        return RouteOutcome(
            result=fallback_result,
            status="degraded_completed",
            fallback_triggered=True,
            reason="primary_unavailable",
        )
