"""Tests for entity normalizer."""

import pytest
from src.normalization.entity_normalizer import EntityNormalizer


class TestEntityNormalizer:
    """Test entity normalization."""

    def test_normalize_basic(self):
        """Test basic normalization."""
        text = "John Smith"
        normalized = EntityNormalizer.normalize(text)
        assert normalized == "john smith"

    def test_normalize_with_accents(self):
        """Test normalization with accents."""
        text = "José García"
        normalized = EntityNormalizer.normalize(text)
        assert "jose" in normalized.lower()
        assert "garcia" in normalized.lower()

    def test_normalize_with_abbreviations(self):
        """Test normalization with abbreviations."""
        text = "dr. john smith"
        normalized = EntityNormalizer.normalize(text)
        assert "doctor" in normalized

    def test_normalize_whitespace(self):
        """Test whitespace normalization."""
        text = "John    Smith"
        normalized = EntityNormalizer.normalize(text)
        assert normalized == "john smith"

    def test_extract_aliases_parenthetical(self):
        """Test extracting parenthetical aliases."""
        text = "United States (USA)"
        aliases = EntityNormalizer.extract_aliases(text)
        assert "USA" in aliases

    def test_extract_aliases_acronyms(self):
        """Test extracting acronyms."""
        text = "United Nations Organization (UNO)"
        aliases = EntityNormalizer.extract_aliases(text)
        assert "UNO" in aliases

    def test_normalize_type_person(self):
        """Test entity type normalization for PERSON."""
        assert EntityNormalizer.normalize_type("PER") == "PERSON"
        assert EntityNormalizer.normalize_type("PERSON") == "PERSON"

    def test_normalize_type_organization(self):
        """Test entity type normalization for ORGANIZATION."""
        assert EntityNormalizer.normalize_type("ORG") == "ORGANIZATION"
        assert EntityNormalizer.normalize_type("ORGANIZATION") == "ORGANIZATION"

    def test_is_valid_entity_valid(self):
        """Test valid entity detection."""
        assert EntityNormalizer.is_valid_entity("John Smith") is True
        assert EntityNormalizer.is_valid_entity("USA") is True

    def test_is_valid_entity_invalid(self):
        """Test invalid entity detection."""
        assert EntityNormalizer.is_valid_entity("") is False
        assert EntityNormalizer.is_valid_entity("a") is False
        assert EntityNormalizer.is_valid_entity("123") is False
        assert EntityNormalizer.is_valid_entity("...") is False

