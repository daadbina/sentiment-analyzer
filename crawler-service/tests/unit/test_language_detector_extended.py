"""
Extended unit tests for language detector module.
"""

import pytest
from unittest.mock import patch, MagicMock
from src.utils.language_detector import LanguageDetector
from src.exceptions import LanguageDetectionError


@pytest.fixture
def detector():
    """Create language detector."""
    return LanguageDetector()


class TestLanguageDetector:
    """Test LanguageDetector class."""

    def test_detect_english(self, detector):
        """Test English language detection."""
        text = "This is a sample English text for language detection."
        lang, confidence = detector.detect(text)
        
        assert lang is not None
        assert confidence is not None
        assert isinstance(confidence, float)
        assert 0 <= confidence <= 1

    def test_detect_spanish(self, detector):
        """Test Spanish language detection."""
        text = "Este es un texto de ejemplo en español para la detección de idioma."
        lang, confidence = detector.detect(text)
        
        assert lang is not None
        assert confidence is not None

    def test_detect_french(self, detector):
        """Test French language detection."""
        text = "Ceci est un exemple de texte en français pour la détection de langue."
        lang, confidence = detector.detect(text)
        
        assert lang is not None
        assert confidence is not None

    def test_detect_german(self, detector):
        """Test German language detection."""
        text = "Dies ist ein Beispieltext in deutscher Sprache zur Spracherkennung."
        lang, confidence = detector.detect(text)
        
        assert lang is not None
        assert confidence is not None

    def test_detect_chinese(self, detector):
        """Test Chinese language detection."""
        text = "这是一个用于语言检测的中文示例文本。"
        lang, confidence = detector.detect(text)
        
        assert lang is not None
        assert confidence is not None

    def test_detect_japanese(self, detector):
        """Test Japanese language detection."""
        text = "これは言語検出のための日本語のサンプルテキストです。"
        lang, confidence = detector.detect(text)
        
        assert lang is not None
        assert confidence is not None

    def test_detect_arabic(self, detector):
        """Test Arabic language detection."""
        text = "هذا نص عينة باللغة العربية لكشف اللغة."
        lang, confidence = detector.detect(text)
        
        assert lang is not None
        assert confidence is not None

    def test_detect_russian(self, detector):
        """Test Russian language detection."""
        text = "Это пример текста на русском языке для определения языка."
        lang, confidence = detector.detect(text)
        
        assert lang is not None
        assert confidence is not None

    def test_detect_portuguese(self, detector):
        """Test Portuguese language detection."""
        text = "Este é um texto de exemplo em português para detecção de idioma."
        lang, confidence = detector.detect(text)
        
        assert lang is not None
        assert confidence is not None

    def test_detect_italian(self, detector):
        """Test Italian language detection."""
        text = "Questo è un testo di esempio in italiano per il rilevamento della lingua."
        lang, confidence = detector.detect(text)
        
        assert lang is not None
        assert confidence is not None

    def test_detect_short_text(self, detector):
        """Test detection with short text."""
        from src.exceptions import LanguageDetectionError
        text = "Hello"

        # Short text may raise LanguageDetectionError
        try:
            lang, confidence = detector.detect(text)
            assert lang is not None
        except LanguageDetectionError:
            pass  # Expected for short text

    def test_detect_empty_text(self, detector):
        """Test detection with empty text."""
        from src.exceptions import LanguageDetectionError
        text = ""

        # Empty text should raise LanguageDetectionError
        with pytest.raises(LanguageDetectionError):
            detector.detect(text)

    def test_detect_numbers_only(self, detector):
        """Test detection with numbers only."""
        from src.exceptions import LanguageDetectionError
        text = "123456789"

        # Numbers only should raise LanguageDetectionError
        with pytest.raises(LanguageDetectionError):
            detector.detect(text)

    def test_detect_mixed_languages(self, detector):
        """Test detection with mixed languages."""
        text = "Hello world 你好 مرحبا"
        try:
            lang, confidence = detector.detect(text)
            # Mixed languages should still return a language
            assert lang is not None
        except LanguageDetectionError:
            # Mixed languages may fail to detect - this is acceptable
            pass

    def test_detect_with_punctuation(self, detector):
        """Test detection with punctuation."""
        text = "Hello, world! How are you? I'm fine, thank you."
        lang, confidence = detector.detect(text)
        
        assert lang is not None
        assert confidence is not None

    def test_detect_with_special_chars(self, detector):
        """Test detection with special characters."""
        text = "Hello @world #test $money %percent"
        lang, confidence = detector.detect(text)
        
        assert lang is not None

    def test_detect_long_text(self, detector):
        """Test detection with long text."""
        text = "This is a long English text. " * 100
        lang, confidence = detector.detect(text)
        
        assert lang is not None
        assert confidence is not None

    def test_detect_consistency(self, detector):
        """Test detection consistency."""
        text = "This is a sample English text for language detection."
        lang1, conf1 = detector.detect(text)
        lang2, conf2 = detector.detect(text)

        assert lang1 == lang2
        # Allow small floating point differences
        assert abs(conf1 - conf2) < 0.01

    def test_detect_case_insensitive(self, detector):
        """Test detection is case insensitive."""
        text_lower = "this is english text"
        text_upper = "THIS IS ENGLISH TEXT"
        
        lang_lower, conf_lower = detector.detect(text_lower)
        lang_upper, conf_upper = detector.detect(text_upper)
        
        assert lang_lower == lang_upper

    def test_detect_with_urls(self, detector):
        """Test detection with URLs."""
        text = "Check out https://example.com for more information about English language."
        lang, confidence = detector.detect(text)
        
        assert lang is not None

    def test_detect_with_emails(self, detector):
        """Test detection with email addresses."""
        text = "Contact us at test@example.com for English language support."
        lang, confidence = detector.detect(text)
        
        assert lang is not None

    def test_detect_with_hashtags(self, detector):
        """Test detection with hashtags."""
        text = "#English #LanguageDetection #Test This is a sample text."
        lang, confidence = detector.detect(text)
        
        assert lang is not None

    def test_detect_with_mentions(self, detector):
        """Test detection with mentions."""
        text = "@user1 @user2 This is an English text for testing."
        lang, confidence = detector.detect(text)
        
        assert lang is not None

    def test_detect_unicode_normalization(self, detector):
        """Test detection with unicode characters."""
        text = "Café résumé naïve"
        lang, confidence = detector.detect(text)
        
        assert lang is not None

    def test_detect_emoji(self, detector):
        """Test detection with emoji."""
        text = "Hello 👋 world 🌍 this is English 😊"
        lang, confidence = detector.detect(text)

        assert lang is not None

    def test_is_supported_language_english(self, detector):
        """Test supported language check for English."""
        assert detector.is_supported_language("en") is True

    def test_is_supported_language_spanish(self, detector):
        """Test supported language check for Spanish."""
        assert detector.is_supported_language("es") is True

    def test_is_supported_language_french(self, detector):
        """Test supported language check for French."""
        assert detector.is_supported_language("fr") is True

    def test_is_supported_language_german(self, detector):
        """Test supported language check for German."""
        assert detector.is_supported_language("de") is True

    def test_is_supported_language_italian(self, detector):
        """Test supported language check for Italian."""
        assert detector.is_supported_language("it") is True

    def test_is_supported_language_portuguese(self, detector):
        """Test supported language check for Portuguese."""
        assert detector.is_supported_language("pt") is True

    def test_is_supported_language_russian(self, detector):
        """Test supported language check for Russian."""
        assert detector.is_supported_language("ru") is True

    def test_is_supported_language_japanese(self, detector):
        """Test supported language check for Japanese."""
        assert detector.is_supported_language("ja") is True

    def test_is_supported_language_chinese(self, detector):
        """Test supported language check for Chinese."""
        assert detector.is_supported_language("zh") is True

    def test_is_supported_language_arabic(self, detector):
        """Test supported language check for Arabic."""
        assert detector.is_supported_language("ar") is True

    def test_is_supported_language_unsupported(self, detector):
        """Test supported language check for unsupported language."""
        assert detector.is_supported_language("xx") is False

    def test_is_supported_language_case_insensitive(self, detector):
        """Test supported language check is case insensitive."""
        assert detector.is_supported_language("EN") is True
        assert detector.is_supported_language("Es") is True
        assert detector.is_supported_language("FR") is True

    def test_detect_with_textblob_fallback(self, detector):
        """Test detection with TextBlob fallback when langdetect fails."""
        from langdetect.lang_detect_exception import LangDetectException

        with patch('src.utils.language_detector.detect') as mock_detect:
            mock_detect.side_effect = LangDetectException(0, "Test error")

            with patch('src.utils.language_detector.TextBlob') as mock_textblob:
                mock_blob = MagicMock()
                mock_blob.detect_language.return_value = "en"
                mock_textblob.return_value = mock_blob

                text = "This is a test text for language detection"
                lang, confidence = detector.detect(text)

                assert lang == "en"
                assert confidence == 0.9

    def test_detect_with_textblob_empty_result(self, detector):
        """Test detection when TextBlob returns empty result."""
        from langdetect.lang_detect_exception import LangDetectException

        with patch('src.utils.language_detector.detect') as mock_detect:
            mock_detect.side_effect = LangDetectException(0, "Test error")

            with patch('src.utils.language_detector.TextBlob') as mock_textblob:
                mock_blob = MagicMock()
                mock_blob.detect_language.return_value = None
                mock_textblob.return_value = mock_blob

                text = "This is a test text"

                with pytest.raises(LanguageDetectionError):
                    detector.detect(text)

    def test_detect_with_all_fallbacks_fail(self, detector):
        """Test detection when all methods fail."""
        from langdetect.lang_detect_exception import LangDetectException

        with patch('src.utils.language_detector.detect') as mock_detect:
            mock_detect.side_effect = LangDetectException(0, "Test error")

            with patch('src.utils.language_detector.TextBlob') as mock_textblob:
                mock_textblob.side_effect = Exception("TextBlob error")

                text = "This is a test text"

                with pytest.raises(LanguageDetectionError):
                    detector.detect(text)

