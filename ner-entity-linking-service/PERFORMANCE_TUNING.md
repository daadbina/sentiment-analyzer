# NER Entity Linking Service Performance Tuning Guide

## Performance Targets

- **Throughput:** ≥200 articles/minute per replica
- **Latency:** ≤5 seconds average extraction time
- **P95 Latency:** ≤8 seconds
- **P99 Latency:** ≤12 seconds
- **Entity Linking Success Rate:** ≥90%
- **Cache Hit Rate:** ≥80%

## Tuning Parameters

### 1. Batch Processing

**Parameter:** `ner_batch_size`

```yaml
# Default: 32
# Increase for higher throughput (more memory usage)
# Decrease for lower latency
ner_batch_size: "64"
```

**Impact:**
- Larger batches = higher throughput, higher latency
- Smaller batches = lower throughput, lower latency

**Recommendation:**
- For throughput optimization: 64-128
- For latency optimization: 16-32

### 2. Model Caching

**Parameter:** `ner_model_cache_size`

```yaml
# Default: 5
# Number of NER models to keep in memory
ner_model_cache_size: "5"
```

**Impact:**
- Larger cache = faster model loading, more memory
- Smaller cache = slower model loading, less memory

**Recommendation:**
- For 14 languages: cache size 5-7
- For single language: cache size 1-2

### 3. Connection Pooling

**PostgreSQL:**
```yaml
postgres_pool_size: "20"
postgres_max_overflow: "10"
postgres_pool_recycle: "3600"
```

**Redis:**
```yaml
redis_pool_size: "10"
redis_max_connections: "50"
```

**Kafka:**
```yaml
kafka_max_poll_records: "100"
kafka_poll_timeout_ms: "1000"
```

**Recommendation:**
- Pool size = number of workers * 2 + 5
- Max overflow = pool size / 2

### 4. Entity Linking Thresholds

**Parameter:** `entity_linking_confidence_threshold`

```yaml
# Default: 0.7
# Lower threshold = more entities linked, more false positives
# Higher threshold = fewer entities linked, fewer false positives
entity_linking_confidence_threshold: "0.75"
```

**Impact:**
- Lower threshold = higher recall, lower precision
- Higher threshold = lower recall, higher precision

**Recommendation:**
- For high precision: 0.8-0.9
- For high recall: 0.5-0.7
- Balanced: 0.7-0.75

### 5. Cache TTL

**Parameter:** `entity_linking_cache_ttl`

```yaml
# Default: 3600 (1 hour)
# Time to live for cached entity linking results
entity_linking_cache_ttl: "7200"
```

**Impact:**
- Longer TTL = higher cache hit rate, stale data
- Shorter TTL = lower cache hit rate, fresher data

**Recommendation:**
- For stable entities: 3600-7200 seconds
- For dynamic entities: 600-1800 seconds

### 6. Resource Allocation

**CPU:**
```yaml
resources:
  requests:
    cpu: "500m"
  limits:
    cpu: "2000m"
```

**Memory:**
```yaml
resources:
  requests:
    memory: "2Gi"
  limits:
    memory: "4Gi"
```

**Recommendation:**
- CPU: 500m-1000m per replica
- Memory: 2Gi-4Gi per replica
- Adjust based on language count and batch size

### 7. Replica Count

**Parameter:** `replicaCount` or HPA `minReplicas`

```yaml
replicaCount: 3
autoscaling:
  minReplicas: 3
  maxReplicas: 10
```

**Recommendation:**
- Minimum 3 replicas for high availability
- Maximum 10 replicas for cost efficiency
- Scale based on consumer lag

## Performance Optimization Strategies

### 1. Optimize Entity Normalization

```python
# Use cached normalization
from src.optimization.model_cache import ModelCache

cache = ModelCache(max_size=5)
normalized = cache.get("normalized_entities")
```

### 2. Batch Processing

```python
from src.optimization.model_cache import BatchProcessor

processor = BatchProcessor(batch_size=64)
batches = processor.create_batches(entities)

for batch in batches:
    process_batch(batch)
```

### 3. Database Query Optimization

```sql
-- Add indexes
CREATE INDEX idx_actors_normalized_name ON actors(normalized_name);
CREATE INDEX idx_actors_wikidata_id ON actors(wikidata_id);

-- Analyze tables
ANALYZE actors;

-- Use EXPLAIN to optimize queries
EXPLAIN ANALYZE SELECT * FROM actors WHERE normalized_name = 'John Smith';
```

### 4. Redis Caching

```python
# Cache entity linking results
redis_client.setex(
    f"entity:{entity_text}:{language}",
    3600,  # TTL
    json.dumps(linking_result)
)
```

### 5. Connection Pooling

```python
# Use connection pooling
from sqlalchemy import create_engine

engine = create_engine(
    "postgresql://...",
    pool_size=20,
    max_overflow=10,
    pool_recycle=3600
)
```

## Monitoring Performance

### Key Metrics

```bash
# Entity extraction latency
curl http://localhost:9104/metrics | grep ner_extraction_latency

# Entity linking success rate
curl http://localhost:9104/metrics | grep ner_entity_linking

# Cache hit rate
curl http://localhost:9104/metrics | grep ner_model_cache

# Kafka consumer lag
curl http://localhost:9104/metrics | grep ner_kafka_consumer_lag
```

### Prometheus Queries

```promql
# Average extraction latency
rate(ner_extraction_latency_seconds_sum[5m]) / rate(ner_extraction_latency_seconds_count[5m])

# P95 extraction latency
histogram_quantile(0.95, ner_extraction_latency_seconds_bucket)

# Entity linking success rate
rate(ner_entity_linking_success_total[5m]) / (rate(ner_entity_linking_success_total[5m]) + rate(ner_entity_linking_failures_total[5m]))

# Cache hit rate
rate(ner_model_cache_hits_total[5m]) / (rate(ner_model_cache_hits_total[5m]) + rate(ner_model_cache_misses_total[5m]))
```

## Benchmarking

### Run Performance Tests

```bash
# Run performance benchmarks
pytest tests/test_performance.py -v

# Run with profiling
python -m cProfile -o profile.prof -m pytest tests/test_performance.py

# Analyze profile
python -m pstats profile.prof
```

### Load Testing

```bash
# Using Apache Bench
ab -n 1000 -c 10 http://localhost:9104/health

# Using wrk
wrk -t4 -c100 -d30s http://localhost:9104/health
```

## Scaling Strategies

### Horizontal Scaling

```bash
# Increase replicas
kubectl scale deployment ner-entity-linking-service \
  --replicas=5 -n sentiment-analyzer

# Monitor scaling
kubectl get hpa -n sentiment-analyzer
```

### Vertical Scaling

```yaml
# Increase resource limits
resources:
  limits:
    cpu: "4000m"
    memory: "8Gi"
```

## Cost Optimization

### Reduce Resource Usage

1. **Optimize batch size:** Smaller batches = less memory
2. **Reduce model cache:** Cache only frequently used models
3. **Increase cache TTL:** Reduce API calls
4. **Use spot instances:** For non-critical replicas

### Monitoring Costs

```bash
# Estimate monthly cost
# CPU: $0.05 per CPU-hour
# Memory: $0.01 per GB-hour

# Example: 3 replicas, 500m CPU, 2Gi memory
# Monthly cost = 3 * (500m * 730h * $0.05 + 2Gi * 730h * $0.01)
#              = 3 * ($18.25 + $14.60)
#              = $98.55
```

