# Embedding Service

Multilingual embedding generation service for the sentiment-analyzer-v2 system. Consumes normalized news articles and produces high-quality embeddings for downstream semantic analysis.

## Features

- **Multilingual Support**: 14+ languages with language-specific models
- **GPU Acceleration**: CUDA support with automatic batch sizing
- **Exactly-Once Semantics**: Outbox pattern for atomic dual-writes
- **Quality Validation**: Embedding dimension, NaN/Inf, and norm checks
- **Drift Detection**: Kolmogorov-Smirnov test for distribution monitoring
- **Model Versioning**: PostgreSQL-based model registry and tracking
- **Distributed Tracing**: OpenTelemetry integration for observability
- **Prometheus Metrics**: 10+ metrics for monitoring and alerting
- **High Availability**: Pod anti-affinity and horizontal autoscaling

## Quick Start

### Local Development

```bash
# Create virtual environment
python3.11 -m venv venv311
source venv311/bin/activate  # or venv311\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export KAFKA_BROKERS=localhost:9092
export QDRANT_HOST=localhost
export POSTGRES_HOST=localhost

# Run with Docker Compose
docker-compose up -d

# Run service
python -m src.main
```

### Docker

```bash
# CPU version
docker build -t embedding-service:latest .
docker run -p 8000:8000 embedding-service:latest

# GPU version
docker build -f Dockerfile.gpu -t embedding-service:gpu .
docker run --gpus all -p 8000:8000 embedding-service:gpu
```

### Kubernetes

```bash
# Using kubectl
kubectl apply -f k8s/

# Using Helm
helm install embedding-service helm/
```

## Architecture

### 9-Stage Pipeline

1. **Language Detection**: Identify article language
2. **Model Selection**: Choose language-specific model
3. **Text Preprocessing**: Normalize and clean text
4. **Batch Assembly**: Group texts for efficient processing
5. **Embedding Computation**: Generate embeddings on GPU
6. **L2 Normalization**: Normalize to unit vectors
7. **Quality Validation**: Check embedding quality
8. **Drift Detection**: Monitor distribution changes
9. **Atomic Write**: Store in Qdrant + publish to Kafka

### Data Flow

```
Kafka (news_canonical)
    ↓
[9-Stage Pipeline]
    ↓
Qdrant (Vector DB) + Kafka (embeddings topic)
```

## Configuration

All configuration via environment variables (see `.env.example`):

```bash
# Kafka
KAFKA_BROKERS=kafka:9092
KAFKA_SCHEMA_REGISTRY_URL=http://schema-registry:8081

# Qdrant
QDRANT_HOST=qdrant
QDRANT_PORT=6333

# PostgreSQL
POSTGRES_HOST=postgres
POSTGRES_USER=embedding

# Model
MODEL_DEVICE=cuda
MODEL_BATCH_SIZE_GPU=32
```

## API Endpoints

- `GET /health` - Health check
- `GET /ready` - Readiness check
- `GET /metrics` - Prometheus metrics
- `GET /info` - Service information

## Monitoring

### Prometheus Metrics

- `embedding_messages_consumed_total` - Messages consumed
- `embedding_computed_total` - Embeddings computed
- `embedding_qdrant_writes_total` - Qdrant writes
- `embedding_validation_failures_total` - Validation failures
- `embedding_computation_duration_seconds` - Computation time
- `embedding_gpu_memory_used_bytes` - GPU memory usage
- `embedding_drift_score` - Drift detection score

### Logs

Structured JSON logs to stdout:

```json
{
  "timestamp": "2025-11-04T10:30:45Z",
  "level": "INFO",
  "service": "embedding-service",
  "message": "Processing batch of 32 messages",
  "batch_id": "abc123",
  "count": 32
}
```

## Testing

```bash
# Run unit tests
pytest tests/

# Run with coverage
pytest --cov=src tests/

# Run specific test
pytest tests/test_preprocessing.py::TestTextPreprocessor::test_normalize_unicode
```

## Performance

- **Throughput**: 1000+ embeddings/second (GPU)
- **Latency**: 50-100ms per batch (GPU)
- **Memory**: 2-4GB (GPU), 1-2GB (CPU)
- **Batch Size**: 32 (GPU), 16 (CPU)

## Troubleshooting

### Service won't start
- Check Kafka connectivity: `telnet kafka 9092`
- Check Qdrant connectivity: `curl http://qdrant:6333/health`
- Check PostgreSQL connectivity: `psql -h postgres -U embedding`

### High latency
- Check GPU utilization: `nvidia-smi`
- Check batch size configuration
- Check model loading time in logs

### Memory issues
- Reduce `MODEL_BATCH_SIZE_GPU`
- Reduce `MODEL_POOL_SIZE`
- Enable model unloading

## Documentation

- [INTEGRATION.md](INTEGRATION.md) - Integration guide with schemas
- [TODO.md](TODO.md) - Implementation task tracking
- [CHANGELOG.md](CHANGELOG.md) - Version history and changes

## Development

### Project Structure

```
embedding-service/
├── src/
│   ├── config.py              # Configuration management
│   ├── exceptions.py          # Custom exceptions
│   ├── metrics.py             # Prometheus metrics
│   ├── service.py             # Main orchestrator
│   ├── main.py                # Entry point
│   ├── api.py                 # FastAPI endpoints
│   ├── models/                # Model management
│   ├── preprocessing/         # Text preprocessing
│   ├── batching/              # Batch processing
│   ├── embedding/             # Embedding computation
│   ├── validation/            # Quality validation
│   ├── qdrant/                # Vector DB integration
│   ├── clients/               # External service clients
│   ├── drift/                 # Drift detection
│   └── outbox/                # Outbox pattern
├── tests/                     # Unit tests
├── k8s/                       # Kubernetes manifests
├── helm/                      # Helm charts
├── Dockerfile                 # CPU image
├── Dockerfile.gpu             # GPU image
├── docker-compose.yml         # Local development
└── requirements.txt           # Python dependencies
```

### Adding New Features

1. Create feature branch: `git checkout -b feature/embedding-service/my-feature`
2. Implement feature with tests
3. Update TODO.md and CHANGELOG.md
4. Create pull request
5. Merge after review

## License

Part of sentiment-analyzer-v2 project.

## Support

For issues and questions, please refer to the main project repository.

