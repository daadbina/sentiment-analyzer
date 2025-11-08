# Neo4j Loader Graph Service

A high-performance microservice for loading and managing graph data in Neo4j, part of the Sentiment Analyzer v2 system.

## Overview

The Neo4j Loader Graph Service is responsible for:
- Consuming messages from Kafka topics (semantic_groups, entities_extracted, predictions, news_canonical)
- Building and loading graph nodes (Article, Group, Entity, Actor, Prediction) and relationships
- Computing graph analytics (centrality, clustering)
- Validating graph integrity
- Providing query interfaces for graph data

## Features

- **High Throughput**: ≥1000 nodes/sec with batch processing (UNWIND)
- **Low Latency**: <1s streaming latency with buffered ingestion
- **Graph Analytics**: Centrality computation (degree, betweenness, closeness) and Louvain clustering
- **Data Quality**: Comprehensive validation with orphan detection and constraint checking
- **Observability**: OpenTelemetry tracing, Prometheus metrics, structured JSON logging
- **Reliability**: Circuit breaker pattern, retry logic, last-write-wins conflict resolution
- **Clean Code**: Single Responsibility, Pure Functions, Explicit Interfaces, ≥90% test coverage

## Architecture

### Node Types
- **Article**: News articles with metadata
- **Group**: Semantic topic clusters
- **Entity**: Named entities (PERSON, ORGANIZATION, LOCATION, etc.)
- **Actor**: Key actors in events
- **Prediction**: ML predictions for groups

### Relationship Types
- **MENTIONS**: Article → Entity
- **BELONGS_TO**: Article → Group
- **RELATED_TO**: Group → Group
- **INVOLVES**: Group → Actor
- **PREDICTS**: Prediction → Group
- **REFERENCES**: Entity → Entity

## Prerequisites

- Python 3.11+
- Neo4j 5.15+ (Enterprise with GDS plugin)
- Kafka 3.5+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (for containerized deployment)

## Installation

### Local Development

1. Clone the repository:
```bash
git clone <repository-url>
cd neo4j-loader-graph-service
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy environment file:
```bash
cp .env.example .env
```

5. Configure environment variables in `.env`

6. Run the service:
```bash
python -m src.main
```

### Docker Deployment

1. Build and run with Docker Compose:
```bash
docker-compose up -d
```

2. Check service health:
```bash
curl http://localhost:8000/health
```

3. View logs:
```bash
docker-compose logs -f neo4j-loader-graph-service
```

## Configuration

All configuration is done via environment variables. See `.env.example` for available options.

### Key Configuration Sections

#### Neo4j
- `NEO4J_URI`: Neo4j connection URI
- `NEO4J_USER`: Neo4j username
- `NEO4J_PASSWORD`: Neo4j password
- `NEO4J_MAX_CONNECTION_POOL_SIZE`: Connection pool size (default: 50)

#### Kafka
- `KAFKA_BOOTSTRAP_SERVERS`: Kafka broker addresses
- `KAFKA_SCHEMA_REGISTRY_URL`: Schema Registry URL
- `KAFKA_CONSUMER_GROUP_ID`: Consumer group ID
- `KAFKA_MAX_POLL_RECORDS`: Max records per poll (default: 100)

#### Batch Processing
- `BATCH_SIZE`: Batch size for UNWIND operations (default: 1000)
- `BATCH_INTERVAL_SECONDS`: Batch interval (default: 300)

#### Stream Processing
- `STREAM_BUFFER_SIZE`: Stream buffer size (default: 100)
- `STREAM_FLUSH_INTERVAL`: Flush interval in seconds (default: 5)

#### Analytics
- `CENTRALITY_INTERVAL_HOURS`: Centrality computation interval (default: 6)
- `CLUSTERING_INTERVAL_HOURS`: Clustering detection interval (default: 12)

## Usage

### Starting the Service

The service automatically:
1. Connects to Neo4j and initializes schema (constraints and indexes)
2. Connects to Kafka and subscribes to topics
3. Starts consuming messages and loading graph data
4. Runs periodic analytics (centrality and clustering)
5. Exposes metrics on port 8000

### Monitoring

#### Prometheus Metrics

Metrics are exposed at `http://localhost:8000/metrics`:

