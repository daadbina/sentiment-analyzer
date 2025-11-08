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
    """List entities with filtering.

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
        metrics_recorder.record_request("GET /entities")

        builder = SQLBuilder("entities")
        builder.select("id", "name", "entity_type", "wikidata_id", "description", "mention_count", "created_at")

        if entity_type:
            builder.where("entity_type = $1", entity_type)

        if search:
            builder.where("name ILIKE $1", f"%{search}%")

        # Get total count
        count_query, count_params = builder.build_count()
        total = await postgres_client.fetch_val(count_query, *count_params)

        # Add pagination
        builder.limit(page_size)
        builder.offset((page - 1) * page_size)
        builder.order_by("mention_count", "DESC")

        query, params = builder.build()
        rows = await postgres_client.fetch_all(query, *params)

        entities = [EntityResponse(**row) for row in rows]

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

        metrics_recorder.record_success("GET /entities")

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
    """Get entity by ID.

    Args:
        entity_id: Entity ID
        postgres_client: PostgreSQL client

    Returns:
        Entity details
    """
    try:
        metrics_recorder.record_request(f"GET /entities/{entity_id}")

        builder = SQLBuilder("entities")
        builder.where("id = $1", entity_id)

        query, params = builder.build()
        row = await postgres_client.fetch_one(query, *params)

        if not row:
            logger.warning(f"Entity not found: {entity_id}")
            metrics_recorder.record_error(f"GET /entities/{entity_id}", "Not found")
            raise HTTPException(status_code=404, detail="Entity not found")

        entity = EntityResponse(**row)

        logger.info(
            "Entity retrieved",
            extra={"extra_fields": {"entity_id": entity_id}},
        )

        metrics_recorder.record_success(f"GET /entities/{entity_id}")

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
    """Create new entity.

    Args:
        entity: Entity data
        postgres_client: PostgreSQL client

    Returns:
        Created entity
    """
    try:
        metrics_recorder.record_request("POST /entities")

        query = """
            INSERT INTO entities (name, entity_type, wikidata_id, description)
            VALUES ($1, $2, $3, $4)
            RETURNING id, name, entity_type, wikidata_id, description, mention_count, created_at
        """

        row = await postgres_client.fetch_one(
            query,
            entity.name,
            entity.entity_type,
            entity.wikidata_id,
            entity.description,
        )

        if not row:
            raise QueryError(message="Failed to create entity")

        created_entity = EntityResponse(**row)

        logger.info(
            "Entity created",
            extra={"extra_fields": {"entity_id": created_entity.id}},
        )

        metrics_recorder.record_success("POST /entities")

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

    Args:
        entity_id: Entity ID
        page: Page number
        page_size: Items per page
        postgres_client: PostgreSQL client

    Returns:
        Entity mentions
    """
    try:
        metrics_recorder.record_request(f"GET /entities/{entity_id}/mentions")

        builder = SQLBuilder("entity_mentions")
        builder.where("entity_id = $1", entity_id)

        # Get total count
        count_query, count_params = builder.build_count()
        total = await postgres_client.fetch_val(count_query, *count_params)

        # Add pagination
        builder.limit(page_size)
        builder.offset((page - 1) * page_size)
        builder.order_by("created_at", "DESC")

        query, params = builder.build()
        rows = await postgres_client.fetch_all(query, *params)

        logger.info(
            "Entity mentions retrieved",
            extra={
                "extra_fields": {
                    "entity_id": entity_id,
                    "count": len(rows),
                }
            },
        )

        metrics_recorder.record_success(f"GET /entities/{entity_id}/mentions")

        return {
            "entity_id": entity_id,
            "mentions": rows,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    except QueryError as e:
        logger.error(f"Failed to get entity mentions: {str(e)}")
        metrics_recorder.record_error(f"GET /entities/{entity_id}/mentions", str(e))
        raise HTTPException(status_code=500, detail="Failed to get entity mentions")

