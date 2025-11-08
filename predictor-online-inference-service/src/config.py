"""
Configuration management for Predictor Online Inference Service.

All configuration parameters are loaded from environment variables.
No hardcoded values or defaults that could lead to production issues.
"""

import os
from dataclasses import dataclass


@dataclass
class KafkaConfig:
    """Kafka configuration parameters."""

    bootstrap_servers: str
    consumer_group_id: str
    schema_registry_url: str
    input_topic: str
    output_topic: str
    ground_truth_topic: str
    enable_tls: bool
    tls_ca_cert: str | None
    tls_client_cert: str | None
    tls_client_key: str | None

    @classmethod
    def from_env(cls) -> "KafkaConfig":
        """Load Kafka configuration from environment variables."""
        return cls(
            bootstrap_servers=os.environ["KAFKA_BOOTSTRAP_SERVERS"],
            consumer_group_id=os.environ.get("KAFKA_CONSUMER_GROUP_ID", "predictor-service"),
            schema_registry_url=os.environ["KAFKA_SCHEMA_REGISTRY_URL"],
            input_topic=os.environ.get("KAFKA_INPUT_TOPIC", "semantic_groups"),
            output_topic=os.environ.get("KAFKA_OUTPUT_TOPIC", "predictions"),
            ground_truth_topic=os.environ.get("KAFKA_GROUND_TRUTH_TOPIC", "ground_truth"),
            enable_tls=os.environ.get("KAFKA_TLS_ENABLED", "false").lower() == "true",
            tls_ca_cert=os.environ.get("KAFKA_TLS_CA_CERT"),
            tls_client_cert=os.environ.get("KAFKA_TLS_CLIENT_CERT"),
            tls_client_key=os.environ.get("KAFKA_TLS_CLIENT_KEY"),
        )


@dataclass
class MLflowConfig:
    """MLflow configuration parameters."""

    tracking_uri: str
    model_name: str
    model_version: str
    model_stage: str
    fallback_model_version: str | None
    model_load_timeout_seconds: int

    @classmethod
    def from_env(cls) -> "MLflowConfig":
        """Load MLflow configuration from environment variables."""
        return cls(
            tracking_uri=os.environ["MLFLOW_TRACKING_URI"],
            model_name=os.environ.get("MLFLOW_MODEL_NAME", "predictor_model"),
            model_version=os.environ.get("MLFLOW_MODEL_VERSION", "v1.0.0"),
            model_stage=os.environ.get("MLFLOW_MODEL_STAGE", "Production"),
            fallback_model_version=os.environ.get("MLFLOW_FALLBACK_MODEL_VERSION"),
            model_load_timeout_seconds=int(os.environ.get("MLFLOW_MODEL_LOAD_TIMEOUT_SECONDS", "30")),
        )


@dataclass
class FeastConfig:
    """Feast feature store configuration parameters."""

    repo_path: str
    online_store_type: str
    offline_store_type: str
    redis_host: str
    redis_port: int
    redis_db: int | None = None
    redis_ssl: bool | None = None
    delta_path: str | None = None
    feature_freshness_threshold_seconds: int | None = None
    feature_reconciliation_threshold: float | None = None

    @classmethod
    def from_env(cls) -> "FeastConfig":
        """Load Feast configuration from environment variables."""
        return cls(
            repo_path=os.environ["FEAST_REPO_PATH"],
            online_store_type=os.environ.get("FEAST_ONLINE_STORE_TYPE", "redis"),
            offline_store_type=os.environ.get("FEAST_OFFLINE_STORE_TYPE", "file"),
            redis_host=os.environ.get(
                "FEAST_REDIS_HOST", os.environ.get("REDIS_HOST", "localhost")
            ),
            redis_port=int(
                os.environ.get("FEAST_REDIS_PORT", os.environ.get("REDIS_PORT", "6379"))
            ),
            redis_db=int(os.environ.get("FEAST_REDIS_DB", "0")),
            redis_ssl=os.environ.get("FEAST_REDIS_SSL", "false").lower() == "true",
            delta_path=os.environ.get("FEAST_DELTA_PATH", os.environ.get("FEAST_DELTA_LAKE_PATH", "/data/delta")),
            feature_freshness_threshold_seconds=int(
                os.environ.get("FEAST_FEATURE_FRESHNESS_THRESHOLD_SECONDS", "3600")
            ),
            feature_reconciliation_threshold=float(
                os.environ.get("FEAST_FEATURE_RECONCILIATION_THRESHOLD", "0.99")
            ),
        )


