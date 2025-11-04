"""End-to-end tests for clustering service."""

import pytest
import numpy as np
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
import json

from src.config import config
from src.pipeline_orchestrator import PipelineOrchestrator
from src.scheduler import ClusteringScheduler


class TestEndToEndPipeline:
    """End-to-end tests for complete clustering pipeline."""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance."""
        return PipelineOrchestrator()

    def create_mock_embeddings(self, n_samples=100, n_features=768):
        """Create mock embeddings for testing."""
        np.random.seed(42)
        embeddings = np.random.randn(n_samples, n_features).astype(np.float32)

        # Create clusters by adding structure
        for i in range(0, n_samples, 10):
            if i + 10 <= n_samples:
                center = np.random.randn(n_features).astype(np.float32)
                for j in range(i, i + 10):
                    embeddings[j] = center + np.random.randn(n_features) * 0.1

        metadata = [
            {
                "article_id": f"art_{i}",
                "embedded_at": datetime.now(timezone.utc) - timedelta(hours=i % 24),
                "publisher_credibility": 0.7 + np.random.rand() * 0.3,
                "language": np.random.choice(["en", "es", "fr", "de"]),
                "domain": np.random.choice(["bbc.com", "reuters.com", "ap.org"]),
                "source": np.random.choice(["BBC", "Reuters", "AP", "CNN"]),
                "published_at": datetime.now(timezone.utc) - timedelta(hours=i % 24),
                "title": f"Article {i}",
                "body": f"This is the body of article {i}",
            }
            for i in range(n_samples)
        ]

        return embeddings, metadata

    @patch('src.vector_retriever.VectorRetriever.retrieve_embeddings')
    @patch('src.delta_lake_writer.DeltaLakeWriter.write_clusters')
    @patch('src.cluster_registry.ClusterRegistry.register_cluster')
    @patch('src.kafka_integration.KafkaProducer.produce_batch')
    def test_e2e_clustering_pipeline(
        self,
        mock_produce,
        mock_register,
        mock_write,
        mock_retrieve,
        orchestrator,
    ):
        """Test complete end-to-end clustering pipeline."""
        # Setup mocks
        embeddings, metadata = self.create_mock_embeddings(n_samples=100)
        mock_retrieve.return_value = (embeddings, metadata)
        mock_write.return_value = True
        mock_register.return_value = True
        mock_produce.return_value = 10

        # Run pipeline
        total, valid, invalid = orchestrator.run_clustering_job()

        # Verify results
        assert total > 0, "Should create clusters"
        assert valid > 0, "Should have valid clusters"
        assert mock_retrieve.called, "Should retrieve embeddings"
        assert mock_write.called, "Should write to Delta Lake"
        assert mock_register.called, "Should register clusters"
        assert mock_produce.called, "Should produce to Kafka"

    @patch('src.vector_retriever.VectorRetriever.retrieve_embeddings')
    @patch('src.delta_lake_writer.DeltaLakeWriter.write_clusters')
    @patch('src.cluster_registry.ClusterRegistry.register_cluster')
    @patch('src.kafka_integration.KafkaProducer.produce_batch')
    def test_e2e_validation_rules(
        self,
        mock_produce,
        mock_register,
        mock_write,
        mock_retrieve,
        orchestrator,
    ):
        """Test that validation rules are enforced."""
        embeddings, metadata = self.create_mock_embeddings(n_samples=50)
        mock_retrieve.return_value = (embeddings, metadata)
        mock_write.return_value = True
        mock_register.return_value = True
        mock_produce.return_value = 5

        total, valid, invalid = orchestrator.run_clustering_job()

        # Verify validation was applied
        assert valid + invalid <= total, "Valid + invalid should not exceed total"

    @patch('src.vector_retriever.VectorRetriever.retrieve_embeddings')
    @patch('src.delta_lake_writer.DeltaLakeWriter.write_clusters')
    @patch('src.cluster_registry.ClusterRegistry.register_cluster')
    @patch('src.kafka_integration.KafkaProducer.produce_batch')
    def test_e2e_temporal_tracking(
        self,
        mock_produce,
        mock_register,
        mock_write,
        mock_retrieve,
        orchestrator,
    ):
        """Test temporal tracking of clusters."""
        embeddings, metadata = self.create_mock_embeddings(n_samples=100)
        mock_retrieve.return_value = (embeddings, metadata)
        mock_write.return_value = True
        mock_register.return_value = True
        mock_produce.return_value = 10

        # Run pipeline twice
        total1, valid1, invalid1 = orchestrator.run_clustering_job()
        total2, valid2, invalid2 = orchestrator.run_clustering_job()

        # Verify temporal tracking
        assert orchestrator.temporal_tracker.cluster_history, "Should track cluster history"

    @patch('src.vector_retriever.VectorRetriever.retrieve_embeddings')
    def test_e2e_empty_window(self, mock_retrieve, orchestrator):
        """Test handling of empty time window."""
        mock_retrieve.return_value = (np.array([]), [])

        total, valid, invalid = orchestrator.run_clustering_job()

        assert total == 0, "Should handle empty window"
        assert valid == 0, "Should have no valid clusters"

    @patch('src.vector_retriever.VectorRetriever.retrieve_embeddings')
    @patch('src.delta_lake_writer.DeltaLakeWriter.write_clusters')
    @patch('src.cluster_registry.ClusterRegistry.register_cluster')
    @patch('src.kafka_integration.KafkaProducer.produce_batch')
    def test_e2e_multilingual_clustering(
        self,
        mock_produce,
        mock_register,
        mock_write,
        mock_retrieve,
        orchestrator,
    ):
        """Test clustering with multilingual articles."""
        embeddings, metadata = self.create_mock_embeddings(n_samples=100)

        # Add language diversity
        languages = ["en", "es", "fr", "de", "zh", "ar"]
        for i, m in enumerate(metadata):
            m["language"] = languages[i % len(languages)]

        mock_retrieve.return_value = (embeddings, metadata)
        mock_write.return_value = True
        mock_register.return_value = True
        mock_produce.return_value = 10

        total, valid, invalid = orchestrator.run_clustering_job()

        assert total > 0, "Should cluster multilingual articles"

    @patch('src.vector_retriever.VectorRetriever.retrieve_embeddings')
    @patch('src.delta_lake_writer.DeltaLakeWriter.write_clusters')
    @patch('src.cluster_registry.ClusterRegistry.register_cluster')
    @patch('src.kafka_integration.KafkaProducer.produce_batch')
    def test_e2e_source_diversity(
        self,
        mock_produce,
        mock_register,
        mock_write,
        mock_retrieve,
        orchestrator,
    ):
        """Test source diversity validation."""
        embeddings, metadata = self.create_mock_embeddings(n_samples=100)

        # Ensure source diversity
        sources = ["BBC", "Reuters", "AP", "CNN", "NYT"]
        for i, m in enumerate(metadata):
            m["source"] = sources[i % len(sources)]

        mock_retrieve.return_value = (embeddings, metadata)
        mock_write.return_value = True
        mock_register.return_value = True
        mock_produce.return_value = 10

        total, valid, invalid = orchestrator.run_clustering_job()

        assert total > 0, "Should cluster with source diversity"


class TestSchedulerIntegration:
    """Integration tests for scheduler."""

    @patch('src.pipeline_orchestrator.PipelineOrchestrator.run_clustering_job')
    def test_scheduler_initialization(self, mock_job):
        """Test scheduler initialization."""
        mock_job.return_value = (10, 8, 2)

        scheduler = ClusteringScheduler()
        assert scheduler.scheduler is not None
        assert scheduler.orchestrator is not None

        scheduler.stop()

    @patch('src.pipeline_orchestrator.PipelineOrchestrator.run_clustering_job')
    def test_scheduler_job_execution(self, mock_job):
        """Test scheduler job execution."""
        mock_job.return_value = (10, 8, 2)

        scheduler = ClusteringScheduler()
        scheduler._run_clustering_job()

        assert mock_job.called, "Should execute clustering job"
        assert scheduler.last_run_time is not None, "Should update last run time"

        scheduler.stop()

    @patch('src.pipeline_orchestrator.PipelineOrchestrator.run_clustering_job')
    def test_scheduler_status(self, mock_job):
        """Test scheduler status reporting."""
        mock_job.return_value = (10, 8, 2)

        scheduler = ClusteringScheduler()
        status = scheduler.get_job_status()

        assert "running" in status
        assert "jobs" in status
        assert "last_run_time" in status

        scheduler.stop()


class TestErrorHandling:
    """Tests for error handling."""

    @patch('src.vector_retriever.VectorRetriever.retrieve_embeddings')
    def test_e2e_retrieval_error(self, mock_retrieve, ):
        """Test handling of retrieval errors."""
        mock_retrieve.side_effect = Exception("Qdrant connection failed")

        orchestrator = PipelineOrchestrator()

        with pytest.raises(Exception):
            orchestrator.run_clustering_job()

    @patch('src.vector_retriever.VectorRetriever.retrieve_embeddings')
    @patch('src.delta_lake_writer.DeltaLakeWriter.write_clusters')
    def test_e2e_write_error(self, mock_write, mock_retrieve):
        """Test handling of write errors."""
        embeddings, metadata = np.random.randn(50, 768), []
        mock_retrieve.return_value = (embeddings, metadata)
        mock_write.side_effect = Exception("Delta Lake write failed")

        orchestrator = PipelineOrchestrator()

        with pytest.raises(Exception):
            orchestrator.run_clustering_job()

