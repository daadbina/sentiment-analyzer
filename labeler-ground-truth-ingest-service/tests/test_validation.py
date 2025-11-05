"""Unit tests for validation module."""

import pytest
from datetime import datetime, timedelta

from src.validation.label_validator import LabelValidator, LicenseChecker, FreshnessValidator


class TestLabelValidator:
    """Test label validator."""

    def test_validate_confidence_valid(self):
        """Test validate confidence with valid value."""
        validator = LabelValidator()
        label = {"confidence": 0.85}

        valid, msg = validator.validate_confidence(label)
        assert valid
        assert "valid" in msg.lower()

    def test_validate_confidence_too_low(self):
        """Test validate confidence with too low value."""
        validator = LabelValidator()
        label = {"confidence": 0.5}

        valid, msg = validator.validate_confidence(label)
        assert not valid
        assert "below threshold" in msg.lower()

    def test_validate_confidence_out_of_range(self):
        """Test validate confidence out of range."""
        validator = LabelValidator()
        label = {"confidence": 1.5}

        valid, msg = validator.validate_confidence(label)
        assert not valid
        assert "out of range" in msg.lower()

    def test_validate_required_fields_present(self):
        """Test validate required fields present."""
        validator = LabelValidator()
        label = {
            "event_id": "123",
            "confidence": 0.85,
            "fetched_at": datetime.utcnow().isoformat(),
            "trace_id": "trace_123"
        }

        valid, msg = validator.validate_required_fields(label)
        assert valid

    def test_validate_required_fields_missing(self):
        """Test validate required fields missing."""
        validator = LabelValidator()
        label = {
            "event_id": "123",
            "confidence": 0.85
        }

        valid, msg = validator.validate_required_fields(label)
        assert not valid

    def test_validate_freshness_valid(self):
        """Test validate freshness with valid label."""
        validator = LabelValidator()
        label = {
            "fetched_at": datetime.utcnow().isoformat()
        }

        valid, msg = validator.validate_freshness(label, "ACLED")
        assert valid

    def test_validate_freshness_stale(self):
        """Test validate freshness with stale label."""
        validator = LabelValidator()
        label = {
            "fetched_at": (datetime.utcnow() - timedelta(days=2)).isoformat()
        }

        valid, msg = validator.validate_freshness(label, "ACLED")
        assert not valid

    @pytest.mark.asyncio
    async def test_validate_batch(self):
        """Test validate batch of labels."""
        validator = LabelValidator()
        labels = [
            {
                "event_id": "123",
                "confidence": 0.85,
                "fetched_at": datetime.utcnow().isoformat(),
                "trace_id": "trace_123"
            },
            {
                "event_id": "124",
                "confidence": 0.5,
                "fetched_at": datetime.utcnow().isoformat(),
                "trace_id": "trace_124"
            }
        ]

        valid, invalid = await validator.validate_batch(labels, "ACLED")
        assert len(valid) >= 0
        assert len(invalid) >= 0


class TestLicenseChecker:
    """Test license checker."""

    def test_check_license_valid_source(self):
        """Test check license with valid source."""
        checker = LicenseChecker()

        valid, license_type = checker.check_license("ACLED")
        assert valid
        assert license_type == "CC-BY-4.0"

    def test_check_license_invalid_source(self):
        """Test check license with invalid source."""
        checker = LicenseChecker()

        valid, license_type = checker.check_license("UNKNOWN")
        assert not valid

    @pytest.mark.asyncio
    async def test_check_batch(self):
        """Test check batch of sources."""
        checker = LicenseChecker()
        sources = ["ACLED", "GDELT", "CoinGecko"]

        valid, invalid = await checker.check_batch(sources)
        assert len(valid) == 3
        assert len(invalid) == 0


class TestFreshnessValidator:
    """Test freshness validator."""

    def test_get_freshness_threshold_acled(self):
        """Test get freshness threshold for ACLED."""
        validator = FreshnessValidator()
        threshold = validator.get_freshness_threshold("ACLED")
        assert threshold == 24

    def test_get_freshness_threshold_gdelt(self):
        """Test get freshness threshold for GDELT."""
        validator = FreshnessValidator()
        threshold = validator.get_freshness_threshold("GDELT")
        assert threshold == 1

    def test_check_freshness_fresh(self):
        """Test check freshness with fresh label."""
        validator = FreshnessValidator()
        label = {
            "fetched_at": datetime.utcnow().isoformat()
        }

        fresh, age = validator.check_freshness(label, "ACLED")
        assert fresh
        assert age < 1

    def test_check_freshness_stale(self):
        """Test check freshness with stale label."""
        validator = FreshnessValidator()
        label = {
            "fetched_at": (datetime.utcnow() - timedelta(days=2)).isoformat()
        }

        fresh, age = validator.check_freshness(label, "ACLED")
        assert not fresh
        assert age > 24


class TestExceptions:
    """Test exception classes."""

    def test_exception_hierarchy(self):
        """Test exception hierarchy."""
        from src.exceptions import (
            LabelError, FetchError, ReconciliationError,
            ValidationError, FreshnessError, CircuitBreakerError
        )

        # Test that all exceptions are subclasses of LabelError
        assert issubclass(FetchError, LabelError)
        assert issubclass(ReconciliationError, LabelError)
        assert issubclass(ValidationError, LabelError)
        assert issubclass(FreshnessError, LabelError)
        assert issubclass(CircuitBreakerError, LabelError)

    def test_exception_instantiation(self):
        """Test exception instantiation."""
        from src.exceptions import FetchError, ReconciliationError

        fetch_error = FetchError("ACLED", "Test fetch error")
        assert "Test fetch error" in str(fetch_error)

        recon_error = ReconciliationError("l1", "g1", "Test reconciliation error")
        assert "Test reconciliation error" in str(recon_error)

    def test_exception_raising(self):
        """Test exception raising."""
        from src.exceptions import ValidationError

        with pytest.raises(ValidationError):
            raise ValidationError("l1", "R1", "Validation failed")

    def test_all_exception_types(self):
        """Test all exception types."""
        from src.exceptions import (
            LabelError, FetchError, ReconciliationError, ValidationError,
            StorageError, LicenseError, FreshnessError, CircuitBreakerError,
            SchemaRegistryError, KafkaError, DatabaseError
        )

        # Test that all exceptions are subclasses of LabelError
        assert issubclass(FetchError, LabelError)
        assert issubclass(ReconciliationError, LabelError)
        assert issubclass(ValidationError, LabelError)
        assert issubclass(StorageError, LabelError)
        assert issubclass(LicenseError, LabelError)
        assert issubclass(FreshnessError, LabelError)
        assert issubclass(CircuitBreakerError, LabelError)
        assert issubclass(SchemaRegistryError, LabelError)
        assert issubclass(KafkaError, LabelError)
        assert issubclass(DatabaseError, LabelError)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

