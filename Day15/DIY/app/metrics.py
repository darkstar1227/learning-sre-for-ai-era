"""
Prometheus metrics for availability SLI.

Records classified events to Prometheus counters for observability.
Reference: Day15/Day15.md - Step 3: Output metrics from classifier
"""

from prometheus_client import Counter

from app.availability import classify_availability, AvailabilityEvent


# Availability SLI counter
# Labels:
#   sli_eligible: "true" or "false" - whether event counts toward denominator
#   sli_result: "good", "bad", or "excluded" - classification result
#   response_status: terminal status from application logic
ask_sli_events_total = Counter(
    "ask_sli_events_total",
    "Classified /ask events for availability SLI",
    labelnames=(
        "sli_eligible",
        "sli_result",
        "response_status",
    ),
)


def record_sli_event(event: AvailabilityEvent) -> None:
    """
    Classify an event and record it to Prometheus.

    This function combines classification logic with metric recording.
    Call this after your application has produced a complete response
    and validated it against the service contract.

    Args:
        event: AvailabilityEvent to classify and record
    """
    classification = classify_availability(event)

    ask_sli_events_total.labels(
        sli_eligible=str(classification.eligible).lower(),
        sli_result=classification.result.value,
        response_status=event.response_status,
    ).inc()
