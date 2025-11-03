"""Tests for source verification stage."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.pipeline.source_stage import SourceVerificationStage
from src.models import ValidationContext, ValidationDetails, NewsRaw
from src.repositories.source_registry import SourceRegistryRepository


class TestSourceVerificationStage:
    """Test source verification stage."""

    @pytest.fixture
    def mock_source_registry(self):
        """Create mock source registry."""
        return AsyncMock(spec=SourceRegistryRepository)

    @pytest.fixture
    def stage(self, mock_source_registry):
        """Create source verification stage."""
        return SourceVerificationStage(mock_source_registry)

    def _create_raw_message(self, source="example"):
        """Create a valid NewsRaw message."""
        return NewsRaw(
            article_id="art_123",
            canonical_url="https://example.com/article",
            title="Test Article",
            body="This is a test article body with sufficient content.",
            url="https://example.com/article",
            published_at="2025-11-03T10:00:00Z",
            language="en",
            source=source,
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

        return ValidationContext(
            article_id="art_123",
            trace_id="trace_123",
            job_id="job_123",
            raw_message=raw_message,
            validation_details=ValidationDetails(),
        )

    def test_stage_initialization(self, stage, mock_source_registry):
        """Test stage initialization."""
        assert stage.name == "SourceVerification"
        assert stage.source_registry == mock_source_registry

    @pytest.mark.asyncio
    async def test_execute_verified_source(self, stage, mock_source_registry):
        """Test execution with verified source."""
        mock_source_registry.verify_source = AsyncMock(return_value=True)
        mock_source_registry.get_publisher_id = AsyncMock(return_value="pub_123")

        context = self._create_context()

        result = await stage.execute(context)

        assert result.validation_details.source_verified is True
        assert result.publisher_id == "pub_123"
        assert len(result.warnings) == 0
        mock_source_registry.verify_source.assert_called_once_with("example")
        mock_source_registry.get_publisher_id.assert_called_once_with("example")

    @pytest.mark.asyncio
    async def test_execute_unverified_source(self, stage, mock_source_registry):
        """Test execution with unverified source."""
        mock_source_registry.verify_source = AsyncMock(return_value=False)

        context = self._create_context()

        result = await stage.execute(context)

        assert result.validation_details.source_verified is False
        assert len(result.warnings) > 0
        assert "not verified" in result.warnings[0]
        mock_source_registry.verify_source.assert_called_once_with("example")

    @pytest.mark.asyncio
    async def test_execute_different_sources(self, stage, mock_source_registry):
        """Test execution with different sources."""
        mock_source_registry.verify_source = AsyncMock(return_value=True)
        mock_source_registry.get_publisher_id = AsyncMock(return_value="pub_456")

        raw_msg = self._create_raw_message(source="bbc")
        context = self._create_context(raw_msg)

        result = await stage.execute(context)

        assert result.validation_details.source_verified is True
        mock_source_registry.verify_source.assert_called_once_with("bbc")

    @pytest.mark.asyncio
    async def test_execute_publisher_id_assignment(self, stage, mock_source_registry):
        """Test that publisher ID is correctly assigned."""
        mock_source_registry.verify_source = AsyncMock(return_value=True)
        mock_source_registry.get_publisher_id = AsyncMock(return_value="pub_789")

        context = self._create_context()

        result = await stage.execute(context)

        assert result.publisher_id == "pub_789"

    @pytest.mark.asyncio
    async def test_execute_exception_handling(self, stage, mock_source_registry):
        """Test exception handling."""
        mock_source_registry.verify_source = AsyncMock(
            side_effect=Exception("Registry error")
        )

        context = self._create_context()

        result = await stage.execute(context)

        assert result.validation_details.source_verified is False
        assert len(result.warnings) > 0
        assert "error" in result.warnings[0].lower()

    @pytest.mark.asyncio
    async def test_execute_preserves_context(self, stage, mock_source_registry):
        """Test that context is preserved."""
        mock_source_registry.verify_source = AsyncMock(return_value=True)
        mock_source_registry.get_publisher_id = AsyncMock(return_value="pub_123")

        context = self._create_context()
        context.title = "Original Title"
        context.body = "Original Body"

        result = await stage.execute(context)

        assert result.title == "Original Title"
        assert result.body == "Original Body"

    @pytest.mark.asyncio
    async def test_execute_multiple_calls(self, stage, mock_source_registry):
        """Test multiple executions."""
        mock_source_registry.verify_source = AsyncMock(return_value=True)
        mock_source_registry.get_publisher_id = AsyncMock(return_value="pub_123")

        context1 = self._create_context()
        context2 = self._create_context()

        result1 = await stage.execute(context1)
        result2 = await stage.execute(context2)

        assert result1.validation_details.source_verified is True
        assert result2.validation_details.source_verified is True
        assert mock_source_registry.verify_source.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_source_from_raw_message(self, stage, mock_source_registry):
        """Test that source is extracted from raw message."""
        mock_source_registry.verify_source = AsyncMock(return_value=True)
        mock_source_registry.get_publisher_id = AsyncMock(return_value="pub_123")

        raw_msg = self._create_raw_message(source="reuters")
        context = self._create_context(raw_msg)

        result = await stage.execute(context)

        mock_source_registry.verify_source.assert_called_once_with("reuters")

    @pytest.mark.asyncio
    async def test_execute_warning_added_on_unverified(self, stage, mock_source_registry):
        """Test that warning is added when source is unverified."""
        mock_source_registry.verify_source = AsyncMock(return_value=False)

        context = self._create_context()
        initial_warnings = len(context.warnings)

        result = await stage.execute(context)

        assert len(result.warnings) > initial_warnings

    @pytest.mark.asyncio
    async def test_execute_no_warning_on_verified(self, stage, mock_source_registry):
        """Test that no warning is added when source is verified."""
        mock_source_registry.verify_source = AsyncMock(return_value=True)
        mock_source_registry.get_publisher_id = AsyncMock(return_value="pub_123")

        context = self._create_context()
        initial_warnings = len(context.warnings)

        result = await stage.execute(context)

        assert len(result.warnings) == initial_warnings

    @pytest.mark.asyncio
    async def test_execute_publisher_id_none(self, stage, mock_source_registry):
        """Test when publisher ID is None."""
        mock_source_registry.verify_source = AsyncMock(return_value=True)
        mock_source_registry.get_publisher_id = AsyncMock(return_value=None)

        context = self._create_context()

        result = await stage.execute(context)

        assert result.validation_details.source_verified is True
        assert result.publisher_id is None

    @pytest.mark.asyncio
    async def test_execute_get_publisher_id_exception(self, stage, mock_source_registry):
        """Test exception when getting publisher ID."""
        mock_source_registry.verify_source = AsyncMock(return_value=True)
        mock_source_registry.get_publisher_id = AsyncMock(
            side_effect=Exception("Publisher lookup failed")
        )

        context = self._create_context()

        result = await stage.execute(context)

        assert result.validation_details.source_verified is False
        assert len(result.warnings) > 0

    @pytest.mark.asyncio
    async def test_execute_context_article_id_preserved(self, stage, mock_source_registry):
        """Test that article ID is preserved."""
        mock_source_registry.verify_source = AsyncMock(return_value=True)
        mock_source_registry.get_publisher_id = AsyncMock(return_value="pub_123")

        context = self._create_context()
        original_article_id = context.article_id

        result = await stage.execute(context)

        assert result.article_id == original_article_id

    @pytest.mark.asyncio
    async def test_execute_context_trace_id_preserved(self, stage, mock_source_registry):
        """Test that trace ID is preserved."""
        mock_source_registry.verify_source = AsyncMock(return_value=True)
        mock_source_registry.get_publisher_id = AsyncMock(return_value="pub_123")

        context = self._create_context()
        original_trace_id = context.trace_id

        result = await stage.execute(context)

        assert result.trace_id == original_trace_id

    @pytest.mark.asyncio
    async def test_execute_context_job_id_preserved(self, stage, mock_source_registry):
        """Test that job ID is preserved."""
        mock_source_registry.verify_source = AsyncMock(return_value=True)
        mock_source_registry.get_publisher_id = AsyncMock(return_value="pub_123")

        context = self._create_context()
        original_job_id = context.job_id

        result = await stage.execute(context)

        assert result.job_id == original_job_id

