"""Tests for distributed tracing utilities."""

import pytest
import uuid
from src.utils.trace import (
    generate_trace_id,
    generate_span_id,
    generate_job_id,
    set_trace_id,
    get_trace_id,
    set_span_id,
    get_span_id,
    set_job_id,
    get_job_id,
    get_trace_context,
    reset_trace_context,
)


class TestTraceGeneration:
    """Test trace ID generation."""

    def test_generate_trace_id(self):
        """Test generating trace ID."""
        trace_id = generate_trace_id()

        assert trace_id is not None
        assert isinstance(trace_id, str)
        assert len(trace_id) > 0
        # Should be valid UUID format
        try:
            uuid.UUID(trace_id)
        except ValueError:
            pytest.fail("Generated trace ID is not a valid UUID")

    def test_generate_trace_id_unique(self):
        """Test that generated trace IDs are unique."""
        trace_id1 = generate_trace_id()
        trace_id2 = generate_trace_id()

        assert trace_id1 != trace_id2

    def test_generate_span_id(self):
        """Test generating span ID."""
        span_id = generate_span_id()

        assert span_id is not None
        assert isinstance(span_id, str)
        assert len(span_id) > 0
        # Should be valid UUID format
        try:
            uuid.UUID(span_id)
        except ValueError:
            pytest.fail("Generated span ID is not a valid UUID")

    def test_generate_span_id_unique(self):
        """Test that generated span IDs are unique."""
        span_id1 = generate_span_id()
        span_id2 = generate_span_id()

        assert span_id1 != span_id2

    def test_generate_job_id(self):
        """Test generating job ID."""
        job_id = generate_job_id()

        assert job_id is not None
        assert isinstance(job_id, str)
        assert job_id.startswith("job_")
        # Should contain timestamp and hex
        parts = job_id.split("_")
        assert len(parts) >= 3

    def test_generate_job_id_unique(self):
        """Test that generated job IDs are unique."""
        job_id1 = generate_job_id()
        job_id2 = generate_job_id()

        assert job_id1 != job_id2

    def test_generate_job_id_format(self):
        """Test job ID format."""
        job_id = generate_job_id()

        # Format: job_YYYYMMDD_HHMMSS_hex
        assert job_id.startswith("job_")
        parts = job_id.split("_")
        assert len(parts) == 4
        assert len(parts[1]) == 8  # YYYYMMDD
        assert len(parts[2]) == 6  # HHMMSS
        assert len(parts[3]) == 8  # hex


class TestTraceContextManagement:
    """Test trace context management."""

    def setup_method(self):
        """Reset trace context before each test."""
        reset_trace_context()

    def test_set_and_get_trace_id(self):
        """Test setting and getting trace ID."""
        test_trace_id = "test_trace_123"
        set_trace_id(test_trace_id)

        result = get_trace_id()

        assert result == test_trace_id

    def test_get_trace_id_auto_generate(self):
        """Test that trace ID is auto-generated if not set."""
        reset_trace_context()

        trace_id = get_trace_id()

        assert trace_id is not None
        assert isinstance(trace_id, str)
        assert len(trace_id) > 0

    def test_get_trace_id_consistent(self):
        """Test that trace ID is consistent across calls."""
        trace_id1 = get_trace_id()
        trace_id2 = get_trace_id()

        assert trace_id1 == trace_id2

    def test_set_and_get_span_id(self):
        """Test setting and getting span ID."""
        test_span_id = "test_span_123"
        set_span_id(test_span_id)

        result = get_span_id()

        assert result == test_span_id

    def test_get_span_id_auto_generate(self):
        """Test that span ID is auto-generated if not set."""
        reset_trace_context()

        span_id = get_span_id()

        assert span_id is not None
        assert isinstance(span_id, str)
        assert len(span_id) > 0

    def test_get_span_id_consistent(self):
        """Test that span ID is consistent across calls."""
        span_id1 = get_span_id()
        span_id2 = get_span_id()

        assert span_id1 == span_id2

    def test_set_and_get_job_id(self):
        """Test setting and getting job ID."""
        test_job_id = "job_test_123"
        set_job_id(test_job_id)

        result = get_job_id()

        assert result == test_job_id

    def test_get_job_id_auto_generate(self):
        """Test that job ID is auto-generated if not set."""
        reset_trace_context()

        job_id = get_job_id()

        assert job_id is not None
        assert isinstance(job_id, str)
        assert job_id.startswith("job_")

    def test_get_job_id_consistent(self):
        """Test that job ID is consistent across calls."""
        job_id1 = get_job_id()
        job_id2 = get_job_id()

        assert job_id1 == job_id2


