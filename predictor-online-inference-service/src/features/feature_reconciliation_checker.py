"""
Feature reconciliation checker for validating consistency between offline and online stores.

Compares features from offline and online stores to ensure consistency.
Implements Rule R7 (Time Order Validation) and feature reconciliation requirements.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from ..exceptions import FeatureReconciliationError
from ..utils.trace import trace_span
from ..metrics import MetricsCollector
from .feature_fetcher import REQUIRED_FEATURES


logger = logging.getLogger(__name__)


class FeatureReconciliationChecker:
    """
    Checker for feature reconciliation between offline and online stores.
    
    Validates that features from offline and online stores match within threshold.
    """
    
    def __init__(self, reconciliation_threshold: float = 0.99):
        """
        Initialize feature reconciliation checker.
        
        Args:
            reconciliation_threshold: Minimum match rate (0.0-1.0)
        """
        self.reconciliation_threshold = reconciliation_threshold
        
        logger.info(
            f"Initialized feature reconciliation checker: "
            f"threshold={reconciliation_threshold}"
        )
    
    async def check_reconciliation(
        self,
        online_features: Dict[str, Any],
        offline_features: Dict[str, Any],
        group_id: str,
        trace_id: Optional[str] = None,
    ) -> Tuple[float, Dict[str, tuple]]:
        """
        Check reconciliation between online and offline features.
        
        Args:
            online_features: Features from online store
            offline_features: Features from offline store
            group_id: Semantic group ID
            trace_id: Optional trace ID for distributed tracing
        
        Returns:
            Tuple of (reconciliation_rate, mismatched_features)
            reconciliation_rate: Percentage of matching features (0.0-1.0)
            mismatched_features: Dict mapping feature name to (offline_value, online_value)
        
        Raises:
            FeatureReconciliationError: If reconciliation rate below threshold
        """
        with trace_span(
            "check_feature_reconciliation",
            attributes={"group_id": group_id, "trace_id": trace_id},
        ):
            mismatched_features = {}
            total_features = 0
            matching_features = 0
            
            # Compare each required feature
            for feature_name in REQUIRED_FEATURES:
                total_features += 1
                
                offline_value = offline_features.get(feature_name)
                online_value = online_features.get(feature_name)
                
                # Check if values match
                if self._values_match(offline_value, online_value, feature_name):
                    matching_features += 1
                else:
                    mismatched_features[feature_name] = (offline_value, online_value)
                    
                    # Record mismatch metric
                    MetricsCollector.record_feature_reconciliation_mismatch(feature_name)
                    
                    logger.warning(
                        f"Feature mismatch: group_id={group_id}, "
                        f"feature={feature_name}, offline={offline_value}, online={online_value}",
                        extra={"trace_id": trace_id, "group_id": group_id},
                    )
            
            # Calculate reconciliation rate
            reconciliation_rate = matching_features / total_features if total_features > 0 else 0.0
            
            logger.debug(
                f"Feature reconciliation: group_id={group_id}, "
                f"rate={reconciliation_rate:.4f}, mismatches={len(mismatched_features)}",
                extra={"trace_id": trace_id, "group_id": group_id},
            )
            
            # Check if reconciliation rate meets threshold
            if reconciliation_rate < self.reconciliation_threshold:
                logger.error(
                    f"Feature reconciliation below threshold: group_id={group_id}, "
                    f"rate={reconciliation_rate:.4f}, threshold={self.reconciliation_threshold}",
                    extra={"trace_id": trace_id, "group_id": group_id},
                )
                raise FeatureReconciliationError(
                    f"Feature reconciliation rate {reconciliation_rate:.4f} below threshold {self.reconciliation_threshold}",
                    group_id=group_id,
                    mismatched_features=mismatched_features,
                    reconciliation_rate=reconciliation_rate,
                    trace_id=trace_id,
                )
            
            return reconciliation_rate, mismatched_features
    
    def _values_match(
        self,
        offline_value: Any,
        online_value: Any,
        feature_name: str,
    ) -> bool:
        """
        Check if offline and online values match.
        
        Args:
            offline_value: Value from offline store
            online_value: Value from online store
            feature_name: Name of the feature
        
        Returns:
            True if values match, False otherwise
        """
        # Handle None values
        if offline_value is None and online_value is None:
            return True
        if offline_value is None or online_value is None:
            return False
        
        # Handle numeric features with tolerance
        if feature_name in ["feature_sentiment_mean", "feature_credibility_mean", "feature_time_density"]:
            return self._numeric_match(offline_value, online_value, tolerance=0.01)
        
        # Handle integer features
        if feature_name == "feature_num_sources":
            return int(offline_value) == int(online_value)
        
        # Handle list/string features
        if feature_name == "feature_entities":
            return self._list_match(offline_value, online_value)
        
        # Default: exact match
        return offline_value == online_value
    
    def _numeric_match(
        self,
        value1: float,
        value2: float,
        tolerance: float = 0.01,
    ) -> bool:
        """
        Check if two numeric values match within tolerance.
        
        Args:
            value1: First value
            value2: Second value
            tolerance: Absolute tolerance for matching
        
        Returns:
            True if values match within tolerance
        """
        try:
            return abs(float(value1) - float(value2)) <= tolerance
        except (TypeError, ValueError):
            return False
    
    def _list_match(self, value1: Any, value2: Any) -> bool:
        """
        Check if two list/string values match.
        
        Args:
            value1: First value (list or string)
            value2: Second value (list or string)
        
        Returns:
            True if values match
        """
        # Convert to lists if strings
        if isinstance(value1, str):
            value1 = value1.split(",") if value1 else []
        if isinstance(value2, str):
            value2 = value2.split(",") if value2 else []
        
        # Convert to sets for comparison
        try:
            set1 = set(value1) if isinstance(value1, list) else {value1}
            set2 = set(value2) if isinstance(value2, list) else {value2}
            return set1 == set2
        except (TypeError, ValueError):
            return False
    
    async def check_batch_reconciliation(
        self,
        online_features_list: List[Dict[str, Any]],
        offline_features_list: List[Dict[str, Any]],
        group_ids: List[str],
        trace_id: Optional[str] = None,
    ) -> Tuple[float, List[Dict[str, tuple]]]:
        """
        Check reconciliation for batch of features.
        
        Args:
            online_features_list: List of features from online store
            offline_features_list: List of features from offline store
            group_ids: List of semantic group IDs
            trace_id: Optional trace ID for distributed tracing
        
        Returns:
            Tuple of (overall_reconciliation_rate, list_of_mismatched_features)
        
        Raises:
            FeatureReconciliationError: If overall reconciliation rate below threshold
        """
        with trace_span(
            "check_batch_feature_reconciliation",
            attributes={"batch_size": len(group_ids), "trace_id": trace_id},
        ):
            if len(online_features_list) != len(offline_features_list) != len(group_ids):
                raise ValueError(
                    f"Length mismatch: online={len(online_features_list)}, "
                    f"offline={len(offline_features_list)}, group_ids={len(group_ids)}"
                )
            
            total_rate = 0.0
            all_mismatches = []
            
            for online_features, offline_features, group_id in zip(
                online_features_list, offline_features_list, group_ids
            ):
                try:
                    rate, mismatches = await self.check_reconciliation(
                        online_features,
                        offline_features,
                        group_id,
                        trace_id,
                    )
                    total_rate += rate
                    all_mismatches.append(mismatches)
                except FeatureReconciliationError:
                    # Continue checking other groups
                    total_rate += 0.0
                    all_mismatches.append({})
            
            # Calculate overall reconciliation rate
            overall_rate = total_rate / len(group_ids) if group_ids else 0.0
            
            logger.info(
                f"Batch feature reconciliation: batch_size={len(group_ids)}, "
                f"overall_rate={overall_rate:.4f}",
                extra={"trace_id": trace_id},
            )
            
            # Check if overall rate meets threshold
            if overall_rate < self.reconciliation_threshold:
                logger.error(
                    f"Batch feature reconciliation below threshold: "
                    f"rate={overall_rate:.4f}, threshold={self.reconciliation_threshold}",
                    extra={"trace_id": trace_id},
                )
                raise FeatureReconciliationError(
                    f"Batch feature reconciliation rate {overall_rate:.4f} below threshold {self.reconciliation_threshold}",
                    reconciliation_rate=overall_rate,
                    trace_id=trace_id,
                )
            
            return overall_rate, all_mismatches

