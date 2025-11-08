"""
Relationship models for Neo4j graph.
Defines all relationship types and their properties.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class MentionsRelationship(BaseModel):
    """
    MENTIONS relationship: Article → Entity
    
    Represents an article mentioning an entity.
    """
    
    frequency: int = Field(
        default=1,
        description="Number of times entity is mentioned",
        ge=1,
    )
    
    position: Optional[int] = Field(
        default=None,
        description="First occurrence position in text",
        ge=0,
    )
    
    confidence: float = Field(
        default=1.0,
        description="NER confidence score [0.0, 1.0]",
        ge=0.0,
        le=1.0,
    )
    
    def to_neo4j_properties(self) -> dict:
        """Convert to Neo4j relationship properties."""
        return self.model_dump(exclude_none=True)


class BelongsToRelationship(BaseModel):
    """
    BELONGS_TO relationship: Article → Group
    
    Represents an article belonging to a semantic group.
    """
    
    membership_score: float = Field(
        ...,
        description="Membership score [0.0, 1.0]",
        ge=0.0,
        le=1.0,
    )
    
    def to_neo4j_properties(self) -> dict:
        """Convert to Neo4j relationship properties."""
        return self.model_dump(exclude_none=True)


class RelatedToRelationship(BaseModel):
    """
    RELATED_TO relationship: Group → Group
    
    Represents semantic similarity between groups.
    """
    
    similarity_score: float = Field(
        ...,
        description="Cosine similarity score [0.0, 1.0]",
        ge=0.0,
        le=1.0,
    )
    
    @field_validator("similarity_score")
    @classmethod
    def validate_similarity(cls, v: float) -> float:
        """Validate similarity score."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Similarity score must be between 0.0 and 1.0")
        return v
    
    def to_neo4j_properties(self) -> dict:
        """Convert to Neo4j relationship properties."""
        return self.model_dump(exclude_none=True)


class InvolvesRelationship(BaseModel):
    """
    INVOLVES relationship: Group → Actor
    
    Represents a group involving an actor.
    """
    
    involvement_score: float = Field(
        default=1.0,
        description="Involvement score [0.0, 1.0]",
        ge=0.0,
        le=1.0,
    )
    
    role: Optional[str] = Field(
        default=None,
        description="Actor's role in the group",
        max_length=256,
    )
    
    def to_neo4j_properties(self) -> dict:
        """Convert to Neo4j relationship properties."""
        return self.model_dump(exclude_none=True)


class PredictsRelationship(BaseModel):
    """
    PREDICTS relationship: Prediction → Group
    
    Represents a prediction about a group.
    """
    
    prediction_score: float = Field(
        ...,
        description="Prediction score [0.0, 1.0]",
        ge=0.0,
        le=1.0,
    )
    
    confidence: float = Field(
        ...,
        description="Prediction confidence [0.0, 1.0]",
        ge=0.0,
        le=1.0,
    )
    
    def to_neo4j_properties(self) -> dict:
        """Convert to Neo4j relationship properties."""
        return self.model_dump(exclude_none=True)


class ReferencesRelationship(BaseModel):
    """
    REFERENCES relationship: Entity → Entity
    
    Represents one entity referencing another.
    """
    
    reference_type: str = Field(
        ...,
        description="Type of reference (co-occurrence, alias, related)",
        max_length=64,
    )
    
    weight: float = Field(
        default=1.0,
        description="Reference weight [0.0, 1.0]",
        ge=0.0,
        le=1.0,
    )
    
    @field_validator("reference_type")
    @classmethod
    def validate_reference_type(cls, v: str) -> str:
        """Validate reference type."""
        allowed_types = {"co-occurrence", "alias", "related"}
        if v.lower() not in allowed_types:
            raise ValueError(f"Reference type must be one of {allowed_types}")
        return v.lower()
    
    def to_neo4j_properties(self) -> dict:
        """Convert to Neo4j relationship properties."""
        return self.model_dump(exclude_none=True)


# Relationship type mapping
RELATIONSHIP_TYPES = {
    "MENTIONS": MentionsRelationship,
    "BELONGS_TO": BelongsToRelationship,
    "RELATED_TO": RelatedToRelationship,
    "INVOLVES": InvolvesRelationship,
    "PREDICTS": PredictsRelationship,
    "REFERENCES": ReferencesRelationship,
}


def get_relationship_model(relationship_type: str) -> type[BaseModel]:
    """
    Get relationship model class by type.
    
    Args:
        relationship_type: Relationship type name
        
    Returns:
        Relationship model class
        
    Raises:
        ValueError: If relationship type is unknown
    """
    if relationship_type not in RELATIONSHIP_TYPES:
        raise ValueError(f"Unknown relationship type: {relationship_type}")
    return RELATIONSHIP_TYPES[relationship_type]

