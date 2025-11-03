"""Main NER Entity Linking Service."""

import logging
import signal
import sys
from datetime import datetime
from src.config import get_config
from src.ner.orchestrator import NEROrchestrator
from src.ner.model_registry import NERModelRegistry
from src.linking.entity_linker import EntityLinker
from src.linking.wikidata_client import WikidataClient
from src.actors.repository import ActorRepository
from src.clients.kafka_consumer import KafkaConsumerClient
from src.clients.kafka_producer import KafkaProducerClient
from src.models import EntitiesExtractedMessage, Actor, EntityType
from src.normalization.entity_normalizer import EntityNormalizer
from src.metrics import MetricsCollector
from prometheus_client import start_http_server

logger = logging.getLogger(__name__)


class NEREntityLinkingService:
    """Main NER Entity Linking Service."""

    def __init__(self):
        """Initialize service."""
        self.config = get_config()
        self.running = False

        # Initialize components
        self.model_registry = NERModelRegistry(self.config.ner.model_cache_size)
        self.ner_orchestrator = NEROrchestrator(self.model_registry)
        self.wikidata_client = WikidataClient(
            self.config.external_apis.wikidata_api_url,
            self.config.external_apis.wikidata_timeout_seconds,
        )
        self.entity_linker = EntityLinker(
            self.wikidata_client,
            self.config.ner.entity_linking_confidence_threshold,
        )
        self.actor_repository = ActorRepository(
            self.config.postgres.connection_string,
            self.config.postgres.pool_size,
            self.config.postgres.max_overflow,
        )
        self.kafka_consumer = KafkaConsumerClient(
            self.config.kafka.brokers,
            self.config.kafka.schema_registry_url,
            self.config.kafka.consumer_group,
            self.config.kafka.input_topic,
        )
        self.kafka_producer = KafkaProducerClient(
            self.config.kafka.brokers,
            self.config.kafka.schema_registry_url,
            self.config.kafka.output_topic,
        )

        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        logger.info("NER Entity Linking Service initialized")

    def start(self) -> None:
        """Start the service."""
        try:
            logger.info("Starting NER Entity Linking Service")

            # Initialize database schema
            self.actor_repository.initialize_schema()

            # Start Prometheus metrics server
            start_http_server(self.config.monitoring.prometheus_port)
            logger.info(
                f"Prometheus metrics server started on port {self.config.monitoring.prometheus_port}"
            )

            self.running = True

            # Main processing loop
            while self.running:
                self._process_message()

        except KeyboardInterrupt:
            logger.info("Service interrupted")
        except Exception as e:
            logger.error(f"Service error: {e}", exc_info=True)
        finally:
            self.shutdown()

    def _process_message(self) -> None:
        """Process a single message from Kafka."""
        try:
            # Consume message
            message, error = self.kafka_consumer.consume_message(timeout_ms=1000)

            if error:
                logger.error(f"Kafka error: {error}")
                return

            if message is None:
                return

            logger.info(f"Processing article: {message.article_id}")

            # Extract entities
            ner_result = self.ner_orchestrator.extract_entities(
                message.normalized_body, message.language, message.article_id
            )

            # Link entities
            linked_entities, linking_success_rate = self.entity_linker.link_entities(
                ner_result.entities
            )

            # Persist actors
            for entity in linked_entities:
                actor = Actor(
                    name=entity.text,
                    normalized_name=EntityNormalizer.normalize(entity.text, message.language),
                    type=entity.entity_type,
                    aliases=EntityNormalizer.extract_aliases(entity.text),
                    country=entity.country,
                    wikidata_id=entity.wikidata_id,
                )
                self.actor_repository.upsert_actor(actor)

            # Create output message
            output_message = EntitiesExtractedMessage(
                article_id=message.article_id,
                entities=linked_entities,
                language=message.language,
                ner_model=ner_result.model_used,
                entity_count=len(linked_entities),
                coverage_score=ner_result.coverage_score,
                linking_success_rate=linking_success_rate,
                extracted_at=datetime.utcnow().isoformat(),
                trace_id=message.trace_id,
            )

            # Produce output message
            if self.kafka_producer.produce_message(output_message):
                self.kafka_consumer.commit_offset()
                logger.info(
                    f"Successfully processed article {message.article_id}: "
                    f"{len(linked_entities)} entities extracted"
                )
            else:
                logger.error(f"Failed to produce message for article {message.article_id}")

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}")
        self.running = False

    def shutdown(self) -> None:
        """Shutdown service."""
        logger.info("Shutting down NER Entity Linking Service")

        try:
            self.ner_orchestrator.shutdown()
            self.actor_repository.close()
            self.kafka_consumer.close()
            self.kafka_producer.close()
            logger.info("Service shutdown complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


def main():
    """Main entry point."""
    service = NEREntityLinkingService()
    service.start()


if __name__ == "__main__":
    main()

