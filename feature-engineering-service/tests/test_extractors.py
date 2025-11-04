"""Unit tests for feature extractors."""

import pytest
from datetime import datetime
from src.extractors import (
    SourceExtractor,
    TemporalExtractor,
    SentimentExtractor,
    EntityExtractor,
    ContentExtractor,
    EmbeddingExtractor,
    SemanticGroup,
    Article,
    Actor,
)


@pytest.fixture
def sample_group():
    """Create sample semantic group."""
    return SemanticGroup(
        group_id="group_001",
        article_ids=["art_001", "art_002", "art_003"],
        centroid_vector=[0.1, 0.2, 0.3, 0.4, 0.5],
        similarity_avg=0.85,
        topic_label="politics",
        metadata={"similarity_std": 0.05},
        created_at=datetime.utcnow().isoformat(),
    )


@pytest.fixture
def sample_articles():
    """Create sample articles."""
    return [
        Article(
            article_id="art_001",
            title="Breaking News",
            body="This is a news article about politics",
            language="en",
            domain="news.com",
            source="Reuters",
            published_at=datetime.utcnow().isoformat(),
            sentiment_score=0.5,
            entities=[{"name": "John", "type": "PERSON"}],
        ),
        Article(
            article_id="art_002",
            title="Another Story",
            body="Another article with more content",
            language="en",
            domain="news.com",
            source="AP",
            published_at=datetime.utcnow().isoformat(),
            sentiment_score=0.3,
            entities=[{"name": "Jane", "type": "PERSON"}],
        ),
        Article(
            article_id="art_003",
            title="Third Article",
            body="Third article with different content",
            language="en",
            domain="blog.com",
            source="Reuters",
            published_at=datetime.utcnow().isoformat(),
            sentiment_score=0.7,
            entities=[{"name": "USA", "type": "LOCATION"}],
        ),
    ]


@pytest.fixture
def sample_actors():
    """Create sample actors."""
    return [
        Actor(
            actor_id="actor_001",
            name="John",
            type="PERSON",
            country="USA",
            sentiment_avg=0.5,
            occurrences=10,
            wikidata_id="Q123",
        ),
    ]


def test_source_extractor(sample_group, sample_articles, sample_actors):
    """Test source extractor."""
    extractor = SourceExtractor()
    features = extractor.extract(sample_group, sample_articles, sample_actors)

    assert "num_sources" in features
    assert features["num_sources"] == 2  # Reuters and AP
    assert "source_credibility_avg" in features
    assert "source_credibility_std" in features
    assert "source_diversity_score" in features


def test_temporal_extractor(sample_group, sample_articles, sample_actors):
    """Test temporal extractor."""
    extractor = TemporalExtractor()
    features = extractor.extract(sample_group, sample_articles, sample_actors)

    assert "time_span_hours" in features
    assert "publication_velocity" in features
    assert "temporal_concentration" in features
    assert "days_since_first_article" in features


def test_sentiment_extractor(sample_group, sample_articles, sample_actors):
    """Test sentiment extractor."""
    extractor = SentimentExtractor()
    features = extractor.extract(sample_group, sample_articles, sample_actors)

    assert "sentiment_mean" in features
    assert "sentiment_std" in features
    assert "sentiment_polarity_ratio" in features
    assert "sentiment_volatility" in features
    assert features["sentiment_mean"] == pytest.approx(0.5, abs=0.1)


def test_entity_extractor(sample_group, sample_articles, sample_actors):
    """Test entity extractor."""
    extractor = EntityExtractor()
    features = extractor.extract(sample_group, sample_articles, sample_actors)

    assert "entity_count" in features
    assert "entity_diversity" in features
    assert "entity_prominence" in features
    assert "entity_concentration" in features


def test_content_extractor(sample_group, sample_articles, sample_actors):
    """Test content extractor."""
    extractor = ContentExtractor()
    features = extractor.extract(sample_group, sample_articles, sample_actors)

    assert "avg_word_count" in features
    assert "avg_title_length" in features
    assert "language_diversity" in features
    assert "domain_diversity" in features
    assert features["language_diversity"] == 1  # All English
    assert features["domain_diversity"] == 2  # news.com and blog.com


def test_embedding_extractor(sample_group, sample_articles, sample_actors):
    """Test embedding extractor."""
    extractor = EmbeddingExtractor()
    features = extractor.extract(sample_group, sample_articles, sample_actors)

    assert "centroid_magnitude" in features
    assert "intra_cluster_similarity_mean" in features
    assert "intra_cluster_similarity_std" in features
    assert "embedding_drift_score" in features

