"""Smart text truncation strategies."""

import logging
from typing import Tuple

from src.exceptions import TruncationError
from src.metrics import embedding_truncation_rate

logger = logging.getLogger(__name__)


class SmartTruncation:
    """Smart truncation strategies for text."""

    def __init__(self, max_length: int = 384):
        """
        Initialize truncation strategy.

        Args:
            max_length: Maximum length in tokens
        """
        self.max_length = max_length
        self._truncated_count = 0
        self._total_count = 0

    def truncate_by_sentences(
        self,
        text: str,
        max_length: int = None,
    ) -> str:
        """
        Truncate text by sentences to preserve meaning.

        Args:
            text: Text to truncate
            max_length: Maximum length (uses self.max_length if None)

        Returns:
            Truncated text
        """
        if max_length is None:
            max_length = self.max_length

        if len(text) <= max_length:
            return text

        try:
            # Split by sentence boundaries
            sentences = text.replace("! ", "!|").replace("? ", "?|").split("|")

            result = ""
            for sentence in sentences:
                if len(result) + len(sentence) <= max_length:
                    result += sentence
                else:
                    break

            self._truncated_count += 1
            self._total_count += 1

            if result:
                return result.strip()
            else:
                # Fallback to character truncation
                return text[:max_length]

        except Exception as e:
            logger.warning(f"Sentence truncation failed: {e}")
            return text[:max_length]

    def truncate_by_words(
        self,
        text: str,
        max_length: int = None,
    ) -> str:
        """
        Truncate text by words.

        Args:
            text: Text to truncate
            max_length: Maximum length (uses self.max_length if None)

        Returns:
            Truncated text
        """
        if max_length is None:
            max_length = self.max_length

        if len(text) <= max_length:
            return text

        try:
            words = text.split()
            result = ""

            for word in words:
                if len(result) + len(word) + 1 <= max_length:
                    result += word + " "
                else:
                    break

            self._truncated_count += 1
            self._total_count += 1

            return result.strip()

        except Exception as e:
            logger.warning(f"Word truncation failed: {e}")
            return text[:max_length]

    def truncate_by_characters(
        self,
        text: str,
        max_length: int = None,
    ) -> str:
        """
        Truncate text by characters (fallback).

        Args:
            text: Text to truncate
            max_length: Maximum length (uses self.max_length if None)

        Returns:
            Truncated text
        """
        if max_length is None:
            max_length = self.max_length

        if len(text) <= max_length:
            return text

        self._truncated_count += 1
        self._total_count += 1

        return text[:max_length]

    def get_truncation_rate(self) -> float:
        """Get ratio of truncated texts."""
        if self._total_count == 0:
            return 0.0

        rate = self._truncated_count / self._total_count
        embedding_truncation_rate.set(rate)
        return rate

    def reset_stats(self) -> None:
        """Reset truncation statistics."""
        self._truncated_count = 0
        self._total_count = 0

