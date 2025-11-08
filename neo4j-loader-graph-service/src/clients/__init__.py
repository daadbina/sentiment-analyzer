"""Clients package for external service connections."""

from .neo4j_client import Neo4jClient, neo4j_client

__all__ = ["Neo4jClient", "neo4j_client"]

