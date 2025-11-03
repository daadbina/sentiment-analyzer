"""Tests for Kafka consumer."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from confluent_kafka import KafkaError, Message
from src.clients.kafka_consumer import KafkaNewsConsumer
from src.models import NewsRaw
from src.exceptions import KafkaError as KafkaErrorException


class TestKafkaNewsConsumer:
    """Test Kafka consumer functionality."""

    @patch('src.clients.kafka_consumer.SchemaRegistryClient')
    @patch('src.clients.kafka_consumer.AvroDeserializer')
    @patch('src.clients.kafka_consumer.Consumer')
    def test_consumer_initialization(self, mock_consumer_class, mock_deserializer_class, mock_registry_class):
        """Test consumer initialization."""
        mock_consumer = MagicMock()
        mock_consumer_class.return_value = mock_consumer
        mock_deserializer = MagicMock()
        mock_deserializer_class.return_value = mock_deserializer

        consumer = KafkaNewsConsumer()

        assert consumer.consumer is not None
        assert consumer.deserializer is not None
        mock_consumer_class.assert_called_once()

    @patch('src.clients.kafka_consumer.SchemaRegistryClient')
    @patch('src.clients.kafka_consumer.AvroDeserializer')
    @patch('src.clients.kafka_consumer.Consumer')
    def test_consumer_initialization_failure(self, mock_consumer_class, mock_deserializer_class, mock_registry_class):
        """Test consumer initialization failure."""
        mock_consumer_class.side_effect = Exception("Connection failed")

        with pytest.raises(KafkaErrorException):
            KafkaNewsConsumer()

    @patch('src.clients.kafka_consumer.SchemaRegistryClient')
    @patch('src.clients.kafka_consumer.AvroDeserializer')
    @patch('src.clients.kafka_consumer.Consumer')
    def test_subscribe_to_topics(self, mock_consumer_class, mock_deserializer_class, mock_registry_class):
        """Test subscribing to topics."""
        mock_consumer = MagicMock()
        mock_consumer_class.return_value = mock_consumer

        consumer = KafkaNewsConsumer()
        consumer.subscribe(['news_raw'])

        mock_consumer.subscribe.assert_called_once_with(['news_raw'])

    @patch('src.clients.kafka_consumer.SchemaRegistryClient')
    @patch('src.clients.kafka_consumer.AvroDeserializer')
    @patch('src.clients.kafka_consumer.Consumer')
    def test_subscribe_without_consumer(self, mock_consumer_class, mock_deserializer_class, mock_registry_class):
        """Test subscribing without initialized consumer."""
        mock_consumer_class.return_value = None

        consumer = KafkaNewsConsumer()
        consumer.consumer = None

        with pytest.raises(KafkaErrorException):
            consumer.subscribe(['news_raw'])

    @patch('src.clients.kafka_consumer.SchemaRegistryClient')
    @patch('src.clients.kafka_consumer.AvroDeserializer')
    @patch('src.clients.kafka_consumer.Consumer')
    def test_poll_message(self, mock_consumer_class, mock_deserializer_class, mock_registry_class):
        """Test polling for message."""
        mock_consumer = MagicMock()
        mock_message = MagicMock()
        mock_message.error.return_value = None
        mock_consumer.poll.return_value = mock_message
        mock_consumer_class.return_value = mock_consumer

        consumer = KafkaNewsConsumer()
        result = consumer.poll(1000)

        assert result == mock_message
        mock_consumer.poll.assert_called_once_with(1000)

    @patch('src.clients.kafka_consumer.SchemaRegistryClient')
    @patch('src.clients.kafka_consumer.AvroDeserializer')
    @patch('src.clients.kafka_consumer.Consumer')
    def test_poll_timeout(self, mock_consumer_class, mock_deserializer_class, mock_registry_class):
        """Test poll timeout."""
        mock_consumer = MagicMock()
        mock_consumer.poll.return_value = None
        mock_consumer_class.return_value = mock_consumer

        consumer = KafkaNewsConsumer()
        result = consumer.poll(1000)

        assert result is None

    @patch('src.clients.kafka_consumer.SchemaRegistryClient')
    @patch('src.clients.kafka_consumer.AvroDeserializer')
    @patch('src.clients.kafka_consumer.Consumer')
    def test_poll_partition_eof(self, mock_consumer_class, mock_deserializer_class, mock_registry_class):
        """Test poll partition EOF."""
        mock_consumer = MagicMock()
        mock_message = MagicMock()
        mock_error = MagicMock()
        mock_error.code.return_value = KafkaError._PARTITION_EOF
        mock_message.error.return_value = mock_error
        mock_consumer.poll.return_value = mock_message
        mock_consumer_class.return_value = mock_consumer

        consumer = KafkaNewsConsumer()
        result = consumer.poll(1000)

        assert result is None

    @patch('src.clients.kafka_consumer.SchemaRegistryClient')
    @patch('src.clients.kafka_consumer.AvroDeserializer')
    @patch('src.clients.kafka_consumer.Consumer')
    def test_poll_error(self, mock_consumer_class, mock_deserializer_class, mock_registry_class):
        """Test poll error."""
        mock_consumer = MagicMock()
        mock_message = MagicMock()
        mock_error = MagicMock()
        mock_error.code.return_value = KafkaError.UNKNOWN
        mock_message.error.return_value = mock_error
        mock_consumer.poll.return_value = mock_message
        mock_consumer_class.return_value = mock_consumer

        consumer = KafkaNewsConsumer()

        with pytest.raises(KafkaErrorException):
            consumer.poll(1000)

    @patch('src.clients.kafka_consumer.SchemaRegistryClient')
    @patch('src.clients.kafka_consumer.AvroDeserializer')
    @patch('src.clients.kafka_consumer.Consumer')
    def test_deserialize_message(self, mock_consumer_class, mock_deserializer_class, mock_registry_class):
        """Test message deserialization."""
        mock_consumer = MagicMock()
        mock_consumer_class.return_value = mock_consumer
        mock_deserializer = MagicMock()
        mock_deserializer_class.return_value = mock_deserializer

        # Mock deserialized data
        mock_deserializer.return_value = {
            'article_id': 'art_123',
            'canonical_url': 'https://example.com',
            'title': 'Test Article',
            'body': 'Test body',
            'url': 'https://example.com',
            'published_at': '2025-11-03T10:00:00Z',
            'language': 'en',
            'source': 'test_source',
            'crawled_at': '2025-11-03T11:00:00Z',
            'checksum': 'abc123',
            'validation_score': 0.8,
            'schema_version': '1.0.0',
            'ingest_job_id': 'job_123',
            'publisher_id': 'pub_123',
            'extraction_method': 'rss',
        }

        mock_message = MagicMock()
        mock_message.value.return_value = b'test_data'

        consumer = KafkaNewsConsumer()
        result = consumer.deserialize_message(mock_message)

        assert isinstance(result, NewsRaw)
        assert result.article_id == 'art_123'
        assert result.title == 'Test Article'

    @patch('src.clients.kafka_consumer.SchemaRegistryClient')
    @patch('src.clients.kafka_consumer.AvroDeserializer')
    @patch('src.clients.kafka_consumer.Consumer')
    def test_deserialize_message_failure(self, mock_consumer_class, mock_deserializer_class, mock_registry_class):
        """Test message deserialization failure."""
        mock_consumer = MagicMock()
        mock_consumer_class.return_value = mock_consumer
        mock_deserializer = MagicMock()
        mock_deserializer.side_effect = Exception("Deserialization failed")
        mock_deserializer_class.return_value = mock_deserializer

        mock_message = MagicMock()

        consumer = KafkaNewsConsumer()

        with pytest.raises(KafkaErrorException):
            consumer.deserialize_message(mock_message)

    @patch('src.clients.kafka_consumer.SchemaRegistryClient')
    @patch('src.clients.kafka_consumer.AvroDeserializer')
    @patch('src.clients.kafka_consumer.Consumer')
    def test_commit_message(self, mock_consumer_class, mock_deserializer_class, mock_registry_class):
        """Test committing message offset."""
        mock_consumer = MagicMock()
        mock_consumer_class.return_value = mock_consumer

        mock_message = MagicMock()
        mock_message.partition.return_value = 0

        consumer = KafkaNewsConsumer()
        consumer.commit(mock_message, asynchronous=False)

        mock_consumer.commit.assert_called_once_with(mock_message, asynchronous=False)

    @patch('src.clients.kafka_consumer.SchemaRegistryClient')
    @patch('src.clients.kafka_consumer.AvroDeserializer')
    @patch('src.clients.kafka_consumer.Consumer')
    def test_commit_message_failure(self, mock_consumer_class, mock_deserializer_class, mock_registry_class):
        """Test commit failure."""
        mock_consumer = MagicMock()
        mock_consumer.commit.side_effect = Exception("Commit failed")
        mock_consumer_class.return_value = mock_consumer

        mock_message = MagicMock()

        consumer = KafkaNewsConsumer()

        with pytest.raises(KafkaErrorException):
            consumer.commit(mock_message)

    @patch('src.clients.kafka_consumer.SchemaRegistryClient')
    @patch('src.clients.kafka_consumer.AvroDeserializer')
    @patch('src.clients.kafka_consumer.Consumer')
    def test_get_consumer_lag(self, mock_consumer_class, mock_deserializer_class, mock_registry_class):
        """Test getting consumer lag."""
        mock_consumer = MagicMock()
        mock_partition = MagicMock()
        mock_partition.partition = 0
        mock_consumer.assignment.return_value = [mock_partition]
        mock_consumer.get_watermark_offsets.return_value = (0, 100)
        mock_committed = MagicMock()
        mock_committed.offset = 50
        mock_consumer.committed.return_value = [mock_committed]
        mock_consumer_class.return_value = mock_consumer

        consumer = KafkaNewsConsumer()
        lag = consumer.get_consumer_lag()

        assert lag[0] == 50  # 100 - 50 = 50

    @patch('src.clients.kafka_consumer.SchemaRegistryClient')
    @patch('src.clients.kafka_consumer.AvroDeserializer')
    @patch('src.clients.kafka_consumer.Consumer')
    def test_get_consumer_lag_no_consumer(self, mock_consumer_class, mock_deserializer_class, mock_registry_class):
        """Test getting consumer lag without consumer."""
        mock_consumer_class.return_value = None

        consumer = KafkaNewsConsumer()
        consumer.consumer = None
        lag = consumer.get_consumer_lag()

        assert lag == {}

    @patch('src.clients.kafka_consumer.SchemaRegistryClient')
    @patch('src.clients.kafka_consumer.AvroDeserializer')
    @patch('src.clients.kafka_consumer.Consumer')
    def test_close_consumer(self, mock_consumer_class, mock_deserializer_class, mock_registry_class):
        """Test closing consumer."""
        mock_consumer = MagicMock()
        mock_consumer_class.return_value = mock_consumer

        consumer = KafkaNewsConsumer()
        consumer.close()

        mock_consumer.close.assert_called_once()

    @patch('src.clients.kafka_consumer.SchemaRegistryClient')
    @patch('src.clients.kafka_consumer.AvroDeserializer')
    @patch('src.clients.kafka_consumer.Consumer')
    def test_close_consumer_error(self, mock_consumer_class, mock_deserializer_class, mock_registry_class):
        """Test closing consumer with error."""
        mock_consumer = MagicMock()
        mock_consumer.close.side_effect = Exception("Close failed")
        mock_consumer_class.return_value = mock_consumer

        consumer = KafkaNewsConsumer()
        # Should not raise exception
        consumer.close()

        mock_consumer.close.assert_called_once()

    @patch('src.clients.kafka_consumer.SchemaRegistryClient')
    @patch('src.clients.kafka_consumer.AvroDeserializer')
    @patch('src.clients.kafka_consumer.Consumer')
    def test_seek_to_offset_success(self, mock_consumer_class, mock_deserializer_class, mock_registry_class):
        """Test seeking to offset - success."""
        mock_consumer = MagicMock()
        mock_consumer_class.return_value = mock_consumer

        consumer = KafkaNewsConsumer()
        consumer.seek_to_offset(0, 100)

        mock_consumer.seek.assert_called_once()

    @patch('src.clients.kafka_consumer.SchemaRegistryClient')
    @patch('src.clients.kafka_consumer.AvroDeserializer')
    @patch('src.clients.kafka_consumer.Consumer')
    def test_seek_to_offset_error(self, mock_consumer_class, mock_deserializer_class, mock_registry_class):
        """Test seeking to offset - error."""
        mock_consumer = MagicMock()
        mock_consumer.seek.side_effect = Exception("Seek failed")
        mock_consumer_class.return_value = mock_consumer

        consumer = KafkaNewsConsumer()

        with pytest.raises(KafkaErrorException):
            consumer.seek_to_offset(0, 100)

    @patch('src.clients.kafka_consumer.SchemaRegistryClient')
    @patch('src.clients.kafka_consumer.AvroDeserializer')
    @patch('src.clients.kafka_consumer.Consumer')
    def test_seek_to_offset_not_initialized(self, mock_consumer_class, mock_deserializer_class, mock_registry_class):
        """Test seeking to offset when consumer not initialized."""
        mock_consumer_class.side_effect = Exception("Init failed")

        with pytest.raises(KafkaErrorException):
            consumer = KafkaNewsConsumer()

    @patch('src.clients.kafka_consumer.SchemaRegistryClient')
    @patch('src.clients.kafka_consumer.AvroDeserializer')
    @patch('src.clients.kafka_consumer.Consumer')
    def test_get_current_offset_success(self, mock_consumer_class, mock_deserializer_class, mock_registry_class):
        """Test getting current offset - success."""
        mock_consumer = MagicMock()
        mock_offset = MagicMock()
        mock_offset.offset = 150
        mock_consumer.committed.return_value = [mock_offset]
        mock_consumer_class.return_value = mock_consumer

        consumer = KafkaNewsConsumer()
        offset = consumer.get_current_offset(0)

        assert offset == 150
        mock_consumer.committed.assert_called_once()

    @patch('src.clients.kafka_consumer.SchemaRegistryClient')
    @patch('src.clients.kafka_consumer.AvroDeserializer')
    @patch('src.clients.kafka_consumer.Consumer')
    def test_get_current_offset_no_offset(self, mock_consumer_class, mock_deserializer_class, mock_registry_class):
        """Test getting current offset when no offset committed."""
        mock_consumer = MagicMock()
        mock_offset = MagicMock()
        mock_offset.offset = -1
        mock_consumer.committed.return_value = [mock_offset]
        mock_consumer_class.return_value = mock_consumer

        consumer = KafkaNewsConsumer()
        offset = consumer.get_current_offset(0)

        assert offset == 0

    @patch('src.clients.kafka_consumer.SchemaRegistryClient')
    @patch('src.clients.kafka_consumer.AvroDeserializer')
    @patch('src.clients.kafka_consumer.Consumer')
    def test_get_current_offset_error(self, mock_consumer_class, mock_deserializer_class, mock_registry_class):
        """Test getting current offset - error."""
        mock_consumer = MagicMock()
        mock_consumer.committed.side_effect = Exception("Get offset failed")
        mock_consumer_class.return_value = mock_consumer

        consumer = KafkaNewsConsumer()

        with pytest.raises(KafkaErrorException):
            consumer.get_current_offset(0)

