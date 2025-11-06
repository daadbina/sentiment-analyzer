"""Kafka producer for computed features."""

import json
import os
from confluent_kafka import Producer, KafkaError
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import SerializationContext, MessageField
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
        self.producer: Optional[Producer] = None
        self.schema_registry_client: Optional[SchemaRegistryClient] = None
        self.avro_serializer: Optional[AvroSerializer] = None
        self.topic = "features_computed"
        self.schema_str: Optional[str] = None

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

            # Load schema from file
            schema_path = os.path.join(
                os.path.dirname(__file__),
                "../../schemas/features_computed.avsc"
            )
            with open(schema_path, "r") as f:
                self.schema_str = f.read()

            # Initialize Avro serializer
            self.avro_serializer = AvroSerializer(
                self.schema_registry_client,
                self.schema_str,
            )

            logger.info(
                "Schema loaded and serializer initialized",
                topic=self.topic,
            )

            # Initialize Kafka producer
            producer_config = {
                "bootstrap.servers": self.config.kafka.brokers,
                "acks": "all",  # Wait for all replicas
                "retries": 3,
            }

            self.producer = Producer(producer_config)

            logger.info(
                "Kafka producer connected",
                bootstrap_servers=self.config.kafka.brokers,
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
        feature_version: str = "v1.0",
        validation_status: str = "VALID",
        validation_failures: list = None,
        computation_duration_ms: int = 0,
        trace_id: str = "",
        callback: Optional[Callable] = None,
    ) -> bool:
        """Produce a message.

        Args:
            group_id: Semantic group ID
            features: Computed features
            feature_version: Feature engineering version
            validation_status: Feature validation status
            validation_failures: List of validation failures
            computation_duration_ms: Time taken to compute features
            trace_id: Distributed trace identifier
            callback: Optional callback function

        Returns:
            True if message queued successfully
        """
        if not self.producer or not self.avro_serializer:
            raise KafkaErrorException("Producer not connected")

        try:
            if validation_failures is None:
                validation_failures = []

            message_value = {
                "group_id": group_id,
                "features": features,
                "timestamp": int(__import__("time").time() * 1000),
                "feature_version": feature_version,
                "feature_count": len(features),
                "validation_status": validation_status,
                "validation_failures": validation_failures,
                "computation_duration_ms": computation_duration_ms,
                "trace_id": trace_id,
                "schema_version": "1.0",
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

            # Serialize message using AvroSerializer
            serialized_value = self.avro_serializer(
                message_value,
                SerializationContext(self.topic, MessageField.VALUE),
            )

            self.producer.produce(
                topic=self.topic,
                value=serialized_value,
                key=group_id.encode("utf-8"),
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

