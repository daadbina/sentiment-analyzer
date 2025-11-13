"""
Configuration management for Trainer & Model Registry Service.

All configuration parameters are externalized to environment variables
using Pydantic BaseSettings. No hardcoded values are allowed.
"""

from typing import Optional
from pydantic import Field, field_validator, ConfigDict
from pydantic_settings import BaseSettings


class FeastConfig(BaseSettings):
    """Feast feature store configuration - uses remote HTTP API only."""

    model_config = ConfigDict(extra="ignore", env_file=".env", case_sensitive=True)

    server_url: str = Field(
        default="http://154.53.166.231:6566",
        alias="FEAST_SERVER_URL",
        description="URL of remote Feast feature server",
    )
    timeout: int = Field(
        default=30,
        alias="FEAST_TIMEOUT",
        description="Timeout for Feast HTTP requests in seconds",
    )


class MLflowConfig(BaseSettings):
    """MLflow model registry configuration."""

    model_config = ConfigDict(extra="ignore", env_file=".env", case_sensitive=True)

    tracking_uri: str = Field(
        default="http://localhost:5000",
        alias="MLFLOW_TRACKING_URI",
        description="MLflow tracking server URI",
    )
    artifact_store: str = Field(
        default="s3://sentiment-analyzer/mlflow",
        alias="MLFLOW_ARTIFACT_STORE",
        description="MLflow artifact store path",
    )
    registry_uri: str = Field(
        default="http://localhost:5000",
        alias="MLFLOW_REGISTRY_URI",
        description="MLflow model registry URI",
    )


class S3Config(BaseSettings):
    """AWS S3 configuration."""

    model_config = ConfigDict(extra="ignore", env_file=".env", case_sensitive=True)

    bucket: str = Field(
        default="sentiment-analyzer-models",
        alias="S3_BUCKET",
        description="S3 bucket for model artifacts",
    )
    region: str = Field(
        default="us-east-1", alias="S3_REGION", description="AWS region"
    )
    access_key_id: str = Field(
        default="minioadmin", alias="S3_ACCESS_KEY_ID", description="S3 access key ID"
    )
    secret_access_key: str = Field(
        default="minioadmin",
        alias="S3_SECRET_ACCESS_KEY",
        description="S3 secret access key",
    )
    endpoint_url: Optional[str] = Field(
        default="http://localhost:9000",
        alias="S3_ENDPOINT_URL",
        description="S3 endpoint URL (for LocalStack)",
    )


