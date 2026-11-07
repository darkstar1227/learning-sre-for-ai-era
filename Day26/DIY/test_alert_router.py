from alert_router import AIEvent, Destination, route


def test_fast_burn_pages_on_call() -> None:
    event = AIEvent(
        event_type="provider_timeout",
        error_budget_fast_burn=True,
        task_failure_rate=0.28,
    )
    assert route(event) is Destination.PAGER


def test_sustained_quality_drift_enters_evaluation_queue() -> None:
    event = AIEvent(
        event_type="citation_drift",
        quality_ratio=0.94,
        baseline_quality_ratio=0.98,
        sample_size=186,
    )
    assert route(event) is Destination.EVALUATION_QUEUE


def test_one_bad_answer_does_not_page() -> None:
    event = AIEvent(event_type="single_bad_answer", sample_size=1)
    assert route(event) is Destination.REVIEW_SAMPLE


def test_successful_unsafe_tool_execution_escalates() -> None:
    event = AIEvent(
        event_type="tool_execution",
        unsafe_tool_attempt=True,
        tool_execution_succeeded=True,
    )
    assert route(event) is Destination.SECURITY_ESCALATION
