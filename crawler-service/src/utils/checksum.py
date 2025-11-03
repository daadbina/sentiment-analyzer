"""
Checksum and encoding utilities.

Provides checksum generation and encoding validation for articles.
"""

import hashlib
import logging

logger = logging.getLogger(__name__)


class ChecksumEngine:
    """
    Generates and validates checksums for article content.

    Ensures data integrity and detects corruption.
    """

    @staticmethod
    def generate_sha256(content: str) -> str:
        """
        Generate SHA-256 checksum for content.

        Args:
            content: Content to checksum.

        Returns:
            str: Hex-encoded SHA-256 checksum.
        """
        if not isinstance(content, str):
            content = str(content)

        # Ensure UTF-8 encoding
        content_bytes = content.encode("utf-8")
        return hashlib.sha256(content_bytes).hexdigest()

    @staticmethod
    def generate_md5(content: str) -> str:
        """
        Generate MD5 checksum for content.

        Args:
            content: Content to checksum.

        Returns:
            str: Hex-encoded MD5 checksum.
        """
        if not isinstance(content, str):
            content = str(content)

        content_bytes = content.encode("utf-8")
        return hashlib.md5(content_bytes, usedforsecurity=False).hexdigest()  # nosec B324

    @staticmethod
    def verify_checksum(content: str, checksum: str, algorithm: str = "sha256") -> bool:
        """
        Verify content against checksum.

        Args:
            content: Content to verify.
            checksum: Expected checksum value.
            algorithm: Hash algorithm (sha256, md5).

        Returns:
            bool: True if checksum matches.
        """
        if algorithm.lower() == "sha256":
            computed = ChecksumEngine.generate_sha256(content)
        elif algorithm.lower() == "md5":
            computed = ChecksumEngine.generate_md5(content)
        else:
            logger.warning(f"Unknown checksum algorithm: {algorithm}")
            return False

        return computed.lower() == checksum.lower()

    @staticmethod
    def validate_utf8(content: bytes | str) -> bool:
        """
        Validate that content is valid UTF-8.

        Args:
            content: Bytes or string to validate.

        Returns:
            bool: True if valid UTF-8.
        """
        try:
            if isinstance(content, str):
                # If already a string, it's valid UTF-8
                content.encode("utf-8")
            else:
                # If bytes, try to decode
                content.decode("utf-8")
            return True
        except (UnicodeDecodeError, UnicodeEncodeError):
            logger.warning("Content is not valid UTF-8")
            return False

    @staticmethod
    def ensure_utf8(content: str) -> str:
        """
        Ensure content is valid UTF-8.

        Removes invalid characters if necessary.

        Args:
            content: Content to ensure UTF-8 for.

        Returns:
            str: Valid UTF-8 content.
        """
        if isinstance(content, bytes):
            try:
                return content.decode("utf-8")
            except UnicodeDecodeError:
                # Replace invalid characters
                return content.decode("utf-8", errors="replace")

        # If already string, encode and decode to ensure validity
        try:
            return content.encode("utf-8").decode("utf-8")
        except UnicodeDecodeError:
            return content.encode("utf-8", errors="replace").decode("utf-8")
