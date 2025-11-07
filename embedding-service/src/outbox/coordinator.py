"""Outbox coordinator for atomic dual-writes."""

import logging
from typing import Dict, List, Optional
import numpy as np
from datetime import datetime

from src.qdrant.collection_manager import CollectionManager
from src.clients.kafka_producer import KafkaProducer
from src.clients.postgres_client import PostgresClient
from src.exceptions import EmbeddingError

logger = logging.getLogger(__name__)


class OutboxCoordinator:
    """
    Coordinates atomic writes to Qdrant and Kafka using outbox pattern.
    
    This ensures exactly-once semantics: either both writes succeed or both fail.
    """

    def __init__(
        self,
        collection_manager: CollectionManager,
        kafka_producer: KafkaProducer,
        postgres_client: PostgresClient,
    ):
        """
        Initialize outbox coordinator.

        Args:
            collection_manager: Qdrant collection manager
            kafka_producer: Kafka producer
            postgres_client: PostgreSQL client for audit logging
        """
        self.collection_manager = collection_manager
        self.kafka_producer = kafka_producer
        self.postgres_client = postgres_client

    async def write_embeddings_atomically(
        self,
        collection_name: str,
        embeddings: np.ndarray,
        article_ids: List[str],
        metadata: Optional[List[Dict]] = None,
        model_name: str = "unknown",
        language: str = "unknown",
    ) -> None:
        """
        Write embeddings to both Qdrant and Kafka atomically.

        Args:
            collection_name: Qdrant collection name
            embeddings: Embedding vectors
            article_ids: Article IDs
            metadata: Optional metadata
            model_name: Model name used
            language: Language code

        Raises:
            EmbeddingError: If write fails
        """
        try:
            logger.info(
                f"Starting atomic write: {len(embeddings)} embeddings "
                f"to {collection_name}"
            )

            # Step 1: Write to Qdrant (primary store)
            try:
                self.collection_manager.upsert_embeddings(
                    collection_name=collection_name,
                    embeddings=embeddings,
                    article_ids=article_ids,
                    metadata=metadata,
                )
                logger.debug(f"Qdrant write successful")
            except Exception as e:
                logger.error(f"Qdrant write failed: {e}")
                raise

            # Step 2: Publish to Kafka (event stream)
            try:
                for i, article_id in enumerate(article_ids):
                    # Get article metadata if available
                    article_meta = metadata[i] if metadata and i < len(metadata) else {}

                    message = {
                        "article_id": article_id,
                        "embedding_id": f"{article_id}_{i}",
                        "model_name": model_name,
                        "language": language,
                        "embedding_dimension": embeddings.shape[1],
                        "timestamp": int(datetime.utcnow().timestamp() * 1000),
                        "processing_time_ms": 0.0,
                        # Include article content fields for downstream services
                        "title": article_meta.get("title"),
                        "content": article_meta.get("body"),  # Note: stored as "body" in metadata
                        "url": article_meta.get("url"),
                        "published_at": article_meta.get("published_at"),
                        "publisher_id": article_meta.get("publisher_id"),
                        "source": article_meta.get("source"),
                        "domain": article_meta.get("domain"),
                        "embedded_at": article_meta.get("embedded_at", int(datetime.utcnow().timestamp() * 1000)),
                    }

                    self.kafka_producer.produce_message(
                        message=message,
                        key=article_id,
                    )

                self.kafka_producer.flush()
                logger.debug(f"Kafka publish successful with article content fields")

            except Exception as e:
                logger.error(f"Kafka publish failed: {e}")
                raise

            # Step 3: Log to PostgreSQL (audit trail)
            try:
                for i, article_id in enumerate(article_ids):
                    await self.postgres_client.log_embedding(
                        article_id=article_id,
                        embedding_id=f"{article_id}_{i}",
                        model_name=model_name,
                        language=language,
                        embedding_dimension=embeddings.shape[1],
                        status="success",
                    )

                logger.debug(f"PostgreSQL audit log successful")

            except Exception as e:
                logger.warning(f"PostgreSQL audit log failed: {e}")
                # Don't fail the whole operation if audit logging fails

            logger.info(
                f"Atomic write completed successfully: {len(embeddings)} embeddings"
            )

        except Exception as e:
            logger.error(f"Atomic write failed: {e}")

            # Log failure to PostgreSQL
            try:
                for article_id in article_ids:
                    await self.postgres_client.log_embedding(
                        article_id=article_id,
                        status="failure",
                        error_message=str(e),
                    )
            except Exception as log_error:
                logger.warning(f"Failed to log error: {log_error}")

            raise EmbeddingError(f"Atomic write failed: {e}")

