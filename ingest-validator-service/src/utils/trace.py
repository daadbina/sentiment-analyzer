"""Distributed tracing utilities."""

import uuid
import contextvars
from datetime import datetime

# Context variables for trace propagation
trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "trace_id", default=""
)
span_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("span_id", default="")
job_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("job_id", default="")


def generate_trace_id() -> str:
    """Generate a new trace ID (ULID format)."""
    return str(uuid.uuid4())


def generate_span_id() -> str:
    """Generate a new span ID."""
    return str(uuid.uuid4())


def generate_job_id() -> str:
    """Generate a new job ID."""
    return f"job_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"


def set_trace_id(trace_id: str) -> None:
    """Set trace ID in context."""
    trace_id_var.set(trace_id)


def get_trace_id() -> str:
    """Get current trace ID from context."""
    trace_id = trace_id_var.get()
    if not trace_id:
        trace_id = generate_trace_id()
        set_trace_id(trace_id)
    return trace_id


def set_span_id(span_id: str) -> None:
    """Set span ID in context."""
    span_id_var.set(span_id)


def get_span_id() -> str:
    """Get current span ID from context."""
    span_id = span_id_var.get()
    if not span_id:
        span_id = generate_span_id()
        set_span_id(span_id)
    return span_id


def set_job_id(job_id: str) -> None:
    """Set job ID in context."""
    job_id_var.set(job_id)


def get_job_id() -> str:
    """Get current job ID from context."""
    job_id = job_id_var.get()
    if not job_id:
        job_id = generate_job_id()
        set_job_id(job_id)
    return job_id


def get_trace_context() -> dict:
    """Get complete trace context."""
    return {
        "trace_id": get_trace_id(),
        "span_id": get_span_id(),
        "job_id": get_job_id(),
    }


def reset_trace_context() -> None:
    """Reset all trace context variables."""
    trace_id_var.set("")
    span_id_var.set("")
    job_id_var.set("")
