"""
PostgreSQL client for Neo4j Loader Graph Service.
Handles metadata storage, audit logging, and lineage tracking.
"""

from typing import Dict, Any, List, Optional
import asyncpg
import structlog
import json
from datetime import datetime

from ..config import config
from ..exceptions import ConnectionError as GraphConnectionError, QueryError

logger = structlog.get_logger(__name__)


class PostgresClient:
    """
    Async PostgreSQL client for metadata and audit storage.
    """

    def __init__(self):
        """Initialize PostgreSQL client."""
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        """
        Establish connection pool to PostgreSQL.
        
        Raises:
            GraphConnectionError: If connection fails
        """
        try:
            self._pool = await asyncpg.create_pool(
                host=config.postgres_host,
                port=config.postgres_port,
                user=config.postgres_user,
                password=config.postgres_password,
                database=config.postgres_database,
                min_size=config.postgres_min_pool_size,
                max_size=config.postgres_max_pool_size,
                command_timeout=60,
            )
            
            logger.info(
                "postgres_connected",
                host=config.postgres_host,
                database=config.postgres_database,
                pool_size=f"{config.postgres_min_pool_size}-{config.postgres_max_pool_size}",
            )
            
            # Initialize schema
            await self._initialize_schema()
            
        except Exception as e:
            logger.error(
                "postgres_connection_failed",
                error=str(e),
                host=config.postgres_host,
            )
            raise GraphConnectionError(
                message=f"Failed to connect to PostgreSQL: {str(e)}",
                service="postgresql",
                host=config.postgres_host,
            ) from e

    async def close(self) -> None:
        """Close PostgreSQL connection pool."""
        if self._pool:
            await self._pool.close()
            logger.info("postgres_connection_closed")

    async def _initialize_schema(self) -> None:
        """Initialize database schema for graph metadata and audit tables."""
        try:
            # Create graph_metadata table
            await self.execute_query("""
                CREATE TABLE IF NOT EXISTS graph_metadata (
                    id SERIAL PRIMARY KEY,
                    snapshot_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
                    node_counts JSONB NOT NULL,
                    relationship_counts JSONB NOT NULL,
                    centrality_stats JSONB,
                    clustering_stats JSONB,
                    graph_metrics JSONB,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW()
                )
            """)
            
            # Create graph_audit table
            await self.execute_query("""
                CREATE TABLE IF NOT EXISTS graph_audit (
                    id SERIAL PRIMARY KEY,
                    operation_type VARCHAR(50) NOT NULL,
                    node_type VARCHAR(50),
                    node_id VARCHAR(255),
                    relationship_type VARCHAR(50),
                    operation_status VARCHAR(20) NOT NULL,
                    trace_id VARCHAR(255),
                    error_message TEXT,
                    metadata JSONB,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW()
                )
            """)
            
            # Create data_lineage table
            await self.execute_query("""
                CREATE TABLE IF NOT EXISTS data_lineage (
                    id SERIAL PRIMARY KEY,
                    source_system VARCHAR(100) NOT NULL,
                    source_topic VARCHAR(255) NOT NULL,
                    source_offset BIGINT,
                    source_partition INT,
                    node_id VARCHAR(255) NOT NULL,
                    node_type VARCHAR(50) NOT NULL,
                    transformation_applied VARCHAR(255),
                    trace_id VARCHAR(255),
                    created_at TIMESTAMP NOT NULL DEFAULT NOW()
                )
            """)
            
            # Create indexes
            await self.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_graph_audit_created_at 
                ON graph_audit(created_at DESC)
            """)
            
            await self.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_graph_audit_trace_id 
                ON graph_audit(trace_id)
            """)
            
            await self.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_data_lineage_node_id 
                ON data_lineage(node_id)
            """)
            
            await self.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_data_lineage_trace_id 
                ON data_lineage(trace_id)
            """)
            
            logger.info("postgres_schema_initialized")
            
        except Exception as e:
            logger.error("postgres_schema_initialization_failed", error=str(e))
            raise

    async def execute_query(
        self,
        query: str,
        params: Optional[List[Any]] = None,
        trace_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query.
        
        Args:
            query: SQL query
            params: Query parameters
            trace_id: Trace ID for correlation
            
        Returns:
            List of result rows as dictionaries
            
        Raises:
            QueryError: If query execution fails
        """
        if not self._pool:
            raise GraphConnectionError(
                message="PostgreSQL pool is not initialized",
                service="postgresql",
            )
        
        try:
            async with self._pool.acquire() as conn:
                if params:
                    rows = await conn.fetch(query, *params)
                else:
                    rows = await conn.fetch(query)
                
                results = [dict(row) for row in rows]
                
                logger.debug(
                    "postgres_query_executed",
                    query_preview=query[:100],
                    row_count=len(results),
                    trace_id=trace_id,
                )
                
                return results
                
        except Exception as e:
            logger.error(
                "postgres_query_failed",
                query_preview=query[:100],
                error=str(e),
                trace_id=trace_id,
            )
            raise QueryError(
                message=f"PostgreSQL query failed: {str(e)}",
                query=query[:200],
                details={"error": str(e)},
            ) from e

    async def execute_insert(
        self,
        query: str,
        params: Optional[List[Any]] = None,
        trace_id: Optional[str] = None,
    ) -> int:
        """
        Execute an INSERT query.
        
        Args:
            query: SQL INSERT query
            params: Query parameters
            trace_id: Trace ID for correlation
            
        Returns:
            ID of inserted row
            
        Raises:
            QueryError: If insert fails
        """
        if not self._pool:
            raise GraphConnectionError(
                message="PostgreSQL pool is not initialized",
                service="postgresql",
            )
        
        try:
            async with self._pool.acquire() as conn:
                if params:
                    row_id = await conn.fetchval(query + " RETURNING id", *params)
                else:
                    row_id = await conn.fetchval(query + " RETURNING id")
                
                logger.debug(
                    "postgres_insert_executed",
                    query_preview=query[:100],
                    row_id=row_id,
                    trace_id=trace_id,
                )
                
                return row_id
                
        except Exception as e:
            logger.error(
                "postgres_insert_failed",
                query_preview=query[:100],
                error=str(e),
                trace_id=trace_id,
            )
            raise QueryError(
                message=f"PostgreSQL insert failed: {str(e)}",
                query=query[:200],
                details={"error": str(e)},
            ) from e

    async def save_graph_metadata(
        self,
        node_counts: Dict[str, int],
        relationship_counts: Dict[str, int],
        centrality_stats: Optional[Dict[str, Any]] = None,
        clustering_stats: Optional[Dict[str, Any]] = None,
        graph_metrics: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ) -> int:
        """
        Save graph metadata snapshot.
        
        Args:
            node_counts: Node counts by label
            relationship_counts: Relationship counts by type
            centrality_stats: Centrality computation results
            clustering_stats: Clustering detection results
            graph_metrics: Global graph metrics
            trace_id: Trace ID for correlation
            
        Returns:
            Snapshot ID
        """
        query = """
        INSERT INTO graph_metadata (
            node_counts,
            relationship_counts,
            centrality_stats,
            clustering_stats,
            graph_metrics
        ) VALUES ($1, $2, $3, $4, $5)
        """
        
        params = [
            json.dumps(node_counts),
            json.dumps(relationship_counts),
            json.dumps(centrality_stats) if centrality_stats else None,
            json.dumps(clustering_stats) if clustering_stats else None,
            json.dumps(graph_metrics) if graph_metrics else None,
        ]
        
        snapshot_id = await self.execute_insert(query, params, trace_id)
        
        logger.info(
            "graph_metadata_saved",
            snapshot_id=snapshot_id,
            total_nodes=node_counts.get("_total", 0),
            total_relationships=relationship_counts.get("_total", 0),
            trace_id=trace_id,
        )
        
        return snapshot_id

    async def log_audit_event(
        self,
        operation_type: str,
        operation_status: str,
        node_type: Optional[str] = None,
        node_id: Optional[str] = None,
        relationship_type: Optional[str] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ) -> int:
        """
        Log audit event.
        
        Args:
            operation_type: Type of operation (load, update, delete)
            operation_status: Status (success, failure)
            node_type: Node type
            node_id: Node ID
            relationship_type: Relationship type
            error_message: Error message if failed
            metadata: Additional metadata
            trace_id: Trace ID for correlation
            
        Returns:
            Audit log ID
        """
        query = """
        INSERT INTO graph_audit (
            operation_type,
            node_type,
            node_id,
            relationship_type,
            operation_status,
            trace_id,
            error_message,
            metadata
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """
        
        params = [
            operation_type,
            node_type,
            node_id,
            relationship_type,
            operation_status,
            trace_id,
            error_message,
            json.dumps(metadata) if metadata else None,
        ]
        
        audit_id = await self.execute_insert(query, params, trace_id)
        
        logger.debug(
            "audit_event_logged",
            audit_id=audit_id,
            operation_type=operation_type,
            operation_status=operation_status,
            trace_id=trace_id,
        )
        
        return audit_id

    async def track_lineage(
        self,
        source_system: str,
        source_topic: str,
        node_id: str,
        node_type: str,
        source_offset: Optional[int] = None,
        source_partition: Optional[int] = None,
        transformation_applied: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> int:
        """
        Track data lineage from source to Neo4j.

        Args:
            source_system: Source system name (e.g., 'kafka')
            source_topic: Source topic name
            node_id: Node ID in Neo4j
            node_type: Node type
            source_offset: Kafka offset
            source_partition: Kafka partition
            transformation_applied: Transformation description
            trace_id: Trace ID for correlation

        Returns:
            Lineage record ID
        """
        query = """
        INSERT INTO data_lineage (
            source_system,
            source_topic,
            source_offset,
            source_partition,
            node_id,
            node_type,
            transformation_applied,
            trace_id
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """

        params = [
            source_system,
            source_topic,
            source_offset,
            source_partition,
            node_id,
            node_type,
            transformation_applied,
            trace_id,
        ]

        lineage_id = await self.execute_insert(query, params, trace_id)

        logger.debug(
            "lineage_tracked",
            lineage_id=lineage_id,
            source_topic=source_topic,
            node_id=node_id,
            node_type=node_type,
            trace_id=trace_id,
        )

        return lineage_id

    async def get_latest_snapshot(self) -> Optional[Dict[str, Any]]:
        """
        Get the latest graph metadata snapshot.

        Returns:
            Latest snapshot data or None if no snapshots exist
        """
        query = """
        SELECT * FROM graph_metadata
        ORDER BY snapshot_timestamp DESC
        LIMIT 1
        """

        results = await self.execute_query(query)

        if results:
            return results[0]

        return None

    async def get_node_lineage(
        self,
        node_id: str,
        trace_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get lineage history for a specific node.

        Args:
            node_id: Node ID
            trace_id: Trace ID for correlation

        Returns:
            List of lineage records
        """
        query = """
        SELECT * FROM data_lineage
        WHERE node_id = $1
        ORDER BY created_at DESC
        """

        results = await self.execute_query(query, [node_id], trace_id)

        logger.debug(
            "node_lineage_retrieved",
            node_id=node_id,
            record_count=len(results),
            trace_id=trace_id,
        )

        return results


# Global PostgreSQL client instance
postgres_client = PostgresClient()

