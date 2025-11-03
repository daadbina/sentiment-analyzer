"""Error factory for structured error creation."""

from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ErrorInfo:
    """Error information."""

    code: str
    message: str
    severity: str
    retry_recommended: bool
    category: str


class ErrorRegistry:
    """Registry of known error codes and their metadata."""

    # Error definitions: code -> (message, severity, retry_recommended, category)
    ERRORS: Dict[str, tuple[str, str, bool, str]] = {
        # Timestamp errors (R1)
        "R1_TIMESTAMP_INVALID": (
            "Timestamp validation failed",
            "ERROR",
            True,
            "temporal",
        ),
        "R1_TIMESTAMP_PARSE_ERROR": (
            "Failed to parse timestamp",
            "ERROR",
            True,
            "temporal",
        ),
        "R1_FUTURE_DATE": (
            "Article timestamp is in the future",
            "WARNING",
            False,
            "temporal",
        ),
        # Language detection errors (R2)
        "R2_LANGUAGE_DETECTION_FAILED": (
            "Language detection failed",
            "WARNING",
            True,
            "language",
        ),
        "R2_LOW_CONFIDENCE": (
            "Language detection confidence below threshold",
            "WARNING",
            False,
            "language",
        ),
        # Duplicate detection errors (R3)
        "R3_DUPLICATE_DETECTED": (
            "Article is a duplicate",
            "ERROR",
            False,
            "deduplication",
        ),
        "R3_DEDUP_SERVICE_ERROR": (
            "Deduplication service error",
            "WARNING",
            True,
            "deduplication",
        ),
        # Source verification errors (R6)
        "R6_SOURCE_UNVERIFIED": (
            "Source not in verified registry",
            "ERROR",
            False,
            "source",
        ),
        "R6_SOURCE_BLACKLISTED": (
            "Source is blacklisted",
            "ERROR",
            False,
            "source",
        ),
        # Encoding errors (R9)
        "R9_ENCODING_INVALID": (
            "Invalid UTF-8 encoding",
            "ERROR",
            True,
            "encoding",
        ),
        "R9_CHECKSUM_MISMATCH": (
            "Checksum validation failed",
            "ERROR",
            False,
            "encoding",
        ),
        # Schema errors (R12)
        "R12_SCHEMA_INVALID": (
            "Schema validation failed",
            "ERROR",
            False,
            "schema",
        ),
        "R12_MISSING_FIELD": (
            "Required field missing",
            "ERROR",
            False,
            "schema",
        ),
        # Content quality errors
        "CONTENT_QUALITY_LOW": (
            "Content quality score too low",
            "WARNING",
            False,
            "quality",
        ),
        "CONTENT_TITLE_INVALID": (
            "Title validation failed",
            "WARNING",
            False,
            "quality",
        ),
        "CONTENT_BODY_INVALID": (
            "Body validation failed",
            "WARNING",
            False,
            "quality",
        ),
        # System errors
        "KAFKA_ERROR": (
            "Kafka operation failed",
            "ERROR",
            True,
            "system",
        ),
        "CACHE_ERROR": (
            "Cache operation failed",
            "WARNING",
            True,
            "system",
        ),
        "DATABASE_ERROR": (
            "Database operation failed",
            "ERROR",
            True,
            "system",
        ),
    }

    @classmethod
    def get_error_info(cls, error_code: str) -> ErrorInfo:
        """Get error information by code.

        Args:
            error_code: Error code

        Returns:
            ErrorInfo with metadata
        """
        if error_code not in cls.ERRORS:
            return ErrorInfo(
                code=error_code,
                message="Unknown error",
                severity="ERROR",
                retry_recommended=False,
                category="unknown",
            )

        message, severity, retry_recommended, category = cls.ERRORS[error_code]
        return ErrorInfo(
            code=error_code,
            message=message,
            severity=severity,
            retry_recommended=retry_recommended,
            category=category,
        )


class ErrorFactory:
    """Factory for creating structured error objects."""

    @staticmethod
    def create_error_dict(
        error_code: str,
        details: Optional[Dict[str, Any]] = None,
        article_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create structured error dictionary.

        Args:
            error_code: Error code
            details: Additional error details
            article_id: Article ID if applicable

        Returns:
            Structured error dictionary
        """
        error_info = ErrorRegistry.get_error_info(error_code)

        error_dict = {
            "error_code": error_info.code,
            "message": error_info.message,
            "severity": error_info.severity,
            "category": error_info.category,
            "retry_recommended": error_info.retry_recommended,
        }

        if article_id:
            error_dict["article_id"] = article_id

        if details:
            error_dict["details"] = details

        return error_dict

    @staticmethod
    def create_error_list(
        error_codes: list[str],
        article_id: Optional[str] = None,
    ) -> list[Dict[str, Any]]:
        """Create list of structured errors.

        Args:
            error_codes: List of error codes
            article_id: Article ID if applicable

        Returns:
            List of error dictionaries
        """
        return [
            ErrorFactory.create_error_dict(code, article_id=article_id)
            for code in error_codes
        ]
