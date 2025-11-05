"""
PostgreSQL client for Trainer & Model Registry Service.

Provides async database operations with connection pooling.
"""

import logging
from typing import Optional, List, Dict, Any
import asyncpg
from asyncpg import Pool

from src.config import PostgreSQLConfig
from src.exceptions import ExternalServiceError

logger = logging.getLogger(__name__)


class PostgreSQLClient:
    """PostgreSQL database client with connection pooling."""

    def __init__(self, config: PostgreSQLConfig):
        """
        Initialize PostgreSQL client.

        Args:
            config: PostgreSQL configuration
        """
        self.config = config
        self.pool: Optional[Pool] = None
        logger.info(f"PostgreSQL client initialized for {config.host}:{config.port}")

    async def connect(self) -> None:
        """
        Establish connection pool to PostgreSQL.

        Raises:
            ExternalServiceError: If connection fails
        """
        try:
            self.pool = await asyncpg.create_pool(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password,
                database=self.config.database,
                min_size=1,
                max_size=self.config.pool_size,
                max_queries=50000,
                max_cached_statement_lifetime=300,
                max_cacheable_statement_size=15000,
                command_timeout=60,
            )
            logger.info("PostgreSQL connection pool established")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise ExternalServiceError(
                f"Failed to connect to PostgreSQL: {e}",
                service_name="PostgreSQL",
                details={"host": self.config.host, "port": self.config.port},
            )

    async def disconnect(self) -> None:
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("PostgreSQL connection pool closed")

    async def health_check(self) -> bool:
        """
        Check PostgreSQL connection health.

        Returns:
            True if connection is healthy, False otherwise
        """
        if not self.pool:
            logger.warning("Connection pool not initialized")
            return False

        try:
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            logger.debug("PostgreSQL health check passed")
            return True
        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {e}")
            return False

    async def execute(self, query: str, *args) -> None:
        """
        Execute a query without returning results.

        Args:
            query: SQL query
            *args: Query parameters

        Raises:
            ExternalServiceError: If query execution fails
        """
        if not self.pool:
            raise ExternalServiceError(
                "Connection pool not initialized",
                service_name="PostgreSQL",
            )

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(query, *args)
            logger.debug(f"Executed query: {query[:100]}...")
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise ExternalServiceError(
                f"Query execution failed: {e}",
                service_name="PostgreSQL",
                details={"query": query[:100]},
            )

    async def fetch_one(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """
        Fetch a single row.

        Args:
            query: SQL query
            *args: Query parameters

        Returns:
            Dictionary with row data or None if no rows

        Raises:
            ExternalServiceError: If query execution fails
        """
        if not self.pool:
            raise ExternalServiceError(
                "Connection pool not initialized",
                service_name="PostgreSQL",
            )

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, *args)
            if row:
                logger.debug(f"Fetched one row from query: {query[:100]}...")
                return dict(row)
            return None
        except Exception as e:
            logger.error(f"Fetch one failed: {e}")
            raise ExternalServiceError(
                f"Fetch one failed: {e}",
                service_name="PostgreSQL",
                details={"query": query[:100]},
            )

    async def fetch_all(self, query: str, *args) -> List[Dict[str, Any]]:
        """
        Fetch all rows.

        Args:
            query: SQL query
            *args: Query parameters

        Returns:
            List of dictionaries with row data

        Raises:
            ExternalServiceError: If query execution fails
        """
        if not self.pool:
            raise ExternalServiceError(
                "Connection pool not initialized",
                service_name="PostgreSQL",
            )

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, *args)
            logger.debug(f"Fetched {len(rows)} rows from query: {query[:100]}...")
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Fetch all failed: {e}")
            raise ExternalServiceError(
                f"Fetch all failed: {e}",
                service_name="PostgreSQL",
                details={"query": query[:100]},
            )

    async def fetch_val(self, query: str, *args) -> Any:
        """
        Fetch a single value.

        Args:
            query: SQL query
            *args: Query parameters

        Returns:
            Single value from query

        Raises:
            ExternalServiceError: If query execution fails
        """
        if not self.pool:
            raise ExternalServiceError(
                "Connection pool not initialized",
                service_name="PostgreSQL",
            )

        try:
            async with self.pool.acquire() as conn:
                value = await conn.fetchval(query, *args)
            logger.debug(f"Fetched value from query: {query[:100]}...")
            return value
        except Exception as e:
            logger.error(f"Fetch value failed: {e}")
            raise ExternalServiceError(
                f"Fetch value failed: {e}",
                service_name="PostgreSQL",
                details={"query": query[:100]},
            )

    async def insert(self, table: str, data: Dict[str, Any]) -> int:
        """
        Insert a row.

        Args:
            table: Table name
            data: Dictionary with column names and values

        Returns:
            Number of rows inserted

        Raises:
            ExternalServiceError: If insert fails
        """
        if not self.pool:
            raise ExternalServiceError(
                "Connection pool not initialized",
                service_name="PostgreSQL",
            )

        try:
            columns = ", ".join(data.keys())
            placeholders = ", ".join(f"${i+1}" for i in range(len(data)))
            query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
            values = list(data.values())

            async with self.pool.acquire() as conn:
                result = await conn.execute(query, *values)

            logger.debug(f"Inserted row into {table}")
            return 1
        except Exception as e:
            logger.error(f"Insert failed: {e}")
            raise ExternalServiceError(
                f"Insert failed: {e}",
                service_name="PostgreSQL",
                details={"table": table},
            )

    async def update(
        self, table: str, data: Dict[str, Any], where: str, *where_args
    ) -> int:
        """
        Update rows.

        Args:
            table: Table name
            data: Dictionary with column names and values
            where: WHERE clause
            *where_args: WHERE clause parameters

        Returns:
            Number of rows updated

        Raises:
            ExternalServiceError: If update fails
        """
        if not self.pool:
            raise ExternalServiceError(
                "Connection pool not initialized",
                service_name="PostgreSQL",
            )

        try:
            set_clause = ", ".join(f"{k} = ${i+1}" for i, k in enumerate(data.keys()))
            query = f"UPDATE {table} SET {set_clause} WHERE {where}"
            values = list(data.values()) + list(where_args)

            async with self.pool.acquire() as conn:
                result = await conn.execute(query, *values)

            logger.debug(f"Updated rows in {table}")
            return 1
        except Exception as e:
            logger.error(f"Update failed: {e}")
            raise ExternalServiceError(
                f"Update failed: {e}",
                service_name="PostgreSQL",
                details={"table": table},
            )
