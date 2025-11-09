"""Configuration management for labeler-ground-truth-ingest-service."""

from pydantic import Field, field_validator, ConfigDict
from pydantic_settings import BaseSettings
from typing import Optional


class KafkaSettings(BaseSettings):
    """Kafka configuration."""

    brokers: str = Field(
        default="154.53.166.231:9092",
        alias="KAFKA_BROKERS",
        description="Kafka bootstrap servers"
    )
    consumer_group: str = Field(
        default="labeler-ground-truth-ingest-service",
        alias="KAFKA_CONSUMER_GROUP",
        description="Kafka consumer group"
    )
    schema_registry_url: str = Field(
        default="http://154.53.166.231:8081",
        alias="KAFKA_SCHEMA_REGISTRY_URL",
        description="Schema Registry endpoint"
    )
    ground_truth_topic: str = Field(
        default="ground_truth",
        alias="KAFKA_GROUND_TRUTH_TOPIC",
        description="Kafka topic for ground truth labels"
    )
    semantic_groups_topic: str = Field(
        default="semantic_groups",
        alias="KAFKA_SEMANTIC_GROUPS_TOPIC",
        description="Kafka topic for semantic groups"
    )
    max_poll_interval_ms: int = Field(
        default=900000,
        alias="KAFKA_MAX_POLL_INTERVAL_MS",
        description="Maximum poll interval in milliseconds (15 minutes default)"
    )
    producer_batch_size: int = Field(
        default=1000,
        alias="KAFKA_PRODUCER_BATCH_SIZE",
        description="Number of messages to produce before flushing"
    )
    consumer_max_retries: int = Field(
        default=10,
        alias="KAFKA_CONSUMER_MAX_RETRIES",
        description="Maximum retries for partition assignment"
    )
    consumer_max_consecutive_timeouts: int = Field(
        default=5,
        alias="KAFKA_CONSUMER_MAX_CONSECUTIVE_TIMEOUTS",
        description="Maximum consecutive poll timeouts before breaking"
    )
    consumer_max_polls: int = Field(
        default=20,
        alias="KAFKA_CONSUMER_MAX_POLLS",
        description="Maximum number of polls per consume_batch call"
    )
    consumer_poll_timeout_ms: int = Field(
        default=5000,
        alias="KAFKA_CONSUMER_POLL_TIMEOUT_MS",
        description="Timeout in milliseconds per poll"
    )
    consumer_partition_wait_ms: int = Field(
        default=1000,
        alias="KAFKA_CONSUMER_PARTITION_WAIT_MS",
        description="Wait time in milliseconds for partition assignment"
    )
    consumer_batch_commit_interval: int = Field(
        default=100,
        alias="KAFKA_CONSUMER_BATCH_COMMIT_INTERVAL",
        description="Commit offset every N messages"
    )
    consumer_auto_commit_enabled: bool = Field(
        default=False,
        alias="KAFKA_CONSUMER_AUTO_COMMIT_ENABLED",
        description="Enable automatic offset commits"
    )
    consumer_auto_commit_interval_ms: int = Field(
        default=5000,
        alias="KAFKA_CONSUMER_AUTO_COMMIT_INTERVAL_MS",
        description="Auto-commit interval in milliseconds"
    )

    model_config = ConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


