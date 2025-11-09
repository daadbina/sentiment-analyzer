"""Predictions API endpoints."""

from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional
import logging

from src.api.schemas import (
    PredictionResponse,
    PredictionListResponse,
    PredictionCreate,
)
from src.clients import PostgreSQLClient
from src.queries import SQLBuilder
from src.exceptions import QueryError
from src.utils.logging import get_logger
from src.metrics import metrics_recorder

logger = get_logger(__name__)

router = APIRouter(prefix="/predictions", tags=["predictions"])


async def get_postgres_client() -> PostgreSQLClient:
    """Get PostgreSQL client dependency."""
    from src.clients import postgres_client

    return postgres_client


@router.get("", response_model=PredictionListResponse)
async def list_predictions(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    group_id: Optional[str] = None,
    domain: Optional[str] = None,
    postgres_client: PostgreSQLClient = Depends(get_postgres_client),
) -> PredictionListResponse:
    """List predictions with filtering.

    Args:
        page: Page number
        page_size: Items per page
        group_id: Filter by group ID
        domain: Filter by domain
        postgres_client: PostgreSQL client

    Returns:
        List of predictions
    """
    try:

        builder = SQLBuilder("predictions")
        builder.select("id", "group_id", "domain", "prediction_probability", "prediction_confidence", "model_version", "features", "predicted_at", "trace_id", "created_at")

        if group_id:
            builder.where("group_id = $1", group_id)

        if domain:
            builder.where("domain = $1", domain)

        # Get total count
        count_query, count_params = builder.build_count()
        total = await postgres_client.fetch_val(count_query, *count_params)

        # Add pagination
        builder.limit(page_size)
        builder.offset((page - 1) * page_size)
        builder.order_by("created_at", "DESC")

        query, params = builder.build()
        rows = await postgres_client.fetch_all(query, *params)

        # Convert rows to dicts and handle JSON conversion
        import json
        predictions = []
        for row in rows:
            row_dict = dict(row)
            # Parse JSON features
            if 'features' in row_dict and isinstance(row_dict['features'], str):
                try:
                    row_dict['features'] = json.loads(row_dict['features']) if row_dict['features'] else None
                except:
                    row_dict['features'] = None
            predictions.append(PredictionResponse(**row_dict))

        logger.info(
            "Predictions listed",
            extra={
                "extra_fields": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                }
            },
        )


        return PredictionListResponse(
            items=predictions,
            total=total,
            page=page,
            page_size=page_size,
        )

    except QueryError as e:
        logger.error(f"Failed to list predictions: {str(e)}")
        metrics_recorder.record_error("GET /predictions", str(e))
        raise HTTPException(status_code=500, detail="Failed to list predictions")


@router.get("/{prediction_id}", response_model=PredictionResponse)
async def get_prediction(
    prediction_id: int,
    postgres_client: PostgreSQLClient = Depends(get_postgres_client),
) -> PredictionResponse:
    """Get prediction by ID.

    Args:
        prediction_id: Prediction ID
        postgres_client: PostgreSQL client

    Returns:
        Prediction details
    """
    try:

        builder = SQLBuilder("predictions")
        builder.select("id", "group_id", "domain", "prediction_probability", "prediction_confidence", "model_version", "features", "predicted_at", "trace_id", "created_at")
        builder.where("id = $1", prediction_id)

        query, params = builder.build()
        row = await postgres_client.fetch_one(query, *params)

        if not row:
            logger.warning(f"Prediction not found: {prediction_id}")
            metrics_recorder.record_error(f"GET /predictions/{prediction_id}", "Not found")
            raise HTTPException(status_code=404, detail="Prediction not found")

        # Convert row to dict and handle JSON conversion
        import json
        row_dict = dict(row)
        if 'features' in row_dict and isinstance(row_dict['features'], str):
            try:
                row_dict['features'] = json.loads(row_dict['features']) if row_dict['features'] else None
            except:
                row_dict['features'] = None

        prediction = PredictionResponse(**row_dict)

        logger.info(
            "Prediction retrieved",
            extra={"extra_fields": {"prediction_id": prediction_id}},
        )


        return prediction

    except QueryError as e:
        logger.error(f"Failed to get prediction: {str(e)}")
        metrics_recorder.record_error(f"GET /predictions/{prediction_id}", str(e))
        raise HTTPException(status_code=500, detail="Failed to get prediction")


