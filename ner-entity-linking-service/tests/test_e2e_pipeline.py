"""
End-to-end pipeline integration tests.
"""
import pytest
import json
from datetime import datetime
from src.models import (
    NewsCanonicalMessage,
    EntitiesExtractedMessage,
    Entity,
    Actor,
    EntityType,
)
from src.clients.kafka_consumer import KafkaConsumerClient
from src.clients.kafka_producer import KafkaProducerClient
from src.actors.repository import ActorRepository
from src.normalization.entity_normalizer import EntityNormalizer
from src.linking.entity_linker import EntityLinker
from src.linking.wikidata_client import WikidataClient
from tests.test_fixtures import sample_entity


@pytest.mark.integration
class TestE2EPipeline:
    """End-to-end pipeline integration tests."""

    @pytest.fixture
    def normalizer(self):
        """Create entity normalizer."""
        return EntityNormalizer()

    @pytest.fixture
    def linker(self):
        """Create entity linker."""
        wikidata_client = WikidataClient(api_url="https://www.wikidata.org/w/api.php")
        return EntityLinker(wikidata_client=wikidata_client)

    def test_entity_normalization_pipeline(self, normalizer: EntityNormalizer):
        """Test entity normalization in pipeline."""
        entity_text = "Dr. John Smith"
        
        normalized = normalizer.normalize(entity_text)
        
        assert normalized is not None
        assert isinstance(normalized, str)
        assert len(normalized) > 0

    def test_entity_linking_pipeline(self, linker: EntityLinker, sample_entity: Entity):
        """Test entity linking in pipeline."""
        linked_entity = linker.link_entity(sample_entity)

        assert linked_entity is not None
        assert linked_entity.text == sample_entity.text

    def test_full_message_processing(
        self,
        normalizer: EntityNormalizer,
        linker: EntityLinker,
    ):
        """Test full message processing pipeline."""
        # Create input message
        input_message = NewsCanonicalMessage(
            article_id="test-article-1",
            canonical_url="https://test.com/article",
            title="Test Article",
            normalized_body="John Smith works at Microsoft. He is from Seattle.",
            language="en",
            publisher_id="pub-001",
            publisher_credibility=0.95,
            domain="test.com",
            published_at="2025-11-03T20:00:00Z",
            normalized_at="2025-11-03T20:00:00Z",
            trace_id="test-trace-1",
        )
        
        # Create entities
        entity1 = Entity(
            entity_id="entity-1",
            text="John Smith",
            normalized_text="john smith",
            entity_type=EntityType.PERSON,
            confidence=0.95,
            start_char=0,
            end_char=10,
            context_snippet="John Smith works at Microsoft",
        )

        entity2 = Entity(
            entity_id="entity-2",
            text="Microsoft",
            normalized_text="microsoft",
            entity_type=EntityType.ORGANIZATION,
            confidence=0.98,
            start_char=21,
            end_char=30,
            context_snippet="works at Microsoft. He is",
        )
        
        # Process entities
        normalized_text1 = normalizer.normalize(entity1.text)
        normalized_text2 = normalizer.normalize(entity2.text)
        
        assert normalized_text1 is not None
        assert normalized_text2 is not None
        
        # Create output message
        output_message = EntitiesExtractedMessage(
            article_id=input_message.article_id,
            entities=[entity1, entity2],
            extracted_at=datetime.now().isoformat() + "Z",
            language=input_message.language,
            ner_model="test-model",
            entity_count=2,
            coverage_score=0.75,
            linking_success_rate=0.5,
            trace_id=input_message.trace_id,
        )
        
        assert output_message.article_id == input_message.article_id
        assert len(output_message.entities) == 2
        assert output_message.entity_count == 2

    def test_multilingual_pipeline(self, normalizer: EntityNormalizer):
        """Test multilingual entity processing."""
        test_cases = [
            ("John Smith", "en"),  # English
            ("محمد علي", "ar"),  # Arabic
            ("Владимир Путин", "ru"),  # Russian
            ("张三", "zh"),  # Chinese
        ]
        
        for entity_text, language in test_cases:
            normalized = normalizer.normalize(entity_text)
            assert normalized is not None
            assert isinstance(normalized, str)

    def test_actor_persistence_pipeline(self, test_env_vars):
        """Test actor persistence in pipeline."""
        # Create actor repository
        repo = ActorRepository(
            host=test_env_vars.get("POSTGRES_HOST", "localhost"),
            port=int(test_env_vars.get("POSTGRES_PORT", "5432")),
            user=test_env_vars.get("POSTGRES_USER", "postgres"),
            password=test_env_vars.get("POSTGRES_PASSWORD", ""),
            database=test_env_vars.get("POSTGRES_DATABASE", "sentiment"),
        )
        
        # Create actor
        actor = Actor(
            actor_id="test-actor-e2e-1",
            normalized_name="john smith",
            type=ActorType.PERSON,
            occurrences=1,
            first_seen=datetime.now(),
            last_seen=datetime.now(),
            wikidata_id="Q123456",
            country="US",
        )
        
        # Persist actor
        persisted_actor = repo.upsert_actor(actor)
        assert persisted_actor is not None
        assert persisted_actor.actor_id == "test-actor-e2e-1"
        
        # Lookup actor
        found_actor = repo.lookup_by_normalized_name("john smith")
        assert found_actor is not None
        
        repo.close()

    def test_coverage_calculation(self):
        """Test coverage score calculation."""
        # Create entities
        entities = [
            Entity(
                entity_id="e1",
                text="John",
                normalized_text="john",
                entity_type="PERSON",
                confidence=0.95,
                start_char=0,
                end_char=4,
                context_snippet="John works",
            ),
            Entity(
                entity_id="e2",
                text="Microsoft",
                normalized_text="microsoft",
                entity_type="ORGANIZATION",
                confidence=0.98,
                start_char=12,
                end_char=21,
                context_snippet="works at Microsoft",
            ),
        ]
        
        # Calculate coverage (2 entities in ~30 words = ~6.7%)
        entity_count = len(entities)
        assert entity_count == 2
        
        # Coverage should be reasonable
        coverage_score = min(entity_count / 30.0, 1.0)
        assert 0.0 <= coverage_score <= 1.0

    def test_linking_success_rate(self):
        """Test linking success rate calculation."""
        # Create entities with linking info
        linked_entities = 3
        total_entities = 5
        
        linking_success_rate = linked_entities / total_entities
        
        assert linking_success_rate == 0.6
        assert 0.0 <= linking_success_rate <= 1.0

