"""Text preprocessing pipeline using Chain of Responsibility pattern."""

import logging
import re
from typing import List, Optional
import unicodedata

from src.exceptions import PreprocessingError
from src.metrics import embedding_preprocessing_duration_seconds
import time

logger = logging.getLogger(__name__)


class TextPreprocessor:
    """Text preprocessing pipeline with multiple stages."""

    def __init__(self):
        """Initialize text preprocessor."""
        self.stages = [
            self._normalize_unicode,
            self._remove_html_tags,
            self._remove_urls,
            self._remove_extra_whitespace,
            self._remove_special_characters,
        ]

    def preprocess(self, text: str) -> str:
        """
        Apply preprocessing pipeline to text.

        Args:
            text: Raw text to preprocess

        Returns:
            Preprocessed text

        Raises:
            PreprocessingError: If preprocessing fails
        """
        if not text:
            return ""

        try:
            start_time = time.time()

            result = text
            for stage in self.stages:
                result = stage(result)

            process_time = time.time() - start_time
            embedding_preprocessing_duration_seconds.observe(process_time)

            logger.debug(
                f"Preprocessed text in {process_time:.3f}s "
                f"({len(text)} -> {len(result)} chars)"
            )

            return result

        except Exception as e:
            logger.error(f"Preprocessing failed: {e}")
            raise PreprocessingError(f"Preprocessing failed: {e}")

    def preprocess_batch(self, texts: List[str]) -> List[str]:
        """
        Preprocess a batch of texts.

        Args:
            texts: List of texts to preprocess

        Returns:
            List of preprocessed texts
        """
        return [self.preprocess(text) for text in texts]

    @staticmethod
    def _normalize_unicode(text: str) -> str:
        """Normalize Unicode characters (NFD normalization)."""
        return unicodedata.normalize("NFD", text)

    @staticmethod
    def _remove_html_tags(text: str) -> str:
        """Remove HTML tags."""
        return re.sub(r"<[^>]+>", "", text)

    @staticmethod
    def _remove_urls(text: str) -> str:
        """Remove URLs."""
        return re.sub(
            r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
            "",
            text,
        )

    @staticmethod
    def _remove_extra_whitespace(text: str) -> str:
        """Remove extra whitespace."""
        # Replace multiple spaces with single space
        text = re.sub(r"\s+", " ", text)
        # Strip leading/trailing whitespace
        return text.strip()

    @staticmethod
    def _remove_special_characters(text: str) -> str:
        """Remove special characters but keep punctuation."""
        # Keep alphanumeric, spaces, and common punctuation
        return re.sub(r"[^\w\s\.\,\!\?\-\'\"]", "", text)

