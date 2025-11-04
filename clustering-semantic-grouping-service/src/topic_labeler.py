"""Topic labeling for clusters using TF-IDF and optional LLM."""

import logging
from typing import List, Optional
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

logger = logging.getLogger(__name__)


class TopicLabeler:
    """Generates topic labels for clusters."""

    def __init__(self, max_features: int = 1000, max_label_words: int = 5):
        """
        Initialize topic labeler.

        Args:
            max_features: Maximum TF-IDF features
            max_label_words: Maximum words in label
        """
        self.max_features = max_features
        self.max_label_words = max_label_words
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            stop_words="english",
            ngram_range=(1, 2),
        )
        logger.info(
            f"Initialized TopicLabeler: max_features={max_features}, "
            f"max_label_words={max_label_words}"
        )

    def generate_label_extractive(
        self,
        articles: List[dict],
        top_k: int = 5,
    ) -> str:
        """
        Generate label using TF-IDF extractive method.

        Args:
            articles: List of article metadata
            top_k: Number of top terms to consider

        Returns:
            Topic label string
        """
        if not articles:
            return "Unknown Topic"

        # Extract text from articles
        texts = []
        for article in articles:
            title = article.get("title", "")
            body = article.get("body", "")
            text = f"{title} {body}".strip()
            if text:
                texts.append(text)

        if not texts:
            return "Unknown Topic"

        try:
            # Compute TF-IDF
            tfidf_matrix = self.vectorizer.fit_transform(texts)
            feature_names = self.vectorizer.get_feature_names_out()

            # Get mean TF-IDF scores
            mean_tfidf = np.asarray(tfidf_matrix.mean(axis=0)).flatten()

            # Get top terms
            top_indices = np.argsort(mean_tfidf)[-top_k:][::-1]
            top_terms = [feature_names[i] for i in top_indices]

            # Create label
            label = " ".join(top_terms[: self.max_label_words])

            logger.debug(f"Generated extractive label: {label}")
            return label

        except Exception as e:
            logger.error(f"Error generating extractive label: {e}", exc_info=True)
            return "Unknown Topic"

    def generate_label_abstractive(
        self,
        articles: List[dict],
        llm_client: Optional[object] = None,
    ) -> str:
        """
        Generate label using LLM abstractive method.

        Args:
            articles: List of article metadata
            llm_client: Optional LLM client for abstractive summarization

        Returns:
            Topic label string
        """
        if llm_client is None:
            logger.debug("No LLM client provided, falling back to extractive method")
            return self.generate_label_extractive(articles)

        try:
            # Extract titles and summaries
            titles = [a.get("title", "") for a in articles if a.get("title")]
            summaries = [a.get("summary", "") for a in articles if a.get("summary")]

            if not titles and not summaries:
                return "Unknown Topic"

            # Prepare prompt
            context = "\n".join(titles[:5] + summaries[:5])
            prompt = f"Generate a concise topic label (max 5 words) for these articles:\n{context}"

            # Call LLM
            label = llm_client.generate(prompt, max_tokens=20)

            logger.debug(f"Generated abstractive label: {label}")
            return label

        except Exception as e:
            logger.error(f"Error generating abstractive label: {e}", exc_info=True)
            return self.generate_label_extractive(articles)

    def generate_label(
        self,
        articles: List[dict],
        method: str = "extractive",
        llm_client: Optional[object] = None,
    ) -> str:
        """
        Generate topic label using specified method.

        Args:
            articles: List of article metadata
            method: "extractive" or "abstractive"
            llm_client: Optional LLM client for abstractive method

        Returns:
            Topic label string
        """
        if method == "extractive":
            return self.generate_label_extractive(articles)
        elif method == "abstractive":
            return self.generate_label_abstractive(articles, llm_client)
        else:
            logger.warning(f"Unknown method: {method}, using extractive")
            return self.generate_label_extractive(articles)

