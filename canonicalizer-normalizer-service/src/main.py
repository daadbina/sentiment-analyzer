"""Main entry point for canonicalizer-normalizer service."""

import asyncio
import logging
import signal
from logging.handlers import RotatingFileHandler

from src.config import get_settings
from src.service import CanonicalizeNormalizerService
from src.initialization.kafka_initializer import KafkaInitializer
from src.initialization.database_initializer import DatabaseInitializer

# Configure logging
def setup_logging():
    """Setup logging configuration."""
    settings = get_settings()

    # Create logger
    logger = logging.getLogger()
    logger.setLevel(settings.service.log_level)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(settings.service.log_level)

    # File handler
    file_handler = RotatingFileHandler(
        "canonicalizer-normalizer.log",
        maxBytes=10485760,  # 10MB
        backupCount=5,
    )
    file_handler.setLevel(settings.service.log_level)

    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


async def main():
    """Main entry point."""
    logger = setup_logging()
    settings = get_settings()

    logger.info(f"Starting {settings.service.app_name}")
    logger.info(f"Environment: {settings.service.environment}")
    logger.info(f"Kafka brokers: {settings.kafka.brokers}")
    logger.info(f"Schema Registry: {settings.kafka.schema_registry_url}")

    # Initialize Kafka topics
    logger.info("Initializing Kafka topics...")
    kafka_initializer = KafkaInitializer(settings.kafka.brokers)
    required_topics = [
        {
            'name': settings.kafka.input_topic,
            'num_partitions': 3,
            'replication_factor': 1
        },
        {
            'name': settings.kafka.output_topic,
            'num_partitions': 3,
            'replication_factor': 1
        },
        {
            'name': settings.kafka.dlq_topic,
            'num_partitions': 3,
            'replication_factor': 1
        }
    ]
    kafka_initializer.ensure_topics_exist(required_topics)

    # Initialize database schema
    logger.info("Initializing database schema...")
    db_initializer = DatabaseInitializer(
        host=settings.postgres.host,
        port=settings.postgres.port,
        user=settings.postgres.user,
        password=settings.postgres.password,
        database=settings.postgres.database
    )
    db_initializer.ensure_schema_exists()
    db_initializer.seed_publishers()

    # Create service
    service = CanonicalizeNormalizerService()

    # Setup signal handlers
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        asyncio.create_task(service.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start service
    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Service error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())

