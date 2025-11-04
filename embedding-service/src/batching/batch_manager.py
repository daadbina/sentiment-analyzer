"""Batch management for efficient processing."""

import logging
from typing import List, Tuple
from dataclasses import dataclass

from src.metrics import embedding_batch_size

logger = logging.getLogger(__name__)


@dataclass
class Batch:
    """Represents a batch of texts to process."""

    texts: List[str]
    article_ids: List[str]
    batch_id: str

    def __len__(self) -> int:
        """Get batch size."""
        return len(self.texts)

    def __repr__(self) -> str:
        """String representation."""
        return f"Batch(id={self.batch_id}, size={len(self)})"


class BatchManager:
    """Manages batching of texts for efficient processing."""

    def __init__(self, batch_size: int = 32):
        """
        Initialize batch manager.

        Args:
            batch_size: Default batch size
        """
        self.batch_size = batch_size
        self._batch_counter = 0

    def create_batches(
        self,
        texts: List[str],
        article_ids: List[str],
        batch_size: int = None,
    ) -> List[Batch]:
        """
        Create batches from texts.

        Args:
            texts: List of texts to batch
            article_ids: List of article IDs corresponding to texts
            batch_size: Batch size (uses default if None)

        Returns:
            List of Batch objects
        """
        if batch_size is None:
            batch_size = self.batch_size

        if len(texts) != len(article_ids):
            raise ValueError("texts and article_ids must have same length")

        batches = []

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]
            batch_ids = article_ids[i : i + batch_size]

            batch_id = f"batch_{self._batch_counter}"
            self._batch_counter += 1

            batch = Batch(
                texts=batch_texts,
                article_ids=batch_ids,
                batch_id=batch_id,
            )

            batches.append(batch)
            embedding_batch_size.observe(len(batch))

            logger.debug(f"Created {batch}")

        logger.info(
            f"Created {len(batches)} batches from {len(texts)} texts "
            f"(batch_size={batch_size})"
        )

        return batches

    def get_batch_stats(self, batches: List[Batch]) -> dict:
        """Get statistics about batches."""
        if not batches:
            return {
                "total_batches": 0,
                "total_texts": 0,
                "avg_batch_size": 0,
                "min_batch_size": 0,
                "max_batch_size": 0,
            }

        sizes = [len(b) for b in batches]

        return {
            "total_batches": len(batches),
            "total_texts": sum(sizes),
            "avg_batch_size": sum(sizes) / len(batches),
            "min_batch_size": min(sizes),
            "max_batch_size": max(sizes),
        }

