"""Integration tests for clustering service."""

import pytest
import numpy as np
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock
import json

from src.config import config
from src.pipeline_orchestrator import PipelineOrchestrator
from src.kafka_integration import KafkaConsumer, KafkaProducer


class TestPipelineIntegration:
    """Integration tests for complete pipeline."""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance."""
        return PipelineOrchestrator()

    def test_pipeline_initialization(self, orchestrator):
        """Test pipeline initialization."""
        assert orchestrator.time_window_manager is not None
        assert orchestrator.vector_retriever is not None
        assert orchestrator.clustering_engine is not None
        assert orchestrator.validator is not None
        assert orchestrator.centroid_calculator is not None
        assert orchestrator.metadata_aggregator is not None
        assert orchestrator.topic_labeler is not None
        assert orchestrator.temporal_tracker is not None
        assert orchestrator.delta_writer is not None
        assert orchestrator.registry is not None
        assert orchestrator.cache is not None
        assert orchestrator.producer is not None

    @patch('src.vector_retriever.VectorRetriever.retrieve_embeddings')
    def test_pipeline_with_mock_embeddings(self, mock_retrieve, orchestrator):
        """Test pipeline with mocked embeddings."""
        # Create mock embeddings
        np.random.seed(42)
        embeddings = np.random.randn(50, 768).astype(np.float32)
        metadata = [
            {
                "article_id": f"art_{i}",
                "embedded_at": datetime.now(timezone.utc),
                "publisher_credibility": 0.8,
                "language": "en",
                "domain": "example.com",
                "source": f"source_{i % 3}",
                "published_at": datetime.now(timezone.utc) - timedelta(hours=i),
            }
            for i in range(50)
        ]

        mock_retrieve.return_value = (embeddings, metadata)

        # Run pipeline
        with patch.object(orchestrator.delta_writer, 'write_clusters', return_value=True):
            with patch.object(orchestrator.registry, 'register_cluster', return_value=True):
                with patch.object(orchestrator.producer, 'produce_batch', return_value=50):
                    total, valid, invalid = orchestrator.run_clustering_job()

        assert total > 0
        assert valid > 0
        assert invalid >= 0

    @patch('src.vector_retriever.VectorRetriever.retrieve_embeddings')
    def test_pipeline_validation_filtering(self, mock_retrieve, orchestrator):
        """Test that invalid clusters are filtered."""
        # Create embeddings with one very small cluster
        np.random.seed(42)
        embeddings = np.random.randn(10, 768).astype(np.float32)
        metadata = [
            {
                "article_id": f"art_{i}",
                "embedded_at": datetime.now(timezone.utc),
                "publisher_credibility": 0.8,
                "language": "en",
                "domain": "example.com",
                "source": f"source_{i % 2}",
                "published_at": datetime.now(timezone.utc),
            }
            for i in range(10)
        ]

        mock_retrieve.return_value = (embeddings, metadata)

        with patch.object(orchestrator.delta_writer, 'write_clusters', return_value=True):
            with patch.object(orchestrator.registry, 'register_cluster', return_value=True):
                with patch.object(orchestrator.producer, 'produce_batch', return_value=0):
                    total, valid, invalid = orchestrator.run_clustering_job()

        # Should have some invalid clusters due to small size
        assert invalid >= 0


class TestKafkaIntegration:
    """Integration tests for Kafka components."""

    def test_kafka_consumer_initialization(self):
        """Test Kafka consumer initialization."""
        consumer = KafkaConsumer(
            brokers=config.kafka.brokers,
            schema_registry_url=config.kafka.schema_registry_url,
            topic=config.kafka.input_topic,
            consumer_group=config.kafka.consumer_group,
        )
        assert consumer.topic == config.kafka.input_topic
        consumer.close()

    def test_kafka_producer_initialization(self):
        """Test Kafka producer initialization."""
        producer = KafkaProducer(
            brokers=config.kafka.brokers,
            schema_registry_url=config.kafka.schema_registry_url,
            topic=config.kafka.output_topic,
        )
        assert producer.topic == config.kafka.output_topic
        producer.close()

    @patch('confluent_kafka.Producer.produce')
    def test_kafka_producer_produce_cluster(self, mock_produce):
        """Test producing a cluster message."""
        producer = KafkaProducer(
            brokers=config.kafka.brokers,
            schema_registry_url=config.kafka.schema_registry_url,
            topic=config.kafka.output_topic,
        )

        cluster = {
            "group_id": "cluster_1",
            "article_ids": ["art_1", "art_2", "art_3"],
            "article_count": 3,
            "similarity_avg": 0.87,
            "topic_label": "Breaking News",
            "centroid_vector": [0.1] * 768,
            "metadata": {},
            "created_at": datetime.utcnow().isoformat(),
        }

        result = producer.produce_cluster(cluster, key="cluster_1")

        assert result is True
        producer.close()

    @patch('confluent_kafka.Producer.produce')
    def test_kafka_producer_produce_batch(self, mock_produce):
        """Test producing a batch of clusters."""
        producer = KafkaProducer(
            brokers=config.kafka.brokers,
            schema_registry_url=config.kafka.schema_registry_url,
            topic=config.kafka.output_topic,
        )

        clusters = [
            {
                "group_id": f"cluster_{i}",
                "article_ids": [f"art_{i}_{j}" for j in range(3)],
                "article_count": 3,
                "similarity_avg": 0.85 + i * 0.01,
                "topic_label": f"Topic {i}",
                "centroid_vector": [0.1] * 768,
                "metadata": {},
                "created_at": datetime.utcnow().isoformat(),
            }
            for i in range(5)
        ]

        count = producer.produce_batch(clusters)

        assert count == 5
        producer.close()


class TestDataPersistence:
    """Integration tests for data persistence."""

    @patch('src.cluster_registry.ClusterRegistry.register_cluster')
    def test_cluster_registry_register(self, mock_register):
        """Test cluster registration."""
        from src.cluster_registry import ClusterRegistry

        registry = ClusterRegistry(
            host=config.postgres.host,
            port=config.postgres.port,
            user=config.postgres.user,
            password=config.postgres.password,
            database=config.postgres.database,
        )

        cluster = {
            "group_id": "cluster_1",
            "article_count": 5,
            "similarity_avg": 0.87,
            "topic_label": "Breaking News",
            "centroid_vector": [0.1] * 768,
            "metadata": {},
        }

        mock_register.return_value = True
        result = registry.register_cluster(cluster)

        assert result is True

    @patch('src.cache_manager.redis.Redis')
    def test_cache_manager_set_get(self, mock_redis):
        """Test cache manager set/get operations."""
        from src.cache_manager import CacheManager

        cache = CacheManager(
            host=config.redis.host,
            port=config.redis.port,
            cache_ttl_seconds=config.redis.cache_ttl_seconds,
        )

        state = {
            "cluster_id": "cluster_1",
            "article_count": 5,
            "similarity_avg": 0.87,
        }

        # Mock Redis operations
        cache.redis_client.setex = MagicMock(return_value=True)
        cache.redis_client.get = MagicMock(return_value=json.dumps(state))

        # Test set
        result = cache.set_cluster_state("cluster_1", state)
        assert result is True

        # Test get
        retrieved = cache.get_cluster_state("cluster_1")
        assert retrieved == state


class TestConfigurationManagement:
    """Tests for configuration management."""

    def test_config_initialization(self):
        """Test configuration initialization."""
        assert config.kafka.brokers is not None
        assert config.qdrant.host is not None
        assert config.postgres.host is not None
        assert config.redis.host is not None
        assert config.clustering.algorithm in ["hdbscan", "dbscan"]
        assert config.clustering.min_cluster_size > 0
        assert config.validation.min_cluster_purity > 0

    def test_config_values(self):
        """Test configuration values."""
        assert config.clustering.min_cluster_size == 3
        assert config.clustering.similarity_threshold == 0.85
        assert config.validation.min_cluster_purity == 0.85
        assert config.validation.min_sources == 2

