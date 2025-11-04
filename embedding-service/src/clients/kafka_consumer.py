"""Kafka consumer for news_canonical topic."""

import logging
import json
from typing import Optional, Dict, Callable
from confluent_kafka import Consumer, KafkaError
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroDeserializer

from src.config import config
from src.exceptions import KafkaConsumerError
from src.metrics import embedding_messages_consumed_total, embedding_consumer_lag

logger = logging.getLogger(__name__)


class KafkaConsumer:
    """Kafka consumer for news_canonical topic."""

    def __init__(self):
        """Initialize Kafka consumer."""
        self.config = config.kafka
        self.consumer = None
        self.deserializer = None

    def initialize(self) -> None:
        """Initialize consumer and schema registry."""
        try:
            logger.info(
                f"Initializing Kafka consumer for topic: {self.config.input_topic}"
            )

            # Initialize schema registry
            schema_registry_client = SchemaRegistryClient(
                {"url": self.config.schema_registry_url}
            )

            # Create Avro deserializer
            self.deserializer = AvroDeserializer(schema_registry_client)

            # Create consumer
            consumer_config = {
                "bootstrap.servers": self.config.brokers,
                "group.id": self.config.consumer_group,
                "auto.offset.reset": "earliest",
                "enable.auto.commit": False,
                "max.poll.interval.ms": self.config.max_poll_interval_ms,
            }

            self.consumer = Consumer(consumer_config)
            self.consumer.subscribe([self.config.input_topic])

            logger.info("Kafka consumer initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Kafka consumer: {e}")
            raise KafkaConsumerError(
                f"Failed to initialize Kafka consumer: {e}"
            )

    def consume_message(self, timeout_ms: int = 1000) -> Optional[Dict]:
        """
        Consume a single message from Kafka.

        Args:
            timeout_ms: Timeout in milliseconds

        Returns:
            Deserialized message or None if timeout

        Raises:
            KafkaConsumerError: If consumption fails
        """
        try:
            msg = self.consumer.poll(timeout_ms)

            if msg is None:
                return None

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    logger.debug("Reached end of partition")
                    return None
                else:
                    raise KafkaConsumerError(f"Kafka error: {msg.error()}")

            # Deserialize message
            try:
                value = self.deserializer(msg.value(), None)
                embedding_messages_consumed_total.inc()
                return value
            except Exception as e:
                logger.error(f"Failed to deserialize message: {e}")
                return None

        except Exception as e:
            logger.error(f"Failed to consume message: {e}")
            raise KafkaConsumerError(f"Failed to consume message: {e}")

    def consume_batch(
        self,
        batch_size: int = 100,
        timeout_ms: int = 5000,
    ) -> list:
        """
        Consume a batch of messages.

        Args:
            batch_size: Number of messages to consume
            timeout_ms: Timeout in milliseconds

        Returns:
            List of deserialized messages
        """
        messages = []
        start_time = None

        while len(messages) < batch_size:
            msg = self.consume_message(timeout_ms)

            if msg is None:
                break

            messages.append(msg)

        logger.debug(f"Consumed batch of {len(messages)} messages")

        return messages

    def commit_offset(self) -> None:
        """Commit current offset."""
        try:
            self.consumer.commit(asynchronous=False)
            logger.debug("Offset committed")
        except Exception as e:
            logger.warning(f"Failed to commit offset: {e}")

    def get_consumer_lag(self) -> Dict[int, int]:
        """Get consumer lag per partition."""
        try:
            lag = {}
            for partition in self.consumer.assignment():
                low, high = self.consumer.get_watermark_offsets(
                    partition.topic,
                    partition.partition,
                )
                current_offset = self.consumer.position([partition])[0].offset
                lag[partition.partition] = high - current_offset
                embedding_consumer_lag.labels(
                    partition=partition.partition
                ).set(lag[partition.partition])

            return lag
        except Exception as e:
            logger.warning(f"Failed to get consumer lag: {e}")
            return {}

    def close(self) -> None:
        """Close consumer."""
        if self.consumer:
            self.consumer.close()
            logger.info("Kafka consumer closed")

