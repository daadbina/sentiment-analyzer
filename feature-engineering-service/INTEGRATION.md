# Feature Engineering Service - Integration Guide

## Service Overview

The Feature Engineering Service is Phase 3 of the sentiment-analyzer-v2 system. It consumes semantic groups from Kafka, extracts and computes 24 features across 6 categories, and writes features to both offline (Feast/Delta Lake) and online (Redis) feature stores.

## Data Contracts

### Input: Semantic Groups (Kafka Topic: `semantic_groups`)

```json
{
  "group_id": "group_001",
  "article_ids": ["art_001", "art_002", "art_003"],
  "centroid_vector": [0.1, 0.2, 0.3, ...],
  "similarity_avg": 0.85,
  "topic_label": "politics",
  "metadata": {
    "similarity_std": 0.05
  },
  "created_at": "2025-11-04T10:00:00Z",
  "articles": [
    {
      "article_id": "art_001",
      "title": "Breaking News",
      "body": "Article content...",
      "language": "en",
      "domain": "news.com",
      "source": "Reuters",
      "published_at": "2025-11-04T09:00:00Z",
      "sentiment_score": 0.5,
      "entities": [
        {"name": "John", "type": "PERSON"}
      ]
    }
  ],
  "actors": [
    {
      "actor_id": "actor_001",
      "name": "John",
      "type": "PERSON",
      "country": "USA",
      "sentiment_avg": 0.5,
      "occurrences": 10,
      "wikidata_id": "Q123"
    }
  ]
}
```

### Output: Computed Features (Kafka Topic: `features_computed`)

```json
{
  "group_id": "group_001",
  "features": {
    "num_sources": 2,
    "source_credibility_avg": 0.75,
    "source_credibility_std": 0.1,
    "source_diversity_score": 0.8,
    "time_span_hours": 2.5,
    "publication_velocity": 1.2,
    "temporal_concentration": 0.6,
    "days_since_first_article": 0.1,
    "sentiment_mean": 0.5,
    "sentiment_std": 0.15,
    "sentiment_polarity_ratio": 1.5,
    "sentiment_volatility": 0.2,
    "entity_count": 5,
    "entity_diversity": 3,
    "entity_prominence": 0.4,
    "entity_concentration": 0.7,
    "avg_word_count": 150.5,
    "avg_title_length": 5.2,
    "language_diversity": 1,
    "domain_diversity": 2,
    "centroid_magnitude": 0.55,
    "intra_cluster_similarity_mean": 0.85,
    "intra_cluster_similarity_std": 0.05,
    "embedding_drift_score": 0.02
  },
  "timestamp": 1730700000000
}
```

## Feature Categories

### 1. Source Features (4)
- `num_sources`: Count of unique news sources
- `source_credibility_avg`: Average publisher credibility
- `source_credibility_std`: Standard deviation of credibility
- `source_diversity_score`: Entropy of source distribution

### 2. Temporal Features (4)
- `time_span_hours`: Duration from earliest to latest article
- `publication_velocity`: Articles per hour
- `temporal_concentration`: Ratio of articles in peak hour
- `days_since_first_article`: Days elapsed since first publication

### 3. Sentiment Features (4)
- `sentiment_mean`: Average sentiment score
- `sentiment_std`: Standard deviation of sentiment
- `sentiment_polarity_ratio`: Positive vs negative articles ratio
- `sentiment_volatility`: Change in sentiment over time

### 4. Entity Features (4)
- `entity_count`: Total unique entities mentioned
- `entity_diversity`: Unique entity types
- `entity_prominence`: Frequency of top entity
- `entity_concentration`: Entropy of entity distribution

### 5. Content Features (4)
- `avg_word_count`: Average article length
- `avg_title_length`: Average title length
- `language_diversity`: Number of languages in group
- `domain_diversity`: Number of content domains

### 6. Embedding Features (4)
- `centroid_magnitude`: L2 norm of cluster centroid
- `intra_cluster_similarity_mean`: Average pairwise similarity
- `intra_cluster_similarity_std`: Std dev of pairwise similarities
- `embedding_drift_score`: Distance from baseline embedding distribution

