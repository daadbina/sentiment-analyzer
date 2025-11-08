# API Analytics Service

REST API for querying semantic groups, predictions, graph data, and analytics from the Sentiment Analyzer v2 system.

## Overview

The API Analytics Service provides a comprehensive REST API for:
- Querying semantic groups and their articles
- Accessing predictions and sentiment analysis results
- Exploring entities and their mentions
- Analyzing trends and distributions
- Traversing the knowledge graph
- Exporting data in multiple formats

## Features

- **Authentication & Authorization**: JWT-based authentication with role-based access control (RBAC)
- **Query Building**: Efficient parameterized SQL and Cypher queries
- **Caching**: Redis-based query result caching with TTL
- **Rate Limiting**: Per-user per-endpoint rate limiting
- **Pagination**: Offset-based and cursor-based pagination
- **Filtering & Search**: Flexible filtering and full-text search
- **Analytics**: Trend analysis, distribution analysis, top items
- **Graph Queries**: Neo4j graph traversal and path finding
- **Export**: CSV and JSON export functionality
- **Monitoring**: Prometheus metrics and structured logging
- **Health Checks**: Comprehensive health check endpoints

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                      │
├─────────────────────────────────────────────────────────────┤
│  Authentication │ Authorization │ Rate Limiting │ Caching   │
├─────────────────────────────────────────────────────────────┤
│  API Routes (Groups, Predictions, Entities, Analytics, etc) │
├─────────────────────────────────────────────────────────────┤
│  Query Builders │ Data Aggregator │ Pagination │ Filtering  │
├─────────────────────────────────────────────────────────────┤
│  PostgreSQL │ Neo4j │ Redis │ Prometheus                    │
└─────────────────────────────────────────────────────────────┘
```

## Installation

### Prerequisites

- Python 3.11+
- PostgreSQL 13+
- Neo4j 5+
- Redis 7+

### Setup

1. Clone the repository:
```bash
git clone https://github.com/daadbina/sentiment-analyzer.git
cd sentiment-analyzer-v2/api-analytics-service
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

4. Configure environment:
```bash
cp .env.example .env
# Edit .env with your configuration
```

## Configuration

All configuration is managed through environment variables. See `.env.example` for all available options.

### Key Configuration

```bash
# PostgreSQL
POSTGRES_HOST=154.53.166.231
POSTGRES_PORT=5432
POSTGRES_USER=adminsentiment
POSTGRES_PASSWORD=wp2400!!!!
POSTGRES_DATABASE=sentiment

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# JWT
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# API
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
```

## Running

### Local Development

```bash
python -m src.main
```

The API will be available at `http://localhost:8000`

### Docker

```bash
docker-compose up
```

### Production

```bash
gunicorn -w 4 -b 0.0.0.0:8000 src.app:app
```

## API Endpoints

### Groups
- `GET /api/v1/groups` - List groups
- `GET /api/v1/groups/{id}` - Get group details
- `GET /api/v1/groups/{id}/articles` - Get articles in group
- `GET /api/v1/groups/{id}/entities` - Get entities in group
- `GET /api/v1/groups/{id}/prediction` - Get prediction for group
- `POST /api/v1/groups` - Create group
- `PUT /api/v1/groups/{id}` - Update group
- `DELETE /api/v1/groups/{id}` - Delete group

### Predictions
- `GET /api/v1/predictions` - List predictions
- `GET /api/v1/predictions/{id}` - Get prediction details
- `GET /api/v1/predictions/group/{group_id}` - Get predictions for group
- `POST /api/v1/predictions` - Create prediction

### Entities
- `GET /api/v1/entities` - List entities
- `GET /api/v1/entities/{id}` - Get entity details
- `GET /api/v1/entities/{id}/mentions` - Get entity mentions
- `POST /api/v1/entities` - Create entity

### Analytics
- `GET /api/v1/analytics/trends` - Trend analysis
- `GET /api/v1/analytics/distributions` - Distribution analysis
- `GET /api/v1/analytics/top-entities` - Top entities
- `GET /api/v1/analytics/top-actors` - Top actors

### Graph
- `GET /api/v1/graph/neighbors/{id}` - Get graph neighbors
- `GET /api/v1/graph/paths/{from}/{to}` - Find paths
- `GET /api/v1/graph/centrality` - Centrality metrics

### Export
- `GET /api/v1/export/groups` - Export groups
- `GET /api/v1/export/predictions` - Export predictions
- `GET /api/v1/export/entities` - Export entities

### Health
- `GET /health` - Health check
- `GET /ready` - Readiness check
- `GET /live` - Liveness check

## Authentication

All endpoints (except health checks) require JWT authentication:

```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/groups
```

## Testing

Run tests:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=src --cov-report=html
```

## Monitoring

Prometheus metrics available at `http://localhost:9111/metrics`

Key metrics:
- `api_requests_total` - Total API requests
- `api_request_latency_ms` - Request latency
- `api_errors_total` - Total errors
- `api_cache_hits_total` - Cache hits
- `api_cache_misses_total` - Cache misses
- `api_rate_limit_exceeded_total` - Rate limit violations

## Logging

Structured JSON logging with trace ID propagation. Logs include:
- Timestamp
- Log level
- Message
- Trace ID
- User ID
- Endpoint
- Latency

## Development

### Code Quality

```bash
# Format code
black src/

# Lint
ruff check src/

# Type checking
mypy src/

# Security scan
bandit -r src/
```

### Project Structure

```
api-analytics-service/
├── src/
│   ├── main.py                 # Entry point
│   ├── app.py                  # FastAPI application
│   ├── config.py               # Configuration
│   ├── exceptions.py           # Custom exceptions
│   ├── metrics.py              # Prometheus metrics
│   ├── auth/                   # Authentication & authorization
│   ├── api/                    # API routes
│   ├── clients/                # Database clients
│   ├── queries/                # Query builders
│   ├── storage/                # Caching & rate limiting
│   └── utils/                  # Utilities
├── tests/                      # Test suite
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container image
├── docker-compose.yml          # Local development
├── pytest.ini                  # Pytest configuration
└── README.md                   # This file
```

## Performance

- **API Latency**: p95 <300ms, p99 <500ms
- **Throughput**: ≥1000 requests/second per replica
- **Cache Hit Rate**: ≥50% for repeated queries
- **Authentication Latency**: ≤50ms per request
- **Memory Footprint**: ≤2GB per replica

## Deployment

### Kubernetes

```bash
kubectl apply -f k8s/
```

### Helm

```bash
helm install api-analytics-service helm/api-analytics-service/
```

## Troubleshooting

### Database Connection Issues

Check database connectivity:
```bash
curl http://localhost:8000/ready
```

### Rate Limiting

Check rate limit status in response headers:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1234567890
```

### Cache Issues

Clear cache:
```bash
redis-cli FLUSHDB
```

## Contributing

1. Create feature branch: `git checkout -b feature/my-feature`
2. Make changes and commit: `git commit -m "feat: my feature"`
3. Push to remote: `git push origin feature/my-feature`
4. Create pull request

## License

Proprietary - Sentiment Analyzer v2

## Support

For issues and questions, please contact the development team.

