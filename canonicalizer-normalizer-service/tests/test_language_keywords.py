"""Tests for language-specific keyword dictionaries."""

import pytest
from src.classification.language_keywords import (
    PERSIAN_KEYWORDS,
    CHINESE_KEYWORDS,
    ARABIC_KEYWORDS,
    LANGUAGE_KEYWORDS,
    get_keywords_for_language,
    get_all_keywords_for_language,
)


class TestPersianKeywords:
    """Test Persian keyword dictionary."""

    def test_persian_keywords_structure(self):
        """Test Persian keywords have correct structure."""
        assert isinstance(PERSIAN_KEYWORDS, dict)
        assert len(PERSIAN_KEYWORDS) == 8  # 8 domains

    def test_persian_keywords_domains(self):
        """Test Persian keywords contain all domains."""
        expected_domains = {
            'politics', 'economy', 'technology', 'conflict',
            'health', 'environment', 'sports', 'entertainment'
        }
        assert set(PERSIAN_KEYWORDS.keys()) == expected_domains

    def test_persian_keywords_not_empty(self):
        """Test Persian keywords are not empty."""
        for domain, keywords in PERSIAN_KEYWORDS.items():
            assert isinstance(keywords, list)
            assert len(keywords) > 0

    def test_persian_politics_keywords(self):
        """Test Persian politics keywords."""
        keywords = PERSIAN_KEYWORDS['politics']
        assert 'سیاست' in keywords
        assert 'دولت' in keywords
        assert 'انتخابات' in keywords

    def test_persian_economy_keywords(self):
        """Test Persian economy keywords."""
        keywords = PERSIAN_KEYWORDS['economy']
        assert 'اقتصاد' in keywords
        assert 'بازار' in keywords

    def test_persian_technology_keywords(self):
        """Test Persian technology keywords."""
        keywords = PERSIAN_KEYWORDS['technology']
        assert 'فناوری' in keywords
        assert 'کامپیوتر' in keywords


class TestChineseKeywords:
    """Test Chinese keyword dictionary."""

    def test_chinese_keywords_structure(self):
        """Test Chinese keywords have correct structure."""
        assert isinstance(CHINESE_KEYWORDS, dict)
        assert len(CHINESE_KEYWORDS) == 8  # 8 domains

    def test_chinese_keywords_domains(self):
        """Test Chinese keywords contain all domains."""
        expected_domains = {
            'politics', 'economy', 'technology', 'conflict',
            'health', 'environment', 'sports', 'entertainment'
        }
        assert set(CHINESE_KEYWORDS.keys()) == expected_domains

    def test_chinese_keywords_not_empty(self):
        """Test Chinese keywords are not empty."""
        for domain, keywords in CHINESE_KEYWORDS.items():
            assert isinstance(keywords, list)
            assert len(keywords) > 0

    def test_chinese_politics_keywords(self):
        """Test Chinese politics keywords."""
        keywords = CHINESE_KEYWORDS['politics']
        assert '政治' in keywords
        assert '政府' in keywords

    def test_chinese_economy_keywords(self):
        """Test Chinese economy keywords."""
        keywords = CHINESE_KEYWORDS['economy']
        assert '经济' in keywords
        assert '市场' in keywords

    def test_chinese_technology_keywords(self):
        """Test Chinese technology keywords."""
        keywords = CHINESE_KEYWORDS['technology']
        assert '技术' in keywords
        assert '计算机' in keywords


class TestArabicKeywords:
    """Test Arabic keyword dictionary."""

    def test_arabic_keywords_structure(self):
        """Test Arabic keywords have correct structure."""
        assert isinstance(ARABIC_KEYWORDS, dict)
        assert len(ARABIC_KEYWORDS) == 8  # 8 domains

    def test_arabic_keywords_domains(self):
        """Test Arabic keywords contain all domains."""
        expected_domains = {
            'politics', 'economy', 'technology', 'conflict',
            'health', 'environment', 'sports', 'entertainment'
        }
        assert set(ARABIC_KEYWORDS.keys()) == expected_domains

    def test_arabic_keywords_not_empty(self):
        """Test Arabic keywords are not empty."""
        for domain, keywords in ARABIC_KEYWORDS.items():
            assert isinstance(keywords, list)
            assert len(keywords) > 0

    def test_arabic_politics_keywords(self):
        """Test Arabic politics keywords."""
        keywords = ARABIC_KEYWORDS['politics']
        assert 'سياسة' in keywords
        assert 'حكومة' in keywords

    def test_arabic_economy_keywords(self):
        """Test Arabic economy keywords."""
        keywords = ARABIC_KEYWORDS['economy']
        assert 'اقتصاد' in keywords
        assert 'سوق' in keywords

    def test_arabic_technology_keywords(self):
        """Test Arabic technology keywords."""
        keywords = ARABIC_KEYWORDS['technology']
        assert 'تكنولوجيا' in keywords
        assert 'حاسوب' in keywords


