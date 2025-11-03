"""Tests for Pydantic models."""

import pytest
from src.models import (
    NewsRaw,
    NewsValidated,
    NewsRejected,
    ValidationContext,
    ValidationResult,
    ValidationDetails,
    HealthStatus,
)


class TestNewsRaw:
    """Test NewsRaw model."""

    def test_create_news_raw(self):
        """Test creating NewsRaw."""
        msg = NewsRaw(
            article_id="123",
            canonical_url="https://example.com",
            title="Test Title",
            body="Test Body",
            url="https://example.com",
            published_at="2025-11-02T10:00:00Z",
            language="en",
            source="test_source",
            crawled_at="2025-11-02T11:00:00Z",
            checksum="abc123",
            validation_score=0.8,
            schema_version="1.0.0",
            ingest_job_id="job_123",
            publisher_id="pub_123",
            extraction_method="rss",
        )

        assert msg.article_id == "123"
        assert msg.title == "Test Title"


class TestValidationDetails:
    """Test ValidationDetails model."""

    def test_create_validation_details(self):
        """Test creating ValidationDetails."""
        details = ValidationDetails(
            schema_valid=True,
            encoding_valid=True,
            timestamp_valid=True,
            source_verified=True,
            language_detected=True,
            not_duplicate=True,
            content_quality_ok=True,
        )

        assert details.schema_valid is True
        assert details.language_detected is True


class TestNewsValidated:
    """Test NewsValidated model."""

    def test_create_news_validated(self):
        """Test creating NewsValidated."""
        details = ValidationDetails()
        msg = NewsValidated(
            article_id="art_123",
            canonical_url="https://example.com",
            title="Test Title",
            body="Test Body",
            url="https://example.com",
            source="test_source",
            language="en",
            language_confidence=0.95,
            language_detection_method="consensus",
            source_published_at_raw="2025-11-02T10:00:00Z",
            source_published_at_utc="2025-11-02T10:00:00Z",
            ingested_at="2025-11-02T11:00:00Z",
            validated_at="2025-11-02T11:01:00Z",
            checksum="abc123",
            validation_score=0.88,
            validation_details=details,
            schema_version="1.0.0",
            ingest_job_id="job_123",
            validation_job_id="job_456",
            trace_id="trace_123",
        )

        assert msg.article_id == "art_123"
        assert msg.language == "en"

    def test_validate_score_range(self):
        """Test validation score range validation."""
        details = ValidationDetails()

        # Valid score
        msg = NewsValidated(
            article_id="art_123",
            canonical_url="https://example.com",
            title="Test Title",
            body="Test Body",
            url="https://example.com",
            source="test_source",
            language="en",
            language_confidence=0.95,
            language_detection_method="consensus",
            source_published_at_raw="2025-11-02T10:00:00Z",
            source_published_at_utc="2025-11-02T10:00:00Z",
            ingested_at="2025-11-02T11:00:00Z",
            validated_at="2025-11-02T11:01:00Z",
            checksum="abc123",
            validation_score=0.88,
            validation_details=details,
            schema_version="1.0.0",
            ingest_job_id="job_123",
            validation_job_id="job_456",
            trace_id="trace_123",
        )

        assert msg.validation_score == 0.88

        # Invalid score - too high
        with pytest.raises(ValueError):
            NewsValidated(
                article_id="art_123",
                canonical_url="https://example.com",
                title="Test Title",
                body="Test Body",
                url="https://example.com",
                source="test_source",
                language="en",
                language_confidence=0.95,
                language_detection_method="consensus",
                source_published_at_raw="2025-11-02T10:00:00Z",
                source_published_at_utc="2025-11-02T10:00:00Z",
                ingested_at="2025-11-02T11:00:00Z",
                validated_at="2025-11-02T11:01:00Z",
                checksum="abc123",
                validation_score=1.5,
                validation_details=details,
                schema_version="1.0.0",
                ingest_job_id="job_123",
                validation_job_id="job_456",
                trace_id="trace_123",
            )


class TestNewsRejected:
    """Test NewsRejected model."""

    def test_create_news_rejected(self):
        """Test creating NewsRejected."""
        msg = NewsRejected(
            article_id="art_123",
            url="https://example.com",
            source="test_source",
            rejected_at="2025-11-02T11:01:00Z",
            validation_score=0.45,
            rejection_reason="Low quality",
            error_codes=["QUALITY_LOW"],
            error_details={"quality": "0.45"},
            original_message={"id": "123"},
            trace_id="trace_123",
            validation_job_id="job_456",
            schema_version="1.0.0",
        )

        assert msg.article_id == "art_123"
        assert msg.rejection_reason == "Low quality"


class TestValidationContext:
    """Test ValidationContext model."""

    def test_create_validation_context(self):
        """Test creating ValidationContext."""
        raw_msg = NewsRaw(
            article_id="123",
            canonical_url="https://example.com",
            title="Test Title",
            body="Test Body",
            url="https://example.com",
            published_at="2025-11-02T10:00:00Z",
            language="en",
            source="test_source",
            crawled_at="2025-11-02T11:00:00Z",
            checksum="abc123",
            validation_score=0.8,
            schema_version="1.0.0",
            ingest_job_id="job_123",
            publisher_id="pub_123",
            extraction_method="rss",
        )

        context = ValidationContext(
            article_id="art_123",
            trace_id="trace_123",
            job_id="job_123",
            raw_message=raw_msg,
        )

        assert context.article_id == "art_123"
        assert context.raw_message.article_id == "123"


class TestValidationResult:
    """Test ValidationResult model."""

    def test_create_validation_result(self):
        """Test creating ValidationResult."""
        result = ValidationResult(
            article_id="art_123",
            trace_id="trace_123",
            job_id="job_123",
            is_valid=True,
            validation_score=0.88,
        )

        assert result.article_id == "art_123"
        assert result.is_valid is True


class TestHealthStatus:
    """Test HealthStatus model."""

    def test_create_health_status(self):
        """Test creating HealthStatus."""
        status = HealthStatus(
            status="healthy",
            timestamp="2025-11-02T11:00:00Z",
            components={"kafka": "healthy", "redis": "healthy"},
        )

        assert status.status == "healthy"
        assert status.components["kafka"] == "healthy"
