"""OpenTelemetry tracing for distributed tracing."""

import logging
from typing import Optional
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

logger = logging.getLogger(__name__)


class TracingConfig:
    """Configuration for OpenTelemetry tracing."""

    def __init__(
        self,
        service_name: str = "clustering-service",
        jaeger_host: str = "localhost",
        jaeger_port: int = 6831,
        jaeger_agent_port: int = 6831,
        enabled: bool = True,
    ):
        """
        Initialize tracing configuration.

        Args:
            service_name: Service name for tracing
            jaeger_host: Jaeger agent host
            jaeger_port: Jaeger agent port
            jaeger_agent_port: Jaeger agent port
            enabled: Whether tracing is enabled
        """
        self.service_name = service_name
        self.jaeger_host = jaeger_host
        self.jaeger_port = jaeger_port
        self.jaeger_agent_port = jaeger_agent_port
        self.enabled = enabled


class TracingManager:
    """Manages OpenTelemetry tracing."""

    def __init__(self, config: Optional[TracingConfig] = None):
        """
        Initialize tracing manager.

        Args:
            config: Tracing configuration
        """
        self.config = config or TracingConfig()
        self.tracer_provider = None
        self.tracer = None
        logger.info(f"Initialized TracingManager: {self.config.service_name}")

    def initialize(self):
        """Initialize OpenTelemetry tracing."""
        if not self.config.enabled:
            logger.info("Tracing is disabled")
            return

        try:
            # Create Jaeger exporter
            jaeger_exporter = JaegerExporter(
                agent_host_name=self.config.jaeger_host,
                agent_port=self.config.jaeger_agent_port,
            )

            # Create tracer provider
            self.tracer_provider = TracerProvider(
                resource=Resource.create({SERVICE_NAME: self.config.service_name})
            )

            # Add Jaeger exporter
            self.tracer_provider.add_span_processor(
                BatchSpanProcessor(jaeger_exporter)
            )

            # Set global tracer provider
            trace.set_tracer_provider(self.tracer_provider)

            # Get tracer
            self.tracer = trace.get_tracer(__name__)

            # Instrument libraries
            SQLAlchemyInstrumentor().instrument()
            RequestsInstrumentor().instrument()

            logger.info(
                f"Tracing initialized: {self.config.service_name} -> "
                f"{self.config.jaeger_host}:{self.config.jaeger_agent_port}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize tracing: {e}", exc_info=True)
            self.config.enabled = False

    def get_tracer(self):
        """
        Get tracer instance.

        Returns:
            Tracer instance
        """
        if not self.config.enabled or not self.tracer:
            return NoOpTracer()
        return self.tracer

    def create_span(self, name: str, attributes: dict = None):
        """
        Create a span.

        Args:
            name: Span name
            attributes: Span attributes

        Returns:
            Span context manager
        """
        if not self.config.enabled or not self.tracer:
            return NoOpSpan()

        span = self.tracer.start_as_current_span(name)
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        return span

    def shutdown(self):
        """Shutdown tracing."""
        if self.tracer_provider:
            self.tracer_provider.force_flush()
            logger.info("Tracing shutdown complete")


class NoOpTracer:
    """No-op tracer for when tracing is disabled."""

    def start_as_current_span(self, name: str):
        """Return no-op span."""
        return NoOpSpan()


class NoOpSpan:
    """No-op span for when tracing is disabled."""

    def __enter__(self):
        """Enter context."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context."""
        pass

    def set_attribute(self, key: str, value):
        """Set attribute (no-op)."""
        pass

    def add_event(self, name: str, attributes: dict = None):
        """Add event (no-op)."""
        pass

    def record_exception(self, exception: Exception):
        """Record exception (no-op)."""
        pass


def create_tracing_manager(
    service_name: str = "clustering-service",
    jaeger_host: str = "localhost",
    jaeger_port: int = 6831,
    enabled: bool = True,
) -> TracingManager:
    """
    Create and initialize tracing manager.

    Args:
        service_name: Service name
        jaeger_host: Jaeger host
        jaeger_port: Jaeger port
        enabled: Whether tracing is enabled

    Returns:
        Initialized TracingManager
    """
    config = TracingConfig(
        service_name=service_name,
        jaeger_host=jaeger_host,
        jaeger_agent_port=jaeger_port,
        enabled=enabled,
    )
    manager = TracingManager(config)
    manager.initialize()
    return manager

