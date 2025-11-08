"""Embedding feature extractor."""

from typing import Dict, Any, List
import math
import numpy as np
from .base import FeatureExtractor, SemanticGroup, Article, Actor
from ..utils import StructuredLogger

logger = StructuredLogger(__name__)


class EmbeddingExtractor(FeatureExtractor):
    """Extract embedding-related features."""

    def __init__(self):
        """Initialize embedding extractor."""
        super().__init__("embedding_extractor")
        self.features_extracted = [
            "centroid_magnitude",
            "intra_cluster_similarity_mean",
            "intra_cluster_similarity_std",
            "embedding_drift_score",
        ]

    def extract(
        self,
        group: SemanticGroup,
        articles: List[Article],
        actors: List[Actor],
    ) -> Dict[str, Any]:
        """Extract embedding features.

        Args:
            group: Semantic group
            articles: Articles in group
            actors: Actors (unused for embedding features)

        Returns:
            Dictionary of embedding features
        """
        if not self.validate_inputs(group, articles, actors):
            logger.warning("Invalid inputs for embedding extraction", group_id=self.get_group_id(group))
            return {}

        try:
            features = {}

            # Get centroid_vector safely from dict or object
            centroid_vector = group.get("centroid_vector") if isinstance(group, dict) else getattr(group, "centroid_vector", None)
            similarity_avg = group.get("similarity_avg") if isinstance(group, dict) else getattr(group, "similarity_avg", None)
            similarity_std = group.get("similarity_std") if isinstance(group, dict) else getattr(group, "similarity_std", None)
            metadata = group.get("metadata", {}) if isinstance(group, dict) else getattr(group, "metadata", {})

            logger.debug(
                "Embedding extraction inputs",
                group_id=self.get_group_id(group),
                has_centroid_vector=centroid_vector is not None,
                similarity_avg=similarity_avg,
                similarity_std=similarity_std,
                metadata_keys=list(metadata.keys()) if metadata else [],
            )

            # centroid_magnitude: L2 norm of cluster centroid
            if centroid_vector:
                centroid = np.array(centroid_vector)
                features["centroid_magnitude"] = float(np.linalg.norm(centroid))
            else:
                features["centroid_magnitude"] = 1.0  # Default to 1.0 for normalized embeddings

            # intra_cluster_similarity_mean: Average pairwise similarity
            # Using the provided similarity_avg from group metadata
            if similarity_avg is not None:
                features["intra_cluster_similarity_mean"] = float(similarity_avg)
            else:
                features["intra_cluster_similarity_mean"] = 0.5  # Default to 0.5 (neutral)

            # intra_cluster_similarity_std: Std dev of pairwise similarities
            # Try multiple sources for similarity_std
            if similarity_std is not None:
                features["intra_cluster_similarity_std"] = float(similarity_std)
            elif metadata and "similarity_std" in metadata:
                features["intra_cluster_similarity_std"] = float(metadata["similarity_std"])
            else:
                # Compute from article embeddings if available
                # For now, use a default value
                features["intra_cluster_similarity_std"] = 0.1  # Default small variance

            # embedding_drift_score: Distance from baseline embedding distribution
            # This would typically be computed against a baseline distribution
            # For now, use a placeholder based on centroid magnitude variance
            if centroid_vector:
                # Normalize centroid and compute drift as deviation from unit norm
                centroid = np.array(centroid_vector)
                norm = np.linalg.norm(centroid)
                if norm > 0:
                    normalized = centroid / norm
                    # Drift is how much the normalized centroid deviates from uniform
                    expected_value = 1.0 / math.sqrt(len(centroid))
                    drift = np.std(normalized) - expected_value
                    features["embedding_drift_score"] = max(0.0, float(drift))
                else:
                    features["embedding_drift_score"] = 0.0
            else:
                features["embedding_drift_score"] = 0.0

            logger.info(
                "Embedding features extracted",
                group_id=self.get_group_id(group),
                centroid_magnitude=features["centroid_magnitude"],
                intra_cluster_similarity_mean=features["intra_cluster_similarity_mean"],
                intra_cluster_similarity_std=features["intra_cluster_similarity_std"],
            )
            return features

        except Exception as e:
            logger.error(
                "Error extracting embedding features",
                group_id=self.get_group_id(group),
                error=str(e),
            )
            return {}

