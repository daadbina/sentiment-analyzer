"""Analytics API endpoints."""

from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional
from datetime import datetime, timedelta
import logging

from src.api.schemas import (
    TrendResponse,
    TrendData,
    DistributionResponse,
    DistributionData,
    TopItemsResponse,
    TopItemResponse,
)
from src.clients import PostgreSQLClient
from src.queries import SQLBuilder
from src.exceptions import QueryError
from src.utils.logging import get_logger
from src.metrics import metrics_recorder

logger = get_logger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


async def get_postgres_client() -> PostgreSQLClient:
    """Get PostgreSQL client dependency."""
    from src.clients import postgres_client

    return postgres_client


@router.get("/trends", response_model=TrendResponse)
async def get_trends(
    metric: str = Query(..., description="Metric to analyze"),
    days: int = Query(30, ge=1, le=365),
    postgres_client: PostgreSQLClient = Depends(get_postgres_client),
) -> TrendResponse:
    """Get trend analysis.

    Args:
        metric: Metric to analyze (groups, predictions, entities)
        days: Number of days to analyze
        postgres_client: PostgreSQL client

    Returns:
        Trend data
    """
    try:
        metrics_recorder.record_request("GET /analytics/trends")

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # Build query based on metric
        if metric == "groups":
            query = """
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM semantic_groups
                WHERE created_at >= $1 AND created_at <= $2
                GROUP BY DATE(created_at)
                ORDER BY date ASC
            """
        elif metric == "predictions":
            query = """
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM predictions
                WHERE created_at >= $1 AND created_at <= $2
                GROUP BY DATE(created_at)
                ORDER BY date ASC
            """
        elif metric == "entities":
            query = """
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM entities
                WHERE created_at >= $1 AND created_at <= $2
                GROUP BY DATE(created_at)
                ORDER BY date ASC
            """
        else:
            raise HTTPException(status_code=400, detail="Invalid metric")

        rows = await postgres_client.fetch_all(query, start_date, end_date)

        trend_data = [
            TrendData(
                timestamp=datetime.fromisoformat(row["date"].isoformat()),
                value=float(row["count"]),
            )
            for row in rows
        ]

        logger.info(
            "Trends retrieved",
            extra={
                "extra_fields": {
                    "metric": metric,
                    "days": days,
                    "data_points": len(trend_data),
                }
            },
        )

        metrics_recorder.record_success("GET /analytics/trends")

        return TrendResponse(
            metric=metric,
            data=trend_data,
            start_date=start_date,
            end_date=end_date,
        )

    except QueryError as e:
        logger.error(f"Failed to get trends: {str(e)}")
        metrics_recorder.record_error("GET /analytics/trends", str(e))
        raise HTTPException(status_code=500, detail="Failed to get trends")


@router.get("/distributions", response_model=DistributionResponse)
async def get_distributions(
    metric: str = Query(..., description="Metric to analyze"),
    postgres_client: PostgreSQLClient = Depends(get_postgres_client),
) -> DistributionResponse:
    """Get distribution analysis.

    Args:
        metric: Metric to analyze (sentiment, entity_type)
        postgres_client: PostgreSQL client

    Returns:
        Distribution data
    """
    try:
        metrics_recorder.record_request("GET /analytics/distributions")

        if metric == "sentiment":
            query = """
                SELECT sentiment, COUNT(*) as count
                FROM predictions
                GROUP BY sentiment
                ORDER BY count DESC
            """
        elif metric == "entity_type":
            query = """
                SELECT entity_type, COUNT(*) as count
                FROM entities
                GROUP BY entity_type
                ORDER BY count DESC
            """
        else:
            raise HTTPException(status_code=400, detail="Invalid metric")

        rows = await postgres_client.fetch_all(query)

        total = sum(row["count"] for row in rows)
        dist_data = [
            DistributionData(
                label=row[list(row.keys())[0]],
                value=row["count"],
                percentage=(row["count"] / total * 100) if total > 0 else 0,
            )
            for row in rows
        ]

        logger.info(
            "Distributions retrieved",
            extra={
                "extra_fields": {
                    "metric": metric,
                    "categories": len(dist_data),
                }
            },
        )

        metrics_recorder.record_success("GET /analytics/distributions")

        return DistributionResponse(
            metric=metric,
            data=dist_data,
            total=total,
        )

    except QueryError as e:
        logger.error(f"Failed to get distributions: {str(e)}")
        metrics_recorder.record_error("GET /analytics/distributions", str(e))
        raise HTTPException(status_code=500, detail="Failed to get distributions")


