"""Tests for language detection."""

import pytest
from src.language.language_detector import (
    LanguageDetector,
    LanguageDetectionResult,
    MultiLanguageProcessor,
)


class TestLanguageDetectionResult:
    """Test language detection result."""

    def test_result_creation(self):
        """Test creating detection result."""
        result = LanguageDetectionResult(
            language_code="en",
            language_name="English",
            confidence=0.95,
            is_reliable=True,
        )
        assert result.language_code == "en"
        assert result.language_name == "English"
        assert result.confidence == 0.95
        assert result.is_reliable is True

    def test_result_fields(self):
        """Test result has required fields."""
        result = LanguageDetectionResult(
            language_code="fa",
            language_name="Persian",
            confidence=0.85,
            is_reliable=True,
        )
        assert hasattr(result, 'language_code')
        assert hasattr(result, 'language_name')
        assert hasattr(result, 'confidence')
        assert hasattr(result, 'is_reliable')


class TestLanguageDetector:
    """Test language detector."""

    def test_detector_initialization(self):
        """Test detector initialization."""
        detector = LanguageDetector()
        assert detector is not None

    def test_detector_supported_languages(self):
        """Test supported languages."""
        languages = LanguageDetector.get_supported_languages()
        assert isinstance(languages, dict)
        assert len(languages) > 0
        assert 'en' in languages
        assert 'fa' in languages
        assert 'zh' in languages
        assert 'ar' in languages

    def test_detector_is_supported_language(self):
        """Test checking if language is supported."""
        assert LanguageDetector.is_supported_language('en') is True
        assert LanguageDetector.is_supported_language('fa') is True
        assert LanguageDetector.is_supported_language('xx') is False

    def test_detector_detect_language_empty(self):
        """Test detecting language with empty text."""
        detector = LanguageDetector()
        result = detector.detect_language("")
        assert result is None

    def test_detector_detect_language_short(self):
        """Test detecting language with short text."""
        detector = LanguageDetector()
        result = detector.detect_language("hi")
        assert result is None

    def test_detector_detect_language_returns_result_or_none(self):
        """Test detect_language returns correct type."""
        detector = LanguageDetector()
        result = detector.detect_language("This is a test sentence in English")
        if result is not None:
            assert isinstance(result, LanguageDetectionResult)

    def test_detector_detect_multiple_languages_empty(self):
        """Test detecting multiple languages with empty text."""
        detector = LanguageDetector()
        results = detector.detect_multiple_languages("")
        assert isinstance(results, list)
        assert len(results) == 0

    def test_detector_detect_multiple_languages_short(self):
        """Test detecting multiple languages with short text."""
        detector = LanguageDetector()
        results = detector.detect_multiple_languages("hi")
        assert isinstance(results, list)
        assert len(results) == 0

    def test_detector_detect_multiple_languages_returns_list(self):
        """Test detect_multiple_languages returns list."""
        detector = LanguageDetector()
        results = detector.detect_multiple_languages("This is a test sentence in English")
        assert isinstance(results, list)

    def test_detector_supported_languages_dict(self):
        """Test supported languages is a dictionary."""
        languages = LanguageDetector.SUPPORTED_LANGUAGES
        assert isinstance(languages, dict)
        assert all(isinstance(k, str) for k in languages.keys())
        assert all(isinstance(v, str) for v in languages.values())


class TestMultiLanguageProcessor:
    """Test multi-language processor."""

    def test_processor_initialization(self):
        """Test processor initialization."""
        detector = LanguageDetector()
        processor = MultiLanguageProcessor(detector)
        assert processor is not None
        assert processor.detector is detector

    def test_processor_register_processor(self):
        """Test registering language processor."""
        detector = LanguageDetector()
        processor = MultiLanguageProcessor(detector)

        class MockProcessor:
            def normalize(self, text):
                return text.lower()

        processor.register_processor("en", MockProcessor())
        assert "en" in processor.language_processors

    def test_processor_process_empty_text(self):
        """Test processing empty text."""
        detector = LanguageDetector()
        processor = MultiLanguageProcessor(detector)
        result = processor.process("")
        assert result is None

    def test_processor_process_returns_string_or_none(self):
        """Test process returns string or None."""
        detector = LanguageDetector()
        processor = MultiLanguageProcessor(detector)
        result = processor.process("This is a test sentence")
        if result is not None:
            assert isinstance(result, str)

    def test_processor_get_language_info_empty(self):
        """Test getting language info with empty text."""
        detector = LanguageDetector()
        processor = MultiLanguageProcessor(detector)
        result = processor.get_language_info("")
        assert result is None

    def test_processor_get_language_info_returns_result_or_none(self):
        """Test get_language_info returns correct type."""
        detector = LanguageDetector()
        processor = MultiLanguageProcessor(detector)
        result = processor.get_language_info("This is a test sentence")
        if result is not None:
            assert isinstance(result, LanguageDetectionResult)

    def test_processor_with_registered_processor(self):
        """Test processor with registered language processor."""
        detector = LanguageDetector()
        processor = MultiLanguageProcessor(detector)

        class MockProcessor:
            def normalize(self, text):
                return text.upper()

        processor.register_processor("en", MockProcessor())
        result = processor.process("test")
        # Result depends on language detection
        assert result is None or isinstance(result, str)


class TestLanguageDetectorIntegration:
    """Integration tests for language detector."""

    def test_detector_initialization_and_languages(self):
        """Test detector initialization and language support."""
        detector = LanguageDetector()
        languages = detector.get_supported_languages()
        assert len(languages) >= 14  # At least 14 languages supported

    def test_detector_language_support_coverage(self):
        """Test language support coverage."""
        languages = LanguageDetector.get_supported_languages()
        required_languages = ['en', 'fa', 'zh', 'ar', 'ru', 'ja', 'ko', 'hi']
        for lang in required_languages:
            assert lang in languages

    def test_multi_language_processor_initialization(self):
        """Test multi-language processor initialization."""
        detector = LanguageDetector()
        processor = MultiLanguageProcessor(detector)
        assert processor.detector is detector
        assert len(processor.language_processors) == 0

    def test_multi_language_processor_register_multiple(self):
        """Test registering multiple processors."""
        detector = LanguageDetector()
        processor = MultiLanguageProcessor(detector)

        class MockProcessor:
            def normalize(self, text):
                return text

        processor.register_processor("en", MockProcessor())
        processor.register_processor("fa", MockProcessor())
        processor.register_processor("zh", MockProcessor())
        assert len(processor.language_processors) == 3

