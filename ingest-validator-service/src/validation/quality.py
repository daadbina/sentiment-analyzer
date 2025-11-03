"""Content quality validation and scoring."""

import logging
import re
from typing import Tuple, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class QualityScorer:
    """Scores content quality based on heuristics."""

    # Language-specific thresholds (adjusted for RSS feeds with short summaries)
    LANGUAGE_THRESHOLDS = {
        "en": {"title_min": 5, "title_max": 200, "body_min": 50, "word_count_min": 10},
        "fa": {"title_min": 5, "title_max": 200, "body_min": 50, "word_count_min": 10},
        "ru": {"title_min": 5, "title_max": 200, "body_min": 50, "word_count_min": 10},
        "zh": {"title_min": 5, "title_max": 200, "body_min": 40, "word_count_min": 15},
        "ar": {"title_min": 5, "title_max": 200, "body_min": 50, "word_count_min": 10},
    }

    DEFAULT_THRESHOLDS = {
        "title_min": 5,
        "title_max": 200,
        "body_min": 50,  # Reduced from 100 for RSS feeds
        "word_count_min": 10,  # Reduced from 20 for RSS feeds
    }
    MAX_SPECIAL_CHAR_RATIO = 0.05

    @staticmethod
    def get_thresholds(language: str) -> dict:
        """Get quality thresholds for language.

        Args:
            language: Language code

        Returns:
            Thresholds dictionary
        """
        return QualityScorer.LANGUAGE_THRESHOLDS.get(
            language, QualityScorer.DEFAULT_THRESHOLDS
        )

    @staticmethod
    def validate_title(title: str, language: str = "en") -> Tuple[bool, Optional[str]]:
        """Validate title.

        Args:
            title: Title text
            language: Language code

        Returns:
            Tuple of (is_valid, error_message)
        """
        thresholds = QualityScorer.get_thresholds(language)

        if not title:
            return False, "Title is empty"

        title_len = len(title)
        if title_len < thresholds["title_min"]:
            return False, f"Title too short ({title_len} < {thresholds['title_min']})"

        if title_len > thresholds["title_max"]:
            return False, f"Title too long ({title_len} > {thresholds['title_max']})"

        return True, None

    @staticmethod
    def validate_body(body: str, language: str = "en") -> Tuple[bool, Optional[str]]:
        """Validate body content.

        Args:
            body: Body text
            language: Language code

        Returns:
            Tuple of (is_valid, error_message)
        """
        thresholds = QualityScorer.get_thresholds(language)

        if not body:
            return False, "Body is empty"

        body_len = len(body)
        if body_len < thresholds["body_min"]:
            return False, f"Body too short ({body_len} < {thresholds['body_min']})"

        # Check minimum sentences (relaxed for RSS feeds with summaries)
        sentences = re.split(r"[.!?]+", body)
        sentences = [s.strip() for s in sentences if s.strip()]
        if len(sentences) < 1:
            return False, "Body has no sentences"

        return True, None

    @staticmethod
    def count_words(text: str) -> int:
        """Count words in text.

        Args:
            text: Text string

        Returns:
            Word count
        """
        # Split on whitespace and punctuation
        words = re.findall(r"\b\w+\b", text)
        return len(words)

    @staticmethod
    def validate_word_count(
        text: str, language: str = "en"
    ) -> Tuple[bool, Optional[str]]:
        """Validate minimum word count.

        Args:
            text: Text string
            language: Language code

        Returns:
            Tuple of (is_valid, error_message)
        """
        thresholds = QualityScorer.get_thresholds(language)
        word_count = QualityScorer.count_words(text)

        if word_count < thresholds["word_count_min"]:
            return (
                False,
                f"Word count too low ({word_count} < {thresholds['word_count_min']})",
            )

        return True, None

    @staticmethod
    def validate_url(url: str) -> Tuple[bool, Optional[str]]:
        """Validate URL format.

        Args:
            url: URL string

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            result = urlparse(url)
            if not all([result.scheme, result.netloc]):
                return False, "Invalid URL format"
            if result.scheme not in ["http", "https"]:
                return False, f"Invalid URL scheme: {result.scheme}"
            return True, None
        except Exception as e:
            return False, f"URL validation error: {e}"

    @staticmethod
    def calculate_special_char_ratio(text: str) -> float:
        """Calculate ratio of special characters.

        Args:
            text: Text string

        Returns:
            Ratio of special characters (0.0-1.0)
        """
        if not text:
            return 0.0

        special_chars = len(
            re.findall(r"[^a-zA-Z0-9\s\u0600-\u06FF\u4E00-\u9FFF\u0400-\u04FF]", text)
        )
        return special_chars / len(text)

    @staticmethod
    def score_content(
        title: str,
        body: str,
        url: str,
        language: str = "en",
    ) -> Tuple[float, list[str]]:
        """Score content quality.

        Args:
            title: Title text
            body: Body text
            url: Article URL
            language: Language code

        Returns:
            Tuple of (quality_score, list_of_issues)
        """
        issues = []
        score = 1.0

        # Validate title (reduced penalty for RSS feeds)
        title_valid, title_error = QualityScorer.validate_title(title, language)
        if not title_valid:
            issues.append(f"Title: {title_error}")
            score -= 0.1  # Reduced from 0.2

        # Validate body (reduced penalty for RSS feeds)
        body_valid, body_error = QualityScorer.validate_body(body, language)
        if not body_valid:
            issues.append(f"Body: {body_error}")
            score -= 0.1  # Reduced from 0.2

        # Validate word count (reduced penalty for RSS feeds)
        word_valid, word_error = QualityScorer.validate_word_count(body, language)
        if not word_valid:
            issues.append(f"Word count: {word_error}")
            score -= 0.05  # Reduced from 0.15

        # Validate URL
        url_valid, url_error = QualityScorer.validate_url(url)
        if not url_valid:
            issues.append(f"URL: {url_error}")
            score -= 0.15

        # Check special character ratio
        special_ratio = QualityScorer.calculate_special_char_ratio(body)
        if special_ratio > QualityScorer.MAX_SPECIAL_CHAR_RATIO:
            issues.append(f"High special character ratio: {special_ratio:.2%}")
            score -= 0.1

        # Ensure score is in valid range
        score = max(0.0, min(1.0, score))

        return score, issues
