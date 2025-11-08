"""Prometheus metrics for API Analytics Service.

Provides comprehensive monitoring of API performance, errors, cache, and rate limiting.
"""

from prometheus_client import Counter, Histogram, Gauge
from typing import Optional


# Request metrics
api_requests_total = Counter(
    "api_requests_total",
    "Total API requests",
    ["endpoint", "method", "status"],
)

api_request_latency_ms = Histogram(
    "api_request_latency_ms",
    "API request latency in milliseconds",
    ["endpoint", "method"],
    buckets=(10, 50, 100, 250, 500, 1000, 2500, 5000),
)

# Error metrics
api_errors_total = Counter(
    "api_errors_total",
    "Total API errors",
    ["endpoint", "error_type"],
)

# Cache metrics
api_cache_hits_total = Counter(
    "api_cache_hits_total",
    "Total cache hits",
    ["endpoint"],
)

api_cache_misses_total = Counter(
    "api_cache_misses_total",
    "Total cache misses",
    ["endpoint"],
)

api_cache_hit_rate = Gauge(
    "api_cache_hit_rate",
    "Cache hit rate",
    ["endpoint"],
)

# Rate limiting metrics
api_rate_limit_exceeded_total = Counter(
    "api_rate_limit_exceeded_total",
    "Total rate limit violations",
    ["user_id", "endpoint"],
)

# Authentication metrics
api_auth_failures_total = Counter(
    "api_auth_failures_total",
    "Total authentication failures",
    ["reason"],
)

api_auth_latency_ms = Histogram(
    "api_auth_latency_ms",
    "Authentication latency in milliseconds",
    buckets=(5, 10, 25, 50, 100),
)

# Database query metrics
api_query_latency_ms = Histogram(
    "api_query_latency_ms",
    "Database query latency in milliseconds",
    ["query_type", "database"],
    buckets=(10, 50, 100, 250, 500, 1000, 2500, 5000),
)

api_query_errors_total = Counter(
    "api_query_errors_total",
    "Total query errors",
    ["query_type", "database"],
)

# Export metrics
api_export_duration_seconds = Histogram(
    "api_export_duration_seconds",
    "Export operation duration in seconds",
    ["format"],
    buckets=(1, 5, 10, 30, 60, 120),
)

api_export_size_bytes = Gauge(
    "api_export_size_bytes",
    "Export size in bytes",
    ["format"],
)

# Connection pool metrics
api_db_connection_pool_size = Gauge(
    "api_db_connection_pool_size",
    "Database connection pool size",
    ["database"],
)

api_db_connection_pool_available = Gauge(
    "api_db_connection_pool_available",
    "Available connections in pool",
    ["database"],
)

# Active requests
api_active_requests = Gauge(
    "api_active_requests",
    "Number of active requests",
    ["endpoint"],
)


class MetricsRecorder:
    """Helper class for recording metrics."""

    @staticmethod
    def record_request(
        endpoint: str,
        method: str,
        status: int,
        latency_ms: float,
    ) -> None:
        """Record API request metrics.

        Args:
            endpoint: API endpoint
            method: HTTP method
            status: HTTP status code
            latency_ms: Request latency in milliseconds
        """
        api_requests_total.labels(
            endpoint=endpoint,
            method=method,
            status=status,
        ).inc()

        api_request_latency_ms.labels(
            endpoint=endpoint,
            method=method,
        ).observe(latency_ms)

    @staticmethod
    def record_error(
        endpoint: str,
        error_type: str,
    ) -> None:
        """Record API error.

        Args:
            endpoint: API endpoint
            error_type: Type of error
        """
        api_errors_total.labels(
            endpoint=endpoint,
            error_type=error_type,
        ).inc()

    @staticmethod
    def record_cache_hit(endpoint: str) -> None:
        """Record cache hit.

        Args:
            endpoint: API endpoint
        """
        api_cache_hits_total.labels(endpoint=endpoint).inc()

    @staticmethod
    def record_cache_miss(endpoint: str) -> None:
        """Record cache miss.

        Args:
            endpoint: API endpoint
        """
        api_cache_misses_total.labels(endpoint=endpoint).inc()

    @staticmethod
    def record_rate_limit_exceeded(
        user_id: str,
        endpoint: str,
    ) -> None:
        """Record rate limit violation.

        Args:
            user_id: User ID
            endpoint: API endpoint
        """
        api_rate_limit_exceeded_total.labels(
            user_id=user_id,
            endpoint=endpoint,
        ).inc()

    @staticmethod
    def record_auth_failure(reason: str) -> None:
        """Record authentication failure.

        Args:
            reason: Failure reason
        """
        api_auth_failures_total.labels(reason=reason).inc()

    @staticmethod
    def record_auth_latency(latency_ms: float) -> None:
        """Record authentication latency.

        Args:
            latency_ms: Latency in milliseconds
        """
        api_auth_latency_ms.observe(latency_ms)

    @staticmethod
    def record_query(
        query_type: str,
        database: str,
        latency_ms: float,
    ) -> None:
        """Record database query.

        Args:
            query_type: Type of query
            database: Database name
            latency_ms: Query latency in milliseconds
        """
        api_query_latency_ms.labels(
            query_type=query_type,
            database=database,
        ).observe(latency_ms)

    @staticmethod
    def record_query_error(
        query_type: str,
        database: str,
    ) -> None:
        """Record query error.

        Args:
            query_type: Type of query
            database: Database name
        """
        api_query_errors_total.labels(
            query_type=query_type,
            database=database,
        ).inc()

    @staticmethod
    def record_export(
        format_type: str,
        duration_seconds: float,
        size_bytes: int,
    ) -> None:
        """Record export operation.

        Args:
            format_type: Export format (csv, json)
            duration_seconds: Duration in seconds
            size_bytes: Export size in bytes
        """
        api_export_duration_seconds.labels(format=format_type).observe(
            duration_seconds
        )
        api_export_size_bytes.labels(format=format_type).set(size_bytes)

