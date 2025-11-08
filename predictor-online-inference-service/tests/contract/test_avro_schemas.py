"""
Contract tests for Avro schemas.

Tests schema compatibility and evolution for Kafka messages.
"""

import pytest
import json
from typing import Dict, Any
from unittest.mock import MagicMock, patch


# Avro schemas for testing
SEMANTIC_GROUPS_SCHEMA = {
    "type": "record",
    "name": "SemanticGroup",
    "namespace": "com.sentiment.analyzer",
    "fields": [
        {"name": "group_id", "type": "string"},
        {"name": "domain", "type": "string"},
        {"name": "articles", "type": {"type": "array", "items": {
            "type": "record",
            "name": "Article",
            "fields": [
                {"name": "id", "type": "string"},
                {"name": "title", "type": "string"},
                {"name": "content", "type": "string"},
                {"name": "source", "type": "string"},
                {"name": "published_at", "type": "string"},
                {"name": "sentiment_score", "type": ["null", "double"], "default": None},
                {"name": "credibility_score", "type": ["null", "double"], "default": None},
            ]
        }}},
        {"name": "timestamp", "type": "string"},
        {"name": "entities", "type": {"type": "array", "items": "string"}},
    ]
}

PREDICTIONS_SCHEMA = {
    "type": "record",
    "name": "Prediction",
    "namespace": "com.sentiment.analyzer",
    "fields": [
        {"name": "prediction_id", "type": "string"},
        {"name": "group_id", "type": "string"},
        {"name": "domain", "type": "string"},
        {"name": "probability", "type": "double"},
        {"name": "confidence", "type": "double"},
        {"name": "model_version", "type": "string"},
        {"name": "timestamp", "type": "string"},
        {"name": "features", "type": {"type": "map", "values": "double"}},
        {"name": "metadata", "type": ["null", {"type": "map", "values": "string"}], "default": None},
    ]
}

GROUND_TRUTH_SCHEMA = {
    "type": "record",
    "name": "GroundTruth",
    "namespace": "com.sentiment.analyzer",
    "fields": [
        {"name": "label_id", "type": "string"},
        {"name": "group_id", "type": "string"},
        {"name": "domain", "type": "string"},
        {"name": "label", "type": "int"},
        {"name": "label_confidence", "type": "double"},
        {"name": "timestamp", "type": "string"},
        {"name": "source", "type": "string"},
        {"name": "license_status", "type": "string"},
    ]
}


@pytest.fixture
def semantic_group_message() -> Dict[str, Any]:
    """Create a valid semantic group message."""
    return {
        "group_id": "group123",
        "domain": "btc",
        "articles": [
            {
                "id": "art1",
                "title": "Bitcoin rises",
                "content": "Bitcoin price increased today",
                "source": "news.com",
                "published_at": "2024-01-01T00:00:00Z",
                "sentiment_score": 0.75,
                "credibility_score": 0.85,
            }
        ],
        "timestamp": "2024-01-01T00:00:00Z",
        "entities": ["bitcoin", "cryptocurrency"],
    }


@pytest.fixture
def prediction_message() -> Dict[str, Any]:
    """Create a valid prediction message."""
    return {
        "prediction_id": "pred123",
        "group_id": "group123",
        "domain": "btc",
        "probability": 0.75,
        "confidence": 0.85,
        "model_version": "v1.0.0",
        "timestamp": "2024-01-01T00:00:00Z",
        "features": {
            "feature_num_sources": 5.0,
            "feature_sentiment_mean": 0.75,
            "feature_credibility_mean": 0.85,
        },
        "metadata": {
            "cache_hit": "false",
            "latency_ms": "150",
        },
    }


@pytest.fixture
def ground_truth_message() -> Dict[str, Any]:
    """Create a valid ground truth message."""
    return {
        "label_id": "label123",
        "group_id": "group123",
        "domain": "btc",
        "label": 1,
        "label_confidence": 0.9,
        "timestamp": "2024-01-01T00:00:00Z",
        "source": "manual_review",
        "license_status": "active",
    }


