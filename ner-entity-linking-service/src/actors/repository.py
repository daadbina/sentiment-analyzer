"""Actor repository for PostgreSQL persistence."""

import logging
from typing import Optional, List
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
from src.models import Actor
from src.exceptions import ActorRepositoryError
from src.metrics import MetricsCollector

logger = logging.getLogger(__name__)


class ActorRepository:
    """Repository for actor persistence in PostgreSQL."""

    def __init__(self, connection_string: str, pool_size: int = 20, max_overflow: int = 10):
        """
        Initialize actor repository.

        Args:
            connection_string: PostgreSQL connection string
            pool_size: Connection pool size
            max_overflow: Maximum overflow connections
        """
        try:
            self.engine = create_engine(
                connection_string,
                poolclass=QueuePool,
                pool_size=pool_size,
                max_overflow=max_overflow,
                echo=False,
            )
            logger.info("Actor repository initialized")
        except Exception as e:
            logger.error(f"Failed to initialize actor repository: {e}")
            raise ActorRepositoryError(f"Failed to initialize repository: {e}")

    def initialize_schema(self) -> None:
        """Initialize database schema."""
        try:
            with self.engine.connect() as conn:
                # Create actors table
                conn.execute(
                    text("""
                    CREATE TABLE IF NOT EXISTS actors (
                        actor_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        name VARCHAR(500) NOT NULL,
                        normalized_name VARCHAR(500) NOT NULL UNIQUE,
                        type VARCHAR(50) NOT NULL,
                        aliases TEXT[] DEFAULT '{}',
                        country VARCHAR(3),
                        wikidata_id VARCHAR(50),
                        dbpedia_uri VARCHAR(500),
                        sentiment_avg DOUBLE PRECISION DEFAULT 0.0,
                        occurrences INTEGER DEFAULT 1,
                        first_seen TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                        last_seen TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                        ner_fallback_rate DOUBLE PRECISION DEFAULT 0.0,
                        metadata JSONB DEFAULT '{}',
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                    """)
                )

                # Create indexes
                conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS idx_actors_normalized_name ON actors(normalized_name)"
                    )
                )
                conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS idx_actors_wikidata_id ON actors(wikidata_id) WHERE wikidata_id IS NOT NULL"
                    )
                )
                conn.execute(
                    text("CREATE INDEX IF NOT EXISTS idx_actors_type ON actors(type)")
                )
                conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS idx_actors_country ON actors(country) WHERE country IS NOT NULL"
                    )
                )

                conn.commit()
                logger.info("Actor schema initialized")

        except Exception as e:
            logger.error(f"Failed to initialize schema: {e}")
            raise ActorRepositoryError(f"Failed to initialize schema: {e}")

    def upsert_actor(self, actor: Actor) -> str:
        """
        Insert or update actor.

        Args:
            actor: Actor to upsert

        Returns:
            Actor ID

        Raises:
            ActorRepositoryError: If operation fails
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("""
                    INSERT INTO actors (name, normalized_name, type, wikidata_id, country, aliases, occurrences, last_seen)
                    VALUES (:name, :normalized_name, :type, :wikidata_id, :country, :aliases, 1, NOW())
                    ON CONFLICT (normalized_name) DO UPDATE SET
                        aliases = ARRAY(SELECT DISTINCT unnest(actors.aliases || EXCLUDED.aliases)),
                        occurrences = actors.occurrences + 1,
                        last_seen = NOW(),
                        country = COALESCE(EXCLUDED.country, actors.country),
                        wikidata_id = COALESCE(EXCLUDED.wikidata_id, actors.wikidata_id),
                        updated_at = NOW()
                    RETURNING actor_id
                    """),
                    {
                        "name": actor.name,
                        "normalized_name": actor.normalized_name,
                        "type": actor.type,
                        "wikidata_id": actor.wikidata_id,
                        "country": actor.country,
                        "aliases": actor.aliases,
                    },
                )

                actor_id = result.scalar()
                conn.commit()

                if actor_id:
                    MetricsCollector.record_actor_created()
                else:
                    MetricsCollector.record_actor_updated()

                logger.debug(f"Upserted actor: {actor.normalized_name} (ID: {actor_id})")
                return str(actor_id)

        except Exception as e:
            logger.error(f"Failed to upsert actor {actor.normalized_name}: {e}")
            MetricsCollector.record_repository_error()
            raise ActorRepositoryError(f"Failed to upsert actor: {e}", "upsert")

    def find_by_normalized_name(self, normalized_name: str) -> Optional[Actor]:
        """
        Find actor by normalized name.

        Args:
            normalized_name: Normalized actor name

        Returns:
            Actor if found, None otherwise
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text(
                        "SELECT * FROM actors WHERE normalized_name = :normalized_name LIMIT 1"
                    ),
                    {"normalized_name": normalized_name},
                )

                row = result.fetchone()
                if row:
                    return self._row_to_actor(row)

                return None

        except Exception as e:
            logger.error(f"Failed to find actor by name {normalized_name}: {e}")
            MetricsCollector.record_repository_error()
            raise ActorRepositoryError(f"Failed to find actor: {e}", "find")

    def find_by_wikidata_id(self, wikidata_id: str) -> Optional[Actor]:
        """
        Find actor by Wikidata ID.

        Args:
            wikidata_id: Wikidata identifier

        Returns:
            Actor if found, None otherwise
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("SELECT * FROM actors WHERE wikidata_id = :wikidata_id LIMIT 1"),
                    {"wikidata_id": wikidata_id},
                )

                row = result.fetchone()
                if row:
                    return self._row_to_actor(row)

                return None

        except Exception as e:
            logger.error(f"Failed to find actor by Wikidata ID {wikidata_id}: {e}")
            MetricsCollector.record_repository_error()
            raise ActorRepositoryError(f"Failed to find actor: {e}", "find")

    def _row_to_actor(self, row) -> Actor:
        """Convert database row to Actor model."""
        return Actor(
            actor_id=str(row[0]),
            name=row[1],
            normalized_name=row[2],
            type=row[3],
            aliases=list(row[4]) if row[4] else [],
            country=row[5],
            wikidata_id=row[6],
            dbpedia_uri=row[7],
            sentiment_avg=row[8],
            occurrences=row[9],
            first_seen=row[10],
            last_seen=row[11],
            ner_fallback_rate=row[12],
            metadata=row[13] if row[13] else {},
            created_at=row[14],
            updated_at=row[15],
        )

    def close(self) -> None:
        """Close database connections."""
        self.engine.dispose()
        logger.info("Actor repository closed")

