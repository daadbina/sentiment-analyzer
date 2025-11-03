"""Encoding validation and sanitization."""

import logging
import re
import hashlib
from typing import Tuple, Optional
import chardet

logger = logging.getLogger(__name__)


class EncodingValidator:
    """Validates and sanitizes text encoding."""

    # Control characters to remove (except newline, carriage return, tab)
    CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]")

    # Special character ratio threshold
    MAX_SPECIAL_CHAR_RATIO = 0.05

    @staticmethod
    def detect_encoding(text: bytes) -> Optional[str]:
        """Detect text encoding using chardet.

        Args:
            text: Raw bytes

        Returns:
            Detected encoding or None
        """
        try:
            result = chardet.detect(text)
            if result and result.get("encoding"):
                return result["encoding"]
            return None
        except Exception as e:
            logger.debug(f"Encoding detection failed: {e}")
            return None

    @staticmethod
    def remove_bom(text: str) -> str:
        """Remove BOM markers from text.

        Args:
            text: Text string

        Returns:
            Text without BOM
        """
        # Remove UTF-8 BOM
        if text.startswith("\ufeff"):
            text = text[1:]

        # Remove UTF-16 BOM
        if text.startswith("\ufffe"):
            text = text[1:]

        return text

    @staticmethod
    def remove_control_characters(text: str) -> str:
        """Remove control characters except newline, CR, tab.

        Args:
            text: Text string

        Returns:
            Text with control characters removed
        """
        return EncodingValidator.CONTROL_CHAR_PATTERN.sub("", text)

    @staticmethod
    def calculate_checksum(text: str) -> str:
        """Calculate SHA-256 checksum of text.

        Args:
            text: Text string

        Returns:
            Hex-encoded SHA-256 checksum
        """
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def validate_utf8(text: bytes) -> Tuple[bool, Optional[str]]:
        """Validate UTF-8 encoding.

        Args:
            text: Raw bytes

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            text.decode("utf-8")
            return True, None
        except UnicodeDecodeError as e:
            return False, f"Invalid UTF-8: {e}"

    @staticmethod
    def sanitize_text(text: str) -> str:
        """Sanitize text by removing BOM and control characters.

        Args:
            text: Text string

        Returns:
            Sanitized text
        """
        # Remove BOM
        text = EncodingValidator.remove_bom(text)

        # Remove control characters
        text = EncodingValidator.remove_control_characters(text)

        # Normalize whitespace
        text = " ".join(text.split())

        return text

    @staticmethod
    def validate_and_sanitize(
        raw_text: bytes,
        expected_checksum: Optional[str] = None,
    ) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """Validate and sanitize text encoding.

        Args:
            raw_text: Raw bytes
            expected_checksum: Expected SHA-256 checksum

        Returns:
            Tuple of (is_valid, sanitized_text, detected_encoding, error_message)
        """
        try:
            # Validate UTF-8
            is_valid_utf8, utf8_error = EncodingValidator.validate_utf8(raw_text)
            if not is_valid_utf8:
                # Try to detect and convert
                detected_encoding = EncodingValidator.detect_encoding(raw_text)
                if detected_encoding and detected_encoding.lower() != "utf-8":
                    try:
                        text_str = raw_text.decode(detected_encoding, errors="replace")
                    except Exception:
                        return (
                            False,
                            None,
                            detected_encoding,
                            "Failed to decode with detected encoding",
                        )
                else:
                    # Force UTF-8 with replacement
                    text_str = raw_text.decode("utf-8", errors="replace")
            else:
                text_str = raw_text.decode("utf-8")
                detected_encoding = "utf-8"

            # Sanitize
            sanitized = EncodingValidator.sanitize_text(text_str)

            # Verify checksum if provided
            if expected_checksum:
                calculated_checksum = EncodingValidator.calculate_checksum(sanitized)
                if calculated_checksum != expected_checksum:
                    logger.warning(
                        f"Checksum mismatch: expected {expected_checksum}, got {calculated_checksum}"
                    )
                    # Don't fail on checksum mismatch, just warn

            return True, sanitized, detected_encoding, None

        except Exception as e:
            logger.error(f"Encoding validation error: {e}")
            return False, None, None, str(e)
