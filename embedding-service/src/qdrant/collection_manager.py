"""Collection management for Qdrant."""

import logging
from typing import List, Dict, Optional
import numpy as np
from qdrant_client.models import PointStruct
import uuid

from src.qdrant.client import QdrantClient
from src.exceptions import QdrantWriteError

logger = logging.getLogger(__name__)


class CollectionManager:
    """Manages Qdrant collections and point operations."""

    def __init__(self, qdrant_client: QdrantClient):
        """
        Initialize collection manager.

        Args:
            qdrant_client: QdrantClient instance
        """
        self.client = qdrant_client

    def ensure_collection_exists(
        self,
        collection_name: str,
        vector_size: int = 768,
    ) -> None:
        """
        Ensure collection exists, create if not.

        Args:
            collection_name: Name of the collection
            vector_size: Dimension of vectors
        """
        if not self.client.collection_exists(collection_name):
            self.client.create_collection(
                collection_name=collection_name,
                vector_size=vector_size,
                distance_metric="Cosine",
            )

    def build_points(
        self,
        embeddings: np.ndarray,
        article_ids: List[str],
        metadata: Optional[List[Dict]] = None,
    ) -> List[PointStruct]:
        """
        Build PointStruct objects for Qdrant.

        Args:
            embeddings: Array of embeddings (n_samples, embedding_dim)
            article_ids: List of article IDs
            metadata: Optional list of metadata dictionaries

        Returns:
            List of PointStruct objects
        """
        if len(embeddings) != len(article_ids):
            raise ValueError("embeddings and article_ids must have same length")

        points = []

        for i, (embedding, article_id) in enumerate(zip(embeddings, article_ids)):
            # Create payload with metadata
            payload = {
                "article_id": article_id,
                "embedding_index": i,
            }

            if metadata and i < len(metadata):
                payload.update(metadata[i])
                # Debug log first point's metadata
                if i == 0:
                    logger.info(f"Sample metadata for first point: {metadata[i]}")

            # Create point with UUID as ID
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding.tolist(),
                payload=payload,
            )

            points.append(point)

        logger.debug(f"Built {len(points)} points for Qdrant")

        return points

    def upsert_embeddings(
        self,
        collection_name: str,
        embeddings: np.ndarray,
        article_ids: List[str],
        metadata: Optional[List[Dict]] = None,
    ) -> None:
        """
        Upsert embeddings to collection.

        Args:
            collection_name: Name of the collection
            embeddings: Array of embeddings
            article_ids: List of article IDs
            metadata: Optional metadata

        Raises:
            QdrantWriteError: If upsert fails
        """
        try:
            # Ensure collection exists
            self.ensure_collection_exists(
                collection_name,
                vector_size=embeddings.shape[1],
            )

            # Build points
            points = self.build_points(embeddings, article_ids, metadata)

            # Upsert to Qdrant
            self.client.upsert_points(collection_name, points)

            logger.info(
                f"Upserted {len(points)} embeddings to {collection_name}"
            )

        except Exception as e:
            logger.error(f"Failed to upsert embeddings: {e}")
            raise QdrantWriteError(f"Failed to upsert embeddings: {e}")

    def search_similar(
        self,
        collection_name: str,
        query_embedding: np.ndarray,
        limit: int = 10,
    ) -> List[Dict]:
        """
        Search for similar embeddings.

        Args:
            collection_name: Name of the collection
            query_embedding: Query embedding vector
            limit: Number of results

        Returns:
            List of search results
        """
        return self.client.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=limit,
        )

    def get_collection_info(self, collection_name: str) -> Optional[Dict]:
        """Get collection information."""
        try:
            info = self.client.client.get_collection(collection_name)
            return {
                "name": info.name,
                "points_count": info.points_count,
                "vectors_count": info.vectors_count,
            }
        except Exception as e:
            logger.warning(f"Failed to get collection info: {e}")
            return None

