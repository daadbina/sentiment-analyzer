"""Sentiment analysis using language-specific models."""

import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """Analyze sentiment of text using language-specific models."""

    def __init__(self):
        """Initialize sentiment analyzer."""
        self.vader_available = False
        self.textblob_available = False
        self._initialize_vader()
        self._initialize_textblob()

    def _initialize_vader(self) -> None:
        """Initialize VADER sentiment analyzer for English."""
        try:
            from nltk.sentiment import SentimentIntensityAnalyzer
            import nltk

            # Download required VADER lexicon
            try:
                nltk.data.find("sentiment/vader_lexicon")
            except LookupError:
                logger.info("Downloading VADER lexicon...")
                nltk.download("vader_lexicon", quiet=True)

            self.vader = SentimentIntensityAnalyzer()
            self.vader_available = True
            logger.info("VADER sentiment analyzer initialized")
        except ImportError:
            logger.warning("nltk not available, VADER sentiment analysis disabled")
            self.vader_available = False
        except Exception as e:
            logger.error(f"Error initializing VADER: {e}")
            self.vader_available = False

    def _initialize_textblob(self) -> None:
        """Initialize TextBlob for fallback sentiment analysis."""
        try:
            from textblob import TextBlob

            self.textblob = TextBlob
            self.textblob_available = True
            logger.info("TextBlob sentiment analyzer initialized")
        except ImportError:
            logger.warning("textblob not available, TextBlob sentiment analysis disabled")
            self.textblob_available = False
        except Exception as e:
            logger.error(f"Error initializing TextBlob: {e}")
            self.textblob_available = False

    def analyze(self, text: str, language: str = "en") -> float:
        """Analyze sentiment of text.

        Args:
            text: Text to analyze
            language: Language code (ISO 639-1)

        Returns:
            Sentiment score in range [-1.0, 1.0]
        """
        if not text or not isinstance(text, str):
            logger.debug("Empty or invalid text for sentiment analysis")
            return 0.0

        try:
            # Use VADER for English
            if language == "en" and self.vader_available:
                return self._analyze_vader(text)

            # Use TextBlob as fallback for other languages
            if self.textblob_available:
                return self._analyze_textblob(text)

            # Default to neutral if no analyzer available
            logger.warning(
                f"No sentiment analyzer available for language {language}, returning neutral"
            )
            return 0.0

        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return 0.0

    def _analyze_vader(self, text: str) -> float:
        """Analyze sentiment using VADER.

        Args:
            text: Text to analyze

        Returns:
            Sentiment score in range [-1.0, 1.0]
        """
        try:
            # VADER returns compound score in range [-1, 1]
            scores = self.vader.polarity_scores(text)
            compound = scores.get("compound", 0.0)

            logger.debug(
                f"VADER sentiment: compound={compound:.3f}, "
                f"pos={scores.get('pos', 0):.3f}, "
                f"neu={scores.get('neu', 0):.3f}, "
                f"neg={scores.get('neg', 0):.3f}"
            )

            return float(compound)
        except Exception as e:
            logger.error(f"Error in VADER analysis: {e}")
            return 0.0

    def _analyze_textblob(self, text: str) -> float:
        """Analyze sentiment using TextBlob.

        Args:
            text: Text to analyze

        Returns:
            Sentiment score in range [-1.0, 1.0]
        """
        try:
            # TextBlob polarity is in range [-1, 1]
            blob = self.textblob(text)
            polarity = blob.sentiment.polarity

            logger.debug(
                f"TextBlob sentiment: polarity={polarity:.3f}, "
                f"subjectivity={blob.sentiment.subjectivity:.3f}"
            )

            return float(polarity)
        except Exception as e:
            logger.error(f"Error in TextBlob analysis: {e}")
            return 0.0

