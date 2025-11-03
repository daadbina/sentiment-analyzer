"""Tests for validation scorer."""

from src.validation.scoring import ValidationScorer


class TestValidationScorer:
    """Test validation scorer."""

    def test_calculate_language_score_detected(self):
        """Test language score - detected."""
        score = ValidationScorer.calculate_language_score(True, 0.95)
        assert score == 0.95

    def test_calculate_language_score_not_detected(self):
        """Test language score - not detected."""
        score = ValidationScorer.calculate_language_score(False, 0.95)
        assert score == 0.0

    def test_calculate_source_score_verified(self):
        """Test source score - verified."""
        score = ValidationScorer.calculate_source_score(True, 0.9)
        assert score == 0.9

    def test_calculate_source_score_not_verified(self):
        """Test source score - not verified."""
        score = ValidationScorer.calculate_source_score(False, 0.9)
        assert score == 0.0

    def test_calculate_encoding_score_valid(self):
        """Test encoding score - valid."""
        score = ValidationScorer.calculate_encoding_score(True)
        assert score == 1.0

    def test_calculate_encoding_score_invalid(self):
        """Test encoding score - invalid."""
        score = ValidationScorer.calculate_encoding_score(False)
        assert score == 0.0

    def test_calculate_timestamp_score_valid(self):
        """Test timestamp score - valid."""
        score = ValidationScorer.calculate_timestamp_score(True)
        assert score == 1.0

    def test_calculate_timestamp_score_invalid(self):
        """Test timestamp score - invalid."""
        score = ValidationScorer.calculate_timestamp_score(False)
        assert score == 0.0

    def test_calculate_geographic_score_with_country(self):
        """Test geographic score - with country."""
        score = ValidationScorer.calculate_geographic_score("US")
        assert score == 1.0

    def test_calculate_geographic_score_without_country(self):
        """Test geographic score - without country."""
        score = ValidationScorer.calculate_geographic_score(None)
        assert score == 0.5

    def test_calculate_content_score(self):
        """Test content score."""
        score = ValidationScorer.calculate_content_score(0.8)
        assert score == 0.8

    def test_calculate_validation_score_all_valid(self):
        """Test validation score - all valid."""
        vs = ValidationScorer.calculate_validation_score(
            language_score=1.0,
            source_score=1.0,
            encoding_score=1.0,
            timestamp_score=1.0,
            geographic_score=1.0,
            content_score=1.0,
        )
        assert vs == 1.0

    def test_calculate_validation_score_all_invalid(self):
        """Test validation score - all invalid."""
        vs = ValidationScorer.calculate_validation_score(
            language_score=0.0,
            source_score=0.0,
            encoding_score=0.0,
            timestamp_score=0.0,
            geographic_score=0.0,
            content_score=0.0,
        )
        assert vs == 0.0

    def test_calculate_validation_score_mixed(self):
        """Test validation score - mixed."""
        vs = ValidationScorer.calculate_validation_score(
            language_score=0.9,
            source_score=0.8,
            encoding_score=1.0,
            timestamp_score=1.0,
            geographic_score=0.5,
            content_score=0.7,
        )
        assert 0.0 < vs < 1.0

    def test_decide_routing_accept(self):
        """Test routing decision - accept."""
        routing = ValidationScorer.decide_routing(0.90)
        assert routing == "accept"

    def test_decide_routing_reprocess(self):
        """Test routing decision - reprocess."""
        routing = ValidationScorer.decide_routing(0.75)
        assert routing == "reprocess"

    def test_decide_routing_reject(self):
        """Test routing decision - reject."""
        routing = ValidationScorer.decide_routing(0.60)
        assert routing == "reject"

    def test_decide_routing_boundary_accept(self):
        """Test routing decision - boundary accept."""
        routing = ValidationScorer.decide_routing(0.85)
        assert routing == "accept"

    def test_decide_routing_boundary_reprocess(self):
        """Test routing decision - boundary reprocess."""
        routing = ValidationScorer.decide_routing(0.70)
        assert routing == "reprocess"

    def test_score_from_context_all_valid(self):
        """Test score_from_context with all valid components."""
        from src.models import ValidationContext, NewsRaw, ValidationDetails
        from datetime import datetime

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

        context = ValidationContext(
            article_id="art_123",
            trace_id="trace_123",
            job_id="job_123",
            raw_message=raw_message,
        )

        # Set all validation details to valid
        context.validation_details.schema_valid = True
        context.validation_details.encoding_valid = True
        context.validation_details.timestamp_valid = True
        context.validation_details.language_detected = True
        context.validation_details.source_verified = True
        context.language_confidence = 0.95
        context.quality_score = 0.9
        context.country = "US"

        vs, routing = ValidationScorer.score_from_context(context)

        assert vs >= 0.85
        assert routing == "accept"

    def test_score_from_context_low_quality(self):
        """Test score_from_context with low quality."""
        from src.models import ValidationContext, NewsRaw, ValidationDetails
        from datetime import datetime

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

        context = ValidationContext(
            article_id="art_123",
            trace_id="trace_123",
            job_id="job_123",
            raw_message=raw_message,
        )

        # Set all validation details to valid but low quality
        context.validation_details.schema_valid = True
        context.validation_details.encoding_valid = True
        context.validation_details.timestamp_valid = True
        context.validation_details.language_detected = True
        context.validation_details.source_verified = True
        context.language_confidence = 0.95
        context.quality_score = 0.3  # Low quality
        context.country = "US"

        vs, routing = ValidationScorer.score_from_context(context)

        assert vs < 0.85
        assert routing in ["reprocess", "reject"]

    def test_score_from_context_missing_language(self):
        """Test score_from_context with missing language detection."""
        from src.models import ValidationContext, NewsRaw, ValidationDetails
        from datetime import datetime

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

        context = ValidationContext(
            article_id="art_123",
            trace_id="trace_123",
            job_id="job_123",
            raw_message=raw_message,
        )

        # Set language detection to False
        context.validation_details.schema_valid = True
        context.validation_details.encoding_valid = True
        context.validation_details.timestamp_valid = True
        context.validation_details.language_detected = False
        context.validation_details.source_verified = True
        context.language_confidence = 0.0
        context.quality_score = 0.9
        context.country = "US"

        vs, routing = ValidationScorer.score_from_context(context)

        assert vs < 0.85
        assert routing in ["reprocess", "reject"]

    def test_score_from_context_no_country(self):
        """Test score_from_context with no country."""
        from src.models import ValidationContext, NewsRaw, ValidationDetails
        from datetime import datetime

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

        context = ValidationContext(
            article_id="art_123",
            trace_id="trace_123",
            job_id="job_123",
            raw_message=raw_message,
        )

        # Set all validation details to valid but no country
        context.validation_details.schema_valid = True
        context.validation_details.encoding_valid = True
        context.validation_details.timestamp_valid = True
        context.validation_details.language_detected = True
        context.validation_details.source_verified = True
        context.language_confidence = 0.95
        context.quality_score = 0.9
        context.country = None

        vs, routing = ValidationScorer.score_from_context(context)

        # Should still be valid but lower score due to missing country
        assert vs >= 0.70
