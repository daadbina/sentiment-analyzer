"""Language-specific text processors for content normalization."""

import logging
from typing import Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class LanguageProcessor(ABC):
    """Abstract base class for language-specific text processing."""

    @abstractmethod
    def normalize(self, text: str) -> str:
        """Normalize text for the specific language.

        Args:
            text: Input text to normalize

        Returns:
            Normalized text
        """
        pass

    @abstractmethod
    def tokenize(self, text: str) -> list[str]:
        """Tokenize text for the specific language.

        Args:
            text: Input text to tokenize

        Returns:
            List of tokens
        """
        pass


class PersianProcessor(LanguageProcessor):
    """Persian text processor using hazm library."""

    def __init__(self):
        """Initialize Persian processor."""
        try:
            from hazm import Normalizer, word_tokenize
            self.normalizer = Normalizer()
            self.word_tokenize = word_tokenize
            self.available = True
        except ImportError:
            logger.warning("hazm library not available, Persian processing disabled")
            self.available = False

    def normalize(self, text: str) -> str:
        """Normalize Persian text.

        Removes diacritics, normalizes punctuation, and standardizes characters.

        Args:
            text: Input Persian text

        Returns:
            Normalized text
        """
        if not self.available:
            return text

        try:
            # Normalize using hazm
            normalized = self.normalizer.normalize(text)
            return normalized
        except Exception as e:
            logger.error(f"Error normalizing Persian text: {e}")
            return text

    def tokenize(self, text: str) -> list[str]:
        """Tokenize Persian text.

        Args:
            text: Input Persian text

        Returns:
            List of Persian tokens
        """
        if not self.available:
            return text.split()

        try:
            tokens = self.word_tokenize(text)
            return tokens
        except Exception as e:
            logger.error(f"Error tokenizing Persian text: {e}")
            return text.split()


class ChineseProcessor(LanguageProcessor):
    """Chinese text processor using opencc library."""

    def __init__(self):
        """Initialize Chinese processor."""
        try:
            import opencc
            self.converter = opencc.OpenCC('s2t')  # Simplified to Traditional
            self.available = True
        except ImportError:
            logger.warning("opencc library not available, Chinese processing disabled")
            self.available = False

    def normalize(self, text: str) -> str:
        """Normalize Chinese text.

        Converts simplified to traditional Chinese and normalizes punctuation.

        Args:
            text: Input Chinese text

        Returns:
            Normalized text
        """
        if not self.available:
            return text

        try:
            # Convert simplified to traditional
            normalized = self.converter.convert(text)
            # Normalize punctuation
            normalized = self._normalize_punctuation(normalized)
            return normalized
        except Exception as e:
            logger.error(f"Error normalizing Chinese text: {e}")
            return text

    def tokenize(self, text: str) -> list[str]:
        """Tokenize Chinese text.

        Args:
            text: Input Chinese text

        Returns:
            List of Chinese tokens (characters)
        """
        if not self.available:
            return list(text)

        try:
            # Simple character-level tokenization for Chinese
            tokens = list(text)
            return tokens
        except Exception as e:
            logger.error(f"Error tokenizing Chinese text: {e}")
            return list(text)

    @staticmethod
    def _normalize_punctuation(text: str) -> str:
        """Normalize Chinese punctuation."""
        # Replace full-width punctuation with standard punctuation
        replacements = {
            '，': ',',
            '。': '.',
            '！': '!',
            '？': '?',
            '；': ';',
            '：': ':',
            '（': '(',
            '）': ')',
            '【': '[',
            '】': ']',
            '《': '<',
            '》': '>',
            '"': '"',
            '"': '"',
            ''': "'",
            ''': "'",
        }
        for full_width, standard in replacements.items():
            text = text.replace(full_width, standard)
        return text


class ArabicProcessor(LanguageProcessor):
    """Arabic text processor using pyarabic library."""

    def __init__(self):
        """Initialize Arabic processor."""
        try:
            from arabic_reshaper import reshape
            from bidi.algorithm import get_display
            self.reshape = reshape
            self.get_display = get_display
            self.available = True
        except ImportError:
            logger.warning("pyarabic library not available, Arabic processing disabled")
            self.available = False

    def normalize(self, text: str) -> str:
        """Normalize Arabic text.

        Removes diacritics and normalizes punctuation.

        Args:
            text: Input Arabic text

        Returns:
            Normalized text
        """
        if not self.available:
            return text

        try:
            # Remove Arabic diacritics
            normalized = self._remove_diacritics(text)
            # Normalize punctuation
            normalized = self._normalize_punctuation(normalized)
            return normalized
        except Exception as e:
            logger.error(f"Error normalizing Arabic text: {e}")
            return text

    def tokenize(self, text: str) -> list[str]:
        """Tokenize Arabic text.

        Args:
            text: Input Arabic text

        Returns:
            List of Arabic tokens
        """
        if not self.available:
            return text.split()

        try:
            # Simple space-based tokenization for Arabic
            tokens = text.split()
            return tokens
        except Exception as e:
            logger.error(f"Error tokenizing Arabic text: {e}")
            return text.split()

    @staticmethod
    def _remove_diacritics(text: str) -> str:
        """Remove Arabic diacritical marks."""
        arabic_diacritics = [
            '\u064B',  # FATHATAN
            '\u064C',  # DAMMATAN
            '\u064D',  # KASRATAN
            '\u064E',  # FATHA
            '\u064F',  # DAMMA
            '\u0650',  # KASRA
            '\u0651',  # SHADDA
            '\u0652',  # SUKUN
            '\u0653',  # MADDAH ABOVE
            '\u0654',  # HAMZA ABOVE
            '\u0655',  # HAMZA BELOW
            '\u0656',  # SUBSCRIPT ALEF
            '\u0657',  # INVERTED DAMMA
            '\u0658',  # MARK NOON GHUNNA
            '\u0670',  # SUPERSCRIPT ALEF
        ]
        for diacritic in arabic_diacritics:
            text = text.replace(diacritic, '')
        return text

    @staticmethod
    def _normalize_punctuation(text: str) -> str:
        """Normalize Arabic punctuation."""
        replacements = {
            '؛': ';',
            '،': ',',
            '؟': '?',
            '!': '!',
        }
        for arabic_punct, standard in replacements.items():
            text = text.replace(arabic_punct, standard)
        return text


class LanguageProcessorFactory:
    """Factory for creating language-specific processors."""

    _processors = {
        'fa': PersianProcessor,
        'zh': ChineseProcessor,
        'ar': ArabicProcessor,
    }

    @classmethod
    def get_processor(cls, language_code: str) -> Optional[LanguageProcessor]:
        """Get processor for language code.

        Args:
            language_code: ISO 639-1 language code (e.g., 'fa', 'zh', 'ar')

        Returns:
            Language processor instance or None if not available
        """
        processor_class = cls._processors.get(language_code)
        if processor_class:
            try:
                return processor_class()
            except Exception as e:
                logger.error(f"Error creating processor for {language_code}: {e}")
                return None
        return None

    @classmethod
    def register_processor(cls, language_code: str, processor_class: type) -> None:
        """Register a new language processor.

        Args:
            language_code: ISO 639-1 language code
            processor_class: Processor class
        """
        cls._processors[language_code] = processor_class

