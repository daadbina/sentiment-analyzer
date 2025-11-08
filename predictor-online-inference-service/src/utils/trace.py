"""
Distributed tracing utilities for Predictor Online Inference Service.

Provides OpenTelemetry integration for distributed tracing across services.
All operations are traced with context propagation for end-to-end visibility.
"""

import logging
from contextlib import contextmanager
from functools import wraps
from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Span, Status, StatusCode
from ulid import ULID

logger = logging.getLogger(__name__)


# Global tracer instance
_tracer: trace.Tracer | None = None


def initialize_tracing(
    service_name: str,
    jaeger_agent_host: str,
    jaeger_agent_port: int,
    enable_tracing: bool = True,
) -> None:
    """
    Initialize OpenTelemetry tracing with Jaeger exporter.

    Args:
        service_name: Name of the service for tracing
        jaeger_agent_host: Jaeger agent hostname
        jaeger_agent_port: Jaeger agent port
        enable_tracing: Whether to enable tracing
    """
    global _tracer

    if not enable_tracing:
        logger.info("Distributed tracing is disabled")
        return

    try:
        # Create resource with service name
        resource = Resource(attributes={SERVICE_NAME: service_name})

        # Create tracer provider
        provider = TracerProvider(resource=resource)

        # Create Jaeger exporter
        jaeger_exporter = JaegerExporter(
            agent_host_name=jaeger_agent_host,
            agent_port=jaeger_agent_port,
        )

        # Add span processor
        provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))

        # Set global tracer provider
        trace.set_tracer_provider(provider)

        # Get tracer instance
        _tracer = trace.get_tracer(__name__)

        logger.info(
            f"Distributed tracing initialized: service={service_name}, "
            f"jaeger_host={jaeger_agent_host}, jaeger_port={jaeger_agent_port}"
        )
    except Exception as e:
        logger.error(f"Failed to initialize distributed tracing: {e}", exc_info=True)
        _tracer = None


def get_tracer() -> trace.Tracer | None:
    """
    Get the global tracer instance.

    Returns:
        Tracer instance or None if tracing is not initialized
    """
    return _tracer


def generate_trace_id() -> str:
    """
    Generate a unique trace ID using ULID.

    Returns:
        ULID string for trace identification
    """
    return str(ULID())


@contextmanager
def trace_span(
    name: str,
    attributes: dict[str, Any] | None = None,
    trace_id: str | None = None,
):
    """
    Context manager for creating a traced span.

    Args:
        name: Name of the span
        attributes: Additional attributes to attach to the span
        trace_id: Optional trace ID for correlation

    Yields:
        Span object for additional operations

    Example:
        with trace_span("fetch_features", {"group_id": "123"}) as span:
            features = fetch_features()
            span.set_attribute("feature_count", len(features))
    """
    tracer = get_tracer()

    if tracer is None:
        # Tracing not initialized, yield a no-op span
        yield None
        return

    with tracer.start_as_current_span(name) as span:
        try:
            # Add trace_id attribute if provided
            if trace_id:
                span.set_attribute("trace_id", trace_id)

            # Add custom attributes
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, value)

            yield span

            # Mark span as successful
            span.set_status(Status(StatusCode.OK))

        except Exception as e:
            # Record exception in span
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            raise


def trace_function(name: str | None = None):
    """
    Decorator for tracing function execution.

    Args:
        name: Optional custom name for the span (defaults to function name)

    Example:
        @trace_function("predict_batch")
        def predict(features):
            return model.predict(features)
    """

    def decorator(func):
        span_name = name or func.__name__

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            with trace_span(span_name):
                return func(*args, **kwargs)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with trace_span(span_name):
                return await func(*args, **kwargs)

        # Return appropriate wrapper based on function type
        if hasattr(func, "__await__"):
            return async_wrapper
        return sync_wrapper

    return decorator


def add_span_attributes(span: Span | None, attributes: dict[str, Any]) -> None:
    """
    Add attributes to the current span.

    Args:
        span: Span object (can be None if tracing is disabled)
        attributes: Dictionary of attributes to add
    """
    if span is None:
        return

    for key, value in attributes.items():
        try:
            span.set_attribute(key, value)
        except Exception as e:
            logger.warning(f"Failed to set span attribute {key}: {e}")


def add_span_event(
    span: Span | None,
    name: str,
    attributes: dict[str, Any] | None = None,
) -> None:
    """
    Add an event to the current span.

    Args:
        span: Span object (can be None if tracing is disabled)
        name: Name of the event
        attributes: Optional attributes for the event
    """
    if span is None:
        return

    try:
        span.add_event(name, attributes=attributes or {})
    except Exception as e:
        logger.warning(f"Failed to add span event {name}: {e}")


def record_span_exception(span: Span | None, exception: Exception) -> None:
    """
    Record an exception in the current span.

    Args:
        span: Span object (can be None if tracing is disabled)
        exception: Exception to record
    """
    if span is None:
        return

    try:
        span.record_exception(exception)
        span.set_status(Status(StatusCode.ERROR, str(exception)))
    except Exception as e:
        logger.warning(f"Failed to record span exception: {e}")


class TracingContext:
    """
    Context manager for managing trace IDs across operations.

    Provides a convenient way to propagate trace IDs through the call stack.
    """

    def __init__(self, trace_id: str | None = None):
        """
        Initialize tracing context.

        Args:
            trace_id: Optional trace ID (generates new one if not provided)
        """
        self.trace_id = trace_id or generate_trace_id()
        self._span: Span | None = None

    def __enter__(self):
        """Enter the tracing context."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the tracing context."""
        pass

    def start_span(
        self,
        name: str,
        attributes: dict[str, Any] | None = None,
    ) -> Span | None:
        """
        Start a new span within this context.

        Args:
            name: Name of the span
            attributes: Optional attributes for the span

        Returns:
            Span object or None if tracing is disabled
        """
        tracer = get_tracer()
        if tracer is None:
            return None

        span = tracer.start_span(name)
        span.set_attribute("trace_id", self.trace_id)

        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)

        self._span = span
        return span

    def end_span(self) -> None:
        """End the current span."""
        if self._span is not None:
            self._span.end()
            self._span = None

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        """
        Add an event to the current span.

        Args:
            name: Name of the event
            attributes: Optional attributes for the event
        """
        add_span_event(self._span, name, attributes)

    def record_exception(self, exception: Exception) -> None:
        """
        Record an exception in the current span.

        Args:
            exception: Exception to record
        """
        record_span_exception(self._span, exception)
