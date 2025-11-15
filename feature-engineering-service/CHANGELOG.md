# Changelog - Feature Engineering Service

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.12] - 2025-11-15

### Fixed - PostgreSQL Timezone-Aware/Naive Datetime Mismatch
- **Critical Bug Fix** (src/extractors/btc_price_extractor.py)
  - Fixed "can't subtract offset-naive and offset-aware datetimes" PostgreSQL error
  - Added timezone-naive conversion before passing datetime parameters to PostgreSQL queries
  - Updated `_fetch_btc_data()` to convert start_time, end_time, and timestamp to timezone-naive
  - Updated `_fetch_historical_btc_data()` to convert timestamp to timezone-naive
  - Root cause: btc_truth.timestamp column is TIMESTAMP (without timezone), but Python code was passing timezone-aware datetime objects

**Bug Description:**
- BTC price extractor was failing with PostgreSQL error during query execution
- Error: "invalid input for query argument $1: can't subtract offset-naive and offset-aware datetimes"
- Occurred in ORDER BY clause: `ORDER BY ABS(EXTRACT(EPOCH FROM (timestamp - $3)))`
- Python code passed timezone-aware datetime (with tzinfo=UTC) to query
- PostgreSQL btc_truth.timestamp column is TIMESTAMP (timezone-naive)
- PostgreSQL cannot perform arithmetic between timezone-aware and timezone-naive timestamps

**Fix:**
```python
# Convert to timezone-naive for PostgreSQL compatibility
start_time_naive = start_time.replace(tzinfo=None) if start_time.tzinfo else start_time
end_time_naive = end_time.replace(tzinfo=None) if end_time.tzinfo else end_time
timestamp_naive = timestamp.replace(tzinfo=None) if timestamp.tzinfo else timestamp
```

**Result:**
- BTC price queries now execute successfully without timezone errors
- All datetime parameters are converted to timezone-naive before PostgreSQL queries
- Maintains UTC consistency (all datetimes are UTC, just without tzinfo for PostgreSQL)

## [0.3.11] - 2025-11-14

### Fixed - BTC Parquet Generation Never Retries After Initial Failure
- **Critical Bug Fix** (src/service.py)
  - Fixed `_check_and_generate_btc_features()` logic that prevented BTC parquet regeneration
  - Changed condition from "return if None" to "generate if None"
  - Now retries BTC feature generation every hour if initial generation failed

**Bug Description:**
- When database was empty on startup, BTC feature generation failed
- `btc_features_last_generated` remained `None`
- Hourly check incorrectly returned early if `None`, thinking "already generated on startup"
- BTC parquet file was never created, even after BTC data was added to database

**Fix:**
```python
if self.btc_features_last_generated is None:
    # First generation failed or not yet attempted, try now
    await self._generate_btc_features()
    return
```

**Result:**
- BTC features now regenerate every hour until successful
- If database is empty initially, will retry when data becomes available
- Logs "BTC features not yet generated successfully, attempting generation"

## [0.3.10] - 2025-11-14

### Fixed - Re-processing Groups from Database
- **Database Query Enhancement** (src/service.py)
  - Updated `_fetch_group_from_database()` to fetch `countries` column from semantic_groups table
  - Updated `_fetch_group_from_database()` to handle None values for article_ids and countries
  - Ensures re-processed groups have complete data (article_ids, countries)
  - Fixes issue where re-processed groups had 0 articles and no countries

### Fixed - BTC Price Extractor Timezone Issue
- **Timezone Handling** (src/extractors/btc_price_extractor.py)
  - Fixed "can't subtract offset-naive and offset-aware datetimes" error
  - Updated `_get_group_timestamp()` to always return timezone-aware datetime objects
  - Added timezone.utc to naive datetime objects
  - Imported timezone from datetime module

### Changed - Dependency on Clustering Service
- **Requires**: clustering-service v0.8.0 or higher
  - Clustering service now writes article_ids and countries to semantic_groups table
  - Feature-engineering can now re-process groups from database with full context
  - No longer need to query entities or Kafka for countries during re-processing

## [0.3.9] - 2025-11-14

### Added - Event-Driven Reconciliation Updates
- **Reconciliation Consumer** (src/clients/reconciliation_consumer.py)
  - New Kafka consumer for `reconciliation_completed` events from labeler service
  - Consumes events when semantic groups are reconciled with GDELT labels
  - Triggers re-processing of groups to update has_conflict values
  - Runs as background task alongside main semantic_groups consumer

- **Group Re-Processing** (src/service.py)
  - Added `_consume_reconciliation_events()` background task
  - Added `_reprocess_group()` method to re-extract features when reconciliation completes
  - Added `_fetch_group_from_database()` to retrieve group data for re-processing
  - Updates Delta Lake parquet files with correct has_conflict values
  - Runs continuously in background, processing reconciliation events as they arrive

