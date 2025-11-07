"""Inference package."""

from .batch_predictor import BatchPredictor
from .streaming_predictor import StreamingPredictor


__all__ = [
    "BatchPredictor",
    "StreamingPredictor",
]

