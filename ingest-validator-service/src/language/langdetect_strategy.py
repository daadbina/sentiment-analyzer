"""Langdetect-based language detection strategy."""

import logging
from typing import Tuple, Optional

try:
    from langdetect import detect, detect_langs, LangDetectException
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False

logger = logging.getLogger(__name__)


class LangdetectStrategy:
    """Language detection using langdetect library."""

    def __init__(self):
        """Initialize langdetect strategy."""
        self.available = LANGDETECT_AVAILABLE
        if not self.available:
            logger.warning("langdetect not available")

    def detect(self, text: str) -> Tuple[Optional[str], float]:
        """Detect language using langdetect.

        Args:
            text: Text to detect

        Returns:
            Tuple of (language_code, confidence)
        """
        if not self.available or not text:
            return None, 0.0

        try:
            # Get all language probabilities
            langs = detect_langs(text)

            if langs:
                # Get the most probable language
                best_lang = langs[0]
                lang_code = best_lang.lang
                confidence = best_lang.prob

                return lang_code, confidence

            return None, 0.0

        except LangDetectException as e:
            logger.debug(f"Langdetect error: {e}")
            return None, 0.0
        except Exception as e:
            logger.error(f"Langdetect detection error: {e}")
            return None, 0.0

    def is_available(self) -> bool:
        """Check if langdetect is available."""
        return self.available

