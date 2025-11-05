# Trainer & Model Registry Service

**Phase 3 Microservice** for the Sentiment Analyzer v2 system responsible for training ML models, model evaluation, drift detection, MLflow registry management, and artifact storage.

## Overview

The Trainer & Model Registry Service is a batch processing microservice that:
- Retrieves features from Feast offline feature store
- Retrieves labels from PostgreSQL ground-truth table
- Trains multiple model types (XGBoost, Logistic Regression, LLM baseline)
- Evaluates models with comprehensive metrics
- Detects feature and target drift using Evidently
- Manages model versions in MLflow registry
- Promotes models to production with threshold-based gating
- Stores artifacts in S3 with checksums
- Publishes model_trained and model_promoted events to Kafka

## Architecture

### Design Patterns
- **Strategy Pattern**: Pluggable model trainers (XGBoost, LogReg, LLM)
- **Factory Pattern**: Model and evaluator creation
- **Observer Pattern**: Training monitoring and callbacks
- **Template Method Pattern**: Training skeleton with pluggable transformations
- **Repository Pattern**: MLflow operations abstraction
- **Adapter Pattern**: Client wrappers for external services
- **Chain of Responsibility**: Evaluation stages

### Components

| Component | Purpose | Technology |
|-----------|---------|-----------|
| FeatureRetriever | Fetch features from Feast | Feast SDK |
| LabelRetriever | Fetch labels from PostgreSQL | asyncpg |
| Preprocessor | Handle missing values, scaling | scikit-learn |
| Splitter | Train/test/validation split | pandas |
| BaseModel | Abstract model interface | Python ABC |
| XGBoostModel | XGBoost trainer | xgboost |
| LogisticRegressionModel | LogReg baseline | scikit-learn |
| LLMBaselineModel | GPT-4 baseline | OpenAI API |
| Trainer | Training orchestration | Custom |
| Evaluator | Metrics computation | scikit-learn |
| DriftDetector | Drift detection | Evidently |
| ModelPromoter | Promotion logic | MLflow |
| KafkaProducer | Event publishing | confluent-kafka |

## Setup

### Prerequisites
- Python 3.11+
- PostgreSQL 13+
- Kafka 3.0+
- MLflow 2.0+
- Feast 0.30+
- Redis (for online features)
- S3-compatible storage

### Installation

```bash
# Create virtual environment
python -m venv venv311
source venv311/bin/activate  # On Windows: venv311\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your configuration
```

### Configuration

All configuration is externalized via environment variables. See `.env.example` for all parameters:

```bash
# Feast Configuration
FEAST_REGISTRY_PATH=/feast/registry.db
FEAST_REPO_PATH=/feast

# MLflow Configuration
MLFLOW_TRACKING_URI=http://localhost:5000
MLFLOW_ARTIFACT_STORE=s3://sentiment-analyzer/mlflow

# PostgreSQL Configuration
POSTGRES_HOST=154.53.166.231
POSTGRES_PORT=5432
POSTGRES_USER=adminsentiment
POSTGRES_PASSWORD=wp2400!!!!
POSTGRES_DATABASE=sentiment

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=154.53.166.231:9092
KAFKA_SCHEMA_REGISTRY_URL=http://154.53.166.231:8081

# S3 Configuration
S3_BUCKET=sentiment-analyzer-models
S3_REGION=us-east-1

# Training Configuration
TRAINING_WINDOW_MONTHS=18
TEST_SET_SIZE=0.2
VALIDATION_SET_SIZE=0.1

# Model Configuration
XGBOOST_MAX_DEPTH=6
XGBOOST_LEARNING_RATE=0.1
XGBOOST_N_ESTIMATORS=100

# Hyperparameter Tuning
HYPERPARAMETER_TUNING_TRIALS=50

# Model Promotion
MODEL_PROMOTION_THRESHOLD_AUC=0.75

# Monitoring
PROMETHEUS_PORT=9108
JAEGER_AGENT_HOST=localhost
JAEGER_AGENT_PORT=6831
```

