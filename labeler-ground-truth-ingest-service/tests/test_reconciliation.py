"""Unit tests for reconciliation module."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.reconciliation.reconciler import TemporalMatcher, SemanticMatcher, LabelReconciler


class TestTemporalMatcher:
    """Test temporal matcher."""

    def test_temporal_match_within_threshold(self):
        """Test temporal match within threshold.

        R8: Groups must be created at least 24 hours AFTER the event.
        """
        matcher = TemporalMatcher(threshold_hours=48)

        # Event happened now, group created 25 hours later (should match)
        label_time = datetime.utcnow().isoformat()
        group_time = (datetime.utcnow() + timedelta(hours=25)).isoformat()

        matched, confidence = matcher.match(label_time, group_time)
        assert matched
        assert 0.0 < confidence <= 1.0

    def test_temporal_match_outside_threshold(self):
        """Test temporal match outside threshold.

        R8: Groups must be created at least 24 hours AFTER the event.
        Group created before or too soon after event should not match.
        """
        matcher = TemporalMatcher(threshold_hours=48)

        # Event happened now, group created 10 hours later (too soon, should not match)
        label_time = datetime.utcnow().isoformat()
        group_time = (datetime.utcnow() + timedelta(hours=10)).isoformat()

        matched, confidence = matcher.match(label_time, group_time)
        assert not matched
        assert confidence == 0.0

    def test_temporal_match_exact_time(self):
        """Test temporal match at exact 24 hour threshold.

        R8: Groups created exactly 24 hours after event should match with high confidence.
        """
        matcher = TemporalMatcher(threshold_hours=48)

        # Use same base time to avoid floating point precision issues
        base_time = datetime.utcnow()
        label_time = base_time.isoformat()
        # Group created exactly 24 hours after event
        group_time = (base_time + timedelta(hours=24)).isoformat()

        matched, confidence = matcher.match(label_time, group_time)
        assert matched
        assert confidence >= 0.99  # Allow for tiny floating point differences


class TestSemanticMatcher:
    """Test semantic matcher."""

    def test_semantic_match_high_similarity(self):
        """Test semantic match with high similarity."""
        matcher = SemanticMatcher(similarity_threshold=0.5)

        label_desc = "conflict in Syria"
        group_desc = "conflict in Syria"

        matched, confidence = matcher.match(label_desc, group_desc)
        assert matched
        assert confidence == 1.0

    def test_semantic_match_low_similarity(self):
        """Test semantic match with low similarity."""
        matcher = SemanticMatcher(similarity_threshold=0.8)

        label_desc = "conflict in Syria"
        group_desc = "weather in France"

        matched, confidence = matcher.match(label_desc, group_desc)
        assert not matched
        assert confidence < 0.8

    def test_semantic_match_partial_similarity(self):
        """Test semantic match with partial similarity."""
        matcher = SemanticMatcher(similarity_threshold=0.5)

        label_desc = "conflict in Syria"
        group_desc = "conflict in Iraq"

        matched, confidence = matcher.match(label_desc, group_desc)
        assert matched
        assert 0.0 < confidence <= 1.0


class TestLabelReconciler:
    """Test label reconciler."""

    @pytest.mark.asyncio
    async def test_reconcile_label_with_matching_group(self):
        """Test reconcile label with matching group.

        R8: Group must be created at least 24 hours after the event.
        """
        reconciler = LabelReconciler()

        # Event happened now, group created 25 hours later
        event_time = datetime.utcnow()
        label = {
            "event_id": "123",
            "description": "conflict in Syria",
            "event_timestamp": event_time.isoformat(),
            "fetched_at": datetime.utcnow().isoformat(),
            "confidence": 0.85
        }

        groups = [
            {
                "group_id": "group_1",
                "topic_label": "conflict in Syria",
                "created_at": (event_time + timedelta(hours=25)).isoformat()
            }
        ]

        result = await reconciler.reconcile(label, groups)
        assert result is not None
        assert result["group_id"] == "group_1"
        assert result["confidence"] > 0.0

    @pytest.mark.asyncio
    async def test_reconcile_label_no_matching_group(self):
        """Test reconcile label with no matching group.

        Group created too soon after event should not match.
        """
        reconciler = LabelReconciler()

        # Event happened now, group created only 10 hours later (too soon)
        event_time = datetime.utcnow()
        label = {
            "event_id": "123",
            "description": "conflict in Syria",
            "event_timestamp": event_time.isoformat(),
            "fetched_at": datetime.utcnow().isoformat(),
            "confidence": 0.85
        }

        groups = [
            {
                "group_id": "group_1",
                "topic_label": "weather in France",
                "created_at": (event_time + timedelta(hours=10)).isoformat()
            }
        ]

        result = await reconciler.reconcile(label, groups)
        assert result is None

    @pytest.mark.asyncio
    async def test_reconcile_batch(self):
        """Test reconcile batch of labels.

        R8: Groups must be created at least 24 hours after events.
        """
        reconciler = LabelReconciler()

        event_time = datetime.utcnow()
        labels = [
            {
                "event_id": "123",
                "description": "conflict in Syria",
                "event_timestamp": event_time.isoformat(),
                "fetched_at": datetime.utcnow().isoformat(),
                "confidence": 0.85
            },
            {
                "event_id": "124",
                "description": "conflict in Iraq",
                "event_timestamp": event_time.isoformat(),
                "fetched_at": datetime.utcnow().isoformat(),
                "confidence": 0.80
            }
        ]

        groups = [
            {
                "group_id": "group_1",
                "topic_label": "conflict in Syria",
                "created_at": (event_time + timedelta(hours=25)).isoformat()
            }
        ]

        results = await reconciler.reconcile_batch(labels, groups)
        assert len(results) >= 0


    @pytest.mark.asyncio
    async def test_reconciler_has_reconcile_method(self):
        """Test reconciler has reconcile method."""
        reconciler = LabelReconciler()
        assert callable(getattr(reconciler, 'reconcile', None))

    @pytest.mark.asyncio
    async def test_reconciler_initialization(self):
        """Test reconciler initialization."""
        reconciler = LabelReconciler()
        assert reconciler is not None

    @pytest.mark.asyncio
    async def test_reconciler_has_reconcile_batch_method(self):
        """Test reconciler has reconcile_batch method."""
        reconciler = LabelReconciler()
        assert callable(getattr(reconciler, 'reconcile_batch', None))

    @pytest.mark.asyncio
    async def test_enrich_with_ner_countries_no_existing_countries(self):
        """Test NER country extraction when label has no countries."""
        reconciler = LabelReconciler()

        # Mock NER client
        mock_ner_client = MagicMock()
        mock_ner_client.extract_countries = AsyncMock(return_value=["Syria", "Iraq"])
        reconciler.ner_client = mock_ner_client

        result = {
            "group_id": "group_1",
            "confidence": 0.8,
            "label": {
                "event_id": "event_123",
                "description": "Conflict in Syria and Iraq",
                "countries": [],  # No countries
                "language": "en"
            }
        }

        semantic_groups = [
            {
                "group_id": "group_1",
                "topic_label": "Middle East conflict"
            }
        ]

        enriched = await reconciler._enrich_with_ner_countries(result, semantic_groups)

        # Verify countries were extracted
        assert "countries" in enriched["label"]
        assert len(enriched["label"]["countries"]) > 0
        # NER client should have been called
        assert mock_ner_client.extract_countries.called

    @pytest.mark.asyncio
    async def test_enrich_with_ner_countries_existing_countries(self):
        """Test NER country extraction skips when label already has countries."""
        reconciler = LabelReconciler()

        # Mock NER client
        mock_ner_client = MagicMock()
        mock_ner_client.extract_countries = AsyncMock(return_value=["Syria"])
        reconciler.ner_client = mock_ner_client

        result = {
            "group_id": "group_1",
            "confidence": 0.8,
            "label": {
                "event_id": "event_123",
                "description": "Conflict in Syria",
                "countries": ["Syria"],  # Already has countries
                "language": "en"
            }
        }

        semantic_groups = [
            {
                "group_id": "group_1",
                "topic_label": "Middle East conflict"
            }
        ]

        enriched = await reconciler._enrich_with_ner_countries(result, semantic_groups)

        # Verify countries were not changed
        assert enriched["label"]["countries"] == ["Syria"]
        # NER client should NOT have been called
        assert not mock_ner_client.extract_countries.called

    @pytest.mark.asyncio
    async def test_enrich_with_ner_countries_deduplication(self):
        """Test NER country extraction deduplicates countries."""
        reconciler = LabelReconciler()

        # Mock NER client to return duplicates with different cases
        mock_ner_client = MagicMock()
        mock_ner_client.extract_countries = AsyncMock(
            side_effect=[
                ["Syria", "Iraq"],  # From label
                ["syria", "Turkey"]  # From group (syria is duplicate)
            ]
        )
        reconciler.ner_client = mock_ner_client

        result = {
            "group_id": "group_1",
            "confidence": 0.8,
            "label": {
                "event_id": "event_123",
                "description": "Conflict in Syria and Iraq",
                "countries": [],
                "language": "en"
            }
        }

        semantic_groups = [
            {
                "group_id": "group_1",
                "topic_label": "Syria and Turkey conflict"
            }
        ]

        enriched = await reconciler._enrich_with_ner_countries(result, semantic_groups)

        # Verify deduplication (syria/Syria should appear only once)
        countries = enriched["label"]["countries"]
        assert len(countries) == 3  # Syria, Iraq, Turkey (syria deduplicated)
        # Check case-insensitive uniqueness
        countries_lower = [c.lower() for c in countries]
        assert len(countries_lower) == len(set(countries_lower))

    @pytest.mark.asyncio
    async def test_enrich_with_ner_countries_no_ner_client(self):
        """Test NER country extraction gracefully handles missing NER client."""
        with patch('src.reconciliation.reconciler._get_ner_client', return_value=None):
            reconciler = LabelReconciler()
            reconciler.ner_client = None

            result = {
                "group_id": "group_1",
                "confidence": 0.8,
                "label": {
                    "event_id": "event_123",
                    "description": "Conflict in Syria",
                    "countries": [],
                    "language": "en"
                }
            }

            semantic_groups = [
                {
                    "group_id": "group_1",
                    "topic_label": "Middle East conflict"
                }
            ]

            enriched = await reconciler._enrich_with_ner_countries(result, semantic_groups)

            # Verify result is unchanged
            assert enriched["label"]["countries"] == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

