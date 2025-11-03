# Sentiment Analyzer v2 - Changelog

All notable changes to the Sentiment Analyzer v2 project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-11-03

### Added

#### Phase 1: Data Collection & Validation (Initial Implementation)

**Crawler Service (crawler-service)**
- RSS and HTML feed parsers for 8 news sources
- Support for CNN, BBC, Reuters, Al Jazeera, Xinhua, RT, Tasnim, ISNA
- Kafka producer with Avro schema validation
- Feed registry and scheduling system for periodic crawling
- Language detection with FastText
- Deduplication using MinHash and cosine similarity
- Prometheus metrics and health check endpoints
- Docker and Kubernetes deployment configurations
- Helm charts for production deployment
- Comprehensive test suite (unit, integration, contract, performance)

**Ingest Validator Service (ingest-validator-service)**
- Multi-stage validation pipeline for news articles
- Schema validation with Avro schema registry compatibility
- Language detection with FastText, LangDetect, and Transformer strategies
- UTF-8 encoding validation and normalization
- Timestamp validation and UTC conversion
- Geographic information extraction and validation
- Quality scoring with configurable thresholds
- Duplicate detection using MinHash and cosine similarity
- Source reliability verification
- Comprehensive audit logging and error tracking
- Circuit breaker and backpressure handling for resilience
- Redis caching for performance optimization
- Kafka consumer/producer integration
- Prometheus metrics and health check endpoints
- Docker and Kubernetes deployment configurations
- Helm charts for production deployment
- Extensive test suite (unit, integration, contract, performance)

#### Phase 2: Semantic Grouping (Initial Implementation)

**Canonicalizer-Normalizer Service (canonicalizer-normalizer-service)**
- Canonical URL normalization with redirect resolution
- Advanced deduplication with fuzzy matching and similarity scoring
- Publisher ID enrichment and resolution
- Content normalization for multilingual text
- Domain classification and language-specific processing
- Metadata enrichment with geographic and source information
- Batch processing for high-throughput scenarios
- Redis caching for performance optimization
- PostgreSQL mapping for canonical URL tracking
- Kafka consumer/producer integration
- Analytics engine for deduplication metrics
- REST API for manual URL canonicalization
- Security scanning for malicious URLs
- Structured logging and distributed tracing
- Prometheus metrics and health check endpoints
- Docker and Kubernetes deployment configurations
- Helm charts for production deployment
- Comprehensive test suite (unit, integration, performance)

### Infrastructure

- Monorepo structure with 12 microservices
- Shared schemas directory with Avro schemas
- Kubernetes manifests with Kustomize overlays (dev, staging, prod)
- Helm charts for each service
- Docker Compose for local development
- GitHub Actions CI/CD workflows
- Prometheus monitoring configuration
- Professional Git workflow with branch protection rules
- Comprehensive .gitignore configuration

### Documentation

- GIT.md: Complete Git workflow and versioning guide
- Architecture.md: System architecture and data flow
- Microservice.md: Service specifications and responsibilities
- Task.md: Project requirements and phases
- Service-specific README.md and CHANGELOG.md files

## [Unreleased]

Future releases will include:
- Phase 3: Feature Engineering & Model Training
- Phase 4: Graph Building with Neo4j
- Phase 5: REST API for Analysis
- Phase 6: Production Deployment & Monitoring

