"""Pydantic schemas for API responses."""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class ConflictPrediction(BaseModel):
    """Conflict prediction model."""
    
    id: int
    group_id: str
    domain: str
    prediction_probability: float = Field(ge=0.0, le=1.0)
    prediction_confidence: float = Field(ge=0.0, le=1.0)
    model_version: str
    countries: list[str] = Field(default_factory=list)
    predicted_at: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True


class CountryRisk(BaseModel):
    """Country risk aggregation model."""
    
    country: str
    risk_score: float = Field(ge=0.0, le=1.0)
    prediction_count: int
    avg_confidence: float = Field(ge=0.0, le=1.0)
    last_updated: datetime


class TrendDataPoint(BaseModel):
    """Single data point in trend series."""
    
    timestamp: datetime
    prediction_count: int
    avg_probability: float = Field(ge=0.0, le=1.0)
    avg_confidence: float = Field(ge=0.0, le=1.0)


class TrendData(BaseModel):
    """Time-series trend data."""
    
    period: str  # "day", "week", "month"
    data_points: list[TrendDataPoint]


class CountryPair(BaseModel):
    """Country pair with conflict probability."""
    
    country1: str
    country2: str
    probability: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    prediction_count: int
    last_predicted: datetime


class DashboardStats(BaseModel):
    """Overall dashboard statistics."""
    
    total_predictions: int
    total_countries: int
    avg_probability: float = Field(ge=0.0, le=1.0)
    avg_confidence: float = Field(ge=0.0, le=1.0)
    high_risk_count: int  # predictions with probability > 0.7
    last_updated: datetime


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str
    service: str
    version: str
    timestamp: datetime
    database: str
    cache: str

