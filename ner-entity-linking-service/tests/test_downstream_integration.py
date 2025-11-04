"""Tests for downstream service integration."""

import pytest
from src.integration.downstream_service import (
    DownstreamService,
    DownstreamMessage,
    DownstreamServiceIntegration,
    ServiceHealthCheck,
    IntegrationMetrics,
)


class TestDownstreamService:
    """Tests for DownstreamService enum."""

    def test_all_services_defined(self):
        """Test all downstream services are defined."""
        services = [
            DownstreamService.CLUSTERING,
            DownstreamService.FEATURE_ENGINEERING,
            DownstreamService.LABELER,
            DownstreamService.TRAINER,
            DownstreamService.PREDICTOR,
            DownstreamService.NEO4J_LOADER,
            DownstreamService.API,
        ]
        assert len(services) == 7


class TestDownstreamMessage:
    """Tests for DownstreamMessage."""

    def test_create_downstream_message(self):
        """Test creating downstream message."""
        message = DownstreamMessage(
            message_id="msg1",
            article_id="art1",
            destination_service="clustering-service",
            entities=[{"entity_id": "e1", "text": "John"}],
        )
        assert message.message_id == "msg1"
        assert message.article_id == "art1"
        assert len(message.entities) == 1

    def test_message_to_dict(self):
        """Test converting message to dictionary."""
        message = DownstreamMessage(
            message_id="msg1",
            article_id="art1",
            destination_service="clustering-service",
        )
        msg_dict = message.to_dict()
        assert msg_dict["message_id"] == "msg1"
        assert msg_dict["article_id"] == "art1"


class TestDownstreamServiceIntegration:
    """Tests for downstream service integration."""

    def test_validate_for_clustering_service(self):
        """Test validation for clustering service."""
        entity = {
            "entity_id": "e1",
            "text": "John Smith",
            "entity_type": "PERSON",
            "wikidata_id": "Q123",
        }
        is_valid, errors = DownstreamServiceIntegration.validate_for_service(
            entity, DownstreamService.CLUSTERING
        )
        assert is_valid
        assert len(errors) == 0

    def test_validate_missing_required_field(self):
        """Test validation with missing required field."""
        entity = {
            "entity_id": "e1",
            "text": "John Smith",
            # Missing entity_type
            "wikidata_id": "Q123",
        }
        is_valid, errors = DownstreamServiceIntegration.validate_for_service(
            entity, DownstreamService.CLUSTERING
        )
        assert not is_valid
        assert len(errors) > 0

    def test_validate_for_different_services(self):
        """Test validation for different services."""
        entity = {
            "entity_id": "e1",
            "text": "John Smith",
            "entity_type": "PERSON",
            "wikidata_id": "Q123",
        }

        # Should be valid for clustering
        is_valid_clustering, _ = DownstreamServiceIntegration.validate_for_service(
            entity, DownstreamService.CLUSTERING
        )
        assert is_valid_clustering

        # Should be valid for labeler (less strict)
        is_valid_labeler, _ = DownstreamServiceIntegration.validate_for_service(
            entity, DownstreamService.LABELER
        )
        assert is_valid_labeler

    def test_prepare_message_for_service(self):
        """Test preparing message for service."""
        entities = [
            {
                "entity_id": "e1",
                "text": "John Smith",
                "entity_type": "PERSON",
                "wikidata_id": "Q123",
            }
        ]
        message = DownstreamServiceIntegration.prepare_message_for_service(
            "art1", entities, DownstreamService.CLUSTERING, "msg1"
        )
        assert message is not None
        assert message.message_id == "msg1"
        assert len(message.entities) == 1

    def test_prepare_message_with_invalid_entities(self):
        """Test preparing message with invalid entities."""
        entities = [
            {
                "entity_id": "e1",
                "text": "John Smith",
                # Missing required fields
            }
        ]
        message = DownstreamServiceIntegration.prepare_message_for_service(
            "art1", entities, DownstreamService.CLUSTERING
        )
        assert message is None

    def test_get_service_requirements(self):
        """Test getting service requirements."""
        requirements = DownstreamServiceIntegration.get_service_requirements(
            DownstreamService.CLUSTERING
        )
        assert "service" in requirements
        assert "required_fields" in requirements
        assert "optional_fields" in requirements

    def test_get_all_service_requirements(self):
        """Test getting all service requirements."""
        all_requirements = DownstreamServiceIntegration.get_all_service_requirements()
        assert len(all_requirements) == 7
        assert "clustering-service" in all_requirements


