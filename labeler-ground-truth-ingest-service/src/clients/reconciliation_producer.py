"""Kafka producer for reconciliation_completed events."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from confluent_kafka import SerializingProducer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import StringSerializer

from src.config import config
from src.exceptions import KafkaError
from src.utils.trace import get_logger
from src.metrics import get_metrics

logger = get_logger(__name__, config.logging.log_level)
metrics = get_metrics(config.metrics.prometheus_port)


class ReconciliationProducer:
    """Kafka producer for publishing reconciliation_completed events."""

    def __init__(self):
        """Initialize reconciliation producer."""
        self.config = config
        self.brokers = config.kafka.brokers
        self.schema_registry_url = config.kafka.schema_registry_url
        self.topic = "reconciliation_completed"

        self.producer: Optional[SerializingProducer] = None
        self.schema_registry_client: Optional[SchemaRegistryClient] = None
        self.avro_serializer: Optional[AvroSerializer] = None
        self.key_serializer: Optional[StringSerializer] = None

        logger.info(
            "Initializing reconciliation producer",
            operation="init_reconciliation_producer",
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
                schema_str=schema_str
            )

            # Initialize key serializer
            self.key_serializer = StringSerializer("utf_8")

            # Initialize Kafka producer
            self.producer = SerializingProducer({
                "bootstrap.servers": self.brokers,
                "client.id": "labeler-reconciliation-producer",
                "enable.idempotence": True,
                "acks": "all",
                "retries": 3,
                "max.in.flight.requests.per.connection": 5,
                "compression.type": "snappy",
                "key.serializer": self.key_serializer,
                "value.serializer": self.avro_serializer,
                "linger.ms": 100,
                "batch.size": 16384
            })

            logger.info(
                "Reconciliation producer connected successfully",
                operation="connect"
            )

        except Exception as e:
            logger.error(
                f"Failed to connect reconciliation producer: {str(e)}",
                operation="connect",
                error_type=type(e).__name__
            )
            raise KafkaError("connect", self.topic, str(e))

    async def disconnect(self):
        """Disconnect Kafka producer."""
        if self.producer:
            self.producer.flush()
            logger.info(
                "Reconciliation producer disconnected",
                operation="disconnect"
            )

    def _load_schema(self) -> str:
        """Load Avro schema from file."""
        try:
            schema_path = Path(__file__).parent.parent.parent / "schemas" / "reconciliation_completed.avsc"

            if not schema_path.exists():
                raise FileNotFoundError(f"Schema file not found: {schema_path}")

            with open(schema_path, 'r') as f:
                schema = json.load(f)

            logger.info(
                "Reconciliation schema loaded successfully",
                operation="_load_schema",
                schema_name=schema.get("name")
            )

            return json.dumps(schema)

        except Exception as e:
            logger.error(
                f"Failed to load reconciliation schema: {str(e)}",
                operation="_load_schema",
                error_type=type(e).__name__
            )
            raise

    def _delivery_report(self, err, msg):
        """Delivery report callback."""
        if err is not None:
            logger.error(
                f"Reconciliation event delivery failed: {err}",
                operation="delivery_report",
                topic=msg.topic() if msg else "unknown"
            )

    async def publish_reconciliation_completed(
        self,
        group_id: str,
        label_count: int,
        has_conflict: Optional[bool],
        conflict_event_count: int,
        non_conflict_event_count: int,
        countries: list,
        batch_id: Optional[str] = None,
        trace_id: Optional[str] = None
    ):
        """Publish reconciliation_completed event."""
        try:
            message = {
                "group_id": group_id,
                "reconciled_at": datetime.utcnow().isoformat() + "Z",
                "label_count": label_count,
                "has_conflict": has_conflict,
                "conflict_event_count": conflict_event_count,
                "non_conflict_event_count": non_conflict_event_count,
                "countries": countries if countries else [],
                "batch_id": batch_id,
                "trace_id": trace_id,
                "schema_version": "1.0.0"
            }

            self.producer.produce(
                topic=self.topic,
                key=group_id,
                value=message,
                on_delivery=self._delivery_report
            )

            self.producer.poll(0)  # Trigger delivery reports

            logger.info(
                "Reconciliation event published",
                operation="publish",
                group_id=group_id,
                has_conflict=has_conflict,
                label_count=label_count
            )

        except Exception as e:
            logger.error(
                f"Failed to publish reconciliation event: {str(e)}",
                operation="publish",
                group_id=group_id,
                error_type=type(e).__name__
            )
            raise KafkaError("publish", self.topic, str(e))

