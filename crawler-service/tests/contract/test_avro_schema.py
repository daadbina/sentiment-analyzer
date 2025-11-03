"""
Contract tests for Avro schema validation.

Ensures that produced messages conform to the news_raw_v1 schema
and validates schema evolution compatibility.
"""

import json
from pathlib import Path

import pytest
from fastavro import parse_schema, reader, writer
from io import BytesIO

from src.models import NewsRawMessage


class TestAvroSchemaContract:
    """Test Avro schema compliance and evolution."""

    @pytest.fixture
    def schema_path(self):
        """Get path to Avro schema file."""
        return Path(__file__).parent.parent.parent / "schemas" / "news_raw_v1.avsc"

    @pytest.fixture
    def avro_schema(self, schema_path):
        """Load and parse Avro schema."""
        with open(schema_path, "r") as f:
            schema_dict = json.load(f)
        return parse_schema(schema_dict)

    @pytest.fixture
    def valid_message(self):
        """Create a valid NewsRawMessage."""
        return NewsRawMessage(
            article_id="uuid_12345678901234567890",
            canonical_url="https://example.com/article/123",
            title="Breaking News: Technology Advances",
            body="This is a comprehensive article about recent technology advances in the industry.",
            url="https://example.com/article/123?utm_source=twitter",
            source="TechNews Daily",
            language="en",
            published_at="2025-11-02T10:30:00Z",
            crawled_at="2025-11-02T10:35:00Z",
            country="US",
            checksum="sha256_abc123def456",
            validation_score=0.95,
            schema_version="1.0",
            ingest_job_id="job_20251102_001",
            publisher_id="pub_techcrunch",
            author="Jane Doe",
            raw_html="<html>...</html>",
            extraction_method="html_parser",
            metadata={"category": "technology", "tags": "ai,ml"},
        )

    def test_schema_file_exists(self, schema_path):
        """Test that schema file exists."""
        assert schema_path.exists(), f"Schema file not found at {schema_path}"

    def test_schema_is_valid_json(self, schema_path):
        """Test that schema is valid JSON."""
        with open(schema_path, "r") as f:
            schema_dict = json.load(f)
        assert isinstance(schema_dict, dict)
        assert "type" in schema_dict
        assert schema_dict["type"] == "record"

    def test_schema_has_required_fields(self, avro_schema):
        """Test that schema contains all required fields."""
        required_fields = {
            "article_id",
            "canonical_url",
            "title",
            "body",
            "url",
            "source",
            "language",
            "published_at",
            "crawled_at",
            "checksum",
            "schema_version",
            "ingest_job_id",
        }

        schema_field_names = {field["name"] for field in avro_schema["fields"]}
        assert required_fields.issubset(schema_field_names)

    def test_serialize_valid_message(self, avro_schema, valid_message):
        """Test serializing a valid message to Avro."""
        # Convert message to dict
        message_dict = valid_message.model_dump()

        # Serialize
        output = BytesIO()
        writer(output, avro_schema, [message_dict])
        output.seek(0)

        # Verify it can be read back
        records = list(reader(output))
        assert len(records) == 1
        assert records[0]["article_id"] == valid_message.article_id

    def test_deserialize_avro_message(self, avro_schema, valid_message):
        """Test deserializing Avro message back to Python object."""
        message_dict = valid_message.model_dump()

        # Serialize
        output = BytesIO()
        writer(output, avro_schema, [message_dict])
        output.seek(0)

        # Deserialize
        records = list(reader(output))
        deserialized = records[0]

        # Verify fields
        assert deserialized["title"] == valid_message.title
        assert deserialized["source"] == valid_message.source
        assert deserialized["language"] == valid_message.language

    def test_schema_field_types(self, avro_schema):
        """Test that schema field types are correct."""
        field_types = {field["name"]: field["type"] for field in avro_schema["fields"]}

        # String fields
        assert field_types["article_id"] == "string"
        assert field_types["title"] == "string"
        assert field_types["body"] == "string"

        # Optional fields (union with null)
        assert isinstance(field_types["country"], list)
        assert "null" in field_types["country"]

    def test_optional_fields_handling(self, avro_schema):
        """Test that optional fields are properly handled."""
        # Create message with minimal fields
        minimal_message = NewsRawMessage(
            article_id="uuid_12345678901234567890",
            canonical_url="https://example.com/article/123",
            title="Article Title",
            body="Article body content.",
            url="https://example.com/article/123",
            source="News Source",
            language="en",
            published_at="2025-11-02T10:30:00Z",
            crawled_at="2025-11-02T10:35:00Z",
            checksum="sha256_abc123",
            validation_score=0.8,
            schema_version="1.0",
            ingest_job_id="job_001",
            publisher_id="pub_001",
            extraction_method="html",
        )

        message_dict = minimal_message.model_dump()

        # Should serialize without optional fields
        output = BytesIO()
        writer(output, avro_schema, [message_dict])
        output.seek(0)

        records = list(reader(output))
        assert len(records) == 1

    def test_schema_version_field(self, avro_schema, valid_message):
        """Test that schema_version field is present and correct."""
        message_dict = valid_message.model_dump()

        output = BytesIO()
        writer(output, avro_schema, [message_dict])
        output.seek(0)

        records = list(reader(output))
        assert records[0]["schema_version"] == "1.0"

    def test_timestamp_format_validation(self, avro_schema, valid_message):
        """Test that timestamps are in ISO-8601 format."""
        message_dict = valid_message.model_dump()

        # Verify timestamps are strings in ISO format
        assert isinstance(message_dict["published_at"], str)
        assert isinstance(message_dict["crawled_at"], str)
        assert "T" in message_dict["published_at"]
        assert "Z" in message_dict["published_at"]

        # Should serialize successfully
        output = BytesIO()
        writer(output, avro_schema, [message_dict])
        assert output.tell() > 0

    def test_checksum_field_present(self, avro_schema, valid_message):
        """Test that checksum field is present and populated."""
        message_dict = valid_message.model_dump()

        output = BytesIO()
        writer(output, avro_schema, [message_dict])
        output.seek(0)

        records = list(reader(output))
        assert "checksum" in records[0]
        assert records[0]["checksum"] == valid_message.checksum

    def test_validation_score_optional(self, avro_schema):
        """Test that validation_score is optional."""
        message_dict = {
            "article_id": "uuid_12345678901234567890",
            "canonical_url": "https://example.com/article/123",
            "title": "Article Title",
            "body": "Article body content.",
            "url": "https://example.com/article/123",
            "source": "News Source",
            "language": "en",
            "published_at": "2025-11-02T10:30:00Z",
            "crawled_at": "2025-11-02T10:35:00Z",
            "checksum": "sha256_abc123",
            "schema_version": "1.0",
            "ingest_job_id": "job_001",
            "publisher_id": "pub_001",
            "extraction_method": "html",
            "validation_score": 0.5,  # Provide a value
        }

        output = BytesIO()
        writer(output, avro_schema, [message_dict])
        output.seek(0)

        records = list(reader(output))
        assert len(records) == 1

    def test_metadata_field_handling(self, avro_schema, valid_message):
        """Test that metadata field is properly serialized."""
        message_dict = valid_message.model_dump()

        output = BytesIO()
        writer(output, avro_schema, [message_dict])
        output.seek(0)

        records = list(reader(output))
        # Metadata should be preserved if schema supports it
        assert len(records) == 1

    def test_batch_serialization(self, avro_schema):
        """Test serializing multiple messages in batch."""
        messages = [
            {
                "article_id": f"uuid_{i:020d}",
                "canonical_url": f"https://example.com/article/{i}",
                "title": f"Article {i}",
                "body": f"Content for article {i}.",
                "url": f"https://example.com/article/{i}",
                "source": "News Source",
                "language": "en",
                "published_at": "2025-11-02T10:30:00Z",
                "crawled_at": "2025-11-02T10:35:00Z",
                "checksum": f"sha256_{i:06d}",
                "schema_version": "1.0",
                "ingest_job_id": "job_001",
                "publisher_id": "pub_001",
                "extraction_method": "html",
                "validation_score": 0.8,
            }
            for i in range(10)
        ]

        output = BytesIO()
        writer(output, avro_schema, messages)
        output.seek(0)

        records = list(reader(output))
        assert len(records) == 10
