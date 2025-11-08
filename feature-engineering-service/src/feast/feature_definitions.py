"""Feast feature view definitions for semantic group features."""

from datetime import timedelta
from pathlib import Path
from feast import Entity, FeatureView, ValueType, Field, PushSource
from feast.infra.offline_stores.file_source import FileSource
from feast.types import Float32, Int32, String, UnixTimestamp
from ..utils import StructuredLogger

logger = StructuredLogger(__name__)


def create_semantic_group_entity() -> Entity:
    """Create semantic group entity.

    Returns:
        Entity definition for group_id
    """
    return Entity(
        name="group_id",
        value_type=ValueType.STRING,
        description="Semantic group ID from clustering service",
    )


def create_semantic_group_source(push_source_name: str = "semantic_group_features_push") -> PushSource:
    """Create push source for semantic group features.

    Args:
        push_source_name: Name of the push source

    Returns:
        PushSource configuration
    """
    # Create a FileSource as batch source for offline feature retrieval
    # The batch_source is required by Feast but will be populated via push
    import os
    import pandas as pd
    import pyarrow.parquet as pq

    # Create directory if it doesn't exist
    os.makedirs("data/feast/offline_store", exist_ok=True)

    # Create a minimal parquet file with the correct schema
    parquet_path = "data/feast/offline_store/semantic_groups.parquet"
    if not os.path.exists(parquet_path):
        # Create a minimal DataFrame with the schema
        df = pd.DataFrame({
            "group_id": ["dummy"],
            "timestamp": [0],
            "num_sources": [0],
            "source_credibility_avg": [0.0],
            "source_credibility_std": [0.0],
            "source_diversity_score": [0.0],
            "time_span_hours": [0.0],
            "publication_velocity": [0.0],
            "temporal_concentration": [0.0],
            "days_since_first_article": [0.0],
            "sentiment_mean": [0.0],
            "sentiment_std": [0.0],
            "sentiment_polarity_ratio": [0.0],
            "sentiment_volatility": [0.0],
            "entity_count": [0],
            "entity_diversity": [0],
            "entity_prominence": [0.0],
            "entity_concentration": [0.0],
            "avg_word_count": [0.0],
            "avg_title_length": [0.0],
            "language_diversity": [0],
            "domain_diversity": [0],
            "centroid_magnitude": [0.0],
            "intra_cluster_similarity_mean": [0.0],
            "intra_cluster_similarity_std": [0.0],
            "embedding_drift_score": [0.0],
        })
        df.to_parquet(parquet_path, index=False)
        logger.debug(f"Created minimal parquet file at {parquet_path}")

    batch_source = FileSource(
        path=parquet_path,
        timestamp_field="timestamp",
    )

    return PushSource(
        name=push_source_name,
        batch_source=batch_source,
    )


def create_semantic_group_feature_view(
    push_source_name: str = "semantic_group_features_push",
    ttl_days: int = 30,
) -> FeatureView:
    """Create semantic group features feature view.

    Args:
        push_source_name: Name of the push source
        ttl_days: Time-to-live in days

    Returns:
        FeatureView with all 24 semantic group features
    """
    logger.debug("Creating semantic group feature view", push_source_name=push_source_name, ttl_days=ttl_days)

    logger.debug("Creating semantic group entity")
    group_id = create_semantic_group_entity()
    logger.debug("Entity created", entity_name=group_id.name)

    logger.debug("Creating push source", push_source_name=push_source_name)
    source = create_semantic_group_source(push_source_name)
    logger.debug("Push source created", source_name=source.name)

    logger.debug("Creating FeatureView with 24 features")
    return FeatureView(
        name="semantic_group_features",
        entities=[group_id],
        ttl=timedelta(days=ttl_days),
        schema=[
            # Source features (4)
            Field(name="num_sources", dtype=Int32),
            Field(name="source_credibility_avg", dtype=Float32),
            Field(name="source_credibility_std", dtype=Float32),
            Field(name="source_diversity_score", dtype=Float32),
            # Temporal features (4)
            Field(name="time_span_hours", dtype=Float32),
            Field(name="publication_velocity", dtype=Float32),
            Field(name="temporal_concentration", dtype=Float32),
            Field(name="days_since_first_article", dtype=Float32),
            # Sentiment features (4)
            Field(name="sentiment_mean", dtype=Float32),
            Field(name="sentiment_std", dtype=Float32),
            Field(name="sentiment_polarity_ratio", dtype=Float32),
            Field(name="sentiment_volatility", dtype=Float32),
            # Entity features (4)
            Field(name="entity_count", dtype=Int32),
            Field(name="entity_diversity", dtype=Int32),
            Field(name="entity_prominence", dtype=Float32),
            Field(name="entity_concentration", dtype=Float32),
            # Content features (4)
            Field(name="avg_word_count", dtype=Float32),
            Field(name="avg_title_length", dtype=Float32),
            Field(name="language_diversity", dtype=Int32),
            Field(name="domain_diversity", dtype=Int32),
            # Embedding features (4)
            Field(name="centroid_magnitude", dtype=Float32),
            Field(name="intra_cluster_similarity_mean", dtype=Float32),
            Field(name="intra_cluster_similarity_std", dtype=Float32),
            Field(name="embedding_drift_score", dtype=Float32),
        ],
        source=source,
        description="Semantic group features for news realization prediction",
    )

