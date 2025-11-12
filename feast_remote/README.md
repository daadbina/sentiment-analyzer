# Feast Feature Store Deployment Instructions

## Overview
This directory contains the feature definitions for the remote Feast server deployed at `154.53.166.231:6566`.

## Remote Server Details
- **Feast HTTP API**: `http://154.53.166.231:6566`
- **Redis Online Store**: `154.53.166.231:6379`
- **MinIO S3 Storage**: `http://154.53.166.231:9900` (API), `http://154.53.166.231:9901` (Console)

## Deployment Steps

### Step 1: Copy Feature Definitions to Remote Server

```bash
# Copy features.py to remote server
scp feast_remote/features.py root@154.53.166.231:~/feast/feature_repo/

# Or create directly on server
ssh root@154.53.166.231
cd ~/feast/feature_repo
nano features.py
# Paste content from feast_remote/features.py
```

### Step 2: Apply Feature Definitions

```bash
# SSH to remote server
ssh root@154.53.166.231

# Apply features to Feast registry
docker exec feast-feature-server feast apply

# Expected output:
# Created entity semantic_group
# Created feature view semantic_group_features
# Registered 24 features
```

### Step 3: Verify Deployment

```bash
# List feature views
docker exec feast-feature-server feast feature-views list

# Check Feast server health
curl http://154.53.166.231:6566/health

# Test feature retrieval (after features are materialized)
curl -X POST http://154.53.166.231:6566/get-online-features \
  -H "Content-Type: application/json" \
  -d '{
    "features": ["semantic_group_features:sentiment_mean"],
    "entities": {"group_id": ["test-group-id"]}
  }'
```

### Step 4: Materialize Features

```bash
# Materialize features from offline to online store
docker exec feast-feature-server feast materialize-incremental $(date -u +%Y-%m-%dT%H:%M:%S)

# Verify features in Redis
docker exec feast-redis redis-cli KEYS "feast:*"
```

## Feature List

The feature view `semantic_group_features` contains 24 features organized into 6 categories:

1. **Source Features (4)**: num_sources, source_credibility_avg, source_credibility_std, source_diversity_score
2. **Temporal Features (4)**: time_span_hours, publication_velocity, temporal_concentration, days_since_first_article
3. **Sentiment Features (4)**: sentiment_mean, sentiment_std, sentiment_polarity_ratio, sentiment_volatility
4. **Entity Features (4)**: entity_count, entity_diversity, entity_prominence, entity_concentration
5. **Content Features (4)**: avg_word_count, avg_title_length, language_diversity, domain_diversity
6. **Embedding Features (4)**: centroid_magnitude, intra_cluster_similarity_mean, intra_cluster_similarity_std, embedding_drift_score
7. **BTC Features (4)**: btc_change_pct_10h, btc_volatility_score, btc_volume, btc_label_spike

## Service Configuration

After applying features, update all services to use the remote Feast server:

```yaml
# feature-engineering-service/.env
FEAST_SERVER_URL=http://154.53.166.231:6566

# trainer-model-registry-service/.env
FEAST_SERVER_URL=http://154.53.166.231:6566

# predictor-online-inference-service/.env
FEAST_SERVER_URL=http://154.53.166.231:6566
```

## Troubleshooting

### Features not appearing
```bash
# Check Feast logs
docker logs feast-feature-server

# Verify registry
docker exec feast-feature-server feast registry-dump
```

### Connection issues
```bash
# Test Redis connection
docker exec feast-redis redis-cli ping

# Test MinIO connection
curl http://154.53.166.231:9900/minio/health/live
```

## References
- COMPREHENSIVE_REFACTORING_ANALYSIS.md - Section 2.1: Feast Feature Store Implementation
- Architecture.md - Feature Store Architecture

