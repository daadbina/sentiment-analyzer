"""Utility modules for trainer service."""

from .trace import (
    TracingConfig,
    initialize_tracing,
    get_tracer,
    get_current_span,
    set_span_attribute,
    add_span_event,
    shutdown_tracing,
)
from .checksum import (
    compute_file_checksum,
    compute_model_checksum,
    compute_data_checksum,
    compute_array_checksum,
    validate_file_checksum,
    validate_model_checksum,
    validate_data_checksum,
    generate_model_metadata,
)

__all__ = [
    "TracingConfig",
    "initialize_tracing",
    "get_tracer",
    "get_current_span",
    "set_span_attribute",
    "add_span_event",
    "shutdown_tracing",
    "compute_file_checksum",
    "compute_model_checksum",
    "compute_data_checksum",
    "compute_array_checksum",
    "validate_file_checksum",
    "validate_model_checksum",
    "validate_data_checksum",
    "generate_model_metadata",
]
