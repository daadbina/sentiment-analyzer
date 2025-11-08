"""
Query repository for parameterized Cypher queries.
Provides reusable queries for common graph operations.
"""

from typing import Dict, Any, List, Optional
import time
import structlog

from ..clients.neo4j_client import neo4j_client
from ..exceptions import QueryError
from ..metrics import graph_query_latency_ms

logger = structlog.get_logger(__name__)


class QueryRepository:
    """
    Repository of parameterized Cypher queries.
    """

    def __init__(self):
        """Initialize query repository."""
        self.client = neo4j_client

    def get_article_by_id(
        self,
        article_id: str,
        trace_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get article by ID.
        
        Args:
            article_id: Article ID
            trace_id: Trace ID for correlation
            
        Returns:
            Article properties or None
        """
        start_time = time.time()
        
        try:
            query = """
            MATCH (a:Article {id: $article_id})
            RETURN a
            """
            
            result = self.client.execute_query(
                query,
                parameters={"article_id": article_id},
                trace_id=trace_id,
            )
            
            duration = (time.time() - start_time) * 1000
            graph_query_latency_ms.labels(query_type="get_article_by_id").observe(duration)
            
            return result.get("a") if result else None
            
        except Exception as e:
            logger.error(
                "get_article_by_id_failed",
                article_id=article_id,
                error=str(e),
                trace_id=trace_id,
            )
            raise QueryError(
                message=f"Failed to get article: {str(e)}",
                query_type="get_article_by_id",
                trace_id=trace_id,
            ) from e

    def get_articles_by_group(
        self,
        group_id: str,
        limit: int = 100,
        trace_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get articles belonging to a group.
        
        Args:
            group_id: Group ID
            limit: Maximum number of articles to return
            trace_id: Trace ID for correlation
            
        Returns:
            List of article properties
        """
        start_time = time.time()
        
        try:
            query = """
            MATCH (a:Article)-[:BELONGS_TO]->(g:Group {id: $group_id})
            RETURN a
            LIMIT $limit
            """
            
            results = self.client.execute_query(
                query,
                parameters={"group_id": group_id, "limit": limit},
                trace_id=trace_id,
            )
            
            duration = (time.time() - start_time) * 1000
            graph_query_latency_ms.labels(query_type="get_articles_by_group").observe(duration)
            
            # Convert to list
            if isinstance(results, list):
                return [r.get("a") for r in results if r.get("a")]
            elif isinstance(results, dict) and results.get("a"):
                return [results.get("a")]
            return []
            
        except Exception as e:
            logger.error(
                "get_articles_by_group_failed",
                group_id=group_id,
                error=str(e),
                trace_id=trace_id,
            )
            raise QueryError(
                message=f"Failed to get articles by group: {str(e)}",
                query_type="get_articles_by_group",
                trace_id=trace_id,
            ) from e

    def get_entities_by_article(
        self,
        article_id: str,
        trace_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get entities mentioned in an article.
        
        Args:
            article_id: Article ID
            trace_id: Trace ID for correlation
            
        Returns:
            List of entity properties with mention details
        """
        start_time = time.time()
        
        try:
            query = """
            MATCH (a:Article {id: $article_id})-[m:MENTIONS]->(e:Entity)
            RETURN e, m.frequency as frequency, m.confidence as confidence
            ORDER BY m.frequency DESC
            """
            
            results = self.client.execute_query(
                query,
                parameters={"article_id": article_id},
                trace_id=trace_id,
            )
            
            duration = (time.time() - start_time) * 1000
            graph_query_latency_ms.labels(query_type="get_entities_by_article").observe(duration)
            
            # Convert to list
            if isinstance(results, list):
                return results
            elif isinstance(results, dict):
                return [results]
            return []
            
        except Exception as e:
            logger.error(
                "get_entities_by_article_failed",
                article_id=article_id,
                error=str(e),
                trace_id=trace_id,
            )
            raise QueryError(
                message=f"Failed to get entities by article: {str(e)}",
                query_type="get_entities_by_article",
                trace_id=trace_id,
            ) from e

    def get_related_groups(
        self,
        group_id: str,
        min_similarity: float = 0.5,
        limit: int = 10,
        trace_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get groups related to a given group.
        
        Args:
            group_id: Group ID
            min_similarity: Minimum similarity score
            limit: Maximum number of groups to return
            trace_id: Trace ID for correlation
            
        Returns:
            List of related groups with similarity scores
        """
        start_time = time.time()
        
        try:
            query = """
            MATCH (g1:Group {id: $group_id})-[r:RELATED_TO]->(g2:Group)
            WHERE r.similarity_score >= $min_similarity
            RETURN g2, r.similarity_score as similarity
            ORDER BY r.similarity_score DESC
            LIMIT $limit
            """
            
            results = self.client.execute_query(
                query,
                parameters={
                    "group_id": group_id,
                    "min_similarity": min_similarity,
                    "limit": limit,
                },
                trace_id=trace_id,
            )
            
            duration = (time.time() - start_time) * 1000
            graph_query_latency_ms.labels(query_type="get_related_groups").observe(duration)
            
            # Convert to list
            if isinstance(results, list):
                return results
            elif isinstance(results, dict):
                return [results]
            return []
            
        except Exception as e:
            logger.error(
                "get_related_groups_failed",
                group_id=group_id,
                error=str(e),
                trace_id=trace_id,
            )
            raise QueryError(
                message=f"Failed to get related groups: {str(e)}",
                query_type="get_related_groups",
                trace_id=trace_id,
            ) from e

    def get_actors_by_group(
        self,
        group_id: str,
        trace_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get actors involved in a group.
        
        Args:
            group_id: Group ID
            trace_id: Trace ID for correlation
            
        Returns:
            List of actors with involvement details
        """
        start_time = time.time()
        
        try:
            query = """
            MATCH (g:Group {id: $group_id})-[i:INVOLVES]->(a:Actor)
            RETURN a, i.involvement_score as involvement_score, i.role as role
            ORDER BY i.involvement_score DESC
            """
            
            results = self.client.execute_query(
                query,
                parameters={"group_id": group_id},
                trace_id=trace_id,
            )
            
            duration = (time.time() - start_time) * 1000
            graph_query_latency_ms.labels(query_type="get_actors_by_group").observe(duration)
            
            # Convert to list
            if isinstance(results, list):
                return results
            elif isinstance(results, dict):
                return [results]
            return []
            
        except Exception as e:
            logger.error(
                "get_actors_by_group_failed",
                group_id=group_id,
                error=str(e),
                trace_id=trace_id,
            )
            raise QueryError(
                message=f"Failed to get actors by group: {str(e)}",
                query_type="get_actors_by_group",
                trace_id=trace_id,
            ) from e

    def get_predictions_by_group(
        self,
        group_id: str,
        domain: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get predictions for a group.
        
        Args:
            group_id: Group ID
            domain: Optional domain filter (btc, conflict, geopolitical)
            trace_id: Trace ID for correlation
            
        Returns:
            List of predictions
        """
        start_time = time.time()
        
        try:
            if domain:
                query = """
                MATCH (p:Prediction {domain: $domain})-[:PREDICTS]->(g:Group {id: $group_id})
                RETURN p
                ORDER BY p.probability DESC
                """
                parameters = {"group_id": group_id, "domain": domain}
            else:
                query = """
                MATCH (p:Prediction)-[:PREDICTS]->(g:Group {id: $group_id})
                RETURN p
                ORDER BY p.probability DESC
                """
                parameters = {"group_id": group_id}
            
            results = self.client.execute_query(
                query,
                parameters=parameters,
                trace_id=trace_id,
            )
            
            duration = (time.time() - start_time) * 1000
            graph_query_latency_ms.labels(query_type="get_predictions_by_group").observe(duration)
            
            # Convert to list
            if isinstance(results, list):
                return [r.get("p") for r in results if r.get("p")]
            elif isinstance(results, dict) and results.get("p"):
                return [results.get("p")]
            return []
            
        except Exception as e:
            logger.error(
                "get_predictions_by_group_failed",
                group_id=group_id,
                error=str(e),
                trace_id=trace_id,
            )
            raise QueryError(
                message=f"Failed to get predictions by group: {str(e)}",
                query_type="get_predictions_by_group",
                trace_id=trace_id,
            ) from e

    def get_graph_statistics(
        self,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get overall graph statistics.
        
        Args:
            trace_id: Trace ID for correlation
            
        Returns:
            Graph statistics
        """
        start_time = time.time()
        
        try:
            query = """
            MATCH (n)
            WITH labels(n) as labels, count(n) as node_count
            UNWIND labels as label
            WITH label, sum(node_count) as count
            RETURN collect({label: label, count: count}) as node_stats
            """
            
            node_result = self.client.execute_query(query, trace_id=trace_id)
            
            rel_query = """
            MATCH ()-[r]->()
            WITH type(r) as rel_type, count(r) as rel_count
            RETURN collect({type: rel_type, count: rel_count}) as rel_stats
            """
            
            rel_result = self.client.execute_query(rel_query, trace_id=trace_id)
            
            duration = (time.time() - start_time) * 1000
            graph_query_latency_ms.labels(query_type="get_graph_statistics").observe(duration)
            
            return {
                "nodes": node_result.get("node_stats", []),
                "relationships": rel_result.get("rel_stats", []),
                "query_duration_ms": duration,
            }
            
        except Exception as e:
            logger.error(
                "get_graph_statistics_failed",
                error=str(e),
                trace_id=trace_id,
            )
            raise QueryError(
                message=f"Failed to get graph statistics: {str(e)}",
                query_type="get_graph_statistics",
                trace_id=trace_id,
            ) from e


# Global query repository instance
query_repository = QueryRepository()

