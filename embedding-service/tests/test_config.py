"""Tests for configuration."""

import pytest
from src.config import config, Config


class TestConfiguration:
    """Test configuration loading."""

    def test_config_exists(self):
        """Test that config is loaded."""
        assert config is not None
        assert isinstance(config, Config)

    def test_kafka_config(self):
        """Test Kafka configuration."""
        assert config.kafka is not None
        assert config.kafka.brokers
        assert config.kafka.input_topic
        assert config.kafka.output_topic
        assert config.kafka.consumer_group

    def test_postgres_config(self):
        """Test PostgreSQL configuration."""
        assert config.postgres is not None
        assert config.postgres.host
        assert config.postgres.port > 0
        assert config.postgres.user
        assert config.postgres.database

    def test_qdrant_config(self):
        """Test Qdrant configuration."""
        assert config.qdrant is not None
        assert config.qdrant.host
        assert config.qdrant.port > 0
        assert config.qdrant.collection_name
        assert config.qdrant.vector_size > 0

    def test_redis_config(self):
        """Test Redis configuration."""
        assert config.redis is not None
        assert config.redis.host
        assert config.redis.port > 0

    def test_model_config(self):
        """Test model configuration."""
        assert config.model is not None
        assert config.model.device in ["cpu", "cuda", "auto"]
        assert config.model.batch_size_gpu > 0
        assert config.model.batch_size_cpu > 0
        assert config.model.max_sequence_length > 0

    def test_validation_config(self):
        """Test validation configuration."""
        assert config.validation is not None
        assert isinstance(config.validation.enabled, bool)
        assert isinstance(config.validation.drift_detection_enabled, bool)

    def test_metrics_config(self):
        """Test metrics configuration."""
        assert config.metrics is not None
        assert config.metrics.prometheus_port > 0
        assert isinstance(config.metrics.enabled, bool)

    def test_config_frozen(self):
        """Test that config is frozen."""
        with pytest.raises(Exception):
            config.kafka.brokers = "new_value"

