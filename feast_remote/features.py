"""
Feast feature definitions for sentiment analyzer v2.
This file should be deployed to the remote Feast server at 154.53.166.231.

Defines all 24 features for semantic groups as specified in COMPREHENSIVE_REFACTORING_ANALYSIS.md.
"""

from datetime import timedelta
from feast import Entity, FeatureView, Field, FileSource, PushSource
from feast.types import Float32, Int64, String
from feast.data_source import RequestSource

# Entity definition
semantic_group = Entity(
    name="semantic_group",
    join_keys=["group_id"],
    description="Semantic group of related articles from clustering service"
)

# Data source - using S3/MinIO for offline store
semantic_group_source = FileSource(
    path="s3://sentiment-analyzer/feast/offline_store/semantic_groups.parquet",
    timestamp_field="event_timestamp",
    created_timestamp_column="created_at",
)

# Push source for real-time feature updates
semantic_group_push_source = PushSource(
    name="semantic_group_push",
    batch_source=semantic_group_source,
)

# Feature view with all 24 features
semantic_group_features = FeatureView(
    name="semantic_group_features",
    entities=[semantic_group],
    ttl=timedelta(days=7),
    schema=[
        # Source features (4)
        Field(name="num_sources", dtype=Int64, description="Number of unique sources in group"),
        Field(name="source_credibility_avg", dtype=Float32, description="Average source credibility score"),
        Field(name="source_credibility_std", dtype=Float32, description="Standard deviation of source credibility"),
        Field(name="source_diversity_score", dtype=Float32, description="Diversity of sources (entropy-based)"),
        
        # Temporal features (4)
        Field(name="time_span_hours", dtype=Float32, description="Time span between first and last article (hours)"),
        Field(name="publication_velocity", dtype=Float32, description="Articles per hour"),
        Field(name="temporal_concentration", dtype=Float32, description="Temporal clustering coefficient"),
        Field(name="days_since_first_article", dtype=Float32, description="Days since first article in group"),
        
        # Sentiment features (4)
        Field(name="sentiment_mean", dtype=Float32, description="Mean sentiment score across articles"),
        Field(name="sentiment_std", dtype=Float32, description="Standard deviation of sentiment scores"),
        Field(name="sentiment_polarity_ratio", dtype=Float32, description="Ratio of positive to negative articles"),
        Field(name="sentiment_volatility", dtype=Float32, description="Sentiment change rate over time"),
        
        # Entity features (4)
        Field(name="entity_count", dtype=Int64, description="Total number of entities in group"),
        Field(name="entity_diversity", dtype=Float32, description="Diversity of entity types"),
        Field(name="entity_prominence", dtype=Float32, description="Average entity prominence score"),
        Field(name="entity_concentration", dtype=Float32, description="Concentration of top entities"),
        
        # Content features (4)
        Field(name="avg_word_count", dtype=Float32, description="Average word count per article"),
        Field(name="avg_title_length", dtype=Float32, description="Average title length"),
        Field(name="language_diversity", dtype=Float32, description="Number of unique languages"),
        Field(name="domain_diversity", dtype=Float32, description="Number of unique domains"),
        
        # Embedding features (4)
        Field(name="centroid_magnitude", dtype=Float32, description="Magnitude of embedding centroid"),
        Field(name="intra_cluster_similarity_mean", dtype=Float32, description="Mean cosine similarity within cluster"),
        Field(name="intra_cluster_similarity_std", dtype=Float32, description="Std dev of intra-cluster similarity"),
        Field(name="embedding_drift_score", dtype=Float32, description="Embedding drift from previous groups"),
        
        # BTC price features (4)
        Field(name="btc_change_pct_10h", dtype=Float32, description="BTC price change % in next 10 hours"),
        Field(name="btc_volatility_score", dtype=Float32, description="BTC volatility score"),
        Field(name="btc_volume", dtype=Float32, description="BTC trading volume"),
        Field(name="btc_label_spike", dtype=Int64, description="Binary indicator of BTC price spike"),
    ],
    source=semantic_group_push_source,
    online=True,
    description="24 computed features for semantic groups (20 general + 4 BTC-specific)"
)

