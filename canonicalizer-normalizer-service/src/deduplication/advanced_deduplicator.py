"""Advanced deduplication with LSH and semantic similarity."""

import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SemanticSimilarityResult:
    """Result of semantic similarity comparison."""

    article_id: str
    similarity_score: float
    is_duplicate: bool


class LSHDeduplicator:
    """Locality Sensitive Hashing for scalable deduplication."""

    def __init__(self, num_perm: int = 128, threshold: float = 0.9):
        """Initialize LSH deduplicator.

        Args:
            num_perm: Number of permutations for MinHash
            threshold: Similarity threshold for duplicate detection
        """
        self.num_perm = num_perm
        self.threshold = threshold
        self.available = False
        self.lsh = None
        self._initialize_lsh()

    def _initialize_lsh(self) -> None:
        """Initialize LSH index."""
        try:
            from datasketch import LSH, MinHash
            # Create LSH with 8 bands and 16 rows per band
            self.lsh = LSH(num_perm=self.num_perm, num_hashtables=8)
            self.MinHash = MinHash
            self.available = True
            logger.info(f"LSH deduplicator initialized with {self.num_perm} permutations")
        except ImportError:
            logger.warning("datasketch library not available, LSH disabled")
            self.available = False
        except Exception as e:
            logger.error(f"Error initializing LSH: {e}")
            self.available = False

    def add_article(self, article_id: str, content: str) -> bool:
        """Add article to LSH index.

        Args:
            article_id: Unique article identifier
            content: Article content

        Returns:
            True if added successfully, False otherwise
        """
        if not self.available or not content:
            return False

        try:
            minhash = self.MinHash(num_perm=self.num_perm)
            # Create 3-grams
            for d in self._get_shingles(content, 3):
                minhash.update(d.encode('utf8'))

            self.lsh.insert(article_id, minhash)
            return True
        except Exception as e:
            logger.error(f"Error adding article to LSH: {e}")
            return False

    def find_duplicates(self, article_id: str, content: str) -> list[str]:
        """Find potential duplicates using LSH.

        Args:
            article_id: Article identifier
            content: Article content

        Returns:
            List of potentially duplicate article IDs
        """
        if not self.available or not content:
            return []

        try:
            minhash = self.MinHash(num_perm=self.num_perm)
            for d in self._get_shingles(content, 3):
                minhash.update(d.encode('utf8'))

            # Query LSH for similar items
            candidates = self.lsh.query(minhash)
            # Filter out self
            return [cid for cid in candidates if cid != article_id]
        except Exception as e:
            logger.error(f"Error finding duplicates: {e}")
            return []

    @staticmethod
    def _get_shingles(text: str, k: int) -> list[str]:
        """Generate k-grams (shingles) from text.

        Args:
            text: Input text
            k: Shingle size

        Returns:
            List of k-grams
        """
        text = text.lower()
        shingles = []
        for i in range(len(text) - k + 1):
            shingles.append(text[i:i + k])
        return shingles


class SemanticDeduplicator:
    """Semantic similarity detection using sentence embeddings."""

    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """Initialize semantic deduplicator.

        Args:
            model_name: Name of the sentence transformer model
        """
        self.model_name = model_name
        self.available = False
        self.model = None
        self._initialize_model()

    def _initialize_model(self) -> None:
        """Initialize sentence transformer model."""
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name)
            self.available = True
            logger.info(f"Semantic deduplicator initialized with model: {self.model_name}")
        except ImportError:
            logger.warning(
                "sentence-transformers library not available, semantic deduplication disabled. "
                "Install with: pip install sentence-transformers"
            )
            self.available = False
        except Exception as e:
            logger.error(f"Error initializing semantic deduplicator: {e}")
            self.available = False

    def compute_similarity(self, text1: str, text2: str) -> float:
        """Compute semantic similarity between two texts.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score (0.0-1.0)
        """
        if not self.available or not text1 or not text2:
            return 0.0

        try:
            # Truncate texts to avoid token limit
            text1 = text1[:512]
            text2 = text2[:512]

            embeddings = self.model.encode([text1, text2])
            # Compute cosine similarity
            from sklearn.metrics.pairwise import cosine_similarity
            similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
            return float(similarity)
        except Exception as e:
            logger.error(f"Error computing semantic similarity: {e}")
            return 0.0

    def find_semantic_duplicates(
        self,
        article_id: str,
        content: str,
        candidates: list[tuple[str, str]],
        threshold: float = 0.85,
    ) -> list[SemanticSimilarityResult]:
        """Find semantic duplicates among candidates.

        Args:
            article_id: Article identifier
            content: Article content
            candidates: List of (candidate_id, candidate_content) tuples
            threshold: Similarity threshold for duplicate detection

        Returns:
            List of semantic similarity results
        """
        if not self.available or not content or not candidates:
            return []

        results = []
        try:
            for candidate_id, candidate_content in candidates:
                similarity = self.compute_similarity(content, candidate_content)
                is_duplicate = similarity >= threshold

                results.append(SemanticSimilarityResult(
                    article_id=candidate_id,
                    similarity_score=similarity,
                    is_duplicate=is_duplicate,
                ))
        except Exception as e:
            logger.error(f"Error finding semantic duplicates: {e}")

        return results


class AdvancedDeduplicator:
    """Advanced deduplication combining LSH and semantic similarity."""

    def __init__(
        self,
        lsh_threshold: float = 0.9,
        semantic_threshold: float = 0.85,
    ):
        """Initialize advanced deduplicator.

        Args:
            lsh_threshold: LSH similarity threshold
            semantic_threshold: Semantic similarity threshold
        """
        self.lsh = LSHDeduplicator(threshold=lsh_threshold)
        self.semantic = SemanticDeduplicator()
        self.lsh_threshold = lsh_threshold
        self.semantic_threshold = semantic_threshold
        self.articles = {}  # Store article content for semantic comparison

    def add_article(self, article_id: str, content: str) -> bool:
        """Add article to deduplication index.

        Args:
            article_id: Article identifier
            content: Article content

        Returns:
            True if added successfully
        """
        self.articles[article_id] = content
        self.lsh.add_article(article_id, content)
        return True

    def check_duplicate(self, article_id: str, content: str) -> Optional[SemanticSimilarityResult]:
        """Check if article is a duplicate.

        Args:
            article_id: Article identifier
            content: Article content

        Returns:
            Semantic similarity result if duplicate found, None otherwise
        """
        # First, use LSH to find candidates
        lsh_candidates = self.lsh.find_duplicates(article_id, content)

        if not lsh_candidates:
            return None

        # Then, use semantic similarity to verify
        candidate_pairs = [
            (cid, self.articles.get(cid, ""))
            for cid in lsh_candidates
            if cid in self.articles
        ]

        if not candidate_pairs:
            return None

        semantic_results = self.semantic.find_semantic_duplicates(
            article_id,
            content,
            candidate_pairs,
            self.semantic_threshold,
        )

        # Return the most similar duplicate
        duplicates = [r for r in semantic_results if r.is_duplicate]
        if duplicates:
            return max(duplicates, key=lambda x: x.similarity_score)

        return None

    def clear(self) -> None:
        """Clear all stored articles."""
        self.articles.clear()

