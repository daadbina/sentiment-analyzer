#!/usr/bin/env python3
"""Create a dummy parquet file for Feast schema inference with all 24 features"""
import pandas as pd
from datetime import datetime

# Create a dummy dataframe with all 24 features
data = {
    'semantic_group_id': ['dummy'],
    'created_at': [datetime.now()],
    # Source features (2)
    'source_count': [1],
    'source_diversity': [0.5],
    # Temporal features (3)
    'hour_of_day': [12],
    'day_of_week': [3],
    'is_weekend': [0],
    # Sentiment features (4)
    'sentiment_mean': [0.0],
    'sentiment_std': [0.1],
    'sentiment_polarity_ratio': [0.5],
    'sentiment_volatility': [0.2],
    # Entity features (5)
    'entity_count': [10],
    'entity_diversity': [0.7],
    'person_count': [3],
    'org_count': [2],
    'location_count': [1],
    # Content features (4)
    'title_length': [50],
    'body_length': [500],
    'total_length': [550],
    'avg_sentence_length': [25.0],
    # Embedding features (2)
    'embedding_magnitude': [1.0],
    'embedding_std': [0.1],
    # BTC features (4)
    'btc_price_change_1h': [0.5],
    'btc_price_change_4h': [1.2],
    'btc_price_change_24h': [3.5],
    'btc_volatility_24h': [2.1],
}

df = pd.DataFrame(data)
df.to_parquet('feast_remote/data/semantic_groups_full.parquet', index=False)
print("✓ Created dummy parquet file with all 24 features")
print(f"Total features: {len(df.columns) - 2}")  # Exclude semantic_group_id and created_at
print(f"Schema: {list(df.columns)}")

