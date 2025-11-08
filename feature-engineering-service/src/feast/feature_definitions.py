"""Feast feature view definitions for semantic group features."""

from datetime import timedelta
from feast import Entity, FeatureView, ValueType, Field
from feast.infra.offline_stores.delta_source import DeltaSource
from feast.types import Float32, Int32


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


def create_semantic_group_source(delta_path: str = "/data/delta/semantic_groups") -> DeltaSource:
    """Create Delta Lake source for semantic group features.
    
    Args:
        delta_path: Path to Delta Lake table
        
    Returns:
        DeltaSource configuration
    """
    return DeltaSource(
        path=delta_path,
        timestamp_field="timestamp",
    )


def create_semantic_group_feature_view(
    delta_path: str = "/data/delta/semantic_groups",
    ttl_days: int = 30,
) -> FeatureView:
    """Create semantic group features feature view.
    
    Args:
        delta_path: Path to Delta Lake table
        ttl_days: Time-to-live in days
        
    Returns:
        FeatureView with all 24 semantic group features
    """
    group_id = create_semantic_group_entity()
    source = create_semantic_group_source(delta_path)

    return FeatureView(
        name="semantic_group_features",
        entities=[group_id],
        ttl=timedelta(days=ttl_days),
        features=[
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

