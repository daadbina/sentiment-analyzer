"""Topic labeling for clusters using TF-IDF and optional LLM."""

import logging
from typing import List, Optional, Set
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

logger = logging.getLogger(__name__)


class TopicLabeler:
    """Generates topic labels for clusters."""

    # Multilingual stop words for English, Spanish, Italian, Farsi, Chinese, Russian
    MULTILINGUAL_STOP_WORDS = {
        # English
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'what', 'which', 'who', 'when', 'where', 'why', 'how',
        # Spanish
        'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas', 'de', 'del', 'al', 'y', 'o', 'pero', 'en', 'con', 'por', 'para', 'como', 'es', 'son', 'era', 'fue', 'ser', 'estar', 'que', 'se', 'le', 'lo', 'su', 'sus', 'mi', 'mis', 'tu', 'tus', 'este', 'esta', 'estos', 'estas', 'ese', 'esa', 'esos', 'esas',
        # Italian
        'il', 'lo', 'i', 'gli', 'le', 'uno', 'una', 'un', 'di', 'da', 'in', 'con', 'su', 'per', 'tra', 'fra', 'e', 'o', 'ma', 'come', 'che', 'chi', 'cui', 'si', 'ci', 'ne', 'questo', 'questa', 'questi', 'queste', 'quello', 'quella', 'quelli', 'quelle',
        # Farsi (Persian) - common words in Latin script
        'va', 'be', 'az', 'dar', 'ba', 'ke', 'ra', 'ta', 'ya',
        # Chinese (common in pinyin/romanized)
        'de', 'le', 'zai', 'shi', 'bu', 'yi', 'ge', 'wo', 'ni', 'ta', 'men',
        # Russian (common in Latin transliteration)
        'i', 'v', 'na', 'ne', 's', 'po', 'za', 'k', 'ot', 'do', 'iz', 'u', 'o',
        # Common numbers and years
        '2020', '2021', '2022', '2023', '2024', '2025',
        # Common web/news terms
        'http', 'https', 'www', 'com', 'html', 'news', 'article', 'said', 'says', 'according', 'reported'
    }

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
            stop_words=list(self.MULTILINGUAL_STOP_WORDS),
            ngram_range=(1, 2),
            min_df=1,  # Allow rare terms (important for small clusters)
            max_df=0.8,  # Filter terms appearing in >80% of docs
        )
        logger.info(
            f"Initialized TopicLabeler: max_features={max_features}, "
            f"max_label_words={max_label_words}, multilingual_stop_words={len(self.MULTILINGUAL_STOP_WORDS)}"
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
        # Priority: body (from Qdrant) > content > title only
        texts = []
        for article in articles:
            title = article.get("title", "")
            # Try "body" first (from Qdrant), then "content", then title only
            body = article.get("body") or article.get("content", "")

            if body:
                # Use title + body for better topic extraction
                text = f"{title} {body}".strip()
            else:
                # Fall back to title only if no body available
                text = title.strip()

            if text:
                texts.append(text)
                logger.debug(
                    f"Added text for article {article.get('article_id', 'unknown')}: "
                    f"{len(text)} chars (has_body={bool(body)})"
                )

        if not texts:
            logger.warning("No text available for topic labeling")
            return "Unknown Topic"

        try:
            # Compute TF-IDF
            tfidf_matrix = self.vectorizer.fit_transform(texts)
            feature_names = self.vectorizer.get_feature_names_out()

            # Get mean TF-IDF scores across all documents
            mean_tfidf = np.asarray(tfidf_matrix.mean(axis=0)).flatten()

            # Get top terms by TF-IDF score
            top_indices = np.argsort(mean_tfidf)[-top_k:][::-1]
            top_terms = [feature_names[i] for i in top_indices]

            # Filter out any remaining stop words or short terms
            filtered_terms = [
                term for term in top_terms
                if len(term) > 2 and term.lower() not in self.MULTILINGUAL_STOP_WORDS
            ]

            # Create label from top terms
            label = " ".join(filtered_terms[: self.max_label_words])

            logger.info(
                f"Generated extractive label: '{label}' from {len(texts)} articles, "
                f"top_terms={top_terms[:self.max_label_words]}"
            )
            return label if label else "Unknown Topic"

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

