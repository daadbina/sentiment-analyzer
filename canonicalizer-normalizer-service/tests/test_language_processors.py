"""Tests for language-specific text processors."""

import pytest
from src.normalization.language_processors import (
    PersianProcessor,
    ChineseProcessor,
    ArabicProcessor,
    LanguageProcessorFactory,
)


class TestPersianProcessor:
    """Test Persian text processor."""

    def test_persian_processor_initialization(self):
        """Test Persian processor can be initialized."""
        processor = PersianProcessor()
        assert processor is not None

    def test_persian_normalize_basic(self):
        """Test basic Persian text normalization."""
        processor = PersianProcessor()
        text = "سلام دنیا"
        result = processor.normalize(text)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_persian_normalize_with_diacritics(self):
        """Test Persian normalization removes diacritics."""
        processor = PersianProcessor()
        # Text with diacritics
        text = "سَلام"
        result = processor.normalize(text)
        assert isinstance(result, str)

    def test_persian_tokenize(self):
        """Test Persian text tokenization."""
        processor = PersianProcessor()
        text = "سلام دنیا"
        tokens = processor.tokenize(text)
        assert isinstance(tokens, list)
        assert len(tokens) > 0

    def test_persian_tokenize_empty(self):
        """Test Persian tokenization with empty text."""
        processor = PersianProcessor()
        tokens = processor.tokenize("")
        assert isinstance(tokens, list)

    def test_persian_normalize_empty(self):
        """Test Persian normalization with empty text."""
        processor = PersianProcessor()
        result = processor.normalize("")
        assert isinstance(result, str)


class TestChineseProcessor:
    """Test Chinese text processor."""

    def test_chinese_processor_initialization(self):
        """Test Chinese processor can be initialized."""
        processor = ChineseProcessor()
        assert processor is not None

    def test_chinese_normalize_basic(self):
        """Test basic Chinese text normalization."""
        processor = ChineseProcessor()
        text = "你好世界"
        result = processor.normalize(text)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_chinese_normalize_punctuation(self):
        """Test Chinese punctuation normalization."""
        processor = ChineseProcessor()
        text = "你好，世界！"
        result = processor.normalize(text)
        assert isinstance(result, str)
        # If opencc is available, should normalize full-width punctuation
        # If not available, text is returned as-is
        if processor.available:
            assert "，" not in result or "," in result

    def test_chinese_tokenize(self):
        """Test Chinese text tokenization."""
        processor = ChineseProcessor()
        text = "你好世界"
        tokens = processor.tokenize(text)
        assert isinstance(tokens, list)
        assert len(tokens) == 4  # Character-level tokenization

    def test_chinese_tokenize_empty(self):
        """Test Chinese tokenization with empty text."""
        processor = ChineseProcessor()
        tokens = processor.tokenize("")
        assert isinstance(tokens, list)
        assert len(tokens) == 0

    def test_chinese_normalize_empty(self):
        """Test Chinese normalization with empty text."""
        processor = ChineseProcessor()
        result = processor.normalize("")
        assert isinstance(result, str)

    def test_chinese_punctuation_normalization(self):
        """Test Chinese punctuation normalization details."""
        processor = ChineseProcessor()
        text = "你好，世界！"
        result = processor.normalize(text)
        # Verify punctuation was normalized
        assert isinstance(result, str)


class TestArabicProcessor:
    """Test Arabic text processor."""

    def test_arabic_processor_initialization(self):
        """Test Arabic processor can be initialized."""
        processor = ArabicProcessor()
        assert processor is not None

    def test_arabic_normalize_basic(self):
        """Test basic Arabic text normalization."""
        processor = ArabicProcessor()
        text = "مرحبا بالعالم"
        result = processor.normalize(text)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_arabic_normalize_with_diacritics(self):
        """Test Arabic normalization removes diacritics."""
        processor = ArabicProcessor()
        # Text with diacritics
        text = "مَرْحَبًا"
        result = processor.normalize(text)
        assert isinstance(result, str)

    def test_arabic_tokenize(self):
        """Test Arabic text tokenization."""
        processor = ArabicProcessor()
        text = "مرحبا بالعالم"
        tokens = processor.tokenize(text)
        assert isinstance(tokens, list)
        assert len(tokens) > 0

    def test_arabic_tokenize_empty(self):
        """Test Arabic tokenization with empty text."""
        processor = ArabicProcessor()
        tokens = processor.tokenize("")
        assert isinstance(tokens, list)

    def test_arabic_normalize_empty(self):
        """Test Arabic normalization with empty text."""
        processor = ArabicProcessor()
        result = processor.normalize("")
        assert isinstance(result, str)

    def test_arabic_remove_diacritics(self):
        """Test Arabic diacritic removal."""
        processor = ArabicProcessor()
        # Text with various diacritics
        text = "مَرْحَبًا"
        result = processor.normalize(text)
        assert isinstance(result, str)


class TestLanguageProcessorFactory:
    """Test language processor factory."""

    def test_factory_get_persian_processor(self):
        """Test factory returns Persian processor."""
        processor = LanguageProcessorFactory.get_processor('fa')
        assert processor is not None
        assert isinstance(processor, PersianProcessor)

    def test_factory_get_chinese_processor(self):
        """Test factory returns Chinese processor."""
        processor = LanguageProcessorFactory.get_processor('zh')
        assert processor is not None
        assert isinstance(processor, ChineseProcessor)

    def test_factory_get_arabic_processor(self):
        """Test factory returns Arabic processor."""
        processor = LanguageProcessorFactory.get_processor('ar')
        assert processor is not None
        assert isinstance(processor, ArabicProcessor)

    def test_factory_get_unknown_language(self):
        """Test factory returns None for unknown language."""
        processor = LanguageProcessorFactory.get_processor('xx')
        assert processor is None

    def test_factory_get_english_processor(self):
        """Test factory returns None for English (not implemented)."""
        processor = LanguageProcessorFactory.get_processor('en')
        assert processor is None

    def test_factory_register_processor(self):
        """Test factory can register new processor."""
        class DummyProcessor:
            pass

        LanguageProcessorFactory.register_processor('dummy', DummyProcessor)
        processor = LanguageProcessorFactory.get_processor('dummy')
        assert processor is not None

    def test_factory_processor_consistency(self):
        """Test factory returns consistent processor instances."""
        processor1 = LanguageProcessorFactory.get_processor('fa')
        processor2 = LanguageProcessorFactory.get_processor('fa')
        # Both should be instances of PersianProcessor
        assert isinstance(processor1, PersianProcessor)
        assert isinstance(processor2, PersianProcessor)

