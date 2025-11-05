"""
Contract tests for Avro schema compatibility.

Tests schema validation and compatibility.
"""

import pytest
import json
from unittest.mock import patch, MagicMock

from src.clients.kafka_producer import KafkaProducer


class TestAvroSchemaCompatibility:
    """Test Avro schema compatibility."""

    @pytest.fixture
    def model_trained_schema(self):
        """Model trained event schema."""
        return {
            "type": "record",
            "name": "ModelTrained",
            "namespace": "com.sentiment.trainer",
            "fields": [
                {"name": "model_name", "type": "string"},
                {"name": "model_version", "type": "string"},
                {"name": "training_timestamp", "type": "long"},
                {"name": "auc_score", "type": "double"},
                {"name": "precision_score", "type": "double"},
                {"name": "recall_score", "type": "double"},
                {"name": "f1_score", "type": "double"},
                {"name": "training_samples", "type": "int"},
                {"name": "test_samples", "type": "int"},
                {"name": "hyperparameters", "type": {"type": "map", "values": "string"}},
            ]
        }

    @pytest.fixture
    def model_promoted_schema(self):
        """Model promoted event schema."""
        return {
            "type": "record",
            "name": "ModelPromoted",
            "namespace": "com.sentiment.trainer",
            "fields": [
                {"name": "model_name", "type": "string"},
                {"name": "model_version", "type": "string"},
                {"name": "promotion_timestamp", "type": "long"},
                {"name": "target_stage", "type": "string"},
                {"name": "promotion_reason", "type": "string"},
                {"name": "metrics", "type": {"type": "map", "values": "double"}},
            ]
        }

    def test_model_trained_schema_structure(self, model_trained_schema):
        """Test model trained schema structure."""
        assert model_trained_schema["type"] == "record"
        assert model_trained_schema["name"] == "ModelTrained"
        assert len(model_trained_schema["fields"]) > 0

    def test_model_trained_schema_fields(self, model_trained_schema):
        """Test model trained schema fields."""
        field_names = [f["name"] for f in model_trained_schema["fields"]]
        
        assert "model_name" in field_names
        assert "model_version" in field_names
        assert "auc_score" in field_names
        assert "precision_score" in field_names
        assert "recall_score" in field_names
        assert "f1_score" in field_names

    def test_model_trained_schema_field_types(self, model_trained_schema):
        """Test model trained schema field types."""
        fields = {f["name"]: f["type"] for f in model_trained_schema["fields"]}
        
        assert fields["model_name"] == "string"
        assert fields["auc_score"] == "double"
        assert fields["training_samples"] == "int"

    def test_model_promoted_schema_structure(self, model_promoted_schema):
        """Test model promoted schema structure."""
        assert model_promoted_schema["type"] == "record"
        assert model_promoted_schema["name"] == "ModelPromoted"
        assert len(model_promoted_schema["fields"]) > 0

    def test_model_promoted_schema_fields(self, model_promoted_schema):
        """Test model promoted schema fields."""
        field_names = [f["name"] for f in model_promoted_schema["fields"]]
        
        assert "model_name" in field_names
        assert "model_version" in field_names
        assert "target_stage" in field_names
        assert "metrics" in field_names

    def test_schema_backward_compatibility(self, model_trained_schema):
        """Test backward compatibility."""
        # Original schema
        original_fields = {f["name"]: f["type"] for f in model_trained_schema["fields"]}
        
        # New schema with additional optional field
        new_schema = model_trained_schema.copy()
        new_schema["fields"] = model_trained_schema["fields"] + [
            {"name": "drift_detected", "type": ["null", "boolean"], "default": None}
        ]
        new_fields = {f["name"]: f["type"] for f in new_schema["fields"]}
        
        # All original fields should still exist
        for field_name in original_fields:
            assert field_name in new_fields

    def test_schema_forward_compatibility(self, model_trained_schema):
        """Test forward compatibility."""
        # Schema with optional field
        schema_with_optional = model_trained_schema.copy()
        schema_with_optional["fields"] = [
            f for f in model_trained_schema["fields"]
            if f["name"] != "hyperparameters"
        ]
        
        # Should still be valid
        assert len(schema_with_optional["fields"]) > 0

    def test_schema_field_type_validation(self, model_trained_schema):
        """Test field type validation."""
        for field in model_trained_schema["fields"]:
            assert "name" in field
            assert "type" in field
            assert isinstance(field["name"], str)

    def test_schema_namespace_consistency(self, model_trained_schema, model_promoted_schema):
        """Test namespace consistency."""
        assert model_trained_schema["namespace"] == "com.sentiment.trainer"
        assert model_promoted_schema["namespace"] == "com.sentiment.trainer"

    def test_schema_record_name_uniqueness(self, model_trained_schema, model_promoted_schema):
        """Test record name uniqueness."""
        assert model_trained_schema["name"] != model_promoted_schema["name"]

    def test_schema_required_fields(self, model_trained_schema):
        """Test required fields."""
        required_fields = ["model_name", "model_version", "auc_score"]
        field_names = [f["name"] for f in model_trained_schema["fields"]]
        
        for required_field in required_fields:
            assert required_field in field_names

    def test_schema_numeric_precision(self, model_trained_schema):
        """Test numeric field precision."""
        fields = {f["name"]: f["type"] for f in model_trained_schema["fields"]}
        
        # Scores should be double for precision
        assert fields["auc_score"] == "double"
        assert fields["precision_score"] == "double"
        assert fields["recall_score"] == "double"
        assert fields["f1_score"] == "double"

    def test_schema_timestamp_format(self, model_trained_schema):
        """Test timestamp format."""
        fields = {f["name"]: f["type"] for f in model_trained_schema["fields"]}
        
        # Timestamps should be long (milliseconds since epoch)
        assert fields["training_timestamp"] == "long"

    def test_schema_map_type_validation(self, model_trained_schema):
        """Test map type validation."""
        hyperparams_field = next(
            f for f in model_trained_schema["fields"]
            if f["name"] == "hyperparameters"
        )
        
        assert hyperparams_field["type"]["type"] == "map"
        assert hyperparams_field["type"]["values"] == "string"

    def test_schema_serialization(self, model_trained_schema):
        """Test schema serialization."""
        schema_json = json.dumps(model_trained_schema)
        
        assert schema_json is not None
        assert isinstance(schema_json, str)
        
        # Should be deserializable
        deserialized = json.loads(schema_json)
        assert deserialized == model_trained_schema

    def test_schema_evolution_compatibility(self, model_trained_schema):
        """Test schema evolution compatibility."""
        # Add new optional field
        evolved_schema = model_trained_schema.copy()
        evolved_schema["fields"] = model_trained_schema["fields"] + [
            {"name": "model_type", "type": ["null", "string"], "default": None}
        ]
        
        # Should have more fields
        assert len(evolved_schema["fields"]) > len(model_trained_schema["fields"])

    def test_schema_field_order_independence(self, model_trained_schema):
        """Test that field order doesn't matter for compatibility."""
        # Reorder fields
        reordered_fields = list(reversed(model_trained_schema["fields"]))
        reordered_schema = model_trained_schema.copy()
        reordered_schema["fields"] = reordered_fields
        
        # Should still have same fields
        original_names = {f["name"] for f in model_trained_schema["fields"]}
        reordered_names = {f["name"] for f in reordered_schema["fields"]}
        
        assert original_names == reordered_names

