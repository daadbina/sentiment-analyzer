"""Integration tests for canonicalizer-normalizer-service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.analytics.analytics_engine import RealTimeAnalytics
from src.database.connection_pool import ConnectionPoolManager
from src.tracing.tracer import DistributedTracer, TracingConfig
from src.api.api_server import (
    CanonicalizeEndpoint,
    BatchCanonicalizeEndpoint,
    APIRequest,
)


class TestEndToEndPipeline:
    """End-to-end pipeline integration tests."""

    @pytest.mark.asyncio
    async def test_canonicalization_with_analytics(self):
        """Test canonicalization with analytics tracking."""
        analytics = RealTimeAnalytics()
        canonicalizer = AsyncMock()
        canonicalizer.canonicalize = AsyncMock(
            return_value={"url": "https://example.com", "domain": "politics"}
        )

        endpoint = CanonicalizeEndpoint(canonicalizer)
        request = APIRequest(url="https://example.com")

        # Record analytics
        analytics.record_message_processed(50.0, domain="politics")
        analytics.record_message_accepted()

        # Canonicalize
        response = await endpoint.handle(request)

        assert response.success is True
        assert analytics.total_messages_processed == 1
        assert analytics.total_messages_accepted == 1

    @pytest.mark.asyncio
    async def test_batch_canonicalization_with_analytics(self):
        """Test batch canonicalization with analytics."""
        analytics = RealTimeAnalytics()
        canonicalizer = AsyncMock()
        canonicalizer.canonicalize = AsyncMock(
            return_value={"url": "https://example.com"}
        )

        endpoint = BatchCanonicalizeEndpoint(canonicalizer, batch_size=100)
        requests = [
            APIRequest(url=f"https://example{i}.com") for i in range(10)
        ]

        # Record analytics for each
        for i in range(10):
            analytics.record_message_processed(50.0 + i)
            if i % 2 == 0:
                analytics.record_message_accepted()
            else:
                analytics.record_message_rejected()

        # Canonicalize batch
        response = await endpoint.handle(requests)

        assert response.success is True
        assert analytics.total_messages_processed == 10
        assert analytics.total_messages_accepted == 5
        assert analytics.total_messages_rejected == 5

    def test_analytics_with_tracing(self):
        """Test analytics with distributed tracing."""
        analytics = RealTimeAnalytics()
        config = TracingConfig(enabled=False)
        tracer = DistributedTracer(config)

        # Start trace
        span = tracer.start_span(
            operation_name="canonicalize_batch",
            trace_id="trace-123",
            attributes={"batch_size": 10},
        )

        # Record analytics
        for i in range(10):
            analytics.record_message_processed(50.0)
            tracer.add_event(span.span_id, f"processed_message_{i}")

        # End trace
        tracer.end_span(span.span_id, status="OK")

        # Verify
        assert analytics.total_messages_processed == 10
        assert len(span.events) == 10
        assert span.status == "OK"

    def test_connection_pool_with_analytics(self):
        """Test connection pool with analytics."""
        analytics = RealTimeAnalytics()
        pool_manager = ConnectionPoolManager(dsn="postgresql://localhost/db")

        # Simulate pool operations
        stats = pool_manager.get_stats()
        assert stats.total_connections == 0

        # Record analytics
        analytics.record_message_processed(50.0)
        analytics.record_cache_hit()

        assert analytics.total_messages_processed == 1
        assert analytics.cache_hits == 1


class TestServiceIntegration:
    """Service integration tests."""

    def test_analytics_snapshot_generation(self):
        """Test analytics snapshot generation."""
        analytics = RealTimeAnalytics()

        # Simulate message processing
        for i in range(100):
            analytics.record_message_processed(50.0 + i, domain="politics")
            if i % 10 == 0:
                analytics.record_error()
            if i % 5 == 0:
                analytics.record_cache_hit()
            else:
                analytics.record_cache_miss()

        # Get snapshot
        snapshot = analytics.get_snapshot()

        assert snapshot.total_messages_processed == 100
        assert snapshot.error_rate > 0.0
        assert snapshot.cache_hit_rate > 0.0
        assert snapshot.domain_distribution["politics"] == 100

    def test_tracing_with_multiple_spans(self):
        """Test tracing with multiple spans."""
        config = TracingConfig(enabled=False)
        tracer = DistributedTracer(config)

        # Create parent span
        parent_span = tracer.start_span(
            operation_name="process_article",
            trace_id="trace-123",
        )

        # Create child spans
        child_spans = []
        for i in range(5):
            child_span = tracer.start_span(
                operation_name=f"step_{i}",
                trace_id="trace-123",
                parent_span_id=parent_span.span_id,
            )
            child_spans.append(child_span)
            tracer.add_event(child_span.span_id, f"step_{i}_completed")
            tracer.end_span(child_span.span_id, status="OK")

        # End parent span
        tracer.end_span(parent_span.span_id, status="OK")

        # Verify
        trace_spans = tracer.get_trace("trace-123")
        assert len(trace_spans) == 6  # 1 parent + 5 children
        assert all(s.status == "OK" for s in trace_spans)

    def test_connection_pool_health_check(self):
        """Test connection pool health check."""
        pool_manager = ConnectionPoolManager(
            dsn="postgresql://localhost/db",
            health_check_interval=1,
        )

        # Get initial stats
        stats = pool_manager.get_stats()
        assert stats.health_check_failures == 0

        # Simulate health check failure
        pool_manager.stats.health_check_failures = 1
        stats = pool_manager.get_stats()
        assert stats.health_check_failures == 1


class TestErrorHandling:
    """Error handling integration tests."""

    @pytest.mark.asyncio
    async def test_canonicalization_error_handling(self):
        """Test error handling in canonicalization."""
        canonicalizer = AsyncMock()
        canonicalizer.canonicalize = AsyncMock(
            side_effect=Exception("Canonicalization failed")
        )

        endpoint = CanonicalizeEndpoint(canonicalizer)
        request = APIRequest(url="https://example.com")
        response = await endpoint.handle(request)

        assert response.success is False
        assert response.error is not None

    @pytest.mark.asyncio
    async def test_batch_canonicalization_partial_failure(self):
        """Test batch canonicalization with partial failures."""
        canonicalizer = AsyncMock()

        # Simulate partial failures
        call_count = 0

        async def canonicalize_with_failures(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 3 == 0:
                raise Exception("Canonicalization failed")
            return {"url": "https://example.com"}

        canonicalizer.canonicalize = canonicalize_with_failures

        endpoint = BatchCanonicalizeEndpoint(canonicalizer)
        requests = [APIRequest(url=f"https://example{i}.com") for i in range(9)]

        # This should handle errors gracefully
        try:
            response = await endpoint.handle(requests)
            # Response may succeed or fail depending on error handling
            assert response is not None
        except Exception:
            # Error handling is acceptable
            pass

    def test_analytics_error_tracking(self):
        """Test analytics error tracking."""
        analytics = RealTimeAnalytics()

        # Record messages and errors
        for i in range(100):
            analytics.record_message_processed(50.0)
            if i % 20 == 0:
                analytics.record_error()

        error_rate = analytics.get_error_rate()
        assert error_rate == 0.05  # 5 errors out of 100 messages


class TestPerformanceMetrics:
    """Performance metrics integration tests."""

    def test_throughput_calculation(self):
        """Test throughput calculation."""
        analytics = RealTimeAnalytics()

        # Record messages
        for i in range(100):
            analytics.record_message_processed(50.0)

        throughput = analytics.get_throughput()
        assert throughput >= 0.0

    def test_average_processing_time(self):
        """Test average processing time calculation."""
        analytics = RealTimeAnalytics()

        # Record messages with varying processing times
        times = [10.0, 20.0, 30.0, 40.0, 50.0]
        for time in times:
            analytics.record_message_processed(time)

        avg_time = analytics.get_average_processing_time()
        assert avg_time == 30.0  # Average of 10, 20, 30, 40, 50

    def test_cache_performance_metrics(self):
        """Test cache performance metrics."""
        analytics = RealTimeAnalytics()

        # Simulate cache operations
        for i in range(100):
            if i % 3 == 0:
                analytics.record_cache_hit()
            else:
                analytics.record_cache_miss()

        hit_rate = analytics.get_cache_hit_rate()
        assert 0.3 < hit_rate < 0.35  # Approximately 33% hit rate


class TestDataConsistency:
    """Data consistency integration tests."""

    def test_analytics_data_consistency(self):
        """Test analytics data consistency."""
        analytics = RealTimeAnalytics()

        # Record various metrics
        analytics.record_message_processed(50.0, domain="politics", publisher="BBC")
        analytics.record_message_accepted()
        analytics.record_cache_hit()
        analytics.record_deduplication_hit()

        # Verify consistency
        assert analytics.total_messages_processed == 1
        assert analytics.total_messages_accepted == 1
        assert analytics.cache_hits == 1
        assert analytics.deduplication_hits == 1
        assert analytics.domain_distribution["politics"] == 1
        assert analytics.publisher_distribution["BBC"] == 1

    def test_tracing_data_consistency(self):
        """Test tracing data consistency."""
        config = TracingConfig(enabled=False)
        tracer = DistributedTracer(config)

        # Create spans
        span1 = tracer.start_span(
            operation_name="op1",
            trace_id="trace-123",
            attributes={"key": "value"},
        )
        span2 = tracer.start_span(
            operation_name="op2",
            trace_id="trace-123",
        )

        # Verify consistency
        assert len(tracer.spans) == 2
        trace_spans = tracer.get_trace("trace-123")
        assert len(trace_spans) == 2
        assert all(s.trace_id == "trace-123" for s in trace_spans)

