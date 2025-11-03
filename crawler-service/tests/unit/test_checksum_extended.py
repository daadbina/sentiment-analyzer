"""
Extended unit tests for checksum module.
"""

import pytest
from src.utils.checksum import ChecksumEngine


@pytest.fixture
def engine():
    """Create checksum engine."""
    return ChecksumEngine()


class TestChecksumEngine:
    """Test ChecksumGenerator class."""

    def test_generate_sha256_simple(self, engine):
        """Test SHA256 generation for simple text."""
        text = "Hello, World!"
        checksum = engine.generate_sha256(text)
        
        assert checksum is not None
        assert len(checksum) == 64  # SHA256 hex is 64 chars
        assert isinstance(checksum, str)

    def test_generate_sha256_empty(self, engine):
        """Test SHA256 generation for empty string."""
        checksum = engine.generate_sha256("")

        assert checksum is not None
        assert len(checksum) == 64

    def test_generate_sha256_unicode(self, engine):
        """Test SHA256 generation for unicode text."""
        text = "Hello, 世界! 🌍"
        checksum = engine.generate_sha256(text)

        assert checksum is not None
        assert len(checksum) == 64

    def test_generate_sha256_long_text(self, engine):
        """Test SHA256 generation for long text."""
        text = "x" * 100000
        checksum = engine.generate_sha256(text)

        assert checksum is not None
        assert len(checksum) == 64

    def test_generate_sha256_consistency(self, engine):
        """Test SHA256 consistency."""
        text = "Test content"
        checksum1 = engine.generate_sha256(text)
        checksum2 = engine.generate_sha256(text)

        assert checksum1 == checksum2

    def test_generate_sha256_different_inputs(self, engine):
        """Test SHA256 produces different outputs for different inputs."""
        checksum1 = engine.generate_sha256("text1")
        checksum2 = engine.generate_sha256("text2")

        assert checksum1 != checksum2

    def test_generate_md5_simple(self, engine):
        """Test MD5 generation for simple text."""
        text = "Hello, World!"
        checksum = engine.generate_md5(text)

        assert checksum is not None
        assert len(checksum) == 32  # MD5 hex is 32 chars
        assert isinstance(checksum, str)

    def test_generate_md5_empty(self, engine):
        """Test MD5 generation for empty string."""
        checksum = engine.generate_md5("")

        assert checksum is not None
        assert len(checksum) == 32

    def test_generate_md5_consistency(self, engine):
        """Test MD5 consistency."""
        text = "Test content"
        checksum1 = engine.generate_md5(text)
        checksum2 = engine.generate_md5(text)

        assert checksum1 == checksum2

    def test_generate_md5_different_inputs(self, engine):
        """Test MD5 produces different outputs for different inputs."""
        checksum1 = engine.generate_md5("text1")
        checksum2 = engine.generate_md5("text2")

        assert checksum1 != checksum2

    def test_verify_sha256_valid(self, engine):
        """Test SHA256 verification with valid checksum."""
        text = "Test content"
        checksum = engine.generate_sha256(text)

        is_valid = engine.verify_checksum(text, checksum, "sha256")

        assert is_valid is True

    def test_verify_sha256_invalid(self, engine):
        """Test SHA256 verification with invalid checksum."""
        text = "Test content"
        invalid_checksum = "0" * 64

        is_valid = engine.verify_checksum(text, invalid_checksum, "sha256")

        assert is_valid is False

    def test_verify_md5_valid(self, engine):
        """Test MD5 verification with valid checksum."""
        text = "Test content"
        checksum = engine.generate_md5(text)

        is_valid = engine.verify_checksum(text, checksum, "md5")

        assert is_valid is True

    def test_verify_md5_invalid(self, engine):
        """Test MD5 verification with invalid checksum."""
        text = "Test content"
        invalid_checksum = "0" * 32

        is_valid = engine.verify_checksum(text, invalid_checksum, "md5")

        assert is_valid is False

    def test_generate_sha256_special_chars(self, engine):
        """Test SHA256 with special characters."""
        text = "!@#$%^&*()_+-=[]{}|;:',.<>?/~`"
        checksum = engine.generate_sha256(text)

        assert checksum is not None
        assert len(checksum) == 64

    def test_generate_md5_special_chars(self, engine):
        """Test MD5 with special characters."""
        text = "!@#$%^&*()_+-=[]{}|;:',.<>?/~`"
        checksum = engine.generate_md5(text)

        assert checksum is not None
        assert len(checksum) == 32

    def test_generate_sha256_newlines(self, engine):
        """Test SHA256 with newlines."""
        text = "Line 1\nLine 2\nLine 3"
        checksum = engine.generate_sha256(text)

        assert checksum is not None
        assert len(checksum) == 64

    def test_generate_md5_newlines(self, engine):
        """Test MD5 with newlines."""
        text = "Line 1\nLine 2\nLine 3"
        checksum = engine.generate_md5(text)

        assert checksum is not None
        assert len(checksum) == 32

    def test_generate_sha256_tabs(self, engine):
        """Test SHA256 with tabs."""
        text = "Col1\tCol2\tCol3"
        checksum = engine.generate_sha256(text)

        assert checksum is not None
        assert len(checksum) == 64

    def test_generate_md5_tabs(self, engine):
        """Test MD5 with tabs."""
        text = "Col1\tCol2\tCol3"
        checksum = engine.generate_md5(text)

        assert checksum is not None
        assert len(checksum) == 32

    def test_validate_utf8_string(self, engine):
        """Test UTF-8 validation for string."""
        text = "Hello, World!"
        is_valid = engine.validate_utf8(text)

        assert is_valid is True

    def test_validate_utf8_unicode_string(self, engine):
        """Test UTF-8 validation for unicode string."""
        text = "Hello, 世界! 🌍"
        is_valid = engine.validate_utf8(text)

        assert is_valid is True

    def test_validate_utf8_bytes(self, engine):
        """Test UTF-8 validation for bytes."""
        text = "Hello, World!".encode("utf-8")
        is_valid = engine.validate_utf8(text)

        assert is_valid is True

    def test_ensure_utf8_string(self, engine):
        """Test UTF-8 ensuring for string."""
        text = "Hello, World!"
        result = engine.ensure_utf8(text)

        assert result == text
        assert isinstance(result, str)

    def test_ensure_utf8_unicode_string(self, engine):
        """Test UTF-8 ensuring for unicode string."""
        text = "Hello, 世界! 🌍"
        result = engine.ensure_utf8(text)

        assert result == text
        assert isinstance(result, str)

    def test_ensure_utf8_bytes(self, engine):
        """Test UTF-8 ensuring for bytes."""
        text = "Hello, World!".encode("utf-8")
        result = engine.ensure_utf8(text)

        assert result == "Hello, World!"
        assert isinstance(result, str)

    def test_verify_checksum_unknown_algorithm(self, engine):
        """Test verify_checksum with unknown algorithm."""
        text = "Test content"
        checksum = "somechecksum"

        is_valid = engine.verify_checksum(text, checksum, "unknown")

        assert is_valid is False

    def test_generate_sha256_non_string(self, engine):
        """Test SHA256 generation for non-string input."""
        number = 12345
        checksum = engine.generate_sha256(number)

        assert checksum is not None
        assert len(checksum) == 64

    def test_generate_md5_non_string(self, engine):
        """Test MD5 generation for non-string input."""
        number = 12345
        checksum = engine.generate_md5(number)

        assert checksum is not None
        assert len(checksum) == 32

    def test_validate_utf8_bytes_valid(self, engine):
        """Test UTF-8 validation for valid bytes."""
        text = "Hello, World!".encode("utf-8")
        is_valid = engine.validate_utf8(text)

        assert is_valid is True

    def test_validate_utf8_bytes_invalid(self, engine):
        """Test UTF-8 validation for invalid bytes."""
        # Create invalid UTF-8 bytes
        invalid_bytes = b'\x80\x81\x82'
        is_valid = engine.validate_utf8(invalid_bytes)

        assert is_valid is False

    def test_ensure_utf8_bytes_invalid(self, engine):
        """Test UTF-8 ensuring for invalid bytes."""
        # Create invalid UTF-8 bytes
        invalid_bytes = b'\x80\x81\x82'
        result = engine.ensure_utf8(invalid_bytes)

        assert isinstance(result, str)
        # Should have replacement characters
        assert len(result) > 0

    def test_ensure_utf8_string_with_replacement(self, engine):
        """Test UTF-8 ensuring for string with replacement."""
        # Create a string that when encoded and decoded with errors='replace' changes
        text = "Hello, World!"
        result = engine.ensure_utf8(text)

        assert isinstance(result, str)
        assert result == text
