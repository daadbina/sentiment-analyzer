"""Vector normalization utilities."""

import logging
import numpy as np
from typing import Optional

logger = logging.getLogger(__name__)


def normalize_embeddings(
    embeddings: np.ndarray,
    norm: str = "l2",
) -> np.ndarray:
    """
    Normalize embeddings using specified norm.

    Args:
        embeddings: Array of shape (n_samples, embedding_dim)
        norm: Normalization type ("l2", "l1", or None)

    Returns:
        Normalized embeddings
    """
    if embeddings.size == 0:
        return embeddings

    if norm == "l2":
        return normalize_l2(embeddings)
    elif norm == "l1":
        return normalize_l1(embeddings)
    elif norm is None:
        return embeddings
    else:
        logger.warning(f"Unknown norm type: {norm}, returning unnormalized")
        return embeddings


def normalize_l2(embeddings: np.ndarray) -> np.ndarray:
    """
    L2 normalization (Euclidean norm).

    Args:
        embeddings: Array of shape (n_samples, embedding_dim)

    Returns:
        L2-normalized embeddings
    """
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    # Avoid division by zero
    norms = np.where(norms == 0, 1, norms)
    return embeddings / norms


def normalize_l1(embeddings: np.ndarray) -> np.ndarray:
    """
    L1 normalization (Manhattan norm).

    Args:
        embeddings: Array of shape (n_samples, embedding_dim)

    Returns:
        L1-normalized embeddings
    """
    norms = np.linalg.norm(embeddings, ord=1, axis=1, keepdims=True)
    # Avoid division by zero
    norms = np.where(norms == 0, 1, norms)
    return embeddings / norms


def get_embedding_norm(embedding: np.ndarray) -> float:
    """
    Get L2 norm of an embedding.

    Args:
        embedding: 1D array of embedding values

    Returns:
        L2 norm value
    """
    return float(np.linalg.norm(embedding))


def compute_cosine_similarity(
    embedding1: np.ndarray,
    embedding2: np.ndarray,
) -> float:
    """
    Compute cosine similarity between two embeddings.

    Args:
        embedding1: First embedding (1D array)
        embedding2: Second embedding (1D array)

    Returns:
        Cosine similarity score (-1 to 1)
    """
    # Normalize embeddings
    norm1 = np.linalg.norm(embedding1)
    norm2 = np.linalg.norm(embedding2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return float(np.dot(embedding1, embedding2) / (norm1 * norm2))


def cosine_similarity(embeddings: np.ndarray) -> np.ndarray:
    """
    Compute cosine similarity matrix for embeddings.

    Args:
        embeddings: Array of shape (n_samples, embedding_dim)

    Returns:
        Cosine similarity matrix of shape (n_samples, n_samples)
    """
    # Compute dot product matrix
    similarity = np.dot(embeddings, embeddings.T)
    return similarity

