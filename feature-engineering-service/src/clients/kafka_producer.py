"""Kafka producer for computed features."""

from confluent_kafka import Producer
from confluent_kafka.avro import AvroProducer
from typing import Dict, Any, Optional, Callable
from ..config import config
from ..utils import StructuredLogger
from ..exceptions import KafkaError as KafkaErrorException

logger = StructuredLogger(__name__)


class FeaturesProducer:
    """Produce computed features to Kafka."""

    def __init__(self):
        """Initialize producer."""
        self.config = config
        self.producer: Optional[AvroProducer] = None
        self.topic = "features_computed"

    def connect(self) -> bool:
        """Connect to Kafka.

        Returns:
            True if connection successful
        """
        try:
            producer_config = {
                "bootstrap.servers": self.config.kafka.bootstrap_servers,
                "acks": "all",  # Wait for all replicas
                "retries": 3,
                "schema.registry.url": self.config.kafka.schema_registry_url,
            }

            self.producer = AvroProducer(producer_config)

            logger.info(
                "Kafka producer connected",
                bootstrap_servers=self.config.kafka.bootstrap_servers,
                topic=self.topic,
            )
            return True

        except Exception as e:
            logger.error("Failed to connect to Kafka", error=str(e))
            raise KafkaErrorException(f"Failed to connect to Kafka: {str(e)}")

    def produce_message(
        self,
        group_id: str,
        features: Dict[str, Any],
        callback: Optional[Callable] = None,
    ) -> bool:
        """Produce a message.

        Args:
            group_id: Semantic group ID
            features: Computed features
            callback: Optional callback function

        Returns:
            True if message queued successfully
        """
        if not self.producer:
            raise KafkaErrorException("Producer not connected")

        try:
            message_value = {
                "group_id": group_id,
                "features": features,
                "timestamp": int(__import__("time").time() * 1000),
            }

            def delivery_callback(err, msg):
                if err:
                    logger.error(
                        "Message delivery failed",
                        error=str(err),
                        group_id=group_id,
                    )
                else:
                    logger.info(
                        "Message delivered",
                        topic=msg.topic(),
                        partition=msg.partition(),
                        offset=msg.offset(),
                    )
                if callback:
                    callback(err, msg)

            self.producer.produce(
                topic=self.topic,
                value=message_value,
                key=group_id,
                on_delivery=delivery_callback,
            )

            logger.info(
                "Message produced",
                group_id=group_id,
                feature_count=len(features),
            )
            return True

        except Exception as e:
            logger.error("Error producing message", error=str(e), group_id=group_id)
            raise KafkaErrorException(f"Error producing message: {str(e)}")

    def flush(self, timeout_ms: int = 30000) -> int:
        """Flush pending messages.

        Args:
            timeout_ms: Timeout in milliseconds

        Returns:
            Number of messages still in queue
        """
        if not self.producer:
            return 0

        remaining = self.producer.flush(timeout_ms)
        logger.info("Producer flushed", remaining_messages=remaining)
        return remaining

    def close(self):
        """Close producer connection."""
        if self.producer:
            self.flush()
            self.producer = None
            logger.info("Kafka producer closed")

