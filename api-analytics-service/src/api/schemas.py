"""Pydantic schemas for API requests and responses."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============================================================================
# Groups
# ============================================================================


class GroupBase(BaseModel):
    """Base group schema."""

    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = Field(None, max_length=2000)
    semantic_vector: Optional[List[float]] = None
    article_count: int = Field(default=0, ge=0)
    entity_count: int = Field(default=0, ge=0)


class GroupCreate(GroupBase):
    """Create group schema."""

    pass


class GroupUpdate(BaseModel):
    """Update group schema."""

    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = Field(None, max_length=2000)


class GroupResponse(GroupBase):
    """Group response schema."""

    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True


class GroupListResponse(BaseModel):
    """Group list response schema."""

    items: List[GroupResponse]
    total: int
    page: int
    page_size: int


# ============================================================================
# Predictions
# ============================================================================


class PredictionBase(BaseModel):
    """Base prediction schema."""

    group_id: str
    sentiment: str = Field(..., pattern="^(positive|negative|neutral)$")
    confidence: float = Field(..., ge=0.0, le=1.0)
    model_version: str


class PredictionCreate(PredictionBase):
    """Create prediction schema."""

    pass


class PredictionResponse(PredictionBase):
    """Prediction response schema."""

    id: str
    created_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True


class PredictionListResponse(BaseModel):
    """Prediction list response schema."""

    items: List[PredictionResponse]
    total: int
    page: int
    page_size: int


# ============================================================================
# Entities
# ============================================================================


class EntityBase(BaseModel):
    """Base entity schema."""

    name: str = Field(..., min_length=1, max_length=500)
    entity_type: str = Field(..., min_length=1, max_length=100)
    wikidata_id: Optional[str] = None
    description: Optional[str] = None


class EntityCreate(EntityBase):
    """Create entity schema."""

    pass


class EntityResponse(EntityBase):
    """Entity response schema."""

    id: str
    mention_count: int = Field(default=0, ge=0)
    created_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True


class EntityListResponse(BaseModel):
    """Entity list response schema."""

    items: List[EntityResponse]
    total: int
    page: int
    page_size: int


# ============================================================================
# Analytics
# ============================================================================


class TrendData(BaseModel):
    """Trend data point."""

    timestamp: datetime
    value: float
    label: Optional[str] = None


class TrendResponse(BaseModel):
    """Trend analysis response."""

    metric: str
    data: List[TrendData]
    start_date: datetime
    end_date: datetime


class DistributionData(BaseModel):
    """Distribution data point."""

    label: str
    value: int
    percentage: float


class DistributionResponse(BaseModel):
    """Distribution analysis response."""

    metric: str
    data: List[DistributionData]
    total: int


class TopItemResponse(BaseModel):
    """Top item response."""

    rank: int
    name: str
    count: int
    percentage: float


class TopItemsResponse(BaseModel):
    """Top items response."""

    metric: str
    items: List[TopItemResponse]
    total: int


# ============================================================================
# Graph
# ============================================================================


class GraphNode(BaseModel):
    """Graph node."""

    id: str
    label: str
    properties: Dict[str, Any] = {}


class GraphRelationship(BaseModel):
    """Graph relationship."""

    id: str
    type: str
    source_id: str
    target_id: str
    properties: Dict[str, Any] = {}


class GraphPath(BaseModel):
    """Graph path."""

    nodes: List[GraphNode]
    relationships: List[GraphRelationship]


class NeighborsResponse(BaseModel):
    """Neighbors response."""

    node_id: str
    neighbors: List[GraphNode]
    relationship_count: int


class PathResponse(BaseModel):
    """Path response."""

    from_id: str
    to_id: str
    paths: List[GraphPath]
    path_count: int


class CentralityMetric(BaseModel):
    """Centrality metric."""

    node_id: str
    value: float


class CentralityResponse(BaseModel):
    """Centrality response."""

    metric_type: str
    metrics: List[CentralityMetric]


# ============================================================================
# Export
# ============================================================================


class ExportRequest(BaseModel):
    """Export request schema."""

    format: str = Field(..., pattern="^(csv|json)$")
    filters: Optional[Dict[str, Any]] = None


class ExportResponse(BaseModel):
    """Export response schema."""

    export_id: str
    format: str
    status: str
    created_at: datetime
    download_url: Optional[str] = None


# ============================================================================
# Error
# ============================================================================


class ErrorResponse(BaseModel):
    """Error response schema."""

    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    trace_id: Optional[str] = None

