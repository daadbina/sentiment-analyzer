# NER Entity Linking Service Troubleshooting Guide

## Common Issues and Solutions

### 1. Service Fails to Start

**Symptoms:**
- Pod in CrashLoopBackOff state
- Service exits immediately after starting

**Diagnosis:**
```bash
kubectl logs <pod-name> -n sentiment-analyzer
```

**Common Causes and Solutions:**

| Cause | Solution |
|-------|----------|
| Missing environment variables | Check ConfigMap and Secret are created |
| Kafka broker unreachable | Verify Kafka broker address and network connectivity |
| PostgreSQL connection failed | Check PostgreSQL host, port, credentials |
| Redis connection failed | Verify Redis host and port |
| Model download failed | Check internet connectivity and disk space |

### 2. High Consumer Lag

**Symptoms:**
- Kafka consumer lag increasing
- Articles not being processed in real-time

**Diagnosis:**
```bash
# Check consumer lag
kafka-consumer-groups --bootstrap-server kafka:9092 \
  --group ner-service-group \
  --describe

# Check pod metrics
kubectl top pod <pod-name> -n sentiment-analyzer
```

**Solutions:**
1. **Increase replicas:**
   ```bash
   kubectl scale deployment ner-entity-linking-service \
     --replicas=5 -n sentiment-analyzer
   ```

2. **Increase batch size:**
   ```yaml
   # In ConfigMap
   ner_batch_size: "64"
   ```

3. **Optimize resource allocation:**
   ```yaml
   resources:
     requests:
       cpu: 1000m
       memory: 4Gi
   ```

### 3. Entity Linking Failures

**Symptoms:**
- High rate of entity linking failures
- Wikidata/DBpedia API errors in logs

**Diagnosis:**
```bash
# Check metrics
curl http://localhost:9104/metrics | grep entity_linking_failures

# Check logs for API errors
kubectl logs <pod-name> -n sentiment-analyzer | grep -i "linking\|wikidata\|dbpedia"
```

**Solutions:**
1. **Check external API connectivity:**
   ```bash
   curl https://www.wikidata.org/w/api.php
   curl https://api.dbpedia-spotlight.org/en/annotate
   ```

2. **Increase timeout:**
   ```yaml
   entity_linking_timeout: "20"
   ```

3. **Lower confidence threshold:**
   ```yaml
   entity_linking_confidence_threshold: "0.5"
   ```

### 4. Memory Leaks

**Symptoms:**
- Memory usage continuously increasing
- Pod eventually killed due to OOMKilled

**Diagnosis:**
```bash
# Monitor memory usage
kubectl top pod <pod-name> -n sentiment-analyzer --containers

# Check for memory leaks in logs
kubectl logs <pod-name> -n sentiment-analyzer | grep -i "memory\|gc"
```

**Solutions:**
1. **Reduce model cache size:**
   ```yaml
   ner_model_cache_size: "3"
   ```

2. **Increase memory limits:**
   ```yaml
   resources:
     limits:
       memory: "8Gi"
   ```

3. **Restart pod:**
   ```bash
   kubectl delete pod <pod-name> -n sentiment-analyzer
   ```

### 5. Database Connection Pool Exhaustion

**Symptoms:**
- "Connection pool exhausted" errors in logs
- Slow query responses

**Diagnosis:**
```bash
# Check active connections
psql -h postgres -U adminsentiment -d sentiment -c \
  "SELECT count(*) FROM pg_stat_activity;"

# Check pool metrics
curl http://localhost:9104/metrics | grep connection_pool
```

**Solutions:**
1. **Increase pool size:**
   ```yaml
   postgres_pool_size: "30"
   postgres_max_overflow: "15"
   ```

2. **Reduce connection timeout:**
   ```yaml
   postgres_pool_recycle: "1800"
   ```

3. **Optimize queries:**
   - Add indexes to frequently queried columns
   - Use EXPLAIN ANALYZE to identify slow queries

### 6. Redis Cache Issues

**Symptoms:**
- Cache hits very low
- Entity linking taking longer than expected

