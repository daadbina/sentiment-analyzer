"""Utility modules for Predictor Online Inference Service."""

from .ab_testing import (
    ABTestingStrategy,
    ModelVariant,
    NoABTestingStrategy,
    SimpleABTestingStrategy,
    create_ab_testing_strategy,
)
from .logging_config import (
    ContextLogger,
    get_logger,
    setup_logging,
)
from .trace import (
    TracingContext,
    add_span_attributes,
    add_span_event,
    generate_trace_id,
    get_tracer,
    initialize_tracing,
    record_span_exception,
    trace_function,
    trace_span,
)

__all__ = [
    # Tracing
    "initialize_tracing",
    "get_tracer",
    "generate_trace_id",
    "trace_span",
    "trace_function",
    "add_span_attributes",
    "add_span_event",
    "record_span_exception",
    "TracingContext",
    # Logging
    "setup_logging",
    "get_logger",
    "ContextLogger",
    # A/B Testing
    "ModelVariant",
    "ABTestingStrategy",
    "SimpleABTestingStrategy",
    "NoABTestingStrategy",
    "create_ab_testing_strategy",
]

