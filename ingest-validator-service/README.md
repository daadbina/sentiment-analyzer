# Ingest Validator Service

A production-grade microservice for validating multilingual news articles with comprehensive multi-stage validation pipeline, consensus-based language detection, and exactly-once Kafka semantics.

## Overview

The Ingest Validator Service consumes raw news articles from Kafka topic `news_raw`, applies comprehensive validation rules (R1-R12), performs consensus-based language detection, and publishes validated articles to `news_validated` or rejected articles to `news_rejected`.

**Key Features:**
- Multi-stage validation pipeline with early exit optimization
- Dual-model language detection (FastText + XLM-RoBERTa) with consensus logic
- Timestamp normalization supporting multiple date formats
- UTF-8 encoding validation with BOM detection
- Content quality scoring with language-specific thresholds
- Duplicate detection integration via gRPC
- Exactly-once Kafka semantics with offset management
- Circuit breaker pattern for external dependencies
- Comprehensive metrics and distributed tracing
- TimescaleDB audit logging

## Quick Start

### Prerequisites
- Python 3.11+
- Kafka broker
- Schema Registry
- PostgreSQL/TimescaleDB
- Redis

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Set environment variables:

```bash
export KAFKA_BROKERS=localhost:9092
export SCHEMA_REGISTRY_URL=http://localhost:8081
export REDIS_HOST=localhost
export REDIS_PORT=6379
export TIMESCALEDB_DSN=postgresql://user:password@localhost:5432/validator
export DEDUP_SERVICE_URL=localhost:50051
```

### Running the Service

```bash
python -m src.main
```

The service will start on `http://localhost:8000` with:
- `/health` - Overall health check
- `/ready` - Readiness probe
- `/live` - Liveness probe
- `/metrics` - Prometheus metrics

## Architecture

### Validation Pipeline

```
Input → Schema Validation → Encoding Validation → Timestamp Validation 
→ Source Verification → Language Detection → Duplicate Check 
→ Content Quality → Scoring → Output Routing
```

### Validation Score Formula

```
VS = 0.15×L + 0.15×S + 0.15×E + 0.15×T + 0.15×G + 0.25×C
```

**Decision Logic:**
- VS ≥ 0.85 → Publish to `news_validated`
- 0.70 ≤ VS < 0.85 → Send to reprocess queue
- VS < 0.70 → Publish to `news_rejected`

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test suite
pytest tests/unit/
pytest tests/integration/
pytest tests/contract/
pytest tests/performance/
```

## Monitoring

### Prometheus Metrics

- `validator_messages_consumed_total` - Total messages consumed
- `validator_messages_validated_total` - Messages published to news_validated
- `validator_messages_rejected_total` - Messages published to news_rejected
- `validator_validation_duration_seconds` - End-to-end validation latency
- `validator_validation_score` - Distribution of validation scores
- `validator_language_confidence` - Average language detection confidence
- `validator_duplicate_rate` - Ratio of duplicate articles
- `validator_consumer_lag` - Kafka consumer lag

### Health Checks

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl http://localhost:8000/live
```

## Deployment

### Docker

```bash
docker build -t ingest-validator:latest .
docker run -p 8000:8000 ingest-validator:latest
```

### Docker Compose

```bash
docker-compose up -d
```

## Documentation

- See `CHANGELOG.md` for implementation details
- See `TODO.md` for remaining work
- See `.augment/rules/ingest-validator-service.md` for technical design

## License

Proprietary - Sentiment Analyzer Project

