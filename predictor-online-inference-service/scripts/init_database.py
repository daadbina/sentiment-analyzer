"""
Database initialization script for predictor service.

This script creates the necessary database tables and indexes.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

import asyncpg

# Add parent directory to path to import config
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import PostgresConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def create_tables() -> bool:
    """
    Create database tables for predictor service.

    Returns:
        True if successful, False otherwise
    """
    try:
        # Load configuration
        config = PostgresConfig.from_env()

        logger.info("Connecting to PostgreSQL...")
        logger.info(f"Host: {config.host}:{config.port}")
        logger.info(f"Database: {config.database}")
        logger.info(f"User: {config.user}")

        # Connect to database
        conn = await asyncpg.connect(
            host=config.host,
            port=config.port,
            database=config.database,
            user=config.user,
            password=config.password,
        )

        logger.info("✓ Connected to PostgreSQL")

        # Read and execute migration script
        migration_file = Path(__file__).parent.parent / "schemas" / "migrations" / "001_initial_schema.sql"
        
        if not migration_file.exists():
            logger.error(f"Migration file not found: {migration_file}")
            return False

        logger.info(f"Reading migration file: {migration_file}")
        migration_sql = migration_file.read_text()

        logger.info("Executing migration...")
        await conn.execute(migration_sql)
        logger.info("✓ Migration executed successfully")

        # Verify tables were created
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('predictions', 'prediction_audit_log')
        """)

        logger.info(f"✓ Created tables: {[t['table_name'] for t in tables]}")

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

