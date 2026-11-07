"""Fixture that generates metrics, logs, and traces for a simulated request."""

import logging
import time
import uuid
from opentelemetry import trace

from app.metrics import timeout_incidents, answer_requests
from app.logging_setup import setup_logging
from app.tracing import get_tracer


logger = setup_logging()


class SimulatedRequest:
    """Simulates a request with dependency timeout scenario."""

    def __init__(self, request_id=None, dependency="retriever", timeout=True):
        self.request_id = request_id or f"demo-{uuid.uuid4().hex[:8]}"
        self.dependency = dependency  # retriever, model, tool
        self.timeout = timeout
        self.tracer = get_tracer()

    def log_event(self, event: str, error_class: str = None, **extra_fields):
        """
        Emit a structured log with request_id for correlation.

        Note: request_id is in logs/traces for correlation,
        but NOT in metrics labels (metrics only use low-cardinality fields).
        """
        record = logging.LogRecord(
            name="app",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg=event,
            args=(),
            exc_info=None,
        )
        record.request_id = self.request_id
        record.event = event
        record.error_class = error_class

        # Attach extra fields
        for key, value in extra_fields.items():
            setattr(record, key, value)

        logger.handle(record)

    def execute(self):
        """
        Execute the simulated request with:
        1. One metric (counter increment)
        2. One JSON log entry
        3. One trace with 2+ spans
        """
        with self.tracer.start_as_current_span(f"ask") as ask_span:
            # Add request_id to trace attributes for correlation
            ask_span.set_attribute("request_id", self.request_id)
            ask_span.set_attribute("dependency", self.dependency)

            if self.timeout:
                # Simulate timeout scenario
                with self.tracer.start_as_current_span("dependency_retrieve") as retrieve_span:
                    retrieve_span.set_attribute("request_id", self.request_id)
                    retrieve_span.set_attribute("dependency", self.dependency)

                    # Simulate retrieval time
                    time.sleep(0.1)

                    # Log the timeout event
                    self.log_event(
                        event="dependency_timeout",
                        error_class="TimeoutError",
                        dependency=self.dependency,
                        retry_count=1,
                    )

                # Increment metrics with low-cardinality labels ONLY
                timeout_incidents.labels(dependency=self.dependency).inc()
                answer_requests.labels(outcome="upstream_timeout").inc()
            else:
                # Success scenario
                with self.tracer.start_as_current_span("dependency_retrieve") as retrieve_span:
                    retrieve_span.set_attribute("request_id", self.request_id)
                    retrieve_span.set_attribute("dependency", self.dependency)

                    time.sleep(0.05)

                # Log success
                self.log_event(
                    event="dependency_success",
                    error_class=None,
                    dependency=self.dependency,
                    duration_ms=50,
                )

                answer_requests.labels(outcome="success").inc()

        return {
            "request_id": self.request_id,
            "dependency": self.dependency,
            "timeout": self.timeout,
        }


def create_fixture_requests(count=1, mix_outcomes=False):
    """
    Create multiple fixture requests for observability testing.

    Args:
        count: Number of requests to generate
        mix_outcomes: If True, generate both timeout and success requests

    Returns:
        List of executed request results with request_id for correlation
    """
    results = []
    for i in range(count):
        if mix_outcomes:
            timeout = (i % 2 == 0)
        else:
            timeout = True

        req = SimulatedRequest(timeout=timeout)
        result = req.execute()
        results.append(result)

    return results
