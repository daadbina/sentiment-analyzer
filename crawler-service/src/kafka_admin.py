"""
Kafka topic administration and initialization.

Handles Kafka topic creation and configuration.
"""

import logging
from typing import List, Dict, Any
from confluent_kafka.admin import AdminClient, NewTopic, ConfigResource, ResourceType

from .config import get_settings
from .exceptions import ConfigError

logger = logging.getLogger(__name__)


class KafkaTopicManager:
    """
    Manages Kafka topic creation and configuration.

    Ensures required topics exist before service starts producing messages.
    """

    def __init__(self) -> None:
        """Initialize Kafka topic manager."""
        self.settings = get_settings()
        self.admin_client: AdminClient = None

    async def initialize(self) -> None:
        """
        Initialize Kafka admin client and create required topics.

        Creates topics if they don't exist with proper configuration.

        Raises:
            ConfigError: If Kafka initialization fails.
        """
        try:
            logger.info("Initializing Kafka topic manager...")

            # Create admin client
            self.admin_client = AdminClient({
                "bootstrap.servers": self.settings.kafka_brokers,
            })

            # Verify connection
            cluster_metadata = self.admin_client.list_topics(timeout=10)
            logger.info(
                f"Connected to Kafka cluster with {len(cluster_metadata.brokers)} brokers"
            )

            # Create required topics
            await self._create_topics()

            logger.info("Kafka topic initialization complete")

        except Exception as e:
            logger.error(f"Kafka initialization failed: {str(e)}")
            raise ConfigError(
                f"Failed to initialize Kafka topics: {str(e)}",
                error_code="KAFKA_INIT_FAILED",
            )

    async def _create_topics(self) -> None:
        """
        Create required Kafka topics if they don't exist.

        Creates:
        - news_raw: Main topic for raw news articles
        - news_raw_dlq: Dead-letter queue for failed messages
        """
        # Define topics to create
        topics_config = [
            {
                "name": self.settings.kafka_topic,
                "num_partitions": 6,
                "replication_factor": 1,
                "config": {
                    "retention.ms": "2592000000",  # 30 days
                    "compression.type": "snappy",
                    "max.message.bytes": "10485760",  # 10MB
                    "min.insync.replicas": "1",
                },
            },
            {
                "name": self.settings.kafka_dlq_topic,
                "num_partitions": 3,
                "replication_factor": 1,
                "config": {
                    "retention.ms": "7776000000",  # 90 days
                    "compression.type": "snappy",
                    "max.message.bytes": "10485760",  # 10MB
                },
            },
        ]

        # Get existing topics
        existing_topics = self.admin_client.list_topics(timeout=10).topics

        # Create topics that don't exist
        topics_to_create = []
        for topic_config in topics_config:
            topic_name = topic_config["name"]

            if topic_name in existing_topics:
                logger.info(f"Topic '{topic_name}' already exists")
                continue

            logger.info(
                f"Creating topic '{topic_name}' with "
                f"{topic_config['num_partitions']} partitions"
            )

            new_topic = NewTopic(
                topic=topic_name,
                num_partitions=topic_config["num_partitions"],
                replication_factor=topic_config["replication_factor"],
                config=topic_config["config"],
            )
            topics_to_create.append(new_topic)

        if not topics_to_create:
            logger.info("All required topics already exist")
            return

        # Create topics
        futures = self.admin_client.create_topics(topics_to_create)

        # Wait for topic creation
        for topic_name, future in futures.items():
            try:
                future.result()  # Block until topic is created
                logger.info(f"Topic '{topic_name}' created successfully")
            except Exception as e:
                # Ignore "topic already exists" errors
                if "already exists" in str(e).lower():
                    logger.info(f"Topic '{topic_name}' already exists")
                else:
                    logger.error(f"Failed to create topic '{topic_name}': {str(e)}")
                    raise ConfigError(
                        f"Failed to create topic '{topic_name}': {str(e)}",
                        error_code="TOPIC_CREATE_FAILED",
                    )

    async def verify_topics(self) -> Dict[str, bool]:
        """
        Verify that required topics exist.

        Returns:
            Dict[str, bool]: Map of topic names to existence status.
        """
        if not self.admin_client:
            raise ConfigError(
                "Admin client not initialized",
                error_code="ADMIN_CLIENT_NOT_INITIALIZED",
            )

        existing_topics = self.admin_client.list_topics(timeout=10).topics

        required_topics = [
            self.settings.kafka_topic,
            self.settings.kafka_dlq_topic,
        ]

        return {
            topic: topic in existing_topics
            for topic in required_topics
        }

    async def get_topic_config(self, topic_name: str) -> Dict[str, Any]:
        """
        Get topic configuration.

        Args:
            topic_name: Name of the topic.

        Returns:
            Dict[str, Any]: Topic configuration.
        """
        if not self.admin_client:
            raise ConfigError(
                "Admin client not initialized",
                error_code="ADMIN_CLIENT_NOT_INITIALIZED",
            )

        resource = ConfigResource(ResourceType.TOPIC, topic_name)
        futures = self.admin_client.describe_configs([resource])

        for res, future in futures.items():
            try:
                config = future.result()
                return {
                    key: value.value
                    for key, value in config.items()
                }
            except Exception as e:
                logger.error(f"Failed to get config for topic '{topic_name}': {str(e)}")
                raise ConfigError(
                    f"Failed to get topic config: {str(e)}",
                    error_code="TOPIC_CONFIG_FAILED",
                )

        return {}

    async def health_check(self) -> bool:
        """
        Check Kafka connection health.

        Returns:
            bool: True if Kafka is healthy, False otherwise.
        """
        if not self.admin_client:
            return False

        try:
            self.admin_client.list_topics(timeout=5)
            return True
        except Exception as e:
            logger.error(f"Kafka health check failed: {str(e)}")
            return False

    def close(self) -> None:
        """Close admin client connection."""
        if self.admin_client:
            # AdminClient doesn't have explicit close method
            self.admin_client = None
            logger.info("Kafka admin client closed")

