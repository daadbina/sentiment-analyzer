"""
Health check module for service monitoring.

Provides health status and readiness checks.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status enumeration."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class HealthCheck:
    """
    Health check for service components.

    Tracks component health status.
    """

    def __init__(self, name: str) -> None:
        """
        Initialize health check.

        Args:
            name: Component name.
        """
        self.name = name
        self.status = HealthStatus.HEALTHY
        self.last_check: Optional[datetime] = None
        self.error_message: Optional[str] = None

    def set_healthy(self) -> None:
        """Mark component as healthy."""
        self.status = HealthStatus.HEALTHY
        self.last_check = datetime.utcnow()
        self.error_message = None

    def set_degraded(self, error: str) -> None:
        """
        Mark component as degraded.

        Args:
            error: Error message.
        """
        self.status = HealthStatus.DEGRADED
        self.last_check = datetime.utcnow()
        self.error_message = error

    def set_unhealthy(self, error: str) -> None:
        """
        Mark component as unhealthy.

        Args:
            error: Error message.
        """
        self.status = HealthStatus.UNHEALTHY
        self.last_check = datetime.utcnow()
        self.error_message = error

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.

        Returns:
            dict: Health check data.
        """
        return {
            "name": self.name,
            "status": self.status.value,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "error": self.error_message,
        }


class HealthCheckManager:
    """
    Manages health checks for all service components.

    Aggregates component health into overall service health.
    """

    def __init__(self) -> None:
        """Initialize health check manager."""
        self.checks: Dict[str, HealthCheck] = {}
        self.started_at = datetime.utcnow()

    def register_check(self, name: str) -> HealthCheck:
        """
        Register health check for component.

        Args:
            name: Component name.

        Returns:
            HealthCheck: Health check instance.
        """
        check = HealthCheck(name)
        self.checks[name] = check
        logger.info(f"Registered health check for {name}")
        return check

    def get_check(self, name: str) -> Optional[HealthCheck]:
        """
        Get health check for component.

        Args:
            name: Component name.

        Returns:
            HealthCheck or None if not found.
        """
        return self.checks.get(name)

    def get_overall_status(self) -> HealthStatus:
        """
        Get overall service health status.

        Returns:
            HealthStatus: Overall status.
        """
        if not self.checks:
            return HealthStatus.HEALTHY

        statuses = [check.status for check in self.checks.values()]

        # If any component is unhealthy, service is unhealthy
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY

        # If any component is degraded, service is degraded
        if HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED

        return HealthStatus.HEALTHY

    def get_readiness(self) -> bool:
        """
        Check if service is ready to handle requests.

        Returns:
            bool: True if ready.
        """
        # Service is ready if no critical components are unhealthy
        critical_components = {"kafka_producer", "feed_registry", "scheduler"}

        for name in critical_components:
            check = self.get_check(name)
            if check and check.status == HealthStatus.UNHEALTHY:
                return False

        return True

    def get_liveness(self) -> bool:
        """
        Check if service is alive.

        Returns:
            bool: True if alive.
        """
        # Service is alive if it's running
        return True

    def get_health_report(self) -> Dict[str, Any]:
        """
        Get comprehensive health report.

        Returns:
            dict: Health report.
        """
        return {
            "status": self.get_overall_status().value,
            "ready": self.get_readiness(),
            "alive": self.get_liveness(),
            "uptime_seconds": (
                datetime.utcnow() - self.started_at
            ).total_seconds(),
            "components": {
                name: check.to_dict() for name, check in self.checks.items()
            },
        }

    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get health metrics summary for Prometheus.

        Returns:
            dict: Metrics summary.
        """
        overall_status = self.get_overall_status()
        status_value = 1 if overall_status == HealthStatus.HEALTHY else 0

        return {
            "health_status": status_value,
            "ready": 1 if self.get_readiness() else 0,
            "alive": 1 if self.get_liveness() else 0,
            "uptime_seconds": (datetime.utcnow() - self.started_at).total_seconds(),
        }
