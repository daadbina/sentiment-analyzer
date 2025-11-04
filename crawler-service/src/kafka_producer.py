"""
Kafka producer for publishing articles to Kafka topics.

Implements Adapter pattern for confluent-kafka library with Avro serialization.
"""

import json
import logging
from typing import Optional, Any
from confluent_kafka import Producer, KafkaError
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import SerializationContext, MessageField

from .config import get_settings
from .exceptions import PublishError
from .models import NewsRawMessage

logger = logging.getLogger(__name__)


class KafkaProducerAdapter:
    """
    Adapter for Kafka producer with Avro serialization.

    Wraps confluent-kafka producer with schema registry integration.
    """

    def __init__(self) -> None:
        """Initialize Kafka producer."""
        self.settings = get_settings()
        self.producer: Optional[Producer] = None
        self.schema_registry_client: Optional[SchemaRegistryClient] = None
        self.avro_serializer: Optional[AvroSerializer] = None
        self._delivery_reports: list[dict] = []

    async def start(self) -> None:
        """Start Kafka producer and schema registry client."""
        try:
            # Initialize schema registry client
            self.schema_registry_client = SchemaRegistryClient(
                {"url": self.settings.schema_registry_url}
            )

            # Get schema from registry
            schema_str = self._get_schema()

            # Initialize Avro serializer
            self.avro_serializer = AvroSerializer(
                self.schema_registry_client,
                schema_str,
            )

            # Initialize Kafka producer
            self.producer = Producer(
                {
                    "bootstrap.servers": self.settings.kafka_brokers,
                    "acks": self.settings.kafka_acks,
                    "retries": self.settings.kafka_max_retries,
                    "on_delivery": self._delivery_report,
                }
            )

            logger.info(
                f"Kafka producer started, brokers: {self.settings.kafka_brokers}"
            )

        except Exception as e:
            raise PublishError(
                f"Failed to initialize Kafka producer: {str(e)}",
                error_code="PRODUCER_INIT_FAILED",
            )

    async def stop(self) -> None:
        """Stop Kafka producer and flush pending messages."""
        if self.producer:
            try:
                self.producer.flush(timeout=30)
                logger.info("Kafka producer stopped")
            except Exception as e:
                logger.error(f"Error stopping Kafka producer: {str(e)}")

    async def publish(
        self,
        message: NewsRawMessage,
        topic: Optional[str] = None,
    ) -> None:
        """
        Publish article message to Kafka.

        Args:
            message: Article message to publish.
            topic: Kafka topic (uses default if not specified).

        Raises:
            PublishError: If publish fails.
        """
        if not self.producer:
            raise PublishError(
                "Producer not initialized",
                error_code="PRODUCER_NOT_INITIALIZED",
            )

        topic = topic or self.settings.kafka_topic

        try:
            # Serialize message
            message_dict = message.to_dict()

            # Publish to Kafka
            self.producer.produce(
                topic=topic,
                key=message.article_id.encode("utf-8"),
                value=self.avro_serializer(
                    message_dict,
                    SerializationContext(topic, MessageField.VALUE),
                ),
            )

            # Flush to ensure message is sent immediately
            self.producer.flush(timeout=5)

            logger.debug(f"Published article {message.article_id} to {topic}")

        except Exception as e:
            raise PublishError(
                f"Failed to publish message: {str(e)}",
                topic=topic,
                error_code="PUBLISH_FAILED",
            )

    async def publish_dlq(
        self,
        message: dict,
        error: str,
    ) -> None:
        """
        Publish failed message to dead-letter queue.

        Args:
            message: Original message that failed.
            error: Error description.
        """
        if not self.producer:
            logger.error("Producer not initialized, cannot publish to DLQ")
            return

        try:
            dlq_message = {
                "original_message": message,
                "error": error,
                "timestamp": self.settings.app_name,
            }

            self.producer.produce(
                topic=self.settings.kafka_dlq_topic,
                key=message.get("article_id", "unknown").encode("utf-8"),
                value=json.dumps(dlq_message).encode("utf-8"),
            )

            logger.warning(f"Published message to DLQ: {error}")

        except Exception as e:
            logger.error(f"Failed to publish to DLQ: {str(e)}")

    def _delivery_report(self, err: Optional[KafkaError], msg: Any) -> None:
        """
        Delivery report callback for Kafka producer.

        Args:
            err: Error if delivery failed.
            msg: Delivered message.
        """
        if err is not None:
            logger.error(f"Message delivery failed: {err}")
            self._delivery_reports.append(
                {
                    "status": "failed",
                    "error": str(err),
                    "topic": msg.topic() if msg else None,
                }
            )
        else:
            logger.debug(
                f"Message delivered to {msg.topic()} [{msg.partition()}] "
                f"at offset {msg.offset()}"
            )
            self._delivery_reports.append(
                {
                    "status": "success",
                    "topic": msg.topic(),
                    "partition": msg.partition(),
                    "offset": msg.offset(),
                }
            )

    def _get_schema(self) -> str:
        """
        Get Avro schema for news_raw topic.

        Returns:
            str: Avro schema JSON string.
        """
        # This would typically be loaded from schema registry or file
        # For now, return inline schema
        return json.dumps(
            {
                "type": "record",
                "name": "NewsRaw",
                "namespace": "com.sentiment_analyzer.crawler",
                "fields": [
                    {"name": "article_id", "type": "string"},
                    {"name": "canonical_url", "type": "string"},
                    {"name": "title", "type": "string"},
                    {"name": "body", "type": "string"},
                    {"name": "url", "type": "string"},
                    {"name": "source", "type": "string"},
                    {"name": "language", "type": "string"},
                    {"name": "published_at", "type": "string"},
                    {"name": "crawled_at", "type": "string"},
                    {"name": "country", "type": ["null", "string"]},
                    {"name": "checksum", "type": "string"},
                    {"name": "validation_score", "type": "float"},
                    {"name": "schema_version", "type": "string"},
                    {"name": "ingest_job_id", "type": "string"},
                    {"name": "publisher_id", "type": "string"},
                    {"name": "author", "type": ["null", "string"]},
                    {"name": "raw_html", "type": ["null", "string"]},
                    {"name": "extraction_method", "type": "string"},
                    {
                        "name": "metadata",
                        "type": {"type": "map", "values": "string"},
                    },
                ],
            }
        )

    def get_delivery_reports(self) -> list[dict]:
        """
        Get delivery reports for monitoring.

        Returns:
            list[dict]: List of delivery report dictionaries.
        """
        return self._delivery_reports.copy()
