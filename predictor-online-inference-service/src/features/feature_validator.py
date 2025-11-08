"""
Feature validator for validating feature completeness and quality.

Validates features against expected schema and quality thresholds.
Implements fail-fast validation to catch issues early.
"""

import logging
from datetime import datetime
from typing import Any

from ..exceptions import FeatureValidationError
from ..utils.trace import trace_span
from .feature_fetcher import REQUIRED_FEATURES

logger = logging.getLogger(__name__)


class FeatureValidator:
    """
    Validator for feature completeness and quality.

    Validates features against expected schema and quality thresholds.
    """

    def __init__(self, feature_freshness_threshold_seconds: int = 3600):
        """
        Initialize feature validator.

        Args:
            feature_freshness_threshold_seconds: Maximum age of features in seconds
        """
        self.feature_freshness_threshold_seconds = feature_freshness_threshold_seconds

        logger.info(
            f"Initialized feature validator: "
            f"freshness_threshold={feature_freshness_threshold_seconds}s"
        )

    async def validate_features(
        self,
        features: dict[str, Any],
        group_id: str,
        trace_id: str | None = None,
    ) -> None:
        """
        Validate feature completeness and quality.

        Args:
            features: Feature dictionary to validate
            group_id: Semantic group ID
            trace_id: Optional trace ID for distributed tracing

        Raises:
            FeatureValidationError: If validation fails
        """
        with trace_span(
            "validate_features",
            attributes={"group_id": group_id, "trace_id": trace_id},
        ):
            # Check for missing features
            missing_features = self._check_missing_features(features)
            if missing_features:
                logger.error(
                    f"Missing required features: group_id={group_id}, "
                    f"missing={missing_features}",
                    extra={"trace_id": trace_id, "group_id": group_id},
                )
                raise FeatureValidationError(
                    f"Missing required features: {missing_features}",
                    group_id=group_id,
                    missing_features=missing_features,
                    trace_id=trace_id,
                )

            # Check for null features
            null_features = self._check_null_features(features)
            if null_features:
                logger.error(
                    f"Null feature values: group_id={group_id}, null={null_features}",
                    extra={"trace_id": trace_id, "group_id": group_id},
                )
                raise FeatureValidationError(
                    f"Null feature values: {null_features}",
                    group_id=group_id,
                    invalid_features=dict.fromkeys(null_features, "null value"),
                    trace_id=trace_id,
                )

            # Check feature types
            invalid_types = self._check_feature_types(features)
            if invalid_types:
                logger.error(
                    f"Invalid feature types: group_id={group_id}, invalid={invalid_types}",
                    extra={"trace_id": trace_id, "group_id": group_id},
                )
                raise FeatureValidationError(
                    f"Invalid feature types: {invalid_types}",
                    group_id=group_id,
                    invalid_features=invalid_types,
                    trace_id=trace_id,
                )

            # Check feature ranges
            out_of_range = self._check_feature_ranges(features)
            if out_of_range:
                logger.error(
                    f"Features out of range: group_id={group_id}, out_of_range={out_of_range}",
                    extra={"trace_id": trace_id, "group_id": group_id},
                )
                raise FeatureValidationError(
                    f"Features out of range: {out_of_range}",
                    group_id=group_id,
                    invalid_features=out_of_range,
                    trace_id=trace_id,
                )

            # Check feature freshness
            if "feature_timestamp" in features:
                self._check_feature_freshness(features, group_id, trace_id)

            logger.debug(
                f"Features validated successfully: group_id={group_id}",
                extra={"trace_id": trace_id, "group_id": group_id},
            )

    def _check_missing_features(self, features: dict[str, Any]) -> list[str]:
        """
        Check for missing required features.

        Args:
            features: Feature dictionary

        Returns:
            List of missing feature names
        """
        missing = []
        for feature_name in REQUIRED_FEATURES:
            if feature_name not in features:
                missing.append(feature_name)
        return missing

    def _check_null_features(self, features: dict[str, Any]) -> list[str]:
        """
        Check for null feature values.

        Args:
            features: Feature dictionary

        Returns:
            List of feature names with null values
        """
        null_features = []
        for feature_name in REQUIRED_FEATURES:
            if features.get(feature_name) is None:
                null_features.append(feature_name)
        return null_features

    def _check_feature_types(self, features: dict[str, Any]) -> dict[str, str]:
        """
        Check feature types against expected types.

        Args:
            features: Feature dictionary

        Returns:
            Dictionary of invalid features and their issues
        """
        invalid = {}

        # feature_num_sources: int
        if "feature_num_sources" in features:
            if not isinstance(features["feature_num_sources"], (int, float)):
                invalid["feature_num_sources"] = (
                    f"expected numeric, got {type(features['feature_num_sources']).__name__}"
                )

        # feature_sentiment_mean: float
        if "feature_sentiment_mean" in features:
            if not isinstance(features["feature_sentiment_mean"], (int, float)):
                invalid["feature_sentiment_mean"] = (
                    f"expected numeric, got {type(features['feature_sentiment_mean']).__name__}"
                )

        # feature_credibility_mean: float
        if "feature_credibility_mean" in features:
            if not isinstance(features["feature_credibility_mean"], (int, float)):
                invalid["feature_credibility_mean"] = (
                    f"expected numeric, got {type(features['feature_credibility_mean']).__name__}"
                )

        # feature_entities: list or string
        if "feature_entities" in features:
            if not isinstance(features["feature_entities"], (list, str)):
                invalid["feature_entities"] = (
                    f"expected list or string, got {type(features['feature_entities']).__name__}"
                )

        # feature_time_density: float
        if "feature_time_density" in features:
            if not isinstance(features["feature_time_density"], (int, float)):
                invalid["feature_time_density"] = (
                    f"expected numeric, got {type(features['feature_time_density']).__name__}"
                )

        return invalid

    def _check_feature_ranges(self, features: dict[str, Any]) -> dict[str, str]:
        """
        Check feature values are within expected ranges.

        Args:
            features: Feature dictionary

        Returns:
            Dictionary of out-of-range features and their issues
        """
        out_of_range = {}

        # feature_num_sources: >= 0
        if "feature_num_sources" in features:
            if features["feature_num_sources"] < 0:
                out_of_range["feature_num_sources"] = (
                    f"negative value: {features['feature_num_sources']}"
                )

        # feature_sentiment_mean: [-1, 1]
        if "feature_sentiment_mean" in features:
            value = features["feature_sentiment_mean"]
            if not -1.0 <= value <= 1.0:
                out_of_range["feature_sentiment_mean"] = f"out of range [-1, 1]: {value}"

        # feature_credibility_mean: [0, 1]
        if "feature_credibility_mean" in features:
            value = features["feature_credibility_mean"]
            if not 0.0 <= value <= 1.0:
                out_of_range["feature_credibility_mean"] = f"out of range [0, 1]: {value}"

        # feature_time_density: [0, 1]
        if "feature_time_density" in features:
            value = features["feature_time_density"]
            if not 0.0 <= value <= 1.0:
                out_of_range["feature_time_density"] = f"out of range [0, 1]: {value}"

        return out_of_range

    def _check_feature_freshness(
        self,
        features: dict[str, Any],
        group_id: str,
        trace_id: str | None = None,
    ) -> None:
        """
        Check feature freshness against threshold.

        Args:
            features: Feature dictionary
            group_id: Semantic group ID
            trace_id: Optional trace ID for distributed tracing

        Raises:
            FeatureValidationError: If features are too old
        """
        try:
            feature_timestamp = datetime.fromisoformat(features["feature_timestamp"])
            age_seconds = (datetime.utcnow() - feature_timestamp).total_seconds()

            if age_seconds > self.feature_freshness_threshold_seconds:
                logger.warning(
                    f"Features are stale: group_id={group_id}, "
                    f"age_seconds={age_seconds:.2f}, "
                    f"threshold={self.feature_freshness_threshold_seconds}",
                    extra={"trace_id": trace_id, "group_id": group_id},
                )
                raise FeatureValidationError(
                    f"Features are stale: age={age_seconds:.2f}s, "
                    f"threshold={self.feature_freshness_threshold_seconds}s",
                    group_id=group_id,
                    invalid_features={
                        "feature_timestamp": f"stale by {age_seconds - self.feature_freshness_threshold_seconds:.2f}s"
                    },
                    trace_id=trace_id,
                )
        except (ValueError, KeyError) as e:
            logger.warning(
                f"Failed to parse feature timestamp: group_id={group_id}, error={e}",
                extra={"trace_id": trace_id, "group_id": group_id},
            )