**Why This Matters:**
- **Timing Issue Fixed**: Previously, feature-engineering processed groups BEFORE labeler reconciled them
  - Result: All groups had `has_conflict=None` (unreconciled)
  - Even after labeler reconciled them, parquet files still showed `None`
- **Real-Time Updates**: Now re-processes groups when reconciliation completes
  - Parquet files get updated with correct `has_conflict=True/False` values
  - Training data is always up-to-date with latest reconciliation status
- **Event-Driven Architecture**: No polling, clean separation of concerns

**Data Flow:**
1. Feature-engineering processes semantic group → saves with `has_conflict=None` (unreconciled)
2. Labeler reconciles group with GDELT → publishes reconciliation_completed event
3. Feature-engineering consumes event → re-processes group
4. Queries reconciliation_log → gets updated has_conflict value
5. Updates Delta Lake parquet file with correct has_conflict

**Background Tasks:**
- Main task: Consumes semantic_groups topic (new groups)
- Reconciliation task: Consumes reconciliation_completed topic (updates)
- Both run concurrently, independent of each other

---

## [0.3.8] - 2025-11-14

### Fixed - has_conflict Returns None for Unreconciled Groups
- **Critical fix for ML training** - Modified src/extractors/embedding_extractor.py:
  - Changed `_check_conflict_status()` return type from `bool` to `Optional[bool]`
  - Now returns `None` for unreconciled groups (no GDELT labels) instead of `False`
  - Returns `None` for reconciled groups without GDELT metadata (old data)
  - Only returns `True`/`False` for groups with actual GDELT conflict labels

**Problem Fixed:**
- Previously: Unreconciled groups had `has_conflict=False` (looked like a real label)
- Now: Unreconciled groups have `has_conflict=None` (correctly indicates "not labeled")

**Why This Matters:**
- `False` = "This is a non-conflict event" (a real label from GDELT)
- `None` = "We don't know if this is conflict or not" (not labeled yet)
- Training on `False` values for unreconciled groups creates **label noise**
- ML training should ONLY use groups where `has_conflict` is `True` or `False` (not `None`)

**Behavior:**
- Unreconciled groups (no reconciliation_log entry): `has_conflict=None`
- Reconciled but no GDELT metadata (old data): `has_conflict=None`
- Reconciled with `label_conflict=1`: `has_conflict=True`
- Reconciled with `label_conflict=0`: `has_conflict=False`

**Impact:**
- Parquet files now correctly distinguish labeled vs unlabeled groups
- Training service can filter to only labeled groups (`has_conflict IS NOT NULL`)
- Prediction service can filter to only unlabeled groups (`has_conflict IS NULL`)

---

## [0.3.7] - 2025-11-14

### Changed - Filter Groups Without Countries
- **Added country filter** - Modified src/service.py:
  - Now skips semantic groups that have no countries (empty or whitespace-only)
  - Filter applied after all feature extraction is complete
  - Returns empty features dict to trigger skip logic
  - Rationale: Cannot predict conflicts between countries if no countries are present
  - Reduces dataset size and focuses on geographically-specific events
  - Logs skipped groups with reason: "Skipping semantic group without countries"

**Behavior:**
- Groups with `countries=""` or `countries="   "` are skipped
- Groups with valid countries (e.g., `countries="US,CN"`) are processed normally
- Skipped groups do NOT get written to parquet files or Feast feature store

**Impact:**
- Cleaner training dataset - only groups with country information
- Smaller parquet files - no empty country rows
- Aligns with goal of predicting conflicts between countries

---

## [0.3.6] - 2025-11-14

### Changed - has_conflict Feature Now Detects Actual War/Conflict Events
- **Enhanced conflict detection** - Modified src/extractors/embedding_extractor.py:
  - Changed `_check_conflict_status()` to detect actual war/conflict events using GDELT metadata
  - Now queries ONLY `max_label_conflict` (GDELT conflict indicator)
  - Returns True if any matched GDELT event has `label_conflict=1` (actual war/conflict)
  - Removed data quality check (multiple label_ids) - this is for war detection, not data quality
  - Updated docstring to clarify new behavior
  - Simplified logging to show only max_label_conflict

**Previous Behavior:**
- `has_conflict = True` only when group_id had multiple different label_ids
- This indicated data quality issues (ambiguous labeling), NOT actual conflict events
- Feature name was misleading - sounded like war detection but was actually label ambiguity

**New Behavior:**
- `has_conflict = True` ONLY when any matched GDELT event has `label_conflict=1`
- Purely for war/conflict detection, NOT data quality issues
- Requires labeler service v0.13.0+ with GDELT metadata columns

