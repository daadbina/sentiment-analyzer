"""Tests for quality scoring stage."""

import pytest
from unittest.mock import patch, MagicMock
from src.pipeline.quality_stage import QualityScoringStage
from src.models import ValidationContext, ValidationDetails, NewsRaw
from src.validation.quality import QualityScorer


class TestQualityScoringStage:
    """Test quality scoring stage."""

    @pytest.fixture
    def stage(self):
        """Create quality scoring stage."""
        return QualityScoringStage()

    def _create_raw_message(self):
        """Create a valid NewsRaw message."""
        return NewsRaw(
            article_id="art_123",
            canonical_url="https://example.com/article",
            title="Test Article",
            body="This is a test article body with sufficient content for quality scoring.",
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
        return context

    def test_stage_initialization(self, stage):
        """Test stage initialization."""
        assert stage.name == "QualityScoring"

    @pytest.mark.asyncio
    async def test_execute_valid_quality(self, stage):
        """Test execution with valid quality content."""
        context = self._create_context()

        result = await stage.execute(context)

        assert result.quality_score is not None
        assert isinstance(result.quality_score, (int, float))
        assert 0.0 <= result.quality_score <= 1.0

    @pytest.mark.asyncio
    async def test_execute_high_quality_score(self, stage):
        """Test execution with high quality score."""
        context = self._create_context()

        with patch.object(
            QualityScorer,
            'score_content',
            return_value=(0.9, [])
        ):
            result = await stage.execute(context)

        assert result.quality_score == 0.9
        assert result.validation_details.content_quality_ok is True

    @pytest.mark.asyncio
    async def test_execute_low_quality_score(self, stage):
        """Test execution with low quality score."""
        context = self._create_context()

        with patch.object(
            QualityScorer,
            'score_content',
            return_value=(0.5, ["Title too short", "Body too short"])
        ):
            result = await stage.execute(context)

        assert result.quality_score == 0.5
        assert result.validation_details.content_quality_ok is False

    @pytest.mark.asyncio
    async def test_execute_threshold_at_0_7(self, stage):
        """Test execution at quality threshold (0.7)."""
        context = self._create_context()

        with patch.object(
            QualityScorer,
            'score_content',
            return_value=(0.7, [])
        ):
            result = await stage.execute(context)

        assert result.quality_score == 0.7
        assert result.validation_details.content_quality_ok is True

    @pytest.mark.asyncio
    async def test_execute_just_below_threshold(self, stage):
        """Test execution just below quality threshold."""
        context = self._create_context()

        with patch.object(
            QualityScorer,
            'score_content',
            return_value=(0.69, ["Minor issue"])
        ):
            result = await stage.execute(context)

        assert result.quality_score == 0.69
        assert result.validation_details.content_quality_ok is False

    @pytest.mark.asyncio
    async def test_execute_adds_issues_as_warnings(self, stage):
        """Test that issues are added as warnings."""
        context = self._create_context()
        issues = ["Title too short", "Body too short", "Low word count"]

        with patch.object(
            QualityScorer,
            'score_content',
            return_value=(0.5, issues)
        ):
            result = await stage.execute(context)

        assert len(result.warnings) == len(issues)
        for issue in issues:
            assert issue in result.warnings

    @pytest.mark.asyncio
    async def test_execute_no_issues(self, stage):
        """Test execution with no quality issues."""
        context = self._create_context()
        initial_warnings = len(context.warnings)

        with patch.object(
            QualityScorer,
            'score_content',
            return_value=(0.95, [])
        ):
            result = await stage.execute(context)

        assert len(result.warnings) == initial_warnings

    @pytest.mark.asyncio
    async def test_execute_exception_handling(self, stage):
        """Test exception handling."""
        context = self._create_context()

        with patch.object(
            QualityScorer,
            'score_content',
            side_effect=Exception("Scoring error")
        ):
            result = await stage.execute(context)

        assert result.quality_score == 0.0
        assert result.validation_details.content_quality_ok is False
        assert len(result.errors) > 0
        assert "error" in result.errors[0].lower()

    @pytest.mark.asyncio
    async def test_execute_passes_correct_parameters(self, stage):
        """Test that correct parameters are passed to scorer."""
        context = self._create_context()
        context.title = "Test Title"
        context.body = "Test Body"
        context.url = "https://example.com"
        context.language = "en"

        with patch.object(
            QualityScorer,
            'score_content',
            return_value=(0.8, [])
        ) as mock_score:
            result = await stage.execute(context)

        mock_score.assert_called_once_with(
            "Test Title",
            "Test Body",
            "https://example.com",
            "en"
        )

    @pytest.mark.asyncio
    async def test_execute_empty_title(self, stage):
        """Test execution with empty title."""
        context = self._create_context()
        context.title = ""

        with patch.object(
            QualityScorer,
            'score_content',
            return_value=(0.5, ["Title too short"])
        ) as mock_score:
            result = await stage.execute(context)

        # Verify empty string is passed
        mock_score.assert_called_once()
        call_args = mock_score.call_args[0]
        assert call_args[0] == ""

    @pytest.mark.asyncio
    async def test_execute_empty_body(self, stage):
        """Test execution with empty body."""
        context = self._create_context()
        context.body = ""

        with patch.object(
            QualityScorer,
            'score_content',
            return_value=(0.5, ["Body too short"])
        ) as mock_score:
            result = await stage.execute(context)

        # Verify empty string is passed
        mock_score.assert_called_once()
        call_args = mock_score.call_args[0]
        assert call_args[1] == ""

    @pytest.mark.asyncio
    async def test_execute_none_title(self, stage):
        """Test execution with None title."""
        context = self._create_context()
        context.title = None

        with patch.object(
            QualityScorer,
            'score_content',
            return_value=(0.5, ["Title missing"])
        ) as mock_score:
            result = await stage.execute(context)

        # Verify empty string is passed for None
        mock_score.assert_called_once()
        call_args = mock_score.call_args[0]
        assert call_args[0] == ""

    @pytest.mark.asyncio
    async def test_execute_none_body(self, stage):
        """Test execution with None body."""
        context = self._create_context()
        context.body = None

        with patch.object(
            QualityScorer,
            'score_content',
            return_value=(0.5, ["Body missing"])
        ) as mock_score:
            result = await stage.execute(context)

        # Verify empty string is passed for None
        mock_score.assert_called_once()
        call_args = mock_score.call_args[0]
        assert call_args[1] == ""

    @pytest.mark.asyncio
    async def test_execute_none_url(self, stage):
        """Test execution with None URL."""
        context = self._create_context()
        context.url = None

        with patch.object(
            QualityScorer,
            'score_content',
            return_value=(0.8, [])
        ) as mock_score:
            result = await stage.execute(context)

        # Verify empty string is passed for None
        mock_score.assert_called_once()
        call_args = mock_score.call_args[0]
        assert call_args[2] == ""

    @pytest.mark.asyncio
    async def test_execute_none_language(self, stage):
        """Test execution with None language."""
        context = self._create_context()
        context.language = None

        with patch.object(
            QualityScorer,
            'score_content',
            return_value=(0.8, [])
        ) as mock_score:
            result = await stage.execute(context)

        # Verify default language is used
        mock_score.assert_called_once()
        call_args = mock_score.call_args[0]
        assert call_args[3] == "en"

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
    async def test_execute_multiple_calls(self, stage):
        """Test multiple executions."""
        context1 = self._create_context()
        context2 = self._create_context()

        result1 = await stage.execute(context1)
        result2 = await stage.execute(context2)

        assert result1.quality_score is not None
        assert result2.quality_score is not None

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
    async def test_execute_different_languages(self, stage):
        """Test execution with different languages."""
        languages = ["en", "fr", "de", "es", "ar", "zh", "ru"]

        for lang in languages:
            context = self._create_context()
            context.language = lang

            with patch.object(
                QualityScorer,
                'score_content',
                return_value=(0.8, [])
            ) as mock_score:
                result = await stage.execute(context)

            # Verify language is passed correctly
            mock_score.assert_called_once()
            call_args = mock_score.call_args[0]
            assert call_args[3] == lang

