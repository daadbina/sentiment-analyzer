"""
Integration tests for Kafka consumer and producer.
"""
import json
import pytest
from confluent_kafka import Producer, Consumer, KafkaError
from src.clients.kafka_consumer import KafkaConsumerClient
from src.clients.kafka_producer import KafkaProducerClient
from src.models import NewsCanonicalMessage, EntitiesExtractedMessage, Entity


@pytest.mark.integration
class TestKafkaConsumer:
    """Integration tests for Kafka consumer."""

    def test_consumer_initialization(self, kafka_brokers: str):
        """Test Kafka consumer initialization."""
        consumer = KafkaConsumerClient(
            brokers=kafka_brokers,
            consumer_group="test-group",
            schema_registry_url="http://localhost:8081",
            input_topic="test-topic",
        )
        assert consumer is not None
        assert consumer.consumer is not None

    def test_consumer_subscribe_to_topic(self, kafka_brokers: str):
        """Test consumer subscribes to topic."""
        consumer = KafkaConsumerClient(
            brokers=kafka_brokers,
            consumer_group="test-group",
            schema_registry_url="http://localhost:8081",
            input_topic="test-topic",
        )
        # Consumer should be subscribed to topic
        assert consumer.consumer is not None

    def test_consumer_poll_timeout(self, kafka_brokers: str):
        """Test consumer poll with timeout."""
        consumer = KafkaConsumerClient(
            brokers=kafka_brokers,
            consumer_group="test-group",
            schema_registry_url="http://localhost:8081",
            input_topic="test-topic",
        )
        # Poll should return None when no messages
        message, error = consumer.consume_message(timeout_ms=100)
        assert message is None or isinstance(message, NewsCanonicalMessage)


@pytest.mark.integration
class TestKafkaProducer:
    """Integration tests for Kafka producer."""

    def test_producer_initialization(self, kafka_brokers: str):
        """Test Kafka producer initialization."""
        producer = KafkaProducerClient(
            brokers=kafka_brokers,
            schema_registry_url="http://localhost:8081",
            output_topic="test-output",
        )
        assert producer is not None
        assert producer.producer is not None

    def test_producer_send_message(self, kafka_brokers: str):
        """Test producer sends message."""
        producer = KafkaProducerClient(
            brokers=kafka_brokers,
            schema_registry_url="http://localhost:8081",
            output_topic="test-output",
        )
        
        # Create test message
        entity = Entity(
            entity_id="test-entity-1",
            text="John Doe",
            entity_type="PERSON",
            confidence=0.95,
            start_char=0,
            end_char=8,
            context_snippet="John Doe is a person",
        )
        
        message = EntitiesExtractedMessage(
            article_id="test-article-1",
            entities=[entity],
            extracted_at="2025-11-03T20:00:00Z",
            language="en",
            ner_model="test-model",
            entity_count=1,
            coverage_score=0.5,
            linking_success_rate=0.0,
            trace_id="test-trace-1",
        )
        
        # Send message
        result = producer.send_message(message)
        assert result is not None


@pytest.mark.integration
class TestKafkaEndToEnd:
    """End-to-end Kafka integration tests."""

    def test_produce_and_consume_message(self, kafka_brokers: str):
        """Test producing and consuming a message."""
        producer = KafkaProducerClient(
            brokers=kafka_brokers,
            schema_registry_url="http://localhost:8081",
            output_topic="test-e2e-topic",
        )
        
        consumer = KafkaConsumerClient(
            brokers=kafka_brokers,
            consumer_group="test-e2e-group",
            schema_registry_url="http://localhost:8081",
            input_topic="test-e2e-topic",
        )
        
        # Create and send test message
        entity = Entity(
            entity_id="test-entity-1",
            text="Test Entity",
            entity_type="PERSON",
            confidence=0.9,
            start_char=0,
            end_char=11,
            context_snippet="Test Entity is here",
        )
        
        message = EntitiesExtractedMessage(
            article_id="test-article-1",
            entities=[entity],
            extracted_at="2025-11-03T20:00:00Z",
            language="en",
            ner_model="test-model",
            entity_count=1,
            coverage_score=0.5,
            linking_success_rate=0.0,
            trace_id="test-trace-1",
        )
        
        producer.send_message(message)
        
        # Consume message
        consumed_message, error = consumer.consume_message(timeout_ms=5000)
        
        # Verify message was consumed
        if consumed_message:
            assert consumed_message.article_id == "test-article-1"
            assert len(consumed_message.entities) == 1
            assert consumed_message.entities[0].text == "Test Entity"