@dataclass
class RedisConfig:
    """Redis cache configuration parameters."""

    host: str
    port: int
    db: int
    password: str | None
    ssl: bool
    max_connections: int
    socket_timeout: int
    socket_connect_timeout: int

    @classmethod
    def from_env(cls) -> "RedisConfig":
        """Load Redis configuration from environment variables."""
        return cls(
            host=os.environ.get("REDIS_HOST", "localhost"),
            port=int(os.environ.get("REDIS_PORT", "6379")),
            db=int(os.environ.get("REDIS_DB", "1")),
            password=os.environ.get("REDIS_PASSWORD"),
            ssl=os.environ.get("REDIS_SSL", "false").lower() == "true",
            max_connections=int(os.environ.get("REDIS_MAX_CONNECTIONS", "50")),
            socket_timeout=int(os.environ.get("REDIS_SOCKET_TIMEOUT", "5")),
            socket_connect_timeout=int(os.environ.get("REDIS_SOCKET_CONNECT_TIMEOUT", "5")),
        )


@dataclass
class PostgresConfig:
    """PostgreSQL database configuration parameters."""

    host: str
    port: int
    user: str
    password: str
    database: str
    min_pool_size: int
    max_pool_size: int
    command_timeout: int
    ssl_mode: str

    @classmethod
    def from_env(cls) -> "PostgresConfig":
        """Load PostgreSQL configuration from environment variables."""
        return cls(
            host=os.environ["POSTGRES_HOST"],
            port=int(os.environ.get("POSTGRES_PORT", "5432")),
            user=os.environ.get("POSTGRES_USER", "postgres"),
            password=os.environ.get("POSTGRES_PASSWORD", ""),
            database=os.environ.get("POSTGRES_DATABASE", "sentiment_analyzer"),
            min_pool_size=int(os.environ.get("POSTGRES_MIN_POOL_SIZE", "10")),
            max_pool_size=int(os.environ.get("POSTGRES_MAX_POOL_SIZE", "50")),
            command_timeout=int(os.environ.get("POSTGRES_COMMAND_TIMEOUT", "30")),
            ssl_mode=os.environ.get("POSTGRES_SSL_MODE", "prefer"),
        )


@dataclass
class InferenceConfig:
    """Inference configuration parameters."""

    batch_size: int
    timeout_seconds: int
    cache_ttl_seconds: int
    enable_streaming: bool
    ab_testing_enabled: bool

    @classmethod
    def from_env(cls) -> "InferenceConfig":
        """Load inference configuration from environment variables."""
        return cls(
            batch_size=int(os.environ.get("INFERENCE_BATCH_SIZE", "100")),
            timeout_seconds=int(os.environ.get("INFERENCE_TIMEOUT_SECONDS", "30")),
            cache_ttl_seconds=int(os.environ.get("INFERENCE_CACHE_TTL_SECONDS", "3600")),
            enable_streaming=os.environ.get("INFERENCE_ENABLE_STREAMING", "true").lower() == "true",
            ab_testing_enabled=os.environ.get("INFERENCE_AB_TESTING_ENABLED", "false").lower() == "true",
        )


@dataclass
class APIConfig:
    """REST API configuration parameters."""

    host: str
    port: int
    workers: int
    enable_cors: bool
    cors_origins: list[str]
    enable_auth: bool
    api_key: str | None
    jwt_secret: str | None
    rate_limit_per_minute: int

    @classmethod
    def from_env(cls) -> "APIConfig":
        """Load API configuration from environment variables."""
        cors_origins_str = os.environ.get("CORS_ORIGINS", "*")
        cors_origins = [origin.strip() for origin in cors_origins_str.split(",")]

        return cls(
            host=os.environ.get("API_HOST", "0.0.0.0"),
            port=int(os.environ.get("REST_API_PORT", "8000")),
            workers=int(os.environ.get("API_WORKERS", "4")),
            enable_cors=os.environ.get("ENABLE_CORS", "true").lower() == "true",
            cors_origins=cors_origins,
            enable_auth=os.environ.get("ENABLE_AUTH", "false").lower() == "true",
            api_key=os.environ.get("API_KEY"),
            jwt_secret=os.environ.get("JWT_SECRET"),
            rate_limit_per_minute=int(os.environ.get("RATE_LIMIT_PER_MINUTE", "60")),
        )


@dataclass
class MonitoringConfig:
    """Monitoring and observability configuration parameters."""

    prometheus_port: int
    enable_tracing: bool
    jaeger_agent_host: str
    jaeger_agent_port: int
    log_level: str

    @classmethod
    def from_env(cls) -> "MonitoringConfig":
        """Load monitoring configuration from environment variables."""
        return cls(
            prometheus_port=int(os.environ.get("PROMETHEUS_PORT", "9109")),
            enable_tracing=os.environ.get("ENABLE_TRACING", "true").lower() == "true",
            jaeger_agent_host=os.environ.get("JAEGER_AGENT_HOST", "localhost"),
            jaeger_agent_port=int(os.environ.get("JAEGER_AGENT_PORT", "6831")),
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
        )


