"""
Unit tests for configuration management.

Tests configuration loading and validation.
"""

import pytest
import os
from unittest.mock import patch

from src.config import (
    config,
    FeastConfig,
    MLflowConfig,
    PostgreSQLConfig,
    S3Config,
    KafkaConfig,
    TrainingConfig,
    XGBoostConfig,
    LogisticRegressionConfig,
    HyperparameterTuningConfig,
    DriftDetectionConfig,
    ModelPromotionConfig,
    PrometheusConfig,
    JaegerConfig,
    ServiceConfig,
    LLMConfig,
)


class TestFeastConfig:
    """Test Feast configuration."""

    def test_feast_config_defaults(self):
        """Test Feast config has defaults."""
        feast_config = FeastConfig()
        assert feast_config.registry_path is not None
        assert feast_config.feature_store_type is not None

    def test_feast_config_from_env(self):
        """Test Feast config from environment."""
        with patch.dict(os.environ, {"FEAST_REGISTRY_PATH": "/tmp/feast"}):
            feast_config = FeastConfig()
            assert feast_config.registry_path == "/tmp/feast"


class TestMLflowConfig:
    """Test MLflow configuration."""

    def test_mlflow_config_defaults(self):
        """Test MLflow config has defaults."""
        mlflow_config = MLflowConfig()
        assert mlflow_config.tracking_uri is not None
        assert mlflow_config.artifact_store is not None

    def test_mlflow_config_from_env(self):
        """Test MLflow config from environment."""
        with patch.dict(os.environ, {"MLFLOW_TRACKING_URI": "http://localhost:5000"}):
            mlflow_config = MLflowConfig()
            assert mlflow_config.tracking_uri == "http://localhost:5000"


class TestPostgreSQLConfig:
    """Test PostgreSQL configuration."""

    def test_postgres_config_defaults(self):
        """Test PostgreSQL config has defaults."""
        pg_config = PostgreSQLConfig()
        assert pg_config.host is not None
        assert pg_config.port > 0
        assert pg_config.user is not None
        assert pg_config.database is not None

    def test_postgres_config_from_env(self):
        """Test PostgreSQL config from environment."""
        env_vars = {
            "POSTGRES_HOST": "db.example.com",
            "POSTGRES_PORT": "5433",
            "POSTGRES_USER": "testuser",
        }
        with patch.dict(os.environ, env_vars):
            pg_config = PostgreSQLConfig()
            assert pg_config.host == "db.example.com"
            assert pg_config.port == 5433
            assert pg_config.user == "testuser"


class TestS3Config:
    """Test S3 configuration."""

    def test_s3_config_defaults(self):
        """Test S3 config has defaults."""
        s3_config = S3Config()
        assert s3_config.bucket is not None
        assert s3_config.region is not None

    def test_s3_config_from_env(self):
        """Test S3 config from environment."""
        env_vars = {
            "S3_BUCKET": "my-bucket",
            "S3_REGION": "us-west-2",
        }
        with patch.dict(os.environ, env_vars):
            s3_config = S3Config()
            assert s3_config.bucket == "my-bucket"
            assert s3_config.region == "us-west-2"


class TestKafkaConfig:
    """Test Kafka configuration."""

    def test_kafka_config_defaults(self):
        """Test Kafka config has defaults."""
        kafka_config = KafkaConfig()
        assert kafka_config.bootstrap_servers is not None
        assert kafka_config.schema_registry_url is not None

    def test_kafka_config_from_env(self):
        """Test Kafka config from environment."""
        env_vars = {
            "KAFKA_BOOTSTRAP_SERVERS": "kafka:9092",
            "KAFKA_SCHEMA_REGISTRY_URL": "http://schema-registry:8081",
        }
        with patch.dict(os.environ, env_vars):
            kafka_config = KafkaConfig()
            assert kafka_config.bootstrap_servers == "kafka:9092"
            assert kafka_config.schema_registry_url == "http://schema-registry:8081"


