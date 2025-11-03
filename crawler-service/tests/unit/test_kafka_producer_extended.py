"""
Extended unit tests for Kafka producer module.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock, call
from datetime import datetime

from src.kafka_producer import KafkaProducerAdapter
from src.models import NewsRawMessage
from src.exceptions import PublishError


class TestKafkaProducerAdapterExtended:
    """Extended tests for KafkaProducerAdapter."""

    @pytest.fixture
    def producer(self):
        """Create producer instance."""
        return KafkaProducerAdapter()

    @pytest.fixture
    def sample_message(self):
        """Create sample news message."""
        return NewsRawMessage(
            article_id="test-123",
            canonical_url="https://example.com/article",
            title="Test Article",
            body="Test content",
            url="https://example.com/article",
            source="Test Source",
            language="en",
            published_at="2024-01-15T10:30:00Z",
            checksum="abc123def456",
            validation_score=0.95,
            schema_version="1.0",
            ingest_job_id="job-123",
            publisher_id="pub-123",
            extraction_method="html",
        )

    @pytest.mark.asyncio
    async def test_start_success(self, producer):
        """Test successful producer start."""
        with patch('src.kafka_producer.SchemaRegistryClient') as mock_registry, \
             patch('src.kafka_producer.AvroSerializer') as mock_serializer, \
             patch('src.kafka_producer.Producer') as mock_producer:
            
            mock_registry_instance = MagicMock()
            mock_registry.return_value = mock_registry_instance
            
            await producer.start()
            
            assert producer.schema_registry_client is not None
            assert producer.producer is not None
            assert producer.avro_serializer is not None

    @pytest.mark.asyncio
    async def test_start_failure(self, producer):
        """Test producer start failure."""
        with patch('src.kafka_producer.SchemaRegistryClient') as mock_registry:
            mock_registry.side_effect = Exception("Connection failed")
            
            with pytest.raises(PublishError):
                await producer.start()

    @pytest.mark.asyncio
    async def test_stop_success(self, producer):
        """Test successful producer stop."""
        producer.producer = MagicMock()
        producer.producer.flush = MagicMock()
        
        await producer.stop()
        
        producer.producer.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_no_producer(self, producer):
        """Test stop when producer not initialized."""
        producer.producer = None
        
        # Should not raise
        await producer.stop()

    @pytest.mark.asyncio
    async def test_stop_flush_error(self, producer):
        """Test stop with flush error."""
        producer.producer = MagicMock()
        producer.producer.flush.side_effect = Exception("Flush failed")
        
        # Should not raise
        await producer.stop()

    @pytest.mark.asyncio
    async def test_publish_success(self, producer, sample_message):
        """Test successful message publish."""
        producer.producer = MagicMock()
        producer.avro_serializer = MagicMock(return_value=b"serialized")

        await producer.publish(sample_message)

        producer.producer.produce.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_not_initialized(self, producer, sample_message):
        """Test publish when producer not initialized."""
        producer.producer = None

        with pytest.raises(PublishError):
            await producer.publish(sample_message)

    @pytest.mark.asyncio
    async def test_publish_with_custom_topic(self, producer, sample_message):
        """Test publish with custom topic."""
        producer.producer = MagicMock()
        producer.avro_serializer = MagicMock(return_value=b"serialized")

        await producer.publish(sample_message, topic="custom-topic")

        call_args = producer.producer.produce.call_args
        assert call_args[1]["topic"] == "custom-topic"

    @pytest.mark.asyncio
    async def test_publish_failure(self, producer, sample_message):
        """Test publish failure."""
        producer.producer = MagicMock()
        producer.avro_serializer = MagicMock(side_effect=Exception("Serialization failed"))

        with pytest.raises(PublishError):
            await producer.publish(sample_message)

    @pytest.mark.asyncio
    async def test_publish_dlq_success(self, producer):
        """Test successful DLQ publish."""
        producer.producer = MagicMock()
        
        message = {"article_id": "test-123", "title": "Test"}
        error = "Validation failed"
        
        await producer.publish_dlq(message, error)
        
        producer.producer.produce.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_dlq_no_producer(self, producer):
        """Test DLQ publish when producer not initialized."""
        producer.producer = None
        
        message = {"article_id": "test-123"}
        error = "Error"
        
        # Should not raise
        await producer.publish_dlq(message, error)

    @pytest.mark.asyncio
    async def test_publish_dlq_failure(self, producer):
        """Test DLQ publish failure."""
        producer.producer = MagicMock()
        producer.producer.produce.side_effect = Exception("Produce failed")
        
        message = {"article_id": "test-123"}
        error = "Error"
        
        # Should not raise
        await producer.publish_dlq(message, error)

    @pytest.mark.asyncio
    async def test_delivery_report(self, producer):
        """Test delivery report callback."""
        err = None
        msg = MagicMock()
        msg.topic.return_value = "test-topic"
        msg.partition.return_value = 0
        msg.offset.return_value = 100
        
        producer._delivery_report(err, msg)
        
        # Should not raise

    @pytest.mark.asyncio
    async def test_delivery_report_error(self, producer):
        """Test delivery report with error."""
        err = MagicMock()
        err.str.return_value = "Delivery failed"
        msg = MagicMock()
        
        producer._delivery_report(err, msg)
        
        # Should not raise

    def test_get_schema(self, producer):
        """Test schema retrieval."""
        schema = producer._get_schema()
        
        assert schema is not None
        assert isinstance(schema, str)
        assert "record" in schema or "type" in schema

