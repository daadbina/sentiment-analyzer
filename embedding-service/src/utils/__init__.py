"""Utility modules for Embedding Service."""

from src.utils.device_utils import get_device, is_gpu_available
from src.utils.checksum import compute_model_hash, compute_tokenizer_hash
from src.utils.trace import get_trace_id, set_trace_id

__all__ = [
    "get_device",
    "is_gpu_available",
    "compute_model_hash",
    "compute_tokenizer_hash",
    "get_trace_id",
    "set_trace_id",
]

