"""Tests for geographic extraction stage."""

import pytest
from unittest.mock import patch, MagicMock
from src.pipeline.geographic_stage import GeographicExtractionStage
from src.models import ValidationContext, ValidationDetails, NewsRaw
from src.validation.geographic import GeographicExtractor


class TestGeographicExtractionStage:
    """Test geographic extraction stage."""

    @pytest.fixture
    def stage(self):
        """Create geographic extraction stage."""
        return GeographicExtractionStage()

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
        return context

    def test_stage_initialization(self, stage):
        """Test stage initialization."""
        assert stage.name == "GeographicExtraction"

    @pytest.mark.asyncio
    async def test_execute_extracts_country(self, stage):
        """Test execution extracts country."""
        context = self._create_context()

        with patch.object(
            GeographicExtractor,
            'extract_country',
            return_value="United States"
        ):
            result = await stage.execute(context)

        assert result.country == "United States"

    @pytest.mark.asyncio
    async def test_execute_no_country_extracted(self, stage):
        """Test execution when no country is extracted."""
        context = self._create_context()
        context.country = None

        with patch.object(
            GeographicExtractor,
            'extract_country',
            return_value=None
        ):
            result = await stage.execute(context)

        assert result.country is None

    @pytest.mark.asyncio
    async def test_execute_preserves_existing_country(self, stage):
        """Test that existing country is passed to extractor."""
        context = self._create_context()
        context.country = "France"

        with patch.object(
            GeographicExtractor,
            'extract_country',
            return_value="France"
        ) as mock_extract:
            result = await stage.execute(context)

        # Verify existing_country parameter
        mock_extract.assert_called_once()
        call_kwargs = mock_extract.call_args[1]
        assert call_kwargs.get("existing_country") == "France"

    @pytest.mark.asyncio
    async def test_execute_passes_correct_parameters(self, stage):
        """Test that correct parameters are passed to extractor."""
        context = self._create_context()
        context.title = "Article about France"
        context.body = "This article discusses France"
        context.url = "https://example.com/france"
        context.country = None

        with patch.object(
            GeographicExtractor,
            'extract_country',
            return_value="France"
        ) as mock_extract:
            result = await stage.execute(context)

        mock_extract.assert_called_once_with(
            title="Article about France",
            body="This article discusses France",
            url="https://example.com/france",
            existing_country=None
        )

    @pytest.mark.asyncio
    async def test_execute_empty_title(self, stage):
        """Test execution with empty title."""
        context = self._create_context()
        context.title = ""

        with patch.object(
            GeographicExtractor,
            'extract_country',
            return_value=None
        ) as mock_extract:
            result = await stage.execute(context)

        # Verify empty string is passed
        mock_extract.assert_called_once()
        call_kwargs = mock_extract.call_args[1]
        assert call_kwargs.get("title") == ""

    @pytest.mark.asyncio
    async def test_execute_empty_body(self, stage):
        """Test execution with empty body."""
        context = self._create_context()
        context.body = ""

        with patch.object(
            GeographicExtractor,
            'extract_country',
            return_value=None
        ) as mock_extract:
            result = await stage.execute(context)

        # Verify empty string is passed
        mock_extract.assert_called_once()
        call_kwargs = mock_extract.call_args[1]
        assert call_kwargs.get("body") == ""

    @pytest.mark.asyncio
    async def test_execute_empty_url(self, stage):
        """Test execution with empty URL."""
        context = self._create_context()
        context.url = ""

        with patch.object(
            GeographicExtractor,
            'extract_country',
            return_value=None
        ) as mock_extract:
            result = await stage.execute(context)

        # Verify empty string is passed
        mock_extract.assert_called_once()
        call_kwargs = mock_extract.call_args[1]
        assert call_kwargs.get("url") == ""

    @pytest.mark.asyncio
    async def test_execute_none_title(self, stage):
        """Test execution with None title."""
        context = self._create_context()
        context.title = None

        with patch.object(
            GeographicExtractor,
            'extract_country',
            return_value=None
        ) as mock_extract:
            result = await stage.execute(context)

        # Verify empty string is passed for None
        mock_extract.assert_called_once()
        call_kwargs = mock_extract.call_args[1]
        assert call_kwargs.get("title") == ""

    @pytest.mark.asyncio
    async def test_execute_none_body(self, stage):
        """Test execution with None body."""
        context = self._create_context()
        context.body = None

        with patch.object(
            GeographicExtractor,
            'extract_country',
            return_value=None
        ) as mock_extract:
            result = await stage.execute(context)

        # Verify empty string is passed for None
        mock_extract.assert_called_once()
        call_kwargs = mock_extract.call_args[1]
        assert call_kwargs.get("body") == ""

    @pytest.mark.asyncio
    async def test_execute_none_url(self, stage):
        """Test execution with None URL."""
        context = self._create_context()
        context.url = None

        with patch.object(
            GeographicExtractor,
            'extract_country',
            return_value=None
        ) as mock_extract:
            result = await stage.execute(context)

        # Verify empty string is passed for None
        mock_extract.assert_called_once()
        call_kwargs = mock_extract.call_args[1]
        assert call_kwargs.get("url") == ""

    @pytest.mark.asyncio
    async def test_execute_exception_handling(self, stage):
        """Test exception handling."""
        context = self._create_context()

        with patch.object(
            GeographicExtractor,
            'extract_country',
            side_effect=Exception("Extraction error")
        ):
            result = await stage.execute(context)

        # Geographic extraction is not critical, so no error is added
        assert len(result.errors) == 0

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

        with patch.object(
            GeographicExtractor,
            'extract_country',
            return_value="United States"
        ):
            result1 = await stage.execute(context1)
            result2 = await stage.execute(context2)

        assert result1.country == "United States"
        assert result2.country == "United States"

    @pytest.mark.asyncio
    async def test_execute_different_countries(self, stage):
        """Test extraction of different countries."""
        countries = ["United States", "France", "Germany", "Japan", "Brazil"]

        for country in countries:
            context = self._create_context()

            with patch.object(
                GeographicExtractor,
                'extract_country',
                return_value=country
            ):
                result = await stage.execute(context)

            assert result.country == country

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
    async def test_execute_updates_country_when_extracted(self, stage):
        """Test that country is updated when extracted."""
        context = self._create_context()
        context.country = None

        with patch.object(
            GeographicExtractor,
            'extract_country',
            return_value="Canada"
        ):
            result = await stage.execute(context)

        assert result.country == "Canada"

    @pytest.mark.asyncio
    async def test_execute_returns_context(self, stage):
        """Test that context is returned."""
        context = self._create_context()

        result = await stage.execute(context)

        assert result is not None
        assert isinstance(result, ValidationContext)

    @pytest.mark.asyncio
    async def test_execute_long_title(self, stage):
        """Test execution with long title."""
        context = self._create_context()
        context.title = "A" * 1000

        with patch.object(
            GeographicExtractor,
            'extract_country',
            return_value=None
        ):
            result = await stage.execute(context)

        assert result is not None

    @pytest.mark.asyncio
    async def test_execute_long_body(self, stage):
        """Test execution with long body."""
        context = self._create_context()
        context.body = "A" * 10000

        with patch.object(
            GeographicExtractor,
            'extract_country',
            return_value=None
        ):
            result = await stage.execute(context)

        assert result is not None