- `graph_nodes_created_total`: Total nodes created by type
- `graph_relationships_created_total`: Total relationships created by type
- `graph_load_duration_seconds`: Load operation duration
- `graph_validation_failures_total`: Validation failures
- `graph_centrality_computation_duration_seconds`: Centrality computation duration
- `graph_clustering_detection_duration_seconds`: Clustering detection duration
- `graph_query_latency_ms`: Query latency
- `graph_write_failures_total`: Write failures

#### Health Check

Health check endpoint: `http://localhost:8000/health`

Returns:
```json
{
  "service": "neo4j-loader-graph-service",
  "status": "healthy",
  "components": {
    "neo4j": {"status": "healthy", "details": {...}},
    "kafka": {"status": "healthy", "lag": {...}}
  }
}
```

#### Structured Logging

All logs are in JSON format with trace IDs for correlation:
```json
{
  "event": "nodes_batch_loaded",
  "node_label": "Article",
  "batch_size": 1000,
  "nodes_created": 1000,
  "duration_seconds": 0.523,
  "trace_id": "01HQXYZ...",
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "info"
}
```

## Development

### Project Structure

```
neo4j-loader-graph-service/
├── src/
│   ├── analytics/          # Graph analytics (centrality, clustering)
│   ├── builders/           # Node and relationship builders
│   ├── clients/            # Neo4j client
│   ├── kafka/              # Kafka consumer and message handling
│   ├── loaders/            # Batch and stream loaders
│   ├── models/             # Pydantic models for nodes and relationships
│   ├── queries/            # Query repository
│   ├── schema/             # Schema management
│   ├── service/            # Service orchestration
│   ├── validation/         # Graph validation
│   ├── config.py           # Configuration
│   ├── exceptions.py       # Custom exceptions
│   ├── metrics.py          # Prometheus metrics
│   └── main.py             # Entry point
├── tests/                  # Test suite
├── Dockerfile              # Docker image definition
├── docker-compose.yml      # Docker Compose configuration
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variables template
├── README.md               # This file
├── CHANGELOG.md            # Version history
└── TODO.md                 # Task tracking
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_node_builder.py

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Format code
black src/

# Lint code
ruff check src/

# Type checking
mypy src/

# Security scan
bandit -r src/
```

## Performance

### Throughput
- **Target**: ≥1000 nodes/sec
- **Batch Size**: 1000 nodes per UNWIND operation
- **Batch Interval**: 5 minutes

### Latency
- **Streaming**: <1s from Kafka to Neo4j
- **Query p95**: <1s for common queries
- **Write Failures**: <0.5%

### Resource Usage
- **Memory**: 2-4GB heap for Neo4j
- **CPU**: 2-4 cores recommended
- **Disk**: SSD recommended for Neo4j data

## Troubleshooting

### Common Issues

#### Connection Errors
```
Error: Failed to connect to Neo4j
Solution: Check NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD in .env
```

#### Kafka Consumer Lag
```
Warning: Consumer lag > 1000 messages
Solution: Increase BATCH_SIZE or STREAM_BUFFER_SIZE
```

#### Memory Issues
```
Error: OutOfMemoryError in Neo4j
Solution: Increase NEO4J_dbms_memory_heap_max__size
```

### Debug Mode

Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
python -m src.main
```

## Contributing

1. Follow clean code principles (Single Responsibility, Pure Functions, Explicit Interfaces)
2. Write tests for all new features (≥90% coverage required)
3. Use conventional commits format: `<type>(<scope>): <subject>`
4. Update CHANGELOG.md and TODO.md
5. Run code quality checks before committing

## License

Copyright © 2024 Sentiment Analyzer v2 Team. All rights reserved.

## Support

For issues and questions:
- Create an issue in the repository
- Contact the development team
- Check the documentation in `docs/`

## Version

Current version: 1.0.0

See CHANGELOG.md for version history.

