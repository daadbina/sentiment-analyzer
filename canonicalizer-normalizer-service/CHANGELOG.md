# Changelog

All notable changes to the canonicalizer-normalizer-service will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.1.0] - 2025-11-12

### Changed
- **Enhanced Sentiment Analysis Logging**
  - Added INFO level logging in `SentimentAnalyzer.analyze()` to log sentiment score and text preview
  - Added WARNING level logging for empty or invalid text
  - Added INFO level logging for very short text (< 10 chars) with accuracy warning
  - Added text length validation and logging before sentiment analysis
  - Changed empty text logging from DEBUG to WARNING level for better visibility

### Fixed
- **Sentiment Feature Debugging** (Part of CRITICAL FIX for constant sentiment features)
  - Added comprehensive logging to diagnose why sentiment features are constant
  - Log normalized_title and normalized_body lengths before sentiment analysis
  - Log sentiment_score result at INFO level instead of DEBUG
  - Added text preview in logs to verify content is being analyzed
  - This enables diagnosis of whether empty content is causing constant 0.0 sentiment scores

### Impact
- ✅ Better visibility into sentiment analysis process
- ✅ Easier debugging of constant sentiment feature issue
- ✅ Warnings when content is too short for accurate sentiment analysis
- ✅ Ability to verify if normalized content is empty

## [3.0.0] - 2024-01-21

### Added

#### Version 3.0.0 - Production Deployment & Testing
- Docker containerization with multi-stage build
- Docker Compose for local development environment
- Prometheus monitoring configuration with 15+ metrics
- Alerting rules for critical service conditions
- Comprehensive API documentation (OpenAPI-style)
- Deployment guide with troubleshooting
- Integration tests (15 tests) for end-to-end pipeline
- Performance benchmarks (13 tests) for throughput and latency
- Health check endpoints for service monitoring
- 28 comprehensive tests for deployment and testing

#### Version 2.1.0 - Database Optimization
- Connection pooling with configurable min/max sizes
- Automatic health checks for database connections
- Database indexing for frequently queried fields (publisher domain, article URL hash, canonicalization timestamp)
- Index management and statistics
- Connection pool statistics and monitoring
- 18 comprehensive tests for connection pooling

#### Version 2.2.0 - Distributed Tracing
- OpenTelemetry integration for distributed tracing
- Jaeger backend support for trace visualization
- Trace span creation, completion, and event tracking
- Trace export as JSON for analysis
- Trace propagation through pipeline stages
- 23 comprehensive tests for distributed tracing

#### Version 2.3.0 - Real-Time Analytics
- Real-time analytics engine for pipeline monitoring
- Time series metrics collection
- Analytics snapshots with aggregated statistics
- Cache hit rate tracking
- Deduplication rate tracking
- Error rate calculation
- Throughput monitoring (messages per second)
- Domain and publisher distribution tracking
- 33 comprehensive tests for analytics

#### Version 2.4.0 - REST API Endpoints
- Single article canonicalization endpoint
- Batch canonicalization endpoint (configurable batch size)
- Publisher lookup endpoint
- Deduplication check endpoint
- Health check endpoint
- Standardized API request/response models
- Error handling and validation
- 24 comprehensive tests for API endpoints

### Test Coverage
- **Total Tests**: 421 (100% passing)
- Version 1.0.0: 61 tests (core pipeline)
- Version 1.1.0: 58 tests (language processing)
- Version 1.2.0: 27 tests (ML classification)
- Version 1.3.0: 50 tests (advanced deduplication)
- Version 1.4.0: 41 tests (performance optimization)
- Version 1.5.0: 60 tests (monitoring & observability)
- Version 2.0.0: 23 tests (multi-language support)
- Version 2.1.0: 18 tests (database optimization)
- Version 2.2.0: 23 tests (distributed tracing)
- Version 2.3.0: 33 tests (real-time analytics)
- Version 2.4.0: 24 tests (REST API)
- Version 3.0.0: 28 tests (integration & performance)

## [2.0.0] - 2024-01-20

### Added

#### Version 1.1.0 - Language-Specific Processing
- Persian text normalization using hazm library (normalization, tokenization)
- Chinese text normalization using opencc library (simplified/traditional conversion, punctuation normalization)
- Arabic text normalization with diacritic removal and reshaping
- Language-specific keyword dictionaries for domain classification (8 domains × 3 languages)
- LanguageProcessorFactory for creating language-specific processors
- 58 comprehensive tests for language processing

