# Labeler Ground-Truth Ingest Service - Runbook

**Service:** `labeler-ground-truth-ingest-service`  
**Version:** 1.0.0  
**Last Updated:** 2025-11-05

---

## Table of Contents

1. [Service Overview](#service-overview)
2. [Common Issues & Solutions](#common-issues--solutions)
3. [Troubleshooting Guide](#troubleshooting-guide)
4. [Performance Tuning](#performance-tuning)
5. [Monitoring & Alerting](#monitoring--alerting)
6. [Escalation Procedures](#escalation-procedures)

---

## Service Overview

The labeler-ground-truth-ingest-service ingests ground-truth labels from external APIs (ACLED, GDELT, CoinGecko), reconciles them with semantic groups, validates label quality, and writes to Delta Lake, PostgreSQL, and Kafka.

**Key Dependencies:**
- Kafka (154.53.166.231:9092)
- PostgreSQL (154.53.166.231:5432)
- Schema Registry (http://154.53.166.231:8081)
- ACLED API (https://acleddata.com)
- GDELT API (https://api.gdeltproject.org)
- CoinGecko API (https://api.coingecko.com)

---

## Common Issues & Solutions

### Issue 1: Service Fails to Start - "Connection refused" to Kafka

**Symptoms:**
- Service exits with error: `Connection refused: 154.53.166.231:9092`
- Logs show: `KafkaError: Failed to connect to Kafka`

**Root Cause:**
- Kafka broker is down or unreachable
- Network connectivity issue
- Incorrect broker address in configuration

**Solution:**
```bash
# 1. Verify Kafka is running
docker ps | grep kafka

# 2. Check Kafka broker connectivity
telnet 154.53.166.231 9092

# 3. Verify configuration
echo $KAFKA_BROKERS

# 4. Restart service
kubectl rollout restart deployment/labeler-ground-truth-ingest-service -n sentiment-analyzer
```

---

### Issue 2: Schema Registry Connection Error

**Symptoms:**
- Error: `SchemaRegistryError: Failed to connect to Schema Registry`
- Logs show: `Connection refused: http://154.53.166.231:8081`

**Root Cause:**
- Schema Registry is down
- Incorrect registry URL
- Network connectivity issue

**Solution:**
```bash
# 1. Check Schema Registry health
curl http://154.53.166.231:8081/subjects

# 2. Verify configuration
echo $SCHEMA_REGISTRY_URL

# 3. Register schemas if missing
python scripts/register_schemas.py

# 4. Restart service
kubectl rollout restart deployment/labeler-ground-truth-ingest-service -n sentiment-analyzer
```

---

### Issue 3: PostgreSQL Connection Pool Exhausted

**Symptoms:**
- Error: `asyncpg.TooManyConnectionsError: too many connections`
- Logs show: `Connection pool exhausted`
- Labels not being written to database

**Root Cause:**
- Too many concurrent connections
- Connections not being released properly
- Database connection limit reached

**Solution:**
```bash
# 1. Check current connections
psql -h 154.53.166.231 -U adminsentiment -d sentiment \
  -c "SELECT count(*) FROM pg_stat_activity;"

# 2. Increase pool size in config
POSTGRES_POOL_SIZE=30  # Increase from default 20

# 3. Kill idle connections
psql -h 154.53.166.231 -U adminsentiment -d sentiment \
  -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state='idle';"

# 4. Restart service
kubectl rollout restart deployment/labeler-ground-truth-ingest-service -n sentiment-analyzer
```

---

### Issue 4: ACLED API Rate Limiting

**Symptoms:**
- Error: `FetchError: ACLED API returned 429 Too Many Requests`
- Labels not being fetched from ACLED
- Circuit breaker opens

**Root Cause:**
- Exceeded ACLED API rate limit
- Too many concurrent requests
- API key quota exceeded

**Solution:**
```bash
# 1. Check ACLED API status
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "https://api.acleddata.com/api/status"

# 2. Verify API key is valid
# Check ACLED_API_KEY in secrets

# 3. Increase fetch interval
ACLED_FETCH_INTERVAL_HOURS=48  # Increase from 24

# 4. Wait for circuit breaker to reset (60 seconds)
# Service will automatically retry

# 5. Check logs for rate limit details
kubectl logs -f deployment/labeler-ground-truth-ingest-service -n sentiment-analyzer
```

---

### Issue 5: Delta Lake Write Failures

**Symptoms:**
- Error: `StorageError: Failed to write labels to Delta Lake`
- Logs show: `Schema error: Invalid data type for Delta Lake: Null`
- Labels not persisted

**Root Cause:**
- Nullable types in schema
- None values not sanitized
- Incorrect data types

**Solution:**
```bash
# 1. Check Delta Lake path
ls -la /data/delta_lake/ground_truth

# 2. Verify data sanitization is working
# Check logs for sanitization messages

# 3. Restart service to retry writes
kubectl rollout restart deployment/labeler-ground-truth-ingest-service -n sentiment-analyzer

# 4. Check Delta Lake table schema
python -c "from deltalake import DeltaTable; dt = DeltaTable('/data/delta_lake/ground_truth'); print(dt.schema())"
```

---

### Issue 6: Label Reconciliation Accuracy Low

**Symptoms:**
- Logs show: `label_reconciliation_failures_total > 100`
- Reconciliation accuracy < 95%
- Many labels not matched to semantic groups

**Root Cause:**
- Temporal threshold too strict
- Semantic similarity threshold too high
- Semantic groups not available

**Solution:**
```bash
# 1. Check reconciliation metrics
curl http://localhost:9107/metrics | grep label_reconciliation

# 2. Adjust thresholds
LABEL_RECONCILIATION_THRESHOLD=72  # Increase from 48 hours
SEMANTIC_SIMILARITY_THRESHOLD=0.75  # Decrease from 0.85

# 3. Verify semantic groups are available
psql -h 154.53.166.231 -U adminsentiment -d sentiment \
  -c "SELECT count(*) FROM semantic_groups;"

# 4. Restart service with new thresholds
kubectl set env deployment/labeler-ground-truth-ingest-service \
  LABEL_RECONCILIATION_THRESHOLD=72 -n sentiment-analyzer
```

---

### Issue 7: High Memory Usage

**Symptoms:**
- Pod memory usage > 1GB
- OOMKilled errors in logs
- Service crashes

**Root Cause:**
- Large batch sizes
- Memory leak in reconciliation
- Unbounded label queue

**Solution:**
```bash
# 1. Check memory usage
kubectl top pod -n sentiment-analyzer | grep labeler

# 2. Reduce batch size
LABEL_BATCH_SIZE=100  # Decrease from 500

# 3. Increase memory limits
kubectl set resources deployment/labeler-ground-truth-ingest-service \
  --limits=memory=2Gi -n sentiment-analyzer

# 4. Restart service
kubectl rollout restart deployment/labeler-ground-truth-ingest-service -n sentiment-analyzer
```

---

## Troubleshooting Guide

### Step 1: Check Service Status

```bash
# Check pod status
kubectl get pods -n sentiment-analyzer | grep labeler

# Check pod logs
kubectl logs -f deployment/labeler-ground-truth-ingest-service -n sentiment-analyzer

# Check pod events
kubectl describe pod <pod-name> -n sentiment-analyzer
```

### Step 2: Check Health Endpoints

```bash
# Health check
curl http://localhost:9107/health

# Readiness check
curl http://localhost:9107/ready

# Liveness check
curl http://localhost:9107/live
```

### Step 3: Check Metrics

```bash
# Get Prometheus metrics
curl http://localhost:9107/metrics | grep label_

# Check specific metrics
curl http://localhost:9107/metrics | grep label_freshness_hours
curl http://localhost:9107/metrics | grep label_confidence_avg
```

### Step 4: Check Database

```bash
# Check ground_truth table
psql -h 154.53.166.231 -U adminsentiment -d sentiment \
  -c "SELECT count(*) FROM ground_truth;"

# Check reconciliation log
psql -h 154.53.166.231 -U adminsentiment -d sentiment \
  -c "SELECT count(*) FROM reconciliation_log;"

# Check license audit
psql -h 154.53.166.231 -U adminsentiment -d sentiment \
  -c "SELECT * FROM license_audit ORDER BY last_check DESC LIMIT 10;"
```

---

## Performance Tuning

### Optimize Label Fetching

```bash
# Increase fetch parallelism
ACLED_FETCH_WORKERS=5
GDELT_FETCH_WORKERS=5
COINGECKO_FETCH_WORKERS=5

# Increase fetch timeout
API_TIMEOUT_SECONDS=30

# Increase retry attempts
API_RETRY_ATTEMPTS=5
```

### Optimize Reconciliation

```bash
# Increase reconciliation batch size
RECONCILIATION_BATCH_SIZE=1000

# Increase reconciliation workers
RECONCILIATION_WORKERS=10

# Adjust temporal threshold
LABEL_RECONCILIATION_THRESHOLD=72
```

### Optimize Storage

```bash
# Increase PostgreSQL pool size
POSTGRES_POOL_SIZE=30

# Increase Delta Lake write batch size
DELTA_LAKE_BATCH_SIZE=5000

# Enable Delta Lake compression
DELTA_LAKE_COMPRESSION=snappy
```

---

## Monitoring & Alerting

### Key Metrics to Monitor

1. **label_fetched_total** - Total labels fetched by source
2. **label_reconciled_total** - Successfully reconciled labels
3. **label_validation_failures_total** - Failed validations
4. **label_freshness_hours** - Age of latest label by source
5. **label_confidence_avg** - Average label confidence score

### Alert Thresholds

```yaml
- alert: LabelFreshnessACLED
  expr: label_freshness_hours{source="acled"} > 24
  for: 1h
  severity: warning

- alert: LabelFreshnessGDELT
  expr: label_freshness_hours{source="gdelt"} > 1
  for: 30m
  severity: warning

- alert: LabelReconciliationFailures
  expr: label_reconciliation_failures_total > 100
  for: 10m
  severity: critical

- alert: LabelValidationFailures
  expr: label_validation_failures_total / label_fetched_total > 0.10
  for: 10m
  severity: warning
```

---

## Escalation Procedures

### Level 1: Automatic Recovery

- Service automatically retries failed operations
- Circuit breaker resets after 60 seconds
- Graceful degradation to backup feeds

### Level 2: Manual Intervention

- Check logs and metrics
- Verify external API connectivity
- Adjust configuration parameters
- Restart service

### Level 3: Escalation

- Contact Kafka team if broker issues
- Contact Database team if PostgreSQL issues
- Contact API team if external API issues
- Contact Platform team if infrastructure issues

---

**For additional support, contact the Sentiment Analyzer Team.**

