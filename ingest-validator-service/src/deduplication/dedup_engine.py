"""Deduplication engine using MinHash and LSH for near-duplicate detection."""

import logging
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta
from datasketch import MinHash, MinHashLSH
import hashlib

logger = logging.getLogger(__name__)


class DuplicateResult:
    """Result of duplicate detection."""

    def __init__(
        self,
        is_duplicate: bool,
        similarity_score: float = 0.0,
        matched_article_id: Optional[str] = None,
        match_type: str = "none",  # "exact", "near", "none"
    ):
        """Initialize duplicate result.

        Args:
            is_duplicate: Whether article is duplicate
            similarity_score: Similarity score (0.0-1.0)
            matched_article_id: ID of matched article if duplicate
            match_type: Type of match (exact, near, none)
        """
        self.is_duplicate = is_duplicate
        self.similarity_score = similarity_score
        self.matched_article_id = matched_article_id
        self.match_type = match_type


class DeduplicationEngine:
    """Deduplication engine using MinHash and LSH.

    Implements R3 validation rule for duplicate detection.
    Supports both exact (checksum) and near-duplicate (MinHash) detection.
    """

    def __init__(
        self,
        num_perm: int = 128,
        similarity_threshold: float = 0.85,
        time_window_hours: int = 48,
    ):
        """Initialize deduplication engine.

        Args:
            num_perm: Number of permutations for MinHash (default 128)
            similarity_threshold: Similarity threshold for near-duplicates (default 0.85)
            time_window_hours: Time window for temporal filtering (default 48 hours)
        """
        self.num_perm = num_perm
        self.similarity_threshold = similarity_threshold
        self.time_window_hours = time_window_hours

        # LSH for near-duplicate detection
        self.lsh = MinHashLSH(threshold=similarity_threshold, num_perm=num_perm)

        # Storage for articles: checksum -> article metadata
        self.checksum_index: Dict[str, Dict] = {}

        # Storage for MinHash signatures: article_id -> MinHash
        self.minhash_index: Dict[str, MinHash] = {}

        # Storage for article metadata: article_id -> metadata
        self.article_metadata: Dict[str, Dict] = {}

    def add_article(
        self,
        article_id: str,
        checksum: str,
        content: str,
        published_at: datetime,
    ) -> None:
        """Add article to deduplication index.

        Args:
            article_id: Unique article identifier
            checksum: SHA-256 checksum of article content
            content: Article content (title + body)
            published_at: Publication timestamp
        """
        # Store checksum index for exact duplicate detection
        if checksum not in self.checksum_index:
            self.checksum_index[checksum] = {
                "article_id": article_id,
                "published_at": published_at,
            }

        # Generate MinHash signature for near-duplicate detection
        signature = self._generate_signature(content)
        self.minhash_index[article_id] = signature

        # Add to LSH index
        self.lsh.insert(article_id, signature)

        # Store article metadata
        self.article_metadata[article_id] = {
            "checksum": checksum,
            "published_at": published_at,
            "added_at": datetime.utcnow(),
        }

        logger.debug(f"Added article {article_id} to dedup index")

    def check_duplicate(
        self,
        checksum: str,
        content: str,
        published_at: datetime,
    ) -> DuplicateResult:
        """Check if article is duplicate.

        Args:
            checksum: SHA-256 checksum of article content
            content: Article content (title + body)
            published_at: Publication timestamp

        Returns:
            DuplicateResult with duplicate status and details
        """
        # Check for exact duplicate (checksum match)
        if checksum in self.checksum_index:
            existing = self.checksum_index[checksum]
            return DuplicateResult(
                is_duplicate=True,
                similarity_score=1.0,
                matched_article_id=existing["article_id"],
                match_type="exact",
            )

        # Check for near-duplicates using MinHash + LSH
        signature = self._generate_signature(content)
        candidates = self.lsh.query(signature)

        if candidates:
            # Filter by time window
            time_cutoff = published_at - timedelta(hours=self.time_window_hours)

            for candidate_id in candidates:
                if candidate_id not in self.article_metadata:
                    continue

                candidate_meta = self.article_metadata[candidate_id]
                candidate_published = candidate_meta["published_at"]

                # Skip if outside time window
                if candidate_published < time_cutoff:
                    continue

                # Calculate similarity score
                candidate_sig = self.minhash_index[candidate_id]
                similarity = self._calculate_similarity(signature, candidate_sig)

                if similarity >= self.similarity_threshold:
                    return DuplicateResult(
                        is_duplicate=True,
                        similarity_score=similarity,
                        matched_article_id=candidate_id,
                        match_type="near",
                    )

        # No duplicate found
        return DuplicateResult(
            is_duplicate=False,
            similarity_score=0.0,
            match_type="none",
        )

    def _generate_signature(self, content: str) -> MinHash:
        """Generate MinHash signature for content.

        Args:
            content: Article content

        Returns:
            MinHash signature
        """
        signature = MinHash(num_perm=self.num_perm)

        # Normalize content
        normalized = content.lower().strip()

        # Generate shingles (4-grams)
        shingles = self._generate_shingles(normalized, n=4)

        # Add shingles to MinHash
        for shingle in shingles:
            signature.update(shingle.encode("utf-8"))

        return signature

    def _generate_shingles(self, text: str, n: int = 4) -> List[str]:
        """Generate n-grams (shingles) from text.

        Args:
            text: Input text
            n: Shingle size (default 4)

        Returns:
            List of shingles
        """
        # Split into words
        words = text.split()

        # Generate word-level shingles
        shingles = []
        for i in range(len(words) - n + 1):
            shingle = " ".join(words[i : i + n])
            shingles.append(shingle)

        return shingles if shingles else [text]

    def _calculate_similarity(self, sig1: MinHash, sig2: MinHash) -> float:
        """Calculate Jaccard similarity between two MinHash signatures.

        Args:
            sig1: First MinHash signature
            sig2: Second MinHash signature

        Returns:
            Similarity score (0.0-1.0)
        """
        return sig1.jaccard(sig2)

    def get_stats(self) -> Dict:
        """Get deduplication engine statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            "num_articles": len(self.article_metadata),
            "num_checksums": len(self.checksum_index),
            "num_minhashes": len(self.minhash_index),
            "similarity_threshold": self.similarity_threshold,
            "time_window_hours": self.time_window_hours,
        }

    def clear(self) -> None:
        """Clear all deduplication data."""
        self.lsh = MinHashLSH(threshold=self.similarity_threshold, num_perm=self.num_perm)
        self.checksum_index.clear()
        self.minhash_index.clear()
        self.article_metadata.clear()
        logger.info("Deduplication engine cleared")

