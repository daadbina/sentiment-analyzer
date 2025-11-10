"""Database initializer for creating required tables and indexes."""

import logging
import asyncpg
from src.config import get_config

logger = logging.getLogger(__name__)


class DatabaseInitializer:
    """Initializes database tables and indexes."""

    # Default news sources with credibility scores
    DEFAULT_SOURCES = [
        ("cnn", "CNN", 0.8, True, "cnn"),
        ("bbc", "BBC", 0.85, True, "bbc"),
        ("reuters", "Reuters", 0.9, True, "reuters"),
        ("aljazeera", "Al Jazeera", 0.75, True, "aljazeera"),
        ("xinhua", "Xinhua", 0.7, True, "xinhua"),
        ("rt", "RT", 0.6, True, "rt"),
        ("tasnim", "Tasnim", 0.65, True, "tasnim"),
        ("isna", "ISNA", 0.7, True, "isna"),
        ("webhose_free_datasets", "Webhose Free News Datasets (Training Data)", 1.0, True, "training_data"),
    ]

    @staticmethod
    async def initialize() -> bool:
        """Initialize database tables and indexes.

        Returns:
            True if initialization successful, False otherwise
        """
        config = get_config()

        try:
            # Connect to database
            conn = await asyncpg.connect(
                host=config.database.host,
                port=config.database.port,
                user=config.database.user,
                password=config.database.password,
                database=config.database.name,
            )

            logger.info(f"Connected to database: {config.database.name}")

            # Create sources table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS sources (
                    id VARCHAR(255) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    credibility_score FLOAT DEFAULT 0.5,
                    is_active BOOLEAN DEFAULT TRUE,
                    publisher_id VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            logger.info("✓ Created sources table")

            # Create audit_logs table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id SERIAL PRIMARY KEY,
                    article_id VARCHAR(255) NOT NULL,
                    trace_id VARCHAR(255) NOT NULL,
                    job_id VARCHAR(255),
                    validation_score FLOAT,
                    is_valid BOOLEAN,
                    errors TEXT[],
                    warnings TEXT[],
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            logger.info("✓ Created audit_logs table")

            # Create rejection_logs table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS rejection_logs (
                    id SERIAL PRIMARY KEY,
                    article_id VARCHAR(255) NOT NULL,
                    trace_id VARCHAR(255) NOT NULL,
                    job_id VARCHAR(255),
                    rejection_reason TEXT,
                    error_codes TEXT[],
                    retry_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            logger.info("✓ Created rejection_logs table")

            # Create indexes
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_logs_article_id 
                ON audit_logs(article_id)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_logs_trace_id 
                ON audit_logs(trace_id)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at 
                ON audit_logs(created_at)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_rejection_logs_article_id 
                ON rejection_logs(article_id)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_rejection_logs_trace_id 
                ON rejection_logs(trace_id)
            """)
            logger.info("✓ Created indexes")

            # Insert default sources
            for source_id, name, credibility, is_active, publisher_id in DatabaseInitializer.DEFAULT_SOURCES:
                await conn.execute("""
                    INSERT INTO sources (id, name, credibility_score, is_active, publisher_id)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (id) DO UPDATE SET
                        name = $2,
                        credibility_score = $3,
                        is_active = $4,
                        publisher_id = $5,
                        updated_at = CURRENT_TIMESTAMP
                """, source_id, name, credibility, is_active, publisher_id)

            logger.info("✓ Inserted default sources")

            await conn.close()
            logger.info("✓ Database initialization complete!")
            return True

        except Exception as e:
            logger.error(f"✗ Database initialization failed: {e}", exc_info=True)
            return False

