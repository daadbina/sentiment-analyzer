"""
Integration tests for PostgreSQL actor repository.
"""
import pytest
from datetime import datetime
from src.actors.repository import ActorRepository
from src.models import Actor, EntityType


@pytest.mark.integration
class TestActorRepository:
    """Integration tests for actor repository."""

    @pytest.fixture
    def repository(self, test_env_vars, postgres_connection):
        """Create actor repository for tests."""
        repo = ActorRepository(
            host=postgres_connection.get_dsn().split("host=")[1].split(" ")[0],
            port=5432,
            user=postgres_connection.get_dsn().split("user=")[1].split(" ")[0],
            password=postgres_connection.get_dsn().split("password=")[1].split(" ")[0],
            database=postgres_connection.get_dsn().split("dbname=")[1].split(" ")[0],
        )
        repo.initialize_schema()
        yield repo
        repo.close()

    def test_repository_initialization(self, repository: ActorRepository):
        """Test actor repository initialization."""
        assert repository is not None
        assert repository.pool is not None

    def test_upsert_actor(self, repository: ActorRepository):
        """Test upserting an actor."""
        actor = Actor(
            actor_id="test-actor-1",
            normalized_name="john doe",
            type=ActorType.PERSON,
            occurrences=1,
            first_seen=datetime.now(),
            last_seen=datetime.now(),
            wikidata_id="Q123456",
            country="US",
        )
        
        result = repository.upsert_actor(actor)
        assert result is not None
        assert result.actor_id == "test-actor-1"

    def test_lookup_actor_by_name(self, repository: ActorRepository):
        """Test looking up actor by normalized name."""
        actor = Actor(
            actor_id="test-actor-2",
            normalized_name="jane smith",
            type=ActorType.PERSON,
            occurrences=1,
            first_seen=datetime.now(),
            last_seen=datetime.now(),
            wikidata_id="Q789012",
            country="UK",
        )
        
        repository.upsert_actor(actor)
        
        # Lookup by normalized name
        found_actor = repository.lookup_by_normalized_name("jane smith")
        assert found_actor is not None
        assert found_actor.actor_id == "test-actor-2"

    def test_lookup_actor_by_wikidata_id(self, repository: ActorRepository):
        """Test looking up actor by Wikidata ID."""
        actor = Actor(
            actor_id="test-actor-3",
            normalized_name="bob wilson",
            type=ActorType.PERSON,
            occurrences=1,
            first_seen=datetime.now(),
            last_seen=datetime.now(),
            wikidata_id="Q345678",
            country="CA",
        )
        
        repository.upsert_actor(actor)
        
        # Lookup by Wikidata ID
        found_actor = repository.lookup_by_wikidata_id("Q345678")
        assert found_actor is not None
        assert found_actor.actor_id == "test-actor-3"

    def test_actor_deduplication(self, repository: ActorRepository):
        """Test actor deduplication with similar names."""
        actor1 = Actor(
            actor_id="test-actor-4",
            normalized_name="john smith",
            type=ActorType.PERSON,
            occurrences=1,
            first_seen=datetime.now(),
            last_seen=datetime.now(),
            wikidata_id="Q111111",
            country="US",
        )
        
        actor2 = Actor(
            actor_id="test-actor-5",
            normalized_name="john smith",  # Same normalized name
            type=ActorType.PERSON,
            occurrences=1,
            first_seen=datetime.now(),
            last_seen=datetime.now(),
            wikidata_id="Q222222",
            country="US",
        )
        
        repository.upsert_actor(actor1)
        repository.upsert_actor(actor2)
        
        # Should find the first actor
        found_actor = repository.lookup_by_normalized_name("john smith")
        assert found_actor is not None
        assert found_actor.actor_id in ["test-actor-4", "test-actor-5"]

    def test_actor_occurrence_increment(self, repository: ActorRepository):
        """Test incrementing actor occurrences."""
        actor = Actor(
            actor_id="test-actor-6",
            normalized_name="alice johnson",
            type=ActorType.PERSON,
            occurrences=1,
            first_seen=datetime.now(),
            last_seen=datetime.now(),
            wikidata_id="Q555555",
            country="AU",
        )
        
        repository.upsert_actor(actor)
        
        # Upsert same actor again (should increment occurrences)
        actor.occurrences = 2
        repository.upsert_actor(actor)
        
        found_actor = repository.lookup_by_normalized_name("alice johnson")
        assert found_actor.occurrences >= 1

    def test_actor_type_validation(self, repository: ActorRepository):
        """Test actor type validation."""
        for actor_type in ActorType:
            actor = Actor(
                actor_id=f"test-actor-type-{actor_type.value}",
                normalized_name=f"test {actor_type.value}",
                type=actor_type,
                occurrences=1,
                first_seen=datetime.now(),
                last_seen=datetime.now(),
                wikidata_id=f"Q{actor_type.value}",
                country="US",
            )
            
            result = repository.upsert_actor(actor)
            assert result.type == actor_type

