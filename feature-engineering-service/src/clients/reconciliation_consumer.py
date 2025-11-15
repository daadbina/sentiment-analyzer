"""Kafka consumer for reconciliation_completed events."""

import json
from pathlib import Path
from typing import Optional, Dict, Any
from confluent_kafka import DeserializingConsumer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroDeserializer
from confluent_kafka.serialization import StringDeserializer

from src.config import config
from src.exceptions import KafkaError
from src.utils import StructuredLogger

logger = StructuredLogger(__name__)


class ReconciliationConsumer:
    """Kafka consumer for reconciliation_completed events."""

    def __init__(self):
        """Initialize reconciliation consumer."""
        self.config = config
        self.brokers = config.kafka.brokers
        self.schema_registry_url = config.kafka.schema_registry_url
        self.topic = "reconciliation_completed"
        self.consumer_group = "feature-engineering-reconciliation-group"

        self.consumer: Optional[DeserializingConsumer] = None
        self.schema_registry_client: Optional[SchemaRegistryClient] = None
        self.avro_deserializer: Optional[AvroDeserializer] = None

        logger.info(
            "Initializing reconciliation consumer",
            brokers=self.brokers,
            topic=self.topic,
            consumer_group=self.consumer_group
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

            # Initialize Avro deserializer
            self.avro_deserializer = AvroDeserializer(
                self.schema_registry_client,
                schema_str=schema_str
            )

            # Initialize Kafka consumer
            self.consumer = DeserializingConsumer({
                "bootstrap.servers": self.brokers,
                "group.id": self.consumer_group,
                "auto.offset.reset": "earliest",
                "enable.auto.commit": True,
                "auto.commit.interval.ms": 5000,
                "key.deserializer": StringDeserializer("utf_8"),
                "value.deserializer": self.avro_deserializer
            })

            # Subscribe to topic
            self.consumer.subscribe([self.topic])

            logger.info(
                "Reconciliation consumer connected successfully",
                topic=self.topic
            )

        except Exception as e:
            logger.error(
                f"Failed to connect reconciliation consumer: {str(e)}",
                error_type=type(e).__name__
            )
            raise KafkaError("connect", self.topic, str(e))

    async def disconnect(self):
        """Disconnect Kafka consumer."""
        if self.consumer:
            self.consumer.close()
            logger.info("Reconciliation consumer disconnected")

    def _load_schema(self) -> str:
        """Load Avro schema from file."""
        try:
            # Use the same schema from labeler service
            schema_path = Path(__file__).parent.parent.parent.parent / "labeler-ground-truth-ingest-service" / "schemas" / "reconciliation_completed.avsc"

            if not schema_path.exists():
                raise FileNotFoundError(f"Schema file not found: {schema_path}")

            with open(schema_path, 'r') as f:
                schema = json.load(f)

            logger.info(
                "Reconciliation schema loaded successfully",
                schema_name=schema.get("name")
            )

            return json.dumps(schema)

        except Exception as e:
            logger.error(
                f"Failed to load reconciliation schema: {str(e)}",
                error_type=type(e).__name__
            )
            raise

    def consume_message(self, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
        """Consume a single message from the topic.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Message dict or None if no message available
        """
        try:
            msg = self.consumer.poll(timeout=timeout)

            if msg is None:
                return None

            if msg.error():
                logger.error(f"Consumer error: {msg.error()}")
                return None

            # Message value is already deserialized by AvroDeserializer
            message = msg.value()

            logger.debug(
                "Consumed reconciliation event",
                group_id=message.get("group_id") if message else None
            )

            return message

        except Exception as e:
            logger.error(
                f"Failed to consume message: {str(e)}",
                error_type=type(e).__name__
            )
            return None

