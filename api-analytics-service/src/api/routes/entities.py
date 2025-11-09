"""Entities API endpoints."""

from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional
import logging

from src.api.schemas import (
    EntityResponse,
    EntityListResponse,
    EntityCreate,
)
from src.clients import PostgreSQLClient
from src.queries import SQLBuilder
from src.exceptions import QueryError
from src.utils.logging import get_logger
from src.metrics import metrics_recorder

logger = get_logger(__name__)

router = APIRouter(prefix="/entities", tags=["entities"])


async def get_postgres_client() -> PostgreSQLClient:
    """Get PostgreSQL client dependency."""
    from src.clients import postgres_client

    return postgres_client


@router.get("", response_model=EntityListResponse)
async def list_entities(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    entity_type: Optional[str] = None,
    search: Optional[str] = None,
    postgres_client: PostgreSQLClient = Depends(get_postgres_client),
) -> EntityListResponse:
    """List entities (actors) with filtering.

    Args:
        page: Page number
        page_size: Items per page
        entity_type: Filter by entity type
        search: Search term for name
        postgres_client: PostgreSQL client

    Returns:
        List of entities
    """
    try:

        builder = SQLBuilder("actors")
        builder.select("actor_id", "name", "normalized_name", "type", "wikidata_id", "country", "aliases", "dbpedia_uri", "sentiment_avg", "occurrences", "first_seen", "last_seen", "ner_fallback_rate", "metadata", "created_at", "updated_at")

        if entity_type:
            builder.where("type = $1", entity_type)

        if search:
            builder.where("name ILIKE $1", f"%{search}%")

        # Get total count
        count_query, count_params = builder.build_count()
        total = await postgres_client.fetch_val(count_query, *count_params)

        # Add pagination
        builder.limit(page_size)
        builder.offset((page - 1) * page_size)
        builder.order_by("occurrences", "DESC")

        query, params = builder.build()
        rows = await postgres_client.fetch_all(query, *params)

        # Convert rows to dicts and handle UUID/JSON conversion
        import json
        entities = []
        for row in rows:
            row_dict = dict(row)
            # Convert UUID to string
            if 'actor_id' in row_dict and row_dict['actor_id']:
                row_dict['actor_id'] = str(row_dict['actor_id'])
            # Parse JSON metadata
            if 'metadata' in row_dict and isinstance(row_dict['metadata'], str):
                try:
                    row_dict['metadata'] = json.loads(row_dict['metadata']) if row_dict['metadata'] else None
                except:
                    row_dict['metadata'] = None
            entities.append(EntityResponse(**row_dict))

        logger.info(
            "Entities listed",
            extra={
                "extra_fields": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                }
            },
        )


        return EntityListResponse(
            items=entities,
            total=total,
            page=page,
            page_size=page_size,
        )

    except QueryError as e:
        logger.error(f"Failed to list entities: {str(e)}")
        metrics_recorder.record_error("GET /entities", str(e))
        raise HTTPException(status_code=500, detail="Failed to list entities")


@router.get("/{entity_id}", response_model=EntityResponse)
async def get_entity(
    entity_id: str,
    postgres_client: PostgreSQLClient = Depends(get_postgres_client),
) -> EntityResponse:
    """Get entity (actor) by ID.

    Args:
        entity_id: Entity (actor) ID
        postgres_client: PostgreSQL client

    Returns:
        Entity details
    """
    try:

        builder = SQLBuilder("actors")
        builder.select("actor_id", "name", "normalized_name", "type", "wikidata_id", "country", "aliases", "dbpedia_uri", "sentiment_avg", "occurrences", "first_seen", "last_seen", "ner_fallback_rate", "metadata", "created_at", "updated_at")
        builder.where("actor_id::text = $1", entity_id)

        query, params = builder.build()
        row = await postgres_client.fetch_one(query, *params)

        if not row:
            logger.warning(f"Entity not found: {entity_id}")
            metrics_recorder.record_error(f"GET /entities/{entity_id}", "Not found")
            raise HTTPException(status_code=404, detail="Entity not found")

        # Convert row to dict and handle UUID/JSON conversion
        import json
        row_dict = dict(row)
        if 'actor_id' in row_dict and row_dict['actor_id']:
            row_dict['actor_id'] = str(row_dict['actor_id'])
        if 'metadata' in row_dict and isinstance(row_dict['metadata'], str):
            try:
                row_dict['metadata'] = json.loads(row_dict['metadata']) if row_dict['metadata'] else None
            except:
                row_dict['metadata'] = None

        entity = EntityResponse(**row_dict)

        logger.info(
            "Entity retrieved",
            extra={"extra_fields": {"entity_id": entity_id}},
        )


        return entity

    except QueryError as e:
        logger.error(f"Failed to get entity: {str(e)}")
        metrics_recorder.record_error(f"GET /entities/{entity_id}", str(e))
        raise HTTPException(status_code=500, detail="Failed to get entity")


@router.post("", response_model=EntityResponse)
async def create_entity(
    entity: EntityCreate,
    postgres_client: PostgreSQLClient = Depends(get_postgres_client),
) -> EntityResponse:
    """Create new entity (actor).

    Args:
        entity: Entity data
        postgres_client: PostgreSQL client

    Returns:
        Created entity
    """
    try:
        import json

        # Generate normalized name if not provided
        normalized_name = entity.normalized_name or entity.name.lower().strip()

        query = """
            INSERT INTO actors (name, normalized_name, type, wikidata_id, country, aliases, dbpedia_uri, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING actor_id, name, normalized_name, type, wikidata_id, country, aliases, dbpedia_uri, sentiment_avg, occurrences, first_seen, last_seen, ner_fallback_rate, metadata, created_at, updated_at
        """

        row = await postgres_client.fetch_one(
            query,
            entity.name,
            normalized_name,
            entity.type,
            entity.wikidata_id,
            entity.country,
            entity.aliases or [],
            entity.dbpedia_uri,
            entity.metadata,
        )

        if not row:
            raise QueryError(message="Failed to create entity")

        created_entity = EntityResponse(**row)

        logger.info(
            "Entity created",
            extra={"extra_fields": {"entity_id": created_entity.actor_id}},
        )


        return created_entity

    except QueryError as e:
        logger.error(f"Failed to create entity: {str(e)}")
        metrics_recorder.record_error("POST /entities", str(e))
        raise HTTPException(status_code=500, detail="Failed to create entity")


@router.get("/{entity_id}/mentions", response_model=dict)
async def get_entity_mentions(
    entity_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    postgres_client: PostgreSQLClient = Depends(get_postgres_client),
) -> dict:
    """Get mentions of an entity.

    Note: This endpoint requires article-actor relationship data which is not yet available in the database.
    Returns empty result until the relationship table is created by upstream services.

    Args:
        entity_id: Entity ID
        page: Page number
        page_size: Items per page
        postgres_client: PostgreSQL client

    Returns:
        Entity mentions (currently empty until relationship data is available)
    """
    # TODO: Implement once article_actors or similar relationship table is created
    # For now, return empty result to avoid 500 errors

    logger.info(
        "Entity mentions requested (feature not yet implemented)",
        extra={
            "extra_fields": {
                "entity_id": entity_id,
                "note": "Relationship table not yet available",
            }
        },
    )

    return {
        "entity_id": entity_id,
        "mentions": [],
        "total": 0,
        "page": page,
        "page_size": page_size,
        "note": "Entity mentions feature requires article-actor relationship data which is not yet available in the database",
    }