class TestLanguageKeywordsMapping:
    """Test language keywords mapping."""

    def test_language_keywords_structure(self):
        """Test language keywords mapping structure."""
        assert isinstance(LANGUAGE_KEYWORDS, dict)
        assert 'fa' in LANGUAGE_KEYWORDS
        assert 'zh' in LANGUAGE_KEYWORDS
        assert 'ar' in LANGUAGE_KEYWORDS

    def test_language_keywords_mapping_values(self):
        """Test language keywords mapping values."""
        assert LANGUAGE_KEYWORDS['fa'] == PERSIAN_KEYWORDS
        assert LANGUAGE_KEYWORDS['zh'] == CHINESE_KEYWORDS
        assert LANGUAGE_KEYWORDS['ar'] == ARABIC_KEYWORDS


class TestGetKeywordsForLanguage:
    """Test get_keywords_for_language function."""

    def test_get_persian_politics_keywords(self):
        """Test getting Persian politics keywords."""
        keywords = get_keywords_for_language('fa', 'politics')
        assert isinstance(keywords, list)
        assert len(keywords) > 0
        assert 'سیاست' in keywords

    def test_get_chinese_economy_keywords(self):
        """Test getting Chinese economy keywords."""
        keywords = get_keywords_for_language('zh', 'economy')
        assert isinstance(keywords, list)
        assert len(keywords) > 0
        assert '经济' in keywords

    def test_get_arabic_technology_keywords(self):
        """Test getting Arabic technology keywords."""
        keywords = get_keywords_for_language('ar', 'technology')
        assert isinstance(keywords, list)
        assert len(keywords) > 0
        assert 'تكنولوجيا' in keywords

    def test_get_keywords_unknown_language(self):
        """Test getting keywords for unknown language."""
        keywords = get_keywords_for_language('xx', 'politics')
        assert isinstance(keywords, list)
        assert len(keywords) == 0

    def test_get_keywords_unknown_domain(self):
        """Test getting keywords for unknown domain."""
        keywords = get_keywords_for_language('fa', 'unknown')
        assert isinstance(keywords, list)
        assert len(keywords) == 0

    def test_get_keywords_all_domains(self):
        """Test getting keywords for all domains."""
        domains = ['politics', 'economy', 'technology', 'conflict',
                   'health', 'environment', 'sports', 'entertainment']
        for domain in domains:
            keywords = get_keywords_for_language('fa', domain)
            assert len(keywords) > 0


class TestGetAllKeywordsForLanguage:
    """Test get_all_keywords_for_language function."""

    def test_get_all_persian_keywords(self):
        """Test getting all Persian keywords."""
        keywords = get_all_keywords_for_language('fa')
        assert isinstance(keywords, dict)
        assert len(keywords) == 8
        assert keywords == PERSIAN_KEYWORDS

    def test_get_all_chinese_keywords(self):
        """Test getting all Chinese keywords."""
        keywords = get_all_keywords_for_language('zh')
        assert isinstance(keywords, dict)
        assert len(keywords) == 8
        assert keywords == CHINESE_KEYWORDS

    def test_get_all_arabic_keywords(self):
        """Test getting all Arabic keywords."""
        keywords = get_all_keywords_for_language('ar')
        assert isinstance(keywords, dict)
        assert len(keywords) == 8
        assert keywords == ARABIC_KEYWORDS

    def test_get_all_keywords_unknown_language(self):
        """Test getting all keywords for unknown language."""
        keywords = get_all_keywords_for_language('xx')
        assert isinstance(keywords, dict)
        assert len(keywords) == 0

    def test_get_all_keywords_structure(self):
        """Test structure of all keywords."""
        for lang_code in ['fa', 'zh', 'ar']:
            keywords = get_all_keywords_for_language(lang_code)
            for domain, words in keywords.items():
                assert isinstance(words, list)
                assert len(words) > 0

