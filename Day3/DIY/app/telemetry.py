from opentelemetry import trace

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)

from opentelemetry.sdk.resources import (
    SERVICE_NAME,
    Resource,
)

from opentelemetry.sdk.trace import (
    TracerProvider,
)

from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
)


def configure_tracing() -> None:
    resource = Resource.create(
        {
            SERVICE_NAME: "sre-lab-api",
        }
    )

    provider = TracerProvider(
        resource=resource,
    )

    exporter = OTLPSpanExporter(
        endpoint="otel-collector:4317",
        insecure=True,
    )

    provider.add_span_processor(
        BatchSpanProcessor(
            exporter,
        )
    )

    trace.set_tracer_provider(
        provider,
    )
