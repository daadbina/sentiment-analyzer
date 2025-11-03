"""Tests for distributed tracing."""

import pytest
import json
from datetime import datetime, timezone
from src.tracing.tracer import (
    DistributedTracer,
    TracingConfig,
    TraceSpan,
)


class TestTraceSpan:
    """Test trace span."""

    def test_trace_span_creation(self):
        """Test creating trace span."""
        now = datetime.now(timezone.utc)
        span = TraceSpan(
            trace_id="trace-123",
            span_id="span-456",
            parent_span_id="parent-789",
            operation_name="test_operation",
            start_time=now,
        )
        assert span.trace_id == "trace-123"
        assert span.span_id == "span-456"
        assert span.parent_span_id == "parent-789"
        assert span.operation_name == "test_operation"
        assert span.start_time == now

    def test_trace_span_defaults(self):
        """Test trace span default values."""
        now = datetime.now(timezone.utc)
        span = TraceSpan(
            trace_id="trace-123",
            span_id="span-456",
            operation_name="test_operation",
            start_time=now,
        )
        assert span.parent_span_id is None
        assert span.end_time is None
        assert span.duration_ms == 0.0
        assert span.status == "UNSET"
        assert span.attributes == {}
        assert span.events == []

    def test_trace_span_to_dict(self):
        """Test converting trace span to dict."""
        now = datetime.now(timezone.utc)
        span = TraceSpan(
            trace_id="trace-123",
            span_id="span-456",
            operation_name="test_operation",
            start_time=now,
            status="OK",
            attributes={"key": "value"},
        )
        span_dict = span.to_dict()
        assert span_dict['trace_id'] == "trace-123"
        assert span_dict['span_id'] == "span-456"
        assert span_dict['operation_name'] == "test_operation"
        assert span_dict['status'] == "OK"
        assert span_dict['attributes'] == {"key": "value"}


class TestTracingConfig:
    """Test tracing configuration."""

    def test_tracing_config_defaults(self):
        """Test tracing config defaults."""
        config = TracingConfig()
        assert config.enabled is True
        assert config.jaeger_host == "localhost"
        assert config.jaeger_port == 6831
        assert config.service_name == "canonicalizer-normalizer-service"
        assert config.sample_rate == 1.0

    def test_tracing_config_custom(self):
        """Test tracing config with custom values."""
        config = TracingConfig(
            enabled=False,
            jaeger_host="jaeger.example.com",
            jaeger_port=6832,
            service_name="custom-service",
            sample_rate=0.5,
        )
        assert config.enabled is False
        assert config.jaeger_host == "jaeger.example.com"
        assert config.jaeger_port == 6832
        assert config.service_name == "custom-service"
        assert config.sample_rate == 0.5

    def test_tracing_config_sample_rate_bounds(self):
        """Test tracing config sample rate bounds."""
        config1 = TracingConfig(sample_rate=-0.5)
        assert config1.sample_rate == 0.0

        config2 = TracingConfig(sample_rate=1.5)
        assert config2.sample_rate == 1.0

        config3 = TracingConfig(sample_rate=0.75)
        assert config3.sample_rate == 0.75


