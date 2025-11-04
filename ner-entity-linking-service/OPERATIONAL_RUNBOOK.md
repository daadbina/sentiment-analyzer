# NER Entity Linking Service - Operational Runbook

## Table of Contents

1. [Service Overview](#service-overview)
2. [Startup Procedures](#startup-procedures)
3. [Shutdown Procedures](#shutdown-procedures)
4. [Monitoring & Alerting](#monitoring--alerting)
5. [Common Issues & Troubleshooting](#common-issues--troubleshooting)
6. [Incident Response](#incident-response)
7. [Scaling Operations](#scaling-operations)
8. [Backup & Recovery](#backup--recovery)
9. [Performance Tuning](#performance-tuning)
10. [Maintenance Windows](#maintenance-windows)

## Service Overview

**Service Name:** NER Entity Linking Service  
**Purpose:** Extract named entities from news articles and link them to knowledge bases  
**Language:** Python 3.11  
**Container:** Docker  
**Orchestration:** Kubernetes  
**Dependencies:** Kafka, PostgreSQL, Redis, Wikidata API, DBpedia Spotlight

## Startup Procedures

### Local Development

```bash
# 1. Activate virtual environment
source venv311/bin/activate  # Linux/Mac
.\venv311\Scripts\Activate.ps1  # Windows

# 2. Start dependencies
docker-compose up -d

# 3. Run migrations
python -m alembic upgrade head

# 4. Start service
python -m src.main
```

### Docker Deployment

```bash
# 1. Build image
docker build -t ner-entity-linking:v1.0.0 .

# 2. Run container
docker run -d \
  --name ner-entity-linking \
  -e KAFKA_BROKERS=kafka:9092 \
  -e POSTGRES_HOST=postgres \
  -e REDIS_HOST=redis \
  -p 9104:9104 \
  ner-entity-linking:v1.0.0
```

### Kubernetes Deployment

```bash
# 1. Create namespace
kubectl create namespace ner-services

# 2. Create secrets
kubectl create secret generic ner-secrets \
  --from-literal=postgres-password=<password> \
  --from-literal=redis-password=<password> \
  -n ner-services

# 3. Deploy with Helm
helm install ner-entity-linking ./helm \
  -n ner-services \
  -f helm/values.yaml

# 4. Verify deployment
kubectl get pods -n ner-services
kubectl logs -f deployment/ner-entity-linking -n ner-services
```

## Shutdown Procedures

### Graceful Shutdown

```bash
# 1. Stop accepting new messages
kubectl patch deployment ner-entity-linking \
  -p '{"spec":{"replicas":0}}' \
  -n ner-services

# 2. Wait for in-flight messages to complete (max 5 minutes)
kubectl logs -f deployment/ner-entity-linking -n ner-services

# 3. Verify all messages processed
kubectl exec -it <pod-name> -n ner-services -- \
  python -c "from src.clients.kafka_consumer import consumer; print(consumer.position())"

# 4. Delete deployment
kubectl delete deployment ner-entity-linking -n ner-services
```

### Emergency Shutdown

```bash
# Force immediate shutdown (may lose in-flight messages)
kubectl delete pod <pod-name> -n ner-services --grace-period=0 --force
```

## Monitoring & Alerting

### Key Metrics to Monitor

| Metric | Threshold | Action |
|--------|-----------|--------|
| Consumer Lag | >1000 messages | Scale up replicas |
| Entity Linking Failure Rate | >10% | Check external APIs |
| Pod Memory | >80% of limit | Increase memory limit |
| Pod CPU | >80% of limit | Increase CPU limit |
| API Response Time | >10 seconds | Check database performance |
| Cache Hit Rate | <70% | Increase cache size |

### Prometheus Queries

```promql
# Consumer lag
ner_kafka_consumer_lag

# Entity extraction latency (p95)
histogram_quantile(0.95, ner_extraction_latency_seconds)

# Entity linking success rate
ner_linking_success_rate

# Pod memory usage
container_memory_usage_bytes{pod="ner-entity-linking"}

# Pod CPU usage
rate(container_cpu_usage_seconds_total{pod="ner-entity-linking"}[5m])
```

### Alert Rules

```yaml
- alert: HighConsumerLag
  expr: ner_kafka_consumer_lag > 1000
  for: 5m
  annotations:
    summary: "High Kafka consumer lag"

- alert: HighEntityLinkingFailureRate
  expr: (1 - ner_linking_success_rate) > 0.1
  for: 5m
  annotations:
    summary: "High entity linking failure rate"

- alert: PodMemoryHigh
  expr: container_memory_usage_bytes{pod="ner-entity-linking"} > 3.5e9
  for: 5m
  annotations:
    summary: "Pod memory usage high"
```

## Common Issues & Troubleshooting

### Issue: Service fails to start

**Symptoms:** Pod crashes immediately after startup

**Diagnosis:**
```bash
kubectl logs <pod-name> -n ner-services
```

**Common Causes:**
- Missing environment variables
- Database connection failure
- Kafka broker unreachable
- Redis connection failure

**Resolution:**
```bash
# Check environment variables
kubectl get configmap ner-config -n ner-services -o yaml

# Check database connectivity
kubectl exec -it <pod-name> -n ner-services -- \
  python -c "import psycopg2; psycopg2.connect('...')"

# Check Kafka connectivity
kubectl exec -it <pod-name> -n ner-services -- \
  python -c "from kafka import KafkaConsumer; KafkaConsumer('...')"
```

### Issue: High consumer lag

**Symptoms:** Kafka consumer lag increasing over time

**Diagnosis:**
```bash
# Check consumer lag
kubectl exec -it <pod-name> -n ner-services -- \
  python -c "from src.clients.kafka_consumer import consumer; print(consumer.position())"

# Check processing latency
kubectl logs <pod-name> -n ner-services | grep "latency"
```

**Resolution:**
```bash
# Scale up replicas
kubectl scale deployment ner-entity-linking --replicas=5 -n ner-services

# Check for slow operations
kubectl logs <pod-name> -n ner-services | grep "slow"

# Increase batch size
kubectl set env deployment/ner-entity-linking \
  BATCH_SIZE=64 -n ner-services
```

### Issue: Entity linking failures

**Symptoms:** High failure rate for entity linking

**Diagnosis:**
```bash
# Check external API status
curl -I https://query.wikidata.org/sparql

# Check circuit breaker state
kubectl logs <pod-name> -n ner-services | grep "circuit_breaker"
```

**Resolution:**
```bash
# Increase retry attempts
kubectl set env deployment/ner-entity-linking \
  MAX_RETRIES=5 -n ner-services

# Increase timeout
kubectl set env deployment/ner-entity-linking \
  API_TIMEOUT=30 -n ner-services

# Check external API health
curl https://query.wikidata.org/sparql?query=SELECT%20*%20WHERE%20{%3Fs%20%3Fp%20%3Fo%7D%20LIMIT%201
```

## Incident Response

### Severity Levels

| Level | Response Time | Impact |
|-------|---------------|--------|
| Critical | <15 minutes | Service unavailable |
| High | <1 hour | Degraded performance |
| Medium | <4 hours | Minor issues |
| Low | <24 hours | Cosmetic issues |

### Incident Response Steps

1. **Acknowledge** (within 15 minutes)
   - Confirm incident
   - Assign incident commander
   - Create incident ticket

2. **Investigate** (within 30 minutes)
   - Check logs and metrics
   - Identify root cause
   - Assess impact

3. **Mitigate** (within 1 hour)
   - Apply temporary fix
   - Scale resources if needed
   - Notify stakeholders

4. **Resolve** (within 4 hours)
   - Implement permanent fix
   - Deploy to production
   - Verify resolution

5. **Post-Mortem** (within 24 hours)
   - Document incident
   - Identify improvements
   - Update runbook

## Scaling Operations

### Horizontal Scaling

```bash
# Scale up
kubectl scale deployment ner-entity-linking --replicas=5 -n ner-services

# Scale down
kubectl scale deployment ner-entity-linking --replicas=3 -n ner-services

# Auto-scaling
kubectl autoscale deployment ner-entity-linking \
  --min=3 --max=10 \
  --cpu-percent=70 \
  -n ner-services
```

### Vertical Scaling

```bash
# Update resource limits
kubectl set resources deployment ner-entity-linking \
  --limits=cpu=2000m,memory=4Gi \
  --requests=cpu=500m,memory=2Gi \
  -n ner-services
```

## Backup & Recovery

### Database Backup

```bash
# Create backup
kubectl exec -it <postgres-pod> -n ner-services -- \
  pg_dump -U postgres ner_db > backup.sql

# Restore backup
kubectl exec -it <postgres-pod> -n ner-services -- \
  psql -U postgres ner_db < backup.sql
```

### Redis Backup

```bash
# Create backup
kubectl exec -it <redis-pod> -n ner-services -- \
  redis-cli BGSAVE

# Restore backup
kubectl cp <redis-pod>:/data/dump.rdb ./dump.rdb -n ner-services
```

## Performance Tuning

### Database Optimization

```sql
-- Create indexes
CREATE INDEX idx_actor_name ON actors(normalized_name);
CREATE INDEX idx_entity_type ON entities(entity_type);
CREATE INDEX idx_wikidata_id ON entities(wikidata_id);

-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM actors WHERE normalized_name = 'john smith';
```

### Cache Optimization

```bash
# Increase cache size
kubectl set env deployment/ner-entity-linking \
  CACHE_MAX_SIZE=10000 -n ner-services

# Adjust TTL
kubectl set env deployment/ner-entity-linking \
  CACHE_TTL=3600 -n ner-services
```

## Maintenance Windows

### Planned Maintenance

```bash
# 1. Announce maintenance window
# 2. Drain connections
kubectl drain <node> --ignore-daemonsets -n ner-services

# 3. Perform maintenance
# 4. Uncordon node
kubectl uncordon <node> -n ner-services

# 5. Verify service health
kubectl get pods -n ner-services
```

### Rolling Updates

```bash
# Update image
kubectl set image deployment/ner-entity-linking \
  ner-entity-linking=ner-entity-linking:v1.1.0 \
  -n ner-services

# Monitor rollout
kubectl rollout status deployment/ner-entity-linking -n ner-services

# Rollback if needed
kubectl rollout undo deployment/ner-entity-linking -n ner-services
```

## Contact & Escalation

- **On-Call Engineer:** [Contact Info]
- **Team Lead:** [Contact Info]
- **Incident Commander:** [Contact Info]
- **Slack Channel:** #ner-entity-linking-incidents
- **PagerDuty:** [Link]

