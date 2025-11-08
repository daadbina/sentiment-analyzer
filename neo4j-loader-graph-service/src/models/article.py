"""
Article node model for Neo4j graph.
Represents a news article with metadata and content.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class Article(BaseModel):
    """
    Article node model.
    
    Represents a news article in the graph with all relevant metadata.
    """
    
    id: str = Field(
        ...,
        description="Article ULID identifier",
        min_length=26,
        max_length=26,
    )
    
    canonical_url: str = Field(
        ...,
        description="Canonical URL of the article",
        max_length=2048,
    )
    
    title: str = Field(
        ...,
        description="Article title",
        max_length=1024,
    )
    
    content: Optional[str] = Field(
        default=None,
        description="Article body content",
    )
    
    published_at: datetime = Field(
        ...,
        description="Publication timestamp (UTC)",
    )
    
    source: str = Field(
        ...,
        description="News source identifier",
        max_length=256,
    )
    
    language: str = Field(
        ...,
        description="Article language (ISO 639-1 code)",
        min_length=2,
        max_length=2,
    )
    
    country: Optional[str] = Field(
        default=None,
        description="Country of origin (ISO 3166-1 alpha-2)",
        min_length=2,
        max_length=2,
    )
    
    sentiment_score: Optional[float] = Field(
        default=None,
        description="Sentiment score [-1.0, +1.0]",
        ge=-1.0,
        le=1.0,
    )
    
    checksum: str = Field(
        ...,
        description="Content checksum for deduplication",
        max_length=64,
    )
    
    publisher_id: Optional[str] = Field(
        default=None,
        description="Publisher ULID identifier",
        min_length=26,
        max_length=26,
    )
    
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Node creation timestamp",
    )
    
    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        """Validate language code format."""
        if not v.islower():
            raise ValueError("Language code must be lowercase")
        return v
    
    @field_validator("country")
    @classmethod
    def validate_country(cls, v: Optional[str]) -> Optional[str]:
        """Validate country code format."""
        if v and not v.isupper():
            raise ValueError("Country code must be uppercase")
        return v
    
    def to_neo4j_properties(self) -> dict:
        """
        Convert model to Neo4j node properties.
        
        Returns:
            Dictionary of node properties
        """
        props = self.model_dump(exclude_none=True)
        
        # Convert datetime to ISO format string
        if "published_at" in props:
            props["published_at"] = props["published_at"].isoformat()
        if "created_at" in props:
            props["created_at"] = props["created_at"].isoformat()
            
        return props
    
    @classmethod
    def from_kafka_message(cls, message: dict) -> "Article":
        """
        Create Article from Kafka message.
        
        Args:
            message: Kafka message dictionary
            
        Returns:
            Article instance
        """
        return cls(
            id=message["article_id"],
            canonical_url=message["canonical_url"],
            title=message["title"],
            content=message.get("body"),
            published_at=datetime.fromisoformat(message["source_published_at_utc"]),
            source=message["source"],
            language=message["language"],
            country=message.get("country"),
            sentiment_score=message.get("sentiment_score"),
            checksum=message["checksum"],
            publisher_id=message.get("publisher_id"),
        )
    
    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
                "canonical_url": "https://example.com/article",
                "title": "Example Article Title",
                "content": "Article body content...",
                "published_at": "2025-11-07T12:00:00Z",
                "source": "example_news",
                "language": "en",
                "country": "US",
                "sentiment_score": 0.5,
                "checksum": "abc123def456",
                "publisher_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
                "created_at": "2025-11-07T12:00:00Z",
            }
        }

