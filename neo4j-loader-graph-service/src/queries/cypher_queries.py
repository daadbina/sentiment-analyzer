"""
Cypher query templates for Neo4j graph operations.
Provides parameterized queries for common graph operations.
"""

from typing import Dict, Any, List, Optional


class CypherQueries:
    """
    Collection of parameterized Cypher query templates.
    """

    # Origin Tracing Queries
    
    @staticmethod
    def get_earliest_article_in_group(group_id: str) -> tuple[str, Dict[str, Any]]:
        """
        Get the earliest article in a semantic group by published_at timestamp.
        
        Args:
            group_id: Group ID
            
        Returns:
            Tuple of (query, parameters)
        """
        query = """
        MATCH (a:Article)-[:BELONGS_TO]->(g:Group {id: $group_id})
        RETURN a
        ORDER BY a.published_at ASC
        LIMIT 1
        """
        
        params = {"group_id": group_id}
        return query, params

    @staticmethod
    def get_article_propagation_path(article_id: str) -> tuple[str, Dict[str, Any]]:
        """
        Get propagation path of an article through groups.
        
        Args:
            article_id: Article ID
            
        Returns:
            Tuple of (query, parameters)
        """
        query = """
        MATCH path = (a:Article {id: $article_id})-[:BELONGS_TO]->(g:Group)-[:RELATED_TO*0..3]->(related:Group)
        RETURN path, length(path) as path_length
        ORDER BY path_length ASC
        """
        
        params = {"article_id": article_id}
        return query, params

    # Network Analysis Queries
    
    @staticmethod
    def get_shortest_path_between_entities(
        entity_id_1: str,
        entity_id_2: str,
        max_hops: int = 5,
    ) -> tuple[str, Dict[str, Any]]:
        """
        Find shortest path between two entities.
        
        Args:
            entity_id_1: First entity ID
            entity_id_2: Second entity ID
            max_hops: Maximum path length
            
        Returns:
            Tuple of (query, parameters)
        """
        query = f"""
        MATCH path = shortestPath(
            (e1:Entity {{id: $entity_id_1}})-[*1..{max_hops}]-(e2:Entity {{id: $entity_id_2}})
        )
        RETURN path, length(path) as path_length
        """
        
        params = {
            "entity_id_1": entity_id_1,
            "entity_id_2": entity_id_2,
        }
        return query, params

    @staticmethod
    def get_influential_actors(limit: int = 10) -> tuple[str, Dict[str, Any]]:
        """
        Get most influential actors by degree centrality.
        
        Args:
            limit: Number of actors to return
            
        Returns:
            Tuple of (query, parameters)
        """
        query = """
        MATCH (actor:Actor)
        WHERE actor.degree_centrality IS NOT NULL
        RETURN actor
        ORDER BY actor.degree_centrality DESC
        LIMIT $limit
        """
        
        params = {"limit": limit}
        return query, params

    @staticmethod
    def get_entity_co_occurrence_network(
        entity_id: str,
        min_co_occurrences: int = 2,
    ) -> tuple[str, Dict[str, Any]]:
        """
        Get entities that co-occur with a given entity in articles.
        
        Args:
            entity_id: Entity ID
            min_co_occurrences: Minimum co-occurrence count
            
        Returns:
            Tuple of (query, parameters)
        """
        query = """
        MATCH (e1:Entity {id: $entity_id})<-[:MENTIONS]-(a:Article)-[:MENTIONS]->(e2:Entity)
        WHERE e1 <> e2
        WITH e2, count(a) as co_occurrences
        WHERE co_occurrences >= $min_co_occurrences
        RETURN e2, co_occurrences
        ORDER BY co_occurrences DESC
        """
        
        params = {
            "entity_id": entity_id,
            "min_co_occurrences": min_co_occurrences,
        }
        return query, params

    # Temporal Queries
    
    @staticmethod
    def get_articles_in_time_window(
        start_time: str,
        end_time: str,
        domain: Optional[str] = None,
    ) -> tuple[str, Dict[str, Any]]:
        """
        Get articles published within a time window.
        
        Args:
            start_time: Start timestamp (ISO format)
            end_time: End timestamp (ISO format)
            domain: Optional domain filter
            
        Returns:
            Tuple of (query, parameters)
        """
        if domain:
            query = """
            MATCH (a:Article)
            WHERE a.published_at >= datetime($start_time)
              AND a.published_at <= datetime($end_time)
              AND a.domain = $domain
            RETURN a
            ORDER BY a.published_at ASC
            """
            params = {
                "start_time": start_time,
                "end_time": end_time,
                "domain": domain,
            }
        else:
            query = """
            MATCH (a:Article)
            WHERE a.published_at >= datetime($start_time)
              AND a.published_at <= datetime($end_time)
            RETURN a
            ORDER BY a.published_at ASC
            """
            params = {
                "start_time": start_time,
                "end_time": end_time,
            }
        
        return query, params

    @staticmethod
    def get_temporal_entity_evolution(
        entity_id: str,
        time_window_hours: int = 24,
    ) -> tuple[str, Dict[str, Any]]:
        """
        Track how an entity appears over time.
        
        Args:
            entity_id: Entity ID
            time_window_hours: Time window in hours
            
        Returns:
            Tuple of (query, parameters)
        """
        query = """
        MATCH (e:Entity {id: $entity_id})<-[:MENTIONS]-(a:Article)
        WHERE a.published_at >= datetime() - duration({hours: $time_window_hours})
        WITH a, e
        ORDER BY a.published_at ASC
        RETURN a.published_at as timestamp, count(a) as mention_count
        """
        
        params = {
            "entity_id": entity_id,
            "time_window_hours": time_window_hours,
        }
        return query, params

    # Prediction Queries
    
    @staticmethod
    def get_predictions_for_group(group_id: str) -> tuple[str, Dict[str, Any]]:
        """
        Get all predictions for a semantic group.
        
        Args:
            group_id: Group ID
            
        Returns:
            Tuple of (query, parameters)
        """
        query = """
        MATCH (p:Prediction)-[:PREDICTS]->(g:Group {id: $group_id})
        RETURN p
        ORDER BY p.predicted_at DESC
        """
        
        params = {"group_id": group_id}
        return query, params

    @staticmethod
    def get_high_confidence_predictions(
        domain: str,
        min_confidence: float = 0.8,
        limit: int = 100,
    ) -> tuple[str, Dict[str, Any]]:
        """
        Get high-confidence predictions for a domain.
        
        Args:
            domain: Domain (politics, finance, crypto)
            min_confidence: Minimum confidence threshold
            limit: Maximum number of predictions
            
        Returns:
            Tuple of (query, parameters)
        """
        query = """
        MATCH (p:Prediction)-[:PREDICTS]->(g:Group)
        WHERE p.domain = $domain
          AND p.confidence >= $min_confidence
        RETURN p, g
        ORDER BY p.confidence DESC, p.predicted_at DESC
        LIMIT $limit
        """
        
        params = {
            "domain": domain,
            "min_confidence": min_confidence,
            "limit": limit,
        }
        return query, params

    # Community Queries
    
    @staticmethod
    def get_nodes_in_community(community_id: int) -> tuple[str, Dict[str, Any]]:
        """
        Get all nodes in a community.
        
        Args:
            community_id: Community ID
            
        Returns:
            Tuple of (query, parameters)
        """
        query = """
        MATCH (n)-[:BELONGS_TO_COMMUNITY]->(c:Community {id: $community_id})
        RETURN n, labels(n) as node_labels
        """
        
        params = {"community_id": community_id}
        return query, params

    @staticmethod
    def get_community_statistics() -> tuple[str, Dict[str, Any]]:
        """
        Get statistics about communities.
        
        Returns:
            Tuple of (query, parameters)
        """
        query = """
        MATCH (c:Community)<-[:BELONGS_TO_COMMUNITY]-(n)
        WITH c, count(n) as member_count
        RETURN 
            c.id as community_id,
            member_count,
            avg(member_count) as avg_community_size,
            max(member_count) as max_community_size,
            min(member_count) as min_community_size
        ORDER BY member_count DESC
        """
        
        params = {}
        return query, params

    # Graph Statistics Queries
    
    @staticmethod
    def get_node_degree_distribution() -> tuple[str, Dict[str, Any]]:
        """
        Get degree distribution of nodes.
        
        Returns:
            Tuple of (query, parameters)
        """
        query = """
        MATCH (n)
        WITH n, size((n)--()) as degree
        RETURN degree, count(n) as node_count
        ORDER BY degree ASC
        """
        
        params = {}
        return query, params

    @staticmethod
    def get_relationship_type_distribution() -> tuple[str, Dict[str, Any]]:
        """
        Get distribution of relationship types.
        
        Returns:
            Tuple of (query, parameters)
        """
        query = """
        MATCH ()-[r]->()
        RETURN type(r) as relationship_type, count(r) as count
        ORDER BY count DESC
        """
        
        params = {}
        return query, params


# Global query templates instance
cypher_queries = CypherQueries()

