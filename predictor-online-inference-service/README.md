# Predictor Online Inference Service

Real-time and batch machine learning inference service for predicting event realization probabilities for semantic news groups.

## Overview

The Predictor Online Inference Service is a production-ready stateless microservice that:

- Performs real-time streaming inference from Kafka topics
- Provides REST API for synchronous batch and single predictions
- Integrates with Feature Engineering Service via Feast (offline/online store)
- Integrates with Labeler Service for ground-truth validation
- Loads models from MLflow registry with version management
- Caches predictions in Redis for performance
- Stores prediction history in PostgreSQL with full audit trail
- Publishes predictions to Kafka topic using Avro schema
- Supports A/B testing across model versions
- Provides comprehensive monitoring via Prometheus metrics
- Implements graceful degradation with fallback models

## Architecture

### Components

- **FastAPI**: REST API framework with async handlers
- **MLflow**: Model registry and version management
- **Feast**: Feature store (offline: Delta Lake, online: Redis)
- **Kafka**: Message broker with Avro schema registry
- **PostgreSQL**: Database for prediction history and labels
- **Redis**: Caching and online feature store
- **Prometheus**: Metrics collection
- **OpenTelemetry + Jaeger**: Distributed tracing

### Design Patterns

- **Strategy Pattern**: Pluggable inference strategies
- **Factory Pattern**: Model and predictor creation
- **Observer Pattern**: Prediction monitoring
- **Repository Pattern**: Abstract data access
- **Adapter Pattern**: Wrap external clients
- **Circuit Breaker Pattern**: Protect model loading
- **Cache-Aside Pattern**: Lazy load predictions

## Performance SLOs

- API latency p95: <300ms (including feature fetch)
- Streaming latency p95: <200ms (including feature fetch)
- Throughput: ≥1000 predictions/sec
- Cache hit rate: ≥50%
- Feature fetch latency: <50ms p95
- Label query latency: <100ms p95

## Installation

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Access to MLflow tracking server
- Access to Feast feature store
- Access to Kafka cluster
- Access to PostgreSQL database
- Access to Redis instance

### Local Development

1. Clone the repository:
```bash
git clone <repository-url>
cd predictor-online-inference-service
```

2. Copy environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run with Docker Compose:
```bash
docker-compose up -d
```

5. Run locally:
```bash
python -m src.main
```

## Configuration

All configuration is done via environment variables. See `.env.example` for all available options.

### Key Configuration Sections

- **Kafka**: Message broker configuration
- **MLflow**: Model registry configuration
- **Feast**: Feature store configuration
- **Redis**: Cache configuration
- **PostgreSQL**: Database configuration
- **Inference**: Inference behavior configuration
- **API**: REST API configuration
- **Monitoring**: Observability configuration
- **Validation**: Validation thresholds

## API Endpoints

### POST /api/v1/predict

Make prediction for a single semantic group.

**Request:**
```json
{
  "group_id": "group_123",
  "domain": "btc"
}
```

**Response:**
```json
{
  "group_id": "group_123",
  "domain": "btc",
  "prediction_probability": 0.85,
  "prediction_confidence": 0.70,
  "model_version": "v1.0.0",
  "predicted_at": "2025-11-07T12:00:00Z",
  "trace_id": "01JCABCDEFGHIJKLMNOPQRSTUV"
}
```

### POST /api/v1/predict/batch

Make predictions for multiple semantic groups.

**Request:**
```json
{
  "group_ids": ["group_123", "group_456"],
  "domain": "btc"
}
```

**Response:**
```json
{
  "predictions": [...],
  "total": 2
}
```

### GET /api/v1/health

Check service and dependency health.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-11-07T12:00:00Z",
  "dependencies": {
    "mlflow": "healthy",
    "feast": "healthy",
    "redis": "healthy",
    "postgres": "healthy",
    "kafka": "healthy"
  }
}
```

### GET /api/v1/model/metadata

Get metadata for the current model version.

**Response:**
```json
{
  "model_name": "predictor_model",
  "model_version": "v1.0.0",
  "stage": "Production",
  "created_at": "2025-11-01T00:00:00Z",
  "description": "Event realization prediction model",
  "tags": {
    "framework": "xgboost",
    "accuracy": "0.85"
  }
}
```

### GET /metrics

Prometheus metrics endpoint.

## Monitoring

### Prometheus Metrics

The service exposes 30+ Prometheus metrics including:

- `predictions_total`: Total predictions by mode
- `prediction_latency_ms`: Prediction latency histogram
- `prediction_cache_hits_total`: Cache hit counter
- `prediction_cache_misses_total`: Cache miss counter
- `model_load_failures_total`: Model load failure counter
- `feature_fetch_failures_total`: Feature fetch failure counter
- `feature_fetch_latency_ms`: Feature fetch latency histogram
- `label_consistency_score`: Label consistency gauge
- `api_request_latency_ms`: API request latency histogram

### Distributed Tracing

The service uses OpenTelemetry for distributed tracing with Jaeger backend. All requests include a `trace_id` for correlation.

### Structured Logging

All logs are structured JSON with the following fields:

- `timestamp`: ISO 8601 timestamp
- `level`: Log level (DEBUG/INFO/WARNING/ERROR)
- `message`: Log message
- `service`: Service name
- `trace_id`: Trace ID for correlation
- `group_id`: Semantic group ID (when applicable)
- `model_version`: Model version (when applicable)

## Testing

Run unit tests:
```bash
pytest tests/unit -v
```

Run integration tests:
```bash
pytest tests/integration -v
```

Run all tests with coverage:
```bash
pytest tests/ --cov=src --cov-report=html
```

## Deployment

### Docker

Build Docker image:
```bash
docker build -t predictor-online-inference-service:latest .
```

Run Docker container:
```bash
docker run -p 8000:8000 -p 9090:9090 --env-file .env predictor-online-inference-service:latest
```

### Kubernetes

Deploy to Kubernetes:
```bash
kubectl apply -f k8s/
```

## License

Copyright © 2025. All rights reserved.

