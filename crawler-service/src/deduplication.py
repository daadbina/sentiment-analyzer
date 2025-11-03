"""
Deduplication module using MinHash and cosine similarity.

Detects duplicate articles using probabilistic data structures.
"""

import logging
from datasketch import MinHash, MinHashLSH

from .parser import ParsedArticle
from .exceptions import DuplicateArticleError
from .config import get_settings

logger = logging.getLogger(__name__)


class DeduplicationEngine:
    """
    Deduplicates articles using MinHash and LSH.

    Implements R3 validation rule for duplicate detection.
    """

    def __init__(self, num_perm: int = 128) -> None:
        """
        Initialize deduplication engine.

        Args:
            num_perm: Number of permutations for MinHash (default 128).
        """
        self.settings = get_settings()
        self.num_perm = num_perm
        self.lsh = MinHashLSH(threshold=0.5, num_perm=num_perm)
        self.cache: dict[str, MinHash] = {}
        self.max_cache_size = self.settings.dedup_cache_size

    def add_article(self, article: ParsedArticle) -> str:
        """
        Add article to deduplication cache.

        Args:
            article: Article to add.

        Returns:
            str: Article signature (MinHash ID).

        Raises:
            DuplicateArticleError: If article is duplicate.
        """
        signature = self._generate_signature(article)

        # Check if duplicate exists
        duplicates = self.lsh.query(signature)
        if duplicates:
            raise DuplicateArticleError(
                f"Duplicate article detected (similar to {len(duplicates)} existing)",
                article_id=article.canonical_url,
                error_code="DUPLICATE_FOUND",
            )

        # Add to LSH and cache
        article_id = article.canonical_url
        self.lsh.insert(article_id, signature)
        self.cache[article_id] = signature

        # Manage cache size
        if len(self.cache) > self.max_cache_size:
            self._evict_oldest()

        logger.debug(f"Added article to dedup cache: {article_id}")
        return article_id

    def is_duplicate(self, article: ParsedArticle) -> bool:
        """
        Check if article is duplicate.

        Args:
            article: Article to check.

        Returns:
            bool: True if article is duplicate.
        """
        try:
            signature = self._generate_signature(article)
            duplicates = self.lsh.query(signature)
            return len(duplicates) > 0
        except Exception as e:
            logger.error(f"Error checking for duplicates: {str(e)}")
            return False

    def get_similar_articles(
        self,
        article: ParsedArticle,
        threshold: float = 0.7,
    ) -> list[str]:
        """
        Find similar articles in cache.

        Args:
            article: Article to find similar articles for.
            threshold: Similarity threshold (0.0-1.0).

        Returns:
            list[str]: List of similar article IDs.
        """
        try:
            signature = self._generate_signature(article)
            duplicates = self.lsh.query(signature)
            return list(duplicates)
        except Exception as e:
            logger.error(f"Error finding similar articles: {str(e)}")
            return []

    def clear_cache(self) -> None:
        """Clear deduplication cache."""
        self.lsh = MinHashLSH(threshold=0.5, num_perm=self.num_perm)
        self.cache.clear()
        logger.info("Deduplication cache cleared")

    def get_cache_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            dict: Cache statistics.
        """
        return {
            "cache_size": len(self.cache),
            "max_cache_size": self.max_cache_size,
            "num_perm": self.num_perm,
            "cache_usage_percent": (len(self.cache) / self.max_cache_size) * 100,
        }

    def _generate_signature(self, article: ParsedArticle) -> MinHash:
        """
        Generate MinHash signature for article.

        Uses title and body for similarity computation.

        Args:
            article: Article to generate signature for.

        Returns:
            MinHash: Article signature.
        """
        signature = MinHash(num_perm=self.num_perm)

        # Combine title and body for hashing
        content = f"{article.title} {article.body}".lower()

        # Generate shingles (n-grams)
        shingles = self._generate_shingles(content, n=4)

        # Add shingles to MinHash
        for shingle in shingles:
            signature.update(shingle.encode("utf-8"))

        return signature

    def _generate_shingles(self, text: str, n: int = 4) -> set[str]:
        """
        Generate n-grams (shingles) from text.

        Args:
            text: Text to generate shingles from.
            n: Shingle size (default 4).

        Returns:
            set[str]: Set of shingles.
        """
        shingles = set()
        words = text.split()

        for i in range(len(words) - n + 1):
            shingle = " ".join(words[i : i + n])
            shingles.add(shingle)

        return shingles

    def _evict_oldest(self) -> None:
        """
        Evict oldest entries from cache when size limit reached.

        Uses simple FIFO eviction strategy.
        """
        # Remove 10% of cache when limit reached
        num_to_remove = int(self.max_cache_size * 0.1)
        keys_to_remove = list(self.cache.keys())[:num_to_remove]

        for key in keys_to_remove:
            del self.cache[key]

        logger.debug(f"Evicted {num_to_remove} entries from dedup cache")
