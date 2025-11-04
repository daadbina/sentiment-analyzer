"""Dynamic batching based on available resources."""

import logging
from typing import List, Optional

from src.utils.device_utils import get_optimal_batch_size, get_gpu_memory_info
from src.batching.batch_manager import BatchManager, Batch

logger = logging.getLogger(__name__)


class DynamicBatcher:
    """Dynamically adjusts batch size based on available resources."""

    def __init__(
        self,
        device: str = "cpu",
        base_batch_size: int = 32,
        min_batch_size: int = 1,
        max_batch_size: int = 128,
    ):
        """
        Initialize dynamic batcher.

        Args:
            device: Device type ("cuda" or "cpu")
            base_batch_size: Base batch size
            min_batch_size: Minimum batch size
            max_batch_size: Maximum batch size
        """
        self.device = device
        self.base_batch_size = base_batch_size
        self.min_batch_size = min_batch_size
        self.max_batch_size = max_batch_size
        self.batch_manager = BatchManager(base_batch_size)

    def get_optimal_batch_size(
        self,
        sequence_length: int = 384,
        model_size_gb: float = 1.0,
    ) -> int:
        """
        Calculate optimal batch size for current device.

        Args:
            sequence_length: Average sequence length
            model_size_gb: Model size in GB

        Returns:
            Optimal batch size
        """
        optimal = get_optimal_batch_size(
            self.device,
            sequence_length,
            model_size_gb,
        )

        # Clamp to min/max
        batch_size = max(self.min_batch_size, min(optimal, self.max_batch_size))

        logger.info(
            f"Calculated optimal batch size: {batch_size} "
            f"(device={self.device}, seq_len={sequence_length})"
        )

        return batch_size

    def create_dynamic_batches(
        self,
        texts: List[str],
        article_ids: List[str],
        sequence_length: int = 384,
        model_size_gb: float = 1.0,
    ) -> List[Batch]:
        """
        Create batches with dynamically calculated batch size.

        Args:
            texts: List of texts to batch
            article_ids: List of article IDs
            sequence_length: Average sequence length
            model_size_gb: Model size in GB

        Returns:
            List of Batch objects
        """
        batch_size = self.get_optimal_batch_size(sequence_length, model_size_gb)

        return self.batch_manager.create_batches(
            texts,
            article_ids,
            batch_size,
        )

    def get_memory_info(self) -> dict:
        """Get current memory information."""
        return get_gpu_memory_info()

