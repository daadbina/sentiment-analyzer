"""API routes for dashboard endpoints."""

from datetime import datetime
from fastapi import APIRouter, Query, Depends, HTTPException
import structlog
from typing import List

from ..models import (
    ConflictPrediction,
    CountryRisk,
    TrendData,
    CountryPair,
    DashboardStats,
    HealthResponse,
)
from ..services import DashboardService
from ..database import PostgresClient, RedisCache

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/dashboard")

# Global instances (will be initialized in main.py)
postgres_client: PostgresClient = None
redis_cache: RedisCache = None


def get_dashboard_service() -> DashboardService:
    """Dependency to get dashboard service."""
    return DashboardService(postgres_client, redis_cache)


@router.get("/conflict-predictions/latest", response_model=List[ConflictPrediction])
async def get_latest_predictions(
    limit: int = Query(100, ge=1, le=500, description="Maximum number of predictions"),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    hours: int = Query(24, ge=1, le=168, description="Time range in hours"),
    service: DashboardService = Depends(get_dashboard_service),
):
    """
    Get latest conflict predictions with country pairs.
    
    - **limit**: Maximum number of predictions to return (1-500)
    - **min_confidence**: Minimum confidence threshold (0.0-1.0)
    - **hours**: Time range in hours (1-168)
    """
    try:
        logger.info(
            "get_latest_predictions_request",
            limit=limit,
            min_confidence=min_confidence,
            hours=hours,
        )
        predictions = await service.get_latest_predictions(
            limit=limit,
            min_confidence=min_confidence,
            hours=hours,
        )
        logger.info("get_latest_predictions_success", count=len(predictions))
        return predictions
    except Exception as e:
        logger.error("get_latest_predictions_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conflict-predictions/by-country", response_model=List[CountryRisk])
async def get_country_risk_scores(
    service: DashboardService = Depends(get_dashboard_service),
):
    """
    Get aggregated conflict risk scores by country.
    
    Returns risk scores, prediction counts, and confidence levels for each country.
    """
    try:
        logger.info("get_country_risk_scores_request")
        scores = await service.get_country_risk_scores()
        logger.info("get_country_risk_scores_success", count=len(scores))
        return scores
    except Exception as e:
        logger.error("get_country_risk_scores_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conflict-predictions/trends", response_model=TrendData)
async def get_trend_data(
    period: str = Query("day", regex="^(day|week|month)$", description="Aggregation period"),
    days: int = Query(7, ge=1, le=90, description="Number of days to include"),
    service: DashboardService = Depends(get_dashboard_service),
):
    """
    Get time-series trend data for conflict predictions.
    
    - **period**: Aggregation period (day, week, month)
    - **days**: Number of days to include (1-90)
    """
    try:
        logger.info("get_trend_data_request", period=period, days=days)
        trends = await service.get_trend_data(period=period, days=days)
        logger.info("get_trend_data_success", period=period, points=len(trends.data_points))
        return trends
    except Exception as e:
        logger.error("get_trend_data_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conflict-predictions/top-pairs", response_model=List[CountryPair])
async def get_top_country_pairs(
    limit: int = Query(10, ge=1, le=50, description="Number of top pairs to return"),
    service: DashboardService = Depends(get_dashboard_service),
):
    """
    Get top country pairs by conflict probability.
    
    - **limit**: Number of top pairs to return (1-50)
    """
    try:
        logger.info("get_top_country_pairs_request", limit=limit)
        pairs = await service.get_top_country_pairs(limit=limit)
        logger.info("get_top_country_pairs_success", count=len(pairs))
        return pairs
    except Exception as e:
        logger.error("get_top_country_pairs_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conflict-predictions/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    service: DashboardService = Depends(get_dashboard_service),
):
    """
    Get overall dashboard statistics.
    
    Returns total predictions, countries, averages, and high-risk counts.
    """
    try:
        logger.info("get_dashboard_stats_request")
        stats = await service.get_dashboard_stats()
        logger.info("get_dashboard_stats_success", stats=stats.dict())
        return stats
    except Exception as e:
        logger.error("get_dashboard_stats_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/network-graph")
async def get_network_graph(
    min_confidence: float = Query(0.5, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    hours: int = Query(168, ge=1, le=720, description="Time range in hours (default 7 days)"),
    service: DashboardService = Depends(get_dashboard_service),
):
    """
    Get network graph data with nodes (countries) and edges (predictions).

    Returns a graph structure optimized for visualization:
    - **nodes**: Countries with risk scores
    - **links**: Predictions between country pairs
    - **metadata**: Graph statistics

    - **min_confidence**: Minimum confidence threshold (0.0-1.0)
    - **hours**: Time range in hours (1-720, default 168 = 7 days)
    """
    try:
        logger.info(
            "get_network_graph_request",
            min_confidence=min_confidence,
            hours=hours,
        )
        graph_data = await service.get_network_graph_data(min_confidence, hours)
        logger.info(
            "get_network_graph_success",
            node_count=len(graph_data.get('nodes', [])),
            link_count=len(graph_data.get('links', [])),
        )
        return graph_data
    except Exception as e:
        logger.error("get_network_graph_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/btc-predictions")
async def get_btc_predictions(
    limit: int = Query(10, ge=1, le=100),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    hours: int = Query(24, ge=1, le=720),
    service: DashboardService = Depends(get_dashboard_service),
):
    """
    Get latest Bitcoin price predictions.

    Returns the most recent BTC predictions with probability and confidence scores.

    **Parameters:**
    - **limit**: Maximum number of predictions to return (1-100, default 10)
    - **min_confidence**: Minimum confidence threshold (0.0-1.0)
    - **hours**: Time range in hours (1-720, default 24)
    """
    try:
        logger.info(
            "get_btc_predictions_request",
            limit=limit,
            min_confidence=min_confidence,
            hours=hours,
        )
        predictions = await service.get_btc_predictions(limit, min_confidence, hours)
        logger.info(
            "get_btc_predictions_success",
            count=len(predictions),
        )
        return {"predictions": predictions, "count": len(predictions)}
    except Exception as e:
        logger.error("get_btc_predictions_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

