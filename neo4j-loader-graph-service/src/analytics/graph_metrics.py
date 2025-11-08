"""
Graph metrics calculator for Neo4j Loader Graph Service.
Computes global graph metrics like node counts, relationship counts, density, etc.
"""

from typing import Dict, Any, Optional
import structlog
import time

from ..clients.neo4j_client import neo4j_client
from ..exceptions import QueryError
from ..metrics import graph_analytics_duration_seconds

logger = structlog.get_logger(__name__)


class GraphMetricsCalculator:
    """
    Calculator for global graph metrics.
    
    Computes metrics like:
    - Node counts by label
    - Relationship counts by type
    - Graph density
    - Average degree
    - Connected components
    """

    def __init__(self):
        """Initialize graph metrics calculator."""
        self.neo4j_client = neo4j_client

    def compute_all_metrics(
        self,
        node_label: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Compute all graph metrics.
        
        Args:
            node_label: Optional node label to filter by
            trace_id: Trace ID for correlation
            
        Returns:
            Dictionary of all metrics
            
        Raises:
            QueryError: If metric computation fails
        """
        start_time = time.time()
        
        try:
            logger.info(
                "graph_metrics_computation_started",
                node_label=node_label,
                trace_id=trace_id,
            )
            
            # Compute node counts
            node_counts = self._compute_node_counts(trace_id)
            
            # Compute relationship counts
            relationship_counts = self._compute_relationship_counts(trace_id)
            
            # Compute graph density
            density = self._compute_density(
                total_nodes=node_counts.get("_total", 0),
                total_relationships=relationship_counts.get("_total", 0),
            )
            
            # Compute average degree
            avg_degree = self._compute_average_degree(
                total_nodes=node_counts.get("_total", 0),
                total_relationships=relationship_counts.get("_total", 0),
            )
            
            metrics = {
                "node_counts": node_counts,
                "relationship_counts": relationship_counts,
                "density": density,
                "average_degree": avg_degree,
                "timestamp": time.time(),
            }
            
            duration = time.time() - start_time
            
            graph_analytics_duration_seconds.labels(
                analytics_type="graph_metrics",
            ).observe(duration)
            
            logger.info(
                "graph_metrics_computed",
                total_nodes=node_counts.get("_total", 0),
                total_relationships=relationship_counts.get("_total", 0),
                density=density,
                average_degree=avg_degree,
                duration_seconds=duration,
                trace_id=trace_id,
            )
            
            return metrics
            
        except Exception as e:
            logger.error(
                "graph_metrics_computation_failed",
                error=str(e),
                trace_id=trace_id,
            )
            raise QueryError(
                message=f"Failed to compute graph metrics: {str(e)}",
                query="graph_metrics_computation",
                details={"error": str(e)},
            ) from e

    def _compute_node_counts(
        self,
        trace_id: Optional[str] = None,
    ) -> Dict[str, int]:
        """
        Compute node counts by label.
        
        Args:
            trace_id: Trace ID for correlation
            
        Returns:
            Dictionary of node counts by label
        """
        query = """
        MATCH (n)
        RETURN labels(n)[0] AS label, count(n) AS count
        """
        
        results = self.neo4j_client.execute_query(query, trace_id=trace_id)
        
        node_counts = {}
        total = 0
        
        for record in results:
            label = record.get("label", "Unknown")
            count = record.get("count", 0)
            node_counts[label] = count
            total += count
        
        node_counts["_total"] = total
        
        logger.debug(
            "node_counts_computed",
            total_nodes=total,
            label_count=len(node_counts) - 1,
            trace_id=trace_id,
        )
        
        return node_counts

    def _compute_relationship_counts(
        self,
        trace_id: Optional[str] = None,
    ) -> Dict[str, int]:
        """
        Compute relationship counts by type.
        
        Args:
            trace_id: Trace ID for correlation
            
        Returns:
            Dictionary of relationship counts by type
        """
        query = """
        MATCH ()-[r]->()
        RETURN type(r) AS type, count(r) AS count
        """
        
        results = self.neo4j_client.execute_query(query, trace_id=trace_id)
        
        relationship_counts = {}
        total = 0
        
        for record in results:
            rel_type = record.get("type", "Unknown")
            count = record.get("count", 0)
            relationship_counts[rel_type] = count
            total += count
        
        relationship_counts["_total"] = total
        
        logger.debug(
            "relationship_counts_computed",
            total_relationships=total,
            type_count=len(relationship_counts) - 1,
            trace_id=trace_id,
        )
        
        return relationship_counts

    def _compute_density(
        self,
        total_nodes: int,
        total_relationships: int,
    ) -> float:
        """
        Compute graph density.
        
        Density = actual_edges / possible_edges
        For directed graph: possible_edges = n * (n - 1)
        
        Args:
            total_nodes: Total number of nodes
            total_relationships: Total number of relationships
            
        Returns:
            Graph density (0.0 to 1.0)
        """
        if total_nodes < 2:
            return 0.0
        
        possible_edges = total_nodes * (total_nodes - 1)
        density = total_relationships / possible_edges if possible_edges > 0 else 0.0
        
        return round(density, 6)

    def _compute_average_degree(
        self,
        total_nodes: int,
        total_relationships: int,
    ) -> float:
        """
        Compute average node degree.
        
        Average degree = 2 * edges / nodes (for undirected)
        For directed: Average degree = edges / nodes
        
        Args:
            total_nodes: Total number of nodes
            total_relationships: Total number of relationships
            
        Returns:
            Average degree
        """
        if total_nodes == 0:
            return 0.0
        
        # For directed graph
        avg_degree = total_relationships / total_nodes
        
        return round(avg_degree, 2)

    def compute_connected_components(
        self,
        trace_id: Optional[str] = None,
    ) -> int:
        """
        Compute number of connected components.
        
        Args:
            trace_id: Trace ID for correlation
            
        Returns:
            Number of connected components
        """
        query = """
        CALL gds.wcc.stats('graph')
        YIELD componentCount
        RETURN componentCount
        """
        
        try:
            results = self.neo4j_client.execute_query(query, trace_id=trace_id)
            
            if results:
                component_count = results[0].get("componentCount", 0)
                
                logger.debug(
                    "connected_components_computed",
                    component_count=component_count,
                    trace_id=trace_id,
                )
                
                return component_count
            
            return 0
            
        except Exception as e:
            logger.warning(
                "connected_components_computation_failed",
                error=str(e),
                trace_id=trace_id,
            )
            return 0


# Global graph metrics calculator instance
graph_metrics_calculator = GraphMetricsCalculator()

