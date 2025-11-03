"""Performance tests for throughput and latency."""

import time
import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.service import ValidatorService
from src.models import NewsRaw, ValidationContext


class TestThroughput:
    """Test throughput performance."""

    @pytest.mark.asyncio
    async def test_message_processing_latency(self):
        """Test message processing latency."""
        # Create a mock message
        raw_msg = NewsRaw(
            article_id="test_123",
            canonical_url="https://example.com",
            title="Test Article Title",
            body="This is a test article body with sufficient content for validation.",
            url="https://example.com",
            published_at="2025-11-02T10:00:00Z",
            language="en",
            source="test_source",
            crawled_at="2025-11-02T11:00:00Z",
            checksum="abc123",
            validation_score=0.8,
            schema_version="1.0.0",
            ingest_job_id="job_123",
            publisher_id="pub_123",
            extraction_method="rss",
        )

        # Mock the validator service
        with patch("src.service.ValidatorService") as mock_service:
            service = mock_service.return_value
            service.process_message = AsyncMock()

            # Measure processing time
            start_time = time.time()
            await service.process_message()
            elapsed_time = time.time() - start_time

            # Verify latency is reasonable (should be < 2 seconds per design doc)
            assert elapsed_time < 2.0, f"Processing took {elapsed_time}s, expected < 2s"

    def test_validation_score_calculation_performance(self):
        """Test validation score calculation performance."""
        from src.validation.scoring import ValidationScorer
        from src.models import ValidationDetails

        # Create a validation context
        context = ValidationContext(
            article_id="test_123",
            trace_id="trace_123",
            job_id="job_123",
            raw_message=NewsRaw(
                article_id="test_123",
                canonical_url="https://example.com",
                title="Test Article Title",
                body="This is a test article body with sufficient content for validation.",
                url="https://example.com",
                published_at="2025-11-02T10:00:00Z",
                language="en",
                source="test_source",
                crawled_at="2025-11-02T11:00:00Z",
                checksum="abc123",
                validation_score=0.8,
                schema_version="1.0.0",
                ingest_job_id="job_123",
                publisher_id="pub_123",
                extraction_method="rss",
            ),
            language="en",
            language_confidence=0.95,
            validation_details=ValidationDetails(
                schema_valid=True,
                encoding_valid=True,
                timestamp_valid=True,
                language_detected=True,
                source_verified=True,
                not_duplicate=True,
                content_quality_ok=True,
            ),
            country="US",
            quality_score=0.85,
        )

        # Measure scoring time
        start_time = time.time()
        score = ValidationScorer.calculate_validation_score(
            language_score=0.95,
            source_score=1.0,
            encoding_score=1.0,
            timestamp_score=1.0,
            geographic_score=1.0,
            content_score=0.85,
        )
        elapsed_time = time.time() - start_time

        # Verify score is calculated quickly (should be < 100ms)
        assert elapsed_time < 0.1, f"Scoring took {elapsed_time}s, expected < 0.1s"
        assert 0.0 <= score <= 1.0, f"Score {score} out of range"

    def test_language_detection_performance(self):
        """Test language detection performance."""
        from src.language.detector import LanguageDetector

        detector = LanguageDetector()

        # Test with English text
        text = "This is a test article about technology and innovation."

        # Measure detection time
        start_time = time.time()
        language, confidence, method = detector.detect(text)
        elapsed_time = time.time() - start_time

        # Verify detection is reasonably fast (should be < 1 second)
        assert elapsed_time < 1.0, f"Detection took {elapsed_time}s, expected < 1s"
        assert language is not None
        assert 0.0 <= confidence <= 1.0

    def test_timestamp_parsing_performance(self):
        """Test timestamp parsing performance."""
        from src.validation.timestamp import TimestampValidator

        timestamps = [
            "2025-11-02T10:00:00Z",
            "2025-11-02T10:00:00+00:00",
            "2025-11-02 10:00:00",
            "Nov 02, 2025 10:00:00",
        ]

        # Measure parsing time for multiple timestamps
        start_time = time.time()
        for ts in timestamps:
            result = TimestampValidator.parse_timestamp(ts)
            assert result is not None
        elapsed_time = time.time() - start_time

        # Verify parsing is fast (should be < 100ms for 4 timestamps)
        assert elapsed_time < 0.1, f"Parsing took {elapsed_time}s, expected < 0.1s"

    def test_encoding_validation_performance(self):
        """Test encoding validation performance."""
        from src.validation.encoding import EncodingValidator

        text = "This is a test article with special characters: é, ñ, ü, 中文, العربية"

        # Measure validation time
        start_time = time.time()
        is_valid, sanitized, encoding, error = EncodingValidator.validate_and_sanitize(
            text.encode("utf-8")
        )
        elapsed_time = time.time() - start_time

        # Verify validation is fast (should be < 50ms)
        assert elapsed_time < 0.05, f"Validation took {elapsed_time}s, expected < 0.05s"
        assert is_valid is True

    def test_quality_scoring_performance(self):
        """Test quality scoring performance."""
        from src.validation.quality import QualityScorer

        title = "Test Article Title"
        body = "This is a test article body with sufficient content for validation. " * 10
        url = "https://example.com/article"

        # Measure scoring time
        start_time = time.time()
        score, issues = QualityScorer.score_content(title, body, url, "en")
        elapsed_time = time.time() - start_time

        # Verify scoring is fast (should be < 50ms)
        assert elapsed_time < 0.05, f"Scoring took {elapsed_time}s, expected < 0.05s"
        assert 0.0 <= score <= 1.0

    def test_geographic_extraction_performance(self):
        """Test geographic extraction performance."""
        from src.validation.geographic import GeographicExtractor

        title = "Breaking News from United States"
        body = "This article discusses events in the United States and Canada."
        url = "https://example.com/us/news"

        # Measure extraction time
        start_time = time.time()
        country = GeographicExtractor.extract_country(title, body, url)
        elapsed_time = time.time() - start_time

        # Verify extraction is fast (should be < 50ms)
        assert elapsed_time < 0.05, f"Extraction took {elapsed_time}s, expected < 0.05s"

