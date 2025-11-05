"""
OpenTelemetry tracing integration for Trainer & Model Registry Service.

Provides distributed tracing with Jaeger exporter and trace context propagation.
"""

import logging
from typing import Optional
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

logger = logging.getLogger(__name__)


class TracingConfig:
    """Configuration for OpenTelemetry tracing."""

    def __init__(
        self,
        service_name: str,
        jaeger_host: str = "localhost",
        jaeger_port: int = 6831,
        enabled: bool = True,
    ):
        """
        Initialize tracing configuration.

        Args:
            service_name: Name of the service
            jaeger_host: Jaeger agent host
            jaeger_port: Jaeger agent port
            enabled: Whether tracing is enabled
        """
        self.service_name = service_name
        self.jaeger_host = jaeger_host
        self.jaeger_port = jaeger_port
        self.enabled = enabled


def initialize_tracing(config: TracingConfig) -> Optional[trace.Tracer]:
    """
    Initialize OpenTelemetry tracing with Jaeger exporter.

    Args:
        config: Tracing configuration

    Returns:
        Tracer instance or None if tracing is disabled
    """
    if not config.enabled:
        logger.info("Tracing is disabled")
        return None

    try:
        # Create Jaeger exporter
        jaeger_exporter = JaegerExporter(
            agent_host_name=config.jaeger_host,
            agent_port=config.jaeger_port,
        )

        # Create resource
        resource = Resource(
            attributes={
                SERVICE_NAME: config.service_name,
            }
        )

        # Create tracer provider
        tracer_provider = TracerProvider(resource=resource)
        tracer_provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))

        # Set global tracer provider
        trace.set_tracer_provider(tracer_provider)

        # Instrument libraries
        RequestsInstrumentor().instrument()
        SQLAlchemyInstrumentor().instrument()

        logger.info(
            f"Tracing initialized with Jaeger at {config.jaeger_host}:{config.jaeger_port}"
        )

        return trace.get_tracer(__name__)

    except Exception as e:
        logger.error(f"Failed to initialize tracing: {e}")
        return None


def get_tracer(name: str) -> trace.Tracer:
    """
    Get a tracer instance.

    Args:
        name: Name of the tracer (typically __name__)

    Returns:
        Tracer instance
    """
    return trace.get_tracer(name)


def get_current_span() -> trace.Span:
    """
    Get the current active span.

    Returns:
        Current span
    """
    return trace.get_current_span()


def set_span_attribute(key: str, value: str) -> None:
    """
    Set an attribute on the current span.

    Args:
        key: Attribute key
        value: Attribute value
    """
    span = get_current_span()
    if span:
        span.set_attribute(key, value)


def add_span_event(name: str, attributes: Optional[dict] = None) -> None:
    """
    Add an event to the current span.

    Args:
        name: Event name
        attributes: Optional event attributes
    """
    span = get_current_span()
    if span:
        span.add_event(name, attributes or {})


def shutdown_tracing() -> None:
    """Shutdown tracing and flush pending spans."""
    try:
        tracer_provider = trace.get_tracer_provider()
        if hasattr(tracer_provider, "force_flush"):
            tracer_provider.force_flush()
        logger.info("Tracing shutdown complete")
    except Exception as e:
        logger.error(f"Error during tracing shutdown: {e}")
