"""Kafka producer for ground truth labels."""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from confluent_kafka import SerializingProducer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import StringSerializer

from src.config import config
from src.exceptions import KafkaError, SchemaRegistryError
from src.utils.trace import get_logger
from src.metrics import get_metrics
from src.clients.circuit_breaker import CircuitBreaker, ExponentialBackoff
import time


logger = get_logger(__name__, config.logging.log_level)
metrics = get_metrics(config.metrics.prometheus_port)


class KafkaProducerClient:
    """Kafka producer with Avro serialization."""

    def __init__(self):
        """Initialize Kafka producer."""
        self.config = config
        self.brokers = config.kafka.brokers
        self.schema_registry_url = config.kafka.schema_registry_url
        self.topic = config.kafka.ground_truth_topic

        self.producer: Optional[SerializingProducer] = None
        self.schema_registry_client: Optional[SchemaRegistryClient] = None
        self.avro_serializer: Optional[AvroSerializer] = None
        self.key_serializer: Optional[StringSerializer] = None

        # Initialize circuit breaker for resilience
        self.circuit_breaker = CircuitBreaker(
            name="ground_truth_producer",
            failure_threshold=5,
            recovery_timeout_seconds=60
        )

        # Initialize exponential backoff for retries
        self.backoff = ExponentialBackoff(
            initial_delay_ms=100,
            max_delay_ms=30000,
            multiplier=2.0,
            jitter=True
        )

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
                schema_str
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
        """Load Avro schema from file.

        Returns:
            JSON string of Avro schema

        Raises:
            FileNotFoundError: If schema file not found
            json.JSONDecodeError: If schema file is invalid JSON
        """
        try:
            # Get path to schema file relative to this file
            schema_path = Path(__file__).parent.parent.parent / "schemas" / "ground_truth.avsc"

            logger.debug(
                "Loading schema from file",
                operation="_load_schema",
                schema_path=str(schema_path)
            )

            if not schema_path.exists():
                raise FileNotFoundError(f"Schema file not found: {schema_path}")

            # Load and parse schema
            with open(schema_path, 'r') as f:
                schema = json.load(f)

            logger.info(
                "Schema loaded successfully",
                operation="_load_schema",
                schema_name=schema.get("name"),
                schema_namespace=schema.get("namespace")
            )

            return json.dumps(schema)

        except FileNotFoundError as e:
            logger.error(
                f"Schema file not found: {str(e)}",
                operation="_load_schema",
                error_type=type(e).__name__
            )
            raise
        except json.JSONDecodeError as e:
            logger.error(
                f"Invalid JSON in schema file: {str(e)}",
                operation="_load_schema",
                error_type=type(e).__name__
            )
            raise

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
        """Produce batch of labels to Kafka in smaller chunks to avoid timeout."""
        if not labels:
            return True

        if not self.producer or not self.avro_serializer:
            raise KafkaError("produce_batch", self.topic, "Producer not connected")

        start_time = time.time()
        success_count = 0
        error_count = 0
        batch_size = self.config.kafka.producer_batch_size

        try:
            # Produce labels in smaller batches to avoid consumer timeout
            for i in range(0, len(labels), batch_size):
                batch = labels[i:i + batch_size]
                batch_start = time.time()

                logger.info(
                    f"Producing batch {i // batch_size + 1} of {(len(labels) + batch_size - 1) // batch_size}",
                    operation="produce_batch",
                    batch_start_index=i,
                    batch_size=len(batch)
                )

                for label in batch:
                    try:
                        await self.produce_label(label)
                        success_count += 1

                        # Record produced message
                        metrics.record_kafka_producer_message(self.topic)

                    except Exception as e:
                        logger.error(
                            f"Failed to produce label: {str(e)}",
                            operation="produce_batch",
                            event_id=label.get("event_id"),
                            error_type=type(e).__name__
                        )
                        error_count += 1

                        # Record production error
                        metrics.record_kafka_production_error(self.topic)

                # Flush after each batch
                self.producer.flush()
                batch_duration = time.time() - batch_start

                logger.info(
                    f"Batch flushed",
                    operation="produce_batch",
                    batch_index=i // batch_size,
                    batch_size=len(batch),
                    batch_duration_seconds=batch_duration
                )

            duration_seconds = time.time() - start_time

            # Record production duration
            metrics.record_kafka_production(self.topic, duration_seconds)
            metrics.record_fetch("kafka", success_count, duration_seconds)

            logger.info(
                f"Batch production completed",
                operation="produce_batch",
                total_labels=len(labels),
                success_count=success_count,
                duration_seconds=duration_seconds,
                throughput_labels_per_second=success_count / duration_seconds if duration_seconds > 0 else 0,
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

    def get_health_status(self) -> dict:
        """Get producer health status including circuit breaker state.

        Returns:
            Health status dictionary
        """
        return {
            "connected": self.producer is not None,
            "topic": self.topic,
            "circuit_breaker": self.circuit_breaker.get_state()
        }

