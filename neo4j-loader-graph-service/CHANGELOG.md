# Changelog

All notable changes to the Neo4j Loader Graph Service will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Fixed Avro deserialization by migrating from old AvroConsumer API to new Consumer + AvroDeserializer pattern
- Updated all ID validation to accept both ULIDs (26 chars) and UUIDs (36 chars) for compatibility with upstream services
- Fixed Article, Group, and Entity models to accept both ULID and UUID formats
- Fixed message_validator.py to validate both ULID and UUID formats for article_id and group_id
- Added debug logging to Kafka consumer for better observability
- Fixed Windows signal handling for graceful shutdown
- Fixed missing configuration fields (service_version, environment)
- Fixed Neo4j connection configuration
- Fixed message handler registration for all topics
- Fixed handler signature to pass topic, message, and trace_id
- Fixed Pydantic v2 protected namespace warning in Prediction model
- Added missing graph_clusters_detected metric
- Fixed publisher_id validation to only accept valid 26-character ULIDs, set to None for invalid values
- Added comprehensive debug logging for entity validation to identify data structure issues
- Fixed entity field name mapping: upstream sends "text" and "entity_type", mapped to "name" and "type" in Entity model
- Updated message_validator.py to check for correct upstream field names: "text" and "entity_type" instead of "name" and "type"
- Added entity type mapping in Entity.from_kafka_message() to handle upstream entity types (PERSON, ORGANIZATION, LOCATION)

### Added
- Initial project structure and foundation
- TODO.md with 145+ enumerated tasks
- CHANGELOG.md skeleton
- Configuration management with Pydantic Settings (50+ environment variables)
- Custom exception hierarchy (10 exception classes)
- Prometheus metrics (30+ metrics)
- Neo4j client with connection pooling and retry logic
- Schema manager with 5 unique constraints and 10 indexes
- Pydantic models for 5 node types (Article, Group, Entity, Actor, Prediction)
- Pydantic models for 6 relationship types
- Kafka consumer for 4 topics with Avro deserialization
- Message validator with topic-specific validation
- Message router for handling Kafka messages
- Node builder with MERGE logic and conflict resolution
- Relationship builder for all 6 relationship types
- Batch loader with UNWIND batching (1000 nodes/batch)
- Stream loader with buffering (100-message buffer, 5s flush)
- Centrality computer (degree, betweenness, closeness)
- Clustering detector using Louvain algorithm
- Graph validator with orphan detection and constraint checking
- Query repository with 8+ parameterized queries
- Service orchestrator with lifecycle management
- Main entry point with structured logging
- Dockerfile with multi-stage build
- docker-compose.yml with all dependencies
- .dockerignore and .env.example
- Comprehensive README.md with setup and troubleshooting

- PostgreSQL client with lineage tracking and snapshot retrieval
- Snapshot manager with snapshot creation, comparison, and cleanup
- Backup manager with neo4j-admin dump/restore
- Kafka producer for graph_updated events with Avro serialization
- Circuit breaker pattern for fault tolerance
- Token bucket rate limiter for backpressure management
- Graph metrics calculator for node/relationship counts and density

### In Progress
- OpenTelemetry tracing integration
- Test suite (unit, integration, contract, performance tests)
- TLS configuration
- Alerting rules documentation
- S3/MinIO storage for backups
- Redis query caching
- Dead-letter queue for failed messages

## [1.0.0] - TBD

### Added
- Graph schema management for 5 node types (Article, Group, Entity, Actor, Prediction)
- Graph schema management for 6 relationship types (MENTIONS, BELONGS_TO, RELATED_TO, INVOLVES, PREDICTS, REFERENCES)
- Neo4j client with connection pooling, sessions, transactions, and retry logic
- Kafka consumer for 4 topics (semantic_groups, entities_extracted, predictions, news_canonical)
- Avro deserialization with schema registry integration
- Batch loader with UNWIND batching (1000 nodes/batch)
- Stream loader with 100-message buffer for real-time updates
- Node builders for all 5 node types
- Relationship builders for all 6 relationship types
- Conflict resolution with last-write-wins strategy
- Centrality computation (degree, betweenness, closeness)
- Clustering detection using Louvain algorithm
- Graph validation and orphan detection
- Optimized Cypher queries for origin tracing and network analysis
- Daily PostgreSQL snapshots with validation
- Neo4j backup and restore functionality
- PostgreSQL integration for metadata and audit logging
- Kafka producer for graph_updated events
- Service orchestration with health endpoints
- OpenTelemetry tracing with Jaeger exporter
- Structured JSON logging with trace_id propagation
- Comprehensive test suite (≥90% coverage)
- Dockerfile with multi-stage build
- docker-compose.dev.yml for local development
- Prometheus metrics (9 metrics)
- Alerting rules documentation

### Performance
- ≥1000 nodes/sec batch loading throughput
- <1s streaming update latency
- <0.5% write failure rate
- Query p95 latency <1s
- Centrality computation <10min for 100k nodes
- Clustering detection <15min for 100k nodes
- Daily snapshots <10min

### Security
- TLS configuration for Kafka and Neo4j
- PostgreSQL SSL mode
- No hardcoded credentials
- All secrets via environment variables

### Monitoring
- 9 Prometheus metrics exposed on :9110/metrics
- 5 alerting rules configured
- OpenTelemetry distributed tracing
- Structured logging with correlation IDs

### Quality
- Zero static analysis violations (ruff, black, mypy, bandit)
- ≥90% unit test coverage
- Integration tests with testcontainers
- Contract tests for Avro schemas
- Performance tests validated
- Zero orphaned nodes
- Zero hardcoded queries
- No TODO placeholders in code

## Version History

### Milestone 1: Foundation (Phase 1)
- Project structure established
- Core configuration and utilities

### Milestone 2: Graph Schema (Phase 2)
- Neo4j client and schema manager
- Data models for all node and relationship types

### Milestone 3: Data Ingestion (Phases 3-5)
- Kafka consumer with Avro support
- Node and relationship builders
- Conflict resolution

### Milestone 4: Graph Operations (Phases 6-8)
- Batch and stream loading
- Graph metrics computation
- Validation and integrity checks

### Milestone 5: Query & Storage (Phases 9-11)
- Optimized Cypher queries
- Snapshot and backup management
- PostgreSQL integration

### Milestone 6: Integration (Phases 12-14)
- Kafka producer for events
- Service orchestration
- Observability stack

### Milestone 7: Quality & Deployment (Phases 15-17)
- Comprehensive testing
- Deployment artifacts
- Production readiness validation

---

**Maintainer:** Neo4j Loader Graph Service Team
**Last Updated:** 2025-11-08

