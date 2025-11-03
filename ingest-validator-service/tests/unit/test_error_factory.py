"""Tests for error factory."""

import pytest
from src.utils.error_factory import ErrorRegistry, ErrorFactory, ErrorInfo


class TestErrorRegistry:
    """Test error registry."""

    def test_get_error_info_timestamp_invalid(self):
        """Test getting timestamp invalid error info."""
        error_info = ErrorRegistry.get_error_info("R1_TIMESTAMP_INVALID")

        assert error_info.code == "R1_TIMESTAMP_INVALID"
        assert error_info.message == "Timestamp validation failed"
        assert error_info.severity == "ERROR"
        assert error_info.retry_recommended is True
        assert error_info.category == "temporal"

    def test_get_error_info_timestamp_parse_error(self):
        """Test getting timestamp parse error info."""
        error_info = ErrorRegistry.get_error_info("R1_TIMESTAMP_PARSE_ERROR")

        assert error_info.code == "R1_TIMESTAMP_PARSE_ERROR"
        assert error_info.message == "Failed to parse timestamp"
        assert error_info.severity == "ERROR"
        assert error_info.retry_recommended is True
        assert error_info.category == "temporal"

    def test_get_error_info_future_date(self):
        """Test getting future date error info."""
        error_info = ErrorRegistry.get_error_info("R1_FUTURE_DATE")

        assert error_info.code == "R1_FUTURE_DATE"
        assert error_info.message == "Article timestamp is in the future"
        assert error_info.severity == "WARNING"
        assert error_info.retry_recommended is False
        assert error_info.category == "temporal"

    def test_get_error_info_language_detection_failed(self):
        """Test getting language detection failed error info."""
        error_info = ErrorRegistry.get_error_info("R2_LANGUAGE_DETECTION_FAILED")

        assert error_info.code == "R2_LANGUAGE_DETECTION_FAILED"
        assert error_info.message == "Language detection failed"
        assert error_info.severity == "WARNING"
        assert error_info.retry_recommended is True
        assert error_info.category == "language"

    def test_get_error_info_low_confidence(self):
        """Test getting low confidence error info."""
        error_info = ErrorRegistry.get_error_info("R2_LOW_CONFIDENCE")

        assert error_info.code == "R2_LOW_CONFIDENCE"
        assert error_info.message == "Language detection confidence below threshold"
        assert error_info.severity == "WARNING"
        assert error_info.retry_recommended is False
        assert error_info.category == "language"

    def test_get_error_info_duplicate_detected(self):
        """Test getting duplicate detected error info."""
        error_info = ErrorRegistry.get_error_info("R3_DUPLICATE_DETECTED")

        assert error_info.code == "R3_DUPLICATE_DETECTED"
        assert error_info.message == "Article is a duplicate"
        assert error_info.severity == "ERROR"
        assert error_info.retry_recommended is False
        assert error_info.category == "deduplication"

    def test_get_error_info_dedup_service_error(self):
        """Test getting dedup service error info."""
        error_info = ErrorRegistry.get_error_info("R3_DEDUP_SERVICE_ERROR")

        assert error_info.code == "R3_DEDUP_SERVICE_ERROR"
        assert error_info.message == "Deduplication service error"
        assert error_info.severity == "WARNING"
        assert error_info.retry_recommended is True
        assert error_info.category == "deduplication"

    def test_get_error_info_source_unverified(self):
        """Test getting source unverified error info."""
        error_info = ErrorRegistry.get_error_info("R6_SOURCE_UNVERIFIED")

        assert error_info.code == "R6_SOURCE_UNVERIFIED"
        assert error_info.message == "Source not in verified registry"
        assert error_info.severity == "ERROR"
        assert error_info.retry_recommended is False
        assert error_info.category == "source"

    def test_get_error_info_source_blacklisted(self):
        """Test getting source blacklisted error info."""
        error_info = ErrorRegistry.get_error_info("R6_SOURCE_BLACKLISTED")

        assert error_info.code == "R6_SOURCE_BLACKLISTED"
        assert error_info.message == "Source is blacklisted"
        assert error_info.severity == "ERROR"
        assert error_info.retry_recommended is False
        assert error_info.category == "source"

    def test_get_error_info_encoding_invalid(self):
        """Test getting encoding invalid error info."""
        error_info = ErrorRegistry.get_error_info("R9_ENCODING_INVALID")

        assert error_info.code == "R9_ENCODING_INVALID"
        assert error_info.message == "Invalid UTF-8 encoding"
        assert error_info.severity == "ERROR"
        assert error_info.retry_recommended is True
        assert error_info.category == "encoding"

    def test_get_error_info_checksum_mismatch(self):
        """Test getting checksum mismatch error info."""
        error_info = ErrorRegistry.get_error_info("R9_CHECKSUM_MISMATCH")

        assert error_info.code == "R9_CHECKSUM_MISMATCH"
        assert error_info.message == "Checksum validation failed"
        assert error_info.severity == "ERROR"
        assert error_info.retry_recommended is False
        assert error_info.category == "encoding"

    def test_get_error_info_schema_invalid(self):
        """Test getting schema invalid error info."""
        error_info = ErrorRegistry.get_error_info("R12_SCHEMA_INVALID")

        assert error_info.code == "R12_SCHEMA_INVALID"
        assert error_info.message == "Schema validation failed"
        assert error_info.severity == "ERROR"
        assert error_info.retry_recommended is False
        assert error_info.category == "schema"

    def test_get_error_info_missing_field(self):
        """Test getting missing field error info."""
        error_info = ErrorRegistry.get_error_info("R12_MISSING_FIELD")

        assert error_info.code == "R12_MISSING_FIELD"
        assert error_info.message == "Required field missing"
        assert error_info.severity == "ERROR"
        assert error_info.retry_recommended is False
        assert error_info.category == "schema"

    def test_get_error_info_content_quality_low(self):
        """Test getting content quality low error info."""
        error_info = ErrorRegistry.get_error_info("CONTENT_QUALITY_LOW")

        assert error_info.code == "CONTENT_QUALITY_LOW"
        assert error_info.message == "Content quality score too low"
        assert error_info.severity == "WARNING"
        assert error_info.retry_recommended is False
        assert error_info.category == "quality"

    def test_get_error_info_content_title_invalid(self):
        """Test getting content title invalid error info."""
        error_info = ErrorRegistry.get_error_info("CONTENT_TITLE_INVALID")

        assert error_info.code == "CONTENT_TITLE_INVALID"
        assert error_info.message == "Title validation failed"
        assert error_info.severity == "WARNING"
        assert error_info.retry_recommended is False
        assert error_info.category == "quality"

    def test_get_error_info_content_body_invalid(self):
        """Test getting content body invalid error info."""
        error_info = ErrorRegistry.get_error_info("CONTENT_BODY_INVALID")

        assert error_info.code == "CONTENT_BODY_INVALID"
        assert error_info.message == "Body validation failed"
        assert error_info.severity == "WARNING"
        assert error_info.retry_recommended is False
        assert error_info.category == "quality"

    def test_get_error_info_kafka_error(self):
        """Test getting Kafka error info."""
        error_info = ErrorRegistry.get_error_info("KAFKA_ERROR")

        assert error_info.code == "KAFKA_ERROR"
        assert error_info.message == "Kafka operation failed"
        assert error_info.severity == "ERROR"
        assert error_info.retry_recommended is True
        assert error_info.category == "system"

    def test_get_error_info_cache_error(self):
        """Test getting cache error info."""
        error_info = ErrorRegistry.get_error_info("CACHE_ERROR")

        assert error_info.code == "CACHE_ERROR"
        assert error_info.message == "Cache operation failed"
        assert error_info.severity == "WARNING"
        assert error_info.retry_recommended is True
        assert error_info.category == "system"

    def test_get_error_info_database_error(self):
        """Test getting database error info."""
        error_info = ErrorRegistry.get_error_info("DATABASE_ERROR")

        assert error_info.code == "DATABASE_ERROR"
        assert error_info.message == "Database operation failed"
        assert error_info.severity == "ERROR"
        assert error_info.retry_recommended is True
        assert error_info.category == "system"

    def test_get_error_info_unknown_error(self):
        """Test getting unknown error info."""
        error_info = ErrorRegistry.get_error_info("UNKNOWN_ERROR_CODE")

        assert error_info.code == "UNKNOWN_ERROR_CODE"
        assert error_info.message == "Unknown error"
        assert error_info.severity == "ERROR"
        assert error_info.retry_recommended is False
        assert error_info.category == "unknown"


