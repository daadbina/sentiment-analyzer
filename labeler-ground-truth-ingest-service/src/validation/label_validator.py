"""Label validation module."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple, Optional
from src.config import config
from src.exceptions import ValidationError, FreshnessError
from src.utils.trace import get_logger


logger = get_logger(__name__, config.logging.log_level)


class LabelValidator:
    """Validate label quality and consistency."""

    def __init__(self):
        """Initialize label validator."""
        pass

    def validate_confidence(self, label: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate label confidence score."""
        # Support both 'confidence' and 'label_confidence' field names
        confidence = label.get("label_confidence") or label.get("confidence", 0.0)

        if not isinstance(confidence, (int, float)):
            return False, "Confidence must be numeric"

        if confidence < 0.0 or confidence > 1.0:
            return False, f"Confidence out of range: {confidence}"

        if confidence < config.label.confidence_threshold:
            return False, f"Confidence below threshold: {confidence} < {config.label.confidence_threshold}"

        return True, "Confidence valid"

    def validate_freshness(self, label: Dict[str, Any], source: str) -> Tuple[bool, str]:
        """Validate label freshness (R10)."""
        try:
            from datetime import timezone
            fetched_at_str = label.get("fetched_at", "").replace("Z", "+00:00")
            fetched_at = datetime.fromisoformat(fetched_at_str)

            # Ensure both datetimes are timezone-aware for comparison
            if fetched_at.tzinfo is None:
                fetched_at = fetched_at.replace(tzinfo=timezone.utc)

            now = datetime.now(timezone.utc)
            age_hours = (now - fetched_at).total_seconds() / 3600

            # Check freshness thresholds
            if source == "ACLED":
                threshold = config.label.freshness_acled_hours
            elif source == "GDELT":
                threshold = config.label.freshness_gdelt_hours
            elif source == "CoinGecko":
                threshold = config.label.freshness_coingecko_minutes / 60
            else:
                threshold = 24

            if age_hours > threshold:
                return False, f"Label too old: {age_hours}h > {threshold}h"

            return True, "Freshness valid"

        except Exception as e:
            return False, f"Freshness validation error: {str(e)}"

    def validate_temporal_alignment(
        self,
        label: Dict[str, Any],
        group_created_at: str
    ) -> Tuple[bool, str]:
        """Validate temporal alignment (R8: ≥24h post-cluster)."""
        try:
            label_date = datetime.fromisoformat(label.get("event_date", "").replace("Z", "+00:00"))
            group_date = datetime.fromisoformat(group_created_at.replace("Z", "+00:00"))

            time_diff_hours = (label_date - group_date).total_seconds() / 3600

            if time_diff_hours < config.label.temporal_threshold_hours:
                return False, f"Label too close to cluster creation: {time_diff_hours}h < {config.label.temporal_threshold_hours}h"

            return True, "Temporal alignment valid"

        except Exception as e:
            return False, f"Temporal alignment validation error: {str(e)}"

    def validate_required_fields(self, label: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate required fields."""
        required_fields = [
            "event_id",
            "fetched_at",
            "trace_id"
        ]

        for field in required_fields:
            if field not in label or label[field] is None:
                return False, f"Missing required field: {field}"

        # Check for confidence field (support both 'confidence' and 'label_confidence')
        if not (label.get("label_confidence") or label.get("confidence")):
            return False, "Missing required field: confidence (label_confidence or confidence)"

        return True, "All required fields present"

    def validate_label(
        self,
        label: Dict[str, Any],
        source: str,
        group_created_at: Optional[str] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate label comprehensively.

        Returns:
            Tuple of (valid: bool, errors: List[str])
        """
        errors = []

        # Required fields
        valid, msg = self.validate_required_fields(label)
        if not valid:
            errors.append(msg)

        # Confidence
        valid, msg = self.validate_confidence(label)
        if not valid:
            errors.append(msg)

        # Freshness
        if config.validation.enable_freshness_check:
            valid, msg = self.validate_freshness(label, source)
            if not valid:
                errors.append(msg)

        # Temporal alignment
        if group_created_at:
            valid, msg = self.validate_temporal_alignment(label, group_created_at)
            if not valid:
                errors.append(msg)

        return len(errors) == 0, errors

    async def validate_batch(
        self,
        labels: List[Dict[str, Any]],
        source: str
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Validate batch of labels.

        Returns:
            Tuple of (valid_labels, invalid_labels)
        """
        valid_labels = []
        invalid_labels = []

        for label in labels:
            is_valid, errors = self.validate_label(label, source)

            if is_valid:
                valid_labels.append(label)
            else:
                invalid_labels.append({
                    "label": label,
                    "errors": errors
                })

        logger.info(
            f"Batch validation completed",
            operation="validate_batch",
            source=source,
            total_labels=len(labels),
            valid_labels=len(valid_labels),
            invalid_labels=len(invalid_labels)
        )

        return valid_labels, invalid_labels


class LicenseChecker:
    """Check license compliance."""

    def __init__(self):
        """Initialize license checker."""
        self.license_registry = {
            "ACLED": "CC-BY-4.0",
            "GDELT": "CC-BY-4.0",
            "CoinGecko": "CC-BY-4.0"
        }

    def check_license(self, source: str) -> Tuple[bool, str]:
        """Check license compliance."""
        if source not in self.license_registry:
            return False, f"Unknown source: {source}"

        license_type = self.license_registry[source]
        logger.info(
            f"License check passed",
            operation="check_license",
            source=source,
            license=license_type
        )

        return True, license_type

    async def check_batch(self, sources: List[str]) -> Tuple[List[str], List[str]]:
        """Check licenses for batch of sources."""
        valid_sources = []
        invalid_sources = []

        for source in sources:
            is_valid, license_type = self.check_license(source)
            if is_valid:
                valid_sources.append(source)
            else:
                invalid_sources.append(source)

        return valid_sources, invalid_sources


class FreshnessValidator:
    """Validate label freshness."""

    def __init__(self):
        """Initialize freshness validator."""
        pass

    def get_freshness_threshold(self, source: str) -> float:
        """Get freshness threshold in hours."""
        if source == "ACLED":
            return config.label.freshness_acled_hours
        elif source == "GDELT":
            return config.label.freshness_gdelt_hours
        elif source == "CoinGecko":
            return config.label.freshness_coingecko_minutes / 60
        else:
            return 24

    def check_freshness(self, label: Dict[str, Any], source: str) -> Tuple[bool, float]:
        """Check if label is fresh."""
        try:
            fetched_at = datetime.fromisoformat(label.get("fetched_at", "").replace("Z", "+00:00"))
            now = datetime.utcnow()
            age_hours = (now - fetched_at).total_seconds() / 3600

            threshold = self.get_freshness_threshold(source)

            if age_hours <= threshold:
                return True, age_hours
            else:
                return False, age_hours

        except Exception as e:
            logger.error(
                f"Freshness check failed: {str(e)}",
                operation="check_freshness",
                error_type=type(e).__name__
            )
            return False, 0.0