@router.get("/top-entities", response_model=TopItemsResponse)
async def get_top_entities(
    limit: int = Query(10, ge=1, le=100),
    postgres_client: PostgreSQLClient = Depends(get_postgres_client),
) -> TopItemsResponse:
    """Get top entities by mention count.

    Args:
        limit: Number of top items to return
        postgres_client: PostgreSQL client

    Returns:
        Top entities
    """
    try:
        metrics_recorder.record_request("GET /analytics/top-entities")

        query = """
            SELECT name, mention_count
            FROM entities
            ORDER BY mention_count DESC
            LIMIT $1
        """

        rows = await postgres_client.fetch_all(query, limit)

        total = await postgres_client.fetch_val(
            "SELECT COUNT(*) FROM entities"
        )

        total_mentions = sum(row["mention_count"] for row in rows)

        items = [
            TopItemResponse(
                rank=i + 1,
                name=row["name"],
                count=row["mention_count"],
                percentage=(
                    (row["mention_count"] / total_mentions * 100)
                    if total_mentions > 0
                    else 0
                ),
            )
            for i, row in enumerate(rows)
        ]

        logger.info(
            "Top entities retrieved",
            extra={
                "extra_fields": {
                    "limit": limit,
                    "count": len(items),
                }
            },
        )

        metrics_recorder.record_success("GET /analytics/top-entities")

        return TopItemsResponse(
            metric="top_entities",
            items=items,
            total=total,
        )

    except QueryError as e:
        logger.error(f"Failed to get top entities: {str(e)}")
        metrics_recorder.record_error("GET /analytics/top-entities", str(e))
        raise HTTPException(status_code=500, detail="Failed to get top entities")


@router.get("/top-actors", response_model=TopItemsResponse)
async def get_top_actors(
    limit: int = Query(10, ge=1, le=100),
    postgres_client: PostgreSQLClient = Depends(get_postgres_client),
) -> TopItemsResponse:
    """Get top actors by involvement.

    Args:
        limit: Number of top items to return
        postgres_client: PostgreSQL client

    Returns:
        Top actors
    """
    try:
        metrics_recorder.record_request("GET /analytics/top-actors")

        query = """
            SELECT name, mention_count
            FROM entities
            WHERE entity_type = 'PERSON'
            ORDER BY mention_count DESC
            LIMIT $1
        """

        rows = await postgres_client.fetch_all(query, limit)

        total = await postgres_client.fetch_val(
            "SELECT COUNT(*) FROM entities WHERE entity_type = 'PERSON'"
        )

        total_mentions = sum(row["mention_count"] for row in rows)

        items = [
            TopItemResponse(
                rank=i + 1,
                name=row["name"],
                count=row["mention_count"],
                percentage=(
                    (row["mention_count"] / total_mentions * 100)
                    if total_mentions > 0
                    else 0
                ),
            )
            for i, row in enumerate(rows)
        ]

        logger.info(
            "Top actors retrieved",
            extra={
                "extra_fields": {
                    "limit": limit,
                    "count": len(items),
                }
            },
        )

        metrics_recorder.record_success("GET /analytics/top-actors")

        return TopItemsResponse(
            metric="top_actors",
            items=items,
            total=total,
        )

    except QueryError as e:
        logger.error(f"Failed to get top actors: {str(e)}")
        metrics_recorder.record_error("GET /analytics/top-actors", str(e))
        raise HTTPException(status_code=500, detail="Failed to get top actors")

