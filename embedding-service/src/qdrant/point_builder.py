"""Point builder for Qdrant vector database."""

import logging
from typing import Dict, List, Any
import uuid
import numpy as np
from qdrant_client.models import PointStruct, VectorParams

logger = logging.getLogger(__name__)


class PointBuilder:
    """Builds points for Qdrant vector database."""

    def __init__(self, collection_name: str, vector_size: int):
        """
        Initialize point builder.

        Args:
            collection_name: Name of Qdrant collection
            vector_size: Size of embedding vectors
        """
        self.collection_name = collection_name
        self.vector_size = vector_size

    def build_point(
        self,
        embedding: np.ndarray,
        metadata: Dict[str, Any],
        point_id: str = None,
    ) -> PointStruct:
        """
        Build a single point for Qdrant.

        Args:
            embedding: Embedding vector
            metadata: Metadata dictionary
            point_id: Optional point ID (generated if not provided)

        Returns:
            PointStruct for Qdrant
        """
        if point_id is None:
            point_id = str(uuid.uuid4())

        # Convert embedding to list
        if isinstance(embedding, np.ndarray):
            embedding = embedding.tolist()

        # Validate embedding dimension
        if len(embedding) != self.vector_size:
            raise ValueError(
                f"Embedding dimension {len(embedding)} "
                f"does not match collection dimension {self.vector_size}"
            )

        # Create point
        point = PointStruct(
            id=point_id,
            vector=embedding,
            payload=metadata,
        )

        return point

    def build_points(
        self,
        embeddings: np.ndarray,
        metadatas: List[Dict[str, Any]],
        point_ids: List[str] = None,
    ) -> List[PointStruct]:
        """
        Build multiple points for Qdrant.

        Args:
            embeddings: Array of embeddings (n_samples, vector_size)
            metadatas: List of metadata dictionaries
            point_ids: Optional list of point IDs

        Returns:
            List of PointStruct objects
        """
        if len(embeddings) != len(metadatas):
            raise ValueError(
                f"Number of embeddings ({len(embeddings)}) "
                f"does not match number of metadatas ({len(metadatas)})"
            )

        if point_ids is None:
            point_ids = [str(uuid.uuid4()) for _ in range(len(embeddings))]

        if len(point_ids) != len(embeddings):
            raise ValueError(
                f"Number of point IDs ({len(point_ids)}) "
                f"does not match number of embeddings ({len(embeddings)})"
            )

        points = []
        for i, (embedding, metadata, point_id) in enumerate(
            zip(embeddings, metadatas, point_ids)
        ):
            try:
                point = self.build_point(embedding, metadata, point_id)
                points.append(point)
            except Exception as e:
                logger.error(f"Error building point {i}: {e}")
                raise

        logger.debug(f"Built {len(points)} points for collection {self.collection_name}")

        return points

    def build_batch_points(
        self,
        embeddings: np.ndarray,
        metadatas: List[Dict[str, Any]],
        batch_size: int = 100,
        point_ids: List[str] = None,
    ) -> List[List[PointStruct]]:
        """
        Build points in batches.

        Args:
            embeddings: Array of embeddings
            metadatas: List of metadata dictionaries
            batch_size: Size of each batch
            point_ids: Optional list of point IDs

        Returns:
            List of batches of PointStruct objects
        """
        points = self.build_points(embeddings, metadatas, point_ids)

        batches = []
        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            batches.append(batch)

        logger.debug(
            f"Built {len(batches)} batches of points "
            f"(batch_size={batch_size})"
        )

        return batches

    def validate_embedding(self, embedding: np.ndarray) -> bool:
        """
        Validate embedding.

        Args:
            embedding: Embedding vector

        Returns:
            True if valid
        """
        if len(embedding) != self.vector_size:
            logger.error(
                f"Invalid embedding dimension: {len(embedding)} "
                f"(expected {self.vector_size})"
            )
            return False

        if np.any(np.isnan(embedding)):
            logger.error("Embedding contains NaN values")
            return False

        if np.any(np.isinf(embedding)):
            logger.error("Embedding contains Inf values")
            return False

        return True

    def validate_metadata(self, metadata: Dict[str, Any]) -> bool:
        """
        Validate metadata.

        Args:
            metadata: Metadata dictionary

        Returns:
            True if valid
        """
        if not isinstance(metadata, dict):
            logger.error("Metadata must be a dictionary")
            return False

        # Check for required fields
        required_fields = ["article_id", "language", "timestamp"]
        for field in required_fields:
            if field not in metadata:
                logger.warning(f"Missing required metadata field: {field}")

        return True

    @staticmethod
    def get_vector_params(vector_size: int) -> VectorParams:
        """
        Get vector parameters for collection creation.

        Args:
            vector_size: Size of vectors

        Returns:
            VectorParams object
        """
        return VectorParams(size=vector_size, distance="Cosine")

