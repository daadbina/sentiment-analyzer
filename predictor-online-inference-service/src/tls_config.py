"""
TLS/SSL configuration for secure connections.

Provides TLS configuration for Kafka, Redis, and PostgreSQL.
"""

import logging
import ssl
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TLSConfig:
    """TLS configuration settings."""

    enabled: bool = False
    ca_cert_path: str | None = None
    client_cert_path: str | None = None
    client_key_path: str | None = None
    verify_mode: str = "CERT_REQUIRED"  # CERT_NONE, CERT_OPTIONAL, CERT_REQUIRED
    check_hostname: bool = True


class TLSConfigManager:
    """
    Manager for TLS/SSL configurations.

    Handles certificate loading and SSL context creation for different services.
    """

    def __init__(
        self,
        kafka_tls_config: TLSConfig | None = None,
        redis_tls_config: TLSConfig | None = None,
        postgres_tls_config: TLSConfig | None = None,
    ):
        """
        Initialize TLS configuration manager.

        Args:
            kafka_tls_config: TLS configuration for Kafka
            redis_tls_config: TLS configuration for Redis
            postgres_tls_config: TLS configuration for PostgreSQL
        """
        self.kafka_tls_config = kafka_tls_config or TLSConfig()
        self.redis_tls_config = redis_tls_config or TLSConfig()
        self.postgres_tls_config = postgres_tls_config or TLSConfig()

        logger.info(
            f"Initialized TLS config manager: "
            f"kafka_enabled={self.kafka_tls_config.enabled}, "
            f"redis_enabled={self.redis_tls_config.enabled}, "
            f"postgres_enabled={self.postgres_tls_config.enabled}"
        )

    def create_ssl_context(self, tls_config: TLSConfig) -> ssl.SSLContext | None:
        """
        Create SSL context from TLS configuration.

        Args:
            tls_config: TLS configuration

        Returns:
            SSL context or None if TLS is disabled

        Raises:
            FileNotFoundError: If certificate files are not found
            ssl.SSLError: If SSL context creation fails
        """
        if not tls_config.enabled:
            logger.debug("TLS is disabled, returning None")
            return None

        try:
            # Create SSL context
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)

            # Set verify mode
            verify_mode_map = {
                "CERT_NONE": ssl.CERT_NONE,
                "CERT_OPTIONAL": ssl.CERT_OPTIONAL,
                "CERT_REQUIRED": ssl.CERT_REQUIRED,
            }
            context.verify_mode = verify_mode_map.get(tls_config.verify_mode, ssl.CERT_REQUIRED)

            # Set hostname checking
            context.check_hostname = tls_config.check_hostname

            # Load CA certificate
            if tls_config.ca_cert_path:
                ca_cert_path = Path(tls_config.ca_cert_path)
                if not ca_cert_path.exists():
                    raise FileNotFoundError(f"CA certificate not found: {ca_cert_path}")

                context.load_verify_locations(cafile=str(ca_cert_path))
                logger.info(f"Loaded CA certificate: {ca_cert_path}")

            # Load client certificate and key
            if tls_config.client_cert_path and tls_config.client_key_path:
                client_cert_path = Path(tls_config.client_cert_path)
                client_key_path = Path(tls_config.client_key_path)

                if not client_cert_path.exists():
                    raise FileNotFoundError(f"Client certificate not found: {client_cert_path}")
                if not client_key_path.exists():
                    raise FileNotFoundError(f"Client key not found: {client_key_path}")

                context.load_cert_chain(
                    certfile=str(client_cert_path),
                    keyfile=str(client_key_path),
                )
                logger.info(
                    f"Loaded client certificate: {client_cert_path}, " f"key: {client_key_path}"
                )

            logger.info("SSL context created successfully")
            return context

        except Exception as e:
            logger.error(f"Failed to create SSL context: {e}")
            raise

    def get_kafka_ssl_config(self) -> dict[str, Any]:
        """
        Get Kafka SSL configuration.

        Returns:
            Dictionary with Kafka SSL configuration
        """
        if not self.kafka_tls_config.enabled:
            logger.debug("Kafka TLS is disabled")
            return {}

        config = {
            "security_protocol": "SSL",
            "ssl_check_hostname": self.kafka_tls_config.check_hostname,
        }

        if self.kafka_tls_config.ca_cert_path:
            config["ssl_cafile"] = self.kafka_tls_config.ca_cert_path

        if self.kafka_tls_config.client_cert_path:
            config["ssl_certfile"] = self.kafka_tls_config.client_cert_path

        if self.kafka_tls_config.client_key_path:
            config["ssl_keyfile"] = self.kafka_tls_config.client_key_path

        logger.info("Kafka SSL configuration created")
        return config

    def get_redis_ssl_config(self) -> dict[str, Any]:
        """
        Get Redis SSL configuration.

        Returns:
            Dictionary with Redis SSL configuration
        """
        if not self.redis_tls_config.enabled:
            logger.debug("Redis TLS is disabled")
            return {}

        ssl_context = self.create_ssl_context(self.redis_tls_config)

        config = {
            "ssl": True,
            "ssl_cert_reqs": self.redis_tls_config.verify_mode,
        }

        if ssl_context:
            config["ssl_context"] = ssl_context

        if self.redis_tls_config.ca_cert_path:
            config["ssl_ca_certs"] = self.redis_tls_config.ca_cert_path

        if self.redis_tls_config.client_cert_path:
            config["ssl_certfile"] = self.redis_tls_config.client_cert_path

        if self.redis_tls_config.client_key_path:
            config["ssl_keyfile"] = self.redis_tls_config.client_key_path

        logger.info("Redis SSL configuration created")
        return config

    def get_postgres_ssl_config(self) -> dict[str, Any]:
        """
        Get PostgreSQL SSL configuration.

        Returns:
            Dictionary with PostgreSQL SSL configuration
        """
        if not self.postgres_tls_config.enabled:
            logger.debug("PostgreSQL TLS is disabled")
            return {"ssl": False}

        ssl_context = self.create_ssl_context(self.postgres_tls_config)

        config = {
            "ssl": ssl_context if ssl_context else True,
        }

        logger.info("PostgreSQL SSL configuration created")
        return config

    def validate_certificates(self) -> bool:
        """
        Validate that all required certificates exist.

        Returns:
            True if all certificates are valid, False otherwise
        """
        all_valid = True

        # Validate Kafka certificates
        if self.kafka_tls_config.enabled:
            if self.kafka_tls_config.ca_cert_path:
                if not Path(self.kafka_tls_config.ca_cert_path).exists():
                    logger.error(
                        f"Kafka CA certificate not found: " f"{self.kafka_tls_config.ca_cert_path}"
                    )
                    all_valid = False

            if self.kafka_tls_config.client_cert_path:
                if not Path(self.kafka_tls_config.client_cert_path).exists():
                    logger.error(
                        f"Kafka client certificate not found: "
                        f"{self.kafka_tls_config.client_cert_path}"
                    )
                    all_valid = False

            if self.kafka_tls_config.client_key_path:
                if not Path(self.kafka_tls_config.client_key_path).exists():
                    logger.error(
                        f"Kafka client key not found: " f"{self.kafka_tls_config.client_key_path}"
                    )
                    all_valid = False

        # Validate Redis certificates
        if self.redis_tls_config.enabled and self.redis_tls_config.ca_cert_path:
            if not Path(self.redis_tls_config.ca_cert_path).exists():
                logger.error(
                    f"Redis CA certificate not found: " f"{self.redis_tls_config.ca_cert_path}"
                )
                all_valid = False

        # Validate PostgreSQL certificates
        if self.postgres_tls_config.enabled and self.postgres_tls_config.ca_cert_path:
            if not Path(self.postgres_tls_config.ca_cert_path).exists():
                logger.error(
                    f"PostgreSQL CA certificate not found: "
                    f"{self.postgres_tls_config.ca_cert_path}"
                )
                all_valid = False

        if all_valid:
            logger.info("All certificates validated successfully")
        else:
            logger.error("Certificate validation failed")

        return all_valid


