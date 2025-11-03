"""Pytest configuration and fixtures."""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_validated_message():
    """Create sample validated message."""
    from src.models import NewsValidatedMessage, ValidationDetails

    return NewsValidatedMessage(
        article_id="test-article-1",
        canonical_url="https://example.com/article",
        title="Test Article Title",
        body="This is the test article body with sufficient content.",
        url="https://example.com/article",
        source="test-source",
        language="en",
        language_confidence=0.95,
        language_detection_method="langdetect",
        source_published_at_raw="2024-01-01T12:00:00Z",
        source_published_at_utc="2024-01-01T12:00:00Z",
        ingested_at="2024-01-01T12:05:00Z",
        validated_at="2024-01-01T12:10:00Z",
        country="US",
        checksum="abc123",
        validation_score=0.95,
        validation_details=ValidationDetails(
            schema_valid=True,
            encoding_valid=True,
            timestamp_valid=True,
            source_verified=True,
            language_detected=True,
            not_duplicate=True,
            content_quality_ok=True,
        ),
        schema_version="1.0",
        ingest_job_id="ingest-job-1",
        validation_job_id="validation-job-1",
        trace_id="trace-123",
        publisher_id="pub-1",
    )


@pytest.fixture
def sample_canonical_message():
    """Create sample canonical message."""
    from src.models import NewsCanonicalMessage, NormalizationDetails

    return NewsCanonicalMessage(
        article_id="test-article-1",
        canonical_url="https://example.com/article",
        normalized_url="https://example.com/article",
        url_hash="hash123",
        title="Test Article Title",
        normalized_title="Test Article Title",
        body="This is the test article body with sufficient content.",
        normalized_body="This is the test article body with sufficient content.",
        url="https://example.com/article",
        source="test-source",
        publisher_id="pub-1",
        publisher_name="Test Publisher",
        publisher_credibility=0.9,
        publisher_country="US",
        language="en",
        source_published_at_utc="2024-01-01T12:00:00Z",
        validated_at="2024-01-01T12:10:00Z",
        canonicalized_at="2024-01-01T12:15:00Z",
        country="US",
        region="NA",
        domain_category="politics",
        content_type="article",
        readability_score=0.75,
        word_count=50,
        sentence_count=5,
        checksum="abc123",
        normalized_checksum="abc123",
        validation_score=0.95,
        normalization_score=0.88,
        normalization_details=NormalizationDetails(
            url_canonicalized=True,
            redirects_resolved=False,
            publisher_identified=True,
            content_cleaned=True,
            metadata_enriched=True,
            domain_classified=True,
            fuzzy_dedup_checked=True,
        ),
        schema_version="1.0",
        ingest_job_id="ingest-job-1",
        validation_job_id="validation-job-1",
        canonicalization_job_id="canon-job-1",
        trace_id="trace-123",
    )

