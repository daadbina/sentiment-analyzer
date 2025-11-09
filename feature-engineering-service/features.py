"""
Feast feature definitions for semantic group features.

Defines the semantic_group_features feature view with all 28 computed features (24 base + 4 BTC).
"""

from datetime import timedelta
from feast import Entity, Feature, FeatureView, ValueType, Field
from feast.infra.offline_stores.file_source import FileSource
from feast.infra.offline_stores.delta_source import DeltaSource
from feast.types import Float32, Int32

# Define the semantic group entity
group_id = Entity(
    name="group_id",
    value_type=ValueType.STRING,
    description="Semantic group ID from clustering service",
)

# Define the feature source (Delta Lake)
semantic_group_source = DeltaSource(
    path="/data/delta/semantic_groups",
    timestamp_field="timestamp",
)

# Define the feature view with all 28 features (24 base + 4 BTC)
semantic_group_features = FeatureView(
    name="semantic_group_features",
    entities=[group_id],
    ttl=timedelta(days=30),
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
        Field(name="entity_diversity", dtype=Float32),
        Field(name="entity_prominence", dtype=Float32),
        Field(name="entity_concentration", dtype=Float32),
        # Content features (4)
        Field(name="avg_word_count", dtype=Float32),
        Field(name="avg_title_length", dtype=Float32),
        Field(name="language_diversity", dtype=Float32),
        Field(name="domain_diversity", dtype=Float32),
        # Embedding features (4)
        Field(name="centroid_magnitude", dtype=Float32),
        Field(name="intra_cluster_similarity_mean", dtype=Float32),
        Field(name="intra_cluster_similarity_std", dtype=Float32),
        Field(name="embedding_drift_score", dtype=Float32),
        # BTC price features (4)
        Field(name="btc_change_pct_10h", dtype=Float32),
        Field(name="btc_volatility_score", dtype=Float32),
        Field(name="btc_volume", dtype=Float32),
        Field(name="btc_label_spike", dtype=Int32),
    ],
    source=semantic_group_source,
    description="28 computed features for semantic groups (24 base + 4 BTC price features)",
)