## Upstream Dependencies

### Crawler Service
- Provides raw articles to ingest-validator
- Must be running before feature-engineering

### Ingest Validator Service
- Validates and normalizes articles
- Must be running before feature-engineering

### Canonicalizer Normalizer Service
- Normalizes URLs and deduplicates articles
- Must be running before feature-engineering

### NER Entity Linking Service
- Extracts and links entities
- Must be running before feature-engineering

### Embedding Service
- Generates semantic embeddings
- Must be running before feature-engineering

### Clustering Service
- Groups similar articles into semantic groups
- **DIRECT DEPENDENCY**: Produces `semantic_groups` topic

## Downstream Dependencies

### Trainer Service
- Consumes `features_computed` topic
- Uses features for model training

### Predictor Service
- Consumes `features_computed` topic
- Uses features for online inference

### Neo4j Loader Service
- Consumes `features_computed` topic
- Loads features into knowledge graph

## Configuration

### Environment Variables

```bash
# Kafka
KAFKA_BOOTSTRAP_SERVERS=154.53.166.231:9092
KAFKA_CONSUMER_GROUP=feature-engineering-group
KAFKA_SCHEMA_REGISTRY_URL=http://154.53.166.231:8081

# PostgreSQL (for actor data)
POSTGRES_HOST=154.53.166.231
POSTGRES_PORT=5432
POSTGRES_DATABASE=sentiment_db
POSTGRES_USER=admin
POSTGRES_PASSWORD=wp2400!!!!

# Redis (online feature store)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Feast (offline feature store)
FEAST_REPO_PATH=/app/feast_repo

# Monitoring
METRICS_PORT=9106
LOG_LEVEL=INFO
```

## Deployment

### Docker

```bash
docker build -t feature-engineering-service:latest .
docker run -e KAFKA_BOOTSTRAP_SERVERS=154.53.166.231:9092 \
           -e POSTGRES_HOST=154.53.166.231 \
           -p 9106:9106 \
           feature-engineering-service:latest
```

### Kubernetes

```bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

### Helm

```bash
helm install feature-engineering ./helm/feature-engineering-service
```

## Monitoring

### Prometheus Metrics

- `feature_groups_consumed_total`: Total semantic groups consumed
- `feature_computed_total`: Total features computed
- `feature_validation_failures_total`: Validation failures
- `feature_feast_writes_total`: Feast writes
- `feature_redis_writes_total`: Redis writes
- `feature_reconciliation_mismatches_total`: Offline-online mismatches
- `feature_computation_duration_seconds`: Computation latency
- `feature_extraction_duration_seconds`: Extraction latency
- `feature_drift_score`: Distribution drift score
- `feature_consumer_lag`: Kafka consumer lag
- `feature_batch_size`: Batch size
- `feature_processing_queue_size`: Queue size

### Health Check

```bash
curl http://localhost:9106/metrics
```

## Testing

### Unit Tests

```bash
pytest tests/ -v --cov=src --cov-report=html
```

### Integration Tests

```bash
docker-compose up -d
pytest tests/integration/ -v
docker-compose down
```

## Troubleshooting

### Service won't start
- Check Kafka connectivity: `kafka-console-consumer --bootstrap-server 154.53.166.231:9092 --list-topics`
- Check PostgreSQL connectivity: `psql -h 154.53.166.231 -U admin -d sentiment_db`
- Check Redis connectivity: `redis-cli -h localhost ping`

### Features not being computed
- Check Kafka consumer lag: `kafka-consumer-groups --bootstrap-server 154.53.166.231:9092 --group feature-engineering-group --describe`
- Check logs: `docker logs feature-engineering-service`
- Verify upstream services are running

### Offline-online mismatch
- Run reconciliation: Check metrics for `feature_reconciliation_mismatches_total`
- Verify Redis TTL settings
- Check Feast write operations

## Performance Targets

- **Latency**: ≤5 seconds per semantic group
- **Throughput**: ≥100 groups/minute
- **Availability**: ≥99.5%
- **Offline-Online Consistency**: ≥99%

