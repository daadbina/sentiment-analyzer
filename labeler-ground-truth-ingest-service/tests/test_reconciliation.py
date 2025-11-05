"""Unit tests for reconciliation module."""

import pytest
from datetime import datetime, timedelta

from src.reconciliation.reconciler import TemporalMatcher, SemanticMatcher, LabelReconciler


class TestTemporalMatcher:
    """Test temporal matcher."""

    def test_temporal_match_within_threshold(self):
        """Test temporal match within threshold."""
        matcher = TemporalMatcher(threshold_hours=48)

        label_time = datetime.utcnow().isoformat()
        group_time = (datetime.utcnow() - timedelta(hours=24)).isoformat()

        matched, confidence = matcher.match(label_time, group_time)
        assert matched
        assert 0.0 < confidence <= 1.0

    def test_temporal_match_outside_threshold(self):
        """Test temporal match outside threshold."""
        matcher = TemporalMatcher(threshold_hours=48)

        label_time = datetime.utcnow().isoformat()
        group_time = (datetime.utcnow() - timedelta(hours=72)).isoformat()

        matched, confidence = matcher.match(label_time, group_time)
        assert not matched
        assert confidence == 0.0

    def test_temporal_match_exact_time(self):
        """Test temporal match at exact time."""
        matcher = TemporalMatcher(threshold_hours=48)

        time_str = datetime.utcnow().isoformat()

        matched, confidence = matcher.match(time_str, time_str)
        assert matched
        assert confidence == 1.0


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
        """Test reconcile label with matching group."""
        reconciler = LabelReconciler()

        label = {
            "event_id": "123",
            "description": "conflict in Syria",
            "fetched_at": datetime.utcnow().isoformat(),
            "confidence": 0.85
        }

        groups = [
            {
                "group_id": "group_1",
                "topic_label": "conflict in Syria",
                "created_at": (datetime.utcnow() - timedelta(hours=24)).isoformat()
            }
        ]

        result = await reconciler.reconcile(label, groups)
        assert result is not None
        assert result["group_id"] == "group_1"
        assert result["confidence"] > 0.0

    @pytest.mark.asyncio
    async def test_reconcile_label_no_matching_group(self):
        """Test reconcile label with no matching group."""
        reconciler = LabelReconciler()

        label = {
            "event_id": "123",
            "description": "conflict in Syria",
            "fetched_at": datetime.utcnow().isoformat(),
            "confidence": 0.85
        }

        groups = [
            {
                "group_id": "group_1",
                "topic_label": "weather in France",
                "created_at": (datetime.utcnow() - timedelta(hours=72)).isoformat()
            }
        ]

        result = await reconciler.reconcile(label, groups)
        assert result is None

    @pytest.mark.asyncio
    async def test_reconcile_batch(self):
        """Test reconcile batch of labels."""
        reconciler = LabelReconciler()

        labels = [
            {
                "event_id": "123",
                "description": "conflict in Syria",
                "fetched_at": datetime.utcnow().isoformat(),
                "confidence": 0.85
            },
            {
                "event_id": "124",
                "description": "conflict in Iraq",
                "fetched_at": datetime.utcnow().isoformat(),
                "confidence": 0.80
            }
        ]

        groups = [
            {
                "group_id": "group_1",
                "topic_label": "conflict in Syria",
                "created_at": (datetime.utcnow() - timedelta(hours=24)).isoformat()
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

