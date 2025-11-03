"""Distributed tracing with OpenTelemetry."""

import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timezone
import json

logger = logging.getLogger(__name__)


@dataclass
class TraceSpan:
    """Trace span information."""

    trace_id: str
    span_id: str
    operation_name: str
    start_time: datetime
    parent_span_id: Optional[str] = None
    end_time: Optional[datetime] = None
    duration_ms: float = 0.0
    status: str = "UNSET"
    attributes: Dict[str, Any] = None
    events: list = None

    def __post_init__(self):
        """Initialize defaults."""
        if self.attributes is None:
            self.attributes = {}
        if self.events is None:
            self.events = []

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'trace_id': self.trace_id,
            'span_id': self.span_id,
            'parent_span_id': self.parent_span_id,
            'operation_name': self.operation_name,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_ms': self.duration_ms,
            'status': self.status,
            'attributes': self.attributes,
            'events': self.events,
        }


class TracingConfig:
    """Tracing configuration."""

    def __init__(
        self,
        enabled: bool = True,
        jaeger_host: str = "localhost",
        jaeger_port: int = 6831,
        service_name: str = "canonicalizer-normalizer-service",
        sample_rate: float = 1.0,
    ):
        """Initialize tracing config.

        Args:
            enabled: Enable tracing
            jaeger_host: Jaeger agent host
            jaeger_port: Jaeger agent port
            service_name: Service name for tracing
            sample_rate: Sampling rate (0.0-1.0)
        """
        self.enabled = enabled
        self.jaeger_host = jaeger_host
        self.jaeger_port = jaeger_port
        self.service_name = service_name
        self.sample_rate = max(0.0, min(1.0, sample_rate))


class DistributedTracer:
    """Distributed tracing with OpenTelemetry."""

    def __init__(self, config: TracingConfig):
        """Initialize distributed tracer.

        Args:
            config: Tracing configuration
        """
        self.config = config
        self.tracer = None
        self.spans: Dict[str, TraceSpan] = {}
        self._initialize_tracer()

    def _initialize_tracer(self) -> None:
        """Initialize tracer."""
        if not self.config.enabled:
            logger.info("Distributed tracing disabled")
            return

        try:
            from opentelemetry import trace
            from opentelemetry.exporter.jaeger.thrift import JaegerExporter
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            jaeger_exporter = JaegerExporter(
                agent_host_name=self.config.jaeger_host,
                agent_port=self.config.jaeger_port,
            )

            trace.set_tracer_provider(TracerProvider())
            trace.get_tracer_provider().add_span_processor(
                BatchSpanProcessor(jaeger_exporter)
            )

            self.tracer = trace.get_tracer(__name__)
            logger.info(
                f"Distributed tracing initialized: "
                f"jaeger://{self.config.jaeger_host}:{self.config.jaeger_port}"
            )
        except ImportError:
            logger.warning("OpenTelemetry libraries not available, tracing disabled")
            self.config.enabled = False
        except Exception as e:
            logger.error(f"Error initializing tracer: {e}")
            self.config.enabled = False

    def start_span(
        self,
        operation_name: str,
        trace_id: str,
        parent_span_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> TraceSpan:
        """Start a trace span.

        Args:
            operation_name: Operation name
            trace_id: Trace ID
            parent_span_id: Parent span ID
            attributes: Span attributes

        Returns:
            Trace span
        """
        import uuid

        span_id = str(uuid.uuid4())
        span = TraceSpan(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            start_time=datetime.now(timezone.utc),
            attributes=attributes or {},
        )

        self.spans[span_id] = span

        if self.tracer:
            try:
                with self.tracer.start_as_current_span(operation_name) as otel_span:
                    if attributes:
                        for key, value in attributes.items():
                            otel_span.set_attribute(key, value)
            except Exception as e:
                logger.warning(f"Error recording span: {e}")

        return span

    def end_span(
        self,
        span_id: str,
        status: str = "OK",
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Optional[TraceSpan]:
        """End a trace span.

        Args:
            span_id: Span ID
            status: Span status
            attributes: Additional attributes

        Returns:
            Completed trace span
        """
        if span_id not in self.spans:
            return None

        span = self.spans[span_id]
        span.end_time = datetime.now(timezone.utc)
        span.status = status
        span.duration_ms = (span.end_time - span.start_time).total_seconds() * 1000

        if attributes:
            span.attributes.update(attributes)

        return span

    def add_event(
        self,
        span_id: str,
        event_name: str,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add event to span.

        Args:
            span_id: Span ID
            event_name: Event name
            attributes: Event attributes
        """
        if span_id not in self.spans:
            return

        span = self.spans[span_id]
        event = {
            'name': event_name,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'attributes': attributes or {},
        }
        span.events.append(event)

    def get_span(self, span_id: str) -> Optional[TraceSpan]:
        """Get span by ID.

        Args:
            span_id: Span ID

        Returns:
            Trace span or None
        """
        return self.spans.get(span_id)

    def get_trace(self, trace_id: str) -> list:
        """Get all spans for a trace.

        Args:
            trace_id: Trace ID

        Returns:
            List of trace spans
        """
        return [span for span in self.spans.values() if span.trace_id == trace_id]

    def export_trace(self, trace_id: str) -> str:
        """Export trace as JSON.

        Args:
            trace_id: Trace ID

        Returns:
            JSON representation of trace
        """
        spans = self.get_trace(trace_id)
        trace_data = {
            'trace_id': trace_id,
            'spans': [span.to_dict() for span in spans],
            'span_count': len(spans),
        }
        return json.dumps(trace_data, indent=2)

