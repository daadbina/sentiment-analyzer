"""Database schema migrations."""

import logging
import os
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool

from .config import config

logger = logging.getLogger(__name__)


class MigrationRunner:
    """Run database schema migrations."""

    def __init__(self):
        """Initialize migration runner."""
        self.dsn = (
            f"postgresql://{config.postgres.user}:{config.postgres.password}"
            f"@{config.postgres.host}:{config.postgres.port}/{config.postgres.database}"
        )
        self.engine = create_engine(
            self.dsn,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )
        self.migrations_dir = Path(__file__).parent.parent / "schemas" / "migrations"
        logger.info(f"MigrationRunner initialized with DSN: {self.dsn}")

    def get_migration_files(self):
        """Get sorted list of migration files."""
        if not self.migrations_dir.exists():
            logger.warning(f"Migrations directory not found: {self.migrations_dir}")
            return []

        migration_files = sorted(self.migrations_dir.glob("*.sql"))
        logger.info(f"Found {len(migration_files)} migration files")
        return migration_files

    def create_migrations_table(self):
        """Create migrations tracking table."""
        with self.engine.connect() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        id SERIAL PRIMARY KEY,
                        migration_name VARCHAR(255) NOT NULL UNIQUE,
                        executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
            )
            conn.commit()
            logger.info("Created schema_migrations table")

    def get_executed_migrations(self):
        """Get list of already executed migrations."""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT migration_name FROM schema_migrations ORDER BY id")
            )
            executed = {row[0] for row in result}
            logger.debug(f"Found {len(executed)} executed migrations")
            return executed

    def run_migration(self, migration_file):
        """Run a single migration file."""
        migration_name = migration_file.name
        logger.info(f"Running migration: {migration_name}")

        try:
            with open(migration_file, "r") as f:
                sql_content = f.read()

            with self.engine.connect() as conn:
                # Execute migration
                conn.execute(text(sql_content))

                # Record migration
                conn.execute(
                    text(
                        "INSERT INTO schema_migrations (migration_name) VALUES (:name)"
                    ),
                    {"name": migration_name},
                )
                conn.commit()

            logger.info(f"Successfully executed migration: {migration_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to execute migration {migration_name}: {e}")
            raise

    def run_all_migrations(self):
        """Run all pending migrations."""
        logger.info("Starting migration process")

        try:
            # Create migrations table
            self.create_migrations_table()

            # Get migration files
            migration_files = self.get_migration_files()
            if not migration_files:
                logger.warning("No migration files found")
                return

            # Get executed migrations
            executed = self.get_executed_migrations()

            # Run pending migrations
            pending_count = 0
            for migration_file in migration_files:
                if migration_file.name not in executed:
                    self.run_migration(migration_file)
                    pending_count += 1
                else:
                    logger.debug(f"Skipping already executed migration: {migration_file.name}")

            logger.info(f"Migration process complete. Executed {pending_count} migrations")

        except Exception as e:
            logger.error(f"Migration process failed: {e}", exc_info=True)
            raise

    def rollback_migration(self, migration_name):
        """Rollback a specific migration (manual process)."""
        logger.warning(f"Rollback requested for migration: {migration_name}")
        logger.warning("Manual rollback required - please review migration files")

    def get_migration_status(self):
        """Get status of all migrations."""
        try:
            migration_files = self.get_migration_files()
            executed = self.get_executed_migrations()

            status = {
                "total_migrations": len(migration_files),
                "executed_migrations": len(executed),
                "pending_migrations": len(migration_files) - len(executed),
                "migrations": [],
            }

            for migration_file in migration_files:
                status["migrations"].append(
                    {
                        "name": migration_file.name,
                        "executed": migration_file.name in executed,
                    }
                )

            return status

        except Exception as e:
            logger.error(f"Failed to get migration status: {e}")
            return {"error": str(e)}


def run_migrations():
    """Run all pending migrations."""
    runner = MigrationRunner()
    runner.run_all_migrations()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_migrations()

