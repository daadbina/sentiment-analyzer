"""
Node builders for creating Neo4j nodes from Kafka messages.
Implements the Builder pattern for graph node construction.
"""

from typing import Dict, Any, List, Optional
import structlog

from ..models import Article, Group, Entity, Actor, Prediction
from ..exceptions import ValidationError

logger = structlog.get_logger(__name__)


class NodeBuilder:
    """
    Builder for creating Neo4j nodes from Kafka messages.
    """

    @staticmethod
    def build_article_node(message: Dict[str, Any]) -> Article:
        """
        Build Article node from news_canonical message.
        
        Args:
            message: Kafka message from news_canonical topic
            
        Returns:
            Article model instance
            
        Raises:
            ValidationError: If article creation fails
        """
        try:
            article = Article.from_kafka_message(message)
            logger.debug(
                "article_node_built",
                article_id=article.id,
                source=article.source,
            )
            return article
        except Exception as e:
            logger.error(
                "article_node_build_failed",
                error=str(e),
                message_keys=list(message.keys()),
            )
            raise ValidationError(
                message=f"Failed to build Article node: {str(e)}",
                validation_type="node_construction",
                details={"node_type": "Article", "error": str(e)},
            ) from e

    @staticmethod
    def build_group_node(message: Dict[str, Any]) -> Group:
        """
        Build Group node from semantic_groups message.
        
        Args:
            message: Kafka message from semantic_groups topic
            
        Returns:
            Group model instance
            
        Raises:
            ValidationError: If group creation fails
        """
        try:
            group = Group.from_kafka_message(message)
            logger.debug(
                "group_node_built",
                group_id=group.id,
                size=group.size,
                topic_label=group.topic_label,
            )
            return group
        except Exception as e:
            logger.error(
                "group_node_build_failed",
                error=str(e),
                message_keys=list(message.keys()),
            )
            raise ValidationError(
                message=f"Failed to build Group node: {str(e)}",
                validation_type="node_construction",
                details={"node_type": "Group", "error": str(e)},
            ) from e

    @staticmethod
    def build_entity_nodes(message: Dict[str, Any]) -> List[Entity]:
        """
        Build Entity nodes from entities_extracted message.
        
        Args:
            message: Kafka message from entities_extracted topic
            
        Returns:
            List of Entity model instances
            
        Raises:
            ValidationError: If entity creation fails
        """
        try:
            entities = []
            entity_list = message.get("entities", [])
            
            for entity_data in entity_list:
                entity = Entity.from_kafka_message(entity_data)
                entities.append(entity)
            
            logger.debug(
                "entity_nodes_built",
                article_id=message.get("article_id"),
                entity_count=len(entities),
            )
            return entities
        except Exception as e:
            logger.error(
                "entity_nodes_build_failed",
                error=str(e),
                message_keys=list(message.keys()),
            )
            raise ValidationError(
                message=f"Failed to build Entity nodes: {str(e)}",
                validation_type="node_construction",
                details={"node_type": "Entity", "error": str(e)},
            ) from e

    @staticmethod
    def build_prediction_node(message: Dict[str, Any]) -> Prediction:
        """
        Build Prediction node from predictions message.
        
        Args:
            message: Kafka message from predictions topic
            
        Returns:
            Prediction model instance
            
        Raises:
            ValidationError: If prediction creation fails
        """
        try:
            prediction = Prediction.from_kafka_message(message)
            logger.debug(
                "prediction_node_built",
                prediction_id=prediction.id,
                group_id=prediction.group_id,
                domain=prediction.domain,
            )
            return prediction
        except Exception as e:
            logger.error(
                "prediction_node_build_failed",
                error=str(e),
                message_keys=list(message.keys()),
            )
            raise ValidationError(
                message=f"Failed to build Prediction node: {str(e)}",
                validation_type="node_construction",
                details={"node_type": "Prediction", "error": str(e)},
            ) from e

    @staticmethod
    def build_cypher_create_query(
        node_label: str,
        properties: Dict[str, Any],
        node_id: str,
    ) -> tuple[str, Dict[str, Any]]:
        """
        Build Cypher MERGE query for node creation with conflict resolution.
        
        Args:
            node_label: Node label (Article, Group, Entity, Actor, Prediction)
            properties: Node properties
            node_id: Node ID for MERGE
            
        Returns:
            Tuple of (query, parameters)
        """
        # Use MERGE for upsert behavior (last-write-wins)
        query = f"""
        MERGE (n:{node_label} {{id: $node_id}})
        ON CREATE SET n = $properties, n.created_at = datetime()
        ON MATCH SET n += $properties, n.updated_at = datetime()
        RETURN n
        """
        
        parameters = {
            "node_id": node_id,
            "properties": properties,
        }
        
        return query, parameters

    @staticmethod
    def build_batch_create_query(
        node_label: str,
        batch_data: List[Dict[str, Any]],
    ) -> tuple[str, Dict[str, Any]]:
        """
        Build Cypher UNWIND query for batch node creation.
        
        Args:
            node_label: Node label
            batch_data: List of node property dictionaries
            
        Returns:
            Tuple of (query, parameters)
        """
        query = f"""
        UNWIND $batch AS item
        MERGE (n:{node_label} {{id: item.id}})
        ON CREATE SET n = item, n.created_at = datetime()
        ON MATCH SET n += item, n.updated_at = datetime()
        RETURN count(n) as nodes_created
        """
        
        parameters = {
            "batch": batch_data,
        }
        
        return query, parameters


# Global node builder instance
node_builder = NodeBuilder()

