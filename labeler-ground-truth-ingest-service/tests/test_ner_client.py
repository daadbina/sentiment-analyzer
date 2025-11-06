"""Unit tests for NER client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.clients.ner_client import NERClient


class TestNERClient:
    """Test NER client for country extraction."""

    def test_ner_client_initialization(self):
        """Test NER client initialization."""
        with patch('src.clients.ner_client.NERClient.__init__', return_value=None):
            client = NERClient()
            assert client is not None

    @pytest.mark.asyncio
    async def test_extract_countries_empty_text(self):
        """Test country extraction with empty text."""
        with patch('src.clients.ner_client.NERClient.__init__', return_value=None):
            client = NERClient()
            client.orchestrator = None
            
            result = await client.extract_countries("", language="en")
            assert result == []

    @pytest.mark.asyncio
    async def test_extract_countries_with_mock_ner(self):
        """Test country extraction with mocked NER orchestrator."""
        with patch('src.clients.ner_client.NERClient.__init__', return_value=None):
            client = NERClient()
            
            # Mock NER result
            mock_entity = MagicMock()
            mock_entity.text = "Syria"
            mock_entity.entity_type = "LOCATION"
            mock_entity.confidence = 0.95
            
            mock_result = MagicMock()
            mock_result.entities = [mock_entity]
            mock_result.coverage_score = 0.85
            mock_result.extraction_duration_ms = 100
            
            mock_orchestrator = MagicMock()
            mock_orchestrator.extract_entities = MagicMock(return_value=mock_result)
            client.orchestrator = mock_orchestrator
            
            result = await client.extract_countries(
                "Conflict in Syria",
                language="en",
                article_id="test_article"
            )
            
            assert len(result) == 1
            assert result[0] == "Syria"

    @pytest.mark.asyncio
    async def test_extract_countries_multiple(self):
        """Test country extraction with multiple countries."""
        with patch('src.clients.ner_client.NERClient.__init__', return_value=None):
            client = NERClient()
            
            # Mock multiple entities
            mock_entity1 = MagicMock()
            mock_entity1.text = "Syria"
            mock_entity1.entity_type = "LOCATION"
            mock_entity1.confidence = 0.95
            
            mock_entity2 = MagicMock()
            mock_entity2.text = "Turkey"
            mock_entity2.entity_type = "GPE"
            mock_entity2.confidence = 0.92
            
            mock_result = MagicMock()
            mock_result.entities = [mock_entity1, mock_entity2]
            mock_result.coverage_score = 0.85
            mock_result.extraction_duration_ms = 100
            
            mock_orchestrator = MagicMock()
            mock_orchestrator.extract_entities = MagicMock(return_value=mock_result)
            client.orchestrator = mock_orchestrator
            
            result = await client.extract_countries(
                "Conflict between Syria and Turkey",
                language="en"
            )
            
            assert len(result) == 2
            assert "Syria" in result
            assert "Turkey" in result

    @pytest.mark.asyncio
    async def test_extract_countries_filters_non_location(self):
        """Test that non-location entities are filtered out."""
        with patch('src.clients.ner_client.NERClient.__init__', return_value=None):
            client = NERClient()
            
            # Mock mixed entity types
            mock_entity1 = MagicMock()
            mock_entity1.text = "Syria"
            mock_entity1.entity_type = "LOCATION"
            mock_entity1.confidence = 0.95
            
            mock_entity2 = MagicMock()
            mock_entity2.text = "John Smith"
            mock_entity2.entity_type = "PERSON"
            mock_entity2.confidence = 0.90
            
            mock_result = MagicMock()
            mock_result.entities = [mock_entity1, mock_entity2]
            mock_result.coverage_score = 0.85
            mock_result.extraction_duration_ms = 100
            
            mock_orchestrator = MagicMock()
            mock_orchestrator.extract_entities = MagicMock(return_value=mock_result)
            client.orchestrator = mock_orchestrator
            
            result = await client.extract_countries(
                "John Smith in Syria",
                language="en"
            )
            
            assert len(result) == 1
            assert result[0] == "Syria"

    @pytest.mark.asyncio
    async def test_extract_countries_from_title(self):
        """Test country extraction from title only."""
        with patch('src.clients.ner_client.NERClient.__init__', return_value=None):
            client = NERClient()
            
            mock_entity = MagicMock()
            mock_entity.text = "Iran"
            mock_entity.entity_type = "GPE"
            mock_entity.confidence = 0.93
            
            mock_result = MagicMock()
            mock_result.entities = [mock_entity]
            mock_result.coverage_score = 0.80
            mock_result.extraction_duration_ms = 50
            
            mock_orchestrator = MagicMock()
            mock_orchestrator.extract_entities = MagicMock(return_value=mock_result)
            client.orchestrator = mock_orchestrator
            
            result = await client.extract_countries_from_title(
                "Tensions rise in Iran",
                language="en"
            )
            
            assert len(result) == 1
            assert result[0] == "Iran"

    @pytest.mark.asyncio
    async def test_extract_countries_combined_deduplication(self):
        """Test combined extraction with deduplication."""
        with patch('src.clients.ner_client.NERClient.__init__', return_value=None):
            client = NERClient()
            
            # Mock orchestrator
            mock_orchestrator = MagicMock()
            client.orchestrator = mock_orchestrator
            
            # Mock extract_countries_from_title
            async def mock_extract_title(*args, **kwargs):
                return ["Syria", "Turkey"]
            
            # Mock extract_countries_from_content
            async def mock_extract_content(*args, **kwargs):
                return ["Turkey", "Iran"]  # Turkey is duplicate
            
            client.extract_countries_from_title = mock_extract_title
            client.extract_countries_from_content = mock_extract_content
            
            result = await client.extract_countries_combined(
                title="Conflict in Syria and Turkey",
                content="Turkey and Iran tensions",
                language="en"
            )
            
            # Should have 3 unique countries (Syria, Turkey, Iran)
            assert len(result) == 3
            assert "Syria" in result
            assert "Turkey" in result
            assert "Iran" in result

    @pytest.mark.asyncio
    async def test_extract_countries_error_handling(self):
        """Test error handling in country extraction."""
        with patch('src.clients.ner_client.NERClient.__init__', return_value=None):
            client = NERClient()
            
            # Mock orchestrator that raises exception
            mock_orchestrator = MagicMock()
            mock_orchestrator.extract_entities = MagicMock(
                side_effect=Exception("NER extraction failed")
            )
            client.orchestrator = mock_orchestrator
            
            result = await client.extract_countries(
                "Some text",
                language="en"
            )
            
            # Should return empty list on error
            assert result == []

    @pytest.mark.asyncio
    async def test_extract_countries_enum_entity_type(self):
        """Test handling of enum entity types."""
        with patch('src.clients.ner_client.NERClient.__init__', return_value=None):
            client = NERClient()
            
            # Mock entity with enum-like entity_type
            mock_entity = MagicMock()
            mock_entity.text = "Egypt"
            mock_entity.entity_type = MagicMock()
            mock_entity.entity_type.value = "LOCATION"
            mock_entity.confidence = 0.94
            
            mock_result = MagicMock()
            mock_result.entities = [mock_entity]
            mock_result.coverage_score = 0.85
            mock_result.extraction_duration_ms = 100
            
            mock_orchestrator = MagicMock()
            mock_orchestrator.extract_entities = MagicMock(return_value=mock_result)
            client.orchestrator = mock_orchestrator
            
            result = await client.extract_countries(
                "Conflict in Egypt",
                language="en"
            )
            
            assert len(result) == 1
            assert result[0] == "Egypt"

