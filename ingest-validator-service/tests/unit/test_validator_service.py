"""Tests for validator service."""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from src.service import ValidatorService
from src.models import ValidationContext, NewsRaw, ValidationDetails, ValidationResult
from datetime import datetime


class TestValidatorService:
    """Test validator service."""

    @patch('src.service.KafkaNewsConsumer')
    @patch('src.service.KafkaNewsProducer')
    @patch('src.service.DedupGrpcClient')
    @patch('src.service.RedisCacheManager')
    @patch('src.service.SourceRegistryRepository')
    @patch('src.service.AuditLogRepository')
    @patch('src.service.get_metrics')
    def test_service_initialization(self, mock_metrics, mock_audit, mock_source, mock_cache, mock_dedup, mock_producer, mock_consumer):
        """Test service initialization."""
        service = ValidatorService()

        assert service.consumer is not None
        assert service.producer is not None
        assert service.pipeline is not None
        assert service.backpressure is not None

    @patch('src.service.KafkaNewsConsumer')
    @patch('src.service.KafkaNewsProducer')
    @patch('src.service.DedupGrpcClient')
    @patch('src.service.RedisCacheManager')
    @patch('src.service.SourceRegistryRepository')
    @patch('src.service.AuditLogRepository')
    @patch('src.service.get_metrics')
    @pytest.mark.asyncio
    async def test_service_initialize(self, mock_metrics, mock_audit, mock_source, mock_cache, mock_dedup, mock_producer, mock_consumer):
        """Test service initialization."""
        mock_source_instance = AsyncMock()
        mock_source.return_value = mock_source_instance
        mock_audit_instance = AsyncMock()
        mock_audit.return_value = mock_audit_instance
        mock_dedup_instance = AsyncMock()
        mock_dedup.return_value = mock_dedup_instance
        mock_consumer_instance = MagicMock()
        mock_consumer.return_value = mock_consumer_instance

        service = ValidatorService()
        await service.initialize()

        mock_source_instance.initialize.assert_called_once()
        mock_audit_instance.initialize.assert_called_once()
        mock_dedup_instance.initialize.assert_called_once()
        mock_consumer_instance.subscribe.assert_called_once_with(["news_raw"])

    @patch('src.service.KafkaNewsConsumer')
    @patch('src.service.KafkaNewsProducer')
    @patch('src.service.DedupGrpcClient')
    @patch('src.service.RedisCacheManager')
    @patch('src.service.SourceRegistryRepository')
    @patch('src.service.AuditLogRepository')
    @patch('src.service.get_metrics')
    def test_get_health_status(self, mock_metrics, mock_audit, mock_source, mock_cache, mock_dedup, mock_producer, mock_consumer):
        """Test getting health status."""
        service = ValidatorService()
        health = service.get_health_status()

        assert health["status"] == "healthy"
        assert health["service"] == "ingest-validator"
        assert "components" in health
        assert "backpressure" in health

    @patch('src.service.KafkaNewsConsumer')
    @patch('src.service.KafkaNewsProducer')
    @patch('src.service.DedupGrpcClient')
    @patch('src.service.RedisCacheManager')
    @patch('src.service.SourceRegistryRepository')
    @patch('src.service.AuditLogRepository')
    @patch('src.service.get_metrics')
    def test_is_ready(self, mock_metrics, mock_audit, mock_source, mock_cache, mock_dedup, mock_producer, mock_consumer):
        """Test readiness check."""
        service = ValidatorService()
        assert service.is_ready() is True

    @patch('src.service.KafkaNewsConsumer')
    @patch('src.service.KafkaNewsProducer')
    @patch('src.service.DedupGrpcClient')
    @patch('src.service.RedisCacheManager')
    @patch('src.service.SourceRegistryRepository')
    @patch('src.service.AuditLogRepository')
    @patch('src.service.get_metrics')
    def test_is_not_ready_no_consumer(self, mock_metrics, mock_audit, mock_source, mock_cache, mock_dedup, mock_producer, mock_consumer):
        """Test readiness check without consumer."""
        service = ValidatorService()
        service.consumer = None
        assert service.is_ready() is False

    @patch('src.service.KafkaNewsConsumer')
    @patch('src.service.KafkaNewsProducer')
    @patch('src.service.DedupGrpcClient')
    @patch('src.service.RedisCacheManager')
    @patch('src.service.SourceRegistryRepository')
    @patch('src.service.AuditLogRepository')
    @patch('src.service.get_metrics')
    @pytest.mark.asyncio
    async def test_shutdown(self, mock_metrics, mock_audit, mock_source, mock_cache, mock_dedup, mock_producer, mock_consumer):
        """Test service shutdown."""
        mock_source_instance = AsyncMock()
        mock_source.return_value = mock_source_instance
        mock_audit_instance = AsyncMock()
        mock_audit.return_value = mock_audit_instance
        mock_dedup_instance = AsyncMock()
        mock_dedup.return_value = mock_dedup_instance
        mock_consumer_instance = MagicMock()
        mock_consumer.return_value = mock_consumer_instance
        mock_producer_instance = MagicMock()
        mock_producer.return_value = mock_producer_instance
        mock_cache_instance = MagicMock()
        mock_cache.return_value = mock_cache_instance

        service = ValidatorService()
        await service.shutdown()

        mock_consumer_instance.close.assert_called_once()
        mock_producer_instance.close.assert_called_once()
        mock_dedup_instance.close.assert_called_once()
        mock_cache_instance.close.assert_called_once()
        mock_source_instance.close.assert_called_once()
        mock_audit_instance.close.assert_called_once()

    @patch('src.service.KafkaNewsConsumer')
    @patch('src.service.KafkaNewsProducer')
    @patch('src.service.DedupGrpcClient')
    @patch('src.service.RedisCacheManager')
    @patch('src.service.SourceRegistryRepository')
    @patch('src.service.AuditLogRepository')
    @patch('src.service.get_metrics')
    @pytest.mark.asyncio
    async def test_process_message_no_message(self, mock_metrics, mock_audit, mock_source, mock_cache, mock_dedup, mock_producer, mock_consumer):
        """Test processing when no message available."""
        mock_consumer_instance = MagicMock()
        mock_consumer_instance.poll.return_value = None
        mock_consumer.return_value = mock_consumer_instance

        service = ValidatorService()
        await service.process_message()

        mock_consumer_instance.poll.assert_called_once()

    @patch('src.service.KafkaNewsConsumer')
    @patch('src.service.KafkaNewsProducer')
    @patch('src.service.DedupGrpcClient')
    @patch('src.service.RedisCacheManager')
    @patch('src.service.SourceRegistryRepository')
    @patch('src.service.AuditLogRepository')
    @patch('src.service.get_metrics')
    @pytest.mark.asyncio
    async def test_process_message_with_message(self, mock_metrics, mock_audit, mock_source, mock_cache, mock_dedup, mock_producer, mock_consumer):
        """Test processing with message."""
        # Setup mocks
        mock_consumer_instance = MagicMock()
        mock_message = MagicMock()
        mock_message.partition.return_value = 0
        mock_message.offset.return_value = 100
        mock_consumer_instance.poll.return_value = mock_message
        mock_consumer_instance.deserialize_message.return_value = NewsRaw(
            article_id="art_123",
            canonical_url="https://example.com",
            title="Test Article",
            body="Test body",
            url="https://example.com",
            published_at="2025-11-03T10:00:00Z",
            language="en",
            source="test_source",
            crawled_at="2025-11-03T11:00:00Z",
            checksum="abc123",
            validation_score=0.8,
            schema_version="1.0.0",
            ingest_job_id="job_123",
            publisher_id="pub_123",
            extraction_method="rss",
        )
        mock_consumer.return_value = mock_consumer_instance

        mock_producer_instance = MagicMock()
        mock_producer.return_value = mock_producer_instance

        mock_metrics_instance = MagicMock()
        mock_metrics.return_value = mock_metrics_instance

        service = ValidatorService()
        await service.process_message()

        mock_consumer_instance.poll.assert_called_once()
        mock_consumer_instance.deserialize_message.assert_called_once()
        # Message should be added to batch, not committed immediately
        assert len(service.message_batch) == 1
        assert service.message_batch[0] == mock_message

    @patch('src.service.KafkaNewsConsumer')
    @patch('src.service.KafkaNewsProducer')
    @patch('src.service.DedupGrpcClient')
    @patch('src.service.RedisCacheManager')
    @patch('src.service.SourceRegistryRepository')
    @patch('src.service.AuditLogRepository')
    @patch('src.service.get_metrics')
    @pytest.mark.asyncio
    async def test_route_result_accept(self, mock_metrics, mock_audit, mock_source, mock_cache, mock_dedup, mock_producer, mock_consumer):
        """Test routing result to accept."""
        mock_producer_instance = MagicMock()
        mock_producer.return_value = mock_producer_instance

        mock_audit_instance = AsyncMock()
        mock_audit.return_value = mock_audit_instance

        mock_metrics_instance = MagicMock()
        mock_metrics.return_value = mock_metrics_instance

        service = ValidatorService()

        # Create test context and result
        raw_message = NewsRaw(
            article_id="art_123",
            canonical_url="https://example.com",
            title="Test Article",
            body="Test body",
            url="https://example.com",
            published_at="2025-11-03T10:00:00Z",
            language="en",
            source="test_source",
            crawled_at="2025-11-03T11:00:00Z",
            checksum="abc123",
            validation_score=0.8,
            schema_version="1.0.0",
            ingest_job_id="job_123",
            publisher_id="pub_123",
            extraction_method="rss",
        )

        context = ValidationContext(
            article_id="art_123",
            trace_id="trace_123",
            job_id="job_123",
            raw_message=raw_message,
        )

        result = ValidationResult(
            article_id="art_123",
            trace_id="trace_123",
            job_id="job_123",
            is_valid=True,
            validation_score=0.9,
            errors=[],
            warnings=[],
        )

        await service._route_result(result, context)

        # Should publish to validated topic
        mock_producer_instance.publish_validated.assert_called_once()

    @patch('src.service.KafkaNewsConsumer')
    @patch('src.service.KafkaNewsProducer')
    @patch('src.service.DedupGrpcClient')
    @patch('src.service.RedisCacheManager')
    @patch('src.service.SourceRegistryRepository')
    @patch('src.service.AuditLogRepository')
    @patch('src.service.get_metrics')
    @pytest.mark.asyncio
    async def test_route_result_reject_with_errors(self, mock_metrics, mock_audit, mock_source, mock_cache, mock_dedup, mock_producer, mock_consumer):
        """Test routing result to reject with errors."""
        mock_producer_instance = MagicMock()
        mock_producer.return_value = mock_producer_instance

        mock_audit_instance = AsyncMock()
        mock_audit.return_value = mock_audit_instance

        mock_metrics_instance = MagicMock()
        mock_metrics.return_value = mock_metrics_instance

        service = ValidatorService()

        # Create test context and result with errors
        raw_message = NewsRaw(
            article_id="art_123",
            canonical_url="https://example.com",
            title="Test Article",
            body="Test body",
            url="https://example.com",
            published_at="2025-11-03T10:00:00Z",
            language="en",
            source="test_source",
            crawled_at="2025-11-03T11:00:00Z",
            checksum="abc123",
            validation_score=0.8,
            schema_version="1.0.0",
            ingest_job_id="job_123",
            publisher_id="pub_123",
            extraction_method="rss",
        )

        context = ValidationContext(
            article_id="art_123",
            trace_id="trace_123",
            job_id="job_123",
            raw_message=raw_message,
        )

        result = ValidationResult(
            article_id="art_123",
            trace_id="trace_123",
            job_id="job_123",
            is_valid=False,
            validation_score=0.5,
            errors=["Duplicate detected"],
            warnings=[],
        )

        await service._route_result(result, context)

        # Should publish to rejected topic
        mock_producer_instance.publish_rejected.assert_called_once()

    @patch('src.service.KafkaNewsConsumer')
    @patch('src.service.KafkaNewsProducer')
    @patch('src.service.DedupGrpcClient')
    @patch('src.service.RedisCacheManager')
    @patch('src.service.SourceRegistryRepository')
    @patch('src.service.AuditLogRepository')
    @patch('src.service.get_metrics')
    def test_get_health_status(self, mock_metrics, mock_audit, mock_source, mock_cache, mock_dedup, mock_producer, mock_consumer):
        """Test get_health_status method."""
        service = ValidatorService()

        health = service.get_health_status()

        assert health["status"] == "healthy"
        assert health["service"] == "ingest-validator"
        assert "components" in health
        assert "backpressure" in health

    @patch('src.service.KafkaNewsConsumer')
    @patch('src.service.KafkaNewsProducer')
    @patch('src.service.DedupGrpcClient')
    @patch('src.service.RedisCacheManager')
    @patch('src.service.SourceRegistryRepository')
    @patch('src.service.AuditLogRepository')
    @patch('src.service.get_metrics')
    def test_is_ready(self, mock_metrics, mock_audit, mock_source, mock_cache, mock_dedup, mock_producer, mock_consumer):
        """Test is_ready method."""
        service = ValidatorService()

        assert service.is_ready() is True

    @patch('src.service.KafkaNewsConsumer')
    @patch('src.service.KafkaNewsProducer')
    @patch('src.service.DedupGrpcClient')
    @patch('src.service.RedisCacheManager')
    @patch('src.service.SourceRegistryRepository')
    @patch('src.service.AuditLogRepository')
    @patch('src.service.get_metrics')
    @pytest.mark.asyncio
    async def test_shutdown(self, mock_metrics, mock_audit, mock_source, mock_cache, mock_dedup, mock_producer, mock_consumer):
        """Test shutdown method."""
        mock_dedup_instance = AsyncMock()
        mock_dedup.return_value = mock_dedup_instance
        mock_source_instance = AsyncMock()
        mock_source.return_value = mock_source_instance
        mock_audit_instance = AsyncMock()
        mock_audit.return_value = mock_audit_instance
        mock_cache_instance = MagicMock()
        mock_cache.return_value = mock_cache_instance
        mock_consumer_instance = MagicMock()
        mock_consumer.return_value = mock_consumer_instance
        mock_producer_instance = MagicMock()
        mock_producer.return_value = mock_producer_instance

        service = ValidatorService()
        await service.shutdown()

        mock_consumer_instance.close.assert_called_once()
        mock_producer_instance.close.assert_called_once()
        mock_dedup_instance.close.assert_called_once()
        mock_cache_instance.close.assert_called_once()
        mock_source_instance.close.assert_called_once()
        mock_audit_instance.close.assert_called_once()

    @patch('src.service.KafkaNewsConsumer')
    @patch('src.service.KafkaNewsProducer')
    @patch('src.service.DedupGrpcClient')
    @patch('src.service.RedisCacheManager')
    @patch('src.service.SourceRegistryRepository')
    @patch('src.service.AuditLogRepository')
    @patch('src.service.get_metrics')
    @pytest.mark.asyncio
    async def test_shutdown_with_exception(self, mock_metrics, mock_audit, mock_source, mock_cache, mock_dedup, mock_producer, mock_consumer):
        """Test shutdown with exception."""
        mock_consumer_instance = MagicMock()
        mock_consumer_instance.close.side_effect = Exception("Close error")
        mock_consumer.return_value = mock_consumer_instance

        service = ValidatorService()
        # Should not raise exception
        await service.shutdown()

    @patch('src.service.KafkaNewsConsumer')
    @patch('src.service.KafkaNewsProducer')
    @patch('src.service.DedupGrpcClient')
    @patch('src.service.RedisCacheManager')
    @patch('src.service.SourceRegistryRepository')
    @patch('src.service.AuditLogRepository')
    @patch('src.service.get_metrics')
    @pytest.mark.asyncio
    async def test_initialize_with_source_registry_exception(self, mock_metrics, mock_audit, mock_source, mock_cache, mock_dedup, mock_producer, mock_consumer):
        """Test initialize with source registry exception."""
        mock_source_instance = AsyncMock()
        mock_source_instance.initialize.side_effect = Exception("Registry error")
        mock_source.return_value = mock_source_instance
        mock_audit_instance = AsyncMock()
        mock_audit.return_value = mock_audit_instance
        mock_dedup_instance = AsyncMock()
        mock_dedup.return_value = mock_dedup_instance
        mock_consumer_instance = MagicMock()
        mock_consumer.return_value = mock_consumer_instance

        service = ValidatorService()
        # Should not raise exception, just log warning
        await service.initialize()

    @patch('src.service.KafkaNewsConsumer')
    @patch('src.service.KafkaNewsProducer')
    @patch('src.service.DedupGrpcClient')
    @patch('src.service.RedisCacheManager')
    @patch('src.service.SourceRegistryRepository')
    @patch('src.service.AuditLogRepository')
    @patch('src.service.get_metrics')
    @pytest.mark.asyncio
    async def test_initialize_with_audit_log_exception(self, mock_metrics, mock_audit, mock_source, mock_cache, mock_dedup, mock_producer, mock_consumer):
        """Test initialize with audit log exception."""
        mock_source_instance = AsyncMock()
        mock_source.return_value = mock_source_instance
        mock_audit_instance = AsyncMock()
        mock_audit_instance.initialize.side_effect = Exception("Audit error")
        mock_audit.return_value = mock_audit_instance
        mock_dedup_instance = AsyncMock()
        mock_dedup.return_value = mock_dedup_instance
        mock_consumer_instance = MagicMock()
        mock_consumer.return_value = mock_consumer_instance

        service = ValidatorService()
        # Should not raise exception, just log warning
        await service.initialize()

    @patch('src.service.KafkaNewsConsumer')
    @patch('src.service.KafkaNewsProducer')
    @patch('src.service.DedupGrpcClient')
    @patch('src.service.RedisCacheManager')
    @patch('src.service.SourceRegistryRepository')
    @patch('src.service.AuditLogRepository')
    @patch('src.service.get_metrics')
    @pytest.mark.asyncio
    async def test_initialize_with_dedup_client_exception(self, mock_metrics, mock_audit, mock_source, mock_cache, mock_dedup, mock_producer, mock_consumer):
        """Test initialize with dedup client exception."""
        mock_source_instance = AsyncMock()
        mock_source.return_value = mock_source_instance
        mock_audit_instance = AsyncMock()
        mock_audit.return_value = mock_audit_instance
        mock_dedup_instance = AsyncMock()
        mock_dedup_instance.initialize.side_effect = Exception("Dedup error")
        mock_dedup.return_value = mock_dedup_instance
        mock_consumer_instance = MagicMock()
        mock_consumer.return_value = mock_consumer_instance

        service = ValidatorService()
        # Should not raise exception, just log warning
        await service.initialize()

    @patch('src.service.KafkaNewsConsumer')
    @patch('src.service.KafkaNewsProducer')
    @patch('src.service.DedupGrpcClient')
    @patch('src.service.RedisCacheManager')
    @patch('src.service.SourceRegistryRepository')
    @patch('src.service.AuditLogRepository')
    @patch('src.service.get_metrics')
    @pytest.mark.asyncio
    async def test_initialize_with_kafka_subscription_exception(self, mock_metrics, mock_audit, mock_source, mock_cache, mock_dedup, mock_producer, mock_consumer):
        """Test initialize with Kafka subscription exception."""
        mock_source_instance = AsyncMock()
        mock_source.return_value = mock_source_instance
        mock_audit_instance = AsyncMock()
        mock_audit.return_value = mock_audit_instance
        mock_dedup_instance = AsyncMock()
        mock_dedup.return_value = mock_dedup_instance
        mock_consumer_instance = MagicMock()
        mock_consumer_instance.subscribe.side_effect = Exception("Subscription error")
        mock_consumer.return_value = mock_consumer_instance

        service = ValidatorService()
        # Should not raise exception, just log warning
        await service.initialize()

    @patch('src.service.KafkaNewsConsumer')
    @patch('src.service.KafkaNewsProducer')
    @patch('src.service.DedupGrpcClient')
    @patch('src.service.RedisCacheManager')
    @patch('src.service.SourceRegistryRepository')
    @patch('src.service.AuditLogRepository')
    @patch('src.service.get_metrics')
    @pytest.mark.asyncio
    async def test_process_message_with_exception(self, mock_metrics, mock_audit, mock_source, mock_cache, mock_dedup, mock_producer, mock_consumer):
        """Test process_message with exception."""
        mock_consumer_instance = MagicMock()
        mock_consumer_instance.poll.side_effect = Exception("Poll error")
        mock_consumer.return_value = mock_consumer_instance
        mock_metrics_instance = MagicMock()
        mock_metrics.return_value = mock_metrics_instance

        service = ValidatorService()
        # Should not raise exception
        await service.process_message()

        # Should increment rejected counter
        mock_metrics_instance.messages_rejected_total.inc.assert_called()

    @patch('src.service.KafkaNewsConsumer')
    @patch('src.service.KafkaNewsProducer')
    @patch('src.service.DedupGrpcClient')
    @patch('src.service.RedisCacheManager')
    @patch('src.service.SourceRegistryRepository')
    @patch('src.service.AuditLogRepository')
    @patch('src.service.get_metrics')
    @pytest.mark.asyncio
    async def test_route_result_with_exception(self, mock_metrics, mock_audit, mock_source, mock_cache, mock_dedup, mock_producer, mock_consumer):
        """Test _route_result with exception."""
        mock_producer_instance = MagicMock()
        mock_producer_instance.publish_validated.side_effect = Exception("Publish error")
        mock_producer.return_value = mock_producer_instance

        raw_message = NewsRaw(
            article_id="art_123",
            canonical_url="https://example.com/article",
            title="Test Article",
            body="This is a test article body with sufficient content.",
            url="https://example.com/article",
            published_at="2025-11-03T10:00:00Z",
            language="en",
            source="example",
            crawled_at="2025-11-03T10:05:00Z",
            checksum="abc123",
            validation_score=0.9,
            schema_version="1.0.0",
            ingest_job_id="job_123",
            publisher_id="pub_123",
            extraction_method="html",
        )

        context = ValidationContext(
            article_id="art_123",
            trace_id="trace_123",
            job_id="job_123",
            raw_message=raw_message,
        )

        result = ValidationResult(
            article_id="art_123",
            trace_id="trace_123",
            job_id="job_123",
            is_valid=True,
            validation_score=0.9,
            errors=[],
            warnings=[],
        )

        service = ValidatorService()
        # Should not raise exception
        await service._route_result(result, context)

    @patch('src.service.KafkaNewsConsumer')
    @patch('src.service.KafkaNewsProducer')
    @patch('src.service.DedupGrpcClient')
    @patch('src.service.RedisCacheManager')
    @patch('src.service.SourceRegistryRepository')
    @patch('src.service.AuditLogRepository')
    @patch('src.service.get_metrics')
    def test_replay_from_offset_success(self, mock_metrics, mock_audit, mock_source, mock_cache, mock_dedup, mock_producer, mock_consumer):
        """Test replay from offset - success."""
        mock_consumer_instance = MagicMock()
        mock_consumer_instance.get_current_offset.return_value = 50
        mock_consumer.return_value = mock_consumer_instance

        service = ValidatorService()
        result = service.replay_from_offset(0, 100)

        assert result["status"] == "success"
        assert result["partition"] == 0
        assert result["replay_offset"] == 100
        assert result["previous_offset"] == 50
        mock_consumer_instance.seek_to_offset.assert_called_once_with(0, 100)

    @patch('src.service.KafkaNewsConsumer')
    @patch('src.service.KafkaNewsProducer')
    @patch('src.service.DedupGrpcClient')
    @patch('src.service.RedisCacheManager')
    @patch('src.service.SourceRegistryRepository')
    @patch('src.service.AuditLogRepository')
    @patch('src.service.get_metrics')
    def test_replay_from_offset_error(self, mock_metrics, mock_audit, mock_source, mock_cache, mock_dedup, mock_producer, mock_consumer):
        """Test replay from offset - error."""
        mock_consumer_instance = MagicMock()
        mock_consumer_instance.get_current_offset.side_effect = Exception("Seek failed")
        mock_consumer.return_value = mock_consumer_instance

        service = ValidatorService()
        result = service.replay_from_offset(0, 100)

        assert result["status"] == "error"
        assert result["partition"] == 0
        assert "error" in result

    @patch('src.service.KafkaNewsConsumer')
    @patch('src.service.KafkaNewsProducer')
    @patch('src.service.DedupGrpcClient')
    @patch('src.service.RedisCacheManager')
    @patch('src.service.SourceRegistryRepository')
    @patch('src.service.AuditLogRepository')
    @patch('src.service.get_metrics')
    def test_get_partition_offsets_success(self, mock_metrics, mock_audit, mock_source, mock_cache, mock_dedup, mock_producer, mock_consumer):
        """Test get partition offsets - success."""
        mock_consumer_instance = MagicMock()
        mock_consumer_instance.get_current_offset.return_value = 150
        mock_consumer.return_value = mock_consumer_instance

        service = ValidatorService()
        result = service.get_partition_offsets(0)

        assert result["status"] == "success"
        assert result["partition"] == 0
        assert result["current_offset"] == 150

    @patch('src.service.KafkaNewsConsumer')
    @patch('src.service.KafkaNewsProducer')
    @patch('src.service.DedupGrpcClient')
    @patch('src.service.RedisCacheManager')
    @patch('src.service.SourceRegistryRepository')
    @patch('src.service.AuditLogRepository')
    @patch('src.service.get_metrics')
    def test_get_partition_offsets_error(self, mock_metrics, mock_audit, mock_source, mock_cache, mock_dedup, mock_producer, mock_consumer):
        """Test get partition offsets - error."""
        mock_consumer_instance = MagicMock()
        mock_consumer_instance.get_current_offset.side_effect = Exception("Get offset failed")
        mock_consumer.return_value = mock_consumer_instance

        service = ValidatorService()
        result = service.get_partition_offsets(0)

        assert result["status"] == "error"
        assert result["partition"] == 0
        assert "error" in result

    @patch('src.service.KafkaNewsConsumer')
    @patch('src.service.KafkaNewsProducer')
    @patch('src.service.DedupGrpcClient')
    @patch('src.service.RedisCacheManager')
    @patch('src.service.SourceRegistryRepository')
    @patch('src.service.AuditLogRepository')
    @patch('src.service.get_metrics')
    @pytest.mark.asyncio
    async def test_validate_batch_empty(self, mock_metrics, mock_audit, mock_source, mock_cache, mock_dedup, mock_producer, mock_consumer):
        """Test batch validation with empty list."""
        service = ValidatorService()
        result = await service.validate_batch([])

        assert result["status"] == "success"
        assert result["total_messages"] == 0
        assert result["validated_count"] == 0
        assert result["rejected_count"] == 0

    @patch('src.service.KafkaNewsConsumer')
    @patch('src.service.KafkaNewsProducer')
    @patch('src.service.DedupGrpcClient')
    @patch('src.service.RedisCacheManager')
    @patch('src.service.SourceRegistryRepository')
    @patch('src.service.AuditLogRepository')
    @patch('src.service.get_metrics')
    @pytest.mark.asyncio
    async def test_validate_batch_success(self, mock_metrics, mock_audit, mock_source, mock_cache, mock_dedup, mock_producer, mock_consumer):
        """Test batch validation - success."""
        # Setup mocks
        mock_pipeline = MagicMock()
        mock_context = MagicMock()
        mock_result = MagicMock()
        mock_result.validation_score = 0.9
        mock_result.language = "en"
        mock_result.language_confidence = 0.95
        mock_result.language_detection_method = "fasttext"
        mock_result.source_published_at_utc = "2025-11-02T10:00:00Z"
        mock_result.country = "US"
        mock_result.validation_details = {}
        mock_result.publisher_id = "pub_123"
        mock_result.rejection_reason = None
        mock_result.error_codes = []
        mock_result.error_details = {}

        mock_pipeline.create_context.return_value = mock_context
        mock_pipeline.execute = AsyncMock(return_value=mock_result)

        service = ValidatorService()
        service.pipeline = mock_pipeline
        service.producer = MagicMock()
        service.producer.publish_validated = MagicMock()

        messages = [
            NewsRaw(
                article_id="article_1",
                canonical_url="https://example.com/1",
                title="Test Article 1",
                body="This is a test article body with sufficient content.",
                url="https://example.com/1",
                published_at="2025-11-02T10:00:00Z",
                language="en",
                source="test_source",
                crawled_at="2025-11-02T11:00:00Z",
                checksum="abc123",
                validation_score=0.8,
                schema_version="1.0.0",
                ingest_job_id="job_123",
                publisher_id="pub_123",
                extraction_method="rss",
            ),
        ]

        result = await service.validate_batch(messages)

        assert result["status"] == "success"
        assert result["total_messages"] == 1
        assert result["validated_count"] == 1
        assert result["rejected_count"] == 0
        assert len(result["results"]) == 1
        assert result["results"][0]["status"] == "validated"

    @patch('src.service.KafkaNewsConsumer')
    @patch('src.service.KafkaNewsProducer')
    @patch('src.service.DedupGrpcClient')
    @patch('src.service.RedisCacheManager')
    @patch('src.service.SourceRegistryRepository')
    @patch('src.service.AuditLogRepository')
    @patch('src.service.get_metrics')
    @pytest.mark.asyncio
    async def test_validate_batch_mixed_results(self, mock_metrics, mock_audit, mock_source, mock_cache, mock_dedup, mock_producer, mock_consumer):
        """Test batch validation - mixed results."""
        # Setup mocks
        mock_pipeline = MagicMock()
        mock_context = MagicMock()

        # First message passes validation
        mock_result_pass = MagicMock()
        mock_result_pass.validation_score = 0.9
        mock_result_pass.language = "en"
        mock_result_pass.language_confidence = 0.95
        mock_result_pass.language_detection_method = "fasttext"
        mock_result_pass.source_published_at_utc = "2025-11-02T10:00:00Z"
        mock_result_pass.country = "US"
        mock_result_pass.validation_details = {}
        mock_result_pass.publisher_id = "pub_123"
        mock_result_pass.rejection_reason = None
        mock_result_pass.error_codes = []
        mock_result_pass.error_details = {}

        # Second message fails validation
        mock_result_fail = MagicMock()
        mock_result_fail.validation_score = 0.6
        mock_result_fail.language = "en"
        mock_result_fail.language_confidence = 0.95
        mock_result_fail.language_detection_method = "fasttext"
        mock_result_fail.source_published_at_utc = "2025-11-02T10:00:00Z"
        mock_result_fail.country = "US"
        mock_result_fail.validation_details = {}
        mock_result_fail.publisher_id = "pub_123"
        mock_result_fail.rejection_reason = "Low validation score"
        mock_result_fail.error_codes = ["LOW_SCORE"]
        mock_result_fail.error_details = {"score": "0.6"}

        mock_pipeline.create_context.return_value = mock_context
        mock_pipeline.execute = AsyncMock(side_effect=[mock_result_pass, mock_result_fail])

        service = ValidatorService()
        service.pipeline = mock_pipeline
        service.producer = MagicMock()
        service.producer.publish_validated = MagicMock()
        service.producer.publish_rejected = MagicMock()

        messages = [
            NewsRaw(
                article_id="article_1",
                canonical_url="https://example.com/1",
                title="Test Article 1",
                body="This is a test article body with sufficient content.",
                url="https://example.com/1",
                published_at="2025-11-02T10:00:00Z",
                language="en",
                source="test_source",
                crawled_at="2025-11-02T11:00:00Z",
                checksum="abc123",
                validation_score=0.8,
                schema_version="1.0.0",
                ingest_job_id="job_123",
                publisher_id="pub_123",
                extraction_method="rss",
            ),
            NewsRaw(
                article_id="article_2",
                canonical_url="https://example.com/2",
                title="Short",
                body="Short",
                url="https://example.com/2",
                published_at="2025-11-02T10:00:00Z",
                language="en",
                source="test_source",
                crawled_at="2025-11-02T11:00:00Z",
                checksum="def456",
                validation_score=0.6,
                schema_version="1.0.0",
                ingest_job_id="job_123",
                publisher_id="pub_123",
                extraction_method="rss",
            ),
        ]

        result = await service.validate_batch(messages)

        assert result["status"] == "success"
        assert result["total_messages"] == 2
        assert result["validated_count"] == 1
        assert result["rejected_count"] == 1
        assert len(result["results"]) == 2
        assert result["results"][0]["status"] == "validated"
        assert result["results"][1]["status"] == "rejected"

    @patch('src.service.KafkaNewsConsumer')
    @patch('src.service.KafkaNewsProducer')
    @patch('src.service.DedupGrpcClient')
    @patch('src.service.RedisCacheManager')
    @patch('src.service.SourceRegistryRepository')
    @patch('src.service.AuditLogRepository')
    @patch('src.service.get_metrics')
    @pytest.mark.asyncio
    async def test_validate_batch_error(self, mock_metrics, mock_audit, mock_source, mock_cache, mock_dedup, mock_producer, mock_consumer):
        """Test batch validation - error."""
        # Setup mocks
        mock_pipeline = AsyncMock()
        mock_pipeline.create_context.side_effect = Exception("Pipeline error")

        service = ValidatorService()
        service.pipeline = mock_pipeline

        messages = [
            NewsRaw(
                article_id="article_1",
                canonical_url="https://example.com/1",
                title="Test Article 1",
                body="This is a test article body with sufficient content.",
                url="https://example.com/1",
                published_at="2025-11-02T10:00:00Z",
                language="en",
                source="test_source",
                crawled_at="2025-11-02T11:00:00Z",
                checksum="abc123",
                validation_score=0.8,
                schema_version="1.0.0",
                ingest_job_id="job_123",
                publisher_id="pub_123",
                extraction_method="rss",
            ),
        ]

        result = await service.validate_batch(messages)

        assert result["status"] == "success"
        assert result["total_messages"] == 1
        assert result["rejected_count"] == 1

