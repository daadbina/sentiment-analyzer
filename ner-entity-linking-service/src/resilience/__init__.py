"""Resilience patterns for NER Entity Linking Service."""

from src.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerRegistry,
    CircuitState,
    get_circuit_breaker,
    get_registry,
)
from src.resilience.retry_policy import (
    RetryPolicy,
    RetryPolicyRegistry,
    BackoffStrategy,
    get_retry_policy,
)

__all__ = [
    "CircuitBreaker",
    "CircuitBreakerRegistry",
    "CircuitState",
    "get_circuit_breaker",
    "get_registry",
    "RetryPolicy",
    "RetryPolicyRegistry",
    "BackoffStrategy",
    "get_retry_policy",
]

