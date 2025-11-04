"""Distributed tracing utilities."""

import contextvars
import uuid
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Context variable for trace ID
_trace_id_context: contextvars.ContextVar[str] = contextvars.ContextVar(
    "trace_id", default=""
)


def generate_trace_id() -> str:
    """Generate a new trace ID (UUIDv4)."""
    return str(uuid.uuid4())


def get_trace_id() -> str:
    """
    Get the current trace ID from context.

    Returns:
        Trace ID string, or empty string if not set
    """
    trace_id = _trace_id_context.get()
    if not trace_id:
        trace_id = generate_trace_id()
        set_trace_id(trace_id)
    return trace_id


def set_trace_id(trace_id: str) -> None:
    """
    Set the trace ID in context.

    Args:
        trace_id: Trace ID to set
    """
    _trace_id_context.set(trace_id)


def get_or_create_trace_id(
    incoming_trace_id: Optional[str] = None,
) -> str:
    """
    Get existing trace ID or create a new one.

    Args:
        incoming_trace_id: Optional trace ID from upstream service

    Returns:
        Trace ID string
    """
    if incoming_trace_id:
        set_trace_id(incoming_trace_id)
        return incoming_trace_id

    return get_trace_id()


def create_trace_context(trace_id: Optional[str] = None) -> dict:
    """
    Create a trace context dictionary for logging.

    Args:
        trace_id: Optional trace ID (uses current if not provided)

    Returns:
        Dictionary with trace context
    """
    if not trace_id:
        trace_id = get_trace_id()

    return {"trace_id": trace_id}