class TestErrorFactory:
    """Test error factory."""

    def test_create_error_dict_basic(self):
        """Test creating basic error dictionary."""
        error_dict = ErrorFactory.create_error_dict("R1_TIMESTAMP_INVALID")

        assert error_dict["error_code"] == "R1_TIMESTAMP_INVALID"
        assert error_dict["message"] == "Timestamp validation failed"
        assert error_dict["severity"] == "ERROR"
        assert error_dict["category"] == "temporal"
        assert error_dict["retry_recommended"] is True

    def test_create_error_dict_with_article_id(self):
        """Test creating error dictionary with article ID."""
        error_dict = ErrorFactory.create_error_dict(
            "R1_TIMESTAMP_INVALID",
            article_id="art_123",
        )

        assert error_dict["error_code"] == "R1_TIMESTAMP_INVALID"
        assert error_dict["article_id"] == "art_123"

    def test_create_error_dict_with_details(self):
        """Test creating error dictionary with details."""
        details = {"timestamp": "2025-11-03T10:00:00Z", "reason": "Future date"}
        error_dict = ErrorFactory.create_error_dict(
            "R1_FUTURE_DATE",
            details=details,
        )

        assert error_dict["error_code"] == "R1_FUTURE_DATE"
        assert error_dict["details"] == details

    def test_create_error_dict_with_all_params(self):
        """Test creating error dictionary with all parameters."""
        details = {"timestamp": "2025-11-03T10:00:00Z"}
        error_dict = ErrorFactory.create_error_dict(
            "R1_TIMESTAMP_INVALID",
            details=details,
            article_id="art_123",
        )

        assert error_dict["error_code"] == "R1_TIMESTAMP_INVALID"
        assert error_dict["article_id"] == "art_123"
        assert error_dict["details"] == details

    def test_create_error_dict_unknown_code(self):
        """Test creating error dictionary with unknown code."""
        error_dict = ErrorFactory.create_error_dict("UNKNOWN_CODE")

        assert error_dict["error_code"] == "UNKNOWN_CODE"
        assert error_dict["message"] == "Unknown error"
        assert error_dict["severity"] == "ERROR"

    def test_create_error_list_single_error(self):
        """Test creating error list with single error."""
        error_list = ErrorFactory.create_error_list(["R1_TIMESTAMP_INVALID"])

        assert len(error_list) == 1
        assert error_list[0]["error_code"] == "R1_TIMESTAMP_INVALID"

    def test_create_error_list_multiple_errors(self):
        """Test creating error list with multiple errors."""
        error_codes = [
            "R1_TIMESTAMP_INVALID",
            "R2_LANGUAGE_DETECTION_FAILED",
            "R3_DUPLICATE_DETECTED",
        ]
        error_list = ErrorFactory.create_error_list(error_codes)

        assert len(error_list) == 3
        assert error_list[0]["error_code"] == "R1_TIMESTAMP_INVALID"
        assert error_list[1]["error_code"] == "R2_LANGUAGE_DETECTION_FAILED"
        assert error_list[2]["error_code"] == "R3_DUPLICATE_DETECTED"

    def test_create_error_list_with_article_id(self):
        """Test creating error list with article ID."""
        error_codes = ["R1_TIMESTAMP_INVALID", "R2_LANGUAGE_DETECTION_FAILED"]
        error_list = ErrorFactory.create_error_list(
            error_codes,
            article_id="art_123",
        )

        assert len(error_list) == 2
        assert error_list[0]["article_id"] == "art_123"
        assert error_list[1]["article_id"] == "art_123"

    def test_create_error_list_empty(self):
        """Test creating error list with empty list."""
        error_list = ErrorFactory.create_error_list([])

        assert len(error_list) == 0

    def test_error_info_dataclass(self):
        """Test ErrorInfo dataclass."""
        error_info = ErrorInfo(
            code="TEST_CODE",
            message="Test message",
            severity="ERROR",
            retry_recommended=True,
            category="test",
        )

        assert error_info.code == "TEST_CODE"
        assert error_info.message == "Test message"
        assert error_info.severity == "ERROR"
        assert error_info.retry_recommended is True
        assert error_info.category == "test"

    def test_create_error_dict_multiple_calls(self):
        """Test creating multiple error dictionaries."""
        error_dict1 = ErrorFactory.create_error_dict("R1_TIMESTAMP_INVALID")
        error_dict2 = ErrorFactory.create_error_dict("R2_LANGUAGE_DETECTION_FAILED")

        assert error_dict1["error_code"] == "R1_TIMESTAMP_INVALID"
        assert error_dict2["error_code"] == "R2_LANGUAGE_DETECTION_FAILED"
        assert error_dict1 != error_dict2

    def test_error_registry_all_codes_valid(self):
        """Test that all error codes in registry are valid."""
        for error_code in ErrorRegistry.ERRORS.keys():
            error_info = ErrorRegistry.get_error_info(error_code)
            assert error_info.code == error_code
            assert error_info.message is not None
            assert error_info.severity in ["ERROR", "WARNING"]
            assert isinstance(error_info.retry_recommended, bool)
            assert error_info.category is not None

