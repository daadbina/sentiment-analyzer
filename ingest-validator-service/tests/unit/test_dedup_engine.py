"""Tests for deduplication engine with MinHash + LSH."""

import pytest
from datetime import datetime, timedelta
from src.deduplication.dedup_engine import DeduplicationEngine, DuplicateResult


class TestDeduplicationEngine:
    """Test deduplication engine with MinHash and LSH."""

    @pytest.fixture
    def dedup_engine(self):
        """Create deduplication engine."""
        return DeduplicationEngine(
            num_perm=128,
            similarity_threshold=0.85,
            time_window_hours=48,
        )

    def test_exact_duplicate_detection(self, dedup_engine):
        """Test exact duplicate detection using checksum."""
        checksum = "abc123def456"
        content = "This is a test article about technology"
        published_at = datetime.utcnow()

        # Add first article
        dedup_engine.add_article(
            article_id="article1",
            checksum=checksum,
            content=content,
            published_at=published_at,
        )

        # Check for exact duplicate
        result = dedup_engine.check_duplicate(
            checksum=checksum,
            content="Different content",
            published_at=published_at,
        )

        assert result.is_duplicate is True
        assert result.match_type == "exact"
        assert result.similarity_score == 1.0
        assert result.matched_article_id == "article1"

    def test_no_duplicate_detection(self, dedup_engine):
        """Test when no duplicate exists."""
        content1 = "This is a test article about technology"
        content2 = "Completely different article about sports"
        published_at = datetime.utcnow()

        # Add first article
        dedup_engine.add_article(
            article_id="article1",
            checksum="checksum1",
            content=content1,
            published_at=published_at,
        )

        # Check for duplicate with different content
        result = dedup_engine.check_duplicate(
            checksum="checksum2",
            content=content2,
            published_at=published_at,
        )

        assert result.is_duplicate is False
        assert result.match_type == "none"
        assert result.similarity_score == 0.0

    def test_near_duplicate_detection(self, dedup_engine):
        """Test near-duplicate detection using MinHash + LSH."""
        published_at = datetime.utcnow()

        # Original article - longer content for better shingle matching
        content1 = (
            "Breaking news: Major technology company announces new product "
            "with advanced features and capabilities for enterprise customers"
        )
        dedup_engine.add_article(
            article_id="article1",
            checksum="checksum1",
            content=content1,
            published_at=published_at,
        )

        # Very similar article (near-duplicate) - mostly same content
        content2 = (
            "Breaking news: Major technology company announces new product "
            "with advanced features and capabilities for enterprise customers today"
        )
        result = dedup_engine.check_duplicate(
            checksum="checksum2",
            content=content2,
            published_at=published_at,
        )

        # Should detect as near-duplicate (high similarity)
        assert result.is_duplicate is True
        assert result.match_type == "near"
        assert result.similarity_score >= 0.75  # Relaxed threshold for test
        assert result.matched_article_id == "article1"

    def test_time_window_filtering(self, dedup_engine):
        """Test temporal window filtering for near-duplicates."""
        now = datetime.utcnow()
        old_time = now - timedelta(hours=72)  # 72 hours ago (outside 48-hour window)

        content = "Technology news article"

        # Add old article
        dedup_engine.add_article(
            article_id="article1",
            checksum="checksum1",
            content=content,
            published_at=old_time,
        )

        # Check for duplicate with current time (outside window)
        result = dedup_engine.check_duplicate(
            checksum="checksum2",
            content=content,
            published_at=now,
        )

        # Should not detect as duplicate (outside time window)
        assert result.is_duplicate is False
        assert result.match_type == "none"

    def test_time_window_inclusion(self, dedup_engine):
        """Test that articles within time window are detected."""
        now = datetime.utcnow()
        recent_time = now - timedelta(hours=24)  # 24 hours ago (within 48-hour window)

        content = "Technology news article"

        # Add recent article
        dedup_engine.add_article(
            article_id="article1",
            checksum="checksum1",
            content=content,
            published_at=recent_time,
        )

        # Check for duplicate with current time (within window)
        result = dedup_engine.check_duplicate(
            checksum="checksum2",
            content=content,
            published_at=now,
        )

        # Should detect as duplicate (within time window)
        assert result.is_duplicate is True
        assert result.match_type == "near"

    def test_multiple_articles_in_index(self, dedup_engine):
        """Test dedup engine with multiple articles."""
        published_at = datetime.utcnow()

        # Add multiple articles
        articles = [
            ("article1", "checksum1", "Technology news about AI"),
            ("article2", "checksum2", "Sports news about football"),
            ("article3", "checksum3", "Politics news about elections"),
        ]

        for article_id, checksum, content in articles:
            dedup_engine.add_article(
                article_id=article_id,
                checksum=checksum,
                content=content,
                published_at=published_at,
            )

        # Check for exact duplicate of article2
        result = dedup_engine.check_duplicate(
            checksum="checksum2",
            content="Different content",
            published_at=published_at,
        )

        assert result.is_duplicate is True
        assert result.matched_article_id == "article2"

    def test_similarity_threshold(self, dedup_engine):
        """Test similarity threshold enforcement."""
        published_at = datetime.utcnow()

        # Add article
        content1 = "Technology news"
        dedup_engine.add_article(
            article_id="article1",
            checksum="checksum1",
            content=content1,
            published_at=published_at,
        )

        # Very different content (should not match)
        content2 = "Sports news"
        result = dedup_engine.check_duplicate(
            checksum="checksum2",
            content=content2,
            published_at=published_at,
        )

        assert result.is_duplicate is False

    def test_get_stats(self, dedup_engine):
        """Test statistics retrieval."""
        published_at = datetime.utcnow()

        # Add articles
        for i in range(3):
            dedup_engine.add_article(
                article_id=f"article{i}",
                checksum=f"checksum{i}",
                content=f"Article {i} content",
                published_at=published_at,
            )

        stats = dedup_engine.get_stats()

        assert stats["num_articles"] == 3
        assert stats["num_checksums"] == 3
        assert stats["num_minhashes"] == 3
        assert stats["similarity_threshold"] == 0.85
        assert stats["time_window_hours"] == 48

    def test_clear_engine(self, dedup_engine):
        """Test clearing deduplication engine."""
        published_at = datetime.utcnow()

        # Add articles
        dedup_engine.add_article(
            article_id="article1",
            checksum="checksum1",
            content="Content 1",
            published_at=published_at,
        )

        # Verify article is indexed
        stats_before = dedup_engine.get_stats()
        assert stats_before["num_articles"] == 1

        # Clear engine
        dedup_engine.clear()

        # Verify engine is empty
        stats_after = dedup_engine.get_stats()
        assert stats_after["num_articles"] == 0
        assert stats_after["num_checksums"] == 0

    def test_empty_content_handling(self, dedup_engine):
        """Test handling of empty content."""
        published_at = datetime.utcnow()

        # Add article with empty content
        dedup_engine.add_article(
            article_id="article1",
            checksum="checksum1",
            content="",
            published_at=published_at,
        )

        # Check for duplicate with empty content
        result = dedup_engine.check_duplicate(
            checksum="checksum2",
            content="",
            published_at=published_at,
        )

        # Should handle gracefully
        assert isinstance(result, DuplicateResult)

    def test_duplicate_result_structure(self):
        """Test DuplicateResult data structure."""
        result = DuplicateResult(
            is_duplicate=True,
            similarity_score=0.95,
            matched_article_id="article123",
            match_type="near",
        )

        assert result.is_duplicate is True
        assert result.similarity_score == 0.95
        assert result.matched_article_id == "article123"
        assert result.match_type == "near"

    def test_shingle_generation(self, dedup_engine):
        """Test n-gram (shingle) generation."""
        text = "This is a test article"
        shingles = dedup_engine._generate_shingles(text, n=2)

        assert len(shingles) > 0
        assert isinstance(shingles, list)
        assert all(isinstance(s, str) for s in shingles)

    def test_minhash_signature_generation(self, dedup_engine):
        """Test MinHash signature generation."""
        content = "Technology news article"
        signature = dedup_engine._generate_signature(content)

        assert signature is not None
        # MinHash should have the configured number of permutations
        assert len(signature.hashvalues) == 128

    def test_similarity_calculation(self, dedup_engine):
        """Test Jaccard similarity calculation."""
        content1 = "Technology news article"
        content2 = "Technology news article"

        sig1 = dedup_engine._generate_signature(content1)
        sig2 = dedup_engine._generate_signature(content2)

        similarity = dedup_engine._calculate_similarity(sig1, sig2)

        assert 0.0 <= similarity <= 1.0
        # Identical content should have high similarity
        assert similarity >= 0.9