class TestTrainingConfig:
    """Test training configuration."""

    def test_training_config_defaults(self):
        """Test training config has defaults."""
        training_config = TrainingConfig()
        assert training_config.window_months > 0
        assert 0 < training_config.test_size < 1
        assert 0 < training_config.validation_size < 1
        assert training_config.random_seed is not None

    def test_training_config_from_env(self):
        """Test training config from environment."""
        env_vars = {
            "TRAINING_WINDOW_MONTHS": "24",
            "TRAINING_TEST_SIZE": "0.25",
            "TRAINING_VALIDATION_SIZE": "0.15",
        }
        with patch.dict(os.environ, env_vars):
            training_config = TrainingConfig()
            assert training_config.window_months == 24
            assert training_config.test_size == 0.25
            assert training_config.validation_size == 0.15


class TestXGBoostConfig:
    """Test XGBoost configuration."""

    def test_xgboost_config_defaults(self):
        """Test XGBoost config has defaults."""
        xgb_config = XGBoostConfig()
        assert xgb_config.max_depth > 0
        assert xgb_config.learning_rate > 0
        assert xgb_config.n_estimators > 0

    def test_xgboost_config_from_env(self):
        """Test XGBoost config from environment."""
        env_vars = {
            "XGBOOST_MAX_DEPTH": "8",
            "XGBOOST_LEARNING_RATE": "0.1",
            "XGBOOST_N_ESTIMATORS": "200",
        }
        with patch.dict(os.environ, env_vars):
            xgb_config = XGBoostConfig()
            assert xgb_config.max_depth == 8
            assert xgb_config.learning_rate == 0.1
            assert xgb_config.n_estimators == 200


class TestLogisticRegressionConfig:
    """Test Logistic Regression configuration."""

    def test_logistic_regression_config_defaults(self):
        """Test Logistic Regression config has defaults."""
        lr_config = LogisticRegressionConfig()
        assert lr_config.C > 0
        assert lr_config.penalty is not None
        assert lr_config.solver is not None

    def test_logistic_regression_config_from_env(self):
        """Test Logistic Regression config from environment."""
        env_vars = {
            "LOGISTIC_REGRESSION_C": "0.5",
            "LOGISTIC_REGRESSION_PENALTY": "l2",
        }
        with patch.dict(os.environ, env_vars):
            lr_config = LogisticRegressionConfig()
            assert lr_config.C == 0.5
            assert lr_config.penalty == "l2"


class TestHyperparameterTuningConfig:
    """Test hyperparameter tuning configuration."""

    def test_hyperparameter_tuning_config_defaults(self):
        """Test hyperparameter tuning config has defaults."""
        hpt_config = HyperparameterTuningConfig()
        assert hpt_config.enabled is not None
        assert hpt_config.n_trials > 0

    def test_hyperparameter_tuning_config_from_env(self):
        """Test hyperparameter tuning config from environment."""
        env_vars = {
            "HYPERPARAMETER_TUNING_ENABLED": "true",
            "HYPERPARAMETER_TUNING_TRIALS": "100",
        }
        with patch.dict(os.environ, env_vars):
            hpt_config = HyperparameterTuningConfig()
            assert hpt_config.enabled is True
            assert hpt_config.n_trials == 100


class TestDriftDetectionConfig:
    """Test drift detection configuration."""

    def test_drift_detection_config_defaults(self):
        """Test drift detection config has defaults."""
        dd_config = DriftDetectionConfig()
        assert dd_config.enabled is not None
        assert dd_config.threshold > 0

    def test_drift_detection_config_from_env(self):
        """Test drift detection config from environment."""
        env_vars = {
            "DRIFT_DETECTION_ENABLED": "true",
            "DRIFT_DETECTION_THRESHOLD": "0.1",
        }
        with patch.dict(os.environ, env_vars):
            dd_config = DriftDetectionConfig()
            assert dd_config.enabled is True
            assert dd_config.threshold == 0.1


