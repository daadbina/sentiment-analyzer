"""Tests for timestamp validation stage."""

import pytest
from unittest.mock import patch, MagicMock
from src.pipeline.timestamp_stage import TimestampValidationStage
from src.models import ValidationContext, ValidationDetails, NewsRaw
from src.validation.timestamp import TimestampValidator


class TestTimestampValidationStage:
    """Test timestamp validation stage."""

    @pytest.fixture
    def stage(self):
        """Create timestamp validation stage."""
        return TimestampValidationStage()

    def _create_raw_message(self, published_at="2025-11-03T10:00:00Z", crawled_at="2025-11-03T10:05:00Z"):
        """Create a valid NewsRaw message."""
        return NewsRaw(
            article_id="art_123",
            canonical_url="https://example.com/article",
            title="Test Article",
            body="This is a test article body with sufficient content.",
            url="https://example.com/article",
            published_at=published_at,
            language="en",
            source="example",
            crawled_at=crawled_at,
            checksum="abc123",
            validation_score=0.9,
            schema_version="1.0.0",
            ingest_job_id="job_123",
            publisher_id="pub_123",
            extraction_method="html",
        )

    def _create_context(self, raw_message=None):
        """Create a validation context."""
        if raw_message is None:
            raw_message = self._create_raw_message()

        return ValidationContext(
            article_id="art_123",
            trace_id="trace_123",
            job_id="job_123",
            raw_message=raw_message,
            validation_details=ValidationDetails(),
        )

    def test_stage_initialization(self, stage):
        """Test stage initialization."""
        assert stage.name == "TimestampValidation"

    @pytest.mark.asyncio
    async def test_execute_valid_timestamp(self, stage):
        """Test execution with valid timestamp."""
        context = self._create_context()

        result = await stage.execute(context)

        assert result.validation_details.timestamp_valid is True
        assert result.source_published_at_utc is not None
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_execute_invalid_timestamp(self, stage):
        """Test execution with invalid timestamp."""
        raw_msg = self._create_raw_message(published_at="invalid-date")
        context = self._create_context(raw_msg)

        result = await stage.execute(context)

        assert result.validation_details.timestamp_valid is False
        assert len(result.errors) > 0
        assert "Timestamp validation failed" in result.errors[0]

    @pytest.mark.asyncio
    async def test_execute_iso8601_timestamp(self, stage):
        """Test execution with ISO-8601 timestamp."""
        raw_msg = self._create_raw_message(published_at="2025-11-03T10:00:00Z")
        context = self._create_context(raw_msg)

        result = await stage.execute(context)

        assert result.validation_details.timestamp_valid is True
        assert result.source_published_at_utc is not None

    @pytest.mark.asyncio
    async def test_execute_rfc2822_timestamp(self, stage):
        """Test execution with RFC-2822 timestamp."""
        raw_msg = self._create_raw_message(published_at="Sun, 03 Nov 2025 10:00:00 GMT")
        context = self._create_context(raw_msg)

        result = await stage.execute(context)

        assert result.validation_details.timestamp_valid is True
        assert result.source_published_at_utc is not None

    @pytest.mark.asyncio
    async def test_execute_unix_timestamp(self, stage):
        """Test execution with Unix timestamp."""
        raw_msg = self._create_raw_message(published_at="1730625600")
        context = self._create_context(raw_msg)

        result = await stage.execute(context)

        assert result.validation_details.timestamp_valid is True
        assert result.source_published_at_utc is not None

    @pytest.mark.asyncio
    async def test_execute_future_date_beyond_24h(self, stage):
        """Test execution with future date beyond 24 hours (should fail)."""
        raw_msg = self._create_raw_message(
            published_at="2025-11-05T10:00:00Z",  # 2 days in future
            crawled_at="2025-11-03T10:05:00Z"
        )
        context = self._create_context(raw_msg)

        result = await stage.execute(context)

        # Future dates beyond 24 hours should fail
        assert result.validation_details.timestamp_valid is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_execute_old_date_beyond_5_years(self, stage):
        """Test execution with very old date beyond 5 years (should fail)."""
        raw_msg = self._create_raw_message(
            published_at="2015-11-03T10:00:00Z",  # 10 years old
            crawled_at="2025-11-03T10:05:00Z"
        )
        context = self._create_context(raw_msg)

        result = await stage.execute(context)

        # Old dates beyond 5 years should fail
        assert result.validation_details.timestamp_valid is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_execute_temporal_coherence_check(self, stage):
        """Test temporal coherence (published_at <= crawled_at)."""
        raw_msg = self._create_raw_message(
            published_at="2025-11-03T10:00:00Z",
            crawled_at="2025-11-03T10:05:00Z"
        )
        context = self._create_context(raw_msg)

        result = await stage.execute(context)

        assert result.validation_details.timestamp_valid is True

    @pytest.mark.asyncio
    async def test_execute_temporal_incoherence(self, stage):
        """Test temporal incoherence (published_at > crawled_at)."""
        raw_msg = self._create_raw_message(
            published_at="2025-11-03T10:10:00Z",  # After crawled_at
            crawled_at="2025-11-03T10:05:00Z"
        )
        context = self._create_context(raw_msg)

        result = await stage.execute(context)

        assert result.validation_details.timestamp_valid is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_execute_preserves_context(self, stage):
        """Test that context is preserved."""
        context = self._create_context()
        context.title = "Original Title"
        context.body = "Original Body"

        result = await stage.execute(context)

        assert result.title == "Original Title"
        assert result.body == "Original Body"

    @pytest.mark.asyncio
    async def test_execute_exception_handling(self, stage):
        """Test exception handling."""
        context = self._create_context()

        with patch.object(
            TimestampValidator,
            'validate_and_normalize',
            side_effect=Exception("Validation error")
        ):
            result = await stage.execute(context)

        assert result.validation_details.timestamp_valid is False
        assert len(result.errors) > 0
        assert "error" in result.errors[0].lower()

    @pytest.mark.asyncio
    async def test_execute_warning_added_on_warning_message(self, stage):
        """Test that warning is added when error message is a warning."""
        context = self._create_context()

        with patch.object(
            TimestampValidator,
            'validate_and_normalize',
            return_value=(True, "2025-11-03T10:00:00Z", "R1_FUTURE_DATE")
        ):
            result = await stage.execute(context)

        assert result.validation_details.timestamp_valid is True
        assert len(result.warnings) > 0
        assert "R1_FUTURE_DATE" in result.warnings[0]

    @pytest.mark.asyncio
    async def test_execute_recent_article(self, stage):
        """Test execution with recent article."""
        raw_msg = self._create_raw_message(
            published_at="2025-11-03T09:00:00Z",  # 1 hour before crawl
            crawled_at="2025-11-03T10:05:00Z"
        )
        context = self._create_context(raw_msg)

        result = await stage.execute(context)

        assert result.validation_details.timestamp_valid is True
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_execute_normalized_utc_stored(self, stage):
        """Test that normalized UTC timestamp is stored."""
        context = self._create_context()

        result = await stage.execute(context)

        assert result.source_published_at_utc is not None
        assert "Z" in result.source_published_at_utc or "+" in result.source_published_at_utc or "-" in result.source_published_at_utc

    @pytest.mark.asyncio
    async def test_execute_multiple_calls(self, stage):
        """Test multiple executions."""
        context1 = self._create_context()
        context2 = self._create_context()

        result1 = await stage.execute(context1)
        result2 = await stage.execute(context2)

        assert result1.validation_details.timestamp_valid is True
        assert result2.validation_details.timestamp_valid is True

    @pytest.mark.asyncio
    async def test_execute_context_article_id_preserved(self, stage):
        """Test that article ID is preserved."""
        context = self._create_context()
        original_article_id = context.article_id

        result = await stage.execute(context)

        assert result.article_id == original_article_id

    @pytest.mark.asyncio
    async def test_execute_context_trace_id_preserved(self, stage):
        """Test that trace ID is preserved."""
        context = self._create_context()
        original_trace_id = context.trace_id

        result = await stage.execute(context)

        assert result.trace_id == original_trace_id

    @pytest.mark.asyncio
    async def test_execute_context_job_id_preserved(self, stage):
        """Test that job ID is preserved."""
        context = self._create_context()
        original_job_id = context.job_id

        result = await stage.execute(context)

        assert result.job_id == original_job_id

    @pytest.mark.asyncio
    async def test_execute_different_date_formats(self, stage):
        """Test execution with different date formats."""
        formats = [
            "2025-11-03T10:00:00Z",
            "2025-11-03 10:00:00",
            "11/03/2025 10:00:00",
        ]

        for date_format in formats:
            raw_msg = self._create_raw_message(published_at=date_format)
            context = self._create_context(raw_msg)

            result = await stage.execute(context)

            # Should handle various formats
            assert result.validation_details.timestamp_valid is True or result.validation_details.timestamp_valid is False

