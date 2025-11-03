"""Tests for domain classifier."""

import pytest
from src.classification import DomainClassifier


class TestDomainClassifier:
    """Test domain classification."""

    @pytest.fixture
    def classifier(self):
        """Create classifier instance."""
        return DomainClassifier()

    def test_classify_politics(self, classifier):
        """Test politics classification."""
        title = "Election Results Announced"
        body = "The government announced new political policies for parliament"

        result = classifier.classify(title, body)

        assert result.domain_category == "politics"
        assert result.confidence > 0.0

    def test_classify_economy(self, classifier):
        """Test economy classification."""
        title = "Stock Market Reaches New High"
        body = "The market showed strong business growth with increased trade"

        result = classifier.classify(title, body)

        assert result.domain_category == "economy"
        assert result.confidence > 0.0

    def test_classify_technology(self, classifier):
        """Test technology classification."""
        title = "New AI Algorithm Released"
        body = "Tech companies announce breakthrough in software and digital innovation"

        result = classifier.classify(title, body)

        assert result.domain_category == "technology"
        assert result.confidence > 0.0

    def test_classify_conflict(self, classifier):
        """Test conflict classification."""
        title = "Military Conflict Escalates"
        body = "Armed forces engaged in battle with military attack reported"

        result = classifier.classify(title, body)

        assert result.domain_category == "conflict"
        assert result.confidence > 0.0

    def test_classify_health(self, classifier):
        """Test health classification."""
        title = "New Vaccine Approved"
        body = "Medical doctors announce treatment for disease and pandemic response"

        result = classifier.classify(title, body)

        assert result.domain_category == "health"
        assert result.confidence > 0.0

    def test_classify_environment(self, classifier):
        """Test environment classification."""
        title = "Climate Change Report"
        body = "Environmental pollution and carbon emissions affect sustainability"

        result = classifier.classify(title, body)

        assert result.domain_category == "environment"
        assert result.confidence > 0.0

    def test_classify_sports(self, classifier):
        """Test sports classification."""
        title = "Championship Game Results"
        body = "The team won the match with player scoring in the tournament"

        result = classifier.classify(title, body)

        assert result.domain_category == "sports"
        assert result.confidence > 0.0

    def test_classify_entertainment(self, classifier):
        """Test entertainment classification."""
        title = "Movie Premiere Announced"
        body = "Celebrity actor stars in new film with music and concert performances"

        result = classifier.classify(title, body)

        assert result.domain_category == "entertainment"
        assert result.confidence > 0.0

    def test_classify_general_fallback(self, classifier):
        """Test general fallback classification."""
        title = "Random Article"
        body = "This is some random content without specific domain keywords"

        result = classifier.classify(title, body)

        assert result.domain_category == "general"
        assert result.confidence == 0.0

    def test_classify_confidence_range(self, classifier):
        """Test confidence is in valid range."""
        title = "Politics Article"
        body = "Government and parliament news"

        result = classifier.classify(title, body)

        assert 0.0 <= result.confidence <= 1.0

    def test_classify_case_insensitive(self, classifier):
        """Test case-insensitive classification."""
        title1 = "POLITICS ARTICLE"
        body1 = "GOVERNMENT AND PARLIAMENT"

        title2 = "politics article"
        body2 = "government and parliament"

        result1 = classifier.classify(title1, body1)
        result2 = classifier.classify(title2, body2)

        assert result1.domain_category == result2.domain_category

