"""
Stream loader for Neo4j graph.
Implements streaming ingestion with buffering and flush logic.
"""

from typing import Dict, Any, List, Optional
import time
from collections import defaultdict
import structlog

from ..clients.neo4j_client import neo4j_client
from ..builders.node_builder import node_builder
from ..builders.relationship_builder import relationship_builder
from ..config import config
from ..exceptions import LoadError
from ..metrics import (
    graph_load_duration_seconds,
    graph_nodes_created_total,
    graph_relationships_created_total,
)

logger = structlog.get_logger(__name__)


class StreamLoader:
    """
    Stream loader for Neo4j graph operations.
    Buffers messages and flushes periodically or when buffer is full.
    """

    def __init__(self):
        """Initialize stream loader."""
        self.client = neo4j_client
        self.buffer_size = config.stream_buffer_size
        self.flush_interval = config.stream_flush_timeout
        
        # Buffers for each node type
        self.node_buffers: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        # Buffers for each relationship type
        self.relationship_buffers: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        # Last flush time
        self.last_flush_time = time.time()

    def add_node(
        self,
        node_label: str,
        node_data: Dict[str, Any],
        trace_id: Optional[str] = None,
    ) -> None:
        """
        Add node to buffer.
        
        Args:
            node_label: Node label
            node_data: Node properties
            trace_id: Trace ID for correlation
        """
        self.node_buffers[node_label].append(node_data)
        
        logger.debug(
            "node_added_to_buffer",
            node_label=node_label,
            buffer_size=len(self.node_buffers[node_label]),
            trace_id=trace_id,
        )
        
        # Check if buffer is full
        if len(self.node_buffers[node_label]) >= self.buffer_size:
            self.flush_nodes(node_label, trace_id=trace_id)

    def add_relationship(
        self,
        from_label: str,
        to_label: str,
        rel_type: str,
        relationship_data: Dict[str, Any],
        trace_id: Optional[str] = None,
    ) -> None:
        """
        Add relationship to buffer.
        
        Args:
            from_label: Source node label
            to_label: Target node label
            rel_type: Relationship type
            relationship_data: Relationship data (from_id, to_id, properties)
            trace_id: Trace ID for correlation
        """
        buffer_key = f"{from_label}_{rel_type}_{to_label}"
        self.relationship_buffers[buffer_key].append({
            "from_label": from_label,
            "to_label": to_label,
            "rel_type": rel_type,
            "data": relationship_data,
        })
        
        logger.debug(
            "relationship_added_to_buffer",
            rel_type=rel_type,
            buffer_size=len(self.relationship_buffers[buffer_key]),
            trace_id=trace_id,
        )
        
        # Check if buffer is full
        if len(self.relationship_buffers[buffer_key]) >= self.buffer_size:
            self.flush_relationships(buffer_key, trace_id=trace_id)

    def flush_nodes(
        self,
        node_label: str,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Flush node buffer to Neo4j.
        
        Args:
            node_label: Node label to flush
            trace_id: Trace ID for correlation
            
        Returns:
            Flush summary
        """
        start_time = time.time()
        
        buffer = self.node_buffers[node_label]
        if not buffer:
            return {"nodes_created": 0, "duration_ms": 0}

        try:
            # Build batch query
            query, parameters = node_builder.build_batch_create_query(
                node_label=node_label,
                batch_data=buffer,
            )
            
            # Execute batch write
            result = self.client.execute_batch_write(
                query=query,
                batch_parameters=parameters["batch"],
                trace_id=trace_id,
            )
            
            # Clear buffer
            self.node_buffers[node_label] = []
            
            # Record metrics
            duration = time.time() - start_time
            nodes_created = result.get("nodes_created", 0)
            graph_nodes_created_total.labels(node_type=node_label).inc(nodes_created)
            
            logger.info(
                "nodes_buffer_flushed",
                node_label=node_label,
                buffer_size=len(buffer),
                nodes_created=nodes_created,
                duration_seconds=duration,
                trace_id=trace_id,
            )
            
            return {
                "nodes_created": nodes_created,
                "buffer_size": len(buffer),
                "duration_ms": duration * 1000,
            }
            
        except Exception as e:
            logger.error(
                "nodes_buffer_flush_failed",
                node_label=node_label,
                buffer_size=len(buffer),
                error=str(e),
                trace_id=trace_id,
            )
            raise LoadError(
                message=f"Failed to flush nodes buffer: {str(e)}",
                details={"node_label": node_label, "buffer_size": len(buffer)},
                trace_id=trace_id,
            ) from e

    def flush_relationships(
        self,
        buffer_key: str,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Flush relationship buffer to Neo4j.
        
        Args:
            buffer_key: Buffer key (from_label_rel_type_to_label)
            trace_id: Trace ID for correlation
            
        Returns:
            Flush summary
        """
        start_time = time.time()
        
        buffer = self.relationship_buffers[buffer_key]
        if not buffer:
            return {"relationships_created": 0, "duration_ms": 0}

        try:
            # Extract relationship info from first item
            first_item = buffer[0]
            from_label = first_item["from_label"]
            to_label = first_item["to_label"]
            rel_type = first_item["rel_type"]
            
            # Extract relationship data
            relationships_data = [item["data"] for item in buffer]
            
            # Build batch query
            query, parameters = relationship_builder.build_batch_create_relationships_query(
                from_label=from_label,
                to_label=to_label,
                rel_type=rel_type,
                batch_data=relationships_data,
            )
            
            # Execute batch write
            result = self.client.execute_batch_write(
                query=query,
                batch_parameters=parameters["batch"],
                trace_id=trace_id,
            )
            
            # Clear buffer
            self.relationship_buffers[buffer_key] = []
            
            # Record metrics
            duration = time.time() - start_time
            relationships_created = result.get("relationships_created", 0)
            graph_relationships_created_total.labels(
                relationship_type=rel_type
            ).inc(relationships_created)
            
            logger.info(
                "relationships_buffer_flushed",
                rel_type=rel_type,
                buffer_size=len(buffer),
                relationships_created=relationships_created,
                duration_seconds=duration,
                trace_id=trace_id,
            )
            
            return {
                "relationships_created": relationships_created,
                "buffer_size": len(buffer),
                "duration_ms": duration * 1000,
            }
            
        except Exception as e:
            logger.error(
                "relationships_buffer_flush_failed",
                buffer_key=buffer_key,
                buffer_size=len(buffer),
                error=str(e),
                trace_id=trace_id,
            )
            raise LoadError(
                message=f"Failed to flush relationships buffer: {str(e)}",
                details={"buffer_key": buffer_key, "buffer_size": len(buffer)},
                trace_id=trace_id,
            ) from e

    def flush_all(self, trace_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Flush all buffers to Neo4j.
        
        Args:
            trace_id: Trace ID for correlation
            
        Returns:
            Flush summary
        """
        start_time = time.time()
        
        total_nodes = 0
        total_relationships = 0
        
        # Flush all node buffers
        for node_label in list(self.node_buffers.keys()):
            result = self.flush_nodes(node_label, trace_id=trace_id)
            total_nodes += result["nodes_created"]
        
        # Flush all relationship buffers
        for buffer_key in list(self.relationship_buffers.keys()):
            result = self.flush_relationships(buffer_key, trace_id=trace_id)
            total_relationships += result["relationships_created"]
        
        duration = time.time() - start_time
        self.last_flush_time = time.time()

        # Only log at INFO level when there's actual data to flush
        if total_nodes > 0 or total_relationships > 0:
            logger.info(
                "all_buffers_flushed",
                total_nodes=total_nodes,
                total_relationships=total_relationships,
                duration_seconds=duration,
                trace_id=trace_id,
            )
        else:
            # Use DEBUG level for empty flushes to avoid log clutter
            logger.debug(
                "all_buffers_flushed_empty",
                trace_id=trace_id,
            )

        return {
            "nodes_created": total_nodes,
            "relationships_created": total_relationships,
            "duration_ms": duration * 1000,
        }

    def should_flush(self) -> bool:
        """
        Check if buffers should be flushed based on time interval.
        
        Returns:
            True if flush interval has elapsed
        """
        return (time.time() - self.last_flush_time) >= self.flush_interval


# Global stream loader instance
stream_loader = StreamLoader()

