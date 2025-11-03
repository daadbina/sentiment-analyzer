"""
Article normalizer for data transformation and standardization.

Transforms parsed articles into standardized format for publishing.
"""

import logging
import re
import uuid
from typing import Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from .parser import ParsedArticle
from .models import NewsRawMessage
from .utils import TimestampUtils, ChecksumEngine, LanguageDetector
from .exceptions import NormalizationError

logger = logging.getLogger(__name__)


class ArticleNormalizer:
    """
    Normalizes parsed articles for publishing.

    Standardizes URLs, timestamps, text, and metadata.
    """

    def __init__(self) -> None:
        """Initialize normalizer."""
        self.language_detector = LanguageDetector()

    def normalize(
        self,
        article: ParsedArticle,
        feed_id: str,
        job_id: str,
        validation_score: float = 1.0,
    ) -> NewsRawMessage:
        """
        Normalize article to Kafka message format.

        Args:
            article: Parsed article.
            feed_id: Feed source identifier.
            job_id: Crawl job identifier.
            validation_score: Data quality score.

        Returns:
            NewsRawMessage: Normalized message.

        Raises:
            NormalizationError: If normalization fails.
        """
        try:
            # Normalize URLs
            canonical_url = self._normalize_url(article.url)
            url = article.url

            # Normalize text
            title = self._normalize_text(article.title)
            body = self._normalize_text(article.body)

            # Detect language
            language, _ = self.language_detector.detect(body)

            # Generate checksum
            checksum = ChecksumEngine.generate_sha256(body)

            # Normalize timestamps
            published_at = TimestampUtils.to_iso8601(article.published_at)
            crawled_at = TimestampUtils.to_iso8601(TimestampUtils.now_utc())

            # Extract country if available
            country = self._extract_country(article)

            # Create message
            article_id = (
                article.article_id
                or self._generate_article_id(canonical_url)
            )
            message = NewsRawMessage(
                article_id=article_id,
                canonical_url=canonical_url,
                title=title,
                body=body,
                url=url,
                source=article.source,
                language=language,
                published_at=published_at,
                crawled_at=crawled_at,
                country=country,
                checksum=checksum,
                validation_score=validation_score,
                schema_version="v1.0",
                ingest_job_id=job_id,
                publisher_id=feed_id,
                author=article.author,
                extraction_method=article.extraction_method,
                metadata=article.metadata or {},
            )

            logger.debug(f"Normalized article: {message.article_id}")
            return message

        except Exception as e:
            raise NormalizationError(
                f"Failed to normalize article: {str(e)}",
                error_code="NORMALIZATION_FAILED",
            )

    def _normalize_url(self, url: str) -> str:
        """
        Normalize URL by removing tracking parameters.

        Args:
            url: Original URL.

        Returns:
            str: Normalized URL.
        """
        try:
            parsed = urlparse(url)

            # Remove common tracking parameters
            tracking_params = {
                "utm_source",
                "utm_medium",
                "utm_campaign",
                "utm_content",
                "utm_term",
                "fbclid",
                "gclid",
                "msclkid",
            }

            query_params = parse_qs(parsed.query, keep_blank_values=True)
            filtered_params = {
                k: v for k, v in query_params.items()
                if k.lower() not in tracking_params
            }

            # Reconstruct query string
            new_query = urlencode(filtered_params, doseq=True)

            # Reconstruct URL
            normalized = urlunparse(
                (
                    parsed.scheme,
                    parsed.netloc,
                    parsed.path,
                    parsed.params,
                    new_query,
                    "",  # Remove fragment
                )
            )

            return normalized

        except Exception as e:
            logger.warning(f"Failed to normalize URL: {str(e)}")
            return url

    def _normalize_text(self, text: str) -> str:
        """
        Normalize text by cleaning whitespace and special characters.

        Args:
            text: Original text.

        Returns:
            str: Normalized text.
        """
        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text)

        # Remove control characters
        text = "".join(char for char in text if ord(char) >= 32 or char in "\n\t")

        # Strip leading/trailing whitespace
        text = text.strip()

        return text

    def _extract_country(self, article: ParsedArticle) -> Optional[str]:
        """
        Extract country code from article metadata.

        Args:
            article: Article to extract from.

        Returns:
            str or None: Country code if found.
        """
        if article.metadata and "country" in article.metadata:
            country = article.metadata["country"]
            if isinstance(country, str) and len(country) == 2:
                return country.upper()

        return None

    def _generate_article_id(self, url: str) -> str:
        """
        Generate article ID from URL.

        Args:
            url: Article URL.

        Returns:
            str: Generated article ID.
        """
        # Generate UUID for new articles
        return str(uuid.uuid4())
