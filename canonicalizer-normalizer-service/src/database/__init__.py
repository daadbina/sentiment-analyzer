"""Database module with connection pooling and optimization."""

from .connection_pool import (
    ConnectionPoolManager,
    IndexManager,
    PoolStats,
)

__all__ = [
    'ConnectionPoolManager',
    'IndexManager',
    'PoolStats',
]