#### Version 1.2.0 - ML-Based Classification
- Zero-shot classification using transformer models (distilbert-base-uncased)
- MLDomainClassifier for improved domain classification with confidence scores
- MLPublisherCredibilityScorer for ML-based publisher credibility assessment
- Multi-label classification support
- MLClassifierFactory for creating and caching ML classifiers
- 27 comprehensive tests for ML classification

#### Version 1.3.0 - Advanced Deduplication
- LSH (Locality Sensitive Hashing) for scalable deduplication with datasketch
- SemanticDeduplicator using sentence embeddings (SBERT) for semantic similarity
- AdvancedDeduplicator combining LSH and semantic similarity
- Redirect resolution with HTTP redirect following and loop detection
- CachedRedirectResolver with Redis caching for redirect chains
- 27 tests for advanced deduplication
- 23 tests for redirect resolution

#### Version 1.4.0 - Performance Optimization
- CacheManager with distributed caching (Redis + local in-memory)
- NormalizationResultCache for caching canonicalization, classification, and publisher results
- CacheStats for monitoring cache performance (hit rate, misses, evictions)
- BatchProcessor for concurrent batch processing with configurable batch size and workers
- DatabaseBatchOperations for batch database operations
- RedisBatchOperations for batch Redis operations
- 22 tests for batch processing
- 19 tests for cache management

#### Version 1.5.0 - Monitoring and Observability
- StructuredLogger with JSON-formatted logs and correlation IDs
- PerformanceLogger for logging operations, cache hits/misses, database operations, and external API calls
- MetricsCollector for aggregating metrics with statistics (count, sum, min, max, avg)
- DomainMetrics for domain classification metrics
- DeduplicationMetrics for deduplication metrics
- NormalizationMetrics for normalization metrics
- CacheMetrics for cache performance metrics
- 20 tests for structured logging
- 40 tests for metrics collection

#### Version 2.0.0 - Multi-Language Support
- LanguageDetector for automatic language detection (14+ languages)
- Support for English, Persian, Chinese, Arabic, Russian, Japanese, Korean, Hindi, Spanish, French, German, Portuguese, Italian, Turkish
- MultiLanguageProcessor for language-aware content processing
- LanguageDetectionResult with confidence scores and reliability assessment
- 23 tests for language detection

### Changed
- Enhanced normalization pipeline with language-specific processors
- Improved domain classification with ML models
- Better deduplication with semantic similarity
- Optimized performance with caching and batch processing
- Better observability with structured logging and metrics

### Dependencies Added
- hazm>=0.7.0 (Persian text processing)
- opencc-python-reimplemented>=0.1.7 (Chinese text processing)
- python-bidi>=0.4.2 (Arabic text processing)
- arabic-reshaper>=0.6.0 (Arabic text reshaping)
- transformers>=4.35.0 (Transformer models)
- torch>=2.1.0 (PyTorch)
- sentence-transformers>=2.2.0 (Sentence embeddings)
- scikit-learn>=1.3.0 (ML utilities)
- langdetect>=1.0.9 (Language detection)
- httpx>=0.24.0 (Async HTTP client)

### Test Coverage
- **Total Tests**: 306 (100% passing)
- Version 1.0.0: 61 tests
- Version 1.1.0: 58 tests (language processing)
- Version 1.2.0: 27 tests (ML classification)
- Version 1.3.0: 50 tests (advanced deduplication + redirect resolution)
- Version 1.4.0: 41 tests (batch processing + caching)
- Version 1.5.0: 60 tests (structured logging + metrics)
- Version 2.0.0: 23 tests (language detection)

## [1.0.0] - 2024-01-15

### Added

#### Core Service
- Initial release of canonicalizer-normalizer-service microservice
- Kafka consumer with exactly-once semantics (manual commit, read_committed isolation)
- Kafka producer with idempotent configuration (acks=all, max.in.flight=1)
- PostgreSQL async client for publisher registry and audit logging
- Redis client for URL redirect caching, publisher caching, and LSH bucket caching

#### Canonicalization Pipeline
- URL canonicalization with protocol standardization, parameter normalization, tracking parameter removal
- Publisher resolution with cache-aside pattern and credibility scoring
- Content normalization with ftfy encoding fixes, HTML tag removal, URL removal, whitespace normalization
- Metadata enrichment with country extraction, region extraction, content type classification, readability scoring
- Domain classification with keyword-based classification for 8 categories (politics, economy, technology, conflict, health, environment, sports, entertainment)
- Fuzzy deduplication using MinHash with 3-gram shingling and Jaccard similarity
- Normalization scoring with weighted formula: NS = 0.20×U + 0.20×P + 0.25×C + 0.15×M + 0.10×D + 0.10×F

