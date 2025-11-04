"""Kafka producer for validated and rejected news topics."""

import logging
from typing import Optional
from confluent_kafka import Producer
from confluent_kafka.schema_registry import SchemaRegistryClient, SerializationContext, MessageField
from confluent_kafka.schema_registry.avro import AvroSerializer
from src.config import get_config
from src.exceptions import KafkaError as KafkaErrorException
from src.models import NewsValidated, NewsRejected

logger = logging.getLogger(__name__)


class KafkaNewsProducer:
    """Kafka producer for publishing validated and rejected news."""

    def __init__(self):
        """Initialize Kafka producer."""
        self.config = get_config()
        self.producer: Optional[Producer] = None
        self.validated_serializer: Optional[AvroSerializer] = None
        self.rejected_serializer: Optional[AvroSerializer] = None
        self._initialize()

    def _initialize(self) -> None:
        """Initialize producer and serializers."""
        try:
            # Initialize schema registry client
            schema_registry_client = SchemaRegistryClient(
                {
                    "url": self.config.kafka.schema_registry_url,
                }
            )

            # Load schemas
            with open("schemas/news_validated.avsc", "r") as f:
                validated_schema = f.read()

            with open("schemas/news_rejected.avsc", "r") as f:
                rejected_schema = f.read()

            # Initialize serializers
            self.validated_serializer = AvroSerializer(
                schema_registry_client,
                validated_schema,
            )
            self.rejected_serializer = AvroSerializer(
                schema_registry_client,
                rejected_schema,
            )

            # Producer configuration with idempotence for exactly-once
            producer_config = {
                "bootstrap.servers": self.config.kafka.brokers,
                "acks": "all",  # Wait for all replicas
                "retries": 3,
                "max.in.flight.requests.per.connection": 1,  # Preserve order
                "enable.idempotence": True,  # Prevent duplicates
                "request.timeout.ms": self.config.kafka.processing_timeout_seconds
                * 1000,
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

    def publish_validated(self, message: NewsValidated) -> None:
        """Publish validated message to news_validated topic.

        Args:
            message: Validated news message

        Raises:
            KafkaErrorException: If publishing fails
        """
        if not self.producer or not self.validated_serializer:
            raise KafkaErrorException("Producer not initialized")

        try:
            # Convert to dict for serialization
            message_dict = message.dict()

            # Create serialization context with topic
            ctx = SerializationContext("news_validated", MessageField.VALUE)

            # Serialize and publish
            self.producer.produce(
                topic="news_validated",
                key=message.article_id.encode("utf-8"),
                value=self.validated_serializer(message_dict, ctx),
                on_delivery=self._delivery_report,
            )

            # Flush to ensure message is sent immediately
            self.producer.flush(timeout=5)

            logger.debug(f"Published validated message: {message.article_id}")

        except Exception as e:
            logger.error(f"Failed to publish validated message: {e}")
            raise KafkaErrorException(f"Publishing failed: {e}")

    def publish_rejected(self, message: NewsRejected) -> None:
        """Publish rejected message to news_rejected topic.

        Args:
            message: Rejected news message

        Raises:
            KafkaErrorException: If publishing fails
        """
        if not self.producer or not self.rejected_serializer:
            raise KafkaErrorException("Producer not initialized")

        try:
            # Convert to dict for serialization
            message_dict = message.dict()

            # Create serialization context with topic
            ctx = SerializationContext("news_rejected", MessageField.VALUE)

            # Serialize and publish
            self.producer.produce(
                topic="news_rejected",
                key=message.article_id.encode("utf-8"),
                value=self.rejected_serializer(message_dict, ctx),
                on_delivery=self._delivery_report,
            )

            # Flush to ensure message is sent immediately
            self.producer.flush(timeout=5)

            logger.debug(f"Published rejected message: {message.article_id}")

        except Exception as e:
            logger.error(f"Failed to publish rejected message: {e}")
            raise KafkaErrorException(f"Publishing failed: {e}")

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
