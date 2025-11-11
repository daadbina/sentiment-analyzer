"""Pydantic schemas for API requests and responses."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============================================================================
# Groups
# ============================================================================


class GroupBase(BaseModel):
    """Base group schema."""

    topic_label: Optional[str] = Field(None, max_length=500)
    article_count: int = Field(default=0, ge=0)
    similarity_avg: Optional[float] = Field(None, ge=0.0, le=1.0)


class GroupCreate(GroupBase):
    """Create group schema."""

    pass


class GroupUpdate(BaseModel):
    """Update group schema."""

    topic_label: Optional[str] = Field(None, max_length=500)


class GroupResponse(GroupBase):
    """Group response schema."""

    group_id: str
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

    model_config = {"protected_namespaces": ()}

    group_id: str
    domain: str
    prediction_probability: float = Field(
        ...,
        description="Prediction value (0.0-1.0 for classification, any value for regression)"
    )
    prediction_confidence: float = Field(..., ge=0.0, le=1.0)
    model_version: str


class PredictionCreate(PredictionBase):
    """Create prediction schema."""

    features: Optional[Dict[str, Any]] = None
    trace_id: Optional[str] = None


class PredictionResponse(PredictionBase):
    """Prediction response schema."""

    id: int
    features: Optional[Dict[str, Any]] = None
    predicted_at: datetime
    trace_id: Optional[str] = None
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
# Entities (Actors)
# ============================================================================


class EntityBase(BaseModel):
    """Base entity (actor) schema."""

    name: str = Field(..., min_length=1, max_length=500)
    type: str = Field(..., min_length=1, max_length=100)
    wikidata_id: Optional[str] = None
    country: Optional[str] = None
    aliases: Optional[List[str]] = None


class EntityCreate(EntityBase):
    """Create entity schema."""

    normalized_name: Optional[str] = None
    dbpedia_uri: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class EntityResponse(EntityBase):
    """Entity response schema."""

    actor_id: str
    normalized_name: str
    dbpedia_uri: Optional[str] = None
    sentiment_avg: float = Field(default=0.0)
    occurrences: int = Field(default=0, ge=0)
    first_seen: datetime
    last_seen: datetime
    ner_fallback_rate: float = Field(default=0.0)
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

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

