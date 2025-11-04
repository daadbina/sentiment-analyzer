"""GPU memory management and optimization."""

import logging
import torch
import psutil
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class GPUMemoryManager:
    """Manages GPU memory allocation and optimization."""

    def __init__(self, gpu_memory_fraction: float = 0.8):
        """
        Initialize GPU memory manager.

        Args:
            gpu_memory_fraction: Fraction of GPU memory to use (0.0-1.0)
        """
        self.gpu_memory_fraction = gpu_memory_fraction
        self.total_gpu_memory = None
        self.allocated_memory = 0
        self.reserved_memory = 0

    def initialize(self) -> None:
        """Initialize GPU memory settings."""
        if not torch.cuda.is_available():
            logger.warning("CUDA not available, GPU memory management disabled")
            return

        try:
            # Get total GPU memory
            self.total_gpu_memory = torch.cuda.get_device_properties(0).total_memory

            # Set memory fraction
            torch.cuda.set_per_process_memory_fraction(self.gpu_memory_fraction)

            logger.info(
                f"GPU memory initialized: "
                f"{self.total_gpu_memory / 1e9:.2f}GB "
                f"(using {self.gpu_memory_fraction*100:.0f}%)"
            )

        except Exception as e:
            logger.error(f"Failed to initialize GPU memory: {e}")

    def get_memory_stats(self) -> Dict[str, float]:
        """
        Get current GPU memory statistics.

        Returns:
            Dictionary with memory stats in bytes
        """
        if not torch.cuda.is_available():
            return {
                "total": 0,
                "allocated": 0,
                "reserved": 0,
                "free": 0,
            }

        try:
            allocated = torch.cuda.memory_allocated()
            reserved = torch.cuda.memory_reserved()
            total = self.total_gpu_memory or torch.cuda.get_device_properties(0).total_memory

            return {
                "total": total,
                "allocated": allocated,
                "reserved": reserved,
                "free": total - allocated,
            }

        except Exception as e:
            logger.error(f"Failed to get GPU memory stats: {e}")
            return {
                "total": 0,
                "allocated": 0,
                "reserved": 0,
                "free": 0,
            }

    def get_memory_usage_percent(self) -> float:
        """
        Get GPU memory usage percentage.

        Returns:
            Memory usage as percentage (0-100)
        """
        stats = self.get_memory_stats()
        if stats["total"] == 0:
            return 0.0

        return (stats["allocated"] / stats["total"]) * 100

    def clear_cache(self) -> None:
        """Clear GPU cache to free memory."""
        if torch.cuda.is_available():
            try:
                torch.cuda.empty_cache()
                logger.debug("GPU cache cleared")
            except Exception as e:
                logger.error(f"Failed to clear GPU cache: {e}")

    def should_offload_model(self, threshold: float = 0.85) -> bool:
        """
        Check if model should be offloaded to CPU.

        Args:
            threshold: Memory usage threshold (0-1)

        Returns:
            True if memory usage exceeds threshold
        """
        usage_percent = self.get_memory_usage_percent()
        return usage_percent > (threshold * 100)

    def get_optimal_batch_size(
        self,
        model_memory_per_sample: int,
        min_batch_size: int = 1,
        max_batch_size: int = 128,
    ) -> int:
        """
        Calculate optimal batch size based on available GPU memory.

        Args:
            model_memory_per_sample: Estimated memory per sample in bytes
            min_batch_size: Minimum batch size
            max_batch_size: Maximum batch size

        Returns:
            Optimal batch size
        """
        stats = self.get_memory_stats()
        if stats["free"] == 0:
            return min_batch_size

        # Use 80% of free memory for batch processing
        available_memory = stats["free"] * 0.8

        # Calculate batch size
        batch_size = int(available_memory / model_memory_per_sample)

        # Clamp to min/max
        batch_size = max(min_batch_size, min(batch_size, max_batch_size))

        logger.debug(
            f"Calculated optimal batch size: {batch_size} "
            f"(available: {available_memory/1e9:.2f}GB, "
            f"per_sample: {model_memory_per_sample/1e6:.2f}MB)"
        )

        return batch_size

    def log_memory_stats(self) -> None:
        """Log current GPU memory statistics."""
        stats = self.get_memory_stats()
        usage_percent = self.get_memory_usage_percent()

        logger.info(
            f"GPU Memory: "
            f"allocated={stats['allocated']/1e9:.2f}GB, "
            f"reserved={stats['reserved']/1e9:.2f}GB, "
            f"free={stats['free']/1e9:.2f}GB, "
            f"usage={usage_percent:.1f}%"
        )


class CPUMemoryManager:
    """Manages CPU memory allocation and optimization."""

    def __init__(self, memory_fraction: float = 0.8):
        """
        Initialize CPU memory manager.

        Args:
            memory_fraction: Fraction of CPU memory to use (0.0-1.0)
        """
        self.memory_fraction = memory_fraction
        self.total_memory = psutil.virtual_memory().total

    def get_memory_stats(self) -> Dict[str, float]:
        """
        Get current CPU memory statistics.

        Returns:
            Dictionary with memory stats in bytes
        """
        try:
            vm = psutil.virtual_memory()
            return {
                "total": vm.total,
                "available": vm.available,
                "used": vm.used,
                "free": vm.free,
            }
        except Exception as e:
            logger.error(f"Failed to get CPU memory stats: {e}")
            return {
                "total": 0,
                "available": 0,
                "used": 0,
                "free": 0,
            }

    def get_memory_usage_percent(self) -> float:
        """
        Get CPU memory usage percentage.

        Returns:
            Memory usage as percentage (0-100)
        """
        try:
            return psutil.virtual_memory().percent
        except Exception as e:
            logger.error(f"Failed to get CPU memory usage: {e}")
            return 0.0

    def should_reduce_batch_size(self, threshold: float = 0.85) -> bool:
        """
        Check if batch size should be reduced.

        Args:
            threshold: Memory usage threshold (0-1)

        Returns:
            True if memory usage exceeds threshold
        """
        usage_percent = self.get_memory_usage_percent()
        return usage_percent > (threshold * 100)

    def log_memory_stats(self) -> None:
        """Log current CPU memory statistics."""
        stats = self.get_memory_stats()
        usage_percent = self.get_memory_usage_percent()

        logger.info(
            f"CPU Memory: "
            f"used={stats['used']/1e9:.2f}GB, "
            f"available={stats['available']/1e9:.2f}GB, "
            f"total={stats['total']/1e9:.2f}GB, "
            f"usage={usage_percent:.1f}%"
        )

