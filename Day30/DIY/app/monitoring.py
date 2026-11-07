from prometheus_client import Counter, Gauge, Histogram, make_asgi_app

# Request metrics
ask_requests_total = Counter(
    "ask_requests_total",
    "Total number of /ask requests",
    labelnames=["method", "status_code"],
)

ask_outcomes_total = Counter(
    "ask_outcomes_total",
    "Total number of ask outcomes by workflow_status",
    labelnames=["workflow_status", "degraded"],
)

dependency_failures_total = Counter(
    "dependency_failures_total",
    "Total number of dependency failures",
    labelnames=["dependency", "failure_class"],
)

tool_action_attempted_total = Counter(
    "tool_action_attempted_total",
    "Total number of tool actions attempted",
)

circuit_breaker_state = Gauge(
    "circuit_breaker_state",
    "Circuit breaker state: 0=closed, 1=open, 2=half_open",
    labelnames=["dependency"],
)

ask_request_duration_seconds = Histogram(
    "ask_request_duration_seconds",
    "Ask request duration in seconds",
    labelnames=["outcome"],
)


def record_ask_request(status_code: int) -> None:
    ask_requests_total.labels(method="POST", status_code=status_code).inc()


def record_ask_outcome(workflow_status: str, degraded: bool) -> None:
    ask_outcomes_total.labels(
        workflow_status=workflow_status,
        degraded=str(degraded).lower(),
    ).inc()


def record_dependency_failure(dependency: str, failure_class: str) -> None:
    dependency_failures_total.labels(
        dependency=dependency,
        failure_class=failure_class,
    ).inc()


# Mount metrics endpoint for Prometheus scraping
metrics_app = make_asgi_app()