**GDELT Conflict Indicators:**
- `event_code` in [18, 19, 20, 21, 22, 23] = conflict events (PROTEST → MILITARY_ACTION)
- `goldstein_scale < -2` = negative/conflict events
- `label_conflict = 1` = GDELT's binary conflict classification

**Dependencies:**
- Requires `reconciliation_log` table to have `label_conflict` column (added in labeler v0.13.0)
- Backward compatible: if column doesn't exist, falls back to label_count check only

---

## [0.3.5] - 2025-11-14

### Fixed - Countries Data Source (Read from Kafka Message)
- **Fixed countries extraction** - Modified src/extractors/embedding_extractor.py:
  - Changed countries data source from reconciliation_log database query to semantic_groups Kafka message
  - Removed _fetch_countries_from_reconciliation() method (no longer needed)
  - Countries are now read directly from the message: `group.get("countries", [])`
  - Eliminates race condition where feature-engineering processed messages before reconciliation_log was populated
  - Clustering service already extracts countries from NER entities and includes them in semantic_groups messages
  - No database query needed - faster and more reliable
  - Updated docstring to clarify postgres_client is only used for conflict checking

### Root Cause
- The clustering-semantic-grouping-service extracts countries from NER entities and includes them in the semantic_groups Kafka message (Avro schema field: "countries")
- The labeler-ground-truth-ingest-service also consumes semantic_groups and writes countries to reconciliation_log table
- Both services consume from the same topic in parallel, creating a race condition
- Feature-engineering-service was querying reconciliation_log instead of reading from the message
- This caused empty countries when feature-engineering processed messages before labeler wrote to the database

### Solution
- Read countries directly from the semantic_groups Kafka message (source of truth)
- No dependency on reconciliation_log timing
- No race condition
- Simpler and faster (no database query)

## [0.3.4] - 2025-11-14

### Fixed - Async Migration and Connection Pool Implementation
- **Migrated PostgresClient to asyncpg** - Modified src/clients/postgres_client.py:
  - Replaced psycopg2 (synchronous) with asyncpg (asynchronous)
  - Changed from single connection to connection pool (min_size=2, max_size=10)
  - Converted all methods to async: connect(), get_actors_by_ids(), get_actor_by_id(), get_articles_by_ids(), get_all_actors(), execute_query(), close()
  - Changed SQL placeholders from %s to $1, $2, etc. (asyncpg format)
  - Added proper connection pool management with automatic reconnection
  - Fixed "connection already closed" errors that were occurring in extractors
- **Updated EmbeddingExtractor** - Modified src/extractors/embedding_extractor.py:
  - Made extract() method async
  - Made _fetch_countries_from_reconciliation() async with await
  - Made _check_conflict_status() async with await
  - Updated SQL placeholders from %s to $1
  - Changed execute_query_sync() calls to execute_query() with await
- **Updated BtcPriceExtractor** - Modified src/extractors/btc_price_extractor.py:
  - Made extract() method async
  - Made _fetch_btc_data() async with await
  - Made _fetch_historical_btc_data() async with await
  - Made generate_historical_btc_features() async with await
  - Updated SQL placeholders from %s to $1, $2, etc.
  - Changed execute_query_sync() calls to execute_query() with await
- **Updated FeatureExtractor base class** - Modified src/extractors/base.py:
  - Changed extract() abstract method signature to async
  - All extractors now inherit async pattern
- **Updated all other extractors** - Modified src/extractors/:
  - SourceExtractor: Made extract() method async
  - TemporalExtractor: Made extract() method async
  - SentimentExtractor: Made extract() method async
  - EntityExtractor: Made extract() method async
  - ContentExtractor: Made extract() method async
- **Updated FeatureEngineeringService** - Modified src/service.py:
  - Made start() method async with await for postgres_client.connect()
  - Made _consume_loop() method async
  - Made _process_message() method async
  - Made _extract_features() method async with await for extractor.extract()
  - Made _check_and_generate_btc_features() method async
  - Made _generate_btc_features() method async with await
  - Made shutdown() method async with await for postgres_client.close()
- **Updated main entry point** - Modified src/main.py:
  - Added asyncio import
  - Created async_main() async function
  - Updated main() to use asyncio.run(async_main())
  - Service now runs in async event loop
- **Testing and Verification**:
  - Service restarted successfully with no connection errors
  - PostgreSQL connection pool established successfully
  - BTC features generated successfully (1000 records)
  - No "connection already closed" errors in logs
  - All connections established and service running correctly

### Root Cause Fixed
- **Original Problem**: "connection already closed" InterfaceError in embedding_extractor and btc_price_extractor
- **Root Cause**: Single psycopg2 connection shared across multiple extractors with no connection pooling or reconnection logic
- **Solution**: Migrated to asyncpg with connection pooling, automatic reconnection, and proper async/await pattern throughout the service

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