**Diagnosis:**
```bash
# Check cache metrics
curl http://localhost:9104/metrics | grep cache

# Check Redis connection
redis-cli ping

# Check Redis memory
redis-cli INFO memory
```

**Solutions:**
1. **Clear cache:**
   ```bash
   redis-cli FLUSHDB
   ```

2. **Increase Redis memory:**
   ```yaml
   redis_maxmemory: "2gb"
   redis_maxmemory_policy: "allkeys-lru"
   ```

3. **Increase cache TTL:**
   ```yaml
   entity_linking_cache_ttl: "7200"
   ```

### 7. NER Model Loading Failures

**Symptoms:**
- "Failed to load model" errors
- Service crashes on startup

**Diagnosis:**
```bash
# Check disk space
df -h

# Check model download logs
kubectl logs <pod-name> -n sentiment-analyzer | grep -i "model\|download"
```

**Solutions:**
1. **Increase disk space:**
   ```yaml
   volumeMounts:
     - name: models
       mountPath: /models
   volumes:
     - name: models
       emptyDir:
         sizeLimit: 20Gi
   ```

2. **Pre-download models:**
   - Build Docker image with models included
   - Use init container to download models

### 8. Kafka Message Deserialization Errors

**Symptoms:**
- "Failed to deserialize message" errors
- Articles not being processed

**Diagnosis:**
```bash
# Check message format
kafka-console-consumer --bootstrap-server kafka:9092 \
  --topic news_canonical \
  --from-beginning \
  --max-messages 1
```

**Solutions:**
1. **Verify Avro schema:**
   - Check schema registry for correct schema
   - Verify schema version matches

2. **Check message format:**
   - Ensure all required fields are present
   - Verify data types match schema

### 9. High CPU Usage

**Symptoms:**
- CPU utilization consistently >80%
- Pod throttled by resource limits

**Diagnosis:**
```bash
# Check CPU usage
kubectl top pod <pod-name> -n sentiment-analyzer

# Profile CPU usage
python -m cProfile -o profile.prof src/main.py
```

**Solutions:**
1. **Optimize hot paths:**
   - Profile code to identify bottlenecks
   - Optimize entity normalization and linking

2. **Increase CPU limits:**
   ```yaml
   resources:
     limits:
       cpu: "4000m"
   ```

3. **Reduce batch size:**
   ```yaml
   ner_batch_size: "16"
   ```

### 10. Network Connectivity Issues

**Symptoms:**
- Timeouts connecting to external APIs
- Kafka broker unreachable

**Diagnosis:**
```bash
# Test connectivity from pod
kubectl exec <pod-name> -n sentiment-analyzer -- \
  curl -v https://www.wikidata.org/w/api.php

# Check network policies
kubectl get networkpolicies -n sentiment-analyzer
```

**Solutions:**
1. **Check network policies:**
   - Ensure egress rules allow external API calls
   - Verify DNS resolution

2. **Increase timeouts:**
   ```yaml
   wikidata_api_timeout: "20"
   dbpedia_api_timeout: "20"
   ```

## Performance Optimization

### Query Optimization

```sql
-- Add indexes
CREATE INDEX idx_actors_normalized_name ON actors(normalized_name);
CREATE INDEX idx_actors_wikidata_id ON actors(wikidata_id);

-- Analyze tables
ANALYZE actors;
```

### Connection Pooling

```yaml
postgres_pool_size: "20"
postgres_max_overflow: "10"
redis_pool_size: "10"
```

### Caching Strategy

- Cache entity linking results in Redis
- Use LRU eviction for model cache
- Implement cache warming for common entities

## Monitoring and Alerting

### Key Metrics to Monitor

- Entity extraction latency (p50, p95, p99)
- Entity linking success rate
- Kafka consumer lag
- Database connection pool utilization
- Cache hit rate
- Error rates by type

### Alert Thresholds

- Consumer lag > 1000 messages
- Entity linking failure rate > 10%
- Pod memory > 80% of limit
- Pod CPU > 80% of limit
- API response time > 10 seconds

