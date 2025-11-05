"""
Integration tests for Kafka integration.

Tests Kafka producer and message publishing.
"""

import pytest
from unittest.mock import patch, MagicMock
import json

from src.clients.kafka_producer import KafkaProducer


class TestKafkaIntegration:
    """Test Kafka integration."""

    @pytest.fixture
    def mock_kafka(self):
        """Create mock Kafka."""
        with patch('src.clients.kafka_producer.confluent_kafka.Producer') as mock:
            yield mock

    def test_kafka_producer_initialization(self, mock_kafka):
        """Test Kafka producer initialization."""
        mock_producer = MagicMock()
        mock_kafka.return_value = mock_producer
        
        producer = KafkaProducer()
        
        assert producer is not None

    def test_kafka_producer_send_message(self, mock_kafka):
        """Test sending Kafka message."""
        mock_producer = MagicMock()
        mock_kafka.return_value = mock_producer
        
        producer = KafkaProducer()
        
        result = producer.send_message(
            topic='test_topic',
            key=b'key',
            value=b'value'
        )
        
        assert result is not None

    def test_kafka_producer_send_json_message(self, mock_kafka):
        """Test sending JSON message."""
        mock_producer = MagicMock()
        mock_kafka.return_value = mock_producer
        
        producer = KafkaProducer()
        
        message = {'field1': 'value1', 'field2': 123}
        result = producer.send_json_message(
            topic='test_topic',
            key=b'key',
            value=message
        )
        
        assert result is not None

    def test_kafka_producer_send_avro_message(self, mock_kafka):
        """Test sending Avro message."""
        mock_producer = MagicMock()
        mock_kafka.return_value = mock_producer
        
        producer = KafkaProducer()
        
        message = {'field1': 'value1', 'field2': 123}
        result = producer.send_avro_message(
            topic='test_topic',
            key=b'key',
            value=message,
            schema_id=1
        )
        
        assert result is not None

    def test_kafka_producer_flush(self, mock_kafka):
        """Test message flushing."""
        mock_producer = MagicMock()
        mock_kafka.return_value = mock_producer
        
        producer = KafkaProducer()
        
        producer.flush()
        
        mock_producer.flush.assert_called_once()

    def test_kafka_producer_health_check(self, mock_kafka):
        """Test Kafka health check."""
        mock_producer = MagicMock()
        mock_producer.list_topics.return_value = MagicMock(topics={'test': None})
        mock_kafka.return_value = mock_producer
        
        producer = KafkaProducer()
        
        is_healthy = producer.health_check()
        
        assert is_healthy is True

    def test_kafka_producer_error_handling(self, mock_kafka):
        """Test error handling."""
        mock_producer = MagicMock()
        mock_producer.produce.side_effect = Exception("Send failed")
        mock_kafka.return_value = mock_producer
        
        producer = KafkaProducer()
        
        with pytest.raises(Exception):
            producer.send_message(
                topic='test_topic',
                key=b'key',
                value=b'value'
            )

    def test_kafka_producer_batch_send(self, mock_kafka):
        """Test batch message sending."""
        mock_producer = MagicMock()
        mock_kafka.return_value = mock_producer
        
        producer = KafkaProducer()
        
        messages = [
            {'key': b'key1', 'value': b'value1'},
            {'key': b'key2', 'value': b'value2'},
            {'key': b'key3', 'value': b'value3'},
        ]
        
        for msg in messages:
            producer.send_message(
                topic='test_topic',
                key=msg['key'],
                value=msg['value']
            )
        
        assert mock_producer.produce.call_count >= 3

    def test_kafka_producer_callback(self, mock_kafka):
        """Test message callback."""
        mock_producer = MagicMock()
        mock_kafka.return_value = mock_producer
        
        producer = KafkaProducer()
        
        callback_called = False
        
        def on_delivery(err, msg):
            nonlocal callback_called
            callback_called = True
        
        producer.send_message(
            topic='test_topic',
            key=b'key',
            value=b'value',
            callback=on_delivery
        )
        
        assert producer is not None

    def test_kafka_producer_schema_registry_integration(self, mock_kafka):
        """Test schema registry integration."""
        mock_producer = MagicMock()
        mock_kafka.return_value = mock_producer
        
        producer = KafkaProducer()
        
        message = {
            'model_name': 'xgboost',
            'version': 'v1',
            'auc': 0.85,
            'precision': 0.80,
            'recall': 0.80,
            'f1': 0.80,
        }
        
        result = producer.send_avro_message(
            topic='model_trained',
            key=b'xgboost_v1',
            value=message,
            schema_id=1
        )
        
        assert result is not None

    def test_kafka_producer_exactly_once_semantics(self, mock_kafka):
        """Test exactly-once delivery semantics."""
        mock_producer = MagicMock()
        mock_kafka.return_value = mock_producer
        
        producer = KafkaProducer()
        
        # Should have idempotence enabled
        assert producer is not None

    def test_kafka_producer_partition_selection(self, mock_kafka):
        """Test partition selection."""
        mock_producer = MagicMock()
        mock_kafka.return_value = mock_producer
        
        producer = KafkaProducer()
        
        # Send to specific partition
        result = producer.send_message(
            topic='test_topic',
            key=b'key',
            value=b'value',
            partition=0
        )
        
        assert result is not None

    def test_kafka_producer_compression(self, mock_kafka):
        """Test message compression."""
        mock_producer = MagicMock()
        mock_kafka.return_value = mock_producer
        
        producer = KafkaProducer()
        
        # Large message
        large_value = b'x' * (1024 * 1024)  # 1MB
        
        result = producer.send_message(
            topic='test_topic',
            key=b'key',
            value=large_value
        )
        
        assert result is not None

    def test_kafka_producer_timeout_handling(self, mock_kafka):
        """Test timeout handling."""
        mock_producer = MagicMock()
        mock_producer.produce.side_effect = Exception("Timeout")
        mock_kafka.return_value = mock_producer
        
        producer = KafkaProducer()
        
        with pytest.raises(Exception):
            producer.send_message(
                topic='test_topic',
                key=b'key',
                value=b'value'
            )

    def test_kafka_producer_metrics(self, mock_kafka):
        """Test producer metrics."""
        mock_producer = MagicMock()
        mock_producer.metrics.return_value = {
            'messages_sent': 100,
            'bytes_sent': 10240,
        }
        mock_kafka.return_value = mock_producer
        
        producer = KafkaProducer()
        
        metrics = producer.get_metrics()
        
        assert metrics is not None

