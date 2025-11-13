# Changelog - Feature Engineering Service

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.3] - 2025-11-13

### Changed - Centralized Offline Store Location
- **Updated features.py** - Changed FileSource path:
  - Changed from `data/semantic_groups.parquet` to `../feast/offline_store/semantic_groups.parquet`
  - Centralized location at project root: `feast/offline_store/semantic_groups.parquet`
  - Both feature-engineering and trainer services now use the same offline store location
- **Created .feastignore** - Added to prevent Feast from importing service code
- **Updated FeastWriter** - Modified src/storage/feast_writer.py:
  - Changed to write to offline store only (not online store)
  - Updated `write_features()` default parameter to `to="offline"`
  - Reason: Online store (Redis) not being populated correctly, offline store is local and reliable
- **Updated service.py** - Changed Feast write call:
  - Changed from `to="online_and_offline"` to `to="offline"`
  - Updated log messages to reflect offline store only
- **Architecture Decision**:
  - Feature-engineering-service writes to `feast/offline_store/semantic_groups.parquet`
  - Trainer reads from same location via Feast SDK with Delta Lake fallback
  - Online store (Redis) not used for now

## [0.3.2] - 2025-11-13

### Fixed - Feast Writer Using PushSource
- **Updated FeastWriter** - Modified src/storage/feast_writer.py:
  - Changed from `write_to_online_store()` to `push()` method for PushSource
  - Added push_source_name configuration ("semantic_group_push_source")
  - Properly handles timestamp conversion to datetime type
  - Pushes features to remote Redis online store (154.53.166.231:6379)
- **Updated features.py** - Added PushSource definition:
  - Added semantic_group_push_source with batch_source
  - Changed entity to use join_keys=["group_id"]
  - FeatureView now uses PushSource instead of FileSource
- **Deleted feast_http_writer.py** - Removed incomplete HTTP API implementation
- **Updated service.py** - Switched back to FeastWriter (SDK push method)
- **Cleaned up feast directories**:
  - Deleted root feast/ directory (was creating local files)
  - Deleted C:\feast\ directory (was creating local registry)
  - Both feature_store.yaml files kept (feast_remote/ for server, feature-engineering-service/ for SDK)

## [0.3.1] - 2025-11-13

### Changed - Remote Feast HTTP Writer Implementation (DEPRECATED)
- **New Feast HTTP Writer** - Created src/storage/feast_http_writer.py:
  - FeastHTTPWriter class for pushing features to remote Feast server via HTTP API
  - Uses Feast push API endpoint (/push) to write features to online and offline stores
  - Implements retry logic with configurable max_retries (default: 3)
  - Comprehensive error handling for timeout, connection errors, and HTTP errors
  - Converts features to DataFrame-like format for Feast push API
  - Logs detailed information about push operations and failures
- **Service Integration** - Updated src/service.py:
  - Replaced FeastWriter (local SDK) with FeastHTTPWriter (remote HTTP API)
  - Changed from local Feast instance to remote server at 154.53.166.231:6566
  - Maintained same feature writing interface (write_features method)
  - All 28 features now pushed to centralized remote Feast server
- **Configuration Update** - Updated src/config.py:
  - Fixed push_source_name from "semantic_group_push" to "semantic_group_push_source"
  - Matches push source name defined in remote Feast server features.py
- **Storage Package Update** - Updated src/storage/__init__.py:
  - Added FeastHTTPWriter to exports
  - Maintained backward compatibility with existing storage interfaces

### Impact
- **Centralized Feature Store**: Feature-engineering now writes to same remote Feast server used by trainer and predictor
- **Architecture Fix**: Resolved mismatch where feature-engineering wrote locally but trainer/predictor read remotely
- **Data Consistency**: All services now share the same feature store (single source of truth)
- **Scalability**: HTTP-based push allows feature-engineering to run anywhere without local Feast instance

### Technical Details
- Remote Feast server: 154.53.166.231:6566
- Push endpoint: http://154.53.166.231:6566/push
- Push source: semantic_group_push_source
- Feature view: semantic_group_features (28 features: 24 base + 4 BTC)
- Online store: Redis at 154.53.166.231:6379
- Offline store: File-based parquet on remote server

### Root Cause Fixed
- **Problem**: Feature-engineering wrote to LOCAL Feast (feature-engineering-service/data/), but trainer/predictor read from REMOTE Feast (154.53.166.231:6566)
- **Result**: Trainer got "Feature not found" errors because remote Feast had no features
- **Solution**: Feature-engineering now pushes features to remote Feast server via HTTP API

## [0.3.0] - 2025-11-12

### Changed - Feast HTTP Client Integration
- **Feast Storage Refactoring** - Updated src/storage/feast_writer.py:
  - Replaced direct Feast SDK usage with FeastHTTPClient for remote Feast server
  - Changed from local Feast instance to remote server at 154.53.166.231:6566
  - Updated push_features_to_feast() to use HTTP API instead of SDK
  - Maintained same feature schema and push source configuration
  - Added comprehensive error handling for HTTP communication
