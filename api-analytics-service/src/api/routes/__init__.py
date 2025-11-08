"""API routes module."""

from fastapi import APIRouter

from .groups import router as groups_router
from .predictions import router as predictions_router
from .entities import router as entities_router
from .analytics import router as analytics_router
from .graph import router as graph_router
from .export import router as export_router

# Create main router
router = APIRouter(prefix="/api/v1", tags=["api"])

# Include route modules
router.include_router(groups_router)
router.include_router(predictions_router)
router.include_router(entities_router)
router.include_router(analytics_router)
router.include_router(graph_router)
router.include_router(export_router)

__all__ = ["router"]

