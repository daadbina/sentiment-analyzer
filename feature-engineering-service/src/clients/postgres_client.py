"""PostgreSQL client for actor data."""

import asyncpg
from typing import List, Dict, Any, Optional
from ..config import config
from ..utils import StructuredLogger
from ..exceptions import PostgresError

logger = StructuredLogger(__name__)


class PostgresClient:
    """PostgreSQL client for actor data with asyncpg connection pooling."""

    def __init__(self):
        """Initialize client."""
        self.config = config
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        """Establish connection pool to PostgreSQL.

        Raises:
            PostgresError: If connection fails
        """
        try:
            self.pool = await asyncpg.create_pool(
                host=self.config.postgres.host,
                port=self.config.postgres.port,
                database=self.config.postgres.database,
                user=self.config.postgres.user,
                password=self.config.postgres.password,
                min_size=2,
                max_size=10,
                command_timeout=60,
            )

            logger.info(
                "PostgreSQL connection pool established",
                host=self.config.postgres.host,
                database=self.config.postgres.database,
                min_size=2,
                max_size=10,
            )

        except Exception as e:
            logger.error("Failed to connect to PostgreSQL", error=str(e))
            raise PostgresError(f"Failed to connect to PostgreSQL: {str(e)}")

    async def get_actors_by_ids(self, actor_ids: List[str]) -> List[Dict[str, Any]]:
        """Get actors by IDs.

        Args:
            actor_ids: List of actor IDs

        Returns:
            List of actor dictionaries
        """
        if not self.pool:
            raise PostgresError("Connection pool not initialized")

        if not actor_ids:
            return []

        try:
            async with self.pool.acquire() as conn:
                # asyncpg uses $1, $2, etc. for placeholders
                query = """
                    SELECT actor_id, name, type, country, sentiment_avg, occurrences, wikidata_id
                    FROM actors
                    WHERE actor_id = ANY($1)
                """

                rows = await conn.fetch(query, actor_ids)
                results = [dict(row) for row in rows]

                logger.info(
                    "Actors retrieved",
                    actor_count=len(results),
                )
                return results

        except Exception as e:
            logger.error("Error retrieving actors", error=str(e))
            raise PostgresError(f"Error retrieving actors: {str(e)}")

    async def get_actor_by_id(self, actor_id: str) -> Optional[Dict[str, Any]]:
        """Get single actor by ID.

        Args:
            actor_id: Actor ID

        Returns:
            Actor dictionary or None
        """
        if not self.pool:
            raise PostgresError("Connection pool not initialized")

        try:
            async with self.pool.acquire() as conn:
                query = """
                    SELECT actor_id, name, type, country, sentiment_avg, occurrences, wikidata_id
                    FROM actors
                    WHERE actor_id = $1
                """

                row = await conn.fetchrow(query, actor_id)
                return dict(row) if row else None

        except Exception as e:
            logger.error("Error retrieving actor", error=str(e), actor_id=actor_id)
            raise PostgresError(f"Error retrieving actor: {str(e)}")

    async def get_articles_by_ids(self, article_ids: List[str]) -> List[Dict[str, Any]]:
        """Get articles by IDs.

        Args:
            article_ids: List of article IDs

        Returns:
            List of article dictionaries
        """
        if not self.pool:
            raise PostgresError("Connection pool not initialized")

        if not article_ids:
            return []

        try:
            async with self.pool.acquire() as conn:
                query = """
                    SELECT article_id, title, body, language, domain, source, published_at,
                           sentiment_score, entities
                    FROM articles
                    WHERE article_id = ANY($1)
                """

                rows = await conn.fetch(query, article_ids)
                results = [dict(row) for row in rows]

                logger.debug(
                    "Articles retrieved",
                    requested=len(article_ids),
                    fetched=len(results),
                )
                return results

        except Exception as e:
            logger.error("Error retrieving articles", error=str(e), article_count=len(article_ids))
            raise PostgresError(f"Error retrieving articles: {str(e)}")

    async def get_all_actors(self) -> List[Dict[str, Any]]:
        """Get all actors.

        Returns:
            List of all actor dictionaries
        """
        if not self.pool:
            raise PostgresError("Connection pool not initialized")

        try:
            async with self.pool.acquire() as conn:
                query = """
                    SELECT actor_id, name, type, country, sentiment_avg, occurrences, wikidata_id
                    FROM actors
                    LIMIT 10000
                """

                rows = await conn.fetch(query)
                results = [dict(row) for row in rows]

                logger.debug("All actors retrieved", actor_count=len(results))
                return results

        except Exception as e:
            logger.error("Error retrieving all actors", error=str(e))
            raise PostgresError(f"Error retrieving all actors: {str(e)}")

    async def execute_query(
        self, query: str, *params
    ) -> List[Dict[str, Any]]:
        """Execute a query with parameters.

        Args:
            query: SQL query string (use $1, $2, etc. for placeholders)
            *params: Query parameters

        Returns:
            List of result dictionaries
        """
        if not self.pool:
            raise PostgresError("Connection pool not initialized")

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, *params)
                results = [dict(row) for row in rows]

                logger.debug(
                    "Query executed",
                    result_count=len(results)
                )
                return results

        except Exception as e:
            logger.error("Error executing query", error=str(e))
            raise PostgresError(f"Error executing query: {str(e)}")

    async def close(self) -> None:
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("PostgreSQL connection pool closed")