class PostgreSQLSettings(BaseSettings):
    """PostgreSQL configuration."""

    host: str = Field(
        default="154.53.166.231",
        alias="POSTGRES_HOST",
        description="PostgreSQL host"
    )
    port: int = Field(
        default=5432,
        alias="POSTGRES_PORT",
        description="PostgreSQL port"
    )
    user: str = Field(
        default="adminsentiment",
        alias="POSTGRES_USER",
        description="PostgreSQL username"
    )
    password: str = Field(
        default="wp2400!!!!",
        alias="POSTGRES_PASSWORD",
        description="PostgreSQL password"
    )
    database: str = Field(
        default="sentiment",
        alias="POSTGRES_DATABASE",
        description="PostgreSQL database"
    )
    pool_size: int = Field(
        default=20,
        alias="POSTGRES_POOL_SIZE",
        description="Connection pool size"
    )
    max_overflow: int = Field(
        default=10,
        alias="POSTGRES_MAX_OVERFLOW",
        description="Maximum overflow connections"
    )

    @property
    def dsn(self) -> str:
        """Get PostgreSQL DSN."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

    model_config = ConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


class ACLEDSettings(BaseSettings):
    """ACLED API configuration."""

    api_url: str = Field(
        default="https://acleddata.com/api",
        alias="ACLED_API_URL",
        description="ACLED API base URL"
    )
    api_key: str = Field(
        default="",
        alias="ACLED_API_KEY",
        description="ACLED API key (deprecated, use OAuth)"
    )
    oauth_url: str = Field(
        default="https://acleddata.com/oauth/token",
        alias="ACLED_OAUTH_URL",
        description="ACLED OAuth token endpoint"
    )
    username: str = Field(
        default="",
        alias="ACLED_USERNAME",
        description="ACLED username (email)"
    )
    password: str = Field(
        default="",
        alias="ACLED_PASSWORD",
        description="ACLED password"
    )
    access_token: Optional[str] = Field(
        default=None,
        alias="ACLED_ACCESS_TOKEN",
        description="ACLED access token (cached)"
    )
    token_expires_at: Optional[float] = Field(
        default=None,
        alias="ACLED_TOKEN_EXPIRES_AT",
        description="ACLED token expiration timestamp"
    )
    fetch_interval_hours: int = Field(
        default=24,
        alias="ACLED_FETCH_INTERVAL_HOURS",
        description="ACLED fetch frequency in hours"
    )
    backup_api_url: Optional[str] = Field(
        default=None,
        alias="ACLED_BACKUP_API_URL",
        description="ACLED backup API endpoint"
    )

    model_config = ConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


class GDELTSettings(BaseSettings):
    """GDELT API configuration."""

    api_url: str = Field(
        default="https://api.gdeltproject.org",
        alias="GDELT_API_URL",
        description="GDELT API endpoint"
    )
    fetch_interval_hours: int = Field(
        default=1,
        alias="GDELT_FETCH_INTERVAL_HOURS",
        description="GDELT fetch frequency in hours"
    )
    backup_api_url: Optional[str] = Field(
        default=None,
        alias="GDELT_BACKUP_API_URL",
        description="GDELT backup API endpoint"
    )

    model_config = ConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


class BinanceSettings(BaseSettings):
    """Binance API configuration (free alternative to CoinGecko)."""

    api_url: str = Field(
        default="https://api.binance.com/api/v3",
        alias="BINANCE_API_URL",
        description="Binance API endpoint"
    )
    symbols: str = Field(
        default="BTCUSDT,ETHUSDT,BNBUSDT",
        alias="BINANCE_SYMBOLS",
        description="Comma-separated list of trading symbols"
    )
    interval: str = Field(
        default="1h",
        alias="BINANCE_INTERVAL",
        description="Kline interval (1m, 5m, 15m, 30m, 1h, 4h, 1d, etc.)"
    )
    limit: int = Field(
        default=1000,
        alias="BINANCE_LIMIT",
        description="Maximum number of klines to fetch per symbol"
    )
    fetch_interval_minutes: int = Field(
        default=5,
        alias="BINANCE_FETCH_INTERVAL_MINUTES",
        description="Binance fetch frequency in minutes"
    )
    backup_api_url: Optional[str] = Field(
        default=None,
        alias="BINANCE_BACKUP_API_URL",
        description="Binance backup API endpoint"
    )

    model_config = ConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


class CCXTSettings(BaseSettings):
    """CCXT API configuration (fallback for crypto data)."""

    enabled: bool = Field(
        default=True,
        alias="CCXT_ENABLED",
        description="Enable CCXT as fallback provider"
    )
    exchanges: str = Field(
        default="kraken,coinbase,bybit",
        alias="CCXT_EXCHANGES",
        description="Comma-separated list of CCXT exchanges to try as fallback"
    )
    symbols: str = Field(
        default="BTC/USD,ETH/USD,BNB/USD",
        alias="CCXT_SYMBOLS",
        description="Comma-separated list of trading symbols for CCXT"
    )
    timeframe: str = Field(
        default="1h",
        alias="CCXT_TIMEFRAME",
        description="Timeframe for CCXT klines (1m, 5m, 15m, 30m, 1h, 4h, 1d, etc.)"
    )
    limit: int = Field(
        default=1000,
        alias="CCXT_LIMIT",
        description="Maximum number of klines to fetch per symbol"
    )
    fetch_interval_minutes: int = Field(
        default=5,
        alias="CCXT_FETCH_INTERVAL_MINUTES",
        description="CCXT fetch frequency in minutes"
    )

    model_config = ConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


class LabelSettings(BaseSettings):
    """Label configuration."""

    reconciliation_threshold_hours: int = Field(
        default=48,
        alias="LABEL_RECONCILIATION_THRESHOLD_HOURS",
        description="Temporal matching threshold in hours"
    )
    confidence_threshold: float = Field(
        default=0.7,
        alias="LABEL_CONFIDENCE_THRESHOLD",
        description="Minimum label confidence"
    )
    temporal_threshold_hours: int = Field(
        default=24,
        alias="LABEL_TEMPORAL_THRESHOLD_HOURS",
        description="Temporal threshold for R8 validation"
    )
    freshness_acled_hours: int = Field(
        default=24,
        alias="LABEL_FRESHNESS_ACLED_HOURS",
        description="ACLED freshness threshold in hours"
    )
    freshness_gdelt_hours: int = Field(
        default=1,
        alias="LABEL_FRESHNESS_GDELT_HOURS",
        description="GDELT freshness threshold in hours"
    )
    freshness_binance_minutes: int = Field(
        default=5,
        alias="LABEL_FRESHNESS_BINANCE_MINUTES",
        description="Binance freshness threshold in minutes"
    )
    min_semantic_groups_threshold: int = Field(
        default=50,
        alias="LABEL_MIN_SEMANTIC_GROUPS_THRESHOLD",
        description="Minimum number of semantic groups required before starting deduplication and reconciliation"
    )

    model_config = ConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


class StorageSettings(BaseSettings):
    """Storage configuration."""

    delta_lake_path: str = Field(
        default="/data/delta_lake/ground_truth",
        alias="DELTA_LAKE_PATH",
        description="Delta Lake path for ground truth labels"
    )
    delta_lake_backup_path: str = Field(
        default="/data/delta_lake/backup",
        alias="DELTA_LAKE_BACKUP_PATH",
        description="Delta Lake backup path"
    )

    model_config = ConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


class MetricsSettings(BaseSettings):
    """Metrics configuration."""

    prometheus_port: int = Field(
        default=9107,
        alias="PROMETHEUS_PORT",
        description="Prometheus metrics port"
    )
    prometheus_metrics_enabled: bool = Field(
        default=True,
        alias="PROMETHEUS_METRICS_ENABLED",
        description="Enable Prometheus metrics"
    )

    model_config = ConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


class TracingSettings(BaseSettings):
    """Tracing configuration."""

    jaeger_enabled: bool = Field(
        default=True,
        alias="JAEGER_ENABLED",
        description="Enable Jaeger tracing"
    )
    jaeger_agent_host: str = Field(
        default="localhost",
        alias="JAEGER_AGENT_HOST",
        description="Jaeger agent host"
    )
    jaeger_agent_port: int = Field(
        default=6831,
        alias="JAEGER_AGENT_PORT",
        description="Jaeger agent port"
    )
    jaeger_sampler_type: str = Field(
        default="const",
        alias="JAEGER_SAMPLER_TYPE",
        description="Jaeger sampler type"
    )
    jaeger_sampler_param: float = Field(
        default=1.0,
        alias="JAEGER_SAMPLER_PARAM",
        description="Jaeger sampler parameter"
    )

    model_config = ConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


class LoggingSettings(BaseSettings):
    """Logging configuration."""

    log_level: str = Field(
        default="INFO",
        alias="LOG_LEVEL",
        description="Logging level"
    )
    log_format: str = Field(
        default="json",
        alias="LOG_FORMAT",
        description="Logging format (json or text)"
    )

    model_config = ConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


class ServiceSettings(BaseSettings):
    """Service configuration."""

    service_name: str = Field(
        default="labeler-ground-truth-ingest-service",
        alias="SERVICE_NAME",
        description="Service name"
    )
    service_version: str = Field(
        default="1.0.0",
        alias="SERVICE_VERSION",
        description="Service version"
    )
    environment: str = Field(
        default="development",
        alias="ENVIRONMENT",
        description="Environment (development, staging, production)"
    )
    debug: bool = Field(
        default=False,
        alias="DEBUG",
        description="Debug mode"
    )

    model_config = ConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


class APIClientSettings(BaseSettings):
    """API client configuration."""

    timeout_seconds: int = Field(
        default=30,
        alias="API_CLIENT_TIMEOUT_SECONDS",
        description="API client timeout in seconds"
    )
    retry_max_attempts: int = Field(
        default=3,
        alias="API_CLIENT_RETRY_MAX_ATTEMPTS",
        description="Maximum retry attempts"
    )
    retry_backoff_factor: float = Field(
        default=2.0,
        alias="API_CLIENT_RETRY_BACKOFF_FACTOR",
        description="Retry backoff factor"
    )
    circuit_breaker_threshold: int = Field(
        default=5,
        alias="API_CLIENT_CIRCUIT_BREAKER_THRESHOLD",
        description="Circuit breaker failure threshold"
    )
    circuit_breaker_timeout_seconds: int = Field(
        default=60,
        alias="API_CLIENT_CIRCUIT_BREAKER_TIMEOUT_SECONDS",
        description="Circuit breaker timeout in seconds"
    )

    model_config = ConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


class ReconciliationSettings(BaseSettings):
    """Reconciliation configuration."""

    batch_size: int = Field(
        default=100,
        alias="RECONCILIATION_BATCH_SIZE",
        description="Reconciliation batch size"
    )
    timeout_seconds: int = Field(
        default=300,
        alias="RECONCILIATION_TIMEOUT_SECONDS",
        description="Reconciliation timeout in seconds"
    )
    confidence_threshold: float = Field(
        default=0.65,
        alias="RECONCILIATION_CONFIDENCE_THRESHOLD",
        description="Reconciliation confidence threshold (0.65 to filter out low-confidence matches)"
    )

    model_config = ConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


class ValidationSettings(BaseSettings):
    """Validation configuration."""

    batch_size: int = Field(
        default=100,
        alias="VALIDATION_BATCH_SIZE",
        description="Validation batch size"
    )
    timeout_seconds: int = Field(
        default=300,
        alias="VALIDATION_TIMEOUT_SECONDS",
        description="Validation timeout in seconds"
    )
    enable_license_check: bool = Field(
        default=True,
        alias="VALIDATION_ENABLE_LICENSE_CHECK",
        description="Enable license compliance check"
    )
    enable_freshness_check: bool = Field(
        default=True,
        alias="VALIDATION_ENABLE_FRESHNESS_CHECK",
        description="Enable freshness validation"
    )

    model_config = ConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


class DeduplicationSettings(BaseSettings):
    """Deduplication configuration."""

    enabled: bool = Field(
        default=True,
        alias="DEDUPLICATION_ENABLED",
        description="Enable deduplication"
    )
    hash_algorithm: str = Field(
        default="sha256",
        alias="DEDUPLICATION_HASH_ALGORITHM",
        description="Hash algorithm for deduplication"
    )
    similarity_threshold: float = Field(
        default=0.95,
        alias="DEDUPLICATION_SIMILARITY_THRESHOLD",
        description="Similarity threshold for deduplication"
    )

    model_config = ConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


class DriftDetectionSettings(BaseSettings):
    """Drift detection configuration."""

    enabled: bool = Field(
        default=True,
        alias="DRIFT_DETECTION_ENABLED",
        description="Enable drift detection"
    )
    window_size: int = Field(
        default=100,
        alias="DRIFT_DETECTION_WINDOW_SIZE",
        description="Drift detection window size"
    )
    threshold: float = Field(
        default=0.15,
        alias="DRIFT_DETECTION_THRESHOLD",
        description="Drift detection threshold"
    )

    model_config = ConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


class Config(BaseSettings):
    """Main configuration class."""

    kafka: KafkaSettings = KafkaSettings()
    postgresql: PostgreSQLSettings = PostgreSQLSettings()
    acled: ACLEDSettings = ACLEDSettings()
    gdelt: GDELTSettings = GDELTSettings()
    binance: BinanceSettings = BinanceSettings()
    ccxt: CCXTSettings = CCXTSettings()
    label: LabelSettings = LabelSettings()
    storage: StorageSettings = StorageSettings()
    metrics: MetricsSettings = MetricsSettings()
    tracing: TracingSettings = TracingSettings()
    logging: LoggingSettings = LoggingSettings()
    service: ServiceSettings = ServiceSettings()
    api_client: APIClientSettings = APIClientSettings()
    reconciliation: ReconciliationSettings = ReconciliationSettings()
    validation: ValidationSettings = ValidationSettings()
    deduplication: DeduplicationSettings = DeduplicationSettings()
    drift_detection: DriftDetectionSettings = DriftDetectionSettings()

    model_config = ConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


# Global config instance
config = Config()

