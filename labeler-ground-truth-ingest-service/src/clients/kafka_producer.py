"""Kafka producer for ground truth labels."""

import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from confluent_kafka import SerializingProducer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import StringSerializer

from src.config import config
from src.exceptions import KafkaError, SchemaRegistryError
from src.utils.trace import get_logger
from src.metrics import get_metrics


logger = get_logger(__name__, config.logging.log_level)
metrics = get_metrics(config.metrics.prometheus_port)


class KafkaProducerClient:
    """Kafka producer with Avro serialization."""

    def __init__(self):
        """Initialize Kafka producer."""
        self.brokers = config.kafka.brokers
        self.schema_registry_url = config.kafka.schema_registry_url
        self.topic = config.kafka.ground_truth_topic

        self.producer: Optional[SerializingProducer] = None
        self.schema_registry_client: Optional[SchemaRegistryClient] = None
        self.avro_serializer: Optional[AvroSerializer] = None
        self.key_serializer: Optional[StringSerializer] = None

        logger.info(
            "Initializing Kafka producer",
            operation="init_kafka_producer",
            brokers=self.brokers,
            topic=self.topic
        )

    async def connect(self):
        """Connect to Kafka and Schema Registry."""
        try:
            # Initialize Schema Registry client
            self.schema_registry_client = SchemaRegistryClient({
                "url": self.schema_registry_url
            })

            # Load schema
            schema_str = self._load_schema()

            # Initialize Avro serializer
            self.avro_serializer = AvroSerializer(
                self.schema_registry_client,
                schema_str,
                conf={"auto.register.schemas": False}
            )

            # Initialize key serializer
            self.key_serializer = StringSerializer()

            # Initialize Kafka producer with SerializingProducer
            self.producer = SerializingProducer({
                "bootstrap.servers": self.brokers,
                "client.id": "labeler-ground-truth-ingest-service",
                "enable.idempotence": True,
                "acks": "all",
                "retries": 3,
                "max.in.flight.requests.per.connection": 5,
                "compression.type": "snappy",
                "key.serializer": self.key_serializer,
                "value.serializer": self.avro_serializer
            })

            logger.info(
                "Kafka producer connected successfully",
                operation="connect"
            )

        except Exception as e:
            logger.error(
                f"Failed to connect Kafka producer: {str(e)}",
                operation="connect",
                error_type=type(e).__name__
            )
            raise KafkaError("connect", self.topic, str(e))

    async def disconnect(self):
        """Disconnect Kafka producer."""
        if self.producer:
            self.producer.flush()
            logger.info(
                "Kafka producer disconnected",
                operation="disconnect"
            )

    def _load_schema(self) -> str:
        """Load Avro schema."""
        schema = {
            "type": "record",
            "name": "GroundTruthValue",
            "namespace": "com.sentiment.labeler",
            "fields": [
                {"name": "event_id", "type": "string"},
                {"name": "group_id", "type": ["null", "string"]},
                {"name": "description", "type": ["null", "string"]},
                {"name": "domain", "type": ["null", "string"]},
                {"name": "time_window", "type": ["null", "string"]},
                {"name": "realization_metric", "type": ["null", "string"]},
                {"name": "threshold", "type": ["null", "double"]},
                {"name": "verified_at", "type": ["null", "string"]},
                {"name": "label_realized", "type": ["null", "boolean"]},
                {"name": "label_confidence", "type": ["null", "double"]},
                {"name": "source_confidence", "type": ["null", "double"]},
                {"name": "label_source", "type": ["null", "string"]},
                {"name": "label_source_license", "type": ["null", "string"]},
                {"name": "label_source_url", "type": ["null", "string"]},
                {"name": "last_license_check", "type": ["null", "string"]},
                {"name": "last_updated", "type": ["null", "string"]},
                {"name": "trace_id", "type": ["null", "string"]},
                {"name": "schema_version", "type": ["null", "string"]}
            ]
        }
        return json.dumps(schema)

    def _delivery_report(self, err, msg):
        """Delivery report callback."""
        if err is not None:
            logger.error(
                f"Message delivery failed: {err}",
                operation="delivery_report",
                topic=msg.topic(),
                partition=msg.partition(),
                offset=msg.offset()
            )
        else:
            logger.debug(
                f"Message delivered successfully",
                operation="delivery_report",
                topic=msg.topic(),
                partition=msg.partition(),
                offset=msg.offset()
            )

    async def produce_label(self, label: Dict[str, Any]) -> bool:
        """Produce single label to Kafka."""
        if not self.producer:
            raise KafkaError("produce_label", self.topic, "Producer not connected")

        try:
            start_time = time.time()

            # Prepare message key
            key = label.get("event_id", "")

            # Prepare message value - only include fields that match schema
            value = {
                "event_id": label.get("event_id"),
                "group_id": label.get("group_id"),
                "description": label.get("description"),
                "domain": label.get("domain"),
                "time_window": label.get("time_window"),
                "realization_metric": label.get("realization_metric"),
                "threshold": label.get("threshold"),
                "verified_at": label.get("verified_at"),
                "label_realized": label.get("label_realized"),
                "label_confidence": label.get("label_confidence"),
                "source_confidence": label.get("source_confidence"),
                "label_source": label.get("label_source"),
                "label_source_license": label.get("label_source_license"),
                "label_source_url": label.get("label_source_url"),
                "last_license_check": label.get("last_license_check"),
                "last_updated": label.get("last_updated"),
                "trace_id": label.get("trace_id"),
                "schema_version": label.get("schema_version")
            }

            # Produce message - SerializingProducer handles serialization
            self.producer.produce(
                topic=self.topic,
                key=key,
                value=value,
                on_delivery=self._delivery_report
            )

            # Poll to trigger delivery reports
            self.producer.poll(0)

            duration_seconds = time.time() - start_time
            logger.debug(
                f"Label produced to Kafka",
                operation="produce_label",
                event_id=label.get("event_id"),
                duration_seconds=duration_seconds
            )

            return True

        except Exception as e:
            logger.error(
                f"Failed to produce label to Kafka: {str(e)}",
                operation="produce_label",
                error_type=type(e).__name__
            )
            raise KafkaError("produce_label", self.topic, str(e))

    async def produce_batch(self, labels: List[Dict[str, Any]]) -> bool:
        """Produce batch of labels to Kafka."""
        if not labels:
            return True

        if not self.producer or not self.avro_serializer:
            raise KafkaError("produce_batch", self.topic, "Producer not connected")

        start_time = time.time()
        success_count = 0
        error_count = 0

        try:
            for label in labels:
                try:
                    await self.produce_label(label)
                    success_count += 1
                except Exception as e:
                    logger.error(
                        f"Failed to produce label: {str(e)}",
                        operation="produce_batch",
                        event_id=label.get("event_id"),
                        error_type=type(e).__name__
                    )
                    error_count += 1

            # Flush all messages
            self.producer.flush()

            duration_seconds = time.time() - start_time
            metrics.record_fetch("kafka", success_count, duration_seconds)

            logger.info(
                f"Batch production completed",
                operation="produce_batch",
                total_labels=len(labels),
                success_count=success_count,
                error_count=error_count,
                duration_seconds=duration_seconds
            )

            return error_count == 0

        except Exception as e:
            logger.error(
                f"Batch production failed: {str(e)}",
                operation="produce_batch",
                error_type=type(e).__name__
            )
            raise KafkaError("produce_batch", self.topic, str(e))

