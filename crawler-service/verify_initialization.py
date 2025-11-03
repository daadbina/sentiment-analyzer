"""
Verification script for database and Kafka initialization.

Tests that database tables and Kafka topics are properly initialized.
"""

import asyncio
import sys
import logging
from src.config import get_settings
from src.database import DatabaseManager
from src.kafka_admin import KafkaTopicManager
from src.logging_config import setup_logging

logger = logging.getLogger(__name__)


async def verify_database() -> bool:
    """
    Verify database initialization.

    Returns:
        bool: True if database is properly initialized.
    """
    try:
        logger.info("Verifying database initialization...")
        
        db = DatabaseManager()
        await db.initialize()
        
        # Check health
        is_healthy = await db.health_check()
        if not is_healthy:
            logger.error("Database health check failed")
            return False
        
        logger.info("✓ Database connection successful")
        
        # Verify tables exist
        tables = [
            "feed_sources",
            "crawl_jobs",
            "data_validation_log",
            "data_anomaly_events",
        ]
        
        for table in tables:
            result = await db.fetchrow(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = $1)",
                table,
            )
            if result and result[0]:
                logger.info(f"✓ Table '{table}' exists")
            else:
                logger.error(f"✗ Table '{table}' does not exist")
                return False
        
        # Verify indices exist
        indices = [
            "idx_crawl_jobs_feed_id",
            "idx_crawl_jobs_started_at",
            "idx_validation_log_timestamp",
            "idx_validation_log_rule_id",
            "idx_anomaly_events_detected_at",
            "idx_anomaly_events_feed_id",
        ]
        
        for index in indices:
            result = await db.fetchrow(
                "SELECT EXISTS (SELECT FROM pg_indexes WHERE indexname = $1)",
                index,
            )
            if result and result[0]:
                logger.info(f"✓ Index '{index}' exists")
            else:
                logger.warning(f"⚠ Index '{index}' does not exist")
        
        await db.close()
        logger.info("✓ Database verification complete")
        return True
        
    except Exception as e:
        logger.error(f"Database verification failed: {str(e)}", exc_info=True)
        return False


async def verify_kafka() -> bool:
    """
    Verify Kafka topic initialization.

    Returns:
        bool: True if Kafka topics are properly initialized.
    """
    try:
        logger.info("Verifying Kafka topic initialization...")
        
        kafka = KafkaTopicManager()
        await kafka.initialize()
        
        # Check health
        is_healthy = await kafka.health_check()
        if not is_healthy:
            logger.error("Kafka health check failed")
            return False
        
        logger.info("✓ Kafka connection successful")
        
        # Verify topics exist
        topics = await kafka.verify_topics()
        
        for topic_name, exists in topics.items():
            if exists:
                logger.info(f"✓ Topic '{topic_name}' exists")
                
                # Get topic config
                config = await kafka.get_topic_config(topic_name)
                logger.info(f"  - Partitions: {config.get('num.partitions', 'N/A')}")
                logger.info(f"  - Replication: {config.get('replication.factor', 'N/A')}")
                logger.info(f"  - Retention: {config.get('retention.ms', 'N/A')} ms")
            else:
                logger.error(f"✗ Topic '{topic_name}' does not exist")
                return False
        
        kafka.close()
        logger.info("✓ Kafka verification complete")
        return True
        
    except Exception as e:
        logger.error(f"Kafka verification failed: {str(e)}", exc_info=True)
        return False


async def main() -> None:
    """Main verification entry point."""
    settings = get_settings()
    setup_logging(log_level=settings.log_level)
    
    logger.info("=" * 60)
    logger.info("CRAWLER SERVICE INITIALIZATION VERIFICATION")
    logger.info("=" * 60)
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Database: {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}")
    logger.info(f"Kafka: {settings.kafka_brokers}")
    logger.info("=" * 60)
    
    # Verify database
    db_ok = await verify_database()
    
    # Verify Kafka
    kafka_ok = await verify_kafka()
    
    # Summary
    logger.info("=" * 60)
    logger.info("VERIFICATION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Database: {'✓ PASS' if db_ok else '✗ FAIL'}")
    logger.info(f"Kafka:    {'✓ PASS' if kafka_ok else '✗ FAIL'}")
    logger.info("=" * 60)
    
    if db_ok and kafka_ok:
        logger.info("✓ All verifications passed!")
        sys.exit(0)
    else:
        logger.error("✗ Some verifications failed")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Verification interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Verification failed with error: {str(e)}", exc_info=True)
        sys.exit(1)

