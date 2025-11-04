"""Embedding validation."""

import logging
import numpy as np
from typing import List, Dict

from src.exceptions import ValidationError
from src.metrics import embedding_validation_failures_total
from src.embedding.normalization import get_embedding_norm

logger = logging.getLogger(__name__)


class EmbeddingValidator:
    """Validates embeddings for quality and correctness."""

    def __init__(
        self,
        expected_dimension: int = 768,
        expected_norm_range: tuple = (0.99, 1.01),
    ):
        """
        Initialize validator.

        Args:
            expected_dimension: Expected embedding dimension
            expected_norm_range: Expected L2 norm range for normalized embeddings
        """
        self.expected_dimension = expected_dimension
        self.expected_norm_range = expected_norm_range

    def validate_embedding(self, embedding: np.ndarray) -> Dict:
        """
        Validate a single embedding.

        Args:
            embedding: 1D embedding array

        Returns:
            Dict with 'valid' (bool) and 'errors' (list) keys
        """
        errors = []
        try:
            # Check dimension
            if len(embedding) != self.expected_dimension:
                error_msg = (
                    f"Invalid embedding dimension: {len(embedding)} "
                    f"(expected {self.expected_dimension})"
                )
                logger.warning(error_msg)
                embedding_validation_failures_total.labels(
                    check_type="dimension"
                ).inc()
                errors.append(error_msg)

            # Check for NaN or Inf
            if np.isnan(embedding).any() or np.isinf(embedding).any():
                error_msg = "Embedding contains NaN or Inf values"
                logger.warning(error_msg)
                embedding_validation_failures_total.labels(
                    check_type="nan_inf"
                ).inc()
                errors.append(error_msg)

            # Check norm (for normalized embeddings)
            norm = get_embedding_norm(embedding)
            if not (self.expected_norm_range[0] <= norm <= self.expected_norm_range[1]):
                error_msg = (
                    f"Embedding norm out of range: {norm} "
                    f"(expected {self.expected_norm_range})"
                )
                logger.warning(error_msg)
                embedding_validation_failures_total.labels(
                    check_type="norm"
                ).inc()
                errors.append(error_msg)

            # Check for zero embedding
            if np.allclose(embedding, 0):
                error_msg = "Embedding is all zeros"
                logger.warning(error_msg)
                embedding_validation_failures_total.labels(
                    check_type="zero"
                ).inc()
                errors.append(error_msg)

            return {"valid": len(errors) == 0, "errors": errors}

        except Exception as e:
            logger.error(f"Validation error: {e}")
            embedding_validation_failures_total.labels(
                check_type="error"
            ).inc()
            return {"valid": False, "errors": [str(e)]}

    def validate_batch(
        self,
        embeddings: np.ndarray,
    ) -> Dict[str, any]:
        """
        Validate a batch of embeddings.

        Args:
            embeddings: Array of shape (n_samples, embedding_dim)

        Returns:
            Dictionary with validation results
        """
        if embeddings.size == 0:
            return {
                "valid": True,
                "total": 0,
                "valid_count": 0,
                "invalid_count": 0,
                "invalid_indices": [],
            }

        invalid_indices = []

        for i, embedding in enumerate(embeddings):
            result = self.validate_embedding(embedding)
            if not result["valid"]:
                invalid_indices.append(i)

        valid_count = len(embeddings) - len(invalid_indices)
        is_valid = len(invalid_indices) == 0

        logger.info(
            f"Batch validation: {valid_count}/{len(embeddings)} valid "
            f"({100 * valid_count / len(embeddings):.1f}%)"
        )

        return {
            "valid": is_valid,
            "total": len(embeddings),
            "valid_count": valid_count,
            "invalid_count": len(invalid_indices),
            "invalid_indices": invalid_indices,
        }

