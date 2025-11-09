"""PostgreSQL client for actor data."""

import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional
from ..config import config
from ..utils import StructuredLogger
from ..exceptions import PostgresError

logger = StructuredLogger(__name__)


class PostgresClient:
    """PostgreSQL client for actor data."""

    def __init__(self):
        """Initialize client."""
        self.config = config
        self.connection = None

    def connect(self) -> bool:
        """Connect to PostgreSQL.

        Returns:
            True if connection successful
        """
        try:
            self.connection = psycopg2.connect(
                host=self.config.postgres.host,
                port=self.config.postgres.port,
                database=self.config.postgres.database,
                user=self.config.postgres.user,
                password=self.config.postgres.password,
            )

            logger.info(
                "PostgreSQL connected",
                host=self.config.postgres.host,
                database=self.config.postgres.database,
            )
            return True

        except Exception as e:
            logger.error("Failed to connect to PostgreSQL", error=str(e))
            raise PostgresError(f"Failed to connect to PostgreSQL: {str(e)}")

    def get_actors_by_ids(self, actor_ids: List[str]) -> List[Dict[str, Any]]:
        """Get actors by IDs.

        Args:
            actor_ids: List of actor IDs

        Returns:
            List of actor dictionaries
        """
        if not self.connection:
            raise PostgresError("Not connected to PostgreSQL")

        if not actor_ids:
            return []

        try:
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)

            placeholders = ",".join(["%s"] * len(actor_ids))
            query = f"""
                SELECT actor_id, name, type, country, sentiment_avg, occurrences, wikidata_id
                FROM actors
                WHERE actor_id IN ({placeholders})
            """

            cursor.execute(query, actor_ids)
            results = cursor.fetchall()
            cursor.close()

            logger.info(
                "Actors retrieved",
                actor_count=len(results),
            )
            return results

        except Exception as e:
            logger.error("Error retrieving actors", error=str(e))
            raise PostgresError(f"Error retrieving actors: {str(e)}")

    def get_actor_by_id(self, actor_id: str) -> Optional[Dict[str, Any]]:
        """Get single actor by ID.

        Args:
            actor_id: Actor ID

        Returns:
            Actor dictionary or None
        """
        if not self.connection:
            raise PostgresError("Not connected to PostgreSQL")

        try:
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)

            query = """
                SELECT actor_id, name, type, country, sentiment_avg, occurrences, wikidata_id
                FROM actors
                WHERE actor_id = %s
            """

            cursor.execute(query, (actor_id,))
            result = cursor.fetchone()
            cursor.close()

            return result

        except Exception as e:
            logger.error("Error retrieving actor", error=str(e), actor_id=actor_id)
            raise PostgresError(f"Error retrieving actor: {str(e)}")

    def get_articles_by_ids(self, article_ids: List[str]) -> List[Dict[str, Any]]:
        """Get articles by IDs.

        Args:
            article_ids: List of article IDs

        Returns:
            List of article dictionaries
        """
        if not self.connection:
            raise PostgresError("Not connected to PostgreSQL")

        if not article_ids:
            return []

        try:
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)

            placeholders = ",".join(["%s"] * len(article_ids))
            query = f"""
                SELECT article_id, title, body, language, domain, source, published_at,
                       sentiment_score, entities
                FROM articles
                WHERE article_id IN ({placeholders})
            """

            cursor.execute(query, article_ids)
            results = cursor.fetchall()
            cursor.close()

            logger.debug(
                "Articles retrieved",
                requested=len(article_ids),
                fetched=len(results),
            )
            return results

        except Exception as e:
            logger.error("Error retrieving articles", error=str(e), article_count=len(article_ids))
            raise PostgresError(f"Error retrieving articles: {str(e)}")

    def get_all_actors(self) -> List[Dict[str, Any]]:
        """Get all actors.

        Returns:
            List of all actor dictionaries
        """
        if not self.connection:
            raise PostgresError("Not connected to PostgreSQL")

        try:
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)

            query = """
                SELECT actor_id, name, type, country, sentiment_avg, occurrences, wikidata_id
                FROM actors
                LIMIT 10000
            """

            cursor.execute(query)
            results = cursor.fetchall()
            cursor.close()

            logger.debug("All actors retrieved", actor_count=len(results))
            return results

        except Exception as e:
            logger.error("Error retrieving all actors", error=str(e))
            raise PostgresError(f"Error retrieving all actors: {str(e)}")

    def execute_query_sync(
        self, query: str, *params
    ) -> List[Dict[str, Any]]:
        """Execute a synchronous query with parameters.

        Args:
            query: SQL query string
            *params: Query parameters

        Returns:
            List of result dictionaries
        """
        if not self.connection:
            raise PostgresError("Not connected to PostgreSQL")

        try:
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            cursor.execute(query, params)
            results = cursor.fetchall()
            cursor.close()

            # Commit the transaction to avoid "transaction is aborted" errors
            self.connection.commit()

            logger.debug(
                "Query executed",
                result_count=len(results)
            )
            return results

        except Exception as e:
            logger.error("Error executing query", error=str(e))
            # Rollback the transaction on error
            if self.connection:
                self.connection.rollback()
            raise PostgresError(f"Error executing query: {str(e)}")

    def close(self):
        """Close connection."""
        if self.connection:
            self.connection.close()
            logger.info("PostgreSQL connection closed")

