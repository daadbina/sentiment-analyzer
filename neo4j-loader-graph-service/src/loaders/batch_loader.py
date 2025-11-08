"""
Batch loader for Neo4j graph.
Implements batch loading with UNWIND for high throughput.
"""

from typing import List, Dict, Any, Optional
import time
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
    graph_write_failures_total,
    batch_processing_size,
    batch_processing_duration_seconds,
)

logger = structlog.get_logger(__name__)


class BatchLoader:
    """
    Batch loader for Neo4j graph operations.
    Uses UNWIND for efficient batch inserts.
    """

    def __init__(self):
        """Initialize batch loader."""
        self.client = neo4j_client
        self.batch_size = config.batch_size

    def load_nodes_batch(
        self,
        node_label: str,
        nodes_data: List[Dict[str, Any]],
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Load a batch of nodes into Neo4j.
        
        Args:
            node_label: Node label (Article, Group, Entity, Actor, Prediction)
            nodes_data: List of node property dictionaries
            trace_id: Trace ID for correlation
            
        Returns:
            Batch load summary
            
        Raises:
            LoadError: If batch load fails
        """
        start_time = time.time()
        
        if not nodes_data:
            logger.warning("empty_nodes_batch", node_label=node_label)
            return {"nodes_created": 0, "duration_ms": 0}

        try:
            # Build batch query
            query, parameters = node_builder.build_batch_create_query(
                node_label=node_label,
                batch_data=nodes_data,
            )
            
            # Execute batch write
            result = self.client.execute_batch_write(
                query=query,
                batch_parameters=parameters["batch"],
                trace_id=trace_id,
            )
            
            # Record metrics
            duration = time.time() - start_time
            graph_load_duration_seconds.labels(
                operation_type="batch_nodes",
                batch_size=str(len(nodes_data)),
            ).observe(duration)
            
            batch_processing_size.labels(batch_type="nodes").observe(len(nodes_data))
            batch_processing_duration_seconds.labels(batch_type="nodes").observe(duration)
            
            # Record node creation
            nodes_created = result.get("nodes_created", 0)
            graph_nodes_created_total.labels(node_type=node_label).inc(nodes_created)
            
            logger.info(
                "nodes_batch_loaded",
                node_label=node_label,
                batch_size=len(nodes_data),
                nodes_created=nodes_created,
                duration_seconds=duration,
                trace_id=trace_id,
            )
            
            return {
                "nodes_created": nodes_created,
                "batch_size": len(nodes_data),
                "duration_ms": duration * 1000,
            }
            
        except Exception as e:
            graph_write_failures_total.labels(
                operation_type="batch_nodes",
                failure_reason="batch_write_error",
            ).inc()
            
            logger.error(
                "nodes_batch_load_failed",
                node_label=node_label,
                batch_size=len(nodes_data),
                error=str(e),
                trace_id=trace_id,
            )
            
            raise LoadError(
                message=f"Failed to load nodes batch: {str(e)}",
                batch_id=trace_id,
                details={
                    "node_label": node_label,
                    "batch_size": len(nodes_data),
                },
                trace_id=trace_id,
            ) from e

    def load_relationships_batch(
        self,
        from_label: str,
        to_label: str,
        rel_type: str,
        relationships_data: List[Dict[str, Any]],
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Load a batch of relationships into Neo4j.
        
        Args:
            from_label: Source node label
            to_label: Target node label
            rel_type: Relationship type
            relationships_data: List of relationship data
            trace_id: Trace ID for correlation
            
        Returns:
            Batch load summary
            
        Raises:
            LoadError: If batch load fails
        """
        start_time = time.time()
        
        if not relationships_data:
            logger.warning("empty_relationships_batch", rel_type=rel_type)
            return {"relationships_created": 0, "duration_ms": 0}

        try:
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
            
            # Record metrics
            duration = time.time() - start_time
            graph_load_duration_seconds.labels(
                operation_type="batch_relationships",
                batch_size=str(len(relationships_data)),
            ).observe(duration)
            
            batch_processing_size.labels(batch_type="relationships").observe(len(relationships_data))
            batch_processing_duration_seconds.labels(batch_type="relationships").observe(duration)
            
            # Record relationship creation
            relationships_created = result.get("relationships_created", 0)
            graph_relationships_created_total.labels(
                relationship_type=rel_type
            ).inc(relationships_created)
            
            logger.info(
                "relationships_batch_loaded",
                rel_type=rel_type,
                batch_size=len(relationships_data),
                relationships_created=relationships_created,
                duration_seconds=duration,
                trace_id=trace_id,
            )
            
            return {
                "relationships_created": relationships_created,
                "batch_size": len(relationships_data),
                "duration_ms": duration * 1000,
            }
            
        except Exception as e:
            graph_write_failures_total.labels(
                operation_type="batch_relationships",
                failure_reason="batch_write_error",
            ).inc()
            
            logger.error(
                "relationships_batch_load_failed",
                rel_type=rel_type,
                batch_size=len(relationships_data),
                error=str(e),
                trace_id=trace_id,
            )
            
            raise LoadError(
                message=f"Failed to load relationships batch: {str(e)}",
                batch_id=trace_id,
                details={
                    "rel_type": rel_type,
                    "batch_size": len(relationships_data),
                },
                trace_id=trace_id,
            ) from e

    def load_articles_with_relationships(
        self,
        articles_data: List[Dict[str, Any]],
        groups_mapping: Dict[str, str],
        entities_mapping: Dict[str, List[str]],
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Load articles with their relationships (BELONGS_TO, MENTIONS).
        
        Args:
            articles_data: List of article property dictionaries
            groups_mapping: Mapping of article_id -> group_id
            entities_mapping: Mapping of article_id -> list of entity_ids
            trace_id: Trace ID for correlation
            
        Returns:
            Load summary
        """
        start_time = time.time()
        
        try:
            # Load articles
            articles_result = self.load_nodes_batch(
                node_label="Article",
                nodes_data=articles_data,
                trace_id=trace_id,
            )
            
            # Build BELONGS_TO relationships
            belongs_to_data = []
            for article_id, group_id in groups_mapping.items():
                belongs_to_data.append({
                    "from_id": article_id,
                    "to_id": group_id,
                    "properties": {"membership_score": 1.0},
                })
            
            # Load BELONGS_TO relationships
            belongs_to_result = self.load_relationships_batch(
                from_label="Article",
                to_label="Group",
                rel_type="BELONGS_TO",
                relationships_data=belongs_to_data,
                trace_id=trace_id,
            )
            
            # Build MENTIONS relationships
            mentions_data = []
            for article_id, entity_ids in entities_mapping.items():
                for entity_id in entity_ids:
                    mentions_data.append({
                        "from_id": article_id,
                        "to_id": entity_id,
                        "properties": {"frequency": 1, "confidence": 1.0},
                    })
            
            # Load MENTIONS relationships
            mentions_result = self.load_relationships_batch(
                from_label="Article",
                to_label="Entity",
                rel_type="MENTIONS",
                relationships_data=mentions_data,
                trace_id=trace_id,
            )
            
            duration = time.time() - start_time
            
            logger.info(
                "articles_with_relationships_loaded",
                articles_count=articles_result["nodes_created"],
                belongs_to_count=belongs_to_result["relationships_created"],
                mentions_count=mentions_result["relationships_created"],
                duration_seconds=duration,
                trace_id=trace_id,
            )
            
            return {
                "articles_created": articles_result["nodes_created"],
                "belongs_to_created": belongs_to_result["relationships_created"],
                "mentions_created": mentions_result["relationships_created"],
                "duration_ms": duration * 1000,
            }
            
        except Exception as e:
            logger.error(
                "articles_with_relationships_load_failed",
                error=str(e),
                trace_id=trace_id,
            )
            raise


# Global batch loader instance
batch_loader = BatchLoader()

