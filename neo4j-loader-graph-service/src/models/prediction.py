"""
Prediction node model for Neo4j graph.
Represents predictions about semantic groups.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict


class Prediction(BaseModel):
    """
    Prediction node model.

    Represents a prediction about the realization of a semantic group.
    """

    model_config = ConfigDict(
        protected_namespaces=(),
        json_schema_extra={
            "example": {
                "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
                "group_id": "01ARZ3NDEKTSV4RRFFQ69G5FAW",
                "probability": 0.85,
                "confidence": 0.92,
                "model_version": "xgboost-v1.2.0",
                "domain": "btc",
                "features": {
                    "feature_num_sources": 15,
                    "feature_sentiment_mean": 0.65,
                    "feature_credibility_mean": 0.88,
                },
                "predicted_at": "2025-11-07T12:00:00Z",
            }
        }
    )
    
    id: str = Field(
        ...,
        description="Prediction ULID identifier",
        min_length=26,
        max_length=26,
    )
    
    group_id: str = Field(
        ...,
        description="Associated group ULID identifier",
        min_length=26,
        max_length=26,
    )
    
    probability: float = Field(
        ...,
        description="Prediction probability [0.0, 1.0]",
        ge=0.0,
        le=1.0,
    )
    
    confidence: float = Field(
        ...,
        description="Prediction confidence [0.0, 1.0]",
        ge=0.0,
        le=1.0,
    )
    
    model_version: str = Field(
        ...,
        description="Model version used for prediction",
        max_length=64,
    )
    
    domain: str = Field(
        ...,
        description="Prediction domain (btc, conflict, geopolitical)",
        max_length=64,
    )
    
    features: Dict[str, Any] = Field(
        default_factory=dict,
        description="Feature values used for prediction",
    )
    
    predicted_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Prediction timestamp",
    )
    
    @field_validator("probability", "confidence")
    @classmethod
    def validate_score(cls, v: float) -> float:
        """Validate score is within valid range."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Score must be between 0.0 and 1.0")
        return v
    
    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        """Validate domain is one of the allowed values."""
        allowed_domains = {"btc", "conflict", "geopolitical"}
        if v.lower() not in allowed_domains:
            raise ValueError(f"Domain must be one of {allowed_domains}")
        return v.lower()
    
    def to_neo4j_properties(self) -> dict:
        """
        Convert model to Neo4j node properties.
        
        Returns:
            Dictionary of node properties
        """
        props = self.model_dump(exclude_none=True)
        
        # Convert datetime to ISO format string
        if "predicted_at" in props:
            props["predicted_at"] = props["predicted_at"].isoformat()
        
        # Convert features dict to JSON string for Neo4j
        if "features" in props:
            import json
            props["features"] = json.dumps(props["features"])
            
        return props
    
    @classmethod
    def from_kafka_message(cls, message: dict) -> "Prediction":
        """
        Create Prediction from Kafka message.

        Args:
            message: Kafka message dictionary

        Returns:
            Prediction instance
        """
        # Generate prediction_id from group_id and timestamp if not provided
        import ulid
        prediction_id = message.get("prediction_id")
        if not prediction_id:
            prediction_id = str(ulid.ULID())

        # Parse predicted_at - handle both string and datetime
        predicted_at = message.get("predicted_at")
        if isinstance(predicted_at, str):
            # Remove 'Z' suffix if present and parse
            predicted_at = predicted_at.rstrip('Z')
            predicted_at = datetime.fromisoformat(predicted_at)
        elif not isinstance(predicted_at, datetime):
            predicted_at = datetime.utcnow()

        return cls(
            id=prediction_id,
            group_id=message["group_id"],
            probability=message.get("prediction_probability", message.get("probability", 0.0)),
            confidence=message.get("prediction_confidence", message.get("confidence", 0.0)),
            model_version=message.get("model_version", "unknown"),
            domain=message["domain"],
            features=message.get("features", {}),
            predicted_at=predicted_at,
        )
    


