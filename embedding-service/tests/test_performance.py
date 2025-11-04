"""Performance tests for embedding service."""

import pytest
import time
import numpy as np
from src.models.strategies.sentence_transformer import SentenceTransformerModel
from src.embedding.normalization import normalize_l2
from src.validation.embedding_validator import EmbeddingValidator
from src.batching.batch_optimizer import BatchOptimizer

pytestmark = pytest.mark.performance


@pytest.fixture
def model():
    """Load model for performance tests."""
    model = SentenceTransformerModel(
        model_name="all-MiniLM-L6-v2",
        device="cpu",
    )
    model.load()
    yield model
    model.unload()


def test_embedding_generation_performance(model):
    """Test embedding generation performance."""
    texts = ["This is a test sentence"] * 100

    start = time.time()
    embeddings = model.encode(texts)
    elapsed = time.time() - start

    # Should complete in reasonable time
    assert elapsed < 30.0
    assert embeddings.shape == (100, 384)

    # Calculate throughput
    throughput = len(texts) / elapsed
    print(f"Embedding throughput: {throughput:.2f} texts/sec")


def test_normalization_performance():
    """Test L2 normalization performance."""
    embeddings = np.random.randn(10000, 768)

    start = time.time()
    normalized = normalize_l2(embeddings)
    elapsed = time.time() - start

    # Should complete quickly
    assert elapsed < 1.0
    assert normalized.shape == embeddings.shape

    # Verify normalization
    norms = np.linalg.norm(normalized, axis=1)
    assert np.allclose(norms, 1.0)

    print(f"Normalization time: {elapsed*1000:.2f}ms for 10000 embeddings")


def test_validation_performance():
    """Test embedding validation performance."""
    validator = EmbeddingValidator(embedding_dim=768)
    embeddings = np.random.randn(10000, 768)

    start = time.time()
    for embedding in embeddings:
        validator.validate(embedding)
    elapsed = time.time() - start

    # Should complete quickly
    assert elapsed < 1.0

    print(f"Validation time: {elapsed*1000:.2f}ms for 10000 embeddings")


def test_batch_optimization_performance():
    """Test batch optimization performance."""
    optimizer = BatchOptimizer()

    texts = ["short text"] * 500 + ["this is a much longer text that contains many words"] * 500

    start = time.time()
    batch_size = optimizer.optimize_batch_size(texts)
    elapsed = time.time() - start

    # Should complete quickly
    assert elapsed < 1.0
    assert batch_size > 0

    print(f"Batch optimization time: {elapsed*1000:.2f}ms")


def test_batch_creation_performance():
    """Test batch creation performance."""
    optimizer = BatchOptimizer()

    texts = ["text"] * 1000

    start = time.time()
    batches = optimizer.create_balanced_batches(texts, batch_size=32)
    elapsed = time.time() - start

    # Should complete quickly
    assert elapsed < 1.0
    assert len(batches) > 0

    print(f"Batch creation time: {elapsed*1000:.2f}ms for 1000 texts")


def test_memory_efficiency():
    """Test memory efficiency of embedding storage."""
    # Create embeddings
    embeddings = np.random.randn(10000, 768).astype(np.float32)

    # Calculate memory usage
    memory_bytes = embeddings.nbytes
    memory_mb = memory_bytes / (1024 * 1024)

    # Should be reasonable
    assert memory_mb < 100  # Less than 100MB for 10k embeddings

    print(f"Memory usage: {memory_mb:.2f}MB for 10000 embeddings")


def test_concurrent_embedding_generation(model):
    """Test concurrent embedding generation."""
    import asyncio

    async def generate_embeddings(texts):
        return model.encode(texts)

    texts = ["This is a test sentence"] * 50

    start = time.time()
    embeddings = generate_embeddings(texts)
    elapsed = time.time() - start

    assert elapsed < 15.0
    assert embeddings.shape == (50, 384)

    print(f"Concurrent embedding time: {elapsed*1000:.2f}ms")


def test_large_batch_processing(model):
    """Test processing of large batches."""
    texts = ["This is a test sentence"] * 1000

    start = time.time()
    embeddings = model.encode(texts)
    elapsed = time.time() - start

    # Should handle large batches
    assert elapsed < 60.0
    assert embeddings.shape == (1000, 384)

    throughput = len(texts) / elapsed
    print(f"Large batch throughput: {throughput:.2f} texts/sec")


def test_similarity_computation_performance():
    """Test similarity computation performance."""
    embeddings = np.random.randn(1000, 768)
    query = np.random.randn(768)

    start = time.time()
    similarities = np.dot(embeddings, query)
    elapsed = time.time() - start

    # Should complete quickly
    assert elapsed < 0.1
    assert similarities.shape == (1000,)

    print(f"Similarity computation time: {elapsed*1000:.2f}ms for 1000 embeddings")


def test_batch_optimizer_scaling():
    """Test batch optimizer scaling with different text sizes."""
    optimizer = BatchOptimizer()

    # Small texts
    small_texts = ["short"] * 100
    batch_size_small = optimizer.optimize_batch_size(small_texts)

    # Large texts
    large_texts = ["this is a very long text with many words that takes up more space"] * 100
    batch_size_large = optimizer.optimize_batch_size(large_texts)

    # Large texts should have smaller batch size
    assert batch_size_large <= batch_size_small

    print(f"Small text batch size: {batch_size_small}")
    print(f"Large text batch size: {batch_size_large}")

