# Clustering-Semantic-Grouping-Service

Phase 2 microservice for semantic clustering and grouping of multilingual news articles.

## Overview

This service consumes article embeddings from Qdrant, performs density-based clustering (HDBSCAN/DBSCAN), and publishes semantic groups to Kafka and Delta Lake.

### Key Features

- **HDBSCAN Clustering**: Hierarchical density-based clustering for varying densities
- **DBSCAN Fallback**: Alternative clustering algorithm
- **Temporal Tracking**: Cluster evolution and lineage tracking
- **Quality Validation**: R7 temporal coherence + cluster purity checks
- **Multi-Write**: ACID writes to Delta Lake + PostgreSQL + Kafka
- **Incremental State**: Redis caching for efficient updates
- **Comprehensive Monitoring**: Prometheus metrics + structured logging

## Architecture

### Components

1. **TimeWindowManager**: Sliding window calculation with overlap
2. **VectorRetriever**: Qdrant queries with metadata filtering
3. **ClusteringEngine**: HDBSCAN/DBSCAN with parameter tuning
4. **ClusterValidator**: Quality checks and temporal coherence
5. **CentroidCalculator**: Weighted centroid computation
6. **MetadataAggregator**: Article property aggregation
7. **TopicLabeler**: TF-IDF extractive + optional LLM
8. **TemporalTracker**: Cluster evolution and lineage
9. **DeltaLakeWriter**: ACID writes with versioning
10. **ClusterRegistry**: PostgreSQL metadata storage
11. **CacheManager**: Redis for incremental state
12. **PipelineOrchestrator**: Complete pipeline orchestration

### Data Flow

```
Qdrant (embeddings)
  → Vector Retrieval
  → Preprocessing
  → Clustering (HDBSCAN/DBSCAN)
  → Validation (R7 + purity)
  → Centroid Computation
  → Metadata Aggregation
  → Topic Labeling
  → Temporal Tracking
  → Quality Scoring
  → Multi-Write (Kafka + Delta + PostgreSQL)
```

## Installation

### Prerequisites

- Python 3.11+
- Kafka 3.0+
- PostgreSQL 13+
- Redis 6+
- Qdrant 1.0+

### Setup

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your configuration
```

## Running

### Development

```bash
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8082
```

### Docker

```bash
docker-compose up -d
```

### Tests

```bash
pytest tests/ -v --cov=src
```

## API Endpoints

- `GET /health` - Health check
- `GET /ready` - Readiness check
- `GET /metrics` - Prometheus metrics
- `GET /status` - Service status
- `POST /jobs/clustering/run` - Manually trigger clustering job
- `GET /jobs/clustering/status` - Get job status

## Configuration

See `.env.example` for all configuration options.

### Key Parameters

- `CLUSTERING_ALGORITHM`: hdbscan or dbscan
- `MIN_CLUSTER_SIZE`: Minimum articles per cluster (default: 3)
- `SIMILARITY_THRESHOLD`: Cluster matching threshold (default: 0.85)
- `EXECUTION_FREQUENCY_HOURS`: Job frequency (default: 4)
- `TIME_WINDOW_HOURS`: Processing window size (default: 24)
- `OVERLAP_HOURS`: Window overlap for deduplication (default: 6)

## Validation Rules

- **R7**: Temporal coherence - cluster timestamp ≥ min(article timestamps)
- **Cluster Purity**: ≥0.85 average intra-cluster cosine similarity
- **Minimum Size**: ≥3 articles per cluster
- **Source Diversity**: ≥2 unique sources
- **Time Span**: ≤168 hours from earliest to latest article

## Monitoring

### Prometheus Metrics

- `clustering_jobs_total` - Total jobs executed
- `clustering_duration_seconds` - Job duration
- `clusters_created_total` - Total clusters created

### Logs

Structured JSON logging with trace IDs for debugging.

## Integration

### Upstream Services

- **embedding-service**: Provides embeddings via Qdrant
- **canonicalizer-normalizer-service**: Provides article metadata

### Downstream Services

- **feature-engineering-service**: Consumes semantic groups
- **neo4j-loader-service**: Loads clusters into graph database

## Troubleshooting

### No clusters created

1. Check Qdrant connectivity: `curl http://qdrant:6333/health`
2. Verify embeddings exist in collection
3. Check time window configuration
4. Review logs for validation errors

### High memory usage

1. Reduce `MIN_CLUSTER_SIZE` to create smaller clusters
2. Reduce `TIME_WINDOW_HOURS` to process smaller windows
3. Increase `EXECUTION_FREQUENCY_HOURS` to run more frequently

### Slow clustering

1. Enable parameter tuning: `tune_parameters()`
2. Reduce sample size for tuning
3. Use DBSCAN instead of HDBSCAN for speed

## Development

### Code Style

```bash
black src/ tests/
flake8 src/ tests/
pylint src/ tests/
mypy src/
```

### Testing

```bash
pytest tests/ -v --cov=src --cov-report=html
```

## License

Proprietary - Sentiment Analyzer v2 Project

## Support

For issues and questions, contact the development team.

