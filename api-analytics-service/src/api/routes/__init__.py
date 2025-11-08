"""API routes module."""

from fastapi import APIRouter

from .groups import router as groups_router

# Create main router
router = APIRouter(prefix="/api/v1", tags=["api"])

# Include route modules
router.include_router(groups_router)

__all__ = ["router"]

