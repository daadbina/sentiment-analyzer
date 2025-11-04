# NER Entity Linking Service API Documentation

## Overview

The NER Entity Linking Service is a microservice that extracts named entities from news articles and links them to knowledge bases (Wikidata, DBpedia, OpenSanctions).

## Kafka Topics

### Input Topic: `news_canonical`

Consumes canonicalized news articles from the Canonicalizer-Normalizer Service.

**Message Schema (Avro):**
```json
{
  "article_id": "string",
  "title": "string",
  "content": "string",
  "language": "string",
  "source": "string",
  "published_date": "long",
  "canonical_url": "string"
}
```

### Output Topic: `entities_extracted`

Produces extracted entities with linking information.

**Message Schema (Avro):**
```json
{
  "article_id": "string",
  "entities": [
    {
      "entity_id": "string",
      "text": "string",
      "entity_type": "string",
      "confidence": "double",
      "start_char": "int",
      "end_char": "int",
      "context_snippet": "string",
      "wikidata_id": "string",
      "wikidata_label": "string",
      "dbpedia_uri": "string",
      "opensanctions_match": "boolean"
    }
  ],
  "extraction_timestamp": "long",
  "extraction_latency_ms": "int",
  "coverage_percentage": "double",
  "language": "string"
}
```

## Metrics Endpoints

### Health Check

**Endpoint:** `GET /health`

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-04T10:00:00Z"
}
```

### Readiness Check

**Endpoint:** `GET /ready`

**Response:**
```json
{
  "ready": true,
  "kafka_connected": true,
  "postgres_connected": true,
  "redis_connected": true
}
```

### Prometheus Metrics

**Endpoint:** `GET /metrics`

**Available Metrics:**
- `ner_entities_extracted_total` - Total entities extracted
- `ner_extraction_latency_seconds` - Extraction latency histogram
- `ner_entity_linking_success_total` - Successful entity linking
- `ner_entity_linking_failures_total` - Failed entity linking
- `ner_wikidata_requests_total` - Wikidata API requests
- `ner_dbpedia_requests_total` - DBpedia API requests
- `ner_opensanctions_requests_total` - OpenSanctions API requests
- `ner_kafka_consumer_lag` - Kafka consumer lag
- `ner_model_cache_hits_total` - Model cache hits
- `ner_model_cache_misses_total` - Model cache misses

## Configuration

### Environment Variables

```bash
# Service Configuration
SERVICE_NAME=ner-entity-linking-service
LOG_LEVEL=INFO

# Kafka Configuration
KAFKA_BROKERS=localhost:9092
CONSUMER_GROUP=ner-service-group
INPUT_TOPIC=news_canonical
OUTPUT_TOPIC=entities_extracted

# PostgreSQL Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=adminsentiment
POSTGRES_PASSWORD=wp2400!!!!
POSTGRES_DATABASE=sentiment

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379

# NER Configuration
NER_CONFIDENCE_THRESHOLD=0.85
NER_MAX_ENTITIES_PER_ARTICLE=100

# Entity Linking Configuration
ENTITY_LINKING_TIMEOUT=10
ENTITY_LINKING_CONFIDENCE_THRESHOLD=0.7
```

## Database Schema

### actors Table

```sql
CREATE TABLE actors (
  actor_id UUID PRIMARY KEY,
  normalized_name VARCHAR(255) NOT NULL,
  wikidata_id VARCHAR(50),
  dbpedia_uri VARCHAR(500),
  entity_type VARCHAR(50),
  country VARCHAR(100),
  occurrence_count INT DEFAULT 1,
  first_seen TIMESTAMP,
  last_seen TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_actors_normalized_name ON actors(normalized_name);
CREATE INDEX idx_actors_wikidata_id ON actors(wikidata_id);
CREATE INDEX idx_actors_type ON actors(entity_type);
```

## Error Handling

### Common Errors

| Error | Status | Description |
|-------|--------|-------------|
| KAFKA_CONNECTION_ERROR | 503 | Cannot connect to Kafka broker |
| POSTGRES_CONNECTION_ERROR | 503 | Cannot connect to PostgreSQL |
| REDIS_CONNECTION_ERROR | 503 | Cannot connect to Redis |
| INVALID_MESSAGE_FORMAT | 400 | Invalid Avro message format |
| NER_MODEL_ERROR | 500 | Error loading NER model |
| ENTITY_LINKING_ERROR | 500 | Error linking entity to knowledge base |

## Performance Characteristics

- **Throughput:** ≥200 articles/minute per replica
- **Latency:** ≤5 seconds average extraction time
- **Entity Extraction Accuracy:** ≥90% F1 (English), ≥85% (other languages)
- **Entity Linking Accuracy:** ≥85% precision
- **Coverage:** ≥95% of articles meet R4 thresholds

## Supported Languages

- English (en)
- Persian (fa)
- Russian (ru)
- Chinese (zh)
- Arabic (ar)
- German (de)
- French (fr)
- Spanish (es)
- Japanese (ja)
- Korean (ko)
- Italian (it)
- Portuguese (pt)
- Turkish (tr)
- Hindi (hi)

## Examples

### Processing a News Article

```python
from src.ner.orchestrator import NEROrchestrator

orchestrator = NEROrchestrator()

text = "John Smith works at Microsoft in Seattle."
language = "en"

entities = orchestrator.extract_entities(text, language)

for entity in entities:
    print(f"{entity['text']} ({entity['entity_type']})")
    print(f"  Wikidata: {entity.get('wikidata_id')}")
    print(f"  Confidence: {entity['confidence']}")
```

### Linking an Entity

```python
from src.linking.entity_linker import EntityLinker

linker = EntityLinker()

result = linker.link_entity(
    entity_text="Barack Obama",
    entity_type="PERSON",
    language="en"
)

print(f"Wikidata ID: {result['wikidata_id']}")
print(f"Label: {result['wikidata_label']}")
```

