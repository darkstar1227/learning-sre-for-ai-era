"""
Day16 - Prometheus metrics for latency histogram.

This module defines the ask_request_duration_seconds histogram
to track server-side end-to-end latency for /ask requests.
"""
from prometheus_client import Histogram


ask_request_duration_seconds = Histogram(
    "ask_request_duration_seconds",
    "Server-side end-to-end duration for /ask requests",
    labelnames=("route", "workflow_status", "model_route"),
    buckets=(0.1, 0.25, 0.5, 1, 2, 3, 5, 10, 30),
)
