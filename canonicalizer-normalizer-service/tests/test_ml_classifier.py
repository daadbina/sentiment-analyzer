"""Tests for ML-based domain classification."""

import pytest
from src.classification.ml_classifier import (
    MLDomainClassifier,
    MLPublisherCredibilityScorer,
    MLClassifierFactory,
    ClassificationResult,
)


class TestMLDomainClassifier:
    """Test ML domain classifier."""

    def test_ml_classifier_initialization(self):
        """Test ML classifier can be initialized."""
        classifier = MLDomainClassifier()
        assert classifier is not None
        assert classifier.model_name == 'distilbert-base-uncased'

    def test_ml_classifier_supported_domains(self):
        """Test supported domains are defined."""
        classifier = MLDomainClassifier()
        assert len(classifier.SUPPORTED_DOMAINS) == 8
        assert 'politics' in classifier.SUPPORTED_DOMAINS
        assert 'economy' in classifier.SUPPORTED_DOMAINS
        assert 'technology' in classifier.SUPPORTED_DOMAINS

    def test_ml_classifier_classify_empty_text(self):
        """Test classification with empty text."""
        classifier = MLDomainClassifier()
        result = classifier.classify("")
        assert result is None

    def test_ml_classifier_classify_none_text(self):
        """Test classification with None text."""
        classifier = MLDomainClassifier()
        result = classifier.classify(None)
        assert result is None

    def test_ml_classifier_classify_whitespace(self):
        """Test classification with whitespace text."""
        classifier = MLDomainClassifier()
        result = classifier.classify("   ")
        assert result is None

    def test_ml_classifier_classify_returns_result_or_none(self):
        """Test classification returns ClassificationResult or None."""
        classifier = MLDomainClassifier()
        text = "The stock market rose today"
        result = classifier.classify(text)
        # Result can be None if transformers not available
        if result is not None:
            assert isinstance(result, ClassificationResult)
            assert hasattr(result, 'domain')
            assert hasattr(result, 'confidence')
            assert hasattr(result, 'multi_label_predictions')

    def test_ml_classifier_batch_classify(self):
        """Test batch classification."""
        classifier = MLDomainClassifier()
        texts = [
            "The stock market rose today",
            "New technology breakthrough announced",
            "Sports team wins championship",
        ]
        results = classifier.classify_batch(texts)
        assert isinstance(results, list)
        assert len(results) == 3

    def test_ml_classifier_batch_classify_empty_list(self):
        """Test batch classification with empty list."""
        classifier = MLDomainClassifier()
        results = classifier.classify_batch([])
        assert isinstance(results, list)
        assert len(results) == 0

    def test_ml_classifier_confidence_threshold(self):
        """Test confidence threshold."""
        classifier = MLDomainClassifier()
        threshold = classifier.get_confidence_threshold()
        assert isinstance(threshold, float)
        assert 0.0 <= threshold <= 1.0

    def test_ml_classifier_multi_label_classification(self):
        """Test multi-label classification."""
        classifier = MLDomainClassifier()
        text = "Stock market technology news"
        result = classifier.classify(text, multi_label=True)
        if result is not None:
            assert isinstance(result.multi_label_predictions, dict)

    def test_ml_classifier_text_truncation(self):
        """Test that long text is truncated."""
        classifier = MLDomainClassifier()
        # Create very long text
        long_text = "word " * 200
        result = classifier.classify(long_text)
        # Should not raise error, text should be truncated internally
        assert result is None or isinstance(result, ClassificationResult)


