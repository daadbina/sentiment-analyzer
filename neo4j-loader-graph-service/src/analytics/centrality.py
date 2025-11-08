"""
Centrality computation for graph analytics.
Computes degree, betweenness, and closeness centrality.
"""

from typing import Dict, Any, List, Optional
import time
import structlog

from ..clients.neo4j_client import neo4j_client
from ..exceptions import QueryError
from ..metrics import (
    graph_centrality_computation_duration_seconds,
    graph_analytics_nodes_processed,
)

logger = structlog.get_logger(__name__)


class CentralityComputer:
    """
    Computes centrality metrics for graph nodes.
    """

    def __init__(self):
        """Initialize centrality computer."""
        self.client = neo4j_client

    def compute_degree_centrality(
        self,
        node_label: str,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Compute degree centrality for nodes.
        
        Args:
            node_label: Node label to compute centrality for
            trace_id: Trace ID for correlation
            
        Returns:
            Computation summary
        """
        start_time = time.time()
        
        try:
            # Query to compute degree centrality
            query = f"""
            MATCH (n:{node_label})
            OPTIONAL MATCH (n)-[r]-()
            WITH n, count(r) as degree
            SET n.degree_centrality = degree
            RETURN count(n) as nodes_processed, avg(degree) as avg_degree
            """
            
            result = self.client.execute_query(query, trace_id=trace_id)
            
            duration = time.time() - start_time
            
            # Record metrics
            graph_centrality_computation_duration_seconds.labels(
                centrality_type="degree",
                node_label=node_label,
            ).observe(duration)
            
            nodes_processed = result.get("nodes_processed", 0)
            graph_analytics_nodes_processed.labels(
                analytics_type="degree_centrality",
                node_label=node_label,
            ).inc(nodes_processed)
            
            logger.info(
                "degree_centrality_computed",
                node_label=node_label,
                nodes_processed=nodes_processed,
                avg_degree=result.get("avg_degree", 0),
                duration_seconds=duration,
                trace_id=trace_id,
            )
            
            return {
                "nodes_processed": nodes_processed,
                "avg_degree": result.get("avg_degree", 0),
                "duration_ms": duration * 1000,
            }
            
        except Exception as e:
            logger.error(
                "degree_centrality_computation_failed",
                node_label=node_label,
                error=str(e),
                trace_id=trace_id,
            )
            raise QueryError(
                message=f"Failed to compute degree centrality: {str(e)}",
                query_type="centrality_computation",
                details={"node_label": node_label},
                trace_id=trace_id,
            ) from e

    def compute_betweenness_centrality(
        self,
        node_label: str,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Compute betweenness centrality using Neo4j GDS.
        
        Args:
            node_label: Node label to compute centrality for
            trace_id: Trace ID for correlation
            
        Returns:
            Computation summary
        """
        start_time = time.time()
        
        try:
            # Create graph projection
            projection_query = f"""
            CALL gds.graph.project(
                'betweenness-graph-{node_label}',
                '{node_label}',
                '*'
            )
            YIELD graphName, nodeCount, relationshipCount
            RETURN graphName, nodeCount, relationshipCount
            """
            
            projection_result = self.client.execute_query(
                projection_query,
                trace_id=trace_id,
            )
            
            # Compute betweenness centrality
            compute_query = f"""
            CALL gds.betweenness.write(
                'betweenness-graph-{node_label}',
                {{
                    writeProperty: 'betweenness_centrality'
                }}
            )
            YIELD nodePropertiesWritten, computeMillis
            RETURN nodePropertiesWritten, computeMillis
            """
            
            compute_result = self.client.execute_query(
                compute_query,
                trace_id=trace_id,
            )
            
            # Drop graph projection
            drop_query = f"""
            CALL gds.graph.drop('betweenness-graph-{node_label}')
            YIELD graphName
            RETURN graphName
            """
            
            self.client.execute_query(drop_query, trace_id=trace_id)
            
            duration = time.time() - start_time
            
            # Record metrics
            graph_centrality_computation_duration_seconds.labels(
                centrality_type="betweenness",
                node_label=node_label,
            ).observe(duration)
            
            nodes_processed = compute_result.get("nodePropertiesWritten", 0)
            graph_analytics_nodes_processed.labels(
                analytics_type="betweenness_centrality",
                node_label=node_label,
            ).inc(nodes_processed)
            
            logger.info(
                "betweenness_centrality_computed",
                node_label=node_label,
                nodes_processed=nodes_processed,
                duration_seconds=duration,
                trace_id=trace_id,
            )
            
            return {
                "nodes_processed": nodes_processed,
                "duration_ms": duration * 1000,
            }
            
        except Exception as e:
            logger.error(
                "betweenness_centrality_computation_failed",
                node_label=node_label,
                error=str(e),
                trace_id=trace_id,
            )
            raise QueryError(
                message=f"Failed to compute betweenness centrality: {str(e)}",
                query_type="centrality_computation",
                details={"node_label": node_label},
                trace_id=trace_id,
            ) from e

    def compute_closeness_centrality(
        self,
        node_label: str,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Compute closeness centrality using Neo4j GDS.
        
        Args:
            node_label: Node label to compute centrality for
            trace_id: Trace ID for correlation
            
        Returns:
            Computation summary
        """
        start_time = time.time()
        
        try:
            # Create graph projection
            projection_query = f"""
            CALL gds.graph.project(
                'closeness-graph-{node_label}',
                '{node_label}',
                '*'
            )
            YIELD graphName, nodeCount, relationshipCount
            RETURN graphName, nodeCount, relationshipCount
            """
            
            projection_result = self.client.execute_query(
                projection_query,
                trace_id=trace_id,
            )
            
            # Compute closeness centrality
            compute_query = f"""
            CALL gds.closeness.write(
                'closeness-graph-{node_label}',
                {{
                    writeProperty: 'closeness_centrality'
                }}
            )
            YIELD nodePropertiesWritten, computeMillis
            RETURN nodePropertiesWritten, computeMillis
            """
            
            compute_result = self.client.execute_query(
                compute_query,
                trace_id=trace_id,
            )
            
            # Drop graph projection
            drop_query = f"""
            CALL gds.graph.drop('closeness-graph-{node_label}')
            YIELD graphName
            RETURN graphName
            """
            
            self.client.execute_query(drop_query, trace_id=trace_id)
            
            duration = time.time() - start_time
            
            # Record metrics
            graph_centrality_computation_duration_seconds.labels(
                centrality_type="closeness",
                node_label=node_label,
            ).observe(duration)
            
            nodes_processed = compute_result.get("nodePropertiesWritten", 0)
            graph_analytics_nodes_processed.labels(
                analytics_type="closeness_centrality",
                node_label=node_label,
            ).inc(nodes_processed)
            
            logger.info(
                "closeness_centrality_computed",
                node_label=node_label,
                nodes_processed=nodes_processed,
                duration_seconds=duration,
                trace_id=trace_id,
            )
            
            return {
                "nodes_processed": nodes_processed,
                "duration_ms": duration * 1000,
            }
            
        except Exception as e:
            logger.error(
                "closeness_centrality_computation_failed",
                node_label=node_label,
                error=str(e),
                trace_id=trace_id,
            )
            raise QueryError(
                message=f"Failed to compute closeness centrality: {str(e)}",
                query_type="centrality_computation",
                details={"node_label": node_label},
                trace_id=trace_id,
            ) from e

    def compute_all_centrality_metrics(
        self,
        node_label: str,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Compute all centrality metrics for a node label.
        
        Args:
            node_label: Node label to compute centrality for
            trace_id: Trace ID for correlation
            
        Returns:
            Computation summary
        """
        start_time = time.time()
        
        degree_result = self.compute_degree_centrality(node_label, trace_id)
        betweenness_result = self.compute_betweenness_centrality(node_label, trace_id)
        closeness_result = self.compute_closeness_centrality(node_label, trace_id)
        
        duration = time.time() - start_time
        
        logger.info(
            "all_centrality_metrics_computed",
            node_label=node_label,
            duration_seconds=duration,
            trace_id=trace_id,
        )
        
        return {
            "degree": degree_result,
            "betweenness": betweenness_result,
            "closeness": closeness_result,
            "total_duration_ms": duration * 1000,
        }


# Global centrality computer instance
centrality_computer = CentralityComputer()

