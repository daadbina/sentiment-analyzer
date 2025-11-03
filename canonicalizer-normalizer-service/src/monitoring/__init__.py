"""Monitoring and observability module."""

from .structured_logger import StructuredLogger, PerformanceLogger, correlation_id_var
from .metrics_collector import (
    MetricsCollector,
    MetricValue,
    MetricStats,
    DomainMetrics,
    DeduplicationMetrics,
    NormalizationMetrics,
    CacheMetrics,
)

__all__ = [
    'StructuredLogger',
    'PerformanceLogger',
    'correlation_id_var',
    'MetricsCollector',
    'MetricValue',
    'MetricStats',
    'DomainMetrics',
    'DeduplicationMetrics',
    'NormalizationMetrics',
    'CacheMetrics',
]

