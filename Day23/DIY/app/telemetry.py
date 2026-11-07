from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor


def configure_tracing() -> None:
    resource = Resource.create(
        {
            "service.name": "ai-policy-api",
            "service.version": "dev",
            "deployment.environment.name": "local",
        }
    )
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)


tracer = trace.get_tracer("ai-policy-api.workflow")
