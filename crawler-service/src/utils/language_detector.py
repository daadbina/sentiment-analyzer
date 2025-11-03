"""
Language detection utility.

Detects article language using langdetect and textblob libraries.
"""

import logging
from langdetect import detect, detect_langs, LangDetectException
from textblob import TextBlob

from ..exceptions import LanguageDetectionError
from ..config import get_settings

logger = logging.getLogger(__name__)


class LanguageDetector:
    """
    Detects article language with confidence scoring.

    Uses langdetect as primary detector with textblob as fallback.
    """

    def __init__(self, confidence_threshold: float | None = None) -> None:
        """
        Initialize language detector.

        Args:
            confidence_threshold: Minimum confidence threshold (0.0-1.0).
                                 If None, uses config value.
        """
        self.settings = get_settings()
        self.min_confidence = (
            confidence_threshold
            if confidence_threshold is not None
            else self.settings.lang_conf_threshold
        )

    def detect(self, text: str) -> tuple[str, float]:
        """
        Detect language of text.

        Args:
            text: Text to detect language for.

        Returns:
            tuple[str, float]: (language_code, confidence)

        Raises:
            LanguageDetectionError: If detection fails or confidence too low.
        """
        if not text or not text.strip():
            raise LanguageDetectionError(
                "Cannot detect language of empty text",
                error_code="EMPTY_TEXT",
            )

        # Try langdetect first
        try:
            lang_code = detect(text)
            langs = detect_langs(text)

            # Find confidence for detected language
            confidence = 0.0
            for lang in langs:
                if lang.lang == lang_code:
                    confidence = lang.prob
                    break

            if confidence < self.min_confidence:
                raise LanguageDetectionError(
                    f"Language confidence {confidence:.2f} below threshold "
                    f"{self.min_confidence}",
                    detected_language=lang_code,
                    confidence=confidence,
                    error_code="LOW_CONFIDENCE",
                )

            logger.debug(
                f"Detected language {lang_code} with confidence {confidence:.2f}"
            )
            return lang_code, confidence

        except LangDetectException as e:
            logger.warning(f"langdetect failed: {str(e)}, trying textblob")

        # Fallback to textblob
        try:
            blob = TextBlob(text)
            lang_code = blob.detect_language()

            if not lang_code:
                raise LanguageDetectionError(
                    "TextBlob failed to detect language",
                    error_code="TEXTBLOB_FAILED",
                )

            # TextBlob doesn't provide confidence, assume 0.9
            confidence = 0.9

            logger.debug(
                f"Detected language {lang_code} with textblob "
                f"(confidence: {confidence})"
            )
            return lang_code, confidence

        except Exception as e:
            raise LanguageDetectionError(
                f"Language detection failed: {str(e)}",
                error_code="DETECTION_FAILED",
            )

    def is_supported_language(self, lang_code: str) -> bool:
        """
        Check if language is supported.

        Args:
            lang_code: ISO 639-1 language code.

        Returns:
            bool: True if language is supported.
        """
        # List of supported languages (ISO 639-1 codes)
        supported = {
            "en",  # English
            "es",  # Spanish
            "fr",  # French
            "de",  # German
            "it",  # Italian
            "pt",  # Portuguese
            "ru",  # Russian
            "ja",  # Japanese
            "zh",  # Chinese
            "ar",  # Arabic
            "hi",  # Hindi
            "ko",  # Korean
            "nl",  # Dutch
            "pl",  # Polish
            "tr",  # Turkish
            "vi",  # Vietnamese
            "th",  # Thai
            "id",  # Indonesian
            "sv",  # Swedish
            "no",  # Norwegian
        }
        return lang_code.lower() in supported
