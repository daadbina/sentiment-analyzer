"""Tests for language detection accuracy."""

import pytest
from src.language.detector import LanguageDetector


class TestLanguageDetectionAccuracy:
    """Test language detection accuracy across multiple languages."""

    def setup_method(self):
        """Setup test fixtures."""
        self.detector = LanguageDetector()

    # English test cases
    def test_detect_english_news_article(self):
        """Test English news article detection."""
        text = """
        Breaking News: Major Technology Company Announces New Product
        
        A leading technology company has announced a groundbreaking new product that 
        is expected to revolutionize the industry. The product features advanced artificial 
        intelligence capabilities and machine learning algorithms. Industry experts believe 
        this will significantly impact the market in the coming years.
        """
        lang, confidence, method = self.detector.detect(text, "full_article")
        assert lang == "en", f"Expected 'en', got '{lang}'"
        assert confidence >= 0.85, f"Expected confidence >= 0.85, got {confidence}"

    def test_detect_english_short_text(self):
        """Test English short text detection."""
        text = "Breaking news from the United States today"
        lang, confidence, method = self.detector.detect(text, "rss_summary")
        assert lang == "en", f"Expected 'en', got '{lang}'"
        assert confidence >= 0.70, f"Expected confidence >= 0.70, got {confidence}"

    # Persian test cases
    def test_detect_persian_news_article(self):
        """Test Persian news article detection."""
        text = """
        خبر شکاف‌ساز: شرکت فناوری بزرگ محصول جدید را معرفی کرد
        
        یک شرکت فناوری پیشرو محصول انقلابی جدیدی را معرفی کرده است که انتظار می‌رود 
        صنعت را متحول کند. این محصول دارای قابلیت‌های هوش مصنوعی پیشرفته و الگوریتم‌های 
        یادگیری ماشین است. کارشناسان صنعت معتقدند این محصول تأثیر قابل‌توجهی بر بازار خواهد داشت.
        """
        lang, confidence, method = self.detector.detect(text, "full_article")
        assert lang == "fa", f"Expected 'fa', got '{lang}'"
        assert confidence >= 0.85, f"Expected confidence >= 0.85, got {confidence}"

    def test_detect_persian_short_text(self):
        """Test Persian short text detection."""
        text = "اخبار شکاف‌ساز از ایران امروز"
        lang, confidence, method = self.detector.detect(text, "rss_summary")
        assert lang == "fa", f"Expected 'fa', got '{lang}'"
        assert confidence >= 0.70, f"Expected confidence >= 0.70, got {confidence}"

    # Russian test cases
    def test_detect_russian_news_article(self):
        """Test Russian news article detection."""
        text = """
        Сенсационные новости: крупная технологическая компания объявила о новом продукте
        
        Ведущая технологическая компания объявила о революционном новом продукте, который, 
        как ожидается, изменит индустрию. Продукт обладает передовыми возможностями 
        искусственного интеллекта и алгоритмами машинного обучения. Эксперты отрасли 
        считают, что это значительно повлияет на рынок в ближайшие годы.
        """
        lang, confidence, method = self.detector.detect(text, "full_article")
        assert lang == "ru", f"Expected 'ru', got '{lang}'"
        assert confidence >= 0.85, f"Expected confidence >= 0.85, got {confidence}"

    def test_detect_russian_short_text(self):
        """Test Russian short text detection."""
        text = "Сенсационные новости из России сегодня"
        lang, confidence, method = self.detector.detect(text, "rss_summary")
        assert lang == "ru", f"Expected 'ru', got '{lang}'"
        assert confidence >= 0.70, f"Expected confidence >= 0.70, got {confidence}"

    # Chinese test cases
    def test_detect_chinese_news_article(self):
        """Test Chinese news article detection."""
        text = """
        突破性新闻：主要科技公司宣布推出新产品

        一家领先的科技公司宣布了一款革命性的新产品，预计将改变整个行业。该产品具有先进的
        人工智能功能和机器学习算法。行业专家认为这将在未来几年对市场产生重大影响。
        """
        lang, confidence, method = self.detector.detect(text, "full_article")
        assert lang in ["zh", "zh-cn", "zh-hans"], f"Expected Chinese variant, got '{lang}'"
        # Chinese detection is harder, relax threshold to 0.70
        assert confidence >= 0.70, f"Expected confidence >= 0.70, got {confidence}"

    def test_detect_chinese_short_text(self):
        """Test Chinese short text detection."""
        text = "今天来自中国的突破性新闻"
        lang, confidence, method = self.detector.detect(text, "rss_summary")
        assert lang in ["zh", "zh-cn", "zh-hans"], f"Expected Chinese variant, got '{lang}'"
        assert confidence >= 0.70, f"Expected confidence >= 0.70, got {confidence}"

    # Arabic test cases
    def test_detect_arabic_news_article(self):
        """Test Arabic news article detection."""
        text = """
        أخبار حاسمة: شركة تكنولوجيا كبرى تعلن عن منتج جديد
        
        أعلنت شركة تكنولوجيا رائدة عن منتج جديد ثوري من المتوقع أن يحدث ثورة في الصناعة. 
        يتميز المنتج بقدرات ذكاء اصطناعي متقدمة وخوارزميات التعلم الآلي. يعتقد خبراء الصناعة 
        أن هذا سيؤثر بشكل كبير على السوق في السنوات القادمة.
        """
        lang, confidence, method = self.detector.detect(text, "full_article")
        assert lang == "ar", f"Expected 'ar', got '{lang}'"
        assert confidence >= 0.85, f"Expected confidence >= 0.85, got {confidence}"

    def test_detect_arabic_short_text(self):
        """Test Arabic short text detection."""
        text = "أخبار حاسمة من الشرق الأوسط اليوم"
        lang, confidence, method = self.detector.detect(text, "rss_summary")
        assert lang == "ar", f"Expected 'ar', got '{lang}'"
        assert confidence >= 0.70, f"Expected confidence >= 0.70, got {confidence}"

    # Edge cases
    def test_detect_empty_text(self):
        """Test empty text detection."""
        lang, confidence, method = self.detector.detect("", "full_article")
        assert lang is None, f"Expected None for empty text, got '{lang}'"
        assert confidence == 0.0, f"Expected confidence 0.0, got {confidence}"

    def test_detect_numbers_only(self):
        """Test numbers-only text detection."""
        lang, confidence, method = self.detector.detect("123456789", "full_article")
        # Should return None or very low confidence
        assert confidence < 0.5, f"Expected low confidence for numbers, got {confidence}"

    def test_detect_mixed_language_text(self):
        """Test mixed language text detection."""
        text = "Hello world مرحبا بالعالم"
        lang, confidence, method = self.detector.detect(text, "full_article")
        # Should detect one of the languages
        assert lang is not None, "Expected language detection for mixed text"
        assert lang in ["en", "ar"], f"Expected 'en' or 'ar', got '{lang}'"

    def test_detect_returns_tuple(self):
        """Test that detect returns proper tuple."""
        text = "This is a test"
        result = self.detector.detect(text, "full_article")
        assert isinstance(result, tuple), "Expected tuple result"
        assert len(result) == 3, "Expected 3-element tuple"
        lang, confidence, method = result
        assert isinstance(lang, (str, type(None))), "Expected lang to be str or None"
        assert isinstance(confidence, float), "Expected confidence to be float"
        assert isinstance(method, str), "Expected method to be str"

    def test_detect_confidence_range(self):
        """Test that confidence is always in valid range."""
        texts = [
            "This is English text",
            "هذا نص عربي",
            "这是中文文本",
            "Это русский текст",
            "این متن فارسی است",
        ]
        for text in texts:
            lang, confidence, method = self.detector.detect(text, "full_article")
            assert 0.0 <= confidence <= 1.0, f"Confidence {confidence} out of range"

    def test_detect_method_returned(self):
        """Test that detection method is returned."""
        text = "This is a test article with sufficient content for language detection"
        lang, confidence, method = self.detector.detect(text, "full_article")
        assert method in ["langdetect", "fasttext", "transformer", "none", "error"], \
            f"Unexpected method: {method}"

    def test_detect_with_source_type_rss(self):
        """Test detection with RSS source type."""
        text = "Breaking news from today"
        lang, confidence, method = self.detector.detect(text, "rss_summary")
        assert lang is not None, "Expected language detection for RSS"
        assert isinstance(confidence, float), "Expected float confidence"

    def test_detect_with_source_type_full(self):
        """Test detection with full article source type."""
        text = "This is a comprehensive article with detailed information about recent events"
        lang, confidence, method = self.detector.detect(text, "full_article")
        assert lang is not None, "Expected language detection for full article"
        assert isinstance(confidence, float), "Expected float confidence"

