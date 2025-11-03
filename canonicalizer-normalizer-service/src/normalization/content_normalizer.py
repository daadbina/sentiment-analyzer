"""Content normalization module."""

import logging
import hashlib
import re
from typing import Tuple
from bs4 import BeautifulSoup
import ftfy

from src.exceptions import ContentNormalizationError
from src.models import ContentNormalizationResult

logger = logging.getLogger(__name__)


class ContentNormalizer:
    """Normalizes article content (title and body)."""

    def __init__(self):
        """Initialize content normalizer."""
        self.html_tag_pattern = re.compile(r"<[^>]+>")
        self.whitespace_pattern = re.compile(r"\s+")
        self.url_pattern = re.compile(r"https?://\S+")

    def normalize(self, title: str, body: str) -> ContentNormalizationResult:
        """Normalize article content.

        Args:
            title: Article title
            body: Article body

        Returns:
            ContentNormalizationResult with normalized content
        """
        try:
            # Normalize title
            normalized_title = self._normalize_text(title)

            # Normalize body
            normalized_body = self._normalize_text(body)

            # Calculate checksums
            normalized_checksum = hashlib.sha256(
                (normalized_title + normalized_body).encode()
            ).hexdigest()

            # Calculate word and sentence counts
            word_count = len(normalized_body.split())
            sentence_count = len(re.split(r"[.!?]+", normalized_body))

            return ContentNormalizationResult(
                original_title=title,
                normalized_title=normalized_title,
                original_body=body,
                normalized_body=normalized_body,
                normalized_checksum=normalized_checksum,
                word_count=word_count,
                sentence_count=sentence_count,
            )

        except Exception as e:
            logger.error(f"Content normalization failed: {e}")
            return ContentNormalizationResult(
                original_title=title,
                normalized_title=title,
                original_body=body,
                normalized_body=body,
                normalized_checksum="",
                word_count=0,
                sentence_count=0,
                error=str(e),
            )

    def _normalize_text(self, text: str) -> str:
        """Normalize text content.

        Args:
            text: Text to normalize

        Returns:
            Normalized text
        """
        if not text:
            return ""

        # Step 1: Fix encoding issues
        text = ftfy.fix_text(text)

        # Step 2: Remove HTML tags
        text = self.html_tag_pattern.sub(" ", text)

        # Step 3: Decode HTML entities
        text = BeautifulSoup(text, "html.parser").get_text()

        # Step 4: Remove URLs
        text = self.url_pattern.sub("", text)

        # Step 5: Normalize whitespace
        text = self.whitespace_pattern.sub(" ", text)

        # Step 6: Strip leading/trailing whitespace
        text = text.strip()

        # Step 7: Normalize quotes
        text = text.replace(""", '"').replace(""", '"')
        text = text.replace("'", "'").replace("'", "'")

        # Step 8: Remove control characters
        text = "".join(char for char in text if ord(char) >= 32 or char in "\n\t")

        return text

    def clean_title(self, title: str) -> str:
        """Clean article title.

        Args:
            title: Title to clean

        Returns:
            Cleaned title
        """
        title = self._normalize_text(title)

        # Remove common suffixes
        suffixes = [" - CNN", " - BBC", " - Reuters", " | News", " | Article"]
        for suffix in suffixes:
            if title.endswith(suffix):
                title = title[: -len(suffix)]

        # Limit length
        if len(title) > 500:
            title = title[:497] + "..."

        return title

    def clean_body(self, body: str) -> str:
        """Clean article body.

        Args:
            body: Body to clean

        Returns:
            Cleaned body
        """
        body = self._normalize_text(body)

        # Remove common footer patterns
        footer_patterns = [
            r"©.*?All rights reserved",
            r"Follow us on.*?$",
            r"Share this.*?$",
            r"Subscribe.*?$",
        ]

        for pattern in footer_patterns:
            body = re.sub(pattern, "", body, flags=re.IGNORECASE | re.MULTILINE)

        # Remove excessive newlines
        body = re.sub(r"\n{3,}", "\n\n", body)

        return body

