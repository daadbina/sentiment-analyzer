"""Kafka consumer for news_validated topic."""

import logging
from typing import Optional
from confluent_kafka import Consumer, KafkaError, Message
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroDeserializer

from src.config import get_settings
from src.exceptions import KafkaError as KafkaErrorException
from src.models import NewsValidatedMessage

logger = logging.getLogger(__name__)


class KafkaCanonicalConsumer:
    """Kafka consumer for news_validated topic with exactly-once semantics."""

    def __init__(self):
        """Initialize Kafka consumer."""
        self.settings = get_settings()
        self.consumer: Optional[Consumer] = None
        self.deserializer: Optional[AvroDeserializer] = None
        self._initialize()

    def _initialize(self) -> None:
        """Initialize consumer and deserializer."""
        try:
            # Initialize schema registry client
            schema_registry_client = SchemaRegistryClient(
                {
                    "url": self.settings.kafka.schema_registry_url,
                }
            )

            # Initialize Avro deserializer
            self.deserializer = AvroDeserializer(schema_registry_client)

            # Consumer configuration with exactly-once semantics
            consumer_config = {
                "bootstrap.servers": self.settings.kafka.brokers,
                "group.id": self.settings.kafka.consumer_group,
                "auto.offset.reset": "earliest",
                "enable.auto.commit": False,  # Manual commit for exactly-once
                "isolation.level": "read_committed",  # Only read committed messages
                "max.poll.interval.ms": self.settings.kafka.max_poll_interval_ms,
                "session.timeout.ms": 30000,
                "heartbeat.interval.ms": 10000,
            }

            self.consumer = Consumer(consumer_config)
            logger.info("Kafka consumer initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Kafka consumer: {e}")
            raise KafkaErrorException(f"Consumer initialization failed: {e}")

    def subscribe(self, topics: list[str]) -> None:
        """Subscribe to topics.

        Args:
            topics: List of topic names

        Raises:
            KafkaErrorException: If subscription fails
        """
        if not self.consumer:
            raise KafkaErrorException("Consumer not initialized")

        try:
            self.consumer.subscribe(topics)
            logger.info(f"Subscribed to topics: {topics}")
        except Exception as e:
            logger.error(f"Failed to subscribe to topics: {e}")
            raise KafkaErrorException(f"Subscription failed: {e}")

    def poll(self, timeout_ms: int = 1000) -> Optional[Message]:
        """Poll for next message.

        Args:
            timeout_ms: Poll timeout in milliseconds

        Returns:
            Kafka message or None if timeout

        Raises:
            KafkaErrorException: If poll fails
        """
        if not self.consumer:
            raise KafkaErrorException("Consumer not initialized")

        try:
            msg = self.consumer.poll(timeout_ms)

            if msg is None:
                return None

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    return None
                else:
                    raise KafkaErrorException(f"Consumer error: {msg.error()}")

            return msg

        except Exception as e:
            logger.error(f"Poll failed: {e}")
            raise KafkaErrorException(f"Poll failed: {e}")

    def deserialize_message(self, msg: Message) -> NewsValidatedMessage:
        """Deserialize Kafka message to NewsValidatedMessage.

        Args:
            msg: Kafka message

        Returns:
            Deserialized NewsValidatedMessage object

        Raises:
            KafkaErrorException: If deserialization fails
        """
        try:
            if not self.deserializer:
                raise KafkaErrorException("Deserializer not initialized")

            # Deserialize value
            value = self.deserializer(msg.value(), None)

            # Convert to NewsValidatedMessage model
            return NewsValidatedMessage(**value)

        except Exception as e:
            logger.error(f"Deserialization failed: {e}")
            raise KafkaErrorException(f"Deserialization failed: {e}")

    def commit(self, msg: Message, asynchronous: bool = False) -> None:
        """Commit message offset.

        Args:
            msg: Message to commit
            asynchronous: Whether to commit asynchronously

        Raises:
            KafkaErrorException: If commit fails
        """
        if not self.consumer:
            raise KafkaErrorException("Consumer not initialized")

        try:
            self.consumer.commit(msg, asynchronous=asynchronous)
            logger.debug(f"Committed offset for partition {msg.partition()}")
        except Exception as e:
            logger.error(f"Commit failed: {e}")
            raise KafkaErrorException(f"Commit failed: {e}")

    def get_consumer_lag(self) -> dict[str, int]:
        """Get consumer lag per partition.

        Returns:
            Dictionary of partition -> lag
        """
        if not self.consumer:
            return {}

        try:
            lag_dict = {}
            partitions = self.consumer.assignment()

            for partition in partitions:
                low, high = self.consumer.get_watermark_offsets(partition)
                committed_offset = self.consumer.committed([partition])[0].offset

                if committed_offset >= 0:
                    lag = high - committed_offset
                    lag_dict[partition.partition] = lag

            return lag_dict

        except Exception as e:
            logger.error(f"Failed to get consumer lag: {e}")
            return {}

    def close(self) -> None:
        """Close consumer connection."""
        if self.consumer:
            try:
                self.consumer.close()
                logger.info("Kafka consumer closed")
            except Exception as e:
                logger.error(f"Error closing consumer: {e}")

