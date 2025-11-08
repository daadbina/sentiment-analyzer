"""Export API endpoints."""

from fastapi import APIRouter, Query, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import Optional
import logging
import json
import csv
import io
from datetime import datetime

from src.clients import PostgreSQLClient
from src.queries import SQLBuilder
from src.exceptions import QueryError, ExportError
from src.utils.logging import get_logger
from src.metrics import metrics_recorder

logger = get_logger(__name__)

router = APIRouter(prefix="/export", tags=["export"])


async def get_postgres_client() -> PostgreSQLClient:
    """Get PostgreSQL client dependency."""
    from src.clients import postgres_client

    return postgres_client


@router.get("/groups")
async def export_groups(
    format: str = Query("csv", regex="^(csv|json)$"),
    postgres_client: PostgreSQLClient = Depends(get_postgres_client),
):
    """Export groups as CSV or JSON.

    Args:
        format: Export format (csv or json)
        postgres_client: PostgreSQL client

    Returns:
        Exported data
    """
    try:
        metrics_recorder.record_request("GET /export/groups")

        query = """
            SELECT id, title, description, article_count, entity_count, created_at, updated_at
            FROM semantic_groups
            ORDER BY created_at DESC
        """

        rows = await postgres_client.fetch_all(query)

        if format == "json":
            # Convert datetime objects to strings
            data = [
                {
                    **row,
                    "created_at": row["created_at"].isoformat(),
                    "updated_at": row["updated_at"].isoformat(),
                }
                for row in rows
            ]

            output = io.StringIO()
            json.dump(data, output, indent=2)
            output.seek(0)

            logger.info(
                "Groups exported as JSON",
                extra={"extra_fields": {"count": len(rows)}},
            )

            metrics_recorder.record_success("GET /export/groups")

            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="application/json",
                headers={
                    "Content-Disposition": "attachment; filename=groups.json"
                },
            )

        else:  # CSV
            output = io.StringIO()
            writer = csv.DictWriter(
                output,
                fieldnames=[
                    "id",
                    "title",
                    "description",
                    "article_count",
                    "entity_count",
                    "created_at",
                    "updated_at",
                ],
            )

            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {
                        **row,
                        "created_at": row["created_at"].isoformat(),
                        "updated_at": row["updated_at"].isoformat(),
                    }
                )

            output.seek(0)

            logger.info(
                "Groups exported as CSV",
                extra={"extra_fields": {"count": len(rows)}},
            )

            metrics_recorder.record_success("GET /export/groups")

            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={
                    "Content-Disposition": "attachment; filename=groups.csv"
                },
            )

    except QueryError as e:
        logger.error(f"Failed to export groups: {str(e)}")
        metrics_recorder.record_error("GET /export/groups", str(e))
        raise HTTPException(status_code=500, detail="Failed to export groups")


@router.get("/predictions")
async def export_predictions(
    format: str = Query("csv", regex="^(csv|json)$"),
    postgres_client: PostgreSQLClient = Depends(get_postgres_client),
):
    """Export predictions as CSV or JSON.

    Args:
        format: Export format (csv or json)
        postgres_client: PostgreSQL client

    Returns:
        Exported data
    """
    try:
        metrics_recorder.record_request("GET /export/predictions")

        query = """
            SELECT id, group_id, sentiment, confidence, model_version, created_at
            FROM predictions
            ORDER BY created_at DESC
        """

        rows = await postgres_client.fetch_all(query)

        if format == "json":
            data = [
                {
                    **row,
                    "created_at": row["created_at"].isoformat(),
                }
                for row in rows
            ]

            output = io.StringIO()
            json.dump(data, output, indent=2)
            output.seek(0)

            logger.info(
                "Predictions exported as JSON",
                extra={"extra_fields": {"count": len(rows)}},
            )

            metrics_recorder.record_success("GET /export/predictions")

            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="application/json",
                headers={
                    "Content-Disposition": "attachment; filename=predictions.json"
                },
            )

        else:  # CSV
            output = io.StringIO()
            writer = csv.DictWriter(
                output,
                fieldnames=[
                    "id",
                    "group_id",
                    "sentiment",
                    "confidence",
                    "model_version",
                    "created_at",
                ],
            )

            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {
                        **row,
                        "created_at": row["created_at"].isoformat(),
                    }
                )

            output.seek(0)

            logger.info(
                "Predictions exported as CSV",
                extra={"extra_fields": {"count": len(rows)}},
            )

            metrics_recorder.record_success("GET /export/predictions")

            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={
                    "Content-Disposition": "attachment; filename=predictions.csv"
                },
            )

    except QueryError as e:
        logger.error(f"Failed to export predictions: {str(e)}")
        metrics_recorder.record_error("GET /export/predictions", str(e))
        raise HTTPException(status_code=500, detail="Failed to export predictions")


@router.get("/entities")
async def export_entities(
    format: str = Query("csv", regex="^(csv|json)$"),
    postgres_client: PostgreSQLClient = Depends(get_postgres_client),
):
    """Export entities as CSV or JSON.

    Args:
        format: Export format (csv or json)
        postgres_client: PostgreSQL client

    Returns:
        Exported data
    """
    try:
        metrics_recorder.record_request("GET /export/entities")

        query = """
            SELECT id, name, entity_type, wikidata_id, description, mention_count, created_at
            FROM entities
            ORDER BY mention_count DESC
        """

        rows = await postgres_client.fetch_all(query)

        if format == "json":
            data = [
                {
                    **row,
                    "created_at": row["created_at"].isoformat(),
                }
                for row in rows
            ]

            output = io.StringIO()
            json.dump(data, output, indent=2)
            output.seek(0)

            logger.info(
                "Entities exported as JSON",
                extra={"extra_fields": {"count": len(rows)}},
            )

            metrics_recorder.record_success("GET /export/entities")

            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="application/json",
                headers={
                    "Content-Disposition": "attachment; filename=entities.json"
                },
            )

        else:  # CSV
            output = io.StringIO()
            writer = csv.DictWriter(
                output,
                fieldnames=[
                    "id",
                    "name",
                    "entity_type",
                    "wikidata_id",
                    "description",
                    "mention_count",
                    "created_at",
                ],
            )

            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {
                        **row,
                        "created_at": row["created_at"].isoformat(),
                    }
                )

            output.seek(0)

            logger.info(
                "Entities exported as CSV",
                extra={"extra_fields": {"count": len(rows)}},
            )

            metrics_recorder.record_success("GET /export/entities")

            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={
                    "Content-Disposition": "attachment; filename=entities.csv"
                },
            )

    except QueryError as e:
        logger.error(f"Failed to export entities: {str(e)}")
        metrics_recorder.record_error("GET /export/entities", str(e))
        raise HTTPException(status_code=500, detail="Failed to export entities")

