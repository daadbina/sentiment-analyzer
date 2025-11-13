"""Logging configuration for Trainer Model Registry Service."""

import logging
import sys
from logging.handlers import RotatingFileHandler


def setup_logging(log_level: str = "INFO", service_name: str = "trainer-model-registry-service") -> None:
    """
    Setup logging configuration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        service_name: Name of the service for log identification.
    """
    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Set log levels for third-party libraries to suppress DEBUG/INFO noise
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    logging.getLogger("confluent_kafka").setLevel(logging.WARNING)
    logging.getLogger("asyncpg").setLevel(logging.WARNING)
    logging.getLogger("redis").setLevel(logging.WARNING)
    logging.getLogger("feast").setLevel(logging.WARNING)
    logging.getLogger("mlflow").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("xgboost").setLevel(logging.WARNING)
    logging.getLogger("sklearn").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("s3transfer").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.ERROR)

    # Suppress deprecation warnings from libraries
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="websockets")
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="uvicorn")
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="feast")
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="mlflow")
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="opentelemetry")
    warnings.filterwarnings("ignore", message=".*artifact_path.*deprecated.*")
    warnings.filterwarnings("ignore", message=".*Call to deprecated method.*")

    # Suppress MLflow's internal warnings about artifact_path
    logging.getLogger("mlflow.models.model").setLevel(logging.ERROR)

    root_logger.info(f"Logging configured: level={log_level}, service={service_name}")

