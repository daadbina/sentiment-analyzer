"""Qdrant client wrapper for embedding service."""

import logging
from typing import List, Dict, Optional
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from src.config import config
from src.exceptions import QdrantWriteError

logger = logging.getLogger(__name__)


class QdrantClientWrapper:
    """Wrapper around Qdrant client with error handling."""

    def __init__(self):
        """Initialize Qdrant client wrapper."""
        self.client = None
        self.collection_name = config.qdrant.collection_name
        self.vector_size = config.qdrant.vector_size

    async def initialize(self) -> None:
        """Initialize Qdrant client connection."""
        try:
            logger.info(
                f"Connecting to Qdrant at {config.qdrant.host}:{config.qdrant.port}"
            )

            self.client = QdrantClient(
                host=config.qdrant.host,
                port=config.qdrant.port,
                api_key=config.qdrant.api_key,
                timeout=30,
            )

            # Test connection
            health = self.client.get_collections()
            logger.info(f"Connected to Qdrant, collections: {len(health.collections)}")

        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise QdrantWriteError(f"Failed to connect to Qdrant: {str(e)}")

    async def disconnect(self) -> None:
        """Disconnect from Qdrant."""
        if self.client:
            try:
                self.client.close()
                logger.info("Disconnected from Qdrant")
            except Exception as e:
                logger.error(f"Error disconnecting from Qdrant: {e}")

    async def ensure_collection_exists(self) -> None:
        """Ensure collection exists, create if not."""
        try:
            # Check if collection exists
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if self.collection_name in collection_names:
                logger.info(f"Collection {self.collection_name} already exists")
                return

            # Create collection
            logger.info(f"Creating collection {self.collection_name}")

            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE,
                ),
            )

            logger.info(f"Created collection {self.collection_name}")

        except Exception as e:
            logger.error(f"Failed to ensure collection exists: {e}")
            raise QdrantWriteError(f"Failed to ensure collection: {str(e)}")

    async def upsert_points(
        self,
        points: List[PointStruct],
    ) -> None:
        """
        Upsert points to collection.

        Args:
            points: List of PointStruct objects
        """
        try:
            if not points:
                logger.warning("No points to upsert")
                return

            self.client.upsert(
                collection_name=self.collection_name,
                points=points,
            )

            logger.debug(f"Upserted {len(points)} points to {self.collection_name}")

        except Exception as e:
            logger.error(f"Failed to upsert points: {e}")
            raise QdrantWriteError(f"Failed to upsert points: {str(e)}")

    async def search(
        self,
        query_vector: np.ndarray,
        limit: int = 10,
        score_threshold: float = None,
    ) -> List[Dict]:
        """
        Search for similar vectors.

        Args:
            query_vector: Query embedding vector
            limit: Number of results to return
            score_threshold: Minimum similarity score

        Returns:
            List of search results
        """
        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector.tolist(),
                limit=limit,
                score_threshold=score_threshold,
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
            logger.error(f"Failed to search: {e}")
            raise QdrantWriteError(f"Failed to search: {str(e)}")

    async def delete_points(
        self,
        point_ids: List[str],
    ) -> None:
        """
        Delete points from collection.

        Args:
            point_ids: List of point IDs to delete
        """
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=point_ids,
            )

            logger.debug(f"Deleted {len(point_ids)} points from {self.collection_name}")

        except Exception as e:
            logger.error(f"Failed to delete points: {e}")
            raise QdrantWriteError(f"Failed to delete points: {str(e)}")

    async def get_collection_info(self) -> Dict:
        """
        Get collection information.

        Returns:
            Collection information dictionary
        """
        try:
            info = self.client.get_collection(self.collection_name)

            return {
                "name": info.name,
                "points_count": info.points_count,
                "vectors_count": info.vectors_count,
                "config": info.config,
            }

        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            raise QdrantWriteError(f"Failed to get collection info: {str(e)}")

    async def delete_collection(self) -> None:
        """Delete collection."""
        try:
            self.client.delete_collection(self.collection_name)
            logger.info(f"Deleted collection {self.collection_name}")

        except Exception as e:
            logger.error(f"Failed to delete collection: {e}")
            raise QdrantWriteError(f"Failed to delete collection: {str(e)}")

