"""
Group node model for Neo4j graph.
Represents a semantic cluster of related articles.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class Group(BaseModel):
    """
    Group node model.
    
    Represents a semantic cluster of related news articles.
    """
    
    id: str = Field(
        ...,
        description="Group ULID identifier",
        min_length=26,
        max_length=26,
    )
    
    topic_label: str = Field(
        ...,
        description="Human-readable topic label",
        max_length=512,
    )
    
    size: int = Field(
        ...,
        description="Number of articles in the group",
        ge=1,
    )
    
    similarity_avg: float = Field(
        ...,
        description="Average cosine similarity within group",
        ge=0.0,
        le=1.0,
    )
    
    embedding_model: str = Field(
        ...,
        description="Embedding model used for clustering",
        max_length=256,
    )
    
    embedding_version: str = Field(
        ...,
        description="Embedding model version",
        max_length=64,
    )
    
    created_at: datetime = Field(
        ...,
        description="Group creation timestamp",
    )
    
    article_ids: Optional[List[str]] = Field(
        default=None,
        description="List of article IDs in the group (not stored in Neo4j)",
    )
    
    @field_validator("similarity_avg")
    @classmethod
    def validate_similarity(cls, v: float) -> float:
        """Validate similarity score is within valid range."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Similarity must be between 0.0 and 1.0")
        return v
    
    def to_neo4j_properties(self) -> dict:
        """
        Convert model to Neo4j node properties.
        
        Returns:
            Dictionary of node properties
        """
        props = self.model_dump(exclude={"article_ids"}, exclude_none=True)
        
        # Convert datetime to ISO format string
        if "created_at" in props:
            props["created_at"] = props["created_at"].isoformat()
            
        return props
    
    @classmethod
    def from_kafka_message(cls, message: dict) -> "Group":
        """
        Create Group from Kafka message.
        
        Args:
            message: Kafka message dictionary
            
        Returns:
            Group instance
        """
        return cls(
            id=message["group_id"],
            topic_label=message["topic_label"],
            size=len(message.get("article_ids", [])),
            similarity_avg=message["similarity_avg"],
            embedding_model=message["embedding_model"],
            embedding_version=message["embedding_version"],
            created_at=datetime.fromisoformat(message["created_at"]),
            article_ids=message.get("article_ids"),
        )
    
    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
                "topic_label": "Bitcoin Price Surge",
                "size": 15,
                "similarity_avg": 0.87,
                "embedding_model": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
                "embedding_version": "1.0.0",
                "created_at": "2025-11-07T12:00:00Z",
                "article_ids": [
                    "01ARZ3NDEKTSV4RRFFQ69G5FAV",
                    "01ARZ3NDEKTSV4RRFFQ69G5FAW",
                ],
            }
        }

