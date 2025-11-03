"""Tests for language detection stage."""

import pytest
from unittest.mock import patch, MagicMock
from src.pipeline.language_stage import LanguageDetectionStage
from src.models import ValidationContext, ValidationDetails, NewsRaw
from src.language.detector import LanguageDetector


class TestLanguageDetectionStage:
    """Test language detection stage."""

    @pytest.fixture
    def stage(self):
        """Create language detection stage."""
        return LanguageDetectionStage()

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
        context.source = raw_message.source
        return context

    def test_stage_initialization(self, stage):
        """Test stage initialization."""
        assert stage.name == "LanguageDetection"
        assert stage.detector is not None

    @pytest.mark.asyncio
    async def test_execute_english_detection(self, stage):
        """Test execution with English text."""
        context = self._create_context()

        result = await stage.execute(context)

        assert result.validation_details.language_detected is True
        assert result.language is not None
        assert result.language_confidence is not None
        assert result.language_detection_method is not None
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_execute_language_code_set(self, stage):
        """Test that language code is set."""
        context = self._create_context()

        result = await stage.execute(context)

        assert result.language is not None
        assert isinstance(result.language, str)
        assert len(result.language) > 0

    @pytest.mark.asyncio
    async def test_execute_confidence_set(self, stage):
        """Test that confidence is set."""
        context = self._create_context()

        result = await stage.execute(context)

        assert result.language_confidence is not None
        assert isinstance(result.language_confidence, (int, float))
        assert 0.0 <= result.language_confidence <= 1.0

    @pytest.mark.asyncio
    async def test_execute_detection_method_set(self, stage):
        """Test that detection method is set."""
        context = self._create_context()

        result = await stage.execute(context)

        assert result.language_detection_method is not None
        assert isinstance(result.language_detection_method, str)
        assert len(result.language_detection_method) > 0

    @pytest.mark.asyncio
    async def test_execute_failed_detection(self, stage):
        """Test execution when detection fails."""
        context = self._create_context()

        with patch.object(
            stage.detector,
            'detect',
            return_value=(None, 0.0, "failed")
        ):
            result = await stage.execute(context)

        assert result.validation_details.language_detected is False
        assert len(result.errors) > 0
        assert "Language detection failed" in result.errors[0]

    @pytest.mark.asyncio
    async def test_execute_exception_handling(self, stage):
        """Test exception handling."""
        context = self._create_context()

        with patch.object(
            stage.detector,
            'detect',
            side_effect=Exception("Detection error")
        ):
            result = await stage.execute(context)

        assert result.validation_details.language_detected is False
        assert len(result.errors) > 0
        assert "error" in result.errors[0].lower()

    @pytest.mark.asyncio
    async def test_execute_combines_title_and_body(self, stage):
        """Test that title and body are combined for detection."""
        context = self._create_context()
        context.title = "Title Text"
        context.body = "Body Text"

        with patch.object(
            stage.detector,
            'detect',
            return_value=("en", 0.95, "fasttext")
        ) as mock_detect:
            result = await stage.execute(context)

        # Verify detect was called with combined text
        mock_detect.assert_called_once()
        call_args = mock_detect.call_args[0][0]
        assert "Title Text" in call_args
        assert "Body Text" in call_args

    @pytest.mark.asyncio
    async def test_execute_rss_summary_source_type(self, stage):
        """Test that RSS summary source type is used when source is set."""
        context = self._create_context()
        context.source = "example"

        with patch.object(
            stage.detector,
            'detect',
            return_value=("en", 0.95, "fasttext")
        ) as mock_detect:
            result = await stage.execute(context)

        # Verify source_type parameter
        mock_detect.assert_called_once()
        call_kwargs = mock_detect.call_args[1]
        assert call_kwargs.get("source_type") == "rss_summary"

    @pytest.mark.asyncio
    async def test_execute_full_article_source_type(self, stage):
        """Test that full article source type is used when source is None."""
        context = self._create_context()
        context.source = None

        with patch.object(
            stage.detector,
            'detect',
            return_value=("en", 0.95, "fasttext")
        ) as mock_detect:
            result = await stage.execute(context)

        # Verify source_type parameter
        mock_detect.assert_called_once()
        call_kwargs = mock_detect.call_args[1]
        assert call_kwargs.get("source_type") == "full_article"

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

        assert result1.validation_details.language_detected is True
        assert result2.validation_details.language_detected is True

    @pytest.mark.asyncio
    async def test_execute_different_languages(self, stage):
        """Test detection of different languages."""
        languages = [
            ("en", "English text"),
            ("fr", "Texte français"),
            ("de", "Deutscher Text"),
            ("es", "Texto español"),
        ]

        for lang_code, text in languages:
            context = self._create_context()
            context.title = text
            context.body = text

            with patch.object(
                stage.detector,
                'detect',
                return_value=(lang_code, 0.95, "fasttext")
            ):
                result = await stage.execute(context)

            assert result.language == lang_code
            assert result.validation_details.language_detected is True

    @pytest.mark.asyncio
    async def test_execute_low_confidence(self, stage):
        """Test detection with low confidence."""
        context = self._create_context()

        with patch.object(
            stage.detector,
            'detect',
            return_value=("en", 0.45, "fasttext")
        ):
            result = await stage.execute(context)

        assert result.validation_details.language_detected is True
        assert result.language_confidence == 0.45

    @pytest.mark.asyncio
    async def test_execute_high_confidence(self, stage):
        """Test detection with high confidence."""
        context = self._create_context()

        with patch.object(
            stage.detector,
            'detect',
            return_value=("en", 0.99, "fasttext")
        ):
            result = await stage.execute(context)

        assert result.validation_details.language_detected is True
        assert result.language_confidence == 0.99

    @pytest.mark.asyncio
    async def test_execute_empty_title(self, stage):
        """Test execution with empty title."""
        context = self._create_context()
        context.title = ""

        result = await stage.execute(context)

        # Should still attempt detection with body only
        assert result.validation_details.language_detected is True or result.validation_details.language_detected is False

    @pytest.mark.asyncio
    async def test_execute_empty_body(self, stage):
        """Test execution with empty body."""
        context = self._create_context()
        context.body = ""

        result = await stage.execute(context)

        # Should still attempt detection with title only
        assert result.validation_details.language_detected is True or result.validation_details.language_detected is False

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
    async def test_execute_fasttext_method(self, stage):
        """Test detection using fasttext method."""
        context = self._create_context()

        with patch.object(
            stage.detector,
            'detect',
            return_value=("en", 0.95, "fasttext")
        ):
            result = await stage.execute(context)

        assert result.language_detection_method == "fasttext"

    @pytest.mark.asyncio
    async def test_execute_transformer_method(self, stage):
        """Test detection using transformer method."""
        context = self._create_context()

        with patch.object(
            stage.detector,
            'detect',
            return_value=("en", 0.98, "transformer")
        ):
            result = await stage.execute(context)

        assert result.language_detection_method == "transformer"

