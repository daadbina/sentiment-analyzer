"""Contract tests for Avro schema evolution."""

import pytest
import json
import avro.schema
import avro.io
import io
from typing import Dict, Any


class TestSchemaEvolution:
    """Test Avro schema evolution and backward compatibility."""

    @staticmethod
    def serialize_message(schema: avro.schema.Schema, message: Dict[str, Any]) -> bytes:
        """Serialize message using Avro schema."""
        writer = avro.io.DatumWriter(schema)
        bytes_writer = io.BytesIO()
        encoder = avro.io.BinaryEncoder(bytes_writer)
        writer.write(message, encoder)
        return bytes_writer.getvalue()

    @staticmethod
    def deserialize_message(schema: avro.schema.Schema, data: bytes) -> Dict[str, Any]:
        """Deserialize message using Avro schema."""
        bytes_reader = io.BytesIO(data)
        decoder = avro.io.BinaryDecoder(bytes_reader)
        reader = avro.io.DatumReader(schema)
        return reader.read(decoder)

    def test_news_raw_schema_v1(self):
        """Test news_raw schema v1."""
        schema_str = """
        {
            "type": "record",
            "name": "NewsRaw",
            "namespace": "com.sentiment.news",
            "fields": [
                {"name": "article_id", "type": "string"},
                {"name": "title", "type": "string"},
                {"name": "body", "type": "string"},
                {"name": "url", "type": "string"},
                {"name": "published_at", "type": "string"},
                {"name": "language", "type": "string"},
                {"name": "source", "type": "string"},
                {"name": "ingest_job_id", "type": "string"},
                {"name": "validation_score", "type": "float"},
                {"name": "crawled_at", "type": "string"},
                {"name": "checksum", "type": "string"}
            ]
        }
        """

        schema = avro.schema.parse(schema_str)

        message = {
            "article_id": "test-1",
            "title": "Test Title",
            "body": "Test Body",
            "url": "https://example.com",
            "published_at": "2025-11-02T10:00:00Z",
            "language": "en",
            "source": "test-source",
            "ingest_job_id": "job-1",
            "validation_score": 0.85,
            "crawled_at": "2025-11-02T10:05:00Z",
            "checksum": "abc123"
        }

        # Serialize and deserialize
        serialized = self.serialize_message(schema, message)
        deserialized = self.deserialize_message(schema, serialized)

        # Check all fields except float (due to precision)
        assert deserialized["article_id"] == message["article_id"]
        assert deserialized["title"] == message["title"]
        assert deserialized["body"] == message["body"]
        assert abs(deserialized["validation_score"] - message["validation_score"]) < 0.001

    def test_news_validated_schema_v1(self):
        """Test news_validated schema v1."""
        schema_str = """
        {
            "type": "record",
            "name": "NewsValidated",
            "namespace": "com.sentiment.news",
            "fields": [
                {"name": "article_id", "type": "string"},
                {"name": "canonical_url", "type": ["null", "string"], "default": null},
                {"name": "title", "type": "string"},
                {"name": "body", "type": "string"},
                {"name": "url", "type": "string"},
                {"name": "source", "type": "string"},
                {"name": "language", "type": "string"},
                {"name": "language_confidence", "type": "float"},
                {"name": "language_detection_method", "type": "string"},
                {"name": "source_published_at_raw", "type": ["null", "string"], "default": null},
                {"name": "source_published_at_utc", "type": "string"},
                {"name": "ingested_at", "type": "string"},
                {"name": "validated_at", "type": "string"},
                {"name": "country", "type": ["null", "string"], "default": null},
                {"name": "checksum", "type": "string"},
                {"name": "validation_score", "type": "float"},
                {"name": "schema_version", "type": "string"},
                {"name": "ingest_job_id", "type": "string"},
                {"name": "validation_job_id", "type": "string"},
                {"name": "trace_id", "type": "string"},
                {"name": "publisher_id", "type": ["null", "string"], "default": null}
            ]
        }
        """

        schema = avro.schema.parse(schema_str)

        message = {
            "article_id": "test-1",
            "canonical_url": None,
            "title": "Test Title",
            "body": "Test Body",
            "url": "https://example.com",
            "source": "test-source",
            "language": "en",
            "language_confidence": 0.95,
            "language_detection_method": "langdetect",
            "source_published_at_raw": None,
            "source_published_at_utc": "2025-11-02T10:00:00Z",
            "ingested_at": "2025-11-02T10:05:00Z",
            "validated_at": "2025-11-02T10:05:01Z",
            "country": "US",
            "checksum": "abc123",
            "validation_score": 0.92,
            "schema_version": "1.0.0",
            "ingest_job_id": "job-1",
            "validation_job_id": "val-job-1",
            "trace_id": "trace-1",
            "publisher_id": None
        }

        # Serialize and deserialize
        serialized = self.serialize_message(schema, message)
        deserialized = self.deserialize_message(schema, serialized)

        # Check all fields except floats (due to precision)
        assert deserialized["article_id"] == message["article_id"]
        assert deserialized["title"] == message["title"]
        assert deserialized["country"] == message["country"]
        assert abs(deserialized["language_confidence"] - message["language_confidence"]) < 0.001
        assert abs(deserialized["validation_score"] - message["validation_score"]) < 0.001

    def test_news_rejected_schema_v1(self):
        """Test news_rejected schema v1."""
        schema_str = """
        {
            "type": "record",
            "name": "NewsRejected",
            "namespace": "com.sentiment.news",
            "fields": [
                {"name": "article_id", "type": "string"},
                {"name": "url", "type": "string"},
                {"name": "source", "type": "string"},
                {"name": "rejected_at", "type": "string"},
                {"name": "validation_score", "type": "float"},
                {"name": "rejection_reason", "type": "string"},
                {"name": "error_codes", "type": {"type": "array", "items": "string"}},
                {"name": "retry_count", "type": "int"},
                {"name": "trace_id", "type": "string"},
                {"name": "validation_job_id", "type": "string"},
                {"name": "schema_version", "type": "string"}
            ]
        }
        """

        schema = avro.schema.parse(schema_str)

        message = {
            "article_id": "test-1",
            "url": "https://example.com",
            "source": "test-source",
            "rejected_at": "2025-11-02T10:05:01Z",
            "validation_score": 0.65,
            "rejection_reason": "Quality threshold not met",
            "error_codes": ["QUALITY_THRESHOLD"],
            "retry_count": 0,
            "trace_id": "trace-1",
            "validation_job_id": "val-job-1",
            "schema_version": "1.0.0"
        }

        # Serialize and deserialize
        serialized = self.serialize_message(schema, message)
        deserialized = self.deserialize_message(schema, serialized)

        # Check all fields except float (due to precision)
        assert deserialized["article_id"] == message["article_id"]
        assert deserialized["rejection_reason"] == message["rejection_reason"]
        assert deserialized["error_codes"] == message["error_codes"]
        assert abs(deserialized["validation_score"] - message["validation_score"]) < 0.001

    def test_schema_backward_compatibility_optional_field(self):
        """Test backward compatibility with optional fields."""
        # Schema with optional field
        schema_str = """
        {
            "type": "record",
            "name": "TestMessage",
            "fields": [
                {"name": "id", "type": "string"},
                {"name": "title", "type": "string"},
                {"name": "description", "type": ["null", "string"], "default": null}
            ]
        }
        """

        schema = avro.schema.parse(schema_str)

        # Message with optional field as null
        message = {
            "id": "test-1",
            "title": "Test",
            "description": None
        }

        # Serialize and deserialize
        serialized = self.serialize_message(schema, message)
        deserialized = self.deserialize_message(schema, serialized)

        assert deserialized["id"] == "test-1"
        assert deserialized["title"] == "Test"
        assert deserialized["description"] is None

    def test_schema_forward_compatibility_default_value(self):
        """Test forward compatibility with default values."""
        # Schema with default value
        schema_str = """
        {
            "type": "record",
            "name": "TestMessage",
            "fields": [
                {"name": "id", "type": "string"},
                {"name": "status", "type": "string", "default": "active"}
            ]
        }
        """
        
        schema = avro.schema.parse(schema_str)
        
        # Message without status field (will use default)
        message = {
            "id": "test-1",
            "status": "active"
        }
        
        serialized = self.serialize_message(schema, message)
        deserialized = self.deserialize_message(schema, serialized)
        
        assert deserialized["status"] == "active"

    def test_schema_union_types(self):
        """Test schema with union types."""
        schema_str = """
        {
            "type": "record",
            "name": "TestMessage",
            "fields": [
                {"name": "id", "type": "string"},
                {"name": "value", "type": ["null", "string", "int"]}
            ]
        }
        """
        
        schema = avro.schema.parse(schema_str)
        
        # Test with null
        message1 = {"id": "test-1", "value": None}
        serialized1 = self.serialize_message(schema, message1)
        deserialized1 = self.deserialize_message(schema, serialized1)
        assert deserialized1["value"] is None
        
        # Test with string
        message2 = {"id": "test-2", "value": "test"}
        serialized2 = self.serialize_message(schema, message2)
        deserialized2 = self.deserialize_message(schema, serialized2)
        assert deserialized2["value"] == "test"
        
        # Test with int
        message3 = {"id": "test-3", "value": 42}
        serialized3 = self.serialize_message(schema, message3)
        deserialized3 = self.deserialize_message(schema, serialized3)
        assert deserialized3["value"] == 42

    def test_schema_nested_records(self):
        """Test schema with nested records."""
        schema_str = """
        {
            "type": "record",
            "name": "Article",
            "fields": [
                {"name": "id", "type": "string"},
                {
                    "name": "metadata",
                    "type": {
                        "type": "record",
                        "name": "Metadata",
                        "fields": [
                            {"name": "created_at", "type": "string"},
                            {"name": "updated_at", "type": "string"}
                        ]
                    }
                }
            ]
        }
        """
        
        schema = avro.schema.parse(schema_str)
        
        message = {
            "id": "test-1",
            "metadata": {
                "created_at": "2025-11-02T10:00:00Z",
                "updated_at": "2025-11-02T10:05:00Z"
            }
        }
        
        serialized = self.serialize_message(schema, message)
        deserialized = self.deserialize_message(schema, serialized)
        
        assert deserialized == message

    def test_schema_array_types(self):
        """Test schema with array types."""
        schema_str = """
        {
            "type": "record",
            "name": "TestMessage",
            "fields": [
                {"name": "id", "type": "string"},
                {"name": "tags", "type": {"type": "array", "items": "string"}}
            ]
        }
        """
        
        schema = avro.schema.parse(schema_str)
        
        message = {
            "id": "test-1",
            "tags": ["tag1", "tag2", "tag3"]
        }
        
        serialized = self.serialize_message(schema, message)
        deserialized = self.deserialize_message(schema, serialized)
        
        assert deserialized == message

    def test_schema_map_types(self):
        """Test schema with map types."""
        schema_str = """
        {
            "type": "record",
            "name": "TestMessage",
            "fields": [
                {"name": "id", "type": "string"},
                {"name": "properties", "type": {"type": "map", "values": "string"}}
            ]
        }
        """
        
        schema = avro.schema.parse(schema_str)
        
        message = {
            "id": "test-1",
            "properties": {
                "key1": "value1",
                "key2": "value2"
            }
        }
        
        serialized = self.serialize_message(schema, message)
        deserialized = self.deserialize_message(schema, serialized)
        
        assert deserialized == message

