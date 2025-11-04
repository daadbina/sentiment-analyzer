"""Offline-online feature reconciliation."""

from typing import Dict, Any, Tuple
from ..clients import FeastClient, RedisClient
from ..utils import StructuredLogger
from ..exceptions import ReconciliationError

logger = StructuredLogger(__name__)


class FeatureReconciliation:
    """Reconcile offline and online features."""

    def __init__(self):
        """Initialize reconciliation."""
        self.feast_client = FeastClient()
        self.redis_client = RedisClient()
        self.feast_client.connect()
        self.redis_client.connect()

    def reconcile(
        self,
        group_id: str,
        feature_names: list,
    ) -> Tuple[bool, Dict[str, Any]]:
        """Reconcile offline and online features.

        Args:
            group_id: Semantic group ID
            feature_names: List of feature names

        Returns:
            Tuple of (is_consistent, reconciliation_report)
        """
        try:
            # Get features from both stores
            offline_features = self.feast_client.get_features(group_id, feature_names)
            online_features = self.redis_client.get_features(group_id)

            if not offline_features or not online_features:
                logger.warning(
                    "Missing features in one or both stores",
                    group_id=group_id,
                    has_offline=bool(offline_features),
                    has_online=bool(online_features),
                )
                return False, {
                    "group_id": group_id,
                    "is_consistent": False,
                    "reason": "missing_features",
                }

            # Compare features
            mismatches = []
            for feature_name in feature_names:
                offline_value = offline_features.get(feature_name)
                online_value = online_features.get(feature_name)

                if offline_value != online_value:
                    mismatches.append({
                        "feature": feature_name,
                        "offline_value": offline_value,
                        "online_value": online_value,
                    })

            is_consistent = len(mismatches) == 0

            report = {
                "group_id": group_id,
                "is_consistent": is_consistent,
                "mismatch_count": len(mismatches),
                "mismatches": mismatches,
            }

            if is_consistent:
                logger.info(
                    "Features reconciled successfully",
                    group_id=group_id,
                )
            else:
                logger.warning(
                    "Feature mismatches detected",
                    group_id=group_id,
                    mismatch_count=len(mismatches),
                )

            return is_consistent, report

        except Exception as e:
            logger.error(
                "Error reconciling features",
                group_id=group_id,
                error=str(e),
            )
            raise ReconciliationError(f"Error reconciling features: {str(e)}")

    def close(self):
        """Close connections."""
        self.feast_client.close()
        self.redis_client.close()

