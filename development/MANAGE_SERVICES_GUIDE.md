# Manage Services Script - Complete Guide

## Overview
The `manage_services.ps1` script is the **ONLY** way to start, stop, restart, and manage all microservices in the Sentiment Analyzer v2 project.

**Location**: `development/manage_services.ps1`

---

## Available Actions

### 1. START ALL SERVICES
```powershell
.\manage_services.ps1 -Action start
```
- Starts all 9 microservices in order
- Flushes Redis, Qdrant, Kafka, and PostgreSQL before starting
- Creates log files in `development/logs/`
- Checks service health after startup

**Services started (in order)**:
1. crawler-service (port 8000)
2. ingest-validator-service (port 8001)
3. canonicalizer-normalizer-service (port 8002)
4. ner-entity-linking-service (port 8003)
5. embedding-service (port 8004, venv311)
6. clustering-semantic-grouping-service (port 8005, venv311)
7. feature-engineering-service (port 8006, venv311)
8. labeler-ground-truth-ingest-service (port 8007, venv311)
9. trainer-model-registry-service (port 8008, venv311)

---

### 2. STOP ALL SERVICES
```powershell
.\manage_services.ps1 -Action stop
```
- Gracefully stops all running services
- Cleans up PID files
- Removes old log files

---

### 3. CHECK SERVICE STATUS
```powershell
.\manage_services.ps1 -Action status
```
- Shows which services are currently running
- Displays PID and port for each service
- Shows log file location

---

### 4. RESTART SERVICES
```powershell
# Restart all services
.\manage_services.ps1 -Action restart

# Restart specific service
.\manage_services.ps1 -Action restart -Service "embedding-service"
```
- Stops and starts services
- Flushes external services on full restart

---

### 5. INITIATE CRAWL
```powershell
# Crawl Reuters feed
.\manage_services.ps1 -Action crawl -Service "reuters"

# Crawl other feeds
.\manage_services.ps1 -Action crawl -Service "bbc"
.\manage_services.ps1 -Action crawl -Service "aljazeera"
.\manage_services.ps1 -Action crawl -Service "guardian"
```
- Sends HTTP POST request to crawler service
- Crawls specified news feed
- Returns job status and article count

---

### 6. INITIATE CLUSTERING
```powershell
.\manage_services.ps1 -Action clustering
```
- Triggers clustering job on clustering service
- Processes embeddings from last 24 hours
- Returns cluster statistics (total, valid, invalid)
- **IMPORTANT**: Run this after crawl to process semantic groups

---

### 7. FLUSH KAFKA TOPICS
```powershell
.\manage_services.ps1 -Action flush-kafka
```
- Deletes all messages from all Kafka topics
- Topics flushed:
  - news_raw
  - news_validated
  - news_canonical
  - entities_extracted
  - embeddings
  - semantic_groups
  - features_computed
  - labeled_groups
  - models_trained

---

### 8. FLUSH REDIS
```powershell
.\manage_services.ps1 -Action flush-redis
```
- Clears all Redis cache
- Validates Redis is empty (0 keys)
- Used for clearing cached entity links and Feast online store

---

### 9. FLUSH QDRANT
```powershell
.\manage_services.ps1 -Action flush-qdrant
```
- Deletes all vector collections
- Clears news_embeddings_v1 collection
- Resets vector database

---

### 10. FLUSH DATABASE
```powershell
.\manage_services.ps1 -Action flush-database
```
- Truncates all PostgreSQL tables
- Clears articles, entities, embeddings, clusters, features, labels, models, predictions

---

### 11. FLUSH ALL EXTERNAL SERVICES
```powershell
.\manage_services.ps1 -Action flush-all
```
- Flushes Redis, Qdrant, Kafka, and PostgreSQL in sequence
- Shows summary of flush results
- **Used before starting fresh pipeline**

---

## Typical Workflow

### Fresh Start (Complete Pipeline)
```powershell
# 1. Stop all services
.\manage_services.ps1 -Action stop

# 2. Start all services (automatically flushes external services)
.\manage_services.ps1 -Action start

# 3. Wait for services to initialize (30 seconds)
Start-Sleep -Seconds 30

# 4. Crawl news articles
.\manage_services.ps1 -Action crawl -Service "reuters"

# 5. Wait for crawl to complete (60 seconds)
Start-Sleep -Seconds 60

# 6. Trigger clustering
.\manage_services.ps1 -Action clustering

# 7. Wait for clustering (120 seconds)
Start-Sleep -Seconds 120

# 8. Check logs for data flow
Get-Content development/logs/labeler-ground-truth-ingest-service_*.log | Select-Object -Last 50
```

### Debug Single Service
```powershell
# Restart specific service
.\manage_services.ps1 -Action restart -Service "embedding-service"

# Check logs
Get-Content development/logs/embedding-service_*.log | Select-Object -Last 100
```

### Clear All Data
```powershell
# Flush all external services
.\manage_services.ps1 -Action flush-all

# Restart services
.\manage_services.ps1 -Action restart
```

---

## Log Files
All service logs are stored in `development/logs/` with format:
```
{service-name}_{YYYYMMDD}_{HHMMSS}.log
```

Example:
```
embedding-service_20251106_122823.log
labeler-ground-truth-ingest-service_20251106_122827.log
```

---

## Important Notes

1. **Always use this script** - Never kill processes manually
2. **Services must start in order** - Upstream services must be ready before downstream
3. **Wait between operations** - Allow services time to initialize
4. **Check logs** - Always verify data flow through logs
5. **Flush before fresh start** - Use `flush-all` before testing new pipeline

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Service won't start | Check logs, verify port is free, restart service |
| No data flowing | Check Kafka topics, verify consumer groups, check logs |
| Clustering produces 0 clusters | Check embeddings in Qdrant, verify semantic_groups topic |
| Labeler not consuming | Check semantic_groups topic has data, restart labeler |


