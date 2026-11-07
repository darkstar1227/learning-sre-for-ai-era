"""OpenTelemetry tracing setup with request_id correlation."""

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource


_initialized = False


def setup_tracing(service_name="day21-demo"):
    """
    Initialize OpenTelemetry tracer with OTLP exporter.
    In this demo, we use SimpleSpanProcessor which exports immediately.
    In production, use BatchSpanProcessor for efficiency.

    Safe to call multiple times; initialization only happens once.
    """
    global _initialized

    if _initialized:
        return trace.get_tracer(__name__)

    resource = Resource.create({
        "service.name": service_name,
    })

    tracer_provider = TracerProvider(resource=resource)

    # Try to connect to OTLP collector; if not available, spans are still created locally
    try:
        otlp_exporter = OTLPSpanExporter(
            endpoint="localhost:4317",
            insecure=True,
        )
        tracer_provider.add_span_processor(SimpleSpanProcessor(otlp_exporter))
    except Exception:
        # If collector not available, spans still work locally but won't be exported
        pass

    trace.set_tracer_provider(tracer_provider)
    _initialized = True
    return trace.get_tracer(__name__)


def get_tracer():
    """Get the global tracer instance."""
    return trace.get_tracer(__name__)