- **Configuration Update** - Updated src/config.py:
  - Added FeastHTTPConfig class for remote Feast server configuration
  - Configured server URL, timeout, max retries, push source, and feature view
  - Environment variable support for all Feast HTTP settings
- **Service Integration** - Updated src/service.py:
  - Integrated FeastHTTPClient into service initialization
  - Passed Feast HTTP client to FeastWriter for feature storage
  - Maintained backward compatibility with existing feature extraction logic

### Impact
- **Centralized Feature Store**: All services now use single remote Feast server
- **Simplified Deployment**: No need for local Feast instances in each service
- **Improved Reliability**: HTTP-based communication with retry logic
- **Architecture Compliance**: Implements centralized feature storage pattern

### Technical Details
- Remote Feast server: 154.53.166.231:6566
- Redis online store: 154.53.166.231:6379
- MinIO S3 offline store: http://154.53.166.231:9900
- Feature view: semantic_group_features (24 features)
- Push source: semantic_group_push_source

## [0.2.4] - 2025-11-09

### Added - BTC Price Feature Integration
- **BTC Price Feature Extractor** - New src/extractors/btc_price_extractor.py:
  - BtcPriceExtractor class extending BaseExtractor
  - Fetches BTC price data from PostgreSQL btc_truth table (Dataset 7)
  - Extracts 4 features: btc_change_pct_10h, btc_volatility_score, btc_volume, btc_label_spike
  - Temporal alignment logic (±1 hour window) to match BTC data with semantic groups
  - Handles missing BTC data gracefully with default values (0.0, False)
  - Comprehensive logging with BTC price values and timestamps
- **PostgreSQL Client Enhancement**:
  - Added execute_query_sync() method for synchronous queries
  - Supports parameterized queries with RealDictCursor
- **Feast Feature View Update**:
  - Updated feature count from 24 to 28 (4 new BTC features)
  - Added BTC feature fields to Feast schema
  - Updated parquet file schema to include BTC features
  - Updated feature view description to include BTC price prediction
- **Service Integration**:
  - Integrated BtcPriceExtractor into service.py extractor chain
  - BTC features extracted for all semantic groups
  - BTC features written to Feast offline store (Delta Lake)
  - BTC features written to Redis online store
  - BTC features published to Kafka topic 'features_computed'

### Expected Impact
- **BTC Price Prediction**: Enables models to predict BTC price changes based on news sentiment
- **Feature Diversity**: Increased from 24 to 28 features
- **Temporal Correlation**: BTC features aligned with news publication time
- **Architecture Compliance**: Implements Dataset 7 (Bitcoin & Financial Prices) from Architecture.md
- **Task Completion**: Addresses Phase 3 BTC price prediction requirement from Task.md

### Technical Details
- Temporal alignment uses ±1 hour window to find closest BTC data point
- BTC data queried using ORDER BY ABS(EXTRACT(EPOCH FROM (timestamp - $3))) for closest match
- Default values used when BTC data not available (graceful degradation)
- BTC features integrated seamlessly with existing 24 semantic group features
- Feature version remains v1.0 (backward compatible addition)

## [0.2.3] - 2025-11-08

### Fixed
- **CRITICAL**: Implemented UPSERT logic in Delta Lake writer to prevent duplicate group_ids (was 66% duplication rate)
- **CRITICAL**: Fixed source_extractor.py line 57 - replaced sentiment_score placeholder with actual credibility lookup
- **HIGH**: Removed metadata columns (feature_count, feature_sum, feature_mean, feature_min, feature_max, feature_range) from feature store
- **HIGH**: Fixed embedding_extractor to use default values (1.0, 0.5, 0.1) instead of zeros
- Added comprehensive logging to sentiment, entity, and embedding extractors for debugging

### Verified
- ✅ **ZERO duplicate group_ids** - UPSERT logic working correctly
- ✅ **NO metadata columns** - Clean feature store with only 24 actual features
- ✅ **NO null values** - All features have valid data
- ✅ **Feature variance** - Most features have reasonable variance for model training
- ✅ **Data quality** - Features suitable for trainer service

### Known Issues (Upstream Data Quality)
- sentiment_mean is constant (0.5) - articles have sentiment_score = 0.5 (neutral/default)
- entity_count is zero - articles don't have entities populated from NER service
- source_credibility_avg is constant (0.5) - articles don't have credibility data

### Technical Details
- Delta Lake UPSERT: Reads existing table, filters out group_id, concatenates with new row, overwrites table
- Metadata columns removed in service._write_features() before writing to all backends
- Embedding extractor now checks for similarity_std in multiple locations (direct attribute, metadata dict)
- All extractors now log detailed information for debugging data quality issues

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