def load_tls_config_from_env() -> TLSConfigManager:
    """
    Load TLS configuration from environment variables.

    Returns:
        TLSConfigManager instance
    """
    import os

    # Kafka TLS configuration
    kafka_tls_config = TLSConfig(
        enabled=os.getenv("KAFKA_TLS_ENABLED", "false").lower() == "true",
        ca_cert_path=os.getenv("KAFKA_CA_CERT_PATH"),
        client_cert_path=os.getenv("KAFKA_CLIENT_CERT_PATH"),
        client_key_path=os.getenv("KAFKA_CLIENT_KEY_PATH"),
        verify_mode=os.getenv("KAFKA_TLS_VERIFY_MODE", "CERT_REQUIRED"),
        check_hostname=os.getenv("KAFKA_TLS_CHECK_HOSTNAME", "true").lower() == "true",
    )

    # Redis TLS configuration
    redis_tls_config = TLSConfig(
        enabled=os.getenv("REDIS_TLS_ENABLED", "false").lower() == "true",
        ca_cert_path=os.getenv("REDIS_CA_CERT_PATH"),
        client_cert_path=os.getenv("REDIS_CLIENT_CERT_PATH"),
        client_key_path=os.getenv("REDIS_CLIENT_KEY_PATH"),
        verify_mode=os.getenv("REDIS_TLS_VERIFY_MODE", "CERT_REQUIRED"),
        check_hostname=os.getenv("REDIS_TLS_CHECK_HOSTNAME", "true").lower() == "true",
    )

    # PostgreSQL TLS configuration
    postgres_tls_config = TLSConfig(
        enabled=os.getenv("POSTGRES_SSL_ENABLED", "false").lower() == "true",
        ca_cert_path=os.getenv("POSTGRES_CA_CERT_PATH"),
        client_cert_path=os.getenv("POSTGRES_CLIENT_CERT_PATH"),
        client_key_path=os.getenv("POSTGRES_CLIENT_KEY_PATH"),
        verify_mode=os.getenv("POSTGRES_SSL_VERIFY_MODE", "CERT_REQUIRED"),
        check_hostname=os.getenv("POSTGRES_SSL_CHECK_HOSTNAME", "true").lower() == "true",
    )

    return TLSConfigManager(
        kafka_tls_config=kafka_tls_config,
        redis_tls_config=redis_tls_config,
        postgres_tls_config=postgres_tls_config,
    )
