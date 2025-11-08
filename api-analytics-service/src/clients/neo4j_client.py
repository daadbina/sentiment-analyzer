"""Neo4j graph database client."""

from neo4j import AsyncDriver, AsyncSession, async_driver
from typing import Optional, List, Dict, Any
import logging

from src.config import config
from src.exceptions import DatabaseConnectionError, QueryError
from src.utils.logging import get_logger, LatencyTracker

logger = get_logger(__name__)


class Neo4jClient:
    """Neo4j graph database client."""

    def __init__(self):
        """Initialize Neo4j client."""
        self.driver: Optional[AsyncDriver] = None
        self.config = config.neo4j

    async def connect(self) -> None:
        """Create Neo4j driver.

        Raises:
            DatabaseConnectionError: If connection fails
        """
        try:
            logger.info("Connecting to Neo4j...")

            self.driver = async_driver(
                self.config.uri,
                auth=(self.config.user, self.config.password),
                connection_timeout=self.config.connection_timeout,
                max_pool_size=self.config.pool_size,
            )

            # Test connection
            async with self.driver.session() as session:
                await session.run("RETURN 1")

            logger.info(
                "Neo4j connection established",
                extra={
                    "extra_fields": {
                        "uri": self.config.uri,
                        "pool_size": self.config.pool_size,
                    }
                },
            )

        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {str(e)}")
            raise DatabaseConnectionError(
                message="Failed to connect to Neo4j",
                details={"error": str(e)},
            )

    async def disconnect(self) -> None:
        """Close Neo4j driver."""
        if self.driver:
            await self.driver.close()
            logger.info("Neo4j driver closed")

    async def health_check(self) -> bool:
        """Check Neo4j health.

        Returns:
            True if Neo4j is healthy, False otherwise
        """
        try:
            if not self.driver:
                return False

            async with self.driver.session() as session:
                await session.run("RETURN 1")

            logger.info("Neo4j health check passed")
            return True

        except Exception as e:
            logger.error(f"Neo4j health check failed: {str(e)}")
            return False

    async def execute(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Execute Cypher query.

        Args:
            query: Cypher query
            parameters: Query parameters

        Returns:
            List of result records

        Raises:
            DatabaseConnectionError: If not connected
            QueryError: If query execution fails
        """
        if not self.driver:
            raise DatabaseConnectionError(
                message="Not connected to Neo4j"
            )

        try:
            with LatencyTracker(logger, "Neo4j execute"):
                async with self.driver.session() as session:
                    result = await session.run(query, parameters or {})
                    records = await result.data()
                    return records

        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            raise QueryError(
                message="Query execution failed",
                details={"error": str(e), "query": query},
            )

    async def execute_write(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Execute write Cypher query in transaction.

        Args:
            query: Cypher query
            parameters: Query parameters

        Returns:
            List of result records

        Raises:
            DatabaseConnectionError: If not connected
            QueryError: If query execution fails
        """
        if not self.driver:
            raise DatabaseConnectionError(
                message="Not connected to Neo4j"
            )

        try:
            with LatencyTracker(logger, "Neo4j execute_write"):
                async with self.driver.session() as session:
                    result = await session.write_transaction(
                        self._execute_query,
                        query,
                        parameters or {},
                    )
                    return result

        except Exception as e:
            logger.error(f"Write query execution failed: {str(e)}")
            raise QueryError(
                message="Write query execution failed",
                details={"error": str(e), "query": query},
            )

    @staticmethod
    async def _execute_query(
        tx,
        query: str,
        parameters: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Execute query in transaction.

        Args:
            tx: Transaction
            query: Cypher query
            parameters: Query parameters

        Returns:
            List of result records
        """
        result = await tx.run(query, parameters)
        return await result.data()

    async def get_neighbors(
        self,
        node_id: str,
        relationship_type: Optional[str] = None,
        depth: int = 1,
    ) -> List[Dict[str, Any]]:
        """Get neighboring nodes.

        Args:
            node_id: Node ID
            relationship_type: Optional relationship type filter
            depth: Traversal depth

        Returns:
            List of neighboring nodes

        Raises:
            DatabaseConnectionError: If not connected
            QueryError: If query execution fails
        """
        rel_filter = f":{relationship_type}" if relationship_type else ""
        query = f"""
            MATCH (n)-[{rel_filter}*1..{depth}]-(neighbor)
            WHERE n.id = $node_id
            RETURN DISTINCT neighbor
        """

        return await self.execute(query, {"node_id": node_id})

    async def find_paths(
        self,
        from_id: str,
        to_id: str,
        max_length: int = 5,
    ) -> List[Dict[str, Any]]:
        """Find paths between nodes.

        Args:
            from_id: Source node ID
            to_id: Target node ID
            max_length: Maximum path length

        Returns:
            List of paths

        Raises:
            DatabaseConnectionError: If not connected
            QueryError: If query execution fails
        """
        query = f"""
            MATCH path = shortestPath((from)-[*1..{max_length}]-(to))
            WHERE from.id = $from_id AND to.id = $to_id
            RETURN path
        """

        return await self.execute(
            query,
            {"from_id": from_id, "to_id": to_id},
        )


# Global Neo4j client instance
neo4j_client = Neo4jClient()

