"""Kafka consumer for semantic groups."""

from confluent_kafka import Consumer, KafkaError
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroDeserializer
from confluent_kafka.serialization import SerializationContext, MessageField
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
        self.consumer: Optional[Consumer] = None
        self.topic = "semantic_groups"
        self.schema_registry_client: Optional[SchemaRegistryClient] = None
        self.avro_deserializer: Optional[AvroDeserializer] = None

    def connect(self) -> bool:
        """Connect to Kafka.

        Returns:
            True if connection successful
        """
        try:
            # Initialize schema registry client
            self.schema_registry_client = SchemaRegistryClient(
                {"url": self.config.kafka.schema_registry_url}
            )

            # Initialize Avro deserializer
            self.avro_deserializer = AvroDeserializer(self.schema_registry_client)

            consumer_config = {
                "bootstrap.servers": self.config.kafka.brokers,
                "group.id": self.config.kafka.consumer_group,
                "auto.offset.reset": "earliest",
                "enable.auto.commit": False,
                "isolation.level": "read_committed",  # Exactly-once semantics
            }

            self.consumer = Consumer(consumer_config)
            self.consumer.subscribe([self.topic])

            logger.info(
                "Kafka consumer connected",
                bootstrap_servers=self.config.kafka.brokers,
                topic=self.topic,
            )
            return True

        except Exception as e:
            logger.error("Failed to connect to Kafka", error=str(e), exc_info=True)
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
            msg = self.consumer.poll(timeout_ms / 1000)

            if msg is None:
                return None

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    # End of partition, not an error
                    return None
                else:
                    logger.warning("Consumer error", error=str(msg.error()))
                    return None

            # Deserialize Avro message
            try:
                raw_value = msg.value()
                logger.debug(
                    "Raw message value",
                    length=len(raw_value) if raw_value else 0,
                    first_bytes=raw_value[:20].hex() if raw_value else None,
                )

                ctx = SerializationContext(msg.topic(), MessageField.VALUE)
                message_data = self.avro_deserializer(raw_value, ctx)

                logger.debug(
                    "Deserialized message",
                    message_type=type(message_data),
                    message_keys=list(message_data.keys()) if isinstance(message_data, dict) else None,
                )
            except Exception as e:
                logger.error(
                    "Error deserializing Avro message",
                    error=str(e),
                    exc_info=True,
                    partition=msg.partition(),
                    offset=msg.offset(),
                )
                return None

            logger.debug(
                "Message consumed",
                topic=msg.topic(),
                partition=msg.partition(),
                offset=msg.offset(),
                group_id=message_data.get("group_id") if message_data else None,
            )

            return message_data

        except Exception as e:
            logger.warning("Error consuming message", error=str(e), exc_info=True)
            return None

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
            logger.error("Error committing offset", error=str(e), exc_info=True)
            return False

    def close(self):
        """Close consumer connection."""
        if self.consumer:
            self.consumer.close()
            logger.info("Kafka consumer closed")

