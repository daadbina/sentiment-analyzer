"""Fuzzy deduplication module using MinHash."""

import logging
from typing import List, Dict, Optional
from datasketch import MinHash

from src.exceptions import FuzzyDeduplicationError
from src.models import FuzzyDeduplicationResult

logger = logging.getLogger(__name__)


class FuzzyDeduplicator:
    """Detects fuzzy duplicates using MinHash and LSH."""

    def __init__(self, threshold: float = 0.90, num_perm: int = 128):
        """Initialize fuzzy deduplicator.

        Args:
            threshold: Similarity threshold for deduplication
            num_perm: Number of permutations for MinHash
        """
        self.threshold = threshold
        self.num_perm = num_perm
        self.minhashes: Dict[str, MinHash] = {}

    def check_duplicate(self, article_id: str, content: str) -> FuzzyDeduplicationResult:
        """Check if article is a fuzzy duplicate.

        Args:
            article_id: Article ID
            content: Article content (title + body)

        Returns:
            FuzzyDeduplicationResult with duplicate check results
        """
        try:
            # Create MinHash for content
            minhash = self._create_minhash(content)
            self.minhashes[article_id] = minhash

            # Find similar articles by comparing with all existing minhashes
            similar_articles = []
            for existing_id, existing_minhash in self.minhashes.items():
                if existing_id != article_id:
                    similarity = self._calculate_similarity(
                        minhash,
                        existing_minhash,
                    )
                    if similarity >= self.threshold:
                        similar_articles.append({
                            "article_id": existing_id,
                            "similarity": similarity,
                        })

            # Determine primary article
            primary_article_id = None
            if similar_articles:
                # Use first similar article as primary (could be improved)
                primary_article_id = similar_articles[0]["article_id"]

            return FuzzyDeduplicationResult(
                similar_articles=similar_articles,
                primary_article_id=primary_article_id,
                checked=True,
            )

        except Exception as e:
            logger.error(f"Fuzzy deduplication failed for {article_id}: {e}")
            return FuzzyDeduplicationResult(error=str(e))

    def _create_minhash(self, content: str) -> MinHash:
        """Create MinHash from content.

        Args:
            content: Content to hash

        Returns:
            MinHash object
        """
        minhash = MinHash(num_perm=self.num_perm)

        # Split content into shingles (3-grams)
        shingles = self._create_shingles(content, 3)

        for shingle in shingles:
            minhash.update(shingle.encode("utf-8"))

        return minhash

    def _create_shingles(self, text: str, k: int = 3) -> List[str]:
        """Create k-grams (shingles) from text.

        Args:
            text: Text to create shingles from
            k: Shingle size

        Returns:
            List of shingles
        """
        # Normalize text
        text = text.lower().replace(" ", "")

        # Create shingles
        shingles = []
        for i in range(len(text) - k + 1):
            shingles.append(text[i : i + k])

        return shingles

    def _calculate_similarity(self, mh1: MinHash, mh2: MinHash) -> float:
        """Calculate Jaccard similarity between two MinHashes.

        Args:
            mh1: First MinHash
            mh2: Second MinHash

        Returns:
            Similarity score (0-1)
        """
        try:
            # Estimate Jaccard similarity
            similarity = mh1.jaccard(mh2)
            return min(1.0, max(0.0, similarity))
        except Exception as e:
            logger.error(f"Similarity calculation failed: {e}")
            return 0.0

    def clear(self) -> None:
        """Clear deduplication state."""
        self.minhashes.clear()
        logger.info("Fuzzy deduplicator cleared")

