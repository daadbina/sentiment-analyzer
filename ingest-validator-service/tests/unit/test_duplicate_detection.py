"""Tests for duplicate detection accuracy."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.pipeline.duplicate_stage import DuplicateDetectionStage
from src.models import ValidationContext, NewsRaw, ValidationDetails
from src.clients.dedup_grpc_client import DedupGrpcClient
from src.cache.redis_manager import RedisCacheManager


class TestDuplicateDetectionAccuracy:
    """Test duplicate detection accuracy and performance."""

    def setup_method(self):
        """Setup test fixtures."""
        self.mock_dedup_client = AsyncMock(spec=DedupGrpcClient)
        self.mock_cache_manager = Mock(spec=RedisCacheManager)
        self.stage = DuplicateDetectionStage(
            self.mock_dedup_client,
            self.mock_cache_manager,
        )

    def _create_context(self, article_id: str, checksum: str) -> ValidationContext:
        """Create a validation context for testing."""
        return ValidationContext(
            article_id=article_id,
            trace_id="trace_123",
            job_id="job_123",
            raw_message=NewsRaw(
                article_id=article_id,
                canonical_url="https://example.com",
                title="Test Article",
                body="Test body content",
                url="https://example.com",
                published_at="2025-11-02T10:00:00Z",
                language="en",
                source="test_source",
                crawled_at="2025-11-02T11:00:00Z",
                checksum=checksum,
                validation_score=0.8,
                schema_version="1.0.0",
                ingest_job_id="job_123",
                publisher_id="pub_123",
                extraction_method="rss",
            ),
            checksum=checksum,
        )

    @pytest.mark.asyncio
    async def test_no_duplicate_new_article(self):
        """Test that new articles are not marked as duplicates."""
        context = self._create_context("art_1", "checksum_1")
        
        # Mock: not in cache, not in dedup service
        self.mock_cache_manager.exists.return_value = False
        self.mock_dedup_client.check_duplicate.return_value = False
        self.mock_dedup_client.register_article.return_value = None
        self.mock_cache_manager.set.return_value = None
        self.mock_cache_manager.get_checksum_cache_key.return_value = "cache_key_1"

        result = await self.stage.execute(context)

        assert result.validation_details.not_duplicate is True
        assert len(result.errors) == 0
        self.mock_dedup_client.check_duplicate.assert_called_once()
        self.mock_dedup_client.register_article.assert_called_once()

    @pytest.mark.asyncio
    async def test_duplicate_detected_from_cache(self):
        """Test that duplicates are detected from cache."""
        context = self._create_context("art_2", "checksum_2")
        
        # Mock: found in cache
        self.mock_cache_manager.exists.return_value = True
        self.mock_cache_manager.get_checksum_cache_key.return_value = "cache_key_2"

        result = await self.stage.execute(context)

        assert result.validation_details.not_duplicate is False
        assert len(result.errors) > 0
        assert "Duplicate detected (cached)" in result.errors[0]

    @pytest.mark.asyncio
    async def test_duplicate_detected_from_service(self):
        """Test that duplicates are detected from dedup service."""
        context = self._create_context("art_3", "checksum_3")
        
        # Mock: not in cache, but found in dedup service
        self.mock_cache_manager.exists.return_value = False
        self.mock_dedup_client.check_duplicate.return_value = True
        self.mock_cache_manager.get_checksum_cache_key.return_value = "cache_key_3"

        result = await self.stage.execute(context)

        assert result.validation_details.not_duplicate is False
        assert len(result.errors) > 0
        assert "Duplicate detected:" in result.errors[0]

    @pytest.mark.asyncio
    async def test_no_checksum_skips_detection(self):
        """Test that articles without checksum skip duplicate detection."""
        context = self._create_context("art_4", "")
        context.checksum = None

        result = await self.stage.execute(context)

        assert result.validation_details.not_duplicate is True
        assert len(result.errors) == 0
        self.mock_dedup_client.check_duplicate.assert_not_called()

    @pytest.mark.asyncio
    async def test_duplicate_detection_error_handling(self):
        """Test that duplicate detection errors don't fail validation."""
        context = self._create_context("art_5", "checksum_5")
        
        # Mock: dedup service throws error
        self.mock_cache_manager.exists.return_value = False
        self.mock_dedup_client.check_duplicate.side_effect = Exception("Service error")
        self.mock_cache_manager.get_checksum_cache_key.return_value = "cache_key_5"

        result = await self.stage.execute(context)

        # Should not fail, but add warning
        assert result.validation_details.not_duplicate is True
        assert len(result.warnings) > 0
        assert "Duplicate detection error" in result.warnings[0]

    @pytest.mark.asyncio
    async def test_multiple_articles_same_checksum(self):
        """Test that multiple articles with same checksum are detected."""
        # First article (new)
        context1 = self._create_context("art_6", "checksum_6")
        self.mock_cache_manager.exists.return_value = False
        self.mock_dedup_client.check_duplicate.return_value = False
        self.mock_cache_manager.get_checksum_cache_key.return_value = "cache_key_6"

        result1 = await self.stage.execute(context1)
        assert result1.validation_details.not_duplicate is True

        # Second article (duplicate)
        context2 = self._create_context("art_7", "checksum_6")
        self.mock_cache_manager.exists.return_value = True
        self.mock_cache_manager.get_checksum_cache_key.return_value = "cache_key_6"

        result2 = await self.stage.execute(context2)
        assert result2.validation_details.not_duplicate is False

    @pytest.mark.asyncio
    async def test_different_checksums_not_duplicates(self):
        """Test that articles with different checksums are not duplicates."""
        checksums = ["checksum_a", "checksum_b", "checksum_c"]
        
        for i, checksum in enumerate(checksums):
            context = self._create_context(f"art_{i}", checksum)
            self.mock_cache_manager.exists.return_value = False
            self.mock_dedup_client.check_duplicate.return_value = False
            self.mock_cache_manager.get_checksum_cache_key.return_value = f"cache_key_{i}"

            result = await self.stage.execute(context)
            assert result.validation_details.not_duplicate is True

    @pytest.mark.asyncio
    async def test_cache_key_generation(self):
        """Test that cache keys are properly generated."""
        context = self._create_context("art_8", "checksum_8")
        
        self.mock_cache_manager.exists.return_value = False
        self.mock_dedup_client.check_duplicate.return_value = False
        self.mock_cache_manager.get_checksum_cache_key.return_value = "generated_key"

        await self.stage.execute(context)

        # Verify cache key was requested
        self.mock_cache_manager.get_checksum_cache_key.assert_called()

    @pytest.mark.asyncio
    async def test_article_registration_on_new_article(self):
        """Test that new articles are registered in dedup service."""
        context = self._create_context("art_9", "checksum_9")

        self.mock_cache_manager.exists.return_value = False
        self.mock_dedup_client.check_duplicate.return_value = False
        self.mock_cache_manager.get_checksum_cache_key.return_value = "cache_key_9"

        await self.stage.execute(context)

        # Verify article was registered with new signature (includes content and published_at)
        self.mock_dedup_client.register_article.assert_called_once()
        call_kwargs = self.mock_dedup_client.register_article.call_args[1]
        assert call_kwargs['checksum'] == "checksum_9"
        assert call_kwargs['article_id'] == "art_9"

    @pytest.mark.asyncio
    async def test_cache_update_on_new_article(self):
        """Test that cache is updated for new articles."""
        context = self._create_context("art_10", "checksum_10")
        
        self.mock_cache_manager.exists.return_value = False
        self.mock_dedup_client.check_duplicate.return_value = False
        self.mock_cache_manager.get_checksum_cache_key.return_value = "cache_key_10"

        await self.stage.execute(context)

        # Verify cache was updated
        self.mock_cache_manager.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_validation_details_updated(self):
        """Test that validation details are properly updated."""
        context = self._create_context("art_11", "checksum_11")
        
        self.mock_cache_manager.exists.return_value = False
        self.mock_dedup_client.check_duplicate.return_value = False
        self.mock_cache_manager.get_checksum_cache_key.return_value = "cache_key_11"

        result = await self.stage.execute(context)

        # Verify validation details
        assert isinstance(result.validation_details, ValidationDetails)
        assert hasattr(result.validation_details, 'not_duplicate')
        assert result.validation_details.not_duplicate is True

    @pytest.mark.asyncio
    async def test_error_message_format(self):
        """Test that error messages are properly formatted."""
        context = self._create_context("art_12", "checksum_12")
        
        self.mock_cache_manager.exists.return_value = True
        self.mock_cache_manager.get_checksum_cache_key.return_value = "cache_key_12"

        result = await self.stage.execute(context)

        assert len(result.errors) > 0
        error_msg = result.errors[0]
        assert "checksum_12" in error_msg
        assert "Duplicate detected" in error_msg

