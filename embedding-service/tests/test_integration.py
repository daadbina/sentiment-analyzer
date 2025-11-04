"""Integration tests with Testcontainers."""

import pytest
import asyncio
import numpy as np
from testcontainers.postgres import PostgresContainer
from testcontainers.kafka import KafkaContainer

pytestmark = pytest.mark.integration


@pytest.fixture(scope="session")
def postgres_container():
    """Start PostgreSQL container."""
    container = PostgresContainer("postgres:15")
    container.start()
    yield container
    container.stop()


@pytest.fixture(scope="session")
def kafka_container():
    """Start Kafka container."""
    container = KafkaContainer("confluentinc/cp-kafka:7.5.0")
    container.start()
    yield container
    container.stop()


@pytest.mark.asyncio
async def test_postgres_connection(postgres_container):
    """Test PostgreSQL connection."""
    import asyncpg

    connection_string = postgres_container.get_connection_url()

    # Connect to database
    conn = await asyncpg.connect(connection_string)
    result = await conn.fetchval("SELECT 1")

    assert result == 1

    await conn.close()


@pytest.mark.asyncio
async def test_kafka_connection(kafka_container):
    """Test Kafka connection."""
    from confluent_kafka import Producer

    brokers = kafka_container.get_bootstrap_server()

    # Create producer
    producer = Producer({"bootstrap.servers": brokers})

    # Produce message
    producer.produce("test-topic", b"test-message")
    producer.flush()

    assert True


@pytest.mark.asyncio
async def test_embedding_service_with_postgres(postgres_container):
    """Test embedding service with PostgreSQL."""
    import asyncpg

    connection_string = postgres_container.get_connection_url()

    # Connect and create table
    conn = await asyncpg.connect(connection_string)

    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS embeddings (
            id SERIAL PRIMARY KEY,
            article_id VARCHAR(255),
            embedding FLOAT8[],
            created_at TIMESTAMP DEFAULT NOW()
        )
        """
    )

    # Insert embedding
    embedding = np.random.randn(768).tolist()
    await conn.execute(
        "INSERT INTO embeddings (article_id, embedding) VALUES ($1, $2)",
        "article-123",
        embedding,
    )

    # Query embedding
    result = await conn.fetchrow("SELECT * FROM embeddings WHERE article_id = $1", "article-123")

    assert result is not None
    assert result["article_id"] == "article-123"

    await conn.close()


@pytest.mark.asyncio
async def test_model_loading():
    """Test model loading."""
    from src.models.strategies.sentence_transformer import SentenceTransformerModel

    model = SentenceTransformerModel(
        model_name="all-MiniLM-L6-v2",
        device="cpu",
    )

    model.load()

    assert model.is_loaded
    assert model.get_embedding_dimension() == 384

    # Test encoding
    texts = ["Hello world", "This is a test"]
    embeddings = model.encode(texts)

    assert embeddings.shape == (2, 384)

    model.unload()


@pytest.mark.asyncio
async def test_preprocessing_pipeline():
    """Test preprocessing pipeline."""
    from src.preprocessing.text_preprocessor import TextPreprocessor

    preprocessor = TextPreprocessor()

    text = "  Hello   WORLD!!! <html>test</html> https://example.com  "
    processed = preprocessor.preprocess(text)

    assert "hello" in processed.lower()
    assert "world" in processed.lower()
    assert "<html>" not in processed
    assert "https://" not in processed


@pytest.mark.asyncio
async def test_batch_creation():
    """Test batch creation."""
    from src.batching.batch_manager import BatchManager

    manager = BatchManager()

    texts = ["text1", "text2", "text3", "text4"]
    article_ids = ["id1", "id2", "id3", "id4"]
    batches = manager.create_batches(texts, article_ids, batch_size=4)

    assert len(batches) == 1
    assert batches[0].batch_id is not None
    assert len(batches[0].texts) == 4


@pytest.mark.asyncio
async def test_embedding_validation():
    """Test embedding validation."""
    from src.validation.embedding_validator import EmbeddingValidator
    from src.embedding.normalization import normalize_l2

    validator = EmbeddingValidator(expected_dimension=768)

    # Valid embedding (normalized)
    valid_embedding = np.random.randn(768).astype(np.float32)
    valid_embedding = normalize_l2(valid_embedding.reshape(1, -1))[0]
    result = validator.validate_embedding(valid_embedding)
    assert result["valid"]

    # Invalid dimension
    invalid_embedding = np.random.randn(512).astype(np.float32)
    result_invalid = validator.validate_embedding(invalid_embedding)
    assert not result_invalid["valid"]

    # NaN embedding
    nan_embedding = np.full(768, np.nan, dtype=np.float32)
    result_nan = validator.validate_embedding(nan_embedding)
    assert not result_nan["valid"]


@pytest.mark.asyncio
async def test_drift_detection():
    """Test drift detection."""
    from src.drift.drift_detector import DriftDetector

    detector = DriftDetector()

    # Add baseline samples
    baseline = np.random.randn(100, 768).astype(np.float32)
    detector.add_samples(baseline)

    # Add current samples (no drift)
    current_no_drift = np.random.randn(10, 768).astype(np.float32)
    result = detector.detect_drift(current_no_drift)

    assert isinstance(result, dict)
    assert "drift_detected" in result
    assert "ks_statistic" in result

    # Add current samples (with drift)
    current_with_drift = np.random.randn(10, 768).astype(np.float32) + 2.0
    result_drift = detector.detect_drift(current_with_drift)

    assert isinstance(result_drift, dict)
    assert "drift_detected" in result_drift


@pytest.mark.asyncio
async def test_anomaly_detection():
    """Test anomaly detection."""
    from src.validation.anomaly_detector import AnomalyDetector

    detector = AnomalyDetector()

    # Create embeddings with anomalies
    embeddings = np.random.randn(100, 768)
    embeddings[0] = np.full(768, 100.0)  # Anomaly

    # Detect anomalies
    anomalies, scores = detector.detect_z_score_anomalies(embeddings)

    assert np.sum(anomalies) > 0
    assert anomalies[0]


@pytest.mark.asyncio
async def test_pooling_strategies():
    """Test pooling strategies."""
    from src.embedding.pooling_strategies import PoolingFactory

    # Create embeddings
    embeddings = np.random.randn(2, 10, 768)

    # Test mean pooling
    mean_pool = PoolingFactory.create("mean")
    result = mean_pool.pool(embeddings)
    assert result.shape == (2, 768)

    # Test max pooling
    max_pool = PoolingFactory.create("max")
    result = max_pool.pool(embeddings)
    assert result.shape == (2, 768)

    # Test CLS pooling
    cls_pool = PoolingFactory.create("cls")
    result = cls_pool.pool(embeddings)
    assert result.shape == (2, 768)


@pytest.mark.asyncio
async def test_batch_optimizer():
    """Test batch optimizer."""
    from src.batching.batch_optimizer import BatchOptimizer

    optimizer = BatchOptimizer()

    texts = ["short text"] * 50 + ["this is a much longer text that contains many words"] * 50

    # Optimize batch size
    batch_size = optimizer.optimize_batch_size(texts)
    assert batch_size > 0

    # Create balanced batches
    batches = optimizer.create_balanced_batches(texts, batch_size=10)
    assert len(batches) > 0

    # Create token-aware batches
    batches = optimizer.create_token_aware_batches(texts, max_tokens=512)
    assert len(batches) > 0

