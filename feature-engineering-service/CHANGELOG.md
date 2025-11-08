# Changelog - Feature Engineering Service

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.2] - 2025-11-08

### Fixed
- **CRITICAL**: Fixed push_source_name parameter in feast_client.py (was incorrectly using feature_view_name)
- **CRITICAL**: Fixed Entity definition with join_keys parameter for proper entity column recognition
- **CRITICAL**: Fixed Redis connection string format (removed redis:// prefix for Feast compatibility)
- Delta Lake schema mismatch now handled with automatic table recreation
- Entity extractor warning changed to debug level (no entities is valid case for some groups)

### Verified
- ✅ All 24 features extracted successfully from semantic groups
- ✅ Features transformed and normalized correctly
- ✅ Features validated with no quality issues
- ✅ Features written to Delta Lake offline store
- ✅ Features written to Feast offline store via push method
- ✅ Features written to Redis online store
- ✅ Features published to Kafka topic 'features_computed'
- ✅ End-to-end pipeline working without errors or warnings

### Technical Details
- Entity.join_keys parameter specifies which columns are entity keys for Redis serialization
- Feast Redis online store expects connection_string without redis:// protocol prefix
- PushSource requires proper entity column definition for online store writes
- All 24 features now successfully persisted across all backends (Delta Lake, Feast, Redis)

## [0.2.1] - 2025-11-08

### Fixed
- PushSource batch_source now uses FileSource with minimal parquet file (Feast 0.37.1 compatibility)
- FeatureView schema parameter changed from 'features' to 'schema' (Feast 0.37.1 API)
- Field dtype now uses correct Feast types (String, UnixTimestamp, Int32, Float32)
- Registry logging fixed to handle entity string representation
- Feast registry initialization now completes successfully without errors
- Service successfully registers semantic_group_features view on startup

### Technical Details
- Created minimal parquet file with all 24 feature columns for FileSource batch_source
- Feast 0.37.1 requires explicit schema definition in FeatureView
- PushSource requires valid DataSource for batch_source (cannot be None)
- Entity mismatch warning is expected for PushSource-based feature views

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

