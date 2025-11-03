"""Tests for base validation stage."""

import pytest
from src.pipeline.stage import ValidationStage
from src.models import ValidationContext, ValidationDetails, NewsRaw


class ConcreteValidationStage(ValidationStage):
    """Concrete implementation of ValidationStage for testing."""

    async def execute(self, context: ValidationContext) -> ValidationContext:
        """Execute validation stage."""
        return context


class TestValidationStageBase:
    """Test base validation stage."""

    @pytest.fixture
    def stage(self):
        """Create concrete validation stage."""
        return ConcreteValidationStage("TestStage")

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

        return ValidationContext(
            article_id="art_123",
            trace_id="trace_123",
            job_id="job_123",
            raw_message=raw_message,
            validation_details=ValidationDetails(),
        )

    def test_stage_initialization(self, stage):
        """Test stage initialization."""
        assert stage.name == "TestStage"

    def test_add_error(self, stage):
        """Test adding error to context."""
        context = self._create_context()
        error_msg = "Test error"

        stage._add_error(context, error_msg)

        assert error_msg in context.errors
        assert len(context.errors) == 1

    def test_add_error_duplicate_prevention(self, stage):
        """Test that duplicate errors are not added."""
        context = self._create_context()
        error_msg = "Test error"

        stage._add_error(context, error_msg)
        stage._add_error(context, error_msg)

        assert len(context.errors) == 1

    def test_add_error_multiple_different(self, stage):
        """Test adding multiple different errors."""
        context = self._create_context()
        error1 = "Error 1"
        error2 = "Error 2"

        stage._add_error(context, error1)
        stage._add_error(context, error2)

        assert error1 in context.errors
        assert error2 in context.errors
        assert len(context.errors) == 2

    def test_add_warning(self, stage):
        """Test adding warning to context."""
        context = self._create_context()
        warning_msg = "Test warning"

        stage._add_warning(context, warning_msg)

        assert warning_msg in context.warnings
        assert len(context.warnings) == 1

    def test_add_warning_duplicate_prevention(self, stage):
        """Test that duplicate warnings are not added."""
        context = self._create_context()
        warning_msg = "Test warning"

        stage._add_warning(context, warning_msg)
        stage._add_warning(context, warning_msg)

        assert len(context.warnings) == 1

    def test_add_warning_multiple_different(self, stage):
        """Test adding multiple different warnings."""
        context = self._create_context()
        warning1 = "Warning 1"
        warning2 = "Warning 2"

        stage._add_warning(context, warning1)
        stage._add_warning(context, warning2)

        assert warning1 in context.warnings
        assert warning2 in context.warnings
        assert len(context.warnings) == 2

    def test_add_error_and_warning_together(self, stage):
        """Test adding both errors and warnings."""
        context = self._create_context()
        error_msg = "Test error"
        warning_msg = "Test warning"

        stage._add_error(context, error_msg)
        stage._add_warning(context, warning_msg)

        assert error_msg in context.errors
        assert warning_msg in context.warnings
        assert len(context.errors) == 1
        assert len(context.warnings) == 1

    @pytest.mark.asyncio
    async def test_execute_returns_context(self, stage):
        """Test that execute returns context."""
        context = self._create_context()

        result = await stage.execute(context)

        assert result is context

    def test_stage_name_property(self, stage):
        """Test stage name property."""
        assert stage.name == "TestStage"

    def test_stage_name_different_values(self):
        """Test stage with different names."""
        stage1 = ConcreteValidationStage("Stage1")
        stage2 = ConcreteValidationStage("Stage2")

        assert stage1.name == "Stage1"
        assert stage2.name == "Stage2"

    def test_add_error_empty_string(self, stage):
        """Test adding empty string error."""
        context = self._create_context()
        error_msg = ""

        stage._add_error(context, error_msg)

        assert error_msg in context.errors

    def test_add_warning_empty_string(self, stage):
        """Test adding empty string warning."""
        context = self._create_context()
        warning_msg = ""

        stage._add_warning(context, warning_msg)

        assert warning_msg in context.warnings

    def test_add_error_long_message(self, stage):
        """Test adding long error message."""
        context = self._create_context()
        error_msg = "A" * 1000

        stage._add_error(context, error_msg)

        assert error_msg in context.errors

    def test_add_warning_long_message(self, stage):
        """Test adding long warning message."""
        context = self._create_context()
        warning_msg = "A" * 1000

        stage._add_warning(context, warning_msg)

        assert warning_msg in context.warnings

    def test_add_error_special_characters(self, stage):
        """Test adding error with special characters."""
        context = self._create_context()
        error_msg = "Error: !@#$%^&*()_+-=[]{}|;:',.<>?/~`"

        stage._add_error(context, error_msg)

        assert error_msg in context.errors

    def test_add_warning_special_characters(self, stage):
        """Test adding warning with special characters."""
        context = self._create_context()
        warning_msg = "Warning: !@#$%^&*()_+-=[]{}|;:',.<>?/~`"

        stage._add_warning(context, warning_msg)

        assert warning_msg in context.warnings

    def test_add_error_unicode(self, stage):
        """Test adding error with unicode characters."""
        context = self._create_context()
        error_msg = "Error: 你好世界 مرحبا العالم"

        stage._add_error(context, error_msg)

        assert error_msg in context.errors

    def test_add_warning_unicode(self, stage):
        """Test adding warning with unicode characters."""
        context = self._create_context()
        warning_msg = "Warning: 你好世界 مرحبا العالم"

        stage._add_warning(context, warning_msg)

        assert warning_msg in context.warnings

    def test_add_error_preserves_order(self, stage):
        """Test that errors are added in order."""
        context = self._create_context()
        errors = ["Error 1", "Error 2", "Error 3"]

        for error in errors:
            stage._add_error(context, error)

        assert context.errors == errors

    def test_add_warning_preserves_order(self, stage):
        """Test that warnings are added in order."""
        context = self._create_context()
        warnings = ["Warning 1", "Warning 2", "Warning 3"]

        for warning in warnings:
            stage._add_warning(context, warning)

        assert context.warnings == warnings

    def test_add_error_case_sensitive(self, stage):
        """Test that error deduplication is case sensitive."""
        context = self._create_context()
        error1 = "Error"
        error2 = "error"

        stage._add_error(context, error1)
        stage._add_error(context, error2)

        assert len(context.errors) == 2

    def test_add_warning_case_sensitive(self, stage):
        """Test that warning deduplication is case sensitive."""
        context = self._create_context()
        warning1 = "Warning"
        warning2 = "warning"

        stage._add_warning(context, warning1)
        stage._add_warning(context, warning2)

        assert len(context.warnings) == 2

    def test_add_error_whitespace_sensitive(self, stage):
        """Test that error deduplication is whitespace sensitive."""
        context = self._create_context()
        error1 = "Error message"
        error2 = "Error  message"

        stage._add_error(context, error1)
        stage._add_error(context, error2)

        assert len(context.errors) == 2

    def test_add_warning_whitespace_sensitive(self, stage):
        """Test that warning deduplication is whitespace sensitive."""
        context = self._create_context()
        warning1 = "Warning message"
        warning2 = "Warning  message"

        stage._add_warning(context, warning1)
        stage._add_warning(context, warning2)

        assert len(context.warnings) == 2

