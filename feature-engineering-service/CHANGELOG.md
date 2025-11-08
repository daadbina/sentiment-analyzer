# Changelog - Feature Engineering Service

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-11-08

### Added
- Feast registry management (feast/registry.py) for feature view registration
- Feast feature definitions (feast/feature_definitions.py) with all 24 features
- Delta Lake writer (storage/delta_writer.py) for explicit offline feature storage
- Actual Feast write_features() implementation using pandas DataFrames
- Actual Feast get_features() implementation with historical retrieval
- Feature view registration on service startup
- Health check and feature view validation methods to FeastClient
- Comprehensive logging for all Feast operations including data types and statistics

### Changed
- FeastClient.write_features() now writes to Delta Lake via Feast push method
- FeastClient.get_features() now retrieves from Feast offline store with proper entity handling
- Service initialization now includes Feast registry setup
- _write_features() now writes to Delta Lake, Feast, and Redis in sequence

### Fixed
- Feast feature view not being registered in registry
- Placeholder implementations in FeastClient replaced with actual Feast operations
- Missing Delta Lake backend for offline feature storage
- Feature-engineering-service not actually persisting features to Feast

## [0.1.0] - 2025-11-04

### Added
- Initial project setup with directory structure
- Configuration management with environment variables
- Custom exception hierarchy for error handling
- Prometheus metrics for monitoring
- Distributed tracing with OpenTelemetry
- Feature versioning and checksum utilities
- Kafka consumer with exactly-once semantics
- Kafka producer with Avro serialization
- PostgreSQL client for actor data retrieval
- Redis client for online feature store
- Feast client for offline feature store
- 6 feature extractors computing 24 features across 6 categories
- Feature aggregator and normalizer transformers
- Feature validator with quality checks
- Drift detection with KS and Jensen-Shannon tests
- Feast integration with Delta Lake offline store
- Redis integration for online feature store
- Offline-online reconciliation
- Main service orchestrator with Chain of Responsibility pattern
- Comprehensive unit tests for all components
- Integration tests with Feast, Redis, PostgreSQL
- INTEGRATION.md with service contracts and data schemas
- README.md with quick start guide
- Kubernetes deployment manifests
- Helm charts for production deployment
- Prometheus alerting rules

### Changed
- N/A

### Fixed
- N/A

### Deprecated
- N/A

### Removed
- N/A

### Security
- Non-root container user (featureeng)
- Read-only root filesystem
- No privilege escalation
- Dropped all Linux capabilities

---

## Implementation Notes

### Design Patterns Used
1. **Strategy Pattern**: Pluggable feature extractors per domain
2. **Factory Pattern**: Feature computation pipeline creation
3. **Observer Pattern**: Feature quality monitoring
4. **Template Method Pattern**: Feature computation skeleton
5. **Repository Pattern**: Feast operations abstraction
6. **Adapter Pattern**: Feast and Redis client wrapping
7. **Chain of Responsibility Pattern**: Feature validation stages
8. **Outbox Pattern**: Atomic Feast + Redis writes

### Feature Categories
- **Source Features** (4): num_sources, credibility metrics, diversity
- **Temporal Features** (4): time_span, velocity, concentration, days_since
- **Sentiment Features** (4): mean, std, polarity_ratio, volatility
- **Entity Features** (4): count, diversity, prominence, concentration
- **Content Features** (4): word_count, title_length, language_diversity, domain_diversity
- **Embedding Features** (4): centroid_magnitude, similarity metrics, drift_score

### Integration Points
- **Input**: Kafka `semantic_groups`, PostgreSQL `actors`, Qdrant embeddings
- **Output**: Kafka `features_computed`, Feast offline (Delta Lake), Redis online
- **Storage**: PostgreSQL feature metadata and lineage

### Non-Functional Requirements
- Availability: ≥99.5% monthly
- Feature Latency: ≤5 seconds per group
- Throughput: ≥100 groups/minute per replica
- Message Delivery: Exactly-once
- Offline-Online Consistency: ≥99%
- Memory: ≤2 GB per replica
- Consumer Lag: ≤60 seconds

---

**Last Updated**: 2025-11-04  
**Version**: 0.1.0 (In Development)  
**Maintainer**: Feature Engineering Service Team

