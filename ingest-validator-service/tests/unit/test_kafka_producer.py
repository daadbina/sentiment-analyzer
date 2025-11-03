"""Tests for Kafka producer."""

import pytest
from unittest.mock import Mock, MagicMock, patch, mock_open
from src.clients.kafka_producer import KafkaNewsProducer
from src.models import NewsValidated, NewsRejected
from src.exceptions import KafkaError as KafkaErrorException
from datetime import datetime


class TestKafkaNewsProducer:
    """Test Kafka producer functionality."""

    @patch('builtins.open', new_callable=mock_open, read_data='{"type": "record"}')
    @patch('src.clients.kafka_producer.SchemaRegistryClient')
    @patch('src.clients.kafka_producer.AvroSerializer')
    @patch('src.clients.kafka_producer.Producer')
    def test_producer_initialization(self, mock_producer_class, mock_serializer_class, mock_registry_class, mock_file):
        """Test producer initialization."""
        mock_producer = MagicMock()
        mock_producer_class.return_value = mock_producer
        mock_serializer = MagicMock()
        mock_serializer_class.return_value = mock_serializer

        producer = KafkaNewsProducer()

        assert producer.producer is not None
        assert producer.validated_serializer is not None
        assert producer.rejected_serializer is not None
        mock_producer_class.assert_called_once()

    @patch('builtins.open', new_callable=mock_open, read_data='{"type": "record"}')
    @patch('src.clients.kafka_producer.SchemaRegistryClient')
    @patch('src.clients.kafka_producer.AvroSerializer')
    @patch('src.clients.kafka_producer.Producer')
    def test_producer_initialization_failure(self, mock_producer_class, mock_serializer_class, mock_registry_class, mock_file):
        """Test producer initialization failure."""
        mock_producer_class.side_effect = Exception("Connection failed")

        with pytest.raises(KafkaErrorException):
            KafkaNewsProducer()

    @patch('builtins.open', new_callable=mock_open, read_data='{"type": "record"}')
    @patch('src.clients.kafka_producer.SchemaRegistryClient')
    @patch('src.clients.kafka_producer.AvroSerializer')
    @patch('src.clients.kafka_producer.Producer')
    def test_publish_validated_message(self, mock_producer_class, mock_serializer_class, mock_registry_class, mock_file):
        """Test publishing validated message."""
        mock_producer = MagicMock()
        mock_producer_class.return_value = mock_producer
        mock_serializer = MagicMock()
        mock_serializer_class.return_value = mock_serializer

        producer = KafkaNewsProducer()

        # Create test message
        message = NewsValidated(
            article_id="art_123",
            canonical_url="https://example.com",
            title="Test Article",
            body="Test body",
            url="https://example.com",
            source="test_source",
            language="en",
            language_confidence=0.95,
            language_detection_method="fasttext",
            source_published_at_raw="2025-11-03T10:00:00Z",
            source_published_at_utc="2025-11-03T10:00:00Z",
            ingested_at="2025-11-03T11:00:00Z",
            validated_at="2025-11-03T11:00:00Z",
            country="US",
            checksum="abc123",
            validation_score=0.9,
            validation_details={
                "schema_valid": True,
                "encoding_valid": True,
                "timestamp_valid": True,
                "source_verified": True,
                "language_detected": True,
                "not_duplicate": True,
                "content_quality_valid": True,
                "geographic_valid": True,
            },
            schema_version="1.0.0",
            ingest_job_id="job_123",
            validation_job_id="val_job_123",
            trace_id="trace_123",
            publisher_id="pub_123",
        )

        producer.publish_validated(message)

        mock_producer.produce.assert_called_once()

    @patch('builtins.open', new_callable=mock_open, read_data='{"type": "record"}')
    @patch('src.clients.kafka_producer.SchemaRegistryClient')
    @patch('src.clients.kafka_producer.AvroSerializer')
    @patch('src.clients.kafka_producer.Producer')
    def test_publish_validated_without_producer(self, mock_producer_class, mock_serializer_class, mock_registry_class, mock_file):
        """Test publishing without initialized producer."""
        mock_producer_class.return_value = None

        producer = KafkaNewsProducer()
        producer.producer = None

        message = NewsValidated(
            article_id="art_123",
            canonical_url="https://example.com",
            title="Test Article",
            body="Test body",
            url="https://example.com",
            source="test_source",
            language="en",
            language_confidence=0.95,
            language_detection_method="fasttext",
            source_published_at_raw="2025-11-03T10:00:00Z",
            source_published_at_utc="2025-11-03T10:00:00Z",
            ingested_at="2025-11-03T11:00:00Z",
            validated_at="2025-11-03T11:00:00Z",
            country="US",
            checksum="abc123",
            validation_score=0.9,
            validation_details={},
            schema_version="1.0.0",
            ingest_job_id="job_123",
            validation_job_id="val_job_123",
            trace_id="trace_123",
            publisher_id="pub_123",
        )

        with pytest.raises(KafkaErrorException):
            producer.publish_validated(message)

    @patch('builtins.open', new_callable=mock_open, read_data='{"type": "record"}')
    @patch('src.clients.kafka_producer.SchemaRegistryClient')
    @patch('src.clients.kafka_producer.AvroSerializer')
    @patch('src.clients.kafka_producer.Producer')
    def test_publish_rejected_message(self, mock_producer_class, mock_serializer_class, mock_registry_class, mock_file):
        """Test publishing rejected message."""
        mock_producer = MagicMock()
        mock_producer_class.return_value = mock_producer
        mock_serializer = MagicMock()
        mock_serializer_class.return_value = mock_serializer

        producer = KafkaNewsProducer()

        # Create test message
        message = NewsRejected(
            article_id="art_123",
            url="https://example.com",
            source="test_source",
            rejected_at="2025-11-03T11:00:00Z",
            validation_score=0.5,
            rejection_reason="Low validation score",
            error_codes=["LOW_SCORE"],
            error_details={"score": "0.5"},
            retry_count=0,
            original_message={},
            trace_id="trace_123",
            validation_job_id="val_job_123",
            schema_version="1.0.0",
        )

        producer.publish_rejected(message)

        mock_producer.produce.assert_called_once()

    @patch('builtins.open', new_callable=mock_open, read_data='{"type": "record"}')
    @patch('src.clients.kafka_producer.SchemaRegistryClient')
    @patch('src.clients.kafka_producer.AvroSerializer')
    @patch('src.clients.kafka_producer.Producer')
    def test_publish_rejected_without_producer(self, mock_producer_class, mock_serializer_class, mock_registry_class, mock_file):
        """Test publishing rejected without initialized producer."""
        mock_producer_class.return_value = None

        producer = KafkaNewsProducer()
        producer.producer = None

        message = NewsRejected(
            article_id="art_123",
            url="https://example.com",
            source="test_source",
            rejected_at="2025-11-03T11:00:00Z",
            validation_score=0.5,
            rejection_reason="Low validation score",
            error_codes=["LOW_SCORE"],
            error_details={"score": "0.5"},
            retry_count=0,
            original_message={},
            trace_id="trace_123",
            validation_job_id="val_job_123",
            schema_version="1.0.0",
        )

        with pytest.raises(KafkaErrorException):
            producer.publish_rejected(message)

    @patch('builtins.open', new_callable=mock_open, read_data='{"type": "record"}')
    @patch('src.clients.kafka_producer.SchemaRegistryClient')
    @patch('src.clients.kafka_producer.AvroSerializer')
    @patch('src.clients.kafka_producer.Producer')
    def test_flush_messages(self, mock_producer_class, mock_serializer_class, mock_registry_class, mock_file):
        """Test flushing pending messages."""
        mock_producer = MagicMock()
        mock_producer.flush.return_value = 0
        mock_producer_class.return_value = mock_producer

        producer = KafkaNewsProducer()
        remaining = producer.flush(30000)

        assert remaining == 0
        mock_producer.flush.assert_called_once_with(30000)

    @patch('builtins.open', new_callable=mock_open, read_data='{"type": "record"}')
    @patch('src.clients.kafka_producer.SchemaRegistryClient')
    @patch('src.clients.kafka_producer.AvroSerializer')
    @patch('src.clients.kafka_producer.Producer')
    def test_flush_with_pending_messages(self, mock_producer_class, mock_serializer_class, mock_registry_class, mock_file):
        """Test flushing with pending messages."""
        mock_producer = MagicMock()
        mock_producer.flush.return_value = 5
        mock_producer_class.return_value = mock_producer

        producer = KafkaNewsProducer()
        remaining = producer.flush(30000)

        assert remaining == 5

    @patch('builtins.open', new_callable=mock_open, read_data='{"type": "record"}')
    @patch('src.clients.kafka_producer.SchemaRegistryClient')
    @patch('src.clients.kafka_producer.AvroSerializer')
    @patch('src.clients.kafka_producer.Producer')
    def test_flush_without_producer(self, mock_producer_class, mock_serializer_class, mock_registry_class, mock_file):
        """Test flushing without producer."""
        mock_producer_class.return_value = None

        producer = KafkaNewsProducer()
        producer.producer = None
        remaining = producer.flush(30000)

        assert remaining == 0

    @patch('builtins.open', new_callable=mock_open, read_data='{"type": "record"}')
    @patch('src.clients.kafka_producer.SchemaRegistryClient')
    @patch('src.clients.kafka_producer.AvroSerializer')
    @patch('src.clients.kafka_producer.Producer')
    def test_close_producer(self, mock_producer_class, mock_serializer_class, mock_registry_class, mock_file):
        """Test closing producer."""
        mock_producer = MagicMock()
        mock_producer.flush.return_value = 0
        mock_producer_class.return_value = mock_producer

        producer = KafkaNewsProducer()
        producer.close()

        mock_producer.flush.assert_called_once()
        mock_producer.close.assert_called_once()

    @patch('builtins.open', new_callable=mock_open, read_data='{"type": "record"}')
    @patch('src.clients.kafka_producer.SchemaRegistryClient')
    @patch('src.clients.kafka_producer.AvroSerializer')
    @patch('src.clients.kafka_producer.Producer')
    def test_close_producer_error(self, mock_producer_class, mock_serializer_class, mock_registry_class, mock_file):
        """Test closing producer with error."""
        mock_producer = MagicMock()
        mock_producer.close.side_effect = Exception("Close failed")
        mock_producer_class.return_value = mock_producer

        producer = KafkaNewsProducer()
        # Should not raise exception
        producer.close()

        mock_producer.close.assert_called_once()

    @patch('builtins.open', new_callable=mock_open, read_data='{"type": "record"}')
    @patch('src.clients.kafka_producer.SchemaRegistryClient')
    @patch('src.clients.kafka_producer.AvroSerializer')
    @patch('src.clients.kafka_producer.Producer')
    def test_delivery_report_success(self, mock_producer_class, mock_serializer_class, mock_registry_class, mock_file):
        """Test delivery report callback on success."""
        mock_producer = MagicMock()
        mock_producer_class.return_value = mock_producer

        producer = KafkaNewsProducer()

        # Mock message
        mock_msg = MagicMock()
        mock_msg.topic.return_value = "news_validated"
        mock_msg.partition.return_value = 0

        # Call delivery report with no error
        producer._delivery_report(None, mock_msg)

        # Should not raise exception

    @patch('builtins.open', new_callable=mock_open, read_data='{"type": "record"}')
    @patch('src.clients.kafka_producer.SchemaRegistryClient')
    @patch('src.clients.kafka_producer.AvroSerializer')
    @patch('src.clients.kafka_producer.Producer')
    def test_delivery_report_error(self, mock_producer_class, mock_serializer_class, mock_registry_class, mock_file):
        """Test delivery report callback on error."""
        mock_producer = MagicMock()
        mock_producer_class.return_value = mock_producer

        producer = KafkaNewsProducer()

        # Call delivery report with error
        producer._delivery_report(Exception("Delivery failed"), None)

        # Should not raise exception

