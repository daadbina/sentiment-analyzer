# Changelog

All notable changes to the NER Entity Linking Service will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-11-03

### Added

- Initial implementation of NER Entity Linking Service
- Multilingual NER support for 14 languages:
  - English, Persian, Russian, Chinese, Arabic
  - German, French, Spanish, Japanese, Korean
  - Italian, Portuguese, Turkish, Hindi
- Multiple NER model strategies:
  - spaCy transformers for Western languages
  - HuggingFace BERT models for other languages
- Entity linking to knowledge bases:
  - Wikidata Query Service (primary)
  - DBpedia Spotlight (secondary)
  - OpenSanctions (tertiary)
- Actor management and deduplication:
  - PostgreSQL persistence
  - Normalization and alias extraction
  - Occurrence tracking
- Kafka integration:
  - Consumer for `news_canonical` topic
  - Producer for `entities_extracted` topic
  - Exactly-once semantics
  - Avro schema validation
- Comprehensive monitoring:
  - Prometheus metrics (counters, histograms, gauges)
  - OpenTelemetry tracing support
  - Structured logging
- High availability features:
  - Connection pooling (PostgreSQL, Redis)
  - Circuit breaker pattern for external APIs
  - Rate limiting
  - Graceful shutdown
- Docker and Kubernetes support:
  - Multi-stage Dockerfile
  - Docker Compose for local development
  - Health checks
- Comprehensive test suite:
  - Unit tests for normalization
  - Unit tests for NER orchestration
  - Unit tests for entity linking
  - Mock-based testing for external dependencies

### Configuration

- Service configuration via environment variables
- Support for development, staging, and production environments
- Configurable thresholds for entity coverage validation
- Configurable model cache size and timeouts

### Documentation

- README.md with setup and usage instructions
- CHANGELOG.md for version tracking
- Inline code documentation and docstrings
- Configuration examples

## Future Enhancements

- [ ] DBpedia Spotlight integration
- [ ] OpenSanctions integration
- [ ] Relationship extraction between entities
- [ ] Co-occurrence analysis
- [ ] Advanced disambiguation strategies
- [ ] Multi-hop entity linking
- [ ] Custom entity type support
- [ ] Batch processing optimization
- [ ] GPU acceleration for NER models
- [ ] Distributed caching with Redis Cluster