class TestTraceContext:
    """Test trace context operations."""

    def setup_method(self):
        """Reset trace context before each test."""
        reset_trace_context()

    def test_get_trace_context(self):
        """Test getting complete trace context."""
        context = get_trace_context()

        assert isinstance(context, dict)
        assert "trace_id" in context
        assert "span_id" in context
        assert "job_id" in context

    def test_get_trace_context_values(self):
        """Test trace context contains valid values."""
        context = get_trace_context()

        assert context["trace_id"] is not None
        assert context["span_id"] is not None
        assert context["job_id"] is not None
        assert len(context["trace_id"]) > 0
        assert len(context["span_id"]) > 0
        assert len(context["job_id"]) > 0

    def test_get_trace_context_consistent(self):
        """Test that trace context is consistent."""
        context1 = get_trace_context()
        context2 = get_trace_context()

        assert context1 == context2

    def test_get_trace_context_with_set_values(self):
        """Test trace context with manually set values."""
        set_trace_id("trace_123")
        set_span_id("span_456")
        set_job_id("job_789")

        context = get_trace_context()

        assert context["trace_id"] == "trace_123"
        assert context["span_id"] == "span_456"
        assert context["job_id"] == "job_789"

    def test_reset_trace_context(self):
        """Test resetting trace context."""
        # Set some values
        set_trace_id("trace_123")
        set_span_id("span_456")
        set_job_id("job_789")

        # Reset
        reset_trace_context()

        # Get new values (should be auto-generated)
        trace_id = get_trace_id()
        span_id = get_span_id()
        job_id = get_job_id()

        assert trace_id != "trace_123"
        assert span_id != "span_456"
        assert job_id != "job_789"

    def test_reset_trace_context_multiple_times(self):
        """Test resetting trace context multiple times."""
        for _ in range(3):
            reset_trace_context()
            context = get_trace_context()
            assert context["trace_id"] is not None
            assert context["span_id"] is not None
            assert context["job_id"] is not None

    def test_trace_context_isolation(self):
        """Test that trace context is isolated between resets."""
        set_trace_id("trace_1")
        context1 = get_trace_context()

        reset_trace_context()

        set_trace_id("trace_2")
        context2 = get_trace_context()

        assert context1["trace_id"] == "trace_1"
        assert context2["trace_id"] == "trace_2"
        assert context1["trace_id"] != context2["trace_id"]

    def test_trace_id_persistence(self):
        """Test that trace ID persists across multiple calls."""
        trace_id = get_trace_id()

        # Call multiple times
        for _ in range(5):
            assert get_trace_id() == trace_id

    def test_span_id_persistence(self):
        """Test that span ID persists across multiple calls."""
        span_id = get_span_id()

        # Call multiple times
        for _ in range(5):
            assert get_span_id() == span_id

    def test_job_id_persistence(self):
        """Test that job ID persists across multiple calls."""
        job_id = get_job_id()

        # Call multiple times
        for _ in range(5):
            assert get_job_id() == job_id

    def test_trace_context_all_fields_present(self):
        """Test that all fields are present in trace context."""
        context = get_trace_context()

        required_fields = ["trace_id", "span_id", "job_id"]
        for field in required_fields:
            assert field in context
            assert context[field] is not None
            assert isinstance(context[field], str)

    def test_trace_context_no_empty_values(self):
        """Test that trace context has no empty values."""
        context = get_trace_context()

        for key, value in context.items():
            assert value != ""
            assert len(value) > 0

    def test_multiple_trace_contexts(self):
        """Test creating multiple trace contexts."""
        reset_trace_context()
        context1 = get_trace_context()

        reset_trace_context()
        context2 = get_trace_context()

        # Contexts should be different after reset
        assert context1["trace_id"] != context2["trace_id"]
        assert context1["span_id"] != context2["span_id"]
        assert context1["job_id"] != context2["job_id"]

