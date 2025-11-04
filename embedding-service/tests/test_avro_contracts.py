"""Contract tests for Avro schemas."""

import pytest
import json
from fastavro import parse_schema, writer, reader
from io import BytesIO

pytestmark = pytest.mark.contract


# Avro schemas
NEWS_CANONICAL_SCHEMA = {
    "type": "record",
    "name": "NewsCanonical",
    "fields": [
        {"name": "article_id", "type": "string"},
        {"name": "title", "type": "string"},
        {"name": "content", "type": "string"},
        {"name": "language", "type": "string"},
        {"name": "source_url", "type": "string"},
        {"name": "published_at", "type": "long"},
        {"name": "crawled_at", "type": "long"},
    ],
}

EMBEDDINGS_SCHEMA = {
    "type": "record",
    "name": "Embeddings",
    "fields": [
        {"name": "article_id", "type": "string"},
        {"name": "embedding_model", "type": "string"},
        {"name": "embedding_dimension", "type": "int"},
        {"name": "language", "type": "string"},
        {"name": "created_at", "type": "long"},
        {"name": "processing_time_ms", "type": "int"},
    ],
}


@pytest.fixture
def parsed_news_schema():
    """Parse news canonical schema."""
    return parse_schema(NEWS_CANONICAL_SCHEMA)


@pytest.fixture
def parsed_embeddings_schema():
    """Parse embeddings schema."""
    return parse_schema(EMBEDDINGS_SCHEMA)


def test_news_canonical_schema_valid(parsed_news_schema):
    """Test news canonical schema is valid."""
    assert parsed_news_schema is not None
    assert parsed_news_schema["name"] == "NewsCanonical"
    assert len(parsed_news_schema["fields"]) == 7


def test_embeddings_schema_valid(parsed_embeddings_schema):
    """Test embeddings schema is valid."""
    assert parsed_embeddings_schema is not None
    assert parsed_embeddings_schema["name"] == "Embeddings"
    assert len(parsed_embeddings_schema["fields"]) == 6


def test_news_canonical_serialization(parsed_news_schema):
    """Test news canonical message serialization."""
    record = {
        "article_id": "article-123",
        "title": "Test Article",
        "content": "This is test content",
        "language": "en",
        "source_url": "https://example.com",
        "published_at": 1699000000000,
        "crawled_at": 1699000001000,
    }

    # Serialize
    fo = BytesIO()
    writer(fo, parsed_news_schema, [record])

    # Deserialize
    fo.seek(0)
    records = list(reader(fo))

    assert len(records) == 1
    assert records[0]["article_id"] == "article-123"
    assert records[0]["title"] == "Test Article"


def test_embeddings_serialization(parsed_embeddings_schema):
    """Test embeddings message serialization."""
    record = {
        "article_id": "article-123",
        "embedding_model": "all-MiniLM-L6-v2",
        "embedding_dimension": 384,
        "language": "en",
        "created_at": 1699000000000,
        "processing_time_ms": 150,
    }

    # Serialize
    fo = BytesIO()
    writer(fo, parsed_embeddings_schema, [record])

    # Deserialize
    fo.seek(0)
    records = list(reader(fo))

    assert len(records) == 1
    assert records[0]["article_id"] == "article-123"
    assert records[0]["embedding_model"] == "all-MiniLM-L6-v2"


def test_news_canonical_batch_serialization(parsed_news_schema):
    """Test batch serialization of news canonical messages."""
    records = [
        {
            "article_id": f"article-{i}",
            "title": f"Article {i}",
            "content": f"Content {i}",
            "language": "en",
            "source_url": f"https://example.com/{i}",
            "published_at": 1699000000000 + i * 1000,
            "crawled_at": 1699000001000 + i * 1000,
        }
        for i in range(10)
    ]

    # Serialize
    fo = BytesIO()
    writer(fo, parsed_news_schema, records)

    # Deserialize
    fo.seek(0)
    deserialized = list(reader(fo))

    assert len(deserialized) == 10
    for i, record in enumerate(deserialized):
        assert record["article_id"] == f"article-{i}"


def test_embeddings_batch_serialization(parsed_embeddings_schema):
    """Test batch serialization of embeddings messages."""
    records = [
        {
            "article_id": f"article-{i}",
            "embedding_model": "all-MiniLM-L6-v2",
            "embedding_dimension": 384,
            "language": "en",
            "created_at": 1699000000000 + i * 1000,
            "processing_time_ms": 100 + i * 10,
        }
        for i in range(10)
    ]

    # Serialize
    fo = BytesIO()
    writer(fo, parsed_embeddings_schema, records)

    # Deserialize
    fo.seek(0)
    deserialized = list(reader(fo))

    assert len(deserialized) == 10
    for i, record in enumerate(deserialized):
        assert record["article_id"] == f"article-{i}"


def test_schema_field_types(parsed_news_schema):
    """Test schema field types."""
    fields = {f["name"]: f["type"] for f in parsed_news_schema["fields"]}

    assert fields["article_id"] == "string"
    assert fields["title"] == "string"
    assert fields["content"] == "string"
    assert fields["language"] == "string"
    assert fields["source_url"] == "string"
    assert fields["published_at"] == "long"
    assert fields["crawled_at"] == "long"


def test_schema_compatibility():
    """Test schema compatibility."""
    # Original schema
    original = parse_schema(NEWS_CANONICAL_SCHEMA)

    # Extended schema (backward compatible)
    extended = {
        "type": "record",
        "name": "NewsCanonical",
        "fields": [
            {"name": "article_id", "type": "string"},
            {"name": "title", "type": "string"},
            {"name": "content", "type": "string"},
            {"name": "language", "type": "string"},
            {"name": "source_url", "type": "string"},
            {"name": "published_at", "type": "long"},
            {"name": "crawled_at", "type": "long"},
            {"name": "updated_at", "type": ["null", "long"], "default": None},
        ],
    }

    extended_parsed = parse_schema(extended)

    # Both should be valid
    assert original is not None
    assert extended_parsed is not None


def test_invalid_record_fails(parsed_news_schema):
    """Test that invalid records fail serialization."""
    # Missing required field
    invalid_record = {
        "article_id": "article-123",
        "title": "Test Article",
        # Missing content, language, source_url, published_at, crawled_at
    }

    fo = BytesIO()

    with pytest.raises(Exception):
        writer(fo, parsed_news_schema, [invalid_record])


def test_schema_evolution():
    """Test schema evolution."""
    # Version 1
    schema_v1 = parse_schema(NEWS_CANONICAL_SCHEMA)

    # Version 2 (with optional field)
    schema_v2_def = {
        "type": "record",
        "name": "NewsCanonical",
        "fields": [
            {"name": "article_id", "type": "string"},
            {"name": "title", "type": "string"},
            {"name": "content", "type": "string"},
            {"name": "language", "type": "string"},
            {"name": "source_url", "type": "string"},
            {"name": "published_at", "type": "long"},
            {"name": "crawled_at", "type": "long"},
            {"name": "author", "type": ["null", "string"], "default": None},
        ],
    }

    schema_v2 = parse_schema(schema_v2_def)

    # Both should be valid
    assert schema_v1 is not None
    assert schema_v2 is not None

