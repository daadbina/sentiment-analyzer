"""Kafka producer for embeddings topic."""

import logging
import json
from typing import Dict, Callable, Optional
from confluent_kafka import Producer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer

from src.config import config
from src.exceptions import KafkaProducerError

logger = logging.getLogger(__name__)


class SerializationContext:
    """Simple serialization context for Avro serializer."""

    def __init__(self, topic: str, field: str = "value"):
        """Initialize context with topic name and field."""
        self.topic = topic
        self.field = field


class KafkaProducer:
    """Kafka producer for embeddings topic."""

    def __init__(self):
        """Initialize Kafka producer."""
        self.config = config.kafka
        self.producer = None
        self.serializer = None

    def initialize(self) -> None:
        """Initialize producer and schema registry."""
        try:
            logger.info(
                f"Initializing Kafka producer for topic: {self.config.output_topic}"
            )

            # Initialize schema registry
            logger.debug(f"Connecting to schema registry: {self.config.schema_registry_url}")
            schema_registry_client = SchemaRegistryClient(
                {"url": self.config.schema_registry_url}
            )

            # Get schema
            schema_str = self._get_embeddings_schema()
            logger.debug(f"Using Avro schema: {schema_str}")

            # Create Avro serializer
            self.serializer = AvroSerializer(
                schema_registry_client,
                schema_str=schema_str,
            )

            logger.debug("Avro serializer created successfully")

            # Create producer
            producer_config = {
                "bootstrap.servers": self.config.brokers,
                "acks": "all",
                "retries": 3,
                "max.in.flight.requests.per.connection": 1,
            }

            self.producer = Producer(producer_config)
            logger.debug(f"Producer created with config: {producer_config}")

            logger.info("Kafka producer initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}", exc_info=True)
            raise KafkaProducerError(
                f"Failed to initialize Kafka producer: {e}"
            )

    def produce_message(
        self,
        message: Dict,
        key: Optional[str] = None,
        callback: Optional[Callable] = None,
    ) -> None:
        """
        Produce a message to Kafka.

        Args:
            message: Message dictionary to produce
            key: Optional message key
            callback: Optional delivery callback

        Raises:
            KafkaProducerError: If production fails
        """
        try:
            logger.debug(f"Serializing message: {message}")

            # Create serialization context with topic information
            ctx = SerializationContext(self.config.output_topic)

            # Serialize the message with proper context
            serialized_value = self.serializer(message, ctx)

            logger.debug(f"Serialized value type: {type(serialized_value)}, length: {len(serialized_value) if serialized_value else 0}")

            if serialized_value is None:
                logger.error(f"Serializer returned None for message: {message}")
                raise KafkaProducerError("Avro serializer returned None")

            logger.debug(f"Producing message to {self.config.output_topic}")

            self.producer.produce(
                topic=self.config.output_topic,
                key=key.encode() if key else None,
                value=serialized_value,
                on_delivery=callback or self._delivery_callback,
            )

            logger.debug(f"Produced message to {self.config.output_topic}")

        except Exception as e:
            logger.error(f"Failed to produce message: {e}", exc_info=True)
            raise KafkaProducerError(f"Failed to produce message: {e}")

    def flush(self, timeout_ms: int = 10000) -> int:
        """
        Flush pending messages.

        Args:
            timeout_ms: Timeout in milliseconds

        Returns:
            Number of messages still in queue
        """
        remaining = self.producer.flush(timeout_ms)
        if remaining > 0:
            logger.warning(f"{remaining} messages still in queue after flush")
        return remaining

    def close(self) -> None:
        """Close producer."""
        try:
            if self.producer:
                self.flush()
                # Try to close the producer
                if hasattr(self.producer, 'close'):
                    self.producer.close()
                logger.info("Kafka producer closed")
        except Exception as e:
            logger.warning(f"Error closing Kafka producer: {e}")

    @staticmethod
    def _delivery_callback(err, msg):
        """Delivery callback for produced messages."""
        if err:
            logger.error(f"Message delivery failed: {err}")
        else:
            logger.debug(
                f"Message delivered to {msg.topic()} "
                f"[{msg.partition()}] at offset {msg.offset()}"
            )

    @staticmethod
    def _get_embeddings_schema() -> str:
        """Get Avro schema for embeddings topic."""
        return json.dumps({
            "type": "record",
            "name": "EmbeddingMessage",
            "namespace": "com.sentiment.embeddings",
            "fields": [
                {"name": "article_id", "type": "string"},
                {"name": "embedding_id", "type": "string"},
                {"name": "model_name", "type": "string"},
                {"name": "language", "type": "string"},
                {"name": "embedding_dimension", "type": "int"},
                {"name": "timestamp", "type": "long"},
                {"name": "processing_time_ms", "type": "float"},
                # Article content fields for downstream semantic processing
                # All new fields have default values for backward compatibility
                {"name": "title", "type": ["null", "string"], "default": None},
                {"name": "content", "type": ["null", "string"], "default": None},
                {"name": "url", "type": ["null", "string"], "default": None},
                {"name": "published_at", "type": ["null", "string"], "default": None},
                {"name": "publisher_id", "type": ["null", "string"], "default": None},
                {"name": "source", "type": ["null", "string"], "default": None},
                {"name": "domain", "type": ["null", "string"], "default": None},
                {"name": "embedded_at", "type": "long", "default": 0},
            ],
        })

