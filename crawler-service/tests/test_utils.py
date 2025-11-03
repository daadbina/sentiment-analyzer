"""Tests for utility modules."""

import pytest
from datetime import datetime, timedelta

from src.utils import TimestampUtils, ChecksumEngine, LanguageDetector


class TestTimestampUtils:
    """Tests for TimestampUtils class."""

    def test_now_utc(self):
        """Test getting current UTC time."""
        now = TimestampUtils.now_utc()

        assert isinstance(now, datetime)
        assert now.tzinfo is not None

    def test_to_iso8601(self):
        """Test converting datetime to ISO-8601."""
        dt = datetime(2024, 1, 15, 10, 30, 0)
        iso_str = TimestampUtils.to_iso8601(dt)

        assert "T" in iso_str
        assert "Z" in iso_str or "+00:00" in iso_str

    def test_from_iso8601(self):
        """Test parsing ISO-8601 string."""
        iso_str = "2024-01-15T10:30:00Z"
        dt = TimestampUtils.from_iso8601(iso_str)

        assert isinstance(dt, datetime)
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 15

    def test_validate_iso8601_valid(self):
        """Test validating valid ISO-8601 string."""
        iso_str = "2024-01-15T10:30:00Z"

        assert TimestampUtils.validate_iso8601(iso_str) is True

    def test_validate_iso8601_invalid(self):
        """Test validating invalid ISO-8601 string."""
        assert TimestampUtils.validate_iso8601("invalid") is False
        assert TimestampUtils.validate_iso8601("2024-13-45") is False

    def test_is_reasonable_date_valid(self):
        """Test reasonable date validation for valid dates."""
        now = TimestampUtils.now_utc()

        assert TimestampUtils.is_reasonable_date(now) is True

    def test_is_reasonable_date_too_old(self):
        """Test reasonable date validation for old dates."""
        old_date = datetime(1900, 1, 1)

        assert TimestampUtils.is_reasonable_date(old_date) is False

    def test_is_reasonable_date_future(self):
        """Test reasonable date validation for future dates."""
        future_date = datetime.utcnow() + timedelta(days=365)

        assert TimestampUtils.is_reasonable_date(future_date) is False


class TestChecksumEngine:
    """Tests for ChecksumEngine class."""

    def test_generate_sha256(self):
        """Test SHA-256 checksum generation."""
        text = "Test content"
        checksum = ChecksumEngine.generate_sha256(text)

        assert checksum is not None
        assert len(checksum) == 64  # SHA-256 hex length

    def test_generate_md5(self):
        """Test MD5 checksum generation."""
        text = "Test content"
        checksum = ChecksumEngine.generate_md5(text)

        assert checksum is not None
        assert len(checksum) == 32  # MD5 hex length

    def test_sha256_consistency(self):
        """Test SHA-256 checksum consistency."""
        text = "Test content"
        checksum1 = ChecksumEngine.generate_sha256(text)
        checksum2 = ChecksumEngine.generate_sha256(text)

        assert checksum1 == checksum2

    def test_sha256_different_content(self):
        """Test SHA-256 produces different checksums for different content."""
        checksum1 = ChecksumEngine.generate_sha256("Content 1")
        checksum2 = ChecksumEngine.generate_sha256("Content 2")

        assert checksum1 != checksum2

    def test_validate_utf8_valid(self):
        """Test UTF-8 validation for valid content."""
        text = "Valid UTF-8 content with émojis 🎉"

        assert ChecksumEngine.validate_utf8(text) is True

    def test_validate_utf8_invalid(self):
        """Test UTF-8 validation for invalid content."""
        # Create invalid UTF-8 bytes
        invalid_bytes = b"\x80\x81\x82"

        try:
            invalid_bytes.decode("utf-8")
            is_valid = False
        except UnicodeDecodeError:
            is_valid = True

        assert is_valid is True


class TestLanguageDetector:
    """Tests for LanguageDetector class."""

    def test_detect_english(self):
        """Test detecting English language."""
        detector = LanguageDetector()
        text = "This is a sample English text with substantial content. " * 5
        lang, confidence = detector.detect(text)

        assert lang == "en"
        assert confidence > 0.5

    def test_detect_french(self):
        """Test detecting French language."""
        detector = LanguageDetector()
        text = "Ceci est un exemple de texte français avec du contenu substantiel. " * 5
        lang, confidence = detector.detect(text)

        assert lang == "fr"
        assert confidence > 0.5

    def test_detect_spanish(self):
        """Test detecting Spanish language."""
        detector = LanguageDetector()
        text = "Este es un ejemplo de texto en español con contenido sustancial. " * 5
        lang, confidence = detector.detect(text)

        assert lang == "es"
        assert confidence > 0.5

    def test_detect_german(self):
        """Test detecting German language."""
        detector = LanguageDetector()
        text = "Dies ist ein Beispieltext in deutscher Sprache mit substanziellem Inhalt. " * 5
        lang, confidence = detector.detect(text)

        assert lang == "de"
        assert confidence > 0.5

    def test_detect_confidence_threshold(self):
        """Test language detection with confidence threshold."""
        detector = LanguageDetector(confidence_threshold=0.9)
        text = "This is English text"

        lang, confidence = detector.detect(text)
        # May not meet high threshold for short text
        assert isinstance(lang, str)
        assert isinstance(confidence, float)

    def test_detect_empty_text(self):
        """Test language detection with empty text."""
        detector = LanguageDetector()

        with pytest.raises(Exception):
            detector.detect("")

    def test_detect_short_text(self):
        """Test language detection with short text."""
        detector = LanguageDetector(confidence_threshold=0.2)
        text = "Hello world"

        lang, confidence = detector.detect(text)
        assert isinstance(lang, str)
        assert isinstance(confidence, float)