class TestServiceHealthCheck:
    """Tests for service health check."""

    def test_check_service_health(self):
        """Test checking service health."""
        health = ServiceHealthCheck.check_service_health(DownstreamService.CLUSTERING)
        assert "service" in health
        assert "status" in health
        assert health["status"] in ["healthy", "degraded", "unhealthy"]

    def test_check_all_services_health(self):
        """Test checking all services health."""
        health_status = ServiceHealthCheck.check_all_services_health()
        assert len(health_status) == 7
        assert "clustering-service" in health_status

    def test_update_service_health(self):
        """Test updating service health."""
        ServiceHealthCheck.update_service_health(
            DownstreamService.CLUSTERING, "degraded"
        )
        health = ServiceHealthCheck.check_service_health(DownstreamService.CLUSTERING)
        assert health["status"] == "degraded"

        # Reset to healthy
        ServiceHealthCheck.update_service_health(
            DownstreamService.CLUSTERING, "healthy"
        )


class TestIntegrationMetrics:
    """Tests for integration metrics."""

    def test_get_integration_metrics(self):
        """Test getting integration metrics."""
        metrics = IntegrationMetrics.get_integration_metrics()
        assert "total_services" in metrics
        assert "services" in metrics
        assert "health_status" in metrics
        assert "timestamp" in metrics
        assert metrics["total_services"] == 7

    def test_get_service_compatibility(self):
        """Test getting service compatibility."""
        entity = {
            "entity_id": "e1",
            "text": "John Smith",
            "entity_type": "PERSON",
            "wikidata_id": "Q123",
        }
        compatibility = IntegrationMetrics.get_service_compatibility(entity)
        assert len(compatibility) == 7
        assert "clustering-service" in compatibility
        assert isinstance(compatibility["clustering-service"], bool)

    def test_get_service_compatibility_incomplete_entity(self):
        """Test service compatibility for incomplete entity."""
        entity = {
            "entity_id": "e1",
            "text": "John Smith",
            # Missing entity_type and wikidata_id
        }
        compatibility = IntegrationMetrics.get_service_compatibility(entity)
        # Should be incompatible with most services
        assert not compatibility["clustering-service"]


class TestDownstreamIntegrationWorkflow:
    """Integration tests for downstream service integration."""

    def test_full_integration_workflow(self):
        """Test full downstream integration workflow."""
        # Create entities for clustering/feature engineering
        entities = [
            {
                "entity_id": "e1",
                "text": "John Smith",
                "entity_type": "PERSON",
                "wikidata_id": "Q123",
                "confidence": 0.95,
            },
            {
                "entity_id": "e2",
                "text": "Microsoft",
                "entity_type": "ORGANIZATION",
                "wikidata_id": "Q456",
                "confidence": 0.92,
            },
        ]

        # Check compatibility
        for entity in entities:
            compatibility = IntegrationMetrics.get_service_compatibility(entity)
            assert compatibility["clustering-service"]

        # Prepare messages for services that don't require features
        for service in [
            DownstreamService.CLUSTERING,
            DownstreamService.FEATURE_ENGINEERING,
            DownstreamService.LABELER,
            DownstreamService.NEO4J_LOADER,
            DownstreamService.API,
        ]:
            message = DownstreamServiceIntegration.prepare_message_for_service(
                "art1", entities, service
            )
            assert message is not None
            assert len(message.entities) > 0

    def test_service_health_workflow(self):
        """Test service health workflow."""
        # Check initial health
        health = ServiceHealthCheck.check_all_services_health()
        assert len(health) == 7

        # Update health
        ServiceHealthCheck.update_service_health(
            DownstreamService.CLUSTERING, "degraded"
        )

        # Check updated health
        health = ServiceHealthCheck.check_service_health(DownstreamService.CLUSTERING)
        assert health["status"] == "degraded"

        # Reset
        ServiceHealthCheck.update_service_health(
            DownstreamService.CLUSTERING, "healthy"
        )