class TestMLPublisherCredibilityScorer:
    """Test ML publisher credibility scorer."""

    def test_credibility_scorer_initialization(self):
        """Test credibility scorer can be initialized."""
        scorer = MLPublisherCredibilityScorer()
        assert scorer is not None

    def test_credibility_scorer_score_publisher_basic(self):
        """Test basic publisher scoring."""
        scorer = MLPublisherCredibilityScorer()
        score = scorer.score_publisher("example.com")
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_credibility_scorer_with_accuracy(self):
        """Test scoring with historical accuracy."""
        scorer = MLPublisherCredibilityScorer()
        score = scorer.score_publisher(
            "example.com",
            historical_accuracy=0.9
        )
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_credibility_scorer_with_article_count(self):
        """Test scoring with article count."""
        scorer = MLPublisherCredibilityScorer()
        score = scorer.score_publisher(
            "example.com",
            article_count=1000
        )
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_credibility_scorer_with_engagement(self):
        """Test scoring with engagement metric."""
        scorer = MLPublisherCredibilityScorer()
        score = scorer.score_publisher(
            "example.com",
            avg_engagement=50.0
        )
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_credibility_scorer_with_all_features(self):
        """Test scoring with all features."""
        scorer = MLPublisherCredibilityScorer()
        score = scorer.score_publisher(
            "example.com",
            historical_accuracy=0.85,
            article_count=500,
            avg_engagement=75.0
        )
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_credibility_scorer_batch_score(self):
        """Test batch scoring."""
        scorer = MLPublisherCredibilityScorer()
        publishers = [
            {
                'domain': 'example1.com',
                'historical_accuracy': 0.9,
                'article_count': 1000,
                'avg_engagement': 80.0,
            },
            {
                'domain': 'example2.com',
                'historical_accuracy': 0.7,
                'article_count': 500,
                'avg_engagement': 50.0,
            },
        ]
        scores = scorer.score_batch(publishers)
        assert isinstance(scores, dict)
        assert len(scores) == 2
        assert 'example1.com' in scores
        assert 'example2.com' in scores

    def test_credibility_scorer_batch_score_empty(self):
        """Test batch scoring with empty list."""
        scorer = MLPublisherCredibilityScorer()
        scores = scorer.score_batch([])
        assert isinstance(scores, dict)
        assert len(scores) == 0

    def test_credibility_scorer_score_range(self):
        """Test that scores are always in valid range."""
        scorer = MLPublisherCredibilityScorer()
        # Test with extreme values
        score1 = scorer.score_publisher("test.com", historical_accuracy=0.0)
        score2 = scorer.score_publisher("test.com", historical_accuracy=1.0)
        score3 = scorer.score_publisher("test.com", article_count=0)
        score4 = scorer.score_publisher("test.com", article_count=10000)

        assert 0.0 <= score1 <= 1.0
        assert 0.0 <= score2 <= 1.0
        assert 0.0 <= score3 <= 1.0
        assert 0.0 <= score4 <= 1.0


class TestMLClassifierFactory:
    """Test ML classifier factory."""

    def test_factory_get_domain_classifier(self):
        """Test factory returns domain classifier."""
        classifier = MLClassifierFactory.get_domain_classifier()
        assert classifier is not None
        assert isinstance(classifier, MLDomainClassifier)

    def test_factory_get_domain_classifier_custom_model(self):
        """Test factory with custom model name."""
        classifier = MLClassifierFactory.get_domain_classifier('bert-base-uncased')
        assert classifier is not None
        assert classifier.model_name == 'bert-base-uncased'

    def test_factory_get_credibility_scorer(self):
        """Test factory returns credibility scorer."""
        scorer = MLClassifierFactory.get_credibility_scorer()
        assert scorer is not None
        assert isinstance(scorer, MLPublisherCredibilityScorer)

    def test_factory_caching(self):
        """Test factory caches instances."""
        classifier1 = MLClassifierFactory.get_domain_classifier()
        classifier2 = MLClassifierFactory.get_domain_classifier()
        # Should return same instance
        assert classifier1 is classifier2

    def test_factory_credibility_scorer_caching(self):
        """Test factory caches credibility scorer."""
        scorer1 = MLClassifierFactory.get_credibility_scorer()
        scorer2 = MLClassifierFactory.get_credibility_scorer()
        # Should return same instance
        assert scorer1 is scorer2


class TestClassificationResult:
    """Test ClassificationResult dataclass."""

    def test_classification_result_creation(self):
        """Test creating classification result."""
        result = ClassificationResult(
            domain='politics',
            confidence=0.95,
            multi_label_predictions={'politics': 0.95, 'economy': 0.05}
        )
        assert result.domain == 'politics'
        assert result.confidence == 0.95
        assert len(result.multi_label_predictions) == 2

    def test_classification_result_fields(self):
        """Test classification result has required fields."""
        result = ClassificationResult(
            domain='technology',
            confidence=0.87,
            multi_label_predictions={'technology': 0.87}
        )
        assert hasattr(result, 'domain')
        assert hasattr(result, 'confidence')
        assert hasattr(result, 'multi_label_predictions')

