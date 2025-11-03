"""Tests for NER orchestrator."""

import pytest
from unittest.mock import Mock, MagicMock
from src.ner.orchestrator import NEROrchestrator
from src.ner.model_registry import NERModelRegistry
from src.exceptions import UnsupportedLanguageError, NERExtractionError


class TestNEROrchestrator:
    """Test NER orchestration."""

    @pytest.fixture
    def mock_registry(self):
        """Create mock model registry."""
        registry = Mock(spec=NERModelRegistry)
        registry.is_language_supported.return_value = True
        
        # Mock strategy
        strategy = Mock()
        strategy.extract_entities.return_value = [
            ("John Smith", "PERSON", 0, 10, 0.95),
            ("USA", "GPE", 20, 23, 0.92),
        ]
        strategy.get_model_name.return_value = "en_core_web_trf"
        
        registry.get_model.return_value = strategy
        return registry

    @pytest.fixture
    def orchestrator(self, mock_registry):
        """Create orchestrator with mock registry."""
        return NEROrchestrator(mock_registry)

    def test_extract_entities_success(self, orchestrator, mock_registry):
        """Test successful entity extraction."""
        text = "John Smith is from USA."
        result = orchestrator.extract_entities(text, "en", "article-123")
        
        assert len(result.entities) == 2
        assert result.entities[0].text == "John Smith"
        assert result.entities[0].entity_type == "PERSON"
        assert result.entities[1].text == "USA"
        assert result.entities[1].entity_type == "GPE"
        assert result.coverage_score > 0
        assert result.language == "en"

    def test_extract_entities_unsupported_language(self, orchestrator, mock_registry):
        """Test extraction with unsupported language."""
        mock_registry.is_language_supported.return_value = False
        
        with pytest.raises(UnsupportedLanguageError):
            orchestrator.extract_entities("Text", "xx", "article-123")

    def test_extract_context(self, orchestrator):
        """Test context extraction."""
        text = "John Smith is a famous person from USA."
        context = orchestrator._extract_context(text, 0, 10, window=10)
        
        assert "John Smith" in context
        assert len(context) > 0

    def test_calculate_coverage(self, orchestrator):
        """Test coverage calculation."""
        # Test with reasonable entity count
        coverage = orchestrator._calculate_coverage(5, 500, "en")
        assert 0 <= coverage <= 1.0
        
        # Test with zero text length
        coverage = orchestrator._calculate_coverage(0, 0, "en")
        assert coverage == 0.0

    def test_shutdown(self, orchestrator, mock_registry):
        """Test service shutdown."""
        orchestrator.shutdown()
        mock_registry.unload_all.assert_called_once()

