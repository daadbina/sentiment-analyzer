"""Utility modules for Predictor Online Inference Service."""

from .trace import (
    initialize_tracing,
    get_tracer,
    generate_trace_id,
    trace_span,
    trace_function,
    add_span_attributes,
    add_span_event,
    record_span_exception,
    TracingContext,
)
from .logging_config import (
    setup_logging,
    get_logger,
    ContextLogger,
)
from .ab_testing import (
    ModelVariant,
    ABTestingStrategy,
    SimpleABTestingStrategy,
    NoABTestingStrategy,
    create_ab_testing_strategy,
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

