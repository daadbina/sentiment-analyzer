"""Pydantic models for data validation."""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime


class NewsRaw(BaseModel):
    """Raw news article from crawler."""

    article_id: str
    canonical_url: str
    title: str
    body: str
    url: str
    published_at: str
    language: str
    source: str
    crawled_at: str
    country: Optional[str] = None
    checksum: str
    validation_score: float
    schema_version: str
    ingest_job_id: str
    publisher_id: str
    author: Optional[str] = None
    raw_html: Optional[str] = None
    extraction_method: str
    metadata: Dict[str, str] = {}

    class Config:
        """Pydantic config."""

        extra = "allow"


class ValidationDetails(BaseModel):
    """Detailed validation results per stage."""

    schema_valid: bool = False
    encoding_valid: bool = False
    timestamp_valid: bool = False
    source_verified: bool = False
    language_detected: bool = False
    not_duplicate: bool = False
    content_quality_ok: bool = False


class NewsValidated(BaseModel):
    """Validated news article."""

    article_id: str
    canonical_url: str
    title: str
    body: str
    url: str
    source: str
    language: str
    language_confidence: float
    language_detection_method: str
    source_published_at_raw: str
    source_published_at_utc: str
    ingested_at: str
    validated_at: str
    country: Optional[str] = None
    checksum: str
    validation_score: float
    validation_details: ValidationDetails
    schema_version: str
    ingest_job_id: str
    validation_job_id: str
    trace_id: str
    publisher_id: Optional[str] = None

    @validator("validation_score")
    def validate_score(cls, v):
        """Validate score is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("validation_score must be between 0.0 and 1.0")
        return v

    @validator("language_confidence")
    def validate_confidence(cls, v):
        """Validate confidence is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("language_confidence must be between 0.0 and 1.0")
        return v


class NewsRejected(BaseModel):
    """Rejected news article with error details."""

    article_id: str
    url: str
    source: str
    rejected_at: str
    validation_score: float
    rejection_reason: str
    error_codes: List[str]
    error_details: Dict[str, str]
    retry_count: int = 0
    original_message: Dict[str, Any]
    trace_id: str
    validation_job_id: str
    schema_version: str


class ValidationContext(BaseModel):
    """Context passed through validation pipeline."""

    article_id: str
    trace_id: str
    job_id: str
    raw_message: NewsRaw

    # Validation results
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    # Extracted/normalized data
    title: Optional[str] = None
    body: Optional[str] = None
    url: Optional[str] = None
    canonical_url: Optional[str] = None
    source: Optional[str] = None
    source_published_at_utc: Optional[str] = None
    language: Optional[str] = None
    language_confidence: Optional[float] = None
    language_detection_method: Optional[str] = None
    country: Optional[str] = None
    checksum: Optional[str] = None
    publisher_id: Optional[str] = None

    # Validation details
    validation_details: ValidationDetails = Field(default_factory=ValidationDetails)
    validation_score: float = 0.0

    # Component scores (actual values, not fallbacks)
    quality_score: Optional[float] = None

    # Timestamps
    ingested_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    validated_at: Optional[str] = None

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True


class ValidationResult(BaseModel):
    """Result of validation pipeline."""

    article_id: str
    trace_id: str
    job_id: str
    is_valid: bool
    validation_score: float
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    # Output message (either validated or rejected)
    validated_message: Optional[NewsValidated] = None
    rejected_message: Optional[NewsRejected] = None


class HealthStatus(BaseModel):
    """Health check status."""

    status: str  # "healthy", "degraded", "unhealthy"
    timestamp: str
    components: Dict[str, str]  # Component name -> status
    version: str = "1.0.0"


class ReadinessStatus(BaseModel):
    """Readiness check status."""

    ready: bool
    timestamp: str
    dependencies: Dict[str, bool]  # Dependency name -> ready status
