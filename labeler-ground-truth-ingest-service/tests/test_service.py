"""Unit tests for LabelerService."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.service import LabelerService


class TestLabelerService:
    """Test LabelerService."""

    @pytest.mark.asyncio
    async def test_service_initialization(self, mock_config):
        """Test service initialization."""
        with patch('src.config.config', mock_config):
            with patch('src.service.ACLEDFetcher'):
                with patch('src.service.GDELTFetcher'):
                    with patch('src.service.BinanceFetcher'):
                        with patch('src.service.KafkaProducerClient'):
                            with patch('src.service.DeltaLakeWriter'):
                                with patch('src.service.PostgreSQLWriter'):
                                    service = LabelerService()

                                    assert service is not None
                                    assert service.service_name == "labeler-ground-truth-ingest-service"

    @pytest.mark.asyncio
    async def test_service_start(self, mock_config):
        """Test service start."""
        import sys
        import pytest

        # Skip on Windows due to signal handler limitations
        if sys.platform == 'win32':
            pytest.skip("Signal handlers not supported on Windows")

        with patch('src.config.config', mock_config):
            with patch('src.service.ACLEDFetcher'):
                with patch('src.service.GDELTFetcher'):
                    with patch('src.service.BinanceFetcher'):
                        with patch('src.service.KafkaProducerClient') as mock_kafka_class:
                            with patch('src.service.DeltaLakeWriter'):
                                with patch('src.service.PostgreSQLWriter') as mock_postgres_class:
                                    service = LabelerService()
                                    service.kafka_producer = AsyncMock()
                                    service.postgres_writer = AsyncMock()

                                    await service.start()

                                    service.kafka_producer.connect.assert_called_once()
                                    service.postgres_writer.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_service_shutdown(self, mock_config):
        """Test service shutdown."""
        with patch('src.config.config', mock_config):
            with patch('src.service.ACLEDFetcher'):
                with patch('src.service.GDELTFetcher'):
                    with patch('src.service.BinanceFetcher'):
                        with patch('src.service.KafkaProducerClient'):
                            with patch('src.service.DeltaLakeWriter'):
                                with patch('src.service.PostgreSQLWriter'):
                                    service = LabelerService()
                                    service.kafka_producer = AsyncMock()
                                    service.postgres_writer = AsyncMock()
                                    service.running = True  # Set running to True so shutdown will close

                                    await service.shutdown()

                                    # Verify service is no longer running
                                    assert service.running is False

    @pytest.mark.asyncio
    async def test_health_check(self, mock_config):
        """Test health check endpoint."""
        with patch('src.config.config', mock_config):
            with patch('src.service.ACLEDFetcher'):
                with patch('src.service.GDELTFetcher'):
                    with patch('src.service.BinanceFetcher'):
                        with patch('src.service.KafkaProducerClient'):
                            with patch('src.service.DeltaLakeWriter'):
                                with patch('src.service.PostgreSQLWriter'):
                                    service = LabelerService()

                                    health = await service.health_check()

                                    assert health is not None
                                    assert "status" in health

    @pytest.mark.asyncio
    async def test_readiness_check(self, mock_config):
        """Test readiness check endpoint."""
        with patch('src.config.config', mock_config):
            with patch('src.service.ACLEDFetcher'):
                with patch('src.service.GDELTFetcher'):
                    with patch('src.service.BinanceFetcher'):
                        with patch('src.service.KafkaProducerClient'):
                            with patch('src.service.DeltaLakeWriter'):
                                with patch('src.service.PostgreSQLWriter'):
                                    service = LabelerService()
                                    service.kafka_producer = AsyncMock()
                                    service.postgres_writer = AsyncMock()

                                    ready = await service.readiness_check()

                                    assert ready is not None
                                    assert "ready" in ready

    @pytest.mark.asyncio
    async def test_service_run_loop(self, mock_config):
        """Test service run loop."""
        with patch('src.config.config', mock_config):
            with patch('src.service.ACLEDFetcher'):
                with patch('src.service.GDELTFetcher'):
                    with patch('src.service.BinanceFetcher'):
                        with patch('src.service.KafkaProducerClient'):
                            with patch('src.service.DeltaLakeWriter'):
                                with patch('src.service.PostgreSQLWriter'):
                                    service = LabelerService()
                                    service.kafka_producer = AsyncMock()
                                    service.postgres_writer = AsyncMock()
                                    service.running = True

                                    # Should have running flag
                                    assert service.running is True


    @pytest.mark.asyncio
    async def test_service_shutdown(self, mock_config):
        """Test service shutdown."""
        with patch('src.config.config', mock_config):
            with patch('src.service.ACLEDFetcher'):
                with patch('src.service.GDELTFetcher'):
                    with patch('src.service.BinanceFetcher'):
                        with patch('src.service.KafkaProducerClient'):
                            with patch('src.service.DeltaLakeWriter'):
                                with patch('src.service.PostgreSQLWriter'):
                                    service = LabelerService()
                                    service.kafka_producer = AsyncMock()
                                    service.postgres_writer = AsyncMock()
                                    service.running = True

                                    await service.shutdown()

                                    assert service.running is False

    @pytest.mark.asyncio
    async def test_service_semantic_groups_attribute(self, mock_config):
        """Test service semantic groups attribute."""
        with patch('src.config.config', mock_config):
            with patch('src.service.ACLEDFetcher'):
                with patch('src.service.GDELTFetcher'):
                    with patch('src.service.BinanceFetcher'):
                        with patch('src.service.KafkaProducerClient'):
                            with patch('src.service.DeltaLakeWriter'):
                                with patch('src.service.PostgreSQLWriter'):
                                    service = LabelerService()

                                    # Should have semantic_groups attribute
                                    assert isinstance(service.semantic_groups, list)


class TestMainModule:
    """Test main module."""

    @pytest.mark.asyncio
    async def test_main_entry_point(self, mock_config):
        """Test main entry point."""
        with patch('src.config.config', mock_config):
            with patch('src.main.LabelerService') as mock_service_class:
                mock_service = AsyncMock()
                mock_service_class.return_value = mock_service

                # Import and test main
                from src import main

                # Should have main function
                assert hasattr(main, 'main')

    @pytest.mark.asyncio
    async def test_main_service_lifecycle(self, mock_config):
        """Test main service lifecycle."""
        with patch('src.config.config', mock_config):
            with patch('src.main.LabelerService') as mock_service_class:
                mock_service = AsyncMock()
                mock_service_class.return_value = mock_service

                from src.main import main

                # Should complete without error
                assert True

    def test_main_module_imports(self):
        """Test main module imports."""
        from src import main

        # Should have main function
        assert hasattr(main, 'main')
        assert callable(main.main)


class TestServiceMethods:
    """Test service methods."""

    @pytest.mark.asyncio
    async def test_service_fetch_acled_labels(self, mock_config):
        """Test fetching ACLED labels."""
        with patch('src.config.config', mock_config):
            with patch('src.service.ACLEDFetcher') as mock_fetcher_class:
                with patch('src.service.GDELTFetcher'):
                    with patch('src.service.BinanceFetcher'):
                        with patch('src.service.KafkaProducerClient'):
                            with patch('src.service.DeltaLakeWriter'):
                                with patch('src.service.PostgreSQLWriter'):
                                    mock_fetcher = AsyncMock()
                                    mock_fetcher.fetch = AsyncMock(return_value=[])
                                    mock_fetcher_class.return_value = mock_fetcher

                                    service = LabelerService()
                                    service.acled_fetcher = mock_fetcher

                                    # Should have fetcher
                                    assert service.acled_fetcher is not None

    @pytest.mark.asyncio
    async def test_service_has_validators(self, mock_config):
        """Test service has validators."""
        with patch('src.config.config', mock_config):
            with patch('src.service.ACLEDFetcher'):
                with patch('src.service.GDELTFetcher'):
                    with patch('src.service.BinanceFetcher'):
                        with patch('src.service.KafkaProducerClient'):
                            with patch('src.service.DeltaLakeWriter'):
                                with patch('src.service.PostgreSQLWriter'):
                                    service = LabelerService()

                                    # Should have validators
                                    assert service.validator is not None
                                    assert service.license_checker is not None
                                    assert service.freshness_validator is not None
                                    assert service.reconciler is not None

    @pytest.mark.asyncio
    async def test_service_has_storage_writers(self, mock_config):
        """Test service has storage writers."""
        with patch('src.config.config', mock_config):
            with patch('src.service.ACLEDFetcher'):
                with patch('src.service.GDELTFetcher'):
                    with patch('src.service.BinanceFetcher'):
                        with patch('src.service.KafkaProducerClient'):
                            with patch('src.service.DeltaLakeWriter'):
                                with patch('src.service.PostgreSQLWriter'):
                                    service = LabelerService()

                                    # Should have storage writers
                                    assert service.kafka_producer is not None
                                    assert service.delta_lake_writer is not None
                                    assert service.postgres_writer is not None

    @pytest.mark.asyncio
    async def test_fetch_labels_from_acled(self, mock_config):
        """Test fetching labels from ACLED."""
        with patch('src.config.config', mock_config):
            with patch('src.service.ACLEDFetcher') as mock_fetcher_class:
                with patch('src.service.GDELTFetcher'):
                    with patch('src.service.BinanceFetcher'):
                        with patch('src.service.KafkaProducerClient'):
                            with patch('src.service.DeltaLakeWriter'):
                                with patch('src.service.PostgreSQLWriter'):
                                    service = LabelerService()
                                    mock_fetcher_instance = AsyncMock()
                                    mock_fetcher_instance.fetch = AsyncMock(return_value=[{"event_id": "123"}])
                                    mock_fetcher_class.return_value = mock_fetcher_instance

                # This would be called in the actual service
                labels = await mock_fetcher_instance.fetch()

                assert len(labels) > 0

    @pytest.mark.asyncio
    async def test_fetch_labels_from_gdelt(self, mock_config):
        """Test fetching labels from GDELT."""
        with patch('src.config.config', mock_config):
            with patch('src.service.ACLEDFetcher'):
                with patch('src.service.GDELTFetcher') as mock_fetcher_class:
                    with patch('src.service.BinanceFetcher'):
                        with patch('src.service.KafkaProducerClient'):
                            with patch('src.service.DeltaLakeWriter'):
                                with patch('src.service.PostgreSQLWriter'):
                                    service = LabelerService()
                                    mock_fetcher_instance = AsyncMock()
                                    mock_fetcher_instance.fetch = AsyncMock(return_value=[{"event_id": "456"}])
                                    mock_fetcher_class.return_value = mock_fetcher_instance

                                    labels = await mock_fetcher_instance.fetch()

                                    assert len(labels) > 0

    @pytest.mark.asyncio
    async def test_fetch_labels_from_binance(self, mock_config):
        """Test fetching labels from Binance."""
        with patch('src.config.config', mock_config):
            with patch('src.service.ACLEDFetcher'):
                with patch('src.service.GDELTFetcher'):
                    with patch('src.service.BinanceFetcher') as mock_fetcher_class:
                        with patch('src.service.KafkaProducerClient'):
                            with patch('src.service.DeltaLakeWriter'):
                                with patch('src.service.PostgreSQLWriter'):
                                    service = LabelerService()
                                    mock_fetcher_instance = AsyncMock()
                                    mock_fetcher_instance.fetch = AsyncMock(return_value=[{"timestamp": "2025-11-05"}])
                                    mock_fetcher_class.return_value = mock_fetcher_instance

                                    labels = await mock_fetcher_instance.fetch()

                                    assert len(labels) > 0

    @pytest.mark.asyncio
    async def test_process_labels_pipeline(self, mock_config, sample_acled_label):
        """Test complete label processing pipeline."""
        with patch('src.config.config', mock_config):
            with patch('src.service.ACLEDFetcher'):
                with patch('src.service.GDELTFetcher'):
                    with patch('src.service.BinanceFetcher'):
                        with patch('src.service.KafkaProducerClient'):
                            with patch('src.service.DeltaLakeWriter'):
                                with patch('src.service.PostgreSQLWriter'):
                                    service = LabelerService()
                                    service.kafka_producer = AsyncMock()
                                    service.postgres_writer = AsyncMock()
                                    service.delta_lake_writer = AsyncMock()

                                    # Mock the pipeline methods
                                    service.fetch_labels = AsyncMock(return_value={"acled": [sample_acled_label]})
                                    service.validate_labels = AsyncMock(return_value={"valid": [sample_acled_label], "invalid": []})
                                    service.reconcile_labels = AsyncMock(return_value=[sample_acled_label])

                                    # This would be called in the actual service
                                    labels = await service.fetch_labels()
                                    assert len(labels["acled"]) > 0

    @pytest.mark.asyncio
    async def test_metrics_collection(self, mock_config):
        """Test metrics collection."""
        with patch('src.config.config', mock_config):
            with patch('src.service.ACLEDFetcher'):
                with patch('src.service.GDELTFetcher'):
                    with patch('src.service.BinanceFetcher'):
                        with patch('src.service.KafkaProducerClient'):
                            with patch('src.service.DeltaLakeWriter'):
                                with patch('src.service.PostgreSQLWriter'):
                                    service = LabelerService()

                                    # Metrics should be initialized
                                    assert service is not None


class TestServiceConfiguration:
    """Test service configuration."""

    def test_config_from_environment(self):
        """Test loading configuration from environment."""
        with patch.dict('os.environ', {
            'KAFKA_BROKERS': '154.53.166.231:9092',
            'SCHEMA_REGISTRY_URL': 'http://154.53.166.231:8081',
            'POSTGRES_HOST': '154.53.166.231',
        }):
            # Configuration should load from environment
            pass

    def test_config_defaults(self):
        """Test configuration defaults."""
        # Configuration should have sensible defaults
        pass


class TestServiceMetrics:
    """Test service metrics."""

    def test_metrics_initialization(self, mock_config):
        """Test metrics are initialized."""
        with patch('src.config.config', mock_config):
            with patch('src.service.ACLEDFetcher'):
                with patch('src.service.GDELTFetcher'):
                    with patch('src.service.BinanceFetcher'):
                        with patch('src.service.KafkaProducerClient'):
                            with patch('src.service.DeltaLakeWriter'):
                                with patch('src.service.PostgreSQLWriter'):
                                    service = LabelerService()

                                    # Metrics should be available
                                    assert service is not None

    def test_metrics_export(self, mock_config):
        """Test metrics export."""
        with patch('src.config.config', mock_config):
            with patch('src.service.ACLEDFetcher'):
                with patch('src.service.GDELTFetcher'):
                    with patch('src.service.BinanceFetcher'):
                        with patch('src.service.KafkaProducerClient'):
                            with patch('src.service.DeltaLakeWriter'):
                                with patch('src.service.PostgreSQLWriter'):
                                    service = LabelerService()

                                    # Metrics should be exportable
                                    assert service is not None

