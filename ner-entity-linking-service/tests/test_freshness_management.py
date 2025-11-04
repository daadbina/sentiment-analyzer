"""Tests for knowledge base freshness management."""

import pytest
from datetime import datetime, timedelta
from src.knowledge_base.freshness_manager import (
    FreshnessMetadata,
    FreshnessManager,
    CacheInvalidationStrategy,
)


class TestFreshnessMetadata:
    """Tests for FreshnessMetadata."""

    def test_create_freshness_metadata(self):
        """Test creating freshness metadata."""
        now = datetime.utcnow()
        metadata = FreshnessMetadata(
            entity_id="Q123",
            last_updated=now,
            source="wikidata",
            confidence=0.95,
            update_frequency="weekly",
        )
        assert metadata.entity_id == "Q123"
        assert metadata.source == "wikidata"
        assert not metadata.is_stale


class TestFreshnessManager:
    """Tests for freshness manager."""

    def test_check_freshness_fresh_data(self):
        """Test checking freshness for fresh data."""
        now = datetime.utcnow()
        freshness = FreshnessManager.check_freshness(
            "Q123", now, "wikidata", "PERSON"
        )
        assert not freshness.is_stale
        assert freshness.staleness_days == 0

    def test_check_freshness_stale_data(self):
        """Test checking freshness for stale data."""
        old_date = datetime.utcnow() - timedelta(days=60)
        freshness = FreshnessManager.check_freshness(
            "Q123", old_date, "wikidata", "PERSON"
        )
        assert freshness.is_stale
        assert freshness.staleness_days == 60

    def test_check_freshness_different_sources(self):
        """Test freshness thresholds for different sources."""
        old_date = datetime.utcnow() - timedelta(days=15)

        # Wikidata: 30 day threshold
        freshness_wd = FreshnessManager.check_freshness(
            "Q123", old_date, "wikidata", "PERSON"
        )
        assert not freshness_wd.is_stale

        # OpenSanctions: 7 day threshold
        freshness_os = FreshnessManager.check_freshness(
            "Q123", old_date, "opensanctions", "PERSON"
        )
        assert freshness_os.is_stale

    def test_get_staleness_score(self):
        """Test getting staleness score."""
        now = datetime.utcnow()
        score = FreshnessManager.get_staleness_score(now, "wikidata")
        assert score == 0.0

        old_date = datetime.utcnow() - timedelta(days=30)
        score = FreshnessManager.get_staleness_score(old_date, "wikidata")
        assert 0.0 <= score <= 1.0

    def test_get_freshness_score(self):
        """Test getting freshness score."""
        now = datetime.utcnow()
        score = FreshnessManager.get_freshness_score(now, "wikidata")
        assert score == 1.0

        old_date = datetime.utcnow() - timedelta(days=30)
        score = FreshnessManager.get_freshness_score(old_date, "wikidata")
        assert 0.0 <= score <= 1.0

    def test_should_refresh(self):
        """Test checking if refresh is needed."""
        now = datetime.utcnow()
        assert not FreshnessManager.should_refresh(now, "wikidata")

        old_date = datetime.utcnow() - timedelta(days=60)
        assert FreshnessManager.should_refresh(old_date, "wikidata")

    def test_get_next_refresh_time_daily(self):
        """Test getting next refresh time for daily updates."""
        now = datetime.utcnow()
        next_refresh = FreshnessManager.get_next_refresh_time(now, "PERSON")
        # PERSON has weekly frequency
        assert next_refresh > now

    def test_get_next_refresh_time_different_types(self):
        """Test next refresh time for different entity types."""
        now = datetime.utcnow()

        person_refresh = FreshnessManager.get_next_refresh_time(now, "PERSON")
        org_refresh = FreshnessManager.get_next_refresh_time(now, "ORGANIZATION")
        location_refresh = FreshnessManager.get_next_refresh_time(now, "LOCATION")

        # PERSON (weekly) < ORGANIZATION (monthly) < LOCATION (yearly)
        assert person_refresh < org_refresh < location_refresh

    def test_batch_check_freshness(self):
        """Test batch freshness checking."""
        now = datetime.utcnow()
        old_date = datetime.utcnow() - timedelta(days=60)

        entities = [
            {
                "entity_id": "Q1",
                "last_updated": now,
                "source": "wikidata",
                "entity_type": "PERSON",
            },
            {
                "entity_id": "Q2",
                "last_updated": old_date,
                "source": "wikidata",
                "entity_type": "PERSON",
            },
        ]

        results = FreshnessManager.batch_check_freshness(entities)
        assert len(results) == 2
        assert not results[0].is_stale
        assert results[1].is_stale

    def test_get_stale_entities(self):
        """Test getting stale entities."""
        now = datetime.utcnow()
        old_date = datetime.utcnow() - timedelta(days=60)

        entities = [
            {
                "entity_id": "Q1",
                "last_updated": now,
                "source": "wikidata",
                "entity_type": "PERSON",
            },
            {
                "entity_id": "Q2",
                "last_updated": old_date,
                "source": "wikidata",
                "entity_type": "PERSON",
            },
        ]

        stale = FreshnessManager.get_stale_entities(entities)
        assert len(stale) == 1
        assert stale[0]["entity_id"] == "Q2"


