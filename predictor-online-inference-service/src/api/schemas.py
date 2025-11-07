"""
API schemas for request and response models.

Defines Pydantic models for API validation and documentation.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator


class PredictionRequest(BaseModel):
    """Request model for single prediction."""
    
    group_id: str = Field(..., description="Semantic group ID")
    domain: str = Field(..., description="Domain (btc/conflict/geopolitical)")
    
    @validator("domain")
    def validate_domain(cls, v):
        """Validate domain value."""
        allowed_domains = ["btc", "conflict", "geopolitical"]
        if v not in allowed_domains:
            raise ValueError(f"Domain must be one of {allowed_domains}")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "group_id": "group_123",
                "domain": "btc",
            }
        }


class BatchPredictionRequest(BaseModel):
    """Request model for batch prediction."""
    
    group_ids: List[str] = Field(..., description="List of semantic group IDs")
    domain: str = Field(..., description="Domain (btc/conflict/geopolitical)")
    
    @validator("domain")
    def validate_domain(cls, v):
        """Validate domain value."""
        allowed_domains = ["btc", "conflict", "geopolitical"]
        if v not in allowed_domains:
            raise ValueError(f"Domain must be one of {allowed_domains}")
        return v
    
    @validator("group_ids")
    def validate_group_ids(cls, v):
        """Validate group_ids list."""
        if not v:
            raise ValueError("group_ids cannot be empty")
        if len(v) > 1000:
            raise ValueError("group_ids cannot exceed 1000 items")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "group_ids": ["group_123", "group_456", "group_789"],
                "domain": "btc",
            }
        }


class PredictionResponse(BaseModel):
    """Response model for prediction."""
    
    group_id: str = Field(..., description="Semantic group ID")
    domain: str = Field(..., description="Domain")
    prediction_probability: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Prediction probability (0.0-1.0)",
    )
    prediction_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Prediction confidence (0.0-1.0)",
    )
    model_version: str = Field(..., description="Model version used")
    predicted_at: str = Field(..., description="Prediction timestamp (ISO format)")
    trace_id: Optional[str] = Field(None, description="Trace ID for distributed tracing")
    
    class Config:
        schema_extra = {
            "example": {
                "group_id": "group_123",
                "domain": "btc",
                "prediction_probability": 0.85,
                "prediction_confidence": 0.70,
                "model_version": "v1.0.0",
                "predicted_at": "2025-11-07T12:00:00Z",
                "trace_id": "01JCABCDEFGHIJKLMNOPQRSTUV",
            }
        }


class BatchPredictionResponse(BaseModel):
    """Response model for batch prediction."""
    
    predictions: List[PredictionResponse] = Field(..., description="List of predictions")
    total: int = Field(..., description="Total number of predictions")
    
    class Config:
        schema_extra = {
            "example": {
                "predictions": [
                    {
                        "group_id": "group_123",
                        "domain": "btc",
                        "prediction_probability": 0.85,
                        "prediction_confidence": 0.70,
                        "model_version": "v1.0.0",
                        "predicted_at": "2025-11-07T12:00:00Z",
                        "trace_id": "01JCABCDEFGHIJKLMNOPQRSTUV",
                    }
                ],
                "total": 1,
            }
        }


class HealthResponse(BaseModel):
    """Response model for health check."""
    
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Service version")
    timestamp: str = Field(..., description="Current timestamp (ISO format)")
    dependencies: Dict[str, str] = Field(..., description="Dependency health status")
    
    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": "2025-11-07T12:00:00Z",
                "dependencies": {
                    "mlflow": "healthy",
                    "feast": "healthy",
                    "redis": "healthy",
                    "postgres": "healthy",
                    "kafka": "healthy",
                },
            }
        }


class ErrorResponse(BaseModel):
    """Response model for errors."""
    
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    trace_id: Optional[str] = Field(None, description="Trace ID for debugging")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    
    class Config:
        schema_extra = {
            "example": {
                "error": "FeatureFetchError",
                "message": "Failed to fetch features from online store",
                "trace_id": "01JCABCDEFGHIJKLMNOPQRSTUV",
                "details": {
                    "group_id": "group_123",
                    "store_type": "online",
                },
            }
        }


class ModelMetadataResponse(BaseModel):
    """Response model for model metadata."""
    
    model_name: str = Field(..., description="Model name")
    model_version: str = Field(..., description="Model version")
    stage: str = Field(..., description="Model stage (Production/Staging/etc)")
    created_at: Optional[str] = Field(None, description="Model creation timestamp")
    description: Optional[str] = Field(None, description="Model description")
    tags: Optional[Dict[str, str]] = Field(None, description="Model tags")
    
    class Config:
        schema_extra = {
            "example": {
                "model_name": "predictor_model",
                "model_version": "v1.0.0",
                "stage": "Production",
                "created_at": "2025-11-01T00:00:00Z",
                "description": "Event realization prediction model",
                "tags": {
                    "framework": "xgboost",
                    "accuracy": "0.85",
                },
            }
        }

