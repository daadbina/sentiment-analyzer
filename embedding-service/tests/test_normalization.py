"""Tests for embedding normalization."""

import pytest
import numpy as np
from src.embedding.normalization import normalize_l2, normalize_l1, cosine_similarity


class TestNormalization:
    """Test normalization functions."""

    def test_l2_normalization(self):
        """Test L2 normalization."""
        embeddings = np.random.randn(10, 768).astype(np.float32)
        normalized = normalize_l2(embeddings)

        # Check shape is preserved
        assert normalized.shape == embeddings.shape

        # Check norms are close to 1
        norms = np.linalg.norm(normalized, axis=1)
        np.testing.assert_array_almost_equal(norms, np.ones(10), decimal=5)

    def test_l1_normalization(self):
        """Test L1 normalization."""
        embeddings = np.random.randn(10, 768).astype(np.float32)
        normalized = normalize_l1(embeddings)

        # Check shape is preserved
        assert normalized.shape == embeddings.shape

        # Check L1 norms are close to 1
        norms = np.sum(np.abs(normalized), axis=1)
        np.testing.assert_array_almost_equal(norms, np.ones(10), decimal=5)

    def test_cosine_similarity(self):
        """Test cosine similarity computation."""
        embeddings = np.random.randn(10, 768).astype(np.float32)
        normalized = normalize_l2(embeddings)

        # Compute similarity matrix
        similarity = cosine_similarity(normalized)

        # Check shape
        assert similarity.shape == (10, 10)

        # Check diagonal is 1 (self-similarity) - allow small tolerance for floating point
        np.testing.assert_array_almost_equal(
            np.diag(similarity), np.ones(10), decimal=4
        )

        # Check symmetry
        np.testing.assert_array_almost_equal(similarity, similarity.T, decimal=5)

        # Check values are in [-1, 1] - allow small tolerance for floating point
        assert np.all(similarity >= -1.01)
        assert np.all(similarity <= 1.01)

    def test_zero_vector_normalization(self):
        """Test normalization of zero vector."""
        embeddings = np.zeros((1, 768), dtype=np.float32)
        normalized = normalize_l2(embeddings)

        # Should handle gracefully
        assert normalized.shape == embeddings.shape
        assert not np.any(np.isnan(normalized))

    def test_single_embedding(self):
        """Test normalization of single embedding."""
        embedding = np.random.randn(768).astype(np.float32)
        embeddings = embedding.reshape(1, -1)

        normalized = normalize_l2(embeddings)
        norm = np.linalg.norm(normalized)

        np.testing.assert_almost_equal(norm, 1.0, decimal=5)

