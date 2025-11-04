# Embedding Service Integration Guide

## Overview

The Embedding Service is Phase 2 of the sentiment-analyzer-v2 system. It consumes normalized news articles from the `news_canonical` Kafka topic and produces multilingual embeddings stored in Qdrant vector database.

## Data Flow

```
news_canonical (Kafka)
    ↓
[Language Detection]
    ↓
[Model Selection]
    ↓
[Text Preprocessing]
    ↓
[Batch Assembly]
    ↓
[GPU Embedding Computation]
    ↓
[L2 Normalization]
    ↓
[Quality Validation]
    ↓
[Drift Detection]
    ↓
Qdrant (Vector DB) + embeddings (Kafka)
```

## Input Schema

**Topic**: `news_canonical`

**Avro Schema**:
```json
{
  "type": "record",
  "name": "NewsCanonical",
  "fields": [
    {"name": "article_id", "type": "string"},
    {"name": "normalized_body", "type": "string"},
    {"name": "language", "type": "string"},
    {"name": "domain", "type": "string"},
    {"name": "timestamp", "type": "long"}
  ]
}
```

## Output Schema

**Topic**: `embeddings`

**Avro Schema**:
```json
{
  "type": "record",
  "name": "EmbeddingMessage",
  "fields": [
    {"name": "article_id", "type": "string"},
    {"name": "embedding_id", "type": "string"},
    {"name": "model_name", "type": "string"},
    {"name": "language", "type": "string"},
    {"name": "embedding_dimension", "type": "int"},
    {"name": "timestamp", "type": "long"},
    {"name": "processing_time_ms", "type": "float"}
  ]
}
```

## Qdrant Collection

**Collection Name**: `embeddings`

**Vector Size**: 768 (multilingual-mpnet-base-v2)

**Distance Metric**: Cosine

**Payload Fields**:
- `article_id`: Article identifier
- `embedding_index`: Index in batch
- `model_name`: Model used for embedding
- `language`: Language code
- `timestamp`: Processing timestamp

## Configuration

### Environment Variables

```bash
# Kafka
KAFKA_BROKERS=localhost:9092
KAFKA_SCHEMA_REGISTRY_URL=http://localhost:8081
KAFKA_INPUT_TOPIC=news_canonical
KAFKA_OUTPUT_TOPIC=embeddings
KAFKA_CONSUMER_GROUP=embedding-service

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=embeddings
QDRANT_VECTOR_SIZE=768

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=embedding
POSTGRES_PASSWORD=password
POSTGRES_DB=embedding

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Model
MODEL_DEVICE=cuda  # or cpu
MODEL_BATCH_SIZE_GPU=32
MODEL_BATCH_SIZE_CPU=16
MODEL_MAX_SEQUENCE_LENGTH=512

# Validation
VALIDATION_ENABLED=true
DRIFT_DETECTION_ENABLED=true
```

## Supported Languages

The service supports 14+ languages with language-specific models:

- English: `all-mpnet-base-v2`
- Spanish: `paraphrase-multilingual-mpnet-base-v2`
- French: `paraphrase-multilingual-mpnet-base-v2`
- German: `paraphrase-multilingual-mpnet-base-v2`
- Portuguese: `paraphrase-multilingual-mpnet-base-v2`
- Italian: `paraphrase-multilingual-mpnet-base-v2`
- Dutch: `paraphrase-multilingual-mpnet-base-v2`
- Russian: `paraphrase-multilingual-mpnet-base-v2`
- Chinese: `paraphrase-multilingual-mpnet-base-v2`
- Japanese: `paraphrase-multilingual-mpnet-base-v2`
- Korean: `paraphrase-multilingual-mpnet-base-v2`
- Arabic: `paraphrase-multilingual-mpnet-base-v2`
- Hindi: `paraphrase-multilingual-mpnet-base-v2`
- Thai: `paraphrase-multilingual-mpnet-base-v2`

## API Endpoints

### Health Check
```
GET /health
```

### Readiness Check
```
GET /ready
```

### Metrics
```
GET /metrics
```

### Service Info
```
GET /info
```

## Deployment

### Docker Compose
```bash
docker-compose up -d
```

### Kubernetes
```bash
kubectl apply -f k8s/
# or
helm install embedding-service helm/
```

## Monitoring

### Prometheus Metrics

- `embedding_messages_consumed_total`: Total messages consumed
- `embedding_computed_total`: Total embeddings computed
- `embedding_qdrant_writes_total`: Total Qdrant writes
- `embedding_validation_failures_total`: Total validation failures
- `embedding_computation_duration_seconds`: Computation time histogram
- `embedding_batch_size`: Batch size histogram
- `embedding_gpu_memory_used_bytes`: GPU memory usage
- `embedding_gpu_utilization_percent`: GPU utilization
- `embedding_consumer_lag`: Kafka consumer lag
- `embedding_drift_score`: Drift detection score

### Logs

Logs are written to stdout with structured format:
```
2025-11-04 10:30:45 - embedding-service - INFO - Processing batch of 32 messages
```

## Error Handling

The service implements circuit breaker pattern for fault tolerance:

- **Failure Threshold**: 5 consecutive failures
- **Timeout**: 30 seconds
- **Retry**: Exponential backoff with max 3 retries

## Performance Characteristics

- **Throughput**: 1000+ embeddings/second (GPU)
- **Latency**: 50-100ms per batch (GPU)
- **Memory**: 2-4GB (GPU), 1-2GB (CPU)
- **Batch Size**: 32 (GPU), 16 (CPU)

## Troubleshooting

### Service won't start
- Check Kafka connectivity
- Check Qdrant connectivity
- Check PostgreSQL connectivity
- Review logs for specific errors

### High latency
- Check GPU utilization
- Check batch size configuration
- Check model loading time

### Memory issues
- Reduce batch size
- Reduce model pool size
- Enable model unloading

## Next Steps

The embeddings are consumed by:
1. **Clustering Service**: Groups similar articles
2. **Feature Engineering Service**: Computes features for ML models
3. **Neo4j Loader**: Builds knowledge graph

