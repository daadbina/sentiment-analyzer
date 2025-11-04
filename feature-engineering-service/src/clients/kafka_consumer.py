"""Kafka consumer for semantic groups."""

from confluent_kafka import Consumer, KafkaError
from confluent_kafka.avro import AvroConsumer
from typing import Optional, Dict, Any
import json
from ..config import config
from ..utils import StructuredLogger, TraceContext
from ..exceptions import KafkaError as KafkaErrorException

logger = StructuredLogger(__name__)


class SemanticGroupConsumer:
    """Consume semantic groups from Kafka."""

    def __init__(self):
        """Initialize consumer."""
        self.config = config
        self.consumer: Optional[AvroConsumer] = None
        self.topic = "semantic_groups"

    def connect(self) -> bool:
        """Connect to Kafka.

        Returns:
            True if connection successful
        """
        try:
            consumer_config = {
                "bootstrap.servers": self.config.kafka.bootstrap_servers,
                "group.id": self.config.kafka.consumer_group,
                "auto.offset.reset": "earliest",
                "enable.auto.commit": False,
                "isolation.level": "read_committed",  # Exactly-once semantics
                "schema.registry.url": self.config.kafka.schema_registry_url,
            }

            self.consumer = AvroConsumer(consumer_config)
            self.consumer.subscribe([self.topic])

            logger.info(
                "Kafka consumer connected",
                bootstrap_servers=self.config.kafka.bootstrap_servers,
                topic=self.topic,
            )
            return True

        except Exception as e:
            logger.error("Failed to connect to Kafka", error=str(e))
            raise KafkaErrorException(f"Failed to connect to Kafka: {str(e)}")

    def consume_message(self, timeout_ms: int = 1000) -> Optional[Dict[str, Any]]:
        """Consume a single message.

        Args:
            timeout_ms: Timeout in milliseconds

        Returns:
            Message dictionary or None if timeout
        """
        if not self.consumer:
            raise KafkaErrorException("Consumer not connected")

        try:
            msg = self.consumer.poll(timeout_ms)

            if msg is None:
                return None

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    return None
                else:
                    raise KafkaErrorException(f"Consumer error: {msg.error()}")

            # Message is in Avro format, already deserialized
            message_data = msg.value()

            logger.info(
                "Message consumed",
                topic=msg.topic(),
                partition=msg.partition(),
                offset=msg.offset(),
            )

            return message_data

        except Exception as e:
            logger.error("Error consuming message", error=str(e))
            raise KafkaErrorException(f"Error consuming message: {str(e)}")

    def commit_offset(self) -> bool:
        """Commit current offset.

        Returns:
            True if commit successful
        """
        if not self.consumer:
            raise KafkaErrorException("Consumer not connected")

        try:
            self.consumer.commit(asynchronous=False)
            logger.info("Offset committed")
            return True
        except Exception as e:
            logger.error("Error committing offset", error=str(e))
            return False

    def close(self):
        """Close consumer connection."""
        if self.consumer:
            self.consumer.close()
            logger.info("Kafka consumer closed")

