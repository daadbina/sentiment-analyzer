# Deployment Guide

This document provides comprehensive deployment instructions for the Predictor Online Inference Service.

## Prerequisites

### Infrastructure Requirements

- **Kubernetes Cluster**: v1.24+ with HPA support
- **Docker Registry**: For storing container images
- **External Services**:
  - Kafka cluster (v3.0+) with Schema Registry
  - PostgreSQL database (v14+)
  - Redis instance (v7.0+)
  - MLflow tracking server (v2.8+)
  - Feast feature store (v0.35+)
  - Jaeger tracing backend (optional)

### Access Requirements

- Kubernetes cluster admin access
- Docker registry push access
- Database credentials
- Kafka credentials
- MLflow access token

## Local Development

### Using Docker Compose

1. **Copy environment file**:
```bash
cp .env.example .env
# Edit .env with your configuration
```

2. **Start services**:
```bash
docker-compose up -d
```

3. **Check service health**:
```bash
curl http://localhost:8000/api/v1/health
```

4. **View logs**:
```bash
docker-compose logs -f predictor-service
```

5. **Stop services**:
```bash
docker-compose down
```

### Using Python Directly

1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

2. **Set environment variables**:
```bash
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
export MLFLOW_TRACKING_URI=http://localhost:5000
# ... other variables
```

3. **Run service**:
```bash
python -m src.main
```

## Production Deployment

### Step 1: Build Docker Image

```bash
# Build image
docker build -t predictor-online-inference-service:1.0.0 .

# Tag for registry
docker tag predictor-online-inference-service:1.0.0 your-registry/predictor-online-inference-service:1.0.0

# Push to registry
docker push your-registry/predictor-online-inference-service:1.0.0
```

### Step 2: Configure Kubernetes

1. **Update ConfigMap** (`k8s/configmap.yaml`):
```bash
# Edit with your configuration
kubectl apply -f k8s/configmap.yaml
```

2. **Create Secrets** (`k8s/secret.yaml`):
```bash
# Update with actual credentials
kubectl apply -f k8s/secret.yaml
```

3. **Deploy Service**:
```bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/hpa.yaml
```

### Step 3: Verify Deployment

1. **Check pod status**:
```bash
kubectl get pods -l app=predictor-service
```

2. **Check service health**:
```bash
kubectl port-forward svc/predictor-service 8000:8000
curl http://localhost:8000/api/v1/health
```

3. **Check logs**:
```bash
kubectl logs -l app=predictor-service -f
```

4. **Check metrics**:
```bash
kubectl port-forward svc/predictor-service 9090:9090
curl http://localhost:9090/metrics
```

## Configuration

### Environment Variables

See `.env.example` for all available configuration options.

**Critical Variables**:
- `KAFKA_BOOTSTRAP_SERVERS`: Kafka broker addresses
- `MLFLOW_TRACKING_URI`: MLflow server URL
- `FEAST_REPO_PATH`: Path to Feast repository
- `REDIS_HOST`: Redis server address
- `POSTGRES_HOST`: PostgreSQL server address

### Resource Limits

**Recommended Settings**:
- CPU Request: 500m
- CPU Limit: 2000m
- Memory Request: 512Mi
- Memory Limit: 2Gi

**Scaling**:
- Min Replicas: 3
- Max Replicas: 10
- Target CPU: 70%
- Target Memory: 80%

## Monitoring

### Prometheus Metrics

Metrics are exposed on port 9090 at `/metrics` endpoint.

**Key Metrics**:
- `predictions_total`: Total predictions by mode
- `prediction_latency_ms`: Prediction latency histogram
- `prediction_cache_hits_total`: Cache hit counter
- `model_load_failures_total`: Model load failure counter
- `feature_fetch_failures_total`: Feature fetch failure counter
- `label_consistency_score`: Label consistency gauge

### Health Checks

**Liveness Probe**: `/api/v1/health`
- Initial Delay: 30s
- Period: 10s
- Timeout: 5s
- Failure Threshold: 3

**Readiness Probe**: `/api/v1/health`
- Initial Delay: 10s
- Period: 5s
- Timeout: 3s
- Failure Threshold: 3

### Logging

Logs are structured JSON with the following fields:
- `timestamp`: ISO 8601 timestamp
- `level`: Log level
- `message`: Log message
- `service`: Service name
- `trace_id`: Trace ID for correlation

## Troubleshooting

### Service Won't Start

1. **Check pod logs**:
```bash
kubectl logs -l app=predictor-service --tail=100
```

2. **Check events**:
```bash
kubectl get events --sort-by='.lastTimestamp'
```

3. **Verify configuration**:
```bash
kubectl describe configmap predictor-config
kubectl describe secret predictor-secrets
```

### High Latency

1. **Check feature fetch latency**:
```bash
# Query Prometheus
feature_fetch_latency_ms{quantile="0.95"}
```

2. **Check cache hit rate**:
```bash
# Query Prometheus
rate(prediction_cache_hits_total[5m]) / rate(predictions_total[5m])
```

3. **Check model load time**:
```bash
# Check logs for model loading
kubectl logs -l app=predictor-service | grep "Model loaded"
```

### Model Load Failures

1. **Verify MLflow connectivity**:
```bash
kubectl exec -it <pod-name> -- curl http://mlflow:5000/health
```

2. **Check model version**:
```bash
# Verify model exists in MLflow
curl http://mlflow:5000/api/2.0/mlflow/registered-models/get?name=predictor_model
```

3. **Check fallback model**:
```bash
# Verify fallback model version is set
kubectl get configmap predictor-config -o yaml | grep fallback
```

## Rollback

### Kubernetes Rollback

```bash
# View deployment history
kubectl rollout history deployment/predictor-service

# Rollback to previous version
kubectl rollout undo deployment/predictor-service

# Rollback to specific revision
kubectl rollout undo deployment/predictor-service --to-revision=2
```

### Docker Rollback

```bash
# Update deployment with previous image
kubectl set image deployment/predictor-service predictor-service=your-registry/predictor-online-inference-service:0.9.0
```

## Maintenance

### Updating Configuration

```bash
# Update ConfigMap
kubectl apply -f k8s/configmap.yaml

# Restart pods to pick up changes
kubectl rollout restart deployment/predictor-service
```

### Scaling

```bash
# Manual scaling
kubectl scale deployment/predictor-service --replicas=5

# Update HPA
kubectl apply -f k8s/hpa.yaml
```

### Draining Pods

```bash
# Gracefully drain a node
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data
```

## Security

### Secrets Management

- Store sensitive credentials in Kubernetes Secrets
- Use RBAC to restrict access to secrets
- Rotate credentials regularly
- Never commit secrets to version control

### Network Policies

Consider implementing network policies to restrict traffic:
- Allow ingress only from API gateway
- Allow egress only to required services
- Deny all other traffic

## Performance Tuning

### Batch Size

Adjust `INFERENCE_BATCH_SIZE` based on:
- Available memory
- Model size
- Latency requirements

### Cache TTL

Adjust `INFERENCE_CACHE_TTL_SECONDS` based on:
- Prediction freshness requirements
- Cache hit rate
- Memory constraints

### Worker Count

Adjust `API_WORKERS` based on:
- CPU cores available
- Concurrent request load
- Memory per worker

## Support

For issues or questions:
- Check logs: `kubectl logs -l app=predictor-service`
- Check metrics: Prometheus dashboard
- Check traces: Jaeger UI
- Contact: Predictor Service Team

