"""Tests for deduplication engine."""

import pytest
from src.validation.deduplication import DeduplicationEngine


@pytest.fixture
def dedup_engine():
    """Create deduplication engine."""
    return DeduplicationEngine()


@pytest.fixture
def sample_label():
    """Create sample label."""
    return {
        "event_id": "evt_001",
        "event_date": "2025-11-05",
        "label_source": "GDELT",
        "confidence": 0.85,
        "fetched_at": "2025-11-05T10:00:00Z",
        "trace_id": "trace_001"
    }


class TestDeduplicationEngine:
    """Test deduplication engine."""

    def test_init(self, dedup_engine):
        """Test initialization."""
        assert dedup_engine is not None
        assert len(dedup_engine.seen_hashes) == 0

    def test_compute_label_hash(self, dedup_engine, sample_label):
        """Test hash computation."""
        hash1 = dedup_engine._compute_label_hash(sample_label)
        hash2 = dedup_engine._compute_label_hash(sample_label)
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex length

    @pytest.mark.asyncio
    async def test_register_label(self, dedup_engine, sample_label):
        """Test label registration."""
        await dedup_engine.register_label(sample_label)

        assert len(dedup_engine.seen_hashes) == 1

    def test_is_duplicate_new_label(self, dedup_engine, sample_label):
        """Test duplicate detection for new label."""
        is_dup, existing = dedup_engine.is_duplicate(sample_label)

        assert is_dup is False
        assert existing == {}

    @pytest.mark.asyncio
    async def test_is_duplicate_existing_label(self, dedup_engine, sample_label):
        """Test duplicate detection for existing label."""
        await dedup_engine.register_label(sample_label)

        is_dup, existing = dedup_engine.is_duplicate(sample_label)

        assert is_dup is True
        assert existing["event_id"] == sample_label["event_id"]

    @pytest.mark.asyncio
    async def test_deduplicate_batch_no_duplicates(self, dedup_engine):
        """Test deduplication with no duplicates."""
        labels = [
            {
                "event_id": f"evt_{i:03d}",
                "event_date": "2025-11-05",
                "label_source": "GDELT",
                "confidence": 0.85,
                "fetched_at": "2025-11-05T10:00:00Z",
                "trace_id": f"trace_{i:03d}"
            }
            for i in range(5)
        ]

        unique, duplicates = await dedup_engine.deduplicate_batch(labels)

        assert len(unique) == 5
        assert len(duplicates) == 0

    @pytest.mark.asyncio
    async def test_deduplicate_batch_with_duplicates(self, dedup_engine):
        """Test deduplication with duplicates."""
        label1 = {
            "event_id": "evt_001",
            "event_date": "2025-11-05",
            "label_source": "GDELT",
            "confidence": 0.80,
            "fetched_at": "2025-11-05T10:00:00Z",
            "trace_id": "trace_001"
        }

        label2 = {
            "event_id": "evt_001",
            "event_date": "2025-11-05",
            "label_source": "GDELT",
            "confidence": 0.90,  # Higher confidence
            "fetched_at": "2025-11-05T10:00:00Z",
            "trace_id": "trace_002"
        }

        unique, duplicates = await dedup_engine.deduplicate_batch([label1, label2])

        # First label is registered, second is a duplicate with higher confidence
        # So we should have 1 unique (the higher confidence one) and 1 duplicate (the lower one)
        assert len(unique) == 1
        assert len(duplicates) == 1
        # The unique label should be the one with higher confidence
        assert unique[0]["confidence"] == 0.90

    @pytest.mark.asyncio
    async def test_deduplicate_batch_multiple_sources(self, dedup_engine):
        """Test deduplication with multiple sources."""
        labels = [
            {
                "event_id": "evt_001",
                "event_date": "2025-11-05",
                "label_source": "GDELT",
                "confidence": 0.85,
                "fetched_at": "2025-11-05T10:00:00Z",
                "trace_id": "trace_001"
            },
            {
                "event_id": "evt_001",
                "event_date": "2025-11-05",
                "label_source": "Binance",  # Different source
                "confidence": 0.85,
                "fetched_at": "2025-11-05T10:00:00Z",
                "trace_id": "trace_002"
            }
        ]

        unique, duplicates = await dedup_engine.deduplicate_batch(labels)

        # Different sources = different hashes = not duplicates
        assert len(unique) == 2
        assert len(duplicates) == 0

    @pytest.mark.asyncio
    async def test_clear_cache(self, dedup_engine, sample_label):
        """Test cache clearing."""
        await dedup_engine.register_label(sample_label)
        assert len(dedup_engine.seen_hashes) == 1

        dedup_engine.clear_cache()
        assert len(dedup_engine.seen_hashes) == 0

    @pytest.mark.asyncio
    async def test_get_cache_stats(self, dedup_engine, sample_label):
        """Test cache statistics."""
        await dedup_engine.register_label(sample_label)

        stats = dedup_engine.get_cache_stats()

        assert stats["cache_size"] == 1
        assert "operation" in stats

    @pytest.mark.asyncio
    async def test_deduplicate_batch_empty(self, dedup_engine):
        """Test deduplication with empty batch."""
        unique, duplicates = await dedup_engine.deduplicate_batch([])

        assert len(unique) == 0
        assert len(duplicates) == 0

    @pytest.mark.asyncio
    async def test_deduplicate_batch_invalid_label(self, dedup_engine):
        """Test deduplication with invalid label."""
        labels = [
            {
                "event_id": None,
                "event_date": None,
                "label_source": None,
                "confidence": 0.85,
                "fetched_at": "2025-11-05T10:00:00Z",
                "trace_id": "trace_001"
            }
        ]

        unique, duplicates = await dedup_engine.deduplicate_batch(labels)

        # Should handle gracefully
        assert len(unique) + len(duplicates) == 1

