# Labeler Ground-Truth Ingest Service

Ingest ground-truth labels from external APIs (ACLED, GDELT, CoinGecko), reconcile labels with semantic groups, validate label consistency and freshness, write ground-truth data to Delta Lake and PostgreSQL, and publish labels to Kafka for model training.

## Features

- **Multi-source label ingestion**: ACLED (conflicts), GDELT (events), CoinGecko (crypto prices)
- **Label reconciliation**: Temporal and semantic matching with semantic groups
- **Label validation**: Consistency checks, freshness validation (R10), temporal alignment (R8)
- **Deduplication**: Hash-based deduplication with confidence scoring
- **License tracking**: Track and verify label source licenses
- **Dual-write coordination**: Atomic writes to Kafka, Delta Lake, and PostgreSQL
- **Drift detection**: Monitor label distribution shifts and anomalies
- **Circuit breaker**: Resilient API calls with fallback mechanisms
- **Comprehensive logging**: Structured logging with trace IDs for debugging
- **Prometheus metrics**: Monitor label ingestion, reconciliation, validation

## Architecture

### Components

- **API Fetchers**: ACLED, GDELT, CoinGecko clients with circuit breaker
- **Label Reconciler**: Temporal and semantic matching
- **Label Validator**: Quality checks and consistency validation
- **License Checker**: Track and verify label source licenses
- **Freshness Validator**: Enforce R10 freshness requirements
- **Delta Lake Writer**: ACID writes with data sanitization
- **PostgreSQL Writer**: Transactional writes with connection pooling
- **Kafka Producer**: Avro serialization with exactly-once semantics

### Data Flow

```
ACLED API ─┐
GDELT API  ├─> Fetch ─> Validate ─> Reconcile ─> Store ─> Kafka
CoinGecko  ┘                                      ├─> Delta Lake
                                                  └─> PostgreSQL
```

## Configuration

All configuration is externalized to environment variables. See `.env.example` for all parameters.

### Key Parameters

- `KAFKA_BROKERS`: Kafka bootstrap servers
- `SCHEMA_REGISTRY_URL`: Schema Registry endpoint
- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`: PostgreSQL connection
- `ACLED_API_KEY`: ACLED API key
- `ACLED_FETCH_INTERVAL_HOURS`: ACLED fetch frequency (default: 24)
- `GDELT_FETCH_INTERVAL_HOURS`: GDELT fetch frequency (default: 1)
- `COINGECKO_FETCH_INTERVAL_MINUTES`: CoinGecko fetch frequency (default: 5)
- `LABEL_RECONCILIATION_THRESHOLD`: Temporal matching threshold in hours (default: 48)
- `LABEL_CONFIDENCE_THRESHOLD`: Minimum label confidence (default: 0.7)

## Installation

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your configuration

# Run service
python -m src.main
```

### Docker

```bash
# Build image
docker build -t sentiment-analyzer/labeler-ground-truth-ingest-service:v1.0.0 .

# Run container
docker run -e KAFKA_BROKERS=154.53.166.231:9092 \
           -e POSTGRES_HOST=154.53.166.231 \
           -e ACLED_API_KEY=your_key \
           sentiment-analyzer/labeler-ground-truth-ingest-service:v1.0.0
```

### Kubernetes

```bash
# Apply manifests
kubectl apply -f k8s/

# Or use Helm
helm install labeler-service ./helm \
  --namespace sentiment-analyzer \
  --values helm/values.yaml
```

## Testing

```bash
# Run unit tests
pytest tests/unit/ -v

# Run integration tests
pytest tests/integration/ -v

# Run all tests with coverage
pytest tests/ --cov=src --cov-report=html
```

## Monitoring

### Prometheus Metrics

- `label_fetched_total`: Total labels fetched by source
- `label_reconciled_total`: Successfully reconciled labels
- `label_validation_failures_total`: Failed label validations
- `label_fetch_duration_seconds`: API fetch latency
- `label_reconciliation_duration_seconds`: Reconciliation latency
- `label_freshness_hours`: Age of latest label by source
- `label_confidence_avg`: Average label confidence score

### Health Checks

- `/health`: Liveness probe
- `/ready`: Readiness probe

## Requirements

- Python 3.11+
- Kafka 2.8+
- PostgreSQL 12+
- Delta Lake 0.10+
- Rust 1.70+ (for librdkafka)

## License

CC-BY-4.0

## Support

For issues and questions, please contact the Sentiment Analyzer Team.

