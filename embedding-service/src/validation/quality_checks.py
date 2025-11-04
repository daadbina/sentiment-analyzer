"""Quality checks for embeddings."""

import logging
import numpy as np
from typing import Dict

logger = logging.getLogger(__name__)


class QualityChecker:
    """Performs quality checks on embeddings."""

    @staticmethod
    def check_embedding_diversity(embeddings: np.ndarray) -> Dict:
        """
        Check diversity of embeddings (should not be too similar).

        Args:
            embeddings: Array of shape (n_samples, embedding_dim)

        Returns:
            Dictionary with diversity metrics
        """
        if len(embeddings) < 2:
            return {
                "mean_similarity": 0.0,
                "max_similarity": 0.0,
                "min_similarity": 0.0,
                "diversity_score": 1.0,
            }

        # Compute pairwise cosine similarities
        normalized = embeddings / (np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-8)
        similarities = np.dot(normalized, normalized.T)

        # Get upper triangle (excluding diagonal)
        mask = np.triu(np.ones_like(similarities, dtype=bool), k=1)
        pairwise_sims = similarities[mask]

        mean_sim = float(np.mean(pairwise_sims))
        max_sim = float(np.max(pairwise_sims))
        min_sim = float(np.min(pairwise_sims))

        # Diversity score: 1 - mean_similarity (higher is better)
        diversity_score = 1.0 - mean_sim

        logger.debug(
            f"Embedding diversity: mean={mean_sim:.3f}, "
            f"max={max_sim:.3f}, min={min_sim:.3f}, "
            f"diversity_score={diversity_score:.3f}"
        )

        return {
            "mean_similarity": mean_sim,
            "max_similarity": max_sim,
            "min_similarity": min_sim,
            "diversity_score": diversity_score,
        }

    @staticmethod
    def check_embedding_statistics(embeddings: np.ndarray) -> Dict:
        """
        Check statistical properties of embeddings.

        Args:
            embeddings: Array of shape (n_samples, embedding_dim)

        Returns:
            Dictionary with statistical metrics
        """
        if embeddings.size == 0:
            return {
                "mean": 0.0,
                "std": 0.0,
                "min": 0.0,
                "max": 0.0,
                "skewness": 0.0,
            }

        mean = float(np.mean(embeddings))
        std = float(np.std(embeddings))
        min_val = float(np.min(embeddings))
        max_val = float(np.max(embeddings))

        # Compute skewness
        centered = embeddings - mean
        skewness = float(np.mean(centered ** 3) / (std ** 3 + 1e-8))

        logger.debug(
            f"Embedding statistics: mean={mean:.4f}, std={std:.4f}, "
            f"min={min_val:.4f}, max={max_val:.4f}, skewness={skewness:.4f}"
        )

        return {
            "mean": mean,
            "std": std,
            "min": min_val,
            "max": max_val,
            "skewness": skewness,
        }

    @staticmethod
    def check_embedding_sparsity(embeddings: np.ndarray, threshold: float = 1e-6) -> Dict:
        """
        Check sparsity of embeddings.

        Args:
            embeddings: Array of shape (n_samples, embedding_dim)
            threshold: Threshold for considering a value as zero

        Returns:
            Dictionary with sparsity metrics
        """
        if embeddings.size == 0:
            return {
                "sparsity": 0.0,
                "zero_elements": 0,
                "total_elements": 0,
            }

        zero_count = np.sum(np.abs(embeddings) < threshold)
        total_count = embeddings.size
        sparsity = zero_count / total_count

        logger.debug(
            f"Embedding sparsity: {sparsity:.2%} "
            f"({zero_count}/{total_count} elements below {threshold})"
        )

        return {
            "sparsity": sparsity,
            "zero_elements": int(zero_count),
            "total_elements": int(total_count),
        }

    @staticmethod
    def perform_full_quality_check(embeddings: np.ndarray) -> Dict:
        """
        Perform comprehensive quality check.

        Args:
            embeddings: Array of shape (n_samples, embedding_dim)

        Returns:
            Dictionary with all quality metrics
        """
        return {
            "diversity": QualityChecker.check_embedding_diversity(embeddings),
            "statistics": QualityChecker.check_embedding_statistics(embeddings),
            "sparsity": QualityChecker.check_embedding_sparsity(embeddings),
        }

