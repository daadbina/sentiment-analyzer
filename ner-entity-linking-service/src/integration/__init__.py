"""Downstream service integration for NER Entity Linking Service."""

from src.integration.downstream_service import (
    DownstreamService,
    DownstreamMessage,
    DownstreamServiceIntegration,
    ServiceHealthCheck,
    IntegrationMetrics,
)

__all__ = [
    "DownstreamService",
    "DownstreamMessage",
    "DownstreamServiceIntegration",
    "ServiceHealthCheck",
    "IntegrationMetrics",
]