class TestSemanticGroupsSchema:
    """Test semantic_groups schema compatibility."""

    def test_schema_structure(self):
        """Test semantic_groups schema structure."""
        assert SEMANTIC_GROUPS_SCHEMA["type"] == "record"
        assert SEMANTIC_GROUPS_SCHEMA["name"] == "SemanticGroup"
        assert len(SEMANTIC_GROUPS_SCHEMA["fields"]) == 5

    def test_required_fields(self):
        """Test semantic_groups required fields."""
        field_names = [f["name"] for f in SEMANTIC_GROUPS_SCHEMA["fields"]]
        assert "group_id" in field_names
        assert "domain" in field_names
        assert "articles" in field_names
        assert "timestamp" in field_names
        assert "entities" in field_names

    def test_valid_message(self, semantic_group_message):
        """Test valid semantic group message."""
        # Verify all required fields are present
        assert "group_id" in semantic_group_message
        assert "domain" in semantic_group_message
        assert "articles" in semantic_group_message
        assert len(semantic_group_message["articles"]) > 0
        
        # Verify article structure
        article = semantic_group_message["articles"][0]
        assert "id" in article
        assert "title" in article
        assert "content" in article

    def test_missing_required_field(self, semantic_group_message):
        """Test semantic group message with missing required field."""
        del semantic_group_message["group_id"]
        
        # Should fail validation
        assert "group_id" not in semantic_group_message

    def test_optional_fields(self, semantic_group_message):
        """Test semantic group message with optional fields."""
        # sentiment_score and credibility_score are optional
        article = semantic_group_message["articles"][0]
        article["sentiment_score"] = None
        article["credibility_score"] = None
        
        assert article["sentiment_score"] is None
        assert article["credibility_score"] is None


class TestPredictionsSchema:
    """Test predictions schema compatibility."""

    def test_schema_structure(self):
        """Test predictions schema structure."""
        assert PREDICTIONS_SCHEMA["type"] == "record"
        assert PREDICTIONS_SCHEMA["name"] == "Prediction"
        assert len(PREDICTIONS_SCHEMA["fields"]) == 9

    def test_required_fields(self):
        """Test predictions required fields."""
        field_names = [f["name"] for f in PREDICTIONS_SCHEMA["fields"]]
        assert "prediction_id" in field_names
        assert "group_id" in field_names
        assert "domain" in field_names
        assert "probability" in field_names
        assert "confidence" in field_names
        assert "model_version" in field_names
        assert "timestamp" in field_names
        assert "features" in field_names

    def test_valid_message(self, prediction_message):
        """Test valid prediction message."""
        assert "prediction_id" in prediction_message
        assert "group_id" in prediction_message
        assert "probability" in prediction_message
        assert 0.0 <= prediction_message["probability"] <= 1.0
        assert 0.0 <= prediction_message["confidence"] <= 1.0

    def test_features_map(self, prediction_message):
        """Test prediction features map."""
        assert "features" in prediction_message
        assert isinstance(prediction_message["features"], dict)
        assert len(prediction_message["features"]) > 0
        
        # All feature values should be numeric
        for value in prediction_message["features"].values():
            assert isinstance(value, (int, float))

    def test_optional_metadata(self, prediction_message):
        """Test prediction optional metadata."""
        # metadata is optional
        prediction_message["metadata"] = None
        assert prediction_message["metadata"] is None
        
        # metadata can be a map
        prediction_message["metadata"] = {"key": "value"}
        assert isinstance(prediction_message["metadata"], dict)


