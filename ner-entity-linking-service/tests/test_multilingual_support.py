"""Tests for multilingual support."""

import pytest
from src.multilingual.language_support import Language, LanguageSupport


class TestLanguageEnum:
    """Tests for Language enum."""

    def test_all_languages_defined(self):
        """Test all languages are defined."""
        languages = [
            Language.ENGLISH,
            Language.PERSIAN,
            Language.RUSSIAN,
            Language.CHINESE,
            Language.ARABIC,
            Language.GERMAN,
            Language.FRENCH,
            Language.SPANISH,
            Language.JAPANESE,
            Language.KOREAN,
            Language.ITALIAN,
            Language.PORTUGUESE,
            Language.TURKISH,
            Language.HINDI,
        ]
        assert len(languages) == 14

    def test_language_codes(self):
        """Test language codes."""
        assert Language.ENGLISH.value == "en"
        assert Language.PERSIAN.value == "fa"
        assert Language.RUSSIAN.value == "ru"
        assert Language.CHINESE.value == "zh"
        assert Language.ARABIC.value == "ar"


class TestLanguageSupport:
    """Tests for language support."""

    def test_is_supported_valid_language(self):
        """Test is_supported for valid language."""
        assert LanguageSupport.is_supported("en")
        assert LanguageSupport.is_supported("fa")
        assert LanguageSupport.is_supported("ru")

    def test_is_supported_invalid_language(self):
        """Test is_supported for invalid language."""
        assert not LanguageSupport.is_supported("xx")
        assert not LanguageSupport.is_supported("invalid")

    def test_get_ner_model(self):
        """Test getting NER model for language."""
        model = LanguageSupport.get_ner_model("en")
        assert "bert" in model.lower()
        assert model == "dslim/bert-base-uncased-finetuned-ner"

    def test_get_ner_model_invalid_language(self):
        """Test getting NER model for invalid language."""
        with pytest.raises(ValueError):
            LanguageSupport.get_ner_model("xx")

    def test_get_script(self):
        """Test getting script for language."""
        assert LanguageSupport.get_script("en") == "Latin"
        assert LanguageSupport.get_script("fa") == "Arabic"
        assert LanguageSupport.get_script("ru") == "Cyrillic"
        assert LanguageSupport.get_script("zh") == "Han"
        assert LanguageSupport.get_script("ja") == "Mixed (Hiragana, Katakana, Kanji)"

    def test_get_direction(self):
        """Test getting writing direction for language."""
        assert LanguageSupport.get_direction("en") == "LTR"
        assert LanguageSupport.get_direction("fa") == "RTL"
        assert LanguageSupport.get_direction("ar") == "RTL"

    def test_get_entity_types(self):
        """Test getting entity types for language."""
        entity_types = LanguageSupport.get_entity_types("en")
        assert "PERSON" in entity_types
        assert "ORGANIZATION" in entity_types
        assert "LOCATION" in entity_types

    def test_get_confidence_threshold(self):
        """Test getting confidence threshold for language."""
        threshold = LanguageSupport.get_confidence_threshold("en")
        assert 0.0 <= threshold <= 1.0
        assert threshold == 0.85

    def test_get_confidence_threshold_varies_by_language(self):
        """Test confidence threshold varies by language."""
        en_threshold = LanguageSupport.get_confidence_threshold("en")
        zh_threshold = LanguageSupport.get_confidence_threshold("zh")
        assert en_threshold != zh_threshold

    def test_normalize_text_english(self):
        """Test text normalization for English."""
        text = "  John Smith  "
        normalized = LanguageSupport.normalize_text(text, "en")
        assert normalized == "john smith"

    def test_normalize_text_persian(self):
        """Test text normalization for Persian."""
        text = "علی"
        normalized = LanguageSupport.normalize_text(text, "fa")
        assert isinstance(normalized, str)
        assert len(normalized) > 0

    def test_normalize_text_invalid_language(self):
        """Test text normalization for invalid language."""
        text = "Test"
        normalized = LanguageSupport.normalize_text(text, "xx")
        # For unsupported languages, returns original text (not lowercased)
        assert normalized == "Test"

    def test_get_supported_languages(self):
        """Test getting list of supported languages."""
        languages = LanguageSupport.get_supported_languages()
        assert len(languages) == 14
        assert "en" in languages
        assert "fa" in languages
        assert "ru" in languages

    def test_get_language_info(self):
        """Test getting comprehensive language information."""
        info = LanguageSupport.get_language_info("en")
        assert info["code"] == "en"
        assert info["name"] == "ENGLISH"
        assert "ner_model" in info
        assert "script" in info
        assert "direction" in info
        assert "entity_types" in info
        assert "confidence_threshold" in info

    def test_get_language_info_invalid_language(self):
        """Test getting language info for invalid language."""
        with pytest.raises(ValueError):
            LanguageSupport.get_language_info("xx")

    def test_all_languages_have_ner_models(self):
        """Test all languages have NER models."""
        for language in LanguageSupport.get_supported_languages():
            model = LanguageSupport.get_ner_model(language)
            assert model is not None
            assert len(model) > 0

    def test_all_languages_have_scripts(self):
        """Test all languages have scripts."""
        for language in LanguageSupport.get_supported_languages():
            script = LanguageSupport.get_script(language)
            assert script is not None
            assert len(script) > 0

    def test_all_languages_have_directions(self):
        """Test all languages have directions."""
        for language in LanguageSupport.get_supported_languages():
            direction = LanguageSupport.get_direction(language)
            assert direction in ["LTR", "RTL"]

    def test_all_languages_have_entity_types(self):
        """Test all languages have entity types."""
        for language in LanguageSupport.get_supported_languages():
            entity_types = LanguageSupport.get_entity_types(language)
            assert len(entity_types) > 0
            assert "PERSON" in entity_types

    def test_all_languages_have_confidence_thresholds(self):
        """Test all languages have confidence thresholds."""
        for language in LanguageSupport.get_supported_languages():
            threshold = LanguageSupport.get_confidence_threshold(language)
            assert 0.0 <= threshold <= 1.0


class TestLanguageSpecificFeatures:
    """Tests for language-specific features."""

    def test_rtl_languages(self):
        """Test RTL language detection."""
        rtl_languages = ["fa", "ar"]
        for lang in rtl_languages:
            direction = LanguageSupport.get_direction(lang)
            assert direction == "RTL"

    def test_ltr_languages(self):
        """Test LTR language detection."""
        ltr_languages = ["en", "de", "fr", "es"]
        for lang in ltr_languages:
            direction = LanguageSupport.get_direction(lang)
            assert direction == "LTR"

    def test_non_latin_scripts(self):
        """Test non-Latin script detection."""
        non_latin = {
            "fa": "Arabic",
            "ru": "Cyrillic",
            "zh": "Han",
            "ar": "Arabic",
            "ja": "Mixed (Hiragana, Katakana, Kanji)",
            "ko": "Hangul",
            "hi": "Devanagari",
        }
        for lang, script in non_latin.items():
            assert LanguageSupport.get_script(lang) == script

    def test_language_confidence_thresholds_reasonable(self):
        """Test language confidence thresholds are reasonable."""
        for language in LanguageSupport.get_supported_languages():
            threshold = LanguageSupport.get_confidence_threshold(language)
            # Thresholds should be between 0.7 and 0.9
            assert 0.7 <= threshold <= 0.9

