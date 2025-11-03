"""
Performance benchmark tests for the Crawler Service.

Measures throughput, latency, and resource usage under various loads.
"""

import asyncio
import time
from datetime import datetime

import pytest

from src.deduplication import DeduplicationEngine
from src.models import NewsRawMessage
from src.normalizer import ArticleNormalizer
from src.parser.base import ParsedArticle
from src.utils.checksum import ChecksumEngine
from src.utils.language_detector import LanguageDetector
from src.validation import ArticleValidator


class TestPerformanceBenchmarks:
    """Performance benchmarks for core components."""

    @pytest.fixture
    def normalizer(self):
        """Create article normalizer."""
        return ArticleNormalizer()

    @pytest.fixture
    def validator(self):
        """Create article validator."""
        return ArticleValidator()

    @pytest.fixture
    def dedup_engine(self):
        """Create deduplication engine."""
        return DeduplicationEngine(num_perm=128)

    @pytest.fixture
    def checksum_engine(self):
        """Create checksum engine."""
        return ChecksumEngine()

    @pytest.fixture
    def language_detector(self):
        """Create language detector."""
        return LanguageDetector()

    def test_normalization_throughput(self, normalizer, benchmark):
        """Benchmark article normalization throughput."""
        article = ParsedArticle(
            title="Test Article Title",
            body="This is a test article body with sufficient content for processing.",
            url="https://example.com/article/123",
            canonical_url="https://example.com/article/123",
            published_at=datetime.now(),
            source="Test Source",
            language="en",
        )

        def normalize():
            return normalizer.normalize(article, "feed_001", "job_001")

        result = benchmark(normalize)
        assert isinstance(result, NewsRawMessage)

    def test_validation_throughput(self, validator, benchmark):
        """Benchmark article validation throughput."""
        message = NewsRawMessage(
            article_id="test_001",
            canonical_url="https://example.com/1",
            title="Valid Article Title",
            body="This is a valid body with sufficient content for validation. " * 5,
            url="https://example.com/1",
            source="Test Source",
            language="en",
            published_at="2025-11-02T10:00:00Z",
            crawled_at="2025-11-02T10:00:00Z",
            checksum="abc123",
            validation_score=0.85,
            schema_version="1.0",
            ingest_job_id="job_001",
            publisher_id="pub_001",
            extraction_method="html",
        )

        def validate():
            return validator.validate(message)

        result = benchmark(validate)
        assert result.is_valid

    def test_deduplication_throughput(self, dedup_engine, benchmark):
        """Benchmark deduplication check throughput."""
        message = NewsRawMessage(
            article_id="test_001",
            canonical_url="https://example.com/1",
            title="Article",
            body="Content.",
            url="https://example.com/1",
            source="Source",
            language="en",
            published_at="2025-11-02T10:00:00Z",
            crawled_at="2025-11-02T10:00:00Z",
            checksum="abc123",
            validation_score=0.8,
            schema_version="1.0",
            ingest_job_id="job_001",
            publisher_id="pub_001",
            extraction_method="html",
        )

        dedup_engine.add_article(message)

        def check_duplicate():
            return dedup_engine.is_duplicate(message)

        result = benchmark(check_duplicate)
        assert result

    def test_checksum_generation_throughput(self, checksum_engine, benchmark):
        """Benchmark checksum generation throughput."""
        content = "This is test content for checksum generation. " * 100

        def generate_checksum():
            return checksum_engine.generate_sha256(content)

        result = benchmark(generate_checksum)
        assert len(result) == 64  # SHA256 hex length

    def test_language_detection_throughput(self, language_detector, benchmark):
        """Benchmark language detection throughput."""
        text = "This is a test article about technology and innovation. " * 10

        def detect_language():
            lang, conf = language_detector.detect(text)
            return lang

        result = benchmark(detect_language)
        assert result in ["en", "unknown"]

    def test_batch_normalization_performance(self, normalizer):
        """Test batch normalization performance."""
        articles = [
            ParsedArticle(
                title=f"Article {i}",
                body=f"This is a comprehensive article about technology and innovation. " * 10,
                url=f"https://example.com/article/{i}",
                canonical_url=f"https://example.com/article/{i}",
                published_at=datetime.now(),
                source="Test Source",
                language="en",
            )
            for i in range(100)
        ]

        start = time.time()
        results = [normalizer.normalize(article, "feed_001", "job_001") for article in articles]
        elapsed = time.time() - start

        assert len(results) == 100
        assert elapsed < 5.0  # Should process 100 articles in < 5 seconds

    def test_batch_validation_performance(self, validator):
        """Test batch validation performance."""
        messages = [
            NewsRawMessage(
                article_id=f"test_{i:04d}",
                canonical_url=f"https://example.com/{i}",
                title=f"Article {i}",
                body=f"Content for article {i}. " * 10,
                url=f"https://example.com/{i}",
                source="Test Source",
                language="en",
                published_at="2025-11-02T10:00:00Z",
                crawled_at="2025-11-02T10:00:00Z",
                checksum=f"abc{i:03d}",
                validation_score=0.8,
                schema_version="1.0",
                ingest_job_id="job_001",
                publisher_id="pub_001",
                extraction_method="html",
            )
            for i in range(100)
        ]

        start = time.time()
        results = [validator.validate(msg) for msg in messages]
        elapsed = time.time() - start

        assert len(results) == 100
        assert elapsed < 5.0  # Should validate 100 messages in < 5 seconds

    def test_deduplication_cache_performance(self, dedup_engine):
        """Test deduplication cache performance with large dataset."""
        # Add 1000 articles to cache
        messages = [
            NewsRawMessage(
                article_id=f"test_{i:04d}",
                canonical_url=f"https://example.com/{i}",
                title=f"Article {i}",
                body=f"Content {i}.",
                url=f"https://example.com/{i}",
                source="Source",
                language="en",
                published_at="2025-11-02T10:00:00Z",
                crawled_at="2025-11-02T10:00:00Z",
                checksum=f"abc{i:04d}",
                validation_score=0.8,
                schema_version="1.0",
                ingest_job_id="job_001",
                publisher_id="pub_001",
                extraction_method="html",
            )
            for i in range(1000)
        ]

        start = time.time()
        for msg in messages:
            dedup_engine.add_article(msg)
        add_time = time.time() - start

        # Check duplicates
        start = time.time()
        for msg in messages[:100]:
            dedup_engine.is_duplicate(msg)
        check_time = time.time() - start

        assert add_time < 10.0  # Add 1000 articles in < 10 seconds
        assert check_time < 1.0  # Check 100 duplicates in < 1 second

    @pytest.mark.asyncio
    async def test_concurrent_normalization(self, normalizer):
        """Test concurrent normalization performance."""
        articles = [
            ParsedArticle(
                title=f"Article {i}",
                body=f"This is a comprehensive article about technology and innovation. " * 5,
                url=f"https://example.com/{i}",
                canonical_url=f"https://example.com/{i}",
                published_at=datetime.now(),
                source="Source",
                language="en",
            )
            for i in range(50)
        ]

        async def normalize_article(article):
            return normalizer.normalize(article, "feed_001", "job_001")

        start = time.time()
        results = await asyncio.gather(*[normalize_article(article) for article in articles])
        elapsed = time.time() - start

        assert len(results) == 50
        assert elapsed < 5.0  # Concurrent processing should be fast

    def test_memory_efficiency_dedup_cache(self, dedup_engine):
        """Test memory efficiency of deduplication cache."""

        # Add articles until cache is full
        for i in range(10000):
            message = NewsRawMessage(
                article_id=f"test_{i:05d}",
                canonical_url=f"https://example.com/{i}",
                title=f"Article {i}",
                body=f"Content {i}.",
                url=f"https://example.com/{i}",
                source="Source",
                language="en",
                published_at="2025-11-02T10:00:00Z",
                crawled_at="2025-11-02T10:00:00Z",
                checksum=f"abc{i:05d}",
                validation_score=0.8,
                schema_version="1.0",
                ingest_job_id="job_001",
                publisher_id="pub_001",
                extraction_method="html",
            )
            dedup_engine.add_article(message)

        # Cache should not exceed max size
        stats = dedup_engine.get_cache_stats()
        assert stats["cache_size"] <= 10000
