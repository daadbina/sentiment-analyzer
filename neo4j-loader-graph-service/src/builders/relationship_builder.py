"""
Relationship builders for creating Neo4j relationships.
Implements the Builder pattern for graph relationship construction.
"""

from typing import Dict, Any, List, Optional
import structlog

from ..models.relationships import (
    MentionsRelationship,
    BelongsToRelationship,
    RelatedToRelationship,
    InvolvesRelationship,
    PredictsRelationship,
    ReferencesRelationship,
)
from ..exceptions import ValidationError

logger = structlog.get_logger(__name__)


class RelationshipBuilder:
    """
    Builder for creating Neo4j relationships.
    """

    @staticmethod
    def build_mentions_relationship(
        article_id: str,
        entity_id: str,
        frequency: int = 1,
        position: Optional[int] = None,
        confidence: float = 1.0,
    ) -> tuple[str, str, str, Dict[str, Any]]:
        """
        Build MENTIONS relationship: Article → Entity
        
        Args:
            article_id: Article node ID
            entity_id: Entity node ID
            frequency: Mention frequency
            position: First occurrence position
            confidence: NER confidence score
            
        Returns:
            Tuple of (from_id, to_id, rel_type, properties)
        """
        relationship = MentionsRelationship(
            frequency=frequency,
            position=position,
            confidence=confidence,
        )
        
        return (
            article_id,
            entity_id,
            "MENTIONS",
            relationship.to_neo4j_properties(),
        )

    @staticmethod
    def build_belongs_to_relationship(
        article_id: str,
        group_id: str,
        membership_score: float,
    ) -> tuple[str, str, str, Dict[str, Any]]:
        """
        Build BELONGS_TO relationship: Article → Group
        
        Args:
            article_id: Article node ID
            group_id: Group node ID
            membership_score: Membership score
            
        Returns:
            Tuple of (from_id, to_id, rel_type, properties)
        """
        relationship = BelongsToRelationship(
            membership_score=membership_score,
        )
        
        return (
            article_id,
            group_id,
            "BELONGS_TO",
            relationship.to_neo4j_properties(),
        )

    @staticmethod
    def build_related_to_relationship(
        group_id_1: str,
        group_id_2: str,
        similarity_score: float,
    ) -> tuple[str, str, str, Dict[str, Any]]:
        """
        Build RELATED_TO relationship: Group → Group
        
        Args:
            group_id_1: First group node ID
            group_id_2: Second group node ID
            similarity_score: Similarity score
            
        Returns:
            Tuple of (from_id, to_id, rel_type, properties)
        """
        relationship = RelatedToRelationship(
            similarity_score=similarity_score,
        )
        
        return (
            group_id_1,
            group_id_2,
            "RELATED_TO",
            relationship.to_neo4j_properties(),
        )

    @staticmethod
    def build_involves_relationship(
        group_id: str,
        actor_id: str,
        involvement_score: float = 1.0,
        role: Optional[str] = None,
    ) -> tuple[str, str, str, Dict[str, Any]]:
        """
        Build INVOLVES relationship: Group → Actor
        
        Args:
            group_id: Group node ID
            actor_id: Actor node ID
            involvement_score: Involvement score
            role: Actor's role
            
        Returns:
            Tuple of (from_id, to_id, rel_type, properties)
        """
        relationship = InvolvesRelationship(
            involvement_score=involvement_score,
            role=role,
        )
        
        return (
            group_id,
            actor_id,
            "INVOLVES",
            relationship.to_neo4j_properties(),
        )

    @staticmethod
    def build_predicts_relationship(
        prediction_id: str,
        group_id: str,
        prediction_score: float,
        confidence: float,
    ) -> tuple[str, str, str, Dict[str, Any]]:
        """
        Build PREDICTS relationship: Prediction → Group
        
        Args:
            prediction_id: Prediction node ID
            group_id: Group node ID
            prediction_score: Prediction score
            confidence: Confidence score
            
        Returns:
            Tuple of (from_id, to_id, rel_type, properties)
        """
        relationship = PredictsRelationship(
            prediction_score=prediction_score,
            confidence=confidence,
        )
        
        return (
            prediction_id,
            group_id,
            "PREDICTS",
            relationship.to_neo4j_properties(),
        )

    @staticmethod
    def build_references_relationship(
        entity_id_1: str,
        entity_id_2: str,
        reference_type: str,
        weight: float = 1.0,
    ) -> tuple[str, str, str, Dict[str, Any]]:
        """
        Build REFERENCES relationship: Entity → Entity
        
        Args:
            entity_id_1: First entity node ID
            entity_id_2: Second entity node ID
            reference_type: Type of reference
            weight: Reference weight
            
        Returns:
            Tuple of (from_id, to_id, rel_type, properties)
        """
        relationship = ReferencesRelationship(
            reference_type=reference_type,
            weight=weight,
        )
        
        return (
            entity_id_1,
            entity_id_2,
            "REFERENCES",
            relationship.to_neo4j_properties(),
        )

    @staticmethod
    def build_cypher_create_relationship_query(
        from_label: str,
        from_id: str,
        to_label: str,
        to_id: str,
        rel_type: str,
        properties: Dict[str, Any],
    ) -> tuple[str, Dict[str, Any]]:
        """
        Build Cypher query for relationship creation.
        
        Args:
            from_label: Source node label
            from_id: Source node ID
            to_label: Target node label
            to_id: Target node ID
            rel_type: Relationship type
            properties: Relationship properties
            
        Returns:
            Tuple of (query, parameters)
        """
        query = f"""
        MATCH (from:{from_label} {{id: $from_id}})
        MATCH (to:{to_label} {{id: $to_id}})
        MERGE (from)-[r:{rel_type}]->(to)
        ON CREATE SET r = $properties, r.created_at = datetime()
        ON MATCH SET r += $properties, r.updated_at = datetime()
        RETURN r
        """
        
        parameters = {
            "from_id": from_id,
            "to_id": to_id,
            "properties": properties,
        }
        
        return query, parameters

    @staticmethod
    def build_batch_create_relationships_query(
        from_label: str,
        to_label: str,
        rel_type: str,
        batch_data: List[Dict[str, Any]],
    ) -> tuple[str, Dict[str, Any]]:
        """
        Build Cypher UNWIND query for batch relationship creation.
        
        Args:
            from_label: Source node label
            to_label: Target node label
            rel_type: Relationship type
            batch_data: List of relationship data (from_id, to_id, properties)
            
        Returns:
            Tuple of (query, parameters)
        """
        query = f"""
        UNWIND $batch AS item
        MATCH (from:{from_label} {{id: item.from_id}})
        MATCH (to:{to_label} {{id: item.to_id}})
        MERGE (from)-[r:{rel_type}]->(to)
        ON CREATE SET r = item.properties, r.created_at = datetime()
        ON MATCH SET r += item.properties, r.updated_at = datetime()
        RETURN count(r) as relationships_created
        """
        
        parameters = {
            "batch": batch_data,
        }
        
        return query, parameters


# Global relationship builder instance
relationship_builder = RelationshipBuilder()

