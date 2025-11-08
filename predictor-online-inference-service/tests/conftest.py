"""
Shared test fixtures and configuration.
"""

import os
import pytest
from typing import Dict, Any


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    os.environ["KAFKA_BOOTSTRAP_SERVERS"] = "localhost:9092"
    os.environ["KAFKA_SCHEMA_REGISTRY_URL"] = "http://localhost:8081"
    os.environ["MLFLOW_TRACKING_URI"] = "http://localhost:5000"
    os.environ["FEAST_REPO_PATH"] = "/feast"
    os.environ["REDIS_HOST"] = "localhost"
    os.environ["POSTGRES_HOST"] = "localhost"
    os.environ["MONITORING_LOG_LEVEL"] = "DEBUG"


@pytest.fixture
def sample_group_id() -> str:
    """Sample group ID for testing."""
    return "group_123"


@pytest.fixture
def sample_domain() -> str:
    """Sample domain for testing."""
    return "btc"


@pytest.fixture
def sample_features() -> Dict[str, Any]:
    """Sample features for testing."""
    return {
        "feature_num_sources": 5,
        "feature_sentiment_mean": 0.75,
        "feature_credibility_mean": 0.85,
        "feature_entities": ["Bitcoin", "BTC"],
        "feature_time_density": 0.65,
    }


@pytest.fixture
def sample_prediction() -> Dict[str, Any]:
    """Sample prediction for testing."""
    return {
        "group_id": "group_123",
        "domain": "btc",
        "prediction_probability": 0.85,
        "prediction_confidence": 0.70,
        "model_version": "v1.0.0",
        "predicted_at": "2025-11-07T12:00:00Z",
        "trace_id": "01JCABCDEFGHIJKLMNOPQRSTUV",
    }


@pytest.fixture
def sample_label() -> Dict[str, Any]:
    """Sample ground-truth label for testing."""
    return {
        "group_id": "group_123",
        "domain": "btc",
        "label_value": 1.0,
        "label_confidence": 0.90,
        "label_source": "ACLED",
        "labeled_at": "2025-11-07T12:00:00Z",
    }

