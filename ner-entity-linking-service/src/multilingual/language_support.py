"""Multilingual support for NER Entity Linking Service."""

import logging
from typing import Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class Language(str, Enum):
    """Supported languages."""

    ENGLISH = "en"
    PERSIAN = "fa"
    RUSSIAN = "ru"
    CHINESE = "zh"
    ARABIC = "ar"
    GERMAN = "de"
    FRENCH = "fr"
    SPANISH = "es"
    JAPANESE = "ja"
    KOREAN = "ko"
    ITALIAN = "it"
    PORTUGUESE = "pt"
    TURKISH = "tr"
    HINDI = "hi"


class LanguageSupport:
    """Handles multilingual support and language-specific operations."""

    # Language to NER model mapping
    LANGUAGE_TO_NER_MODEL = {
        Language.ENGLISH: "dslim/bert-base-uncased-finetuned-ner",
        Language.PERSIAN: "HooshvareLab/bert-fa-base-uncased-ner",
        Language.RUSSIAN: "DeepPavlov/rubert-base-cased",
        Language.CHINESE: "hfl/chinese-roberta-wwm-ext",
        Language.ARABIC: "aubmindlab/bert-base-arabertv2",
        Language.GERMAN: "dbmdz/bert-base-german-cased",
        Language.FRENCH: "dbmdz/bert-base-french-cased",
        Language.SPANISH: "dccuchile/bert-base-spanish-wwm-cased",
        Language.JAPANESE: "cl-tohoku/bert-base-japanese-whole-word-masking",
        Language.KOREAN: "kykim/bert-kor-base",
        Language.ITALIAN: "dbmdz/bert-base-italian-cased",
        Language.PORTUGUESE: "neuralmind/bert-base-portuguese-cased",
        Language.TURKISH: "dbmdz/bert-base-turkish-cased",
        Language.HINDI: "ai4bharat/indic-bert",
    }

    # Language to script mapping
    LANGUAGE_TO_SCRIPT = {
        Language.ENGLISH: "Latin",
        Language.PERSIAN: "Arabic",
        Language.RUSSIAN: "Cyrillic",
        Language.CHINESE: "Han",
        Language.ARABIC: "Arabic",
        Language.GERMAN: "Latin",
        Language.FRENCH: "Latin",
        Language.SPANISH: "Latin",
        Language.JAPANESE: "Mixed (Hiragana, Katakana, Kanji)",
        Language.KOREAN: "Hangul",
        Language.ITALIAN: "Latin",
        Language.PORTUGUESE: "Latin",
        Language.TURKISH: "Latin",
        Language.HINDI: "Devanagari",
    }

    # Language to writing direction mapping
    LANGUAGE_TO_DIRECTION = {
        Language.ENGLISH: "LTR",
        Language.PERSIAN: "RTL",
        Language.RUSSIAN: "LTR",
        Language.CHINESE: "LTR",
        Language.ARABIC: "RTL",
        Language.GERMAN: "LTR",
        Language.FRENCH: "LTR",
        Language.SPANISH: "LTR",
        Language.JAPANESE: "LTR",
        Language.KOREAN: "LTR",
        Language.ITALIAN: "LTR",
        Language.PORTUGUESE: "LTR",
        Language.TURKISH: "LTR",
        Language.HINDI: "LTR",
    }

    # Language-specific entity type mappings
    LANGUAGE_ENTITY_TYPES = {
        Language.ENGLISH: ["PERSON", "ORGANIZATION", "LOCATION", "GPE", "DATE", "MONEY"],
        Language.PERSIAN: ["PERSON", "ORGANIZATION", "LOCATION", "GPE"],
        Language.RUSSIAN: ["PERSON", "ORGANIZATION", "LOCATION", "GPE"],
        Language.CHINESE: ["PERSON", "ORGANIZATION", "LOCATION", "GPE"],
        Language.ARABIC: ["PERSON", "ORGANIZATION", "LOCATION", "GPE"],
        Language.GERMAN: ["PERSON", "ORGANIZATION", "LOCATION", "GPE"],
        Language.FRENCH: ["PERSON", "ORGANIZATION", "LOCATION", "GPE"],
        Language.SPANISH: ["PERSON", "ORGANIZATION", "LOCATION", "GPE"],
        Language.JAPANESE: ["PERSON", "ORGANIZATION", "LOCATION", "GPE"],
        Language.KOREAN: ["PERSON", "ORGANIZATION", "LOCATION", "GPE"],
        Language.ITALIAN: ["PERSON", "ORGANIZATION", "LOCATION", "GPE"],
        Language.PORTUGUESE: ["PERSON", "ORGANIZATION", "LOCATION", "GPE"],
        Language.TURKISH: ["PERSON", "ORGANIZATION", "LOCATION", "GPE"],
        Language.HINDI: ["PERSON", "ORGANIZATION", "LOCATION", "GPE"],
    }

    # Language-specific confidence thresholds
    LANGUAGE_CONFIDENCE_THRESHOLDS = {
        Language.ENGLISH: 0.85,
        Language.PERSIAN: 0.80,
        Language.RUSSIAN: 0.82,
        Language.CHINESE: 0.78,
        Language.ARABIC: 0.80,
        Language.GERMAN: 0.85,
        Language.FRENCH: 0.85,
        Language.SPANISH: 0.85,
        Language.JAPANESE: 0.75,
        Language.KOREAN: 0.80,
        Language.ITALIAN: 0.85,
        Language.PORTUGUESE: 0.85,
        Language.TURKISH: 0.82,
        Language.HINDI: 0.75,
    }

    @staticmethod
    def is_supported(language_code: str) -> bool:
        """Check if language is supported.

        Args:
            language_code: Language code (e.g., 'en', 'fa')

        Returns:
            True if language is supported
        """
        try:
            Language(language_code)
            return True
        except ValueError:
            return False

    @staticmethod
    def get_ner_model(language_code: str) -> str:
        """Get NER model for language.

        Args:
            language_code: Language code

        Returns:
            NER model name

        Raises:
            ValueError: If language not supported
        """
        language = Language(language_code)
        return LanguageSupport.LANGUAGE_TO_NER_MODEL[language]

    @staticmethod
    def get_script(language_code: str) -> str:
        """Get script for language.

        Args:
            language_code: Language code

        Returns:
            Script name
        """
        language = Language(language_code)
        return LanguageSupport.LANGUAGE_TO_SCRIPT[language]

    @staticmethod
    def get_direction(language_code: str) -> str:
        """Get writing direction for language.

        Args:
            language_code: Language code

        Returns:
            Direction (LTR or RTL)
        """
        language = Language(language_code)
        return LanguageSupport.LANGUAGE_TO_DIRECTION[language]

    @staticmethod
    def get_entity_types(language_code: str) -> List[str]:
        """Get supported entity types for language.

        Args:
            language_code: Language code

        Returns:
            List of supported entity types
        """
        language = Language(language_code)
        return LanguageSupport.LANGUAGE_ENTITY_TYPES[language]

    @staticmethod
    def get_confidence_threshold(language_code: str) -> float:
        """Get confidence threshold for language.

        Args:
            language_code: Language code

        Returns:
            Confidence threshold (0-1)
        """
        language = Language(language_code)
        return LanguageSupport.LANGUAGE_CONFIDENCE_THRESHOLDS[language]

    @staticmethod
    def normalize_text(text: str, language_code: str) -> str:
        """Normalize text for language.

        Args:
            text: Text to normalize
            language_code: Language code

        Returns:
            Normalized text
        """
        if not LanguageSupport.is_supported(language_code):
            logger.warning(f"Language {language_code} not supported, returning original text")
            return text

        # Basic normalization
        normalized = text.strip()

        # Language-specific normalization
        if language_code == Language.ARABIC:
            # Remove diacritics
            normalized = _remove_arabic_diacritics(normalized)
        elif language_code == Language.PERSIAN:
            # Normalize Persian characters
            normalized = _normalize_persian(normalized)
        elif language_code == Language.CHINESE:
            # Normalize Chinese characters
            normalized = _normalize_chinese(normalized)

        return normalized.lower()

    @staticmethod
    def get_supported_languages() -> List[str]:
        """Get list of supported languages.

        Returns:
            List of language codes
        """
        return [lang.value for lang in Language]

    @staticmethod
    def get_language_info(language_code: str) -> Dict[str, str]:
        """Get comprehensive language information.

        Args:
            language_code: Language code

        Returns:
            Dictionary with language information
        """
        if not LanguageSupport.is_supported(language_code):
            raise ValueError(f"Language {language_code} not supported")

        language = Language(language_code)
        return {
            "code": language.value,
            "name": language.name,
            "ner_model": LanguageSupport.get_ner_model(language_code),
            "script": LanguageSupport.get_script(language_code),
            "direction": LanguageSupport.get_direction(language_code),
            "entity_types": LanguageSupport.get_entity_types(language_code),
            "confidence_threshold": LanguageSupport.get_confidence_threshold(language_code),
        }


