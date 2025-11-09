"""Groups API endpoints."""

from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional, List
import logging

from src.api.schemas import (
    GroupResponse,
    GroupListResponse,
    GroupCreate,
    GroupUpdate,
)
from src.clients import PostgreSQLClient
from src.queries import SQLBuilder
from src.exceptions import QueryError, NotFoundError
from src.utils.logging import get_logger
from src.metrics import metrics_recorder

logger = get_logger(__name__)

router = APIRouter(prefix="/groups", tags=["groups"])


async def get_postgres_client() -> PostgreSQLClient:
    """Get PostgreSQL client dependency."""
    from src.clients import postgres_client

    return postgres_client


@router.get("", response_model=GroupListResponse)
async def list_groups(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    postgres_client: PostgreSQLClient = Depends(get_postgres_client),
) -> GroupListResponse:
    """List semantic groups with pagination and filtering.

    Args:
        page: Page number
        page_size: Items per page
        search: Search term for title/description
        postgres_client: PostgreSQL client

    Returns:
        List of groups with pagination info

    Raises:
        HTTPException: If query fails
    """
    try:

        # Build query
        builder = SQLBuilder("semantic_groups")
        builder.select("group_id", "topic_label", "article_count", "similarity_avg", "created_at", "updated_at")

        if search:
            builder.where(
                "topic_label ILIKE $1",
                f"%{search}%",
            )

        # Get total count
        count_query, count_params = builder.build_count()
        total = await postgres_client.fetch_val(count_query, *count_params)

        # Add pagination
        builder.limit(page_size)
        builder.offset((page - 1) * page_size)
        builder.order_by("created_at", "DESC")

        # Execute query
        query, params = builder.build()
        rows = await postgres_client.fetch_all(query, *params)

        groups = [GroupResponse(**row) for row in rows]

        logger.info(
            "Groups listed",
            extra={
                "extra_fields": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "count": len(groups),
                }
            },
        )


        return GroupListResponse(
            items=groups,
            total=total,
            page=page,
            page_size=page_size,
        )

    except QueryError as e:
        logger.error(f"Failed to list groups: {str(e)}")
        metrics_recorder.record_error("GET /groups", str(e))
        raise HTTPException(status_code=500, detail="Failed to list groups")


@router.get("/{group_id}", response_model=GroupResponse)
async def get_group(
    group_id: str,
    postgres_client: PostgreSQLClient = Depends(get_postgres_client),
) -> GroupResponse:
    """Get group by ID.

    Args:
        group_id: Group ID
        postgres_client: PostgreSQL client

    Returns:
        Group details

    Raises:
        HTTPException: If group not found or query fails
    """
    try:

        builder = SQLBuilder("semantic_groups")
        builder.select("group_id", "topic_label", "article_count", "similarity_avg", "created_at", "updated_at")
        builder.where("group_id = $1", group_id)

        query, params = builder.build()
        row = await postgres_client.fetch_one(query, *params)

        if not row:
            logger.warning(f"Group not found: {group_id}")
            metrics_recorder.record_error(f"GET /groups/{group_id}", "Not found")
            raise HTTPException(status_code=404, detail="Group not found")

        group = GroupResponse(**row)

        logger.info(
            "Group retrieved",
            extra={"extra_fields": {"group_id": group_id}},
        )


        return group

    except QueryError as e:
        logger.error(f"Failed to get group: {str(e)}")
        metrics_recorder.record_error(f"GET /groups/{group_id}", str(e))
        raise HTTPException(status_code=500, detail="Failed to get group")


@router.post("", response_model=GroupResponse)
async def create_group(
    group: GroupCreate,
    postgres_client: PostgreSQLClient = Depends(get_postgres_client),
) -> GroupResponse:
    """Create new semantic group.

    Args:
        group: Group data
        postgres_client: PostgreSQL client

    Returns:
        Created group

    Raises:
        HTTPException: If creation fails
    """
    try:

        # Insert group
        query = """
            INSERT INTO semantic_groups (topic_label, article_count, similarity_avg)
            VALUES ($1, $2, $3)
            RETURNING group_id, topic_label, article_count, similarity_avg, created_at, updated_at
        """

        row = await postgres_client.fetch_one(
            query,
            group.topic_label,
            group.article_count,
            group.similarity_avg or 0.0,
        )

        if not row:
            raise QueryError(message="Failed to create group")

        created_group = GroupResponse(**row)

        logger.info(
            "Group created",
            extra={"extra_fields": {"group_id": created_group.group_id}},
        )


        return created_group

    except QueryError as e:
        logger.error(f"Failed to create group: {str(e)}")
        metrics_recorder.record_error("POST /groups", str(e))
        raise HTTPException(status_code=500, detail="Failed to create group")


@router.put("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: str,
    group_update: GroupUpdate,
    postgres_client: PostgreSQLClient = Depends(get_postgres_client),
) -> GroupResponse:
    """Update semantic group.

    Args:
        group_id: Group ID
        group_update: Update data
        postgres_client: PostgreSQL client

    Returns:
        Updated group

    Raises:
        HTTPException: If group not found or update fails
    """
    try:

        # Build update query
        updates = []
        params = []
        param_count = 1

        if group_update.topic_label:
            updates.append(f"topic_label = ${param_count}")
            params.append(group_update.topic_label)
            param_count += 1

        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")

        updates.append(f"updated_at = NOW()")
        params.append(group_id)

        query = f"""
            UPDATE semantic_groups
            SET {', '.join(updates)}
            WHERE group_id = ${param_count}
            RETURNING group_id, topic_label, article_count, similarity_avg, created_at, updated_at
        """

        row = await postgres_client.fetch_one(query, *params)

        if not row:
            logger.warning(f"Group not found: {group_id}")
            metrics_recorder.record_error(f"PUT /groups/{group_id}", "Not found")
            raise HTTPException(status_code=404, detail="Group not found")

        updated_group = GroupResponse(**row)

        logger.info(
            "Group updated",
            extra={"extra_fields": {"group_id": group_id}},
        )


        return updated_group

    except QueryError as e:
        logger.error(f"Failed to update group: {str(e)}")
        metrics_recorder.record_error(f"PUT /groups/{group_id}", str(e))
        raise HTTPException(status_code=500, detail="Failed to update group")


@router.delete("/{group_id}")
async def delete_group(
    group_id: str,
    postgres_client: PostgreSQLClient = Depends(get_postgres_client),
) -> dict:
    """Delete semantic group.

    Args:
        group_id: Group ID
        postgres_client: PostgreSQL client

    Returns:
        Success message

    Raises:
        HTTPException: If group not found or deletion fails
    """
    try:

        query = "DELETE FROM semantic_groups WHERE group_id = $1"
        await postgres_client.execute(query, group_id)

        logger.info(
            "Group deleted",
            extra={"extra_fields": {"group_id": group_id}},
        )


        return {"message": "Group deleted successfully"}

    except QueryError as e:
        logger.error(f"Failed to delete group: {str(e)}")
        metrics_recorder.record_error(f"DELETE /groups/{group_id}", str(e))
        raise HTTPException(status_code=500, detail="Failed to delete group")

