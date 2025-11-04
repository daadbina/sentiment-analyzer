"""
Tests for advanced features (DBpedia, OpenSanctions, relationships, co-occurrence).
"""
import pytest
from src.linking.dbpedia_client import DBpediaSpotlightClient
from src.linking.opensanctions_client import OpenSanctionsClient
from src.extraction.relationship_extractor import RelationshipExtractor
from src.analysis.cooccurrence_analyzer import CooccurrenceAnalyzer


class TestDBpediaSpotlightClient:
    """Tests for DBpedia Spotlight client."""

    @pytest.fixture
    def client(self):
        """Create DBpedia client."""
        return DBpediaSpotlightClient()

    def test_client_initialization(self, client):
        """Test client initialization."""
        assert client.base_url == "https://api.dbpedia-spotlight.org"
        assert client.timeout == 10

    def test_extract_entities_method_exists(self, client):
        """Test extract_entities method exists."""
        assert hasattr(client, "extract_entities")

    def test_link_entity_method_exists(self, client):
        """Test link_entity method exists."""
        assert hasattr(client, "link_entity")

    def test_get_entity_info_method_exists(self, client):
        """Test get_entity_info method exists."""
        assert hasattr(client, "get_entity_info")


class TestOpenSanctionsClient:
    """Tests for OpenSanctions client."""

    @pytest.fixture
    def client(self):
        """Create OpenSanctions client."""
        return OpenSanctionsClient()

    def test_client_initialization(self, client):
        """Test client initialization."""
        assert client.base_url == "https://api.opensanctions.org"
        assert client.timeout == 10

    def test_search_method_exists(self, client):
        """Test search method exists."""
        assert hasattr(client, "search")

    def test_check_sanctions_method_exists(self, client):
        """Test check_sanctions method exists."""
        assert hasattr(client, "check_sanctions")

    def test_verify_entity_method_exists(self, client):
        """Test verify_entity method exists."""
        assert hasattr(client, "verify_entity")

    def test_check_sanctions_returns_dict(self, client):
        """Test check_sanctions returns proper structure."""
        result = client.check_sanctions("John Smith")
        
        assert isinstance(result, dict)
        assert "is_sanctioned" in result
        assert "matches" in result
        assert "confidence" in result


class TestRelationshipExtractor:
    """Tests for relationship extractor."""

    @pytest.fixture
    def extractor(self):
        """Create relationship extractor."""
        return RelationshipExtractor()

    def test_extractor_initialization(self, extractor):
        """Test extractor initialization."""
        assert extractor.window_size is not None
        assert len(extractor.patterns) > 0

    def test_extract_relationships(self, extractor):
        """Test extracting relationships."""
        text = "John Smith works at Microsoft in Seattle."
        entities = [
            {"text": "John Smith", "entity_type": "PERSON", "start_char": 0, "end_char": 10},
            {"text": "Microsoft", "entity_type": "ORG", "start_char": 21, "end_char": 30},
        ]
        
        relationships = extractor.extract_relationships(text, entities)
        
        assert isinstance(relationships, list)

    def test_extract_coreferences(self, extractor):
        """Test extracting coreferences."""
        text = "John Smith works at Microsoft. He is the CEO."
        entities = [
            {"text": "John Smith", "entity_type": "PERSON", "start_char": 0, "end_char": 10},
        ]
        
        coreferences = extractor.extract_coreferences(text, entities)
        
        assert isinstance(coreferences, list)

    def test_extract_attributes(self, extractor):
        """Test extracting attributes."""
        text = "John Smith is 35 years old and works at Microsoft."
        entities = [
            {"text": "John Smith", "entity_type": "PERSON", "start_char": 0, "end_char": 10},
        ]
        
        attributes = extractor.extract_attributes(text, entities)
        
        assert isinstance(attributes, list)


class TestCooccurrenceAnalyzer:
    """Tests for co-occurrence analyzer."""

    @pytest.fixture
    def analyzer(self):
        """Create co-occurrence analyzer."""
        return CooccurrenceAnalyzer(window_size=50)

    def test_analyzer_initialization(self, analyzer):
        """Test analyzer initialization."""
        assert analyzer.window_size == 50

    def test_analyze_cooccurrences(self, analyzer):
        """Test analyzing co-occurrences."""
        text = "John Smith works at Microsoft in Seattle."
        entities = [
            {"text": "John Smith", "entity_type": "PERSON", "start_char": 0, "end_char": 10},
            {"text": "Microsoft", "entity_type": "ORG", "start_char": 21, "end_char": 30},
            {"text": "Seattle", "entity_type": "LOC", "start_char": 34, "end_char": 41},
        ]
        
        cooccurrences = analyzer.analyze_cooccurrences(text, entities)
        
        assert isinstance(cooccurrences, list)

    def test_build_cooccurrence_matrix(self, analyzer):
        """Test building co-occurrence matrix."""
        documents = [
            (
                "John Smith works at Microsoft.",
                [
                    {"text": "John Smith", "entity_type": "PERSON", "start_char": 0, "end_char": 10},
                    {"text": "Microsoft", "entity_type": "ORG", "start_char": 21, "end_char": 30},
                ],
            ),
        ]
        
        matrix = analyzer.build_cooccurrence_matrix(documents)
        
        assert isinstance(matrix, dict)

    def test_get_related_entities(self, analyzer):
        """Test getting related entities."""
        matrix = {
            ("John", "Microsoft"): 5,
            ("John", "Seattle"): 3,
            ("Microsoft", "Seattle"): 2,
        }
        
        related = analyzer.get_related_entities("John", matrix, top_k=2)
        
        assert isinstance(related, list)
        assert len(related) <= 2

    def test_calculate_entity_importance(self, analyzer):
        """Test calculating entity importance."""
        matrix = {
            ("John", "Microsoft"): 5,
            ("John", "Seattle"): 3,
            ("Microsoft", "Seattle"): 2,
        }
        
        importance = analyzer.calculate_entity_importance(matrix)
        
        assert isinstance(importance, dict)
        assert "John" in importance
        assert "Microsoft" in importance
        assert "Seattle" in importance

    def test_detect_entity_clusters(self, analyzer):
        """Test detecting entity clusters."""
        matrix = {
            ("John", "Microsoft"): 5,
            ("John", "Seattle"): 5,
            ("Microsoft", "Seattle"): 5,
            ("Alice", "Google"): 5,
            ("Alice", "Mountain View"): 5,
        }
        
        clusters = analyzer.detect_entity_clusters(matrix, threshold=3)
        
        assert isinstance(clusters, list)

