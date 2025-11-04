"""Main embedding service orchestrator."""

import logging
import asyncio
from typing import Optional

from src.config import config
from src.models.model_loader import ModelLoader
from src.models.model_pool import ModelPool
from src.models.model_router import ModelRouter
from src.models.model_registry import ModelRegistry
from src.preprocessing.text_preprocessor import TextPreprocessor
from src.batching.dynamic_batcher import DynamicBatcher
from src.embedding.embedding_engine import EmbeddingEngine
from src.validation.embedding_validator import EmbeddingValidator
from src.qdrant.client import QdrantClient
from src.qdrant.collection_manager import CollectionManager
from src.clients.kafka_consumer import KafkaConsumer
from src.clients.kafka_producer import KafkaProducer
from src.clients.postgres_client import PostgresClient
from src.drift.drift_detector import DriftDetector
from src.outbox.coordinator import OutboxCoordinator
from src.exceptions import EmbeddingError

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Main embedding service."""

    def __init__(self):
        """Initialize embedding service."""
        self.config = config
        self.model_loader = ModelLoader(config.model.cache_dir)
        self.model_router = ModelRouter()
        self.model_registry = ModelRegistry()
        self.model_pool = ModelPool(
            self.model_loader,
            max_models=config.model.model_pool_size,
        )
        self.text_preprocessor = TextPreprocessor()
        self.dynamic_batcher = DynamicBatcher(
            device=config.model.device,
            base_batch_size=config.model.batch_size_gpu,
        )
        self.embedding_engine = EmbeddingEngine(
            self.model_pool,
            self.model_router,
            self.text_preprocessor,
            self.dynamic_batcher,
        )
        self.embedding_validator = EmbeddingValidator(
            expected_dimension=config.qdrant.vector_size,
        )
        self.qdrant_client = QdrantClient()
        self.collection_manager = CollectionManager(self.qdrant_client)
        self.kafka_consumer = KafkaConsumer()
        self.kafka_producer = KafkaProducer()
        self.postgres_client = PostgresClient()
        self.drift_detector = DriftDetector(
            sample_size=config.validation.drift_sample_size,
            drift_threshold=config.validation.drift_threshold,
        )
        self.outbox_coordinator = OutboxCoordinator(
            self.collection_manager,
            self.kafka_producer,
            self.postgres_client,
        )
        self._running = False

    async def initialize(self) -> None:
        """Initialize all service components."""
        try:
            logger.info("Initializing embedding service...")

            # Initialize Qdrant
            self.qdrant_client.connect()

            # Initialize Kafka
            self.kafka_consumer.initialize()
            self.kafka_producer.initialize()

            # Initialize PostgreSQL (optional - log warning if fails)
            try:
                await self.postgres_client.initialize()
            except Exception as e:
                logger.warning(f"PostgreSQL initialization failed (optional): {e}")
                logger.warning("Continuing without PostgreSQL audit logging")

            # Initialize model registry (optional - log warning if fails)
            try:
                await self.model_registry.initialize()
            except Exception as e:
                logger.warning(f"Model registry initialization failed (optional): {e}")
                logger.warning("Continuing without model registry")

            logger.info("Embedding service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize service: {e}")
            raise

    async def shutdown(self) -> None:
        """Shutdown service and cleanup resources."""
        try:
            logger.info("Shutting down embedding service...")

            self._running = False

            # Close Kafka
            self.kafka_consumer.close()
            self.kafka_producer.close()

            # Close Qdrant
            self.qdrant_client.disconnect()

            # Close PostgreSQL
            await self.postgres_client.close()

            # Close model registry
            await self.model_registry.close()

            # Unload models
            self.model_pool.clear()

            logger.info("Embedding service shutdown complete")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

    async def process_batch(self) -> int:
        """
        Process a batch of messages from Kafka.

        Returns:
            Number of messages processed
        """
        try:
            # Consume batch
            messages = self.kafka_consumer.consume_batch(
                batch_size=self.config.model.batch_size_gpu,
                timeout_ms=self.config.kafka.processing_timeout_seconds * 1000,
            )

            if not messages:
                logger.debug("No messages to process")
                return 0

            logger.info(f"Processing batch of {len(messages)} messages")

            # Extract texts and article IDs
            texts = [msg.get("normalized_body", "") for msg in messages]
            article_ids = [msg.get("article_id", "") for msg in messages]
            languages = [msg.get("language", "en") for msg in messages]

            # Compute embeddings
            embeddings, _ = self.embedding_engine.compute_embeddings(
                texts=texts,
                article_ids=article_ids,
                language=languages[0] if languages else "en",
            )

            # Validate embeddings
            if self.config.validation.enabled:
                validation_result = self.embedding_validator.validate_batch(
                    embeddings
                )
                if not validation_result["valid"]:
                    logger.warning(
                        f"Validation failed: {validation_result['invalid_count']} "
                        f"invalid embeddings"
                    )

            # Detect drift
            if self.config.validation.drift_detection_enabled:
                self.drift_detector.add_samples(embeddings)
                drift_result = self.drift_detector.detect_drift(embeddings)
                if drift_result["drift_detected"]:
                    logger.warning(
                        f"Drift detected: KS={drift_result['ks_statistic']:.4f}"
                    )

            # Write to Qdrant and Kafka atomically
            await self.outbox_coordinator.write_embeddings_atomically(
                collection_name=self.config.qdrant.collection_name,
                embeddings=embeddings,
                article_ids=article_ids,
                model_name=self.model_router.select_model(languages[0] if languages else "en"),
                language=languages[0] if languages else "en",
            )

            # Commit offset
            self.kafka_consumer.commit_offset()

            logger.info(f"Processed batch of {len(messages)} messages successfully")

            return len(messages)

        except Exception as e:
            logger.error(f"Failed to process batch: {e}")
            return 0

    async def run(self) -> None:
        """Run the embedding service."""
        try:
            await self.initialize()
            self._running = True

            logger.info("Embedding service started")

            while self._running:
                try:
                    processed = await self.process_batch()
                    if processed == 0:
                        await asyncio.sleep(1)
                except Exception as e:
                    logger.error(f"Error in processing loop: {e}")
                    await asyncio.sleep(5)

        except Exception as e:
            logger.error(f"Service error: {e}")
        finally:
            await self.shutdown()

    def stop(self) -> None:
        """Stop the service."""
        self._running = False