def _remove_arabic_diacritics(text: str) -> str:
    """Remove Arabic diacritics.

    Args:
        text: Arabic text

    Returns:
        Text without diacritics
    """
    arabic_diacritics = [
        "\u064B",  # FATHATAN
        "\u064C",  # DAMMATAN
        "\u064D",  # KASRATAN
        "\u064E",  # FATHA
        "\u064F",  # DAMMA
        "\u0650",  # KASRA
        "\u0651",  # SHADDA
        "\u0652",  # SUKUN
    ]
    for diacritic in arabic_diacritics:
        text = text.replace(diacritic, "")
    return text


def _normalize_persian(text: str) -> str:
    """Normalize Persian text.

    Args:
        text: Persian text

    Returns:
        Normalized text
    """
    # Replace Persian digits with Arabic digits
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    arabic_digits = "0123456789"
    for i, digit in enumerate(persian_digits):
        text = text.replace(digit, arabic_digits[i])

    # Normalize Persian characters
    text = text.replace("ی", "ي")  # Normalize Farsi Yeh
    text = text.replace("ک", "ك")  # Normalize Farsi Kaf

    return text


def _normalize_chinese(text: str) -> str:
    """Normalize Chinese text.

    Args:
        text: Chinese text

    Returns:
        Normalized text
    """
    # Convert traditional to simplified (basic mapping)
    # This is a simplified version; full conversion would require more mappings
    return text

