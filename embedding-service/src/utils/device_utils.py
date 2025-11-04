"""Device detection and management utilities."""

import logging
import torch
from typing import Literal

logger = logging.getLogger(__name__)


def is_gpu_available() -> bool:
    """Check if GPU is available and CUDA is properly configured."""
    try:
        if not torch.cuda.is_available():
            logger.info("CUDA not available")
            return False

        # Try to allocate a small tensor on GPU
        test_tensor = torch.zeros(1, device="cuda")
        del test_tensor
        torch.cuda.empty_cache()

        logger.info(
            f"GPU available: {torch.cuda.get_device_name(0)}, "
            f"CUDA version: {torch.version.cuda}"
        )
        return True
    except Exception as e:
        logger.warning(f"GPU check failed: {e}")
        return False


def get_device(
    device_config: str = "auto",
) -> Literal["cuda", "cpu"]:
    """
    Get the appropriate device for model inference.

    Args:
        device_config: Device configuration ("cuda", "cpu", or "auto")

    Returns:
        Device string ("cuda" or "cpu")
    """
    if device_config == "cuda":
        if is_gpu_available():
            logger.info("Using CUDA device")
            return "cuda"
        else:
            logger.warning("CUDA requested but not available, falling back to CPU")
            return "cpu"

    elif device_config == "cpu":
        logger.info("Using CPU device")
        return "cpu"

    elif device_config == "auto":
        if is_gpu_available():
            logger.info("Auto-detected GPU, using CUDA device")
            return "cuda"
        else:
            logger.info("Auto-detected no GPU, using CPU device")
            return "cpu"

    else:
        logger.warning(f"Unknown device config: {device_config}, defaulting to CPU")
        return "cpu"


def get_gpu_memory_info() -> dict:
    """Get GPU memory information."""
    if not is_gpu_available():
        return {
            "available": False,
            "total_memory_gb": 0,
            "used_memory_gb": 0,
            "free_memory_gb": 0,
        }

    try:
        total_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
        used_memory = torch.cuda.memory_allocated(0) / 1e9
        free_memory = total_memory - used_memory

        return {
            "available": True,
            "total_memory_gb": round(total_memory, 2),
            "used_memory_gb": round(used_memory, 2),
            "free_memory_gb": round(free_memory, 2),
            "utilization_percent": round((used_memory / total_memory) * 100, 2),
        }
    except Exception as e:
        logger.error(f"Failed to get GPU memory info: {e}")
        return {
            "available": False,
            "total_memory_gb": 0,
            "used_memory_gb": 0,
            "free_memory_gb": 0,
        }


def clear_gpu_cache():
    """Clear GPU cache to free memory."""
    if is_gpu_available():
        try:
            torch.cuda.empty_cache()
            logger.debug("GPU cache cleared")
        except Exception as e:
            logger.warning(f"Failed to clear GPU cache: {e}")


def get_optimal_batch_size(
    device: str,
    sequence_length: int,
    model_size_gb: float = 1.0,
) -> int:
    """
    Calculate optimal batch size based on device and sequence length.

    Args:
        device: Device type ("cuda" or "cpu")
        sequence_length: Average sequence length in tokens
        model_size_gb: Approximate model size in GB

    Returns:
        Recommended batch size
    """
    if device == "cuda":
        gpu_info = get_gpu_memory_info()
        if not gpu_info["available"]:
            return 8

        # Reserve 20% of GPU memory for safety
        available_memory_gb = gpu_info["free_memory_gb"] * 0.8

        # Rough estimate: each token takes ~2KB of memory
        memory_per_sample_gb = (sequence_length * 2 / 1024 / 1024) + (
            model_size_gb / 100
        )

        batch_size = max(1, int(available_memory_gb / memory_per_sample_gb))
        logger.debug(
            f"Calculated batch size: {batch_size} "
            f"(available: {available_memory_gb}GB, per_sample: {memory_per_sample_gb}GB)"
        )
        return batch_size
    else:
        # CPU: use smaller batch size
        return 8

