"""Kafka producer for entities_extracted topic."""

import logging
import json
from confluent_kafka import Producer, KafkaError
from confluent_kafka.schema_registry import SchemaRegistryClient, SerializationContext, MessageField
from confluent_kafka.schema_registry.avro import AvroSerializer
from src.models import EntitiesExtractedMessage
from src.exceptions import KafkaError as KafkaServiceError

logger = logging.getLogger(__name__)


class KafkaProducerClient:
    """Kafka producer for entities_extracted topic."""

    def __init__(
        self,
        brokers: str,
        schema_registry_url: str,
        output_topic: str,
    ):
        """
        Initialize Kafka producer.

        Args:
            brokers: Kafka bootstrap servers
            schema_registry_url: Schema Registry URL
            output_topic: Output topic name
        """
        self.brokers = brokers
        self.output_topic = output_topic

        try:
            # Initialize schema registry
            self.schema_registry_client = SchemaRegistryClient(
                {"url": schema_registry_url}
            )

            # Initialize Avro serializer
            self.avro_serializer = AvroSerializer(
                self.schema_registry_client,
                self._get_schema(),
            )

            # Initialize producer
            self.producer = Producer(
                {
                    "bootstrap.servers": brokers,
                    "acks": "all",
                    "retries": 3,
                    "max.in.flight.requests.per.connection": 1,
                }
            )

            logger.info(
                f"Kafka producer initialized for topic {output_topic}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            raise KafkaServiceError(f"Failed to initialize producer: {e}")

    def produce_message(self, message: EntitiesExtractedMessage) -> bool:
        """
        Produce a message.

        Args:
            message: Message to produce

        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert message to dict
            message_dict = message.model_dump()

            # Create serialization context
            ctx = SerializationContext(self.output_topic, MessageField.VALUE)

            # Serialize and produce
            self.producer.produce(
                topic=self.output_topic,
                key=message.article_id.encode("utf-8"),
                value=self.avro_serializer(message_dict, ctx),
                on_delivery=self._delivery_report,
            )

            # Flush to ensure delivery
            self.producer.flush()
            logger.debug(f"Produced message for article: {message.article_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to produce message: {e}")
            return False

    def _delivery_report(self, err, msg):
        """Delivery report callback."""
        if err is not None:
            logger.error(f"Message delivery failed: {err}")
        else:
            logger.debug(
                f"Message delivered to {msg.topic()} "
                f"[{msg.partition()}] at offset {msg.offset()}"
            )

    def _get_schema(self) -> str:
        """Get Avro schema for entities_extracted."""
        return json.dumps({
            "type": "record",
            "name": "EntitiesExtractedMessage",
            "namespace": "com.sentiment_analyzer.ner",
            "fields": [
                {"name": "article_id", "type": "string"},
                {
                    "name": "entities",
                    "type": {
                        "type": "array",
                        "items": {
                            "type": "record",
                            "name": "Entity",
                            "fields": [
                                {"name": "entity_id", "type": "string"},
                                {"name": "text", "type": "string"},
                                {"name": "normalized_text", "type": "string"},
                                {"name": "entity_type", "type": "string"},
                                {"name": "start_char", "type": "int"},
                                {"name": "end_char", "type": "int"},
                                {"name": "confidence", "type": "double"},
                                {"name": "wikidata_id", "type": ["null", "string"]},
                                {"name": "dbpedia_uri", "type": ["null", "string"]},
                                {"name": "country", "type": ["null", "string"]},
                                {
                                    "name": "aliases",
                                    "type": {"type": "array", "items": "string"},
                                },
                                {"name": "context_snippet", "type": "string"},
                            ],
                        },
                    },
                },
                {"name": "language", "type": "string"},
                {"name": "ner_model", "type": "string"},
                {"name": "entity_count", "type": "int"},
                {"name": "coverage_score", "type": "double"},
                {"name": "linking_success_rate", "type": "double"},
                {"name": "extracted_at", "type": "string"},
                {"name": "trace_id", "type": "string"},
                {"name": "schema_version", "type": "string"},
            ],
        })

    def close(self) -> None:
        """Close producer."""
        try:
            self.producer.flush()
            logger.info("Kafka producer closed")
        except Exception as e:
            logger.error(f"Error closing producer: {e}")