@router.post("", response_model=PredictionResponse)
async def create_prediction(
    prediction: PredictionCreate,
    postgres_client: PostgreSQLClient = Depends(get_postgres_client),
) -> PredictionResponse:
    """Create new prediction.

    Args:
        prediction: Prediction data
        postgres_client: PostgreSQL client

    Returns:
        Created prediction
    """
    try:
        from datetime import datetime
        import json

        # Convert features dict to JSON string
        features_json = json.dumps(prediction.features) if prediction.features else None

        query = """
            INSERT INTO predictions (group_id, domain, prediction_probability, prediction_confidence, model_version, features, predicted_at, trace_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id, group_id, domain, prediction_probability, prediction_confidence, model_version, features, predicted_at, trace_id, created_at
        """

        row = await postgres_client.fetch_one(
            query,
            prediction.group_id,
            prediction.domain,
            prediction.prediction_probability,
            prediction.prediction_confidence,
            prediction.model_version,
            features_json,
            datetime.utcnow(),
            prediction.trace_id,
        )

        if not row:
            raise QueryError(message="Failed to create prediction")

        # Convert row to dict and handle JSON conversion
        row_dict = dict(row)
        if 'features' in row_dict and isinstance(row_dict['features'], str):
            try:
                row_dict['features'] = json.loads(row_dict['features']) if row_dict['features'] else None
            except:
                row_dict['features'] = None

        created_prediction = PredictionResponse(**row_dict)

        logger.info(
            "Prediction created",
            extra={"extra_fields": {"prediction_id": created_prediction.id}},
        )


        return created_prediction

    except QueryError as e:
        logger.error(f"Failed to create prediction: {str(e)}")
        metrics_recorder.record_error("POST /predictions", str(e))
        raise HTTPException(status_code=500, detail="Failed to create prediction")


@router.get("/group/{group_id}", response_model=PredictionListResponse)
async def get_group_predictions(
    group_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    postgres_client: PostgreSQLClient = Depends(get_postgres_client),
) -> PredictionListResponse:
    """Get predictions for a group.

    Args:
        group_id: Group ID
        page: Page number
        page_size: Items per page
        postgres_client: PostgreSQL client

    Returns:
        List of predictions for group
    """
    try:

        builder = SQLBuilder("predictions")
        builder.select("id", "group_id", "domain", "prediction_probability", "prediction_confidence", "model_version", "features", "predicted_at", "trace_id", "created_at")
        builder.where("group_id = $1", group_id)

        # Get total count
        count_query, count_params = builder.build_count()
        total = await postgres_client.fetch_val(count_query, *count_params)

        # Add pagination
        builder.limit(page_size)
        builder.offset((page - 1) * page_size)
        builder.order_by("created_at", "DESC")

        query, params = builder.build()
        rows = await postgres_client.fetch_all(query, *params)

        # Convert rows to dicts and handle JSON conversion
        import json
        predictions = []
        for row in rows:
            row_dict = dict(row)
            # Parse JSON features
            if 'features' in row_dict and isinstance(row_dict['features'], str):
                try:
                    row_dict['features'] = json.loads(row_dict['features']) if row_dict['features'] else None
                except:
                    row_dict['features'] = None
            predictions.append(PredictionResponse(**row_dict))

        logger.info(
            "Group predictions retrieved",
            extra={
                "extra_fields": {
                    "group_id": group_id,
                    "count": len(predictions),
                }
            },
        )


        return PredictionListResponse(
            items=predictions,
            total=total,
            page=page,
            page_size=page_size,
        )

    except QueryError as e:
        logger.error(f"Failed to get group predictions: {str(e)}")
        metrics_recorder.record_error(f"GET /predictions/group/{group_id}", str(e))
        raise HTTPException(status_code=500, detail="Failed to get group predictions")

