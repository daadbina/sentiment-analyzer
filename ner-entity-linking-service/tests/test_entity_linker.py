"""Tests for entity linker."""

import pytest
from unittest.mock import Mock
from src.linking.entity_linker import EntityLinker
from src.models import Entity, EntityType


class TestEntityLinker:
    """Test entity linking."""

    @pytest.fixture
    def mock_wikidata_client(self):
        """Create mock Wikidata client."""
        client = Mock()
        client.search_entity.return_value = {
            "wikidata_id": "Q30",
            "label": "United States",
            "description": "Country in North America",
            "country": "USA",
        }
        return client

    @pytest.fixture
    def linker(self, mock_wikidata_client):
        """Create entity linker with mock client."""
        return EntityLinker(mock_wikidata_client)

    def test_link_entity_success(self, linker):
        """Test successful entity linking."""
        entity = Entity(
            entity_id="ent-1",
            text="United States",
            normalized_text="united states",
            entity_type=EntityType.GPE,
            start_char=0,
            end_char=13,
            confidence=0.95,
            context_snippet="The United States is a country",
        )

        linked = linker.link_entity(entity)

        assert linked.wikidata_id == "Q30"
        assert linked.country == "USA"

    def test_link_entity_not_found(self, linker, mock_wikidata_client):
        """Test entity linking when not found."""
        mock_wikidata_client.search_entity.return_value = None

        entity = Entity(
            entity_id="ent-1",
            text="Unknown Entity",
            normalized_text="unknown entity",
            entity_type=EntityType.PERSON,
            start_char=0,
            end_char=14,
            confidence=0.85,
            context_snippet="Unknown Entity was mentioned",
        )

        linked = linker.link_entity(entity)

        assert linked.wikidata_id is None

    def test_link_multiple_entities(self, linker):
        """Test linking multiple entities."""
        entities = [
            Entity(
                entity_id="ent-1",
                text="USA",
                normalized_text="usa",
                entity_type=EntityType.GPE,
                start_char=0,
                end_char=3,
                confidence=0.95,
                context_snippet="USA is a country",
            ),
            Entity(
                entity_id="ent-2",
                text="John Smith",
                normalized_text="john smith",
                entity_type=EntityType.PERSON,
                start_char=10,
                end_char=20,
                confidence=0.90,
                context_snippet="John Smith is a person",
            ),
        ]

        linked_entities, success_rate = linker.link_entities(entities)

        assert len(linked_entities) == 2
        assert success_rate > 0

    def test_link_entities_empty_list(self, linker):
        """Test linking empty entity list."""
        linked_entities, success_rate = linker.link_entities([])
        
        assert len(linked_entities) == 0
        assert success_rate == 0.0

