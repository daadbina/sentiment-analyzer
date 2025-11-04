"""Pooling strategies for embedding aggregation."""

import logging
from abc import ABC, abstractmethod
from typing import Tuple
import numpy as np
import torch

logger = logging.getLogger(__name__)


class PoolingStrategy(ABC):
    """Abstract base class for pooling strategies."""

    @abstractmethod
    def pool(
        self,
        embeddings: np.ndarray,
        attention_mask: np.ndarray = None,
    ) -> np.ndarray:
        """
        Pool embeddings to single vector.

        Args:
            embeddings: Array of shape (batch_size, seq_len, hidden_dim)
            attention_mask: Optional mask of shape (batch_size, seq_len)

        Returns:
            Pooled embeddings of shape (batch_size, hidden_dim)
        """
        pass


class MeanPooling(PoolingStrategy):
    """Mean pooling strategy."""

    def pool(
        self,
        embeddings: np.ndarray,
        attention_mask: np.ndarray = None,
    ) -> np.ndarray:
        """
        Apply mean pooling.

        Args:
            embeddings: Array of shape (batch_size, seq_len, hidden_dim)
            attention_mask: Optional mask of shape (batch_size, seq_len)

        Returns:
            Pooled embeddings of shape (batch_size, hidden_dim)
        """
        if attention_mask is None:
            return np.mean(embeddings, axis=1)

        # Expand mask for broadcasting
        mask_expanded = np.expand_dims(attention_mask, axis=-1)

        # Sum and divide by attention mask sum
        sum_embeddings = (embeddings * mask_expanded).sum(axis=1)
        sum_mask = mask_expanded.sum(axis=1)

        return sum_embeddings / np.maximum(sum_mask, 1e-9)


class MaxPooling(PoolingStrategy):
    """Max pooling strategy."""

    def pool(
        self,
        embeddings: np.ndarray,
        attention_mask: np.ndarray = None,
    ) -> np.ndarray:
        """
        Apply max pooling.

        Args:
            embeddings: Array of shape (batch_size, seq_len, hidden_dim)
            attention_mask: Optional mask of shape (batch_size, seq_len)

        Returns:
            Pooled embeddings of shape (batch_size, hidden_dim)
        """
        if attention_mask is None:
            return np.max(embeddings, axis=1)

        # Mask out padded positions with very negative values
        mask_expanded = np.expand_dims(attention_mask, axis=-1)
        masked_embeddings = embeddings.copy()
        masked_embeddings[mask_expanded == 0] = -np.inf

        return np.max(masked_embeddings, axis=1)


class CLSPooling(PoolingStrategy):
    """CLS token pooling strategy (first token)."""

    def pool(
        self,
        embeddings: np.ndarray,
        attention_mask: np.ndarray = None,
    ) -> np.ndarray:
        """
        Apply CLS pooling (use first token).

        Args:
            embeddings: Array of shape (batch_size, seq_len, hidden_dim)
            attention_mask: Optional mask (unused)

        Returns:
            Pooled embeddings of shape (batch_size, hidden_dim)
        """
        return embeddings[:, 0, :]


class WeightedMeanPooling(PoolingStrategy):
    """Weighted mean pooling with position-based weights."""

    def __init__(self, weight_decay: float = 0.1):
        """
        Initialize weighted mean pooling.

        Args:
            weight_decay: Decay factor for position weights
        """
        self.weight_decay = weight_decay

    def pool(
        self,
        embeddings: np.ndarray,
        attention_mask: np.ndarray = None,
    ) -> np.ndarray:
        """
        Apply weighted mean pooling.

        Args:
            embeddings: Array of shape (batch_size, seq_len, hidden_dim)
            attention_mask: Optional mask of shape (batch_size, seq_len)

        Returns:
            Pooled embeddings of shape (batch_size, hidden_dim)
        """
        batch_size, seq_len, hidden_dim = embeddings.shape

        # Create position-based weights (higher weight for earlier positions)
        positions = np.arange(seq_len)
        weights = np.exp(-self.weight_decay * positions)
        weights = weights / weights.sum()

        # Apply weights
        weighted_embeddings = embeddings * weights[np.newaxis, :, np.newaxis]

        if attention_mask is None:
            return weighted_embeddings.sum(axis=1)

        # Apply attention mask
        mask_expanded = np.expand_dims(attention_mask, axis=-1)
        masked_weighted = weighted_embeddings * mask_expanded

        return masked_weighted.sum(axis=1)


class PoolingFactory:
    """Factory for creating pooling strategies."""

    _strategies = {
        "mean": MeanPooling,
        "max": MaxPooling,
        "cls": CLSPooling,
        "weighted_mean": WeightedMeanPooling,
    }

    @classmethod
    def create(cls, strategy_name: str, **kwargs) -> PoolingStrategy:
        """
        Create pooling strategy.

        Args:
            strategy_name: Name of pooling strategy
            **kwargs: Additional arguments for strategy

        Returns:
            Pooling strategy instance

        Raises:
            ValueError: If strategy not found
        """
        if strategy_name not in cls._strategies:
            raise ValueError(
                f"Unknown pooling strategy: {strategy_name}. "
                f"Available: {list(cls._strategies.keys())}"
            )

        strategy_class = cls._strategies[strategy_name]
        return strategy_class(**kwargs)

    @classmethod
    def register(cls, name: str, strategy_class: type) -> None:
        """
        Register custom pooling strategy.

        Args:
            name: Strategy name
            strategy_class: Strategy class
        """
        cls._strategies[name] = strategy_class
        logger.info(f"Registered pooling strategy: {name}")

    @classmethod
    def get_available(cls) -> list:
        """Get list of available strategies."""
        return list(cls._strategies.keys())

