"""Embedding feature extractor."""

from typing import Dict, Any, List, Optional
import math
import numpy as np
from .base import FeatureExtractor, SemanticGroup, Article, Actor
from ..utils import StructuredLogger

logger = StructuredLogger(__name__)


class EmbeddingExtractor(FeatureExtractor):
    """Extract embedding-related features."""

    def __init__(self, postgres_client=None):
        """Initialize embedding extractor.

        Args:
            postgres_client: PostgreSQL client for querying reconciliation_log (used for conflict checking)
        """
        super().__init__("embedding_extractor")
        self.postgres_client = postgres_client
        self.features_extracted = [
            "centroid_magnitude",
            "intra_cluster_similarity_mean",
            "intra_cluster_similarity_std",
            "embedding_drift_score",
            "countries",
        ]

    async def extract(
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

            # Read countries directly from the semantic_groups Kafka message
            # The clustering service already extracts countries from NER entities and includes them in the message
            group_id = self.get_group_id(group)
            countries = group.get("countries", []) if isinstance(group, dict) else getattr(group, "countries", [])

            logger.debug(
                "Embedding extraction inputs",
                group_id=self.get_group_id(group),
                has_centroid_vector=centroid_vector is not None,
                centroid_vector_length=len(centroid_vector) if centroid_vector else 0,
                similarity_avg=similarity_avg,
                similarity_std=similarity_std,
                countries_count=len(countries) if countries else 0,
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

            # embedding_drift_score: Variance of centroid components
            # Measures how spread out the centroid values are across dimensions
            # Higher variance indicates more drift from a uniform distribution
            if centroid_vector:
                centroid = np.array(centroid_vector)
                # Use standard deviation of centroid components as drift score
                # This captures how much the embedding varies across dimensions
                drift = float(np.std(centroid))
                features["embedding_drift_score"] = drift
            else:
                features["embedding_drift_score"] = 0.0

            # countries: Comma-separated list of unique countries mentioned in the group
            if countries and isinstance(countries, list):
                unique_countries = sorted(set(countries))  # Sort for consistency
                features["countries"] = ",".join(unique_countries)
            else:
                features["countries"] = ""

            # has_conflict: Boolean indicating if group has conflicting labels
            # True if group has multiple different labels in reconciliation_log
            group_id = self.get_group_id(group)
            features["has_conflict"] = await self._check_conflict_status(group_id)

            logger.info(
                "Embedding features extracted",
                group_id=group_id,
                centroid_magnitude=features["centroid_magnitude"],
                intra_cluster_similarity_mean=features["intra_cluster_similarity_mean"],
                intra_cluster_similarity_std=features["intra_cluster_similarity_std"],
                countries=features["countries"],
                has_conflict=features["has_conflict"],
            )
            return features

        except Exception as e:
            logger.error(
                "Error extracting embedding features",
                group_id=self.get_group_id(group),
                error=str(e),
            )
            return {}

    async def _check_conflict_status(self, group_id: str) -> Optional[bool]:
        """Check if a group is about war/conflict based on GDELT metadata.

        A conflict exists when any matched GDELT event has label_conflict=1.
        This indicates the event is about war, violence, protests, or armed conflict.

        Args:
            group_id: Semantic group ID

        Returns:
            True if any matched event is about conflict/war
            False if matched events exist but none are conflicts
            None if no reconciliation data exists (unreconciled group)
        """
        if not self.postgres_client:
            logger.warning(f"PostgreSQL client not available for checking conflict: group_id={group_id}")
            return None

        try:
            # asyncpg uses $1, $2, etc. for placeholders
            query = """
                SELECT MAX(label_conflict) as max_label_conflict,
                       COUNT(*) as label_count
                FROM reconciliation_log
                WHERE group_id = $1
            """

            logger.debug(f"Checking conflict status: group_id={group_id}")
            result = await self.postgres_client.execute_query(query, str(group_id))

            if result and len(result) > 0:
                label_count = result[0].get("label_count", 0)

                # If no reconciliation data exists, return None (not labeled)
                if label_count == 0:
                    logger.debug(f"No reconciliation data found for group_id={group_id} - returning None")
                    return None

                max_label_conflict = result[0].get("max_label_conflict")

                # If max_label_conflict is None, it means reconciled but no GDELT metadata (old data)
                if max_label_conflict is None:
                    logger.debug(f"Reconciled but no GDELT metadata for group_id={group_id} - returning None")
                    return None

                # Conflict if any matched GDELT event has label_conflict=1
                has_conflict = max_label_conflict == 1

                logger.info(
                    f"Conflict check: group_id={group_id}, "
                    f"label_count={label_count}, max_label_conflict={max_label_conflict}, has_conflict={has_conflict}"
                )
                return has_conflict

            logger.debug(f"No reconciliation data found for group_id={group_id} - returning None")
            return None

        except Exception as e:
            logger.error(
                f"Failed to check conflict status: group_id={group_id}, error_type={type(e).__name__}, error={str(e)}"
            )
            return None

