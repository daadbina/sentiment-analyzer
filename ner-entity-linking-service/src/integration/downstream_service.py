"""Downstream service integration."""

import logging
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


class DownstreamService(str, Enum):
    """Downstream services."""

    CLUSTERING = "clustering-service"
    FEATURE_ENGINEERING = "feature-engineering-service"
    LABELER = "labeler-service"
    TRAINER = "trainer-service"
    PREDICTOR = "predictor-service"
    NEO4J_LOADER = "neo4j-loader-service"
    API = "api-service"


@dataclass
class DownstreamMessage:
    """Message for downstream services."""

    message_id: str
    source_service: str = "ner-entity-linking-service"
    destination_service: str = ""
    timestamp: str = ""
    article_id: str = ""
    entities: List[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize defaults."""
        if self.timestamp == "":
            self.timestamp = datetime.utcnow().isoformat()
        if self.entities is None:
            self.entities = []
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


class DownstreamServiceIntegration:
    """Manages integration with downstream services."""

    # Service dependencies
    SERVICE_DEPENDENCIES = {
        DownstreamService.CLUSTERING: {
            "required_fields": ["entity_id", "text", "entity_type", "wikidata_id"],
            "optional_fields": ["confidence", "dbpedia_uri", "aliases"],
        },
        DownstreamService.FEATURE_ENGINEERING: {
            "required_fields": ["entity_id", "text", "entity_type", "wikidata_id"],
            "optional_fields": ["confidence", "linking_success"],
        },
        DownstreamService.LABELER: {
            "required_fields": ["entity_id", "text", "entity_type"],
            "optional_fields": ["wikidata_id", "confidence"],
        },
        DownstreamService.TRAINER: {
            "required_fields": ["entity_id", "features"],
            "optional_fields": ["label", "confidence"],
        },
        DownstreamService.PREDICTOR: {
            "required_fields": ["entity_id", "features"],
            "optional_fields": ["confidence"],
        },
        DownstreamService.NEO4J_LOADER: {
            "required_fields": ["entity_id", "text", "entity_type", "wikidata_id"],
            "optional_fields": ["dbpedia_uri", "aliases", "relationships"],
        },
        DownstreamService.API: {
            "required_fields": ["entity_id", "text", "entity_type"],
            "optional_fields": ["wikidata_id", "confidence", "prediction"],
        },
    }

    @staticmethod
    def validate_for_service(
        entity: Dict[str, Any],
        service: DownstreamService,
    ) -> tuple[bool, List[str]]:
        """Validate entity for downstream service.

        Args:
            entity: Entity dictionary
            service: Downstream service

        Returns:
            Tuple of (is_valid, error_messages)
        """
        dependencies = DownstreamServiceIntegration.SERVICE_DEPENDENCIES.get(service)
        if not dependencies:
            return False, [f"Unknown service: {service}"]

        errors = []

        # Check required fields
        for field in dependencies["required_fields"]:
            if field not in entity or entity[field] is None:
                errors.append(f"Missing required field: {field}")

        return len(errors) == 0, errors

    @staticmethod
    def prepare_message_for_service(
        article_id: str,
        entities: List[Dict[str, Any]],
        service: DownstreamService,
        message_id: str = "",
    ) -> Optional[DownstreamMessage]:
        """Prepare message for downstream service.

        Args:
            article_id: Article ID
            entities: List of entities
            service: Downstream service
            message_id: Message ID

        Returns:
            DownstreamMessage or None if validation fails
        """
        # Validate all entities
        valid_entities = []
        for entity in entities:
            is_valid, errors = DownstreamServiceIntegration.validate_for_service(
                entity, service
            )
            if is_valid:
                valid_entities.append(entity)
            else:
                logger.warning(
                    f"Entity {entity.get('entity_id')} invalid for {service}: {errors}"
                )

        if not valid_entities:
            logger.warning(f"No valid entities for {service}")
            return None

        message = DownstreamMessage(
            message_id=message_id or f"{article_id}_{service.value}",
            destination_service=service.value,
            article_id=article_id,
            entities=valid_entities,
            metadata={
                "entity_count": len(valid_entities),
                "service": service.value,
                "version": "1.0",
            },
        )

        return message

    @staticmethod
    def get_service_requirements(service: DownstreamService) -> Dict:
        """Get requirements for downstream service.

        Args:
            service: Downstream service

        Returns:
            Service requirements
        """
        dependencies = DownstreamServiceIntegration.SERVICE_DEPENDENCIES.get(service)
        if not dependencies:
            return {}

        return {
            "service": service.value,
            "required_fields": dependencies["required_fields"],
            "optional_fields": dependencies["optional_fields"],
            "total_fields": len(dependencies["required_fields"])
            + len(dependencies["optional_fields"]),
        }

    @staticmethod
    def get_all_service_requirements() -> Dict[str, Dict]:
        """Get requirements for all downstream services.

        Returns:
            Dictionary of service requirements
        """
        requirements = {}
        for service in DownstreamService:
            requirements[service.value] = (
                DownstreamServiceIntegration.get_service_requirements(service)
            )
        return requirements


class ServiceHealthCheck:
    """Health checks for downstream services."""

    # Service health status
    SERVICE_HEALTH = {
        DownstreamService.CLUSTERING: {"status": "healthy", "last_check": None},
        DownstreamService.FEATURE_ENGINEERING: {"status": "healthy", "last_check": None},
        DownstreamService.LABELER: {"status": "healthy", "last_check": None},
        DownstreamService.TRAINER: {"status": "healthy", "last_check": None},
        DownstreamService.PREDICTOR: {"status": "healthy", "last_check": None},
        DownstreamService.NEO4J_LOADER: {"status": "healthy", "last_check": None},
        DownstreamService.API: {"status": "healthy", "last_check": None},
    }

    @staticmethod
    def check_service_health(service: DownstreamService) -> Dict[str, Any]:
        """Check health of downstream service.

        Args:
            service: Downstream service

        Returns:
            Health status
        """
        health = ServiceHealthCheck.SERVICE_HEALTH.get(service)
        if not health:
            return {"status": "unknown", "service": service.value}

        return {
            "service": service.value,
            "status": health["status"],
            "last_check": health["last_check"],
        }

    @staticmethod
    def check_all_services_health() -> Dict[str, Dict]:
        """Check health of all downstream services.

        Returns:
            Health status for all services
        """
        health_status = {}
        for service in DownstreamService:
            health_status[service.value] = ServiceHealthCheck.check_service_health(
                service
            )
        return health_status

    @staticmethod
    def update_service_health(
        service: DownstreamService,
        status: str,
    ) -> None:
        """Update service health status.

        Args:
            service: Downstream service
            status: Health status (healthy, degraded, unhealthy)
        """
        if service in ServiceHealthCheck.SERVICE_HEALTH:
            ServiceHealthCheck.SERVICE_HEALTH[service]["status"] = status
            ServiceHealthCheck.SERVICE_HEALTH[service]["last_check"] = (
                datetime.utcnow().isoformat()
            )
            logger.info(f"Updated {service.value} health to {status}")


class IntegrationMetrics:
    """Metrics for downstream service integration."""

    @staticmethod
    def get_integration_metrics() -> Dict[str, Any]:
        """Get integration metrics.

        Returns:
            Integration metrics
        """
        return {
            "total_services": len(DownstreamService),
            "services": [s.value for s in DownstreamService],
            "health_status": ServiceHealthCheck.check_all_services_health(),
            "timestamp": datetime.utcnow().isoformat(),
        }

    @staticmethod
    def get_service_compatibility(
        entity: Dict[str, Any],
    ) -> Dict[str, bool]:
        """Get service compatibility for entity.

        Args:
            entity: Entity dictionary

        Returns:
            Dictionary of service compatibility
        """
        compatibility = {}
        for service in DownstreamService:
            is_valid, _ = DownstreamServiceIntegration.validate_for_service(
                entity, service
            )
            compatibility[service.value] = is_valid
        return compatibility

