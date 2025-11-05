"""Pytest configuration and fixtures."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_config():
    """Mock configuration."""
    config = Mock()
    config.kafka = Mock(
        brokers="154.53.166.231:9092",
        schema_registry_url="http://154.53.166.231:8081",
        topic_ground_truth="ground_truth",
    )
    config.postgres = Mock(
        host="154.53.166.231",
        port=5432,
        user="adminsentiment",
        password="wp2400!!!!",
        database="sentiment",
        pool_size=20,
    )
    config.acled = Mock(
        api_url="https://api.acleddata.com",
        api_key="test-key",
        fetch_interval_hours=24,
    )
    config.gdelt = Mock(
        api_url="https://api.gdeltproject.org",
        fetch_interval_hours=1,
    )
    config.coingecko = Mock(
        api_url="https://api.coingecko.com",
        fetch_interval_minutes=5,
    )
    config.label = Mock(
        confidence_threshold=0.7,
        reconciliation_threshold=48,
        freshness_acled_hours=24,
        freshness_gdelt_hours=1,
        freshness_coingecko_minutes=5,
        temporal_threshold_hours=24,
    )
    config.storage = Mock(
        delta_lake_path="/data/delta_lake/ground_truth",
    )
    config.metrics = Mock(
        prometheus_port=9107,
    )
    config.logging = Mock(
        log_level="INFO",
    )
    config.service = Mock(
        service_name="labeler-ground-truth-ingest-service",
        service_version="1.0.0",
    )
    config.tracing = Mock(
        jaeger_host="localhost",
        jaeger_port=6831,
    )
    return config


@pytest.fixture
def mock_kafka_producer():
    """Mock Kafka producer."""
    producer = AsyncMock()
    producer.connect = AsyncMock()
    producer.produce_label = AsyncMock(return_value=True)
    producer.produce_batch = AsyncMock(return_value=True)
    producer.close = AsyncMock()
    return producer


@pytest.fixture
def mock_postgres_writer():
    """Mock PostgreSQL writer."""
    writer = AsyncMock()
    writer.connect = AsyncMock()
    writer.write_labels = AsyncMock(return_value=True)
    writer.close = AsyncMock()
    return writer


@pytest.fixture
def mock_delta_lake_writer():
    """Mock Delta Lake writer."""
    writer = AsyncMock()
    writer.write_labels = AsyncMock(return_value=True)
    return writer


@pytest.fixture
def sample_acled_label():
    """Sample ACLED label."""
    return {
        "event_id": "12345",
        "event_date": "2025-11-05",
        "country": "Syria",
        "event_type": "Violence against civilians",
        "fatalities": 5,
        "label_conflict": 1,
        "confidence": 0.85,
        "source": "acled",
        "timestamp": "2025-11-05T10:00:00Z",
    }


@pytest.fixture
def sample_gdelt_label():
    """Sample GDELT label."""
    return {
        "event_id": "67890",
        "event_date": "2025-11-05",
        "event_type": "Protest",
        "actor_a": "Protesters",
        "actor_b": "Government",
        "goldstein_scale": -5.0,
        "label_event_type": "protest",
        "confidence": 0.75,
        "source": "gdelt",
        "timestamp": "2025-11-05T11:00:00Z",
    }


@pytest.fixture
def sample_coingecko_label():
    """Sample CoinGecko label."""
    return {
        "timestamp": "2025-11-05T12:00:00Z",
        "open": 45000.0,
        "close": 46500.0,
        "high": 47000.0,
        "low": 44500.0,
        "volume": 1000000000.0,
        "change_pct_10h": 3.33,
        "label_spike": 1,
        "volatility_score": 0.65,
        "source": "coingecko",
        "confidence": 0.80,
    }


@pytest.fixture
def sample_semantic_group():
    """Sample semantic group."""
    from datetime import datetime, timedelta
    # Create a group that was created 2 days ago (to satisfy R8 requirement)
    created_at = (datetime.utcnow() - timedelta(days=2)).isoformat() + "Z"
    return {
        "group_id": "group-001",
        "created_at": created_at,
        "description": "Syria conflict events",
        "keywords": ["Syria", "conflict", "violence"],
        "article_count": 50,
        "embedding": [0.1, 0.2, 0.3, 0.4, 0.5],
    }


@pytest.fixture
def mock_api_response():
    """Mock API response."""
    return {
        "status": "success",
        "data": [
            {
                "event_id": "12345",
                "event_date": "2025-11-05",
                "country": "Syria",
            }
        ],
    }

