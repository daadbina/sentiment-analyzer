"""Kafka producer for computed features."""

import json
import os
from confluent_kafka import Producer
from confluent_kafka.avro import AvroProducer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.schema_registry_client import Schema
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
        self.schema_str: Optional[str] = None

    def connect(self) -> bool:
        """Connect to Kafka.

        Returns:
            True if connection successful
        """
        try:
            # Register schema with Schema Registry
            schema_registry_client = SchemaRegistryClient(
                {"url": self.config.kafka.schema_registry_url}
            )

            # Load schema from file
            schema_path = os.path.join(
                os.path.dirname(__file__),
                "../../schemas/features_computed.avsc"
            )
            with open(schema_path, "r") as f:
                self.schema_str = f.read()

            # Register value schema
            schema = Schema(self.schema_str, schema_type="AVRO")
            schema_id = schema_registry_client.register_schema(
                subject_name=f"{self.topic}-value",
                schema=schema
            )
            logger.info(
                "Schema registered",
                schema_id=schema_id,
                topic=self.topic,
            )

            # Register key schema (simple string)
            key_schema_str = '{"type": "string"}'
            key_schema = Schema(key_schema_str, schema_type="AVRO")
            key_schema_id = schema_registry_client.register_schema(
                subject_name=f"{self.topic}-key",
                schema=key_schema
            )
            self.key_schema_str = key_schema_str

            producer_config = {
                "bootstrap.servers": self.config.kafka.brokers,
                "acks": "all",  # Wait for all replicas
                "retries": 3,
                "schema.registry.url": self.config.kafka.schema_registry_url,
            }

            self.producer = AvroProducer(producer_config)

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
        if not self.producer:
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

            self.producer.produce(
                topic=self.topic,
                value=message_value,
                key=group_id,
                value_schema=self.schema_str,
                key_schema=self.key_schema_str,
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

