"""
Data models for Kafka messages and internal data structures.

Defines Pydantic models for type-safe data handling and validation.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator
import uuid

from .utils import TimestampUtils


class NewsRawMessage(BaseModel):
    """
    Kafka message model for raw news articles.

    Corresponds to news_raw Avro schema.
    """

    article_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique article identifier (UUID)",
    )
    canonical_url: str = Field(description="Canonical/normalized article URL")
    title: str = Field(description="Article headline")
    body: str = Field(description="Article main content")
    url: str = Field(description="Original article URL")
    source: str = Field(description="Publication/source name")
    language: str = Field(description="Detected language code (ISO 639-1)")
    published_at: str = Field(description="Publication timestamp (ISO-8601, UTC)")
    crawled_at: str = Field(
        default_factory=lambda: TimestampUtils.to_iso8601(TimestampUtils.now_utc()),
        description="Crawl timestamp (ISO-8601, UTC)",
    )
    country: Optional[str] = Field(
        default=None,
        description="Country code (ISO 3166-1 alpha-2) if detected",
    )
    checksum: str = Field(description="SHA-256 checksum of article body")
    validation_score: float = Field(
        description="Data quality validation score (0.0-1.0)"
    )
    schema_version: str = Field(description="Schema version tag")
    ingest_job_id: str = Field(description="Crawler job identifier")
    publisher_id: str = Field(description="Feed source/publisher identifier")
    author: Optional[str] = Field(
        default=None,
        description="Article author name if available",
    )
    raw_html: Optional[str] = Field(
        default=None,
        description="Original HTML content (optional, for debugging)",
    )
    extraction_method: str = Field(description="Parser type used (rss, html, etc.)")
    metadata: Dict[str, str] = Field(
        default_factory=dict,
        description="Additional metadata as key-value pairs",
    )

    @validator("validation_score")
    def validate_score(cls, v: float) -> float:
        """Validate validation score is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("validation_score must be between 0.0 and 1.0")
        return v

    @validator("language")
    def validate_language(cls, v: str) -> str:
        """Validate language code format."""
        if not isinstance(v, str) or len(v) != 2:
            raise ValueError("language must be ISO 639-1 code (2 characters)")
        return v.lower()

    @validator("published_at", "crawled_at", pre=True)
    def validate_timestamps(cls, v: str) -> str:
        """Validate timestamps are ISO-8601 format."""
        if not TimestampUtils.validate_iso8601(v):
            raise ValueError(f"Invalid ISO-8601 timestamp: {v}")
        return v

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert model to dictionary for Avro serialization.

        Returns:
            dict: Model data as dictionary.
        """
        return self.model_dump(exclude_none=False)

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "article_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
                "canonical_url": "https://example.com/article",
                "title": "Breaking News",
                "body": "Article content here...",
                "url": "https://example.com/article?utm_source=twitter",
                "source": "Example News",
                "language": "en",
                "published_at": "2024-01-15T10:30:00Z",
                "crawled_at": "2024-01-15T10:35:00Z",
                "country": "US",
                "checksum": "abc123def456...",
                "validation_score": 0.95,
                "schema_version": "v1.0",
                "ingest_job_id": "job_001",
                "publisher_id": "pub_001",
                "author": "John Doe",
                "extraction_method": "html",
                "metadata": {"category": "tech", "tags": "ai,ml"},
            }
        }


class FeedSource(BaseModel):
    """
    Feed source configuration model.

    Represents a news feed to be crawled.
    """

    feed_id: str = Field(description="Unique feed identifier")
    name: str = Field(description="Feed name")
    url: str = Field(description="Feed URL")
    feed_type: str = Field(
        default="rss",
        description="Feed type (rss, html, etc.)",
    )
    enabled: bool = Field(default=True, description="Whether feed is active")
    country: Optional[str] = Field(
        default=None,
        description="Country code for feed",
    )
    language: Optional[str] = Field(
        default=None,
        description="Expected language code",
    )
    crawl_interval_minutes: int = Field(
        default=30,
        description="Crawl frequency in minutes",
    )
    timeout_seconds: int = Field(
        default=10,
        description="Request timeout in seconds",
    )
    headers: Dict[str, str] = Field(
        default_factory=dict,
        description="Custom HTTP headers",
    )
    metadata: Dict[str, str] = Field(
        default_factory=dict,
        description="Additional metadata",
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "feed_id": "feed_001",
                "name": "TechCrunch",
                "url": "https://techcrunch.com/feed/",
                "feed_type": "rss",
                "enabled": True,
                "country": "US",
                "language": "en",
                "crawl_interval_minutes": 30,
                "timeout_seconds": 10,
                "headers": {"User-Agent": "Crawler/1.0"},
                "metadata": {"category": "technology"},
            }
        }


class CrawlJob(BaseModel):
    """
    Crawl job execution model.

    Represents a single crawl job execution.
    """

    job_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique job identifier",
    )
    started_at: str = Field(
        default_factory=lambda: TimestampUtils.to_iso8601(TimestampUtils.now_utc()),
        description="Job start timestamp",
    )
    completed_at: Optional[str] = Field(
        default=None,
        description="Job completion timestamp",
    )
    status: str = Field(
        default="running",
        description="Job status (running, completed, failed)",
    )
    articles_crawled: int = Field(default=0, description="Number of articles crawled")
    articles_published: int = Field(
        default=0,
        description="Number of articles published to Kafka",
    )
    articles_failed: int = Field(default=0, description="Number of failed articles")
    errors: list[str] = Field(default_factory=list, description="Error messages")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "job_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
                "started_at": "2024-01-15T10:00:00Z",
                "completed_at": "2024-01-15T10:30:00Z",
                "status": "completed",
                "articles_crawled": 150,
                "articles_published": 145,
                "articles_failed": 5,
                "errors": ["Feed timeout", "Parse error"],
            }
        }
