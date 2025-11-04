"""Metrics collection for NER Entity Linking Service."""

from src.metrics.nfr_metrics import (
    NFRMetricsCollector,
    LatencyTracker,
)

# Alias for backward compatibility
MetricsCollector = NFRMetricsCollector

__all__ = [
    "NFRMetricsCollector",
    "MetricsCollector",
    "LatencyTracker",
]

