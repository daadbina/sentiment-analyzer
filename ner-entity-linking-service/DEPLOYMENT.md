# NER Entity Linking Service Deployment Guide

## Prerequisites

- Kubernetes 1.20+
- Helm 3.0+
- Docker
- PostgreSQL 12+
- Redis 6.0+
- Kafka 2.8+

## Local Development

### Setup

```bash
# Create virtual environment
python -m venv venv311
source venv311/bin/activate  # On Windows: venv311\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export KAFKA_BROKERS=localhost:9092
export POSTGRES_HOST=localhost
export POSTGRES_USER=adminsentiment
export POSTGRES_PASSWORD=wp2400!!!!
export REDIS_HOST=localhost
```

### Running the Service

```bash
# Start the service
python -m src.main

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## Docker Deployment

### Build Image

```bash
docker build -t sentiment-analyzer/ner-entity-linking-service:1.0.0 .
docker tag sentiment-analyzer/ner-entity-linking-service:1.0.0 \
           sentiment-analyzer/ner-entity-linking-service:latest
```

### Run Container

```bash
docker run -d \
  --name ner-service \
  -e KAFKA_BROKERS=kafka:9092 \
  -e POSTGRES_HOST=postgres \
  -e POSTGRES_USER=adminsentiment \
  -e POSTGRES_PASSWORD=wp2400!!!! \
  -e REDIS_HOST=redis \
  -p 9104:9104 \
  sentiment-analyzer/ner-entity-linking-service:latest
```

## Kubernetes Deployment

### Using kubectl

```bash
# Create namespace
kubectl create namespace sentiment-analyzer

# Apply manifests
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/rbac.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/hpa.yaml

# Verify deployment
kubectl get pods -n sentiment-analyzer
kubectl logs -n sentiment-analyzer -l app=ner-entity-linking-service
```

### Using Helm

```bash
# Install chart
helm install ner-service ./helm \
  --namespace sentiment-analyzer \
  --create-namespace \
  --values helm/values.yaml

# Upgrade chart
helm upgrade ner-service ./helm \
  --namespace sentiment-analyzer \
  --values helm/values.yaml

# Uninstall chart
helm uninstall ner-service --namespace sentiment-analyzer
```

## Configuration

### ConfigMap

Edit `k8s/configmap.yaml` to configure:
- Kafka brokers and topics
- PostgreSQL connection
- Redis connection
- NER model parameters
- Entity linking thresholds

### Secrets

Edit `k8s/secret.yaml` to set:
- PostgreSQL credentials
- API keys for external services
- TLS certificates

## Monitoring

### Prometheus

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'ner-service'
    kubernetes_sd_configs:
      - role: pod
        namespaces:
          names:
            - sentiment-analyzer
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        action: keep
        regex: ner-entity-linking-service
```

### Grafana Dashboards

Import dashboard from `monitoring/grafana/ner-service-dashboard.json`

### Alerts

```yaml
# prometheus-rules.yaml
groups:
  - name: ner-service
    rules:
      - alert: NERServiceDown
        expr: up{job="ner-service"} == 0
        for: 5m
        
      - alert: HighEntityLinkingFailureRate
        expr: rate(ner_entity_linking_failures_total[5m]) > 0.1
        for: 10m
```

## Scaling

### Horizontal Scaling

The service automatically scales based on CPU and memory utilization:

```bash
# Check HPA status
kubectl get hpa -n sentiment-analyzer

# Manual scaling
kubectl scale deployment ner-entity-linking-service \
  --replicas=5 \
  -n sentiment-analyzer
```

### Vertical Scaling

Adjust resource requests/limits in `helm/values.yaml`:

```yaml
resources:
  requests:
    cpu: 1000m
    memory: 4Gi
  limits:
    cpu: 4000m
    memory: 8Gi
```

## Troubleshooting

### Check Service Status

```bash
# Check pod status
kubectl describe pod <pod-name> -n sentiment-analyzer

# Check logs
kubectl logs <pod-name> -n sentiment-analyzer

# Check events
kubectl get events -n sentiment-analyzer
```

### Common Issues

**Issue:** Pod stuck in CrashLoopBackOff
- Check logs: `kubectl logs <pod-name> -n sentiment-analyzer`
- Verify environment variables are set correctly
- Check database connectivity

**Issue:** High consumer lag
- Increase replicas: `kubectl scale deployment ... --replicas=5`
- Check Kafka broker health
- Monitor CPU/memory usage

**Issue:** Entity linking failures
- Check external API connectivity
- Verify API keys in secrets
- Check network policies

## Rollback

```bash
# Helm rollback
helm rollback ner-service 1 --namespace sentiment-analyzer

# kubectl rollback
kubectl rollout undo deployment/ner-entity-linking-service \
  -n sentiment-analyzer
```

## Maintenance

### Database Maintenance

```bash
# Analyze tables for query optimization
ANALYZE actors;
ANALYZE ner_audit_log;

# Vacuum to reclaim space
VACUUM ANALYZE actors;
```

### Cache Cleanup

```bash
# Clear Redis cache
redis-cli FLUSHDB

# Or specific keys
redis-cli DEL ner:entity:*
```

## Performance Tuning

### Connection Pooling

Adjust in `k8s/configmap.yaml`:
```yaml
postgres_pool_size: "20"
postgres_max_overflow: "10"
redis_pool_size: "10"
```

### Model Caching

```yaml
ner_model_cache_size: "5"
```

### Batch Processing

```yaml
ner_batch_size: "32"
```

