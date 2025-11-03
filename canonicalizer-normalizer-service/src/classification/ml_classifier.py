"""ML-based domain classification using transformer models."""

import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ClassificationResult:
    """Result of ML-based classification."""

    domain: str
    confidence: float
    multi_label_predictions: dict[str, float]  # domain -> confidence


class MLDomainClassifier:
    """ML-based domain classifier using transformer models."""

    SUPPORTED_DOMAINS = [
        'politics', 'economy', 'technology', 'conflict',
        'health', 'environment', 'sports', 'entertainment'
    ]

    def __init__(self, model_name: str = 'distilbert-base-uncased'):
        """Initialize ML domain classifier.

        Args:
            model_name: Name of the transformer model to use
        """
        self.model_name = model_name
        self.available = False
        self.model = None
        self.tokenizer = None
        self._initialize_model()

    def _initialize_model(self) -> None:
        """Initialize the transformer model."""
        try:
            from transformers import pipeline
            # Use zero-shot classification pipeline
            self.classifier = pipeline(
                "zero-shot-classification",
                model=self.model_name,
                device=-1  # CPU
            )
            self.available = True
            logger.info(f"ML classifier initialized with model: {self.model_name}")
        except ImportError:
            logger.warning(
                "transformers library not available, ML classification disabled. "
                "Install with: pip install transformers torch"
            )
            self.available = False
        except Exception as e:
            logger.error(f"Error initializing ML classifier: {e}")
            self.available = False

    def classify(self, text: str, multi_label: bool = False) -> Optional[ClassificationResult]:
        """Classify text into domain categories.

        Args:
            text: Input text to classify
            multi_label: Whether to return multi-label predictions

        Returns:
            Classification result with domain and confidence, or None if unavailable
        """
        if not self.available or not text or len(text.strip()) == 0:
            return None

        try:
            # Truncate text to avoid token limit issues
            text = text[:512]

            # Perform zero-shot classification
            result = self.classifier(
                text,
                self.SUPPORTED_DOMAINS,
                multi_class=multi_label
            )

            # Extract primary classification
            primary_domain = result['labels'][0]
            primary_confidence = result['scores'][0]

            # Build multi-label predictions
            multi_label_predictions = {}
            if multi_label:
                for domain, score in zip(result['labels'], result['scores']):
                    multi_label_predictions[domain] = score
            else:
                multi_label_predictions = {primary_domain: primary_confidence}

            return ClassificationResult(
                domain=primary_domain,
                confidence=primary_confidence,
                multi_label_predictions=multi_label_predictions
            )

        except Exception as e:
            logger.error(f"Error classifying text: {e}")
            return None

    def classify_batch(self, texts: list[str], multi_label: bool = False) -> list[Optional[ClassificationResult]]:
        """Classify multiple texts.

        Args:
            texts: List of texts to classify
            multi_label: Whether to return multi-label predictions

        Returns:
            List of classification results
        """
        return [self.classify(text, multi_label) for text in texts]

    def get_confidence_threshold(self) -> float:
        """Get recommended confidence threshold for accepting classifications.

        Returns:
            Recommended confidence threshold (0.0-1.0)
        """
        return 0.5  # 50% confidence threshold


class MLPublisherCredibilityScorer:
    """ML-based publisher credibility scoring."""

    def __init__(self):
        """Initialize ML publisher credibility scorer."""
        self.available = False
        self.model = None
        self._initialize_model()

    def _initialize_model(self) -> None:
        """Initialize the credibility scoring model."""
        try:
            # In a real implementation, this would load a trained model
            # For now, we provide a placeholder that can be extended
            self.available = True
            logger.info("ML publisher credibility scorer initialized")
        except Exception as e:
            logger.error(f"Error initializing credibility scorer: {e}")
            self.available = False

    def score_publisher(
        self,
        publisher_domain: str,
        historical_accuracy: Optional[float] = None,
        article_count: Optional[int] = None,
        avg_engagement: Optional[float] = None,
    ) -> float:
        """Score publisher credibility using ML model.

        Args:
            publisher_domain: Publisher domain name
            historical_accuracy: Historical accuracy rate (0.0-1.0)
            article_count: Number of articles published
            avg_engagement: Average engagement metric

        Returns:
            Credibility score (0.0-1.0)
        """
        if not self.available:
            return 0.5  # Default neutral score

        try:
            # In a real implementation, this would use the trained model
            # For now, use a simple heuristic
            score = 0.5

            if historical_accuracy is not None:
                score = score * 0.5 + historical_accuracy * 0.5

            if article_count is not None:
                # More articles = higher credibility (with diminishing returns)
                article_factor = min(1.0, article_count / 1000.0)
                score = score * 0.7 + article_factor * 0.3

            if avg_engagement is not None:
                # Higher engagement = higher credibility
                engagement_factor = min(1.0, avg_engagement / 100.0)
                score = score * 0.8 + engagement_factor * 0.2

            return min(1.0, max(0.0, score))

        except Exception as e:
            logger.error(f"Error scoring publisher: {e}")
            return 0.5

    def score_batch(
        self,
        publishers: list[dict],
    ) -> dict[str, float]:
        """Score multiple publishers.

        Args:
            publishers: List of publisher info dicts

        Returns:
            Dictionary mapping publisher domain to credibility score
        """
        scores = {}
        for publisher in publishers:
            domain = publisher.get('domain')
            if domain:
                scores[domain] = self.score_publisher(
                    domain,
                    publisher.get('historical_accuracy'),
                    publisher.get('article_count'),
                    publisher.get('avg_engagement'),
                )
        return scores


class MLClassifierFactory:
    """Factory for creating ML classifiers."""

    _classifiers = {}

    @classmethod
    def get_domain_classifier(cls, model_name: str = 'distilbert-base-uncased') -> MLDomainClassifier:
        """Get or create domain classifier.

        Args:
            model_name: Name of the transformer model

        Returns:
            ML domain classifier instance
        """
        if model_name not in cls._classifiers:
            cls._classifiers[model_name] = MLDomainClassifier(model_name)
        return cls._classifiers[model_name]

    @classmethod
    def get_credibility_scorer(cls) -> MLPublisherCredibilityScorer:
        """Get or create credibility scorer.

        Returns:
            ML credibility scorer instance
        """
        if 'credibility_scorer' not in cls._classifiers:
            cls._classifiers['credibility_scorer'] = MLPublisherCredibilityScorer()
        return cls._classifiers['credibility_scorer']

