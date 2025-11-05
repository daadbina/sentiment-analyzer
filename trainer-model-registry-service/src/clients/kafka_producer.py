"""
Kafka producer for Trainer & Model Registry Service.

Provides Kafka producer with Avro serialization.
"""

import logging
from typing import Optional, Dict, Any, Callable
from confluent_kafka import Producer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import StringSerializer

from src.config import KafkaConfig
from src.exceptions import ExternalServiceError

logger = logging.getLogger(__name__)


class KafkaProducerClient:
    """Kafka producer with Avro serialization."""

    def __init__(self, config: KafkaConfig):
        """
        Initialize Kafka producer.

        Args:
            config: Kafka configuration
        """
        self.config = config
        self.producer: Optional[Producer] = None
        self.schema_registry_client: Optional[SchemaRegistryClient] = None
        self.avro_serializer: Optional[AvroSerializer] = None
        logger.info(f"Kafka producer initialized for {config.bootstrap_servers}")

    def connect(self) -> None:
        """
        Initialize Kafka producer and schema registry.

        Raises:
            ExternalServiceError: If connection fails
        """
        try:
            # Initialize schema registry client
            self.schema_registry_client = SchemaRegistryClient(
                {"url": self.config.schema_registry_url}
            )

            # Initialize Avro serializer
            self.avro_serializer = AvroSerializer(
                schema_registry_client=self.schema_registry_client,
                schema_str=None,  # Schema will be provided per message
            )

            # Initialize producer
            producer_config = {
                "bootstrap.servers": self.config.bootstrap_servers,
                "client.id": "trainer-service-producer",
                "acks": "all",
                "retries": 3,
                "max.in.flight.requests.per.connection": 1,
                "enable.idempotence": True,
            }

            self.producer = Producer(producer_config)
            logger.info("Kafka producer connected")

        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            raise ExternalServiceError(
                f"Failed to connect to Kafka: {e}",
                service_name="Kafka",
                details={"bootstrap_servers": self.config.bootstrap_servers},
            )

    def health_check(self) -> bool:
        """
        Check Kafka connection health.

        Returns:
            True if connection is healthy, False otherwise
        """
        if not self.producer:
            logger.warning("Kafka producer not initialized")
            return False

        try:
            # Try to get metadata
            metadata = self.producer.list_topics(timeout=5)
            logger.debug("Kafka health check passed")
            return True
        except Exception as e:
            logger.error(f"Kafka health check failed: {e}")
            return False

    def produce(
        self,
        topic: str,
        value: Dict[str, Any],
        key: Optional[str] = None,
        schema_id: Optional[int] = None,
        on_delivery: Optional[Callable] = None,
    ) -> None:
        """
        Produce message to Kafka topic.

        Args:
            topic: Topic name
            value: Message value (dict)
            key: Message key
            schema_id: Schema ID for Avro serialization
            on_delivery: Callback function for delivery reports

        Raises:
            ExternalServiceError: If production fails
        """
        if not self.producer:
            raise ExternalServiceError(
                "Kafka producer not initialized",
                service_name="Kafka",
            )

        try:
            # Serialize key
            key_bytes = None
            if key:
                key_bytes = StringSerializer("utf_8")(key)

            # Serialize value with Avro
            value_bytes = self._serialize_avro(value, schema_id)

            # Produce message
            self.producer.produce(
                topic=topic,
                key=key_bytes,
                value=value_bytes,
                on_delivery=on_delivery or self._delivery_report,
            )

            # Flush to ensure delivery
            self.producer.flush(timeout=10)

            logger.debug(f"Produced message to {topic} with key: {key}")

        except Exception as e:
            logger.error(f"Failed to produce message: {e}")
            raise ExternalServiceError(
                f"Failed to produce message: {e}",
                service_name="Kafka",
                details={"topic": topic, "schema_id": schema_id},
            )

    def _serialize_avro(
        self, value: Dict[str, Any], schema_id: Optional[int] = None
    ) -> bytes:
        """
        Serialize value using Avro.

        Args:
            value: Value to serialize
            schema_id: Schema ID

        Returns:
            Serialized bytes

        Raises:
            ExternalServiceError: If serialization fails
        """
        try:
            # For now, return JSON-serialized bytes
            # In production, use proper Avro serialization with schema
            import json

            return json.dumps(value).encode("utf-8")
        except Exception as e:
            logger.error(f"Avro serialization failed: {e}")
            raise ExternalServiceError(
                f"Avro serialization failed: {e}",
                service_name="Kafka",
            )

    def _delivery_report(self, err, msg) -> None:
        """
        Delivery report callback.

        Args:
            err: Error (if any)
            msg: Message
        """
        if err is not None:
            logger.error(f"Message delivery failed: {err}")
        else:
            logger.debug(
                f"Message delivered to {msg.topic()} "
                f"[{msg.partition()}] at offset {msg.offset()}"
            )

    def flush(self, timeout: int = 10) -> None:
        """
        Flush pending messages.

        Args:
            timeout: Timeout in seconds

        Raises:
            ExternalServiceError: If flush fails
        """
        if not self.producer:
            raise ExternalServiceError(
                "Kafka producer not initialized",
                service_name="Kafka",
            )

        try:
            self.producer.flush(timeout=timeout)
            logger.debug("Flushed pending messages")
        except Exception as e:
            logger.error(f"Failed to flush messages: {e}")
            raise ExternalServiceError(
                f"Failed to flush messages: {e}",
                service_name="Kafka",
            )

    def close(self) -> None:
        """Close producer."""
        if self.producer:
            self.producer.flush()
            logger.info("Kafka producer closed")
