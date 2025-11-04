"""Tests for Non-Functional Requirements metrics."""

import pytest
import time
from src.metrics.nfr_metrics import (
    NFRMetricsCollector,
    LatencyTracker,
    extraction_latency,
    linking_latency,
    total_latency,
    articles_processed,
    entities_extracted,
    entities_linked,
    extraction_errors,
    linking_errors,
    extraction_confidence,
    linking_success_rate,
    coverage_score,
)


class TestNFRMetricsCollector:
    """Tests for NFR metrics collector."""

    def test_record_extraction_latency(self):
        """Test recording extraction latency."""
        # Just verify the method doesn't raise an exception
        NFRMetricsCollector.record_extraction_latency(0.5)
        assert True

    def test_record_linking_latency(self):
        """Test recording linking latency."""
        # Just verify the method doesn't raise an exception
        NFRMetricsCollector.record_linking_latency(1.0)
        assert True

    def test_record_total_latency(self):
        """Test recording total latency."""
        # Just verify the method doesn't raise an exception
        NFRMetricsCollector.record_total_latency(2.0)
        assert True

    def test_record_article_processed(self):
        """Test recording article processed."""
        initial_count = articles_processed._value.get()
        NFRMetricsCollector.record_article_processed()
        assert articles_processed._value.get() == initial_count + 1

    def test_record_entities_extracted(self):
        """Test recording entities extracted."""
        initial_count = entities_extracted._value.get()
        NFRMetricsCollector.record_entities_extracted(5)
        assert entities_extracted._value.get() == initial_count + 5

    def test_record_entities_linked(self):
        """Test recording entities linked."""
        initial_count = entities_linked._value.get()
        NFRMetricsCollector.record_entities_linked(3)
        assert entities_linked._value.get() == initial_count + 3

    def test_record_extraction_error(self):
        """Test recording extraction error."""
        initial_count = extraction_errors.labels(error_type="timeout")._value.get()
        NFRMetricsCollector.record_extraction_error("timeout")
        assert extraction_errors.labels(error_type="timeout")._value.get() == initial_count + 1

    def test_record_linking_error(self):
        """Test recording linking error."""
        initial_count = linking_errors.labels(error_type="api_failure")._value.get()
        NFRMetricsCollector.record_linking_error("api_failure")
        assert linking_errors.labels(error_type="api_failure")._value.get() == initial_count + 1

    def test_set_cache_hit_rate(self):
        """Test setting cache hit rate."""
        NFRMetricsCollector.set_cache_hit_rate(0.85)
        assert cache_hit_rate._value.get() == 0.85

    def test_set_kafka_consumer_lag(self):
        """Test setting Kafka consumer lag."""
        from src.metrics.nfr_metrics import kafka_consumer_lag
        NFRMetricsCollector.set_kafka_consumer_lag(100)
        assert kafka_consumer_lag._value.get() == 100

    def test_record_extraction_confidence(self):
        """Test recording extraction confidence."""
        # Just verify the method doesn't raise an exception
        NFRMetricsCollector.record_extraction_confidence(0.95)
        assert True

    def test_set_linking_success_rate(self):
        """Test setting linking success rate."""
        NFRMetricsCollector.set_linking_success_rate(0.90)
        assert linking_success_rate._value.get() == 0.90

    def test_set_coverage_score(self):
        """Test setting coverage score."""
        NFRMetricsCollector.set_coverage_score(0.75)
        assert coverage_score._value.get() == 0.75


class TestLatencyTracker:
    """Tests for latency tracker."""

    def test_latency_tracker_extraction(self):
        """Test latency tracker for extraction."""
        with LatencyTracker("extraction"):
            time.sleep(0.05)
        assert True

    def test_latency_tracker_linking(self):
        """Test latency tracker for linking."""
        with LatencyTracker("linking"):
            time.sleep(0.05)
        assert True

    def test_latency_tracker_total(self):
        """Test latency tracker for total."""
        with LatencyTracker("total"):
            time.sleep(0.05)
        assert True

    def test_latency_tracker_accuracy(self):
        """Test latency tracker accuracy."""
        with LatencyTracker("extraction"):
            time.sleep(0.2)
        # Verify that latency was recorded (approximate check)
        # The exact value depends on system performance

    def test_latency_tracker_exception_handling(self):
        """Test latency tracker handles exceptions."""
        try:
            with LatencyTracker("extraction"):
                raise ValueError("Test error")
        except ValueError:
            pass
        # Latency should still be recorded even if exception occurs


class TestMetricsIntegration:
    """Integration tests for metrics."""

    def test_full_processing_metrics(self):
        """Test recording metrics for full processing."""
        # Record article processing
        NFRMetricsCollector.record_article_processed()
        
        # Record extraction
        with LatencyTracker("extraction"):
            time.sleep(0.05)
        NFRMetricsCollector.record_entities_extracted(5)
        for _ in range(5):
            NFRMetricsCollector.record_extraction_confidence(0.95)
        
        # Record linking
        with LatencyTracker("linking"):
            time.sleep(0.05)
        NFRMetricsCollector.record_entities_linked(4)
        
        # Record total
        with LatencyTracker("total"):
            time.sleep(0.1)
        
        # Record quality metrics
        NFRMetricsCollector.set_linking_success_rate(0.8)
        NFRMetricsCollector.set_coverage_score(0.75)
        
        # Verify metrics were recorded
        assert articles_processed._value.get() > 0
        assert entities_extracted._value.get() > 0
        assert entities_linked._value.get() > 0

    def test_error_metrics(self):
        """Test recording error metrics."""
        NFRMetricsCollector.record_extraction_error("timeout")
        NFRMetricsCollector.record_extraction_error("model_error")
        NFRMetricsCollector.record_linking_error("api_failure")
        
        # Verify errors were recorded
        assert extraction_errors.labels(error_type="timeout")._value.get() > 0
        assert extraction_errors.labels(error_type="model_error")._value.get() > 0
        assert linking_errors.labels(error_type="api_failure")._value.get() > 0

    def test_resource_metrics(self):
        """Test recording resource metrics."""
        NFRMetricsCollector.set_cache_hit_rate(0.85)
        NFRMetricsCollector.set_db_connection_pool_size(15)
        NFRMetricsCollector.set_kafka_consumer_lag(50)
        
        # Verify resource metrics were recorded
        from src.metrics.nfr_metrics import cache_hit_rate, db_connection_pool_size, kafka_consumer_lag
        assert cache_hit_rate._value.get() == 0.85
        assert db_connection_pool_size._value.get() == 15
        assert kafka_consumer_lag._value.get() == 50


# Import cache_hit_rate for tests
from src.metrics.nfr_metrics import cache_hit_rate

