"""Tests for encoding validation stage."""

import pytest
from unittest.mock import patch, MagicMock
from src.pipeline.encoding_stage import EncodingValidationStage
from src.models import ValidationContext, ValidationDetails, NewsRaw
from src.validation.encoding import EncodingValidator


class TestEncodingValidationStage:
    """Test encoding validation stage."""

    @pytest.fixture
    def stage(self):
        """Create encoding validation stage."""
        return EncodingValidationStage()

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
        context.checksum = raw_message.checksum
        return context

    def test_stage_initialization(self, stage):
        """Test stage initialization."""
        assert stage.name == "EncodingValidation"

    @pytest.mark.asyncio
    async def test_execute_valid_encoding(self, stage):
        """Test execution with valid UTF-8 encoding."""
        context = self._create_context()

        result = await stage.execute(context)

        assert result.validation_details.encoding_valid is True
        assert len(result.errors) == 0
        assert result.title is not None
        assert result.body is not None

    @pytest.mark.asyncio
    async def test_execute_utf8_text(self, stage):
        """Test execution with UTF-8 text."""
        context = self._create_context()
        context.title = "Test Article with UTF-8: café"
        context.body = "Body with UTF-8: naïve résumé"

        result = await stage.execute(context)

        assert result.validation_details.encoding_valid is True
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_execute_empty_title(self, stage):
        """Test execution with empty title."""
        context = self._create_context()
        context.title = ""

        result = await stage.execute(context)

        assert result.validation_details.encoding_valid is True
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_execute_empty_body(self, stage):
        """Test execution with empty body."""
        context = self._create_context()
        context.body = ""

        result = await stage.execute(context)

        assert result.validation_details.encoding_valid is True
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_execute_none_title(self, stage):
        """Test execution with None title."""
        context = self._create_context()
        context.title = None

        result = await stage.execute(context)

        assert result.validation_details.encoding_valid is True
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_execute_none_body(self, stage):
        """Test execution with None body."""
        context = self._create_context()
        context.body = None

        result = await stage.execute(context)

        assert result.validation_details.encoding_valid is True
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_execute_invalid_title_encoding(self, stage):
        """Test execution with invalid title encoding."""
        context = self._create_context()

        with patch.object(
            EncodingValidator,
            'validate_and_sanitize',
            return_value=(False, None, None, "Invalid encoding")
        ):
            result = await stage.execute(context)

        assert result.validation_details.encoding_valid is False
        assert len(result.errors) > 0
        assert "Title encoding error" in result.errors[0]

    @pytest.mark.asyncio
    async def test_execute_invalid_body_encoding(self, stage):
        """Test execution with invalid body encoding."""
        context = self._create_context()

        # Mock to pass title validation but fail body validation
        call_count = [0]
        def mock_validate(data, checksum):
            call_count[0] += 1
            if call_count[0] == 1:  # First call (title)
                return (True, "sanitized_title", "utf-8", None)
            else:  # Second call (body)
                return (False, None, None, "Invalid encoding")

        with patch.object(
            EncodingValidator,
            'validate_and_sanitize',
            side_effect=mock_validate
        ):
            result = await stage.execute(context)

        assert result.validation_details.encoding_valid is False
        assert len(result.errors) > 0
        assert "Body encoding error" in result.errors[0]

    @pytest.mark.asyncio
    async def test_execute_sanitizes_title(self, stage):
        """Test that title is sanitized."""
        context = self._create_context()
        context.title = "Original Title"

        with patch.object(
            EncodingValidator,
            'validate_and_sanitize',
            return_value=(True, "Sanitized Title", "utf-8", None)
        ):
            result = await stage.execute(context)

        assert result.title == "Sanitized Title"

    @pytest.mark.asyncio
    async def test_execute_sanitizes_body(self, stage):
        """Test that body is sanitized."""
        context = self._create_context()
        context.body = "Original Body"

        with patch.object(
            EncodingValidator,
            'validate_and_sanitize',
            return_value=(True, "Sanitized Body", "utf-8", None)
        ):
            result = await stage.execute(context)

        assert result.body == "Sanitized Body"

    @pytest.mark.asyncio
    async def test_execute_recalculates_checksum(self, stage):
        """Test that checksum is recalculated after sanitization."""
        context = self._create_context()
        original_checksum = context.checksum

        with patch.object(
            EncodingValidator,
            'validate_and_sanitize',
            return_value=(True, "Sanitized", "utf-8", None)
        ):
            with patch.object(
                EncodingValidator,
                'calculate_checksum',
                return_value="new_checksum"
            ):
                result = await stage.execute(context)

        assert result.checksum == "new_checksum"
        assert result.checksum != original_checksum

    @pytest.mark.asyncio
    async def test_execute_exception_handling(self, stage):
        """Test exception handling."""
        context = self._create_context()

        with patch.object(
            EncodingValidator,
            'validate_and_sanitize',
            side_effect=Exception("Encoding error")
        ):
            result = await stage.execute(context)

        assert result.validation_details.encoding_valid is False
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
    async def test_execute_multiple_calls(self, stage):
        """Test multiple executions."""
        context1 = self._create_context()
        context2 = self._create_context()

        result1 = await stage.execute(context1)
        result2 = await stage.execute(context2)

        assert result1.validation_details.encoding_valid is True
        assert result2.validation_details.encoding_valid is True

    @pytest.mark.asyncio
    async def test_execute_long_title(self, stage):
        """Test execution with long title."""
        context = self._create_context()
        context.title = "A" * 1000

        result = await stage.execute(context)

        assert result.validation_details.encoding_valid is True

    @pytest.mark.asyncio
    async def test_execute_long_body(self, stage):
        """Test execution with long body."""
        context = self._create_context()
        context.body = "A" * 10000

        result = await stage.execute(context)

        assert result.validation_details.encoding_valid is True

    @pytest.mark.asyncio
    async def test_execute_special_characters(self, stage):
        """Test execution with special characters."""
        context = self._create_context()
        context.title = "Title with special chars: !@#$%^&*()"
        context.body = "Body with special chars: <html>test</html>"

        result = await stage.execute(context)

        assert result.validation_details.encoding_valid is True

    @pytest.mark.asyncio
    async def test_execute_multilingual_text(self, stage):
        """Test execution with multilingual text."""
        context = self._create_context()
        context.title = "English العربية 中文 Русский"
        context.body = "Mixed languages: Hello مرحبا 你好 Привет"

        result = await stage.execute(context)

        assert result.validation_details.encoding_valid is True

    @pytest.mark.asyncio
    async def test_execute_checksum_includes_both_title_and_body(self, stage):
        """Test that checksum includes both title and body."""
        context = self._create_context()
        context.title = "Title"
        context.body = "Body"

        with patch.object(
            EncodingValidator,
            'validate_and_sanitize',
            return_value=(True, "Sanitized", "utf-8", None)
        ):
            with patch.object(
                EncodingValidator,
                'calculate_checksum',
                return_value="combined_checksum"
            ) as mock_calc:
                result = await stage.execute(context)

        # Verify calculate_checksum was called with combined text
        mock_calc.assert_called_once()
        call_args = mock_calc.call_args[0][0]
        assert "Sanitized" in call_args
        assert "|" in call_args

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

