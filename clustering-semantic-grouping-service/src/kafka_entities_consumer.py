"""Kafka consumer for entities_extracted topic."""

import logging
import json
from typing import List, Dict, Optional
from confluent_kafka import Consumer, KafkaError
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroDeserializer

logger = logging.getLogger(__name__)


class KafkaEntitiesConsumer:
    """Kafka consumer for entities_extracted topic with Avro deserialization."""

    def __init__(
        self,
        brokers: str,
        schema_registry_url: str,
        topic: str = "entities_extracted",
        consumer_group: str = "clustering-entities-consumer-group",
        max_poll_interval_ms: int = 300000,
    ):
        """
        Initialize Kafka entities consumer.

        Args:
            brokers: Kafka brokers (comma-separated)
            schema_registry_url: Schema Registry URL
            topic: Topic to consume (default: entities_extracted)
            consumer_group: Consumer group ID
            max_poll_interval_ms: Max poll interval
        """
        self.topic = topic
        self.schema_registry_client = SchemaRegistryClient(
            {"url": schema_registry_url}
        )

        # Create Avro deserializer
        self.avro_deserializer = AvroDeserializer(
            self.schema_registry_client
        )

        # Consumer configuration
        self.consumer = Consumer({
            "bootstrap.servers": brokers,
            "group.id": consumer_group,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
            "max.poll.interval.ms": max_poll_interval_ms,
        })

        self.consumer.subscribe([topic])
        logger.info(
            f"Initialized KafkaEntitiesConsumer: topic={topic}, group={consumer_group}"
        )

    def consume_batch(
        self,
        batch_size: int = 100,
        timeout_ms: int = 5000,
    ) -> List[Dict]:
        """
        Consume a batch of entity messages.

        Args:
            batch_size: Number of messages to consume
            timeout_ms: Timeout in milliseconds

        Returns:
            List of entity message dictionaries with structure:
            {
                "article_id": str,
                "entities": List[Dict],  # Each entity has: text, entity_type, country, etc.
                "language": str,
                "entity_count": int,
                ...
            }
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

                # Deserialize Avro message
                try:
                    value = self.avro_deserializer(msg.value(), None)
                    
                    if value:
                        messages.append({
                            "article_id": value.get("article_id"),
                            "entities": value.get("entities", []),
                            "language": value.get("language"),
                            "entity_count": value.get("entity_count", 0),
                            "extracted_at": value.get("extracted_at"),
                            "offset": msg.offset(),
                            "partition": msg.partition(),
                        })
                        
                        logger.debug(
                            f"Consumed entity message: article_id={value.get('article_id')}, "
                            f"entity_count={value.get('entity_count', 0)}"
                        )
                except Exception as e:
                    logger.error(f"Error deserializing message: {e}", exc_info=True)
                    continue

            if messages:
                logger.info(
                    f"Consumed {len(messages)} entity messages from {self.topic}"
                )
            
            return messages

        except Exception as e:
            logger.error(f"Error consuming entity messages: {e}", exc_info=True)
            return messages

    def commit_offsets(self) -> bool:
        """Commit current offsets."""
        try:
            self.consumer.commit(asynchronous=False)
            logger.debug("Committed entity consumer offsets")
            return True
        except Exception as e:
            logger.error(f"Error committing offsets: {e}", exc_info=True)
            return False

    def close(self):
        """Close consumer."""
        try:
            self.consumer.close()
            logger.info("Closed Kafka entities consumer")
        except Exception as e:
            logger.error(f"Error closing consumer: {e}", exc_info=True)

