# NER Entity Linking Service

Phase 2 microservice for multilingual Named Entity Recognition (NER) and entity linking in the Sentiment Analyzer v2 system.

## Overview

This service consumes normalized news articles from Kafka topic `news_canonical`, performs language-specific NER for 14 languages, links extracted entities to knowledge bases (Wikidata, DBpedia, OpenSanctions), and publishes enriched entity metadata to Kafka topic `entities_extracted` and PostgreSQL `actors` table.

## Features

- **Multilingual NER**: Support for 14 languages (English, Persian, Russian, Chinese, Arabic, German, French, Spanish, Japanese, Korean, Italian, Portuguese, Turkish, Hindi)
- **Multiple NER Models**: spaCy transformers for Western languages, HuggingFace BERT models for others
- **Entity Linking**: Wikidata Query Service (primary), DBpedia Spotlight (secondary), OpenSanctions (tertiary)
- **Actor Management**: Deduplication and normalization of extracted entities
- **Kafka Integration**: Exactly-once semantics with transactional writes
- **Monitoring**: Prometheus metrics and OpenTelemetry tracing
- **High Availability**: Connection pooling, circuit breakers, rate limiting

## Architecture

### Components

1. **NER Orchestrator**: Coordinates extraction pipeline
2. **Model Registry**: Manages language-specific NER models with LRU caching
3. **Entity Linker**: Links entities to knowledge bases
4. **Actor Repository**: Persists and deduplicates actors in PostgreSQL
5. **Kafka Integration**: Consumes from `news_canonical`, produces to `entities_extracted`

### Data Flow

```
news_canonical (Kafka)
    ↓
NER Extraction (language-specific)
    ↓
Entity Linking (Wikidata, DBpedia, OpenSanctions)
    ↓
Actor Deduplication & Persistence (PostgreSQL)
    ↓
entities_extracted (Kafka) + actors table
```

## Installation

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Kafka 7.5+
- Docker & Docker Compose (for local development)

### Setup

1. Clone repository:
```bash
git clone https://github.com/daadbina/sentiment-analyzer.git
cd sentiment-analyzer/ner-entity-linking-service
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Download NER models:
```bash
python -m spacy download en_core_web_trf
python -m spacy download de_core_news_trf
# ... download other language models
```

## Configuration

Configuration is managed via environment variables. See `src/config.py` for all available options.

### Key Environment Variables

```bash
# Kafka
KAFKA_BROKERS=localhost:9092
SCHEMA_REGISTRY_URL=http://localhost:8081
KAFKA_CONSUMER_GROUP=ner-entity-linking-service
KAFKA_INPUT_TOPIC=news_canonical
KAFKA_OUTPUT_TOPIC=entities_extracted

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=adminsentiment
POSTGRES_PASSWORD=sentiment_secure_pass_2024
POSTGRES_DATABASE=sentiment

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# External APIs
WIKIDATA_API_URL=https://query.wikidata.org/sparql
WIKIDATA_TIMEOUT_SECONDS=10

# Monitoring
PROMETHEUS_PORT=9104
LOG_LEVEL=INFO
```

## Running

### Local Development

```bash
# Start all services
docker-compose up -d

# Run service
python -m src.main

# View logs
docker-compose logs -f ner-service
```

### Production

```bash
# Build Docker image
docker build -t sentiment-analyzer:ner-entity-linking-service .

# Run container
docker run -d \
  --name ner-service \
  -e KAFKA_BROKERS=kafka:9092 \
  -e POSTGRES_HOST=postgres \
  sentiment-analyzer:ner-entity-linking-service
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/test_entity_normalizer.py
```

## Monitoring

### Prometheus Metrics

Metrics available at `http://localhost:9104/metrics`:

- `ner_messages_consumed_total`: Total messages consumed
- `ner_entities_extracted_total`: Total entities extracted
- `ner_entities_linked_total`: Total entities linked
- `ner_extraction_duration_seconds`: Extraction duration histogram
- `ner_linking_duration_seconds`: Linking duration histogram
- `ner_coverage_score`: Entity coverage score histogram
- `ner_linking_success_rate`: Entity linking success rate gauge

### Logging

Structured logging with JSON output for production environments.

## API

### Input (Kafka Topic: news_canonical)

```json
{
  "article_id": "article-123",
  "normalized_body": "John Smith is from USA...",
  "language": "en",
  "trace_id": "trace-456"
}
```

### Output (Kafka Topic: entities_extracted)

```json
{
  "article_id": "article-123",
  "entities": [
    {
      "entity_id": "ent-1",
      "text": "John Smith",
      "normalized_text": "john smith",
      "entity_type": "PERSON",
      "confidence": 0.95,
      "wikidata_id": "Q12345",
      "country": "USA",
      "aliases": ["J. Smith"]
    }
  ],
  "language": "en",
  "ner_model": "en_core_web_trf",
  "entity_count": 5,
  "coverage_score": 0.85,
  "linking_success_rate": 0.80,
  "extracted_at": "2025-11-03T10:30:00Z",
  "trace_id": "trace-456"
}
```

## Performance

- **Throughput**: ~100 articles/second (single instance)
- **Latency**: ~500ms per article (p95)
- **Memory**: ~2GB per instance (with model caching)
- **CPU**: 2-4 cores recommended

## Troubleshooting

### Service won't start

1. Check Kafka connectivity: `kafka-broker-api-versions.sh --bootstrap-server localhost:9092`
2. Check PostgreSQL: `psql -h localhost -U adminsentiment -d sentiment`
3. Check Redis: `redis-cli ping`

### Low entity linking success rate

1. Verify Wikidata API is accessible
2. Check entity normalization logic
3. Review confidence thresholds in config

### High memory usage

1. Reduce model cache size in config
2. Implement model unloading strategy
3. Monitor with `docker stats`

## Contributing

See CONTRIBUTING.md for development guidelines.

## License

MIT License - See LICENSE file for details.

