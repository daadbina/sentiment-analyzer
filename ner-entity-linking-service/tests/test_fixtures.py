"""Test fixtures and utilities."""

import pytest
from datetime import datetime
from src.models import Entity, EntityType, Actor, NewsCanonicalMessage


@pytest.fixture
def sample_entity():
    """Create a sample entity for testing."""
    return Entity(
        entity_id="e1",
        text="John Smith",
        normalized_text="john smith",
        entity_type=EntityType.PERSON,
        confidence=0.95,
        start_char=0,
        end_char=11,
        context_snippet="John Smith works at Microsoft",
        wikidata_id="Q123456",
        dbpedia_uri="http://dbpedia.org/resource/John_Smith",
        country="USA",
        aliases=["J. Smith", "John S."],
    )


@pytest.fixture
def sample_entities():
    """Create multiple sample entities for testing."""
    return [
        Entity(
            entity_id="e1",
            text="John Smith",
            normalized_text="john smith",
            entity_type=EntityType.PERSON,
            confidence=0.95,
            start_char=0,
            end_char=11,
            context_snippet="John Smith works",
            wikidata_id="Q123456",
        ),
        Entity(
            entity_id="e2",
            text="Microsoft",
            normalized_text="microsoft",
            entity_type=EntityType.ORGANIZATION,
            confidence=0.98,
            start_char=21,
            end_char=30,
            context_snippet="works at Microsoft",
            wikidata_id="Q789012",
        ),
        Entity(
            entity_id="e3",
            text="Seattle",
            normalized_text="seattle",
            entity_type=EntityType.LOCATION,
            confidence=0.92,
            start_char=35,
            end_char=42,
            context_snippet="in Seattle",
            wikidata_id="Q345678",
        ),
    ]


@pytest.fixture
def sample_actor():
    """Create a sample actor for testing."""
    return Actor(
        actor_id="a1",
        name="John Smith",
        normalized_name="john smith",
        type=EntityType.PERSON,
        aliases=["J. Smith", "John S."],
        country="USA",
        wikidata_id="Q123456",
        dbpedia_uri="http://dbpedia.org/resource/John_Smith",
        sentiment_avg=0.5,
        occurrences=10,
        first_seen=datetime(2025, 1, 1),
        last_seen=datetime(2025, 11, 4),
        ner_fallback_rate=0.05,
        metadata={"source": "news", "verified": True},
        created_at=datetime(2025, 1, 1),
        updated_at=datetime(2025, 11, 4),
    )


@pytest.fixture
def sample_news_message():
    """Create a sample news canonical message for testing."""
    return NewsCanonicalMessage(
        article_id="art123",
        canonical_url="https://example.com/article/123",
        title="Breaking News: Tech Company Announces New Product",
        normalized_body="John Smith, CEO of Microsoft, announced a new product in Seattle today.",
        language="en",
        publisher_id="pub456",
        publisher_credibility=0.95,
        domain="example.com",
        published_at="2025-11-04T10:00:00Z",
        normalized_at="2025-11-04T10:05:00Z",
        trace_id="trace789",
    )


@pytest.fixture
def sample_multilingual_texts():
    """Create sample texts in multiple languages for testing."""
    return {
        "en": "John Smith works at Microsoft in Seattle.",
        "fa": "جان اسمیت در مایکروسافت در سیاتل کار می کند.",
        "ru": "Джон Смит работает в Microsoft в Сиэтле.",
        "zh": "约翰·史密斯在西雅图的微软公司工作。",
        "ar": "يعمل جون سميث في مايكروسوفت في سياتل.",
        "de": "John Smith arbeitet bei Microsoft in Seattle.",
        "fr": "John Smith travaille chez Microsoft à Seattle.",
        "es": "John Smith trabaja en Microsoft en Seattle.",
        "ja": "ジョン・スミスはシアトルのマイクロソフトで働いています。",
        "ko": "존 스미스는 시애틀의 마이크로소프트에서 일합니다.",
    }


@pytest.fixture
def sample_entity_types():
    """Create sample entities of different types."""
    return {
        "PERSON": Entity(
            entity_id="e_person",
            text="Barack Obama",
            normalized_text="barack obama",
            entity_type=EntityType.PERSON,
            confidence=0.99,
            start_char=0,
            end_char=12,
            context_snippet="Barack Obama was president",
        ),
        "ORGANIZATION": Entity(
            entity_id="e_org",
            text="United Nations",
            normalized_text="united nations",
            entity_type=EntityType.ORGANIZATION,
            confidence=0.98,
            start_char=0,
            end_char=14,
            context_snippet="United Nations headquarters",
        ),
        "LOCATION": Entity(
            entity_id="e_loc",
            text="New York",
            normalized_text="new york",
            entity_type=EntityType.LOCATION,
            confidence=0.97,
            start_char=0,
            end_char=8,
            context_snippet="New York City",
        ),
        "GPE": Entity(
            entity_id="e_gpe",
            text="United States",
            normalized_text="united states",
            entity_type=EntityType.GPE,
            confidence=0.96,
            start_char=0,
            end_char=13,
            context_snippet="United States government",
        ),
    }


@pytest.fixture
def sample_confidence_levels():
    """Create entities with different confidence levels."""
    return {
        "high": Entity(
            entity_id="e_high",
            text="Test Entity",
            normalized_text="test entity",
            entity_type=EntityType.PERSON,
            confidence=0.95,
            start_char=0,
            end_char=11,
            context_snippet="Test Entity",
        ),
        "medium": Entity(
            entity_id="e_medium",
            text="Test Entity",
            normalized_text="test entity",
            entity_type=EntityType.PERSON,
            confidence=0.70,
            start_char=0,
            end_char=11,
            context_snippet="Test Entity",
        ),
        "low": Entity(
            entity_id="e_low",
            text="Test Entity",
            normalized_text="test entity",
            entity_type=EntityType.PERSON,
            confidence=0.50,
            start_char=0,
            end_char=11,
            context_snippet="Test Entity",
        ),
    }


class TestDataFactory:
    """Factory for creating test data."""

    @staticmethod
    def create_entity(
        entity_id: str = "e1",
        text: str = "Test",
        entity_type: EntityType = EntityType.PERSON,
        confidence: float = 0.95,
        **kwargs,
    ) -> Entity:
        """Create an entity with custom parameters."""
        return Entity(
            entity_id=entity_id,
            text=text,
            normalized_text=text.lower(),
            entity_type=entity_type,
            confidence=confidence,
            start_char=0,
            end_char=len(text),
            context_snippet=text,
            **kwargs,
        )

    @staticmethod
    def create_actor(
        actor_id: str = "a1",
        name: str = "Test Actor",
        actor_type: EntityType = EntityType.PERSON,
        **kwargs,
    ) -> Actor:
        """Create an actor with custom parameters."""
        return Actor(
            actor_id=actor_id,
            name=name,
            normalized_name=name.lower(),
            type=actor_type,
            **kwargs,
        )

    @staticmethod
    def create_news_message(
        article_id: str = "art1",
        title: str = "Test Article",
        **kwargs,
    ) -> NewsCanonicalMessage:
        """Create a news message with custom parameters."""
        return NewsCanonicalMessage(
            article_id=article_id,
            canonical_url=f"https://example.com/{article_id}",
            title=title,
            normalized_body="Test body content",
            language="en",
            publisher_id="pub1",
            publisher_credibility=0.95,
            domain="example.com",
            published_at="2025-11-04T10:00:00Z",
            normalized_at="2025-11-04T10:05:00Z",
            trace_id="trace1",
            **kwargs,
        )

