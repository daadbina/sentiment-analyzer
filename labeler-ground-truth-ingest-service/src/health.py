"""Health check endpoints for labeler service."""

from typing import Dict, Any, Optional
from datetime import datetime

from src.config import config
from src.utils.trace import get_logger

logger = get_logger(__name__, config.logging.log_level)


class HealthChecker:
    """Health check manager for service dependencies."""

    def __init__(self):
        """Initialize health checker."""
        self.start_time = datetime.now()
        self.last_check_time: Optional[datetime] = None
        self.kafka_producer = None
        self.postgres_writer = None
        self.schema_registry_client = None

    def set_dependencies(
        self,
        kafka_producer=None,
        postgres_writer=None,
        schema_registry_client=None
    ):
        """Set service dependencies for health checks.

        Args:
            kafka_producer: Kafka producer client
            postgres_writer: PostgreSQL writer with pool
            schema_registry_client: Schema Registry client
        """
        self.kafka_producer = kafka_producer
        self.postgres_writer = postgres_writer
        self.schema_registry_client = schema_registry_client

    async def check_kafka_producer(self) -> Dict[str, Any]:
        """Check Kafka producer health.
        
        Returns:
            Health status dictionary
        """
        try:
            if not self.kafka_producer:
                return {"status": "unknown", "message": "Producer not initialized"}
            
            status = self.kafka_producer.get_health_status()
            
            if status.get("connected"):
                return {
                    "status": "healthy",
                    "message": "Kafka producer connected",
                    "details": status
                }
            else:
                return {
                    "status": "unhealthy",
                    "message": "Kafka producer not connected",
                    "details": status
                }
        except Exception as e:
            logger.error(
                f"Error checking Kafka producer health: {str(e)}",
                operation="check_kafka_producer"
            )
            return {
                "status": "unhealthy",
                "message": f"Error checking producer: {str(e)}"
            }

    async def check_postgres(self) -> Dict[str, Any]:
        """Check PostgreSQL health.

        Returns:
            Health status dictionary
        """
        try:
            if not self.postgres_writer or not self.postgres_writer.pool:
                return {"status": "unknown", "message": "PostgreSQL writer not initialized"}

            # Try to execute a simple query
            conn = await self.postgres_writer.pool.acquire()
            try:
                await conn.fetchval("SELECT 1")
            finally:
                await self.postgres_writer.pool.release(conn)

            return {
                "status": "healthy",
                "message": "PostgreSQL connected and responding"
            }
        except Exception as e:
            logger.error(
                f"Error checking PostgreSQL health: {str(e)}",
                operation="check_postgres"
            )
            return {
                "status": "unhealthy",
                "message": f"PostgreSQL error: {str(e)}"
            }

    async def check_schema_registry(self) -> Dict[str, Any]:
        """Check Schema Registry health.
        
        Returns:
            Health status dictionary
        """
        try:
            if not self.schema_registry_client:
                return {"status": "unknown", "message": "Schema Registry client not initialized"}
            
            # Try to get subjects
            subjects = self.schema_registry_client.get_subjects()
            
            return {
                "status": "healthy",
                "message": "Schema Registry connected",
                "details": {"subjects_count": len(subjects)}
            }
        except Exception as e:
            logger.error(
                f"Error checking Schema Registry health: {str(e)}",
                operation="check_schema_registry"
            )
            return {
                "status": "unhealthy",
                "message": f"Schema Registry error: {str(e)}"
            }

    async def get_health(self) -> Dict[str, Any]:
        """Get overall service health.

        Returns:
            Health status dictionary
        """
        self.last_check_time = datetime.now()

        kafka_producer_health = await self.check_kafka_producer()
        postgres_health = await self.check_postgres()
        schema_registry_health = await self.check_schema_registry()

        # Determine overall status
        statuses = [
            kafka_producer_health.get("status"),
            postgres_health.get("status"),
            schema_registry_health.get("status")
        ]

        if "unhealthy" in statuses:
            overall_status = "unhealthy"
        elif "unknown" in statuses:
            overall_status = "degraded"
        else:
            overall_status = "healthy"

        return {
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
            "checks": {
                "kafka_producer": kafka_producer_health,
                "postgres": postgres_health,
                "schema_registry": schema_registry_health
            }
        }

    async def get_ready(self) -> Dict[str, Any]:
        """Get readiness status (all critical services must be healthy).
        
        Returns:
            Readiness status dictionary
        """
        health = await self.get_health()
        
        # Service is ready if all checks are healthy
        is_ready = health["status"] == "healthy"
        
        return {
            "ready": is_ready,
            "status": health["status"],
            "checks": health["checks"]
        }

    async def get_live(self) -> Dict[str, Any]:
        """Get liveness status (service is running).
        
        Returns:
            Liveness status dictionary
        """
        return {
            "alive": True,
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds()
        }

