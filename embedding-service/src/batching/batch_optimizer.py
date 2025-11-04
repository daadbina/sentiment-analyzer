"""Batch optimization for efficient processing."""

import logging
from typing import List, Tuple
import numpy as np

logger = logging.getLogger(__name__)


class BatchOptimizer:
    """Optimizes batch creation for efficient processing."""

    def __init__(
        self,
        min_batch_size: int = 1,
        max_batch_size: int = 128,
        target_tokens: int = 512,
    ):
        """
        Initialize batch optimizer.

        Args:
            min_batch_size: Minimum batch size
            max_batch_size: Maximum batch size
            target_tokens: Target number of tokens per batch
        """
        self.min_batch_size = min_batch_size
        self.max_batch_size = max_batch_size
        self.target_tokens = target_tokens

    def optimize_batch_size(
        self,
        texts: List[str],
        avg_tokens_per_text: int = 50,
    ) -> int:
        """
        Calculate optimal batch size based on text lengths.

        Args:
            texts: List of texts to process
            avg_tokens_per_text: Average tokens per text

        Returns:
            Optimal batch size
        """
        if not texts:
            return self.min_batch_size

        # Calculate average text length
        avg_length = np.mean([len(text.split()) for text in texts])

        # Calculate batch size to reach target tokens
        batch_size = max(
            self.min_batch_size,
            min(
                self.max_batch_size,
                int(self.target_tokens / (avg_length * avg_tokens_per_text)),
            ),
        )

        logger.debug(
            f"Optimized batch size: {batch_size} "
            f"(avg_length={avg_length:.1f}, target_tokens={self.target_tokens})"
        )

        return batch_size

    def create_balanced_batches(
        self,
        texts: List[str],
        batch_size: int = None,
    ) -> List[List[str]]:
        """
        Create balanced batches by text length.

        Args:
            texts: List of texts to batch
            batch_size: Batch size (auto-calculated if None)

        Returns:
            List of batches
        """
        if batch_size is None:
            batch_size = self.optimize_batch_size(texts)

        # Sort texts by length
        indexed_texts = [(i, text) for i, text in enumerate(texts)]
        indexed_texts.sort(key=lambda x: len(x[1].split()))

        # Create batches with similar length texts
        batches = []
        current_batch = []

        for idx, text in indexed_texts:
            current_batch.append(text)

            if len(current_batch) >= batch_size:
                batches.append(current_batch)
                current_batch = []

        if current_batch:
            batches.append(current_batch)

        logger.debug(
            f"Created {len(batches)} balanced batches "
            f"(batch_size={batch_size})"
        )

        return batches

    def create_token_aware_batches(
        self,
        texts: List[str],
        max_tokens: int = 512,
    ) -> List[List[str]]:
        """
        Create batches with token count awareness.

        Args:
            texts: List of texts to batch
            max_tokens: Maximum tokens per batch

        Returns:
            List of batches
        """
        batches = []
        current_batch = []
        current_tokens = 0

        for text in texts:
            text_tokens = len(text.split())

            # If adding this text exceeds limit, start new batch
            if current_tokens + text_tokens > max_tokens and current_batch:
                batches.append(current_batch)
                current_batch = []
                current_tokens = 0

            current_batch.append(text)
            current_tokens += text_tokens

        if current_batch:
            batches.append(current_batch)

        logger.debug(
            f"Created {len(batches)} token-aware batches "
            f"(max_tokens={max_tokens})"
        )

        return batches

    def estimate_memory_usage(
        self,
        batch_size: int,
        seq_length: int,
        hidden_dim: int,
        dtype_bytes: int = 4,
    ) -> int:
        """
        Estimate memory usage for batch.

        Args:
            batch_size: Batch size
            seq_length: Sequence length
            hidden_dim: Hidden dimension
            dtype_bytes: Bytes per element (4 for float32)

        Returns:
            Estimated memory in bytes
        """
        # Model weights + activations + gradients
        model_memory = batch_size * seq_length * hidden_dim * dtype_bytes
        activation_memory = model_memory * 2  # Approximate
        gradient_memory = model_memory  # For training

        total = model_memory + activation_memory + gradient_memory

        logger.debug(
            f"Estimated memory: {total/1e9:.2f}GB "
            f"(batch={batch_size}, seq={seq_length}, dim={hidden_dim})"
        )

        return total

    def suggest_batch_size(
        self,
        available_memory: int,
        seq_length: int,
        hidden_dim: int,
        dtype_bytes: int = 4,
    ) -> int:
        """
        Suggest batch size based on available memory.

        Args:
            available_memory: Available memory in bytes
            seq_length: Sequence length
            hidden_dim: Hidden dimension
            dtype_bytes: Bytes per element

        Returns:
            Suggested batch size
        """
        # Estimate memory per sample
        memory_per_sample = seq_length * hidden_dim * dtype_bytes * 4  # 4x for overhead

        batch_size = max(
            self.min_batch_size,
            min(
                self.max_batch_size,
                int(available_memory / memory_per_sample),
            ),
        )

        logger.info(
            f"Suggested batch size: {batch_size} "
            f"(available={available_memory/1e9:.2f}GB, "
            f"per_sample={memory_per_sample/1e6:.2f}MB)"
        )

        return batch_size

    def get_batch_statistics(self, batches: List[List[str]]) -> dict:
        """
        Get statistics about batches.

        Args:
            batches: List of batches

        Returns:
            Dictionary with batch statistics
        """
        batch_sizes = [len(batch) for batch in batches]
        batch_tokens = [
            sum(len(text.split()) for text in batch) for batch in batches
        ]

        return {
            "num_batches": len(batches),
            "avg_batch_size": np.mean(batch_sizes),
            "min_batch_size": np.min(batch_sizes),
            "max_batch_size": np.max(batch_sizes),
            "avg_tokens": np.mean(batch_tokens),
            "min_tokens": np.min(batch_tokens),
            "max_tokens": np.max(batch_tokens),
            "total_texts": sum(batch_sizes),
            "total_tokens": sum(batch_tokens),
        }

