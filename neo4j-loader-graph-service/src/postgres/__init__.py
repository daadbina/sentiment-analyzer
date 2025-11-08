"""PostgreSQL integration for metadata and audit logging."""

from .client import postgres_client, PostgresClient

__all__ = [
    "postgres_client",
    "PostgresClient",
]
