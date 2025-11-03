# Canonicalizer-Normalizer Service

A production-grade microservice for canonicalizing, normalizing, and enriching news articles in the sentiment-analyzer-v2 pipeline.

## Overview

The canonicalizer-normalizer-service is a critical component in the multi-stage news processing pipeline. It sits between the ingest-validator-service and downstream NER/embedding services, performing comprehensive article canonicalization, normalization, and enrichment.

### Key Features

- **URL Canonicalization**: Standardizes URLs by removing tracking parameters, normalizing protocols, and extracting domains
- **Publisher Resolution**: Identifies publishers and assigns credibility scores using cache-aside pattern
- **Content Normalization**: Cleans and normalizes article content with encoding fixes, HTML removal, and whitespace normalization
- **Metadata Enrichment**: Extracts country/region information, classifies content type, and calculates readability scores
- **Domain Classification**: Categorizes articles into 8 domains (politics, economy, technology, conflict, health, environment, sports, entertainment)
- **Fuzzy Deduplication**: Detects duplicate articles using MinHash and Jaccard similarity
- **Normalization Scoring**: Calculates quality scores with weighted formula for accept/review/reject decisions

### Architecture

```
Kafka (news_validated) 
  ↓
Schema Validation
  ↓
URL Canonicalization
  ↓
Publisher Resolution
  ↓
Content Normalization
  ↓
Metadata Enrichment
  ↓
Domain Classification
  ↓
Fuzzy Deduplication
  ↓
Normalization Scoring
  ↓
Kafka (news_canonical/DLQ)
```

## Installation

### Prerequisites

- Python 3.11+
- Kafka 3.0+
- PostgreSQL 13+
- Redis 6.0+
- Schema Registry

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd canonicalizer-normalizer-service
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file:
```bash
cp .env.example .env
# Edit .env with your configuration
```

## Configuration

### Environment Variables

```env
# Kafka Configuration
KAFKA_BROKERS=localhost:9092
SCHEMA_REGISTRY_URL=http://localhost:8081
CONSUMER_GROUP=canonicalizer-service-group
INPUT_TOPIC=news_validated
OUTPUT_TOPIC=news_canonical
DLQ_TOPIC=news_canonical_dlq

# PostgreSQL Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=sentiment_analyzer
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Normalization Configuration
NORMALIZATION_SCORE_ACCEPT=0.85
NORMALIZATION_SCORE_REVIEW=0.70
FUZZY_DEDUP_THRESHOLD=0.90

# Service Configuration
PROMETHEUS_PORT=9103
LOG_LEVEL=INFO
```

### Configuration Classes

The service uses Pydantic settings with nested configuration classes:

- `KafkaSettings`: Kafka broker and topic configuration
- `PostgresSettings`: PostgreSQL connection settings
- `RedisSettings`: Redis connection settings
- `NormalizationSettings`: Normalization thresholds and parameters
- `ServiceSettings`: Service-level configuration

## Running the Service

### Development

```bash
python -m src.main
```

### Production

```bash
gunicorn -w 4 -b 0.0.0.0:8000 src.main:app
```

### Docker

```bash
docker build -t canonicalizer-normalizer-service .
docker run -e KAFKA_BROKERS=kafka:9092 canonicalizer-normalizer-service
```

## Testing

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test File

```bash
pytest tests/test_url_canonicalizer.py -v
```

### Run with Coverage

```bash
pytest tests/ --cov=src --cov-report=html
```

### Test Files

- `tests/test_url_canonicalizer.py` - URL canonicalization tests (11 tests)
- `tests/test_content_normalizer.py` - Content normalization tests (11 tests)
- `tests/test_metadata_enricher.py` - Metadata enrichment tests (10 tests)
- `tests/test_domain_classifier.py` - Domain classification tests (11 tests)
- `tests/test_fuzzy_deduplicator.py` - Fuzzy deduplication tests (8 tests)
- `tests/test_normalization_scorer.py` - Normalization scoring tests (11 tests)

**Total: 61 tests, all passing**

## API Endpoints

### Health Check

```bash
GET /health
```

### Metrics

```bash
GET /metrics
```

Prometheus metrics endpoint for monitoring.

## Data Models

### Input: NewsValidatedMessage

From `news_validated` topic (20 fields):
- article_id, canonical_url, title, body, url, source
- language, language_confidence, language_detection_method
- source_published_at_raw, source_published_at_utc, ingested_at, validated_at
- country, checksum, validation_score, validation_details
- schema_version, ingest_job_id, validation_job_id, trace_id, publisher_id

### Output: NewsCanonicalMessage

To `news_canonical` topic (38 fields):
- All input fields plus:
- normalized_url, url_hash, normalized_title, normalized_body
- publisher_name, publisher_credibility, publisher_country
- region, domain_category, content_type, readability_score
- word_count, sentence_count, normalized_checksum
- normalization_score, normalization_details
- canonicalization_job_id, canonicalized_at

## Normalization Score Formula

```
NS = 0.20×U + 0.20×P + 0.25×C + 0.15×M + 0.10×D + 0.10×F

Where:
- U (URL): 1.0 if canonicalized successfully
- P (Publisher): credibility_score from registry (0.0-1.0)
- C (Content): 0.2-1.0 based on word count (≥100 words = 1.0)
- M (Metadata): (readability_score + 1.0) / 2.0
- D (Domain): 1.0 if classified
- F (Fuzzy): 1.0 if checked
```

## Decision Logic

- **NS ≥ 0.85**: Publish to `news_canonical` (accept)
- **0.70 ≤ NS < 0.85**: Publish to `news_canonical` with quality_flag (review)
- **NS < 0.70**: Publish to `news_canonical_dlq` (reject)

## Monitoring

### Prometheus Metrics

- `messages_processed_total`: Total messages processed
- `messages_accepted_total`: Messages accepted (NS ≥ 0.85)
- `messages_review_total`: Messages flagged for review (0.70 ≤ NS < 0.85)
- `messages_rejected_total`: Messages rejected (NS < 0.70)
- `processing_duration_seconds`: Processing time histogram
- `normalization_score_histogram`: Normalization score distribution
- `*_errors_total`: Error counts for each pipeline stage

### Logging

Structured JSON logging with correlation IDs for request tracing.

## Performance

- **Throughput**: ~1000 articles/second (single instance)
- **Latency**: ~100ms per article (p99)
- **Memory**: ~500MB per instance
- **CPU**: ~2 cores recommended

## Troubleshooting

### Common Issues

1. **Kafka Connection Error**
   - Check KAFKA_BROKERS configuration
   - Verify Kafka cluster is running
   - Check network connectivity

2. **PostgreSQL Connection Error**
   - Check POSTGRES_HOST and POSTGRES_PORT
   - Verify PostgreSQL is running
   - Check credentials

3. **Redis Connection Error**
   - Check REDIS_HOST and REDIS_PORT
   - Verify Redis is running
   - Check network connectivity

4. **Schema Registry Error**
   - Check SCHEMA_REGISTRY_URL
   - Verify Schema Registry is running
   - Check network connectivity

## Contributing

1. Create a feature branch
2. Make your changes
3. Add tests for new functionality
4. Run tests: `pytest tests/ -v`
5. Submit a pull request

## License

Proprietary - sentiment-analyzer-v2 project

## Support

For issues and questions, please contact the development team.