class TestModelPromotionConfig:
    """Test model promotion configuration."""

    def test_model_promotion_config_defaults(self):
        """Test model promotion config has defaults."""
        mp_config = ModelPromotionConfig()
        assert mp_config.threshold_auc > 0
        assert mp_config.threshold_precision > 0
        assert mp_config.threshold_recall > 0

    def test_model_promotion_config_from_env(self):
        """Test model promotion config from environment."""
        env_vars = {
            "MODEL_PROMOTION_THRESHOLD_AUC": "0.8",
            "MODEL_PROMOTION_THRESHOLD_PRECISION": "0.75",
        }
        with patch.dict(os.environ, env_vars):
            mp_config = ModelPromotionConfig()
            assert mp_config.threshold_auc == 0.8
            assert mp_config.threshold_precision == 0.75


class TestPrometheusConfig:
    """Test Prometheus configuration."""

    def test_prometheus_config_defaults(self):
        """Test Prometheus config has defaults."""
        prom_config = PrometheusConfig()
        assert prom_config.port > 0
        assert prom_config.enabled is not None

    def test_prometheus_config_from_env(self):
        """Test Prometheus config from environment."""
        env_vars = {
            "PROMETHEUS_PORT": "9109",
            "PROMETHEUS_ENABLED": "true",
        }
        with patch.dict(os.environ, env_vars):
            prom_config = PrometheusConfig()
            assert prom_config.port == 9109
            assert prom_config.enabled is True


class TestJaegerConfig:
    """Test Jaeger configuration."""

    def test_jaeger_config_defaults(self):
        """Test Jaeger config has defaults."""
        jaeger_config = JaegerConfig()
        assert jaeger_config.enabled is not None
        assert jaeger_config.host is not None
        assert jaeger_config.port > 0

    def test_jaeger_config_from_env(self):
        """Test Jaeger config from environment."""
        env_vars = {
            "JAEGER_ENABLED": "true",
            "JAEGER_HOST": "jaeger",
            "JAEGER_PORT": "6831",
        }
        with patch.dict(os.environ, env_vars):
            jaeger_config = JaegerConfig()
            assert jaeger_config.enabled is True
            assert jaeger_config.host == "jaeger"
            assert jaeger_config.port == 6831


class TestServiceConfig:
    """Test service configuration."""

    def test_service_config_defaults(self):
        """Test service config has defaults."""
        service_config = ServiceConfig()
        assert service_config.host is not None
        assert service_config.port > 0
        assert service_config.log_level is not None

    def test_service_config_from_env(self):
        """Test service config from environment."""
        env_vars = {
            "SERVICE_HOST": "0.0.0.0",
            "SERVICE_PORT": "8001",
            "SERVICE_LOG_LEVEL": "DEBUG",
        }
        with patch.dict(os.environ, env_vars):
            service_config = ServiceConfig()
            assert service_config.host == "0.0.0.0"
            assert service_config.port == 8001
            assert service_config.log_level == "DEBUG"


class TestLLMConfig:
    """Test LLM configuration."""

    def test_llm_config_defaults(self):
        """Test LLM config has defaults."""
        llm_config = LLMConfig()
        assert llm_config.model_name is not None
        assert llm_config.temperature >= 0
        assert llm_config.max_tokens > 0

    def test_llm_config_from_env(self):
        """Test LLM config from environment."""
        env_vars = {
            "LLM_MODEL_NAME": "gpt-4",
            "LLM_TEMPERATURE": "0.7",
            "LLM_MAX_TOKENS": "500",
        }
        with patch.dict(os.environ, env_vars):
            llm_config = LLMConfig()
            assert llm_config.model_name == "gpt-4"
            assert llm_config.temperature == 0.7
            assert llm_config.max_tokens == 500


class TestMainConfig:
    """Test main configuration aggregation."""

    def test_main_config_has_all_subconfigs(self):
        """Test main config has all sub-configurations."""
        assert config.feast is not None
        assert config.mlflow is not None
        assert config.postgres is not None
        assert config.s3 is not None
        assert config.kafka is not None
        assert config.training is not None
        assert config.xgboost is not None
        assert config.logistic_regression is not None
        assert config.hyperparameter_tuning is not None
        assert config.drift_detection is not None
        assert config.model_promotion is not None
        assert config.prometheus is not None
        assert config.jaeger is not None
        assert config.service is not None
        assert config.llm is not None

