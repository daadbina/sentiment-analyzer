"""Tests for validation scoring stage."""

import pytest
from unittest.mock import patch, MagicMock
from src.pipeline.scoring_stage import ValidationScoringStage
from src.models import ValidationContext, ValidationDetails, NewsRaw
from src.validation.scoring import ValidationScorer


class TestValidationScoringStage:
    """Test validation scoring stage."""

    @pytest.fixture
    def stage(self):
        """Create validation scoring stage."""
        return ValidationScoringStage()

    def _create_raw_message(self):
        """Create a valid NewsRaw message."""
        return NewsRaw(
            article_id="art_123",
            canonical_url="https://example.com/article",
            title="Test Article",
            body="This is a test article body with sufficient content.",
            url="https://example.com/article",
            published_at="2025-11-03T10:00:00Z",
            language="en",
            source="example",
            crawled_at="2025-11-03T10:05:00Z",
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

        context = ValidationContext(
            article_id="art_123",
            trace_id="trace_123",
            job_id="job_123",
            raw_message=raw_message,
            validation_details=ValidationDetails(),
        )
        # Set title and body from raw message
        context.title = raw_message.title
        context.body = raw_message.body
        context.url = raw_message.url
        context.language = raw_message.language
        context.language_confidence = 0.95
        context.quality_score = 0.8
        context.country = "United States"
        return context

    def test_stage_initialization(self, stage):
        """Test stage initialization."""
        assert stage.name == "ValidationScoring"

    @pytest.mark.asyncio
    async def test_execute_calculates_score(self, stage):
        """Test execution calculates validation score."""
        context = self._create_context()

        result = await stage.execute(context)

        assert result.validation_score is not None
        assert isinstance(result.validation_score, (int, float))
        assert 0.0 <= result.validation_score <= 1.0

    @pytest.mark.asyncio
    async def test_execute_high_score(self, stage):
        """Test execution with high validation score."""
        context = self._create_context()
        context.validation_details.language_detected = True
        context.validation_details.source_verified = True
        context.validation_details.encoding_valid = True
        context.validation_details.timestamp_valid = True
        context.language_confidence = 0.95
        context.quality_score = 0.95
        context.country = "United States"

        with patch.object(
            ValidationScorer,
            'calculate_language_score',
            return_value=1.0
        ), patch.object(
            ValidationScorer,
            'calculate_source_score',
            return_value=1.0
        ), patch.object(
            ValidationScorer,
            'calculate_encoding_score',
            return_value=1.0
        ), patch.object(
            ValidationScorer,
            'calculate_timestamp_score',
            return_value=1.0
        ), patch.object(
            ValidationScorer,
            'calculate_geographic_score',
            return_value=1.0
        ), patch.object(
            ValidationScorer,
            'calculate_content_score',
            return_value=1.0
        ), patch.object(
            ValidationScorer,
            'calculate_validation_score',
            return_value=0.95
        ):
            result = await stage.execute(context)

        assert result.validation_score == 0.95

    @pytest.mark.asyncio
    async def test_execute_low_score(self, stage):
        """Test execution with low validation score."""
        context = self._create_context()
        context.validation_details.language_detected = False
        context.validation_details.source_verified = False
        context.validation_details.encoding_valid = False
        context.validation_details.timestamp_valid = False
        context.language_confidence = 0.0
        context.quality_score = 0.0
        context.country = None

        with patch.object(
            ValidationScorer,
            'calculate_language_score',
            return_value=0.0
        ), patch.object(
            ValidationScorer,
            'calculate_source_score',
            return_value=0.0
        ), patch.object(
            ValidationScorer,
            'calculate_encoding_score',
            return_value=0.0
        ), patch.object(
            ValidationScorer,
            'calculate_timestamp_score',
            return_value=0.0
        ), patch.object(
            ValidationScorer,
            'calculate_geographic_score',
            return_value=0.0
        ), patch.object(
            ValidationScorer,
            'calculate_content_score',
            return_value=0.0
        ), patch.object(
            ValidationScorer,
            'calculate_validation_score',
            return_value=0.0
        ):
            result = await stage.execute(context)

        assert result.validation_score == 0.0

    @pytest.mark.asyncio
    async def test_execute_calls_all_scorers(self, stage):
        """Test that all component scorers are called."""
        context = self._create_context()

        with patch.object(
            ValidationScorer,
            'calculate_language_score',
            return_value=0.9
        ) as mock_lang, patch.object(
            ValidationScorer,
            'calculate_source_score',
            return_value=0.9
        ) as mock_src, patch.object(
            ValidationScorer,
            'calculate_encoding_score',
            return_value=0.9
        ) as mock_enc, patch.object(
            ValidationScorer,
            'calculate_timestamp_score',
            return_value=0.9
        ) as mock_ts, patch.object(
            ValidationScorer,
            'calculate_geographic_score',
            return_value=0.9
        ) as mock_geo, patch.object(
            ValidationScorer,
            'calculate_content_score',
            return_value=0.9
        ) as mock_cont, patch.object(
            ValidationScorer,
            'calculate_validation_score',
            return_value=0.9
        ):
            result = await stage.execute(context)

        mock_lang.assert_called_once()
        mock_src.assert_called_once()
        mock_enc.assert_called_once()
        mock_ts.assert_called_once()
        mock_geo.assert_called_once()
        mock_cont.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_language_score_parameters(self, stage):
        """Test language score calculation parameters."""
        context = self._create_context()
        context.validation_details.language_detected = True
        context.language_confidence = 0.85

        with patch.object(
            ValidationScorer,
            'calculate_language_score',
            return_value=0.9
        ) as mock_lang, patch.object(
            ValidationScorer,
            'calculate_source_score',
            return_value=0.9
        ), patch.object(
            ValidationScorer,
            'calculate_encoding_score',
            return_value=0.9
        ), patch.object(
            ValidationScorer,
            'calculate_timestamp_score',
            return_value=0.9
        ), patch.object(
            ValidationScorer,
            'calculate_geographic_score',
            return_value=0.9
        ), patch.object(
            ValidationScorer,
            'calculate_content_score',
            return_value=0.9
        ), patch.object(
            ValidationScorer,
            'calculate_validation_score',
            return_value=0.9
        ):
            result = await stage.execute(context)

        mock_lang.assert_called_once_with(True, 0.85)

    @pytest.mark.asyncio
    async def test_execute_source_score_parameters(self, stage):
        """Test source score calculation parameters."""
        context = self._create_context()
        context.validation_details.source_verified = True

        with patch.object(
            ValidationScorer,
            'calculate_language_score',
            return_value=0.9
        ), patch.object(
            ValidationScorer,
            'calculate_source_score',
            return_value=0.9
        ) as mock_src, patch.object(
            ValidationScorer,
            'calculate_encoding_score',
            return_value=0.9
        ), patch.object(
            ValidationScorer,
            'calculate_timestamp_score',
            return_value=0.9
        ), patch.object(
            ValidationScorer,
            'calculate_geographic_score',
            return_value=0.9
        ), patch.object(
            ValidationScorer,
            'calculate_content_score',
            return_value=0.9
        ), patch.object(
            ValidationScorer,
            'calculate_validation_score',
            return_value=0.9
        ):
            result = await stage.execute(context)

        mock_src.assert_called_once_with(True, 1.0)

    @pytest.mark.asyncio
    async def test_execute_encoding_score_parameters(self, stage):
        """Test encoding score calculation parameters."""
        context = self._create_context()
        context.validation_details.encoding_valid = True

        with patch.object(
            ValidationScorer,
            'calculate_language_score',
            return_value=0.9
        ), patch.object(
            ValidationScorer,
            'calculate_source_score',
            return_value=0.9
        ), patch.object(
            ValidationScorer,
            'calculate_encoding_score',
            return_value=0.9
        ) as mock_enc, patch.object(
            ValidationScorer,
            'calculate_timestamp_score',
            return_value=0.9
        ), patch.object(
            ValidationScorer,
            'calculate_geographic_score',
            return_value=0.9
        ), patch.object(
            ValidationScorer,
            'calculate_content_score',
            return_value=0.9
        ), patch.object(
            ValidationScorer,
            'calculate_validation_score',
            return_value=0.9
        ):
            result = await stage.execute(context)

        mock_enc.assert_called_once_with(True)

    @pytest.mark.asyncio
    async def test_execute_timestamp_score_parameters(self, stage):
        """Test timestamp score calculation parameters."""
        context = self._create_context()
        context.validation_details.timestamp_valid = True

        with patch.object(
            ValidationScorer,
            'calculate_language_score',
            return_value=0.9
        ), patch.object(
            ValidationScorer,
            'calculate_source_score',
            return_value=0.9
        ), patch.object(
            ValidationScorer,
            'calculate_encoding_score',
            return_value=0.9
        ), patch.object(
            ValidationScorer,
            'calculate_timestamp_score',
            return_value=0.9
        ) as mock_ts, patch.object(
            ValidationScorer,
            'calculate_geographic_score',
            return_value=0.9
        ), patch.object(
            ValidationScorer,
            'calculate_content_score',
            return_value=0.9
        ), patch.object(
            ValidationScorer,
            'calculate_validation_score',
            return_value=0.9
        ):
            result = await stage.execute(context)

        mock_ts.assert_called_once_with(True)

    @pytest.mark.asyncio
    async def test_execute_geographic_score_parameters(self, stage):
        """Test geographic score calculation parameters."""
        context = self._create_context()
        context.country = "France"

        with patch.object(
            ValidationScorer,
            'calculate_language_score',
            return_value=0.9
        ), patch.object(
            ValidationScorer,
            'calculate_source_score',
            return_value=0.9
        ), patch.object(
            ValidationScorer,
            'calculate_encoding_score',
            return_value=0.9
        ), patch.object(
            ValidationScorer,
            'calculate_timestamp_score',
            return_value=0.9
        ), patch.object(
            ValidationScorer,
            'calculate_geographic_score',
            return_value=0.9
        ) as mock_geo, patch.object(
            ValidationScorer,
            'calculate_content_score',
            return_value=0.9
        ), patch.object(
            ValidationScorer,
            'calculate_validation_score',
            return_value=0.9
        ):
            result = await stage.execute(context)

        mock_geo.assert_called_once_with("France")

    @pytest.mark.asyncio
    async def test_execute_content_score_parameters(self, stage):
        """Test content score calculation parameters."""
        context = self._create_context()
        context.quality_score = 0.75

        with patch.object(
            ValidationScorer,
            'calculate_language_score',
            return_value=0.9
        ), patch.object(
            ValidationScorer,
            'calculate_source_score',
            return_value=0.9
        ), patch.object(
            ValidationScorer,
            'calculate_encoding_score',
            return_value=0.9
        ), patch.object(
            ValidationScorer,
            'calculate_timestamp_score',
            return_value=0.9
        ), patch.object(
            ValidationScorer,
            'calculate_geographic_score',
            return_value=0.9
        ), patch.object(
            ValidationScorer,
            'calculate_content_score',
            return_value=0.9
        ) as mock_cont, patch.object(
            ValidationScorer,
            'calculate_validation_score',
            return_value=0.9
        ):
            result = await stage.execute(context)

        mock_cont.assert_called_once_with(0.75)

    @pytest.mark.asyncio
    async def test_execute_exception_handling(self, stage):
        """Test exception handling."""
        context = self._create_context()

        with patch.object(
            ValidationScorer,
            'calculate_language_score',
            side_effect=Exception("Scoring error")
        ):
            result = await stage.execute(context)

        assert result.validation_score == 0.0
        assert len(result.errors) > 0
        assert "error" in result.errors[0].lower()

    @pytest.mark.asyncio
    async def test_execute_preserves_context(self, stage):
        """Test that context is preserved."""
        context = self._create_context()
        context.article_id = "art_123"
        context.trace_id = "trace_123"

        result = await stage.execute(context)

        assert result.article_id == "art_123"
        assert result.trace_id == "trace_123"

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

