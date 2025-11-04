"""Kafka consumer and producer integration."""

import logging
import json
from typing import Optional, Callable, List
from confluent_kafka import Consumer, Producer, KafkaError
from confluent_kafka.serialization import SerializationContext, MessageField
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroDeserializer, AvroSerializer
from confluent_kafka.schema_registry.json_schema import JSONDeserializer, JSONSerializer
import fastavro
import numpy as np

logger = logging.getLogger(__name__)


def convert_numpy_types(obj):
    """Convert numpy types to Python native types for JSON serialization."""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (np.floating, np.integer)):
        return obj.item()
    elif isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_numpy_types(item) for item in obj]
    return obj


class KafkaConsumer:
    """Kafka consumer for embeddings topic."""

    def __init__(
        self,
        brokers: str,
        schema_registry_url: str,
        topic: str,
        consumer_group: str,
        max_poll_interval_ms: int = 300000,
    ):
        """
        Initialize Kafka consumer.

        Args:
            brokers: Kafka brokers (comma-separated)
            schema_registry_url: Schema Registry URL
            topic: Topic to consume
            consumer_group: Consumer group ID
            max_poll_interval_ms: Max poll interval
        """
        self.topic = topic
        self.schema_registry_client = SchemaRegistryClient(
            {"url": schema_registry_url}
        )

        self.consumer = Consumer({
            "bootstrap.servers": brokers,
            "group.id": consumer_group,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
            "max.poll.interval.ms": max_poll_interval_ms,
        })

        self.consumer.subscribe([topic])
        logger.info(
            f"Initialized KafkaConsumer: topic={topic}, group={consumer_group}"
        )

    def consume_batch(
        self,
        batch_size: int = 100,
        timeout_ms: int = 5000,
    ) -> List[dict]:
        """
        Consume a batch of messages.

        Args:
            batch_size: Number of messages to consume
            timeout_ms: Timeout in milliseconds

        Returns:
            List of message dictionaries
        """
        messages = []

        try:
            while len(messages) < batch_size:
                msg = self.consumer.poll(timeout_ms / 1000)

                if msg is None:
                    break

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        logger.error(f"Consumer error: {msg.error()}")
                        break

                # Parse message
                try:
                    value = json.loads(msg.value().decode("utf-8"))
                    messages.append({
                        "key": msg.key().decode("utf-8") if msg.key() else None,
                        "value": value,
                        "offset": msg.offset(),
                        "partition": msg.partition(),
                    })
                except Exception as e:
                    logger.error(f"Error parsing message: {e}")
                    continue

            logger.info(f"Consumed {len(messages)} messages from {self.topic}")
            return messages

        except Exception as e:
            logger.error(f"Error consuming messages: {e}", exc_info=True)
            return messages

    def commit_offsets(self) -> bool:
        """Commit current offsets."""
        try:
            self.consumer.commit(asynchronous=False)
            logger.debug("Committed offsets")
            return True
        except Exception as e:
            logger.error(f"Error committing offsets: {e}", exc_info=True)
            return False

    def close(self):
        """Close consumer."""
        self.consumer.close()
        logger.info("Closed Kafka consumer")


class KafkaProducer:
    """Kafka producer for semantic groups topic."""

    def __init__(
        self,
        brokers: str,
        schema_registry_url: str,
        topic: str,
    ):
        """
        Initialize Kafka producer.

        Args:
            brokers: Kafka brokers (comma-separated)
            schema_registry_url: Schema Registry URL
            topic: Topic to produce to
        """
        self.topic = topic
        self.schema_registry_client = SchemaRegistryClient(
            {"url": schema_registry_url}
        )

        # Import the schema here to avoid circular imports
        from .avro_schemas import SEMANTIC_GROUPS_SCHEMA

        # Create Avro serializer with schema as JSON string
        self.avro_serializer = AvroSerializer(
            self.schema_registry_client,
            json.dumps(SEMANTIC_GROUPS_SCHEMA)
        )

        self.producer = Producer({
            "bootstrap.servers": brokers,
            "acks": "all",
            "retries": 3,
        })

        logger.info(f"Initialized KafkaProducer: topic={topic}")

    def produce_cluster(
        self,
        cluster: dict,
        key: Optional[str] = None,
    ) -> bool:
        """
        Produce a cluster message.

        Args:
            cluster: Cluster dictionary
            key: Optional message key

        Returns:
            True if successful
        """
        try:
            # Convert numpy types to Python native types
            cluster_converted = convert_numpy_types(cluster)

            # Create serialization context with topic information
            ctx = SerializationContext(self.topic, MessageField.VALUE)

            # Serialize using Avro
            value = self.avro_serializer(cluster_converted, ctx)

            # Debug logging
            logger.info(f"Serialized value type: {type(value)}, length: {len(value) if value else 0}")
            if value:
                logger.info(f"First 20 bytes (hex): {value[:20].hex()}")
                if value[0] == 0x00:
                    logger.info("Avro magic byte (0x00) found!")
                else:
                    logger.warning(f"Avro magic byte NOT found! First byte: {hex(value[0])}")

            key_bytes = key.encode("utf-8") if key else None

            self.producer.produce(
                self.topic,
                key=key_bytes,
                value=value,
                on_delivery=self._delivery_report,
            )

            logger.debug(f"Produced cluster: {cluster_converted.get('group_id')}")
            return True

        except Exception as e:
            logger.error(f"Error producing cluster: {e}", exc_info=True)
            return False

    def produce_batch(self, clusters: List[dict]) -> int:
        """
        Produce a batch of clusters.

        Args:
            clusters: List of cluster dictionaries

        Returns:
            Number of successfully produced messages
        """
        count = 0
        for cluster in clusters:
            if self.produce_cluster(cluster, key=cluster.get("group_id")):
                count += 1

        logger.info(f"Produced {count}/{len(clusters)} clusters")
        return count

    def flush(self, timeout_ms: int = 10000) -> int:
        """
        Flush pending messages.

        Args:
            timeout_ms: Timeout in milliseconds

        Returns:
            Number of messages still in queue
        """
        remaining = self.producer.flush(timeout_ms / 1000)
        logger.info(f"Flushed producer (remaining: {remaining})")
        return remaining

    def close(self):
        """Close producer."""
        self.producer.flush()
        logger.info("Closed Kafka producer")

    @staticmethod
    def _delivery_report(err, msg):
        """Delivery report callback."""
        if err is not None:
            logger.error(f"Message delivery failed: {err}")
        else:
            logger.debug(
                f"Message delivered to {msg.topic()} "
                f"[{msg.partition()}] at offset {msg.offset()}"
            )

