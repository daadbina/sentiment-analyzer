"""
Unit tests for external clients.

Tests PostgreSQL, Feast, MLflow, S3, and Kafka clients.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock

from src.clients.postgres_client import PostgreSQLClient
from src.clients.feast_client import FeastClient
from src.clients.mlflow_client import MLflowClient
from src.clients.s3_client import S3Client
from src.clients.kafka_producer import KafkaProducer


class TestPostgreSQLClient:
    """Test PostgreSQL client."""

    @patch("src.clients.postgres_client.asyncpg.create_pool")
    def test_postgres_client_initialization(self, mock_pool):
        """Test PostgreSQL client initialization."""
        client = PostgreSQLClient()
        assert client is not None

    @pytest.mark.asyncio
    @patch("src.clients.postgres_client.asyncpg.create_pool")
    async def test_postgres_client_connect(self, mock_pool):
        """Test PostgreSQL connection."""
        mock_pool_instance = AsyncMock()
        mock_pool.return_value = mock_pool_instance

        client = PostgreSQLClient()
        await client.connect()

        assert client.pool is not None

    @pytest.mark.asyncio
    @patch("src.clients.postgres_client.asyncpg.create_pool")
    async def test_postgres_client_query(self, mock_pool):
        """Test PostgreSQL query execution."""
        mock_pool_instance = AsyncMock()
        mock_connection = AsyncMock()
        mock_pool_instance.acquire.return_value.__aenter__.return_value = (
            mock_connection
        )
        mock_connection.fetch.return_value = [
            {"id": 1, "value": "test1"},
            {"id": 2, "value": "test2"},
        ]
        mock_pool.return_value = mock_pool_instance

        client = PostgreSQLClient()
        await client.connect()

        result = await client.query("SELECT * FROM test")

        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    @patch("src.clients.postgres_client.asyncpg.create_pool")
    async def test_postgres_client_health_check(self, mock_pool):
        """Test PostgreSQL health check."""
        mock_pool_instance = AsyncMock()
        mock_connection = AsyncMock()
        mock_pool_instance.acquire.return_value.__aenter__.return_value = (
            mock_connection
        )
        mock_connection.fetchval.return_value = 1
        mock_pool.return_value = mock_pool_instance

        client = PostgreSQLClient()
        await client.connect()

        is_healthy = await client.health_check()

        assert is_healthy is True

    @pytest.mark.asyncio
    @patch("src.clients.postgres_client.asyncpg.create_pool")
    async def test_postgres_client_disconnect(self, mock_pool):
        """Test PostgreSQL disconnection."""
        mock_pool_instance = AsyncMock()
        mock_pool.return_value = mock_pool_instance

        client = PostgreSQLClient()
        await client.connect()
        await client.disconnect()

        mock_pool_instance.close.assert_called_once()


class TestFeastClient:
    """Test Feast client."""

    @patch("src.clients.feast_client.FeatureStore")
    def test_feast_client_initialization(self, mock_fs):
        """Test Feast client initialization."""
        client = FeastClient()
        assert client is not None

    @patch("src.clients.feast_client.FeatureStore")
    def test_feast_client_get_features(self, mock_fs):
        """Test getting features from Feast."""
        mock_store = MagicMock()
        mock_store.get_online_features.return_value = {
            "feature_1": [1.0, 2.0, 3.0],
            "feature_2": [4.0, 5.0, 6.0],
        }
        mock_fs.return_value = mock_store

        client = FeastClient()

        features = client.get_features(
            entity_rows=[{"entity_id": 1}, {"entity_id": 2}],
            features=["feature_1", "feature_2"],
        )

        assert features is not None

    @patch("src.clients.feast_client.FeatureStore")
    def test_feast_client_schema_validation(self, mock_fs):
        """Test Feast schema validation."""
        mock_store = MagicMock()
        mock_store.get_feature_view.return_value = MagicMock(
            schema={"feature_1": "float", "feature_2": "float"}
        )
        mock_fs.return_value = mock_store

        client = FeastClient()

        schema = client.get_schema("feature_view")

        assert schema is not None


class TestMLflowClient:
    """Test MLflow client."""

    @patch("src.clients.mlflow_client.mlflow")
    def test_mlflow_client_initialization(self, mock_mlflow):
        """Test MLflow client initialization."""
        client = MLflowClient()
        assert client is not None

    @patch("src.clients.mlflow_client.mlflow")
    def test_mlflow_client_create_experiment(self, mock_mlflow):
        """Test creating MLflow experiment."""
        mock_mlflow.create_experiment.return_value = "exp_123"

        client = MLflowClient()

        exp_id = client.create_experiment("test_experiment")

        assert exp_id is not None

    @patch("src.clients.mlflow_client.mlflow")
    def test_mlflow_client_log_model(self, mock_mlflow):
        """Test logging model to MLflow."""
        mock_mlflow.log_model = MagicMock()

        client = MLflowClient()

        model = MagicMock()
        client.log_model(model, "test_model")

        mock_mlflow.log_model.assert_called_once()

    @patch("src.clients.mlflow_client.mlflow")
    def test_mlflow_client_register_model(self, mock_mlflow):
        """Test registering model in MLflow."""
        mock_mlflow.register_model.return_value = MagicMock(version=1)

        client = MLflowClient()

        result = client.register_model("runs:/abc123/model", "test_model")

        assert result is not None

    @patch("src.clients.mlflow_client.mlflow")
    def test_mlflow_client_transition_stage(self, mock_mlflow):
        """Test transitioning model stage."""
        mock_mlflow.transition_model_version_stage = MagicMock()

        client = MLflowClient()

        client.transition_model_stage("test_model", 1, "Production")

        mock_mlflow.transition_model_version_stage.assert_called_once()


class TestS3Client:
    """Test S3 client."""

    @patch("src.clients.s3_client.boto3.client")
    def test_s3_client_initialization(self, mock_boto3):
        """Test S3 client initialization."""
        client = S3Client()
        assert client is not None

    @patch("src.clients.s3_client.boto3.client")
    def test_s3_client_upload(self, mock_boto3):
        """Test S3 upload."""
        mock_s3 = MagicMock()
        mock_boto3.return_value = mock_s3

        client = S3Client()

        result = client.upload(b"data", "bucket", "key")

        assert result is not None

    @patch("src.clients.s3_client.boto3.client")
    def test_s3_client_download(self, mock_boto3):
        """Test S3 download."""
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = {"Body": MagicMock(read=lambda: b"data")}
        mock_boto3.return_value = mock_s3

        client = S3Client()

        result = client.download("bucket", "key")

        assert result is not None

    @patch("src.clients.s3_client.boto3.client")
    def test_s3_client_checksum_validation(self, mock_boto3):
        """Test S3 checksum validation."""
        mock_s3 = MagicMock()
        mock_boto3.return_value = mock_s3

        client = S3Client()

        data = b"test_data"
        checksum = client.compute_checksum(data)

        assert checksum is not None
        assert isinstance(checksum, str)


class TestKafkaProducer:
    """Test Kafka producer."""

    @patch("src.clients.kafka_producer.confluent_kafka.Producer")
    def test_kafka_producer_initialization(self, mock_producer):
        """Test Kafka producer initialization."""
        producer = KafkaProducer()
        assert producer is not None

    @patch("src.clients.kafka_producer.confluent_kafka.Producer")
    def test_kafka_producer_send_message(self, mock_producer):
        """Test sending Kafka message."""
        mock_prod = MagicMock()
        mock_producer.return_value = mock_prod

        producer = KafkaProducer()

        result = producer.send_message(topic="test_topic", key=b"key", value=b"value")

        assert result is not None

    @patch("src.clients.kafka_producer.confluent_kafka.Producer")
    def test_kafka_producer_avro_serialization(self, mock_producer):
        """Test Avro serialization."""
        mock_prod = MagicMock()
        mock_producer.return_value = mock_prod

        producer = KafkaProducer()

        message = {"field1": "value1", "field2": 123}
        result = producer.send_avro_message(
            topic="test_topic", key=b"key", value=message, schema_id=1
        )

        assert result is not None

    @patch("src.clients.kafka_producer.confluent_kafka.Producer")
    def test_kafka_producer_flush(self, mock_producer):
        """Test message flushing."""
        mock_prod = MagicMock()
        mock_producer.return_value = mock_prod

        producer = KafkaProducer()

        producer.flush()

        mock_prod.flush.assert_called_once()

    @patch("src.clients.kafka_producer.confluent_kafka.Producer")
    def test_kafka_producer_health_check(self, mock_producer):
        """Test Kafka health check."""
        mock_prod = MagicMock()
        mock_prod.list_topics.return_value = MagicMock(topics={"test": None})
        mock_producer.return_value = mock_prod

        producer = KafkaProducer()

        is_healthy = producer.health_check()

        assert is_healthy is True
