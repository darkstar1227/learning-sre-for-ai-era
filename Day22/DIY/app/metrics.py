"""
Prometheus metrics for Day22 observability frameworks.

Implements Golden Signals, RED, and USE methods as metrics.
Reference: Day22/Day22.md section ⑥
"""

from prometheus_client import Counter, Gauge, Histogram

# RED: Rate, Errors, Duration
REQUESTS = Counter(
    "ai_requests_total",
    "Completed AI requests by externally visible outcome.",
    ("route", "outcome", "model_route"),
)

REQUEST_DURATION = Histogram(
    "ai_request_duration_seconds",
    "End-to-end duration for an AI request.",
    ("route", "outcome"),
    buckets=(0.1, 0.3, 0.5, 1, 2, 5, 10, 30),
)

# AI-specific: Time To First Token
TTFT = Histogram(
    "ai_ttft_seconds",
    "Time from accepted request to the first streamed token.",
    ("route", "model_route"),
    buckets=(0.1, 0.25, 0.5, 1, 2, 5, 10),
)

# USE: Queue (Saturation, Errors)
QUEUE_WAIT = Histogram(
    "ai_queue_wait_seconds",
    "Time waiting for an inference worker.",
    ("queue", "model_route"),
    buckets=(0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10),
)

QUEUE_DEPTH = Gauge(
    "ai_inference_queue_depth",
    "Requests waiting at the instant of observation.",
    ("queue",),
)

# Workflow steps: RED for step-level failures
WORKFLOW_STEPS = Counter(
    "ai_workflow_steps_total",
    "AI workflow step outcomes.",
    ("step", "outcome"),
)

# Evaluation metrics: Day 08 quality/safety signals
EVALUATIONS = Counter(
    "ai_evaluations_total",
    "Evaluation results for quality and safety.",
    ("result", "evaluator_version"),
)
