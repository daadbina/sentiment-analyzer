"""
Unit tests for configuration module.
"""

import os
import pytest

from src.config import (
    KafkaConfig,
    MLflowConfig,
    FeastConfig,
    RedisConfig,
    PostgresConfig,
    InferenceConfig,
    APIConfig,
    MonitoringConfig,
    ValidationConfig,
    Config,
)


class TestKafkaConfig:
    """Tests for KafkaConfig."""
    
    def test_from_env_with_defaults(self, monkeypatch):
        """Test loading Kafka config from environment with defaults."""
        monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        monkeypatch.setenv("KAFKA_SCHEMA_REGISTRY_URL", "http://localhost:8081")
        
        config = KafkaConfig.from_env()
        
        assert config.bootstrap_servers == "localhost:9092"
        assert config.schema_registry_url == "http://localhost:8081"
        assert config.consumer_group_id == "predictor-service"
        assert config.input_topic == "semantic_groups"
        assert config.output_topic == "predictions"
    
    def test_from_env_with_custom_values(self, monkeypatch):
        """Test loading Kafka config with custom values."""
        monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
        monkeypatch.setenv("KAFKA_SCHEMA_REGISTRY_URL", "http://schema-registry:8081")
        monkeypatch.setenv("KAFKA_CONSUMER_GROUP_ID", "custom-group")
        monkeypatch.setenv("KAFKA_INPUT_TOPIC", "custom-input")
        monkeypatch.setenv("KAFKA_OUTPUT_TOPIC", "custom-output")
        
        config = KafkaConfig.from_env()
        
        assert config.bootstrap_servers == "kafka:9092"
        assert config.schema_registry_url == "http://schema-registry:8081"
        assert config.consumer_group_id == "custom-group"
        assert config.input_topic == "custom-input"
        assert config.output_topic == "custom-output"


class TestMLflowConfig:
    """Tests for MLflowConfig."""
    
    def test_from_env_with_defaults(self, monkeypatch):
        """Test loading MLflow config from environment with defaults."""
        monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
        
        config = MLflowConfig.from_env()
        
        assert config.tracking_uri == "http://localhost:5000"
        assert config.model_name == "predictor_model"
        assert config.model_version == "v1.0.0"
        assert config.model_stage == "Production"


class TestInferenceConfig:
    """Tests for InferenceConfig."""
    
    def test_from_env_with_defaults(self, monkeypatch):
        """Test loading inference config from environment with defaults."""
        config = InferenceConfig.from_env()
        
        assert config.batch_size == 100
        assert config.timeout_seconds == 30
        assert config.cache_ttl_seconds == 3600
        assert config.enable_streaming is True
        assert config.ab_testing_enabled is False
    
    def test_from_env_with_custom_values(self, monkeypatch):
        """Test loading inference config with custom values."""
        monkeypatch.setenv("INFERENCE_BATCH_SIZE", "200")
        monkeypatch.setenv("INFERENCE_TIMEOUT_SECONDS", "60")
        monkeypatch.setenv("INFERENCE_CACHE_TTL_SECONDS", "7200")
        monkeypatch.setenv("INFERENCE_ENABLE_STREAMING", "false")
        monkeypatch.setenv("INFERENCE_AB_TESTING_ENABLED", "true")
        
        config = InferenceConfig.from_env()
        
        assert config.batch_size == 200
        assert config.timeout_seconds == 60
        assert config.cache_ttl_seconds == 7200
        assert config.enable_streaming is False
        assert config.ab_testing_enabled is True


class TestConfig:
    """Tests for main Config class."""
    
    def test_load_config(self, monkeypatch):
        """Test loading complete configuration."""
        # Set minimal required environment variables
        monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        monkeypatch.setenv("KAFKA_SCHEMA_REGISTRY_URL", "http://localhost:8081")
        monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
        monkeypatch.setenv("FEAST_REPO_PATH", "/feast")
        monkeypatch.setenv("REDIS_HOST", "localhost")
        monkeypatch.setenv("POSTGRES_HOST", "localhost")
        
        config = Config.from_env()
        
        assert config.kafka is not None
        assert config.mlflow is not None
        assert config.feast is not None
        assert config.redis is not None
        assert config.postgres is not None
        assert config.inference is not None
        assert config.api is not None
        assert config.monitoring is not None
        assert config.validation is not None
    
    def test_validate_success(self, monkeypatch):
        """Test configuration validation success."""
        # Set minimal required environment variables
        monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        monkeypatch.setenv("KAFKA_SCHEMA_REGISTRY_URL", "http://localhost:8081")
        monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
        monkeypatch.setenv("FEAST_REPO_PATH", "/feast")
        monkeypatch.setenv("REDIS_HOST", "localhost")
        monkeypatch.setenv("POSTGRES_HOST", "localhost")
        
        config = Config.from_env()
        
        # Should not raise exception
        config.validate()
    
    def test_validate_failure_missing_kafka(self, monkeypatch):
        """Test configuration validation failure with missing Kafka config."""
        monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
        monkeypatch.setenv("FEAST_REPO_PATH", "/feast")
        monkeypatch.setenv("REDIS_HOST", "localhost")
        monkeypatch.setenv("POSTGRES_HOST", "localhost")
        
        with pytest.raises(ValueError, match="KAFKA_BOOTSTRAP_SERVERS"):
            config = Config.from_env()
            config.validate()

