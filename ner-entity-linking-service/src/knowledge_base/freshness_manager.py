"""Knowledge base freshness management."""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class FreshnessMetadata:
    """Metadata for knowledge base freshness."""

    entity_id: str
    last_updated: datetime
    source: str  # wikidata, dbpedia, opensanctions
    confidence: float
    update_frequency: str  # daily, weekly, monthly, yearly
    is_stale: bool = False
    staleness_days: int = 0


class FreshnessManager:
    """Manages knowledge base freshness."""

    # Staleness thresholds (in days)
    STALENESS_THRESHOLDS = {
        "wikidata": 30,  # 30 days
        "dbpedia": 60,  # 60 days
        "opensanctions": 7,  # 7 days (frequently updated)
    }

    # Update frequency recommendations
    UPDATE_FREQUENCIES = {
        "PERSON": "weekly",
        "ORGANIZATION": "monthly",
        "LOCATION": "yearly",
        "GPE": "monthly",
    }

    @staticmethod
    def check_freshness(
        entity_id: str,
        last_updated: datetime,
        source: str,
        entity_type: str = "PERSON",
    ) -> FreshnessMetadata:
        """Check if entity data is fresh.

        Args:
            entity_id: Entity ID
            last_updated: Last update timestamp
            source: Data source
            entity_type: Entity type

        Returns:
            FreshnessMetadata
        """
        now = datetime.utcnow()
        staleness_threshold = FreshnessManager.STALENESS_THRESHOLDS.get(source, 30)
        staleness_days = (now - last_updated).days

        is_stale = staleness_days > staleness_threshold

        if is_stale:
            logger.warning(
                f"Entity {entity_id} from {source} is stale "
                f"({staleness_days} days old, threshold: {staleness_threshold})"
            )

        return FreshnessMetadata(
            entity_id=entity_id,
            last_updated=last_updated,
            source=source,
            confidence=1.0 - (staleness_days / (staleness_threshold * 2)),
            update_frequency=FreshnessManager.UPDATE_FREQUENCIES.get(entity_type, "monthly"),
            is_stale=is_stale,
            staleness_days=staleness_days,
        )

    @staticmethod
    def get_staleness_score(
        last_updated: datetime,
        source: str,
    ) -> float:
        """Get staleness score (0-1, higher = more stale).

        Args:
            last_updated: Last update timestamp
            source: Data source

        Returns:
            Staleness score
        """
        now = datetime.utcnow()
        staleness_threshold = FreshnessManager.STALENESS_THRESHOLDS.get(source, 30)
        staleness_days = (now - last_updated).days

        # Score increases with staleness
        score = min(staleness_days / staleness_threshold, 1.0)
        return max(0.0, score)

    @staticmethod
    def get_freshness_score(
        last_updated: datetime,
        source: str,
    ) -> float:
        """Get freshness score (0-1, higher = more fresh).

        Args:
            last_updated: Last update timestamp
            source: Data source

        Returns:
            Freshness score
        """
        staleness_score = FreshnessManager.get_staleness_score(last_updated, source)
        return 1.0 - staleness_score

    @staticmethod
    def should_refresh(
        last_updated: datetime,
        source: str,
        entity_type: str = "PERSON",
    ) -> bool:
        """Check if entity should be refreshed.

        Args:
            last_updated: Last update timestamp
            source: Data source
            entity_type: Entity type

        Returns:
            True if should refresh
        """
        freshness = FreshnessManager.check_freshness(
            "temp", last_updated, source, entity_type
        )
        return freshness.is_stale

    @staticmethod
    def get_next_refresh_time(
        last_updated: datetime,
        entity_type: str = "PERSON",
    ) -> datetime:
        """Get recommended next refresh time.

        Args:
            last_updated: Last update timestamp
            entity_type: Entity type

        Returns:
            Recommended next refresh time
        """
        update_frequency = FreshnessManager.UPDATE_FREQUENCIES.get(entity_type, "monthly")

        if update_frequency == "daily":
            return last_updated + timedelta(days=1)
        elif update_frequency == "weekly":
            return last_updated + timedelta(weeks=1)
        elif update_frequency == "monthly":
            return last_updated + timedelta(days=30)
        elif update_frequency == "yearly":
            return last_updated + timedelta(days=365)
        else:
            return last_updated + timedelta(days=30)

    @staticmethod
    def batch_check_freshness(
        entities: List[Dict],
    ) -> List[FreshnessMetadata]:
        """Check freshness for multiple entities.

        Args:
            entities: List of entity dictionaries with entity_id, last_updated, source

        Returns:
            List of FreshnessMetadata
        """
        results = []
        for entity in entities:
            freshness = FreshnessManager.check_freshness(
                entity.get("entity_id", ""),
                entity.get("last_updated", datetime.utcnow()),
                entity.get("source", "wikidata"),
                entity.get("entity_type", "PERSON"),
            )
            results.append(freshness)
        return results

    @staticmethod
    def get_stale_entities(
        entities: List[Dict],
    ) -> List[Dict]:
        """Get stale entities that need refresh.

        Args:
            entities: List of entity dictionaries

        Returns:
            List of stale entities
        """
        stale = []
        for entity in entities:
            freshness = FreshnessManager.check_freshness(
                entity.get("entity_id", ""),
                entity.get("last_updated", datetime.utcnow()),
                entity.get("source", "wikidata"),
                entity.get("entity_type", "PERSON"),
            )
            if freshness.is_stale:
                stale.append(entity)
        return stale


