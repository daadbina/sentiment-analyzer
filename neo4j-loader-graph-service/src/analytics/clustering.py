"""
Clustering detection for graph analytics.
Implements Louvain community detection algorithm.
"""

from typing import Dict, Any, List, Optional
import time
import structlog

from ..clients.neo4j_client import neo4j_client
from ..exceptions import QueryError
from ..metrics import (
    graph_clustering_detection_duration_seconds,
    graph_analytics_nodes_processed,
    graph_clusters_detected,
)

logger = structlog.get_logger(__name__)


class ClusteringDetector:
    """
    Detects clusters/communities in the graph using Louvain algorithm.
    """

    def __init__(self):
        """Initialize clustering detector."""
        self.client = neo4j_client

    def detect_communities_louvain(
        self,
        node_label: str,
        relationship_type: str = "*",
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Detect communities using Louvain algorithm.
        
        Args:
            node_label: Node label to detect communities for
            relationship_type: Relationship type to consider
            trace_id: Trace ID for correlation
            
        Returns:
            Detection summary
        """
        start_time = time.time()
        
        try:
            # Create graph projection
            projection_query = f"""
            CALL gds.graph.project(
                'louvain-graph-{node_label}',
                '{node_label}',
                '{relationship_type}'
            )
            YIELD graphName, nodeCount, relationshipCount
            RETURN graphName, nodeCount, relationshipCount
            """
            
            projection_result = self.client.execute_query(
                projection_query,
                trace_id=trace_id,
            )
            
            # Run Louvain algorithm
            louvain_query = f"""
            CALL gds.louvain.write(
                'louvain-graph-{node_label}',
                {{
                    writeProperty: 'community_id',
                    includeIntermediateCommunities: true
                }}
            )
            YIELD nodePropertiesWritten, communityCount, modularity, computeMillis
            RETURN nodePropertiesWritten, communityCount, modularity, computeMillis
            """
            
            louvain_result = self.client.execute_query(
                louvain_query,
                trace_id=trace_id,
            )
            
            # Drop graph projection
            drop_query = f"""
            CALL gds.graph.drop('louvain-graph-{node_label}')
            YIELD graphName
            RETURN graphName
            """
            
            self.client.execute_query(drop_query, trace_id=trace_id)
            
            duration = time.time() - start_time
            
            # Record metrics
            graph_clustering_detection_duration_seconds.labels(
                clustering_algorithm="louvain",
                node_label=node_label,
            ).observe(duration)
            
            nodes_processed = louvain_result.get("nodePropertiesWritten", 0)
            community_count = louvain_result.get("communityCount", 0)
            
            graph_analytics_nodes_processed.labels(
                analytics_type="louvain_clustering",
                node_label=node_label,
            ).inc(nodes_processed)
            
            graph_clusters_detected.labels(
                clustering_algorithm="louvain",
                node_label=node_label,
            ).set(community_count)
            
            logger.info(
                "louvain_communities_detected",
                node_label=node_label,
                nodes_processed=nodes_processed,
                community_count=community_count,
                modularity=louvain_result.get("modularity", 0),
                duration_seconds=duration,
                trace_id=trace_id,
            )
            
            return {
                "nodes_processed": nodes_processed,
                "community_count": community_count,
                "modularity": louvain_result.get("modularity", 0),
                "duration_ms": duration * 1000,
            }
            
        except Exception as e:
            logger.error(
                "louvain_clustering_failed",
                node_label=node_label,
                error=str(e),
                trace_id=trace_id,
            )
            raise QueryError(
                message=f"Failed to detect communities: {str(e)}",
                query_type="clustering_detection",
                details={"node_label": node_label},
                trace_id=trace_id,
            ) from e

    def get_community_statistics(
        self,
        node_label: str,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get statistics about detected communities.
        
        Args:
            node_label: Node label to get statistics for
            trace_id: Trace ID for correlation
            
        Returns:
            Community statistics
        """
        try:
            query = f"""
            MATCH (n:{node_label})
            WHERE n.community_id IS NOT NULL
            WITH n.community_id as community, count(n) as size
            RETURN 
                count(community) as total_communities,
                avg(size) as avg_community_size,
                max(size) as max_community_size,
                min(size) as min_community_size
            """
            
            result = self.client.execute_query(query, trace_id=trace_id)
            
            logger.info(
                "community_statistics_retrieved",
                node_label=node_label,
                total_communities=result.get("total_communities", 0),
                avg_size=result.get("avg_community_size", 0),
                trace_id=trace_id,
            )
            
            return {
                "total_communities": result.get("total_communities", 0),
                "avg_community_size": result.get("avg_community_size", 0),
                "max_community_size": result.get("max_community_size", 0),
                "min_community_size": result.get("min_community_size", 0),
            }
            
        except Exception as e:
            logger.error(
                "community_statistics_retrieval_failed",
                node_label=node_label,
                error=str(e),
                trace_id=trace_id,
            )
            raise QueryError(
                message=f"Failed to get community statistics: {str(e)}",
                query_type="community_statistics",
                details={"node_label": node_label},
                trace_id=trace_id,
            ) from e

    def get_top_communities(
        self,
        node_label: str,
        limit: int = 10,
        trace_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get top N communities by size.
        
        Args:
            node_label: Node label to get communities for
            limit: Number of top communities to return
            trace_id: Trace ID for correlation
            
        Returns:
            List of top communities
        """
        try:
            query = f"""
            MATCH (n:{node_label})
            WHERE n.community_id IS NOT NULL
            WITH n.community_id as community, count(n) as size
            ORDER BY size DESC
            LIMIT $limit
            RETURN community, size
            """
            
            results = self.client.execute_query(
                query,
                parameters={"limit": limit},
                trace_id=trace_id,
            )
            
            # Convert to list of dicts
            communities = []
            if isinstance(results, list):
                communities = results
            elif isinstance(results, dict):
                communities = [results]
            
            logger.info(
                "top_communities_retrieved",
                node_label=node_label,
                community_count=len(communities),
                trace_id=trace_id,
            )
            
            return communities
            
        except Exception as e:
            logger.error(
                "top_communities_retrieval_failed",
                node_label=node_label,
                error=str(e),
                trace_id=trace_id,
            )
            raise QueryError(
                message=f"Failed to get top communities: {str(e)}",
                query_type="top_communities",
                details={"node_label": node_label},
                trace_id=trace_id,
            ) from e

    def detect_and_analyze_communities(
        self,
        node_label: str,
        relationship_type: str = "*",
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Detect communities and analyze them.
        
        Args:
            node_label: Node label to analyze
            relationship_type: Relationship type to consider
            trace_id: Trace ID for correlation
            
        Returns:
            Complete analysis summary
        """
        start_time = time.time()
        
        # Detect communities
        detection_result = self.detect_communities_louvain(
            node_label=node_label,
            relationship_type=relationship_type,
            trace_id=trace_id,
        )
        
        # Get statistics
        statistics = self.get_community_statistics(
            node_label=node_label,
            trace_id=trace_id,
        )
        
        # Get top communities
        top_communities = self.get_top_communities(
            node_label=node_label,
            limit=10,
            trace_id=trace_id,
        )
        
        duration = time.time() - start_time
        
        logger.info(
            "communities_detected_and_analyzed",
            node_label=node_label,
            duration_seconds=duration,
            trace_id=trace_id,
        )
        
        return {
            "detection": detection_result,
            "statistics": statistics,
            "top_communities": top_communities,
            "total_duration_ms": duration * 1000,
        }


# Global clustering detector instance
clustering_detector = ClusteringDetector()