#### Data Models
- NewsValidatedMessage model for input from news_validated topic (20 fields)
- NewsCanonicalMessage model for output to news_canonical topic (38 fields)
- NormalizationDetails nested record with transformation flags
- PublisherEntity model for publisher registry
- Result models for each pipeline stage

#### Avro Schema
- news_canonical.avsc schema with 38 fields including nested NormalizationDetails record
- Full compatibility with upstream ingest-validator-service and downstream NER/embedding services

#### Metrics
- Prometheus metrics for all pipeline stages:
  - messages_processed_total
  - messages_accepted_total
  - messages_review_total
  - messages_rejected_total
  - processing_duration_seconds
  - normalization_score_histogram
  - url_canonicalization_errors_total
  - publisher_resolution_errors_total
  - content_normalization_errors_total
  - metadata_enrichment_errors_total
  - domain_classification_errors_total
  - fuzzy_deduplication_errors_total

#### Configuration
- Pydantic settings with nested configuration classes for Kafka, PostgreSQL, Redis, normalization, and service settings
- Support for environment variable configuration
- Configurable thresholds for normalization score acceptance (0.85) and review (0.70)
- Configurable fuzzy deduplication threshold (0.90)

#### Testing
- 61 comprehensive unit tests covering all pipeline components:
  - URL canonicalizer: 11 tests
  - Content normalizer: 11 tests
  - Metadata enricher: 10 tests
  - Domain classifier: 11 tests
  - Fuzzy deduplicator: 8 tests
  - Normalization scorer: 11 tests
- All tests passing with 100% success rate

#### Documentation
- README.md with service overview, setup instructions, configuration, and running instructions
- CHANGELOG.md documenting version 1.0.0 initial release
- TODO.md for future enhancements

### Technical Details

#### Architecture
- Chain of Responsibility Pattern for sequential normalization stages
- Strategy Pattern for pluggable language-specific content cleaners
- Repository Pattern for publisher registry and URL mapping persistence
- Factory Pattern for creating normalization contexts
- Cache-Aside Pattern for Redis caching
- Circuit Breaker Pattern for external dependencies
- Adapter Pattern for Kafka consumer/producer wrappers
- Dependency Injection for configuration and clients

#### Technologies
- Python 3.11 with Pydantic models and pydantic-settings
- Apache Kafka with exactly-once semantics
- Avro schema with Schema Registry
- PostgreSQL with asyncpg for async database operations
- Redis for distributed caching
- Prometheus for metrics collection
- confluent-kafka library for Kafka integration
- MinHash + LSH for fuzzy deduplication
- tldextract for domain parsing
- textstat for readability scoring
- BeautifulSoup4 for HTML parsing
- ftfy for encoding fixes

#### Decision Logic
- NS ≥ 0.85 → Publish to news_canonical
- 0.70 ≤ NS < 0.85 → Publish to news_canonical with quality_flag
- NS < 0.70 → Publish to DLQ

### Known Limitations

- LSH (Locality Sensitive Hashing) implementation uses brute-force comparison for now (will be optimized in future versions)
- Language-specific text processing libraries (hazm, opencc, pyarabic) not yet integrated (planned for v1.1.0)
- No ML-based domain classification (keyword-based only in v1.0.0)
- Publisher credibility scoring uses simple domain-based lookup (will be enhanced with ML in future versions)

### Dependencies

- confluent-kafka>=2.3.0
- pydantic>=2.5.0
- pydantic-settings>=2.1.0
- asyncpg>=0.29.0
- psycopg2-binary>=2.9.9
- redis>=5.0.1
- tldextract>=5.1.1
- ftfy>=6.1.1
- beautifulsoup4>=4.12.2
- datasketch>=1.6.5
- textstat>=0.7.3
- prometheus-client>=0.19.0
- python-ulid>=1.1.0
- pytz>=2023.3

### Configuration Parameters

- KAFKA_BROKERS: 154.53.166.231:9092
- SCHEMA_REGISTRY_URL: http://154.53.166.231:8081
- CONSUMER_GROUP: canonicalizer-service-group
- INPUT_TOPIC: news_validated
- OUTPUT_TOPIC: news_canonical
- DLQ_TOPIC: news_canonical_dlq
- NORMALIZATION_SCORE_ACCEPT: 0.85
- NORMALIZATION_SCORE_REVIEW: 0.70
- FUZZY_DEDUP_THRESHOLD: 0.90
- PROMETHEUS_PORT: 9103

