"""
Orphan node detector for Neo4j graph.
Detects and optionally repairs orphaned nodes without relationships.
"""

from typing import Dict, Any, List, Optional
import structlog

from ..clients.neo4j_client import neo4j_client
from ..exceptions import ValidationError
from ..metrics import graph_validation_orphans_detected_total

logger = structlog.get_logger(__name__)


class OrphanDetector:
    """
    Detector for orphaned nodes in the graph.
    """

    def __init__(self):
        """Initialize orphan detector."""
        self.client = neo4j_client

    def detect_orphan_nodes(
        self,
        node_label: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Detect nodes without any relationships.
        
        Args:
            node_label: Node label to check (None = all nodes)
            trace_id: Trace ID for correlation
            
        Returns:
            List of orphaned nodes
        """
        try:
            if node_label:
                query = f"""
                MATCH (n:{node_label})
                WHERE NOT (n)--()
                RETURN n, labels(n) as node_labels, id(n) as internal_id
                LIMIT 1000
                """
            else:
                query = """
                MATCH (n)
                WHERE NOT (n)--()
                RETURN n, labels(n) as node_labels, id(n) as internal_id
                LIMIT 1000
                """
            
            result = self.client.execute_query(query, {}, trace_id=trace_id)
            
            orphans = []
            for record in result:
                node = record.get("n", {})
                node_labels = record.get("node_labels", [])
                internal_id = record.get("internal_id")
                
                orphans.append({
                    "node": node,
                    "labels": node_labels,
                    "internal_id": internal_id,
                })
            
            # Record metrics
            graph_validation_orphans_detected_total.inc(len(orphans))
            
            logger.info(
                "orphan_nodes_detected",
                node_label=node_label or "all",
                orphan_count=len(orphans),
                trace_id=trace_id,
            )
            
            return orphans
            
        except Exception as e:
            logger.error(
                "orphan_detection_failed",
                node_label=node_label,
                error=str(e),
                trace_id=trace_id,
            )
            raise ValidationError(
                message=f"Failed to detect orphan nodes: {str(e)}",
                validation_type="orphan_detection",
                details={"node_label": node_label, "error": str(e)},
            ) from e

    def detect_orphan_articles(
        self,
        trace_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Detect Article nodes without BELONGS_TO relationship to Group.
        
        Args:
            trace_id: Trace ID for correlation
            
        Returns:
            List of orphaned articles
        """
        try:
            query = """
            MATCH (a:Article)
            WHERE NOT (a)-[:BELONGS_TO]->(:Group)
            RETURN a, id(a) as internal_id
            LIMIT 1000
            """
            
            result = self.client.execute_query(query, {}, trace_id=trace_id)
            
            orphans = []
            for record in result:
                article = record.get("a", {})
                internal_id = record.get("internal_id")
                
                orphans.append({
                    "article": article,
                    "internal_id": internal_id,
                })
            
            logger.warning(
                "orphan_articles_detected",
                orphan_count=len(orphans),
                trace_id=trace_id,
            )
            
            return orphans
            
        except Exception as e:
            logger.error(
                "orphan_article_detection_failed",
                error=str(e),
                trace_id=trace_id,
            )
            return []

    def detect_orphan_entities(
        self,
        trace_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Detect Entity nodes without MENTIONS relationship from Article.
        
        Args:
            trace_id: Trace ID for correlation
            
        Returns:
            List of orphaned entities
        """
        try:
            query = """
            MATCH (e:Entity)
            WHERE NOT (:Article)-[:MENTIONS]->(e)
            RETURN e, id(e) as internal_id
            LIMIT 1000
            """
            
            result = self.client.execute_query(query, {}, trace_id=trace_id)
            
            orphans = []
            for record in result:
                entity = record.get("e", {})
                internal_id = record.get("internal_id")
                
                orphans.append({
                    "entity": entity,
                    "internal_id": internal_id,
                })
            
            logger.warning(
                "orphan_entities_detected",
                orphan_count=len(orphans),
                trace_id=trace_id,
            )
            
            return orphans
            
        except Exception as e:
            logger.error(
                "orphan_entity_detection_failed",
                error=str(e),
                trace_id=trace_id,
            )
            return []

    def detect_orphan_predictions(
        self,
        trace_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Detect Prediction nodes without PREDICTS relationship to Group.
        
        Args:
            trace_id: Trace ID for correlation
            
        Returns:
            List of orphaned predictions
        """
        try:
            query = """
            MATCH (p:Prediction)
            WHERE NOT (p)-[:PREDICTS]->(:Group)
            RETURN p, id(p) as internal_id
            LIMIT 1000
            """
            
            result = self.client.execute_query(query, {}, trace_id=trace_id)
            
            orphans = []
            for record in result:
                prediction = record.get("p", {})
                internal_id = record.get("internal_id")
                
                orphans.append({
                    "prediction": prediction,
                    "internal_id": internal_id,
                })
            
            logger.warning(
                "orphan_predictions_detected",
                orphan_count=len(orphans),
                trace_id=trace_id,
            )
            
            return orphans
            
        except Exception as e:
            logger.error(
                "orphan_prediction_detection_failed",
                error=str(e),
                trace_id=trace_id,
            )
            return []

    def delete_orphan_nodes(
        self,
        node_label: Optional[str] = None,
        dry_run: bool = True,
        trace_id: Optional[str] = None,
    ) -> int:
        """
        Delete orphaned nodes.
        
        Args:
            node_label: Node label to delete (None = all orphans)
            dry_run: If True, only count without deleting
            trace_id: Trace ID for correlation
            
        Returns:
            Number of nodes deleted (or would be deleted if dry_run)
        """
        try:
            # First detect orphans
            orphans = self.detect_orphan_nodes(node_label, trace_id)
            
            if dry_run:
                logger.info(
                    "orphan_deletion_dry_run",
                    node_label=node_label or "all",
                    would_delete_count=len(orphans),
                    trace_id=trace_id,
                )
                return len(orphans)
            
            # Delete orphans
            if node_label:
                query = f"""
                MATCH (n:{node_label})
                WHERE NOT (n)--()
                DELETE n
                RETURN count(n) as deleted_count
                """
            else:
                query = """
                MATCH (n)
                WHERE NOT (n)--()
                DELETE n
                RETURN count(n) as deleted_count
                """
            
            result = self.client.execute_query(query, {}, trace_id=trace_id)
            deleted_count = result[0].get("deleted_count", 0) if result else 0
            
            logger.warning(
                "orphan_nodes_deleted",
                node_label=node_label or "all",
                deleted_count=deleted_count,
                trace_id=trace_id,
            )
            
            return deleted_count
            
        except Exception as e:
            logger.error(
                "orphan_deletion_failed",
                node_label=node_label,
                error=str(e),
                trace_id=trace_id,
            )
            raise ValidationError(
                message=f"Failed to delete orphan nodes: {str(e)}",
                validation_type="orphan_deletion",
                details={"node_label": node_label, "error": str(e)},
            ) from e


# Global orphan detector instance
orphan_detector = OrphanDetector()

