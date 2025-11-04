# Feature Engineering Service

Phase 3 of the sentiment-analyzer-v2 system. Computes 24 features from semantic groups for machine learning models.

## Quick Start

### Prerequisites

- Python 3.11+
- Kafka 3.0+
- PostgreSQL 13+
- Redis 6+
- Feast 0.30+

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running Locally

```bash
# Set environment variables
export KAFKA_BOOTSTRAP_SERVERS=154.53.166.231:9092
export POSTGRES_HOST=154.53.166.231
export POSTGRES_USER=admin
export POSTGRES_PASSWORD=wp2400!!!!

# Run service
python -m src.main
```

### Docker

```bash
# Build image
docker build -t feature-engineering-service:latest .

# Run container
docker run -e KAFKA_BOOTSTRAP_SERVERS=154.53.166.231:9092 \
           -e POSTGRES_HOST=154.53.166.231 \
           -p 9106:9106 \
           feature-engineering-service:latest
```

## Architecture

### Components

1. **Extractors**: Extract 24 features across 6 categories
   - Source Extractor (4 features)
   - Temporal Extractor (4 features)
   - Sentiment Extractor (4 features)
   - Entity Extractor (4 features)
   - Content Extractor (4 features)
   - Embedding Extractor (4 features)

2. **Transformers**: Transform and normalize features
   - Feature Aggregator
   - Feature Normalizer

3. **Validators**: Validate feature quality
   - Feature Validator
   - Quality Checker

4. **Storage**: Write to offline and online stores
   - Feast Writer (offline)
   - Redis Writer (online)
   - Reconciliation

5. **Drift Detection**: Monitor feature distributions
   - Drift Detector (KS and JS tests)

### Data Flow

```
Kafka (semantic_groups)
    ↓
Consumer
    ↓
Extract Features (6 extractors)
    ↓
Transform Features (aggregator, normalizer)
    ↓
Validate Features (validator, quality checks)
    ↓
Write to Storage (Feast + Redis)
    ↓
Produce to Kafka (features_computed)
```

## Features

### Source Features
- Number of unique sources
- Source credibility metrics
- Source diversity

### Temporal Features
- Time span of coverage
- Publication velocity
- Temporal concentration
- Days since first article

### Sentiment Features
- Mean sentiment
- Sentiment volatility
- Polarity ratio

### Entity Features
- Entity count and diversity
- Entity prominence
- Entity concentration

### Content Features
- Average word count
- Title length
- Language and domain diversity

### Embedding Features
- Centroid magnitude
- Intra-cluster similarity
- Embedding drift

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_extractors.py -v
```

## Configuration

See `src/config.py` for all configuration options. All settings can be overridden via environment variables.

## Monitoring

Prometheus metrics available at `http://localhost:9106/metrics`

Key metrics:
- `feature_groups_consumed_total`
- `feature_computed_total`
- `feature_validation_failures_total`
- `feature_computation_duration_seconds`

## Documentation

- [INTEGRATION.md](INTEGRATION.md) - Service contracts and integration guide
- [CHANGELOG.md](CHANGELOG.md) - Version history and design patterns
- [Architecture.md](../Architecture.md) - System architecture
- [Microservice.md](../Microservice.md) - Microservice specifications

## Development

### Code Style

```bash
# Format code
black src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

### Adding New Features

1. Create extractor in `src/extractors/`
2. Add to `FeatureEngineeringService._extract_features()`
3. Add tests in `tests/test_extractors.py`
4. Update CHANGELOG.md

## Performance

- **Latency**: ≤5 seconds per semantic group
- **Throughput**: ≥100 groups/minute
- **Availability**: ≥99.5%
- **Offline-Online Consistency**: ≥99%

## License

Proprietary - Sentiment Analyzer v2 Project

## Support

For issues or questions, contact the development team.

