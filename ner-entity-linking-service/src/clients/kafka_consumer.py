"""Kafka consumer for news_canonical topic."""

import logging
import json
from confluent_kafka import Consumer, KafkaError
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroDeserializer
from src.models import NewsCanonicalMessage
from src.exceptions import KafkaError as KafkaServiceError
from src.metrics import MetricsCollector

logger = logging.getLogger(__name__)


class KafkaConsumerClient:
    """Kafka consumer for news_canonical topic."""

    def __init__(
        self,
        brokers: str,
        schema_registry_url: str,
        consumer_group: str,
        input_topic: str,
        auto_offset_reset: str = "earliest",
        session_timeout_ms: int = 30000,
        request_timeout_ms: int = 40000,
    ):
        """
        Initialize Kafka consumer.

        Args:
            brokers: Kafka bootstrap servers
            schema_registry_url: Schema Registry URL
            consumer_group: Consumer group ID
            input_topic: Input topic name
            auto_offset_reset: Auto offset reset strategy
            session_timeout_ms: Session timeout
            request_timeout_ms: Request timeout
        """
        self.brokers = brokers
        self.consumer_group = consumer_group
        self.input_topic = input_topic

        try:
            # Initialize schema registry
            self.schema_registry_client = SchemaRegistryClient(
                {"url": schema_registry_url}
            )

            # Initialize Avro deserializer
            self.avro_deserializer = AvroDeserializer(self.schema_registry_client)

            # Initialize consumer
            self.consumer = Consumer(
                {
                    "bootstrap.servers": brokers,
                    "group.id": consumer_group,
                    "auto.offset.reset": auto_offset_reset,
                    "session.timeout.ms": session_timeout_ms,
                    "request.timeout.ms": request_timeout_ms,
                    "enable.auto.commit": False,
                }
            )

            self.consumer.subscribe([input_topic])
            logger.info(
                f"Kafka consumer initialized for topic {input_topic} "
                f"with group {consumer_group}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize Kafka consumer: {e}")
            raise KafkaServiceError(f"Failed to initialize consumer: {e}")

    def consume_message(self, timeout_ms: int = 1000) -> tuple:
        """
        Consume a single message.

        Args:
            timeout_ms: Timeout in milliseconds

        Returns:
            Tuple of (message, error)
        """
        try:
            msg_record = self.consumer.poll(timeout_ms / 1000.0)

            if msg_record is None:
                return None, None

            # Deserialize message using Avro deserializer
            try:
                # Manually deserialize the Avro message
                message_data = self.avro_deserializer(msg_record.value(), None)
                message = NewsCanonicalMessage(**message_data)
                MetricsCollector.record_message_consumed()
                logger.debug(f"Consumed message: {message.article_id}")
                return message, None
            except Exception as e:
                logger.error(f"Failed to deserialize message: {e}")
                return None, e

        except Exception as e:
            logger.error(f"Error consuming message: {e}")
            return None, e

    def commit_offset(self) -> None:
        """Commit current offset."""
        try:
            self.consumer.commit()
            logger.debug("Offset committed")
        except Exception as e:
            logger.error(f"Failed to commit offset: {e}")

    def close(self) -> None:
        """Close consumer."""
        try:
            self.consumer.close()
            logger.info("Kafka consumer closed")
        except Exception as e:
            logger.error(f"Error closing consumer: {e}")