## Running the Service

### Development

```bash
# Activate virtual environment
source venv311/bin/activate

# Run the service
python -m src.main

# Service will start on http://localhost:8001
```

### Health Checks

```bash
# Health check
curl http://localhost:8001/health

# Readiness check
curl http://localhost:8001/ready

# Liveness check
curl http://localhost:8001/live
```

## Testing

### Run All Tests

```bash
pytest tests/ -v --cov=src --cov-report=term-missing
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# Contract tests only
pytest tests/contract/ -v
```

### Coverage Report

```bash
pytest tests/ --cov=src --cov-report=html
# Open htmlcov/index.html in browser
```

## Monitoring

### Prometheus Metrics

Metrics available at `http://localhost:9108/metrics`:

- `training_runs_total`: Total training runs by model type
- `training_duration_seconds`: Training time by model type
- `model_auc_score`: AUC score by model version
- `model_precision_score`: Precision score by model version
- `model_recall_score`: Recall score by model version
- `model_f1_score`: F1 score by model version
- `model_drift_detected_total`: Feature/target drift detections
- `model_promoted_total`: Models promoted to production
- `model_promotion_failures_total`: Failed model promotions
- `hyperparameter_tuning_duration_seconds`: Optuna tuning time

### OpenTelemetry Tracing

Traces exported to Jaeger at `http://localhost:16686`

### Structured Logging

All logs include:
- `trace_id`: Distributed trace ID
- `span_id`: Span ID
- `model_name`: Model being trained
- `training_run_id`: MLflow run ID
- `operation`: Current operation
- `duration_ms`: Operation duration
- `status`: Operation status (success/error)

## Development

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/

# Security scanning
bandit -r src/
```

### Project Structure

```
trainer-model-registry-service/
├── src/
│   ├── __init__.py
│   ├── main.py                 # Entry point
│   ├── service.py              # Main service class
│   ├── config.py               # Configuration management
│   ├── exceptions.py           # Custom exceptions
│   ├── utils.py                # Utility functions
│   ├── clients/                # External service clients
│   ├── data/                   # Data retrieval & preprocessing
│   ├── models/                 # Model implementations
│   ├── training/               # Training pipeline
│   ├── evaluation/             # Evaluation & drift detection
│   └── registry/               # Model registry & promotion
├── tests/
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   └── contract/               # Contract tests
├── schemas/                    # Avro schemas
├── requirements.txt            # Python dependencies
├── .env.example                # Example environment variables
├── pytest.ini                  # Pytest configuration
└── README.md                   # This file
```

## API Endpoints

### Health Checks

- `GET /health` - Basic health check
- `GET /ready` - Readiness probe (checks dependencies)
- `GET /live` - Liveness probe (checks service is running)

### Metrics

- `GET /metrics` - Prometheus metrics

## Troubleshooting

### Common Issues

**Issue**: Service fails to connect to Feast
- **Solution**: Verify FEAST_REGISTRY_PATH and FEAST_REPO_PATH are correct

**Issue**: Models not being promoted
- **Solution**: Check MODEL_PROMOTION_THRESHOLD_AUC is not too high

**Issue**: Drift detection not working
- **Solution**: Ensure historical data exists in PostgreSQL

**Issue**: S3 upload failures
- **Solution**: Verify S3_BUCKET exists and credentials are correct

## Contributing

1. Create feature branch: `git checkout -b feature/trainer-service/<description>`
2. Make changes following code quality standards
3. Run tests: `pytest tests/ -v`
4. Commit with conventional format: `git commit -m "feat(trainer-service): <description>"`
5. Push and create PR to develop

## License

Proprietary - Sentiment Analyzer v2

## Support

For issues or questions, contact the Sentiment Analyzer team.

---

**Last Updated**: 2025-11-05  
**Version**: 1.0.0  
**Maintainer**: Trainer & Model Registry Service Team