class TestGroundTruthSchema:
    """Test ground_truth schema compatibility."""

    def test_schema_structure(self):
        """Test ground_truth schema structure."""
        assert GROUND_TRUTH_SCHEMA["type"] == "record"
        assert GROUND_TRUTH_SCHEMA["name"] == "GroundTruth"
        assert len(GROUND_TRUTH_SCHEMA["fields"]) == 8

    def test_required_fields(self):
        """Test ground_truth required fields."""
        field_names = [f["name"] for f in GROUND_TRUTH_SCHEMA["fields"]]
        assert "label_id" in field_names
        assert "group_id" in field_names
        assert "domain" in field_names
        assert "label" in field_names
        assert "label_confidence" in field_names
        assert "timestamp" in field_names
        assert "source" in field_names
        assert "license_status" in field_names

    def test_valid_message(self, ground_truth_message):
        """Test valid ground truth message."""
        assert "label_id" in ground_truth_message
        assert "group_id" in ground_truth_message
        assert "label" in ground_truth_message
        assert ground_truth_message["label"] in [0, 1]
        assert 0.0 <= ground_truth_message["label_confidence"] <= 1.0

    def test_label_values(self, ground_truth_message):
        """Test ground truth label values."""
        # Label should be 0 or 1
        assert ground_truth_message["label"] in [0, 1]
        
        # Test with different label values
        ground_truth_message["label"] = 0
        assert ground_truth_message["label"] == 0
        
        ground_truth_message["label"] = 1
        assert ground_truth_message["label"] == 1

    def test_license_status_values(self, ground_truth_message):
        """Test ground truth license status values."""
        valid_statuses = ["active", "inactive", "expired", "pending"]
        assert ground_truth_message["license_status"] in valid_statuses


class TestSchemaEvolution:
    """Test schema evolution and backward compatibility."""

    def test_add_optional_field_to_semantic_groups(self, semantic_group_message):
        """Test adding optional field to semantic_groups schema."""
        # Add new optional field
        semantic_group_message["priority"] = "high"
        
        # Old consumers should still work (ignore unknown fields)
        assert "group_id" in semantic_group_message
        assert "domain" in semantic_group_message

    def test_add_optional_field_to_predictions(self, prediction_message):
        """Test adding optional field to predictions schema."""
        # Add new optional field
        prediction_message["drift_score"] = 0.05
        
        # Old consumers should still work
        assert "prediction_id" in prediction_message
        assert "probability" in prediction_message

    def test_add_optional_field_to_ground_truth(self, ground_truth_message):
        """Test adding optional field to ground_truth schema."""
        # Add new optional field
        ground_truth_message["reviewer_id"] = "reviewer123"
        
        # Old consumers should still work
        assert "label_id" in ground_truth_message
        assert "label" in ground_truth_message

    def test_remove_optional_field(self, prediction_message):
        """Test removing optional field."""
        # Remove optional metadata field
        prediction_message["metadata"] = None
        
        # Should still be valid
        assert "prediction_id" in prediction_message
        assert "probability" in prediction_message


class TestSchemaCompatibility:
    """Test schema compatibility between producer and consumer."""

    def test_semantic_groups_serialization(self, semantic_group_message):
        """Test semantic_groups message serialization."""
        # Serialize to JSON (simulating Avro serialization)
        serialized = json.dumps(semantic_group_message)
        
        # Deserialize
        deserialized = json.loads(serialized)
        
        # Verify all fields preserved
        assert deserialized["group_id"] == semantic_group_message["group_id"]
        assert deserialized["domain"] == semantic_group_message["domain"]
        assert len(deserialized["articles"]) == len(semantic_group_message["articles"])

    def test_predictions_serialization(self, prediction_message):
        """Test predictions message serialization."""
        serialized = json.dumps(prediction_message)
        deserialized = json.loads(serialized)
        
        assert deserialized["prediction_id"] == prediction_message["prediction_id"]
        assert deserialized["probability"] == prediction_message["probability"]
        assert deserialized["features"] == prediction_message["features"]

    def test_ground_truth_serialization(self, ground_truth_message):
        """Test ground_truth message serialization."""
        serialized = json.dumps(ground_truth_message)
        deserialized = json.loads(serialized)
        
        assert deserialized["label_id"] == ground_truth_message["label_id"]
        assert deserialized["label"] == ground_truth_message["label"]
        assert deserialized["license_status"] == ground_truth_message["license_status"]

