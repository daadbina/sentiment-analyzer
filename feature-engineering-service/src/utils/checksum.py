"""Feature versioning and checksum utilities."""

import hashlib
import json
from typing import Any, Dict
from datetime import datetime


def compute_checksum(data: Any) -> str:
    """Compute SHA256 checksum of data.

    Args:
        data: Data to checksum (dict, list, or string)

    Returns:
        Hex-encoded SHA256 checksum
    """
    if isinstance(data, dict):
        # Sort keys for consistent hashing
        json_str = json.dumps(data, sort_keys=True, default=str)
    elif isinstance(data, (list, tuple)):
        json_str = json.dumps(data, default=str)
    else:
        json_str = str(data)

    return hashlib.sha256(json_str.encode()).hexdigest()


def compute_feature_checksum(features: Dict[str, Any]) -> str:
    """Compute checksum for feature set.

    Args:
        features: Dictionary of feature name -> value

    Returns:
        Hex-encoded SHA256 checksum
    """
    # Sort features by name for consistent hashing
    sorted_features = {k: features[k] for k in sorted(features.keys())}
    return compute_checksum(sorted_features)


def compute_group_checksum(group_id: str, article_ids: list) -> str:
    """Compute checksum for semantic group.

    Args:
        group_id: Group identifier
        article_ids: List of article IDs in group

    Returns:
        Hex-encoded SHA256 checksum
    """
    data = {
        "group_id": group_id,
        "article_ids": sorted(article_ids),
    }
    return compute_checksum(data)


class FeatureVersion:
    """Feature version tracking."""

    def __init__(
        self,
        version: str,
        feature_names: list,
        computation_timestamp: datetime,
    ):
        """Initialize feature version.

        Args:
            version: Version string (e.g., 'v1.0')
            feature_names: List of feature names
            computation_timestamp: When features were computed
        """
        self.version = version
        self.feature_names = sorted(feature_names)
        self.computation_timestamp = computation_timestamp
        self.checksum = self._compute_version_checksum()

    def _compute_version_checksum(self) -> str:
        """Compute version checksum."""
        data = {
            "version": self.version,
            "feature_names": self.feature_names,
            "timestamp": self.computation_timestamp.isoformat(),
        }
        return compute_checksum(data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "version": self.version,
            "feature_names": self.feature_names,
            "computation_timestamp": self.computation_timestamp.isoformat(),
            "checksum": self.checksum,
        }

    def __eq__(self, other):
        """Check equality."""
        if not isinstance(other, FeatureVersion):
            return False
        return self.checksum == other.checksum

    def __hash__(self):
        """Hash version."""
        return hash(self.checksum)


class FeatureLineage:
    """Track feature computation lineage."""

    def __init__(self, group_id: str, trace_id: str):
        """Initialize lineage tracker.

        Args:
            group_id: Semantic group ID
            trace_id: Trace ID for correlation
        """
        self.group_id = group_id
        self.trace_id = trace_id
        self.created_at = datetime.utcnow()
        self.extractors_used: list = []
        self.transformations_applied: list = []
        self.validations_passed: list = []
        self.feature_checksums: Dict[str, str] = {}

    def add_extractor(self, extractor_name: str):
        """Record extractor usage."""
        self.extractors_used.append(extractor_name)

    def add_transformation(self, transformation_name: str):
        """Record transformation."""
        self.transformations_applied.append(transformation_name)

    def add_validation(self, validation_name: str):
        """Record validation."""
        self.validations_passed.append(validation_name)

    def add_feature_checksum(self, feature_name: str, checksum: str):
        """Record feature checksum."""
        self.feature_checksums[feature_name] = checksum

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "group_id": self.group_id,
            "trace_id": self.trace_id,
            "created_at": self.created_at.isoformat(),
            "extractors_used": self.extractors_used,
            "transformations_applied": self.transformations_applied,
            "validations_passed": self.validations_passed,
            "feature_checksums": self.feature_checksums,
        }