class CacheInvalidationStrategy:
    """Strategies for cache invalidation based on freshness."""

    @staticmethod
    def should_invalidate_cache(
        last_updated: datetime,
        source: str,
        cache_ttl_seconds: int = 3600,
    ) -> bool:
        """Check if cache should be invalidated.

        Args:
            last_updated: Last update timestamp
            source: Data source
            cache_ttl_seconds: Cache TTL in seconds

        Returns:
            True if cache should be invalidated
        """
        now = datetime.utcnow()
        age_seconds = (now - last_updated).total_seconds()

        # Invalidate if data is stale
        staleness_threshold_seconds = (
            FreshnessManager.STALENESS_THRESHOLDS.get(source, 30) * 86400
        )
        if age_seconds > staleness_threshold_seconds:
            return True

        # Invalidate if cache TTL expired
        if age_seconds > cache_ttl_seconds:
            return True

        return False

    @staticmethod
    def get_cache_ttl(
        source: str,
        entity_type: str = "PERSON",
    ) -> int:
        """Get recommended cache TTL in seconds.

        Args:
            source: Data source
            entity_type: Entity type

        Returns:
            Cache TTL in seconds
        """
        # Base TTL by source
        base_ttl = {
            "wikidata": 86400,  # 1 day
            "dbpedia": 172800,  # 2 days
            "opensanctions": 43200,  # 12 hours
        }

        ttl = base_ttl.get(source, 86400)

        # Adjust by entity type
        if entity_type == "PERSON":
            ttl = int(ttl * 0.8)  # More frequent updates for people
        elif entity_type == "ORGANIZATION":
            ttl = int(ttl * 1.0)  # Standard for organizations
        elif entity_type == "LOCATION":
            ttl = int(ttl * 2.0)  # Less frequent for locations

        return ttl

    @staticmethod
    def get_invalidation_reason(
        last_updated: datetime,
        source: str,
        cache_ttl_seconds: int = 3600,
    ) -> Optional[str]:
        """Get reason for cache invalidation.

        Args:
            last_updated: Last update timestamp
            source: Data source
            cache_ttl_seconds: Cache TTL in seconds

        Returns:
            Invalidation reason or None
        """
        now = datetime.utcnow()
        age_seconds = (now - last_updated).total_seconds()

        staleness_threshold_seconds = (
            FreshnessManager.STALENESS_THRESHOLDS.get(source, 30) * 86400
        )

        if age_seconds > staleness_threshold_seconds:
            return f"Data is stale ({age_seconds / 86400:.1f} days old)"

        if age_seconds > cache_ttl_seconds:
            return f"Cache TTL expired ({age_seconds / 3600:.1f} hours)"

        return None