class PostgreSQLConfig(BaseSettings):
    """PostgreSQL database configuration."""

    model_config = ConfigDict(extra="ignore", env_file=".env", case_sensitive=True)

    host: str = Field(
        default="154.53.166.231", alias="POSTGRES_HOST", description="PostgreSQL host"
    )
    port: int = Field(
        default=5432, alias="POSTGRES_PORT", description="PostgreSQL port"
    )
    user: str = Field(
        default="adminsentiment",
        alias="POSTGRES_USER",
        description="PostgreSQL username",
    )
    password: str = Field(
        default="wp2400!!!!",
        alias="POSTGRES_PASSWORD",
        description="PostgreSQL password",
    )
    database: str = Field(
        default="sentiment",
        alias="POSTGRES_DATABASE",
        description="PostgreSQL database name",
    )
    pool_size: int = Field(
        default=10, alias="POSTGRES_POOL_SIZE", description="Connection pool size"
    )
    max_overflow: int = Field(
        default=20,
        alias="POSTGRES_MAX_OVERFLOW",
        description="Maximum overflow connections",
    )
    pool_timeout: int = Field(
        default=30, alias="POSTGRES_POOL_TIMEOUT", description="Pool timeout in seconds"
    )
    pool_recycle: int = Field(
        default=3600,
        alias="POSTGRES_POOL_RECYCLE",
        description="Pool recycle time in seconds",
    )

    @property
    def dsn(self) -> str:
        """Generate PostgreSQL DSN."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


class KafkaConfig(BaseSettings):
    """Kafka configuration."""

    model_config = ConfigDict(extra="ignore", env_file=".env", case_sensitive=True)

    bootstrap_servers: str = Field(
        default="154.53.166.231:9092",
        alias="KAFKA_BOOTSTRAP_SERVERS",
        description="Kafka bootstrap servers",
    )
    schema_registry_url: str = Field(
        default="http://154.53.166.231:8081",
        alias="KAFKA_SCHEMA_REGISTRY_URL",
        description="Schema Registry URL",
    )
    consumer_group: str = Field(
        default="trainer-service",
        alias="KAFKA_CONSUMER_GROUP",
        description="Kafka consumer group",
    )
    security_protocol: str = Field(
        default="PLAINTEXT",
        alias="KAFKA_SECURITY_PROTOCOL",
        description="Kafka security protocol",
    )


class TrainingConfig(BaseSettings):
    """Training pipeline configuration."""

    model_config = ConfigDict(extra="ignore", env_file=".env", case_sensitive=True)

    prediction_task: str = Field(
        default="btc_price_spike",
        alias="PREDICTION_TASK",
        description="Prediction task: 'news_realization' or 'btc_price_spike'",
    )
    window_months: int = Field(
        default=18,
        alias="TRAINING_WINDOW_MONTHS",
        description="Training data window in months",
    )
    test_set_size: float = Field(
        default=0.2, alias="TEST_SET_SIZE", description="Test set ratio"
    )
    validation_set_size: float = Field(
        default=0.1, alias="VALIDATION_SET_SIZE", description="Validation set ratio"
    )
    random_seed: int = Field(
        default=42, alias="RANDOM_SEED", description="Random seed for reproducibility"
    )

    @field_validator("prediction_task")
    @classmethod
    def validate_prediction_task(cls, v: str) -> str:
        """Validate prediction task is valid."""
        valid_tasks = ["news_realization", "btc_price_spike"]
        if v not in valid_tasks:
            raise ValueError(f"Prediction task must be one of {valid_tasks}, got {v}")
        return v

    @field_validator("test_set_size", "validation_set_size")
    @classmethod
    def validate_split_sizes(cls, v: float) -> float:
        """Validate split sizes are between 0 and 1."""
        if not 0 < v < 1:
            raise ValueError("Split size must be between 0 and 1")
        return v


class XGBoostConfig(BaseSettings):
    """XGBoost model configuration."""

    model_config = ConfigDict(extra="ignore", env_file=".env", case_sensitive=True)

    max_depth: int = Field(
        default=6, alias="XGBOOST_MAX_DEPTH", description="Maximum tree depth"
    )
    learning_rate: float = Field(
        default=0.1, alias="XGBOOST_LEARNING_RATE", description="Learning rate"
    )
    n_estimators: int = Field(
        default=100,
        alias="XGBOOST_N_ESTIMATORS",
        description="Number of boosting rounds",
    )
    subsample: float = Field(
        default=0.8, alias="XGBOOST_SUBSAMPLE", description="Subsample ratio"
    )
    colsample_bytree: float = Field(
        default=0.8,
        alias="XGBOOST_COLSAMPLE_BYTREE",
        description="Column sample by tree ratio",
    )
    early_stopping_rounds: int = Field(
        default=10,
        alias="XGBOOST_EARLY_STOPPING_ROUNDS",
        description="Early stopping rounds",
    )
    eval_metric: str = Field(
        default="auc", alias="XGBOOST_EVAL_METRIC", description="Evaluation metric"
    )


class LogisticRegressionConfig(BaseSettings):
    """Logistic Regression model configuration."""

    model_config = ConfigDict(extra="ignore", env_file=".env", case_sensitive=True)

    C: float = Field(
        default=1.0,
        alias="LOGISTIC_REGRESSION_C",
        description="Inverse regularization strength",
    )
    penalty: str = Field(
        default="l2",
        alias="LOGISTIC_REGRESSION_PENALTY",
        description="Penalty type (l1, l2, elasticnet)",
    )
    solver: str = Field(
        default="lbfgs",
        alias="LOGISTIC_REGRESSION_SOLVER",
        description="Solver algorithm",
    )
    max_iter: int = Field(
        default=1000,
        alias="LOGISTIC_REGRESSION_MAX_ITER",
        description="Maximum iterations",
    )


class FeatureEngineeringConfig(BaseSettings):
    """Feature engineering configuration."""

    model_config = ConfigDict(extra="ignore", env_file=".env", case_sensitive=True)

    enable_interaction_features: bool = Field(
        default=True,
        alias="FEATURE_ENGINEERING_INTERACTION_ENABLED",
        description="Enable interaction feature generation",
    )
    enable_polynomial_features: bool = Field(
        default=True,
        alias="FEATURE_ENGINEERING_POLYNOMIAL_ENABLED",
        description="Enable polynomial feature generation",
    )
    polynomial_degree: int = Field(
        default=2,
        alias="FEATURE_ENGINEERING_POLYNOMIAL_DEGREE",
        description="Degree for polynomial features",
    )


class RandomForestConfig(BaseSettings):
    """Random Forest model configuration."""

    model_config = ConfigDict(extra="ignore", env_file=".env", case_sensitive=True)

    n_estimators: int = Field(
        default=100,
        alias="RANDOM_FOREST_N_ESTIMATORS",
        description="Number of trees",
    )
    max_depth: int = Field(
        default=10,
        alias="RANDOM_FOREST_MAX_DEPTH",
        description="Maximum tree depth",
    )
    min_samples_split: int = Field(
        default=5,
        alias="RANDOM_FOREST_MIN_SAMPLES_SPLIT",
        description="Minimum samples to split",
    )
    min_samples_leaf: int = Field(
        default=2,
        alias="RANDOM_FOREST_MIN_SAMPLES_LEAF",
        description="Minimum samples per leaf",
    )
    class_weight: str = Field(
        default="balanced",
        alias="RANDOM_FOREST_CLASS_WEIGHT",
        description="Class weight strategy",
    )


class GradientBoostingConfig(BaseSettings):
    """Gradient Boosting model configuration."""

    model_config = ConfigDict(extra="ignore", env_file=".env", case_sensitive=True)

    n_estimators: int = Field(
        default=100,
        alias="GRADIENT_BOOSTING_N_ESTIMATORS",
        description="Number of boosting stages",
    )
    learning_rate: float = Field(
        default=0.1,
        alias="GRADIENT_BOOSTING_LEARNING_RATE",
        description="Learning rate",
    )
    max_depth: int = Field(
        default=5,
        alias="GRADIENT_BOOSTING_MAX_DEPTH",
        description="Maximum tree depth",
    )
    min_samples_split: int = Field(
        default=5,
        alias="GRADIENT_BOOSTING_MIN_SAMPLES_SPLIT",
        description="Minimum samples to split",
    )
    min_samples_leaf: int = Field(
        default=2,
        alias="GRADIENT_BOOSTING_MIN_SAMPLES_LEAF",
        description="Minimum samples per leaf",
    )
    subsample: float = Field(
        default=0.8,
        alias="GRADIENT_BOOSTING_SUBSAMPLE",
        description="Subsample ratio",
    )


class VotingEnsembleConfig(BaseSettings):
    """Voting Ensemble configuration."""

    model_config = ConfigDict(extra="ignore", env_file=".env", case_sensitive=True)

    voting: str = Field(
        default="soft",
        alias="VOTING_ENSEMBLE_VOTING",
        description="Voting method (hard or soft)",
    )
    enable_xgboost: bool = Field(
        default=True,
        alias="VOTING_ENSEMBLE_XGBOOST_ENABLED",
        description="Include XGBoost in ensemble",
    )
    enable_logistic_regression: bool = Field(
        default=True,
        alias="VOTING_ENSEMBLE_LOGISTIC_REGRESSION_ENABLED",
        description="Include Logistic Regression in ensemble",
    )
    enable_random_forest: bool = Field(
        default=True,
        alias="VOTING_ENSEMBLE_RANDOM_FOREST_ENABLED",
        description="Include Random Forest in ensemble",
    )
    enable_gradient_boosting: bool = Field(
        default=True,
        alias="VOTING_ENSEMBLE_GRADIENT_BOOSTING_ENABLED",
        description="Include Gradient Boosting in ensemble",
    )


class HyperparameterTuningConfig(BaseSettings):
    """Hyperparameter tuning configuration."""

    model_config = ConfigDict(extra="ignore", env_file=".env", case_sensitive=True)

    enabled: bool = Field(
        default=True,
        alias="HYPERPARAMETER_TUNING_ENABLED",
        description="Enable hyperparameter tuning",
    )
    trials: int = Field(
        default=50,
        alias="HYPERPARAMETER_TUNING_TRIALS",
        description="Number of Optuna trials",
    )
    timeout: int = Field(
        default=3600,
        alias="HYPERPARAMETER_TUNING_TIMEOUT",
        description="Tuning timeout in seconds",
    )
    n_jobs: int = Field(
        default=4,
        alias="HYPERPARAMETER_TUNING_N_JOBS",
        description="Number of parallel jobs",
    )


class DriftDetectionConfig(BaseSettings):
    """Drift detection configuration."""

    model_config = ConfigDict(extra="ignore", env_file=".env", case_sensitive=True)

    enabled: bool = Field(
        default=True,
        alias="DRIFT_DETECTION_ENABLED",
        description="Enable drift detection",
    )
    threshold: float = Field(
        default=0.1,
        alias="DRIFT_DETECTION_THRESHOLD",
        description="Drift detection threshold",
    )
    reference_window: int = Field(
        default=30,
        alias="DRIFT_DETECTION_REFERENCE_WINDOW",
        description="Reference window in days",
    )


class ModelPromotionConfig(BaseSettings):
    """Model promotion configuration."""

    model_config = ConfigDict(extra="ignore", env_file=".env", case_sensitive=True)

    threshold_auc: float = Field(
        default=0.75,
        alias="MODEL_PROMOTION_THRESHOLD_AUC",
        description="AUC threshold for promotion",
    )
    threshold_precision: float = Field(
        default=0.70,
        alias="MODEL_PROMOTION_THRESHOLD_PRECISION",
        description="Precision threshold for promotion",
    )
    threshold_f1: float = Field(
        default=0.70,
        alias="MODEL_PROMOTION_THRESHOLD_F1",
        description="F1 threshold for promotion",
    )


class PrometheusConfig(BaseSettings):
    """Prometheus monitoring configuration."""

    model_config = ConfigDict(extra="ignore", env_file=".env", case_sensitive=True)

    port: int = Field(
        default=9108, alias="PROMETHEUS_PORT", description="Prometheus metrics port"
    )
    enabled: bool = Field(
        default=True,
        alias="PROMETHEUS_ENABLED",
        description="Enable Prometheus metrics",
    )


class JaegerConfig(BaseSettings):
    """Jaeger tracing configuration."""

    model_config = ConfigDict(extra="ignore", env_file=".env", case_sensitive=True)

    enabled: bool = Field(
        default=True, alias="JAEGER_ENABLED", description="Enable Jaeger tracing"
    )
    agent_host: str = Field(
        default="localhost", alias="JAEGER_AGENT_HOST", description="Jaeger agent host"
    )
    agent_port: int = Field(
        default=6831, alias="JAEGER_AGENT_PORT", description="Jaeger agent port"
    )
    sampler_type: str = Field(
        default="const", alias="JAEGER_SAMPLER_TYPE", description="Jaeger sampler type"
    )
    sampler_param: float = Field(
        default=1.0,
        alias="JAEGER_SAMPLER_PARAM",
        description="Jaeger sampler parameter",
    )


class ServiceConfig(BaseSettings):
    """Service configuration."""

    model_config = ConfigDict(extra="ignore", env_file=".env", case_sensitive=True)

    name: str = Field(
        default="trainer-model-registry-service",
        alias="SERVICE_NAME",
        description="Service name",
    )
    version: str = Field(
        default="1.0.0", alias="SERVICE_VERSION", description="Service version"
    )
    port: int = Field(default=8008, alias="SERVICE_PORT", description="Service port")
    host: str = Field(
        default="0.0.0.0", alias="SERVICE_HOST", description="Service host"
    )
    log_level: str = Field(
        default="INFO", alias="LOG_LEVEL", description="Logging level"
    )
    debug: bool = Field(default=False, alias="DEBUG", description="Debug mode")


class LLMConfig(BaseSettings):
    """LLM configuration."""

    model_config = ConfigDict(extra="ignore", env_file=".env", case_sensitive=True)

    api_key: str = Field(
        default="sk-your-api-key-here",
        alias="OPENAI_API_KEY",
        description="OpenAI API key",
    )
    model_name: str = Field(
        default="gpt-4", alias="OPENAI_MODEL", description="OpenAI model name"
    )
    temperature: float = Field(
        default=0.7, alias="LLM_TEMPERATURE", description="LLM temperature"
    )
    max_tokens: int = Field(
        default=500,
        alias="LLM_MAX_TOKENS",
        description="Maximum tokens for LLM response",
    )


class Config(BaseSettings):
    """Main configuration class aggregating all sub-configs."""

    model_config = ConfigDict(extra="ignore", env_file=".env", case_sensitive=True)

    feast: FeastConfig = FeastConfig()
    mlflow: MLflowConfig = MLflowConfig()
    s3: S3Config = S3Config()
    postgres: PostgreSQLConfig = PostgreSQLConfig()
    kafka: KafkaConfig = KafkaConfig()
    training: TrainingConfig = TrainingConfig()
    xgboost: XGBoostConfig = XGBoostConfig()
    logistic_regression: LogisticRegressionConfig = LogisticRegressionConfig()
    feature_engineering: FeatureEngineeringConfig = FeatureEngineeringConfig()
    random_forest: RandomForestConfig = RandomForestConfig()
    gradient_boosting: GradientBoostingConfig = GradientBoostingConfig()
    voting_ensemble: VotingEnsembleConfig = VotingEnsembleConfig()
    hyperparameter_tuning: HyperparameterTuningConfig = HyperparameterTuningConfig()
    drift_detection: DriftDetectionConfig = DriftDetectionConfig()
    model_promotion: ModelPromotionConfig = ModelPromotionConfig()
    prometheus: PrometheusConfig = PrometheusConfig()
    jaeger: JaegerConfig = JaegerConfig()
    service: ServiceConfig = ServiceConfig()
    llm: LLMConfig = LLMConfig()


# Global config instance
config = Config()
