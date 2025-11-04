"""Qdrant client wrapper."""

import logging
from typing import List, Dict, Optional
import numpy as np
from qdrant_client import QdrantClient as QdrantClientLib
from qdrant_client.models import Distance, VectorParams, PointStruct

from src.config import config
from src.exceptions import QdrantConnectionError, QdrantWriteError
from src.metrics import embedding_qdrant_writes_total, embedding_qdrant_write_failures_total

logger = logging.getLogger(__name__)


class QdrantClient:
    """Wrapper around Qdrant client."""

    def __init__(self):
        """Initialize Qdrant client."""
        self.config = config.qdrant
        self.client = None

    def connect(self) -> None:
        """Connect to Qdrant server."""
        try:
            logger.info(
                f"Connecting to Qdrant at {self.config.host}:{self.config.port}"
            )

            self.client = QdrantClientLib(
                host=self.config.host,
                port=self.config.port,
                api_key=self.config.api_key,
            )

            # Test connection
            self.client.get_collections()

            logger.info("Connected to Qdrant successfully")

        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise QdrantConnectionError(f"Failed to connect to Qdrant: {e}")

    def disconnect(self) -> None:
        """Disconnect from Qdrant."""
        if self.client:
            self.client.close()
            logger.info("Disconnected from Qdrant")

    def collection_exists(self, collection_name: str) -> bool:
        """Check if collection exists."""
        try:
            collections = self.client.get_collections()
            return any(c.name == collection_name for c in collections.collections)
        except Exception as e:
            logger.warning(f"Failed to check collection existence: {e}")
            return False

    def create_collection(
        self,
        collection_name: str,
        vector_size: int,
        distance_metric: str = "Cosine",
    ) -> None:
        """
        Create a collection in Qdrant.

        Args:
            collection_name: Name of the collection
            vector_size: Dimension of vectors
            distance_metric: Distance metric (Cosine, Euclid, Manhattan)
        """
        try:
            if self.collection_exists(collection_name):
                logger.info(f"Collection already exists: {collection_name}")
                return

            logger.info(
                f"Creating collection: {collection_name} "
                f"(vector_size={vector_size}, metric={distance_metric})"
            )

            distance = Distance.COSINE if distance_metric == "Cosine" else Distance.EUCLID

            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=distance,
                ),
            )

            logger.info(f"Collection created: {collection_name}")

        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            raise QdrantWriteError(f"Failed to create collection: {e}")

    def upsert_points(
        self,
        collection_name: str,
        points: List[PointStruct],
    ) -> None:
        """
        Upsert points into collection.

        Args:
            collection_name: Name of the collection
            points: List of PointStruct objects

        Raises:
            QdrantWriteError: If upsert fails
        """
        if not points:
            return

        try:
            logger.debug(f"Upserting {len(points)} points to {collection_name}")

            self.client.upsert(
                collection_name=collection_name,
                points=points,
            )

            embedding_qdrant_writes_total.inc(len(points))

            logger.debug(f"Upserted {len(points)} points successfully")

        except Exception as e:
            embedding_qdrant_write_failures_total.inc()
            logger.error(f"Failed to upsert points: {e}")
            raise QdrantWriteError(f"Failed to upsert points: {e}")

    def search(
        self,
        collection_name: str,
        query_vector: np.ndarray,
        limit: int = 10,
    ) -> List[Dict]:
        """
        Search for similar vectors.

        Args:
            collection_name: Name of the collection
            query_vector: Query vector
            limit: Number of results to return

        Returns:
            List of search results
        """
        try:
            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector.tolist(),
                limit=limit,
            )

            return [
                {
                    "id": r.id,
                    "score": r.score,
                    "payload": r.payload,
                }
                for r in results
            ]

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def delete_collection(self, collection_name: str) -> None:
        """Delete a collection."""
        try:
            self.client.delete_collection(collection_name)
            logger.info(f"Deleted collection: {collection_name}")
        except Exception as e:
            logger.warning(f"Failed to delete collection: {e}")

