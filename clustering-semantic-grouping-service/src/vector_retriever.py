"""Vector retrieval from Qdrant with filtering and pagination."""

import logging
from datetime import datetime
from typing import List, Tuple, Optional
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, DatetimeRange, Range

logger = logging.getLogger(__name__)


class VectorRetriever:
    """Retrieves embeddings from Qdrant with metadata filtering."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        collection_name: str = "news_embeddings_v1",
        timeout: int = 30,
    ):
        """
        Initialize vector retriever.

        Args:
            host: Qdrant host
            port: Qdrant port
            collection_name: Collection name in Qdrant
            timeout: Request timeout in seconds
        """
        self.client = QdrantClient(host=host, port=port, timeout=timeout)
        self.collection_name = collection_name
        logger.info(f"Initialized VectorRetriever: {host}:{port}/{collection_name}")

    def retrieve_embeddings(
        self,
        window_start: datetime,
        window_end: datetime,
        min_credibility: float = 0.7,
        batch_size: int = 1000,
    ) -> Tuple[np.ndarray, List[dict]]:
        """
        Retrieve embeddings within time window with filtering.

        Args:
            window_start: Start of time window (UTC)
            window_end: End of time window (UTC)
            min_credibility: Minimum publisher credibility score
            batch_size: Batch size for pagination

        Returns:
            Tuple of (embeddings array, metadata list)
        """
        all_embeddings = []
        all_metadata = []
        offset = None

        logger.info(
            f"Retrieving embeddings from {window_start.isoformat()} "
            f"to {window_end.isoformat()}"
        )

        try:
            while True:
                # Build filter for time window and credibility
                filter_conditions = Filter(
                    must=[
                        FieldCondition(
                            key="embedded_at",
                            range=DatetimeRange(
                                gte=window_start.timestamp(),
                                lte=window_end.timestamp(),
                            ),
                        ),
                        FieldCondition(
                            key="publisher_credibility",
                            range=Range(gte=min_credibility),
                        ),
                    ]
                )

                # Scroll through collection
                points, next_offset = self.client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=filter_conditions,
                    limit=batch_size,
                    offset=offset,
                    with_vectors=True,
                    with_payload=True,
                )

                if not points:
                    break

                # Extract embeddings and metadata
                for point in points:
                    embedding = np.array(point.vector, dtype=np.float32)
                    metadata = {
                        "article_id": point.payload.get("article_id"),
                        "embedded_at": point.payload.get("embedded_at"),
                        "publisher_credibility": point.payload.get("publisher_credibility"),
                        "language": point.payload.get("language"),
                        "domain": point.payload.get("domain"),
                    }
                    all_embeddings.append(embedding)
                    all_metadata.append(metadata)

                offset = next_offset
                if offset is None:
                    break

            # Convert to numpy array
            if all_embeddings:
                embeddings_array = np.vstack(all_embeddings)
            else:
                embeddings_array = np.array([])

            logger.info(
                f"Retrieved {len(all_embeddings)} embeddings "
                f"(shape: {embeddings_array.shape})"
            )

            return embeddings_array, all_metadata

        except Exception as e:
            logger.error(f"Error retrieving embeddings: {e}", exc_info=True)
            raise

    def get_collection_info(self) -> dict:
        """Get collection information."""
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "points_count": info.points_count,
                "vectors_count": info.vectors_count,
                "config": info.config,
            }
        except Exception as e:
            logger.error(f"Error getting collection info: {e}", exc_info=True)
            raise

