"""PostgreSQL database client with connection pooling."""

import asyncpg
from typing import Optional, List, Dict, Any
import logging

from src.config import config
from src.exceptions import DatabaseConnectionError, QueryError
from src.utils.logging import get_logger, LatencyTracker

logger = get_logger(__name__)


class PostgreSQLClient:
    """PostgreSQL database client with async support."""

    def __init__(self):
        """Initialize PostgreSQL client."""
        self.pool: Optional[asyncpg.Pool] = None
        self.config = config.postgres

    async def connect(self) -> None:
        """Create connection pool.

        Raises:
            DatabaseConnectionError: If connection fails
        """
        try:
            logger.info("Connecting to PostgreSQL...")

            self.pool = await asyncpg.create_pool(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password,
                database=self.config.database,
                min_size=1,
                max_size=self.config.pool_size,
                command_timeout=self.config.pool_timeout,
            )

            logger.info(
                "PostgreSQL connection pool created",
                extra={
                    "extra_fields": {
                        "host": self.config.host,
                        "port": self.config.port,
                        "database": self.config.database,
                        "pool_size": self.config.pool_size,
                    }
                },
            )

        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {str(e)}")
            raise DatabaseConnectionError(
                message="Failed to connect to PostgreSQL",
                details={"error": str(e)},
            )

    async def disconnect(self) -> None:
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("PostgreSQL connection pool closed")

    async def health_check(self) -> bool:
        """Check database health.

        Returns:
            True if database is healthy, False otherwise
        """
        try:
            if not self.pool:
                return False

            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")

            logger.info("PostgreSQL health check passed")
            return True

        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {str(e)}")
            return False

    async def execute(
        self,
        query: str,
        *args,
    ) -> None:
        """Execute query without returning results.

        Args:
            query: SQL query
            *args: Query parameters

        Raises:
            DatabaseConnectionError: If not connected
            QueryError: If query execution fails
        """
        if not self.pool:
            raise DatabaseConnectionError(
                message="Not connected to PostgreSQL"
            )

        try:
            with LatencyTracker(logger, "PostgreSQL execute"):
                async with self.pool.acquire() as conn:
                    await conn.execute(query, *args)

        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            raise QueryError(
                message="Query execution failed",
                details={"error": str(e), "query": query},
            )

    async def fetch_one(
        self,
        query: str,
        *args,
    ) -> Optional[Dict[str, Any]]:
        """Fetch single row.

        Args:
            query: SQL query
            *args: Query parameters

        Returns:
            Row as dictionary or None

        Raises:
            DatabaseConnectionError: If not connected
            QueryError: If query execution fails
        """
        if not self.pool:
            raise DatabaseConnectionError(
                message="Not connected to PostgreSQL"
            )

        try:
            with LatencyTracker(logger, "PostgreSQL fetch_one"):
                async with self.pool.acquire() as conn:
                    row = await conn.fetchrow(query, *args)
                    return dict(row) if row else None

        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            raise QueryError(
                message="Query execution failed",
                details={"error": str(e), "query": query},
            )

    async def fetch_all(
        self,
        query: str,
        *args,
    ) -> List[Dict[str, Any]]:
        """Fetch all rows.

        Args:
            query: SQL query
            *args: Query parameters

        Returns:
            List of rows as dictionaries

        Raises:
            DatabaseConnectionError: If not connected
            QueryError: If query execution fails
        """
        if not self.pool:
            raise DatabaseConnectionError(
                message="Not connected to PostgreSQL"
            )

        try:
            with LatencyTracker(logger, "PostgreSQL fetch_all"):
                async with self.pool.acquire() as conn:
                    rows = await conn.fetch(query, *args)
                    return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            raise QueryError(
                message="Query execution failed",
                details={"error": str(e), "query": query},
            )

    async def fetch_val(
        self,
        query: str,
        *args,
    ) -> Any:
        """Fetch single value.

        Args:
            query: SQL query
            *args: Query parameters

        Returns:
            Single value

        Raises:
            DatabaseConnectionError: If not connected
            QueryError: If query execution fails
        """
        if not self.pool:
            raise DatabaseConnectionError(
                message="Not connected to PostgreSQL"
            )

        try:
            with LatencyTracker(logger, "PostgreSQL fetch_val"):
                async with self.pool.acquire() as conn:
                    return await conn.fetchval(query, *args)

        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            raise QueryError(
                message="Query execution failed",
                details={"error": str(e), "query": query},
            )

    async def transaction(self):
        """Get transaction context.

        Returns:
            Transaction context manager

        Raises:
            DatabaseConnectionError: If not connected
        """
        if not self.pool:
            raise DatabaseConnectionError(
                message="Not connected to PostgreSQL"
            )

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                yield conn


# Global PostgreSQL client instance
postgres_client = PostgreSQLClient()

