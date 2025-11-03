"""Initialize database tables for ingest-validator-service."""

import asyncio
import logging
import asyncpg
import sys
from src.config import get_config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def create_tables():
    """Create required database tables."""
    config = get_config()

    try:
        # Connect to database using environment variables
        import os
        host = os.getenv("POSTGRES_HOST", "154.53.166.231")
        port = int(os.getenv("POSTGRES_PORT", "5432"))
        user = os.getenv("POSTGRES_USER", "adminsentiment")
        password = os.getenv("POSTGRES_PASSWORD", "wp2400!!!!")
        database = os.getenv("POSTGRES_DB", "sentiment")

        logger.info(f"Connecting to {user}@{host}:{port}/{database}")

        conn = await asyncpg.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
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
                job_id VARCHAR(255) NOT NULL,
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
                job_id VARCHAR(255) NOT NULL,
                rejection_reason TEXT,
                error_codes TEXT[],
                retry_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("✓ Created rejection_logs table")
        
        # Create indexes for better query performance
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
        
        # Insert default sources from Task.md
        default_sources = [
            ("cnn", "CNN", 0.8, True, None),
            ("bbc", "BBC News", 0.85, True, None),
            ("reuters", "Reuters", 0.9, True, None),
            ("aljazeera", "Al Jazeera", 0.75, True, None),
            ("xinhua", "Xinhua News", 0.7, True, None),
            ("rt", "RT News", 0.6, True, None),
            ("tasnim", "Tasnim News Agency", 0.65, True, None),
            ("isna", "ISNA News Agency", 0.7, True, None),
        ]
        
        for source_id, name, credibility, is_active, publisher_id in default_sources:
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


async def main():
    """Main entry point."""
    success = await create_tables()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

