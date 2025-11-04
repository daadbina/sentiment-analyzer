"""Metrics collection for NER Entity Linking Service."""

from src.metrics.nfr_metrics import (
    NFRMetricsCollector,
    LatencyTracker,
)

__all__ = [
    "NFRMetricsCollector",
    "LatencyTracker",
]