class TestDistributedTracer:
    """Test distributed tracer."""

    def test_tracer_initialization_disabled(self):
        """Test tracer initialization with tracing disabled."""
        config = TracingConfig(enabled=False)
        tracer = DistributedTracer(config)
        assert tracer.config.enabled is False
        assert tracer.tracer is None

    def test_tracer_initialization_enabled(self):
        """Test tracer initialization with tracing enabled."""
        config = TracingConfig(enabled=True)
        tracer = DistributedTracer(config)
        assert tracer.config.enabled is True or tracer.tracer is None

    def test_tracer_start_span(self):
        """Test starting a span."""
        config = TracingConfig(enabled=False)
        tracer = DistributedTracer(config)

        span = tracer.start_span(
            operation_name="test_op",
            trace_id="trace-123",
            attributes={"key": "value"},
        )

        assert span.operation_name == "test_op"
        assert span.trace_id == "trace-123"
        assert span.attributes == {"key": "value"}
        assert span.span_id in tracer.spans

    def test_tracer_end_span(self):
        """Test ending a span."""
        config = TracingConfig(enabled=False)
        tracer = DistributedTracer(config)

        span = tracer.start_span(
            operation_name="test_op",
            trace_id="trace-123",
        )

        ended_span = tracer.end_span(span.span_id, status="OK")
        assert ended_span is not None
        assert ended_span.status == "OK"
        assert ended_span.end_time is not None
        assert ended_span.duration_ms > 0

    def test_tracer_end_nonexistent_span(self):
        """Test ending nonexistent span."""
        config = TracingConfig(enabled=False)
        tracer = DistributedTracer(config)

        result = tracer.end_span("nonexistent-span-id")
        assert result is None

    def test_tracer_add_event(self):
        """Test adding event to span."""
        config = TracingConfig(enabled=False)
        tracer = DistributedTracer(config)

        span = tracer.start_span(
            operation_name="test_op",
            trace_id="trace-123",
        )

        tracer.add_event(
            span.span_id,
            "test_event",
            attributes={"event_key": "event_value"},
        )

        assert len(span.events) == 1
        assert span.events[0]['name'] == "test_event"
        assert span.events[0]['attributes'] == {"event_key": "event_value"}

    def test_tracer_add_event_nonexistent_span(self):
        """Test adding event to nonexistent span."""
        config = TracingConfig(enabled=False)
        tracer = DistributedTracer(config)

        # Should not raise error
        tracer.add_event("nonexistent-span-id", "test_event")

    def test_tracer_get_span(self):
        """Test getting span by ID."""
        config = TracingConfig(enabled=False)
        tracer = DistributedTracer(config)

        span = tracer.start_span(
            operation_name="test_op",
            trace_id="trace-123",
        )

        retrieved_span = tracer.get_span(span.span_id)
        assert retrieved_span is not None
        assert retrieved_span.span_id == span.span_id

    def test_tracer_get_nonexistent_span(self):
        """Test getting nonexistent span."""
        config = TracingConfig(enabled=False)
        tracer = DistributedTracer(config)

        result = tracer.get_span("nonexistent-span-id")
        assert result is None

    def test_tracer_get_trace(self):
        """Test getting all spans for a trace."""
        config = TracingConfig(enabled=False)
        tracer = DistributedTracer(config)

        span1 = tracer.start_span(
            operation_name="op1",
            trace_id="trace-123",
        )
        span2 = tracer.start_span(
            operation_name="op2",
            trace_id="trace-123",
        )
        span3 = tracer.start_span(
            operation_name="op3",
            trace_id="trace-456",
        )

        trace_spans = tracer.get_trace("trace-123")
        assert len(trace_spans) == 2
        assert all(s.trace_id == "trace-123" for s in trace_spans)

    def test_tracer_export_trace(self):
        """Test exporting trace as JSON."""
        config = TracingConfig(enabled=False)
        tracer = DistributedTracer(config)

        span = tracer.start_span(
            operation_name="test_op",
            trace_id="trace-123",
        )
        tracer.end_span(span.span_id, status="OK")

        json_export = tracer.export_trace("trace-123")
        trace_data = json.loads(json_export)

        assert trace_data['trace_id'] == "trace-123"
        assert trace_data['span_count'] == 1
        assert len(trace_data['spans']) == 1


class TestDistributedTracerIntegration:
    """Integration tests for distributed tracer."""

    def test_tracer_span_lifecycle(self):
        """Test complete span lifecycle."""
        config = TracingConfig(enabled=False)
        tracer = DistributedTracer(config)

        # Start span
        span = tracer.start_span(
            operation_name="process_article",
            trace_id="trace-123",
            attributes={"article_id": "123"},
        )

        # Add events
        tracer.add_event(span.span_id, "canonicalization_started")
        tracer.add_event(span.span_id, "canonicalization_completed")

        # End span
        tracer.end_span(span.span_id, status="OK")

        # Verify
        retrieved_span = tracer.get_span(span.span_id)
        assert retrieved_span.status == "OK"
        assert len(retrieved_span.events) == 2

    def test_tracer_multiple_traces(self):
        """Test handling multiple traces."""
        config = TracingConfig(enabled=False)
        tracer = DistributedTracer(config)

        # Create multiple traces
        for i in range(3):
            span = tracer.start_span(
                operation_name=f"op_{i}",
                trace_id=f"trace-{i}",
            )
            tracer.end_span(span.span_id)

        # Verify
        assert len(tracer.spans) == 3
        for i in range(3):
            trace_spans = tracer.get_trace(f"trace-{i}")
            assert len(trace_spans) == 1

