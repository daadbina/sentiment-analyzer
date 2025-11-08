"""
Neo4j client with connection pooling, sessions, transactions, and retry logic.
Implements the Repository pattern to abstract Neo4j operations.
"""

import time
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
from neo4j import GraphDatabase, Driver, Session, Transaction, exceptions as neo4j_exceptions
import structlog

from ..config import config
from ..exceptions import ConnectionError, QueryError
from ..metrics import (
    neo4j_connection_pool_size,
    neo4j_connection_pool_in_use,
    neo4j_connection_errors_total,
    graph_query_latency_ms,
    graph_query_total,
)

logger = structlog.get_logger(__name__)


class Neo4jClient:
    """
    Neo4j client with connection pooling and retry logic.
    Provides high-level interface for graph operations.
    """

    def __init__(self):
        """Initialize Neo4j client with connection pool."""
        self._driver: Optional[Driver] = None
        self._is_connected = False

    def connect(self) -> None:
        """
        Establish connection to Neo4j database.
        
        Raises:
            ConnectionError: If connection fails
        """
        try:
            neo4j_config = config.get_neo4j_config()
            self._driver = GraphDatabase.driver(
                neo4j_config["uri"],
                auth=neo4j_config["auth"],
                max_connection_lifetime=neo4j_config["max_connection_lifetime"],
                max_connection_pool_size=neo4j_config["max_connection_pool_size"],
                connection_timeout=neo4j_config["connection_timeout"],
                encrypted=neo4j_config["encrypted"],
            )
            
            # Verify connectivity
            self._driver.verify_connectivity()
            self._is_connected = True
            
            logger.info(
                "neo4j_connection_established",
                uri=neo4j_config["uri"],
                database=config.neo4j_database,
            )
            
        except Exception as e:
            neo4j_connection_errors_total.labels(error_type="connection_failed").inc()
            logger.error(
                "neo4j_connection_failed",
                error=str(e),
                uri=config.neo4j_uri,
            )
            raise ConnectionError(
                message=f"Failed to connect to Neo4j: {str(e)}",
                service="neo4j",
                host=config.neo4j_uri,
            ) from e

    def close(self) -> None:
        """Close Neo4j driver and release connections."""
        if self._driver:
            self._driver.close()
            self._is_connected = False
            logger.info("neo4j_connection_closed")

    def is_connected(self) -> bool:
        """Check if client is connected to Neo4j."""
        return self._is_connected and self._driver is not None

    @contextmanager
    def session(self, database: Optional[str] = None):
        """
        Context manager for Neo4j session.
        
        Args:
            database: Database name (defaults to configured database)
            
        Yields:
            Neo4j session
            
        Raises:
            ConnectionError: If not connected
        """
        if not self.is_connected():
            raise ConnectionError(
                message="Neo4j client is not connected",
                service="neo4j",
            )
        
        db_name = database or config.neo4j_database
        session = self._driver.session(database=db_name)
        
        try:
            neo4j_connection_pool_in_use.inc()
            yield session
        finally:
            neo4j_connection_pool_in_use.dec()
            session.close()

    def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query and return results.
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            database: Database name
            trace_id: Trace ID for correlation
            
        Returns:
            List of result records as dictionaries
            
        Raises:
            QueryError: If query execution fails
        """
        start_time = time.time()
        parameters = parameters or {}
        
        try:
            with self.session(database) as session:
                result = session.run(query, parameters)
                records = [dict(record) for record in result]
                
            duration_ms = (time.time() - start_time) * 1000
            graph_query_latency_ms.labels(query_type="read").observe(duration_ms)
            graph_query_total.labels(query_type="read", status="success").inc()
            
            logger.debug(
                "neo4j_query_executed",
                query=query[:100],  # Log first 100 chars
                parameters=parameters,
                duration_ms=duration_ms,
                result_count=len(records),
                trace_id=trace_id,
            )
            
            return records
            
        except neo4j_exceptions.Neo4jError as e:
            duration_ms = (time.time() - start_time) * 1000
            graph_query_total.labels(query_type="read", status="error").inc()
            neo4j_connection_errors_total.labels(error_type="query_error").inc()
            
            logger.error(
                "neo4j_query_failed",
                query=query[:100],
                parameters=parameters,
                error=str(e),
                duration_ms=duration_ms,
                trace_id=trace_id,
            )
            
            raise QueryError(
                message=f"Query execution failed: {str(e)}",
                query=query,
                parameters=parameters,
                trace_id=trace_id,
            ) from e

    def execute_write(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute a write query in a transaction.
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            database: Database name
            trace_id: Trace ID for correlation
            
        Returns:
            Query execution summary
            
        Raises:
            QueryError: If query execution fails
        """
        start_time = time.time()
        parameters = parameters or {}
        
        try:
            with self.session(database) as session:
                result = session.run(query, parameters)
                summary = result.consume()
                
            duration_ms = (time.time() - start_time) * 1000
            graph_query_latency_ms.labels(query_type="write").observe(duration_ms)
            graph_query_total.labels(query_type="write", status="success").inc()
            
            logger.debug(
                "neo4j_write_executed",
                query=query[:100],
                parameters=parameters,
                duration_ms=duration_ms,
                nodes_created=summary.counters.nodes_created,
                relationships_created=summary.counters.relationships_created,
                trace_id=trace_id,
            )
            
            return {
                "nodes_created": summary.counters.nodes_created,
                "nodes_deleted": summary.counters.nodes_deleted,
                "relationships_created": summary.counters.relationships_created,
                "relationships_deleted": summary.counters.relationships_deleted,
                "properties_set": summary.counters.properties_set,
            }
            
        except neo4j_exceptions.Neo4jError as e:
            duration_ms = (time.time() - start_time) * 1000
            graph_query_total.labels(query_type="write", status="error").inc()
            neo4j_connection_errors_total.labels(error_type="write_error").inc()
            
            logger.error(
                "neo4j_write_failed",
                query=query[:100],
                parameters=parameters,
                error=str(e),
                duration_ms=duration_ms,
                trace_id=trace_id,
            )
            
            raise QueryError(
                message=f"Write query failed: {str(e)}",
                query=query,
                parameters=parameters,
                trace_id=trace_id,
            ) from e

    def execute_batch_write(
        self,
        query: str,
        batch_parameters: List[Dict[str, Any]],
        database: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute a batch write using UNWIND.
        
        Args:
            query: Cypher query with UNWIND
            batch_parameters: List of parameter dictionaries
            database: Database name
            trace_id: Trace ID for correlation
            
        Returns:
            Batch execution summary
            
        Raises:
            QueryError: If batch write fails
        """
        start_time = time.time()
        
        try:
            with self.session(database) as session:
                result = session.run(query, {"batch": batch_parameters})
                summary = result.consume()
                
            duration_ms = (time.time() - start_time) * 1000
            graph_query_latency_ms.labels(query_type="batch_write").observe(duration_ms)
            graph_query_total.labels(query_type="batch_write", status="success").inc()
            
            logger.info(
                "neo4j_batch_write_executed",
                batch_size=len(batch_parameters),
                duration_ms=duration_ms,
                nodes_created=summary.counters.nodes_created,
                relationships_created=summary.counters.relationships_created,
                trace_id=trace_id,
            )
            
            return {
                "batch_size": len(batch_parameters),
                "nodes_created": summary.counters.nodes_created,
                "nodes_deleted": summary.counters.nodes_deleted,
                "relationships_created": summary.counters.relationships_created,
                "relationships_deleted": summary.counters.relationships_deleted,
                "properties_set": summary.counters.properties_set,
                "duration_ms": duration_ms,
            }
            
        except neo4j_exceptions.Neo4jError as e:
            duration_ms = (time.time() - start_time) * 1000
            graph_query_total.labels(query_type="batch_write", status="error").inc()
            neo4j_connection_errors_total.labels(error_type="batch_write_error").inc()
            
            logger.error(
                "neo4j_batch_write_failed",
                batch_size=len(batch_parameters),
                error=str(e),
                duration_ms=duration_ms,
                trace_id=trace_id,
            )
            
            raise QueryError(
                message=f"Batch write failed: {str(e)}",
                query=query,
                parameters={"batch_size": len(batch_parameters)},
                trace_id=trace_id,
            ) from e

    def health_check(self) -> bool:
        """
        Perform health check on Neo4j connection.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            if not self.is_connected():
                return False
                
            # Simple query to verify connectivity
            self.execute_query("RETURN 1 AS health")
            return True
            
        except Exception as e:
            logger.warning("neo4j_health_check_failed", error=str(e))
            return False


# Global Neo4j client instance
neo4j_client = Neo4jClient()

