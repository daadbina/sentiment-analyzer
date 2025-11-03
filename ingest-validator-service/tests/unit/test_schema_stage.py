"""Tests for schema validation stage."""

import pytest
from src.pipeline.schema_stage import SchemaValidationStage
from src.models import ValidationContext, ValidationDetails, NewsRaw


class TestSchemaValidationStage:
    """Test schema validation stage."""

    @pytest.fixture
    def stage(self):
        """Create schema validation stage."""
        return SchemaValidationStage()

    def _create_valid_raw_message(self):
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
            raw_message = self._create_valid_raw_message()

        return ValidationContext(
            article_id="art_123",
            trace_id="trace_123",
            job_id="job_123",
            raw_message=raw_message,
            validation_details=ValidationDetails(),
        )

    def test_stage_initialization(self, stage):
        """Test stage initialization."""
        assert stage.name == "SchemaValidation"

    @pytest.mark.asyncio
    async def test_execute_valid_schema(self, stage):
        """Test execution with valid schema."""
        context = self._create_context()

        result = await stage.execute(context)

        assert result.validation_details.schema_valid is True
        assert len(result.errors) == 0
        assert result.title == "Test Article"
        assert result.body == "This is a test article body with sufficient content."
        assert result.url == "https://example.com/article"
        assert result.source == "example"
        assert result.checksum == "abc123"

    @pytest.mark.asyncio
    async def test_execute_missing_article_id(self, stage):
        """Test execution with missing article_id."""
        raw_msg = self._create_valid_raw_message()
        raw_msg.article_id = None

        context = self._create_context(raw_msg)

        result = await stage.execute(context)

        assert result.validation_details.schema_valid is False
        assert len(result.errors) > 0
        assert "Missing required fields" in result.errors[0]

    @pytest.mark.asyncio
    async def test_execute_missing_title(self, stage):
        """Test execution with missing title."""
        raw_msg = self._create_valid_raw_message()
        raw_msg.title = None

        context = self._create_context(raw_msg)

        result = await stage.execute(context)

        assert result.validation_details.schema_valid is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_execute_empty_title(self, stage):
        """Test execution with empty title."""
        raw_msg = self._create_valid_raw_message()
        raw_msg.title = ""

        context = self._create_context(raw_msg)

        result = await stage.execute(context)

        assert result.validation_details.schema_valid is False
        assert "Title must be non-empty string" in result.errors[0]

    @pytest.mark.asyncio
    async def test_execute_whitespace_title(self, stage):
        """Test execution with whitespace-only title."""
        raw_msg = self._create_valid_raw_message()
        raw_msg.title = "   "

        context = self._create_context(raw_msg)

        result = await stage.execute(context)

        assert result.validation_details.schema_valid is False
        assert "Title must be non-empty string" in result.errors[0]

    @pytest.mark.asyncio
    async def test_execute_missing_body(self, stage):
        """Test execution with missing body."""
        raw_msg = self._create_valid_raw_message()
        raw_msg.body = None

        context = self._create_context(raw_msg)

        result = await stage.execute(context)

        assert result.validation_details.schema_valid is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_execute_empty_body(self, stage):
        """Test execution with empty body."""
        raw_msg = self._create_valid_raw_message()
        raw_msg.body = ""

        context = self._create_context(raw_msg)

        result = await stage.execute(context)

        assert result.validation_details.schema_valid is False
        assert "Body must be non-empty string" in result.errors[0]

    @pytest.mark.asyncio
    async def test_execute_missing_url(self, stage):
        """Test execution with missing URL."""
        raw_msg = self._create_valid_raw_message()
        raw_msg.url = None

        context = self._create_context(raw_msg)

        result = await stage.execute(context)

        assert result.validation_details.schema_valid is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_execute_empty_url(self, stage):
        """Test execution with empty URL."""
        raw_msg = self._create_valid_raw_message()
        raw_msg.url = ""

        context = self._create_context(raw_msg)

        result = await stage.execute(context)

        assert result.validation_details.schema_valid is False
        assert "URL must be non-empty string" in result.errors[0]

    @pytest.mark.asyncio
    async def test_execute_missing_source(self, stage):
        """Test execution with missing source."""
        raw_msg = self._create_valid_raw_message()
        raw_msg.source = None

        context = self._create_context(raw_msg)

        result = await stage.execute(context)

        assert result.validation_details.schema_valid is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_execute_empty_source(self, stage):
        """Test execution with empty source."""
        raw_msg = self._create_valid_raw_message()
        raw_msg.source = ""

        context = self._create_context(raw_msg)

        result = await stage.execute(context)

        assert result.validation_details.schema_valid is False
        assert "Source must be non-empty string" in result.errors[0]

    @pytest.mark.asyncio
    async def test_execute_missing_published_at(self, stage):
        """Test execution with missing published_at."""
        raw_msg = self._create_valid_raw_message()
        raw_msg.published_at = None

        context = self._create_context(raw_msg)

        result = await stage.execute(context)

        assert result.validation_details.schema_valid is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_execute_missing_language(self, stage):
        """Test execution with missing language."""
        raw_msg = self._create_valid_raw_message()
        raw_msg.language = None

        context = self._create_context(raw_msg)

        result = await stage.execute(context)

        assert result.validation_details.schema_valid is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_execute_missing_ingest_job_id(self, stage):
        """Test execution with missing ingest_job_id."""
        raw_msg = self._create_valid_raw_message()
        raw_msg.ingest_job_id = None

        context = self._create_context(raw_msg)

        result = await stage.execute(context)

        assert result.validation_details.schema_valid is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_execute_missing_validation_score(self, stage):
        """Test execution with missing validation_score."""
        raw_msg = self._create_valid_raw_message()
        raw_msg.validation_score = None

        context = self._create_context(raw_msg)

        result = await stage.execute(context)

        assert result.validation_details.schema_valid is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_execute_missing_crawled_at(self, stage):
        """Test execution with missing crawled_at."""
        raw_msg = self._create_valid_raw_message()
        raw_msg.crawled_at = None

        context = self._create_context(raw_msg)

        result = await stage.execute(context)

        assert result.validation_details.schema_valid is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_execute_missing_checksum(self, stage):
        """Test execution with missing checksum."""
        raw_msg = self._create_valid_raw_message()
        raw_msg.checksum = None

        context = self._create_context(raw_msg)

        result = await stage.execute(context)

        assert result.validation_details.schema_valid is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_execute_normalizes_whitespace(self, stage):
        """Test that whitespace is normalized."""
        raw_msg = self._create_valid_raw_message()
        raw_msg.title = "  Test Article  "
        raw_msg.body = "  Test body  "
        raw_msg.url = "  https://example.com  "
        raw_msg.source = "  example  "

        context = self._create_context(raw_msg)

        result = await stage.execute(context)

        assert result.validation_details.schema_valid is True
        assert result.title == "Test Article"
        assert result.body == "Test body"
        assert result.url == "https://example.com"
        assert result.source == "example"

    @pytest.mark.asyncio
    async def test_execute_preserves_checksum(self, stage):
        """Test that checksum is preserved."""
        raw_msg = self._create_valid_raw_message()
        raw_msg.checksum = "xyz789"

        context = self._create_context(raw_msg)

        result = await stage.execute(context)

        assert result.validation_details.schema_valid is True
        assert result.checksum == "xyz789"

    @pytest.mark.asyncio
    async def test_execute_multiple_missing_fields(self, stage):
        """Test execution with multiple missing fields."""
        raw_msg = self._create_valid_raw_message()
        raw_msg.title = None
        raw_msg.body = None
        raw_msg.url = None

        context = self._create_context(raw_msg)

        result = await stage.execute(context)

        assert result.validation_details.schema_valid is False
        assert len(result.errors) > 0
        assert "Missing required fields" in result.errors[0]

    @pytest.mark.asyncio
    async def test_execute_exception_handling(self, stage):
        """Test exception handling during schema validation."""
        raw_msg = self._create_valid_raw_message()
        context = self._create_context(raw_msg)

        # Mock raw_message to raise exception when accessing attributes
        class BadRawMessage:
            def __getattr__(self, name):
                raise RuntimeError("Attribute access error")

        context.raw_message = BadRawMessage()

        result = await stage.execute(context)

        assert result.validation_details.schema_valid is False
        assert len(result.errors) > 0
        assert "error" in result.errors[0].lower()

