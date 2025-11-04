"""Kafka producer for news_canonical topic."""

import logging
import json
from typing import Optional
from confluent_kafka import Producer
from confluent_kafka.schema_registry import SchemaRegistryClient, SerializationContext, MessageField
from confluent_kafka.schema_registry.avro import AvroSerializer

from src.config import get_settings
from src.exceptions import KafkaError as KafkaErrorException
from src.models import NewsCanonicalMessage

logger = logging.getLogger(__name__)


class KafkaCanonicalProducer:
    """Kafka producer for publishing canonicalized news."""

    def __init__(self):
        """Initialize Kafka producer."""
        self.settings = get_settings()
        self.producer: Optional[Producer] = None
        self.canonical_serializer: Optional[AvroSerializer] = None
        self._initialize()

    def _initialize(self) -> None:
        """Initialize producer and serializers."""
        try:
            # Initialize schema registry client
            schema_registry_client = SchemaRegistryClient(
                {
                    "url": self.settings.kafka.schema_registry_url,
                }
            )

            # Load schema
            with open("schemas/news_canonical.avsc", "r") as f:
                canonical_schema = f.read()

            # Initialize serializer
            self.canonical_serializer = AvroSerializer(
                schema_registry_client,
                canonical_schema,
            )

            # Producer configuration with idempotence for exactly-once
            producer_config = {
                "bootstrap.servers": self.settings.kafka.brokers,
                "acks": "all",  # Wait for all replicas
                "retries": 3,
                "max.in.flight.requests.per.connection": 1,  # Preserve order
                "enable.idempotence": True,  # Prevent duplicates
                "request.timeout.ms": self.settings.kafka.processing_timeout_seconds * 1000,
            }

            self.producer = Producer(producer_config)
            logger.info("Kafka producer initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            raise KafkaErrorException(f"Producer initialization failed: {e}")

    def _delivery_report(self, err, msg):
        """Delivery report callback."""
        if err is not None:
            logger.error(f"Message delivery failed: {err}")
        else:
            logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}]")

    def publish_canonical(self, message: NewsCanonicalMessage) -> None:
        """Publish canonicalized message to news_canonical topic.

        Args:
            message: Canonicalized news message

        Raises:
            KafkaErrorException: If publishing fails
        """
        if not self.producer or not self.canonical_serializer:
            raise KafkaErrorException("Producer not initialized")

        try:
            # Convert to dict for serialization
            message_dict = message.to_dict()

            # Create serialization context with topic
            ctx = SerializationContext(self.settings.kafka.output_topic, MessageField.VALUE)

            # Serialize and publish
            self.producer.produce(
                topic=self.settings.kafka.output_topic,
                key=message.article_id.encode("utf-8"),
                value=self.canonical_serializer(message_dict, ctx),
                on_delivery=self._delivery_report,
            )

            # Flush to ensure message is sent immediately
            self.producer.flush(timeout=5)

            logger.debug(f"Published canonical message: {message.article_id}")

        except Exception as e:
            logger.error(f"Failed to publish canonical message: {e}")
            raise KafkaErrorException(f"Publishing failed: {e}")

    def publish_dlq(self, article_id: str, error: str, original_message: dict) -> None:
        """Publish failed message to dead-letter queue.

        Args:
            article_id: Article ID
            error: Error description
            original_message: Original message that failed
        """
        if not self.producer:
            logger.error("Producer not initialized, cannot publish to DLQ")
            return

        try:
            dlq_message = {
                "article_id": article_id,
                "error": error,
                "original_message": original_message,
            }

            self.producer.produce(
                topic=self.settings.kafka.dlq_topic,
                key=article_id.encode("utf-8"),
                value=json.dumps(dlq_message).encode("utf-8"),
                on_delivery=self._delivery_report,
            )

            # Flush to ensure message is sent immediately
            self.producer.flush(timeout=5)

            logger.warning(f"Published message to DLQ: {error}")

        except Exception as e:
            logger.error(f"Failed to publish to DLQ: {e}")

    def flush(self, timeout_ms: int = 30000) -> int:
        """Flush pending messages.

        Args:
            timeout_ms: Flush timeout in milliseconds

        Returns:
            Number of messages still in queue after timeout
        """
        if not self.producer:
            return 0

        try:
            remaining = self.producer.flush(timeout_ms)
            if remaining > 0:
                logger.warning(f"{remaining} messages still in queue after flush")
            return remaining
        except Exception as e:
            logger.error(f"Flush failed: {e}")
            return -1

    def close(self) -> None:
        """Close producer connection."""
        if self.producer:
            try:
                self.flush()
                self.producer.close()
                logger.info("Kafka producer closed")
            except Exception as e:
                logger.error(f"Error closing producer: {e}")

