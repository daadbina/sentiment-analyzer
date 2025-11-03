"""Kafka admin client for topic management."""

import logging
from confluent_kafka.admin import AdminClient, NewTopic, ConfigResource, ConfigSource
from src.config import get_config

logger = logging.getLogger(__name__)


class KafkaAdminClient:
    """Manages Kafka topics and configurations."""

    def __init__(self):
        """Initialize Kafka admin client."""
        self.config = get_config()
        self.admin_client = None
        self._initialize()

    def _initialize(self) -> None:
        """Initialize admin client."""
        try:
            admin_config = {
                "bootstrap.servers": self.config.kafka.brokers,
                "client.id": "validator-admin-client",
                "socket.timeout.ms": 10000,
                "connections.max.idle.ms": 540000,
            }
            self.admin_client = AdminClient(admin_config)
            logger.info("Kafka admin client initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Kafka admin client: {e}")
            # Don't raise - admin client is optional
            self.admin_client = None

    def ensure_topics_exist(self) -> bool:
        """Ensure required topics exist, create if missing.

        Returns:
            True if all topics exist or were created successfully
        """
        if not self.admin_client:
            logger.warning("Admin client not initialized, skipping topic creation")
            return False

        try:
            # Define required topics
            topics_to_create = [
                NewTopic("news_raw", num_partitions=3, replication_factor=1),
                NewTopic("news_validated", num_partitions=3, replication_factor=1),
                NewTopic("news_rejected", num_partitions=3, replication_factor=1),
            ]

            # Create topics
            fs = self.admin_client.create_topics(topics_to_create, validate_only=False)

            # Wait for topic creation to complete
            for topic, f in fs.items():
                try:
                    f.result()  # Block until topic is created
                    logger.info(f"✓ Topic '{topic}' created or already exists")
                except Exception as e:
                    # Topic might already exist, which is fine
                    if "already exists" in str(e).lower() or "TOPIC_ALREADY_EXISTS" in str(e):
                        logger.info(f"✓ Topic '{topic}' already exists")
                    else:
                        logger.warning(f"Topic creation warning for '{topic}': {e}")

            logger.info("✓ All required Kafka topics are ready")
            return True

        except Exception as e:
            logger.error(f"Failed to ensure topics exist: {e}")
            return False

    def get_topic_metadata(self, topic: str) -> dict:
        """Get metadata for a topic.

        Args:
            topic: Topic name

        Returns:
            Dictionary with topic metadata
        """
        if not self.admin_client:
            return {}

        try:
            metadata = self.admin_client.list_topics(timeout=10)
            if topic in metadata.topics:
                topic_metadata = metadata.topics[topic]
                return {
                    "name": topic,
                    "partitions": len(topic_metadata.partitions),
                    "error": topic_metadata.error,
                }
            return {}
        except Exception as e:
            logger.error(f"Failed to get topic metadata for '{topic}': {e}")
            return {}

    def close(self) -> None:
        """Close admin client."""
        if self.admin_client:
            self.admin_client.close()
            logger.info("Kafka admin client closed")

