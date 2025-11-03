"""Language detection and support."""

import logging
from typing import Optional, Dict, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LanguageDetectionResult:
    """Result of language detection."""

    language_code: str
    language_name: str
    confidence: float
    is_reliable: bool


class LanguageDetector:
    """Detect language of text."""

    # Supported languages
    SUPPORTED_LANGUAGES = {
        'en': 'English',
        'fa': 'Persian',
        'zh': 'Chinese',
        'ar': 'Arabic',
        'ru': 'Russian',
        'ja': 'Japanese',
        'ko': 'Korean',
        'hi': 'Hindi',
        'es': 'Spanish',
        'fr': 'French',
        'de': 'German',
        'pt': 'Portuguese',
        'it': 'Italian',
        'tr': 'Turkish',
    }

    def __init__(self):
        """Initialize language detector."""
        self.available = False
        self._initialize_detector()

    def _initialize_detector(self) -> None:
        """Initialize language detection library."""
        try:
            from langdetect import detect, detect_langs
            self.detect = detect
            self.detect_langs = detect_langs
            self.available = True
            logger.info("Language detector initialized")
        except ImportError:
            logger.warning("langdetect library not available, language detection disabled")
            self.available = False
        except Exception as e:
            logger.error(f"Error initializing language detector: {e}")
            self.available = False

    def detect_language(self, text: str) -> Optional[LanguageDetectionResult]:
        """Detect language of text.

        Args:
            text: Text to detect language for

        Returns:
            Language detection result or None
        """
        if not self.available or not text or len(text.strip()) < 10:
            return None

        try:
            lang_code = self.detect(text)
            lang_name = self.SUPPORTED_LANGUAGES.get(lang_code, lang_code)

            # Get confidence scores
            try:
                lang_probs = self.detect_langs(text)
                confidence = max([p.prob for p in lang_probs if p.lang == lang_code], default=0.0)
            except Exception:
                confidence = 0.5

            is_reliable = confidence >= 0.8

            return LanguageDetectionResult(
                language_code=lang_code,
                language_name=lang_name,
                confidence=confidence,
                is_reliable=is_reliable,
            )
        except Exception as e:
            logger.warning(f"Error detecting language: {e}")
            return None

    def detect_multiple_languages(self, text: str) -> List[LanguageDetectionResult]:
        """Detect multiple possible languages.

        Args:
            text: Text to detect languages for

        Returns:
            List of language detection results
        """
        if not self.available or not text or len(text.strip()) < 10:
            return []

        try:
            lang_probs = self.detect_langs(text)
            results = []

            for prob in lang_probs:
                lang_code = prob.lang
                lang_name = self.SUPPORTED_LANGUAGES.get(lang_code, lang_code)
                is_reliable = prob.prob >= 0.8

                results.append(LanguageDetectionResult(
                    language_code=lang_code,
                    language_name=lang_name,
                    confidence=prob.prob,
                    is_reliable=is_reliable,
                ))

            return sorted(results, key=lambda x: x.confidence, reverse=True)
        except Exception as e:
            logger.warning(f"Error detecting multiple languages: {e}")
            return []

    @staticmethod
    def is_supported_language(language_code: str) -> bool:
        """Check if language is supported.

        Args:
            language_code: Language code

        Returns:
            True if language is supported
        """
        return language_code in LanguageDetector.SUPPORTED_LANGUAGES

    @staticmethod
    def get_supported_languages() -> Dict[str, str]:
        """Get all supported languages.

        Returns:
            Dictionary of language codes and names
        """
        return LanguageDetector.SUPPORTED_LANGUAGES.copy()


class MultiLanguageProcessor:
    """Process content in multiple languages."""

    def __init__(self, detector: LanguageDetector):
        """Initialize multi-language processor.

        Args:
            detector: Language detector
        """
        self.detector = detector
        self.language_processors = {}

    def register_processor(self, language_code: str, processor) -> None:
        """Register language-specific processor.

        Args:
            language_code: Language code
            processor: Language processor
        """
        self.language_processors[language_code] = processor

    def process(self, text: str) -> Optional[str]:
        """Process text in detected language.

        Args:
            text: Text to process

        Returns:
            Processed text or None
        """
        if not text:
            return None

        # Detect language
        detection = self.detector.detect_language(text)
        if not detection:
            return text

        # Get processor for language
        processor = self.language_processors.get(detection.language_code)
        if not processor:
            return text

        # Process text
        try:
            return processor.normalize(text)
        except Exception as e:
            logger.error(f"Error processing text in {detection.language_code}: {e}")
            return text

    def get_language_info(self, text: str) -> Optional[LanguageDetectionResult]:
        """Get language information for text.

        Args:
            text: Text to analyze

        Returns:
            Language detection result or None
        """
        return self.detector.detect_language(text)

