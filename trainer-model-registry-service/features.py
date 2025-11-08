"""
Feast feature definitions for semantic group features.

Defines the semantic_group_features feature view with all 24 computed features.
"""

from datetime import timedelta
from feast import Entity, Feature, FeatureView, ValueType, Field, PushSource
from feast.infra.offline_stores.file_source import FileSource
from feast.types import Float32, Int32

# Define the semantic group entity
group_id = Entity(
    name="group_id",
    value_type=ValueType.STRING,
    description="Semantic group ID from clustering service",
)

# Create a FileSource as batch source for offline feature retrieval
batch_source = FileSource(
    path="data/feast/offline_store/semantic_groups.parquet",
    timestamp_field="timestamp",
)

# Define the feature source (Push Source for programmatic writes)
semantic_group_source = PushSource(
    name="semantic_group_features_push",
    batch_source=batch_source,
)

# Define the feature view with all 24 features
semantic_group_features = FeatureView(
    name="semantic_group_features",
    entities=[group_id],
    ttl=timedelta(days=30),
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
    source=semantic_group_source,
    description="24 computed features for semantic groups from feature engineering service",
)