class TestCacheInvalidationStrategy:
    """Tests for cache invalidation strategy."""

    def test_should_invalidate_cache_fresh(self):
        """Test cache invalidation for fresh data."""
        now = datetime.utcnow()
        should_invalidate = CacheInvalidationStrategy.should_invalidate_cache(
            now, "wikidata", cache_ttl_seconds=3600
        )
        assert not should_invalidate

    def test_should_invalidate_cache_stale(self):
        """Test cache invalidation for stale data."""
        old_date = datetime.utcnow() - timedelta(days=60)
        should_invalidate = CacheInvalidationStrategy.should_invalidate_cache(
            old_date, "wikidata", cache_ttl_seconds=3600
        )
        assert should_invalidate

    def test_should_invalidate_cache_ttl_expired(self):
        """Test cache invalidation when TTL expired."""
        old_date = datetime.utcnow() - timedelta(hours=2)
        should_invalidate = CacheInvalidationStrategy.should_invalidate_cache(
            old_date, "wikidata", cache_ttl_seconds=3600
        )
        assert should_invalidate

    def test_get_cache_ttl(self):
        """Test getting cache TTL."""
        ttl = CacheInvalidationStrategy.get_cache_ttl("wikidata", "PERSON")
        assert ttl > 0
        assert isinstance(ttl, int)

    def test_get_cache_ttl_different_sources(self):
        """Test cache TTL for different sources."""
        ttl_wd = CacheInvalidationStrategy.get_cache_ttl("wikidata", "PERSON")
        ttl_os = CacheInvalidationStrategy.get_cache_ttl("opensanctions", "PERSON")

        # OpenSanctions should have shorter TTL (more frequent updates)
        assert ttl_os < ttl_wd

    def test_get_cache_ttl_different_entity_types(self):
        """Test cache TTL for different entity types."""
        ttl_person = CacheInvalidationStrategy.get_cache_ttl("wikidata", "PERSON")
        ttl_location = CacheInvalidationStrategy.get_cache_ttl("wikidata", "LOCATION")

        # PERSON should have shorter TTL (more frequent updates)
        assert ttl_person < ttl_location

    def test_get_invalidation_reason_stale(self):
        """Test getting invalidation reason for stale data."""
        old_date = datetime.utcnow() - timedelta(days=60)
        reason = CacheInvalidationStrategy.get_invalidation_reason(
            old_date, "wikidata", cache_ttl_seconds=3600
        )
        assert reason is not None
        assert "stale" in reason.lower()

    def test_get_invalidation_reason_ttl_expired(self):
        """Test getting invalidation reason for expired TTL."""
        old_date = datetime.utcnow() - timedelta(hours=2)
        reason = CacheInvalidationStrategy.get_invalidation_reason(
            old_date, "wikidata", cache_ttl_seconds=3600
        )
        assert reason is not None
        assert "TTL" in reason

    def test_get_invalidation_reason_fresh(self):
        """Test getting invalidation reason for fresh data."""
        now = datetime.utcnow()
        reason = CacheInvalidationStrategy.get_invalidation_reason(
            now, "wikidata", cache_ttl_seconds=3600
        )
        assert reason is None


class TestFreshnessIntegration:
    """Integration tests for freshness management."""

    def test_full_freshness_workflow(self):
        """Test full freshness management workflow."""
        now = datetime.utcnow()
        old_date = datetime.utcnow() - timedelta(days=60)

        # Check freshness
        freshness = FreshnessManager.check_freshness(
            "Q123", old_date, "wikidata", "PERSON"
        )
        assert freshness.is_stale

        # Check if refresh needed
        should_refresh = FreshnessManager.should_refresh(old_date, "wikidata")
        assert should_refresh

        # Get next refresh time
        next_refresh = FreshnessManager.get_next_refresh_time(old_date, "PERSON")
        assert next_refresh > old_date

        # Check cache invalidation
        should_invalidate = CacheInvalidationStrategy.should_invalidate_cache(
            old_date, "wikidata"
        )
        assert should_invalidate

        # Get invalidation reason
        reason = CacheInvalidationStrategy.get_invalidation_reason(old_date, "wikidata")
        assert reason is not None

