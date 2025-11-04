"""Abstract base class for embedding models."""

from abc import ABC, abstractmethod
from typing import List, Tuple
import numpy as np
import logging

logger = logging.getLogger(__name__)


class BaseEmbeddingModel(ABC):
    """Abstract base class for embedding models using Strategy pattern."""

    def __init__(
        self,
        model_name: str,
        device: str = "cpu",
        model_path: str = None,
    ):
        """
        Initialize embedding model.

        Args:
            model_name: Name/identifier of the model
            device: Device to run model on ("cuda" or "cpu")
            model_path: Optional path to local model
        """
        self.model_name = model_name
        self.device = device
        self.model_path = model_path
        self.model = None
        self.tokenizer = None
        self._is_loaded = False

    @abstractmethod
    def load(self) -> None:
        """Load model and tokenizer."""
        pass

    @abstractmethod
    def unload(self) -> None:
        """Unload model and tokenizer to free memory."""
        pass

    @abstractmethod
    def encode(
        self,
        texts: List[str],
        batch_size: int = 32,
        normalize: bool = True,
    ) -> np.ndarray:
        """
        Encode texts to embeddings.

        Args:
            texts: List of texts to encode
            batch_size: Batch size for processing
            normalize: Whether to L2-normalize embeddings

        Returns:
            Array of shape (len(texts), embedding_dim)
        """
        pass

    @abstractmethod
    def get_embedding_dimension(self) -> int:
        """Get embedding dimension."""
        pass

    @abstractmethod
    def get_max_sequence_length(self) -> int:
        """Get maximum sequence length supported by model."""
        pass

    @property
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._is_loaded

    def __enter__(self):
        """Context manager entry."""
        self.load()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.unload()

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"{self.__class__.__name__}("
            f"model_name={self.model_name}, "
            f"device={self.device}, "
            f"loaded={self._is_loaded})"
        )

