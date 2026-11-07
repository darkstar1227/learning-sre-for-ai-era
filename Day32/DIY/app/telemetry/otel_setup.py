"""
OpenTelemetry setup for AI workflow tracing.
Configurable to export to Langfuse, LangSmith, Tempo, or other OTLP-compatible backends.
"""

import base64
import os
from typing import Optional

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, BatchSpanProcessor


def setup_otel_to_langfuse(
    langfuse_base_url: Optional[str] = None,
    langfuse_public_key: Optional[str] = None,
    langfuse_secret_key: Optional[str] = None,
    service_name: str = "answer-api",
) -> trace.Tracer:
    """
    Setup OpenTelemetry to export spans to Langfuse via OTLP.

    Reference: https://langfuse.com/docs/observability/sdk/otel

    Args:
        langfuse_base_url: e.g., "https://cloud.langfuse.com" or "http://localhost:3000"
        langfuse_public_key: Langfuse public key (or env: LANGFUSE_PUBLIC_KEY)
        langfuse_secret_key: Langfuse secret key (or env: LANGFUSE_SECRET_KEY)
        service_name: OpenTelemetry service name

    Returns:
        Configured tracer instance
    """

    # Use environment variables as fallback
    base_url = langfuse_base_url or os.environ.get("LANGFUSE_BASE_URL", "")
    public_key = langfuse_public_key or os.environ.get("LANGFUSE_PUBLIC_KEY", "")
    secret_key = langfuse_secret_key or os.environ.get("LANGFUSE_SECRET_KEY", "")

    if not base_url or not public_key or not secret_key:
        raise ValueError(
            "Langfuse endpoint and credentials required. "
            "Set LANGFUSE_BASE_URL, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY env vars or pass as arguments."
        )

    # Create Basic auth header
    auth = base64.b64encode(f"{public_key}:{secret_key}".encode()).decode()

    # Create tracer provider
    provider = TracerProvider(
        resource=Resource.create({"service.name": service_name})
    )

    # Configure OTLP exporter for Langfuse
    exporter = OTLPSpanExporter(
        endpoint=f"{base_url}/api/public/otel/v1/traces",
        headers={
            "Authorization": f"Basic {auth}",
            "x-langfuse-ingestion-version": "4",  # Check Langfuse docs for current version
        },
    )

    # Use BatchSpanProcessor for production (handles batching, retry, etc.)
    # Use SimpleSpanProcessor for development (immediate export)
    if os.environ.get("DEBUG"):
        provider.add_span_processor(SimpleSpanProcessor(exporter))
    else:
        provider.add_span_processor(BatchSpanProcessor(exporter))

    # Set global tracer provider
    trace.set_tracer_provider(provider)

    return trace.get_tracer(service_name)


def setup_otel_to_collector(
    collector_otlp_endpoint: Optional[str] = None,
    service_name: str = "answer-api",
) -> trace.Tracer:
    """
    Setup OpenTelemetry to export spans to OpenTelemetry Collector.

    This is the recommended path for production: Application → Collector → Backend.
    The Collector handles batching, retry, routing, and can export to multiple backends.

    Args:
        collector_otlp_endpoint: e.g., "http://localhost:4317" (gRPC) or "http://localhost:4318" (HTTP)
        service_name: OpenTelemetry service name

    Returns:
        Configured tracer instance
    """

    # Use environment variable as fallback
    endpoint = collector_otlp_endpoint or os.environ.get(
        "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"
    )

    provider = TracerProvider(
        resource=Resource.create({"service.name": service_name})
    )

    # Configure OTLP exporter for Collector
    exporter = OTLPSpanExporter(endpoint=endpoint)

    # Use BatchSpanProcessor for production
    provider.add_span_processor(BatchSpanProcessor(exporter))

    # Set global tracer provider
    trace.set_tracer_provider(provider)

    return trace.get_tracer(service_name)


def get_tracer(service_name: str = "answer-api") -> trace.Tracer:
    """Get the global tracer instance (should be called after setup_otel_* is called)."""
    return trace.get_tracer(service_name)
