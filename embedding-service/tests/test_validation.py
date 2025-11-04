"""Tests for embedding validation."""

import pytest
import numpy as np
from src.validation.embedding_validator import EmbeddingValidator
from src.validation.quality_checks import QualityChecker
from src.embedding.normalization import normalize_l2


class TestEmbeddingValidator:
    """Test embedding validation."""

    def setup_method(self):
        """Setup test fixtures."""
        self.validator = EmbeddingValidator(expected_dimension=768)

    def test_valid_embedding(self):
        """Test validation of valid embedding."""
        embedding = np.random.randn(768).astype(np.float32)
        # Normalize the embedding
        embedding = normalize_l2(embedding.reshape(1, -1))[0]
        result = self.validator.validate_embedding(embedding)
        assert result["valid"] is True
        assert result["errors"] == []

    def test_wrong_dimension(self):
        """Test validation with wrong dimension."""
        embedding = np.random.randn(512).astype(np.float32)
        result = self.validator.validate_embedding(embedding)
        assert result["valid"] is False
        assert any("dimension" in e.lower() for e in result["errors"])

    def test_nan_values(self):
        """Test validation with NaN values."""
        embedding = np.random.randn(768).astype(np.float32)
        embedding[0] = np.nan
        result = self.validator.validate_embedding(embedding)
        assert result["valid"] is False
        assert any("nan" in e.lower() for e in result["errors"])

    def test_inf_values(self):
        """Test validation with infinite values."""
        embedding = np.random.randn(768).astype(np.float32)
        embedding[0] = np.inf
        result = self.validator.validate_embedding(embedding)
        assert result["valid"] is False
        assert any("inf" in e.lower() for e in result["errors"])

    def test_batch_validation(self):
        """Test batch validation."""
        embeddings = np.random.randn(10, 768).astype(np.float32)
        # Normalize the embeddings
        embeddings = normalize_l2(embeddings)
        result = self.validator.validate_batch(embeddings)
        assert result["valid"] is True
        assert result["valid_count"] == 10
        assert result["invalid_count"] == 0


class TestQualityChecker:
    """Test quality checking."""

    def test_embedding_diversity(self):
        """Test embedding diversity check."""
        embeddings = np.random.randn(100, 768).astype(np.float32)
        result = QualityChecker.check_embedding_diversity(embeddings)
        assert "mean_similarity" in result
        assert "diversity_score" in result
        # Allow small tolerance for floating point precision
        assert -0.01 <= result["diversity_score"] <= 1.01

    def test_embedding_statistics(self):
        """Test embedding statistics."""
        embeddings = np.random.randn(100, 768).astype(np.float32)
        result = QualityChecker.check_embedding_statistics(embeddings)
        assert "mean" in result
        assert "std" in result
        assert "min" in result
        assert "max" in result

    def test_embedding_sparsity(self):
        """Test embedding sparsity check."""
        embeddings = np.random.randn(100, 768).astype(np.float32)
        result = QualityChecker.check_embedding_sparsity(embeddings)
        assert "sparsity" in result
        assert 0 <= result["sparsity"] <= 1

    def test_full_quality_check(self):
        """Test full quality check."""
        embeddings = np.random.randn(100, 768).astype(np.float32)
        result = QualityChecker.perform_full_quality_check(embeddings)
        assert "diversity" in result
        assert "statistics" in result
        assert "sparsity" in result

