"""Data models for canonicalizer-normalizer service."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime


class ValidationDetails(BaseModel):
    """Validation details from ingest-validator."""

    schema_valid: bool
    encoding_valid: bool
    timestamp_valid: bool
    source_verified: bool
    language_detected: bool
    not_duplicate: bool
    content_quality_ok: bool


class NewsValidatedMessage(BaseModel):
    """Input message from news_validated topic."""

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


class NormalizationDetails(BaseModel):
    """Normalization transformation details."""

    url_canonicalized: bool = False
    redirects_resolved: bool = False
    publisher_identified: bool = False
    content_cleaned: bool = False
    metadata_enriched: bool = False
    domain_classified: bool = False
    fuzzy_dedup_checked: bool = False
    transformations_applied: List[str] = Field(default_factory=list)


class NewsCanonicalMessage(BaseModel):
    """Output message for news_canonical topic."""

    article_id: str
    canonical_url: str
    normalized_url: str
    url_hash: str
    title: str
    normalized_title: str
    body: str
    normalized_body: str
    url: str
    source: str
    publisher_id: str
    publisher_name: str
    publisher_credibility: float
    publisher_country: Optional[str] = None
    language: str
    source_published_at_utc: str
    validated_at: str
    canonicalized_at: str
    country: Optional[str] = None
    region: Optional[str] = None
    domain_category: str
    content_type: str
    readability_score: float
    word_count: int
    sentence_count: int
    checksum: str
    normalized_checksum: str
    validation_score: float
    normalization_score: float
    normalization_details: NormalizationDetails
    schema_version: str
    ingest_job_id: str
    validation_job_id: str
    canonicalization_job_id: str
    trace_id: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Kafka serialization."""
        return self.model_dump()


class PublisherEntity(BaseModel):
    """Publisher entity from registry."""

    publisher_id: str
    name: str
    domain: str
    credibility_score: float
    country: Optional[str] = None
    ownership_type: str = "independent"
    verified: bool = True


class URLNormalizationResult(BaseModel):
    """Result of URL normalization."""

    original_url: str
    normalized_url: str
    url_hash: str
    canonicalized: bool
    redirects_resolved: int = 0
    domain: str
    error: Optional[str] = None


class ContentNormalizationResult(BaseModel):
    """Result of content normalization."""

    original_title: str
    normalized_title: str
    original_body: str
    normalized_body: str
    normalized_checksum: str
    word_count: int
    sentence_count: int
    error: Optional[str] = None


class MetadataEnrichmentResult(BaseModel):
    """Result of metadata enrichment."""

    country: Optional[str] = None
    region: Optional[str] = None
    content_type: str = "article"
    readability_score: float = 0.0
    error: Optional[str] = None


class DomainClassificationResult(BaseModel):
    """Result of domain classification."""

    domain_category: str = "general"
    confidence: float = 0.0
    error: Optional[str] = None


class FuzzyDeduplicationResult(BaseModel):
    """Result of fuzzy deduplication."""

    similar_articles: List[Dict[str, Any]] = Field(default_factory=list)
    primary_article_id: Optional[str] = None
    checked: bool = False
    error: Optional[str] = None

