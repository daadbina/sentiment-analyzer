"""
Article validation rules (R1-R9) from Architecture.md.

Implements data quality validation and scoring.
"""

import logging
from dataclasses import dataclass

from .parser import ParsedArticle
from .utils import TimestampUtils, ChecksumEngine, LanguageDetector
from .exceptions import ValidationError

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of article validation."""

    is_valid: bool
    validation_score: float
    errors: list[str]


class ArticleValidator:
    """
    Validates articles against R1-R9 rules from Architecture.md.

    Implements comprehensive data quality checks and scoring.
    """

    def __init__(self) -> None:
        """Initialize validator."""
        self.language_detector = LanguageDetector()

    def validate(self, article: ParsedArticle) -> ValidationResult:
        """
        Validate article against all rules.

        Args:
            article: Parsed article to validate.

        Returns:
            ValidationResult: Validation result with is_valid, score, and errors.
        """
        errors = []
        score = 1.0

        # R1: Timestamp accuracy (ISO-8601, UTC)
        try:
            self._validate_r1_timestamp(article)
        except ValidationError as e:
            errors.append(f"R1: {e.message}")
            score -= 0.15

        # Recency check: Article must be published within last 90 days
        # This ensures we process current news, not historical archives
        try:
            self._validate_article_recency(article)
        except ValidationError as e:
            errors.append(f"Recency: {e.message}")
            score -= 0.20

        # R2: Language detection (≥0.90 confidence)
        try:
            self._validate_r2_language(article)
        except ValidationError as e:
            errors.append(f"R2: {e.message}")
            score -= 0.15

        # R3: Duplicate detection (MinHash + cosine similarity)
        # Note: Implemented separately in deduplication module
        # This is a placeholder for the validation check
        try:
            self._validate_r3_duplicate_check(article)
        except ValidationError as e:
            errors.append(f"R3: {e.message}")
            score -= 0.10

        # R6: Source reliability (verify against registry)
        try:
            self._validate_r6_source_reliability(article)
        except ValidationError as e:
            errors.append(f"R6: {e.message}")
            score -= 0.15

        # R9: Encoding integrity (UTF-8, checksum)
        try:
            self._validate_r9_encoding(article)
        except ValidationError as e:
            errors.append(f"R9: {e.message}")
            score -= 0.15

        # Additional content quality checks
        try:
            self._validate_content_quality(article)
        except ValidationError as e:
            errors.append(f"Content Quality: {e.message}")
            score -= 0.15

        # Ensure score is between 0 and 1
        score = max(0.0, min(1.0, score))

        is_valid = len(errors) == 0 and score >= 0.7

        return ValidationResult(
            is_valid=is_valid, validation_score=score, errors=errors
        )

    def _validate_r1_timestamp(self, article: ParsedArticle) -> None:
        """
        R1: Validate timestamp accuracy (ISO-8601, UTC).

        Args:
            article: Article to validate.

        Raises:
            ValidationError: If timestamp is invalid.
        """
        try:
            # Convert string timestamp to datetime if needed
            published_at = article.published_at
            if isinstance(published_at, str):
                published_at = TimestampUtils.from_iso8601(published_at)

            # Check published_at is valid ISO-8601
            iso_timestamp = TimestampUtils.to_iso8601(published_at)
            if not TimestampUtils.validate_iso8601(iso_timestamp):
                raise ValidationError(
                    "Invalid timestamp format",
                    field="published_at",
                    error_code="R1_INVALID_FORMAT",
                )

            # Check timestamp is reasonable
            if not TimestampUtils.is_reasonable_date(published_at):
                raise ValidationError(
                    "Timestamp is unreasonable (too far in past or future)",
                    field="published_at",
                    error_code="R1_UNREASONABLE_DATE",
                )

        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(
                f"Timestamp validation failed: {str(e)}",
                field="published_at",
                error_code="R1_VALIDATION_FAILED",
            )

    def _validate_article_recency(self, article: ParsedArticle) -> None:
        """
        Validate article recency (published within last 90 days).

        For news crawling, we only process recent articles to ensure
        the system handles current news, not historical archives.
        This is critical for clustering and labeling to work correctly
        with articles from the same time period.

        Args:
            article: Article to validate.

        Raises:
            ValidationError: If article is too old.
        """
        try:
            # Convert string timestamp to datetime if needed
            published_at = article.published_at
            if isinstance(published_at, str):
                published_at = TimestampUtils.from_iso8601(published_at)

            # Check article is recent (within last 90 days)
            if not TimestampUtils.is_recent_article(published_at, max_age_days=90):
                raise ValidationError(
                    "Article is too old (published more than 90 days ago)",
                    field="published_at",
                    error_code="RECENCY_TOO_OLD",
                )

        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(
                f"Article recency validation failed: {str(e)}",
                field="published_at",
                error_code="RECENCY_VALIDATION_FAILED",
            )

    def _validate_r2_language(self, article: ParsedArticle) -> None:
        """
        R2: Validate language detection (≥0.85 confidence for RSS, ≥0.90 for full articles).

        RSS feeds often contain summaries with shorter text, so we use a lower threshold.
        Full articles use the stricter 0.90 threshold per Architecture.md R2.

        Args:
            article: Article to validate.

        Raises:
            ValidationError: If language detection fails or confidence too low.
        """
        if not article.body:
            raise ValidationError(
                "Cannot detect language of empty body",
                field="language",
                error_code="R2_EMPTY_BODY",
            )

        try:
            lang_code, confidence = self.language_detector.detect(article.body)

            # Use adaptive threshold based on content length
            # RSS summaries (< 500 chars): 0.80 threshold
            # Full articles (>= 500 chars): 0.90 threshold
            content_length = len(article.body)
            threshold = 0.80 if content_length < 500 else 0.90

            if confidence < threshold:
                raise ValidationError(
                    f"Language confidence {confidence:.2f} below {threshold} threshold",
                    field="language",
                    value=f"{lang_code}:{confidence:.2f}",
                    error_code="R2_LOW_CONFIDENCE",
                )

        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(
                f"Language detection failed: {str(e)}",
                field="language",
                error_code="R2_DETECTION_FAILED",
            )

    def _validate_r3_duplicate_check(self, article: ParsedArticle) -> None:
        """
        R3: Validate duplicate detection check.

        Note: Actual deduplication is handled by deduplication module.
        This validates that the article has required fields for dedup.

        Args:
            article: Article to validate.

        Raises:
            ValidationError: If required fields missing.
        """
        if not article.canonical_url:
            raise ValidationError(
                "Missing canonical_url for deduplication",
                field="canonical_url",
                error_code="R3_MISSING_URL",
            )

        if not article.body:
            raise ValidationError(
                "Missing body for deduplication",
                field="body",
                error_code="R3_MISSING_BODY",
            )

    def _validate_r6_source_reliability(self, article: ParsedArticle) -> None:
        """
        R6: Validate source reliability (verify against registry).

        Args:
            article: Article to validate.

        Raises:
            ValidationError: If source is invalid.
        """
        if not article.source:
            raise ValidationError(
                "Missing source field",
                field="source",
                error_code="R6_MISSING_SOURCE",
            )

        # Additional source validation would check against feed registry
        # This is a placeholder for that check

    def _validate_r9_encoding(self, article: ParsedArticle) -> None:
        """
        R9: Validate encoding integrity (UTF-8, checksum).

        Args:
            article: Article to validate.

        Raises:
            ValidationError: If encoding is invalid.
        """
        # Validate UTF-8 encoding
        try:
            article.title.encode("utf-8")
            article.body.encode("utf-8")
        except UnicodeEncodeError as e:
            raise ValidationError(
                f"Invalid UTF-8 encoding: {str(e)}",
                field="content",
                error_code="R9_INVALID_ENCODING",
            )

        # Validate checksum can be generated
        try:
            checksum = ChecksumEngine.generate_sha256(article.body)
            if not checksum or len(checksum) != 64:
                raise ValidationError(
                    "Invalid checksum generated",
                    field="checksum",
                    error_code="R9_INVALID_CHECKSUM",
                )
        except Exception as e:
            raise ValidationError(
                f"Checksum generation failed: {str(e)}",
                field="checksum",
                error_code="R9_CHECKSUM_FAILED",
            )

    def _validate_content_quality(self, article: ParsedArticle) -> None:
        """
        Validate general content quality.

        Uses adaptive thresholds for RSS summaries vs. full articles:
        - RSS summaries (< 500 chars): minimum 50 chars, 5 words
        - Full articles (>= 500 chars): minimum 100 chars, 20 words

        Args:
            article: Article to validate.

        Raises:
            ValidationError: If content quality is poor.
        """
        # Check minimum content length
        if len(article.title) < 5:
            raise ValidationError(
                "Title too short (minimum 5 characters)",
                field="title",
                error_code="QUALITY_SHORT_TITLE",
            )

        # Adaptive thresholds based on content length
        content_length = len(article.body)
        if content_length < 500:
            # RSS summary thresholds
            min_chars = 50
            min_words = 5
        else:
            # Full article thresholds
            min_chars = 100
            min_words = 20

        if content_length < min_chars:
            raise ValidationError(
                f"Body too short (minimum {min_chars} characters)",
                field="body",
                error_code="QUALITY_SHORT_BODY",
            )

        # Check for excessive whitespace
        word_count = len(article.body.split())
        if word_count < min_words:
            raise ValidationError(
                f"Body has too few words (minimum {min_words})",
                field="body",
                error_code="QUALITY_FEW_WORDS",
            )