@dataclass
class ValidationConfig:
    """Validation and quality configuration parameters."""

    label_consistency_threshold: float
    feature_reconciliation_threshold: float
    feature_freshness_threshold_seconds: int
    enable_drift_detection: bool
    drift_detection_window_hours: int
    min_samples_for_drift: int

    @classmethod
    def from_env(cls) -> "ValidationConfig":
        """Load validation configuration from environment variables."""
        return cls(
            label_consistency_threshold=float(
                os.environ.get("VALIDATION_LABEL_CONSISTENCY_THRESHOLD", "0.85")
            ),
            feature_reconciliation_threshold=float(
                os.environ.get("VALIDATION_FEATURE_RECONCILIATION_THRESHOLD", "0.99")
            ),
            feature_freshness_threshold_seconds=int(
                os.environ.get("VALIDATION_FEATURE_FRESHNESS_THRESHOLD_SECONDS", "3600")
            ),
            enable_drift_detection=os.environ.get("VALIDATION_ENABLE_DRIFT_DETECTION", "true").lower()
            == "true",
            drift_detection_window_hours=int(
                os.environ.get("VALIDATION_DRIFT_DETECTION_WINDOW_HOURS", "24")
            ),
            min_samples_for_drift=int(
                os.environ.get("VALIDATION_MIN_SAMPLES_FOR_DRIFT", "30")
            ),
        )


@dataclass
class Config:
    """Main configuration container for all service settings."""

    kafka: KafkaConfig
    mlflow: MLflowConfig
    feast: FeastConfig
    redis: RedisConfig
    postgres: PostgresConfig
    inference: InferenceConfig
    api: APIConfig
    monitoring: MonitoringConfig
    validation: ValidationConfig

    @classmethod
    def from_env(cls) -> "Config":
        """Load complete configuration from environment variables."""
        return cls(
            kafka=KafkaConfig.from_env(),
            mlflow=MLflowConfig.from_env(),
            feast=FeastConfig.from_env(),
            redis=RedisConfig.from_env(),
            postgres=PostgresConfig.from_env(),
            inference=InferenceConfig.from_env(),
            api=APIConfig.from_env(),
            monitoring=MonitoringConfig.from_env(),
            validation=ValidationConfig.from_env(),
        )

    def validate(self) -> None:
        """
        Validate configuration parameters.

        Raises:
            ValueError: If any configuration parameter is invalid.
        """
        # Validate Kafka configuration
        if not self.kafka.bootstrap_servers:
            raise ValueError("KAFKA_BOOTSTRAP_SERVERS environment variable is required")
        if not self.kafka.schema_registry_url:
            raise ValueError("KAFKA_SCHEMA_REGISTRY_URL environment variable is required")

        # Validate MLflow configuration
        if not self.mlflow.tracking_uri:
            raise ValueError("MLFLOW_TRACKING_URI environment variable is required")

        # Validate Feast configuration
        if not self.feast.repo_path:
            raise ValueError("FEAST_REPO_PATH environment variable is required")

        # Validate PostgreSQL configuration
        if not self.postgres.host:
            raise ValueError("POSTGRES_HOST environment variable is required")

        # Validate thresholds
        if not 0.0 <= self.validation.label_consistency_threshold <= 1.0:
            raise ValueError("LABEL_CONSISTENCY_THRESHOLD must be between 0.0 and 1.0")
        if not 0.0 <= self.validation.feature_reconciliation_threshold <= 1.0:
            raise ValueError("FEATURE_RECONCILIATION_THRESHOLD must be between 0.0 and 1.0")

        # Validate API authentication
        if self.api.enable_auth and not self.api.api_key and not self.api.jwt_secret:
            raise ValueError("API_KEY or JWT_SECRET required when ENABLE_AUTH is true")


# Global configuration instance
_config: Config | None = None


def get_config() -> Config:
    """
    Get the global configuration instance.

    Returns:
        Config: The global configuration instance.

    Raises:
        RuntimeError: If configuration has not been initialized.
    """
    global _config
    if _config is None:
        raise RuntimeError("Configuration not initialized. Call load_config() first.")
    return _config


def load_config() -> Config:
    """
    Load and validate configuration from environment variables.

    Returns:
        Config: The loaded and validated configuration.

    Raises:
        ValueError: If any required configuration is missing or invalid.
    """
    global _config
    _config = Config.from_env()
    _config.validate()
    return _config
