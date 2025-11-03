"""Tests for validation pipeline orchestrator."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.pipeline.orchestrator import ValidationPipeline
from src.models import ValidationContext, ValidationResult, ValidationDetails, NewsRaw
from src.pipeline.stage import ValidationStage


class TestValidationPipeline:
    """Test validation pipeline orchestrator."""

    def _create_raw_message(self, article_id="art_123"):
        """Helper to create NewsRaw message."""
        return NewsRaw(
            article_id=article_id,
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

    @pytest.fixture
    def validation_details(self):
        """Create validation details."""
        return ValidationDetails(
            schema_valid=True,
            encoding_valid=True,
            timestamp_valid=True,
            source_valid=True,
            language_valid=True,
            duplicate_valid=True,
            quality_valid=True,
            geographic_valid=True,
        )

    @pytest.fixture
    def validation_context(self, validation_details):
        """Create validation context."""
        raw_message = NewsRaw(
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
        return ValidationContext(
            article_id="art_123",
            trace_id="trace_123",
            job_id="job_123",
            raw_message=raw_message,
            title="Test Article",
            body="This is a test article body with sufficient content.",
            url="https://example.com/article",
            source="example",
            language="en",
            validation_score=0.9,
            validation_details=validation_details,
            errors=[],
            warnings=[],
        )

    def test_initialization(self):
        """Test pipeline initialization."""
        stages = []
        pipeline = ValidationPipeline(stages)

        assert pipeline.stages == []

    def test_initialization_with_stages(self):
        """Test pipeline initialization with stages."""
        mock_stage1 = MagicMock(spec=ValidationStage)
        mock_stage2 = MagicMock(spec=ValidationStage)
        stages = [mock_stage1, mock_stage2]

        pipeline = ValidationPipeline(stages)

        assert len(pipeline.stages) == 2
        assert pipeline.stages[0] == mock_stage1
        assert pipeline.stages[1] == mock_stage2

    @pytest.mark.asyncio
    async def test_execute_success(self, validation_context):
        """Test successful pipeline execution."""
        mock_stage = AsyncMock(spec=ValidationStage)
        mock_stage.name = "TestStage"
        mock_stage.execute = AsyncMock(return_value=validation_context)

        pipeline = ValidationPipeline([mock_stage])

        result = await pipeline.execute(validation_context)

        assert result.article_id == "art_123"
        assert result.is_valid is True
        assert result.validation_score == 0.9
        mock_stage.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_multiple_stages(self, validation_context):
        """Test pipeline execution with multiple stages."""
        mock_stage1 = AsyncMock(spec=ValidationStage)
        mock_stage1.name = "Stage1"
        mock_stage1.execute = AsyncMock(return_value=validation_context)

        mock_stage2 = AsyncMock(spec=ValidationStage)
        mock_stage2.name = "Stage2"
        mock_stage2.execute = AsyncMock(return_value=validation_context)

        pipeline = ValidationPipeline([mock_stage1, mock_stage2])

        result = await pipeline.execute(validation_context)

        assert result.article_id == "art_123"
        mock_stage1.execute.assert_called_once()
        mock_stage2.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_early_exit_schema_invalid(self, validation_context):
        """Test early exit when schema validation fails."""
        invalid_context = ValidationContext(
            article_id="art_123",
            trace_id="trace_123",
            job_id="job_123",
            raw_message=self._create_raw_message(),
            title="Test",
            body="Test body",
            url="https://example.com",
            source="example",
            language="en",
            validation_score=0.0,
            validation_details=ValidationDetails(
                schema_valid=False,
                encoding_valid=True,
                timestamp_valid=True,
                source_verified=True,
                language_detected=True,
                not_duplicate=True,
                content_quality_ok=True,
            ),
            errors=["Schema invalid"],
            warnings=[],
        )

        mock_stage1 = AsyncMock(spec=ValidationStage)
        mock_stage1.name = "SchemaValidation"
        mock_stage1.execute = AsyncMock(return_value=invalid_context)

        mock_stage2 = AsyncMock(spec=ValidationStage)
        mock_stage2.name = "Stage2"
        mock_stage2.execute = AsyncMock(return_value=invalid_context)

        pipeline = ValidationPipeline([mock_stage1, mock_stage2])

        result = await pipeline.execute(validation_context)

        assert result.is_valid is False
        mock_stage1.execute.assert_called_once()
        # Stage 2 should not be called due to early exit
        mock_stage2.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_early_exit_encoding_invalid(self, validation_context):
        """Test early exit when encoding validation fails."""
        invalid_context = ValidationContext(
            article_id="art_123",
            trace_id="trace_123",
            job_id="job_123",
            raw_message=self._create_raw_message(),
            title="Test",
            body="Test body",
            url="https://example.com",
            source="example",
            language="en",
            validation_score=0.0,
            validation_details=ValidationDetails(
                schema_valid=True,
                encoding_valid=False,
                timestamp_valid=True,
                source_verified=True,
                language_detected=True,
                not_duplicate=True,
                content_quality_ok=True,
            ),
            errors=["Encoding invalid"],
            warnings=[],
        )

        mock_stage1 = AsyncMock(spec=ValidationStage)
        mock_stage1.name = "EncodingValidation"
        mock_stage1.execute = AsyncMock(return_value=invalid_context)

        mock_stage2 = AsyncMock(spec=ValidationStage)
        mock_stage2.name = "Stage2"
        mock_stage2.execute = AsyncMock(return_value=invalid_context)

        pipeline = ValidationPipeline([mock_stage1, mock_stage2])

        result = await pipeline.execute(validation_context)

        assert result.is_valid is False
        mock_stage1.execute.assert_called_once()
        mock_stage2.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_early_exit_timestamp_invalid(self, validation_context):
        """Test early exit when timestamp validation fails."""
        invalid_context = ValidationContext(
            article_id="art_123",
            trace_id="trace_123",
            job_id="job_123",
            raw_message=self._create_raw_message(),
            title="Test",
            body="Test body",
            url="https://example.com",
            source="example",
            language="en",
            validation_score=0.0,
            validation_details=ValidationDetails(
                schema_valid=True,
                encoding_valid=True,
                timestamp_valid=False,
                source_verified=True,
                language_detected=True,
                not_duplicate=True,
                content_quality_ok=True,
            ),
            errors=["Timestamp invalid"],
            warnings=[],
        )

        mock_stage1 = AsyncMock(spec=ValidationStage)
        mock_stage1.name = "TimestampValidation"
        mock_stage1.execute = AsyncMock(return_value=invalid_context)

        mock_stage2 = AsyncMock(spec=ValidationStage)
        mock_stage2.name = "Stage2"
        mock_stage2.execute = AsyncMock(return_value=invalid_context)

        pipeline = ValidationPipeline([mock_stage1, mock_stage2])

        result = await pipeline.execute(validation_context)

        assert result.is_valid is False
        mock_stage1.execute.assert_called_once()
        mock_stage2.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_exception_handling(self, validation_context):
        """Test exception handling in pipeline."""
        mock_stage = AsyncMock(spec=ValidationStage)
        mock_stage.name = "FailingStage"
        mock_stage.execute = AsyncMock(side_effect=Exception("Stage error"))

        pipeline = ValidationPipeline([mock_stage])

        result = await pipeline.execute(validation_context)

        assert result.is_valid is False
        assert result.validation_score == 0.0
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_execute_low_score_routing(self, validation_context):
        """Test routing with low validation score."""
        low_score_context = ValidationContext(
            article_id="art_123",
            trace_id="trace_123",
            job_id="job_123",
            raw_message=self._create_raw_message(),
            title="Test",
            body="Test body",
            url="https://example.com",
            source="example",
            language="en",
            validation_score=0.6,  # Below 0.70 threshold
            validation_details=ValidationDetails(
                schema_valid=True,
                encoding_valid=True,
                timestamp_valid=True,
                source_verified=True,
                language_detected=True,
                not_duplicate=True,
                content_quality_ok=True,
            ),
            errors=[],
            warnings=[],
        )

        mock_stage = AsyncMock(spec=ValidationStage)
        mock_stage.name = "TestStage"
        mock_stage.execute = AsyncMock(return_value=low_score_context)

        pipeline = ValidationPipeline([mock_stage])

        result = await pipeline.execute(low_score_context)

        assert result.is_valid is False

    @pytest.mark.asyncio
    async def test_execute_medium_score_routing(self, validation_context):
        """Test routing with medium validation score."""
        medium_score_context = ValidationContext(
            article_id="art_123",
            trace_id="trace_123",
            job_id="job_123",
            raw_message=self._create_raw_message(),
            title="Test",
            body="Test body",
            url="https://example.com",
            source="example",
            language="en",
            validation_score=0.75,  # Between 0.70 and 0.85
            validation_details=ValidationDetails(
                schema_valid=True,
                encoding_valid=True,
                timestamp_valid=True,
                source_verified=True,
                language_detected=True,
                not_duplicate=True,
                content_quality_ok=True,
            ),
            errors=[],
            warnings=[],
        )

        mock_stage = AsyncMock(spec=ValidationStage)
        mock_stage.name = "TestStage"
        mock_stage.execute = AsyncMock(return_value=medium_score_context)

        pipeline = ValidationPipeline([mock_stage])

        result = await pipeline.execute(medium_score_context)

        # Medium score should be rejected (< 0.85)
        assert result.is_valid is False

    @pytest.mark.asyncio
    async def test_execute_high_score_routing(self, validation_context):
        """Test routing with high validation score."""
        high_score_context = ValidationContext(
            article_id="art_123",
            trace_id="trace_123",
            job_id="job_123",
            raw_message=self._create_raw_message(),
            title="Test",
            body="Test body",
            url="https://example.com",
            source="example",
            language="en",
            validation_score=0.9,  # Above 0.85 threshold
            validation_details=ValidationDetails(
                schema_valid=True,
                encoding_valid=True,
                timestamp_valid=True,
                source_verified=True,
                language_detected=True,
                not_duplicate=True,
                content_quality_ok=True,
            ),
            errors=[],
            warnings=[],
        )

        mock_stage = AsyncMock(spec=ValidationStage)
        mock_stage.name = "TestStage"
        mock_stage.execute = AsyncMock(return_value=high_score_context)

        pipeline = ValidationPipeline([mock_stage])

        result = await pipeline.execute(high_score_context)

        assert result.is_valid is True

    def test_should_exit_early_schema_invalid(self, validation_context):
        """Test early exit check for schema validation."""
        pipeline = ValidationPipeline([])

        validation_context.validation_details.schema_valid = False

        assert pipeline._should_exit_early(validation_context) is True

    def test_should_exit_early_encoding_invalid(self, validation_context):
        """Test early exit check for encoding validation."""
        pipeline = ValidationPipeline([])

        validation_context.validation_details.encoding_valid = False

        assert pipeline._should_exit_early(validation_context) is True

    def test_should_exit_early_timestamp_invalid(self, validation_context):
        """Test early exit check for timestamp validation."""
        pipeline = ValidationPipeline([])

        validation_context.validation_details.timestamp_valid = False

        assert pipeline._should_exit_early(validation_context) is True

    def test_should_exit_early_all_valid(self, validation_context):
        """Test early exit check when all validations pass."""
        pipeline = ValidationPipeline([])

        assert pipeline._should_exit_early(validation_context) is False

    @pytest.mark.asyncio
    async def test_execute_preserves_warnings(self, validation_context):
        """Test that warnings are preserved through pipeline."""
        context_with_warnings = ValidationContext(
            article_id="art_123",
            trace_id="trace_123",
            job_id="job_123",
            raw_message=self._create_raw_message(),
            title="Test",
            body="Test body",
            url="https://example.com",
            source="example",
            language="en",
            validation_score=0.9,
            validation_details=ValidationDetails(
                schema_valid=True,
                encoding_valid=True,
                timestamp_valid=True,
                source_verified=True,
                language_detected=True,
                not_duplicate=True,
                content_quality_ok=True,
            ),
            errors=[],
            warnings=["R1_FUTURE_DATE"],
        )

        mock_stage = AsyncMock(spec=ValidationStage)
        mock_stage.name = "TestStage"
        mock_stage.execute = AsyncMock(return_value=context_with_warnings)

        pipeline = ValidationPipeline([mock_stage])

        result = await pipeline.execute(validation_context)

        assert result.warnings == ["R1_FUTURE_DATE"]

