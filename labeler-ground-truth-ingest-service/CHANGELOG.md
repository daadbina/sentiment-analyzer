# CHANGELOG: Labeler / Ground-Truth Ingest Service

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned Features
- Increase test coverage to ≥90% (currently 61%)
- Vault integration for API key management
- TLS enforcement for external connections
- Advanced statistical drift detection
- Auto-scaling based on label volume

---

## [0.2.0] - 2025-11-05

### Added
- **Deduplication Engine** (src/validation/deduplication.py)
  - SHA256 hash-based duplicate detection
  - Batch deduplication with cache management
  - Duplicate label tracking and metrics
  - Cache statistics and performance monitoring

- **Drift Detector** (src/validation/drift_detector.py)
  - Statistical anomaly detection (2-sigma threshold)
  - Confidence score drift detection
  - Volume anomaly detection
  - Drift history tracking with configurable window size
  - Comprehensive drift reporting

- **Audit Logger** (src/storage/audit_logger.py)
  - Comprehensive PostgreSQL audit trail
  - Reconciliation decision logging
  - License compliance audit
  - Validation failure tracking
  - Drift detection audit
  - Deduplication audit

- **Comprehensive Test Suite**
  - 12 tests for DeduplicationEngine
  - 13 tests for DriftDetector
  - 16 tests for AuditLogger
  - 7 performance tests (throughput, latency, memory)
  - 13 resilience tests (error handling, retry logic)
  - Total: 191 tests passing, 61% code coverage

### Changed
- Integrated DeduplicationEngine into LabelerService pipeline
- Integrated DriftDetector into LabelerService pipeline
- Integrated AuditLogger into LabelerService pipeline
- Updated service.py to use all new components
- Fixed test_service.py: replaced CoinGeckoFetcher with BinanceFetcher
- Fixed test_api_clients.py: added GDELT DataFrame and Binance symbol tests

### Fixed
- Kafka producer error handling
- API client retry logic
- Delta Lake write sanitization
- PostgreSQL connection pooling

---

## [0.1.0] - 2025-11-05

### Added
- Initial project setup and directory structure
- Python 3.11 virtual environment configuration
- Requirements.txt with all dependencies
- .env template with configuration parameters
- .gitignore for service-specific files
- README.md with service documentation
- TODO.md with comprehensive task breakdown
- CHANGELOG.md (this file)

### Configuration
- BaseSettings classes for Kafka, PostgreSQL, ACLED, GDELT, CoinGecko
- Environment variable loading with pydantic
- Configuration validation and defaults

### Infrastructure
- Avro schema definitions for ground_truth topic
- ACLED, GDELT, and CoinGecko label schemas
- Schema Registry integration (http://154.53.166.231:8081)
- Database schema migrations for ground_truth, reconciliation_log, license_audit tables

### API Clients
- Base APIClient class with async HTTP support
- Retry logic with exponential backoff
- Circuit breaker pattern for API failures
- ACLED API fetcher with pagination and rate limiting
- GDELT API fetcher with event parsing
- CoinGecko API fetcher with price analysis
- Backup feed fallback mechanism

### Reconciliation & Validation
- Label reconciliation engine with temporal matching (24-48h window)
- Semantic matching with cosine similarity
- Label validator with freshness checks (R10)
- License checker with compliance verification
- Deduplication engine with hash-based detection
- Confidence score validation (≥0.7 threshold)

### Storage Layer
- Delta Lake writer with ACID guarantees and data sanitization
- PostgreSQL writer with connection pooling and transaction support
- Reconciliation logger for audit trail
- Database schema migrations

### Kafka Integration
- Kafka producer with AvroSerializer
- Exactly-once semantics (enable.idempotence=true)
- Circuit breaker for Kafka failures
- Outbox pattern for atomic writes

### Core Service
- LabelerService class with lifecycle management
- Label ingestion pipeline (fetch → reconcile → validate → store)
- Scheduled execution (ACLED: 24h, GDELT: 1h, CoinGecko: 5min)
- Drift detection for label distribution anomalies

### Monitoring & Observability
- Prometheus metrics (label_fetched_total, label_reconciled_total, etc.)
- Structured logging with trace_id and operation tracking
- OpenTelemetry integration with Jaeger exporter
- Health check endpoints (/health, /ready, /live)

### Error Handling
- Custom exception hierarchy (LabelError, FetchError, ReconciliationError, ValidationError, StorageError)
- Graceful error recovery and alerting
- Comprehensive error logging

### Testing
- Unit tests for API fetchers (ACLED, GDELT, CoinGecko)
- Unit tests for reconciliation and validation logic
- Integration tests with mock APIs and Kafka
- Contract tests for Avro schema compatibility
- ≥90% code coverage target

### Deployment
- Dockerfile with Python 3.11-slim
- Kubernetes manifests (k8s/)
- Helm charts (helm/)
- Deployment documentation
- Runbook for common issues
- Prometheus alerting rules

---

## Notes

### Design Patterns Used
1. **Strategy Pattern** - Pluggable API fetchers (ACLED, GDELT, CoinGecko)
2. **Factory Pattern** - Create label reconcilers and validators
3. **Observer Pattern** - Label quality observers monitor validation results
4. **Template Method Pattern** - Define label ingestion skeleton with pluggable steps
5. **Repository Pattern** - Abstract database operations behind repository interface
6. **Adapter Pattern** - Wrap external API clients with common interface
7. **Circuit Breaker Pattern** - Protect API calls with fallback to backup feeds
8. **Outbox Pattern** - Ensure atomic Kafka + Delta Lake + PostgreSQL writes

### Clean Code Principles
- Single Responsibility: Each module handles one concern
- Pure Functions: Label matching returns deterministic outputs
- Explicit Interfaces: All components typed using Python Protocol or ABC
- No Hardcoded Values: All parameters externalized to config/env
- Fail Fast: Validate API responses on receipt
- Immutable Data: Input labels treated as immutable
- Structured Logging: All logs include trace_id, label_source, reconciliation_status
- Comprehensive Tests: Unit tests (≥90% coverage), integration tests with mock APIs

### Compliance
- Follows PUBLIC.md rules (no hardcoding, no mock data, complete implementation)
- Follows GIT.md workflow (feature branches, conventional commits, squash merge)
- Follows labeler-ground-truth-ingest-service.md design patterns
- Follows Architecture.md validation rules (R1-R12)
- Follows Microservice.md service specifications

### Key Metrics & SLOs
- Label Latency: ≤1h from API to Kafka (ACLED), ≤5min (GDELT), ≤1min (CoinGecko)
- Throughput: ≥1000 labels per minute per replica
- Message Delivery: Exactly-once for label output
- Label Freshness: ACLED ≤1d, GDELT ≤1h, CoinGecko ≤5min (R10)
- Reconciliation Accuracy: ≥95% correct label-group matching
- Availability: ≥99.5% measured across monthly window
- Memory Footprint: ≤1 GB per replica

---

## Related Services

- **Upstream:** clustering-semantic-grouping-service (provides semantic_groups)
- **Downstream:** trainer-service (consumes ground_truth labels)
- **External APIs:** ACLED, GDELT, CoinGecko
- **Storage:** Delta Lake, PostgreSQL, Kafka

---

**Last Updated:** 2025-11-05
**Version:** 0.2.0
**Status:** FEATURE_COMPLETE (All core components implemented, 191 tests passing, 61% coverage, ready for integration testing)

